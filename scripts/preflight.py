"""Read-only laptop readiness report. Does not log in or post messages."""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def probe(command, cwd=ROOT):
    executable = shutil.which(command[0])
    if not executable:
        return False, "not_installed"
    try:
        result = subprocess.run([executable, *command[1:]], cwd=cwd, capture_output=True,
                                encoding="utf-8", errors="replace", timeout=25)
        # Failed authentication output may contain URLs/codes: do not copy it.
        return (True, result.stdout.strip()[:240]) if result.returncode == 0 else (False, "command_failed")
    except (OSError, subprocess.TimeoutExpired):
        return False, "timeout_or_unavailable"


def collect(kit):
    slots = json.loads((ROOT / "channel/pcs.json").read_text(encoding="utf-8"))["slots"]
    slot = next((key for key, value in slots.items() if platform.node() in value["hostname"]), None)
    checks = {}
    for name, command in {"git": ["git", "--version"], "python": ["python", "--version"],
                          "node": ["node", "--version"], "gh": ["gh", "--version"]}.items():
        ok, detail = probe(command)
        checks[name] = {"ok": ok, "detail": detail.splitlines()[0] if detail else ""}
    authenticated, login = probe(["gh", "api", "user", "--jq", ".login"])
    checks["github_login"] = {"ok": authenticated, "detail": login}
    for repo in ("happycall-ralphthon", "hackathon-ai-kit"):
        ok, detail = probe(["gh", "repo", "view", f"cjj0202-glitch/{repo}", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
        checks[repo] = {"ok": ok, "detail": detail}
    checks["slot_registered"] = {"ok": slot is not None, "detail": slot or "메인에게 hostname 등록 요청"}
    checks["account_matches"] = {"ok": bool(slot and authenticated and slots[slot].get("github") == login), "detail": "등록 계정과 현재 계정 대조"}
    checks["kit_local"] = {"ok": (kit / "scripts/gen_fake_data.py").is_file(), "detail": "sibling kit checkout"}
    optional = {}
    for package in ("PIL", "numpy", "cv2", "win32com", "openai"):
        optional[package] = importlib.util.find_spec(package) is not None
    optional["vercel_installed"] = shutil.which("vercel") is not None
    optional["codex_cli_installed"] = shutil.which("codex") is not None
    optional["claude_cli_installed"] = shutil.which("claude") is not None
    _, head = probe(["git", "rev-parse", "HEAD"])
    _, kit_head = probe(["git", "rev-parse", "HEAD"], kit) if kit.exists() else (False, "missing")
    return {"measured_at": datetime.now(timezone.utc).isoformat(), "hostname": platform.node(),
            "slot": slot, "head": head, "kit_head": kit_head, "checks": checks, "optional": optional,
            "ready_for_assignment": all(item["ok"] for item in checks.values()),
            "scope": "도구·저장소·신원 점검. 제품 실행·모델 API·Vercel 인증 검증은 별도"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", type=Path, default=ROOT.parent / "hackathon-ai-kit")
    args = parser.parse_args()
    report = collect(args.kit)
    output = ROOT / ".local/preflight.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, check in report["checks"].items():
        print(f"{'PASS' if check['ok'] else 'PENDING'} {name}: {check['detail']}")
    print(f"보고서: {output}")
    return 0 if report["ready_for_assignment"] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
