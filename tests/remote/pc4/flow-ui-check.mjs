// Existing product page + real isolated HTTP API. No direct product-state writes.
import { chromium } from '../../e2e/node_modules/playwright/index.mjs';
import assert from 'node:assert/strict';
import { writeFile, readFile } from 'node:fs/promises';
import path from 'node:path';

// This judges browser observations, not the application's completion algorithm.
// Native HTMLMediaElement.played ranges are independent evidence of time coverage.
function judgePlayback(trace) {
 const reasons=[];const d=trace.duration;const events=trace.events||[];const samples=trace.samples||[];
 if(!Number.isFinite(d)||d<=0)reasons.push('invalid-duration');
 if((trace.initialTime??Infinity)>.1)reasons.push('not-started-at-zero');
 if(events.some(e=>e.type==='seeking'||e.type==='seeked'))reasons.push('seek-observed');
 if(samples.length<2||[...events,...samples].some(e=>!Number.isFinite(e.rate)||Math.abs(e.rate-1)>.001))reasons.push('not-continuous-rate-one');
 if([...events,...samples].some(e=>e.caseId!==trace.caseId||e.source!==trace.source||e.session!==trace.session||e.connected===false))reasons.push('stale-case-source-or-session');
 for(const type of ['play','playing','ended'])if(!events.some(e=>e.type===type&&e.trusted===true))reasons.push(`missing-trusted-${type}`);
 if(!trace.ended||Math.abs((trace.finalTime??0)-d)>.15)reasons.push('not-natural-end');
 if((trace.wallSeconds??0)<d-.75)reasons.push('insufficient-wall-time');
 const ranges=(trace.played||[]).filter(r=>Array.isArray(r)&&r.length===2&&r.every(Number.isFinite)).sort((a,b)=>a[0]-b[0]);
 let end=0;for(const [start,stop] of ranges){if(start>end+.1)break;end=Math.max(end,stop);}
 const coverage=Number.isFinite(d)&&d>0?Math.min(end/d,1):0;
 if(coverage<.995)reasons.push('incomplete-native-played-coverage');
 return {accepted:reasons.length===0,reasons,coverage};
}
class CapabilityBlocker extends Error {}
const PLANNED_BOUNDARIES=['audio-end-seek-must-not-complete','audio-segment-must-not-complete','previous-case-native-ended-must-not-complete-current','new-text-different-day-no-implicit-evidence','explicit-reference-text-media-missing','media-404-and-retry','api-error-and-recovery-no-false-save','api-offline-example-and-reconnect','browser-offline-save-and-recovery','two-ui-editors-real-409-no-overwrite','future-evidence-hidden-in-investigation-ui','different-business-totes-not-continuous-tracking',...[1365,921,390].map(width=>`responsive-keyboard-reduced-motion-${width}`)];
function allowedHttpUrl(value,origin){try{const url=new URL(value);return ['http:','https:'].includes(url.protocol)&&url.origin===origin&&!url.username&&!url.password;}catch{return false;}}
function matchesIdentity(expected,observed){return observed?.ready===true&&['runNonce','finalSha','buildFingerprint'].every(key=>typeof expected[key]==='string'&&expected[key].length>0&&observed[key]===expected[key]);}
function checkerSelfTest(){
 const common={caseId:'CASE-0001',source:'/one.wav',session:'session-A',rate:1,connected:true};
 const base={...common,duration:10,initialTime:0,finalTime:10,ended:true,wallSeconds:10.2,played:[[0,10]],samples:[{...common,time:0},{...common,time:5},{...common,time:10}],events:['play','playing','ended'].map(type=>({...common,type,trusted:true}))};
 const tests=[['natural-full-rate-one',true,x=>x],['end-seek',false,x=>({...x,events:[...x.events,{...common,type:'seeking',trusted:true}],played:[[9,10]],wallSeconds:1})],['segment-only',false,x=>({...x,initialTime:3,played:[[3,8]],finalTime:8,ended:false,wallSeconds:5})],['previous-case-callback',false,x=>({...x,events:x.events.map(e=>e.type==='ended'?{...e,caseId:'CASE-0002'}:e)})],['previous-session-callback',false,x=>({...x,events:x.events.map(e=>e.type==='ended'?{...e,session:'old-session'}:e)})],['detached-old-player',false,x=>({...x,events:x.events.map(e=>e.type==='ended'?{...e,connected:false}:e)})],['synthetic-ended',false,x=>({...x,events:x.events.map(e=>e.type==='ended'?{...e,trusted:false}:e)})],['fast-rate',false,x=>({...x,samples:[...x.samples,{...common,rate:2}]})],['missing-middle-coverage',false,x=>({...x,played:[[0,2],[8,10]]})],['wrong-source',false,x=>({...x,events:x.events.map(e=>e.type==='ended'?{...e,source:'/two.wav'}:e)})]];
 const results=tests.map(([id,expected,change])=>{const actual=judgePlayback(change(structuredClone(base)));assert.equal(actual.accepted,expected,id);return{id,status:'PASS',expectedAccepted:expected,...actual};});
 const identity={runNonce:'nonce',finalSha:'sha',buildFingerprint:'build'};
 for(const[id,actual,expected]of [['exact-origin',allowedHttpUrl('http://127.0.0.1:18105/api/cases','http://127.0.0.1:18105'),true],['other-loopback-port',allowedHttpUrl('http://127.0.0.1:8100/api/cases','http://127.0.0.1:18105'),false],['credential-bearing-url',allowedHttpUrl('http://x@127.0.0.1:18105/','http://127.0.0.1:18105'),false],['matching-run-identity',matchesIdentity(identity,{...identity,ready:true}),true],['wrong-run-nonce',matchesIdentity(identity,{...identity,ready:true,runNonce:'other'}),false],['wrong-build-fingerprint',matchesIdentity(identity,{...identity,ready:true,buildFingerprint:'other'}),false]]){assert.equal(actual,expected,id);results.push({id,status:'PASS',actual,expected});}
 assert.equal(new Set(PLANNED_BOUNDARIES).size,PLANNED_BOUNDARIES.length);
 return {kind:'checker-only synthetic observation tests; no browser, app, API or media execution',status:'PASS',checks:results.length,plannedBoundaryIds:PLANNED_BOUNDARIES,results};
}
if(process.argv.includes('--self-test')){console.log(JSON.stringify(checkerSelfTest(),null,2));process.exit(0);}

const UI=process.env.PC4_UI_BASE, API=process.env.PC4_API_BASE, OUT=process.env.PC4_UI_OUT;
let capability,expectedIdentity,origin;const finalSha=process.env.PC4_Q2_FINAL_SHA;
try{
 const parsed=new URL(UI);origin=parsed.origin;
 assert.ok(parsed.protocol==='http:'&&parsed.hostname==='127.0.0.1'&&parsed.port&&UI===origin&&API===origin&&OUT&&allowedHttpUrl(UI,origin),'Exact same isolated runner origin/output required');
 assert.match(finalSha||'',/^[0-9a-f]{40}$/,'Final source SHA is required');
 expectedIdentity=JSON.parse(process.env.PC4_Q2_RUN_IDENTITY||'null');
 assert.equal(expectedIdentity?.finalSha,finalSha);assert.match(expectedIdentity?.runNonce||'',/^[0-9a-f]{32}$/);assert.match(expectedIdentity?.buildFingerprint||'',/^[0-9a-f]{64}$/);
 capability=JSON.parse(await readFile(process.env.PC4_Q2_CAPABILITIES,'utf8'));
 assert.equal(capability.callReviewIntegrated,true,'PC2 CallReview not integrated');
 assert.ok(typeof capability.selectors?.naturalCompletionControl==='string'&&capability.selectors.naturalCompletionControl.trim(),'Actual PC2 completion-gate selector is required');
}catch(error){console.log(JSON.stringify({status:'NOT_RUN',classification:'SETUP_CAPABILITY',error:error.message,ui:{planned:6,executed:0,passed:0,failed:0,notRun:6},browserStarted:false}));process.exit(2);}
const report={startedAt:new Date().toISOString(),suite:'N04-Q2-frozen-source-ui',finalSha,expectedIdentity,plannedBoundaryIds:PLANNED_BOUNDARIES,ui:UI,api:API,executor:'AI Playwright; not human review or live AI',newTmsIntegrated:capability.newTmsIntegrated===true,capabilityClaims:capability,flows:[],boundaries:[],setupErrors:[],consoleErrors:[],blockedExternal:[],blockedLive:[],http:[],requests:[],network:[],limitations:['Capability claims require actual DOM/HTTP verification; they are not passes','All six CASE repetitions require full, natural, rate-one playback without seek','Test-only temporary stores; original state and budget remain untouched','Replay is saved fixture analysis, not actual STT/LLM; text STT absence is scoped to observed requests and runner guards','Real HTTP is relayed without automatic redirects; native browser offline uses route.continue to preserve Chromium offline behavior']};
let fixtures,approvedMedia;
try{fixtures=JSON.parse(await readFile('data/fixtures/cases.json','utf8')).cases;approvedMedia=JSON.parse(await readFile('data/demo-media-manifest.json','utf8')).assets;assert.ok(Array.isArray(fixtures)&&Array.isArray(approvedMedia));}
catch(error){console.log(JSON.stringify({status:'NOT_RUN',classification:'SETUP_FIXTURE',error:error.message,ui:{planned:6,executed:0,passed:0,failed:0,notRun:6},browserStarted:false}));process.exit(2);}
const persist=()=>writeFile(path.join(OUT,'results.json'),JSON.stringify(report,null,2));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function ownFetch(url,options={}){assert.ok(allowedHttpUrl(url,origin),'Refusing non-runner HTTP origin');const response=await fetch(url,{...options,redirect:'manual',signal:AbortSignal.timeout(15000)});assert.ok(response.status<300||response.status>=400,'Runner HTTP redirects are not accepted');assert.ok(allowedHttpUrl(response.url,origin),'Unexpected response origin');return response;}
async function status(){const response=await ownFetch(`${API}/__pc4/status`);assert.equal(response.status,200);const observed=await response.json();assert.ok(matchesIdentity(expectedIdentity,observed),'Runner source/build/nonce identity mismatch');for(const key of ['paidAnalyzerInvocations','externalConnectionsBlocked'])assert.ok(Number.isInteger(observed[key])&&observed[key]>=0,`Missing runner guard count: ${key}`);return observed;}
async function readCase(id){const response=await ownFetch(`${API}/api/cases/${id}`);assert.equal(response.status,200);return response.json();}
async function reset(){await status();const response=await ownFetch(`${API}/__pc4/reset`,{method:'POST'});assert.equal(response.status,200);return response.json();}
let browser;
async function context(options={}){
 const c=await browser.newContext({viewport:{width:1365,height:950},serviceWorkers:'block',...options});let offline=false;
 const setOffline=c.setOffline.bind(c);c.setOffline=async value=>{offline=value;await setOffline(value);};
 await c.route('**/*',async route=>{
  const url=new URL(route.request().url());
  if(['http:','https:'].includes(url.protocol)&&!allowedHttpUrl(url.href,origin)){
   report.blockedExternal.push(route.request().url());await route.abort('blockedbyclient');return;
  }
  let body;try{body=route.request().postDataJSON();}catch{}
  if(url.pathname.endsWith('/analyze') && route.request().method()==='POST' && body?.mode!=='replay'){
   report.blockedLive.push(url.pathname);await route.abort('blockedbyclient');return;
  }
  if(!['http:','https:'].includes(url.protocol)||offline){await route.continue();return;}
  try{
   const response=await route.fetch({maxRedirects:0});const location=response.headers()['location'];
   report.network.push({kind:'http-relay',url:url.href,status:response.status(),location:location||null});
   if(location&&!allowedHttpUrl(new URL(location,url).href,origin)){report.blockedExternal.push({from:url.href,redirect:location});await route.abort('blockedbyclient');return;}
   await route.fulfill({response});
  }catch(error){report.network.push({kind:'request-failed',url:url.href,message:error.message});await route.abort('failed').catch(()=>{});}
 });
 c.on('request',request=>{let body;try{body=request.postDataJSON();}catch{}report.requests.push({url:request.url(),method:request.method(),mode:body?.mode,redirectedFrom:request.redirectedFrom()?.url()||null});});
 c.on('page',page=>{page.setDefaultTimeout(15000);page.on('pageerror',e=>report.consoleErrors.push({kind:'pageerror',message:e.message}));page.on('console',m=>{if(m.type()==='error')report.consoleErrors.push({kind:'console',message:m.text()});});});
 c.on('response',r=>{let data;try{data=r.request().postDataJSON();}catch{}const row={url:r.url(),method:r.request().method(),status:r.status(),sentRevision:data?.expectedRevision,mode:data?.mode,redirectedFrom:r.request().redirectedFrom()?.url()||null,location:r.headers()['location']||null};report.network.push({kind:'browser-response',...row});if(['http:','https:'].includes(new URL(r.url()).protocol)&&!allowedHttpUrl(r.url(),origin))report.blockedExternal.push({unexpectedResponse:r.url()});if(r.url().startsWith(API+'/api/'))report.http.push(row);});
 const page=await c.newPage();
 return {context:c,page};
}
const nav=(page,label)=>page.getByRole('navigation',{name:'주 메뉴'}).getByRole('button',{name:label,exact:true}).click();
async function openCase(page,id){await page.goto(UI,{waitUntil:'domcontentloaded'});await page.getByRole('region',{name:'문의 선택'}).getByRole('button').filter({hasText:id}).click();if(await page.locator('audio').count()!==1)throw new CapabilityBlocker('NOT_RUN: current-case native audio integration absent');await page.locator('audio').waitFor({state:'attached'});}
async function action(page,locator,id,method='PATCH',suffix=''){
 const waiting=page.waitForResponse(r=>r.url()===`${API}/api/cases/${id}${suffix}` && r.request().method()===method);
 await locator.click();const response=await waiting;const data=await response.json();
 assert.equal(response.status(),200,JSON.stringify(data));return data;
}
async function screenshot(page,name){await page.screenshot({path:path.join(OUT,name+'.png'),fullPage:true});}
async function actualControl(page,name,defaultSelector){
 const selector=capability.selectors?.[name]||defaultSelector;
 if(!selector)throw new CapabilityBlocker(`NOT_RUN: ${name} UI contract not supplied`);
 const locator=page.locator(selector);
 if(await locator.count()!==1)throw new CapabilityBlocker(`NOT_RUN: ${name} does not identify one actual integrated control`);
 return locator;
}
async function openReviewDetails(page,label){const summary=page.locator('summary').filter({hasText:label});if(await summary.count()!==1)throw new CapabilityBlocker(`NOT_RUN: review disclosure missing: ${label}`);const details=summary.locator('..');if(!await details.evaluate(el=>el.open))await summary.click();assert.equal(await details.evaluate(el=>el.open),true);return details;}
async function observeAudio(page,id){
 const audio=page.locator('audio');
 if(await audio.count()!==1)throw new CapabilityBlocker('NOT_RUN: one current-case native audio element is required');
 await page.waitForFunction(()=>document.querySelector('audio')?.readyState>=1);
 const session=`${id}-${Date.now()}`;
 await audio.evaluate((a,{id,session})=>{
  const started=performance.now();
  const selected=()=>document.querySelector('[aria-label="문의 선택"] [aria-pressed="true"]')?.textContent?.match(/(?:CASE|INT)-[A-Z0-9]+/)?.[0]||null;
  const sample=()=>({caseId:selected(),source:a.currentSrc,session,connected:a.isConnected,time:a.currentTime,rate:a.playbackRate,wallMs:performance.now()-started});
  const trace={caseId:id,source:a.currentSrc,session,duration:a.duration,initialTime:a.currentTime,events:[],samples:[sample()]};
  const listeners=[];
  for(const type of ['play','playing','pause','timeupdate','ended','seeking','seeked','ratechange','emptied','error']){
   const callback=e=>trace.events.push({...sample(),type,trusted:e.isTrusted});a.addEventListener(type,callback);listeners.push([type,callback]);
  }
  const timer=setInterval(()=>trace.samples.push(sample()),200);
  window.__pc4AudioObservation={element:a,trace,finish(){clearInterval(timer);for(const[type,fn]of listeners)a.removeEventListener(type,fn);return{...trace,wallSeconds:(performance.now()-started)/1000,finalTime:a.currentTime,ended:a.ended,played:Array.from({length:a.played.length},(_,i)=>[a.played.start(i),a.played.end(i)])};}};
 },{id,session});
 return audio;
}
async function finishObservation(page){return page.evaluate(()=>window.__pc4AudioObservation.finish());}
async function playAudio(page,audio){
 // The custom "처음부터 전체 통화 재생" replaces this node and invalidates its observation.
 if(!await audio.isVisible()||!await audio.evaluate(a=>a.controls))throw new CapabilityBlocker('NOT_RUN: current observed native audio controls are unavailable');
 await audio.click({position:{x:24,y:27}});
}
async function audioEnd(page,id){
 const gate=await actualControl(page,'naturalCompletionControl');
 assert.equal(await gate.isEnabled(),false,'Completion gate must be unavailable before full playback');
 const audio=await observeAudio(page,id);let observation;
 const fixture=fixtures.find(item=>item.id===id);assert.ok(typeof fixture?.audioUrl==='string'&&fixture.audioUrl.startsWith('/'),'Current-case fixture audio registration required');const expectedSource=new URL(fixture.audioUrl,UI).href;
 try{
  assert.equal(await audio.evaluate(a=>a.currentSrc),expectedSource,'Native player must use this exact case fixture audio');
  const duration=await audio.evaluate(a=>a.duration);assert.ok(Number.isFinite(duration)&&duration>0&&duration<=180,'Unexpected asset duration; review frozen media contract');
  await playAudio(page,audio);
  await page.waitForFunction(()=>{const a=document.querySelector('audio');return a&&!a.paused&&a.currentTime>0;},null,{timeout:15000});
  await page.waitForFunction(()=>document.querySelector('audio')?.ended===true,null,{timeout:duration*1000+30000});
 }finally{observation=await finishObservation(page);}
 assert.equal(observation.source,expectedSource,'Observed audio source differs from the exact case fixture');
 const judgement=judgePlayback(observation);assert.equal(judgement.accepted,true,JSON.stringify(judgement));
 await gate.waitFor({state:'visible'});assert.equal(await gate.isEnabled(),true,'Actual PC2 gate did not accept full natural playback');
 return {method:'native controls, full duration from zero, rate one, no seek, natural ended',expectedFixtureAudio:expectedSource,...observation,judgement,syntheticEventsDispatched:0};
}
async function eventually(check,message,timeout=15000){const deadline=Date.now()+timeout;while(Date.now()<deadline){if(await check())return;await sleep(100);}assert.fail(message);}
async function nativeVideoPlay(page,video){
 if(!await video.isVisible()||!await video.evaluate(v=>v.controls))throw new CapabilityBlocker('NOT_RUN: actual native video controls unavailable');
 assert.equal(await video.evaluate(v=>v.paused),true,'Video must wait for explicit native playback input');
 await video.evaluate(v=>{const events=[];for(const type of ['play','playing'])v.addEventListener(type,e=>events.push({type,trusted:e.isTrusted,time:v.currentTime,source:v.currentSrc}),{once:true});window.__pc4NativeVideoPlay={events};});
 await video.focus();assert.equal(await video.evaluate(v=>v.ownerDocument.activeElement===v),true,'Native video must hold keyboard focus before Space');await page.keyboard.press('Space');
 await eventually(()=>page.evaluate(()=>['play','playing'].every(type=>window.__pc4NativeVideoPlay.events.some(e=>e.type===type&&e.trusted))),'Space did not produce native trusted video play/playing');
 return {method:'native video focus + keyboard Space',focusVerified:true,events:await page.evaluate(()=>window.__pc4NativeVideoPlay.events)};
}
async function selectRegisteredVideoEvent(page,clip){const eventId=clip.eventIds?.[0];if(!eventId)throw new CapabilityBlocker('NOT_RUN: clip event registration missing');await (await actualControl(page,'wmsVideoEventControl',`[data-testid="event-${eventId}"]`)).click();await eventually(()=>page.locator(capability.selectors?.wmsMediaOpenControl||'[data-testid="open-video"]').count().then(n=>n===1),'Registered clip opener did not appear after selecting its actual WMS event');}
async function verifyVideoAsset(video,clip){
 const expected=approvedMedia.find(asset=>`/demo/${asset.name}`===clip.url);assert.ok(expected?.synthetic===true&&Number.isInteger(expected.bytes)&&/^[0-9a-f]{64}$/.test(expected.sha256),'Registered approved manifest asset required');
 const actual=await video.evaluate(async v=>{const source=v.currentSrc;const url=new URL(source);if(url.origin!==location.origin||!['blob:','http:','https:'].includes(url.protocol))throw new Error('Video source is not this runner origin');const response=await fetch(source,{redirect:'error'});if(!response.ok)throw new Error(`Video source fetch ${response.status}`);const bytes=await response.arrayBuffer();const digest=await crypto.subtle.digest('SHA-256',bytes);return {source,sourceKind:url.protocol,bytes:bytes.byteLength,sha256:Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('')};});
 assert.equal(actual.bytes,expected.bytes,'Rendered video bytes differ from approved manifest');assert.equal(actual.sha256,expected.sha256,'Rendered video hash differs from approved manifest');return {...actual,registeredUrl:clip.url};
}
async function registeredVideo(page,source,label){
 const clip=source.media?.find(m=>m.system==='WMS'&&m.caseId===source.id&&m.synthetic===true&&m.url?.startsWith('/'));
 if(!clip)throw new CapabilityBlocker('NOT_RUN: current-case registered synthetic WMS clip absent');
 const start=clip.startSeconds,end=clip.endSeconds;assert.ok(Number.isFinite(start)&&Number.isFinite(end)&&start>=0&&end>start&&end-start<=180);
 await selectRegisteredVideoEvent(page,clip);
 const opener=await actualControl(page,'wmsMediaOpenControl','[data-testid="open-video"]');
 if(await opener.count()!==1)throw new CapabilityBlocker('NOT_RUN: registered WMS clip opener is not mapped');await opener.click();
 const dialog=await actualControl(page,'mediaDialog','dialog[open]');await dialog.waitFor({state:'visible'});
 assert.ok((await dialog.innerText()).includes(source.id),'Video dialog must identify the current case');assert.match(await dialog.innerText(),/합성/);
 await eventually(()=>page.locator(capability.selectors?.mediaVideo||'dialog[open] video').count().then(n=>n===1),'Verified video did not render after the product asset check');
 const video=await actualControl(page,'mediaVideo','dialog[open] video');
 await eventually(()=>video.evaluate(v=>v.readyState>=1),'Registered video metadata did not load');
 await eventually(()=>video.evaluate((v,start)=>!v.seeking&&Math.abs(v.currentTime-start)<.35,start),'Player did not initialize at the registered segment start');
 const assetVerification=await verifyVideoAsset(video,clip);
 await video.evaluate(v=>{const started=performance.now();const events=[];const listeners=[];for(const type of ['play','playing','timeupdate','pause','ended','seeking','seeked','ratechange']){const fn=e=>events.push({type,trusted:e.isTrusted,time:v.currentTime,rate:v.playbackRate,source:v.currentSrc});v.addEventListener(type,fn);listeners.push([type,fn]);}window.__pc4VideoObservation={initialTime:v.currentTime,finish(){for(const[type,fn]of listeners)v.removeEventListener(type,fn);return{initialTime:this.initialTime,source:v.currentSrc,duration:v.duration,finalTime:v.currentTime,paused:v.paused,wallSeconds:(performance.now()-started)/1000,events,played:Array.from({length:v.played.length},(_,i)=>[v.played.start(i),v.played.end(i)])};}};});
 const playbackInput=await nativeVideoPlay(page,video);
 await eventually(()=>video.evaluate((v,start)=>!v.paused&&v.currentTime>start,start),'Registered segment did not begin native playback');
 await eventually(()=>video.evaluate((v,end)=>v.paused&&v.currentTime>=end-.25,end),'Registered segment did not reach its natural stopping point',(end-start)*1000+30000);
 const observation=await page.evaluate(()=>window.__pc4VideoObservation.finish());assert.equal(observation.source,assetVerification.source);assert.ok(observation.finalTime<=end+.5);assert.ok(observation.wallSeconds>=end-start-.75);
 for(const type of ['play','playing'])assert.ok(observation.events.some(e=>e.type===type&&e.trusted),`Missing native video ${type}`);
 assert.ok(observation.events.every(e=>Math.abs(e.rate-1)<.001&&e.source===observation.source&&!['seeking','seeked'].includes(e.type)),'Video playback changed source/rate or sought');
 let coverageEnd=start;for(const[a,b]of observation.played){if(a>coverageEnd+.1)break;if(b>=start)coverageEnd=Math.max(coverageEnd,b);}assert.ok(coverageEnd>=end-.25,'Registered video segment has missing played coverage');
 await screenshot(page,label+'-registered-cctv');await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});await eventually(()=>opener.evaluate(el=>el.ownerDocument.activeElement===el),'Escape did not restore focus to the actual media opener');
 return {asset:clip.id,registeredRange:[start,end],assetVerification,playbackInput,observation,escapeClosed:true,focusReturnedToOpener:true,syntheticEventsDispatched:0};
}
async function flow(id,repeat){
 const row={id:`${id}-${repeat}`,caseId:id,repetition:repeat,status:'RUNNING',startedAt:new Date().toISOString(),steps:[],store:await reset()};report.flows.push(row);await persist();
 const {context:c,page}=await context();const startHttp=report.http.length;
 try{
  await openCase(page,id);const source=await readCase(id);
  await openReviewDetails(page,'원문과 화자별 대화록 확인');await page.getByRole('heading',{name:'화자별 대화록',exact:true}).waitFor();row.steps.push('source-and-speaker-transcript-disclosure-opened');
  row.audio=await audioEnd(page,id);row.steps.push('full-natural-rate-one-audio-ended');
  const replay=capability.selectors?.replayControl?await actualControl(page,'replayControl'):page.getByRole('button',{name:'저장된 분석 결과 재생',exact:false});
  const analyzed=await action(page,replay,id,'POST','/analyze');
  assert.equal(analyzed.mode,'replay');row.steps.push('replay-analysis-via-ui');
  await openReviewDetails(page,'AI 제안과 현재 입력 상세 대조');await page.getByRole('region',{name:'점포 ID 비교',exact:true}).waitFor();row.steps.push('ai-proposal-and-current-intake-comparison-opened');
  for(const [kind,label] of [['WMS','WMS 작업 확인'],['TMS','TMS 배송 확인']]){
   await nav(page,label);const region=await actualControl(page,`${kind.toLowerCase()}Region`,`[role="region"][aria-label="${kind} 물류 확인"],section[aria-label="${kind} 물류 확인"]`);await region.waitFor();
   assert.ok((await region.innerText()).includes(id));
   const prefix=kind.toLowerCase();
   const raw=capability.selectors?.[prefix+'RawSourceControl']?await actualControl(page,prefix+'RawSourceControl'):region.locator('summary').filter({hasText:'원본 행 보기'}).first();
   if(await raw.count()!==1)throw new CapabilityBlocker(`NOT_RUN: ${kind} integrated raw-source control not mapped`);await raw.click();
   const rawText=capability.selectors?.[prefix+'RawSourceText']?await actualControl(page,prefix+'RawSourceText'):region.locator('details[open] pre').first();
   if(await rawText.count()!==1)throw new CapabilityBlocker(`NOT_RUN: ${kind} integrated raw-source content not mapped`);assert.ok((await rawText.innerText()).length>10);
   const link=capability.selectors?.[prefix+'EvidenceLinkControl']?await actualControl(page,prefix+'EvidenceLinkControl'):region.getByRole('button',{name:'이 근거 연결',exact:true}).first();
   if(await link.count()!==1)throw new CapabilityBlocker(`NOT_RUN: ${kind} integrated evidence-link control not mapped`);
   await action(page,link,id);row.steps.push(`${kind.toLowerCase()}-source-and-evidence-linked-via-ui`);
   if(kind==='WMS'&&id==='CASE-0002'){row.video=await registeredVideo(page,source,row.id);row.steps.push('registered-cctv-segment-native-play-escape-focus-return');}
  }
  await nav(page,'상담 작업대');
  assert.ok((await page.getByRole('region',{name:'연결한 물류 근거'}).innerText()).includes('선택 2건'));
  const requestInput=await actualControl(page,'requestTextarea','.form-grid textarea');
  const review=capability.selectors?.reviewCheckbox?await actualControl(page,'reviewCheckbox'):page.getByRole('checkbox',{name:'점포·상품·전달 부서를 원문과 대조하고, 접수 정보를 편집·확인했습니다.'});
  await requestInput.fill(`${source.intake?.request || source.sourceText}\nPC4 ${id}-${repeat}: 원문과 근거를 대조한 합성 시연 확인.`);
  await (await actualControl(page,'departmentSelect','.department-card select')).selectOption(id==='CASE-0001'?'delivery':'warehouse');
  await review.check();await requestInput.fill((await requestInput.inputValue())+' 수정 후 재확인');assert.equal(await review.isChecked(),false,'Editing must clear prior confirmation');await review.check();
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
  assert.ok(saved.selectedEvidence.every(key=>source.evidence.some(e=>e.id===key)),'Linked evidence must belong to the original case');
  row.steps.push('owner-read-registered-reply-and-closed-state');row.final={status:saved.status,revision:saved.revision,selectedEvidence:saved.selectedEvidence,sourcePreserved:true};
  await screenshot(page,row.id+'-owner');row.status='PASS';
 }catch(error){row.status=error instanceof CapabilityBlocker?'NOT_RUN':'FAIL';row.error={message:error.message,stack:error.stack};await screenshot(page,row.id+'-failure').catch(()=>{});}
 finally{row.finishedAt=new Date().toISOString();row.http=report.http.slice(startHttp);await c.close();await persist();console.log(JSON.stringify({flow:row.id,status:row.status,steps:row.steps,error:row.error?.message}));}
}
async function boundary(id,fn,options={}){const row={id,status:'RUNNING',store:await reset()};report.boundaries.push(row);const {context:c,page}=await context(options);try{row.result=await fn(page,c);row.status='PASS';}catch(error){row.status=error instanceof CapabilityBlocker?'NOT_RUN':'FAIL';row.error=error.message;await screenshot(page,id+'-failure').catch(()=>{});}finally{await c.close();await persist();console.log(JSON.stringify({boundary:id,status:row.status,error:row.error}));}}
async function boundaries(){
 await boundary('audio-end-seek-must-not-complete',async page=>{
  await openCase(page,'CASE-0001');const gate=await actualControl(page,'naturalCompletionControl');assert.equal(await gate.isEnabled(),false);
  const audio=await observeAudio(page,'CASE-0001');await playAudio(page,audio);await page.waitForFunction(()=>document.querySelector('audio')?.currentTime>0);
  await audio.evaluate(a=>{a.currentTime=a.duration-.75;});await page.waitForFunction(()=>document.querySelector('audio')?.ended===true);
  const observation=await finishObservation(page);const judged=judgePlayback(observation);assert.equal(judged.accepted,false);assert.equal(await gate.isEnabled(),false,'End seek incorrectly granted whole-call completion');
  return {scope:'negative only; never one of six completions',observation,judged,actualGateEnabled:false};
 });
 await boundary('audio-segment-must-not-complete',async page=>{
  await openCase(page,'CASE-0001');await openReviewDetails(page,'원문과 화자별 대화록 확인');const segment=await actualControl(page,'segmentControl');const gate=await actualControl(page,'naturalCompletionControl');
  await observeAudio(page,'CASE-0001');await segment.click();await page.waitForFunction(()=>{const a=document.querySelector('audio');return a&&!a.paused&&a.currentTime>0;});
  await page.waitForFunction(()=>document.querySelector('audio')?.paused===true,null,{timeout:capability.segmentTimeoutMs||30000});
  const observation=await finishObservation(page);const judged=judgePlayback(observation);assert.equal(judged.accepted,false);assert.equal(await gate.isEnabled(),false,'Partial segment incorrectly granted whole-call completion');return {observation,judged,actualGateEnabled:false};
 });
 await boundary('previous-case-native-ended-must-not-complete-current',async page=>{
  await openCase(page,'CASE-0001');const old=await observeAudio(page,'CASE-0001');await playAudio(page,old);await page.waitForFunction(()=>document.querySelector('audio')?.currentTime>0);
  await page.getByRole('region',{name:'문의 선택'}).getByRole('button').filter({hasText:'CASE-0002'}).click();const gate=await actualControl(page,'naturalCompletionControl');assert.equal(await gate.isEnabled(),false);
  const oldSourcePreserved=await page.evaluate(()=>window.__pc4AudioObservation.element.currentSrc===window.__pc4AudioObservation.trace.source);
  if(!oldSourcePreserved)throw new CapabilityBlocker('NOT_RUN previous-case callback: player source was replaced; current-case seek would not reproduce an old-source callback');
  const resumed=await page.evaluate(async()=>{try{const a=window.__pc4AudioObservation.element;a.currentTime=a.duration-.75;await a.play();return true;}catch{return false;}});
  if(!resumed)throw new CapabilityBlocker('NOT_RUN callback path: old media cleanup prevented native replay; no synthetic event will be substituted');
  try{await page.waitForFunction(()=>window.__pc4AudioObservation.element.ended===true,null,{timeout:5000});}catch{throw new CapabilityBlocker('NOT_RUN callback path: native previous player could not reach ended after cleanup; no fabricated callback');}
  const observation=await finishObservation(page);assert.equal(judgePlayback(observation).accepted,false);assert.equal(await gate.isEnabled(),false,'Previous-case callback enabled current-case completion');return {observation,currentCase:'CASE-0002',actualGateEnabled:false,syntheticEventsDispatched:0};
 });
 await boundary('new-text-different-day-no-implicit-evidence',async page=>{
  const requestStart=report.requests.length;
  await openCase(page,'CASE-0001');await nav(page,'경영주 접수');
  const ref=fixtures[0];const text='PC4: 동일 점포의 다른 날 배송 문의입니다. 어제 배송과 오늘 배송은 별개이며 이번 문의의 실제 도착 여부를 확인해 주세요.';
  await page.getByLabel('점포코드',{exact:true}).fill(ref.intake.storeId);await page.getByLabel('문의 제목',{exact:true}).fill(ref.intake.subject);await page.getByLabel('상세 내용',{exact:true}).fill(text);
  assert.equal(await page.locator('.owner-form select').inputValue(),'');
  const wait=page.waitForResponse(r=>r.url()===API+'/api/intake' && r.request().method()==='POST');await page.getByRole('button',{name:'문의 접수하기',exact:false}).click();const response=await wait;assert.equal(response.status(),201);const created=await response.json();assert.ok(!created.linkedFixtureId);assert.deepEqual(created.evidence,[]);assert.equal(created.sourceText,text);
  await page.getByRole('button',{name:'시연: 상담 작업대로 이동',exact:false}).click();const analyzing=page.waitForResponse(r=>r.url().endsWith(`/api/cases/${created.id}/analyze`));await page.getByRole('button',{name:'저장된 분석 결과 재생',exact:false}).click();assert.equal((await analyzing).status(),409);await page.getByRole('alert').filter({hasText:'새 텍스트 문의에는 사전 리플레이가 없습니다'}).waitFor();
  assert.equal(await page.locator('audio').count(),0,'Text intake must not render a voice/STT player');
  const requests=report.requests.slice(requestStart);assert.equal(requests.filter(r=>r.method==='POST'&&/stt|transcrib|speech|audio/i.test(new URL(r.url).pathname)).length,0);
  assert.ok(requests.filter(r=>r.url.endsWith('/analyze')).every(r=>r.mode==='replay'));
  await screenshot(page,'new-text-replay-unavailable');return {caseId:created.id,sourcePreserved:true,noImplicitEvidence:true,observedSTTRequests:0,textAudioPlayers:0,STTScope:'browser HTTP observations; server NeverLive/external-network guard is separate runner evidence',analysisStatus:409,analysis:'NOT_RUN: new text has no replay fixture; paid AI forbidden'};
 });
 await boundary('explicit-reference-text-media-missing',async page=>{
  await openCase(page,'CASE-0002');await nav(page,'경영주 접수');await page.locator('.owner-form select').selectOption('CASE-0002');await page.getByLabel('상세 내용',{exact:true}).fill('PC4: 같은 합성 배송건 확인을 요청합니다. 영상은 기록된 등록 여부로만 판단해 주세요.');
  const waiting=page.waitForResponse(r=>r.url()===API+'/api/intake'&&r.request().method()==='POST');await page.getByRole('button',{name:'문의 접수하기',exact:false}).click();const response=await waiting;assert.equal(response.status(),201);const created=await response.json();assert.equal(created.linkedFixtureId,'CASE-0002');assert.ok(!created.media?.length);
  await nav(page,'WMS 작업 확인');const region=await actualControl(page,'wmsRegion','section[aria-label="WMS 공정 확인"]');assert.ok((await region.innerText()).includes('미등록'));assert.equal(await region.locator('[data-testid="open-video"]').count(),0);await screenshot(page,'reference-text-media-missing');return {caseId:created.id,reference:'CASE-0002',mediaCopied:false,missingShown:true};
 });
 await boundary('media-404-and-retry',async(page,c)=>{
  const frozen=await readCase('CASE-0002');const clip=frozen.media?.find(m=>m.system==='WMS'&&m.caseId==='CASE-0002'&&m.synthetic===true&&m.url?.startsWith('/'));
  if(!clip)throw new CapabilityBlocker('NOT_RUN: frozen CASE-0002 has no approved WMS clip for media 404 control');
  const mediaUrl=new URL(clip.url,UI).href;await openCase(page,'CASE-0002');await nav(page,'WMS 작업 확인');await selectRegisteredVideoEvent(page,clip);await c.route(mediaUrl,route=>route.fulfill({status:404,body:'Test missing synthetic asset'}));
  const videoButton=await actualControl(page,'wmsMediaOpenControl','[data-testid="open-video"]');await videoButton.click();const error=page.getByRole('alert').filter({hasText:'영상 재생 차단'});await error.waitFor();assert.match(await error.innerText(),/영상 응답 404/);assert.equal(await page.locator('dialog video').count(),0,'Failed verification must not render a playable video');assert.ok((await page.getByRole('dialog').innerText()).includes('원본 스캔과 비교'));await screenshot(page,'media-404');
  await c.unroute(mediaUrl);await page.getByRole('button',{name:'영상 다시 불러오기',exact:true}).click();await page.waitForFunction(()=>document.querySelector('dialog video')?.readyState>=1);const video=page.getByRole('dialog').locator('video');const assetVerification=await verifyVideoAsset(video,clip);const position=await video.evaluate(v=>v.currentTime);const playbackInput=await nativeVideoPlay(page,video);await page.waitForFunction(start=>{const v=document.querySelector('dialog video');return v && v.currentTime>start+.25;},position);await page.keyboard.press('Escape');assert.equal(await page.getByRole('dialog').count(),0);await eventually(()=>videoButton.evaluate(el=>el.ownerDocument.activeElement===el),'404 retry dialog did not restore opener focus');return {asset:clip.id,url:mediaUrl,injectedStatus:404,errorDisplayed:true,originalScanPreserved:true,retryMetadataLoaded:true,assetVerification,playbackInput,nativeVideoAdvanced:true,escapeClosed:true,focusReturned:true};
 });
 await boundary('api-error-and-recovery-no-false-save',async(page,c)=>{
  await openCase(page,'CASE-0001');const original=await readCase('CASE-0001');await page.locator('.form-grid textarea').fill('PC4 임시 장애에서 저장하면 안 되는 변경');
  const pattern=`${API}/api/cases/CASE-0001`;await c.route(pattern,async route=>{if(route.request().method()==='PATCH')await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:{message:'PC4 합성 일시 장애'}})});else await route.fallback();});
  await page.getByRole('button',{name:'접수 내용 저장',exact:true}).click();await page.getByRole('alert').filter({hasText:'PC4 합성 일시 장애'}).waitFor();assert.equal((await readCase('CASE-0001')).revision,original.revision);assert.equal(await page.getByRole('status').filter({hasText:'상담원이 편집한 접수 정보를 저장했습니다'}).count(),0);await screenshot(page,'api-error-no-false-save');
  await c.unroute(pattern);await action(page,page.getByRole('button',{name:'접수 내용 저장',exact:true}),'CASE-0001');return {injectedStatus:503,errorVisible:true,noFalseSuccess:true,storedRevisionUnchangedOnFailure:true,retrySaved:true};
 });
 await boundary('api-offline-example-and-reconnect',async(page,c)=>{
  const pattern=API+'/api/**';await c.route(pattern,route=>route.abort('connectionrefused'));await page.goto(UI,{waitUntil:'domcontentloaded'});await page.getByRole('button',{name:'합성 예시 열람',exact:true}).click();await page.getByRole('region',{name:'문의 선택'}).waitFor();await page.getByText('현재 예시 열람 중입니다. 변경 사항은 저장되지 않습니다.',{exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'접수 내용 저장',exact:true}).isEnabled(),false);await screenshot(page,'offline-readonly-example');
  await c.unroute(pattern);await page.getByRole('button',{name:'다시 연결',exact:true}).click();await page.waitForFunction(()=>!document.body.textContent.includes('현재 예시 열람 중입니다. 변경 사항은 저장되지 않습니다.'));await page.getByRole('button',{name:'접수 내용 저장',exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'접수 내용 저장',exact:true}).isEnabled(),true);return {scope:'API disconnected; static UI and fixture remain available (not complete device offline)',readonlyExample:true,modeDisplayed:true,reconnected:true};
 });
 await boundary('browser-offline-save-and-recovery',async(page,c)=>{
  await openCase(page,'CASE-0001');const before=await readCase('CASE-0001');await page.locator('.form-grid textarea').fill('PC4 브라우저 오프라인 복구 검사');await c.setOffline(true);
  await page.getByRole('button',{name:'접수 내용 저장',exact:true}).click();await page.getByRole('alert').filter({hasText:'해피콜 서버에 연결하지 못했습니다'}).waitFor();assert.equal((await readCase('CASE-0001')).revision,before.revision);await screenshot(page,'browser-offline-save');
  await c.setOffline(false);await action(page,page.getByRole('button',{name:'접수 내용 저장',exact:true}),'CASE-0001');const after=await readCase('CASE-0001');assert.equal(after.intake.request,'PC4 브라우저 오프라인 복구 검사');return {scope:'actual browser context offline/online',errorDisplayed:true,stateUnchangedOnFailure:true,retrySaved:true};
 });
 await boundary('two-ui-editors-real-409-no-overwrite',async(page,c)=>{
  await openCase(page,'CASE-0001');const second=await c.newPage();await openCase(second,'CASE-0001');
  const input=await actualControl(page,'requestTextarea','.form-grid textarea');await input.fill('PC4 stale editor must not overwrite');
  await (await actualControl(second,'requestTextarea','.form-grid textarea')).fill('PC4 current editor preserved');await action(second,second.getByRole('button',{name:'접수 내용 저장',exact:true}),'CASE-0001');
  const before=await readCase('CASE-0001');const waiting=page.waitForResponse(r=>r.url()===API+'/api/cases/CASE-0001'&&r.request().method()==='PATCH');await page.getByRole('button',{name:'접수 내용 저장',exact:true}).click();const response=await waiting;assert.equal(response.status(),409);await page.getByRole('alert').filter({hasText:'다른 작업자가 접수를 수정했습니다'}).waitFor();const after=await readCase('CASE-0001');assert.equal(after.revision,before.revision);assert.equal(after.intake.request,'PC4 current editor preserved');return {status:409,scope:'two actual UI submissions to real isolated API',freshStatePreserved:true};
 });
 await boundary('future-evidence-hidden-in-investigation-ui',async(page,c)=>{
  const source=await readCase('CASE-0001');const original=source.evidence.find(e=>e.id==='E-M1');assert.ok(original);assert.match(source.asOf,/T07:00:00\+09:00$/);assert.match(original.time,/T05:00:00\+09:00$/);
  await openCase(page,'CASE-0001');await nav(page,'TMS 배송 확인');const originalLink=()=>page.getByRole('heading',{name:original.label,exact:true}).locator('xpath=ancestor::article[1]').getByRole('button',{name:'이 근거 연결',exact:true});assert.equal(await originalLink().isEnabled(),true,'07:00 cutoff must allow registered 05:00 E-M1 evidence');
  const marker='PC4 FUTURE EVIDENCE MUST NOT BE ADOPTED';let injected=false,phase='early-cutoff';
  await c.route(API+'/api/cases',async route=>{if(route.request().method()!=='GET'){await route.fallback();return;}const response=await route.fetch({maxRedirects:0});assert.equal(response.status(),200);const data=await response.json();const item=data.cases.find(x=>x.id==='CASE-0001');const evidence=item?.evidence?.find(e=>e.id==='E-M1');const stop=item?.tms?.stops?.find(s=>s.id===item.store.id);if(!evidence||!stop)throw new Error('Frozen fixture has no E-M1/target stop');if(phase==='early-cutoff'){item.asOf=item.asOf.replace('T07:00:00','T04:30:00');}else{const future=new Date(Date.parse(item.asOf)+3600000).toISOString();evidence.time=future;evidence.label=marker;stop.actual=future;stop.mobileEntry=future;stop.mobileExit=future;}injected=true;await route.fulfill({response,json:data});});
  await openCase(page,'CASE-0001');await nav(page,'TMS 배송 확인');assert.equal(injected,true);assert.equal(await originalLink().isEnabled(),false,'04:30 cutoff must withhold the 05:00 E-M1 observation');
  const earlyPlanned=await actualControl(page,'futurePlannedValue','[aria-label="선택 방문 상세"] dt:text-is("계획 도착") + dd');const futurePlan=await earlyPlanned.innerText();assert.match(futurePlan,/05:00.*기준 이후 계획/,'05:00 future plan remains labelled at 04:30 cutoff');assert.doesNotMatch(futurePlan,/미채택/);
  phase='future-records';injected=false;
  await openCase(page,'CASE-0001');await nav(page,'TMS 배송 확인');assert.equal(injected,true);
  const actual=await actualControl(page,'futureActualValue','[data-testid="tms-actual"]');assert.match(await actual.innerText(),/기준 이후.*미채택/,'Future actual must not appear as current completed delivery');
  const futureFields={actual:await actual.innerText(),plannedAt0430Cutoff:futurePlan};
  for(const[name,label]of [['futureGpsEntryValue','모바일 GPS 진입'],['futureGpsExitValue','모바일 GPS 이탈']]){const value=await actualControl(page,name,`[aria-label="선택 방문 상세"] dt:text-is("${label}") + dd`);futureFields[name]=await value.innerText();assert.match(futureFields[name],/기준 이후.*미채택/,'Future GPS must not appear as a current observed movement');}
  const marked=page.getByRole('heading',{name:marker,exact:true});let futureLinkDisabled=true;
  if(await marked.count()){const card=marked.locator('xpath=ancestor::article[1]');const link=card.getByRole('button',{name:'이 근거 연결',exact:true});if(await link.count()!==1)throw new CapabilityBlocker('NOT_RUN: future evidence link control not identified');futureLinkDisabled=!await link.isEnabled();assert.equal(futureLinkDisabled,true,'Future evidence remained selectable');}
  return {scope:'separate 07:00 positive, 04:30 cutoff counterexample, and +1h actual/GPS read-only HTTP injections; no stored source mutation',normal0700Allows0500Evidence:true,cutoff0430Withholds0500Evidence:true,futureOffsetSeconds:3600,futureActualWithheld:true,futureGpsWithheld:true,futurePlanRetained:true,futureFields,futureLinkDisabled};
 });
 await boundary('different-business-totes-not-continuous-tracking',async page=>{
  const fixture=await readCase('CASE-0002');assert.ok(fixture.wms?.picking?.toteId&&fixture.wms?.shipping?.toteId);assert.notEqual(fixture.wms.picking.toteId,fixture.wms.shipping.toteId);
  await openCase(page,'CASE-0002');await nav(page,'WMS 작업 확인');const notice=await actualControl(page,'differentToteNotice');await notice.waitFor({state:'visible'});const text=await notice.innerText();assert.match(text,/미확인|보증하지|연결.*확인.*필요/,'Distinct business totes need an explicit continuity limitation');return {pickingTote:fixture.wms.picking.toteId,shippingTote:fixture.wms.shipping.toteId,observedNotice:text,scope:'real frozen fixture with distinct business totes; not synthetic visual object tracking proof'};
 });
 for(const width of [1365,921,390])await boundary(`responsive-keyboard-reduced-motion-${width}`,async page=>{
  await openCase(page,'CASE-0001');await page.emulateMedia({reducedMotion:'reduce'});const views=[];
  for(const label of ['상담 작업대','경영주 접수','센터 회신','WMS 작업 확인','TMS 배송 확인']){
   const button=page.getByRole('navigation',{name:'주 메뉴'}).getByRole('button',{name:label,exact:true});await button.focus();await page.keyboard.press('Enter');await page.getByRole('heading',{name:label,exact:true}).first().waitFor();
   const geometry=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,reduced:matchMedia('(prefers-reduced-motion: reduce)').matches}));assert.ok(geometry.scrollWidth<=geometry.width+1,`${label}: horizontal document overflow`);assert.equal(geometry.reduced,true);views.push({label,...geometry});
  }
  const animation=capability.selectors?.animationPlayControl?await actualControl(page,'animationPlayControl'):page.getByRole('button',{name:'설명 재생',exact:true});
  if(await animation.count()!==1)throw new CapabilityBlocker('NOT_RUN: actual TMS reduced-motion animation control not identified');assert.equal(await animation.isEnabled(),false,'Reduced motion must prevent automatic explanation movement');
  const visits=(await actualControl(page,'tmsVisitList','[aria-label="방문 선택"]')).getByRole('button');
  if(await visits.count()<2)throw new CapabilityBlocker('NOT_RUN: fewer than two actual visits for next/previous traversal');
  const heading=await actualControl(page,'tmsSelectedVisitHeading','[aria-label="선택 방문 상세"] h2');
  const previous=await actualControl(page,'tmsPreviousControl','[aria-label="선택 방문 상세"] button:text-is("← 이전 방문")');
  const next=await actualControl(page,'tmsNextControl','[aria-label="선택 방문 상세"] button:text-is("다음 방문 →")');
  await visits.first().focus();await page.keyboard.press('Enter');const firstTitle=await heading.innerText();assert.ok(firstTitle.trim());assert.equal(await visits.first().getAttribute('aria-pressed'),'true');assert.equal(await previous.isEnabled(),false);assert.equal(await next.isEnabled(),true);
  await next.focus();await page.keyboard.press('Enter');const secondTitle=await heading.innerText();assert.notEqual(secondTitle,firstTitle,'Next visit must change selected details');assert.equal(await visits.nth(1).getAttribute('aria-pressed'),'true');
  const selectedRow=await actualControl(page,'tmsSelectedRow','[aria-label="방문 기록 전체"] tbody tr:has(button[aria-pressed="true"])');assert.ok((await selectedRow.innerText()).includes(secondTitle),'Selected table row must follow selected visit');assert.equal(await previous.isEnabled(),true);
  await previous.focus();await page.keyboard.press('Enter');assert.equal(await heading.innerText(),firstTitle);assert.equal(await visits.first().getAttribute('aria-pressed'),'true');assert.ok((await selectedRow.innerText()).includes(firstTitle),'Previous visit must restore selected row');
  const finalGeometry=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));assert.ok(finalGeometry.scrollWidth<=finalGeometry.width+1,'Visit traversal caused document overflow');
  await screenshot(page,`responsive-${width}`);return {views,keyboard:'focused real navigation buttons and visit/next/previous controls + Enter',visitTraversal:{firstTitle,secondTitle,restored:firstTitle,selectedRowFollows:true},reducedMotionControlDisabled:true,scope:'not a complete screen-reader, full Tab-order or color-contrast audit'};
 },{viewport:{width,height:950}});
}
try{
 const deadline=Date.now()+150000;let ready=false;
 while(Date.now()<deadline){try{const response=await ownFetch(UI);if(response.status===200){ready=true;break;}}catch{}await sleep(1000);}
 assert.ok(ready,'Own frozen production UI failed readiness');report.guardStart=await status();assert.equal(report.guardStart.paidAnalyzerInvocations,0);assert.equal(report.guardStart.externalConnectionsBlocked,0);await persist();
 browser=await chromium.launch({headless:true,executablePath:process.env.E2E_CHROMIUM});
 report.browserVersion=browser.version();
 if(process.env.PC4_UI_ONLY!=='boundaries')for(const id of ['CASE-0001','CASE-0002'])for(let repeat=1;repeat<=3;repeat++){await flow(id,repeat);if(process.env.PC4_UI_ONLY==='first')break;}
 if(process.env.PC4_UI_ONLY!=='first')await boundaries();
}catch(error){report.setupErrors.push({classification:'SETUP_OR_HARNESS',message:error.message,stack:error.stack});}
finally{
 if(browser)await browser.close();report.finishedAt=new Date().toISOString();
 try{report.guard=await status();}catch(error){report.guard=null;report.setupErrors.push({classification:'RUN_IDENTITY',message:error.message});}
 for(const id of PLANNED_BOUNDARIES)if(!report.boundaries.some(row=>row.id===id))report.boundaries.push({id,status:'NOT_RUN',error:'Execution never reached this planned boundary'});
 for(const row of [...report.flows,...report.boundaries])if(row.status==='RUNNING'){row.status='NOT_RUN';row.error='Setup/harness interrupted execution';}
 if(report.boundaries.length!==PLANNED_BOUNDARIES.length||new Set(report.boundaries.map(row=>row.id)).size!==PLANNED_BOUNDARIES.length)report.setupErrors.push({classification:'BOUNDARY_PLAN',message:'Duplicate or unexpected boundary entries'});
 const executed=report.flows.filter(x=>['PASS','FAIL'].includes(x.status)).length;
 report.summary={planned:6,executed,passed:report.flows.filter(x=>x.status==='PASS').length,failed:report.flows.filter(x=>x.status==='FAIL').length,notRun:6-executed,boundaryPassed:report.boundaries.filter(x=>x.status==='PASS').length,boundaryFailed:report.boundaries.filter(x=>x.status==='FAIL').length,boundaryNotRun:report.boundaries.filter(x=>x.status==='NOT_RUN').length,setupErrors:report.setupErrors.length};
 const failed=report.summary.failed||report.summary.boundaryFailed||report.blockedLive.length||report.blockedExternal.length||report.guard?.paidAnalyzerInvocations||report.guard?.externalConnectionsBlocked||report.consoleErrors.some(row=>row.kind==='pageerror');
 const blocked=report.setupErrors.length||report.summary.notRun||report.summary.boundaryNotRun||!report.guard;
 report.status=failed?'FAIL':blocked?'NOT_RUN':'PASS';await persist();console.log(JSON.stringify({status:report.status,...report.summary}));process.exitCode=failed?1:blocked?2:0;
}
