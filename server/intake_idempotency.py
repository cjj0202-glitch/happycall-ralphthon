"""Durable intake attempt references, stored atomically with the created case."""
from __future__ import annotations

import copy
import hashlib
import json
import uuid

from server.errors import DemoError


def key_digest(key: str) -> str:
    try:
        parsed = uuid.UUID(key)
        if parsed.version != 4 or str(parsed) != key.lower():
            raise ValueError
    except (AttributeError, TypeError, ValueError):
        raise DemoError("INVALID_IDEMPOTENCY_KEY", "접수 시도 식별자를 확인해 주세요.", 422) from None
    return hashlib.sha256(("oneflow:intake:" + str(parsed)).encode()).hexdigest()


def request_identity(key: str | None, body: dict) -> tuple[str, str] | None:
    if key is None:
        return None
    fingerprint = hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True,
                                             separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return key_digest(key), fingerprint


def lookup(data: dict, digest: str, payload_hash: str | None = None) -> dict | None:
    attempts = data.get("intakeRequests", {})
    if not isinstance(attempts, dict):
        raise DemoError("STORAGE_INVALID", "접수 시도 기록을 확인해 주세요.", 503)
    if digest not in attempts:
        return None
    record = attempts[digest]
    if not isinstance(record, dict) or not isinstance(record.get("payloadHash"), str) or not isinstance(record.get("caseId"), str):
        raise DemoError("STORAGE_INVALID", "접수 시도 기록을 확인해 주세요.", 503)
    if payload_hash is not None and record["payloadHash"] != payload_hash:
        raise DemoError("IDEMPOTENCY_CONFLICT", "이 접수 시도의 내용이 이전 전송과 다릅니다. 이전 접수의 저장 여부를 먼저 확인해 주세요.", 409)
    matches = [case for case in data["cases"] if case["id"] == record["caseId"]]
    if len(matches) != 1:
        raise DemoError("STORAGE_INVALID", "접수 시도와 저장된 문의의 연결을 확인해 주세요.", 503)
    return copy.deepcopy(matches[0])


def record(data: dict, identity: tuple[str, str] | None, case_id: str) -> None:
    if identity is not None:
        data.setdefault("intakeRequests", {})[identity[0]] = {"payloadHash": identity[1], "caseId": case_id}
