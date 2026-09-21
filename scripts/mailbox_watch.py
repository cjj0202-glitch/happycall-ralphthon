"""Windows mailbox launcher. No PowerShell execution-policy changes required."""
from __future__ import annotations

import argparse
import contextlib
import ctypes
from ctypes import wintypes
import json
import msvcrt
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local'
STATE = LOCAL / 'mailbox-watch.json'
MAIL = ROOT / 'channel/mail.py'
HIDDEN = subprocess.CREATE_NO_WINDOW


def query_processes():
    command = """$ErrorActionPreference='Stop'; [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false); @(Get-CimInstance Win32_Process -Filter "Name LIKE 'python%.exe'" | Select-Object ProcessId,ExecutablePath,CommandLine) | ConvertTo-Json -Compress"""
    result = subprocess.run(['powershell', '-NoProfile', '-Command', command],
                            capture_output=True, encoding='utf-8', errors='replace',
                            timeout=30, creationflags=HIDDEN)
    if result.returncode:
        raise RuntimeError('Cannot inspect process commands; refusing start/stop.')
    rows = json.loads(result.stdout or '[]')
    return rows if isinstance(rows, list) else [rows]


kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel.OpenProcess.restype = wintypes.HANDLE
kernel.CloseHandle.argtypes = [wintypes.HANDLE]
kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]


@contextlib.contextmanager
def process_handle(pid, terminate=False):
    handle = kernel.OpenProcess(0x1000 | 0x100000 | (1 if terminate else 0), False, pid)
    if not handle:
        raise RuntimeError(f'Cannot open PID {pid}; no process stopped.')
    try:
        yield handle
    finally:
        kernel.CloseHandle(handle)


def created_ticks(handle):
    values = [wintypes.FILETIME() for _ in range(4)]
    if not kernel.GetProcessTimes(handle, *(ctypes.byref(value) for value in values)):
        raise RuntimeError('Cannot inspect process creation time.')
    return (values[0].dwHighDateTime << 32) | values[0].dwLowDateTime


@contextlib.contextmanager
def lock():
    LOCAL.mkdir(exist_ok=True)
    with (LOCAL / 'mailbox-watch.lock').open('a+b') as stream:
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise RuntimeError('Another start/stop/once/foreground operation holds the lock.') from exc
        try:
            if not stream.read(1):
                stream.write(b'0')
                stream.flush()
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def identity():
    if os.environ.get('RALPH_PC', '').strip():
        raise RuntimeError('RALPH_PC override forbidden. Register actual hostname with pc1.')
    host = platform.node()
    slots = json.loads((ROOT / 'channel/pcs.json').read_text(encoding='utf-8'))['slots']
    matches = [(key, meta) for key, meta in slots.items() if host in meta.get('hostname', [])]
    result = subprocess.run(['gh', 'api', 'user', '--jq', '.login'], cwd=ROOT,
                            capture_output=True, text=True, encoding='utf-8', timeout=25,
                            creationflags=HIDDEN)
    login = result.stdout.strip() if result.returncode == 0 else ''
    print(f'IDENTITY hostname={host} github={login}', flush=True)
    if len(matches) != 1:
        print('PENDING registration: report hostname/login to pc1. Preflight only.', flush=True)
        subprocess.run([sys.executable, str(ROOT / 'scripts/preflight.py')], cwd=ROOT)
        return None
    slot, meta = matches[0]
    if not login or login.casefold() != meta.get('github', '').casefold() or meta.get('inbox') != f'to:{slot}':
        print('PENDING registered GitHub/inbox mismatch; mailbox not read.')
        return None
    return {'hostname': host, 'slot': slot, 'github': login}


def is_watch(process):
    import re
    return bool(re.search(r'(?i)(?:^|[\\/\s"])mail\.py"?\s+watch(?:\s|$)', process.get('CommandLine') or ''))


def verify(state, process, handle):
    expected = subprocess.list2cmdline([state['executable_path'], '-u', str(MAIL), 'watch', '--interval', str(state['interval_seconds'])])
    return (state.get('engine') == 'python' and state['repo_root'] == str(ROOT)
            and state['process_id'] == process['ProcessId']
            and state['command_line'] == process['CommandLine'] == expected
            and state['executable_path'].casefold() == (process['ExecutablePath'] or '').casefold()
            and state['created_ticks'] == created_ticks(handle))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'check', 'status', 'stop', 'once', 'foreground'])
    parser.add_argument('--interval', type=int, default=30)
    args = parser.parse_args()
    if args.interval < 1:
        parser.error('--interval must be positive')
    who = None if args.action == 'stop' else identity()
    if args.action != 'stop' and who is None:
        return 2
    with lock():
        state = json.loads(STATE.read_text(encoding='utf-8-sig')) if STATE.exists() else None
        processes = query_processes()
        process = next((p for p in processes if state and p['ProcessId'] == state['process_id']), None)
        if args.action in ('check', 'status'):
            verified = False
            if process:
                with process_handle(process['ProcessId']) as handle:
                    verified = verify(state, process, handle)
            print(f"READY slot={who['slot']} watchers={sum(is_watch(p) for p in processes)} verified_process={verified} process_id={state['process_id'] if state else None}")
            return 0 if not process or verified else 1
        if process:
            with process_handle(process['ProcessId'], args.action == 'stop') as handle:
                if not verify(state, process, handle):
                    raise RuntimeError('PID/creation time/command/executable/repository mismatch. No process stopped.')
                if args.action == 'stop':
                    if not kernel.TerminateProcess(handle, 0) or kernel.WaitForSingleObject(handle, 5000) != 0:
                        raise RuntimeError('Stop failed/timed out; state retained.')
                    STATE.unlink()
                    print(f"STOPPED process_id={process['ProcessId']}; logs retained")
                    return 0
                if args.action == 'start':
                    print(f"ALREADY_RUNNING process_id={process['ProcessId']}")
                    return 0
                raise RuntimeError('Stop background watcher before once/foreground.')
        if args.action == 'stop':
            if state:
                # A non-Python process could have reused the saved PID. Never kill it.
                STATE.unlink()
            print('NOT_RUNNING: no matching Python PID; no process stopped')
            return 0
        watchers = [p for p in processes if is_watch(p)]
        if watchers:
            raise RuntimeError(f"Unmanaged watchers exist: {[p['ProcessId'] for p in watchers]}; stop in original terminal.")
        command = [sys.executable, '-u', str(MAIL), 'watch', '--interval', str(args.interval)]
        if args.action in ('once', 'foreground'):
            return subprocess.call(command + (['--once'] if args.action == 'once' else ['--bell']), cwd=ROOT)
        stdout = LOCAL / 'mailbox-watch.stdout.log'
        stderr = LOCAL / 'mailbox-watch.stderr.log'
        with stdout.open('wb') as out, stderr.open('wb') as err:
            child = subprocess.Popen(command, cwd=ROOT, stdout=out, stderr=err, creationflags=HIDDEN)
        time.sleep(0.7)
        if child.poll() is not None:
            raise RuntimeError(f'Watcher exited; inspect {stderr}')
        with process_handle(child.pid) as handle:
            ticks = created_ticks(handle)
        state = dict(engine='python', process_id=child.pid, created_ticks=ticks,
                     executable_path=sys.executable, command_line=subprocess.list2cmdline(command),
                     repo_root=str(ROOT), interval_seconds=args.interval, stdout_log=str(stdout),
                     stderr_log=str(stderr), launched_at_utc=datetime.now(timezone.utc).isoformat(), **who)
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"STARTED process_id={child.pid} slot={who['slot']} interval_seconds={args.interval}")
        print(f'STATE {STATE}\nSTDOUT {stdout}\nSTDERR {stderr}')
        print('Verify snapshot freshness/logs separately for successful GitHub polling.')
        return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
