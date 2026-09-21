"""Independent workflow checks against a private file store; never call live AI."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from server.repository import JsonCaseRepository
from server.service import CaseService
from server.errors import DemoError

class NeverLive:
    def analyze(self, *args, **kwargs):
        raise AssertionError("Paid live API is forbidden in this test")

report = {"at": datetime.now(timezone.utc).isoformat(), "kind": "isolated revision/reference service contract, not browser or human test", "checks": []}
out = ROOT / "reports/e2e"
out.mkdir(parents=True, exist_ok=True)

def check(name, f):
    try:
        evidence = f()
        report["checks"].append({"name": name, "status": "PASS", "evidence": evidence})
    except Exception as e:
        report["checks"].append({"name": name, "status": "FAIL_RECHECK", "error": str(e)})

with tempfile.TemporaryDirectory(prefix="private-store-", dir=out) as temp:
    assert Path(temp).resolve().is_relative_to(out.resolve())
    service = CaseService(JsonCaseRepository(Path(temp) / "cases.json", ROOT / "data/fixtures/cases.json"), NeverLive())
    def replay():
        result = service.analyze("CASE-0001", "replay")
        assert result["mode"] == "replay"
        assert result["analysis"]["fields"]["quantity"] is None
        return {"mode": result["mode"], "quantity": result["analysis"]["fields"]["quantity"]}
    check("fixture-replay-null", replay)
    text_body = {"storeId": "SYN-ST01", "subject": "당일 1회차 배송 전체", "type": "missing", "text": "독립 E2E 다른 날 합성 문의"}
    unlinked = service.intake(text_body)
    def no_implicit_join():
        assert unlinked["linkedFixtureId"] is None
        assert unlinked["evidence"] == []
        assert "wms" not in unlinked and "tms" not in unlinked
        return {"reference": None, "evidence": [], "revision": unlinked["revision"]}
    check("same-description-new-intake-unlinked", no_implicit_join)
    def wrong_reference():
        try:
            service.intake({**text_body, "referenceCaseId": "CASE-0002"})
        except DemoError as e:
            assert e.code == "INVALID_REFERENCE_CASE"
            return {"code": e.code}
        raise AssertionError("Mismatched reference was accepted")
    check("mismatched-explicit-reference-denied", wrong_reference)
    case = service.intake({**text_body, "referenceCaseId": "CASE-0001"})
    def explicit_join():
        assert case["linkedFixtureId"] == "CASE-0001"
        assert case["tms"]["routeId"] == "SYN-R01"
        assert {e["id"] for e in case["evidence"]} == {"E-M1", "E-M2", "E-M3"}
        return {"reference": case["linkedFixtureId"], "revision": case["revision"]}
    check("matching-explicit-reference-links", explicit_join)
    cid = case["id"]
    # No hidden GET/retry: the caller supplies the exact snapshot associated with the edit.
    def patch_from(snapshot, body, role="counselor"):
        assert "expectedRevision" not in body
        return service.patch(snapshot["id"], {**body, "expectedRevision": snapshot["revision"]}, role)
    def rejects(snapshot, body, expected, role="counselor", omit_revision=False, status=None):
        before = service.get(snapshot["id"])
        try:
            if omit_revision:
                service.patch(snapshot["id"], body, role)
            else:
                patch_from(snapshot, body, role)
        except DemoError as e:
            assert e.code == expected, (e.code, expected)
            if status is not None:
                assert e.status == status, (e.status, status)
            assert before == service.get(snapshot["id"]), "Rejected request modified saved case"
            return {"code": e.code, "status": e.status, "sentRevision": None if omit_revision else snapshot["revision"], "storedRevision": before["revision"], "unchanged": True}
        raise AssertionError(f"Expected {expected}, request was allowed")
    check("missing-revision-denied-428", lambda: rejects(unlinked, {"intake": {"request": "missing"}}, "REVISION_REQUIRED", omit_revision=True, status=428))
    def stale_revision():
        original = unlinked
        first = patch_from(original, {"intake": {"request": "E2E accepted writer"}})
        assert first["revision"] == original["revision"] + 1
        result = rejects(original, {"intake": {"request": "E2E stale writer"}}, "STATE_CONFLICT", status=409)
        assert service.get(original["id"])["intake"]["request"] == "E2E accepted writer"
        return {**result, "winningRevision": first["revision"]}
    check("accepted-write-then-stale-revision-denied-409", stale_revision)
    check("unconfirmed-handoff-denied", lambda: rejects(service.get(cid), {"departmentId": "delivery", "status": "handed_off", "reviewConfirmed": False}, "REVIEW_REQUIRED"))
    check("foreign-evidence-denied", lambda: rejects(service.get(cid), {"selectedEvidence": ["E-W1"]}, "INVALID_EVIDENCE"))
    def handoff():
        result = patch_from(service.get(cid), {"departmentId": "delivery", "reviewConfirmed": True, "status": "handed_off"})
        assert result["status"] == "handed_off" and result["intake"]["quantity"] is None
        return {"status": result["status"], "quantity": result["intake"]["quantity"]}
    check("null-quantity-handoff-allowed", handoff)
    check("counselor-cannot-register-center-reply", lambda: rejects(service.get(cid), {"reply": "회신"}, "CENTER_ROLE_REQUIRED"))
    def intermediate():
        result = patch_from(service.get(cid), {"reply": "확인 중입니다", "pendingActions": ["운행 확인"], "status": "in_progress"}, "center")
        assert result["status"] == "in_progress" and result["pendingActions"] == ["운행 확인"]
        return {"status": result["status"], "pendingActions": result["pendingActions"]}
    check("intermediate-pending-remains-progress", intermediate)
    check("pending-blocks-close", lambda: rejects(service.get(cid), {"status": "closed"}, "ACTIONS_PENDING", "center"))
    def close():
        result = patch_from(service.get(cid), {"pendingActions": [], "reply": "확인 조치를 완료했습니다", "status": "closed"}, "center")
        assert result["status"] == "closed" and result["replyRegisteredBy"] == "center"
        return {"status": result["status"], "pendingActions": result["pendingActions"], "reply": result["reply"]}
    check("final-reply-after-actions-closes", close)
    check("closed-immutable", lambda: rejects(service.get(cid), {"reply": "다시 수정"}, "CASE_CLOSED", "center"))

(out / "service-contract-revision.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(any(x["status"] != "PASS" for x in report["checks"]))
