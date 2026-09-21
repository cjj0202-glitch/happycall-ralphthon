"""One loopback product host: real handlers/service, isolated replay state only."""
from __future__ import annotations
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
from types import SimpleNamespace


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--product-root', type=Path, required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    args = parser.parse_args()
    root = args.product_root.resolve()
    sys.path.insert(0, str(root))
    counts = {'paidAttempts': 0, 'keyReadAttempts': 0, 'externalAttempts': 0}
    metadata = {'startedAt': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(),
                'productRoot': str(root), 'mode': 'real-product-isolated-replay',
                'existingProcessesTouched': False, 'counts': counts}
    def save():
        args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    def audit(event, values):
        if event == 'open' and isinstance(values[0], (str, bytes)):
            name = Path(str(values[0])).name.lower()
            if name.startswith('.env'):
                counts['keyReadAttempts'] += 1; save()
                raise RuntimeError('Secret file access forbidden in M3')
        if event == 'socket.connect':
            address = values[1]
            if isinstance(address, tuple) and address[0] not in {'127.0.0.1', '::1', 'localhost'}:
                counts['externalAttempts'] += 1; save()
                raise RuntimeError('External connection forbidden in M3')
    sys.addaudithook(audit)
    from scripts.build_deployment_bundle import _output_files, _verified_stamp, source_fingerprint
    output = _output_files(root)
    stamp = _verified_stamp(root, output)
    import uvicorn
    from connexion import AsyncApp
    from server import handlers, runtime_config
    from server.deployment_app import DeploymentRouter
    from server.errors import DemoError
    from server.repository import JsonCaseRepository
    from server.service import CaseService
    class NoPaidAnalyzer:
        def analyze(self, *unused):
            counts['paidAttempts'] += 1; save()
            raise DemoError('M3_LIVE_DISABLED', 'M3 검수는 replay만 사용합니다.', 503)
    def no_key(*unused):
        counts['keyReadAttempts'] += 1; save()
        raise DemoError('M3_LIVE_DISABLED', 'M3 검수는 키를 읽지 않습니다.', 503)
    runtime_config.require_demo_api_key = no_key
    args.state_dir.mkdir(parents=True, exist_ok=False)
    static = args.state_dir/'static'
    for relative, content in output.items():
        dest = static/relative; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(content)
    fixture = args.state_dir/'fixture.json'; fixture.write_bytes((root/'data/fixtures/cases.json').read_bytes())
    repo = JsonCaseRepository(args.state_dir/'cases.json', fixture); repo.list()
    runtime = SimpleNamespace(backend='local-json', service=CaseService(repo, NoPaidAnalyzer()),
                              check_ready=lambda: {'mode': 'no-budget-ledger', 'paidCalls': 0})
    handlers.get_runtime_storage = lambda: runtime
    api = AsyncApp(__name__, specification_dir=str(root/'server'))
    api.add_api('openapi.yaml', strict_validation=True, validate_responses=True)
    app = DeploymentRouter(api, static)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 0)); listener.listen(128)
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port,
                           log_level='warning', access_log=False, lifespan='off',
                           timeout_keep_alive=1, timeout_graceful_shutdown=2))
    assert source_fingerprint(root) == stamp['sourceAfter']
    metadata.update(port=port, host='127.0.0.1', base=f'http://127.0.0.1:{port}', buildStamp=stamp,
                    mediaHashes={p: hashlib.sha256(b).hexdigest() for p,b in output.items() if p.startswith('demo/')},
                    stateDir=str(args.state_dir), statePreserved=True)
    save(); print('M3_HOST_READY', flush=True)
    async def stop_from_stdin():
        await asyncio.to_thread(sys.stdin.readline)
        metadata['shutdownRequestedAt'] = datetime.now(timezone.utc).isoformat(); save()
        server.should_exit = True
    stopper = asyncio.create_task(stop_from_stdin())
    try:
        await server.serve(sockets=[listener])
    finally:
        listener.close(); stopper.cancel()
        metadata.update(stoppedAt=datetime.now(timezone.utc).isoformat(), stopped=True)
        save()


if __name__ == '__main__':
    if sys.platform == 'win32':
        # Local host only: avoid Proactor pipe callbacks on intentionally cancelled media requests.
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
