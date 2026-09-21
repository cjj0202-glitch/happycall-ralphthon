"""Store and verify the demo-only OpenAI credential without printing it."""
from __future__ import annotations

import argparse
import getpass
import json
import os
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env.demo.local"
REQUIRED_POLICY = {
    "ONEFLOW_RUNTIME_MODE": "demo-live",
    "OPENAI_DEMO_BUDGET_USD": "30",
    "OPENAI_DEMO_WARN_USD": "25",
    "OPENAI_DEMO_PURPOSE": "demo-only",
}


def read_env() -> dict[str, str]:
    if not ENV_FILE.is_file():
        return {}
    result: dict[str, str] = {}
    for line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def assert_key(key: str) -> None:
    if not key.startswith("sk-") or len(key) < 40 or any(ch.isspace() for ch in key):
        raise ValueError("OpenAI API 키 형식이 올바르지 않습니다")


def write_secret(key: str) -> None:
    assert_key(key)
    lines = ["# Local demo credential. Git ignored. Do not share."]
    lines += [f"{name}={value}" for name, value in REQUIRED_POLICY.items()]
    lines.append(f"OPENAI_API_KEY={key}")
    fd, temp_name = tempfile.mkstemp(prefix=".env.demo.", suffix=".tmp", dir=ROOT)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")
        os.chmod(temp_name, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temp_name, ENV_FILE)
        if os.name == "nt":
            account = subprocess.check_output(["whoami"], text=True).strip()
            result = subprocess.run(
                ["icacls", str(ENV_FILE), "/inheritance:r", "/grant:r", f"{account}:(R,W)"],
                capture_output=True,
                text=True,
            )
            if result.returncode:
                raise RuntimeError("Windows 로컬 파일 권한 제한에 실패했습니다")
    finally:
        Path(temp_name).unlink(missing_ok=True)


def status() -> int:
    values = read_env()
    key = values.get("OPENAI_API_KEY", "")
    policy_ok = all(values.get(name) == value for name, value in REQUIRED_POLICY.items())
    try:
        assert_key(key)
        key_ok = True
    except ValueError:
        key_ok = False
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", ".env.demo.local"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0
    print(json.dumps({
        "file": str(ENV_FILE),
        "exists": ENV_FILE.is_file(),
        "key_present": key_ok,
        "demo_policy": policy_ok,
        "git_tracked": tracked,
        "budget_usd": values.get("OPENAI_DEMO_BUDGET_USD"),
        "warn_usd": values.get("OPENAI_DEMO_WARN_USD"),
    }, ensure_ascii=False))
    return 0 if key_ok and policy_ok and not tracked else 1


def verify() -> int:
    values = read_env()
    if values.get("ONEFLOW_RUNTIME_MODE") != "demo-live":
        raise ValueError("데모 전용 모드가 아니므로 API 확인을 중단합니다")
    key = values.get("OPENAI_API_KEY", "")
    assert_key(key)
    request = urllib.request.Request(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {key}", "User-Agent": "oneflow-demo-key-check/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read())
            count = len(payload.get("data", []))
            print(json.dumps({"authenticated": True, "http_status": response.status, "models_visible": count, "inference_requested": False}, ensure_ascii=False))
            return 0
    except urllib.error.HTTPError as exc:
        print(json.dumps({"authenticated": False, "http_status": exc.code, "inference_requested": False}, ensure_ascii=False))
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["store", "status", "verify"])
    args = parser.parse_args()
    if args.command == "store":
        key = getpass.getpass("OpenAI demo API key (입력은 표시되지 않음): ")
        write_secret(key)
        print(f"저장 완료: {ENV_FILE} (키 값은 출력하지 않음)")
        return status()
    if args.command == "status":
        return status()
    return verify()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
