import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {spawn,execFileSync} from 'node:child_process';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {runChecks} from './checker.mjs';

const HERE=path.dirname(fileURLToPath(import.meta.url));
const ROOT=path.resolve(HERE,'../../../..');
const PRODUCT=path.resolve(process.argv[2]||path.join(ROOT,'../.local/pc2-m3-product'));
const PYTHON=process.env.M3_PYTHON;
const DEPS=process.env.M3_PYTHON_DEPS;
assert.ok(PYTHON&&DEPS,'Set M3_PYTHON and M3_PYTHON_DEPS to verified installed paths');
const require=createRequire(path.join(ROOT,'tests/e2e/package.json'));
const {chromium}=require('playwright');
const sha=b=>createHash('sha256').update(b).digest('hex');
const stamp=new Date().toISOString().replace(/[:.]/g,'-');
const OUT=path.join(ROOT,'reports/pc2/audio-m3',`parent-${stamp}`);
const STATE=path.join(ROOT,'.local/pc2-m3-states',stamp);
await mkdir(OUT,{recursive:true});
const git=(...a)=>execFileSync('git',a,{cwd:PRODUCT,encoding:'utf8'}).trim();
const files=git('ls-files','server','apps/web','data','scripts/build_deployment_bundle.py').split(/\r?\n/).filter(Boolean);
async function hashes(){return Object.fromEntries(await Promise.all(files.map(async n=>[n,sha(await readFile(path.join(PRODUCT,n)))])));}
const execution={started:new Date().toISOString(),productRoot:PRODUCT,productCommit:git('rev-parse','HEAD'),
  node:process.version,python:PYTHON,pythonDeps:DEPS,browserControl:'Playwright pipe, one Edge browser',
  sourceBefore:await hashes(),checkerSources:{},cleanup:[]};
assert.equal(execution.productCommit,'92d2ecbad981f366a9e5ffc850d9c2bb7fd5d3a2');
assert.equal(git('status','--porcelain'),'','Product checkout must be clean');
for(const name of ['checker.mjs','host.py','run.mjs']){
  const raw=await readFile(path.join(HERE,name));execution.checkerSources[name]={bytes:raw.length,sha256:sha(raw)};
  await writeFile(path.join(OUT,`source-${name}`),raw);
}
const build=await readFile(path.join(PRODUCT,'apps/web/out/.oneflow-build.json'));
await writeFile(path.join(OUT,'build-stamp.json'),build);
const save=()=>writeFile(path.join(OUT,'execution.json'),JSON.stringify(execution,null,2)+'\n');
await save();
const allowed=['PATH','SystemRoot','WINDIR','TEMP','TMP','USERPROFILE','LOCALAPPDATA'];
const env=Object.fromEntries(allowed.filter(k=>process.env[k]).map(k=>[k,process.env[k]]));
let browser,server,report,exitPromise,serverText='';
try{
  server=spawn(PYTHON,[path.join(HERE,'host.py'),'--product-root',PRODUCT,'--state-dir',STATE,'--metadata',path.join(OUT,'server.json')],
    {cwd:PRODUCT,env:{...env,PYTHONPATH:DEPS,PYTHONUTF8:'1',PYTHONDONTWRITEBYTECODE:'1'},windowsHide:true,stdio:['pipe','pipe','pipe']});
  execution.serverPid=server.pid;
  exitPromise=new Promise(resolve=>server.once('exit',(code,signal)=>resolve({code,signal})));
  const ready=new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(new Error('M3 host readiness timeout')),60000);
    const output=b=>{serverText+=b.toString();if(serverText.includes('M3_HOST_READY')){clearTimeout(timer);resolve();}};
    server.stdout.on('data',output);server.stderr.on('data',output);
    server.once('error',e=>{clearTimeout(timer);reject(e);});server.once('exit',code=>{clearTimeout(timer);reject(new Error(`M3 host exited ${code}`));});
  });
  await ready;
  const meta=JSON.parse(await readFile(path.join(OUT,'server.json'),'utf8'));execution.serverAddress={host:meta.host,port:meta.port};
  for(let i=0;i<50;i++){
    try{const r=await fetch(meta.base+'/api/cases');if(r.ok)break;if(i===49)throw new Error(`HTTP ${r.status}`);}catch(e){if(i===49)throw e;}
    await new Promise(resolve=>setTimeout(resolve,100));
  }
  browser=await chromium.launch({channel:'msedge',headless:true});execution.browser=browser.version();await save();
  report=await runChecks({browser,base:meta.base,productRoot:PRODUCT,out:OUT});
}catch(e){execution.fatal=e.stack||String(e);console.log(`M3 RUNNER FATAL ${e.message}`);}
finally{
  if(browser){try{await browser.close();execution.cleanup.push({browser:'closed',disconnected:!browser.isConnected()});}catch(e){execution.cleanup.push({browser:'error',error:String(e)});}}
  if(server){
    if(server.exitCode===null){server.stdin.write('stop\n');server.stdin.end();}
    const result=await Promise.race([exitPromise,new Promise(resolve=>setTimeout(()=>resolve(null),8000))]);
    if(result)execution.cleanup.push({server:'exited',...result});
    else{server.kill();execution.cleanup.push({server:'own-child-terminated-after-timeout',...(await exitPromise)});}
  }
  execution.sourceAfter=await hashes();execution.productStatusAfter=git('status','--porcelain');
  execution.sourcesUnchanged=JSON.stringify(execution.sourceBefore)===JSON.stringify(execution.sourceAfter);
  if(!execution.sourcesUnchanged||execution.productStatusAfter)execution.integrityFailure=true;
  await writeFile(path.join(OUT,'server.log'),serverText);
  execution.finished=new Date().toISOString();execution.summary=report?.summary;await save();
  console.log(JSON.stringify({out:OUT,summary:report?.summary,fatal:execution.fatal||report?.fatal||null,cleanup:execution.cleanup,unchanged:execution.sourcesUnchanged}));
}
if(execution.fatal||execution.integrityFailure||report?.fatal||report?.summary.failed||report?.summary.passed!==14)process.exitCode=1;
