"""Two complete text-intake workflows through the real ASGI application.

Authored model responses and an in-memory budget are test inputs, not live model
accuracy evidence. No listening server, external provider, local case store or
budget ledger is used. Repository reopening below proves same-process CAS
roundtrips, not persistence across processes or a deployed service.
"""
from __future__ import annotations

import copy
from collections import Counter
from dataclasses import dataclass, field
import json
from types import SimpleNamespace
import uuid
from unittest.mock import Mock, patch

import pytest
from starlette.testclient import TestClient

from server.app import create_app
from server.cas_repository import CasCaseRepository
from server.cas_store import InMemoryCasStore
from server.live import LiveAnalyzer
from server.service import CaseService


@dataclass
class MemoryBudget:
    reservations: list = field(default_factory=list)
    completions: list = field(default_factory=list)

    def reserve(self, amount, purpose):
        request_id = f"authored-asgi-{len(self.reservations) + 1}"
        self.reservations.append((amount, purpose, request_id))
        return request_id

    def finish(self, request_id, succeeded):
        self.completions.append((request_id, succeeded))


def authored_input(source):
    """Independent synthetic wording; never read a replay/evaluation answer."""
    store_quote = source["store"]["name"] + "입니다."
    claim = {"product": None, "quantity": None, "unit": None, "evidenceQuote": None}
    if source["type"] == "missing":
        subject_quote = "오늘 첫 배송 차량이 아직 오지 않았습니다."
        request_quote = "현재 차량 위치와 도착 예정 시각을 확인해 주세요."
        subject, department, department_name = "첫 배송 도착 확인", "delivery", "배송 운영"
        ordered, received = copy.deepcopy(claim), copy.deepcopy(claim)
    else:
        subject_quote = "치킨 18개를 주문했습니다. 휴지 한 박스를 받았습니다."
        request_quote = "다른 상품이 온 경위와 회수 방법을 확인해 주세요."
        subject, department, department_name = "다른 상품 수령 확인", "warehouse", "출고 운영"
        ordered = {"product": "치킨", "quantity": 18, "unit": "EA",
                   "evidenceQuote": "치킨 18개를 주문했습니다."}
        received = {"product": "휴지", "quantity": 1, "unit": "BOX",
                    "evidenceQuote": "휴지 한 박스를 받았습니다."}
    body = {"storeId": source["intake"]["storeId"], "subject": source["intake"]["subject"],
            "type": source["type"], "referenceCaseId": source["id"],
            "text": " ".join((store_quote, subject_quote, request_quote))}
    model = {"summary": "통합검사용 작성 응답", "fields": {"subject": subject, "request": request_quote},
             "draftContext": {"subjectQuote": subject_quote, "requestQuote": request_quote},
             "orderedClaim": ordered, "receivedClaim": received,
             "storeClaim": {"name": source["store"]["name"], "evidenceQuote": store_quote},
             "issues": [], "questions": [], "unknowns": ["현장 원인은 센터 확인이 필요합니다."],
             "department": {"id": department, "name": department_name, "reason": "후속 확인 업무 제안"},
             "replyDraft": ""}
    return body, model


@pytest.fixture
def rig():
    backing = InMemoryCasStore()
    repo = CasCaseRepository(backing)
    budget = MemoryBudget()
    provider = Mock()
    service = CaseService(repo, LiveAnalyzer(budget=budget, client_factory=lambda: provider))
    # Patch the dependency boundary, not the routes or domain methods. These
    # sentinels also fail if an accidental fallback touches a real runtime/SDK.
    forbidden = Mock(side_effect=AssertionError("External provider/runtime access is forbidden"))
    with patch("server.handlers.service", return_value=service), \
         patch("server.handlers.get_runtime_storage", forbidden), \
         patch("server.live.OpenAI", forbidden), \
         patch("server.live.require_demo_api_key", forbidden), \
         TestClient(create_app()) as client:
        statuses = []
        client.event_hooks["response"].append(lambda response: statuses.append(response.status_code))
        yield SimpleNamespace(client=client, backing=backing, repo=repo, service=service,
                              provider=provider, budget=budget, statuses=statuses)
    forbidden.assert_not_called()
    provider.audio.transcriptions.create.assert_not_called()


def response_json(response, status=200, error=None):
    assert response.status_code == status, response.text
    result = response.json()
    if error:
        assert result["error"]["code"] == error, result
    return result


def arm_response(rig, model):
    rig.provider.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(
        finish_reason="stop", message=SimpleNamespace(refusal=None, content=json.dumps(model, ensure_ascii=False)))])


def rejected_without_write(rig, operation, status, code):
    before = rig.backing.read(rig.repo.key)
    response_json(operation(), status, code)
    # Compare the transport version too: a rejected operation may not even make
    # an identical-value write, increment a case revision, or append history.
    assert rig.backing.read(rig.repo.key) == before


@pytest.mark.parametrize("case_type", ["missing", "wrong"])
def test_new_text_to_center_final_reply_and_owner_read(rig, case_type):
    client = rig.client
    initial = response_json(client.get("/api/cases"))["cases"]
    assert len(initial) == 2
    source = next(case for case in initial if case["type"] == case_type)
    other = next(case for case in initial if case["type"] != case_type)
    body, model = authored_input(source)
    arm_response(rig, model)
    key = str(uuid.uuid4())
    headers = {"X-Idempotency-Key": key, "X-Demo-Role": "owner"}
    response_json(client.get("/api/intake-attempts/" + key), 404, "INTAKE_ATTEMPT_NOT_FOUND")
    created = response_json(client.post("/api/intake", json=body, headers=headers), 201)
    case_id, url = created["id"], "/api/cases/" + created["id"]
    assert created["revision"] == 0 and created["status"] == "draft"
    assert created["channel"] == "text" and created["linkedFixtureId"] == source["id"]
    assert created["sourceText"] == created["text"] == body["text"]
    for name in ("evidence", "wms", "tms", "asOf"):
        assert created[name] == source[name]
    saved = rig.backing.read(rig.repo.key)
    assert response_json(client.post("/api/intake", json=body, headers=headers), 201) == created
    assert rig.backing.read(rig.repo.key) == saved
    rejected_without_write(rig, lambda: client.post("/api/intake", headers=headers,
        json={**body, "text": "다른 접수 내용"}), 409, "IDEMPOTENCY_CONFLICT")
    rejected_without_write(rig, lambda: client.post(url + "/analyze", json={"mode": "replay"}),
                           409, "REPLAY_NOT_AVAILABLE")

    analyzed = response_json(client.post(url + "/analyze", json={"mode": "demo-live"}))
    current = response_json(client.get(url))
    assert analyzed["revision"] == current["revision"] == 1
    assert current["status"] == "review" and current["reviewConfirmed"] is False
    assert current["analysisMode"] == analyzed["mode"] == "demo-live"
    assert current["analysisRequestId"] == analyzed["requestId"] == "authored-asgi-1"
    assert current["analysis"] == analyzed["analysis"]
    assert current["transcript"] == [{"speaker": "점주", "text": body["text"], "start": 0, "end": 0}]
    assert current["sourceText"] == current["text"] == body["text"]
    assert current["departmentId"] == model["department"]["id"]
    assert current["intake"]["storeId"] == body["storeId"]
    expected_receipt = (None, None) if case_type == "missing" else (1, "BOX")
    assert (current["intake"]["quantity"], current["intake"]["unit"]) == expected_receipt
    assert current["reply"] is None and current["analysis"]["replyDraft"]
    original_analysis, original_transcript = copy.deepcopy(current["analysis"]), copy.deepcopy(current["transcript"])
    rig.provider.chat.completions.create.assert_called_once()
    assert rig.budget.reservations == [(15, "analysis-text", "authored-asgi-1")]
    assert rig.budget.completions == [("authored-asgi-1", True)]
    sent = json.loads(rig.provider.chat.completions.create.call_args.kwargs["messages"][1]["content"])
    assert sent["transcript"] == original_transcript
    assert "replayAnalysis" not in sent and "expected" not in sent

    def patch_form(form, changes, role="counselor"):
        return client.patch(url, json={"expectedRevision": form["revision"], **changes},
                            headers={"X-Demo-Role": role})

    rejected_without_write(rig, lambda: patch_form(current,
        {"intake": {"request": "점주 역할의 내부 접수 수정"}}, "owner"), 403, "READ_ONLY_ROLE")
    human_request = model["draftContext"]["requestQuote"] + " 상담원이 원문을 재확인한 요청입니다."
    current = response_json(patch_form(current, {"intake": {"request": human_request}}))
    assert current["revision"] == 2 and current["reviewConfirmed"] is False
    assert current["intake"]["request"] == human_request
    assert current["analysis"] == original_analysis and current["transcript"] == original_transcript
    rejected_without_write(rig, lambda: patch_form(current,
        {"selectedEvidence": [other["evidence"][0]["id"]]}), 422, "INVALID_EVIDENCE")
    stale_form = copy.deepcopy(current)
    current = response_json(patch_form(current, {"reviewConfirmed": True}))
    assert current["reviewConfirmed"] is True
    # A confirmed form edited again must lose its confirmation. Starting from
    # False would not detect removal of the intake-edit invalidation guard.
    human_request += " 확인 후 문의 내용을 추가로 정정했습니다."
    current = response_json(patch_form(current, {"intake": {"request": human_request}}))
    assert current["revision"] == 4 and current["reviewConfirmed"] is False
    assert current["intake"]["request"] == human_request
    assert current["sourceText"] == current["text"] == body["text"]
    assert current["analysis"] == original_analysis and current["transcript"] == original_transcript
    rejected_without_write(rig, lambda: patch_form(current, {"status": "handed_off"}), 422, "REVIEW_REQUIRED")
    current = response_json(patch_form(current, {"reviewConfirmed": True}))
    assert current["revision"] == 5 and current["reviewConfirmed"] is True
    # Changing evidence invalidates a previous confirmation; exercise WMS/TMS
    # selection through the same case-bound PATCH used by their detail screens.
    selected = [next(row["id"] for row in source["evidence"] if row["system"] == system)
                for system in ("WMS", "TMS")]
    current = response_json(patch_form(current, {"selectedEvidence": selected}))
    assert current["selectedEvidence"] == selected and current["reviewConfirmed"] is False
    rejected_without_write(rig, lambda: patch_form(current, {"status": "handed_off"}), 422, "REVIEW_REQUIRED")
    rejected_without_write(rig, lambda: patch_form(stale_form, {"reviewConfirmed": True}), 409, "STATE_CONFLICT")
    rejected_without_write(rig, lambda: client.patch(url, json={"reviewConfirmed": True}), 428, "REVISION_REQUIRED")
    current = response_json(patch_form(current, {"reviewConfirmed": True}))
    current = response_json(patch_form(current, {"status": "handed_off"}))
    assert current["revision"] == 8 and current["status"] == "handed_off"
    assert current["reviewConfirmed"] is True
    assert (current["intake"]["quantity"], current["intake"]["unit"]) == expected_receipt
    rejected_without_write(rig, lambda: patch_form(current, {"status": "closed"}, "center"),
                           422, "REPLY_REQUIRED")
    rejected_without_write(rig, lambda: patch_form(current, {"reply": "상담원 임의 회신"}),
                           403, "CENTER_ROLE_REQUIRED")
    interim = "합성 시연 중간 회신: 기록을 확인 중이며 현장 원인은 미확인입니다."
    current = response_json(patch_form(current, {"reply": interim,
        "pendingActions": ["센터 기록 대조"], "status": "in_progress"}, "center"))
    assert current["revision"] == 9 and current["status"] == "in_progress"
    assert current["replyRegisteredBy"] == "center" and current["replyRegisteredAt"]
    owner_interim = response_json(client.get(url, headers={"X-Demo-Role": "owner"}))
    assert owner_interim == current and owner_interim["reply"] == interim
    rejected_without_write(rig, lambda: patch_form(current, {"status": "closed"}, "center"),
                           422, "ACTIONS_PENDING")
    stale_center = copy.deepcopy(current)
    current = response_json(patch_form(current, {"pendingActions": ["센터 기록 대조", "점포 재확인"]}, "center"))
    rejected_without_write(rig, lambda: patch_form(stale_center, {"reply": "낡은 화면의 완료 응답",
        "pendingActions": [], "status": "closed"}, "center"), 409, "STATE_CONFLICT")
    final_reply = "합성 시연 최종 회신: 테스트 확인 절차를 마쳤습니다. 실제 물류 조치는 실행하지 않았습니다."
    closed = response_json(patch_form(current, {"reply": final_reply,
        "pendingActions": [], "status": "closed"}, "center"))
    assert closed["revision"] == 11 and closed["status"] == "closed"
    assert closed["reply"] == final_reply and closed["pendingActions"] == []
    assert closed["history"][-1]["actor"] == "center" and len(closed["history"]) == 12
    assert closed["analysis"] == original_analysis and closed["transcript"] == original_transcript
    assert closed["sourceText"] == closed["text"] == body["text"]
    assert closed["intake"]["request"] == human_request and closed["selectedEvidence"] == selected
    assert response_json(client.get(url, headers={"X-Demo-Role": "owner"})) == closed
    rejected_without_write(rig, lambda: patch_form(closed, {"reply": "점주 임의 변경"}, "owner"),
                           403, "READ_ONLY_ROLE")
    rejected_without_write(rig, lambda: client.post(url + "/analyze", json={"mode": "demo-live"}),
                           409, "ANALYSIS_STATE")
    assert response_json(client.post("/api/intake", json=body, headers=headers), 201) == closed
    assert response_json(client.get("/api/intake-attempts/" + key)) == closed
    reopened = CasCaseRepository(rig.backing)
    assert reopened.get(case_id) == closed
    assert {row["id"] for row in reopened.list()} == {row["id"] for row in initial} | {case_id}
    assert all(reopened.get(row["id"]) == row for row in initial)
    rig.provider.chat.completions.create.assert_called_once()
    assert Counter(rig.statuses) == {200: 16, 201: 3, 403: 3, 404: 1, 409: 5, 422: 5, 428: 1}


@pytest.mark.parametrize("case_type", ["missing", "wrong"])
def test_analysis_failure_preserves_new_intake_and_recovery(rig, case_type):
    """A provider failure stays an error; same-case explicit retry can recover."""
    initial = response_json(rig.client.get("/api/cases"))["cases"]
    source = next(case for case in initial if case["type"] == case_type)
    body, model = authored_input(source)
    key = str(uuid.uuid4())
    created = response_json(rig.client.post("/api/intake", json=body,
        headers={"X-Idempotency-Key": key}), 201)
    url = "/api/cases/" + created["id"]
    rig.provider.chat.completions.create.side_effect = RuntimeError("synthetic provider failure")
    rejected_without_write(rig, lambda: rig.client.post(url + "/analyze", json={"mode": "demo-live"}),
                           502, "LIVE_API_FAILED")
    assert response_json(rig.client.get(url)) == created
    assert rig.budget.completions == [("authored-asgi-1", False)]
    rig.provider.chat.completions.create.side_effect = None
    arm_response(rig, model)
    recovered = response_json(rig.client.post(url + "/analyze", json={"mode": "demo-live"}))
    current = response_json(rig.client.get(url))
    assert recovered["requestId"] == "authored-asgi-2" and recovered["revision"] == 1
    assert current["status"] == "review" and current["reviewConfirmed"] is False
    assert current["sourceText"] == body["text"] and current["reply"] is None
    assert len(CasCaseRepository(rig.backing).list()) == 3
    assert rig.budget.completions == [("authored-asgi-1", False), ("authored-asgi-2", True)]
    assert rig.provider.chat.completions.create.call_count == 2
    assert Counter(rig.statuses) == {200: 4, 201: 1, 502: 1}
