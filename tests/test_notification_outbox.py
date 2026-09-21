"""Offline notification intent storage: temporary JSON and in-memory CAS only."""
from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from server.cas_repository import CasCaseRepository
from server.cas_store import CasConflict, InMemoryCasStore
from server.errors import DemoError
from server.repository import JsonCaseRepository
from server.service import CaseService


FIELDS = {"schemaVersion", "id", "caseId", "caseRevision", "kind", "channel",
          "recipientRole", "recipientRef", "createdAt", "status", "reason"}
SENTINEL = "원문 욕설 SENTINEL 010-9876-5432 https://private.invalid/token"


class ObservedStore:
    def __init__(self, backing):
        self.backing, self.attempts = backing, []
        self.before_write = None
        self.failure = None

    def read(self, key):
        return self.backing.read(key)

    def compare_and_swap(self, key, payload, expected_version):
        self.attempts.append(copy.deepcopy(payload))
        hook, self.before_write = self.before_write, None
        if hook:
            hook()
        if self.failure == "definite":
            raise CasConflict()
        result = self.backing.compare_and_swap(key, payload, expected_version)
        if self.failure == "response_lost":
            raise TimeoutError("synthetic response lost after commit")
        return result


def seed(case_id, case_type, store_id):
    intake = {"storeId": store_id, "subject": "합성 문의", "quantity": None,
              "unit": None, "request": SENTINEL}
    return {"id": case_id, "type": case_type, "revision": 0, "status": "review",
            "store": {"id": "MUST-NOT-USE-TOP-LEVEL"}, "sourceText": SENTINEL,
            "transcript": [{"speaker": "점주", "text": SENTINEL}],
            "intake": intake, "reviewConfirmed": True, "departmentId": "delivery",
            "reply": None, "pendingActions": [], "selectedEvidence": [],
            "evidence": [], "history": [],
            "replayAnalysis": {"fields": copy.deepcopy(intake),
                               "department": {"id": "delivery"}}}


@pytest.fixture(params=["json", "cas"])
def rig(request, tmp_path, monkeypatch):
    fixture = tmp_path / "fixtures.json"
    cases = [seed("SYN-NOTIFY-A", "missing", "STORE-A"),
             seed("SYN-NOTIFY-B", "wrong", "STORE-B")]
    fixture.write_text(json.dumps({"cases": cases}, ensure_ascii=False), encoding="utf-8")
    forbidden = Mock(side_effect=AssertionError("External provider must not be used"))
    monkeypatch.setattr("server.live.OpenAI", forbidden)
    monkeypatch.setattr("server.live.require_demo_api_key", forbidden)
    analyzer = Mock(analyze=forbidden)
    if request.param == "json":
        path = tmp_path / "cases.json"
        path.write_text(json.dumps({"cases": cases}, ensure_ascii=False), encoding="utf-8")
        repo = JsonCaseRepository(path, fixture)
        reopen = lambda: JsonCaseRepository(path, fixture)
        snapshot = lambda: path.read_bytes()
        backing = observed = None
    else:
        backing = InMemoryCasStore()
        backing.compare_and_swap("notification-test", {"cases": cases}, None)
        observed = ObservedStore(backing)
        repo = CasCaseRepository(observed, "notification-test", fixture, max_attempts=3)
        reopen = lambda: CasCaseRepository(backing, "notification-test", fixture)
        snapshot = lambda: backing.read("notification-test")
    yield SimpleNamespace(service=CaseService(repo, analyzer), repo=repo, kind=request.param,
                          backing=backing, observed=observed, snapshot=snapshot,
                          reopen=reopen, fixture=fixture, analyzer=analyzer)
    forbidden.assert_not_called()


def patch_fresh(rig, body, role="counselor", case_id="SYN-NOTIFY-A"):
    current = rig.service.get(case_id)
    return rig.service.patch(case_id, {"expectedRevision": current["revision"], **body}, role)


def handoff(rig, case_id="SYN-NOTIFY-A"):
    return patch_fresh(rig, {"status": "handed_off"}, case_id=case_id)


def assert_event(event, case, kind, channel, role, source):
    assert set(event) == FIELDS
    assert event["schemaVersion"] == 1 and type(event["schemaVersion"]) is int
    assert event["caseId"] == case["id"]
    assert event["caseRevision"] == case["revision"]
    assert event["createdAt"] == case["updatedAt"]
    assert (event["kind"], event["channel"], event["recipientRole"]) == (kind, channel, role)
    reference = None if source is None else role + ":" + hashlib.sha256(source.encode()).hexdigest()
    assert event["recipientRef"] == reference
    assert event["status"] == "not_connected"
    assert event["reason"] == ("missing_recipient" if source is None else "delivery_not_configured")
    material = [1, case["id"], case["revision"], kind, channel, role, reference]
    expected_id = hashlib.sha256(json.dumps(material, ensure_ascii=False,
                                           separators=(",", ":")).encode()).hexdigest()
    assert event["id"] == expected_id


@pytest.mark.parametrize("case_id", ["SYN-NOTIFY-A", "SYN-NOTIFY-B"])
def test_handoff_interim_final_are_atomic_and_reopen_with_same_revision(rig, case_id):
    saved = handoff(rig, case_id)
    assert len(saved.get("notificationOutbox", [])) == 1
    assert_event(saved["notificationOutbox"][0], saved, "handoff", "teams", "center", "delivery")
    assert rig.reopen().get(case_id) == saved
    previous = copy.deepcopy(saved["notificationOutbox"])
    saved = patch_fresh(rig, {"status": "handed_off"}, case_id=case_id)
    assert saved["notificationOutbox"] == previous
    saved = patch_fresh(rig, {"status": "in_progress", "reply": "센터 확인 중",
                              "pendingActions": ["확인 필요"]}, "center", case_id)
    assert len(saved["notificationOutbox"]) == 2
    assert_event(saved["notificationOutbox"][-1], saved, "interim_reply", "teams", "counselor", case_id)
    previous = copy.deepcopy(saved["notificationOutbox"])
    saved = patch_fresh(rig, {"reply": "  센터 확인 중  "}, "center", case_id)
    assert saved["notificationOutbox"] == previous
    saved = patch_fresh(rig, {"pendingActions": []}, "center", case_id)
    assert saved["notificationOutbox"] == previous
    # A final transition creates final intents even without a reply in this PATCH.
    saved = patch_fresh(rig, {"status": "closed"}, "center", case_id)
    assert saved["reply"] == "센터 확인 중"
    assert len(saved["notificationOutbox"]) == 4
    assert_event(saved["notificationOutbox"][-2], saved, "final_reply", "teams", "counselor", case_id)
    assert_event(saved["notificationOutbox"][-1], saved, "final_reply", "kakao", "owner", saved["intake"]["storeId"])
    assert len({event["id"] for event in saved["notificationOutbox"]}) == 4
    assert rig.reopen().get(case_id) == saved


def test_reply_and_close_in_one_patch_create_only_two_final_intents(rig):
    before = handoff(rig)
    saved = patch_fresh(rig, {"reply": "최종 회신", "status": "closed"}, "center")
    assert len(saved["notificationOutbox"]) == len(before["notificationOutbox"]) + 2
    assert [x["kind"] for x in saved["notificationOutbox"]] == ["handoff", "final_reply", "final_reply"]
    assert rig.reopen().get(saved["id"]) == saved


def test_legacy_read_draft_edit_and_analysis_do_not_create_or_migrate_intents(rig):
    before = rig.snapshot()
    assert len(rig.service.list()["cases"]) == 2
    assert "notificationOutbox" not in rig.service.get("SYN-NOTIFY-A")
    assert rig.snapshot() == before
    edited = patch_fresh(rig, {"departmentId": "warehouse", "intake": {"request": "修正"}})
    assert "notificationOutbox" not in edited
    rig.service.analyze(edited["id"], "replay")
    assert "notificationOutbox" not in rig.reopen().get(edited["id"])


@pytest.mark.parametrize("scenario,code,status", [
    ("unconfirmed", "REVIEW_REQUIRED", 422), ("owner", "READ_ONLY_ROLE", 403),
    ("pending", "ACTIONS_PENDING", 422), ("stale", "STATE_CONFLICT", 409),
    ("inject", "IMMUTABLE_SOURCE", 422), ("wrong_role", "CENTER_ROLE_REQUIRED", 403),
    ("empty_reply", "EMPTY_REPLY", 422), ("closed", "CASE_CLOSED", 409),
])
def test_rejected_patch_does_not_store_or_produce_intents(rig, monkeypatch, scenario, code, status):
    from server import notifications
    role = "counselor"
    body = {"status": "handed_off"}
    if scenario == "unconfirmed":
        patch_fresh(rig, {"reviewConfirmed": False})
    elif scenario == "owner":
        role = "owner"
    elif scenario == "pending":
        handoff(rig)
        body, role = {"reply": "회신", "pendingActions": ["미완료"], "status": "closed"}, "center"
    elif scenario == "stale":
        handoff(rig)
        body = {"expectedRevision": 0, "status": "handed_off"}
    elif scenario == "inject":
        body = {"notificationOutbox": [{"status": "sent"}]}
    elif scenario == "wrong_role":
        body = {"reply": "상담원 회신"}
    elif scenario == "empty_reply":
        handoff(rig)
        body, role = {"reply": "  "}, "center"
    elif scenario == "closed":
        handoff(rig)
        patch_fresh(rig, {"reply": "최종 회신", "status": "closed"}, "center")
        body, role = {"status": "closed"}, "center"
    before = rig.snapshot()
    producer = Mock(wraps=notifications.append_notification_intents)
    monkeypatch.setattr(notifications, "append_notification_intents", producer)
    with pytest.raises(DemoError) as caught:
        patch_fresh(rig, body, role)
    assert (caught.value.code, caught.value.status) == (code, status)
    assert rig.snapshot() == before
    producer.assert_not_called()


def test_intent_contains_no_source_reply_contact_or_url_and_uses_intake_store_only(rig):
    # Synthetic free-form identifiers exercise the no-PI-copy boundary.
    created = rig.service.intake({"type": "missing", "storeId": SENTINEL,
                                  "subject": "합성 문의", "text": SENTINEL})
    cid = created["id"]
    patch_fresh(rig, {"departmentId": "delivery", "reviewConfirmed": True,
                      "status": "handed_off"}, case_id=cid)
    saved = patch_fresh(rig, {"reply": SENTINEL, "status": "closed"}, "center", cid)
    encoded = json.dumps(saved["notificationOutbox"], ensure_ascii=False)
    for fragment in (SENTINEL, "욕설", "010-9876-5432", "https://", "MUST-NOT-USE-TOP-LEVEL"):
        assert fragment not in encoded
    assert_event(saved["notificationOutbox"][-1], saved, "final_reply", "kakao", "owner", SENTINEL)
    assert saved["sourceText"] == SENTINEL and saved["reply"] == SENTINEL


@pytest.mark.parametrize("missing", [None, "", "   "])
def test_legacy_missing_intake_store_has_missing_recipient_without_store_fallback(rig, missing):
    handoff(rig)
    # Legacy store is seeded directly; clients cannot remove identity after handoff.
    rig.repo.update("SYN-NOTIFY-A", lambda row: {**row, "intake": {**row["intake"], "storeId": missing}})
    saved = patch_fresh(rig, {"reply": "회신", "status": "closed"}, "center")
    assert_event(saved["notificationOutbox"][-1], saved, "final_reply", "kakao", "owner", None)


def test_two_cases_do_not_share_event_ids_or_counselor_and_owner_references(rig):
    results = []
    for cid in ("SYN-NOTIFY-A", "SYN-NOTIFY-B"):
        handoff(rig, cid)
        results.append(patch_fresh(rig, {"reply": "회신", "status": "closed"}, "center", cid))
    left, right = [row["notificationOutbox"] for row in results]
    assert {x["id"] for x in left}.isdisjoint(x["id"] for x in right)
    assert {x["caseId"] for x in left} == {"SYN-NOTIFY-A"}
    assert {x["caseId"] for x in right} == {"SYN-NOTIFY-B"}
    assert left[-1]["recipientRef"] != right[-1]["recipientRef"]
    assert left[-2]["recipientRef"] != right[-2]["recipientRef"]


def test_legacy_unregistered_department_cannot_become_an_intent_recipient(rig):
    rig.repo.update("SYN-NOTIFY-A", lambda row: {**row, "departmentId": "UNREGISTERED-CENTER"})
    before = rig.snapshot()
    with pytest.raises(DemoError) as caught:
        handoff(rig)
    assert (caught.value.code, caught.value.status) == ("INVALID_DEPARTMENT", 422)
    assert rig.snapshot() == before


def test_custom_fixture_department_is_used_instead_of_hardcoded_defaults(rig):
    fixture = json.loads(rig.fixture.read_text(encoding="utf-8"))
    fixture["departments"] = [{"id": "custom-center", "name": "합성 추가 센터"}]
    rig.fixture.write_text(json.dumps(fixture), encoding="utf-8")
    rig.repo.update("SYN-NOTIFY-A", lambda row: {**row, "departmentId": "custom-center"})
    saved = handoff(rig)
    assert len(saved["notificationOutbox"]) == 1
    assert_event(saved["notificationOutbox"][0], saved, "handoff", "teams", "center", "custom-center")


def test_json_failure_before_replace_preserves_case_and_outbox_together(tmp_path, monkeypatch):
    path, fixture = tmp_path / "cases.json", tmp_path / "fixtures.json"
    document = {"cases": [seed("SYN-NOTIFY-A", "missing", "STORE-A")]}
    for target in (path, fixture):
        target.write_text(json.dumps(document), encoding="utf-8")
    repo = JsonCaseRepository(path, fixture)
    before = path.read_bytes()
    calls = []
    def fail_replace(source, destination):
        pending = json.loads(Path(source).read_text(encoding="utf-8"))
        calls.append(pending)
        assert pending["cases"][0]["status"] == "handed_off"
        assert len(pending["cases"][0].get("notificationOutbox", [])) == 1
        raise OSError("synthetic failure before replace")
    monkeypatch.setattr("server.repository.os.replace", fail_replace)
    with pytest.raises(OSError, match="synthetic failure"):
        CaseService(repo, analyzer=Mock()).patch("SYN-NOTIFY-A", {"expectedRevision": 0, "status": "handed_off"})
    assert len(calls) == 1
    assert path.read_bytes() == before
    assert "notificationOutbox" not in repo.get("SYN-NOTIFY-A")


@pytest.fixture
def cas_rig(tmp_path):
    fixture = tmp_path / "fixtures.json"
    cases = [seed("SYN-NOTIFY-A", "missing", "STORE-A"), seed("SYN-NOTIFY-B", "wrong", "STORE-B")]
    fixture.write_text(json.dumps({"cases": cases}), encoding="utf-8")
    backing = InMemoryCasStore()
    backing.compare_and_swap("notification-test", {"cases": cases}, None)
    observed = ObservedStore(backing)
    repo = CasCaseRepository(observed, "notification-test", fixture, max_attempts=3)
    return SimpleNamespace(service=CaseService(repo, analyzer=Mock()), repo=repo,
                           backing=backing, observed=observed,
                           reopen=lambda: CasCaseRepository(backing, "notification-test", fixture),
                           snapshot=lambda: backing.read("notification-test"))


def test_cas_definite_noncommit_retries_one_set_and_preserves_stored_document(cas_rig, monkeypatch):
    from server import notifications
    rig = cas_rig
    before = rig.snapshot()
    rig.observed.failure = "definite"
    producer = Mock(wraps=notifications.append_notification_intents)
    monkeypatch.setattr(notifications, "append_notification_intents", producer)
    with pytest.raises(DemoError) as caught:
        handoff(rig)
    assert (caught.value.code, caught.value.status) == ("STORAGE_BUSY", 503)
    assert rig.snapshot() == before
    producer.assert_called_once()
    assert len(rig.observed.attempts) == 3
    assert all(len(x["cases"][0]["notificationOutbox"]) == 1 for x in rig.observed.attempts)


@pytest.mark.parametrize("same_case", [False, True])
def test_cas_competing_write_does_not_repeat_intent_transform(cas_rig, monkeypatch, same_case):
    from server import notifications
    rig = cas_rig
    winner = rig.reopen()
    target = "SYN-NOTIFY-A" if same_case else "SYN-NOTIFY-B"
    rig.observed.before_write = lambda: winner.update(target, lambda row: {**row, "raceMarker": "winner"})
    producer = Mock(wraps=notifications.append_notification_intents)
    monkeypatch.setattr(notifications, "append_notification_intents", producer)
    if same_case:
        with pytest.raises(DemoError) as caught:
            handoff(rig)
        assert (caught.value.code, caught.value.status) == ("STATE_CONFLICT", 409)
        assert "notificationOutbox" not in winner.get(target)
        assert winner.get(target)["status"] == "review"
        assert len(rig.observed.attempts) == 1
    else:
        saved = handoff(rig)
        assert len(saved["notificationOutbox"]) == 1
        assert rig.reopen().get(saved["id"]) == saved
        assert len(rig.observed.attempts) == 2
        assert rig.observed.attempts[0]["cases"][0] == rig.observed.attempts[1]["cases"][0]
    producer.assert_called_once()
    assert winner.get(target)["raceMarker"] == "winner"


def test_response_lost_after_cas_commit_is_reconciled_by_read_not_second_event(cas_rig):
    rig = cas_rig
    rig.observed.failure = "response_lost"
    with pytest.raises(TimeoutError, match="response lost"):
        handoff(rig)
    saved = rig.reopen().get("SYN-NOTIFY-A")
    assert saved["revision"] == 1 and saved["status"] == "handed_off"
    assert len(saved["notificationOutbox"]) == 1
    before = rig.snapshot()
    rig.observed.failure = None
    with pytest.raises(DemoError) as caught:
        rig.service.patch(saved["id"], {"expectedRevision": 0, "status": "handed_off"})
    assert caught.value.code == "STATE_CONFLICT"
    assert rig.snapshot() == before
    resaved = handoff(rig)
    assert resaved["notificationOutbox"] == saved["notificationOutbox"]


def test_producer_suppresses_same_event_id_and_ignores_timestamp_for_identity():
    from server.notifications import append_notification_intents
    case = seed("SYN-NOTIFY-A", "missing", "STORE-A")
    case["status"] = "handed_off"
    append_notification_intents(case, previous_status="review", previous_reply=None, created_at="2026-09-22T00:00:00+09:00")
    before = copy.deepcopy(case["notificationOutbox"])
    append_notification_intents(case, previous_status="review", previous_reply=None, created_at="2026-09-22T00:01:00+09:00")
    assert case["notificationOutbox"] == before
    assert len(before) == 1


@pytest.mark.parametrize("bad", [None, {}, [None], [{"id": "broken"}]])
def test_malformed_stored_outbox_is_preserved_and_rejected_without_overwrite(rig, bad):
    rig.repo.update("SYN-NOTIFY-A", lambda row: {**row, "notificationOutbox": bad})
    before = rig.snapshot()
    with pytest.raises(DemoError) as caught:
        handoff(rig)
    assert (caught.value.code, caught.value.status) == ("STORAGE_INVALID", 503)
    assert rig.snapshot() == before


def install_stored_intent(rig, *, event_revision, role="counselor", reference_source="SYN-NOTIFY-A"):
    """Independent legacy payload, including a self-consistent but untrusted ID."""
    case = seed("SYN-NOTIFY-A", "missing", "STORE-A")
    case.update(revision=10, status="in_progress", reply="기존 회신", replyRegisteredBy="center")
    kind = {"center": "handoff", "owner": "final_reply", "counselor": "interim_reply"}[role]
    channel = "kakao" if role == "owner" else "teams"
    reference = role + ":" + hashlib.sha256(reference_source.encode()).hexdigest()
    material = [1, case["id"], event_revision, kind, channel, role, reference]
    event = {"schemaVersion": 1, "id": hashlib.sha256(json.dumps(material, ensure_ascii=False,
                separators=(",", ":")).encode()).hexdigest(), "caseId": case["id"],
             "caseRevision": event_revision, "kind": kind, "channel": channel,
             "recipientRole": role, "recipientRef": reference,
             "createdAt": "2026-09-21T12:00:00+09:00", "status": "not_connected",
             "reason": "delivery_not_configured"}
    case["notificationOutbox"] = [event]
    if rig.kind == "json":
        document = json.loads(rig.repo.path.read_text(encoding="utf-8"))
        document["cases"][0] = case
        rig.repo.path.write_text(json.dumps(document), encoding="utf-8")
    else:
        current = rig.snapshot()
        current.payload["cases"][0] = case
        rig.backing.compare_and_swap(rig.repo.key, current.payload, current.version)
    return event


@pytest.mark.parametrize("event_revision", [10, 11, 12])
def test_stored_event_cannot_reserve_the_next_revision_and_suppress_new_reply(rig, event_revision):
    previous = install_stored_intent(rig, event_revision=event_revision)
    before = rig.snapshot()
    if event_revision > 10:
        with pytest.raises(DemoError) as caught:
            patch_fresh(rig, {"reply": "새 회신"}, "center")
        assert (caught.value.code, caught.value.status) == ("STORAGE_INVALID", 503)
        assert rig.snapshot() == before
    else:
        saved = patch_fresh(rig, {"reply": "새 회신"}, "center")
        assert saved["revision"] == 11
        assert len(saved["notificationOutbox"]) == 2
        assert saved["notificationOutbox"][0] == previous
        assert_event(saved["notificationOutbox"][-1], saved, "interim_reply", "teams", "counselor", saved["id"])
        assert rig.reopen().get(saved["id"]) == saved


@pytest.mark.parametrize("role", ["counselor", "owner", "center"])
def test_stored_counselor_binding_is_case_fixed_but_other_roles_preserve_history(rig, role):
    previous = install_stored_intent(rig, event_revision=10, role=role, reference_source="SYN-NOTIFY-B")
    before = rig.snapshot()
    if role == "counselor":
        with pytest.raises(DemoError) as caught:
            patch_fresh(rig, {"reply": "새 회신"}, "center")
        assert (caught.value.code, caught.value.status) == ("STORAGE_INVALID", 503)
        assert rig.snapshot() == before
    else:
        saved = patch_fresh(rig, {"reply": "새 회신"}, "center")
        assert saved["notificationOutbox"][0] == previous
        assert len(saved["notificationOutbox"]) == 2


def test_duplicate_guard_removal_mutant_is_detected(monkeypatch):
    from server import notifications
    source = inspect.getsource(notifications)
    guard = 'if event["id"] not in known_ids:'
    assert source.count(guard) == 1
    namespace = {"__name__": "notification_duplicate_mutant"}
    exec(compile(source.replace(guard, "if True:"), "<notification-duplicate-mutant>", "exec"), namespace)
    with monkeypatch.context() as local:
        local.setattr(notifications, "append_notification_intents", namespace["append_notification_intents"])
        with pytest.raises(AssertionError):
            test_producer_suppresses_same_event_id_and_ignores_timestamp_for_identity()


def test_post_save_intent_mutant_is_detected_at_atomic_json_write(tmp_path, monkeypatch):
    from server import service
    source = inspect.getsource(service)
    original = ('            notifications.append_notification_intents(case, previous_status=old_status,\n'
                '                previous_reply=old_reply, created_at=case["updatedAt"])\n')
    save = "        return self.repo.update(case_id, mutate)"
    assert source.count(original) == source.count(save) == 1
    delayed = ('        before = self.repo.get(case_id)\n'
               '        saved = self.repo.update(case_id, mutate)\n'
               '        notifications.append_notification_intents(saved, previous_status=before.get("status", "draft"),\n'
               '            previous_reply=before.get("reply"), created_at=saved["updatedAt"])\n'
               '        return saved')
    namespace = {"__name__": "notification_post_save_mutant"}
    exec(compile(source.replace(original, "").replace(save, delayed), "<notification-post-save-mutant>", "exec"), namespace)
    with monkeypatch.context() as local:
        local.setattr(CaseService, "patch", namespace["CaseService"].patch)
        with pytest.raises(AssertionError):
            test_json_failure_before_replace_preserves_case_and_outbox_together(tmp_path, local)


def test_recipient_allowlist_guard_removal_mutant_is_detected(rig, monkeypatch):
    from server import service
    source = inspect.getsource(service)
    guard = ('                if case["departmentId"] not in {d["id"] for d in self.departments()}:\n'
             '                    raise DemoError("INVALID_DEPARTMENT", "등록된 담당 부서를 선택해 주세요.", 422)\n')
    assert source.count(guard) == 1
    namespace = {"__name__": "notification_department_mutant"}
    exec(compile(source.replace(guard, ""), "<notification-department-mutant>", "exec"), namespace)
    with monkeypatch.context() as local:
        local.setattr(CaseService, "patch", namespace["CaseService"].patch)
        with pytest.raises(pytest.fail.Exception, match="DID NOT RAISE"):
            test_legacy_unregistered_department_cannot_become_an_intent_recipient(rig)


def test_stored_revision_guard_removal_mutant_is_detected(rig, monkeypatch):
    from server import service
    source = inspect.getsource(service)
    guard = "            notifications.validate_stored_notification_outbox(case)\n"
    assert source.count(guard) == 1
    namespace = {"__name__": "notification_stored_revision_mutant"}
    exec(compile(source.replace(guard, ""), "<notification-stored-revision-mutant>", "exec"), namespace)
    with monkeypatch.context() as local:
        local.setattr(CaseService, "patch", namespace["CaseService"].patch)
        with pytest.raises(pytest.fail.Exception, match="DID NOT RAISE"):
            test_stored_event_cannot_reserve_the_next_revision_and_suppress_new_reply(rig, 11)


def test_stored_counselor_binding_guard_removal_mutant_is_detected(rig, monkeypatch):
    from server import notifications
    source = inspect.getsource(notifications)
    guard = ('                if row["recipientRole"] == "counselor" and reference != "counselor:" + hashlib.sha256(case["id"].encode("utf-8")).hexdigest():\n'
             '                    raise ValueError\n')
    assert source.count(guard) == 1
    namespace = {"__name__": "notification_counselor_binding_mutant"}
    exec(compile(source.replace(guard, ""), "<notification-counselor-binding-mutant>", "exec"), namespace)
    with monkeypatch.context() as local:
        local.setattr(notifications, "_existing_ids", namespace["_existing_ids"])
        with pytest.raises(pytest.fail.Exception, match="DID NOT RAISE"):
            test_stored_counselor_binding_is_case_fixed_but_other_roles_preserve_history(rig, "counselor")
