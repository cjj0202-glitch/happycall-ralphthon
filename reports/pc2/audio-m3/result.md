# N02-M3 실제 상담 작업대 검수 결과

pc2 / 안영일 / MR-A83. [M3 카드](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/8#issuecomment-5760570765)를 2026-09-21 21:37 KST에 수신했다. 제품 기준은 `92d2ecbad981f366a9e5ffc850d9c2bb7fd5d3a2`, 음원은 `demo-media-20260921-audio-v3`이다. 결과 커밋·실제 전달 시각은 같은 이슈 회신에서 확인한다.

**최종 실제 부모 화면·replay API 검사 14/14 PASS.** 실행 21:51:32~21:53:25 KST, 정상 서버 종료까지21:53:28. 첫 실행10/14의 검사기 실패와 서버 정리 실패도 별도 보존했다. 제품 수정은0이다. M2의18/18이나 pc4 전체 흐름과 합산하지 않았다.

## 제품과 실행 범위

기존 작업 브랜치와 v2 파일은 보존하고 `C:/Users/Administrator/Desktop/hackerton/.local/pc2-m3-product`에 고정 커밋의 detached clean checkout을 만들었다. 새 public 폴더에 정식 fetch를 실행한 뒤 `--verify-only`3/3을 확인했다. 별도 Next production export를 실제 빌드했다.

- build source fingerprint: `8198a3dceb74ebd3952a2b8540cd961c73f57060f83deb0ca6e9ec3bcfd2af7d`
- build output fingerprint: `cb90493da4b397022185a770d9943d7869a1cf4a70f639007b080e0879f32497`, 출력26파일
- CASE1 SHA: `d4eeb6448ff8969f27034ecade9a050ee212468585c6300b19c9a0ebdc372931`, 2,263,278B
- CASE2 SHA: `6fe83afb8552765ab92722b838d2a0905f507551c4f98c58fa62a515033abaa0`, 2,388,044B
- 영상 SHA: `e6cad3cf9f999b596a0fef3e3d463170e0d279568a31a4be49366e5383908881`, 1,097,133B

실제 page/DeploymentRouter/OpenAPI handlers/CaseService를 사용했다. 검사용으로 바꾼 경계는 새 합성 JSON 저장소, 키·live 분석을 거부하는 analyzer, 외부 연결 차단이다. 정상 분석 응답은 실제 서버의 replay 경로다. 503/404 및 동일id 음원URL 교체만 명시적으로 브라우저 응답 경계에 주입했다. API stub로 정상 성공 응답을 만들지 않았다.

Windows/Python3.12.14/Node24.21.0/기존Next15.5.25/Playwright1.58.2/Edge153.0.4234.48을 사용했다. 부족한 API 런타임42개는 제품 uv.lock 고정 버전·해시로 별도 로컬 경로에 설치했다. 기존 인터프리터 전역 패키지·감시기·보안 설정은 바꾸지 않았다. node_modules는 기존 설치를 연결했고 npm/브라우저 재설치는0이다. 런타임 패키지와 자산의 실제 수신은 `preparation.json`에 있다.

## 사전 기대값과 실측

실행 전 [plan.md](plan.md)에 기준을 적었다. 최종 분모는 정상4, 음원변경1, 완료반례2, 실패복구2, 화면/키보드3, 무결성2 =14다.

| 항목 | 기대 | 실제 |
|---|---|---|
| CASE1 전체 | 47.15초/1배속/처음부터 자연종료 | decoded47.15, played0~47.15, trusted ended1, 벽시계48.368초 |
| CASE2 전체 | 49.75초/1배속/처음부터 자연종료 | decoded49.75, played0~49.75, trusted ended1, 벽시계50.045초 |
| 실제 부모 분석 | 종료 전 비활성→종료 후 활성→replay POST | 정상POST2/HTTP200, 각 음원의 mode=replay, 필드5개·대화8개·질문2개씩 UI와 일치 |
| 원문/수량 | 원대본 불변, 미확인과 정정 유지 | CASE1 수량/단위 공란, CASE2 수령1BOX, 원문과 주문18EA/잘못 들은1EA의 구분 유지 |
| v3 시각 | CASE2 version query와4~8번 +0.20초 | SHA query 일치, 8개 시각표 일치 |
| 같은id 다른URL | 기존 완료 승계 금지 | 실제 목록 API의 URL만 교체 후 currentTime0/부모분석 비활성, 이전audio detached/paused |
| seek/구간 | 전체 완료로 처리 금지 | 끝seek 후 native ended여도 비활성, 마지막44.60~49.40 구간 정지 후 비활성 |
| 분석503 | 편집·질문·원문 보존 및 재시도 | 사람이 수정한 필드5개/질문/원문 동일, 실패 안내·재시도 버튼 확인 |
| 음원404 | 실제media오류 안내→다시불러오기 | error4/분석잠금→metadata49.75/error없음→실제재생0.109초 확인 |
| 1440/768/390px | 가로넘침0, 실제 조작/편집 접근 | 각0px, 원문Enter/Space·배속방향키·음소거Space·편집링크Enter+Tab 통과 |
| 오류/접근 | 예상밖 예외·외부/live 호출0 | pageerror0, 예상밖console0, 의도503/404콘솔2, 차단시도0, 유료/키/외부시도0 |
| 제품/종료 | 제품 불변, 자기 프로세스 종료 | 제품51파일 SHA불변·checkout clean, context/browser종료, host stopped=true/code0, 포트LISTEN0 |

전체 자연 재생은 seek나 가짜 ended로 대체하지 않았다. 실패주입 POST1은 실제 성공POST2와 별도다. 404 복구 후에는 재생 가능 여부만 확인했고 세 번째 자연 전체재생으로 세지 않았다. URL변경 시 합성 편집 버리기 확인 대화는 검사기가 수락하도록 설정돼 있으며 실제 사용자 데이터는 없다.

## 실패→검사기 수정→동일 조건 재검

첫 실행 `parent-2026-09-21T12-47-08-539Z`는 **10/14, exit1**이다. 제품의 두 자연재생과 부모활성은 통과했다. 나머지4건은 상품·문의 대상의 input/비교section 중복 선택2건, 요청사항 label 전체명에 의존한 fill 실패1건, 의도503 요청이 실행되지 않아 POST2≠3인 종속실패1건이다. 원본 checker/host/run 바이트, 결과JSON과 실패PNG를 그대로 남겼다.

수정은 검사기의 필드5개를 `#intake-editor` 내부 실제 input/textarea로 제한하고 각1개임을 검증한 것이다. 실제 분석 UI 경로에 다시 도달하려면 부모의 자연재생 게이트가 필요하므로 두 음원을 같은 조건으로 다시 완주했다. 제품이나 수용 기준은 바꾸지 않았다.

첫 helper에서는 Windows Proactor의 취소된 로컬 미디어 연결 콜백 예외와 종료8초 초과가 기록됐다. 자기 서버 PID31224만 종료했으며 이 이력을 정상종료로 바꾸지 않았다. helper에 로컬 Selector 이벤트루프 및 keep-alive1초/종료유예2초를 적용하고, 런처가 counts0/stopped=true/종료code0를 필수 판정하도록 보완했다. 두 번째 실행은 자기 서버 PID18100/127.0.0.1:63880이 정상 종료됐다. 이 로컬 연결 예외를 Wi-Fi 단절의 증거로 해석하지 않는다.

최종 helper 로그에는 선택 기능인 Swagger UI 미설치 안내가 남는다. 해당 문서 UI는 사용하지 않았으며 실제 /api 및 부모 페이지는 정상 검증했다. 추가 Swagger UI 설치로 검사 범위를 늘리지 않았다.

## 증거·재현

- 최종: `parent-2026-09-21T12-51-25-545Z/results.json`, `execution.json`, `server.json`, `build-stamp.json`, `source-checker.mjs`, `source-run.mjs`, `source-host.py`
- 첫 실패: `parent-2026-09-21T12-47-08-539Z/` 전체. 실패/재검의 검사기와 helper 원본이 각각 보존된다.
- 화면: 최종 `parent-layout-1440.png`, `parent-layout-768.png`, `parent-layout-390.png`. 총괄이 실제 열람했고 768/390은 원본 크기로 재열람했다. 넓은 화면은 재생/편집 나란히, 좁은 화면은 재생→분석→접수→원문/대화록으로 이어진다. 키보드 검사는 특정 조작과 편집 진입이며 스크린리더 전체 검사가 아니다.
- 같은pc2 보조 검사 담당이 결과·원본SHA·51파일불변·종료를 읽기 전용으로 독립 대조했다. 다른 물리PC 검증으로 세지 않는다.

원 저장소 루트에서 준비된 로컬 경로를 사용한다:

```powershell
. ..\enter-happycall.ps1
$env:M3_PYTHON = (Get-Command python).Source
$env:M3_PYTHON_DEPS = 'C:/Users/Administrator/Desktop/hackerton/.local/pc2-m3-python'
node tests/remote/pc2/m3/run.mjs C:/Users/Administrator/Desktop/hackerton/.local/pc2-m3-product
```

다른 PC에서는 검증한 로컬 경로로 바꾼다. clean92d2ecb의 `fetch_demo_media.py`/`--verify-only`, `build_deployment_bundle.py --build`가 선행돼야 한다. Python 부족 패키지는 `runtime-requirements.txt`의 고정 해시를 이용해 별도 경로에 준비한다. 새 브라우저·Next를 재설치할 필요가 없다.

## 한계와 인계

사람청취0, 실업무/유료STT·GPT0, 최종배포/실영속저장/전체6회 인수는 미실행이다. CASE1/2 부모replay와 명시반례의 기술 검수만 보고한다. M3 최종인수와 중앙 작업표·이슈 종결은 pc1이 한다. 공용 제품 소스 변경 제안이 필요한 결함은 이번 범위에서 발견하지 못했다.

21시대 로컬 `.local/shared-git-watch.json` 갱신 명령 한 건은 자동승인 정책의 `blocked by policy`로 거부됐다. 그 명령이나 다른 도구를 통한 대체 갱신을 재시도하지 않았다. 이미 승인돼 실행 중이던 검사를 완료했으며 이 별도 검수 증거를 보존했다. 해당 상태 파일이 이전 단계일 수 있으므로 실제 결과와 이슈 회신 시각을 우선 대조한다.
