# pc1 → pc4: N04-Q2 통합 후보 검증 실행

## 결과와 기준

pc4 / 장준호 / j324rst-svg의 준비 결과 d7ff5ee를 읽었습니다. 이제 제품 **bfc8543aa65316682948f2e3d5b77a3ee56b21ff**를 고정해 독립 검증을 실행해 주세요. 상담 동선 수정, 합성 16발화 구간 시각, 새 WMS/TMS 연결을 포함합니다. 이 SHA의 기능 후보 검증이며 최종 배포·향후 음질/Blender 자산까지 완료됐다는 뜻은 아닙니다.

메인 실측은 `reports/call-review-workflow.md`, `reports/media/transcript-timing.md`, `reports/e2e/rehearsal-2026-09-21T11-18-13-436Z/results.json`입니다. 새 빌드 6/6·텍스트2/2·안전오프라인1/1, 별도 발화16/16입니다. pc4 실적으로 옮기지 말고 원격 PC에서 독립 실행합니다.

## 입력과 파일 소유

계약 초안은 `reports/channel/N04-Q2-bfc8543-release-inputs.json`입니다. 이 문서/계약을 받는 main HEAD와 **검증할 제품 SHA bfc8543**은 다를 수 있습니다. 제품 checkout은 위 SHA로 고정하고 테스트 checkout은 pc4 브랜치를 유지합니다. 계약의 finalSha는 이번 고정 후보를 뜻합니다.

승인 자산은 Release `demo-media-20260921-audio-v2`의 WAV 2개와 sorter-demo.mp4입니다. 계약에 경로·종류·사례·바이트·SHA·길이를 넣었고 메인이 로컬 파일3/3, fixture/manifest2/2를 대조했습니다. 새 Blender 대표 이미지·기존 pc3 후보 영상을 대체 사용하지 않습니다. 영상 관계는 제품 fixture CASE-0002의 W-W3 / SYN-CAM-02 / 2026-09-18T02:33:00+09:00 / 0~12초가 정본입니다.

pc4의 소유는 `tests/remote/pc4/`, `reports/pc4/`와 기존 테스트 전용 .gitattributes 절입니다. 제품 소스/API/fixture/manifest/원장을 수정하지 않습니다. 기존 checkout의 변경을 보존하고 제품용 별도 clean checkout을 사용합니다.

## 빌드·실행 순서

1. 실제 pc4 저장소 `C:/Users/j324r/OneDrive/문서/ChatGPT/해커톤_D-Day/happycall-ralphthon`에서 원격을 fetch하고 위 제품 SHA의 별도 checkout을 만듭니다. 임의 reset/stash/기존 폴더 삭제는 하지 않습니다.
2. 승인 자산을 준비해 해시/크기를 대조합니다. 이미 있는 파일은 일치 여부를 먼저 확인하고 덮어쓰지 않습니다. PC4에 설치된 Node/npm/브라우저 경로를 사용합니다.
3. 테스트 checkout의 `q2-build.py --product-root <실제 제품 checkout> --final-sha bfc8543aa65316682948f2e3d5b77a3ee56b21ff`를 실행합니다.
4. 제품 `.local/pc4-q2-build.json`의 complete, HEAD/입력 불변을 확인한 뒤 **PC4 빌드의** frontendSourceFingerprint/outputFingerprint를 계약의 frontendSourceFingerprint/frontendOutputFingerprint에 넣습니다. 메인의 raw-byte 지문/Next build ID를 복사해 같은 값인 척하지 않습니다. 이후 PC4의 동일 빌드 하나로 전 회차를 수행합니다.
5. 아래 테스트 호환 부분을 고친 뒤 `q2-contract-selftest.py`, `flow-ui-check.mjs --self-test`, `q2-run.py --release-contract <로컬 계약> --prepare-only`, 이어 `--product-root <제품 checkout> --execute` 순서로 실행합니다. 실제 E2E_CHROMIUM과 비어 있는 18105 포트를 확인합니다.

## 실제 UI에 맞춰야 할 tester 어댑터

계약 JSON의 selector는 제품 소스와 메인 관측을 기준으로 제공했습니다. PC4에서도 실제 DOM의 유일성·가시성을 대조합니다. 누락은 NOT_RUN으로 보존하고 안전 기대값을 낮추지 않습니다.

- 발화 구간 검사 전에 `원문과 화자별 대화록 확인` summary를 사용자가 클릭해 펼칩니다. 상세 비교 문구도 `AI 제안과 현재 입력 상세 대조` summary를 펼친 뒤 검사합니다.
- WMS 영상은 **근거 PATCH 이후** `event-W-W3`를 클릭해야 `open-video`가 나타납니다. 다른 이벤트에 영상이 없는 것은 실패나 대체 사유가 아닙니다.
- 구형 `WMS 물류 확인` 영역과 CCTV 버튼을 새 `WMS 공정 확인` / `open-video`로 매핑합니다. 오류/재시도는 `영상 재생 차단` / `영상 응답 404` / `영상 다시 불러오기`입니다.
- VideoDialog는 승인 원본의 크기/SHA를 검증한 뒤 blob URL로 재생합니다. `currentSrc === /demo/sorter-demo.mp4`를 요구하면 잘못된 실패입니다. blob 바이트의 크기/SHA를 승인 자산과 대조하면서 동일 source·native played 범위·1배속·벽시계 조건은 유지합니다.
- audioPlayControl을 `처음부터 전체 통화 재생`에 지정하면 audio 노드가 교체됩니다. 기존 native audio controls 방식으로 실제 재생을 시작하고 현재 노드를 관측하세요.
- 기본 CASE1은 asOf07:00, E-M1은05:00이므로 허용됩니다. 04:30 경계 입력과 혼동해 첫 근거를 바꾸지 않습니다. 실제 enabled/PATCH/GET을 대조합니다.

## 기대값·인계·중단

기존 Q2의 새 저장소6개·사례별3회·전체음성 자연재생·UI 경계15개 분모를 유지합니다. 동일 소스/빌드/자산/검사기, 실제 HTTP 저장과 재조회, 거부·복구, 원래 상태 보존, 유료/외부 호출0을 확인합니다. 오프라인 안전 차단과 전체 오프라인 저장은 별도입니다.

첫 결과는 계약/빌드/선택자 준비 후 20~30분 이내를 목표로 하고, P0/P1이나 실행 차단은 즉시 같은 #10에 재현 입력·기대/실측으로 회신합니다. 준비 검사를 제품 PASS로 세지 않습니다. 검사기 수정/실패/재시험도 보존하고 결과 SHA·제품 SHA·source/output·보고 경로·미실행 범위를 인계합니다. 메인이 증거를 대조한 뒤 인수하며 현재 issue는 열어 둡니다.

403·정책 거부·소유 충돌은 우회하지 않습니다. 기존 서비스/다른 작업자의 프로세스·원장·키를 조작하지 않고, 허용된 격리 테스트 자원만 사용합니다.
