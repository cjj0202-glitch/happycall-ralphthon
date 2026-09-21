N04 / pc4 장준호(j324rst-svg)에게 TMS 방문순서·도착근거 화면과 전체 흐름 독립 시나리오 검증을 일임합니다.

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

## 해줘야 할 일 · N04
- [ ] `reports/pc4/design.md`, `scenario-test-plan.md`를 먼저 작성하고 `work/pc4-n04-tms-qa` branch에서 작업하세요.
- [ ] TmsScene에서 계획 시각/실제 기록/진입·진출/배송완료 등록을 구분하고 현재 선택 점포·이전/다음 방문·확인해야 할 정보를 직관적으로 보여주세요. 루트 애니메이션·방문 정지는 합성 개념 지도임을 표시하고 일시정지/키보드/reduced-motion을 제공합니다.
- [ ] CASE1 계획05:00 대비 실제없음(null)은 미등록, CASE2 완료05:10은 시스템 등록이며 정확한 상품 인도 여부와 구분합니다. null을00:00·0분·도착완료로 표시하지 마세요. TMS영상은 등록된 후보가 없으면 미등록입니다.
- [ ] raw36 참고키는 배송일+센터+루트+차량+순번입니다. 순번과 완료시각 정렬이 항상 같지 않고 GPS진입은 실물인도가 아닙니다. 시스템 시각·기준일과 원천 기간을 억지로 연결하지 않습니다.
- [ ] 소유: `apps/web/components/TmsScene.tsx`, `TmsScene.module.css`, `data/overlays/pc4-tms.json`, `tests/remote/pc4/`, `reports/pc4/`. 기본 export와 `caseData: CaseData`, `onLinkEvidence(id: string): Promise<void> | void`, `onBack(): void`. 공용 셸/API/fixture를 고치지 말고 pc1에 연결 제안을 보냅니다.
- [ ] 자기TMS 외 통화/텍스트→상담검토→WMS/TMS근거→센터최종회신→경영주조회·종결을 독립 검증하세요. 두흐름 각3회 총6회를 같은커밋/replay/격리상태로 재현할 스크립트와 고정 체크표를 만드세요. 아직 연결되지 않은 단계는 미실행으로 남기고 가짜 성공을 만들지 않습니다. 자기TMS 검사를 독립검증이라고 세지 마세요.
- [ ] 낡은revision409, expectedRevision누락428, 다른점포/날짜근거혼입, 미완료조치종결차단, API오류가성공처럼보이지않음, 미디어404·오프라인/복구를 보고하세요. 초기화는 검사 전용 임시 상태만 쓰고 원본상담/예산원장은 보존합니다.

## 실행 명령 · 실제 보고된 pc4 경로
```powershell
Set-Location 'C:/Users/j324r/OneDrive/문서/ChatGPT/해커톤_D-Day/happycall-ralphthon'
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
2case×1440/1024/390폭·키보드·미등록/시각경계·동일사건 연결을 측정합니다. 통합리허설은 분모6, 실행/통과/실패/미실행을 각각 보고하고 6/6 아니면 완료로 쓰지 않습니다. 실 API/유료 분석 호출0, replay임을 표시합니다. P0/P1마다 재현입력·기대·실측·스크린샷·콘솔·API상태를 붙이고 수정은 소유자 pc1에 전달하세요.
