"""Own isolated replay API/UI processes for pc4; never read demo keys or live ledgers."""
from __future__ import annotations
import argparse, contextlib, hashlib, json, os, socket, subprocess, sys, tempfile, threading, time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def sources():
    paths = list((ROOT / 'server').glob('*.py')) + list((ROOT / 'apps/web/app').glob('*'))
    paths += list((ROOT / 'apps/web/lib').glob('*'))
    paths += [ROOT / x for x in ('apps/web/components/LogisticsView.tsx', 'apps/web/components/LogisticsView.module.css', 'server/openapi.yaml', 'data/fixtures/cases.json', 'apps/web/package-lock.json', 'tests/e2e/package-lock.json')]
    return {str(p.relative_to(ROOT)).replace('\\','/'):digest(p) for p in sorted(paths) if p.is_file()}

class NeverLive:
    attempts = 0
    def analyze(self, *_args, **_kwargs):
        self.attempts += 1
        raise AssertionError('Paid analyzer forbidden in isolated pc4 UI suite')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api-port', type=int, default=18105)
    parser.add_argument('--ui-port', type=int, default=13105)
    parser.add_argument('--only', default='all')
    args=parser.parse_args()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=ROOT/'reports/pc4'/f'ui-flow-{stamp}'
    out.mkdir(parents=True, exist_ok=False)
    logs=ROOT/'.local'/f'ui-flow-{stamp}'
    logs.mkdir(parents=True, exist_ok=False)
    shared=[ROOT/'.local/cases-store.json',ROOT/'.local/demo-usage.json']
    original={str(p):digest(p) for p in shared}
    report={'startedAt':datetime.now(timezone.utc).isoformat(), 'hostname':socket.gethostname(), 'mode':'replay', 'kind':'AI Playwright technical observation; not human usability', 'apiPort':args.api_port, 'uiPort':args.ui_port, 'headStart':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(), 'sourceHashesStart':sources(), 'originalStateBefore':original, 'out':str(out), 'logs':str(logs), 'newTmsIntegrated':False}
    never=NeverLive(); holder={}; server=None; thread=None; owned_web=None; web_log=None; result_code=1
    external=[]; reset_ids=[]
    def checked_connect(method):
        def guarded(sock,address):
            if sock.family in (socket.AF_INET,socket.AF_INET6) and address[0] not in ('127.0.0.1','::1','localhost'):
                external.append(str(address[0])); raise RuntimeError('External network blocked by test guard')
            return method(sock,address)
        return guarded
    try:
        if list((ROOT/'apps/web').glob('.env*')):
            raise RuntimeError('Existing Next .env files require separate handling; refusing to read them')
        for port in (args.api_port,args.ui_port):
            with socket.socket() as probe:
                if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):probe.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
                probe.bind(('127.0.0.1',port))
        from server.repository import JsonCaseRepository
        from server.service import CaseService
        from server.app import create_app
        import uvicorn
        with tempfile.TemporaryDirectory(prefix='pc4-ui-replay-') as temporary, contextlib.ExitStack() as stack:
            temp=Path(temporary)
            report['temporaryStoreRoot']=str(temp)
            stack.enter_context(patch.dict(os.environ, {'ONEFLOW_CORS_ORIGINS':f'http://127.0.0.1:{args.ui_port}'}))
            stack.enter_context(patch('server.handlers.service', side_effect=lambda:holder['service']))
            stack.enter_context(patch('server.runtime_config.read_demo_env',return_value={}))
            stack.enter_context(patch.object(socket.socket,'connect',checked_connect(socket.socket.connect)))
            stack.enter_context(patch.object(socket.socket,'connect_ex',checked_connect(socket.socket.connect_ex)))
            product=create_app()
            async def harness(scope,receive,send):
                path=scope.get('path','')
                if scope['type']=='http' and path.startswith('/__pc4/'):
                    status=200
                    if path=='/__pc4/reset' and scope['method']=='POST':
                        label=f'run-{len(reset_ids)+1:02d}'
                        holder['service']=CaseService(JsonCaseRepository(temp/label/'cases.json'),never)
                        reset_ids.append(label)
                        body={'store':label,'scope':'setup only; new isolated state, existing state never reset'}
                    elif path=='/__pc4/status':
                        body={'ready':True,'paidAnalyzerInvocations':never.attempts,'externalConnectionsBlocked':len(external),'stores':reset_ids}
                    else:status=404;body={'error':'test endpoint not found'}
                    await send({'type':'http.response.start','status':status,'headers':[(b'content-type',b'application/json')]})
                    await send({'type':'http.response.body','body':json.dumps(body).encode()});return
                if scope['type']=='http' and path=='/api/health':
                    await send({'type':'http.response.start','status':503,'headers':[(b'content-type',b'application/json')]})
                    await send({'type':'http.response.body','body':b'{"error":"health excluded to preserve actual budget ledger"}'});return
                await product(scope,receive,send)
            holder['service']=CaseService(JsonCaseRepository(temp/'initial/cases.json'),never)
            config=uvicorn.Config(harness,host='127.0.0.1',port=args.api_port,access_log=False,log_level='error',lifespan='off')
            server=uvicorn.Server(config)
            thread=threading.Thread(target=server.run,daemon=True);thread.start()
            deadline=time.monotonic()+20
            while not server.started and time.monotonic()<deadline:time.sleep(.1)
            if not server.started:raise RuntimeError('Own isolated API failed to start')
            node=Path(os.environ.get('USERPROFILE',''))/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
            browser=ROOT.parent/'.happycall-tools/playwright/chromium-1208/chrome-win64/chrome.exe'
            env={k:v for k,v in os.environ.items() if not any(k.upper().startswith(p) for p in ('OPENAI','ONEFLOW','VERCEL','BLOB','DEMO_'))}
            env.update(NEXT_PUBLIC_API_BASE=f'http://127.0.0.1:{args.api_port}',NEXT_TELEMETRY_DISABLED='1', E2E_CHROMIUM=str(browser),PC4_UI_BASE=f'http://127.0.0.1:{args.ui_port}',PC4_API_BASE=f'http://127.0.0.1:{args.api_port}',PC4_UI_OUT=str(out),PC4_UI_ONLY=args.only)
            command=[str(node),str(ROOT/'apps/web/node_modules/next/dist/bin/next'),'dev','--hostname','127.0.0.1','--port',str(args.ui_port)]
            web_log=(logs/'next.log').open('w',encoding='utf-8')
            owned_web=subprocess.Popen(command,cwd=ROOT/'apps/web',env=env,stdout=web_log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            report['ownedWeb']={'pid':owned_web.pid,'command':command}
            with (logs/'browser-suite.log').open('w',encoding='utf-8') as browser_log:
                result=subprocess.run([str(node),str(ROOT/'tests/remote/pc4/flow-ui-check.mjs')],cwd=ROOT,env=env,stdout=browser_log,stderr=subprocess.STDOUT,timeout=1100,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            result_code=result.returncode
            report['browserExitCode']=result_code
            report['temporaryStores']=reset_ids
            report['temporaryFinalStates']={str(p.relative_to(temp)):json.loads(p.read_text(encoding='utf-8')) for p in temp.glob('*/cases.json')}
    except Exception as error:
        report['fatal']={'type':type(error).__name__,'message':str(error)}
    finally:
        if owned_web and owned_web.poll() is None:
            # This Popen handle identifies our fresh Next parent. Its descendants only.
            stopped=subprocess.run(['taskkill.exe','/PID',str(owned_web.pid),'/T','/F'],capture_output=True,text=True)
            report['ownedWebCleanupExitCode']=stopped.returncode
        if server:server.should_exit=True
        if thread:thread.join(timeout=10)
        if web_log:web_log.close()
        report.update(finishedAt=datetime.now(timezone.utc).isoformat(),paidAnalyzerInvocations=never.attempts,blockedExternalConnections=external,headEnd=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),sourceHashesEnd=sources(),originalStateAfter={str(p):digest(p) for p in shared},apiStopped=not thread or not thread.is_alive())
        report['sameSource']=report['headStart']==report['headEnd'] and report['sourceHashesStart']==report['sourceHashesEnd']
        report['originalStatePreserved']=report['originalStateBefore']==report['originalStateAfter']
        (out/'harness.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'out':str(out),'browserExitCode':result_code,'fatal':report.get('fatal'),'paidCalls':never.attempts,'sameSource':report['sameSource'],'originalStatePreserved':report['originalStatePreserved']},ensure_ascii=False))
    return result_code

if __name__=='__main__':raise SystemExit(main())
