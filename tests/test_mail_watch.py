import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "channel"))
import mail


def issue(number=6, comments=0, state="OPEN"):
    return {"number": number, "title": "worker task", "state": state,
            "labels": [{"name": "to:pc2"}, {"name": "from:pc1"}],
            "author": {"login": "worker"}, "comments": [{}] * comments}


class WatchTests(unittest.TestCase):
    def snapshots(self, previous, current):
        # pc1 receives nothing; both samples are replies on pc1's outgoing issue.
        with patch.object(mail, "sh", side_effect=["[]", json.dumps([previous]), "[]", json.dumps([current])]) as cli:
            old, new = mail._snapshot("to:pc1"), mail._snapshot("to:pc1")
        for call in cli.call_args_list:
            self.assertEqual(call.args[0][:3], ["gh", "issue", "list"])
        return old, new

    def test_outgoing_reply_is_visible_to_main(self):
        old, new = self.snapshots(issue(), issue(comments=1))
        self.assertTrue(any("회신 1건 #6" in e for e in mail._diff(old, new)))

    def test_reply_and_close_between_polls_both_visible(self):
        old, new = self.snapshots(issue(), issue(comments=1, state="CLOSED"))
        events = mail._diff(old, new)
        self.assertEqual(len(events), 2)
        self.assertTrue(any("닫힘 #6" in e for e in events))

    def test_unchanged_poll_silent(self):
        old, new = self.snapshots(issue(comments=2), issue(comments=2))
        self.assertEqual(mail._diff(old, new), [])

    def test_missing_result_is_not_reported_as_closed(self):
        old, _ = self.snapshots(issue(), issue())
        self.assertEqual(mail._diff(old, {}), [])

    def test_old_closed_issue_not_reported_as_new(self):
        _, new = self.snapshots(issue(), issue(state="CLOSED"))
        self.assertEqual(mail._diff({}, new), [])

    def test_network_failures_respect_loop_limit(self):
        args = argparse.Namespace(interval=3, max_loops=3, once=False, bell=False)
        with tempfile.TemporaryDirectory() as tmp, patch.object(mail, "me", return_value=("pc1", {"inbox": "to:pc1"})), \
             patch.object(mail, "_state_path", return_value=Path(tmp)/"state.json"), \
             patch.object(mail, "_snapshot", side_effect=SystemExit("offline")) as query, \
             patch("time.sleep") as sleep, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(mail.cmd_watch(args), 1)
            self.assertEqual(query.call_count, 3)
            self.assertEqual([c.args[0] for c in sleep.call_args_list], [3, 6])

    def test_query_cap_does_not_return_partial_success(self):
        with patch.object(mail, "sh", return_value=json.dumps([issue()] * 1000)):
            with self.assertRaises(SystemExit):
                mail._snapshot("to:pc1")

    def test_cli_uses_this_repository_even_from_another_cwd(self):
        with patch.object(mail.subprocess, "run") as run:
            run.return_value.returncode, run.return_value.stdout = 0, "[]"
            mail.sh(["gh", "issue", "list"])
            self.assertEqual(run.call_args.kwargs["cwd"], mail.ROOT)
            self.assertEqual(run.call_args.kwargs["timeout"], 45)


class WatchConsumerTests(unittest.TestCase):
    """Temporary snapshots and memory-only gh responses; no real mailbox IO."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mail-consumer-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.comments = 0
        self.calls = []
        self.addCleanup(patch.stopall)
        patch.object(mail, "ROOT", self.root).start()
        patch.object(mail, "me", return_value=("pc2", {"inbox": "to:pc2", "role": "ux-review"})).start()
        patch.object(mail, "sh", side_effect=self.memory_gh).start()

    def memory_gh(self, command, *args, **kwargs):
        self.calls.append(command)
        self.assertEqual(command[:3], ["gh", "issue", "list"])
        label = command[command.index("--label") + 1]
        self.assertIn(label, ("to:pc2", "from:pc2"))
        return json.dumps([issue(comments=self.comments)] if label == "to:pc2" else [])

    def watch_once(self, consumer=None, *, legacy=False):
        args = argparse.Namespace(interval=30, max_loops=0, once=True, bell=False)
        if not legacy:
            args.consumer = consumer
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = mail.cmd_watch(args)
        self.assertEqual(code, 0)
        return output.getvalue()

    def isolation_oracle(self):
        # Both consumers establish their own baseline at comment count zero.
        # A first-ever snapshot can announce the existing issue, not a reply.
        self.assertNotIn("회신", self.watch_once("daemon"))
        self.assertNotIn("회신", self.watch_once("main"))
        self.comments = 1
        first = self.watch_once("daemon")
        second = self.watch_once("main")
        self.assertEqual(first.count("회신 1건 #6"), 1)
        self.assertEqual(second.count("회신 1건 #6"), 1,
                         "Consumer B must detect the reply even after A wrote its snapshot")
        self.assertEqual(self.watch_once("daemon"), "")
        self.assertEqual(self.watch_once("main"), "")

    def test_each_consumer_detects_reply_after_other_consumer(self):
        self.isolation_oracle()
        expected = {".mailbox_state.pc2.daemon.json", ".mailbox_state.pc2.main.json"}
        self.assertEqual({p.name for p in self.root.iterdir()}, expected)
        for name in expected:
            self.assertEqual(json.loads((self.root / name).read_text(encoding="utf-8"))["6"]["comments"], 1)

    def test_default_snapshot_path_stays_exactly_compatible(self):
        self.assertEqual(mail._state_path("pc2"), self.root / ".mailbox_state.pc2.json")
        self.assertEqual(mail._state_path("pc2", None), self.root / ".mailbox_state.pc2.json")
        self.watch_once()
        self.assertEqual([p.name for p in self.root.iterdir()], [".mailbox_state.pc2.json"])

    def test_legacy_namespace_without_consumer_still_works(self):
        self.watch_once(legacy=True)
        self.comments = 1
        self.assertEqual(self.watch_once(legacy=True).count("회신 1건 #6"), 1)
        self.assertEqual(self.watch_once(legacy=True), "")
        self.assertEqual([p.name for p in self.root.iterdir()], [".mailbox_state.pc2.json"])

    def test_named_consumer_does_not_advance_default_snapshot(self):
        self.watch_once()
        default = mail._state_path("pc2")
        before = default.read_bytes()
        self.watch_once("assistant")
        self.comments = 1
        self.assertEqual(self.watch_once("assistant").count("회신 1건 #6"), 1)
        self.assertEqual(default.read_bytes(), before)
        self.assertEqual(self.watch_once().count("회신 1건 #6"), 1)
        self.assertEqual(self.watch_once(), "")

    def test_named_path_keeps_registration_slot_separate(self):
        self.assertEqual(mail._state_path("pc2", "main"), self.root / ".mailbox_state.pc2.main.json")
        self.assertEqual(mail._state_path("pc3", "main"), self.root / ".mailbox_state.pc3.main.json")
        self.watch_once("pc4")
        self.assertTrue((self.root / ".mailbox_state.pc2.pc4.json").is_file())
        self.assertFalse((self.root / ".mailbox_state.pc4.json").exists())
        self.assertEqual({cmd[cmd.index("--label") + 1] for cmd in self.calls}, {"to:pc2", "from:pc2"})

    def test_consumer_valid_names_preserve_value_and_boundaries(self):
        for name in ("a", "main", "resident", "main-loop", "main_loop", "a0", "a" * 32):
            with self.subTest(name=name):
                self.assertEqual(mail._consumer_name(name), name)
                self.assertEqual(mail._state_path("pc2", name).parent, self.root)

    def test_invalid_consumer_helper_rejects_path_case_and_length(self):
        invalid = ("", ".", "..", "../pc1", "main/pc1", "main\\pc1", "main.pc1", "C:pc1",
                   "A", "Main", "main ", " main", "main\n", "main\0", "한글", "ｍain",
                   "1main", "_main", "-main", "a" * 33, 1, True, [], {})
        for name in invalid:
            with self.subTest(name=repr(name)):
                with self.assertRaises(argparse.ArgumentTypeError):
                    mail._consumer_name(name)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_direct_watch_invalid_name_stops_before_network_or_snapshot(self):
        for name in ("../pc1", "Main", "a" * 33, "main/pc1", ""):
            args = argparse.Namespace(interval=30, max_loops=0, once=True, bell=False, consumer=name)
            with self.subTest(name=name), self.assertRaises(SystemExit):
                mail.cmd_watch(args)
        self.assertEqual(self.calls, [])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_argparse_invalid_consumer_exits_two_without_dispatch(self):
        for name in ("../pc1", "Main", "a" * 33, ""):
            with self.subTest(name=name), patch.object(sys, "argv", ["mail.py", "watch", "--consumer", name, "--once"]), \
                 patch.object(mail, "cmd_watch") as dispatch, \
                 contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    mail.main()
                self.assertEqual(error.exception.code, 2)
                dispatch.assert_not_called()
        self.assertEqual(self.calls, [])

    def test_argparse_valid_consumer_dispatches_explicit_name(self):
        with patch.object(sys, "argv", ["mail.py", "watch", "--consumer", "main-loop", "--once"]), \
             patch.object(mail, "cmd_watch", return_value=0) as dispatch:
            self.assertEqual(mail.main(), 0)
        args = dispatch.call_args.args[0]
        self.assertEqual(args.consumer, "main-loop")
        self.assertIs(args.once, True)
        self.assertEqual(self.calls, [])

    def test_argparse_omitted_consumer_dispatches_none(self):
        with patch.object(sys, "argv", ["mail.py", "watch", "--once"]), \
             patch.object(mail, "cmd_watch", return_value=0) as dispatch:
            self.assertEqual(mail.main(), 0)
        self.assertIsNone(dispatch.call_args.args[0].consumer)
        self.assertEqual(self.calls, [])

    def test_unregistered_pc_cannot_watch_even_with_named_consumer(self):
        args = argparse.Namespace(interval=30, max_loops=0, once=True, bell=False, consumer="main")
        with patch.object(mail, "me", side_effect=SystemExit("unregistered pc")):
            with self.assertRaisesRegex(SystemExit, "unregistered"):
                mail.cmd_watch(args)
        self.assertEqual(self.calls, [])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_authentication_failure_does_not_create_snapshot(self):
        args = argparse.Namespace(interval=30, max_loops=0, once=True, bell=False, consumer="main")
        with patch.object(mail, "sh", side_effect=SystemExit("not authenticated")) as query, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(mail.cmd_watch(args), 1)
        self.assertEqual(query.call_count, 1)
        self.assertIn("조회 실패 1회", output.getvalue())
        self.assertEqual(list(self.root.iterdir()), [])

    def test_named_network_failure_preserves_last_good_snapshot_and_backoff(self):
        self.watch_once("main")
        path = mail._state_path("pc2", "main")
        before = path.read_bytes()
        args = argparse.Namespace(interval=3, max_loops=3, once=False, bell=False, consumer="main")
        with patch.object(mail, "sh", side_effect=SystemExit("offline")) as query, \
             patch("time.sleep") as sleep, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(mail.cmd_watch(args), 1)
        self.assertEqual(query.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [3, 6])
        self.assertEqual(path.read_bytes(), before)

    def test_mutation_removing_consumer_isolation_breaks_existing_oracle(self):
        # CONTROL and mutant use identical in-memory replies and the same
        # independent oracle. Only the snapshot path separation is removed.
        original_state_path = mail._state_path
        self.isolation_oracle()
        mutant_root = self.root / "mutant"
        mutant_root.mkdir()
        self.comments = 0
        with patch.object(mail, "ROOT", mutant_root), \
             patch.object(mail, "_state_path", side_effect=lambda slot, consumer=None:
                          mail.ROOT / f".mailbox_state.{slot}.json"):
            with self.assertRaisesRegex(AssertionError, "Consumer B must detect"):
                self.isolation_oracle()
        self.assertIs(mail._state_path, original_state_path)
        self.assertEqual({path.name for path in mutant_root.iterdir()}, {".mailbox_state.pc2.json"})


if __name__ == "__main__":
    unittest.main()
