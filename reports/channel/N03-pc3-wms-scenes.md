N03 / pc3 정준화(mcjun86-oss, LAPTOP-U2AL73UH)에게 WMS 공정 화면·이동 애니메이션·이벤트별 합성 CCTV 묶음을 일임합니다.

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

## 해줘야 할 일 · N03
- [ ] `reports/pc3/design.md`, `scenario-test-plan.md`를 먼저 작성하고 `work/pc3-n03-wms-scenes` branch에서 작업하세요.
- [ ] WmsScene에서 피킹→소터 투입→분기/슈트→출고의 시각·토트·상품/수량/단위와 선택 공정의 다음 행동을 보여주세요. 움직임은 실제 좌표가 아닌 공정 설명임을 표시하고 일시정지·reduced-motion·키보드를 지원합니다.
- [ ] CASE2의 피킹 비스킷18EA와 출고 휴지1BOX 차이를 비교하되 발생 공정·작업자 귀책은 미확인으로 남기세요. CASE1은 미도착 주장과 확인된 출고/작업기록을 구분합니다. 원천 30의 snapshot 누계를 개별 이동 이력처럼 만들지 않습니다.
- [ ] 기존 sorter-demo는 CASE2의 등록된 W-W3 분기이동 설명뿐입니다. 최소 피킹/분기/출고 3개 구간을 각 시나리오와 메타데이터로 설계하고, 가능한 AI 생성/코드 애니메이션으로 별도 합성 후보를 만드세요. 생성 기법을 정확히 적고 실제 CCTV로 가장하지 않습니다. 미생성 구간은 미등록으로 표시합니다.
- [ ] 클릭한 event에 caseId/system/cameraId/eventIds/occurredAt/startSeconds/endSeconds/url/synthetic=true/hash가 맞는 영상만 연결하세요. 다른점포/날짜/토트·범위초과·영상실패는 차단/복구 안내가 있어야 합니다.
- [ ] 소유: `apps/web/components/WmsScene.tsx`, `WmsScene.module.css`, `scripts/media_pc3/`, `data/overlays/pc3-wms.json`, `tests/remote/pc3/`, `reports/pc3/`. 기본 export와 `caseData: CaseData`, `onLinkEvidence(id: string): Promise<void> | void`, `onBack(): void`를 제공합니다. 메인이 공용 셸에 연결합니다.
- [ ] MP4/WAV/이미지 원본은 Git에 넣지 마세요. 후보 로컬 경로·바이트·SHA256·생성방법·메타데이터를 먼저 회신하고 별도 Release 후보 태그가 필요하면 pc1에 알려주세요. 공용 fixture/미디어 정본은 직접 수정하지 않습니다.

## 실행 명령 · pc3 현재 저장소에서 실제 경로 확인
pc3 보고에는 저장소 절대경로가 없었습니다. 아래 첫 명령이 반환한 실제 절대경로를 ACK에 쓰세요. 다른 PC 경로를 추정해 만들지 마세요. Git 저장소가 아니면 본인의 기존 happycall-ralphthon 폴더로 이동한 뒤 실행합니다.
```powershell
$pc3RepoRoot = git rev-parse --show-toplevel
if ($LASTEXITCODE -ne 0) { throw 'pc3의 기존 저장소 경로 확인이 필요합니다.' }
Set-Location -LiteralPath $pc3RepoRoot
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
실제 컴포넌트 2case×3폭 렌더, 공정클릭→같은event 영상/원본스캔, 잘못된case/시간/토트/구간 최소6반례 차단, 정상영상 재생 진행·닫기/초점복귀·404복구, reduced-motion에서 불필요한 자동이동 없음. 합성표시 항상 보임, 특정귀책 확정0, source/unknown 유지. 독립 세션으로 반박하되 같은 PC임을 기록하고 pc1 최종 인수를 기다리세요.
