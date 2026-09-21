# N02-M2: 후보 전체 재생·타임라인 검증 결과

pc2 / 안영일 / MR-A83. [메인 검증 카드](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/8#issuecomment-5760122054)를 2026-09-21 21:02 KST에 수신했다. 제품 기준은 `bfc8543aa65316682948f2e3d5b77a3ee56b21ff`, 입력 후보는 `309867bf0930d9c20deee12023125c91cf6e8f6a`이다. 결과 커밋과 실제 전달 시각은 같은 이슈 회신으로 확인한다.

**실제 Edge 재생·화면 검사 18/18 PASS, 정수 타임라인 반례 4/4 PASS.** 실행은 21:10:13~21:12:57 KST였다. 승인 v2와 후보를 같은 브라우저에서 비교했으며 제품·공용 fixture·manifest·API는 변경하지 않았다. 사람 청취는 0회다.

## 입력과 재현

설계와 허용값은 실행 전 [playback-plan.md](playback-plan.md)에 고정했다. [playback-manifest.json](playback-manifest.json)은 기준 커밋의 실제 컴포넌트·CSS·fixture Git blob SHA, 두 자산 SHA/길이, 원본과 후보의 8개 발화 시각·텍스트·화자·PCM SHA를 담는다. 테스트용 사본만 `.local/pc2-m2-playback/product`에 생성한다. 기존 작업 브랜치의 이전 컴포넌트로 메인의 새 코드를 덮지 않는다.

환경: Windows 11, Node v24.21.0, Playwright 1.58.2, Edge 153.0.4234.48 headless. 이미 설치된 도구만 사용했다. 저장소 루트에서 실행:

```powershell
python scripts/media_pc2/prepare_playback.py
python -m unittest discover -s scripts/media_pc2 -p test_playback_timeline.py -v
node --check tests/remote/pc2/m2/build.mjs
node --check tests/remote/pc2/m2/run.mjs
node tests/remote/pc2/m2/run.mjs
```

재현 전 필요한 로컬 입력은 승인 v2 `apps/web/public/demo/CASE-0002.wav`, 기존 후보 `.local/pc2-n02-m2-pause-v1-recheck/CASE-0002-pause020-v1.wav`, 승인 원발화 manifest `.local/pc2-voice-sources-20260921/demo-voice-sources-20260921.manifest.json`이다. `candidate.json`과 자산 SHA/크기를 대조하고 불일치하면 중단한다. 후보 WAV는 [기존 Release](https://github.com/cjj0202-glitch/happycall-ralphthon/releases/tag/demo-media-20260921-pc2-pause020-v1)의 같은 이름 자산이다. 새 음성 생성·다운로드·업로드·유료 호출은 이번 실행에서 0회였다.

## 기대값과 실제 결과

| 항목 | 사전 기대값 | 실측 |
|---|---|---|
| A 전체 | 49.55초, 1배속, trusted ended 1, 완료 1 | duration/currentTime 49.55, played 0~49.55, 벽시계 50.934초, ended/완료 각 1 |
| B 전체 | 49.75초, 1배속, trusted ended 1, 완료 1 | duration/currentTime 49.75, played 0~49.75, 벽시계 49.983초, ended/완료 각 1 |
| B 발화 8개 | 시작 오차 ≤80ms, 종료 커서 ≤2ms, 실제 played 초과 ≤120ms | 시작/최종 커서 오차 0, played 초과 최대 17.641ms, 8/8 정지 |
| 다음 발화 | 다음 생성 구간 시작 침범 0, 구간으로 전체완료 0 | 0/0, 최종 발화도 음원 끝 전 정지 |
| 완료 상태 | A↔B 전환 시 초기화, 중복 시작·정지·끝 seek로 완료 금지 | 모두 충족, 끝 seek 후 실제 ended여도 완료 콜백 0 |
| 오래된 이벤트·잠금 | 이전 audio ended/error 무효, disabled 즉시 정지 | 콜백 0, 현재 음원 오류 0, 잠금 시 정지·버튼 비활성 |
| 1440/1024/390px | 수평 넘침 0, 실제 화자·대화 8개 | 각 0px, 8개 표시, 화면 3개 직접 열람 |
| 키보드 | 원문 접기 Enter/Space, 배속 방향키, 음소거 Space | 세 너비 모두 통과, 배속 1→1.25→1 확인 |
| 보호 경계 | 페이지 예외·외부/API 요청·제품 소스 변경 0 | 각각 0, 로컬 GET 40건, 보호 파일 5개 SHA 불변 |

전체 재생은 실제 HTMLMediaElement가 WAV를 디코딩하고 1배속으로 처음부터 자연 종료한 결과다. 빠른 seek나 합성 ended 이벤트로 전체 재생 성공을 만들지 않았다. 오래된 이벤트 검사는 별도 반례이며 그 성공을 실제 재생으로 계산하지 않았다. 브라우저 음원 재생은 OS 스피커 출력이나 사람이 이해했다는 증거가 아니다.

## 시각표와 샘플 보존

24,000Hz 정수 프레임 417,000에 무음 4,800프레임을 넣은 후보다. 삽입 이전 1~3번 발화는 유지하고 4~8번 발화의 양끝만 0.20초 이동했다. 아래 단위는 초다. 화자와 전체 문장은 manifest에 있으며 바뀌지 않았다.

| 발화 | 화자 | A 시작~끝 | B 시작~끝 | 실제 played 초과 |
|---|---|---|---|---|
| 1 | 상담원 | 0~4.30 | 0~4.30 | 8.935ms |
| 2 | 경영주 | 4.65~12.20 | 4.65~12.20 | 2.127ms |
| 3 | 상담원 | 12.55~17.20 | 12.55~17.20 | 13.427ms |
| 4 | 경영주 | 17.55~23.10 | 17.75~23.30 | 17.641ms |
| 5 | 상담원 | 23.45~29.60 | 23.65~29.80 | 15.974ms |
| 6 | 경영주 | 29.95~36.35 | 30.15~36.55 | 4.989ms |
| 7 | 상담원 | 36.70~44.05 | 36.90~44.25 | 2.280ms |
| 8 | 경영주 | 44.40~49.20 | 44.60~49.40 | 15.079ms |

8개 대응 구간의 실제 PCM을 바이트 대조해 동일함을 확인했다. 추가 무음을 제거하면 전체 A PCM도 복원된다. 시각은 승인된 합성 생성 구간에 근거하며 STT/단어 정렬 시각이 아니다. 서로 다른 화자 음색이나 발음의 사람 식별 정확도는 평가하지 않았다.

## 화면·오류·증거

원시 [results.json](playback-2026-09-21T12-10-13-303Z/results.json)은 모든 기대/실측·media 이벤트·played 범위·요청·환경·소스 SHA·종료 결과를 보존한다. [1440](playback-2026-09-21T12-10-13-303Z/layout-1440.png), [1024](playback-2026-09-21T12-10-13-303Z/layout-1024.png), [390](playback-2026-09-21T12-10-13-303Z/layout-390.png) 화면을 직접 열람했다. 넓은 화면에서는 재생과 접수가 나란히, 모바일에서는 재생→분석 관측 버튼→접수→접힌 원문/대화록 순서다. 텍스트는 줄바꿈되고 조작 요소와 8개 발화가 잘리지 않았다. 자동 포커스 지정 후 Enter/Space/방향키를 검사했으며 전체 Tab 순서나 스크린리더 사용성까지 검증했다는 뜻은 아니다.

21:07 첫 `node --check build.mjs`에서 module.rules 닫힘 괄호 누락으로 SyntaxError가 발생했다. 브라우저 실행 전에 수정하고 동일 구문 검사에 통과했다. 이 초기 실패는 원시 결과의 priorSetupFailures에 남겼다. 실제 브라우저 검사 실패는 0이며 제품 수정은 필요하지 않았다.

증거 패키징 중 Git의 CRLF→LF 변환으로 실행 당시 manifest SHA와 index SHA가 달라지는 것을 발견했다. 이 manifest만 바이트 보존 속성을 적용하고 명시 경로를 재정규화해 일치를 재확인했다. 원시 결과는 수정하지 않았다. `playback-evidence.json`은 각 파일의 실제 로컬 SHA와 Git blob SHA를 구분하며, 나머지 차이는 줄바꿈뿐임을 대조했다.

브라우저 1개/context 1개/page 1개, 제어는 Playwright pipe다. HTTP는 `127.0.0.1:51995`만 수신했고 검사가 끝난 후 context/browser/server 모두 close 완료, browserDisconnected=true였다. BrowserServer·재설치·보안 설정 변경·추가 보조 에이전트는 0이다. 사용자 접근 팝업의 기존 직접 원인과 재발 여부는 이 검사만으로 확정하지 않는다.

## pc1 연결 제안과 남은 판단

1. 기존 승인 v2를 유지한다. 후보 채택 시에만 pc1이 B Release 자산의 크기·SHA를 다시 대조해 별도 URL을 정한다. 컴포넌트 자체를 이 보고서로 교체할 필요는 없다.
2. B의 `audioUrl`, manifest `cases.B.transcript` 및 `transcriptTiming`을 한 단위로 연결한다. 후보 SHA·생성 경계 출처·삽입 프레임을 같이 남긴다. A의 옛 타임라인과 B 음원을 섞지 않는다.
3. 부모 완료 플래그를 사건 id와 음원 URL 변경에 함께 초기화한다. 독립 하네스가 이 계약을 실측했다. 분석 준비 버튼은 관측용이며 실제 부모 page/API 연결은 pc1 인수 검사 대상이다.
4. 사람 청취 0, 실제 부모 전체 서비스에서 후보 사용 0, 새 ASR/유료 호출 0이다. 메인의 기존 A/B ASR 관측은 메인 보고로만 유지한다. 명료도 우월성·음색 만족도·B 정본 채택·최종 인수·TEST 왕복은 완료 처리하지 않았다.

이번 결과는 맡긴 사용자 결과와 사전 수용 기준, 실패 수정, 실제 재검 증거를 연결한다. 공식 배점 확보나 별도 Goal 실행을 주장하지 않는다.
