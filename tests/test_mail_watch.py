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


if __name__ == "__main__":
    unittest.main()
