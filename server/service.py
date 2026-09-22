from __future__ import annotations

import copy
from datetime import datetime, timezone
import math
import uuid

from server.errors import DemoError
from server.live import LiveAnalyzer
from server.repository import CaseRepository
from server import intake_idempotency
from server import notifications

DEFAULT_DEPARTMENTS = [
    {"id": "delivery", "name": "배송 운영"},
    {"id": "warehouse", "name": "출고 운영"},
    {"id": "cs", "name": "고객 지원"},
]
INTAKE_KEYS = {"storeId", "subject", "quantity", "unit", "request"}
PATCH_KEYS = {"intake", "departmentId", "reviewConfirmed", "status", "reply", "replyTitle", "pendingActions", "selectedEvidence", "expectedRevision"}
TRANSITIONS = {"draft": {"draft", "review", "handed_off"}, "review": {"draft", "review", "handed_off"},
               "handed_off": {"handed_off", "in_progress", "closed"}, "in_progress": {"in_progress", "closed"}, "closed": {"closed"}}


def now():
    return datetime.now(timezone.utc).isoformat()


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


class CaseService:
    def __init__(self, repository: CaseRepository, analyzer=None):
        self.repo = repository
        self.analyzer = analyzer or LiveAnalyzer()

    def departments(self):
        return self.repo.fixtures().get("departments", DEFAULT_DEPARTMENTS)

    def list(self):
        return {"cases": self.repo.list()}

    def get(self, case_id):
        return self.repo.get(case_id)

    def intake_attempt(self, request_key):
        result = self.repo.intake_result(intake_idempotency.key_digest(request_key))
        if result is None:
            raise DemoError("INTAKE_ATTEMPT_NOT_FOUND", "이 접수 시도의 저장 결과를 아직 확인하지 못했습니다. 같은 내용으로 다시 확인하거나 재시도해 주세요.", 404)
        return result

    def intake(self, body, request_key=None):
        if set(body) - {"storeId", "subject", "text", "type", "referenceCaseId"}:
            raise DemoError("UNKNOWN_FIELD", "허용되지 않은 접수 필드입니다.")
        if any(not nonempty(body.get(k)) for k in ("storeId", "subject", "text")) or body.get("type") not in ("missing", "wrong"):
            raise DemoError("INVALID_INTAKE", "점포·문의 대상·문의 내용을 입력해 주세요.", 422)
        if len(body["text"]) > 8000:
            raise DemoError("INPUT_LIMIT", "문의 내용은 8,000자 이하여야 합니다.", 422)
        identity = intake_idempotency.request_identity(request_key, body)
        # A committed attempt is bound to its original validated input, not to a
        # later version of the fixture. create() still checks atomically for races.
        if identity is not None:
            existing = self.repo.intake_result(*identity)
            if existing is not None:
                return existing
        # Matching descriptions do not identify the same delivery or date.
        # A caller must explicitly select the source case before any records are joined.
        reference_id = body.get("referenceCaseId")
        linked = None
        if "referenceCaseId" in body:
            if not nonempty(reference_id):
                raise DemoError("INVALID_REFERENCE_CASE", "연결할 합성 사례 ID를 입력해 주세요.", 422)
            linked = next((c for c in self.repo.fixtures()["cases"] if c["id"] == reference_id), None)
            if not linked or any((linked.get("intake", {}).get(key, linked.get(key)) != body[key])
                                 for key in ("storeId", "subject")) or linked.get("type") != body["type"]:
                raise DemoError("INVALID_REFERENCE_CASE", "선택한 사례의 점포·문의 대상·유형이 접수와 일치하지 않습니다.", 422)
        store = copy.deepcopy(linked.get("store")) if linked and linked.get("store") else {
            "id": body["storeId"], "name": linked.get("storeName", body["storeId"]) if linked else body["storeId"]}
        case = {"id": "INT-" + uuid.uuid4().hex[:8].upper(), "type": body["type"], "channel": "text",
                "synthetic": True, "title": body["subject"], "storeId": body["storeId"], "subject": body["subject"],
                "store": store, "storeName": store["name"], "sourceText": body["text"],
                "text": body["text"], "status": "draft", "createdAt": now(), "updatedAt": now(),
                "intake": {"storeId": body["storeId"], "subject": body["subject"], "quantity": None, "unit": None, "request": body["text"]},
                "departmentId": None, "reviewConfirmed": False, "reply": None, "pendingActions": [], "selectedEvidence": [],
                "evidence": copy.deepcopy(linked.get("evidence", [])) if linked else [],
                "linkedFixtureId": linked["id"] if linked else None,
                "history": [{"at": now(), "actor": "owner", "action": "text_intake", "message": "합성 문의 접수"}],
                "transcript": [{"speaker": "점주", "text": body["text"], "start": 0, "end": 0}], "analysis": None}
        if linked:
            for key in ("wms", "tms", "asOf", "expected", "received", "provenance"):
                if key in linked:
                    case[key] = copy.deepcopy(linked[key])
        return self.repo.create(case, identity=identity)

    def _validate_source_context(self, case):
        source_id = case.get("linkedFixtureId") or case["id"]
        source = next((c for c in self.repo.fixtures()["cases"] if c["id"] == source_id), None)
        store_id = case.get("intake", {}).get("storeId")
        if source and nonempty(store_id):
            source_store = source.get("intake", {}).get("storeId") or source.get("store", {}).get("id")
            if store_id != source_store or case.get("type") != source.get("type"):
                raise DemoError("SOURCE_CONTEXT_MISMATCH", "연결된 물류 근거와 접수 점포가 다릅니다. 원본 사례의 점포를 확인해 주세요.", 422)
        valid = {e.get("id") for e in source.get("evidence", [])} if source else set()
        if any(e not in valid for e in case.get("selectedEvidence", [])):
            raise DemoError("INVALID_EVIDENCE", "현재 원본 사례에 속하는 근거만 선택할 수 있습니다.", 422)

    def analyze(self, case_id, mode):
        case = self.repo.get(case_id)
        if case.get("status", "draft") not in ("draft", "review"):
            raise DemoError("ANALYSIS_STATE", "이관된 접수는 분석 결과로 덮어쓰지 않습니다.", 409)
        if mode == "replay":
            fixture = next((c for c in self.repo.fixtures()["cases"] if c["id"] == case_id), None)
            if not fixture:
                raise DemoError("REPLAY_NOT_AVAILABLE", "새 텍스트 문의에는 사전 리플레이가 없습니다. 실제 AI 분석을 선택해 주세요.", 409)
            analysis = fixture.get("replayAnalysis") or fixture.get("analysis")
            if not analysis:
                raise DemoError("REPLAY_NOT_READY", "사전 계산된 분석 자료가 없습니다.", 503)
            result = {"transcript": copy.deepcopy(fixture.get("transcript", [])), "analysis": copy.deepcopy(analysis),
                      "mode": "replay", "requestId": "replay-" + uuid.uuid4().hex}
        elif mode == "demo-live":
            result = self.analyzer.analyze(case, self.departments())
        else:
            raise DemoError("INVALID_MODE", "replay 또는 demo-live 모드를 선택해 주세요.", 422)
        def save(current):
            if current["revision"] != case["revision"]:
                raise DemoError("STATE_CONFLICT", "분석 중 접수가 수정되었습니다. 최신 접수를 확인한 뒤 다시 분석해 주세요.", 409)
            if current.get("status", "draft") not in ("draft", "review"):
                raise DemoError("STATE_CHANGED", "분석 중 접수가 이관되어 결과를 저장하지 않았습니다.", 409)
            current.update({"analysis": result["analysis"], "transcript": result["transcript"],
                            "analysisMode": mode, "analysisRequestId": result["requestId"], "updatedAt": now(),
                            "status": "review", "reviewConfirmed": False})
            current["intake"] = copy.deepcopy(result["analysis"]["fields"])
            current["departmentId"] = result["analysis"]["department"]["id"] or None
            current.setdefault("history", []).append({"at": now(), "actor": "counselor", "action": "analyzed",
                "message": "사전 분석 리플레이" if mode == "replay" else "실제 AI 분석"})
            return current
        saved = self.repo.update(case_id, save)
        result["revision"] = saved["revision"]
        return result

    def reply_draft(self, case_id, body, role=None):
        if role != "center":
            raise DemoError("CENTER_ROLE_REQUIRED", "AI 회신 초안은 센터 역할에서 생성할 수 있습니다.", 403)
        if not isinstance(body, dict) or set(body) - {"mode", "expectedRevision", "centerContext"}:
            raise DemoError("INVALID_INPUT", "회신 생성 요청 형식을 확인해 주세요.", 422)
        center_context = body.get("centerContext")
        if "centerContext" in body:
            if (not isinstance(center_context, dict) or set(center_context) - {"pendingActions", "reply", "replyTitle"}
                    or not {"pendingActions", "reply"}.issubset(center_context)
                    or not isinstance(center_context["reply"], str) or len(center_context["reply"]) > 8000
                    or ("replyTitle" in center_context and (not isinstance(center_context["replyTitle"], str) or len(center_context["replyTitle"]) > 160))
                    or not isinstance(center_context["pendingActions"], list) or len(center_context["pendingActions"]) > 50
                    or any(not nonempty(value) or len(value) > 8000 for value in center_context["pendingActions"])):
                raise DemoError("INVALID_CENTER_CONTEXT", "센터 초안의 회신·남은 조치 형식을 확인해 주세요.", 422)
        revision = body.get("expectedRevision")
        if "expectedRevision" not in body:
            raise DemoError("REVISION_REQUIRED", "현재 확인한 접수 버전이 필요합니다.", 428)
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
            raise DemoError("INVALID_REVISION", "접수 버전은 0 이상의 정수여야 합니다.", 422)
        mode = body.get("mode")
        if mode not in ("replay", "demo-live"):
            raise DemoError("INVALID_MODE", "replay 또는 demo-live 모드를 선택해 주세요.", 422)
        case = self.repo.get(case_id)
        if case["revision"] != revision:
            raise DemoError("STATE_CONFLICT", "접수가 변경되었습니다. 최신 내용을 확인해 주세요.", 409)
        if case.get("status") not in ("handed_off", "in_progress"):
            raise DemoError("REPLY_DRAFT_STATE", "센터에 이관된 처리 중 접수에서만 회신 초안을 생성할 수 있습니다.", 409)
        if mode == "replay":
            text = (case.get("analysis") or {}).get("replyDraft")
            if not nonempty(text):
                raise DemoError("REPLAY_NOT_AVAILABLE", "저장된 회신 초안이 없습니다. 실제 AI 생성을 선택해 주세요.", 409)
            subject = (case.get("intake") or {}).get("subject") or case.get("title") or "접수 문의"
            subject = " ".join(str(subject).split())
            for assertion in ("완료", "확정", "정상 출고", "정상출고", "보상 승인", "보상승인"):
                subject = subject.replace(assertion, "")
            title = (subject.strip() or "접수 문의")[:94] + " 확인 안내"
            result = {"replyTitle": title, "replyDraft": text, "mode": "replay", "requestId": "replay-" + uuid.uuid4().hex}
        else:
            result = self.analyzer.reply_draft(copy.deepcopy(case), center_context=copy.deepcopy(center_context))
        current = self.repo.get(case_id)
        if current["revision"] != revision or current.get("status") != case.get("status"):
            raise DemoError("STATE_CONFLICT", "초안 생성 중 접수가 변경되었습니다. 최신 내용을 확인한 뒤 다시 생성해 주세요.", 409)
        # A generated draft is not a registered reply. No case/history/outbox write.
        return {**result, "revision": revision}

    def patch(self, case_id, body, role="counselor"):
        if role not in ("counselor", "center", "owner"):
            raise DemoError("INVALID_ROLE", "허용되지 않은 데모 역할입니다.", 403)
        if role == "owner":
            raise DemoError("READ_ONLY_ROLE", "점주 역할에서는 센터 처리 상태를 변경할 수 없습니다.", 403)
        if set(body) - PATCH_KEYS:
            raise DemoError("IMMUTABLE_SOURCE", "원본 근거·정답·출처는 접수 수정으로 변경할 수 없습니다.", 422)
        if "expectedRevision" not in body:
            raise DemoError("REVISION_REQUIRED", "화면에서 확인한 접수 버전이 필요합니다. 접수를 다시 열어 주세요.", 428)
        expected_revision = body["expectedRevision"]
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 0:
            raise DemoError("INVALID_REVISION", "접수 버전은 0 이상의 정수여야 합니다.", 422)
        if role != "center" and ({"reply", "replyTitle", "pendingActions"} & set(body)):
            raise DemoError("CENTER_ROLE_REQUIRED", "회신·조치 등록은 센터 역할에서만 가능합니다.", 403)
        def mutate(case):
            # The repository invokes this transform inside its read-modify-write lock.
            if case["revision"] != expected_revision:
                raise DemoError("STATE_CONFLICT", "다른 작업자가 접수를 수정했습니다. 최신 내용을 다시 확인해 주세요.", 409)
            notifications.validate_stored_notification_outbox(case)
            old_status = case.get("status", "draft")
            old_reply = case.get("reply")
            target = body.get("status", old_status)
            if target not in TRANSITIONS.get(old_status, set()):
                raise DemoError("INVALID_TRANSITION", "허용되지 않은 상태 전이입니다.", 409)
            if target in ("in_progress", "closed") and role != "center":
                raise DemoError("CENTER_ROLE_REQUIRED", "진행·종결은 센터 역할에서 처리합니다.", 403)
            if role == "center" and old_status in ("draft", "review"):
                raise DemoError("HANDOFF_REQUIRED", "상담 검토·이관 이후 센터에서 처리할 수 있습니다.", 409)
            if old_status in ("handed_off", "in_progress", "closed") and ({"intake", "departmentId", "reviewConfirmed", "selectedEvidence"} & set(body)):
                raise DemoError("INTAKE_LOCKED", "이관된 접수의 확인 대상과 근거는 변경할 수 없습니다.", 409)
            if old_status == "closed" and body:
                raise DemoError("CASE_CLOSED", "종결된 접수는 변경할 수 없습니다.", 409)
            if "intake" in body:
                intake = body["intake"]
                if not isinstance(intake, dict) or set(intake) - INTAKE_KEYS:
                    raise DemoError("INVALID_INTAKE", "허용되지 않은 접수 필드입니다.", 422)
                quantity = intake.get("quantity")
                if quantity is not None and (isinstance(quantity, bool) or not isinstance(quantity, (int, float)) or not math.isfinite(quantity) or quantity < 0):
                    raise DemoError("INVALID_QUANTITY", "수량은 0 이상의 숫자 또는 미확인이어야 합니다.", 422)
                for key, value in intake.items():
                    if key != "quantity" and value is not None and not isinstance(value, str):
                        raise DemoError("INVALID_INTAKE", "접수 필드 형식이 올바르지 않습니다.", 422)
                case.setdefault("intake", {}).update(copy.deepcopy(intake))
                case["reviewConfirmed"] = False
                self._validate_source_context(case)
            if "departmentId" in body:
                department = body["departmentId"]
                if department is not None and department not in {d["id"] for d in self.departments()}:
                    raise DemoError("INVALID_DEPARTMENT", "등록된 담당 부서를 선택해 주세요.", 422)
                case["departmentId"] = department
                case["reviewConfirmed"] = False
            if "selectedEvidence" in body:
                selected = body["selectedEvidence"]
                valid = {e.get("id") for e in case.get("evidence", [])}
                if not isinstance(selected, list) or any(not isinstance(e, str) or e not in valid for e in selected):
                    raise DemoError("INVALID_EVIDENCE", "현재 문의에 연결된 원본 근거만 선택할 수 있습니다.", 422)
                if selected != case.get("selectedEvidence", []):
                    case["reviewConfirmed"] = False
                case["selectedEvidence"] = selected
                self._validate_source_context(case)
            if "reviewConfirmed" in body:
                if not isinstance(body["reviewConfirmed"], bool):
                    raise DemoError("INVALID_CONFIRMATION", "검토 확인 값이 올바르지 않습니다.", 422)
                case["reviewConfirmed"] = body["reviewConfirmed"]
            if "replyTitle" in body:
                if not nonempty(body["replyTitle"]) or len(body["replyTitle"]) > 160:
                    raise DemoError("INVALID_REPLY_TITLE", "회신 제목을 1~160자로 입력해 주세요.", 422)
                case["replyTitle"] = body["replyTitle"].strip()
            if "reply" in body:
                if not nonempty(body["reply"]):
                    raise DemoError("EMPTY_REPLY", "센터 회신을 입력해 주세요.", 422)
                case["reply"] = body["reply"].strip()
                case["replyRegisteredAt"] = now()
                case["replyRegisteredBy"] = "center"
            if "pendingActions" in body:
                if not isinstance(body["pendingActions"], list) or any(not nonempty(x) for x in body["pendingActions"]):
                    raise DemoError("INVALID_ACTIONS", "미완료 조치는 문자열 목록이어야 합니다.", 422)
                case["pendingActions"] = body["pendingActions"]
            if target == "handed_off":
                fields = case.get("intake", {})
                if not nonempty(fields.get("storeId")) or not nonempty(fields.get("subject")) or not nonempty(case.get("departmentId")):
                    raise DemoError("HANDOFF_FIELDS_REQUIRED", "점포·문의 대상·담당 부서를 확인해 주세요. 미확인 수량은 질문으로 남길 수 있습니다.", 422)
                if case["departmentId"] not in {d["id"] for d in self.departments()}:
                    raise DemoError("INVALID_DEPARTMENT", "등록된 담당 부서를 선택해 주세요.", 422)
                self._validate_source_context(case)
                if case.get("reviewConfirmed") is not True:
                    raise DemoError("REVIEW_REQUIRED", "상담사가 접수 대상과 담당 부서를 확인한 뒤 이관할 수 있습니다.", 422)
            if target == "closed":
                if not nonempty(case.get("reply")) or case.get("replyRegisteredBy") != "center":
                    raise DemoError("REPLY_REQUIRED", "센터 회신 등록 후 종결할 수 있습니다.", 422)
                if case.get("pendingActions"):
                    raise DemoError("ACTIONS_PENDING", "미완료 조치가 남아 있어 종결할 수 없습니다.", 422)
            case["status"] = target
            case["updatedAt"] = now()
            case.setdefault("history", []).append({"at": now(), "actor": role, "action": target,
                "message": "센터 회신 등록" if "reply" in body else "접수 상태 저장"})
            notifications.append_notification_intents(case, previous_status=old_status,
                previous_reply=old_reply, created_at=case["updatedAt"])
            return case
        return self.repo.update(case_id, mutate)
