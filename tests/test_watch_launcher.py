"""Launcher gates, process identity, and a real wrong-PID stop rejection."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if sys.platform == 'win32':
    spec = importlib.util.spec_from_file_location('watch_launcher', ROOT / 'scripts/mailbox_watch.py')
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)


@unittest.skipUnless(sys.platform == 'win32', 'Windows launcher')
class LauncherTests(unittest.TestCase):
    def test_forced_slot_rejected_before_queries(self):
        with patch.dict(os.environ, {'RALPH_PC': 'pc2'}), patch.object(launcher.subprocess, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'override forbidden'):
                launcher.identity()
            run.assert_not_called()

    def test_identity_registration_and_account_gates(self):
        for hosts, login, expected in [([], 'tester', False), (['host'], 'wrong', False), (['host'], 'tester', True)]:
            with self.subTest(hosts=hosts, login=login), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'channel').mkdir()
                (root / 'channel/pcs.json').write_text(json.dumps({'slots': {'pc3': {'hostname': hosts, 'github': 'tester', 'inbox': 'to:pc3'}}}))
                result = subprocess.CompletedProcess([], 0, login, '')
                with patch.object(launcher, 'ROOT', root), patch.object(launcher.platform, 'node', return_value='host'), \
                     patch.dict(os.environ, {'RALPH_PC': ''}), patch.object(launcher.subprocess, 'run', return_value=result) as run, \
                     contextlib.redirect_stdout(io.StringIO()):
                    actual = launcher.identity()
                self.assertEqual(actual is not None, expected)
                commands = [call.args[0] for call in run.call_args_list]
                self.assertFalse(any('mail.py' in str(command) for command in commands))
                self.assertEqual(len(commands), 2 if not hosts else 1)
                if not hosts:
                    self.assertTrue(commands[-1][1].endswith('preflight.py'))

    def identity_fixture(self):
        command = subprocess.list2cmdline([sys.executable, '-u', str(launcher.MAIL), 'watch', '--interval', '30'])
        state = dict(engine='python', repo_root=str(launcher.ROOT), process_id=123, command_line=command,
                     executable_path=sys.executable, created_ticks=10, interval_seconds=30)
        process = dict(ProcessId=123, CommandLine=command, ExecutablePath=sys.executable)
        return state, process

    def test_exact_process_matches_and_each_mutation_fails(self):
        state, process = self.identity_fixture()
        with patch.object(launcher, 'created_ticks', return_value=10):
            self.assertTrue(launcher.verify(state, process, None))
            for key, value in [('process_id', 124), ('created_ticks', 11), ('repo_root', 'C:\\elsewhere'),
                               ('command_line', 'python other.py'), ('executable_path', 'C:\\other.exe'), ('interval_seconds', 31)]:
                with self.subTest(field=key):
                    self.assertFalse(launcher.verify(dict(state, **{key: value}), process, None))

    def test_duplicate_detection_absolute_and_relative(self):
        for command in ['python channel/mail.py watch --interval 30', 'python "C:\\space repo\\channel\\mail.py" watch']:
            self.assertTrue(launcher.is_watch({'CommandLine': command}))
        self.assertFalse(launcher.is_watch({'CommandLine': 'python mailbox_watch.py start'}))
        self.assertFalse(launcher.is_watch({'CommandLine': 'python mail.py inbox'}))

    def test_lock_excludes_concurrent_launcher(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(launcher, 'LOCAL', Path(tmp)):
            with launcher.lock():
                with self.assertRaisesRegex(RuntimeError, 'holds the lock'):
                    with launcher.lock():
                        self.fail('second lock was acquired')
            with launcher.lock():
                pass

    def test_real_wrong_pid_stop_does_not_kill_test_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'scripts').mkdir()
            (root / '.local').mkdir()
            shutil.copyfile(ROOT / 'scripts/mailbox_watch.py', root / 'scripts/mailbox_watch.py')
            state, _ = self.identity_fixture()
            state.update(repo_root=str(root), process_id=os.getpid(), command_line='wrong command')
            state_path = root / '.local/mailbox-watch.json'
            state_path.write_text(json.dumps(state))
            result = subprocess.run([sys.executable, str(root / 'scripts/mailbox_watch.py'), 'stop'], capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn('mismatch', result.stderr)
            self.assertTrue(state_path.exists(), 'mismatched state must remain for inspection')


if __name__ == '__main__':
    unittest.main()
