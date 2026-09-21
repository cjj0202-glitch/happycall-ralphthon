# N01 Bolt — 상담 작업대에서 연결 근거를 바로 읽기

작성: 2026-09-21, pc1/CJJ 대기세션1. 구현 전 설계. 기준 HEAD `88ba3b1`. AGENTS/PROMPT_team, docs24·25·26, ui-reference-brief를 대조했다.

## 하나의 병목과 변경

기존 상담 작업대는 선택 근거를 `연결된 근거 N건 · E-…`로 나열한다. 상담원이 출처·기록 시각·관측 내용을 읽으려면 물류 화면을 다시 열어야 한다. 이번 한 가지 변경은 **저장된 선택 근거를 출처·시각·상태·내용 카드로 표시**하는 것이다. 조회 동작만 추가하고 근거 선택/저장, 접수 편집/확인/이관 계약을 바꾸지 않는다.

전: 원문/AI/사람 편집 → AI 사실/미확인 요약 → 근거 ID 한 줄.  
후: 동일 작업·요약 유지 → 현재 사건/기준시각 → 연결 근거 카드(관측 내용·원본 출처·기록 시각·상태·합성 표시·원본 펼침).

## 사용자 과업·정보 순서

- 상담원은 원문·AI 제안·사람 편집을 그대로 대조한 뒤, 같은 사건의 **저장된 연결 근거**를 확인한다.
- 각 카드에 WMS/TMS 출처, 기록 확인/미확인, 합성 여부를 서로 다른 의미로 표시한다. `fact`는 기록 상태이며 실물 인도·발생 공정·귀책 확정이 아니다.
- 핵심 관측 내용과 출처·시각은 펼침 밖에 둔다. 원본 필드와 근거 ID는 키보드로 여는 native details에 보존한다.
- 선택한 근거가 없으면 WMS/TMS에서 근거를 연결하라는 안내를 제공한다. 기존 물류 이동 버튼을 유지한다.
- AI 요약과 실제 선택 기록은 별도 소제목으로 구분한다. AI의 facts 목록을 새로운 시스템 확정 사실로 승격하지 않는다.

## 데이터·시간·연결 계약

`c.selectedEvidence`의 고유 ID를 **현재 c.evidence만** 조회한다. 다른 사건 목록이나 전역 근거에서 ID를 찾지 않는다. 새 INT가 명시적으로 연결한 원본 사건은 `linkedFixtureId`로 구분한다.

| 상태 | 표시 |
|---|---|
| 현재 사건의 유일한 근거, 기준시각 내 | 카드의 관측값·출처·전체 기록시각 표시 |
| 기록시각 null | 시각 미등록, 기준시각 대조 불가 안내; 수치 0으로 보충하지 않음 |
| 기준시각 이후·시각 파싱/시간대 불명확 | 관측 내용 표시 보류, 사유만 표시 |
| 현재 사건에 없는 ID·중복 원본 ID | 내용 표시 보류, 원본 확인 필요 |
| 명시 caseId/storeId 불일치 또는 relationStatus needs_review/unlinked | 자동 채택 없이 내용 표시 보류 |
| 합성 명시 | 합성 자료 배지; 합성 여부와 기록 상태를 분리 |
| 합성 여부 미등록 | 미등록 표기; 실제 기록으로 추정하지 않음 |

현재 API에는 docs26의 모든 확장 메타필드가 존재하지 않는다. 제공된 source/time/status를 사용하고, 확장 caseId/storeId/relationStatus/sourceAsOf 등이 있으면 경계를 확인한다. 누락된 sourceRecordKey/정밀도/시간대/관계 상태를 임의 확정해 만들지 않는다. ISO의 명시된 시간대를 가진 기록만 KST로 변환한다.

## 상태·권한·복구

새 카드에는 선택 변경·저장 API를 넣지 않는다. 카드 펼침은 접수 상태·reviewConfirmed·formRevision을 바꾸지 않는다. 기존 formRevision은 편집 시작/자기 저장/분석 응답 시점 계약을 유지하며 현재 c.revision으로 자동 덮어쓰지 않는다. 사람 입력·STT·AI 원본과 explicit reference guard도 수정하지 않는다.

표시 보류는 선택 ID를 서버에서 삭제하지 않는다. 카드 오류는 해당 근거만 보류하며 나머지 정상 카드는 읽을 수 있어야 한다. 원인·작업자 귀책·도착 여부를 카드의 배지나 색만으로 확정하지 않는다.

## BMAD 검토와 소유

- 업무 가치: ID 재조회 부담을 줄이는 정보 노출 실험. 업무시간 감소는 사람 관찰 전 미입증.
- UX: 관측값 우선, 원본 펼침, 색 외 상태 텍스트, 1440/1024/390px 읽기와 키보드 이동.
- 구조: 기존 CaseData와 API를 소비하는 읽기 전용 표시. 서버·types·api·fixture 계약 변경 없음.
- 검증: 선택 집합/내용/시간·사건 경계/키보드/미저장 입력/revision을 대조한다.

소유는 page.tsx의 Desk 근거 영역과 globals.css의 해당 스타일, 이 문서, tests/e2e/evidence-cards-bolt.mjs다. LogisticsView, Owner/Center, api/types, fixture, CallReview/WmsScene/TmsScene는 수정하지 않는다. 공유 파일의 다른 작업자 변경을 보존한다.

## 수용 기준·재현 계획

1. ID뿐인 기존 선택을 라벨·원본 출처·기록시각·내용·기록 상태·합성 여부 카드로 읽는다.
2. 선택 0건/연결 후/다른 사건 전환 후 표시 집합이 실제 API와 일치한다. 현재 사건 밖 상세를 노출하지 않는다.
3. null과 0을 구분하고 미래/시간대 불명확·관계 불일치는 표시를 보류한다.
4. native details를 Tab/Enter/Space로 조작하고 focus-visible이 보인다.
5. 1440/1024/390px에서 카드 내용과 버튼이 읽히고 페이지 가로 넘침이 없다.
6. 읽기 동작은 미저장 접수 입력·revision을 바꾸지 않는다. 새 합성 INT에서 동시수정 시 기존 409와 입력 보존을 확인한다.
7. 실제 CASE-0001/2 변경·analyze/replay·유료 모델 호출은 금지한다. 필요한 새 INT만 생성하고 그 ID만 변경한다.

검증 명령: `npm --prefix apps/web run typecheck`, `node tests/e2e/evidence-cards-bolt.mjs`. 실행 결과·전후 수치·한계는 아래에 실제 측정 후 추가한다. AI Playwright 기술 관측이며 실제 사람 Silent Test나 원격 PC 검수가 아니다.

## 구현·실측 결과 — 2026-09-21 18:03 KST

구현은 Desk 내부의 읽기 전용 표시와 `.desk-evidence-*` 14개 스타일로 한정했다. 기존 formRevision 갱신 위치·저장 payload·reviewConfirmed·Owner explicit reference 선택은 그대로다. 최신 검증 시작/종료의 page.tsx, globals.css, LogisticsView, fixture, server/service.py, 테스트 스크립트 SHA-256이 모두 같았다. 검증 중 소스 변경은 없었다.

### 전후 변화

같은 기존 INT-51BB3232를 GET과 화면 선택만으로 비교했다. 저장된 선택은 E-M3/E-M1 두 건으로 동일했다.

| 관측 | 전 | 후 |
|---|---|---|
| 선택 근거 내용 카드 | 0개, ID 한 줄 | 2개 |
| 각 근거의 내용·출처·기록시각·상태·합성 표시 | 작업대에 없음 | 2개 모두 표시 |
| 원본 기록 펼침 | 없음 | 2개, native details |
| AI 사실 목록 제목 | 확인된 사실 | AI가 정리한 사실 · 확인 전 초안 |

전후 PNG는 로컬 `tests/e2e/test-results/evidence-cards-baseline/before.png`, `after.png`에 보존했다. 업무시간 감소나 사용자 만족도는 측정하지 않았다.

### 실제 API·브라우저

최종 실행: `node tests/e2e/evidence-cards-bolt.mjs` → **8 PASS / 0 FAIL_RECHECK**, 18:03:18~18:03:28 KST.

- 결과: `tests/e2e/test-results/evidence-cards-2026-09-21T09-03-18-841Z/results.json`
- 미도착 신규 INT-AFBFF581: 실제 WMS/TMS 연결 버튼으로 E-M3/E-M2/E-M1 연결, API 집합과 카드 3개 일치.
- 오출고 신규 INT-DF356D17: E-W1/E-W3/E-W4 연결, API 집합과 카드 3개 일치.
- 미연결 신규 INT-440EDB09: 같은 점포·대상이어도 카드 0개. 사건 전환 후 기존 카드 3개 복원.
- E-M2/E-W4는 시각 null을 미등록으로 표시하며 unknown을 미확인으로 유지했다.
- Tab 이동 후 Enter 열기/Space 닫기와 3px solid focus-visible 확인. 카드 읽기 중 PATCH 0건, 미저장 요청·로컬 확인 체크 보존, 서버 revision 3/selectedEvidence 3개/reviewConfirmed false 불변.
- 별도 PATCH로 서버 revision 4를 만든 뒤 기존 폼은 expectedRevision 3으로 저장하여 409. 자동 재시도 없이 1회 요청, 입력·선택 집합 유지.
- CASE-0001/2의 revision·선택·원문·접수 전후 동일. analyze 요청 0건. 실제 AI·replay·유료 호출 없음.

| 화면 폭 | 문서 폭 | 카드 폭 | 관측 내용 글자 | 메타 글자 | 가로 넘침 |
|---|---:|---:|---:|---:|---|
| 1440 | 1440 | 639 | 14px | 13px | 없음 |
| 1024 | 1024 | 942 | 14px | 13px | 없음 |
| 390 | 390 | 324 | 14px | 13px | 없음 |

각 폭의 `*-desk.png`, `*-evidence-cards.png`와 `keyboard-details-open.png`, `stale-409-retained-input.png`를 결과 디렉터리에 보존했다. 3폭의 실제 PNG를 열어 내용/배지 줄바꿈·잘림 여부를 확인했다. pageerror 0건, 예상된 409 console 1건, 화면 이동 중 기존 wav 요청 ERR_ABORTED 2건을 원시 결과에 남겼다. 음성 재생 품질은 이번 검증 범위가 아니다.

### 경계 검토와 수정

메모리 내 React SSR 검증은 실제 page.tsx를 변환해 렌더하고 fixture 복제본에만 반례를 넣었다. 서버·원본 fixture를 바꾸지 않았다. 미래 시각, 시간대 누락, 다른 사건/점포, 미연결/검토 필요 관계, 중복/없는 ID, null·0 구분 등 **23/23 PASS**다. 로컬 재현 명령은 `node tests/e2e/test-results/evidence-cards-baseline/boundary.cjs`, 결과는 같은 폴더 `boundary-result.json`이다. 이 보조 스크립트와 PNG/JSON은 Git 제외 로컬 증거이며 커밋 대상은 E2E 스크립트와 본 문서다.

독립 코드 검토에서 발견한 2건을 수정했다. Date.parse가 2월 30일을 다른 날짜로 정규화하지 못하도록 달력 요소를 대조하며, observedAt:null로 미래 time을 가리지 못하도록 제공된 시각 모두를 검사한다. 상충하는 두 시각은 내용을 보류하고 동일 순간의 Z/+09:00 표현은 허용한다. 검토자가 실제 수정 코드를 재실행해 반례 및 정상 대조군 **7/7 PASS**를 확인했다. 수정 후 위 실제 API E2E 8건과 typecheck를 다시 통과했다.

최초 E2E 시도는 닫힌 details 안에도 `.desk-evidence-meta`가 있어 테스트 locator가 중복된 오류였다. 직접 자식 `:scope >`로 수정 후 통과했다. 최초 실행·수정 후 실행·최종 재검증에서 신규 합성 INT 총 9건을 생성했으며 삭제하지 않고 추적 증거로 보존했다. 원본 CASE 변경은 없다.

### 한계·인계

미등록 sourceRecordKey/정밀도/시간대/관계 메타는 미등록으로 남는다. 제공된 ISO 시간대만 KST 변환에 사용하고 원문 source를 파싱해 레코드 키를 만들어내지 않는다. 실제 운영 원천 연동·사람 Silent Test·원격 PC 검수는 미완료다. 기존 다른 화면 이동 시 미저장 Desk 폼이 해제되는 동작은 이번 읽기 전용 카드 변경 범위 밖이며 보존 개선으로 주장하지 않는다.

`npm --prefix apps/web run typecheck`와 소유 파일 `git diff --check` 통과. 서버·배포·Git 커밋/push는 실행하지 않았다. 소유 4파일을 메인 인수 대상으로 반환하며 TODO·공유 계약 완료 판정은 메인이 담당한다.
