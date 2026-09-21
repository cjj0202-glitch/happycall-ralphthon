// Existing product page + real isolated HTTP API. No direct product-state writes.
import { chromium } from '../../e2e/node_modules/playwright/index.mjs';
import assert from 'node:assert/strict';
import { writeFile, readFile } from 'node:fs/promises';
import path from 'node:path';

const UI=process.env.PC4_UI_BASE, API=process.env.PC4_API_BASE, OUT=process.env.PC4_UI_OUT;
assert.ok(UI?.startsWith('http://127.0.0.1:') && API?.startsWith('http://127.0.0.1:') && OUT);
const report={startedAt:new Date().toISOString(),suite:'existing-product-isolated-ui',ui:UI,api:API,executor:'AI Playwright; not human review or live AI',newTmsIntegrated:false,flows:[],boundaries:[],consoleErrors:[],blockedExternal:[],blockedLive:[],http:[],limitations:['Uses existing page.tsx/LogisticsView; new pc4 TmsScene is not integrated','First repetition of each CASE plays the full audio at rate 1; repetitions 2 and 3 seek near the end and await genuine media ended','All setup resets create new test-only temporary stores; original state and budget remain untouched','Replay is saved fixture analysis, not actual STT/LLM']};
const fixtures=JSON.parse(await readFile('data/fixtures/cases.json','utf8')).cases;
const persist=()=>writeFile(path.join(OUT,'results.json'),JSON.stringify(report,null,2));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function readCase(id){const response=await fetch(`${API}/api/cases/${id}`);assert.equal(response.status,200);return response.json();}
async function reset(){const response=await fetch(`${API}/__pc4/reset`,{method:'POST'});assert.equal(response.status,200);return response.json();}
let browser;
async function context(){
 const c=await browser.newContext({viewport:{width:1365,height:950}});
 await c.route('**/*',async route=>{
  const url=new URL(route.request().url());
  if(!['127.0.0.1','localhost'].includes(url.hostname) && ['http:','https:'].includes(url.protocol)){
   report.blockedExternal.push(route.request().url());await route.abort('blockedbyclient');return;
  }
  if(url.pathname.endsWith('/analyze') && route.request().method()==='POST' && route.request().postDataJSON()?.mode!=='replay'){
   report.blockedLive.push(url.pathname);await route.abort('blockedbyclient');return;
  }
  await route.continue();
 });
 const page=await c.newPage();page.setDefaultTimeout(15000);
 page.on('pageerror',e=>report.consoleErrors.push({kind:'pageerror',message:e.message}));
 page.on('console',m=>{if(m.type()==='error')report.consoleErrors.push({kind:'console',message:m.text()});});
 page.on('response',async r=>{if(r.url().startsWith(API+'/api/'))report.http.push({url:r.url(),method:r.request().method(),status:r.status(),sentRevision:r.request().postDataJSON()?.expectedRevision,mode:r.request().postDataJSON()?.mode});});
 return {context:c,page};
}
const nav=(page,label)=>page.getByRole('navigation',{name:'주 메뉴'}).getByRole('button',{name:label,exact:true}).click();
async function openCase(page,id){await page.goto(UI,{waitUntil:'domcontentloaded'});await page.getByRole('region',{name:'문의 선택'}).getByRole('button').filter({hasText:id}).click();await page.locator('audio').waitFor();}
async function action(page,locator,id,method='PATCH',suffix=''){
 const waiting=page.waitForResponse(r=>r.url()===`${API}/api/cases/${id}${suffix}` && r.request().method()===method);
 await locator.click();const response=await waiting;const data=await response.json();
 assert.equal(response.status(),200,JSON.stringify(data));return data;
}
async function screenshot(page,name){await page.screenshot({path:path.join(OUT,name+'.png'),fullPage:true});}
async function audioEnd(page,repeat){
 const audio=page.locator('audio');await page.waitForFunction(()=>document.querySelector('audio')?.readyState>=1);
 const before=await audio.evaluate(a=>({duration:a.duration,ended:a.ended,currentTime:a.currentTime,rate:a.playbackRate,currentSrc:a.currentSrc}));
 assert.ok(before.duration>40 && before.duration<60);assert.equal(before.rate,1);
 const started=Date.now();
 await audio.click({position:{x:24,y:27}});
 await page.waitForFunction(()=>{const a=document.querySelector('audio');return a && !a.paused && a.currentTime>0;},null,{timeout:15000});
 if(repeat>1)await audio.evaluate(a=>{a.currentTime=Math.max(0,a.duration-1.25);});
 await page.waitForFunction(()=>document.querySelector('audio')?.ended===true,null,{timeout:65000});
 const after=await audio.evaluate(a=>({ended:a.ended,currentTime:a.currentTime,duration:a.duration,rate:a.playbackRate}));
 assert.equal(after.ended,true);assert.equal(after.rate,1);
 return {method:repeat===1?'native controls, full duration, actual ended':'native controls, explicit near-end seek, actual ended',wallSeconds:(Date.now()-started)/1000,before,after,syntheticEventsDispatched:0};
}
async function flow(id,repeat){
 const row={id:`${id}-${repeat}`,caseId:id,repetition:repeat,status:'RUNNING',startedAt:new Date().toISOString(),steps:[],store:await reset()};report.flows.push(row);await persist();
 const {context:c,page}=await context();const startHttp=report.http.length;
 try{
  await openCase(page,id);const source=await readCase(id);
  row.audio=await audioEnd(page,repeat);row.steps.push('native-audio-ended');
  const analyzed=await action(page,page.getByRole('button',{name:'저장된 분석 결과 재생',exact:false}),id,'POST','/analyze');
  assert.equal(analyzed.mode,'replay');row.steps.push('replay-analysis-via-ui');
  for(const [kind,label] of [['WMS','WMS 작업 확인'],['TMS','TMS 배송 확인']]){
   await nav(page,label);const region=page.getByRole('region',{name:`${kind} 물류 확인`});await region.waitFor();
   assert.ok((await region.innerText()).includes(id));
   const raw=region.locator('summary').filter({hasText:'원본 행 보기'}).first();await raw.click();
   assert.ok((await region.locator('details[open] pre').first().innerText()).length>10);
   if(kind==='TMS'){
    const ownRow=region.getByRole('row').filter({hasText:'문의 점포'});const cells=await ownRow.getByRole('cell').allTextContents();
    row.tmsOwnRow=cells;assert.ok(cells.includes(id==='CASE-0001'?'미등록':'05:10'));
    assert.ok((await region.innerText()).includes('실제 미도착 확정을 뜻하지 않습니다'));
    assert.ok((await region.innerText()).includes('TMS 이벤트에 연결된 영상이 미등록'));
   }
   const link=region.getByRole('button',{name:'이 근거 연결',exact:true}).first();
   await action(page,link,id);row.steps.push(`${kind.toLowerCase()}-source-and-evidence-linked-via-ui`);
  }
  await nav(page,'상담 작업대');
  assert.ok((await page.getByRole('region',{name:'연결한 물류 근거'}).innerText()).includes('선택 2건'));
  await page.locator('.form-grid textarea').fill(`${source.intake?.request || source.sourceText}\nPC4 ${id}-${repeat}: 원문과 근거를 대조한 합성 시연 확인.`);
  await page.locator('.department-card select').selectOption(id==='CASE-0001'?'delivery':'warehouse');
  await page.getByRole('checkbox',{name:'점포·상품·전달 부서를 원문과 대조하고, 접수 정보를 편집·확인했습니다.'}).check();
  await action(page,page.getByRole('button',{name:'확인 후 센터 전달',exact:false}),id);
  await page.getByRole('heading',{name:'확인 결과 회신',exact:true}).waitFor();row.steps.push('edited-reviewed-and-handed-off-via-ui');
  const final=page.getByRole('button',{name:'최종 회신·처리 완료',exact:true});
  await page.getByLabel('경영주에게 등록할 회신',{exact:false}).fill(`PC4 ${row.id} 중간 회신: 원본 기록과 확인 사항을 검토 중입니다.`);
  await page.getByRole('textbox',{name:'남은 조치 내용',exact:true}).fill(`PC4 ${row.id} 합성 후속 확인`);
  await page.getByRole('button',{name:'조치 추가',exact:true}).click();assert.equal(await final.isEnabled(),false);
  await action(page,page.getByRole('button',{name:'중간 회신 등록',exact:true}),id);
  const interim=await readCase(id);assert.equal(interim.status,'in_progress');assert.ok(interim.pendingActions.length>0);assert.equal(await final.isEnabled(),false);
  row.steps.push('intermediate-reply-and-pending-close-disabled-via-ui');
  while(await page.getByRole('button',{name:/ 조치 완료$/}).count())await page.getByRole('button',{name:/ 조치 완료$/}).first().click();
  const finalText=`PC4 ${row.id} 최종 회신: 합성 확인 조치를 마쳤습니다. 실제 배송 변경이나 미도착 원인은 확정하지 않았습니다.`;
  await page.getByLabel('경영주에게 등록할 회신',{exact:false}).fill(finalText);
  await action(page,final,id);row.steps.push('final-reply-and-closed-via-ui');
  await page.getByRole('button',{name:'경영주 수신 화면 확인',exact:false}).click();
  await page.getByText(finalText,{exact:true}).waitFor();assert.ok((await page.locator('.receipt').innerText()).includes('처리 완료'));
  const saved=await readCase(id);assert.equal(saved.status,'closed');assert.equal(saved.reply,finalText);assert.deepEqual(saved.pendingActions,[]);assert.equal(saved.sourceText,source.sourceText);assert.equal(saved.replyRegisteredBy,'center');
  row.steps.push('owner-read-registered-reply-and-closed-state');row.final={status:saved.status,revision:saved.revision,selectedEvidence:saved.selectedEvidence,sourcePreserved:true};
  await screenshot(page,row.id+'-owner');row.status='PASS';
 }catch(error){row.status='FAIL';row.error={message:error.message,stack:error.stack};await screenshot(page,row.id+'-failure').catch(()=>{});}
 finally{row.finishedAt=new Date().toISOString();row.http=report.http.slice(startHttp);await c.close();await persist();console.log(JSON.stringify({flow:row.id,status:row.status,steps:row.steps,error:row.error?.message}));}
}
async function boundary(id,fn){const row={id,status:'RUNNING',store:await reset()};report.boundaries.push(row);const {context:c,page}=await context();try{row.result=await fn(page,c);row.status='PASS';}catch(error){row.status='FAIL';row.error=error.message;await screenshot(page,id+'-failure').catch(()=>{});}finally{await c.close();await persist();console.log(JSON.stringify({boundary:id,status:row.status,error:row.error}));}}
async function boundaries(){
 await boundary('new-text-different-day-no-implicit-evidence',async page=>{
  await openCase(page,'CASE-0001');await nav(page,'경영주 접수');
  const ref=fixtures[0];const text='PC4: 동일 점포의 다른 날 배송 문의입니다. 어제 배송과 오늘 배송은 별개이며 이번 문의의 실제 도착 여부를 확인해 주세요.';
  await page.getByLabel('점포코드',{exact:true}).fill(ref.intake.storeId);await page.getByLabel('문의 제목',{exact:true}).fill(ref.intake.subject);await page.getByLabel('상세 내용',{exact:true}).fill(text);
  assert.equal(await page.locator('.owner-form select').inputValue(),'');
  const wait=page.waitForResponse(r=>r.url()===API+'/api/intake' && r.request().method()==='POST');await page.getByRole('button',{name:'문의 접수하기',exact:false}).click();const response=await wait;assert.equal(response.status(),201);const created=await response.json();assert.ok(!created.linkedFixtureId);assert.deepEqual(created.evidence,[]);assert.equal(created.sourceText,text);
  await page.getByRole('button',{name:'시연: 상담 작업대로 이동',exact:false}).click();const analyzing=page.waitForResponse(r=>r.url().endsWith(`/api/cases/${created.id}/analyze`));await page.getByRole('button',{name:'저장된 분석 결과 재생',exact:false}).click();assert.equal((await analyzing).status(),409);await page.getByRole('alert').filter({hasText:'새 텍스트 문의에는 사전 리플레이가 없습니다'}).waitFor();
  await screenshot(page,'new-text-replay-unavailable');return {caseId:created.id,sourcePreserved:true,noImplicitEvidence:true,analysisStatus:409,analysis:'NOT_RUN: new text has no replay fixture; paid AI forbidden'};
 });
 await boundary('explicit-reference-text-media-missing',async page=>{
  await openCase(page,'CASE-0002');await nav(page,'경영주 접수');await page.locator('.owner-form select').selectOption('CASE-0002');await page.getByLabel('상세 내용',{exact:true}).fill('PC4: 같은 합성 배송건 확인을 요청합니다. 영상은 기록된 등록 여부로만 판단해 주세요.');
  const waiting=page.waitForResponse(r=>r.url()===API+'/api/intake'&&r.request().method()==='POST');await page.getByRole('button',{name:'문의 접수하기',exact:false}).click();const response=await waiting;assert.equal(response.status(),201);const created=await response.json();assert.equal(created.linkedFixtureId,'CASE-0002');assert.ok(!created.media?.length);
  await nav(page,'WMS 작업 확인');const region=page.getByRole('region',{name:'WMS 물류 확인'});assert.ok((await region.innerText()).includes('미등록'));assert.equal(await region.getByRole('button',{name:/연결 영상/}).count(),0);await screenshot(page,'reference-text-media-missing');return {caseId:created.id,reference:'CASE-0002',mediaCopied:false,missingShown:true};
 });
 await boundary('media-404-and-retry',async(page,c)=>{
  await openCase(page,'CASE-0002');await nav(page,'WMS 작업 확인');await c.route('**/demo/sorter-demo.mp4',route=>route.fulfill({status:404,body:'Test missing synthetic asset'}));
  const videoButton=page.getByRole('button',{name:/AI 합성 CCTV 구간 보기/}).first();await videoButton.click();await page.getByRole('alert').filter({hasText:'연결 영상 또는 등록 구간을 재생할 수 없습니다'}).waitFor();assert.ok((await page.getByRole('dialog').innerText()).includes('원본 스캔과 비교'));await screenshot(page,'media-404');
  await c.unroute('**/demo/sorter-demo.mp4');await page.getByRole('button',{name:'영상 다시 불러오기',exact:true}).click();await page.waitForFunction(()=>document.querySelector('dialog video')?.readyState>=1);await page.getByRole('dialog').locator('video').evaluate(v=>v.play());await page.waitForFunction(()=>{const v=document.querySelector('dialog video');return v && v.currentTime>1;});await page.keyboard.press('Escape');assert.equal(await page.getByRole('dialog').count(),0);return {injectedStatus:404,errorDisplayed:true,originalScanPreserved:true,retryMetadataLoaded:true,nativeVideoAdvanced:true,escapeClosed:true};
 });
 await boundary('api-error-and-recovery-no-false-save',async(page,c)=>{
  await openCase(page,'CASE-0001');const original=await readCase('CASE-0001');await page.locator('.form-grid textarea').fill('PC4 임시 장애에서 저장하면 안 되는 변경');
  const pattern=`${API}/api/cases/CASE-0001`;await c.route(pattern,async route=>{if(route.request().method()==='PATCH')await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:{message:'PC4 합성 일시 장애'}})});else await route.fallback();});
  await page.getByRole('button',{name:'접수 내용 저장',exact:true}).click();await page.getByRole('alert').filter({hasText:'PC4 합성 일시 장애'}).waitFor();assert.equal((await readCase('CASE-0001')).revision,original.revision);assert.equal(await page.getByRole('status').filter({hasText:'상담원이 편집한 접수 정보를 저장했습니다'}).count(),0);await screenshot(page,'api-error-no-false-save');
  await c.unroute(pattern);await action(page,page.getByRole('button',{name:'접수 내용 저장',exact:true}),'CASE-0001');return {injectedStatus:503,errorVisible:true,noFalseSuccess:true,storedRevisionUnchangedOnFailure:true,retrySaved:true};
 });
 await boundary('api-offline-example-and-reconnect',async(page,c)=>{
  const pattern=API+'/**';await c.route(pattern,route=>route.abort('connectionrefused'));await page.goto(UI,{waitUntil:'domcontentloaded'});await page.getByRole('button',{name:'합성 예시 열람',exact:true}).click();await page.getByRole('region',{name:'문의 선택'}).waitFor();await page.getByText('현재 예시 열람 중입니다. 변경 사항은 저장되지 않습니다.',{exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'접수 내용 저장',exact:true}).isEnabled(),false);await screenshot(page,'offline-readonly-example');
  await c.unroute(pattern);await page.getByRole('button',{name:'다시 연결',exact:true}).click();await page.waitForFunction(()=>!document.body.textContent.includes('현재 예시 열람 중입니다. 변경 사항은 저장되지 않습니다.'));await page.getByRole('button',{name:'접수 내용 저장',exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'접수 내용 저장',exact:true}).isEnabled(),true);return {scope:'API disconnected; static UI and fixture remain available (not complete device offline)',readonlyExample:true,modeDisplayed:true,reconnected:true};
 });
 await boundary('browser-offline-save-and-recovery',async(page,c)=>{
  await openCase(page,'CASE-0001');const before=await readCase('CASE-0001');await page.locator('.form-grid textarea').fill('PC4 브라우저 오프라인 복구 검사');await c.setOffline(true);
  await page.getByRole('button',{name:'접수 내용 저장',exact:true}).click();await page.getByRole('alert').filter({hasText:'해피콜 서버에 연결하지 못했습니다'}).waitFor();assert.equal((await readCase('CASE-0001')).revision,before.revision);await screenshot(page,'browser-offline-save');
  await c.setOffline(false);await action(page,page.getByRole('button',{name:'접수 내용 저장',exact:true}),'CASE-0001');const after=await readCase('CASE-0001');assert.equal(after.intake.request,'PC4 브라우저 오프라인 복구 검사');return {scope:'actual browser context offline/online',errorDisplayed:true,stateUnchangedOnFailure:true,retrySaved:true};
 });
}
try{
 const deadline=Date.now()+150000;let ready=false;
 while(Date.now()<deadline){try{const response=await fetch(UI);if(response.status===200){ready=true;break;}}catch{}await sleep(1000);}
 assert.ok(ready,'Own Next UI failed readiness');
 browser=await chromium.launch({headless:true,executablePath:process.env.E2E_CHROMIUM});
 if(process.env.PC4_UI_ONLY!=='boundaries')for(const id of ['CASE-0001','CASE-0002'])for(let repeat=1;repeat<=3;repeat++){await flow(id,repeat);if(process.env.PC4_UI_ONLY==='first')break;}
 if(process.env.PC4_UI_ONLY!=='first')await boundaries();
}catch(error){report.fatal={message:error.message,stack:error.stack};}
finally{
 if(browser)await browser.close();report.finishedAt=new Date().toISOString();report.guard=await fetch(API+'/__pc4/status').then(r=>r.json()).catch(()=>null);report.summary={planned:6,executed:report.flows.length,passed:report.flows.filter(x=>x.status==='PASS').length,failed:report.flows.filter(x=>x.status==='FAIL').length,notRun:6-report.flows.length,boundaryPassed:report.boundaries.filter(x=>x.status==='PASS').length,boundaryFailed:report.boundaries.filter(x=>x.status==='FAIL').length};await persist();console.log(JSON.stringify(report.summary));process.exitCode=report.fatal||report.summary.failed||report.summary.boundaryFailed||report.blockedLive.length||report.guard?.paidAnalyzerInvocations?1:0;
}
