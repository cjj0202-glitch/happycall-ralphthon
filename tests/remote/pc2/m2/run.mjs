import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {build,ROOT,OUT} from './build.mjs';
import {serve} from './server.mjs';

const require=createRequire(path.join(ROOT,'tests/e2e/package.json'));
const {chromium}=require('playwright');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const RUN=new Date().toISOString().replace(/[:.]/g,'-');
const DIR=path.join(ROOT,'reports/pc2/audio-m2',`playback-${RUN}`);
await mkdir(DIR,{recursive:true});
const report={started:new Date().toISOString(),node:process.version,playwright:require('playwright/package.json').version,
  method:'Actual bfc8543 CallReview snapshot rendered in one Edge browser/context/page with local A/B PCM WAVs.',
  limits:['AI technical inspection; human listening0','No real parent page/API persistence or paid requests','Headless native playback is not OS speaker or understanding evidence'],
  checks:[],pageErrors:[],consoleErrors:[],blockedRequests:[],media:[],screenshots:[],cleanup:[],
  priorSetupFailures:[{at:'2026-09-21T21:07:20+09:00',phase:'node --check build.mjs',error:'SyntaxError Unexpected token :; missing module.rules closing bracket. Fixed before any browser launch.'}]};
const resultPath=path.join(DIR,'results.json');
const save=async()=>{report.passed=report.checks.filter(c=>c.status==='PASS').length;report.failed=report.checks.filter(c=>c.status==='FAIL').length;await writeFile(resultPath,JSON.stringify(report,null,2)+'\n');};
const check=async(id,expected,fn)=>{const started=Date.now();try{report.checks.push({id,expected,status:'PASS',actual:await fn(),ms:Date.now()-started});console.log(`PASS ${id}`);}catch(e){report.checks.push({id,expected,status:'FAIL',error:e.stack||String(e),ms:Date.now()-started});console.log(`FAIL ${id}: ${e.message}`);}await save();};
const protectedNames=['apps/web/components/CallReview.tsx','apps/web/components/CallReview.module.css','apps/web/app/page.tsx','data/fixtures/cases.json','data/demo-media-manifest.json'];
const hashes=async()=>Object.fromEntries(await Promise.all(protectedNames.map(async n=>[n,sha(await readFile(path.join(ROOT,n)))])));
report.protectedBefore=await hashes();
let browser,context,service,page,manifest;
try {
  manifest=await build();
  report.productCommit=manifest.productCommit;report.productSources=manifest.productSources;
  report.manifestSha256=sha(await readFile(path.join(ROOT,'reports/pc2/audio-m2/playback-manifest.json')));
  report.assets=manifest.assets;
  service=await serve(manifest);report.serverAddress=service.address;
  // Pipe control: no BrowserServer WebSocket listener is started.
  browser=await chromium.launch({headless:true,channel:process.env.N02_BROWSER_CHANNEL||'msedge'});
  report.browser=browser.version();report.browserControl='Playwright pipe; no BrowserServer';
  context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  await context.route('**/*',async route=>{
    if(new URL(route.request().url()).origin!==service.origin||!['GET','HEAD'].includes(route.request().method())){
      report.blockedRequests.push({url:route.request().url(),method:route.request().method()});await route.abort();
    }else await route.continue();
  });
  await context.addInitScript(()=>{
    window.__mediaLog=[];let sequence=0;const observed=new WeakSet();
    const attach=()=>document.querySelectorAll('audio').forEach(a=>{
      if(observed.has(a))return;observed.add(a);const id=++sequence;
      for(const type of ['loadedmetadata','play','playing','pause','ended','seeking','seeked','error','ratechange'])a.addEventListener(type,e=>window.__mediaLog.push({type,id,src:a.currentSrc,time:a.currentTime,duration:a.duration,rate:a.playbackRate,ready:a.readyState,error:a.error?.code||null,trusted:e.isTrusted,at:performance.now(),played:Array.from({length:a.played.length},(_,i)=>[a.played.start(i),a.played.end(i)])}));
    });
    new MutationObserver(attach).observe(document,{subtree:true,childList:true});
  });
  page=await context.newPage();page.setDefaultTimeout(6000);
  page.on('pageerror',e=>report.pageErrors.push(e.stack||e.message));
  page.on('console',msg=>{if(msg.type()==='error')report.consoleErrors.push(msg.text());});
  await page.goto(service.origin);await page.waitForFunction(()=>window.__m2?.ready);
  const state=()=>page.evaluate(()=>{
    const a=document.querySelector('audio');return{...Object.fromEntries(['variant','complete','disabled','callbacks'].map(k=>[k,window.__m2[k]])),audio:a?{src:a.currentSrc,time:a.currentTime,duration:a.duration,paused:a.paused,ended:a.ended,rate:a.playbackRate,volume:a.volume,muted:a.muted,ready:a.readyState,error:a.error?.code||null,played:Array.from({length:a.played.length},(_,i)=>[a.played.start(i),a.played.end(i)])}:null};
  });
  const metadata=()=>page.waitForFunction(()=>{const a=document.querySelector('audio');return a&&Number.isFinite(a.duration)&&a.readyState>=1;});
  const reset=async v=>{const g=await page.evaluate(()=>window.__m2.generation);await page.evaluate(v=>window.__m2.reset(v),v);await page.waitForFunction(g=>window.__m2.generation>g,g);await metadata();await page.evaluate(()=>{window.__mediaLog=[];});};
  const switchTo=async v=>{await page.getByRole('button',{name:v==='A'?'A 정본 v2':'B 쉼 후보',exact:true}).click();await page.waitForFunction(v=>window.__m2.variant===v,v);await metadata();};
  const start=()=>page.getByRole('button',{name:'처음부터 전체 통화 재생',exact:true});
  const sourceSummary=()=>page.getByText('원문과 화자별 대화록 확인',{exact:true});
  const openTranscript=async()=>{const summary=sourceSummary();if(!(await summary.locator('..').getAttribute('open')))await summary.click();};
  const full=async v=>{
    await reset(v);await metadata();const expected=manifest.assets[v].duration;
    const before=await state();assert.ok(Math.abs(before.audio.duration-expected)<=1/24000);assert.equal(before.audio.rate,1);assert.equal(before.audio.muted,false);assert.equal(before.audio.volume,1);
    const started=Date.now();await start().click();
    await page.waitForFunction(()=>window.__m2.callbacks.length===1,undefined,{timeout:(expected+8)*1000});
    const elapsed=(Date.now()-started)/1000;const actual=await state();
    const events=await page.evaluate(()=>window.__mediaLog);
    const ended=events.filter(e=>e.type==='ended');
    assert.equal(ended.length,1);assert.equal(ended[0].trusted,true);assert.equal(actual.audio.ended,true);assert.equal(actual.audio.rate,1);assert.equal(actual.callbacks.length,1);
    assert.ok(elapsed>=expected-.3&&elapsed<=expected+8);assert.ok(Math.abs(actual.audio.time-expected)<=.02);
    assert.ok(actual.audio.played[0][0]<=.05&&actual.audio.played.at(-1)[1]>=expected-.10);assert.equal(actual.audio.error,null);
    assert.ok(await page.locator('#analysis-gate').isEnabled());
    report.media.push({kind:'full',variant:v,elapsed,state:actual,events});
    return{variant:v,elapsed,expectedSeconds:expected,nativeEnded:ended.length,actual};
  };
  await check('A-full-natural-1x','49.55s decoded/natural ended1/callback1/played0-end',()=>full('A'));
  await check('A-to-B-completion-reset','A complete must not carry into B',async()=>{
    await page.evaluate(()=>{window.__oldAudio=document.querySelector('audio');});await switchTo('B');
    const actual=await state();assert.equal(actual.complete,false);assert.equal(actual.audio.time,0);assert.ok(await page.locator('#analysis-gate').isDisabled());
    const old=await page.evaluate(()=>({paused:window.__oldAudio.paused,connected:window.__oldAudio.isConnected}));assert.equal(old.paused,true);assert.equal(old.connected,false);return{actual,old};
  });
  await check('B-full-natural-1x','49.75s decoded/natural ended1/callback1/played0-end',()=>full('B'));
  await check('B-to-A-completion-reset','B complete must not carry into A',async()=>{await switchTo('A');const actual=await state();assert.equal(actual.complete,false);assert.equal(actual.audio.time,0);assert.ok(await page.locator('#analysis-gate').isDisabled());return actual;});
  for(let i=0;i<8;i++)await check(`B-clip-${i+1}`,'Correct source speaker/text/start/end; no next-turn intrusion or whole completion',async()=>{
    await reset('B');await openTranscript();const t=manifest.turns[i];
    const button=page.getByRole('button',{name:new RegExp(`발화 ${i+1} 구간 재생 `)});
    const row=button.locator('..');assert.ok((await row.innerText()).includes(t.text));assert.ok((await row.innerText()).includes(t.speaker));
    await button.click();await page.waitForFunction(()=>{const a=document.querySelector('audio');return a&&!a.paused;});
    await page.waitForFunction(i=>document.querySelectorAll('li[aria-current="true"]').length===1&&document.querySelector('li[aria-current="true"]').textContent.includes(`발화 ${i+1}`),i);
    await page.waitForFunction(end=>{const a=document.querySelector('audio');return a.paused&&Math.abs(a.currentTime-end)<=.002;},t.B.end,{timeout:(t.B.end-t.B.start+5)*1000});
    await page.waitForTimeout(180);const actual=await state();const events=await page.evaluate(()=>window.__mediaLog);
    const playing=events.filter(e=>e.type==='play'||e.type==='playing');assert.ok(playing.length>0);
    const observedStart=playing[0].time;assert.ok(Math.abs(observedStart-t.B.start)<=.08,`start ${observedStart}`);
    const playedEnd=Math.max(...actual.audio.played.map(r=>r[1]));
    assert.ok(playedEnd<=t.B.end+.12,`overshoot ${playedEnd-t.B.end}`);
    if(i<7)assert.ok(playedEnd<manifest.turns[i+1].B.start);
    assert.equal(actual.audio.paused,true);assert.equal(actual.callbacks.length,0);assert.equal(actual.complete,false);assert.ok(await page.locator('#analysis-gate').isDisabled());
    report.media.push({kind:'clip',index:i,expected:t.B,observedStart,playedEnd,state:actual,events});
    return{speaker:t.speaker,text:t.text,expected:t.B,observedStart,playedEnd,overshoot:playedEnd-t.B.end,finalCursor:actual.audio.time,callbacks:actual.callbacks.length};
  });
  await check('duplicate-start-pause-seek','No completion from repeated start/stop or end seek',async()=>{
    await reset('B');await start().dblclick();await page.waitForTimeout(250);
    await page.evaluate(()=>document.querySelector('audio').pause());const paused=await state();assert.equal(paused.audio.paused,true);assert.equal(paused.callbacks.length,0);
    await page.evaluate(()=>{const a=document.querySelector('audio');a.currentTime=a.duration-.08;});
    await page.waitForFunction(()=>!document.querySelector('audio').seeking);await page.evaluate(()=>document.querySelector('audio').play());
    await page.waitForFunction(()=>document.querySelector('audio').ended);
    const actual=await state();assert.equal(actual.callbacks.length,0);assert.equal(actual.complete,false);assert.ok(await page.locator('#analysis-gate').isDisabled());return{paused,afterSeek:actual};
  });
  await check('switch-playing-old-events-and-disabled','Active A pauses on B switch; old events/disabled cannot complete',async()=>{
    await reset('A');await start().click();await page.waitForTimeout(200);await page.evaluate(()=>{window.__oldAudio=document.querySelector('audio');});
    await switchTo('B');await page.evaluate(()=>{window.__oldAudio.dispatchEvent(new Event('ended'));window.__oldAudio.dispatchEvent(new Event('error'));});
    const switched=await state();assert.equal(switched.callbacks.length,0);assert.equal(switched.complete,false);assert.equal(switched.audio.error,null);
    assert.equal(await page.evaluate(()=>window.__oldAudio.paused),true);
    await start().click();await page.getByLabel('검증용 잠금',{exact:true}).check();
    await page.waitForFunction(()=>document.querySelector('audio').paused);assert.ok(await start().isDisabled());const actual=await state();assert.equal(actual.callbacks.length,0);return{switched,disabled:actual};
  });
  for(const width of [1440,1024,390])await check(`layout-keyboard-${width}`,'Actual component, 0 horizontal overflow, keyboard source disclosure/controls',async()=>{
    await reset('B');await page.setViewportSize({width,height:1000});
    await sourceSummary().focus();await page.keyboard.press('Enter');assert.ok(await sourceSummary().locator('..').getAttribute('open')!==null);
    const texts=await page.getByRole('button',{name:/발화 \d+ 구간 재생 /}).count();assert.equal(texts,8);
    const rate=page.getByLabel('통화 재생 속도',{exact:true});await rate.focus();await page.keyboard.press('ArrowDown');assert.equal(await page.evaluate(()=>document.querySelector('audio').playbackRate),1.25);
    await rate.selectOption('1');const mute=page.getByRole('button',{name:'통화 음소거',exact:true});await mute.focus();await page.keyboard.press('Space');assert.equal(await page.evaluate(()=>document.querySelector('audio').muted),true);await page.keyboard.press('Space');
    const overflow=await page.evaluate(()=>Math.max(document.documentElement.scrollWidth,document.body.scrollWidth)-innerWidth);assert.equal(overflow,0);
    const screenshot=`layout-${width}.png`;await page.screenshot({path:path.join(DIR,screenshot),fullPage:true});report.screenshots.push({file:screenshot,width,sha256:sha(await readFile(path.join(DIR,screenshot)))});
    await sourceSummary().focus();await page.keyboard.press('Space');assert.equal(await sourceSummary().locator('..').getAttribute('open'),null);return{width,overflow,turnButtons:texts,keyboard:'Enter/Space disclosure, rate arrows, mute Space',screenshot};
  });
  await check('request-and-source-integrity','pageerror0/API0/all source hashes unchanged',async()=>{
    report.protectedAfter=await hashes();assert.deepEqual(report.protectedAfter,report.protectedBefore);
    assert.equal(report.pageErrors.length,0);assert.equal(report.blockedRequests.length,0);assert.equal(report.consoleErrors.length,0);
    return{pageErrors:0,blockedRequests:0,consoleErrors:0,sourceFilesUnchanged:protectedNames.length,requests:service.requests.length};
  });
}catch(e){report.fatal=e.stack||String(e);console.log(`FATAL ${e.message}`);}
finally{
  for(const[name,fn]of [['context',()=>context?.close()],['browser',()=>browser?.close()],['server',()=>service?.close()]]){
    const started=Date.now();try{await fn();report.cleanup.push({name,status:'complete',ms:Date.now()-started});}catch(e){report.cleanup.push({name,status:'error',error:String(e)});}
  }
  report.browserDisconnected=browser?!browser.isConnected():true;report.requests=service?.requests||[];
  report.finished=new Date().toISOString();await save();console.log(JSON.stringify({dir:DIR,passed:report.passed,failed:report.failed,fatal:report.fatal||null,cleanup:report.cleanup}));
}
if(report.fatal||report.failed||report.cleanup.some(c=>c.status!=='complete'))process.exitCode=1;
