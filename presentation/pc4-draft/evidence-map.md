# N04-D1 발표 주장·화면·검증 근거 대응표

기준 문서 스냅샷은 main `e1ef36f174f9bf8f68d82a6fbc77eca77bf859cb`, pc4 증거 스냅샷은 `d7841717e8181d4f9315a20dee5099c073251019`입니다. [storyboard](storyboard.md)의 30/65/95/65/45초, 총 300초 계획에 대응합니다. 발표 시간은 계획이며 사람 리허설 실측은 아닙니다. 이 문서는 기존 자료의 읽기·대조 결과이고 새 제품 실행은 0회입니다.

## 제품과 증거 버전 구분

| 식별자 | 실제 대상·실행 시점 | 식별 근거와 미커밋 범위 |
|---|---|---|
| M-PROT | pc1 복구 구현 및 독립 검수의 production build, 20:52~21:03 | source `a519e346e7a097f00961441373e858a088d86bce119640531fecd10762441292`, output `65c40b09aa68ef178eca9d73847c68a92cf237910b65c9040b79c3ba1d2fe40a`. 해당 보고서는 최종 제품 Git SHA를 특정하지 않습니다. 실행 당시 파일·출력 해시가 기준이며, bfc8543은 수정 전 비교 기준입니다. 이를 최신 e1ef36f 전체 제품 검사로 소급하지 않습니다. |
| P4-Q2 | pc4 전체 흐름 검사, 제품 `bfc8543aa65316682948f2e3d5b77a3ee56b21ff` | source `0e80c944bd7a870d4228b355a54266a88b5d99bc7c9c72b1e3b6826cf6bccc47`, output `b769128ff1443dcd7bc361efa23d40709d411dba2aebfc6682d600c48d310f67`. 당시 tester HEAD d7ff5ee, 최종 실행 검사기 파일 SHA `0367a0a5…`이며 Git 커밋과 구분합니다. |
| P4-Q3 | pc4 저장 복구 검사, 제품 `c6f734f60d0dbe0151a69e35b8dfd8a41f3c5bd5` | source `4d6d0f6b9dc00b874efbb2549d7ffc5369cfdde62af86f3f36cd8d2b1764a9b8`, output `3d1be22730f4f84d1e7933099818f3ee6dd354b149774cdad4558fbe1623eab7`. 당시 tester HEAD ca00b2f에 미커밋 검사기를 사용했고 매 실행 전 11개 원본과 시작/종료 SHA를 보존했습니다. 공유 증거 커밋 d784171은 제품 SHA가 아닙니다. |
| M-GROUND | pc1 저장 원응답 정규화 수정·독립 재검 | 최종 `claim_grounding.py` SHA-256 `c98947e06f567560c2d89eb3f75561a9d6bf78e98e42bf774784f60e42b3243e`. 요청 근거화는 별도 `request_grounding.py` SHA-256 `7443589ba87c9083d0dbb6820b00bf77a36359e24bc820ecaa68978766615714`. 두 값은 파일 해시이며 Git 커밋이 아닙니다. |
| M-CARD | pc1 연결 근거 카드 Bolt, 18:03 | 배정 시작 HEAD 88ba3b1. 구현 후 최종 Git SHA는 보고서에 없으며 실행 전후 소유/의존 파일 해시 불변으로 보고했습니다. 당시 로컬 변경에 대한 결과를 최신 통합 제품의 독립 실행으로 바꾸지 않습니다. |
| M-CCTV | pc1 새 CCTV 컴포넌트 격리 구현·독립 순수 검사 | 배정 시작 de68b13. 수정 전 독립 대상 TSX SHA-256 `adacddee…`, 수정 후 `dafe4f74a6ba0816a7ed8061288f9a040ab86c54e737e398dba3b9a6dc6b2395`. 수정 후 브라우저 재검은 미실행입니다. |

## 5장 주장 대응

| 장·시간 | 발표 가능한 주장 | 보여줄 기존 화면·자료 | 대상 | 실행 주체 | 실제 분모 | 증거 경로 | 반드시 붙일 한계 |
|---|---|---|---|---|---|---|---|
| 1 · 30초 | 미도착·오출고의 문의부터 근거·센터 회신·경영주 확인까지 시제품 흐름을 구성했습니다. | 두 사례의 업무 흐름 도식, 실제 Goal 시작 기록 | 요구·Goal 기록과 M-PROT | pc1 | Goal 시작 17:22:02 KST; 제품 완료 분모와 구분 | [팀 프롬프트][M0], [실제 Goal 시작][M1] | 독립 합성 사례, 실제 WMS/TMS·배송 연동 아님. Goal 시작은 완료·공식 제출이 아님. |
| 2 · 65초 | 통화 전체 재생 후 기존 정제 결과·원문을 대조하고 사람이 확인하는 흐름을 검사했습니다. | [상담 작업대 1440px][S1]; 저장 결과·원문·사람 입력 구분 | M-PROT | pc1 독립 AI, 구현자와 분리하되 같은 PC | 음성 2유형×3회 **6/6**, 텍스트 **2/2** | [신뢰성 독립 인수][M3] | 1배속 전체 재생은 기술 검증. 사람 청취·명료도·이번 새 라이브 STT/GPT 검증이 아님. |
| 2 · Bolt 1 | 저장된 모델 응답에서 주문·수령·단위 귀속 오류를 좁혀 수정했습니다. | FIX-W04의 주문 근거 없는 수량/단위는 미확인, 수령 6 EA는 유지하는 전후 요약표 | M-GROUND | pc1 구현 담당 + 분리된 pc1 독립 검수 | **32건 중 4변경·28불변**, 자동 네 필드 **128/128**; 독립 G1~G5 **5/5**, 정상 **2/2**·부정/예정 **2/2** | [수정·실패 이력][B1], [최종 한정 인수][B2] | 새 모델 호출 **0**. 128/128은 storeId·quantity·unit·departmentId만이며 전체 의미·안전·AI 정확도 100%가 아님. 기존 라이브 116/120·64/72를 대체하지 않음. |
| 2 · 요청 보완 | 요청 원문과 인용을 대조하고 미확인은 사람에게 남깁니다. | 정상 요청/철회 반례와 남은 P2의 간단한 비교 | M-GROUND의 request 모듈 | pc1 독립 AI | 기존 **9/9**, 추가 **5/6**; 저장 응답 **36/36 일치** | [요청 근거화 최종 독립 검수][M4] | 공통어 때문에 별개 요청도 지우는 P2 과잉 철회가 남음. 204 passed / 178 subtests는 별도 회귀이며 9·6·36과 합산하지 않음. |
| 3 · 95초 | 같은 사건의 기록과 미확인을 확인한 뒤 센터가 회신하고 경영주가 조회합니다. | [미도착 TMS][S2], [오출고 WMS][S3], [최종 회신][S4] | M-PROT; 원격 근거는 별도 P4-Q2 | pc1 독립 AI / pc4 장준호·j324rst-svg를 구분 | pc1 업무 **6/6**. pc4 별도 업무 **6/6**, 경계 **15/15**, 음성 **6/6**, 영상 **3/3** | [pc1 인수][M3], [pc4 Q2][P2] | 서로 다른 빌드의 6회를 합쳐 최신 제품 12/12라 하지 않음. 기록 부재·합성 영상으로 미도착 원인·실물 인도·귀책을 확정하지 않음. |
| 3 · Bolt 2 | 근거 ID만 보던 작업대에서 내용·출처·시각·미확인 상태를 바로 읽게 했습니다. | 기존 같은 접수의 카드 **0→2** 전후 자료. 원본 PNG는 pc1 로컬 전용 경로이므로 미확보 시 출처를 붙인 수치표로 설명 | M-CARD | pc1 구현 담당; 독립 7건도 같은 pc1 검토자 | 실제 API/UI **8/8**, 메모리 SSR 경계 **23/23**, 독립 코드 반례 **7/7** 각각 별도 | [연결 근거 카드 Bolt][B3] | 시간 절감·만족도·실제 사람 Silent Test 미측정. 당시 다른 화면 왕복의 폼 보존은 이 Bolt의 성과가 아님. |
| 3 · CCTV 범위 | 승인 합성 영상의 확인과 조사 UI를 구분해 개발했습니다. | 기존 승인 영상 캡처 또는 격리 컴포넌트 자료에 버전 표시 | M-CCTV | pc1 구현 담당 + 같은 pc1 독립 검수 | 수정 전 UI **64/64**; 수정 후 순수 함수 **14/14**, 구현자 변이 **1/1**; 독립 순수 **9/9**, 변이 **2/2** | [CCTV 구현][M5], [CCTV 독립][M6] | 수정본 브라우저 **0/1 NOT_RUN**. 임의 UI 좌표는 물체 추적 증거 아님. 승인 영상 960×540와 후보 좌표 1280×720 정합 미완료. |
| 4 · 제품 수정 근거 | 메뉴 왕복의 초안 상실과 저장 응답 유실을 보존·조회·대조로 복구하도록 수정했습니다. | [pc1 복구 비교 화면][S7], 수정 전/후 동작표 | M-PROT | pc1 구현 담당 및 같은 pc1 독립 검수 | 구현자 **54/54**, 별도 독립 복구·화면 **41/41** | [초안·저장 복구 구현][M2], [독립 인수][M3] | 두 분모를 합쳐 독립 95건이라 하지 않음. 메모리 초안이며 강제 종료 후 복원 불가. |
| 4 · 65초 | 실제 실패를 보존하고 검사기를 바로잡아 같은 제품으로 다시 검사했습니다. | Q3 시도 요약과 [503 뒤 원본 조회][S5], [저장 미확정·잔류 알림][S6] | P4-Q3 | 원격 pc4; 같은 pc4 보조 읽기 검토는 별도 원격 인수로 세지 않음 | **3/8 → 7/8 → 8/8**, 마지막 **297/297 관측**, 미실행 0 | [Q3 최종 보고][P3], [세 시도 원본 요약][P4] | 앞선 실패는 selector 등 검사기 오류. 제품 수정으로 고친 버그라 발표하지 않음. 별도 성공 토스트 잔류 P2 미완료. 297은 음성 6회가 아님. |
| 5 · 45초 | 검증한 범위와 남은 배포 조건을 함께 제시합니다. | 분모 요약과 [실패 복구 계획](failure-recovery.md), 배포 상태표 | M-PROT / P4-Q2 / P4-Q3 / 계정 상태 각각 | pc1 및 pc4 증거를 별도 표기 | 오프라인 읽기 전용 **1/1**, 전체 처리 **0/1 BLOCKED**. 21:03 계정 조회 연결 저장소 **0** | [pc1 인수][M3], [계정·배포 상태][M7] | 로그인·g-28 링크는 완료, Blob 생성403·영속 저장 연결·실배포 미완료. 계정 조회0을 팀 전체 저장소 부재로 확대하지 않음. |

## 발표 수치와 화면 사용 규칙

1. main e1ef36f와 증거 d784171은 문서 스냅샷입니다. 최신 제품 전체 통과 SHA로 말하지 않습니다. 본 D1 카드에서 제품·브라우저·서버 재실행은 없습니다.
2. 구현자 자체 검사, 같은 PC의 독립 AI, 원격 pc4 검사를 구별합니다. pc1 보고서의 같은 PC 보조 세션을 pc2/pc3/pc4 실행으로 계산하지 않습니다.
3. 54개 복구 검사·41개 독립 검사·6개 전체 흐름·297개 관측·pytest/subtests는 중복과 단위가 달라 합산하지 않습니다. 실패·미실행·skip을 통과 수에 넣지 않습니다.
4. pc4 Q2 1차 검사기 `31f1ffd2…`는 당시 해시·실행 증거가 있으나 별도 원본 백업 미확인 이력이 있습니다. Q3는 세 시도별 실제 원본 11개씩을 보존했습니다. 재구성본을 최초 원본으로 제출하지 않습니다.
5. 공개 링크는 private 저장소 접근 권한이 필요합니다. PDF에는 승인된 기존 합성 화면과 최소 요약만 사용하며 원응답·로그·키·토큰을 복사하지 않습니다. 표의 화면 경로는 기존 증거 위치이며 이번 카드의 새 캡처가 아닙니다.

## 고정 출처

[M0]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/e1ef36f174f9bf8f68d82a6fbc77eca77bf859cb/PROMPT_team.md
[M1]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/e1ef36f174f9bf8f68d82a6fbc77eca77bf859cb/reports/goal-start-20260921.md
[M2]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/e1ef36f174f9bf8f68d82a6fbc77eca77bf859cb/reports/prototype-resilience.md
[M3]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/e1ef36f174f9bf8f68d82a6fbc77eca77bf859cb/reports/prototype-independent-acceptance.md
[M4]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/e1ef36f174f9bf8f68d82a6fbc77eca77bf859cb/reports/request-grounding-final-independent.md
[M5]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/e1ef36f174f9bf8f68d82a6fbc77eca77bf859cb/reports/cctv-inspector.md
[M6]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/e1ef36f174f9bf8f68d82a6fbc77eca77bf859cb/reports/cctv-inspector-independent.md
[M7]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/e1ef36f174f9bf8f68d82a6fbc77eca77bf859cb/reports/deployment/account-auth-status.md
[B1]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/e1ef36f174f9bf8f68d82a6fbc77eca77bf859cb/reports/analysis-grounding-repair.md
[B2]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/e1ef36f174f9bf8f68d82a6fbc77eca77bf859cb/reports/analysis-grounding-final-independent.md
[B3]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/e1ef36f174f9bf8f68d82a6fbc77eca77bf859cb/reports/design/evidence-cards-bolt.md
[P2]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/d7841717e8181d4f9315a20dee5099c073251019/reports/pc4/q2-candidate-bfc8543.md
[P3]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/d7841717e8181d4f9315a20dee5099c073251019/reports/pc4/q3-c6f734f-results.md
[P4]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/d7841717e8181d4f9315a20dee5099c073251019/reports/pc4/q3-attempts-summary.json
[S1]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/e1ef36f174f9bf8f68d82a6fbc77eca77bf859cb/reports/e2e/prototype-independent-20260921-2102/desk-full-1440.png
[S2]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/e1ef36f174f9bf8f68d82a6fbc77eca77bf859cb/reports/e2e/rehearsal-2026-09-21T11-57-01-364Z/round1-missing-tms.png
[S3]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/e1ef36f174f9bf8f68d82a6fbc77eca77bf859cb/reports/e2e/rehearsal-2026-09-21T11-57-01-364Z/round1-wrong-wms.png
[S4]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/e1ef36f174f9bf8f68d82a6fbc77eca77bf859cb/reports/e2e/rehearsal-2026-09-21T11-57-01-364Z/round1-wrong-closed.png
[S5]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/d7841717e8181d4f9315a20dee5099c073251019/reports/pc4/q3-run-20260921T123023563161Z/Q3-06-06-unsaved-503-get200-is-not-success.png
[S6]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/d7841717e8181d4f9315a20dee5099c073251019/reports/pc4/q3-run-20260921T123023563161Z/Q3-08-q3-08-uncertain-390.png
[S7]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/e1ef36f174f9bf8f68d82a6fbc77eca77bf859cb/reports/e2e/prototype-independent-20260921-2102/recovery-390.png

## v3 미디어와 실제 삽입 화면

[M8]: https://github.com/cjj0202-glitch/happycall-ralphthon/blob/e1ef36f174f9bf8f68d82a6fbc77eca77bf859cb/reports/media/pc2-pause-adoption.md

M8은 pc2의 별도18/18 격리 재생과 pc1의27/27 증거 대조, v3 자산3/3·ASGI4/4를 구분합니다. CASE-0002에0.20초 쉼을 넣어49.55초에서49.75초로 바뀌었습니다. 새 부모 빌드 전체 흐름 완료는 이 자료 기준에서 미확인이고 사람 청취는0회입니다. 과거v2의6/6을 v3 최신 전체흐름 통과로 쓰지 않습니다.

PDF에 실제 삽입한 원본은 assets/manifest.json의3개뿐입니다. 상담 작업대는 정제 실행 전·미저장 초안, TMS는 선택 방문 영역, Q3는 미확정/P2알림 영역을 **기존 화면 일부**로 표시합니다. 픽셀 범위는 pdf-layout.json에 기록합니다. 원본 PNG는 바이트 그대로 보존했고 캡션에 합성·실행주체·출력지문/제품SHA를 붙였습니다. 다른 대응표 링크는 대본에서 참조하는 기존 증거이며 모두 PDF에 삽입한 것은 아닙니다.
