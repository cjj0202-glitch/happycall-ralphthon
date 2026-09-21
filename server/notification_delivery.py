"""N04-D3 synthetic first Bolt, deliberately disconnected from the runtime.

Only a caller-supplied temporary committed source and the in-memory FakeTransport
are supported. Candidate intents are claims, never proof that a save succeeded.
Records/deduplication belong to ONE coordinator instance; this is not a durable
outbox, production authorization, distributed CAS, restart safety, or delivery.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
import hashlib
import json
import re
from threading import RLock
from typing import Protocol


_FIELDS = frozenset({
    "schemaVersion", "id", "caseId", "caseRevision", "kind", "channel",
    "recipientRole", "recipientRef", "createdAt", "status", "reason",
})
_TARGETS = frozenset({
    ("handoff", "teams", "center"),
    ("interim_reply", "teams", "counselor"),
    ("final_reply", "teams", "counselor"),
    ("final_reply", "kakao", "owner"),
})
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_SYNTHETIC_CASE = re.compile(r"SYN-[A-Za-z0-9_-]{1,80}\Z")
_SYNTHETIC_BINDING = re.compile(r"SYN-BIND-[A-Za-z0-9_-]{1,80}\Z")


class DeliveryValidationError(ValueError):
    """Static reason only: never include the rejected source in diagnostics."""


class CommittedCaseSource(Protocol):
    def read_committed(self, case_id: str) -> dict | None:
        """Return a detached, successfully committed temporary snapshot only.

        The source must not expose pending transforms or staging files. This is
        a trusted dependency contract, not a caller-controlled `committed` flag.
        """
        ...


@dataclass(frozen=True)
class SyntheticBinding:
    binding_id: str
    case_id: str
    recipient_role: str
    recipient_ref: str
    channel: str
    active: bool = True


@dataclass(frozen=True)
class SyntheticMessage:
    delivery_id: str
    intent_id: str
    channel: str
    recipient_role: str
    binding_id: str
    event_kind: str
    synthetic: bool = True


@dataclass(frozen=True)
class DeliveryRecord:
    delivery_id: str
    intent_id: str
    state: str
    binding_id: str
    channel: str
    recipient_role: str
    reason: str


@dataclass(frozen=True)
class DeliveryResult:
    delivery_id: str | None
    intent_id: str
    state: str
    reason: str


class FakeTransport:
    """Records only immutable synthetic messages; contains no network adapter."""

    def __init__(self) -> None:
        self._calls: list[SyntheticMessage] = []

    @property
    def calls(self) -> tuple[SyntheticMessage, ...]:
        return tuple(self._calls)

    def send(self, message: SyntheticMessage) -> None:
        if not isinstance(message, SyntheticMessage) or message.synthetic is not True:
            raise DeliveryValidationError("synthetic_message_required")
        self._calls.append(message)


def _digest(value: list) -> str:
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def _validated_intent(value: object) -> dict:
    # This disconnected branch does not yet contain server.notifications.
    # Match its fixed f043c60 schema; do not widen the production 11-field row.
    try:
        if type(value) is not dict or set(value) != _FIELDS:
            raise ValueError
        row = value.copy()
        if (type(row["schemaVersion"]) is not int or row["schemaVersion"] != 1
                or type(row["caseRevision"]) is not int or row["caseRevision"] < 1
                or not isinstance(row["caseId"], str)
                or not _SYNTHETIC_CASE.fullmatch(row["caseId"])
                or (row["kind"], row["channel"], row["recipientRole"]) not in _TARGETS
                or row["status"] != "not_connected"):
            raise ValueError
        role, reference = row["recipientRole"], row["recipientRef"]
        if reference is None:
            if role != "owner" or row["reason"] != "missing_recipient":
                raise ValueError
        else:
            prefix = role + ":"
            if (not isinstance(reference, str) or not reference.startswith(prefix)
                    or not _DIGEST.fullmatch(reference[len(prefix):])
                    or row["reason"] != "delivery_not_configured"):
                raise ValueError
            if role == "counselor" and reference != "counselor:" + hashlib.sha256(
                    row["caseId"].encode("utf-8")).hexdigest():
                raise ValueError
        identity = [1, row["caseId"], row["caseRevision"], row["kind"],
                    row["channel"], role, reference]
        if (not isinstance(row["id"], str) or row["id"] != _digest(identity)
                or not isinstance(row["createdAt"], str)
                or datetime.fromisoformat(row["createdAt"]).tzinfo is None):
            raise ValueError
        return row
    except (KeyError, TypeError, ValueError):
        raise DeliveryValidationError("invalid_synthetic_intent") from None


def _validate_binding(binding: SyntheticBinding, intent: dict) -> None:
    if (not isinstance(binding, SyntheticBinding)
            or not isinstance(binding.binding_id, str)
            or not _SYNTHETIC_BINDING.fullmatch(binding.binding_id)
            or binding.active is not True
            or intent["recipientRef"] is None
            or binding.case_id != intent["caseId"]
            or binding.recipient_role != intent["recipientRole"]
            or binding.recipient_ref != intent["recipientRef"]
            or binding.channel != intent["channel"]):
        raise DeliveryValidationError("invalid_synthetic_binding")


class DeliveryCoordinator:
    """One-instance, synchronous commit/dedup/active-job experiment only."""

    def __init__(self, source: CommittedCaseSource, transport: FakeTransport) -> None:
        if not isinstance(transport, FakeTransport):
            raise DeliveryValidationError("fake_transport_required")
        self._source = source
        self._transport = transport
        self._lock = RLock()
        self._active: dict[str, str] = {}
        self._records: dict[str, DeliveryRecord] = {}

    @property
    def records(self) -> tuple[DeliveryRecord, ...]:
        with self._lock:
            return tuple(self._records.values())

    def _committed_intent(self, candidate: dict) -> dict | None:
        snapshot = self._source.read_committed(candidate["caseId"])
        if snapshot is None:
            return None
        if (type(snapshot) is not dict or snapshot.get("id") != candidate["caseId"]
                or type(snapshot.get("revision")) is not int
                or snapshot["revision"] < candidate["caseRevision"]
                or type(snapshot.get("notificationOutbox")) is not list):
            return None
        found = None
        known: set[str] = set()
        for value in snapshot["notificationOutbox"]:
            # Validate both copies before equality (True == 1 is not identity).
            stored = _validated_intent(value)
            if (stored["caseId"] != snapshot["id"]
                    or stored["caseRevision"] > snapshot["revision"]
                    or stored["id"] in known):
                raise DeliveryValidationError("invalid_committed_snapshot")
            known.add(stored["id"])
            if stored["id"] == candidate["id"] and stored == candidate:
                found = stored
        return found

    @staticmethod
    def _result(record: DeliveryRecord) -> DeliveryResult:
        return DeliveryResult(record.delivery_id, record.intent_id,
                              record.state, record.reason)

    def deliver(self, candidate_intent: dict, binding: SyntheticBinding) -> DeliveryResult:
        intent = _validated_intent(candidate_intent)
        _validate_binding(binding, intent)
        with self._lock:
            # Identity -> persisted save -> per-intent active job -> fake send.
            # A new request or successful in-memory transform cannot skip this.
            try:
                committed = self._committed_intent(intent)
            except DeliveryValidationError:
                raise
            except Exception:
                return DeliveryResult(None, intent["id"], "blocked",
                                      "committed_read_failed")
            if committed is None:
                return DeliveryResult(None, intent["id"], "not_committed",
                                      "stored_intent_not_found")
            active_id = self._active.get(intent["id"])
            if active_id is not None:
                existing = self._records[active_id]
                if existing.binding_id != binding.binding_id:
                    return DeliveryResult(active_id, intent["id"], "blocked",
                                          "binding_changed")
                # No automatic resend even if the previous fake call raised.
                return self._result(existing)
            delivery_id = _digest([1, "synthetic-bolt", intent["id"],
                                   intent["channel"], binding.binding_id])
            record = DeliveryRecord(delivery_id, intent["id"], "queued",
                                    binding.binding_id, intent["channel"],
                                    intent["recipientRole"], "synthetic_ready")
            # Same lock, memory only; this is NOT a durable atomic transaction.
            self._records[delivery_id] = record
            self._active[intent["id"]] = delivery_id
            return self._dispatch_if_active(record, intent)

    def _dispatch_if_active(self, record: DeliveryRecord, intent: dict) -> DeliveryResult:
        if (self._active.get(intent["id"]) != record.delivery_id
                or record.intent_id != intent["id"]
                or self._records.get(record.delivery_id) != record
                or record.state != "queued"):
            return DeliveryResult(record.delivery_id, intent["id"], "blocked",
                                  "inactive_delivery")
        self._records[record.delivery_id] = replace(record, state="in_flight")
        message = SyntheticMessage(record.delivery_id, record.intent_id,
                                   record.channel, record.recipient_role,
                                   record.binding_id, intent["kind"])
        try:
            self._transport.send(message)
        except Exception:
            completed = replace(record, state="unknown", reason="fake_transport_error")
        else:
            completed = replace(record, state="accepted", reason="fake_transport_only")
        self._records[record.delivery_id] = completed
        return self._result(completed)
