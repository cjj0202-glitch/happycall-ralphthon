"""Domain regressions using isolated fixture copies; no live AI or demo-store writes."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from server.errors import DemoError
from server.repository import JsonCaseRepository
from server.service import CaseService


ROOT = Path(__file__).resolve().parents[1]


class DemoBackendTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="oneflow-backend-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.fixture_path = self.root / "fixtures.json"
        self.fixture_path.write_bytes((ROOT / "data/fixtures/cases.json").read_bytes())
        self.repo = JsonCaseRepository(self.root / "cases.json", self.fixture_path)
        self.analyzer = Mock()
        self.analyzer.analyze.side_effect = AssertionError("Live AI must not run in domain tests")
        self.service = CaseService(self.repo, analyzer=self.analyzer)
        self.fixtures = self.repo.fixtures()["cases"]
        self.addCleanup(self.analyzer.analyze.assert_not_called)

    def assert_error(self, code, status, operation, *args, **kwargs):
        with self.assertRaises(DemoError) as caught:
            operation(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(caught.exception.status, status)

    def patch_fresh(self, case_id, body, role="counselor"):
        """Test-only helper: construct a new form from a current, explicit read."""
        current = self.service.get(case_id)
        return self.service.patch(case_id, {**body, "expectedRevision": current["revision"]}, role)

    def intake_body(self, fixture=None):
        fixture = fixture or self.fixtures[0]
        return {"storeId": fixture["intake"]["storeId"],
                "subject": fixture["intake"]["subject"],
                "type": fixture["type"], "text": "도착 여부를 확인해 주세요."}

    def handoff(self, fixture=None):
        fixture = fixture or self.fixtures[0]
        case_id = fixture["id"]
        return self.patch_fresh(case_id, {
            "departmentId": "delivery" if fixture["type"] == "missing" else "warehouse",
            "reviewConfirmed": True, "status": "handed_off"})

    def test_initial_store_has_two_independent_fixtures(self):
        cases = self.service.list()["cases"]
        self.assertEqual(len(cases), 2)
        self.assertEqual({case["type"] for case in cases}, {"missing", "wrong"})
        original = copy.deepcopy(cases[0])
        cases[0]["store"]["name"] = "external mutation"
        self.assertEqual(self.service.get(original["id"]), original)
        reopened = JsonCaseRepository(self.root / "cases.json", self.fixture_path)
        self.assertEqual(len(reopened.list()), 2)

    def test_unknown_case_is_404_for_get_and_patch(self):
        self.assert_error("CASE_NOT_FOUND", 404, self.service.get, "CASE-NOT-FOUND")
        self.assert_error("CASE_NOT_FOUND", 404, self.service.patch, "CASE-NOT-FOUND", {"expectedRevision": 0})

    def test_legacy_revision_reads_zero_then_successful_writes_increment(self):
        self.repo.path.write_text(json.dumps({"cases": self.fixtures}), encoding="utf-8")
        self.assertNotIn("revision", json.loads(self.repo.path.read_text())["cases"][0])
        self.assertEqual([c["revision"] for c in self.service.list()["cases"]], [0, 0])
        self.assertNotIn("revision", json.loads(self.repo.path.read_text())["cases"][0])
        case_id = self.fixtures[0]["id"]
        updated = self.service.patch(case_id, {"expectedRevision": 0, "departmentId": "delivery"})
        self.assertEqual(updated["revision"], 1)
        result = self.service.analyze(case_id, "replay")
        self.assertEqual(result["revision"], 2)
        self.assertEqual(self.service.get(case_id)["revision"], 2)
        self.assertEqual(self.service.intake(self.intake_body())["revision"], 0)

    def test_patch_requires_a_valid_explicit_revision(self):
        case_id = self.fixtures[0]["id"]
        self.assert_error("REVISION_REQUIRED", 428, self.service.patch, case_id, {})
        for revision in (None, True, -1, 1.2, "0"):
            self.assert_error("INVALID_REVISION", 422, self.service.patch, case_id,
                              {"expectedRevision": revision})
        self.assertEqual(self.service.get(case_id)["revision"], 0)

    def test_stale_center_form_cannot_erase_new_pending_actions_and_close(self):
        case_id = self.handoff()["id"]
        # A reads its form; a separate repository/service B then adds an action.
        old_form = self.service.get(case_id)
        other = CaseService(JsonCaseRepository(self.repo.path, self.fixture_path), analyzer=self.analyzer)
        new_form = other.patch(case_id, {"expectedRevision": old_form["revision"],
            "pendingActions": ["기사 확인"], "status": "in_progress"}, "center")
        self.assert_error("STATE_CONFLICT", 409, self.service.patch, case_id,
            {"expectedRevision": old_form["revision"], "pendingActions": old_form["pendingActions"],
             "reply": "처리 완료", "status": "closed"}, "center")
        self.assertEqual(self.service.get(case_id), new_form)
        closed = self.service.patch(case_id, {"expectedRevision": new_form["revision"],
            "pendingActions": [], "reply": "새 조치를 확인하여 완료", "status": "closed"}, "center")
        self.assertEqual(closed["revision"], new_form["revision"] + 1)
        self.assertEqual(closed["status"], "closed")

    def test_stale_human_confirmation_cannot_confirm_changed_intake(self):
        case_id = self.fixtures[0]["id"]
        old_form = self.service.get(case_id)
        new_form = self.service.patch(case_id, {"expectedRevision": old_form["revision"],
            "intake": {"request": "수정된 확인 요청"}})
        self.assert_error("STATE_CONFLICT", 409, self.service.patch, case_id,
            {"expectedRevision": old_form["revision"], "reviewConfirmed": True})
        self.assertEqual(self.service.get(case_id), new_form)
        self.assertFalse(new_form["reviewConfirmed"])

    def test_analyze_cannot_overwrite_a_concurrent_human_edit(self):
        case_id = self.fixtures[0]["id"]
        fixture = self.fixtures[0]
        def simulated_analysis(case, departments):
            self.service.patch(case_id, {"expectedRevision": case["revision"],
                "intake": {"request": "분석 중 사람이 수정한 요청"}, "reviewConfirmed": True})
            return {"analysis": copy.deepcopy(fixture.get("replayAnalysis") or fixture["analysis"]),
                    "transcript": fixture["transcript"], "requestId": "local-simulated-analysis"}
        self.service.analyzer = Mock(analyze=Mock(side_effect=simulated_analysis))
        self.assert_error("STATE_CONFLICT", 409, self.service.analyze, case_id, "demo-live")
        current = self.service.get(case_id)
        self.assertEqual(current["revision"], 1)
        self.assertEqual(current["intake"]["request"], "분석 중 사람이 수정한 요청")
        self.assertTrue(current["reviewConfirmed"])

    def test_department_contract(self):
        self.assertEqual({row["id"] for row in self.service.departments()},
                         {"delivery", "warehouse", "cs"})

    def test_intake_has_frontend_shape_and_exact_fixture_context(self):
        for fixture in self.fixtures:
            with self.subTest(case=fixture["id"]):
                body = self.intake_body(fixture)
                body["referenceCaseId"] = fixture["id"]
                created = self.service.intake(body)
                self.assertEqual(created["store"], fixture["store"])
                self.assertEqual(created["sourceText"], body["text"])
                self.assertTrue(created["title"])
                self.assertEqual(created["channel"], "text")
                self.assertEqual(created["transcript"][0]["text"], body["text"])
                self.assertEqual(created["linkedFixtureId"], fixture["id"])
                for key in ("wms", "tms", "asOf", "expected", "received", "evidence"):
                    self.assertEqual(created[key], fixture[key], key)
                created["wms"]["test_mutation"] = True
                self.assertNotIn("test_mutation", self.service.get(created["id"])["wms"])
                self.assertNotIn("test_mutation", self.service.get(fixture["id"])["wms"])

    def test_any_mismatched_join_key_leaves_context_unlinked(self):
        variants = ({"storeId": "SYN-UNKNOWN"}, {"subject": "새로운 문의 대상"},
                    {"type": "wrong"})
        for change in variants:
            with self.subTest(change=change):
                created = self.service.intake({**self.intake_body(), **change})
                self.assertIsNone(created["linkedFixtureId"])
                self.assertEqual(created["evidence"], [])
                for key in ("wms", "tms", "asOf", "expected", "received"):
                    self.assertFalse(created.get(key), key)

    def test_same_store_subject_and_type_on_another_day_never_auto_links(self):
        body = {**self.intake_body(), "text": "2026년 9월 21일 오늘 배송이 아직 오지 않았습니다."}
        created = self.service.intake(body)
        self.assertIsNone(created["linkedFixtureId"])
        self.assertEqual(created["evidence"], [])
        for key in ("wms", "tms", "asOf", "expected", "received"):
            self.assertNotIn(key, created)

    def test_explicit_reference_rejects_unknown_or_mismatched_context(self):
        body = {**self.intake_body(), "referenceCaseId": self.fixtures[0]["id"]}
        for change in ({"referenceCaseId": "UNKNOWN"}, {"referenceCaseId": None},
                       {"referenceCaseId": 1}, {"storeId": "SYN-OTHER"},
                       {"subject": "새 문의"}, {"type": "wrong"}):
            with self.subTest(change=change):
                self.assert_error("INVALID_REFERENCE_CASE", 422, self.service.intake, {**body, **change})
        self.assertEqual(len(self.service.list()["cases"]), 2)

    def test_linked_context_rejects_store_change_atomically(self):
        created = self.service.intake({**self.intake_body(), "referenceCaseId": self.fixtures[0]["id"]})
        for case_id in (self.fixtures[0]["id"], created["id"]):
            original = self.service.get(case_id)
            for extra in ({}, {"status": "handed_off", "reviewConfirmed": True, "departmentId": "delivery"}):
                self.assert_error("SOURCE_CONTEXT_MISMATCH", 422, self.patch_fresh,
                                  case_id, {"intake": {"storeId": "SYN-OTHER"}, **extra})
                self.assertEqual(self.service.get(case_id), original)

    def test_unknown_store_stays_null_until_confirmed_for_handoff(self):
        case_id = self.fixtures[0]["id"]
        updated = self.patch_fresh(case_id, {"intake": {"storeId": None}, "status": "review"})
        self.assertIsNone(updated["intake"]["storeId"])
        self.assert_error("HANDOFF_FIELDS_REQUIRED", 422, self.patch_fresh, case_id,
                          {"departmentId": "delivery", "reviewConfirmed": True, "status": "handed_off"})
        updated = self.patch_fresh(case_id, {"intake": {"storeId": self.fixtures[0]["intake"]["storeId"]},
                          "departmentId": "delivery", "reviewConfirmed": True, "status": "handed_off"})
        self.assertEqual(updated["status"], "handed_off")

    def test_freeform_subject_edit_does_not_infer_a_different_source_context(self):
        fixture = self.fixtures[0]
        updated = self.patch_fresh(fixture["id"], {
            "intake": {"subject": "예정된 배송이 아직 오지 않았다는 점주 문의"},
            "selectedEvidence": [fixture["evidence"][0]["id"]],
            "departmentId": "delivery", "reviewConfirmed": True, "status": "handed_off"})
        self.assertEqual(updated["status"], "handed_off")
        self.assertEqual(updated["selectedEvidence"], [fixture["evidence"][0]["id"]])

    def test_persisted_foreign_evidence_and_store_cannot_bypass_handoff(self):
        case_id = self.fixtures[0]["id"]
        for changes, code in (({"selectedEvidence": [self.fixtures[1]["evidence"][0]["id"]]}, "INVALID_EVIDENCE"),
                              ({"intake": {"storeId": "SYN-OTHER", "subject": "문의"}, "selectedEvidence": []}, "SOURCE_CONTEXT_MISMATCH")):
            self.repo.update(case_id, lambda case: {**case, **changes})
            self.assert_error(code, 422, self.patch_fresh, case_id,
                              {"departmentId": "delivery", "reviewConfirmed": True, "status": "handed_off"})

    def test_new_intake_replay_is_409_and_manual_handoff_still_works(self):
        created = self.service.intake(self.intake_body())
        self.assert_error("REPLAY_NOT_AVAILABLE", 409, self.service.analyze,
                          created["id"], "replay")
        updated = self.patch_fresh(created["id"], {
            "departmentId": "delivery", "reviewConfirmed": True, "status": "handed_off"})
        self.assertEqual(updated["status"], "handed_off")

    def test_source_fields_are_immutable_and_rejections_are_atomic(self):
        case_id = self.fixtures[0]["id"]
        original = self.service.get(case_id)
        for key in ("sourceText", "transcript", "evidence", "wms", "tms", "expected", "received", "store"):
            with self.subTest(field=key):
                self.assert_error("IMMUTABLE_SOURCE", 422, self.patch_fresh,
                                  case_id, {key: "tampered"})
                self.assertEqual(self.service.get(case_id), original)
        self.patch_fresh(case_id, {"intake": {"request": "새 확인 요청"}})
        current = self.service.get(case_id)
        for key in ("sourceText", "transcript", "evidence", "wms", "tms", "expected", "received", "store"):
            self.assertEqual(current[key], original[key], key)

    def test_handoff_needs_department_then_human_confirmation(self):
        case_id = self.fixtures[0]["id"]
        self.assert_error("HANDOFF_FIELDS_REQUIRED", 422, self.patch_fresh,
                          case_id, {"status": "handed_off", "reviewConfirmed": True})
        self.patch_fresh(case_id, {"departmentId": "delivery"})
        self.assert_error("REVIEW_REQUIRED", 422, self.patch_fresh,
                          case_id, {"status": "handed_off"})
        self.assertEqual(self.service.get(case_id)["status"], "draft")
        self.assertEqual(self.handoff()["status"], "handed_off")

    def test_handoff_requires_store_and_subject_but_allows_null_quantity_unit(self):
        for fixture in self.fixtures:
            with self.subTest(case=fixture["id"]):
                case_id = fixture["id"]
                self.patch_fresh(case_id, {"intake": {"quantity": None, "unit": None}})
                for field in ("storeId", "subject"):
                    self.assert_error("HANDOFF_FIELDS_REQUIRED", 422, self.patch_fresh,
                                      case_id, {"intake": {field: ""}, "departmentId": "delivery",
                                                "reviewConfirmed": True, "status": "handed_off"})
                updated = self.handoff(fixture)
                self.assertIsNone(updated["intake"]["quantity"])
                self.assertIsNone(updated["intake"]["unit"])

    def test_intake_department_and_evidence_edits_reset_confirmation(self):
        case_id = self.fixtures[0]["id"]
        edits = ({"intake": {"request": "다시 확인해 주세요"}},
                 {"departmentId": "warehouse"},
                 {"selectedEvidence": [self.fixtures[0]["evidence"][0]["id"]]})
        for edit in edits:
            with self.subTest(edit=edit):
                self.patch_fresh(case_id, {"reviewConfirmed": True})
                updated = self.patch_fresh(case_id, edit)
                self.assertIs(updated["reviewConfirmed"], False)

    def test_unchanged_evidence_keeps_confirmation(self):
        case_id = self.fixtures[0]["id"]
        selected = [self.fixtures[0]["evidence"][0]["id"]]
        self.patch_fresh(case_id, {"selectedEvidence": selected, "reviewConfirmed": True})
        updated = self.patch_fresh(case_id, {"selectedEvidence": selected})
        self.assertIs(updated["reviewConfirmed"], True)

    def test_foreign_evidence_and_unknown_department_are_rejected(self):
        case_id = self.fixtures[0]["id"]
        original = self.service.get(case_id)
        foreign_id = self.fixtures[1]["evidence"][0]["id"]
        self.assert_error("INVALID_EVIDENCE", 422, self.patch_fresh,
                          case_id, {"selectedEvidence": [foreign_id]})
        self.assert_error("INVALID_DEPARTMENT", 422, self.patch_fresh,
                          case_id, {"departmentId": "unregistered"})
        self.assertEqual(self.service.get(case_id), original)

    def test_handed_off_can_close_directly_with_center_reply(self):
        case_id = self.handoff()["id"]
        closed = self.patch_fresh(case_id, {
            "reply": "운행 상황을 확인해 회신했습니다.", "pendingActions": [], "status": "closed"}, "center")
        self.assertEqual(closed["status"], "closed")
        self.assertEqual(closed["replyRegisteredBy"], "center")
        self.assertEqual(self.service.get(case_id)["status"], "closed")

    def test_close_requires_center_and_reply(self):
        case_id = self.handoff()["id"]
        self.assert_error("CENTER_ROLE_REQUIRED", 403, self.patch_fresh,
                          case_id, {"status": "closed"}, "counselor")
        self.assert_error("REPLY_REQUIRED", 422, self.patch_fresh,
                          case_id, {"status": "closed"}, "center")
        self.assertEqual(self.service.get(case_id)["status"], "handed_off")

    def test_pending_action_blocks_close_until_center_clears_it(self):
        case_id = self.handoff()["id"]
        self.patch_fresh(case_id, {"reply": "확인 중입니다.", "pendingActions": ["기사 확인"]}, "center")
        original = self.service.get(case_id)
        self.assert_error("ACTIONS_PENDING", 422, self.patch_fresh,
                          case_id, {"status": "closed"}, "center")
        self.assertEqual(self.service.get(case_id), original)
        closed = self.patch_fresh(case_id, {"status": "closed", "pendingActions": []}, "center")
        self.assertEqual(closed["status"], "closed")

    def test_owner_is_read_only_and_center_cannot_skip_handoff(self):
        case_id = self.fixtures[0]["id"]
        self.assert_error("READ_ONLY_ROLE", 403, self.patch_fresh,
                          case_id, {"reviewConfirmed": True}, "owner")
        self.assert_error("HANDOFF_REQUIRED", 409, self.patch_fresh,
                          case_id, {"reply": "접수 전 회신"}, "center")

    def test_replay_does_not_bypass_human_review_or_rewrite_source(self):
        case_id = self.fixtures[0]["id"]
        original = self.service.get(case_id)
        result = self.service.analyze(case_id, "replay")
        self.assertEqual(result["mode"], "replay")
        current = self.service.get(case_id)
        self.assertEqual(current["status"], "review")
        self.assertIs(current["reviewConfirmed"], False)
        self.assertEqual(current["sourceText"], original["sourceText"])
        self.assert_error("REVIEW_REQUIRED", 422, self.patch_fresh,
                          case_id, {"status": "handed_off"})

    def test_asgi_startup_list_unknown_id_and_intake_contract(self):
        from starlette.testclient import TestClient
        from server.app import create_app

        with patch("server.handlers.service", return_value=self.service), TestClient(create_app()) as client:
            listed = client.get("/api/cases")
            self.assertEqual(listed.status_code, 200, listed.text)
            self.assertEqual(len(listed.json()["cases"]), 2)
            unknown = client.get("/api/cases/CASE-NOT-FOUND")
            self.assertEqual(unknown.status_code, 404, unknown.text)
            self.assertEqual(unknown.json()["error"]["code"], "CASE_NOT_FOUND")
            created = client.post("/api/intake", json=self.intake_body())
            self.assertEqual(created.status_code, 201, created.text)
            self.assertEqual(created.json()["store"]["id"], self.fixtures[0]["store"]["id"])
            self.assertIsNone(created.json()["linkedFixtureId"])
            linked = client.post("/api/intake", json={**self.intake_body(), "referenceCaseId": self.fixtures[0]["id"]})
            self.assertEqual(linked.status_code, 201, linked.text)
            self.assertEqual(linked.json()["linkedFixtureId"], self.fixtures[0]["id"])
            invalid = client.post("/api/intake", json={**self.intake_body(), "referenceCaseId": 1})
            self.assertEqual(invalid.status_code, 400, invalid.text)
            self.assertEqual(created.json()["sourceText"], self.intake_body()["text"])
            replay = client.post(f"/api/cases/{created.json()['id']}/analyze", json={"mode": "replay"})
            self.assertEqual(replay.status_code, 409, replay.text)
            self.assertEqual(replay.json()["error"]["code"], "REPLAY_NOT_AVAILABLE")

    def test_asgi_workflow_gates_null_fields_and_role_header(self):
        from starlette.testclient import TestClient
        from server.app import create_app

        case_id = self.fixtures[0]["id"]
        url = f"/api/cases/{case_id}"
        with patch("server.handlers.service", return_value=self.service), TestClient(create_app()) as client:
            missing = client.patch(url, json={"departmentId": "delivery"})
            self.assertEqual(missing.status_code, 428, missing.text)
            self.assertEqual(missing.json()["error"]["code"], "REVISION_REQUIRED")
            rejected = client.patch(url, json={"sourceText": "tampered"})
            self.assertEqual(rejected.status_code, 400, rejected.text)
            blocked = client.patch(url, json={"expectedRevision": 0, "departmentId": "delivery", "status": "handed_off"})
            self.assertEqual(blocked.status_code, 422, blocked.text)
            self.assertEqual(blocked.json()["error"]["code"], "REVIEW_REQUIRED")
            handoff = client.patch(url, json={"expectedRevision": 0, "intake": {"quantity": None, "unit": None},
                "departmentId": "delivery", "reviewConfirmed": True, "status": "handed_off"})
            self.assertEqual(handoff.status_code, 200, handoff.text)
            self.assertEqual(handoff.json()["revision"], 1)
            stale = client.patch(url, headers={"X-Demo-Role": "center"},
                                 json={"expectedRevision": 0, "reply": "오래된 화면"})
            self.assertEqual(stale.status_code, 409, stale.text)
            self.assertEqual(stale.json()["error"]["code"], "STATE_CONFLICT")
            blocked = client.patch(url, json={"expectedRevision": 1, "status": "closed"})
            self.assertEqual(blocked.status_code, 403, blocked.text)
            center = {"X-Demo-Role": "center"}
            blocked = client.patch(url, headers=center,
                json={"expectedRevision": 1, "reply": "확인 중입니다.", "pendingActions": ["확인"], "status": "closed"})
            self.assertEqual(blocked.status_code, 422, blocked.text)
            self.assertEqual(blocked.json()["error"]["code"], "ACTIONS_PENDING")
            closed = client.patch(url, headers=center,
                json={"expectedRevision": 1, "reply": "확인 후 회신했습니다.", "pendingActions": [], "status": "closed"})
            self.assertEqual(closed.status_code, 200, closed.text)
            self.assertEqual(closed.json()["status"], "closed")


if __name__ == "__main__":
    unittest.main()
