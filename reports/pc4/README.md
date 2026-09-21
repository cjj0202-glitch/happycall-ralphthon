# N04 — TMS 구현·검증 인계

후속 N04-Q2(2026-09-21 20시): 최종 통합 릴리스의 [실행 계약·매트릭스](q2-plan.md)와 [검사기 준비 기록](q2-ui-checker-notes.md)을 추가했습니다. **최종 제품 0/6, 경계 0/15 미실행**입니다. 아래 N04 결과는 이전 빌드의 이력이며 Q2에 합산하지 않습니다. 최종 실행은 `tests/remote/pc4/q2-run.py`의 준비/실행 게이트를 사용합니다. 이전 `flow-ui-run.py`의 dev 실행은 최종 릴리스 검증 경로가 아닙니다.

2026-09-21 KST, pc4 / 장준호 / j324rst-svg. 사용자가 19:16에 #10 작업 수행을 직접 지시해 제품 작업을 재개했습니다. 기준은 `a952edee271574401332148f42969621a81a74d7`, 브랜치는 `work/pc4-n04-tms-qa`입니다. 기존 변경을 보존하고 fast-forward로 받았으며 공용 코드·중앙 작업표는 수정하지 않았습니다.

## 구현 결과

`TmsScene`은 문의 점포의 계획 도착·배송완료 등록·모바일 진출입을 구분합니다. CASE1의 계획 05:00/실적 null은 미등록으로, CASE2의 05:10은 시스템 등록으로 표시합니다. 실물 인도 여부는 별도 확인 사항입니다. 선택 방문, 이전/다음, 원천 순번/완료시각 표 정렬, 합성 경로와 정지 가능한 트럭 설명, 키보드·모션 감소를 제공합니다.

업무일·센터·루트·차량·순번과 명시적 사건 연결을 검사합니다. 다른 사건/점포/날짜, 무시간대/잘못된 달력/기준 이후 기록을 자동 연결하지 않습니다. 서버가 `referenceCaseId`로 검증한 신규 텍스트 접수는 `linkedFixtureId`와 원천 내용 전체를 대조해 지원합니다. 저장 실패는 인라인 오류·재시도로 처리하고 새 서버 revision의 근거 선택 해제를 반영합니다.

TMS 영상은 미등록입니다. 개념 지도와 차량 설명은 GPS 궤적이나 실물 인도의 증거가 아닙니다. 설계·BMAD·미결정은 [design.md](design.md), 전체 검증 계획은 [scenario-test-plan.md](scenario-test-plan.md)에 있습니다.

## 실측과 구분

| 검사 | 실측 | 증거/한계 |
|---|---|---|
| TMS 계약 반례 | 39/39 PASS | [계약 JSON](tms-contract-results.json), 현재 소스 SHA 포함 |
| TMS 실제 브라우저 | 25/25 PASS, 오류 0, 소스 변화 0 | [UI JSON](tms-ui-2026-09-21T10-29-43-975Z/results.json); 1440/1024/390 × 2사례, 키보드·모션·비동기·날짜·관계키 |
| 기존 제품 UI 두 사례 × 3회 | 6/6 PASS | [전체 흐름 보고](ui-flow-results.md); **기존 pc1 셸/LogisticsView** 기준, 새 TMS 통합 검증은 아님 |
| 기존 제품 UI 장애·경계 | 6/6 PASS | 영상404/재생복구, API503, API단절, 실제 브라우저 offline/online, 신규 텍스트/명시참조 |
| 독립 HTTP 통화·텍스트 × 3회 | 6/6 PASS | [HTTP JSON](scenario-results-20260921T102227592862Z.json), 실제 loopback 요청136건 |
| HTTP 상태/관계/장애 경계 | 12/12 PASS | revision428/409, 타사건, 역할, 미완료 종결, 503/단절복구. 공식 모델 평가12개와 별개 |
| TypeScript | 제품·하네스 모두 PASS | `tsc --noEmit --incremental false` |
| 제품 빌드 | PASS | `npm --prefix apps/web run build`, 기존 제품 정적 export |
| 전체 Python 단위검사 | 169건 중 168 PASS / 1 SKIP | FFmpeg 실파일 변환 검사는 실행 파일 미설정으로 SKIP, 실패0 |
| 준비·미디어 | preflight 10/10, 작업표 검사 PASS, 자산3/3 해시 일치 | 기존 45개 작업표 검사와 N04 인수는 다른 사실 |

실제 전체 음성 1배속 재생은 각 사례의 첫 회에만 수행했습니다(47.782초/49.693초). 반복 2~3회는 끝부분 탐색 후 실제 `ended`를 관측했습니다. 신규 텍스트는 저장된 replay가 없어 409를 표시하며 실제 AI 정제는 미실행입니다. 유료 호출·외부 분석 호출은 0입니다. 새 임시 상담 상태만 사용했고 원본 상담/예산 해시가 보존됐습니다.

## 발견·수정·재검증

1. 서버에서 근거 선택을 해제해도 로컬 ‘연결됨’ 표시가 남는 문제 → revision/selectedEvidence로 상태 수명 동기화 → 실제 UI 회귀 PASS.
2. 정상 `INT-*` 명시참조 텍스트 접수를 차단하는 문제 → 서버 반환 계약·원천 전체 일치 검증 추가 → 실제 UI 회귀 PASS 및 계약 반례 추가.
3. SVG title의 여러 자식으로 발생한 hydration 오류 → 단일 문자열 → 최종 브라우저 pageErrors 0.

[초기 TMS 개발 관측](tms-ui-2026-09-21T10-28-09-987Z/results.json)은 수정 중 소스가 변해 `sourceStable=false`입니다. 이를 고정 소스 전후 성능 비교로 계산하지 않습니다. 최종 고정 소스 실행은 위 25/25 결과입니다. 전체 흐름의 첫 탐색 2건은 테스트 label locator 오류였으며 제품 수정 없이 검사만 고쳐 같은 제품 소스로 재실행했습니다.

같은 pc4의 보조 에이전트가 결함을 재검토했습니다. 이를 pc1의 독립 인수나 다른 물리 PC 실적으로 세지 않습니다.

## pc1 통합 지점

공용 `apps/web/app/page.tsx`의 TMS 분기에서 다음 기본 export를 사용하세요. WMS 분기와 기존 상태 저장 계약은 유지합니다. 워커는 이 공용 파일을 편집하지 않았습니다.

```tsx
import TmsScene from '@/components/TmsScene';

<TmsScene
  caseData={active}
  onBack={() => setView('desk')}
  onLinkEvidence={async id => {
    await save(active.id, {
      expectedRevision: active.revision,
      selectedEvidence: Array.from(new Set([...(active.selectedEvidence || []), id])),
    });
    setToast('물류 근거를 접수 건에 연결했습니다.');
  }}
/>
```

부모 콜백은 실제 저장 성공에만 resolve하고 실패는 reject해야 합니다. 화면이 가진 revision을 그대로 보내고 409를 최신 revision으로 자동 재시도하지 않습니다. `data/overlays/pc4-tms.json`은 검토한 두 합성 사례의 연결 계약이며 원천 운영자료가 아닙니다. 신규 물류 사례는 검토된 계약 추가가 필요합니다.

## 재현

이 PC는 작업 루트에서 `. .\Start-HappyCall.ps1`을 실행하면 저장소로 이동하고 Python/Node/Git/gh PATH를 준비합니다. npm 실행 파일은 `node '..\.happycall-tools\npm\bin\npm-cli.js'`입니다. 다른 PC에서는 설치된 Node/npm/Python을 사용하세요.

```powershell
node tests/remote/pc4/tms-contract-check.cjs
python tests/remote/pc4/scenario-check.py --port 18104
python tests/remote/pc4/flow-ui-run.py --api-port 18105 --ui-port 13105

# 별도 터미널: 공용 셸을 변경하지 않는 TMS 계약 하네스
node tests/remote/pc4/ui-serve.mjs
# 브라우저 경로는 이 PC의 설치 경로로 지정
$env:E2E_CHROMIUM = Join-Path (Split-Path (Get-Location).Path -Parent) '.happycall-tools/playwright/chromium-1208/chrome-win64/chrome.exe'
node tests/remote/pc4/ui-check.mjs
```

의존성은 `apps/web`과 `tests/e2e`의 lockfile, Python은 `uv.lock` 기준입니다. 검사 서버는 고유 포트를 사용하며 기존 3100/8100 서버를 종료하지 않습니다. `flow-ui-run.py`는 이 PC의 portable 런타임 배치를 사용하므로 다른 환경에서는 Node/Chromium 경로를 대조하세요.

## 남은 인수

pc1의 공용 셸 연결, 연결 후 같은 릴리스 6회 재검증, 실제 사람 검수와 실제 AI 품질 평가는 별도입니다. TEST 왕복 미완료도 유지합니다. pc4는 main 병합·배포·중앙 TODO 변경·이슈 종결을 수행하지 않았습니다. 통합과 최종 인수는 메인에게 요청합니다.
