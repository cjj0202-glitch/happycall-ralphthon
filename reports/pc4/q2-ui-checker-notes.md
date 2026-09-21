# N04-Q2 UI 검사기 준비 기록

- 준비 시각: 2026-09-21 20:05 KST. 최종 제품 검사 상태: **NOT_RUN**.
- 준비 작업 기준 HEAD: `1b82f1d7fad1b31545d512b28896bfcba40189ec`.
- 업무 기준 문서: `e5469aa99bb266c5a977b80c097223275ac6fc9b`의 `docs/28_PC_업무배정_기준.md`, `planning/media/production-quality.md`, `planning/media/synthetic-center-scene.md`.
- 수정 범위: `tests/remote/pc4/flow-ui-check.mjs`와 이 문서뿐. 제품 소스, fixture, 공용 설정, 원본 원장 수정 없음. commit/push 없음.
- 최종 통합 SHA·자산·표준 UI selector 미확정. 기존 PC2 CallReview는 공용 화면에 통합되지 않았으며 예전 UI 결과를 Q2 결과로 재사용하지 않는다.

## 이번에 실행한 검사

```powershell
node --check tests/remote/pc4/flow-ui-check.mjs
node tests/remote/pc4/flow-ui-check.mjs --self-test
```

구문 검사 통과. 검사기 자체 합성 관측 self-test **16/16 PASS**이며 stdout JSON에 개별 결과와 `plannedBoundaryIds`를 출력한다. 자연 종료 양성 1개, 끝 탐색·구간·다른 사건/세션·분리된 옛 player·가짜 ended·2배속·중간 구간 누락·다른 source 반례, origin/실행 식별값 확인을 포함한다. 이는 앱 알고리즘 검증 결과가 아니다.

브라우저, 서버, 빌드, 제품 API, 음성/영상 재생은 이번 준비에서 **0회 실행**했다. 제품 전체 흐름은 계획 6회 / 실행 0회 / 통과 0회 / 실패 0회 / NOT_RUN 6회다. 경계 검사는 계획 15개 / 실행 0개다. 유료 호출도 0회다.

검사기 SHA-256: `b64bf8e028f187829acdca3f243e37e382996b4f6e99e45cd4ca4c14d19a845e`.

## 실행 입력과 격리

실제 실행은 부모의 `q2-run.py`가 준비·검증한 최종 production 산출물에만 허용한다. 검사기에서 git checkout, build, 설치, 서버 기동 또는 배포는 하지 않는다.

| 입력 | 의미 |
| --- | --- |
| `PC4_UI_BASE`, `PC4_API_BASE` | 정확히 동일한 `http://127.0.0.1:<지정 포트>` origin. 경로·자격정보·다른 localhost 포트 허용 안 함 |
| `PC4_UI_OUT` | 해당 실행만의 결과/화면 디렉터리 |
| `PC4_Q2_FINAL_SHA` | 최종 통합 commit 40자리 |
| `PC4_Q2_RUN_IDENTITY` | JSON `{runNonce, finalSha, buildFingerprint}`. 각각 32/40/64자리 hex |
| `PC4_Q2_CAPABILITIES` | 최종 UI에서 확인한 selector JSON 파일 경로 |
| `E2E_CHROMIUM` | 설치된 Chromium 실행 파일 |

`/__pc4/status`의 실제 nonce/SHA/build가 입력과 일치하고 `ready=true`인지 브라우저 시작 전, 각 임시 원장 reset 전, 종료 후 확인한다. paid/external count는 음수가 아닌 정수여야 한다. 시작 시 두 count는 0이어야 하며 종료 시 비영 값은 실패다. 각 flow는 runner가 발행한 `store.store`를 기록한다.

브라우저 HTTP origin은 지정된 하나만 허용한다. HTTP relay는 실제 요청의 응답을 가져오되 자동 redirect를 0회로 설정하며 다른 origin Location을 거부한다. 요청, relay 응답, 브라우저 응답, redirect 정보와 분석 mode를 기록한다. 서비스 워커를 차단한다. Node의 원장/상태 조회는 `redirect: manual`로 redirect를 수락하지 않는다. 분석 POST는 `mode=replay`만 허용하며 실제 유료 분석은 runner의 NeverLive/외부 연결 차단 증거와 함께 판단한다.

`browser-offline-save-and-recovery`에서는 Chromium의 실제 offline 설정을 켜고 relay를 건너뛰어 브라우저가 네트워크 실패를 관측하도록 한다. 별도 API 단절 검사는 `/api/**`만 차단하므로 같은 origin 정적 UI를 잘못 차단하지 않는다.

실행 브라우저의 `browser.version()`을 `report.browserVersion`에 기록하며 console error와 pageerror는 결과에 보존한다.

## 6회 전체 흐름과 음성 관측

CASE-0001과 CASE-0002를 각각 3회 수행하며 **6회 모두 처음부터 끝까지 실제 1배속 자연 재생**한다. 빠른 반복용 끝 탐색은 제거했다. 긴 음성도 생략하지 않는다. 각 run은 새 임시 store로 시작한다.

실제 UI play control을 누르고 native `play`, `playing`, `ended`의 `isTrusted`, `currentSrc`, 선택 사건, 관측 세션, DOM 연결 여부, `currentTime`, `playbackRate`, seeking/seeked, 실제 경과 시간, native `played` 구간을 기록한다. 200ms 표본과 이벤트 기록을 남긴다. 시작 시각 0 근처, rate 1, 탐색 없음, 자연 ended, 99.5% 이상 구간 coverage, 전체 길이에 맞는 경과 시간을 모두 요구한다. 자연 완료 제어는 재생 전 disabled, 완료 후 enabled여야 한다. 양성 흐름에서 `currentTime` 변경, 인공 DOM event, API 직접 상태 업데이트는 없다.

각 흐름은 replay 분석 → 실제 WMS/TMS 원본 표시·근거 연결 → 상담원 편집·확인 → 편집 후 확인 해제/재확인 → 센터 전달 → 중간 회신과 남은 조치로 최종 완료 차단 → 조치 완료 → 센터 최종 회신·closed → 경영주 등록 회신 조회를 수행하도록 준비했다. 실제 HTTP의 revision/status/reply/pendingActions와 원문 보존, 선택 근거가 같은 사건의 원본 근거에 속하는지도 관측한다.

CASE-0002는 **각 3회 모두** 등록된 현재 사건 WMS CCTV 구간을 실제 UI로 열고 play를 누른다. fixture의 start/end, native play/playing·시간·rate·played coverage·source를 대조하며 구간 끝까지 1배속으로 재생해 정지해야 한다. 양성 영상 재생에서도 seek나 인공 이벤트를 쓰지 않는다. 구간 끝 screenshot, Escape 닫기, 실제 opener로 focus 복귀가 필수이며 영상 제어가 미통합이면 그 flow도 NOT_RUN이다.

## 최종 UI selector 인계

capability 값만으로 통과시키지 않는다. canonical selector가 실제 DOM의 단일 제어를 가리켜야 하며, 미제공 또는 미통합이면 NOT_RUN이다. `naturalCompletionControl`은 실제 완료 제약을 받는 버튼 등 enabled/disabled를 관측할 수 있는 제어여야 한다. 임의 안내 문구를 이 제어 대신 지정하면 안 된다.

| selector | 요구/용도 |
| --- | --- |
| `naturalCompletionControl` | 필수. 실제 PC2 전체 청취 완료 제어 |
| `audioPlayControl` | custom player일 때 필수. native visible controls면 실제 native play 클릭 사용 |
| `segmentControl` | 구간 청취 반례에 필수. 실제 구간 재생 제어 |
| `replayControl` | replay 분석 버튼. 기존 접근성 이름 유지 시 fallback 있음 |
| `requestTextarea`, `departmentSelect`, `reviewCheckbox` | 상담 편집·확인 제어. 기존 UI fallback 있음 |
| `wmsRegion`, `tmsRegion` | 실제 통합 scene 영역. 기존 LogisticsView fallback을 새 통합의 증거로 간주하지 않음 |
| `wmsRawSourceControl`, `tmsRawSourceControl` | 실제 원본 펼침 제어 |
| `wmsRawSourceText`, `tmsRawSourceText` | 펼친 원본 내용 |
| `wmsEvidenceLinkControl`, `tmsEvidenceLinkControl` | 실제 같은 사건 근거 연결 제어 |
| `wmsMediaOpenControl`, `mediaDialog`, `mediaVideo` | CASE-0002 매회 등록 CCTV 열기·dialog·native video 제어 |
| `mediaPlayControl` | custom video player일 때 필수. visible native controls면 실제 play 클릭 사용 |
| `differentToteNotice` | 서로 다른 업무 토트의 연속 추적 한계를 설명하는 실제 안내 |
| `futureActualValue` | 미래 실적 미채택 표시. 현재 TmsScene의 `[data-testid="tms-actual"]` fallback 있음 |
| `futurePlannedValue`, `futureGpsEntryValue`, `futureGpsExitValue` | 동일 미래 시각의 계획 허용·GPS 미채택 양성/반례 비교 |
| `animationPlayControl` | reduced-motion 적용 대상 TMS 설명 재생 버튼 |
| `tmsVisitList`, `tmsSelectedVisitHeading`, `tmsSelectedRow` | 실제 방문 버튼 목록·선택 상세 제목·현재 선택 표행 |
| `tmsPreviousControl`, `tmsNextControl` | 3폭별 실제 이전/다음 keyboard 탐색 제어 |

`segmentTimeoutMs`는 구간 재생 길이에 맞춰 지정할 수 있다(기본 30초). 일부 기존 화면의 접근성 이름/구조를 유지하는 locator가 남아 있으므로 최종 UI의 이름이 변경되면 해당 selector 인계 및 검사기 조정이 필요하다. 미확정 화면을 현행 제품 실패로 단정하지 않는다.

## 계획된 필수 경계 15개

모두 이번 준비에서는 **NOT_RUN**이다. 검사기 `PLANNED_BOUNDARIES`와 self-test stdout JSON이 동일 목록을 공개한다. 실행에 도달하지 못한 항목도 결과에 NOT_RUN 행을 채우며 빈 목록이나 일부 실행을 전체 통과로 집계하지 않는다.

| ID | 실제 실행 시 관측 범위 |
| --- | --- |
| `audio-end-seek-must-not-complete` | native play 뒤 끝 탐색으로 실제 ended가 발생해도 전체 완료 제어 거부. 양성 6회에 포함하지 않음 |
| `audio-segment-must-not-complete` | 실제 구간 제어 재생·정지 후 전체 완료 제어 거부 |
| `previous-case-native-ended-must-not-complete-current` | 사건 변경 뒤 옛 source의 native ended로 현재 사건 완료가 켜지지 않음. source 교체/cleanup 때문에 재현이 불가능하면 NOT_RUN; 인공 이벤트 대체 없음 |
| `new-text-different-day-no-implicit-evidence` | 다른 날 신규 텍스트 문의는 음성 player/STT 요청 없음, 명시 연결 없이 근거 없음, 실제 replay 409 표시. 유료 신규 분석은 실행하지 않음 |
| `explicit-reference-text-media-missing` | 명시 연결 신규 텍스트에도 복사되지 않은 미디어를 미등록으로 표시 |
| `media-404-and-retry` | 승인된 현재 사건 WMS 자산의 404 주입 → 안내/원본 유지 → 실제 영상 재시도 진전 → Escape 닫기 |
| `api-error-and-recovery-no-false-save` | 503 주입에서 저장 성공 오표시/원장 변경 없음, 장애 해제 후 UI 재시도 |
| `api-offline-example-and-reconnect` | API 단절 시 저장 불가 예시 모드, API 재연결 후 저장 가능 |
| `browser-offline-save-and-recovery` | 실제 browser offline/online에서 저장 실패·원장 보존·재시도 |
| `two-ui-editors-real-409-no-overwrite` | 두 UI의 동시 편집으로 실제 409, 최신 내용 덮어쓰기 없음 |
| `future-evidence-hidden-in-investigation-ui` | GET 응답에 조회 기준 +1시간 근거·계획·actual·GPS를 명시 주입. 미래 계획은 계획으로 유지하는 양성 대조, actual/GPS는 현재 실적 미채택, 근거 연결 차단(표시 자체를 무조건 숨기라는 뜻은 아님) |
| `different-business-totes-not-continuous-tracking` | 실제 CASE-0002의 서로 다른 피킹/출고 토트와 연속 추적 한계 문구 |
| `responsive-keyboard-reduced-motion-1365` | 1365px에서 5개 주 메뉴 keyboard Enter 전환, 실제 방문 선택·다음·이전·선택 표행 동기화·첫 방문 이전 disabled, 문서 가로 넘침, reduced motion, screenshot |
| `responsive-keyboard-reduced-motion-921` | 동일, 921px |
| `responsive-keyboard-reduced-motion-390` | 동일, 390px |

future 경계의 HTTP 응답 주입은 테스트 입력이며 원본 fixture나 저장 원장을 바꾸지 않는다. 토트 검사는 업무 식별자/안내 확인 범위이며 영상 속 동일 물체의 연속 추적 증명이 아니다. 접근성 검사는 실제 주 메뉴·방문·이전/다음의 focus+Enter와 motion/폭 검사이며 스크린리더, 전체 Tab 순서, 색 대비, 사람 육안 검토를 완료했다는 뜻이 아니다. 3폭 항목의 방문 제어 또는 미래 경계의 필드 중 하나라도 미확정이면 부분 검사만으로 PASS하지 않고 해당 항목 전체를 NOT_RUN으로 처리한다.

## 집계와 남은 사항

- `PASS`: 6회 모두 실제 완주, 모든 계획 경계 PASS, setup 오류/유료 시도/외부 접근/pageerror 없음, runner 식별값 확인.
- `FAIL`: 실행한 제품 반례가 허용되거나 UI/API 기대값 실패, 비용/외부 연결/실제 pageerror 발생. 반례의 거부는 기대 결과이므로 해당 경계 PASS다.
- `NOT_RUN`: 최종 입력·통합·selector 없음, 환경/실행 식별값 문제, 재현 불가능한 callback, 실행하지 못한 항목. setup만 실패한 경우 제품 실행 분모는 0이다.
- 부모 runner는 flow의 `(caseId, repetition)` 6개 및 서로 다른 `store.store`, 동일 source/build, 원본 원장 보존, 전체 필수 경계와 비용/네트워크/프로세스 정리를 추가 검증한다.
- 기존 N04의 seek 반복 및 이전 모듈 실행 결과는 이 Q2의 성공 수에 포함하지 않는다. 최종 SHA/자산·표준 selector 도착 후 부모의 명시 실행 계약으로만 제품 검사를 시작한다.
