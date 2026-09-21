#!/usr/bin/env python3
"""신원 카드 — 작업을 시키기 전에, 그리고 첫 회신에 반드시 붙인다.

세션 이름도 cwd 도 IP 도 신원을 확실히 말해 주지 않는다. 그래서 같은 형식으로 답해야
상대가 판정할 수 있다. 모든 값은 «잰 순간의 관측»이다.

    python channel/whoami.py             # 카드 전문
    python channel/whoami.py --oneline   # 한 줄 (프로브 회신용)
    python channel/whoami.py --hostname  # hostname 만 (pcs.json 채울 때)
"""
from __future__ import annotations

import argparse
import json
import platform
import socket
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent


def _utf8_stdout() -> None:
    """한국어 Windows 콘솔은 기본이 cp949 라 «—»·«🚨» 에서 죽는다.

    죽는 곳이 하필 「미등록」 경고문이라, 이걸 안 고치면 가장 중요한 메시지가 안 보인다.
    """
    for stream in (sys.stdout, sys.stderr):
        enc = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
        if enc != "utf8":
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_utf8_stdout()


def run(cmd: list[str], cwd: Path | None = None) -> str:
    try:
        out = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=20,
            encoding="utf-8", errors="replace",
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def hostname() -> str:
    """🚨 bash `hostname` 은 한글 호스트명을 깨뜨린다. platform.node() 는 제대로 읽는다."""
    return platform.node() or socket.gethostname()


def local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "미상"
    finally:
        s.close()


def load_cfg() -> dict:
    return json.loads((ROOT / "channel" / "pcs.json").read_text(encoding="utf-8"))


def my_slot(cfg: dict) -> tuple[str | None, dict | None, str]:
    """hostname 으로 슬롯을 찾는다.

    🚨 못 찾으면 «미등록» 을 반환한다. 기본 슬롯으로 떨어뜨리지 않는다 —
    그렇게 하면 남의 편지함을 자기 것으로 읽는다. 이 구멍은 실제로 사고를 냈다.
    """
    import os

    forced = os.environ.get("RALPH_PC", "").strip()
    if forced:
        s = cfg["slots"].get(forced)
        if s:
            return forced, s, "RALPH_PC 환경변수"
        return None, None, f"RALPH_PC={forced} 인데 pcs.json 에 없다"

    host = hostname()
    for slot, meta in cfg["slots"].items():
        if host in meta.get("hostname", []):
            return slot, meta, "hostname 표"
    return None, None, "미등록"


def gh_login() -> str:
    out = run(["gh", "api", "user", "--jq", ".login"])
    return out or "gh 미인증"


def git_head(path: Path) -> str:
    if not (path / ".git").exists():
        return "git 아님"
    head = run(["git", "log", "--oneline", "-1"], cwd=path)
    br = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=path)
    dirty = run(["git", "status", "--porcelain"], cwd=path)
    n = len([x for x in dirty.splitlines() if x.strip()])
    return f"{br} @ {head[:48]} · {'clean' if n == 0 else f'미커밋 {n}건'}"


def card(doing: str = "") -> str:
    cfg = load_cfg()
    slot, meta, how = my_slot(cfg)
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

    role = meta.get("role", "미정") if meta else "—"
    inbox = meta.get("inbox") if meta else None

    lines = [
        "## 신원 카드",
        "",
        f"- **슬롯**: {slot or '🚨 미등록'} ({how})",
        f"- **역할**: {role}",
        f"- **편지함**: {inbox or '🚨 없음 — 수신하지 않는다'}",
        f"- **hostname**: `{hostname()}`",
        f"- **IP**: {local_ip()}  (DHCP 라 바뀐다. 판정은 hostname 이 기준)",
        f"- **GitHub**: {gh_login()}",
        f"- **OS**: {platform.system()} {platform.release()}",
        f"- **cwd**: `{Path.cwd()}`",
        f"- **이 레포**: {git_head(ROOT)}",
        f"- **지금 하는 일**: {doing or '(안 적음 — 선점 판정에 쓰이니 적는 편이 좋다)'}",
        f"- **잰 시각**: {now}",
    ]
    if slot is None:
        lines += [
            "",
            "> 🚨 **이 PC 는 pcs.json 에 없습니다.** 편지를 받지 않습니다.",
            "> `channel/pcs.json` 의 해당 슬롯 `hostname` 에 위 값을 넣으십시오.",
            "> 등록 전에는 수신을 시도하지 마십시오 — 남의 편지를 처리하는 사고가 됩니다.",
        ]
    return "\n".join(lines)


def oneline() -> str:
    cfg = load_cfg()
    slot, meta, _ = my_slot(cfg)
    role = meta.get("role", "미정") if meta else "—"
    now = datetime.now(KST).strftime("%m-%d %H:%M:%S")
    return (
        f"{slot or '미등록'}/{role} · host={hostname()} · ip={local_ip()} "
        f"· gh={gh_login()} · cwd={Path.cwd().name} · {now} KST"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="신원 카드")
    ap.add_argument("--oneline", action="store_true", help="한 줄로")
    ap.add_argument("--hostname", action="store_true", help="hostname 만")
    ap.add_argument("--doing", default="", help="지금 하는 일 한 줄")
    a = ap.parse_args()

    if a.hostname:
        print(hostname())
    elif a.oneline:
        print(oneline())
    else:
        print(card(a.doing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
