"""File-backed demo store. Every read-modify-write is serialized across processes."""
from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Callable, Protocol

from filelock import FileLock

from server.errors import DemoError
from server import intake_idempotency

ROOT = Path(__file__).resolve().parents[1]


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.stem + "-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


class CaseRepository(Protocol):
    def list(self) -> list[dict]: ...
    def get(self, case_id: str) -> dict: ...
    def create(self, case: dict, identity: tuple[str, str] | None = None) -> dict: ...
    def intake_result(self, key_digest: str, payload_hash: str | None = None) -> dict | None: ...
    def update(self, case_id: str, transform: Callable[[dict], dict]) -> dict: ...
    def fixtures(self) -> dict: ...


class JsonCaseRepository:
    def __init__(self, path: Path | None = None, fixture_path: Path | None = None):
        self.path = path or ROOT / ".local/cases-store.json"
        self.fixture_path = fixture_path or ROOT / "data/fixtures/cases.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(str(self.path) + ".lock", timeout=15)

    def fixtures(self) -> dict:
        if not self.fixture_path.exists():
            raise DemoError("FIXTURES_NOT_READY", "합성 사례 파일이 아직 준비되지 않았습니다.", 503)
        raw = json.loads(self.fixture_path.read_text(encoding="utf-8-sig"))
        return {"cases": raw} if isinstance(raw, list) else raw

    def _read(self) -> dict:
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            data = {"cases": copy.deepcopy(self.fixtures()["cases"])}
            atomic_json(self.path, data)
        for case in data["cases"]:
            case.setdefault("revision", 0)
        return data

    def list(self) -> list[dict]:
        with self.lock:
            return copy.deepcopy(self._read()["cases"])

    def get(self, case_id: str) -> dict:
        for case in self.list():
            if case["id"] == case_id:
                return case
        raise DemoError("CASE_NOT_FOUND", "해당 접수를 찾을 수 없습니다.", 404)

    def intake_result(self, key_digest: str, payload_hash: str | None = None) -> dict | None:
        with self.lock:
            return intake_idempotency.lookup(self._read(), key_digest, payload_hash)

    def create(self, case: dict, identity: tuple[str, str] | None = None) -> dict:
        case = {**copy.deepcopy(case), "revision": 0}
        with self.lock:
            data = self._read()
            if identity is not None:
                existing = intake_idempotency.lookup(data, *identity)
                if existing is not None:
                    return existing
            if any(row["id"] == case["id"] for row in data["cases"]):
                raise DemoError("DUPLICATE_CASE", "이미 존재하는 접수입니다.", 409)
            data["cases"].append(copy.deepcopy(case))
            intake_idempotency.record(data, identity, case["id"])
            atomic_json(self.path, data)
        return copy.deepcopy(case)

    def update(self, case_id: str, transform: Callable[[dict], dict]) -> dict:
        with self.lock:
            data = self._read()
            for index, case in enumerate(data["cases"]):
                if case["id"] == case_id:
                    result = transform(copy.deepcopy(case))
                    result["revision"] = case["revision"] + 1
                    data["cases"][index] = result
                    atomic_json(self.path, data)
                    return copy.deepcopy(result)
        raise DemoError("CASE_NOT_FOUND", "해당 접수를 찾을 수 없습니다.", 404)
