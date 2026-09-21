"""Independent, loopback HTTP scenario checks using only temporary replay state.

Does not count API workflows as six UI completions. Never launches/restarts any
existing runtime, loads .env files, or creates a paid-API budget ledger.
"""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
KIND = "independent loopback HTTP/OpenAPI scenarios; not UI or live AI"


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def git(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=15)
    if result.returncode:
        raise RuntimeError("Could not read Git source identity")
    return result.stdout.strip()


def source_hashes():
    paths = sorted((ROOT / "server").glob("*.py"))
    paths += [ROOT / "server/openapi.yaml", ROOT / "data/fixtures/cases.json"]
    return {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path) for path in paths}


def original_state_hashes():
    directories = {ROOT / ".local"}
    configured = os.environ.get("ONEFLOW_STATE_DIR")
    if configured and Path(configured).is_absolute():
        directories.add(Path(configured))
    return {str(folder / name): sha(folder / name) for folder in directories
            for name in ("cases-store.json", "demo-usage.json")}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


class NeverLive:
    attempts = 0

    def analyze(self, *_args, **_kwargs):
        self.attempts += 1
        raise AssertionError("Paid AI invocation forbidden in pc4 scenario checks")


class NetworkGuard:
    """Only this process's loopback traffic is allowed, including dependency code."""

    def __init__(self):
        self.blocked = 0

    @contextlib.contextmanager
    def active(self):
        original_connect = socket.socket.connect
        original_connect_ex = socket.socket.connect_ex

        def checked(method):
            def connect(sock, address):
                if sock.family in (socket.AF_INET, socket.AF_INET6):
                    if address[0] not in ("127.0.0.1", "::1", "localhost"):
                        self.blocked += 1
                        raise RuntimeError("External network forbidden by pc4 scenario guard")
                return method(sock, address)
            return connect

        with patch.object(socket.socket, "connect", checked(original_connect)), \
                patch.object(socket.socket, "connect_ex", checked(original_connect_ex)):
            yield


class FaultGate:
    """Test-only, one-request 503 injection before the real ASGI application."""

    def __init__(self, app):
        self.app = app
        self.fail_next = False

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and self.fail_next:
            self.fail_next = False
            body = json.dumps({"error": {"code": "PC4_INJECTED_UNAVAILABLE",
                                         "message": "Test-only temporary API failure"}}).encode()
            await send({"type": "http.response.start", "status": 503,
                        "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": body})
            return
        await self.app(scope, receive, send)


class OwnedServer:
    def __init__(self, port):
        import uvicorn
        from server.app import create_app
        self.port = port
        self.gate = FaultGate(create_app())
        self.uvicorn = uvicorn
        self.server = None
        self.thread = None
        self.socket = None

    def start(self):
        require(self.thread is None, "Test server already running")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # bind fails if another runtime already owns the port. Never stop it.
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            sock.bind(("127.0.0.1", self.port))
            sock.listen(128)
            config = self.uvicorn.Config(self.gate, host="127.0.0.1", port=self.port,
                                         log_level="error", access_log=False,
                                         lifespan="off", timeout_graceful_shutdown=3)
            self.server = self.uvicorn.Server(config)
            self.socket = sock
            self.thread = threading.Thread(target=self.server.run, kwargs={"sockets": [sock]}, daemon=True)
            self.thread.start()
            deadline = time.monotonic() + 10
            while not self.server.started and self.thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.02)
            require(self.server.started and self.thread.is_alive(), "Owned test server failed to start")
        except BaseException:
            sock.close()
            self.stop()
            raise

    def stop(self):
        if self.server:
            self.server.should_exit = True
        if self.thread:
            self.thread.join(timeout=5)
            require(not self.thread.is_alive(), "Owned test server did not stop cleanly")
        if self.socket:
            self.socket.close()
        self.thread = self.server = self.socket = None


class HTTP:
    def __init__(self, port):
        self.base = f"http://127.0.0.1:{port}"
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.requests = []

    def call(self, path, method="GET", body=None, role="counselor"):
        if body and method == "POST" and path.endswith("/analyze"):
            require(body.get("mode") == "replay", "Only explicit replay is allowed")
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method,
                                         headers={"Content-Type": "application/json", "X-Demo-Role": role})
        try:
            response = self.opener.open(request, timeout=8)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            raw = response.read()
            result = json.loads(raw) if raw else {}
            status = response.status
        self.requests.append({"method": method, "path": path, "role": role,
                              "status": status, "errorCode": result.get("error", {}).get("code"),
                              "sentRevision": body.get("expectedRevision") if isinstance(body, dict) else None,
                              "savedRevision": result.get("revision")})
        return status, result

    def get(self, case_id):
        status, result = self.call(f"/api/cases/{case_id}")
        require(status == 200, f"Read failed: HTTP {status}")
        return result

    def edit(self, snapshot, changes, role="counselor"):
        require("expectedRevision" not in changes, "Preserve the revision attached to the reviewed snapshot")
        return self.call(f"/api/cases/{snapshot['id']}", "PATCH",
                         {**changes, "expectedRevision": snapshot["revision"]}, role)

    def save(self, snapshot, changes, role="counselor"):
        status, result = self.edit(snapshot, changes, role)
        require(status == 200, f"Save expected 200, got {status}/{result.get('error', {}).get('code')}")
        require(result["revision"] == snapshot["revision"] + 1, "Revision must advance exactly once")
        return result

    def reject(self, snapshot, changes, status, code, role="counselor", omit_revision=False):
        before = self.get(snapshot["id"])
        actual, result = (self.call(f"/api/cases/{snapshot['id']}", "PATCH", changes, role)
                          if omit_revision else self.edit(snapshot, changes, role))
        require((actual, result.get("error", {}).get("code")) == (status, code),
                f"Expected {status}/{code}, got {actual}/{result.get('error', {}).get('code')}")
        require(before == self.get(snapshot["id"]), "Rejected request changed stored state")
        return {"expected": status, "actual": actual, "code": code, "storedStateUnchanged": True}


def workflow(http, fixtures, flow, repetition):
    steps = []
    if flow == "CALL":
        current = http.get("CASE-0001")
        original = current["sourceText"]
        status, replay = http.call("/api/cases/CASE-0001/analyze", "POST", {"mode": "replay"})
        require(status == 200 and replay["mode"] == "replay", "Explicit fixture replay failed")
        current = http.get(current["id"])
        require(current["intake"]["quantity"] is None, "Unknown delivered quantity must remain null")
        require(current["reviewConfirmed"] is False, "Replay cannot perform human confirmation")
        department = "delivery"
        steps.append({"step": "saved-analysis-replay", "status": "PASS", "actualAI": False,
                      "audioPlayback": "NOT_RUN_HTTP_ONLY"})
    else:
        reference = fixtures[1]
        original = f"PC4 TEXT-{repetition} 합성 문의: 비스킷 18개 주문 대신 휴지 1박스를 받았습니다. 회송과 처리를 확인해 주세요."
        status, current = http.call("/api/intake", "POST", {
            "storeId": reference["intake"]["storeId"], "subject": reference["intake"]["subject"],
            "type": reference["type"], "referenceCaseId": reference["id"], "text": original}, "owner")
        require(status == 201 and current["linkedFixtureId"] == reference["id"], "Explicit text reference failed")
        before_analysis = http.get(current["id"])
        status, replay = http.call(f"/api/cases/{current['id']}/analyze", "POST", {"mode": "replay"})
        require(status == 409 and replay.get("error", {}).get("code") == "REPLAY_NOT_AVAILABLE",
                "New text must not silently substitute a fixture analysis")
        require(http.get(current["id"]) == before_analysis, "Unavailable replay changed intake")
        current = http.save(current, {"intake": {"quantity": 1, "unit": "BOX"}})
        department = "warehouse"
        steps.append({"step": "new-text-source-and-explicit-reference", "status": "PASS",
                      "refinement": "NOT_RUN_REPLAY_UNAVAILABLE", "manualReview": "1 BOX; no EA conversion"})
    require(current["sourceText"] == original, "Source text changed")
    require(bool(current.get("wms")) and bool(current.get("tms")), "Same-case logistics missing")
    evidence_ids = [item["id"] for item in current["evidence"]]
    require(bool(evidence_ids), "Expected source-case evidence")
    current = http.save(current, {"selectedEvidence": evidence_ids, "departmentId": department})
    require(current["reviewConfirmed"] is False, "Evidence edit must invalidate confirmation")
    steps.append({"step": "same-case-evidence-and-review", "status": "PASS", "selectedEvidence": evidence_ids})
    blocked = http.reject(current, {"status": "handed_off"}, 422, "REVIEW_REQUIRED")
    current = http.save(current, {"reviewConfirmed": True, "status": "handed_off"})
    steps.append({"step": "confirmed-handoff", "status": "PASS", "unconfirmedControl": blocked})
    current = http.save(current, {"reply": "합성 시연: 센터 확인 중입니다.", "pendingActions": ["합성 확인 조치"],
                                  "status": "in_progress"}, "center")
    blocked = http.reject(current, {"status": "closed"}, 422, "ACTIONS_PENDING", "center")
    steps.append({"step": "intermediate-reply-and-pending-close-block", "status": "PASS", "negativeControl": blocked})
    final_reply = f"PC4 {flow}-{repetition} 최종 회신: 합성 확인 조치를 완료했습니다. 실제 물류 변경은 없습니다."
    current = http.save(current, {"reply": final_reply, "pendingActions": [], "status": "closed"}, "center")
    status, owner = http.call(f"/api/cases/{current['id']}", role="owner")
    require(status == 200 and owner["status"] == "closed" and owner["reply"] == final_reply,
            "Owner could not retrieve registered final reply")
    require(owner["replyRegisteredBy"] == "center" and owner["pendingActions"] == [], "Invalid final state")
    require(owner["sourceText"] == original, "Workflow modified source text")
    steps.append({"step": "center-final-and-owner-http-read", "status": "PASS", "revision": owner["revision"]})
    return {"caseId": current["id"], "flow": flow, "repetition": repetition, "steps": steps,
            "finalStatus": owner["status"], "uiCompletion": "NOT_RUN", "sourcePreserved": True}


def boundaries(http, fixtures, owned):
    checks = []

    def check(name, function):
        try:
            evidence = function()
            checks.append({"id": name, "status": "PASS", "evidence": evidence})
        except Exception as error:
            checks.append({"id": name, "status": "FAIL", "error": str(error)})

    ref = fixtures[0]
    body = {"storeId": ref["intake"]["storeId"], "subject": ref["intake"]["subject"],
            "type": ref["type"], "text": "2099-01-01 다른 날짜 합성 문의입니다."}

    def new(body_override=None):
        status, result = http.call("/api/intake", "POST", {**body, **(body_override or {})}, "owner")
        require(status == 201, f"Intake failed: {status}")
        return result

    unlinked = new()

    def no_join():
        require(unlinked["linkedFixtureId"] is None and unlinked["evidence"] == [], "Different-date auto join")
        require("wms" not in unlinked and "tms" not in unlinked, "Unexpected logistics inheritance")
        return {"caseId": unlinked["id"], "referenceCaseId": None, "evidenceCount": 0}

    check("same-store-other-date-no-auto-link", no_join)
    check("missing-revision-428", lambda: http.reject(unlinked, {"intake": {"request": "missing"}},
                                                     428, "REVISION_REQUIRED", omit_revision=True))

    def stale():
        winner = http.save(unlinked, {"intake": {"request": "accepted edit"}})
        result = http.reject(unlinked, {"intake": {"request": "stale edit"}}, 409, "STATE_CONFLICT")
        require(http.get(unlinked["id"]) == winner, "Winner lost after conflict")
        return result

    check("stale-revision-409-preserves-winner", stale)

    def wrong_reference():
        before = http.call("/api/cases")[1]
        status, error = http.call("/api/intake", "POST", {**body, "referenceCaseId": fixtures[1]["id"]}, "owner")
        require(status == 422 and error["error"]["code"] == "INVALID_REFERENCE_CASE", "Foreign reference accepted")
        require(http.call("/api/cases")[1] == before, "Invalid reference created a case")
        return {"status": status, "code": error["error"]["code"], "stateUnchanged": True}

    check("foreign-store-explicit-reference-422", wrong_reference)
    linked = new({"referenceCaseId": ref["id"]})
    check("foreign-case-evidence-422", lambda: http.reject(linked, {"selectedEvidence": [fixtures[1]["evidence"][0]["id"]]}, 422, "INVALID_EVIDENCE"))
    check("linked-store-change-422", lambda: http.reject(linked, {"intake": {"storeId": "SYN-OTHER"}}, 422, "SOURCE_CONTEXT_MISMATCH"))
    check("owner-write-403", lambda: http.reject(linked, {"reviewConfirmed": True}, 403, "READ_ONLY_ROLE", "owner"))
    check("counselor-center-reply-403", lambda: http.reject(linked, {"reply": "invalid counselor reply"}, 403, "CENTER_ROLE_REQUIRED"))
    handed = http.save(linked, {"departmentId": "delivery", "reviewConfirmed": True, "status": "handed_off"})
    check("reply-required-before-close", lambda: http.reject(handed, {"status": "closed"}, 422, "REPLY_REQUIRED", "center"))

    def stale_actions():
        new_actions = http.save(handed, {"reply": "확인 중", "pendingActions": ["새 조치"], "status": "in_progress"}, "center")
        result = http.reject(handed, {"reply": "오래된 완료", "pendingActions": [], "status": "closed"}, 409, "STATE_CONFLICT", "center")
        require(http.get(handed["id"]) == new_actions, "New pending action lost")
        return result

    check("stale-center-form-cannot-discard-new-actions", stale_actions)

    def unavailable():
        current = http.get(unlinked["id"])
        owned.gate.fail_next = True
        status, error = http.edit(current, {"intake": {"request": "recovered edit"}})
        require(status == 503 and error["error"]["code"] == "PC4_INJECTED_UNAVAILABLE", "Injected failure hidden")
        require(http.get(current["id"]) == current, "503 request changed saved case")
        saved = http.save(current, {"intake": {"request": "recovered edit"}})
        return {"injectedHTTP": status, "retryHTTP": 200, "savedRevision": saved["revision"],
                "uiFalseSuccessCheck": "NOT_RUN_HTTP_ONLY"}

    check("api-503-and-explicit-retry", unavailable)

    def disconnect():
        before = http.get(unlinked["id"])
        owned.stop()
        try:
            try:
                http.get(unlinked["id"])
            except urllib.error.URLError:
                disconnected = True
            else:
                raise AssertionError("Expected real loopback connection refusal")
        finally:
            owned.start()
        require(http.get(unlinked["id"]) == before, "Saved intake lost on owned server restart")
        return {"connectionRefused": disconnected, "restoredHTTP": 200, "statePreserved": True,
                "scope": "owned test server restart; not browser offline UI"}

    check("owned-http-server-disconnect-and-recovery", disconnect)
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18104)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    require(1024 <= args.port <= 65535, "Use an unprivileged isolated test port")
    output = args.output or ROOT / "reports/pc4" / f"scenario-results-{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}.json"
    output = output.resolve()
    require(output.is_relative_to((ROOT / "reports/pc4").resolve()), "Reports must stay in reports/pc4")
    require(not output.exists(), "Refusing to overwrite prior scenario evidence")
    report = {"kind": KIND, "startedAt": utc(), "host": socket.gethostname(), "slot": "pc4",
              "mode": "replay", "apiPort": args.port, "checks": [], "httpScenarios": [],
              "uiScenarios": [{"id": f"{flow}-{repeat}", "status": "NOT_RUN",
                               "reason": "This script executes HTTP, not browser interactions"}
                              for flow in ("CALL", "TEXT") for repeat in range(1, 4)],
              "uiBoundaries": [{"id": name, "status": "NOT_RUN"} for name in
                               ("api-error-no-false-success", "media-404-recovery", "browser-offline-online")],
              "limitations": ["No live STT/LLM or human observation", "New text has no fixture replay; manual review is measured",
                              "Own TMS is not counted as independently accepted", "Not a complete UI release rehearsal"]}
    original = original_state_hashes()
    report["originalStateHashesBefore"] = original
    guard = NetworkGuard()
    never = NeverLive()
    owned = None
    try:
        report["headStart"] = git("rev-parse", "HEAD")
        report["branch"] = git("branch", "--show-current")
        report["sourceHashesStart"] = source_hashes()
        from server.repository import JsonCaseRepository
        from server.service import CaseService
        fixture_data = json.loads((ROOT / "data/fixtures/cases.json").read_text(encoding="utf-8-sig"))
        fixtures = fixture_data["cases"] if isinstance(fixture_data, dict) else fixture_data
        with tempfile.TemporaryDirectory(prefix="pc4-http-replay-") as folder:
            temp_root = Path(folder)
            holder = {}
            http = HTTP(args.port)
            with patch("server.handlers.service", side_effect=lambda: holder["service"]), guard.active():
                owned = OwnedServer(args.port)
                owned.start()
                try:
                    for flow in ("CALL", "TEXT"):
                        for repeat in range(1, 4):
                            scenario_id = f"{flow}-{repeat}"
                            path = temp_root / scenario_id / "cases.json"
                            holder["service"] = CaseService(JsonCaseRepository(path), never)
                            row = {"id": scenario_id, "startedAt": utc(), "isolatedStore": scenario_id,
                                   "head": git("rev-parse", "HEAD")}
                            request_start = len(http.requests)
                            try:
                                require(http.call("/api/cases")[0] == 200, "Actual API unavailable")
                                row["evidence"] = workflow(http, fixtures, flow, repeat)
                                row["status"] = "PASS"
                            except Exception as error:
                                row.update(status="FAIL", error=str(error))
                            row["finishedAt"] = utc()
                            row["requests"] = http.requests[request_start:]
                            report["httpScenarios"].append(row)
                    holder["service"] = CaseService(JsonCaseRepository(temp_root / "boundaries/cases.json"), never)
                    report["checks"] = boundaries(http, fixtures, owned)
                    report["httpRequestCount"] = len(http.requests)
                finally:
                    owned.stop()
        report["headEnd"] = git("rev-parse", "HEAD")
        report["sourceHashesEnd"] = source_hashes()
        report["sameSource"] = (report["headStart"] == report["headEnd"] and
                                report["sourceHashesStart"] == report["sourceHashesEnd"] and
                                all(row["head"] == report["headStart"] for row in report["httpScenarios"]))
    except Exception as error:
        report["fatal"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        report["originalStateHashesAfter"] = original_state_hashes()
        report["originalStatePreserved"] = original == report["originalStateHashesAfter"]
        report["paidAnalyzerInvocations"] = never.attempts
        report["blockedExternalConnections"] = guard.blocked
        report["finishedAt"] = utc()
        report["summary"] = {
            "http": {"planned": 6, "executed": len(report["httpScenarios"]),
                     "passed": sum(row["status"] == "PASS" for row in report["httpScenarios"]),
                     "failed": sum(row["status"] == "FAIL" for row in report["httpScenarios"]),
                     "notRun": 6 - len(report["httpScenarios"])},
            "ui": {"planned": 6, "executed": 0, "passed": 0, "failed": 0, "notRun": 6},
            "boundary": {"executed": len(report["checks"]),
                         "passed": sum(row["status"] == "PASS" for row in report["checks"]),
                         "failed": sum(row["status"] == "FAIL" for row in report["checks"])}}
        successful = ("fatal" not in report and report.get("sameSource") and report["originalStatePreserved"]
                      and never.attempts == 0 and guard.blocked == 0
                      and report["summary"]["http"]["passed"] == 6
                      and report["summary"]["boundary"]["failed"] == 0)
        report["httpSuiteStatus"] = "PASS" if successful else "FAIL"
        report["fullUIRehearsalStatus"] = "NOT_RUN"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"output": str(output), "status": report["httpSuiteStatus"],
                          "summary": report["summary"], "fatal": report.get("fatal")}, ensure_ascii=False))
    return 0 if successful else 1


if __name__ == "__main__":
    raise SystemExit(main())
