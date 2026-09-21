#!/usr/bin/env python3
"""편지함 부트스트랩 — 라벨과 고정 상태 이슈를 만든다. 메인 PC 에서 1회.

    python channel/setup.py            # 무엇을 만들지 보여만 준다
    python channel/setup.py --apply    # 실제로 만든다

두 번 돌려도 안전하다(이미 있으면 건너뛴다).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import whoami as ident  # noqa: E402

ident._utf8_stdout()  # 한국어 Windows 콘솔(cp949) 대비

ROOT = Path(__file__).resolve().parent.parent
STATUS_MARK = "[STATUS]"

SLOT_COLOR = "1d76db"
TYPE_COLOR = {
    "A-즉시조치": "d93f0b",
    "C-결정요청": "fbca04",
    "D-규칙전달": "0e8a16",
    "E-경고정정": "b60205",
    "F-자료전달": "5319e7",
}


def sh(cmd: list[str], check: bool = True) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        sys.stderr.write((p.stderr or p.stdout).strip() + "\n")
    return p.returncode, (p.stdout or "").strip()


def ensure_label(name: str, color: str, desc: str, apply: bool) -> None:
    rc, _ = sh(["gh", "label", "list", "--search", name, "--json", "name"], check=False)
    rc2, out = sh(["gh", "label", "list", "--limit", "200", "--json", "name"], check=False)
    existing = {x["name"] for x in json.loads(out or "[]")} if rc2 == 0 else set()
    if name in existing:
        print(f"  = 라벨 있음   {name}")
        return
    if not apply:
        print(f"  + 라벨 만들 것 {name}  ({desc})")
        return
    rc, _ = sh(["gh", "label", "create", name, "--color", color, "--description", desc])
    print(f"  {'OK' if rc == 0 else 'X '} 라벨 생성   {name}")


def ensure_status_issue(slot: str, role: str, apply: bool) -> None:
    rc, out = sh(["gh", "issue", "list", "--label", "status", "--state", "open",
                  "--limit", "50", "--json", "number,title"], check=False)
    items = json.loads(out or "[]") if rc == 0 else []
    title = f"{STATUS_MARK} {slot} — {role}"
    for it in items:
        if it["title"].startswith(f"{STATUS_MARK} {slot}"):
            print(f"  = 상태이슈 있음 #{it['number']} {it['title']}")
            return
    if not apply:
        print(f"  + 상태이슈 만들 것 {title}")
        return
    body = (f"# {slot} / {role}\n\n"
            "> 🚨 자동 생성 — 이 body 는 `mail.py status --set` 이 «덮어씁니다».\n"
            "> 여기에 대화를 쌓지 마십시오. 지시는 편지(이슈)로 따로 만듭니다.\n\n"
            "- **갱신**: (아직 없음)\n- **지금 하는 일**: (아직 없음)\n")
    rc, url = sh(["gh", "issue", "create", "--title", title,
                  "--label", "status", "--body", body])
    print(f"  {'OK' if rc == 0 else 'X '} 상태이슈 생성 {url}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제로 만든다")
    a = ap.parse_args()

    cfg = json.loads((ROOT / "channel" / "pcs.json").read_text(encoding="utf-8"))

    if not a.apply:
        print("※ 계획만 보여줍니다. 실제로 만들려면 --apply\n")

    print("[라벨 — 수신처]")
    for slot, meta in cfg["slots"].items():
        ensure_label(f"to:{slot}", SLOT_COLOR,
                     f"수신처 {slot} ({meta.get('role','미정')})", a.apply)
    print("\n[라벨 — 발신처]")
    for slot in cfg["slots"]:
        ensure_label(f"from:{slot}", "c5def5", f"발신처 {slot}", a.apply)

    print("\n[라벨 — 유형]")
    for k, v in cfg["types"].items():
        ensure_label(v["label"], TYPE_COLOR.get(v["label"], "ededed"), v["설명"][:90], a.apply)

    print("\n[라벨 — 기타]")
    ensure_label("urgent", "b60205", "상대가 지금 멈춰야 하는 것", a.apply)
    ensure_label("status", "0052cc", "PC 별 고정 상태 이슈 (닫지 말 것)", a.apply)

    print("\n[고정 상태 이슈]")
    for slot, meta in cfg["slots"].items():
        ensure_status_issue(slot, meta.get("role", "미정"), a.apply)

    print("\n확인:  python channel/mail.py board")
    return 0


if __name__ == "__main__":
    sys.exit(main())
