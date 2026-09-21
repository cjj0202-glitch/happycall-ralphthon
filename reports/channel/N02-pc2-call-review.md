N02 / pc2 안영일(MR-A83)에게 통화 검토 UX와 음성 명료도 개선의 기능 묶음을 일임합니다.

## 왜 지금
사용자가 메인에게 큰 기능을 실제 다른 PC에 편지로 일임하라고 다시 지시했습니다. 이 편지는 이전 docs24 배정을 실행 가능한 단위로 구체화합니다. 로컬 보조 세션을 다른 PC 실적으로 계산하지 않습니다. 기준 main 커밋은 `d4b4a8137fbc608911e9f6f71bd4b5e289e0a958`입니다. 이후 main 변경은 diff로 확인하고 공용 파일을 덮어쓰지 마세요.

공통 정본: AGENTS.md → PROMPT_team.md → docs/24_야간_4PC_작업계획.md → docs/25_단계별_상세설계와_전체테스트.md → docs/26_원천구조와_솔루션_연결계약.md. 원천은 30_센터작업모니터링/33_해피콜분석/36_자동점착운영이며 이번 화면은 독립 합성 사례입니다. 실제 운영 자료·행·식별값을 Git/Release/AI API에 보내지 않습니다.

## 공통 실행·인계
- 첫 회신에 실제 hostname/GitHub/절대경로/HEAD/선점 파일/첫 산출물 예정 시각을 적으세요. 신원은 pcs.json 본인 슬롯과 일치해야 합니다. 기존 작업이 있으면 보존하고 같은 이슈에 충돌 경로를 회신합니다.
- 상세설계(사용자 결과·화면/상태·키/시간/출처·실패/복구·수용 기준) → 작은 Bolt 1개 → 구현/단위·UI 테스트 → 반례 → 수정/재검 순서로 진행하세요. BMAD 4관점·Grill-me 미결정·Ralph 실행 기록을 reports/본인pc/에 남깁니다. 기존 결정은 반복 질문하지 마세요.
- 자기 branch에 명시 파일만 중간 커밋·push하고 이 편지에 결과 커밋/파일/명령/기대값·실측/화면/한계를 회신하세요. main에는 직접 push·merge하지 않습니다. 메인이 코드리뷰·통합·독립 적대검증 후 인수합니다. 자기 작업을 승인하거나 이슈를 닫지 마세요.
- 20:00 첫 작동본, 22:00 통합 가능한 결과를 목표로 하며 늦으면 실제 예상시각과 원인을 회신합니다. 최종 목표는 9/22 09:00 KST입니다. 새 결과가 없으면 반복 편지를 만들지 말고 기존 이슈 코멘트·상태 이슈를 이용합니다.
- 현재 Vercel은 52g Studio/g-28이며 배포·공용 API·fixture·page.tsx·LogisticsView·lib/types.ts·manifest·작업표는 pc1 소유입니다. 기존 TEST 발송·메인 API 재시작·AWS 설치 정책거부 및 Blob403을 해결하라는 업무가 아닙니다. 해당 거부를 다른 PC로 우회하지 마세요.
- 기본 개발/검사는 무과금 replay입니다. 유료 TTS/STT/LLM을 자동 반복하거나 원장을 새로 만들지 마세요. 기존 v2 음원으로 시작하고 새 음성은 재생성 계획/예상 호출/필요 입력을 pc1에 회신해 기존 총예산 원장과 연결합니다. 공개 범위·비용을 몰래 늘리지 않습니다.

## 중단 조건
미등록/계정 불일치, 소유 경로 충돌, 정책·권한 거부, 비밀값/원천자료 공개 위험은 해당 작업을 멈추고 재현과 영향만 회신합니다. 가능한 독립 부분은 계속합니다. TEST 미완료는 docs24의 DEC-016에 따라 별도 유지하며 준비됐다고 허위 보고하지 않습니다. watcher는 감지만 하며 세션 자동 재개 성공을 가정하지 않습니다.

## 해줘야 할 일 · N02
- [ ] `reports/pc2/design.md`, `scenario-test-plan.md`를 먼저 작성하고 `work/pc2-n02-call-review` branch에서 작업하세요.
- [ ] 상담원이 통화 종료 후 원문 대화록·AI 정제·상담 입력 차이·추가 질문을 한눈에 대조하는 CallReview를 구현하세요. 두 화자, 선택 발화 시각/재생 구간, 단위 정정(1 EA→1 BOX), 미식별 점포, 분석 중/실패/재시도/음원 없음 상태를 구분합니다. 원대본을 실제 STT 결과로 표시하지 않습니다.
- [ ] 현재 v2 음원의 재생·화자 구분·배속/볼륨/자막 동작을 개선하고 전후 작은 Bolt를 기록하세요. 기존 수치 -18.0/-17.9 LUFS 및 STT 점포/용어 오류가 출발점입니다. 실제 사람이 듣지 않았다면 명료도 합격으로 쓰지 않습니다.
- [ ] 소유: `apps/web/components/CallReview.tsx`, `CallReview.module.css`, `scripts/media_pc2/`, `planning/media/voice-scenarios.md`, `tests/remote/pc2/`, `reports/pc2/`. 공용 CSS/page/fixture/manifest 수정 금지. 합성 자산은 본인 output 아래 별도 후보로 만들고 pc1이 채택/Release합니다.
- [ ] export 기본 컴포넌트 계약은 `caseData: CaseData`, 선택적 `disabled?: boolean`, `onPlaybackEnded?: () => void`를 기준으로 하세요. 종료 이전 분석 실행을 우회하지 말고 부모 연결 예시를 보고서에 주세요. 기존 native audio 접근성과 키보드를 보존합니다. 추가 props는 제안으로 기록합니다.

## 실행 명령 · 실제 보고된 pc2 경로
```powershell
Set-Location 'C:/Users/Administrator/Desktop/hackerton/happycall-ralphthon'
python channel/whoami.py
gh api user --jq .login
git status --short
git rev-parse HEAD
git fetch origin
git log --oneline HEAD..origin/main
# 로컬 변경/분기 상태를 대조한 뒤 안전할 때만 ff-only 최신화
# 자기 branch는 기존 변경을 보존하고 하나만 생성/재사용
python scripts/fetch_demo_media.py --upgrade-approved
python scripts/fetch_demo_media.py --verify-only
# 기대: verified 3개, missing 0. 다른 음원이 있으면 보존·실패가 맞습니다.
python channel/mail.py watch --interval 30 --bell
```

## 검증 방법 + 기대값
WAV2건 끝까지 재생·오류0, 재생시각과 선택발화 정합, 원문/AI/사람 구분, 미확인점포가 확정되지 않음, muted/배속 상태 보임, 키보드 조작/초점, 1440·1024·390폭 수평 넘침0. 실제 컴포넌트 렌더를 Playwright로 확인하고 무음/404/짧은음원/잘못된 시각 반례도 남기세요. 테스트 수·입력·실측을 명시하며 OS 출력/사람청취는 별도입니다. 유료 호출0으로 개발검증하세요.
