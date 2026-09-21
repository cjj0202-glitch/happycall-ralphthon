"""Windows-only local demo launcher; no shell policy changes or secret reads."""
from __future__ import annotations

import contextlib
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local" / "demo-launcher"
STATE = LOCAL / "processes.json"
FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@contextlib.contextmanager
def locked():
    if os.name != "nt":
        raise RuntimeError("This launcher requires Windows.")
    import msvcrt
    LOCAL.mkdir(parents=True, exist_ok=True)
    with (LOCAL / "launcher.lock").open("a+b") as stream:
        stream.seek(0)
        if not stream.read(1):
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise RuntimeError("Another start/stop is running. Try again after it finishes.") from exc
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def processes():
    command = ("[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); "
               "@(Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,"
               "CommandLine,@{n='Created';e={$_.CreationDate.ToUniversalTime().ToString('o')}}) "
               "| ConvertTo-Json -Compress")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                            capture_output=True, encoding="utf-8", check=True, timeout=12,
                            creationflags=FLAGS)
    rows = json.loads(result.stdout or "[]")
    if isinstance(rows, dict):
        rows = [rows]
    return {int(row["ProcessId"]): row for row in rows}


def identity(row):
    return {key: row[key] for key in ("ProcessId", "ParentProcessId", "CommandLine", "Created")}


def matches(saved, current):
    return bool(current and saved.get("CommandLine") and
                all(saved.get(key) == current.get(key)
                    for key in ("ProcessId", "CommandLine", "Created")))


def load_state():
    if not STATE.exists():
        return {"root": str(ROOT), "processes": []}
    data = json.loads(STATE.read_text(encoding="utf-8"))
    if data.get("root") != str(ROOT) or not isinstance(data.get("processes"), list):
        raise RuntimeError("Unexpected PID state. Do not stop processes until the file is reviewed.")
    return data


def save_state(state):
    temp = STATE.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(STATE)


def refresh(state, rows):
    owned = {int(p["ProcessId"]) for p in state["processes"]
             if matches(p, rows.get(int(p["ProcessId"])))}
    while True:
        added = {pid for pid, row in rows.items()
                 if int(row["ParentProcessId"]) in owned and pid not in owned and row["CommandLine"]}
        if not added:
            break
        owned.update(added)
    previous = {int(p["ProcessId"]): p for p in state["processes"]}
    previous.update({pid: identity(rows[pid]) for pid in owned})
    state["processes"] = list(previous.values())
    return owned


def port_open(port):
    with socket.socket() as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def healthy():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8100/api/health", timeout=1) as response:
            body = json.load(response)
        return isinstance(body, dict) and body.get("status") == "ok" and body.get("synthetic") is True and body.get("runtime") == "synthetic-demo"
    except (OSError, ValueError):
        return False


def web_ready():
    try:
        with urllib.request.urlopen("http://127.0.0.1:3100", timeout=1) as response:
            return response.status == 200 and "text/html" in response.headers.get("Content-Type", "")
    except OSError:
        return False


def stop_owned(state):
    """Open a stable Windows handle, then recheck identity before terminating it."""
    rows = processes()
    owned = refresh(state, rows)
    save_state(state)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.TerminateProcess.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handles = []
    try:
        for saved in state["processes"]:
            pid = int(saved["ProcessId"])
            if pid in owned:
                handle = kernel.OpenProcess(0x0001 | 0x1000, False, pid)
                if handle:
                    handles.append((saved, handle))
        # Handles prevent killing a replacement process if a PID is recycled.
        current = processes()
        for saved, handle in reversed(handles):
            if matches(saved, current.get(int(saved["ProcessId"]))):
                if not kernel.TerminateProcess(handle, 0):
                    raise RuntimeError(f"Could not stop managed PID {saved['ProcessId']}.")
    finally:
        for _, handle in handles:
            kernel.CloseHandle(handle)
    time.sleep(0.3)
    current = processes()
    remaining = [p for p in state["processes"] if matches(p, current.get(int(p["ProcessId"])))]
    if remaining:
        state["processes"] = remaining
        save_state(state)
        raise RuntimeError("Some managed processes remain; retry stop. External processes were not stopped.")
    STATE.unlink(missing_ok=True)
    print("Managed demo processes stopped; external processes were not stopped.")


def start():
    with locked():
        state = load_state()
        owned = refresh(state, processes())
        if owned:
            save_state(state)
            if healthy() and web_ready():
                print("Demo already running: http://127.0.0.1:3100 (no duplicate start)")
                return
            raise RuntimeError("Managed demo exists but is not ready. Inspect logs, then run python scripts/stop_demo.py.")
        if any(port_open(port) for port in (8100, 3100)):
            raise RuntimeError("Port 8100 or 3100 is occupied by an unmanaged service. Nothing started or stopped.")
        python = ROOT / ".venv" / "Scripts" / "python.exe"
        if not python.is_file():
            raise RuntimeError("Python dependencies missing. From the repository run: uv sync")
        check = subprocess.run([str(python), "-c", "import connexion, uvicorn"],
                               capture_output=True, creationflags=FLAGS, timeout=15)
        if check.returncode:
            raise RuntimeError("Python dependencies incomplete. From the repository run: uv sync")
        node = shutil.which("node.exe")
        npm = shutil.which("npm.cmd")
        npm_cli = Path(npm).parent / "node_modules/npm/bin/npm-cli.js" if npm else Path("__missing__")
        if not node or not npm_cli.is_file():
            raise RuntimeError("Node.js/npm installation not found. Install Node.js with npm and reopen the terminal.")
        if not (ROOT / "apps/web/node_modules/next/package.json").is_file():
            raise RuntimeError("Web dependencies missing. Run: cd apps/web; npm.cmd ci")
        state = {"root": str(ROOT), "processes": []}
        children = []
        try:
            commands = [
                ("backend", [str(python), str(ROOT / "scripts/run_demo_server.py")], ROOT),
                ("web", [node, str(npm_cli), "run", "dev"], ROOT / "apps/web"),
            ]
            for name, command, cwd in commands:
                with (LOCAL / f"{name}.log").open("ab", buffering=0) as log:
                    child = subprocess.Popen(command, cwd=cwd, stdin=subprocess.DEVNULL,
                                             stdout=log, stderr=subprocess.STDOUT, creationflags=FLAGS)
                children.append(child)
                row = processes().get(child.pid)
                if not row or row.get("CommandLine") != subprocess.list2cmdline(command):
                    raise RuntimeError(f"Cannot verify launched {name} process identity. Check its log.")
                state["processes"].append(identity(row))
                refresh(state, processes())
                save_state(state)
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if any(child.poll() is not None for child in children):
                    raise RuntimeError("A demo process exited during startup. Check .local/demo-launcher/*.log")
                if healthy() and web_ready():
                    refresh(state, processes())
                    save_state(state)
                    print("Demo ready: http://127.0.0.1:3100")
                    print("Health JSON verified: status=ok, synthetic=true, runtime=synthetic-demo")
                    print("Stop: python scripts/stop_demo.py")
                    return
                time.sleep(0.5)
            raise RuntimeError("Demo readiness timed out (60 seconds). Check .local/demo-launcher/*.log")
        except BaseException:
            if state["processes"]:
                stop_owned(state)
            # Popen handles refer only to processes created by this invocation.
            for child in children:
                if child.poll() is None:
                    child.terminate()
            raise


if __name__ == "__main__":
    try:
        start()
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
