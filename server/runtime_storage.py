"""Explicit storage selection; cloud requests may only use existing ledgers."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import os
from pathlib import Path
import re
from threading import RLock

from server.budget import Budget
from server.cas_budget import CasBudget
from server.cas_repository import CasCaseRepository
from server.cas_store import CasConflict, CasStore, CasValue
from server.errors import DemoError
from server.live import LiveAnalyzer
from server.repository import CaseRepository, JsonCaseRepository, ROOT
from server.service import CaseService
from server.vercel_blob_store import VercelBlobCasStore


def storage_unavailable() -> DemoError:
    return DemoError("STORAGE_UNAVAILABLE", "저장소 상태를 확인할 수 없습니다. 잠시 후 다시 시도해 주세요.", 503)


def _invalid_config() -> DemoError:
    return DemoError("STORAGE_CONFIG_INVALID", "서버 저장소 설정이 올바르지 않습니다.", 503)


@dataclass(frozen=True)
class StorageConfig:
    backend: str
    state_dir: Path | None = None
    token: str | None = field(default=None, repr=False)
    store_id: str | None = field(default=None, repr=False)
    initial_reserved_cents: int | None = None


def storage_config(environ: Mapping[str, str] | None = None) -> StorageConfig:
    environment = os.environ if environ is None else environ
    backend = environment.get("ONEFLOW_STORAGE_BACKEND", "local-json")
    is_vercel = environment.get("VERCEL") == "1" or bool(environment.get("VERCEL_ENV"))
    if backend not in ("local-json", "vercel-blob") or (is_vercel and backend != "vercel-blob"):
        raise _invalid_config()
    if backend == "local-json":
        raw_path = environment.get("ONEFLOW_STATE_DIR")
        if raw_path is None:
            path = ROOT / ".local"
        else:
            if not isinstance(raw_path, str) or not raw_path.strip() or "\0" in raw_path:
                raise _invalid_config()
            path = Path(raw_path)
            if not path.is_absolute():
                raise _invalid_config()
        return StorageConfig(backend=backend, state_dir=path)
    token = environment.get("BLOB_READ_WRITE_TOKEN")
    store_id = environment.get("ONEFLOW_BLOB_STORE_ID")
    initial = environment.get("ONEFLOW_BUDGET_INITIAL_RESERVED_CENTS")
    if (not isinstance(token, str) or not 0 < len(token) <= 8192
            or any(not 33 <= ord(char) <= 126 for char in token)
            or not isinstance(store_id, str) or not re.fullmatch(r"(?:store_)?[A-Za-z0-9]{1,63}", store_id)
            or not isinstance(initial, str) or not re.fullmatch(r"[0-9]+", initial)):
        raise _invalid_config()
    try:
        initial_cents = int(initial)
    except ValueError:
        raise _invalid_config() from None
    return StorageConfig(backend=backend, token=token, store_id=store_id, initial_reserved_cents=initial_cents)


class ExistingDocumentsStore:
    """Production adapter guard: absence never authorizes automatic reseeding."""

    def __init__(self, store: CasStore):
        self.store = store

    def read(self, key: str) -> CasValue:
        try:
            value = self.store.read(key)
        except Exception:
            raise storage_unavailable() from None
        if value is None:
            raise storage_unavailable()
        return value

    def compare_and_swap(self, key: str, payload: dict, expected_version: str | None) -> str:
        if expected_version is None:
            raise storage_unavailable()
        try:
            return self.store.compare_and_swap(key, payload, expected_version)
        except CasConflict:
            raise
        except Exception:
            raise storage_unavailable() from None


@dataclass
class RuntimeStorage:
    backend: str
    repository: CaseRepository
    budget: Budget | CasBudget
    service: CaseService

    def check_ready(self) -> dict:
        """Read current state; never cache readiness or initialize cloud state."""
        try:
            if self.backend == "vercel-blob":
                self.repository.list()
            return self.budget.status()
        except Exception:
            raise storage_unavailable() from None


def _build_runtime(config: StorageConfig) -> RuntimeStorage:
    try:
        if config.backend == "local-json":
            repository = JsonCaseRepository(path=config.state_dir / "cases-store.json")
            budget = Budget(path=config.state_dir / "demo-usage.json")
        else:
            transport = VercelBlobCasStore(token=config.token, store_id=config.store_id)
            store = ExistingDocumentsStore(transport)
            repository = CasCaseRepository(store)
            budget = CasBudget(store, initial_reserved_cents=config.initial_reserved_cents)
        analyzer = LiveAnalyzer(budget=budget)
        return RuntimeStorage(config.backend, repository, budget, CaseService(repository, analyzer=analyzer))
    except Exception:
        raise _invalid_config() from None


_cache_lock = RLock()
_cached: tuple[StorageConfig, RuntimeStorage] | None = None


def get_runtime_storage(environ: Mapping[str, str] | None = None) -> RuntimeStorage:
    """Select by a validated configuration snapshot, including secret rotation."""
    config = storage_config(environ)
    global _cached
    with _cache_lock:
        if _cached is None or _cached[0] != config:
            _cached = (config, _build_runtime(config))
        return _cached[1]


def clear_runtime_storage_cache() -> None:
    """Test/configuration boundary; do not interrupt requests using an old client."""
    global _cached
    with _cache_lock:
        _cached = None
