import { chromium } from '../../tests/e2e/node_modules/playwright/index.mjs';
import { spawn, execFileSync } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
const root=process.cwd(),out=path.join(root,'reports/e2e/prototype-independent-fonts-20260921-2105'),base='http://127.0.0.1:8921';
await mkdir(out,{recursive:true});
const meta=path.join(out,'server.json');
const env=Object.fromEntries(['PATH','SystemRoot','WINDIR','TEMP','TMP','USERPROFILE'].filter(k=>process.env[k]).map(k=>[k,process.env[k]]));
const server=spawn(path.join(root,'.venv/Scripts/python.exe'),['tests/helpers/rehearsal_server.py','--port','8921','--metadata',meta,'--preserve-state'],{cwd:root,env:{...env,PYTHONUTF8:'1'},windowsHide:true,stdio:['ignore','pipe','pipe']});
let log='',browser;server.stdout.on('data',d=>log+=d);server.stderr.on('data',d=>log+=d);const result={startedAt:new Date().toISOString(),status:'NOT_RUN',fonts:[]};
try{
 for(let i=0;i<60;i++){if(server.exitCode!==null)throw Error(log);try{if((await fetch(base+'/api/cases')).ok)break;}catch{}await new Promise(r=>setTimeout(r,250));}
 result.server=JSON.parse(await readFile(meta,'utf8'));
 result.serverProcess=JSON.parse(execFileSync('powershell.exe',['-NoProfile','-Command',`[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-CimInstance Win32_Process -Filter 'ProcessId = ${result.server.pid}' | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress`],{encoding:'utf8',windowsHide:true}));
 assert.ok(result.serverProcess.ProcessId===server.pid||result.serverProcess.ParentProcessId===server.pid);assert.ok(result.serverProcess.CommandLine.includes(meta));
 browser=await chromium.launch({executablePath:'C:/Users/choi8/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe',headless:true});const page=await browser.newPage({viewport:{width:1440,height:1000}});
 await page.route('**/*',route=>{const u=new URL(route.request().url());return u.hostname==='127.0.0.1'&&u.port==='8921'?route.continue():route.abort();});
 await page.goto(base,{waitUntil:'networkidle'});await page.getByRole('heading',{name:'상담 작업대',exact:true}).waitFor();
 const cdp=await page.context().newCDPSession(page);await cdp.send('DOM.enable');await cdp.send('CSS.enable');const {root:doc}=await cdp.send('DOM.getDocument');
 for(const selector of ['body','h1','.workspace-sync strong','.workspace-sync button','textarea','.department-card select','.review-check span']){
   const {nodeId}=await cdp.send('DOM.querySelector',{nodeId:doc.nodeId,selector});if(!nodeId){result.fonts.push({selector,status:'NO_NODE'});continue;}
   const computed=await page.locator(selector).first().evaluate(el=>{const s=getComputedStyle(el);return {text:el.textContent?.slice(0,80),fontFamily:s.fontFamily,fontSize:s.fontSize,fontWeight:s.fontWeight,lineHeight:s.lineHeight};});
   const platform=await cdp.send('CSS.getPlatformFontsForNode',{nodeId});result.fonts.push({selector,computed,platformFonts:platform.fonts});
 }
 result.fontAvailability=await page.evaluate(()=>Object.fromEntries(['Pretendard Variable','Pretendard','Segoe UI','Malgun Gothic','Batang','Gulim'].map(name=>[name,document.fonts.check(`13px "${name}"`,'한글 가나다')] )));
 await page.screenshot({path:path.join(out,'viewport-1440.png')});result.status='PASS';
}catch(e){result.status='FAIL';result.failure=e.stack;process.exitCode=1;}finally{if(browser)await browser.close();server.kill();result.finishedAt=new Date().toISOString();await writeFile(path.join(out,'server.log'),log);await writeFile(path.join(out,'results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result.fonts));console.log(JSON.stringify({out,status:result.status,failure:result.failure}));}
