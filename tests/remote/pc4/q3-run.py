"""Prepare by default. Execute only a declared, verified final production export.

No pull/build/install/deploy occurs here. A separate clean checkout at finalSha
must already hold a verified same-origin Next export and approved synthetic media.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from q2_contract import git, inspect_release, inventory, required_inputs, sha

TEST_ROOT = Path(__file__).resolve().parents[3]


def aggregate_guard(report, browser):
    failures = []
    for key in ('sameSource', 'sameBuild', 'sameTester', 'originalStatePreserved', 'apiStopped'):
        if report.get(key) is not True: failures.append(key)
    if report.get('paidAnalyzerInvocations') != 0 or report.get('blockedExternalConnections'):
        failures.append('COST_OR_NETWORK_GUARD')
    if report.get('fatal') or report.get('browserExitCode') != 0: failures.append('SETUP_OR_BROWSER_FAILED')
    if not browser or browser.get('status') != 'PASS' or browser.get('setupErrors'):
        failures.append('BROWSER_NOT_PASS')
    else:
        axes = browser.get('axes', [])
        expected = {f'Q3-{i:02}' for i in range(1, 9)}
        if len(axes) != 8 or {a.get('id') for a in axes} != expected or any(a.get('status') != 'PASS' for a in axes):
            failures.append('EIGHT_UNIQUE_AXES_REQUIRED')
        stores = [a.get('store', {}).get('store') for a in axes]
        if len(set(stores)) != 8 or any(not s for s in stores): failures.append('EIGHT_FRESH_STORES_REQUIRED')
        if any(not a.get('checks') for a in axes): failures.append('AXIS_OBSERVATIONS_MISSING')
        guard = browser.get('guard', {}) or {}
        identity = report.get('identity', {})
        if not identity or any(guard.get(k) != v for k, v in identity.items()) or guard.get('ready') is not True:
            failures.append('IDENTITY_MISMATCH')
        if guard.get('paidAnalyzerInvocations') != 0 or guard.get('externalConnectionsBlocked') != 0:
            failures.append('RUNNER_COST_OR_NETWORK')
        if browser.get('external') or browser.get('analysisRequests') or browser.get('pageErrors'):
            failures.append('BROWSER_NETWORK_OR_PAGEERROR')
    return failures



def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return sha(path.read_bytes()) if path.is_file() else None


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def prepare(contract, output):
    result = {'preparedAt': now(), 'task': 'N04-Q3', 'status': 'PREPARED_NOT_RUN',
              'finalInputBlockers': required_inputs(contract), 'productExecutions': 0,
              'axes': {'planned': 8, 'executed': 0, 'passed': 0, 'notRun': 8},
              'boundaryExecutions': 0, 'paidCalls': 0,
              'note': 'Schema readiness is not module integration, browser execution or acceptance.'}
    write(output, result)
    print(json.dumps(result, ensure_ascii=False))
    return 0


def execute(args, contract):
    product = args.product_root.resolve(strict=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = TEST_ROOT / 'reports/pc4' / ('q3-run-' + stamp)
    logs = TEST_ROOT / '.local' / ('q3-run-' + stamp)
    out.mkdir(parents=True, exist_ok=False)
    logs.mkdir(parents=True, exist_ok=False)
    report = {'startedAt': now(), 'task': 'N04-Q3', 'status': 'NOT_RUN',
              'productRoot': str(product), 'testerHead': git(TEST_ROOT, 'rev-parse', 'HEAD'),
              'runnerHashes': {p.name: digest(p) for p in list(Path(__file__).parent.glob('*.py')) + list(Path(__file__).parent.glob('q3-*.mjs'))},
              'checkerHash': digest(Path(__file__).with_name('q3-check.mjs')),
              'pythonVersion': sys.version, 'pythonExecutable': sys.executable,
              'paidAnalyzerInvocations': 0, 'blockedExternalConnections': [],
              'sameSource': False, 'sameBuild': False, 'sameTester': False, 'originalStatePreserved': False,
              'apiStopped': True, 'browserExitCode': None, 'productExecutions': 0}
    sources = out / 'tester-source'
    sources.mkdir()
    for name, expected in report['runnerHashes'].items():
        content = (Path(__file__).parent / name).read_bytes()
        if sha(content) != expected: raise RuntimeError('Tester changed during source archival')
        (sources / name).write_bytes(content)
    original_paths = [product / '.local/cases-store.json', product / '.local/demo-usage.json']
    original = {str(p): digest(p) for p in original_paths}
    report['originalStateBefore'] = original
    server = thread = browser_process = None
    read_only_files = {}
    browser_result = None
    paid = []
    stores = []
    owned = None
    stack = contextlib.ExitStack()
    product_running = [False]
    def deny_sensitive_reads(event, values):
        if product_running[0] and event == 'open' and isinstance(values[0], (str, bytes)):
            path = Path(os.fsdecode(values[0]))
            if path.name.lower().startswith('.env') or path.resolve() in original_paths:
                raise RuntimeError('PC4 product execution cannot open local secrets or original ledgers')
    sys.addaudithook(deny_sensitive_reads)
    class NeverLive:
        def analyze(self, *_a, **_kw):
            paid.append(now())
            raise RuntimeError('PC4 paid analyzer forbidden')
    def connect_guard(method):
        def guarded(sock, address):
            if sock.family in (socket.AF_INET, socket.AF_INET6) and address[0] not in ('127.0.0.1', '::1', 'localhost'):
                report['blockedExternalConnections'].append(str(address[0]))
                raise RuntimeError('PC4 external network forbidden')
            return method(sock, address)
        return guarded
    try:
        evidence, output = inspect_release(product, contract)
        report['releaseStart'] = evidence
        parsed = urllib.parse.urlsplit(contract['targetUrl'])
        port = parsed.port
        with socket.socket() as probe:
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            probe.bind(('127.0.0.1', port))
        node = Path(shutil.which('node') or '')
        chromium = Path(os.environ.get('E2E_CHROMIUM', ''))
        if not node.is_file() or not chromium.is_file():
            raise RuntimeError('Explicit installed Node and E2E_CHROMIUM paths required')
        report['nodeVersion'] = subprocess.check_output([str(node), '--version'], text=True).strip()
        report['nodeExecutable'] = str(node)
        report['chromiumExecutable'] = str(chromium)
        with chromium.open('rb') as stream:
            report['chromiumExecutableSha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
        package = TEST_ROOT / 'tests/e2e/node_modules/playwright/package.json'
        report['playwrightVersion'] = json.loads(package.read_text(encoding='utf-8'))['version']
        product_running[0] = True
        sys.path.insert(0, str(product))
        from server.repository import JsonCaseRepository
        from server.service import CaseService
        from server.app import create_app
        from starlette.staticfiles import StaticFiles
        import uvicorn
        holder = {}
        owned = Path(tempfile.mkdtemp(prefix='pc4-q3-'))
        report['ownedTemporaryRoot'] = str(owned)
        static = owned / 'static'
        static.mkdir()
        for name, content in output.items():
            target = static / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        read_only_files = {str(static / n): sha(b) for n, b in output.items()}
        fixture_snapshot = owned / 'fixture.json'
        fixture_snapshot.write_bytes(output['cases.json'])
        read_only_files[str(fixture_snapshot)] = sha(output['cases.json'])
        identity = {'runNonce': secrets.token_hex(16), 'finalSha': contract['finalSha'],
                    'buildFingerprint': contract['frontendOutputFingerprint']}
        report['identity'] = identity
        caps = dict(contract['capabilities'])
        caps.update(callReviewIntegrated=True, newTmsIntegrated=True)
        caps_path = out / 'capabilities.json'
        write(caps_path, caps)
        # Keep isolation patches until both the browser and server are stopped.
        # nullcontext deliberately does not close the ExitStack on an exception.
        with contextlib.nullcontext(stack):
            stack.enter_context(patch.dict(os.environ, {'ONEFLOW_CORS_ORIGINS': contract['targetUrl']}))
            stack.enter_context(patch('server.handlers.service', side_effect=lambda: holder['service']))
            stack.enter_context(patch('server.runtime_config.read_demo_env', return_value={}))
            stack.enter_context(patch.object(socket.socket, 'connect', connect_guard(socket.socket.connect)))
            stack.enter_context(patch.object(socket.socket, 'connect_ex', connect_guard(socket.socket.connect_ex)))
            app = create_app()
            static_app = StaticFiles(directory=static, html=True)
            def new_store():
                label = 'run-' + str(len(stores) + 1).zfill(2)
                holder['service'] = CaseService(JsonCaseRepository(owned / label / 'cases.json', fixture_snapshot), NeverLive())
                stores.append(label)
                return label
            new_store()
            async def harness(scope, receive, send):
                path = scope.get('path', '')
                if scope['type'] == 'http' and path.startswith('/__pc4/'):
                    status = 200
                    if path == '/__pc4/reset' and scope['method'] == 'POST':
                        body = {'store': new_store(), 'scope': 'new isolated test state only'}
                    elif path == '/__pc4/status':
                        body = dict(identity, ready=True, paidAnalyzerInvocations=len(paid),
                                    externalConnectionsBlocked=len(report['blockedExternalConnections']), stores=stores)
                    else:
                        status, body = 404, {'error': 'No such test endpoint'}
                    await send({'type': 'http.response.start', 'status': status, 'headers': [(b'content-type', b'application/json')]})
                    await send({'type': 'http.response.body', 'body': json.dumps(body).encode()})
                    return
                if path == '/api/health':
                    await send({'type': 'http.response.start', 'status': 503, 'headers': [(b'content-type', b'application/json')]})
                    await send({'type': 'http.response.body', 'body': b'{"error":"PC4 health key and budget reads excluded"}'})
                    return
                await (app if path.startswith('/api/') else static_app)(scope, receive, send)
            server = uvicorn.Server(uvicorn.Config(harness, host='127.0.0.1', port=port, access_log=False, log_level='error', lifespan='off'))
            thread = threading.Thread(target=server.run, daemon=True)
            thread.start()
            deadline = time.monotonic() + 20
            while not server.started and time.monotonic() < deadline:
                time.sleep(.1)
            if not server.started:
                raise RuntimeError('Own isolated production host failed to start')
            report['ownedServer'] = {'pid': os.getpid(), 'thread': thread.name, 'port': port}
            with urllib.request.urlopen(contract['targetUrl'] + '/__pc4/status', timeout=10) as response:
                observed = json.load(response)
            if any(observed.get(k) != v for k, v in identity.items()):
                raise RuntimeError('Run identity mismatch; refusing browser execution')
            report['httpAssetChecks'] = []
            for asset in contract['assets']:
                url = contract['targetUrl'] + '/' + asset['path']
                with urllib.request.urlopen(url, timeout=20) as response:
                    blob = response.read()
                    if response.geturl() != url or sha(blob) != asset['sha256'] or len(blob) != asset['bytes']:
                        raise RuntimeError('HTTP asset bytes or URL mismatch')
                request = urllib.request.Request(url, headers={'Range': 'bytes=0-31'})
                with urllib.request.urlopen(request, timeout=10) as response:
                    part = response.read()
                    expected_range = f'bytes 0-31/{asset["bytes"]}'
                    if response.status != 206 or response.headers.get('Content-Range') != expected_range or part != blob[:32]:
                        raise RuntimeError('HTTP Range/206 mismatch')
                report['httpAssetChecks'].append({'path': asset['path'], 'sha256': sha(blob), 'range206': True})
            env = {k: v for k, v in os.environ.items() if not k.upper().startswith(('OPENAI', 'ONEFLOW', 'VERCEL', 'BLOB', 'DEMO_'))}
            env.update(PC4_UI_BASE=contract['targetUrl'], PC4_API_BASE=contract['targetUrl'], PC4_UI_OUT=str(out),
                       PC4_Q2_FINAL_SHA=contract['finalSha'], PC4_Q2_CAPABILITIES=str(caps_path),
                       PC4_Q2_RUN_IDENTITY=json.dumps(identity), PC4_UI_ONLY='all')
            command = [str(node), str(Path(__file__).with_name('q3-check.mjs'))]
            report['productExecutions'] = 1
            with (logs / 'browser.log').open('w', encoding='utf-8') as log:
                browser_process = subprocess.Popen(command, cwd=product, env=env, stdout=log, stderr=subprocess.STDOUT,
                                                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                report['browserExitCode'] = browser_process.wait(timeout=1800)
            result_path = out / 'results.json'
            if result_path.is_file():
                browser_result = json.loads(result_path.read_text(encoding='utf-8'))
    except Exception as error:
        report['fatal'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        if browser_process and browser_process.poll() is None:
            # Only our fresh Popen child and its browser descendants, never existing servers/watchers.
            cleanup = subprocess.run(['taskkill.exe', '/PID', str(browser_process.pid), '/T', '/F'], capture_output=True)
            report['ownedBrowserCleanupExitCode'] = cleanup.returncode
        if server:
            server.should_exit = True
        if thread:
            thread.join(timeout=10)
        report['apiStopped'] = not thread or not thread.is_alive()
        if report['apiStopped']:
            stack.close()
            product_running[0] = False
        # If the daemon thread cannot stop, preserve isolation until this runner
        # exits. Never reopen real service/key/network access to a running server.
        report['paidAnalyzerInvocations'] = len(paid)
        report['originalStateAfter'] = {str(p): digest(p) for p in original_paths} if report['apiStopped'] else None
        report['originalStatePreserved'] = report['originalStateAfter'] == original
        report['sameBuild'] = bool(read_only_files) and all(digest(Path(n)) == h for n, h in read_only_files.items())
        report['runnerHashesEnd'] = {p.name: digest(p) for p in list(Path(__file__).parent.glob('*.py')) + list(Path(__file__).parent.glob('q3-*.mjs'))}
        report['checkerHashEnd'] = digest(Path(__file__).with_name('q3-check.mjs'))
        report['sameTester'] = report['runnerHashesEnd'] == report['runnerHashes'] and report['checkerHashEnd'] == report['checkerHash']
        try:
            end, unused = inspect_release(product, contract)
            report['releaseEnd'] = end
            report['sameSource'] = end == report.get('releaseStart')
        except Exception as error:
            report['releaseEndError'] = str(error)
        report['guardFailures'] = aggregate_guard(report, browser_result)
        report['status'] = 'PASS' if not report['guardFailures'] else ('NOT_RUN' if report['productExecutions'] == 0 else 'FAIL')
        report['finishedAt'] = now()
        report['temporaryStateHashes'] = {p.relative_to(owned).as_posix(): digest(p) for p in owned.glob('run-*/cases.json')} if owned else {}
        # Preserve synthetic state for independent review; no recursive cleanup is attempted.
        report['temporaryFilesPreserved'] = bool(owned)
        write(out / 'harness.json', report)
        print(json.dumps({'out': str(out), 'status': report['status'], 'guardFailures': report['guardFailures'], 'fatal': report.get('fatal')}, ensure_ascii=False))
    return 0 if report['status'] == 'PASS' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-contract', type=Path, default=Path(__file__).with_name('q2-release.template.json'))
    parser.add_argument('--product-root', type=Path)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--output', type=Path, default=TEST_ROOT / 'reports/pc4/q3-preparation.json')
    args = parser.parse_args()
    contract = json.loads(args.release_contract.read_text(encoding='utf-8-sig'))
    if not args.execute or args.prepare_only:
        return prepare(contract, args.output)
    if not args.product_root:
        parser.error('--execute requires an explicit separate --product-root at the final SHA')
    return execute(args, contract)


if __name__ == '__main__':
    raise SystemExit(main())
