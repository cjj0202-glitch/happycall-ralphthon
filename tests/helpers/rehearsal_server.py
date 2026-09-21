"""Isolated no-cost rehearsal host; never a replacement for the running demo API.

Existing OpenAPI handlers and business service run unchanged. Only runtime storage,
health-key readiness and the paid analyzer are injected test boundaries. No control
or synthetic-success endpoint is exposed. Four fresh stores share one loaded release.
"""
from __future__ import annotations

import argparse
import asyncio
from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def deny_external_and_secrets(event, args):
    if event == "open" and isinstance(args[0], (str, bytes)):
        name = Path(str(args[0])).name.lower()
        if name.startswith(".env") or name in {"demo-usage.json", "cases-store.json"} and str(ROOT / ".local").lower() in str(args[0]).lower():
            raise RuntimeError("Rehearsal cannot access secrets or existing local ledgers")
    if event == "socket.connect":
        address = args[1]
        if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
            raise RuntimeError("External network forbidden in rehearsal")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--port", type=int, default=8821)
    args = parser.parse_args()
    sys.addaudithook(deny_external_and_secrets)
    from scripts.build_deployment_bundle import _output_files, _verified_stamp, source_fingerprint
    output = _output_files(ROOT)
    stamp = _verified_stamp(ROOT, output)
    backend_hashes = {p.relative_to(ROOT).as_posix(): digest(p) for p in (ROOT / "server").glob("*.py")}
    backend_hashes["server/openapi.yaml"] = digest(ROOT / "server/openapi.yaml")

    import uvicorn
    from connexion import AsyncApp
    from server import handlers, runtime_config
    from server.deployment_app import DeploymentRouter
    from server.errors import DemoError
    from server.repository import JsonCaseRepository
    from server.service import CaseService

    class NoPaidAnalyzer:
        def analyze(self, *unused):
            raise DemoError("REHEARSAL_LIVE_DISABLED", "격리 리허설은 저장된 분석만 사용합니다.", 503)

    def no_key_read(*unused):
        raise DemoError("REHEARSAL_LIVE_DISABLED", "격리 리허설에서 키를 읽지 않습니다.", 503)

    runtime_config.require_demo_api_key = no_key_read
    current_runtime = ContextVar("rehearsal_runtime")
    handlers.get_runtime_storage = lambda: current_runtime.get()

    class ScopedRuntime:
        def __init__(self, app, runtime):
            self.app, self.runtime = app, runtime

        async def __call__(self, scope, receive, send):
            token = current_runtime.set(self.runtime)
            try:
                await self.app(scope, receive, send)
            finally:
                current_runtime.reset(token)

    with tempfile.TemporaryDirectory(prefix="oneflow-rehearsal-") as temporary:
        root = Path(temporary)
        static = root / "static"
        for relative, content in output.items():
            dest = static / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
        fixture = root / "fixture.json"
        shutil.copyfile(ROOT / "data/fixtures/cases.json", fixture)
        assert source_fingerprint(ROOT) == stamp["sourceAfter"]
        assert all(digest(ROOT / name) == value for name, value in backend_hashes.items()), "Backend changed while importing"
        servers = []
        for offset in range(4):
            repo = JsonCaseRepository(root / f"round-{offset + 1}" / "cases.json", fixture)
            repo.list()
            runtime = SimpleNamespace(backend="local-json", service=CaseService(repo, NoPaidAnalyzer()),
                                      check_ready=lambda: {"mode": "no-budget-ledger", "paidCalls": 0})
            api = AsyncApp(__name__ + str(offset), specification_dir=str(ROOT / "server"))
            api.add_api("openapi.yaml", strict_validation=True, validate_responses=True)
            app = ScopedRuntime(DeploymentRouter(api, static), runtime)
            servers.append(uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=args.port + offset,
                                                        log_level="warning", access_log=False, lifespan="off")))
        metadata = {"startedAt": datetime.now(timezone.utc).isoformat(), "pid": __import__("os").getpid(),
                    "ports": list(range(args.port, args.port + 4)), "buildStamp": stamp,
                    "backendHashes": backend_hashes, "fixtureSha256": digest(fixture),
                    "mediaHashes": {p: hashlib.sha256(b).hexdigest() for p, b in output.items() if p.startswith("demo/")},
                    "staticSnapshot": str(static), "temporaryStateRoot": str(root),
                    "mode": "isolated-replay-only", "existingProcessesTouched": False,
                    "keyReads": 0, "paidCalls": 0, "budgetLedgerCreated": False}
        Path(args.metadata).write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        print("REHEARSAL_METADATA_READY", flush=True)
        await asyncio.gather(*(server.serve() for server in servers))


if __name__ == "__main__":
    asyncio.run(main())
