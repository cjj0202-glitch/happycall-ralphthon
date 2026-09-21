# N04-Q2 · 최종 통합 릴리스 교차검증 계획

작성: 2026-09-21 20:02 KST · pc4 장준호 / j324rst-svg · 메인 배정 #10 댓글 `5759287396`.

**현재는 준비이며 최종 검증을 실행하지 않았습니다. 최종 통합 SHA 미수신, 핵심 실행 0/6·PASS 0·FAIL 0·NOT_RUN 6입니다. 경계 검사도 예정 15건 전부 NOT_RUN입니다.** 과거 모듈 검사·기존 셸의 6/6·검사기 자체 테스트를 이 분모에 합산하지 않습니다.

읽기 기준은 `e5469aa99bb266c5a977b80c097223275ac6fc9b`의 `docs/28_PC_업무배정_기준.md`, `planning/media/production-quality.md`, `synthetic-center-scene.md`, `scene-layout-v1.json`, `reports/rehearsal.md`입니다. 이 SHA는 준비 참고이며 최종 검증 대상으로 지정된 SHA가 아닙니다. 실제 구현 계약은 전달받은 최종 소스에서 다시 대조합니다.

## 사용자 결과·설계

상담원이 두 합성 문의의 통화를 끝까지 재생하고 저장된 분석·원문·사람 수정을 구분하며, 동일 사건의 WMS/TMS 근거를 확인·연결한 후 센터 이관과 최종 회신을 저장하고 경영주 화면에서 다시 조회할 수 있는지 검사합니다. 설명용 이동·합성 영상·시스템 등록을 실제 상품 인도나 귀책의 증거로 확대하지 않습니다.

| BMAD 관점 | 이번 검증 판단 |
|---|---|
| 업무 | 접수부터 센터 최종 회신·경영주 조회까지 실제 저장된 결과인가 |
| UX | 진행/미등록/오류/다음 행동, 선택 사건·방문·표행, 좁은 화면·키보드 동선이 일치하는가 |
| 구조·계약 | 같은 SHA·빌드·자산, 사건/시각/관계키, revision·role·미완료 조치 조건을 보존하는가 |
| 검증 | 양성·반례·복구를 분리해 HTTP·UI·재조회와 실행 분모로 입증하는가 |

작은 Bolt 가설은 **화면의 완료 표시가 실제 전체 재생·저장·등록 근거와 일치해야 사용자가 잘못된 확신 없이 다음 단계로 이동할 수 있다**입니다. 불일치 한 건을 재현하면 소유자가 핵심 변경 하나를 적용한 새 SHA를 받고 같은 입력·조건으로 재시험합니다. 수정 전후 증거를 보존하며 서로 다른 SHA의 성공을 합쳐 한 릴리스 6/6을 만들지 않습니다. AI Playwright 기술 관측이며 사람 청취·Silent Test·만족도 측정은 아닙니다.

Grill-me 잔여 입력은 아래 최종 릴리스 계약입니다. 이미 승인된 두 유형·역할·replay 검증을 다시 질문하지 않습니다.

## 메인에게 필요한 최종 입력과 실행 게이트

1. **정확한 최종 main SHA** 및 통합된 CallReview/WmsScene/TmsScene 경로·기능 목록. 분기 이름/현재 최신이라는 표현만으로 실행하지 않습니다.
2. **승인 자산 manifest**와 사례별 실제 파일 경로·SHA-256·byte 크기·음성 길이·영상 구간·case/event/camera/occurredAt. 실행기에서 내려받거나 유사 파일로 대체하지 않습니다.
3. **실제 통합 DOM 선택자 계약**: 전체 통화 완료 게이트, 구간 재생, replay, WMS/TMS 영역·원본행·근거 연결, 접수 입력/확인, TMS 선택방문·표행·이전/다음·애니메이션, 서로 다른 토트 연속성 제한, 영상 오류/재시도/닫기. 선택자가 없으면 제품 클릭을 수행한 것으로 간주하지 않습니다.
4. **생산 빌드 계약**: clean 별도 checkout의 finalSha, fixture/manifest/전체 추적 제품 입력 해시(웹 바깥 JSON import 포함), frontend source/output fingerprint, 성공한 빌드 기록. 실행기 버전·해시도 고정합니다.
5. **격리 실행 주소/기능 계약**: 전용 loopback UI와 동일 출처 API, 무과금 replay, 임시 상담 저장소, 실제 저장 API·오류코드. 기존 상담·예산 원장·키·운영 프로세스를 재사용하거나 변경하지 않습니다.

`q2-run.py` 기본 또는 `--prepare-only`는 준비 결과만 만듭니다. `q2-build.py`는 명시한 `--product-root`와 `--final-sha`의 별도 clean checkout에서 생산 빌드·전체 제품 입력 해시를 기록합니다. `q2_contract.py`의 artifact gate를 통과한 뒤에만 `q2-run.py --execute`가 실제 제품을 실행합니다. 게이트 실패는 NOT_RUN/BLOCKED이며 테스트 통과가 아닙니다. 이 문서 작성 과정에서는 위 명령으로 제품을 실행하지 않았습니다.

## 핵심 분모 6 — 같은 릴리스의 두 사례 각 3회

| 실행 ID | 고정 입력 | 기대 결과 | 현재 |
|---|---|---|---|
| CASE-0001-1 | SYN-ST01 · 미도착 · 승인 음성 · replay · delivery | 아래 공통 단계 전부 저장·재조회, 실적 null/실제 인도 미확인 보존 | NOT_RUN |
| CASE-0001-2 | 같은 사례·빌드·자산, 새 격리 상태 | 같은 완료 기준 | NOT_RUN |
| CASE-0001-3 | 같은 사례·빌드·자산, 새 격리 상태 | 같은 완료 기준 | NOT_RUN |
| CASE-0002-1 | SYN-ST02 · 오출고 · 승인 음성 · replay · warehouse | 아래 공통 단계 전부 저장·재조회, 주문 18 EA/수령 진술 1 BOX 분리 | NOT_RUN |
| CASE-0002-2 | 같은 사례·빌드·자산, 새 격리 상태 | 같은 완료 기준 | NOT_RUN |
| CASE-0002-3 | 같은 사례·빌드·자산, 새 격리 상태 | 같은 완료 기준 | NOT_RUN |

각 회차의 필수 단계:

1. native 재생 조작으로 **0초부터 1배속 전체 음성 자연 종료**. actual duration·wall time·played 구간·ratechange/seeking/ended/error를 관측합니다. 끝 seek·부분 구간·임의 ended 이벤트는 완주로 세지 않습니다. 실제 CallReview 완료 게이트가 종료 전 잠기고 종료 후 열리는지 대조합니다.
2. UI에서 명시적 replay 분석 → 원문/저장된 AI 제안/사람 입력 구분. 실제 STT·GPT 요청은 0건입니다. replay를 실제 전사 성공이라고 쓰지 않습니다.
3. WMS/TMS 각각 원본행을 열고 같은 사건의 근거를 UI로 연결 → HTTP 성공·selectedEvidence·GET을 대조합니다. CASE2의 승인 CCTV는 event/camera/시각/구간·합성 문구·닫기/포커스 복귀를 확인합니다. CASE1/TMS의 미등록 영상은 다른 영상으로 대체하지 않습니다.
4. 접수 편집 → 확인 체크 → 재편집 시 확인 해제·이관 차단 → 다시 확인·UI 이관. 원문은 불변이고 저장 요청의 expectedRevision이 실제 편집 버전과 일치해야 합니다.
5. 센터 중간 회신+남은 조치 저장 → 종결 차단/in_progress 유지 → 조치 완료+최종 회신 저장 → 경영주 조회 → 새로고침/GET에서 closed·회신·조치 없음·센터 등록 주체 확인.

한 단계라도 실패/미실행이면 해당 회차는 PASS가 아닙니다. UI 저장 실패를 직접 API 쓰기로 대신하지 않습니다. API 읽기는 상태 대조에, 거부 요청은 별도 반례에만 사용합니다. 핵심 흐름의 수정 확인 해제·미완료 종결 검사를 별도 성공 건수로 더하지 않습니다.

## 별도 경계 분모 15 — 전부 현재 NOT_RUN

다음 ID는 준비 중인 `flow-ui-check.mjs`의 `PLANNED_BOUNDARIES`와 맞춥니다. 표의 세부 조건 중 한 항목이라도 구현/선택자/자산이 없으면 해당 묶음은 NOT_RUN 또는 FAIL 사유를 남깁니다. 검사 계획이 실행 증거를 대신하지 않습니다.

| ID | 입력·실행 방법 | 기대값·실측할 증거 |
|---|---|---|
| audio-end-seek-must-not-complete | 재생 직후 끝 근처 seek하여 native ended 발생 | 전체 통화 완료 게이트 비활성, 재생 관측은 불완전. 핵심 6회에 합산 금지 |
| audio-segment-must-not-complete | 실제 구간 재생 버튼으로 일부만 재생·정지 | 구간만 재생되며 전체 청취/완료로 바뀌지 않음. 구간·played·게이트 상태 |
| previous-case-native-ended-must-not-complete-current | CASE1 재생 중 CASE2 선택, 이전 미디어의 지연 종료/콜백 관측 | CASE2 완료·자막·연결 상태에 영향 없음. 실제 이전 객체 경로가 없으면 미실행 |
| new-text-different-day-no-implicit-evidence | 같은 점포명이나 다른 날짜의 텍스트, referenceCaseId 없이 UI 접수 | STT 요청 0, 원문 보존, 근거 자동 연결 없음. 요청·신규 사건 GET |
| explicit-reference-text-media-missing | 실제 UI로 동일 점포/유형/문의대상과 명시 reference 선택 | STT 요청 0, 명시 연결 근거만 허용. INT 사건 미등록 미디어는 다른 영상으로 대체하지 않음. 신규 replay 409는 표시·상태 불변 |
| media-404-and-retry | 승인 영상 URL에 404 주입 후 해제·실제 재시도 | 인라인 실패/복구, 거짓 재생 성공 없음. 등록 구간 재생·닫기/포커스·영상 밖 대체 금지 |
| api-error-and-recovery-no-false-save | 실제 UI 저장 경로에 503·느린 실패 후 복구 | 성공 문구/연결됨/저장 revision 증가 없음, 사용자 입력 보존, 복구 후 UI 저장·GET 일치 |
| api-offline-example-and-reconnect | API 단절, 정적 UI 접근 유지 후 연결 복구 | 예시/읽기 모드 표시·쓰기 차단, 복구 후 실제 저장 확인. 오프라인 전체 완주와 구분 |
| browser-offline-save-and-recovery | 브라우저 네트워크 offline 중 저장, online 복구 | offline 오류·거짓 성공 없음·입력 보존. 원장 재초기화 없이 연결 복구 |
| two-ui-editors-real-409-no-overwrite | 같은 사건을 두 실제 UI 편집기에서 열고 A 저장 후 낡은 B 저장 | 실제 409·B 입력 보존·A 값 유실 0. 응답과 GET, 새 버전 확인 없이 재시도 금지 |
| future-evidence-hidden-in-investigation-ui | 읽기 응답에 asOf 이후 실적/근거 주입; 미래 계획은 별도 양성 입력 | 미래 **실적·근거**를 확인된/선택 가능한 근거로 채택하지 않음. 미래 **계획**은 예정으로 표시 가능. null/실자정/시간대·날짜 경계 구분, 저장 원본 불변 |
| different-business-totes-not-continuous-tracking | CASE2 피킹 토트A/출고 토트B, 다른 사건·날짜·토트·카메라/구간의 후보 | 업무 토트와 SYN-VIS 객체를 구분, 연속 추적·귀책 미확인. 관계 불일치 차단, WMS 영상을 TMS로 재사용하지 않음 |
| responsive-keyboard-reduced-motion-1365 | 1365px·5뷰·Tab/Enter·reduced-motion, TMS 방문/표 선택·이전다음 | 문서 가로 넘침/가림 없음, 선택 방문=선택 표행, 경계 버튼 잠금, 문의점포 복귀, 모션 정지·TMS영상 미등록 |
| responsive-keyboard-reduced-motion-921 | 같은 입력 921px | 같은 기준, 표 내부 스크롤은 허용·문서 전체 넘침 금지 |
| responsive-keyboard-reduced-motion-390 | 같은 입력 390px | 같은 기준, 실제 포커스·터치 버튼·정보 읽기 순서 보존 |

추가 텍스트 실행은 핵심 음성 6회 분모 밖입니다. 경계 묶음의 여러 assertion을 별도 완주 수로 세지 않습니다. 15개 ID의 PASS/FAIL/NOT_RUN을 모두 보고하고 누락 ID를 삭제해 분모를 줄이지 않습니다. 전체 오프라인 저장 흐름은 현행 기능·검사가 없으면 **0/1 NOT_RUN 또는 BLOCKED**로 따로 남기며, 안전한 저장 차단 PASS와 바꾸어 쓰지 않습니다. 기존 20입력·12경계 모델 평가를 이 15개 UI 경계로 대체하지 않습니다.

## 증거·인수·중단

- 실행 시작/종료 KST·UTC, finalSha, 전체 제품 입력/빌드/자산/실행기 해시, 브라우저·Node·Python, run identity와 실제 로드 주소를 기록합니다. 검사 중 입력이 변하면 해당 실행을 최종 고정 릴리스 판정에서 제외합니다.
- 회차별 단계/기대/실측, 음성 자연재생 관측, HTTP 상태·역할·revision, 최종 GET, 스크린샷·콘솔/pageerror·네트워크 오류를 보존합니다. 404/503 같은 의도한 주입과 정상 흐름 오류를 구분합니다. 오류를 숨기지 않습니다.
- 외부 요청·live/유료 analyzer 호출 0. 원천자료·키·원본 로그·원장·기존 상담 상태를 읽거나 공유하지 않고 격리 입력만 사용합니다. 제품 소유 파일 수정·배포·commit/push는 이 계획 작업의 범위가 아닙니다.
- 최종 SHA/자산/선택자 부재, artifact gate 실패, 소유 충돌·권한 거부 시 의존 실행만 중단하고 정확한 NOT_RUN 사유를 같은 #10에 인계합니다. P0/P1은 재현→소유자 수정→동일 조건 재검 후에만 메인이 인수합니다.

**이 파일의 완료 범위는 준비 계획 한 건입니다. 최종 생산 빌드·전체 음성 재생·6회 업무 흐름·15개 UI 경계를 실행한 보고가 아닙니다.**
