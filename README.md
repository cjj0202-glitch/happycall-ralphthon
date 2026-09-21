# happycall-ralphthon

**먼저 읽기:** [작업표](TODO.md) · [공식 일정·채점·제출 대조](docs/09_공식규정_전수대조.md) · [목표](docs/03_목표와_범위.md) · [상세 설계](docs/04_제품_상세설계.md) · [4PC 운영](docs/05_랄프톤_실행계획.md) · [노트북 사전 준비](docs/08_다른_노트북_사전준비.md) · [Goal 초안](GOAL.md) · [점수 전략](docs/11_점수전략과_증거설계.md) · [행사 Vercel 연결](docs/12_Vercel_행사계정_연결.md)

**최종 제출은 9/22 12:00 KST.** 실제 `/goal` 원문과 Codex JSONL도 제출 대상입니다. 로그 원본은 GitHub에 올리지 않습니다. 제품 작업 완료 체크는 `ops/tasks.py`의 증거 검증을 거칩니다.

노트북 4대가 랄프톤 방식으로 **해피콜 시스템**을 만듭니다.
4대는 서로 직접 대화할 수 없으므로 **GitHub Issues 를 편지함으로** 씁니다.

```
받은편지함 = to:<내슬롯> 라벨이 붙은 open 이슈
보내기     = 이슈 생성      회신 = 코멘트      처리완료 = close
상태보고   = 편지가 아니다 — 고정 상태 이슈 body 를 덮어쓴다
```

---

## 도착해서 3분

```bash
gh auth status                      # 로그인 안 돼 있으면 gh auth login
git clone https://github.com/<계정>/happycall-ralphthon
cd happycall-ralphthon

python channel/whoami.py            # ① 신원 확인 — 「미등록」이면 여기서 멈춘다
```

「미등록」이 나오면 hostname과 본인 GitHub 계정을 메인에게 전달합니다. 메인이 [`channel/pcs.json`](channel/pcs.json)에 등록하고 공유하면 다시 확인합니다. **등록 전에 편지함을 읽지 마십시오** — 남의 편지를 처리하는 사고가 됩니다.

```bash
python channel/mail.py board        # ② 4대 상태 한눈에
python channel/mail.py inbox        # ③ 내 앞 편지
```

---

## 편지함 명령

| 명령 | 무엇 |
|---|---|
| `python channel/mail.py whoami` | 신원 카드 — 첫 회신에 붙인다 |
| `python channel/mail.py inbox` | 내 앞 열린 편지 |
| `python channel/mail.py read 12` | 본문 + 회신 전부 |
| `python channel/mail.py send --to pc3 --type A --title "..." --body-file b.md` | 편지 보내기 |
| `python channel/mail.py reply 12 --body "..."` | 회신 |
| `python channel/mail.py done 12 --evidence "..."` | 처리완료 (증거 없으면 안 닫힌다) |
| `python channel/mail.py status --set "지금 하는 일"` | 상태 갱신 (편지 아님) |
| `python channel/mail.py watch --interval 30 --bell` | **감시** — 새것이 있을 때만 울린다 |

의존성 없습니다 — 파이썬 표준 라이브러리와 `gh` 만 씁니다.

---

## 🚨 셋만 기억하면 됩니다

**1. 상태 보고는 편지가 아닙니다.**
원본 채널 1,433건 실측에서 상태 보고가 **51.5%** 였습니다. 그걸 다 편지로 만들면
편지함이 상태로 덮여 진짜 지시가 묻힙니다. `status --set` 를 쓰십시오.

**2. 감지는 감시기에 맡기고, 중계하지 마십시오.**
별도 터미널에서 `python channel/mail.py watch --interval 30 --bell` 을 띄워 둡니다.
**새것이 있을 때만** 울립니다. 원본에서 감시 세션을 켠 날 편지가 **4배**로 뛰었는데,
터진 것은 읽는 폴링이 아니라 그 세션이 **중계 허브**가 된 것이었습니다.

**3. 「에러 없음」은 검증이 아닙니다.**
무엇을 보고 됐다고 판단했는지 수치와 시각으로 적으십시오. 기대값이 없으면
받는 쪽은 **자기 자로 재서 통과시킵니다.**

---

## 문서

| 파일 | 무엇 |
|---|---|
| [docs/01_ChatGPT_전달_프롬프트.md](docs/01_ChatGPT_전달_프롬프트.md) | **복붙용.** 워커 루프 · 메인 루프 프롬프트 |
| [docs/공유문_팀원_카톡.md](docs/공유문_팀원_카톡.md) | **팀원에게 그대로 보내는 글** — 카톡·슬랙에 붙여넣는다 |
| [docs/08_다른_노트북_사전준비.md](docs/08_다른_노트북_사전준비.md) | 사전준비 상세 (정본) |
| [PROMPT_build.md](PROMPT_build.md) · [PROMPT_main.md](PROMPT_main.md) | 워커·메인 시작 프롬프트 (정본) |
| [AGENTS.md](AGENTS.md) | 에이전트 상시 지침 — Codex CLI 가 자동으로 읽는다 |
| `.claude/skills/mailbox/` | **스킬** — 「편지함」·「inbox」·「회신해」 등에 자동 발동 |
| `.claude/skills/ralph-loop/` | **스킬** — 「랄프」·「루프 돌려」·「다음 덩어리」에 자동 발동 |
| `.agents/skills/mailbox/`, `.agents/skills/ralph-loop/` | **Codex 스킬** — Claude와 같은 원본 규약 참조 |
| [channel/00_채널규약.md](channel/00_채널규약.md) | 편지함 규약 전문 — 유형 분류, 6칸 템플릿, 금기 6가지 |
| [docs/00_랄프톤_운영설계.md](docs/00_랄프톤_운영설계.md) | 4대 구조, 루프 규율, 붙여넣는 프롬프트, 체크포인트 |
| [channel/pcs.json](channel/pcs.json) | 슬롯 ↔ 역할 ↔ hostname ↔ 계정 매핑 (여기 하나만 고친다) |

---

## 메인 PC 가 1회만 하는 것

```bash
python channel/setup.py            # 계획만 보여준다
python channel/setup.py --apply    # 라벨 + 고정 상태 이슈 생성
```

팀원 3명을 collaborator 로 초대합니다(Settings → Collaborators, 또는):

```bash
gh api -X PUT repos/<계정>/happycall-ralphthon/collaborators/<팀원계정> -f permission=push
```

---

## 계보

사내 `_PC간채널`(2026-08-17 개설, 처리완료 1,433건)의 규약 중 **측정으로 살아남은 것만**
옮겼습니다. 퇴화가 확인된 규약(`긴급도`·`회신` 머리글 필드 — 충전율 24.7%/13.3%,
`_to_` 수신 세션 지정 — 사용률 21.4%)은 가져오지 않았습니다.
