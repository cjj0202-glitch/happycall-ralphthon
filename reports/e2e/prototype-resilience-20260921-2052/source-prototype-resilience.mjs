import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';

const base = process.env.RESILIENCE_URL || 'http://127.0.0.1:8851';
const output = process.env.RESILIENCE_OUTPUT || '.local/prototype-resilience-after';
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || 'C:/Users/choi8/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe', headless: true });
const results = { startedAt: new Date().toISOString(), base, checks: [], http: [], pageErrors: [], external: [], failures: [] };
results.runnerSha256=createHash('sha256').update(await readFile(new URL(import.meta.url))).digest('hex');
if(process.env.RESILIENCE_METADATA)results.serverMetadata=JSON.parse(await readFile(process.env.RESILIENCE_METADATA,'utf8'));
const check = (name, actual, expected) => { assert.deepEqual(actual, expected, name); results.checks.push({ name, actual, expected }); };
const contexts = [];
const nav = (page, name) => page.getByRole('navigation').getByRole('button', { name, exact: true }).click();
const subject = page => page.getByRole('textbox', { name: '상품·문의 대상 필수', exact: true });
const caseButton = (page, id) => page.locator('.case-button').filter({ hasText: id });
const refresh = async page => { await page.getByRole('button', { name: '목록 새로고침', exact: true }).click(); await page.getByRole('button', { name: '목록 새로고침', exact: true }).waitFor(); };
const api = async (page, url, method = 'GET', data, role = 'counselor') => {
  const response = await page.request.fetch(base + url, { method, data, headers: { 'X-Demo-Role': role } });
  assert.ok(response.ok(), `${method} ${url}: ${response.status()} ${await response.text()}`); return response.json();
};
async function newPage(width = 1440) {
  const context = await browser.newContext({ viewport: { width, height: 1000 } }); contexts.push(context);
  const page = await context.newPage();
  page.on('pageerror', error => results.pageErrors.push(error.message));
  page.on('request', req => { if (/^https?:/.test(req.url()) && !req.url().startsWith(base)) results.external.push(req.url()); });
  page.on('response', response => { if (response.url().includes('/api/')) results.http.push({ method: response.request().method(), path: new URL(response.url()).pathname.replace(/(\/api\/intake-attempts\/)[^/]+/, '$1[request-key]'), status: response.status() }); });
  await page.goto(base); await subject(page).waitFor(); return page;
}
await mkdir(output, { recursive: true });
try {
  const counselor = await newPage(); const center = await newPage(); const owner = await newPage();
  await subject(counselor).fill('상담 초안 A'); await nav(counselor, 'WMS 작업 확인'); await nav(counselor, '상담 작업대');
  check('desk same-case tab draft preserved', await subject(counselor).inputValue(), '상담 초안 A');
  await caseButton(counselor, 'CASE-0002').click(); await subject(counselor).fill('상담 초안 B'); await caseButton(counselor, 'CASE-0001').click();
  check('desk different-case draft isolated', await subject(counselor).inputValue(), '상담 초안 A');
  await nav(center, '센터 회신'); await center.getByLabel('경영주에게 등록할 회신').fill('센터 임시 회신'); await center.getByLabel('남은 조치 내용').fill('작성 중인 조치');
  await nav(center, 'TMS 배송 확인'); await nav(center, '센터 회신');
  check('center reply/action preserved', [await center.getByLabel('경영주에게 등록할 회신').inputValue(), await center.getByLabel('남은 조치 내용').inputValue()], ['센터 임시 회신','작성 중인 조치']);

  await nav(owner, '경영주 접수'); await owner.getByRole('textbox',{name:'점포코드',exact:true}).fill('SYN-PROTOTYPE-01'); await owner.getByRole('textbox',{name:'문의 제목',exact:true}).fill('동일 접수 복구 검증'); await owner.getByLabel('상세 내용').fill('오늘 배송이 도착하지 않았습니다. 도착 여부를 확인해 주세요.');
  await nav(owner, 'TMS 배송 확인'); await nav(owner, '경영주 접수');
  check('owner draft preserved', await owner.getByLabel('상세 내용').inputValue(), '오늘 배송이 도착하지 않았습니다. 도착 여부를 확인해 주세요.');
  const before = (await api(owner, '/api/cases')).cases.length;
  const postAttempts = []; let lostResponse; let acknowledgeCommit;
  const committed = new Promise(resolve => { acknowledgeCommit = resolve; });
  await owner.route('**/api/intake', async route => {
    if (route.request().method() !== 'POST') return route.continue();
    postAttempts.push({ key: route.request().headers()['x-idempotency-key'], body: route.request().postDataJSON() });
    const response = await route.fetch(); const body = await response.json();
    if (!lostResponse) { lostResponse = { status: response.status(), id: body.id, revision: body.revision }; await route.abort('failed'); acknowledgeCommit(); return; }
    await route.fulfill({ response });
  });
  await owner.getByRole('button', { name: '문의 접수하기', exact: true }).click(); await owner.getByRole('button', { name: '접수 저장 여부 확인', exact: true }).waitFor();
  await committed; await owner.locator('.notice[role=alert]').filter({hasText:'응답을 받지 못해'}).waitFor();
  check('POST committed before response loss', lostResponse.status, 201);
  check('unknown POST locks original input', await owner.getByLabel('상세 내용').isDisabled(), true);
  check('unknown POST prevents new submit', await owner.getByRole('button', { name: '문의 접수하기', exact: true }).isDisabled(), true);
  // A lagging lookup is a hostile boundary: even 404 must not create a new key.
  await owner.route('**/api/intake-attempts/*', route => route.fulfill({ status: 404, contentType:'application/json', body: JSON.stringify({ error: { code:'INTAKE_ATTEMPT_NOT_FOUND', message:'아직 확인되지 않았습니다.' } }) }), { times: 1 });
  await owner.getByRole('button', { name: '접수 저장 여부 확인', exact: true }).click(); await owner.getByRole('button', { name:'같은 내용으로 접수 확인·재시도', exact:true }).click();
  await owner.getByText(`${lostResponse.id} 접수가 등록되었습니다.`, { exact:true }).waitFor();
  check('same key and payload after lookup 404', { keyMatches: postAttempts[1].key === postAttempts[0].key, payloadMatches: JSON.stringify(postAttempts[1].body) === JSON.stringify(postAttempts[0].body) }, { keyMatches: true, payloadMatches: true });
  check('UUID v4 key supplied', /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(postAttempts[0].key), true);
  check('response loss retry creates exactly one case', (await api(owner,'/api/cases')).cases.length - before, 1);
  await owner.unroute('**/api/intake'); const caseId = lostResponse.id;

  await refresh(counselor); await caseButton(counselor, caseId).click();
  await counselor.getByPlaceholder('경영주가 요청한 내용을 확인해 주세요.', { exact:true }).fill('배송 여부 확인 후 안내해 주세요.'); await counselor.locator('.department-card select').selectOption('delivery');
  await counselor.locator('.review-check input').check();
  await counselor.getByRole('button', { name:'접수 내용 저장',exact:true }).click(); await counselor.getByText('상담원이 편집한 접수 정보를 저장했습니다.',{exact:true}).waitFor();
  check('saved confirmation retains meaning', await counselor.locator('.review-check input').isChecked(), true);
  await counselor.getByRole('button', { name:'확인 후 센터 전달',exact:true }).click(); await counselor.getByText('확인한 접수 내용과 근거를 센터에 전달했습니다.',{exact:true}).waitFor();
  check('actual counselor handoff PATCH', (await api(counselor,`/api/cases/${caseId}`)).status, 'handed_off');
  await refresh(center); await caseButton(center,caseId).click();
  await center.getByLabel('경영주에게 등록할 회신').fill('배송 기록을 확인하고 있습니다. 기사 확인 후 추가 안내하겠습니다.'); await center.getByLabel('남은 조치 내용').fill('기사 확인');
  check('unadded action prevents accidental close', await center.getByRole('button',{name:'최종 회신·처리 완료',exact:true}).isDisabled(),true);
  await center.getByRole('button',{name:'조치 추가',exact:true}).click();
  let centerAbort = true; await center.route(`**/api/cases/${caseId}`, async route => {
    if (route.request().method() !== 'PATCH' || !centerAbort) return route.continue();
    centerAbort = false; const response = await route.fetch(); check('center response-loss PATCH really committed',response.status(),200); await route.abort('failed');
  });
  await center.getByRole('button',{name:'중간 회신 등록',exact:true}).click(); await center.getByRole('button',{name:'회신 저장 여부 확인',exact:true}).waitFor();
  check('unknown center save blocks blind retry',await center.getByRole('button',{name:'중간 회신 등록',exact:true}).isDisabled(),true);
  check('unknown center save protects submitted reply from new edits',await center.getByLabel('경영주에게 등록할 회신').isDisabled(),true);
  await center.getByRole('button',{name:'회신 저장 여부 확인',exact:true}).click(); await center.getByText('서버에 요청한 회신이 저장되어 있음을 확인했습니다.',{exact:true}).waitFor();
  await refresh(owner); check('independent owner receives registered reply', await owner.locator('.registered-reply p').innerText(), '배송 기록을 확인하고 있습니다. 기사 확인 후 추가 안내하겠습니다.');
  await center.getByRole('button',{name:'기사 확인 조치 완료',exact:true}).click(); await center.getByLabel('경영주에게 등록할 회신').fill('기사 확인 후 도착 기록을 확인했습니다. 문의 처리를 완료합니다.');
  await center.getByRole('button',{name:'최종 회신·처리 완료',exact:true}).click(); await center.getByText('회신을 등록하고 처리를 완료했습니다. 경영주 화면에도 반영되었습니다.',{exact:true}).waitFor();
  await refresh(owner); check('three-context completed receipt',await owner.locator('.receipt .badge').first().innerText(),'처리 완료');
  check('final stored reply delivered',await owner.locator('.registered-reply p').innerText(),'기사 확인 후 도착 기록을 확인했습니다. 문의 처리를 완료합니다.');

  await nav(counselor,'상담 작업대'); await caseButton(counselor,'CASE-0001').click();
  const original = await api(counselor,'/api/cases/CASE-0001');
  await api(counselor,'/api/cases/CASE-0001','PATCH',{expectedRevision:original.revision,intake:{...original.intake,request:'다른 담당자의 최신 요청'},status:'review'});
  await refresh(counselor); check('refresh never overwrites unsaved form',await subject(counselor).inputValue(),'상담 초안 A');
  check('stale revision blocks save',await counselor.getByRole('button',{name:'접수 내용 저장',exact:true}).isDisabled(),true);
  await counselor.getByRole('button',{name:'최신 내용 대조',exact:true}).click(); await counselor.getByRole('region',{name:'최신 서버 내용과 초안 대조'}).waitFor();
  check('comparison contains independently stored request',(await counselor.getByRole('region',{name:'최신 서버 내용과 초안 대조'}).innerText()).includes('다른 담당자의 최신 요청'),true);
  await counselor.getByRole('button',{name:'내 초안 유지 · 다시 확인',exact:true}).focus(); await counselor.keyboard.press('Enter');
  check('keyboard explicit keep clears human confirmation',await counselor.locator('.review-check input').isChecked(),false);
  check('keep draft retains local subject',await subject(counselor).inputValue(),'상담 초안 A');
  check('keep choice alone performs no server write',(await api(counselor,'/api/cases/CASE-0001')).intake.subject,original.intake.subject);
  await counselor.getByRole('button',{name:'접수 내용 저장',exact:true}).click(); await counselor.getByText('상담원이 편집한 접수 정보를 저장했습니다.',{exact:true}).waitFor();
  check('explicitly rebased draft persists real PATCH',(await api(counselor,'/api/cases/CASE-0001')).intake.subject,'상담 초안 A');

  await counselor.getByPlaceholder('경영주가 요청한 내용을 확인해 주세요.', { exact:true }).fill('저장 응답 유실 복구');
  await counselor.route('**/api/cases/CASE-0001',async route=>{if(route.request().method()!=='PATCH')return route.continue();const response=await route.fetch();check('desk response-loss PATCH committed',response.status(),200);await route.abort('failed');},{times:1});
  await counselor.getByRole('button',{name:'접수 내용 저장',exact:true}).click(); await counselor.getByRole('button',{name:'저장 여부 확인',exact:true}).waitFor();
  check('unknown desk save protects submitted form from new edits',await subject(counselor).isDisabled(),true);
  await counselor.getByRole('button',{name:'저장 여부 확인',exact:true}).click(); await counselor.getByText('서버에 요청한 접수 내용이 저장되어 있음을 확인했습니다.',{exact:true}).waitFor();
  check('desk recovered server payload',(await api(counselor,'/api/cases/CASE-0001')).intake.request,'저장 응답 유실 복구');

  let releaseSave, markSaved;
  const saveGate = new Promise(resolve => { releaseSave = resolve; });
  const saveArrived = new Promise(resolve => { markSaved = resolve; });
  await counselor.getByPlaceholder('경영주가 요청한 내용을 확인해 주세요.',{exact:true}).fill('지연 응답에서도 초안 보호');
  await counselor.route('**/api/cases/CASE-0001',async route=>{if(route.request().method()!=='PATCH')return route.continue();const response=await route.fetch();markSaved();await saveGate;await route.fulfill({response});},{times:1});
  await counselor.getByRole('button',{name:'접수 내용 저장',exact:true}).click(); await saveArrived;
  await nav(counselor,'WMS 작업 확인'); await nav(counselor,'상담 작업대');
  check('in-flight save remains locked after menu remount',await subject(counselor).isDisabled(),true);
  check('in-flight save cannot be sent twice',await counselor.getByRole('button',{name:'접수 내용 저장',exact:true}).isDisabled(),true);
  releaseSave(); await counselor.getByText('상담원이 편집한 접수 정보를 저장했습니다.',{exact:true}).waitFor();
  check('delayed save applies to original case',(await api(counselor,'/api/cases/CASE-0001')).intake.request,'지연 응답에서도 초안 보호');

  await caseButton(counselor,'CASE-0002').click();
  const otherCase=await api(counselor,'/api/cases/CASE-0002');
  await api(counselor,'/api/cases/CASE-0002','PATCH',{expectedRevision:otherCase.revision,intake:{...otherCase.intake,request:'실제 충돌 대조군'},status:'review'});
  await counselor.getByRole('button',{name:'접수 내용 저장',exact:true}).click();
  await counselor.getByRole('region',{name:'최신 서버 내용과 초안 대조'}).waitFor();
  check('409 preserves original local draft',await subject(counselor).inputValue(),'상담 초안 B');
  check('409 did not overwrite remote request',(await api(counselor,'/api/cases/CASE-0002')).intake.request,'실제 충돌 대조군');
  check('actual PATCH 409 recorded',results.http.some(item=>item.method==='PATCH'&&item.path==='/api/cases/CASE-0002'&&item.status===409),true);
  await counselor.getByRole('button',{name:'서버 내용 사용',exact:true}).click();
  await caseButton(counselor,'CASE-0001').click();

  await owner.getByRole('textbox',{name:'문의 제목',exact:true}).fill('조회로 복구되는 새 접수');
  await owner.getByLabel('상세 내용').fill('두 번째 문의입니다. 기존 문의와 별도로 배송 여부를 확인해 주세요.');
  const beforeLookup=(await api(owner,'/api/cases')).cases.length; let secondId='';
  await owner.route('**/api/intake',async route=>{const response=await route.fetch();secondId=(await response.json()).id;await route.abort('failed');},{times:1});
  await owner.getByRole('button',{name:'문의 접수하기',exact:true}).click();
  await owner.locator('.notice[role=alert]').filter({hasText:'응답을 받지 못해'}).waitFor();
  await owner.getByRole('button',{name:'접수 저장 여부 확인',exact:true}).click();
  await owner.getByText(`${secondId} 접수가 등록되었습니다.`,{exact:true}).waitFor();
  check('GET attempt 200 restores committed intake once',(await api(owner,'/api/cases')).cases.length-beforeLookup,1);
  check('confirmed intake unlocks input',await owner.getByLabel('상세 내용').isDisabled(),false);

  for (const width of [1440,1024,390]) {
    await counselor.setViewportSize({width,height:1000});
    await subject(counselor).fill(`폭 ${width} 초안`); const current=await api(counselor,'/api/cases/CASE-0001');
    await api(counselor,'/api/cases/CASE-0001','PATCH',{expectedRevision:current.revision,intake:{...current.intake,request:`폭 ${width} 서버 변경`},status:'review'});
    await refresh(counselor); await counselor.getByRole('button',{name:'최신 내용 대조',exact:true}).click();
    const region=counselor.getByRole('region',{name:'최신 서버 내용과 초안 대조'}); await region.waitFor();
    check(`horizontal overflow at ${width}`,await counselor.evaluate(()=>Math.max(0,document.documentElement.scrollWidth-innerWidth)),0);
    await region.screenshot({path:path.join(output,`recovery-${width}.png`)});
    await counselor.getByRole('button',{name:'서버 내용 사용',exact:true}).focus(); await counselor.keyboard.press('Enter');
    check(`server choice loaded at ${width}`,await counselor.getByPlaceholder('경영주가 요청한 내용을 확인해 주세요.', { exact:true }).inputValue(),`폭 ${width} 서버 변경`);
  }
  // A separate fixture-backed setup supplies a real stored AI draft. This is a
  // no-cost API test precondition, not a claim that voice playback was tested here.
  await api(center,'/api/cases/CASE-0002/analyze','POST',{mode:'replay'});
  const centerSetup=await api(center,'/api/cases/CASE-0002');
  await api(center,'/api/cases/CASE-0002','PATCH',{expectedRevision:centerSetup.revision,intake:centerSetup.intake,departmentId:centerSetup.departmentId,reviewConfirmed:true,status:'handed_off'});
  await refresh(center); await caseButton(center,'CASE-0002').click();
  await center.getByRole('button',{name:'초안을 편집창에 가져오기',exact:true}).click();
  await center.getByLabel('남은 조치 내용').fill('분기 기록 확인'); await center.getByRole('button',{name:'조치 추가',exact:true}).click();
  let releaseCenter,markCenter;
  const centerGate=new Promise(resolve=>{releaseCenter=resolve;});const centerArrived=new Promise(resolve=>{markCenter=resolve;});
  await center.route('**/api/cases/CASE-0002',async route=>{if(route.request().method()!=='PATCH')return route.continue();const response=await route.fetch();markCenter();await centerGate;await route.fulfill({response});},{times:1});
  await center.getByRole('button',{name:'중간 회신 등록',exact:true}).click();await centerArrived;
  await nav(center,'TMS 배송 확인');await nav(center,'센터 회신');
  check('center delayed reply stays locked after remount',await center.getByLabel('경영주에게 등록할 회신').isDisabled(),true);
  check('center delayed action text stays locked',await center.getByLabel('남은 조치 내용').isDisabled(),true);
  check('center delayed action completion stays locked',await center.getByRole('button',{name:'분기 기록 확인 조치 완료',exact:true}).isDisabled(),true);
  check('center delayed AI draft import stays locked',await center.getByRole('button',{name:'초안을 편집창에 가져오기',exact:true}).isDisabled(),true);
  check('center delayed reply resubmit stays locked',await center.getByRole('button',{name:'중간 회신 등록',exact:true}).isDisabled(),true);
  await new Promise(resolve=>setTimeout(resolve,3000));releaseCenter();
  await center.getByText('중간 회신을 등록했습니다. 남은 조치는 계속 진행됩니다.',{exact:true}).waitFor();
  check('center unlocks only after response',await center.getByLabel('경영주에게 등록할 회신').isDisabled(),false);
  check('center pending action survived delayed reply',(await api(center,'/api/cases/CASE-0002')).pendingActions,['분기 기록 확인']);
  await subject(counselor).fill('새로고침 경고 초안'); let unloadDialog = '';
  counselor.once('dialog',async dialog=>{unloadDialog=dialog.type();await dialog.dismiss();});
  try{await counselor.reload({timeout:5000});}catch{}
  check('browser beforeunload warning requested',unloadDialog,'beforeunload');
  check('dismissed reload retains draft',await subject(counselor).inputValue(),'새로고침 경고 초안');
  check('console page errors',results.pageErrors,[]); check('external browser requests',results.external,[]);
} catch(error) { results.failures.push({message:error.message,stack:error.stack}); for(const [i,context] of contexts.entries()){const page=context.pages()[0];if(page&&!page.isClosed())await writeFile(path.join(output,`failure-page-${i}.txt`),await page.locator('body').innerText().catch(()=>''));} process.exitCode=1; }
finally { results.finishedAt=new Date().toISOString();await writeFile(path.join(output,'results.json'),JSON.stringify(results,null,2));console.log(JSON.stringify({checks:results.checks.length,failures:results.failures,output}));await browser.close(); }


