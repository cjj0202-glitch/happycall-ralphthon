"""Case repository over an injected, genuinely atomic CAS transport."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Callable

from server.cas_store import CasConflict, CasStore, CasValue
from server.errors import DemoError
from server.repository import ROOT
from server import intake_idempotency


class CasCaseRepository:
    def __init__(self, store: CasStore, key: str = "oneflow/cases.json",
                 fixture_path: Path | None = None, max_attempts: int = 8):
        if not key or isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
            raise ValueError("A key and positive integer max_attempts are required")
        self.store, self.key, self.max_attempts = store, key, max_attempts
        self.fixture_path = fixture_path or ROOT / "data/fixtures/cases.json"

    def fixtures(self) -> dict:
        if not self.fixture_path.exists():
            raise DemoError("FIXTURES_NOT_READY", "합성 사례 파일이 아직 준비되지 않았습니다.", 503)
        raw = json.loads(self.fixture_path.read_text(encoding="utf-8-sig"))
        return {"cases": raw} if isinstance(raw, list) else raw

    @staticmethod
    def _document(value: CasValue) -> dict:
        data = copy.deepcopy(value.payload)
        if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
            raise DemoError("STORAGE_INVALID", "접수 저장 데이터 형식을 확인해 주세요.", 503)
        ids = set()
        for case in data["cases"]:
            if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not case["id"] or case["id"] in ids:
                raise DemoError("STORAGE_INVALID", "접수 저장 데이터 형식을 확인해 주세요.", 503)
            ids.add(case["id"])
            revision = case.setdefault("revision", 0)
            if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
                raise DemoError("STORAGE_INVALID", "접수 저장 버전을 확인해 주세요.", 503)
        return data

    @staticmethod
    def _busy():
        return DemoError("STORAGE_BUSY", "저장 요청이 겹쳤습니다. 잠시 후 다시 시도해 주세요.", 503)

    def _existing(self) -> tuple[CasValue, dict]:
        value = self.store.read(self.key)
        if value is None:
            raise DemoError("STORAGE_STATE_LOST", "처리 중 저장 데이터가 사라졌습니다. 저장소를 확인해 주세요.", 503)
        return value, self._document(value)

    def _read(self) -> tuple[CasValue, dict]:
        value = self.store.read(self.key)
        if value is not None:
            return value, self._document(value)
        data = {"cases": copy.deepcopy(self.fixtures()["cases"])}
        # Validate fixtures before writing; legacy revision defaults are read-only.
        self._document(CasValue(data, "fixture-validation"))
        try:
            version = self.store.compare_and_swap(self.key, data, None)
        except CasConflict:
            return self._existing()
        value = CasValue(data, version)
        return value, self._document(value)

    def list(self) -> list[dict]:
        return copy.deepcopy(self._read()[1]["cases"])

    def get(self, case_id: str) -> dict:
        for case in self.list():
            if case["id"] == case_id:
                return case
        raise DemoError("CASE_NOT_FOUND", "해당 접수를 찾을 수 없습니다.", 404)

    def intake_result(self, key_digest: str, payload_hash: str | None = None) -> dict | None:
        return intake_idempotency.lookup(self._read()[1], key_digest, payload_hash)

    def create(self, case: dict, identity: tuple[str, str] | None = None) -> dict:
        result = {**copy.deepcopy(case), "revision": 0}
        self._document(CasValue({"cases": [result]}, "create-validation"))
        value, data = self._read()
        for attempt in range(self.max_attempts):
            if identity is not None:
                existing = intake_idempotency.lookup(data, *identity)
                if existing is not None:
                    return existing
            if any(row["id"] == result["id"] for row in data["cases"]):
                raise DemoError("DUPLICATE_CASE", "이미 존재하는 접수입니다.", 409)
            data["cases"].append(copy.deepcopy(result))
            intake_idempotency.record(data, identity, result["id"])
            try:
                self.store.compare_and_swap(self.key, data, value.version)
                return copy.deepcopy(result)
            except CasConflict:
                value, data = self._existing()
                if identity is not None:
                    existing = intake_idempotency.lookup(data, *identity)
                    if existing is not None:
                        return existing
                if any(row["id"] == result["id"] for row in data["cases"]):
                    raise DemoError("DUPLICATE_CASE", "이미 존재하는 접수입니다.", 409) from None
        raise self._busy()

    def update(self, case_id: str, transform: Callable[[dict], dict]) -> dict:
        value, data = self._read()
        original = next((case for case in data["cases"] if case["id"] == case_id), None)
        if original is None:
            raise DemoError("CASE_NOT_FOUND", "해당 접수를 찾을 수 없습니다.", 404)
        original = copy.deepcopy(original)
        # Exactly once: side effects and paid model calls must not be replayed.
        result = copy.deepcopy(transform(copy.deepcopy(original)))
        if not isinstance(result, dict) or result.get("id") != case_id:
            raise DemoError("INVALID_CASE_UPDATE", "접수 수정에서 접수 ID를 변경할 수 없습니다.", 422)
        result["revision"] = original["revision"] + 1
        for attempt in range(self.max_attempts):
            index = next((i for i, case in enumerate(data["cases"]) if case["id"] == case_id), None)
            if index is None or data["cases"][index] != original:
                raise DemoError("STATE_CONFLICT", "다른 작업자가 접수를 수정했습니다. 최신 내용을 다시 확인해 주세요.", 409)
            data["cases"][index] = copy.deepcopy(result)
            try:
                self.store.compare_and_swap(self.key, data, value.version)
                return copy.deepcopy(result)
            except CasConflict:
                value, data = self._existing()
                current = next((case for case in data["cases"] if case["id"] == case_id), None)
                if current != original:
                    raise DemoError("STATE_CONFLICT", "다른 작업자가 접수를 수정했습니다. 최신 내용을 다시 확인해 주세요.", 409) from None
        raise self._busy()
