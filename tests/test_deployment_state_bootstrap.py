"""Bootstrap checks with fake CAS only; no environment files or remote calls."""
import copy
import json

import pytest

from scripts import bootstrap_deployment_state as tool
from server.cas_budget import CasBudget
from server.cas_store import InMemoryCasStore, CasConflict


CASES = {"cases": [{"id": "SYNTHETIC-BOOTSTRAP", "revision": 4,
                     "text": "PRIVATE-SOURCE-SENTINEL", "history": [{"kind": "synthetic"}]}]}


class Store(InMemoryCasStore):
    def __init__(self):
        super().__init__()
        self.writes = []

    def compare_and_swap(self, key, payload, expected_version):
        self.writes.append((key, expected_version))
        return super().compare_and_swap(key, payload, expected_version)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_create_readback_preserves_input_and_carries_baseline_once():
    store = Store()
    before = copy.deepcopy(CASES)
    result = tool.bootstrap(store, CASES, 2920)
    assert result == {"status": "created", "createdDocuments": 2, "attemptedWrites": 2,
                      "caseCount": 1, "baselineReservedCents": 2920,
                      "budgetEntryCount": 0, "totalReservedCents": 2920}
    assert store.writes == [(tool.BUDGET_KEY, None), (tool.CASES_KEY, None)]
    assert store.read(tool.CASES_KEY).payload == CASES == before
    initial = store.read(tool.BUDGET_KEY)
    result = tool.bootstrap(store, CASES, 2920)
    assert result["status"] == "already_initialized" and result["createdDocuments"] == 0
    assert store.read(tool.BUDGET_KEY) == initial and len(store.writes) == 2


def test_existing_reservations_remain_and_different_baseline_is_rejected():
    store = Store()
    tool.bootstrap(store, CASES, 2920)
    CasBudget(store, initial_reserved_cents=2920).reserve(15, "synthetic")
    before = store.read(tool.BUDGET_KEY)
    count = len(store.writes)
    assert tool.bootstrap(store, CASES, 2920)["totalReservedCents"] == 2935
    with pytest.raises(tool.BootstrapError, match="EXISTING_BUDGET_MISMATCH"):
        tool.bootstrap(store, CASES, 0)
    assert store.read(tool.BUDGET_KEY) == before and len(store.writes) == count


def test_existing_case_mismatch_stops_before_any_create():
    store = Store()
    store.compare_and_swap(tool.CASES_KEY, CASES, None)
    changed = copy.deepcopy(CASES)
    changed["cases"][0]["revision"] = 3
    with pytest.raises(tool.BootstrapError, match="EXISTING_CASES_MISMATCH"):
        tool.bootstrap(store, changed, 2920)
    assert store.read(tool.BUDGET_KEY) is None and len(store.writes) == 1


def test_existing_cases_with_missing_budget_never_reseed_even_resume():
    store = Store()
    store.compare_and_swap(tool.CASES_KEY, CASES, None)
    with pytest.raises(tool.BootstrapError, match="MISSING_EXISTING_BUDGET"):
        tool.bootstrap(store, CASES, 2920, resume_partial=True)
    assert store.read(tool.BUDGET_KEY) is None and len(store.writes) == 1


def test_partial_failure_not_retried_then_requires_reviewed_pristine_resume():
    class FailCases(Store):
        fail = True

        def compare_and_swap(self, key, payload, expected_version):
            if key == tool.CASES_KEY and self.fail:
                raise OSError("SECRET-TOKEN PRIVATE-SOURCE-SENTINEL")
            return super().compare_and_swap(key, payload, expected_version)

    store = FailCases()
    with pytest.raises(tool.BootstrapError) as caught:
        tool.bootstrap(store, CASES, 2920)
    assert caught.value.code == "REMOTE_STATE_UNCERTAIN"
    assert (caught.value.created, caught.value.attempted) == (1, 2)
    budget = store.read(tool.BUDGET_KEY)
    store.fail = False
    with pytest.raises(tool.BootstrapError, match="PARTIAL_STATE_REQUIRES_REVIEW"):
        tool.bootstrap(store, CASES, 2920)
    result = tool.bootstrap(store, CASES, 2920, resume_partial=True)
    assert result["createdDocuments"] == 1 and result["totalReservedCents"] == 2920
    assert store.read(tool.BUDGET_KEY) == budget


def test_nonpristine_partial_budget_cannot_recreate_cases():
    store = Store()
    CasBudget(store, initial_reserved_cents=2920).reserve(15, "synthetic")
    before = store.read(tool.BUDGET_KEY)
    with pytest.raises(tool.BootstrapError, match="PARTIAL_STATE_NOT_PRISTINE"):
        tool.bootstrap(store, CASES, 2920, resume_partial=True)
    assert store.read(tool.BUDGET_KEY) == before and store.read(tool.CASES_KEY) is None


def test_create_race_is_not_overwritten_or_retried():
    class Race(Store):
        def compare_and_swap(self, key, payload, expected_version):
            super().compare_and_swap(key, payload, expected_version)
            raise CasConflict()

    store = Race()
    with pytest.raises(tool.BootstrapError, match="CREATE_CONFLICT_REVIEW_REQUIRED"):
        tool.bootstrap(store, CASES, 2920)
    assert len(store.writes) == 1 and store.read(tool.CASES_KEY) is None
    assert store.read(tool.BUDGET_KEY).payload["initialReservedCents"] == 2920


def test_confirmed_put_requires_readback_not_only_success_response():
    class Lost(Store):
        reads = 0

        def read(self, key):
            self.reads += 1
            return None

    store = Lost()
    with pytest.raises(tool.BootstrapError, match="READBACK_STATE_MISSING"):
        tool.bootstrap(store, CASES, 2920)
    assert len(store.writes) == 2


@pytest.mark.parametrize("amount", [-1, True, 2.5, None])
def test_invalid_baseline_has_no_writes(amount):
    store = Store()
    with pytest.raises(tool.BootstrapError, match="INVALID_BASELINE"):
        tool.bootstrap(store, CASES, amount)
    assert store.writes == []


@pytest.mark.parametrize("document", [{}, {"cases": [{"id": "x", "revision": True}]},
                                     {"cases": [{"id": "x"}, {"id": "x"}]},
                                     {"cases": [], "intakeRequests": {"x": {}}},
                                     {"cases": [], 1: "cannot-coerce-key"}])
def test_invalid_cases_has_no_writes(document):
    store = Store()
    with pytest.raises(tool.BootstrapError, match="INVALID_CASES_INPUT"):
        tool.bootstrap(store, document, 2920)
    assert store.writes == []


@pytest.mark.parametrize("backend", ["vercel-blob", "dynamodb"])
def test_dry_run_never_reads_credentials_or_constructs_transport(tmp_path, capsys, backend):
    path = tmp_path / "private-source.json"
    path.write_text(json.dumps(CASES), encoding="utf-8")

    class NoEnvironment:
        def get(self, key):
            raise AssertionError("must not inspect credentials")

    def forbidden(**kwargs):
        raise AssertionError("must not construct transport")

    assert tool.main(["--cases", str(path), "--baseline-reserved-cents", "2920", "--backend", backend],
                     environ=NoEnvironment(), store_factory=forbidden) == 0
    output = capsys.readouterr().out
    assert json.loads(output)["status"] == "dry_run_offline"
    assert "PRIVATE-SOURCE" not in output and str(path) not in output


def test_apply_requires_reviewed_baseline_gate_before_environment(tmp_path, capsys):
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(CASES), encoding="utf-8")
    assert tool.main(["--cases", str(path), "--baseline-reserved-cents", "2920", "--apply"],
                     environ={}) == 1
    assert json.loads(capsys.readouterr().out)["code"] == "BASELINE_REVIEW_CONFIRMATION_REQUIRED"


def test_apply_uses_only_named_environment_and_sanitizes_transport_error(tmp_path, capsys):
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(CASES), encoding="utf-8")
    args = ["--cases", str(path), "--baseline-reserved-cents", "2920", "--apply",
            "--confirm-baseline-reviewed"]
    environment = {"BLOB_READ_WRITE_TOKEN": "SECRET-TOKEN-SENTINEL", "ONEFLOW_BLOB_STORE_ID": "offline123"}
    store = Store()
    assert tool.main(args, environ=environment, store_factory=lambda **kwargs: store) == 0
    assert json.loads(capsys.readouterr().out)["totalReservedCents"] == 2920

    def fail(**kwargs):
        raise OSError("SECRET-TOKEN-SENTINEL PRIVATE-SOURCE-SENTINEL")

    assert tool.main(args, environ=environment, store_factory=fail) == 1
    output = capsys.readouterr().out
    assert json.loads(output)["code"] == "REMOTE_STATE_UNCERTAIN"
    assert "SENTINEL" not in output


def test_dynamodb_backend_reuses_create_only_guards_with_table_environment(tmp_path, capsys):
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(CASES), encoding="utf-8")
    args = ["--cases", str(path), "--baseline-reserved-cents", "2920", "--backend", "dynamodb",
            "--apply", "--confirm-baseline-reviewed"]
    observed = []
    store = Store()

    def factory(**kwargs):
        observed.append(kwargs)
        return store

    for expected in ("created", "already_initialized"):
        assert tool.main(args, environ={"ONEFLOW_DYNAMODB_TABLE": "synthetic-table"}, store_factory=factory) == 0
        assert json.loads(capsys.readouterr().out)["status"] == expected
    assert observed == [{"table_name": "synthetic-table"}] * 2
    assert len(store.writes) == 2


def test_dynamodb_size_limit_checked_before_environment_or_partial_writes(tmp_path, capsys):
    path = tmp_path / "cases.json"
    cases = copy.deepcopy(CASES)
    cases["cases"][0]["text"] = "x" * (350 * 1024)
    path.write_text(json.dumps(cases), encoding="utf-8")
    assert tool.main(["--cases", str(path), "--baseline-reserved-cents", "2920", "--backend", "dynamodb"],
                     environ={}) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["code"] == "DYNAMODB_CASES_TOO_LARGE_OR_INVALID" and result["attemptedWrites"] == 0


@pytest.mark.parametrize("raw", ['{"cases":[],"cases":[]}', '{"cases":[],"x":NaN}', '[]'])
def test_strict_input_json_refuses_ambiguous_documents(tmp_path, raw):
    path = tmp_path / "cases.json"
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(tool.BootstrapError, match="INVALID_CASES_INPUT"):
        tool.read_cases(path)
