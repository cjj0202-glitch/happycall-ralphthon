"""Persist notification intentions with the case; never deliver or queue a send."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import re

from server.errors import DemoError

SCHEMA_VERSION = 1
FIELDS = {"schemaVersion", "id", "caseId", "caseRevision", "kind", "channel",
          "recipientRole", "recipientRef", "createdAt", "status", "reason"}
TARGETS = {("handoff", "teams", "center"), ("interim_reply", "teams", "counselor"),
           ("final_reply", "teams", "counselor"), ("final_reply", "kakao", "owner")}
HEX_DIGEST = re.compile(r"[0-9a-f]{64}")


def _identifier(event: dict) -> str:
    identity = [SCHEMA_VERSION, event["caseId"], event["caseRevision"], event["kind"],
                event["channel"], event["recipientRole"], event["recipientRef"]]
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def _existing_ids(case: dict, *, max_revision: int) -> set[str]:
    """Fail closed on a malformed stored value without echoing its contents."""
    rows = case.get("notificationOutbox", [])
    try:
        if not isinstance(rows, list):
            raise ValueError
        ids = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != FIELDS:
                raise ValueError
            if (type(row["schemaVersion"]) is not int or row["schemaVersion"] != SCHEMA_VERSION
                    or row["caseId"] != case["id"] or type(row["caseRevision"]) is not int
                    or not 1 <= row["caseRevision"] <= max_revision
                    or (row["kind"], row["channel"], row["recipientRole"]) not in TARGETS
                    or row["status"] != "not_connected"):
                raise ValueError
            reference = row["recipientRef"]
            if reference is None and row["recipientRole"] != "owner":
                raise ValueError
            if reference is not None:
                prefix = row["recipientRole"] + ":"
                if not isinstance(reference, str) or not reference.startswith(prefix) or not HEX_DIGEST.fullmatch(reference[len(prefix):]):
                    raise ValueError
                if row["recipientRole"] == "counselor" and reference != "counselor:" + hashlib.sha256(case["id"].encode("utf-8")).hexdigest():
                    raise ValueError
            if row["reason"] != ("missing_recipient" if reference is None else "delivery_not_configured"):
                raise ValueError
            if (not isinstance(row["id"], str) or row["id"] != _identifier(row)
                    or not isinstance(row["createdAt"], str)
                    or datetime.fromisoformat(row["createdAt"]).tzinfo is None):
                raise ValueError
            ids.add(row["id"])
        return ids
    except (KeyError, TypeError, ValueError):
        raise DemoError("STORAGE_INVALID", "저장된 알림 기록 형식을 확인해 주세요.", 503) from None


def validate_stored_notification_outbox(case: dict) -> None:
    """Check the persisted snapshot before a transform may add its next revision."""
    _existing_ids(case, max_revision=case["revision"])


def append_notification_intents(case: dict, *, previous_status: str,
                                previous_reply: str | None, created_at: str) -> None:
    """Called after PATCH validation, before its one atomic repository write.

    case.revision is still the old revision inside the repository transform.
    Recipient references are logical identifiers, not verified delivery addresses.
    No source text or response body is copied into an intent.
    """
    status = case.get("status", "draft")
    targets = []
    if status == "handed_off" and previous_status in {"draft", "review"}:
        targets = [("handoff", "teams", "center", case.get("departmentId"))]
    elif status == "closed" and previous_status != "closed":
        targets = [("final_reply", "teams", "counselor", case["id"]),
                   ("final_reply", "kakao", "owner", case.get("intake", {}).get("storeId"))]
    elif status in {"handed_off", "in_progress"}:
        old_reply = previous_reply.strip() if isinstance(previous_reply, str) else ""
        reply = case.get("reply")
        if isinstance(reply, str) and reply.strip() and reply.strip() != old_reply:
            targets = [("interim_reply", "teams", "counselor", case["id"])]
    if not targets:
        return
    # The service validated the persisted snapshot at its old revision first.
    # Here the same transform may already have appended this next-revision ID.
    known_ids = _existing_ids(case, max_revision=case["revision"] + 1)
    for kind, channel, role, source in targets:
        # Hash the original identifier, using strip only to detect absence.
        reference = (role + ":" + hashlib.sha256(source.encode("utf-8")).hexdigest()
                     if isinstance(source, str) and source.strip() else None)
        if reference is None and role != "owner":
            raise DemoError("STORAGE_INVALID", "저장된 알림 대상 형식을 확인해 주세요.", 503)
        event = {"schemaVersion": SCHEMA_VERSION, "caseId": case["id"],
                 "caseRevision": case["revision"] + 1, "kind": kind, "channel": channel,
                 "recipientRole": role, "recipientRef": reference, "createdAt": created_at,
                 "status": "not_connected",
                 "reason": "delivery_not_configured" if reference is not None else "missing_recipient"}
        event["id"] = _identifier(event)
        if event["id"] not in known_ids:
            case.setdefault("notificationOutbox", []).append(event)
            known_ids.add(event["id"])
