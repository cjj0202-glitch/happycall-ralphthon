# N04-U1 TMS 센터 조사·읽기 전용 결과

pc4 장준호 / j324rst-svg. 기록 시각 2026-09-21T22:56:27.363536+09:00. 작업 브랜치 `work/pc4-n04-tms-qa`, 시작 HEAD `d89c8e3ae5c0923bbd5648151d0c723a2810dd16`. [배정 댓글](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/10#issuecomment-5761479723)의 고정 제품 기준은 `ed2b188de31091a71f1596f50961239d02813107`입니다. 발표자료는 중단·보존 상태를 유지했습니다.

## 사용자가 얻는 변화

- TmsScene의 선택적 `backLabel?: string`을 추가했습니다. 생략하면 기존 `상담으로 돌아가기`, 센터 진입 시 부모는 `센터 업무로 돌아가기`를 전달할 수 있습니다. 실제 `onBack` 콜백 호출 방식은 유지했습니다.
- `handed_off`, `in_progress`, `closed`는 연결 버튼과 실제 `link()` 함수 진입을 모두 차단합니다. 상태 이유는 각각 `센터 전달`, `센터 조사 중`, `처리완료`이며 이관된 접수는 근거 조회만 가능하다고 알립니다. 근거나 방문이 0건이어도 이유가 표시됩니다.
- draft/review의 정상 관련 근거는 계속 연결할 수 있습니다. 기존 busy/pending·중복 연결·비교 방문·관계 가드와 이미 연결된 표시, 방문 선택·정렬·원본 조회 UI를 보존했습니다. 화면 역할을 실제 로그인·권한으로 표현하지 않습니다.
- 상태를 remount 컨텍스트에 넣고 이미 unmount된 연결 콜백도 차단합니다. 같은 ID/revision에서 상태만 전환해도 이전 요청의 늦은 성공·실패가 새 화면에 표시되지 않습니다. 이미 전송한 서버 요청을 취소했다는 뜻은 아닙니다.
- 소유 제품 파일은 `apps/web/components/TmsScene.tsx` 하나입니다. CSS·새 색·폰트·라이브러리·부모 page.tsx·공용 API/상태·WmsScene은 수정하지 않았습니다. 고정 main에 있던 `ApiError.uncertain`별 실패 안내를 보존했습니다.

## 부모 readOnly 추가 계약

[추가 댓글 5761510081](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/10#issuecomment-5761510081)에 따라 `readOnly?: boolean` 기본 false를 받습니다. 부모 true OR 상태 잠금으로 판단하며 false가 handed_off/in_progress/closed 잠금을 해제하지 않습니다. 부모가 이관 전 draft/review를 조회 전용으로 열면 ‘읽기 전용 · 이 접수의 근거는 조회만 할 수 있습니다.’라고 알립니다. 부모 prop도 remount 경계에 포함했습니다.

상태 잠금·backLabel의 첫 결과는 중간 커밋 `8d0eebd41ded178275f2b825aa7a63e2715d47ba`로 보존했습니다. 그 뒤 추가 계약의 8개 검사를 넣었습니다: true+draft/review 2개, false+잠금3상태 3개, prop만 바뀐 뒤 pending resolve/reject 2개, true→false 편집 복귀 1개. 아래는 추가 계약을 포함한 최종 36개 결과입니다.

## 실제 실행 결과

순수 검사기는 실제 TmsScene TSX를 메모리에서 컴파일하고 JSX의 버튼 props와 실제 onClick→link, effect/cleanup을 제어된 hook 환경에서 실행합니다. 연결 콜백은 기록용 경계이며 HTTP를 호출하지 않습니다. CASE-0001을 기본 사례로 상태/방문/관계 반례를 만들었습니다. 이 36개는 서로 겹치는 상태·행동 검사이며 36개 업무 시나리오나 28개 독립 버그가 아닙니다.

| 검사 | 기대 | 실측 |
|---|---|---|
| 동일 입력의 고정 main | 기존 정상 행동 유지, 새 읽기 전용/문구 요구 미구현 재현 | 8/36 PASS, 28 FAIL, exit 1 |
| 수정본 | 정상과 차단 요구 모두 충족 | 36/36 PASS, FAIL 0, exit 0 |
| 함수의 readOnly 가드만 제거 | disabled를 우회한 직접 호출 차단 실패 검출 | handed_off/in_progress/closed 3건 실패, 변이 검출 |
| 버튼의 readOnly 가드만 제거 | 쓰기 버튼 활성 결함 검출 | 상태별 disabled 및 전환 검사 실패, 변이 검출 |
| 변이 합계 | 각 가드의 독립 검출 | 2/2 DETECTED |
| 기본/센터 backLabel | 표시와 콜백 정확히 1회 | 둘 다 PASS |
| 같은 ID/revision 상태 전환 | resolve/reject 뒤 낡은 성공·오류·추가 호출 없음 | 세 상태×두 결과 6건 PASS |
| 고정 main TypeScript | 원래 기준과 후보 모두 타입 오류 0 | 기준/후보 exit 0, TypeScript 5.9.3 |

최종 순수 실행: 2026-09-21T14:01:01.156Z ~ 2026-09-21T14:01:09.571Z (UTC). 수정본 원문 SHA-256 `2480e2d9b86b1c62941e05146c99781c8646f8fa2923a80eb5d07de5e6a0e9a2`, 검사기 `04f1ed592f4b9b3d17ed8ecad29c0ef240faf87ffc4f79ef3bd6503de3f62327`. 기준·후보는 같은 ed2b188 fixture/overlay/실제 ApiError 클래스와 같은 검사기를 사용했습니다. 제품 소스만 달랐습니다. [기준 결과](tms-role-readonly-baseline.json), [수정 결과](tms-role-readonly-unit-results.json)에 개별 기대 대조와 변이 실패 항목·해시를 기록했습니다.

## 실패·검토·검사 조건 정리

설계의 정상/차단 계약을 고정 소스와 후보에서 대조하여 미구현 행동과 개선 결과를 구분했습니다. 독립 코드 검토가 handed_off의 ‘센터 조사 중’ 표현은 착수를 단정한다고 지적해 ‘센터 전달’로 정정했습니다. 상태값을 비동기 컨텍스트로 분리하고 부모의 실제 복귀 연결을 pc1 인수 항목으로 남겼습니다.

검사기 초안의 기준/후보 결과는 각각 8/28·28/28이었으나 fixture 전체 해시가 달랐습니다. 차이는 transcript/timing 및 CASE-0002 audioUrl이고 두 사례의 TMS/근거는 같았습니다. 비교 조건을 더 엄밀히 하기 위해 `--dependencies-ref`를 ed2b188로 고정하고 최종 기준/후보를 다시 실행했습니다. 초안 검사기와 두 실행은 [initial-checker](tms-role-readonly-initial-checker.mjs), [initial-baseline](tms-role-readonly-initial-baseline.json), [initial-unit-results](tms-role-readonly-initial-unit-results.json)에 보존했으며, 최종 동일 입력 결과와 구분합니다.

## 타입 검사와 재현

현재 pc4 작업 브랜치의 공용 api.ts는 고정 main보다 오래되어 ApiError가 없습니다. 그 파일을 무단 편집하거나 main을 통째로 병합하지 않았습니다. `.local/tms-role-readonly-fixed-main`에 ed2b188의 web·data 32개 추적 파일을 복사했고 설치된 node_modules를 junction으로 참조했습니다. 기준 검사를 실행한 뒤 TmsScene 하나만 후보로 대체해 같은 타입 검사를 실행했습니다. 이 결과는 **고정 main 의존성 위 후보의 타입 검사**이며 pc4 오래된 작업 트리 전체나 최신 메인 제품의 빌드 성공이 아닙니다. 순수 검사기의 ApiError도 가짜 클래스를 만들지 않고 고정 main의 실제 클래스 AST를 컴파일하며 API 요청 함수는 실행하지 않습니다.

```text
node tests/e2e/tms-role-readonly-unit.mjs --source-ref ed2b188de31091a71f1596f50961239d02813107 --baseline --json
node tests/e2e/tms-role-readonly-unit.mjs --json
node apps/web/node_modules/typescript/bin/tsc --noEmit --incremental false --project .local/tms-role-readonly-fixed-main/apps/web/tsconfig.json
```

두 순수 명령의 기본 `--dependencies-ref`는 ed2b188입니다. 첫 명령의 exit 1은 새 요구가 없는 기준 제품의 예상 결과입니다. 타입 검사 사본은 Git으로 배포하지 않으며 [typecheck JSON](tms-role-readonly-typecheck.json)의 32개 원본 Git blob/후보 SHA-256으로 재구성할 수 있습니다. 메인은 고정 main에 TmsScene 변경을 적용한 뒤 통합 상태에서 다시 타입 검사를 할 수 있습니다. 설치나 서버 시작은 재현 명령에 포함하지 않습니다.

## 인계와 미실행

부모 화면에서 센터 진입 시 `backLabel="센터 업무로 돌아가기"`와 센터 화면으로 복귀하는 기존 `onBack`을 함께 전달해야 합니다. 센터 전체보기에서 draft/review를 조회할 때도 `readOnly={true}`를 전달합니다. 부모 false는 사건 상태 잠금을 해제하지 않습니다. 단순 문구 지원과 컴포넌트 콜백 1회 검사는 실제 센터 라우팅 성공이 아닙니다. 상태 전환 remount는 현재 선택 방문/정렬을 초기화합니다.

새 서버·브라우저·소켓·설치·과금·배포·운영 데이터 사용은 0회입니다. 실제 DOM/키보드/레이아웃/원본 details 열기·애니메이션·전체 앱 빌드·센터 부모 통합·브라우저/HTTP 회귀·실제 쓰기 취소는 NOT_RUN입니다. controlled matchMedia=false 및 hook 수명 검사는 실제 React DOM 검사를 대신하지 않습니다. 메인의 독립 검토·부모 통합·최신 제품 인수가 남아 있으며 #10과 N04 전체를 완료 처리하지 않습니다.
