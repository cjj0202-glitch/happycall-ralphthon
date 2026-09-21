#!/usr/bin/env python3
"""GitHub Issues 를 편지함으로 쓰는 세션 간 채널.

    받은편지함 = to:<내슬롯> 라벨이 붙은 open 이슈
    보내기     = 이슈 생성      회신 = 코멘트      처리완료 = close

왜 파일이 아니라 이슈인가 — 4대가 동시에 쓴다. 파일이면 충돌이 나고, 랄프 루프는
충돌을 풀 줄 모른다. 이슈는 원리적으로 충돌이 없고 clone 도 필요 없다.

사용
    python channel/mail.py whoami
    python channel/mail.py inbox                     # 내 앞 열린 편지
    python channel/mail.py read 12
    python channel/mail.py send --to pc2 --type A --title "..." --body-file b.md
    python channel/mail.py reply 12 --body "..."
    python channel/mail.py done 12 --evidence "PID 5092 · 기동 10:25:53 · 27건"
    python channel/mail.py status --set "지금 무엇을 하는 중"
    python channel/mail.py board                     # 4대 상태 한눈에
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import whoami as ident  # noqa: E402

ident._utf8_stdout()  # 한국어 Windows 콘솔(cp949) 대비 — whoami 와 같은 처리

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
STATUS_MARK = "[STATUS]"

# 본문에 있으면 발송을 막는다. 값이 아니라 «경로»만 보낸다 (금기 6).
SECRET_PATTERNS = [
    (r"(?i)\b(sk-[A-Za-z0-9_\-]{20,})", "OpenAI 계열 키"),
    (r"(?i)\b(gh[pousr]_[A-Za-z0-9]{30,})", "GitHub 토큰"),
    (r"(?i)\b(AKIA[0-9A-Z]{16})\b", "AWS 액세스 키"),
    (r"(?i)\bxox[baprs]-[A-Za-z0-9-]{10,}", "Slack 토큰"),
    (r"(?i)(api[_-]?key|secret|passwd|password|token)\s*[:=]\s*['\"]?[A-Za-z0-9/+_\-]{16,}",
     "키=값 형태"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "개인키 블록"),
]


def sh(cmd: list[str], check: bool = True, stdin: str | None = None) -> str:
    p = subprocess.run(
        cmd, capture_output=True, text=True, input=stdin,
        encoding="utf-8", errors="replace",
    )
    if check and p.returncode != 0:
        sys.stderr.write((p.stderr or p.stdout or "").strip() + "\n")
        raise SystemExit(f"실패: {' '.join(cmd[:3])}... (exit {p.returncode})")
    return p.stdout.strip()


def cfg() -> dict:
    return json.loads((ROOT / "channel" / "pcs.json").read_text(encoding="utf-8"))


def me() -> tuple[str, dict]:
    c = cfg()
    slot, meta, how = ident.my_slot(c)
    if slot is None:
        raise SystemExit(
            f"🚨 이 PC 는 pcs.json 에 없습니다 ({how}).\n"
            f"   hostname = {ident.hostname()}\n"
            f"   channel/pcs.json 의 슬롯에 넣거나 RALPH_PC=pc2 로 지정하십시오.\n"
            f"   등록 전에는 수신하지 마십시오 — 남의 편지를 처리하는 사고가 됩니다."
        )
    return slot, meta


def now() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")


def kst(iso: str) -> str:
    """GitHub 은 UTC 로 준다. 그대로 보여 주면 시간 축이 갈린다.

    원본 채널에서 가장 무거운 오판이 이것이었다 — 「2시간 뒤에도 그대로라 동기화 지연으로
    보기 어렵다」는 회신이 왔는데, 그 2시간은 «자기» 기준이었고 상대 push 로부터는 11분이었다.
    관측에는 언제·어느 기준으로 잰 것인가가 붙어야 한다.
    """
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone(KST).strftime("%m-%d %H:%M KST")
    except Exception:
        return iso[:16].replace("T", " ") + " UTC?"


def scan_secrets(text: str) -> list[str]:
    hits = []
    for pat, why in SECRET_PATTERNS:
        for m in re.finditer(pat, text):
            frag = m.group(0)
            hits.append(f"{why}: {frag[:12]}…({len(frag)}자)")
    return hits


# ─────────────────────────────── 명령들 ───────────────────────────────

def cmd_whoami(a) -> int:
    print(ident.card(a.doing))
    return 0


def cmd_inbox(a) -> int:
    slot, meta = me()
    label = meta["inbox"]
    raw = sh([
        "gh", "issue", "list", "--label", label, "--state", "open",
        "--limit", "50", "--json", "number,title,labels,author,createdAt,comments",
    ])
    items = json.loads(raw or "[]")
    if not items:
        print(f"받은편지함({slot}) — 열린 편지 없음")
        return 0

    print(f"받은편지함({slot}) — {len(items)}건\n")
    for it in items:
        labs = [x["name"] for x in it["labels"]]
        urgent = "🚨 " if "urgent" in labs else ""
        typ = next((x for x in labs if re.match(r"^[A-F]-", x)), "?")
        nrep = len(it.get("comments", []) or [])
        print(f"  #{it['number']:<4} {urgent}[{typ}] {it['title']}")
        print(f"        from {it['author']['login']} · {kst(it['createdAt'])} · 회신 {nrep}건")
    print(f"\n  본문: python channel/mail.py read <번호>")
    return 0


def cmd_read(a) -> int:
    raw = sh([
        "gh", "issue", "view", str(a.number),
        "--json", "number,title,body,labels,author,createdAt,state,comments",
    ])
    it = json.loads(raw)
    labs = ", ".join(x["name"] for x in it["labels"])
    print(f"#{it['number']} [{it['state']}] {it['title']}")
    print(f"라벨: {labs}")
    print(f"보낸이: {it['author']['login']} · {kst(it['createdAt'])}")
    print("─" * 70)
    print(it["body"] or "(본문 없음)")
    for c in it.get("comments", []) or []:
        print("─" * 70)
        print(f"↩ {c['author']['login']} · {kst(c['createdAt'])}")
        print(c["body"])
    return 0


def cmd_send(a) -> int:
    slot, meta = me()
    c = cfg()

    if a.to not in c["slots"]:
        raise SystemExit(f"수신처 '{a.to}' 가 pcs.json 에 없습니다. {list(c['slots'])}")
    if a.type not in c["types"]:
        raise SystemExit(
            f"유형 '{a.type}' 이 없습니다.\n"
            + "\n".join(f"  {k} = {v['label']} — {v['설명']}" for k, v in c["types"].items())
            + "\n🚨 상태보고(B)·감시신호(G)·교차검증(H) 은 편지로 만들지 않습니다."
              "\n   상태는 `mail.py status --set`, 나머지는 코멘트로 끝내십시오."
        )

    body = Path(a.body_file).read_text(encoding="utf-8") if a.body_file else (a.body or "")
    if not body.strip():
        raise SystemExit("본문이 비었습니다. --body 또는 --body-file 을 주십시오.")

    hits = scan_secrets(body + "\n" + a.title)
    if hits:
        print("🚨 시크릿으로 보이는 값이 본문에 있습니다 — 발송을 멈춥니다.")
        for h in hits:
            print(f"   - {h}")
        print("\n값이 아니라 «경로»만 보내십시오. 실제 값은 각 PC 의 .env 에 둡니다.")
        return 2

    to_meta = c["slots"][a.to]
    header = "\n".join([
        f"- **보낸 PC**: {slot} / {meta.get('role','미정')}  (`{ident.hostname()}`)",
        f"- **받는 PC**: {a.to} / {to_meta.get('role','미정')}",
        f"- **유형**: {c['types'][a.type]['label']}",
        f"- **보낸 시각**: {now()}",
        "",
        "> 🚨 회신할 때는 「그쪽」이 아니라 **위 «보낸 PC» 이름으로** 인용하십시오.",
        "> 한 PC 에 세션이 여럿입니다. 합쳐 읽으면 자기가 한 적 없는 판단을 되돌려받습니다.",
        "",
        "---",
        "",
    ])

    labels = [f"to:{a.to}", c["types"][a.type]["label"], f"from:{slot}"]
    if a.urgent:
        labels.append("urgent")

    cmd = [
        "gh", "issue", "create",
        "--title", a.title,
        "--body-file", "-",
        "--label", ",".join(labels),
    ]
    if to_meta.get("github"):
        cmd += ["--assignee", to_meta["github"]]

    url = sh(cmd, stdin=header + body)
    print(f"보냈습니다 → {url}")
    print("🚨 «보냄» 은 «읽음» 도 «처리» 도 아닙니다. 회신으로만 압니다.")
    return 0


def cmd_reply(a) -> int:
    slot, meta = me()
    body = Path(a.body_file).read_text(encoding="utf-8") if a.body_file else (a.body or "")
    if not body.strip():
        raise SystemExit("회신 본문이 비었습니다.")
    hits = scan_secrets(body)
    if hits:
        print("🚨 시크릿으로 보이는 값이 있습니다 — 회신을 멈춥니다.")
        for h in hits:
            print(f"   - {h}")
        return 2
    sig = f"\n\n— {slot}/{meta.get('role','미정')} · {now()}"
    sh(["gh", "issue", "comment", str(a.number), "--body-file", "-"], stdin=body + sig)
    print(f"회신했습니다 → #{a.number}")
    return 0


def cmd_done(a) -> int:
    """규약 ⑦ — 회신 없이 닫지 않는다.

    이 게이트는 실제로 일했다. 원본 채널에서 `--force-no-reply` 사유가 68건 남았고
    그중 「회신: 필요」였던 것은 0건이었다. 막는 게 아니라 «적게» 만드는 장치다.
    """
    slot, meta = me()
    if not a.evidence and not a.force_no_reply:
        print("🚨 회신 없이 닫을 수 없습니다 (규약 ⑦).")
        print("   --evidence \"무엇을 어떻게 확인했는가 — 수치·시각·PID\"")
        print("   정말 회신이 필요 없으면: --force-no-reply \"사유\"")
        print("\n   「에러 없음」은 검증이 아닙니다. 무엇을 보고 됐다고 판단했는지 적으십시오.")
        return 2

    if a.evidence:
        body = f"**처리 완료**\n\n{a.evidence}\n\n— {slot}/{meta.get('role','미정')} · {now()}"
    else:
        body = (f"**회신 없이 종결** — 사유: {a.force_no_reply}\n\n"
                f"— {slot}/{meta.get('role','미정')} · {now()}")
    sh(["gh", "issue", "comment", str(a.number), "--body-file", "-"], stdin=body)
    sh(["gh", "issue", "close", str(a.number)])
    print(f"처리완료 → #{a.number}")
    return 0


def _status_issue(slot: str) -> int | None:
    raw = sh([
        "gh", "issue", "list", "--label", "status", "--state", "open",
        "--limit", "20", "--json", "number,title",
    ])
    for it in json.loads(raw or "[]"):
        if it["title"].startswith(f"{STATUS_MARK} {slot}"):
            return it["number"]
    return None


def cmd_status(a) -> int:
    """상태보고는 편지가 아니다 — 고정 이슈 body 를 «덮어쓴다».

    원본 실측에서 상태보고가 전체의 51.5% 였다. 그것을 전부 편지로 만들면 편지함이
    상태로 덮여 진짜 지시가 묻힌다. 게다가 상태는 낡으면 거짓이 되므로 쌓으면 안 된다.
    """
    slot, meta = me()
    n = _status_issue(slot)
    if n is None:
        raise SystemExit(f"{slot} 의 상태 이슈가 없습니다. `python channel/setup.py` 를 먼저 돌리십시오.")

    if not a.set:
        raw = sh(["gh", "issue", "view", str(n), "--json", "body"])
        print(json.loads(raw)["body"])
        return 0

    body = "\n".join([
        f"# {slot} / {meta.get('role','미정')}",
        "",
        "> 🚨 자동 생성 — 이 body 는 매번 «덮어써집니다». 여기에 대화를 쌓지 마십시오.",
        "> 상태는 낡으면 거짓이 됩니다. 아래 «갱신» 시각보다 오래됐으면 믿지 마십시오.",
        "",
        f"- **갱신**: {now()}",
        f"- **hostname**: `{ident.hostname()}`",
        f"- **지금 하는 일**: {a.set}",
        "",
        "```",
        ident.oneline(),
        "```",
    ])
    sh(["gh", "issue", "edit", str(n), "--body-file", "-"], stdin=body)
    print(f"상태 갱신 → #{n}")
    return 0


def cmd_board(a) -> int:
    c = cfg()
    raw = sh([
        "gh", "issue", "list", "--label", "status", "--state", "open",
        "--limit", "20", "--json", "number,title,body,updatedAt",
    ])
    st = {}
    for it in json.loads(raw or "[]"):
        m = re.match(rf"{re.escape(STATUS_MARK)}\s+(\S+)", it["title"])
        if m:
            st[m.group(1)] = it

    raw2 = sh([
        "gh", "issue", "list", "--state", "open", "--limit", "100",
        "--json", "number,labels,title",
    ])
    open_issues = json.loads(raw2 or "[]")

    print(f"{'슬롯':<6} {'역할':<12} {'열린편지':>8}  상태")
    print("─" * 78)
    for slot, meta in c["slots"].items():
        cnt = sum(
            1 for it in open_issues
            if any(x["name"] == f"to:{slot}" for x in it["labels"])
        )
        it = st.get(slot)
        if it:
            m = re.search(r"\*\*지금 하는 일\*\*:\s*(.+)", it["body"] or "")
            doing = m.group(1).strip() if m else "(미기재)"
            m2 = re.search(r"\*\*갱신\*\*:\s*(.+)", it["body"] or "")
            when = m2.group(1).strip() if m2 else "?"
            state = f"{doing[:34]}  ({when})"
        else:
            state = "— 상태 이슈 없음"
        print(f"{slot:<6} {meta.get('role','미정'):<12} {cnt:>8}  {state}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="GitHub Issues 편지함")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("whoami", help="신원 카드")
    p.add_argument("--doing", default="")
    p.set_defaults(fn=cmd_whoami)

    p = sub.add_parser("inbox", help="내 앞 열린 편지")
    p.set_defaults(fn=cmd_inbox)

    p = sub.add_parser("read", help="편지 본문 + 회신")
    p.add_argument("number", type=int)
    p.set_defaults(fn=cmd_read)

    p = sub.add_parser("send", help="편지 보내기")
    p.add_argument("--to", required=True)
    p.add_argument("--type", required=True, help="A즉시조치 C결정요청 D규칙전달 E경고정정 F자료전달")
    p.add_argument("--title", required=True)
    p.add_argument("--body")
    p.add_argument("--body-file")
    p.add_argument("--urgent", action="store_true", help="상대가 지금 멈춰야 하는 것")
    p.set_defaults(fn=cmd_send)

    p = sub.add_parser("reply", help="회신")
    p.add_argument("number", type=int)
    p.add_argument("--body")
    p.add_argument("--body-file")
    p.set_defaults(fn=cmd_reply)

    p = sub.add_parser("done", help="처리완료 (회신 게이트)")
    p.add_argument("number", type=int)
    p.add_argument("--evidence", help="무엇을 어떻게 확인했는가 — 수치·시각·PID")
    p.add_argument("--force-no-reply", help="회신이 정말 필요 없는 사유")
    p.set_defaults(fn=cmd_done)

    p = sub.add_parser("status", help="내 상태 갱신/조회")
    p.add_argument("--set", help="지금 하는 일 한 줄")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("board", help="4대 상태 한눈에")
    p.set_defaults(fn=cmd_board)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
