import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / "ops/tasks.py"
spec = importlib.util.spec_from_file_location("task_board", PATH)
board = importlib.util.module_from_spec(spec)
spec.loader.exec_module(board)


class TaskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "channel").mkdir()
        (self.root / "channel/pcs.json").write_text(json.dumps({"slots": {
            "pc1": {"role": "main", "hostname": ["test-main"], "github": "main"},
            "pc2": {"role": "worker", "hostname": ["test-worker"], "github": "worker"}}}), encoding="utf-8")
        self.task = {"id": "T1", "title": "test", "owner": "pc1", "phase": "test", "minutes": 20,
                     "state": "TODO", "depends_on": [], "outputs": ["result.txt"], "checks": {"C1": "expected result"}}
        self.plan = {"tasks": [self.task]}
        (self.root / "result.txt").write_text("measured result", encoding="utf-8")

    def evidence(self, **updates):
        evidence = {"task_id": "T1", "spec_hash": board.spec_hash(self.task), "measured_at": "2026-09-21T00:00:00Z", "observer": "pc1",
                    "checks": {"C1": {"expected": "expected result", "observed": "measured result", "passed": True}}, "artifacts": ["result.txt"]}
        evidence.update(updates)
        (self.root / "evidence.json").write_text(json.dumps(evidence), encoding="utf-8")
        return evidence

    def test_full_lifecycle_checks_only_after_review_and_evidence(self):
        plan = board.transition(self.plan, "T1", "start", self.root)
        self.assertIn("- [ ] **T1", board.markdown(plan))
        plan = board.transition(plan, "T1", "review", self.root)
        self.evidence()
        plan = board.transition(plan, "T1", "accept", self.root, "evidence.json")
        self.assertIn("- [x] **T1", board.markdown(plan))
        self.assertEqual(len(plan["tasks"][0]["artifact_hashes"]), 2)
        self.assertEqual(self.task["state"], "TODO")

    def test_accept_requires_evidence(self):
        self.task["state"] = "REVIEW"
        with self.assertRaisesRegex(ValueError, "evidence"):
            board.transition(self.plan, "T1", "accept", self.root)

    def test_skip_review_rejected(self):
        self.evidence()
        with self.assertRaises(ValueError):
            board.transition(self.plan, "T1", "accept", self.root, "evidence.json")

    def test_unfinished_dependency_blocks_start(self):
        other = copy.deepcopy(self.task)
        other.update(id="T2", owner="pc2", depends_on=["T1"])
        self.plan["tasks"].append(other)
        with self.assertRaisesRegex(ValueError, "선행"):
            board.transition(self.plan, "T2", "start", self.root)

    def test_review_counts_towards_wip(self):
        self.task["state"] = "REVIEW"
        other = copy.deepcopy(self.task)
        other.update(id="T2", state="TODO")
        self.plan["tasks"].append(other)
        with self.assertRaisesRegex(ValueError, "하나"):
            board.transition(self.plan, "T2", "start", self.root)

    def test_unregistered_worker_blocks_start(self):
        cfg = board.read(self.root / "channel/pcs.json")
        cfg["slots"]["pc2"]["hostname"] = []
        (self.root / "channel/pcs.json").write_text(json.dumps(cfg), encoding="utf-8")
        self.task["owner"] = "pc2"
        with self.assertRaisesRegex(ValueError, "등록"):
            board.transition(self.plan, "T1", "start", self.root)

    def test_non_main_pc_cannot_write(self):
        with patch.object(board.platform, "node", return_value="test-worker"):
            with self.assertRaisesRegex(ValueError, "pc1"):
                board.main_pc(self.root)

    def test_failed_or_missing_observation_rejected(self):
        for item in ({"passed": False, "observed": "failure"}, {"passed": True, "observed": ""}):
            self.evidence(checks={"C1": {"expected": "expected result", **item}})
            with self.assertRaises(ValueError):
                board.verify_evidence(self.root, self.task, "evidence.json")

    def test_changed_criteria_rejected(self):
        self.evidence()
        self.task["checks"]["C1"] = "changed criterion"
        with self.assertRaisesRegex(ValueError, "버전"):
            board.verify_evidence(self.root, self.task, "evidence.json")

    def test_missing_artifact_rejected(self):
        self.evidence()
        (self.root / "result.txt").unlink()
        with self.assertRaisesRegex(ValueError, "산출물"):
            board.verify_evidence(self.root, self.task, "evidence.json")

    def test_outside_path_rejected(self):
        self.evidence(artifacts=["result.txt", "../outside.txt"])
        with self.assertRaisesRegex(ValueError, "내부"):
            board.verify_evidence(self.root, self.task, "evidence.json")

    def test_duplicate_and_cycle_rejected(self):
        with self.assertRaisesRegex(ValueError, "중복"):
            board.validate({"tasks": [self.task, copy.deepcopy(self.task)]})
        self.task["depends_on"] = ["T1"]
        with self.assertRaisesRegex(ValueError, "순환"):
            board.validate(self.plan)

    def test_lock_does_not_allow_second_writer(self):
        (self.root / "ops").mkdir()
        with board.lock(self.root):
            with self.assertRaises(FileExistsError):
                with board.lock(self.root):
                    pass
        self.assertFalse((self.root / "ops/.tasks.lock").exists())

    def test_hash_detects_post_accept_change(self):
        self.evidence()
        before = board.verify_evidence(self.root, self.task, "evidence.json")
        (self.root / "result.txt").write_text("changed", encoding="utf-8")
        after = board.verify_evidence(self.root, self.task, "evidence.json")
        self.assertNotEqual(before, after)

    def test_windows_newlines_do_not_change_text_evidence_hash(self):
        self.evidence()
        (self.root / "result.txt").write_bytes(b"one\ntwo\n")
        before = board.verify_evidence(self.root, self.task, "evidence.json")
        (self.root / "result.txt").write_bytes(b"one\r\ntwo\r\n")
        after = board.verify_evidence(self.root, self.task, "evidence.json")
        self.assertEqual(before, after)

    def test_reverify_requires_reason_and_records_old_hashes(self):
        self.task["state"] = "REVIEW"
        self.evidence()
        done = board.transition(self.plan, "T1", "accept", self.root, "evidence.json")
        with self.assertRaises(ValueError):
            board.transition(done, "T1", "reverify", self.root, "evidence.json")
        (self.root / "result.txt").write_text("corrected result", encoding="utf-8")
        again = board.transition(done, "T1", "reverify", self.root, "evidence.json", "repeat verification after correction")
        self.assertEqual(again["tasks"][0]["history"][-1]["previous_artifact_hashes"], done["tasks"][0]["artifact_hashes"])
        self.assertNotEqual(again["tasks"][0]["artifact_hashes"], done["tasks"][0]["artifact_hashes"])


if __name__ == "__main__":
    unittest.main()
