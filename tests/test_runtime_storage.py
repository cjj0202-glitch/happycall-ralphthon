"""Isolated storage wiring tests; no credential files, real transport or paid API."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier, get_ident
from unittest.mock import Mock

import httpx
import pytest

from server import handlers
from server import runtime_config
from server import runtime_storage as storage
from server.cas_budget import CasBudget
from server.cas_repository import CasCaseRepository
from server.cas_store import CasConflict, InMemoryCasStore
from server.errors import DemoError
from server.vercel_blob_store import VercelBlobCasStore


BLOB_ENV = {"ONEFLOW_STORAGE_BACKEND": "vercel-blob", "BLOB_READ_WRITE_TOKEN": "offline-only-token",
            "ONEFLOW_BLOB_STORE_ID": "store_offline123", "ONEFLOW_BUDGET_INITIAL_RESERVED_CENTS": "75"}
ENV_KEYS = {*BLOB_ENV, "ONEFLOW_STATE_DIR", "VERCEL", "VERCEL_ENV"}
CASES_KEY = "oneflow/cases.json"
BUDGET_KEY = "oneflow/budget.json"


@pytest.fixture(autouse=True)
def isolated_runtime(monkeypatch, tmp_path):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(storage, "ROOT", tmp_path)
    monkeypatch.setattr(runtime_config, "require_demo_api_key", Mock(return_value="offline-no-network"))
    storage.clear_runtime_storage_cache()
    yield
    storage.clear_runtime_storage_cache()


def use_env(monkeypatch, values):
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def seeded_store(initial=75):
    store = InMemoryCasStore()
    CasCaseRepository(store).list()
    CasBudget(store, initial_reserved_cents=initial).status()
    return store


def install_cloud(monkeypatch, store=None):
    backing = seeded_store() if store is None else store
    constructor = Mock(return_value=backing)
    monkeypatch.setattr(storage, "VercelBlobCasStore", constructor)
    use_env(monkeypatch, BLOB_ENV)
    return backing, constructor


def assert_503(call, code=None):
    with pytest.raises(DemoError) as caught:
        call()
    assert caught.value.status == 503
    if code:
        assert caught.value.code == code
    return caught.value


def test_default_local_factory_preserves_filenames_and_shared_budget(tmp_path):
    runtime = storage.get_runtime_storage({})
    assert runtime.backend == "local-json"
    assert runtime.repository.path == tmp_path / ".local/cases-store.json"
    assert runtime.budget.path == tmp_path / ".local/demo-usage.json"
    assert runtime.service.repo is runtime.repository
    assert runtime.service.analyzer.budget is runtime.budget
    assert runtime is storage.get_runtime_storage({"ONEFLOW_STORAGE_BACKEND": "local-json"})
    assert runtime.check_ready()["accounting"] == "conservative-local-reservations"
    assert not runtime.repository.path.exists()
    created = runtime.repository.create({"id": "INT-LOCAL"})
    assert created["revision"] == 0
    assert runtime.repository.path.is_file()


def test_explicit_absolute_local_path_contains_both_ledgers_and_changes_cache(tmp_path):
    directory = tmp_path / "chosen-state"
    first = storage.get_runtime_storage({"ONEFLOW_STATE_DIR": str(directory)})
    first.budget.reserve(15, "analysis-text")
    first.repository.create({"id": "INT-PATH"})
    assert first.repository.path == directory / "cases-store.json"
    assert first.budget.path == directory / "demo-usage.json"
    assert first.budget.status()["reservedUsd"] == .15
    other = storage.get_runtime_storage({"ONEFLOW_STATE_DIR": str(tmp_path / "other-state")})
    assert other is not first
    assert other.budget.status()["reservedUsd"] == 0
    assert first.repository.get("INT-PATH")["id"] == "INT-PATH"


@pytest.mark.parametrize("values", [{"ONEFLOW_STORAGE_BACKEND": ""}, {"ONEFLOW_STORAGE_BACKEND": " "},
    {"ONEFLOW_STORAGE_BACKEND": "untrusted-secret-backend"}, {"ONEFLOW_STORAGE_BACKEND": "VERCEL-BLOB"},
    {"ONEFLOW_STATE_DIR": ""}, {"ONEFLOW_STATE_DIR": " "}, {"ONEFLOW_STATE_DIR": "relative/path"},
    {"ONEFLOW_STATE_DIR": "nul\0path"}, {"VERCEL": "1"}, {"VERCEL_ENV": "production"},
    {"VERCEL_ENV": "preview", "ONEFLOW_STORAGE_BACKEND": "local-json"}])
def test_invalid_local_config_and_vercel_fallback_are_rejected_without_io(values, monkeypatch):
    local = Mock(side_effect=AssertionError("must not construct local storage"))
    cloud = Mock(side_effect=AssertionError("must not construct remote storage"))
    monkeypatch.setattr(storage, "JsonCaseRepository", local)
    monkeypatch.setattr(storage, "VercelBlobCasStore", cloud)
    exc = assert_503(lambda: storage.get_runtime_storage(values), "STORAGE_CONFIG_INVALID")
    assert str(exc) == "서버 저장소 설정이 올바르지 않습니다."
    local.assert_not_called()
    cloud.assert_not_called()


@pytest.mark.parametrize("key,value", [
    ("BLOB_READ_WRITE_TOKEN", None), ("BLOB_READ_WRITE_TOKEN", ""), ("BLOB_READ_WRITE_TOKEN", "a\nb"),
    ("ONEFLOW_BLOB_STORE_ID", None), ("ONEFLOW_BLOB_STORE_ID", ""), ("ONEFLOW_BLOB_STORE_ID", "bad.invalid/path"),
    ("ONEFLOW_BUDGET_INITIAL_RESERVED_CENTS", None), ("ONEFLOW_BUDGET_INITIAL_RESERVED_CENTS", ""),
    ("ONEFLOW_BUDGET_INITIAL_RESERVED_CENTS", "-1"), ("ONEFLOW_BUDGET_INITIAL_RESERVED_CENTS", "1.0"),
    ("ONEFLOW_BUDGET_INITIAL_RESERVED_CENTS", "1e2"), ("ONEFLOW_BUDGET_INITIAL_RESERVED_CENTS", " 0"),
    ("ONEFLOW_BUDGET_INITIAL_RESERVED_CENTS", "+1"), ("ONEFLOW_BUDGET_INITIAL_RESERVED_CENTS", "１２"),
])
def test_cloud_requires_explicit_valid_credentials_store_and_migration_amount(key, value, monkeypatch):
    values = dict(BLOB_ENV)
    if value is None:
        del values[key]
    else:
        values[key] = value
    constructor = Mock(side_effect=AssertionError("invalid config must not construct transport"))
    monkeypatch.setattr(storage, "VercelBlobCasStore", constructor)
    assert_503(lambda: storage.get_runtime_storage(values), "STORAGE_CONFIG_INVALID")
    constructor.assert_not_called()


def test_explicit_zero_migration_is_allowed_and_secrets_are_not_in_config_repr():
    config = storage.storage_config({**BLOB_ENV, "ONEFLOW_BUDGET_INITIAL_RESERVED_CENTS": "0"})
    assert config.initial_reserved_cents == 0
    assert BLOB_ENV["BLOB_READ_WRITE_TOKEN"] not in repr(config)
    assert BLOB_ENV["ONEFLOW_BLOB_STORE_ID"] not in repr(config)


def test_cloud_factory_does_not_touch_network_or_seed_and_wires_exact_budget(monkeypatch):
    backing, constructor = install_cloud(monkeypatch)
    backing.read = Mock(wraps=backing.read)
    backing.compare_and_swap = Mock(wraps=backing.compare_and_swap)
    runtime = storage.get_runtime_storage()
    constructor.assert_called_once_with(token=BLOB_ENV["BLOB_READ_WRITE_TOKEN"], store_id=BLOB_ENV["ONEFLOW_BLOB_STORE_ID"])
    backing.read.assert_not_called()
    backing.compare_and_swap.assert_not_called()
    assert runtime.backend == "vercel-blob"
    assert isinstance(runtime.repository, CasCaseRepository)
    assert isinstance(runtime.budget, CasBudget)
    assert runtime.service.repo is runtime.repository
    assert runtime.service.analyzer.budget is runtime.budget
    assert runtime.repository.store is runtime.budget.store
    assert runtime.check_ready()["reservedUsd"] == .75
    backing.compare_and_swap.assert_not_called()


def test_cache_uses_all_storage_settings_including_token_rotation_and_backend(monkeypatch, tmp_path):
    _, constructor = install_cloud(monkeypatch)
    first = storage.get_runtime_storage(BLOB_ENV)
    assert storage.get_runtime_storage(dict(BLOB_ENV)) is first
    constructor.assert_called_once()
    for key, value in (("BLOB_READ_WRITE_TOKEN", "new-offline-token"), ("ONEFLOW_BLOB_STORE_ID", "store_other123"),
                       ("ONEFLOW_BUDGET_INITIAL_RESERVED_CENTS", "76")):
        changed = storage.get_runtime_storage({**BLOB_ENV, key: value})
        assert changed is not first
        assert changed.service.analyzer.budget is changed.budget
    local = storage.get_runtime_storage({"ONEFLOW_STATE_DIR": str(tmp_path / "local")})
    assert local.backend == "local-json"
    assert local is not first


def test_concurrent_first_factory_calls_share_one_constructor_and_budget(monkeypatch):
    _, constructor = install_cloud(monkeypatch)
    barrier = Barrier(16)
    def read_runtime(_):
        barrier.wait(timeout=10)
        return storage.get_runtime_storage()
    with ThreadPoolExecutor(max_workers=16) as pool:
        runtimes = list(pool.map(read_runtime, range(16)))
    constructor.assert_called_once()
    assert len({id(runtime) for runtime in runtimes}) == 1
    assert len({id(runtime.budget) for runtime in runtimes}) == 1


def test_guard_rejects_absence_and_every_initial_create_before_transport():
    backing = Mock()
    backing.read.return_value = None
    guard = storage.ExistingDocumentsStore(backing)
    assert_503(lambda: guard.read(CASES_KEY), "STORAGE_UNAVAILABLE")
    assert_503(lambda: guard.compare_and_swap(CASES_KEY, {"cases": []}, None), "STORAGE_UNAVAILABLE")
    backing.compare_and_swap.assert_not_called()


def test_guard_preserves_confirmed_conflict_and_redacts_uncertain_failures():
    backing = Mock()
    guard = storage.ExistingDocumentsStore(backing)
    backing.compare_and_swap.side_effect = CasConflict()
    with pytest.raises(CasConflict):
        guard.compare_and_swap(CASES_KEY, {}, "etag")
    backing.compare_and_swap.side_effect = TimeoutError("private-offline-token/private-payload")
    exc = assert_503(lambda: guard.compare_and_swap(CASES_KEY, {}, "etag"), "STORAGE_UNAVAILABLE")
    assert "private" not in str(exc)
    backing.read.side_effect = RuntimeError("private-key")
    exc = assert_503(lambda: guard.read(CASES_KEY), "STORAGE_UNAVAILABLE")
    assert "private" not in str(exc)


@pytest.mark.parametrize("problem", ["cases-absent", "budget-absent", "cases-corrupt", "budget-corrupt",
                                      "budget-mismatch", "read-timeout"])
def test_bad_cloud_state_blocks_analysis_and_health_without_any_write(problem, monkeypatch):
    backing = seeded_store()
    observed = Mock(wraps=backing)
    def read(key):
        if (problem == "cases-absent" and key == CASES_KEY) or (problem == "budget-absent" and key == BUDGET_KEY):
            return None
        if problem == "read-timeout":
            raise TimeoutError("private-offline-token in exception")
        value = backing.read(key)
        if (problem == "cases-corrupt" and key == CASES_KEY) or (problem == "budget-corrupt" and key == BUDGET_KEY):
            return type(value)({}, value.version)
        if problem == "budget-mismatch" and key == BUDGET_KEY:
            value.payload["initialReservedCents"] = 0
        return value
    observed.read.side_effect = read
    install_cloud(monkeypatch, observed)
    runtime = storage.get_runtime_storage()
    runtime.service.analyzer.analyze = Mock(side_effect=AssertionError("must stop before analysis"))
    result = asyncio.run(handlers.analyze_case("CASE-0001", {"mode": "demo-live"}))
    assert result[1] == 503
    assert result[0]["error"]["code"] == "STORAGE_UNAVAILABLE"
    health = asyncio.run(handlers.health())
    assert health == result
    assert "private" not in json.dumps(health)
    assert "offline-token" not in json.dumps(health)
    runtime.service.analyzer.analyze.assert_not_called()
    observed.compare_and_swap.assert_not_called()


def test_cached_runtime_rechecks_state_and_cannot_mask_later_missing_ledger(monkeypatch):
    backing, _ = install_cloud(monkeypatch)
    runtime = storage.get_runtime_storage()
    assert handlers.service() is runtime.service
    original = backing.read
    backing.read = Mock(side_effect=lambda key: None if key == BUDGET_KEY else original(key))
    assert_503(handlers.service, "STORAGE_UNAVAILABLE")
    assert storage.get_runtime_storage() is runtime


def test_budget_disappearing_after_preflight_blocks_paid_model_calls(monkeypatch):
    backing, _ = install_cloud(monkeypatch)
    runtime = storage.get_runtime_storage()
    runtime.service.intake({"storeId": "SYN-ST01", "subject": "배송 확인", "text": "확인해 주세요", "type": "missing"})
    case = next(case for case in runtime.repository.list() if case["id"].startswith("INT-"))
    handlers.service()  # Healthy before the subsequent disappearance.
    client = Mock()
    runtime.service.analyzer.client_factory = Mock(return_value=client)
    original = backing.read
    backing.read = Mock(side_effect=lambda key: None if key == BUDGET_KEY else original(key))
    writes = Mock(wraps=backing.compare_and_swap)
    backing.compare_and_swap = writes
    assert_503(lambda: runtime.service.analyze(case["id"], "demo-live"), "STORAGE_UNAVAILABLE")
    client.chat.completions.create.assert_not_called()
    client.audio.transcriptions.create.assert_not_called()
    writes.assert_not_called()


def test_health_and_live_reservation_observe_the_same_budget_object(monkeypatch):
    install_cloud(monkeypatch)
    runtime = storage.get_runtime_storage()
    assert handlers.service().analyzer.budget is runtime.budget
    request_id = runtime.service.analyzer.budget.reserve(15, "analysis-text")
    health = asyncio.run(handlers.health())
    assert health["status"] == "ok"
    assert health["budget"]["reservedUsd"] == .9
    assert health["budget"]["accounting"] == "conservative-shared-reservations"
    runtime.budget.finish(request_id, False)
    assert asyncio.run(handlers.health())["budget"]["reservedUsd"] == .9


def test_health_key_readiness_is_separate_and_failed_storage_never_returns_success(monkeypatch):
    install_cloud(monkeypatch)
    monkeypatch.setattr(runtime_config, "require_demo_api_key", Mock(side_effect=DemoError("API_KEY_MISSING", "safe", 503)))
    healthy = asyncio.run(handlers.health())
    assert healthy["liveReady"] is False
    assert healthy["status"] == "ok"
    monkeypatch.setenv("ONEFLOW_BUDGET_INITIAL_RESERVED_CENTS", "")
    failed = asyncio.run(handlers.health())
    assert failed[1] == 503
    assert failed[0]["error"]["code"] == "STORAGE_UNAVAILABLE"


def test_bad_constructor_exception_is_static_and_does_not_fallback_to_local(monkeypatch):
    use_env(monkeypatch, BLOB_ENV)
    constructor = Mock(side_effect=RuntimeError("synthetic-secret-url-and-token"))
    local = Mock(side_effect=AssertionError("no fallback"))
    monkeypatch.setattr(storage, "VercelBlobCasStore", constructor)
    monkeypatch.setattr(storage, "JsonCaseRepository", local)
    response = asyncio.run(handlers.list_cases())
    assert response[1] == 503
    assert response[0]["error"]["code"] == "STORAGE_CONFIG_INVALID"
    assert "secret" not in json.dumps(response)
    local.assert_not_called()


def test_service_factory_and_health_storage_reads_run_off_event_loop_thread(monkeypatch):
    main_thread = get_ident()
    seen = []
    runtime = Mock()
    runtime.backend = "vercel-blob"
    runtime.check_ready.side_effect = lambda: seen.append(get_ident()) or {"reservedUsd": 0}
    runtime.service.list.return_value = {"cases": []}
    monkeypatch.setattr(handlers, "get_runtime_storage", Mock(return_value=runtime))
    assert asyncio.run(handlers.list_cases()) == {"cases": []}
    assert asyncio.run(handlers.health())["budget"]["reservedUsd"] == 0
    assert len(seen) == 2
    assert all(thread != main_thread for thread in seen)


def test_status_read_racing_with_reserve_never_writes_old_state(monkeypatch):
    backing, _ = install_cloud(monkeypatch)
    runtime = storage.get_runtime_storage()
    before = backing.read(BUDGET_KEY)
    barrier = Barrier(2)
    original_read = backing.read
    first_status = True
    def racing_read(key):
        nonlocal first_status
        value = original_read(key)
        if key == BUDGET_KEY and first_status:
            first_status = False
            barrier.wait(timeout=10)
            barrier.wait(timeout=10)
        return value
    backing.read = racing_read
    with ThreadPoolExecutor(max_workers=2) as pool:
        status_future = pool.submit(runtime.check_ready)
        barrier.wait(timeout=10)
        request_id = runtime.budget.reserve(15, "analysis-text")
        barrier.wait(timeout=10)
        snapshot = status_future.result(timeout=10)
    assert snapshot["reservedUsd"] == .75
    after = original_read(BUDGET_KEY)
    assert after.version != before.version
    assert len(after.payload["entries"]) == 1
    assert after.payload["entries"][0]["requestId"] == request_id
    assert runtime.check_ready()["reservedUsd"] == .9


@pytest.mark.parametrize("failure", ["http400", "http503", "timeout", "bad-json"])
def test_actual_blob_adapter_write_errors_are_static_503_in_intake_and_reserve(failure, monkeypatch):
    backing = seeded_store()
    CasCaseRepository(backing).create({"id": "INT-OFFLINE", "channel": "text", "status": "draft", "text": "합성 문의"})
    writes = []
    def respond(request):
        if request.method == "GET":
            value = backing.read(request.url.path.lstrip("/"))
            assert value is not None
            return httpx.Response(200, json=value.payload, headers={"etag": '"offline-etag"'})
        writes.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("private-response-token", request=request)
        if failure == "bad-json":
            return httpx.Response(200, content=b"private-response-token, not json")
        return httpx.Response(400 if failure == "http400" else 503,
                              json={"error": {"code": "private-response-token", "message": "private-input"}})
    adapter = VercelBlobCasStore(token="offline-only-token", store_id="store_offline123",
                                transport=httpx.MockTransport(respond))
    try:
        install_cloud(monkeypatch, adapter)
        runtime = storage.get_runtime_storage()
        client = Mock()
        runtime.service.analyzer.client_factory = Mock(return_value=client)
        intake = asyncio.run(handlers.create_intake({"storeId": "SYN-ST01", "subject": "문의", "text": "합성 문의", "type": "missing"}))
        analysis = asyncio.run(handlers.analyze_case("INT-OFFLINE", {"mode": "demo-live"}))
        for result in (intake, analysis):
            assert result[1] == 503
            assert result[0]["error"]["code"] == "STORAGE_UNAVAILABLE"
            assert "private" not in json.dumps(result)
            assert "offline-only-token" not in json.dumps(result)
        assert len(writes) == 2  # One attempt per operation, no uncertain-write retries.
        client.chat.completions.create.assert_not_called()
        client.audio.transcriptions.create.assert_not_called()
    finally:
        adapter.close()


@pytest.mark.parametrize("failure", ["absent", "timeout", "malformed"])
def test_actual_blob_adapter_read_failure_prevents_handler_analysis_and_reseed(failure, monkeypatch):
    requests = []
    def respond(request):
        requests.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("private-response-token", request=request)
        if failure == "absent":
            return httpx.Response(404)
        return httpx.Response(200, content=b"private-response-token", headers={"etag": '"offline-etag"'})
    adapter = VercelBlobCasStore(token="offline-only-token", store_id="store_offline123",
                                transport=httpx.MockTransport(respond))
    try:
        install_cloud(monkeypatch, adapter)
        runtime = storage.get_runtime_storage()
        runtime.service.analyzer.analyze = Mock(side_effect=AssertionError("preflight must stop analysis"))
        result = asyncio.run(handlers.analyze_case("CASE-0001", {"mode": "demo-live"}))
        assert result[1] == 503
        assert result[0]["error"]["code"] == "STORAGE_UNAVAILABLE"
        assert "private" not in json.dumps(result)
        assert [request.method for request in requests] == ["GET"]
        runtime.service.analyzer.analyze.assert_not_called()
    finally:
        adapter.close()
