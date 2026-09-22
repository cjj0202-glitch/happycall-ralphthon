import copy
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from server.errors import DemoError
from server.live import LiveAnalyzer
from server.service import CaseService


class ReplyDraftTests(unittest.TestCase):
    def setUp(self):
        self.case = {"id": "CASE-0001", "revision": 3, "status": "handed_off", "reply": None,
                     "analysis": {"replyDraft": "저장된 검토 초안"}, "history": [], "pendingActions": ["기사 확인"]}
        self.repo = Mock()
        self.repo.get.side_effect = lambda _: copy.deepcopy(self.case)
        self.analyzer = Mock()
        self.analyzer.reply_draft.return_value = {"replyTitle": "배송 문의 확인 안내", "replyDraft": "추가 확인이 필요합니다.", "mode": "demo-live", "requestId": "r1"}
        self.service = CaseService(self.repo, self.analyzer)

    def call(self, mode="replay", role="center", revision=3):
        return self.service.reply_draft("CASE-0001", {"mode": mode, "expectedRevision": revision}, role)

    def test_replay_never_calls_live_or_writes(self):
        before = copy.deepcopy(self.case)
        self.assertEqual(self.call()["mode"], "replay")
        self.analyzer.reply_draft.assert_not_called()
        self.repo.update.assert_not_called()
        self.assertEqual(self.case, before)

    def test_live_is_read_only(self):
        self.assertEqual(self.call("demo-live")["revision"], 3)
        self.analyzer.reply_draft.assert_called_once()
        self.repo.update.assert_not_called()
        self.assertIsNone(self.case["reply"])

    def test_role_and_states_block_before_model(self):
        for role in (None, "owner", "counselor"):
            with self.assertRaises(DemoError) as raised:
                self.call("demo-live", role)
            self.assertEqual(raised.exception.status, 403)
        for state in ("draft", "review", "closed"):
            self.case["status"] = state
            with self.assertRaises(DemoError) as raised:
                self.call("demo-live")
            self.assertEqual(raised.exception.status, 409)
        self.analyzer.reply_draft.assert_not_called()

    def test_revision_before_and_after_model(self):
        with self.assertRaises(DemoError):
            self.call("demo-live", revision=2)
        self.analyzer.reply_draft.assert_not_called()
        self.analyzer.reply_draft.side_effect = lambda _, **kwargs: (self.case.update(revision=4) or {"replyDraft": "초안", "mode": "demo-live"})
        with self.assertRaises(DemoError) as raised:
            self.call("demo-live")
        self.assertEqual(raised.exception.status, 409)
        self.repo.update.assert_not_called()

    def test_missing_replay_does_not_call_live(self):
        self.case["analysis"] = None
        with self.assertRaises(DemoError):
            self.call()
        self.analyzer.reply_draft.assert_not_called()

    def test_local_center_context_is_distinct_and_never_saved(self):
        context = {"pendingActions": [], "reply": "기사와 확인한 내용을 검토 중입니다.", "replyTitle": "기사 확인 안내"}
        self.service.reply_draft("CASE-0001", {"mode": "demo-live", "expectedRevision": 3, "centerContext": context}, "center")
        self.assertEqual(self.analyzer.reply_draft.call_args.kwargs["center_context"], context)
        self.assertEqual(self.analyzer.reply_draft.call_args.args[0]["pendingActions"], ["기사 확인"])
        self.assertEqual(self.case["pendingActions"], ["기사 확인"])
        self.repo.update.assert_not_called()
        for invalid in (None, {}, {"reply": "", "pendingActions": [""]}, {"reply": 1, "pendingActions": []}):
            with self.assertRaises(DemoError) as raised:
                self.service.reply_draft("CASE-0001", {"mode": "demo-live", "expectedRevision": 3, "centerContext": invalid}, "center")
            self.assertEqual(raised.exception.status, 422)

    def test_openapi_http_route(self):
        from starlette.testclient import TestClient
        from server.app import create_app
        from unittest.mock import patch
        with patch("server.handlers.service", return_value=self.service):
            with TestClient(create_app()) as client:
                response = client.post("/api/cases/CASE-0001/reply-draft", headers={"X-Demo-Role": "center"},
                    json={"mode": "demo-live", "expectedRevision": 3, "centerContext": {"reply": "", "pendingActions": []}})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["revision"], 3)
                self.assertEqual(response.json()["replyTitle"], "배송 문의 확인 안내")
                denied = client.post("/api/cases/CASE-0001/reply-draft", headers={"X-Demo-Role": "owner"},
                    json={"mode": "replay", "expectedRevision": 3})
                self.assertIn(denied.status_code, (400, 403))
                conflict = client.post("/api/cases/CASE-0001/reply-draft", headers={"X-Demo-Role": "center"},
                    json={"mode": "demo-live", "expectedRevision": 2})
                self.assertEqual(conflict.status_code, 409, conflict.text)
        self.repo.update.assert_not_called()

    def test_live_response_and_failure_budget(self):
        budget, client = Mock(), Mock()
        budget.reserve.return_value = "request-1"
        client.responses.create.return_value = SimpleNamespace(status="completed", output_text=json.dumps({"replyTitle": "배송 확인 안내", "replyDraft": "확인 후 안내드리겠습니다."}))
        analyzer = LiveAnalyzer(budget, lambda: client)
        self.assertEqual(analyzer.reply_draft(self.case)["mode"], "demo-live")
        budget.reserve.assert_called_once_with(15, "reply-draft")
        budget.finish.assert_called_once_with("request-1", True)
        self.assertFalse(client.responses.create.call_args.kwargs["store"])
        client.responses.create.side_effect = RuntimeError("secret provider metadata")
        with self.assertRaises(DemoError) as raised:
            analyzer.reply_draft(self.case)
        self.assertNotIn("secret", str(raised.exception))
        budget.finish.assert_called_with("request-1", False)

    def test_replay_title_is_bounded_and_nonfinal(self):
        self.case["intake"] = {"subject": "배송완료 정상 출고 확정 " + "긴문의" * 100}
        title = self.call()["replyTitle"]
        self.assertLessEqual(len(title), 100)
        self.assertTrue(title.endswith(" 확인 안내"))
        self.assertNotIn("완료", title)
        self.assertNotIn("확정", title)

    def test_http_title_generate_patch_read_and_permissions(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from starlette.testclient import TestClient
        from server.app import create_app
        from server.repository import JsonCaseRepository, atomic_json
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "cases.json"
            atomic_json(store, {"cases": []})
            repo = JsonCaseRepository(store)
            repo.create({**self.case, "status": "in_progress", "intake": {"subject": "배송 문의"}, "pendingActions": []})
            service = CaseService(repo, self.analyzer)
            with patch("server.handlers.service", return_value=service), TestClient(create_app()) as client:
                generated = client.post("/api/cases/CASE-0001/reply-draft", headers={"X-Demo-Role": "center"},
                    json={"mode": "replay", "expectedRevision": 0, "centerContext": {"reply": "", "replyTitle": "", "pendingActions": []}})
                self.assertEqual(generated.status_code, 200, generated.text)
                self.assertEqual(generated.json()["replyTitle"], "배송 문의 확인 안내")
                self.assertNotIn("replyTitle", repo.get("CASE-0001"))
                payload = {"expectedRevision": 0, "replyTitle": "배송 문의 확인 안내", "reply": "확인 후 안내드립니다.", "pendingActions": [], "status": "in_progress"}
                for role in ("owner", "counselor"):
                    denied = client.patch("/api/cases/CASE-0001", headers={"X-Demo-Role": role}, json=payload)
                    self.assertEqual(denied.status_code, 403, denied.text)
                saved = client.patch("/api/cases/CASE-0001", headers={"X-Demo-Role": "center"}, json=payload)
                self.assertEqual(saved.status_code, 200, saved.text)
                self.assertEqual(saved.json()["replyTitle"], payload["replyTitle"])
                loaded = client.get("/api/cases/CASE-0001").json()
                self.assertEqual(loaded["replyTitle"], payload["replyTitle"])
                self.assertEqual(loaded["reply"], payload["reply"])
                legacy = client.patch("/api/cases/CASE-0001", headers={"X-Demo-Role": "center"},
                    json={"expectedRevision": loaded["revision"], "reply": "추가 확인 중입니다."})
                self.assertEqual(legacy.status_code, 200, legacy.text)
                self.assertEqual(legacy.json()["replyTitle"], payload["replyTitle"])
                invalid = client.patch("/api/cases/CASE-0001", headers={"X-Demo-Role": "center"},
                    json={"expectedRevision": legacy.json()["revision"], "replyTitle": "x" * 161})
                self.assertIn(invalid.status_code, (400, 422), invalid.text)

    def test_title_only_counselor_and_locked_state_rejected(self):
        with self.assertRaises(DemoError) as denied:
            self.service.patch("CASE-0001", {"expectedRevision": 3, "replyTitle": "제목"}, "counselor")
        self.assertEqual(denied.exception.status, 403)
        self.repo.update.side_effect = lambda _, mutate: mutate(copy.deepcopy({**self.case, "status": "closed"}))
        with self.assertRaises(DemoError) as locked:
            self.service.patch("CASE-0001", {"expectedRevision": 3, "replyTitle": "제목"}, "center")
        self.assertEqual(locked.exception.status, 409)


if __name__ == "__main__":
    unittest.main()
