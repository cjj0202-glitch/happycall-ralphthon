"""Offline CAS behavioral/concurrency tests; no real remote or paid API calls."""
from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
from threading import Barrier, Lock
import unittest
from unittest.mock import Mock

from server.cas_budget import CasBudget
from server.cas_repository import CasCaseRepository
from server.cas_store import CasConflict, InMemoryCasStore
from server.errors import DemoError
from server.repository import ROOT
from server.service import CaseService


class ObservedStore:
    def __init__(self, backing=None):
        self.backing = backing or InMemoryCasStore()
        self.writes = 0

    def read(self, key):
        return self.backing.read(key)

    def compare_and_swap(self, key, payload, expected_version):
        self.writes += 1
        return self.backing.compare_and_swap(key, payload, expected_version)


class RacingStore(ObservedStore):
    """Release the first N writes together after every caller has read."""
    def __init__(self, parties, backing=None):
        super().__init__(backing)
        self.barrier, self.guard = Barrier(parties), Lock()
        self.parties = parties

    def compare_and_swap(self, key, payload, expected_version):
        with self.guard:
            self.writes += 1
            should_wait = self.writes <= self.parties
        if should_wait:
            self.barrier.wait(timeout=10)
        return self.backing.compare_and_swap(key, payload, expected_version)


class HookStore(ObservedStore):
    def __init__(self, backing, hook):
        super().__init__(backing)
        self.hook = hook

    def compare_and_swap(self, key, payload, expected_version):
        hook, self.hook = self.hook, None
        if hook:
            hook()
        return super().compare_and_swap(key, payload, expected_version)


class RejectingStore(ObservedStore):
    def compare_and_swap(self, key, payload, expected_version):
        self.writes += 1
        raise CasConflict()


def parallel(operations):
    def capture(operation):
        try:
            return operation()
        except DemoError as exc:
            return exc
    with ThreadPoolExecutor(max_workers=len(operations)) as pool:
        return list(pool.map(capture, operations))


class ErrorAssertions(unittest.TestCase):
    def error(self, code, status, operation, *args, **kwargs):
        with self.assertRaises(DemoError) as caught:
            operation(*args, **kwargs)
        self.assertEqual((caught.exception.code, caught.exception.status), (code, status))


class StoreContractTests(ErrorAssertions):
    def test_absence_create_only_update_version_and_copy_isolation(self):
        store = InMemoryCasStore()
        self.assertIsNone(store.read("key"))
        payload = {"nested": [1]}
        first = store.compare_and_swap("key", payload, None)
        payload["nested"].append(2)
        self.assertEqual(store.read("key").payload, {"nested": [1]})
        snapshot = store.read("key")
        snapshot.payload["nested"].clear()
        with self.assertRaises(CasConflict):
            store.compare_and_swap("key", {}, None)
        second = store.compare_and_swap("key", {"nested": [3]}, first)
        self.assertNotEqual(first, second)
        with self.assertRaises(CasConflict):
            store.compare_and_swap("key", {"nested": [4]}, first)
        self.assertEqual(store.read("key").payload, {"nested": [3]})
        self.assertIsNone(store.read("other-key"))


class CasCaseTests(ErrorAssertions):
    def setUp(self):
        self.backing = InMemoryCasStore()
        self.repo = CasCaseRepository(self.backing)
        self.fixtures = self.repo.fixtures()["cases"]
        self.case_a, self.case_b = [case["id"] for case in self.fixtures]

    def change(self, repo, case_id, label):
        return repo.update(case_id, lambda case: {**case, "label": label})

    def test_shared_instances_read_created_case_and_do_not_leak_mutable_references(self):
        initial = self.repo.list()
        self.assertEqual(len(initial), 2)
        self.assertEqual({case["type"] for case in initial}, {"missing", "wrong"})
        original = copy.deepcopy(initial[0])
        initial[0]["intake"]["request"] = "external mutation"
        fixture = self.repo.fixtures()
        fixture["cases"].clear()
        self.assertEqual(self.repo.get(original["id"]), original)
        self.assertEqual(len(self.repo.fixtures()["cases"]), 2)
        source = {"id": "INT-COPY", "revision": 99, "nested": ["source"]}
        created = self.repo.create(source)
        source["nested"].append("source mutation")
        created["nested"].append("return mutation")
        reopened = CasCaseRepository(self.backing)
        self.assertEqual(reopened.get("INT-COPY"), {"id": "INT-COPY", "revision": 0, "nested": ["source"]})
        captured = []
        def transform(case):
            case["nested"].append("updated")
            captured.append(case)
            return case
        result = self.repo.update("INT-COPY", transform)
        result["nested"].clear()
        captured[0]["nested"].clear()
        self.assertEqual(reopened.get("INT-COPY")["nested"], ["source", "updated"])
        self.assertEqual(reopened.get("INT-COPY")["revision"], 1)

    def test_legacy_revisions_are_read_without_writes_then_increment_once(self):
        self.backing.compare_and_swap(self.repo.key, {"cases": self.fixtures, "extra": "preserved"}, None)
        observed = ObservedStore(self.backing)
        repo = CasCaseRepository(observed)
        self.assertEqual([case["revision"] for case in repo.list()], [0, 0])
        self.assertEqual(observed.writes, 0)
        self.assertNotIn("revision", self.backing.read(repo.key).payload["cases"][0])
        result = self.change(repo, self.case_a, "saved")
        self.assertEqual(result["revision"], 1)
        self.assertEqual(self.backing.read(repo.key).payload["extra"], "preserved")

    def test_missing_duplicate_and_transform_error_do_not_change_existing_data(self):
        before = self.repo.list()
        self.error("CASE_NOT_FOUND", 404, self.repo.get, "missing")
        self.error("CASE_NOT_FOUND", 404, self.repo.update, "missing", Mock())
        self.error("DUPLICATE_CASE", 409, self.repo.create, before[0])
        def fail(case):
            case["intake"]["request"] = "must not save"
            raise ValueError("transform failed")
        with self.assertRaises(ValueError):
            self.repo.update(self.case_a, fail)
        self.assertEqual(self.repo.list(), before)

    def test_initialization_race_does_not_overwrite_the_winners_new_intake(self):
        winner = CasCaseRepository(self.backing)
        hook = HookStore(self.backing, lambda: winner.create({"id": "INT-WINNER"}))
        loser = CasCaseRepository(hook)
        self.assertEqual({case["id"] for case in loser.list()}, {self.case_a, self.case_b, "INT-WINNER"})
        self.assertEqual(len(winner.list()), 3)

    def test_simultaneous_first_intakes_are_both_retained(self):
        racing = RacingStore(2)
        repos = [CasCaseRepository(racing) for _ in range(2)]
        result = parallel([lambda i=i: repos[i].create({"id": f"INT-{i}"}) for i in range(2)])
        self.assertFalse(any(isinstance(item, Exception) for item in result))
        self.assertEqual({case["id"] for case in repos[0].list()}, {self.case_a, self.case_b, "INT-0", "INT-1"})

    def test_duplicate_create_race_has_one_winner(self):
        self.repo.list()
        racing = RacingStore(2, self.backing)
        repos = [CasCaseRepository(racing) for _ in range(2)]
        results = parallel([lambda i=i: repos[i].create({"id": "INT-SAME", "writer": i}) for i in range(2)])
        self.assertEqual(sum(isinstance(item, dict) for item in results), 1)
        errors = [item.code for item in results if isinstance(item, DemoError)]
        self.assertEqual(errors, ["DUPLICATE_CASE"])
        self.assertEqual(sum(case["id"] == "INT-SAME" for case in self.repo.list()), 1)

    def test_competing_same_case_edits_reject_one_without_repeating_transform(self):
        self.repo.list()
        racing = RacingStore(2, self.backing)
        counts = [0, 0]
        def edit(index):
            def transform(case):
                counts[index] += 1
                return {**case, "label": f"writer-{index}"}
            return CasCaseRepository(racing).update(self.case_a, transform)
        results = parallel([lambda i=i: edit(i) for i in range(2)])
        winners = [item for item in results if isinstance(item, dict)]
        self.assertEqual(len(winners), 1)
        self.assertEqual([item.code for item in results if isinstance(item, DemoError)], ["STATE_CONFLICT"])
        self.assertEqual(counts, [1, 1])
        self.assertEqual(self.repo.get(self.case_a), winners[0])
        self.assertEqual(winners[0]["revision"], 1)

    def test_competing_different_case_edits_are_merged_without_repeating_transform(self):
        self.repo.list()
        racing = RacingStore(2, self.backing)
        counts = [0, 0]
        ids = [self.case_a, self.case_b]
        def edit(index):
            def transform(case):
                counts[index] += 1
                return {**case, "label": f"writer-{index}"}
            return CasCaseRepository(racing).update(ids[index], transform)
        results = parallel([lambda i=i: edit(i) for i in range(2)])
        self.assertTrue(all(isinstance(item, dict) for item in results))
        self.assertEqual(counts, [1, 1])
        self.assertEqual([(self.repo.get(cid)["label"], self.repo.get(cid)["revision"]) for cid in ids],
                         [("writer-0", 1), ("writer-1", 1)])

    def test_stale_center_form_cannot_erase_new_action_and_close(self):
        service = CaseService(self.repo, analyzer=Mock())
        initial = service.get(self.case_a)
        handoff = service.patch(self.case_a, {"expectedRevision": initial["revision"], "departmentId": "delivery",
                                             "reviewConfirmed": True, "status": "handed_off"})
        other = CaseService(CasCaseRepository(self.backing), analyzer=Mock())
        current = other.patch(self.case_a, {"expectedRevision": handoff["revision"], "pendingActions": ["기사 확인"],
                                           "status": "in_progress"}, "center")
        self.error("STATE_CONFLICT", 409, service.patch, self.case_a,
                   {"expectedRevision": handoff["revision"], "pendingActions": [], "reply": "완료", "status": "closed"}, "center")
        self.assertEqual(service.get(self.case_a), current)

    def test_patch_missing_revision_is_rejected_and_fresh_revision_is_accepted(self):
        service = CaseService(self.repo, analyzer=Mock())
        self.error("REVISION_REQUIRED", 428, service.patch, self.case_a, {"departmentId": "delivery"})
        saved = service.patch(self.case_a, {"expectedRevision": 0, "departmentId": "delivery"})
        self.assertEqual(saved["revision"], 1)
        self.assertEqual(saved["departmentId"], "delivery")

    def test_analysis_saves_through_other_case_collision_with_one_analyzer_call(self):
        self.repo.list()
        hook = HookStore(self.backing, lambda: self.change(self.repo, self.case_b, "other case edit"))
        fixture = self.fixtures[0]
        analyzer = Mock()
        analyzer.analyze.return_value = {"analysis": fixture.get("replayAnalysis") or fixture["analysis"],
                                         "transcript": fixture["transcript"], "requestId": "offline-only"}
        service = CaseService(CasCaseRepository(hook), analyzer=analyzer)
        result = service.analyze(self.case_a, "demo-live")
        analyzer.analyze.assert_called_once()
        self.assertEqual(result["revision"], 1)
        self.assertEqual(self.repo.get(self.case_b)["label"], "other case edit")
        self.assertEqual(self.repo.get(self.case_a)["analysisRequestId"], "offline-only")

    def test_analysis_same_case_collision_does_not_call_analyzer_again(self):
        self.repo.list()
        hook = HookStore(self.backing, lambda: self.change(self.repo, self.case_a, "human edit"))
        fixture = self.fixtures[0]
        analyzer = Mock()
        analyzer.analyze.return_value = {"analysis": fixture.get("replayAnalysis") or fixture["analysis"],
                                         "transcript": fixture["transcript"], "requestId": "offline-only"}
        service = CaseService(CasCaseRepository(hook), analyzer=analyzer)
        self.error("STATE_CONFLICT", 409, service.analyze, self.case_a, "demo-live")
        analyzer.analyze.assert_called_once()
        self.assertEqual(self.repo.get(self.case_a)["label"], "human edit")
        self.assertNotIn("analysisRequestId", self.repo.get(self.case_a))

    def test_retry_exhaustion_is_bounded_and_does_not_repeat_transform(self):
        before = self.repo.list()
        rejecting = RejectingStore(self.backing)
        repo = CasCaseRepository(rejecting, max_attempts=3)
        transform = Mock(side_effect=lambda case: {**case, "label": "not saved"})
        self.error("STORAGE_BUSY", 503, repo.update, self.case_a, transform)
        self.assertEqual(rejecting.writes, 3)
        transform.assert_called_once()
        self.assertEqual(self.repo.list(), before)
        self.error("STORAGE_BUSY", 503, repo.create, {"id": "INT-NOT-SAVED"})
        self.assertEqual(rejecting.writes, 6)

    def test_uncertain_transport_error_is_not_retried_or_reseeded(self):
        self.repo.list()
        store = ObservedStore(self.backing)
        store.compare_and_swap = Mock(side_effect=TimeoutError("uncertain write"))
        repo = CasCaseRepository(store)
        with self.assertRaises(TimeoutError):
            self.change(repo, self.case_a, "not confirmed")
        store.compare_and_swap.assert_called_once()
        broken = Mock()
        broken.read.side_effect = TimeoutError("read failed")
        with self.assertRaises(TimeoutError):
            CasCaseRepository(broken).list()
        broken.compare_and_swap.assert_not_called()

    def test_corrupt_existing_documents_do_not_reset_to_fixtures(self):
        for payload in ({}, {"cases": {}}, {"cases": [{"id": "x", "revision": -1}]},
                        {"cases": [{"id": "x"}, {"id": "x"}]}, {"cases": [{"id": "x", "revision": True}]}):
            with self.subTest(payload=payload):
                store = ObservedStore()
                store.backing.compare_and_swap("oneflow/cases.json", payload, None)
                self.error("STORAGE_INVALID", 503, CasCaseRepository(store).list)
                self.assertEqual(store.writes, 0)
                self.assertEqual(store.read("oneflow/cases.json").payload, payload)

    def test_fixture_list_and_wrapper_and_missing_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixtures.json"
            self.error("FIXTURES_NOT_READY", 503, CasCaseRepository(InMemoryCasStore(), fixture_path=path).list)
            for data in ([{"id": "custom"}], {"cases": [{"id": "custom"}], "departments": [{"id": "custom-dept"}]}):
                path.write_text(json.dumps(data), encoding="utf-8-sig")
                repo = CasCaseRepository(InMemoryCasStore(), fixture_path=path)
                self.assertEqual(repo.list(), [{"id": "custom", "revision": 0}])
                if isinstance(data, dict):
                    self.assertEqual(repo.fixtures()["departments"], data["departments"])

    def test_invalid_transform_cannot_change_case_identity(self):
        before = self.repo.get(self.case_a)
        self.error("INVALID_CASE_UPDATE", 422, self.repo.update, self.case_a, lambda case: {**case, "id": "different"})
        self.assertEqual(self.repo.get(self.case_a), before)

    def test_document_disappearing_after_conflict_is_not_reinitialized(self):
        before = self.repo.list()
        store = Mock()
        store.read.side_effect = [self.backing.read(self.repo.key), None]
        store.compare_and_swap.side_effect = CasConflict()
        self.error("STORAGE_STATE_LOST", 503, self.change, CasCaseRepository(store), self.case_a, "lost")
        store.compare_and_swap.assert_called_once()
        self.assertEqual(self.repo.list(), before)

    def test_target_body_change_without_revision_increment_is_still_rejected(self):
        self.repo.list()
        def out_of_contract_writer():
            value = self.backing.read(self.repo.key)
            value.payload["cases"][0]["intake"]["request"] = "changed without revision"
            self.backing.compare_and_swap(self.repo.key, value.payload, value.version)
        hook = HookStore(self.backing, out_of_contract_writer)
        self.error("STATE_CONFLICT", 409, self.change, CasCaseRepository(hook), self.case_a, "not saved")
        self.assertEqual(self.repo.get(self.case_a)["intake"]["request"], "changed without revision")
        self.assertNotIn("label", self.repo.get(self.case_a))


class CasBudgetTests(ErrorAssertions):
    def setUp(self):
        self.backing = InMemoryCasStore()

    def budget(self, store=None, **kwargs):
        return CasBudget(store or self.backing, limit_cents=100, warn_cents=80, **kwargs)

    def test_migrated_total_counts_once_on_reopen_and_exact_limit_is_allowed(self):
        budget = self.budget(initial_reserved_cents=79)
        self.assertFalse(budget.status()["warning"])
        first = budget.reserve(1, "analysis-text")
        self.assertTrue(budget.status()["warning"])
        other = self.budget(initial_reserved_cents=79)
        second = other.reserve(20, "analysis-audio")
        self.assertNotEqual(first, second)
        self.assertEqual(budget.status()["reservedUsd"], 1)
        self.error("BUDGET_LIMIT", 429, other.reserve, 1, "analysis-text")
        self.assertEqual(len(self.backing.read(budget.key).payload["entries"]), 2)
        self.assertEqual(other.status()["accounting"], "conservative-shared-reservations")

    def test_migration_over_limit_is_preserved_and_blocks_calls(self):
        budget = self.budget(initial_reserved_cents=101)
        self.assertEqual(budget.status()["reservedUsd"], 1.01)
        self.assertTrue(budget.status()["warning"])
        self.error("BUDGET_LIMIT", 429, budget.reserve, 1, "analysis-text")
        self.assertEqual(self.backing.read(budget.key).payload["initialReservedCents"], 101)

    def test_configuration_drift_fails_closed_without_reset(self):
        budget = self.budget(initial_reserved_cents=30)
        budget.reserve(10, "analysis-text")
        before = self.backing.read(budget.key)
        for configuration in ({"initial_reserved_cents": 0}, {"initial_reserved_cents": 40},
                              {"initial_reserved_cents": 30, "limit_cents": 200},
                              {"initial_reserved_cents": 30, "warn_cents": 90}):
            options = {"limit_cents": 100, "warn_cents": 80, **configuration}
            other = CasBudget(self.backing, **options)
            self.error("BUDGET_CONFIG_MISMATCH", 503, other.status)
            self.error("BUDGET_CONFIG_MISMATCH", 503, other.reserve, 1, "analysis-text")
            self.assertEqual(self.backing.read(budget.key), before)

    def test_initialization_race_preserves_winner_reservation(self):
        winner = self.budget(initial_reserved_cents=30)
        hooked = HookStore(self.backing, lambda: winner.reserve(10, "analysis-text"))
        loser = self.budget(hooked, initial_reserved_cents=30)
        self.assertEqual(loser.status()["reservedUsd"], .4)
        self.assertEqual(len(self.backing.read(winner.key).payload["entries"]), 1)

    def test_parallel_global_reservations_never_exceed_limit(self):
        self.budget(initial_reserved_cents=10).status()
        racing = RacingStore(12, self.backing)
        budgets = [self.budget(racing, initial_reserved_cents=10, max_attempts=32) for _ in range(12)]
        results = parallel([lambda budget=budget: budget.reserve(15, "analysis-text") for budget in budgets])
        accepted = [item for item in results if isinstance(item, str)]
        rejected = [item for item in results if isinstance(item, DemoError)]
        self.assertEqual(len(accepted), 6)
        self.assertEqual(len(set(accepted)), 6)
        self.assertEqual([item.code for item in rejected], ["BUDGET_LIMIT"] * 6)
        self.assertEqual(budgets[0].status()["reservedUsd"], 1)
        self.assertEqual(len(self.backing.read(budgets[0].key).payload["entries"]), 6)

    def test_failed_and_completed_reservations_remain_and_finish_is_idempotent(self):
        budget = self.budget()
        failed = budget.reserve(25, "analysis-text")
        completed = budget.reserve(25, "analysis-audio")
        budget.finish(failed, False)
        budget.finish(failed, True)
        budget.finish(completed, True)
        budget.finish(completed, False)
        before = self.backing.read(budget.key)
        budget.finish(failed, False)
        budget.finish(completed, True)
        budget.finish("unknown", False)
        self.assertEqual(self.backing.read(budget.key), before)
        self.assertEqual(budget.status()["reservedUsd"], .5)
        states = {entry["requestId"]: entry["state"] for entry in before.payload["entries"]}
        self.assertEqual(states, {failed: "failed-cost-uncertain", completed: "completed"})

    def test_parallel_duplicate_finishes_have_one_terminal_write(self):
        original = self.budget()
        request_id = original.reserve(50, "analysis-text")
        racing = RacingStore(2, self.backing)
        budgets = [self.budget(racing) for _ in range(2)]
        outcomes = parallel([lambda index=i: budgets[index].finish(request_id, bool(index)) for i in range(2)])
        self.assertEqual(outcomes, [None, None])
        entry = self.backing.read(original.key).payload["entries"][0]
        self.assertIn(entry["state"], ("completed", "failed-cost-uncertain"))
        self.assertEqual(original.status()["reservedUsd"], .5)
        self.assertEqual(racing.writes, 2)

    def test_finish_does_not_drop_a_concurrent_new_reservation(self):
        original = self.budget()
        request_id = original.reserve(30, "analysis-text")
        hook = HookStore(self.backing, lambda: original.reserve(40, "analysis-audio"))
        self.budget(hook).finish(request_id, False)
        data = self.backing.read(original.key).payload
        self.assertEqual(original.status()["reservedUsd"], .7)
        self.assertEqual(len(data["entries"]), 2)
        self.assertEqual(next(entry for entry in data["entries"] if entry["requestId"] == request_id)["state"],
                         "failed-cost-uncertain")

    def test_retry_exhaustion_retains_reservation_and_is_bounded(self):
        original = self.budget()
        request_id = original.reserve(20, "analysis-text")
        rejecting = RejectingStore(self.backing)
        budget = self.budget(rejecting, max_attempts=3)
        self.error("STORAGE_BUSY", 503, budget.reserve, 10, "analysis-text")
        self.assertEqual(rejecting.writes, 3)
        self.error("STORAGE_BUSY", 503, budget.finish, request_id, False)
        self.assertEqual(rejecting.writes, 6)
        self.assertEqual(original.status()["reservedUsd"], .2)
        self.assertEqual(self.backing.read(original.key).payload["entries"][0]["state"], "reserved")

    def test_uncertain_write_keeps_committed_charge_and_never_retries(self):
        budget = self.budget()
        budget.status()
        observed = ObservedStore(self.backing)
        def commit_then_timeout(key, payload, expected_version):
            self.backing.compare_and_swap(key, payload, expected_version)
            raise TimeoutError("response missing after commit")
        observed.compare_and_swap = Mock(side_effect=commit_then_timeout)
        with self.assertRaises(TimeoutError):
            self.budget(observed).reserve(30, "analysis-text")
        observed.compare_and_swap.assert_called_once()
        self.assertEqual(budget.status()["reservedUsd"], .3)
        self.assertEqual(len(self.backing.read(budget.key).payload["entries"]), 1)

    def test_invalid_values_and_ledger_corruption_never_reset_budget(self):
        budget = self.budget()
        for cents in (0, -1, True, 1.5, "1", None):
            with self.subTest(cents=cents), self.assertRaises(ValueError):
                budget.reserve(cents, "analysis-text")
        self.assertIsNone(self.backing.read(budget.key))
        request_id = budget.reserve(10, "analysis-text")
        valid = self.backing.read(budget.key).payload
        corrupt = [None, {}, {**valid, "initialReservedCents": -1}, {**valid, "schemaVersion": True},
                   {**valid, "entries": [*valid["entries"], *valid["entries"]]},
                   {**valid, "entries": [{**valid["entries"][0], "reservedCents": -50}]}]
        for payload in corrupt:
            with self.subTest(payload=payload):
                store = ObservedStore()
                store.backing.compare_and_swap(budget.key, payload, None)
                target = self.budget(store)
                self.error("BUDGET_INVALID", 503, target.reserve, 1, "analysis-text")
                self.error("BUDGET_INVALID", 503, target.finish, request_id, False)
                self.assertEqual(store.writes, 0)
                self.assertEqual(store.read(budget.key).payload, payload)

    def test_constructor_rejects_invalid_configuration(self):
        for options in ({"limit_cents": 0}, {"warn_cents": -1}, {"warn_cents": 101, "limit_cents": 100},
                        {"initial_reserved_cents": True}, {"initial_reserved_cents": -1},
                        {"max_attempts": 0}, {"max_attempts": 1.1}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                CasBudget(self.backing, **options)

    def test_document_disappearing_after_conflict_does_not_reopen_budget(self):
        original = self.budget(initial_reserved_cents=50)
        original.reserve(10, "analysis-text")
        store = Mock()
        store.read.side_effect = [self.backing.read(original.key), None]
        store.compare_and_swap.side_effect = CasConflict()
        self.error("STORAGE_STATE_LOST", 503, self.budget(store, initial_reserved_cents=50).reserve, 10, "analysis-text")
        store.compare_and_swap.assert_called_once()
        self.assertEqual(original.status()["reservedUsd"], .6)

    def test_initialization_with_different_migration_amounts_has_no_silent_winner_reset(self):
        racing = RacingStore(2, self.backing)
        budgets = [self.budget(racing, initial_reserved_cents=amount) for amount in (30, 40)]
        result = parallel([budget.status for budget in budgets])
        accepted = [item for item in result if isinstance(item, dict)]
        rejected = [item for item in result if isinstance(item, DemoError)]
        self.assertEqual(len(accepted), 1)
        self.assertEqual([item.code for item in rejected], ["BUDGET_CONFIG_MISMATCH"])
        self.assertEqual(self.backing.read(budgets[0].key).payload["initialReservedCents"] / 100,
                         accepted[0]["reservedUsd"])


if __name__ == "__main__":
    unittest.main()
