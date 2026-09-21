import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { spawn, execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const port = Number(process.env.PROTOTYPE_PORT || 8911);
assert.ok(Number.isInteger(port) && port >= 1024 && port <= 65532, 'Base port must leave four valid ports');
const out = path.resolve(root, process.env.PROTOTYPE_OUTPUT || `reports/e2e/prototype-independent-${new Date().toISOString().replace(/[:.]/g, '-')}`);
await mkdir(out, { recursive: true });
const base = `http://127.0.0.1:${port}`;
const metadataPath = path.join(out, 'server.json');
const env = Object.fromEntries(['PATH','SystemRoot','WINDIR','TEMP','TMP','USERPROFILE'].filter(k=>process.env[k]).map(k=>[k,process.env[k]]));
const server = spawn(process.env.REHEARSAL_PYTHON || path.join(root,'.venv/Scripts/python.exe'), ['tests/helpers/rehearsal_server.py','--port',String(port),'--metadata',metadataPath,'--preserve-state'], {cwd:root,env:{...env,PYTHONUTF8:'1',PYTHONDONTWRITEBYTECODE:'1'},windowsHide:true,stdio:['ignore','pipe','pipe']});
let log=''; server.stdout.on('data',d=>log+=d);server.stderr.on('data',d=>log+=d);
const result={startedAt:new Date().toISOString(),executor:'Independent AI browser reviewer; not human observation',base,checks:[],responses:[],pageErrors:[],external:[]};
const check=(name,actual,expected)=>{assert.deepEqual(actual,expected,name);result.checks.push({name,actual,expected});};
let browser;
try {
  for(let i=0;i<60;i++){if(server.exitCode!==null)throw Error(`Server exited ${server.exitCode}: ${log}`);try{if((await fetch(base+'/api/cases')).ok)break;}catch{}await new Promise(r=>setTimeout(r,250));}
  result.server=JSON.parse(await readFile(metadataPath,'utf8'));
  result.serverProcess=JSON.parse(execFileSync('powershell.exe',['-NoProfile','-Command',`[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-CimInstance Win32_Process -Filter 'ProcessId = ${result.server.pid}' | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress`],{encoding:'utf8',windowsHide:true}));
  check('owned runtime launched by own Python process',result.serverProcess.ProcessId===server.pid||result.serverProcess.ParentProcessId===server.pid,true);
  check('runtime command matches isolated test metadata',result.serverProcess.CommandLine.includes(metadataPath),true);
  browser=await chromium.launch({...(process.env.E2E_CHROMIUM ? {executablePath:process.env.E2E_CHROMIUM} : {}),headless:true});
  const context=await browser.newContext({viewport:{width:1440,height:1000}});
  await context.route('**/*',async route=>{const u=new URL(route.request().url());if(u.hostname!=='127.0.0.1'||u.port!==String(port)){result.external.push(u.origin+u.pathname);return route.abort();}if(u.pathname.endsWith('/analyze'))throw Error('No analysis calls in independent recovery probes');await route.continue();});
  const page=await context.newPage();page.setDefaultTimeout(10000);page.on('pageerror',e=>result.pageErrors.push(e.message));page.on('response',r=>{if(r.url().includes('/api/'))result.responses.push({method:r.request().method(),path:new URL(r.url()).pathname,status:r.status()});});
  const nav=name=>page.getByRole('navigation').getByRole('button',{name,exact:true}).click();
  const req=page.getByPlaceholder('경영주가 요청한 내용을 확인해 주세요.',{exact:true});
  const save=page.getByRole('button',{name:'접수 내용 저장',exact:true});
  const api=async(method='GET',body)=>{const r=await context.request.fetch(base+'/api/cases/CASE-0001',{method,headers:{'X-Demo-Role':'counselor'},data:body});assert.equal(r.status(),200,await r.text());return r.json();};
  const refresh=async()=>{await page.getByRole('button',{name:'목록 새로고침',exact:true}).click();await page.getByRole('button',{name:'목록 새로고침',exact:true}).waitFor();};
  await page.goto(base,{waitUntil:'networkidle'});await req.waitFor();
  result.computedTypography=await page.evaluate(()=>{const s=getComputedStyle(document.body);return {fontFamily:s.fontFamily,fontSize:s.fontSize,lineHeight:s.lineHeight,color:s.color,background:s.backgroundColor};});
  const storageBefore=await page.evaluate(()=>({local:{...localStorage},session:{...sessionStorage}}));
  // A late third-party save must prevent a lost-response recovery from claiming
  // that the current server still contains our submitted content.
  await req.fill('독립검수: 응답 유실 원래 요청');
  await page.route('**/api/cases/CASE-0001',async route=>{if(route.request().method()!=='PATCH')return route.continue();const r=await route.fetch();check('uncertain probe really committed first PATCH',r.status(),200);await route.abort('failed');},{times:1});
  await save.click();await page.getByRole('button',{name:'저장 여부 확인',exact:true}).waitFor();
  const first=await api();const external=await api('PATCH',{expectedRevision:first.revision,status:'review',intake:{...first.intake,request:'독립검수: 다른 담당자의 후속 저장'}});
  await page.getByRole('button',{name:'저장 여부 확인',exact:true}).click();
  const recovery=page.getByRole('region',{name:'최신 서버 내용과 초안 대조',exact:true});await recovery.waitFor();
  check('later remote change is shown, not acknowledged as original save',(await recovery.innerText()).includes(external.intake.request),true);
  check('uncertain local draft retained',await req.inputValue(),'독립검수: 응답 유실 원래 요청');
  check('recovery blocks edits before choice',await req.isDisabled(),true);
  check('recovery blocks resave before choice',await save.isDisabled(),true);
  check('inspection performs no server write',(await api()).revision,external.revision);
  await page.getByRole('button',{name:'내 초안 유지 · 다시 확인',exact:true}).click();
  check('explicit keep clears confirmation',await page.locator('.review-check input').isChecked(),false);
  check('explicit keep preserves local draft',await req.inputValue(),'독립검수: 응답 유실 원래 요청');
  check('explicit keep alone performs no server write',(await api()).revision,external.revision);
  // A second writer races after inspection but before our save. The stale
  // revision must fail again instead of silently adopting the newer revision.
  const race=await api('PATCH',{expectedRevision:external.revision,status:'review',intake:{...external.intake,request:'독립검수: 대조 직후 재충돌'}});
  const conflict=page.waitForResponse(r=>r.url().endsWith('/api/cases/CASE-0001')&&r.request().method()==='PATCH');await save.click();check('second writer after inspection still returns 409',(await conflict).status(),409);await recovery.waitFor();
  check('second writer request survives 409',(await api()).intake.request,race.intake.request);
  check('local request survives second conflict',await req.inputValue(),'독립검수: 응답 유실 원래 요청');
  await page.getByRole('button',{name:'서버 내용 사용',exact:true}).click();check('explicit use-server loads raced content',await req.inputValue(),race.intake.request);
  // Negative control: 503 without a commit. Recovery must expose both versions
  // instead of interpreting any successful GET as a successful PATCH.
  await req.fill('독립검수: 저장되지 않은 503 요청');
  await page.route('**/api/cases/CASE-0001',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:{code:'CONTROL_UNAVAILABLE',message:'독립검수 의도적 서비스 불가'}})}),{times:1});
  await save.click();await page.getByRole('button',{name:'저장 여부 확인',exact:true}).click();await recovery.waitFor();check('503 without commit retains revision',(await api()).revision,race.revision);check('503 keeps submitted draft for comparison',await req.inputValue(),'독립검수: 저장되지 않은 503 요청');
  check('503 comparison presents previous server request',(await recovery.innerText()).includes(race.intake.request),true);
  for(const width of [1440,1024,390]){await page.setViewportSize({width,height:1000});await recovery.scrollIntoViewIfNeeded();check(`recovery horizontal overflow ${width}`,await page.evaluate(()=>Math.max(0,document.documentElement.scrollWidth-innerWidth)),0);await recovery.screenshot({path:path.join(out,`recovery-${width}.png`)});await page.screenshot({path:path.join(out,`desk-${width}.png`),fullPage:true});}
  await page.getByRole('button',{name:'서버 내용 사용',exact:true}).focus();await page.keyboard.press('Enter');check('keyboard use-server after uncommitted failure restores original',await req.inputValue(),race.intake.request);
  // Independent role drafts never leak into persistent browser storage.
  await req.fill('독립검수: 메모리 초안만');await nav('센터 회신');await page.getByLabel('경영주에게 등록할 회신').fill('독립검수: 센터 별도 초안');await nav('상담 작업대');check('role navigation retains only own desk draft',await req.inputValue(),'독립검수: 메모리 초안만');
  check('customer drafts not persisted to local or session storage',await page.evaluate(()=>({local:{...localStorage},session:{...sessionStorage}})),storageBefore);
  // Current screen coverage: all five workspaces at three real viewport widths.
  for(const width of [1440,1024,390]){await page.setViewportSize({width,height:1000});for(const [view,label] of [['desk','상담 작업대'],['wms','WMS 작업 확인'],['tms','TMS 배송 확인'],['center','센터 회신'],['owner','경영주 접수']]){await nav(label);check(`${view} document overflow ${width}`,await page.evaluate(()=>Math.max(0,document.documentElement.scrollWidth-innerWidth)),0);await page.screenshot({path:path.join(out,`${view}-full-${width}.png`),fullPage:true});}}
  check('unexpected page errors',result.pageErrors,[]);check('external requests',result.external,[]);result.status='PASS';
}catch(e){result.status='FAIL';result.failure=e.stack;process.exitCode=1;}
finally{if(browser)await browser.close();server.kill();await writeFile(path.join(out,'server.log'),log);result.finishedAt=new Date().toISOString();result.runnerSha256=createHash('sha256').update(await readFile(new URL(import.meta.url))).digest('hex');await writeFile(path.join(out,'results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify({out,status:result.status,checks:result.checks.length,failure:result.failure}));}
