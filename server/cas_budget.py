"""Global conservative reservations over CAS; this is not provider billing."""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import uuid

from server.cas_store import CasConflict, CasStore, CasValue
from server.errors import DemoError


def _cents(value, *, positive=False):
    return not isinstance(value, bool) and isinstance(value, int) and value >= (1 if positive else 0)


class CasBudget:
    def __init__(self, store: CasStore, key: str = "oneflow/budget.json", limit_cents: int = 3000,
                 warn_cents: int = 2500, initial_reserved_cents: int = 0, max_attempts: int = 8):
        if (not key or not _cents(limit_cents, positive=True) or not _cents(warn_cents)
                or warn_cents > limit_cents or not _cents(initial_reserved_cents)
                or not _cents(max_attempts, positive=True)):
            raise ValueError("Invalid budget configuration")
        self.store, self.key, self.max_attempts = store, key, max_attempts
        self.limit, self.warn, self.initial_reserved_cents = limit_cents, warn_cents, initial_reserved_cents

    def _document(self, value: CasValue) -> dict:
        data = copy.deepcopy(value.payload)
        if (not isinstance(data, dict) or type(data.get("schemaVersion")) is not int or data["schemaVersion"] != 1
                or not _cents(data.get("initialReservedCents")) or not _cents(data.get("limitCents"), positive=True)
                or not _cents(data.get("warnCents")) or data["warnCents"] > data["limitCents"]
                or not isinstance(data.get("entries"), list)):
            raise DemoError("BUDGET_INVALID", "예산 저장 데이터 형식을 확인해 주세요.", 503)
        if (data["initialReservedCents"], data["limitCents"], data["warnCents"]) != (
                self.initial_reserved_cents, self.limit, self.warn):
            raise DemoError("BUDGET_CONFIG_MISMATCH", "공유 예산의 이관액·상한 설정이 일치하지 않습니다.", 503)
        ids = set()
        for entry in data["entries"]:
            if (not isinstance(entry, dict) or not isinstance(entry.get("requestId"), str) or not entry["requestId"]
                    or entry["requestId"] in ids or not _cents(entry.get("reservedCents"), positive=True)
                    or entry.get("state") not in ("reserved", "completed", "failed-cost-uncertain")
                    or not isinstance(entry.get("purpose"), str) or not isinstance(entry.get("at"), str)):
                raise DemoError("BUDGET_INVALID", "예산 예약 데이터를 확인해 주세요.", 503)
            ids.add(entry["requestId"])
        return data

    @staticmethod
    def _busy():
        return DemoError("STORAGE_BUSY", "예산 예약 요청이 겹쳤습니다. 잠시 후 다시 시도해 주세요.", 503)

    def _existing(self) -> tuple[CasValue, dict]:
        value = self.store.read(self.key)
        if value is None:
            raise DemoError("STORAGE_STATE_LOST", "처리 중 예산 데이터가 사라졌습니다. 저장소를 확인해 주세요.", 503)
        return value, self._document(value)

    def _read(self) -> tuple[CasValue, dict]:
        value = self.store.read(self.key)
        if value is not None:
            return value, self._document(value)
        data = {"schemaVersion": 1, "initialReservedCents": self.initial_reserved_cents,
                "limitCents": self.limit, "warnCents": self.warn, "entries": []}
        try:
            version = self.store.compare_and_swap(self.key, data, None)
        except CasConflict:
            return self._existing()
        return CasValue(data, version), data

    @staticmethod
    def _total(data: dict) -> int:
        return data["initialReservedCents"] + sum(entry["reservedCents"] for entry in data["entries"])

    def status(self) -> dict:
        total = self._total(self._read()[1])
        return {"reservedUsd": total / 100, "limitUsd": self.limit / 100,
                "warning": total >= self.warn, "accounting": "conservative-shared-reservations"}

    def reserve(self, cents: int, purpose: str) -> str:
        if not _cents(cents, positive=True):
            raise ValueError("Positive integer reservation required")
        if not isinstance(purpose, str) or not purpose.strip():
            raise ValueError("Reservation purpose is required")
        request_id = str(uuid.uuid4())
        entry = {"requestId": request_id, "purpose": purpose, "reservedCents": cents,
                 "state": "reserved", "at": datetime.now(timezone.utc).isoformat()}
        value, data = self._read()
        for attempt in range(self.max_attempts):
            if self._total(data) + cents > self.limit:
                raise DemoError("BUDGET_LIMIT", "데모 예산 상한에 도달하여 API 호출을 중단했습니다.", 429)
            data["entries"].append(copy.deepcopy(entry))
            try:
                self.store.compare_and_swap(self.key, data, value.version)
                return request_id
            except CasConflict:
                value, data = self._existing()
        raise self._busy()

    def finish(self, request_id: str, success: bool):
        if not isinstance(success, bool):
            raise ValueError("success must be a boolean")
        value, data = self._read()
        for attempt in range(self.max_attempts):
            entry = next((entry for entry in data["entries"] if entry["requestId"] == request_id), None)
            if entry is None or entry["state"] != "reserved":
                return
            entry["state"] = "completed" if success else "failed-cost-uncertain"
            try:
                self.store.compare_and_swap(self.key, data, value.version)
                return
            except CasConflict:
                value, data = self._existing()
        raise self._busy()
