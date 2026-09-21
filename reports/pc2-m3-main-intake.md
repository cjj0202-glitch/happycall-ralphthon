# PC2 N02-M3 메인 독립 인수 검토

2026-09-21 KST. **고정 제품의 API 기반 통화 replay 기술 검수 결과는 수용합니다. 최신 제품 전체·오프라인 예시·음성 자연스러움·최종 배포 통과로 확대하는 해석은 수용하지 않습니다.** 제품 변경·커밋·편지 발송 없이 로컬 Git 원본과 검사기만 검토했습니다.

- 결과 커밋: `d65a798b62395a1ec1ad6c02e118f2dc9a2f9409`
- PC2 실행 제품: `92d2ecbad981f366a9e5ffc850d9c2bb7fd5d3a2`
- 원격 최종 실행: `parent-2026-09-21T12-51-25-545Z`, 21:51:32~21:53:25 KST. 원격 14/14 PASS, 실패0.
- 원격 첫 실행: `parent-2026-09-21T12-47-08-539Z`, 10/14 PASS, 실패4. 보존 원본을 최종 결과로 덮지 않았습니다.
- 이번 메인 브라우저 재실행: **0 / NOT_RUN**. 서버·소켓·브라우저·외부 연결·유료 API·키 읽기·설치·런타임 중지 모두0. 이전 자동승인 거부 작업을 우회하지 않았습니다.

## 바이트·제품·분모 대조

로컬 Git의 `git show <결과커밋>:<경로>`를 Python subprocess의 원바이트로 읽었습니다. `.local/pc2-m3-intake/`에 격리 추출한 파일만 검사했습니다.

| 독립 대조 | 실측 | 판정 |
|---|---:|---|
| evidence-index의 파일 크기·SHA256 | 34/34 일치 | 수용. 인덱스 자신은 원래 분모 제외 |
| 실행 제품 sourceBefore의 51개 파일 | Git 원바이트29 + CRLF 변환22, 미대응0 | 수용. 줄바꿈을 숨겨 동일 바이트라 부르지 않음 |
| sourceBefore/sourceAfter | 51/51 동일, 상태 문자열 공란 | 원격 제품 불변 기록 수용 |
| 최종 checks 배열 / PASS 집계 | 14 / 14 | 원격 주장과 일치 |
| 첫 checks 배열 / PASS 집계 | 14 / 10 | 실패4 보존 확인 |
| build-stamp recordDigest | 1/1 재계산 일치 | 메타데이터 자체 정합 수용 |

최종 `results.json`은 71,435 B, SHA256 `daaf0993bb1a80aeee2789ff402dab75ec2b8b4735c16dd188ab8537190afd84`입니다. 첫 결과는 89,889 B, SHA256 `3ca792194c4f2407b9cc43fc8ecba36ac9395ad116c61d14d4a398fba01fabce`입니다. 최종 checker SHA256 `cb4558737077e3536fa1bfc43f72201bf8cf5ab14c6e9ea06ce76ac1137d6fb8`는 실행 보관본과 `tests/remote/pc2/m3/checker.mjs`가 같습니다. host/run도 각 실행 보관본과 등록본이 일치합니다.

분모14는 baseline1 + 두 케이스의 전체재생·분석4 + 분석실패1 + URL교체1 + 완료반례2 + 음원복구1 + 화면/키보드3 + 요청무결성1입니다. 보고서의 묶음 기준 정상4/음원변경1/완료반례2/실패복구2/화면3/무결성2와 일치합니다. 제품 불변·프로세스 종료 확인은 런처의 추가 조건이며 14에 따로 더하지 않습니다. 다른 M2·PC4·메인 검사와 합산하지 않습니다.

## 인과·주입·실패 이력 검토

실제 검사 소스는 고정 제품의 export 페이지와 DeploymentRouter, OpenAPI handlers, CaseService를 사용합니다. 정상 응답 경로는 API stub이 아니라 별도 합성 JSON 저장소의 replay입니다. `handlers.get_runtime_storage`를 격리 저장소로 바꾸고 live analyzer/키 조회를 실패시키므로 실제 클라우드 저장소·유료 분석을 검수한 것은 아닙니다.

- CASE1: native duration47.15초, played `[0,47.15]`, 1배속·volume1·unmuted, trusted ended1, 경과48.368초.
- CASE2: native duration49.75초, played `[0,49.75]`, 같은 재생 조건, trusted ended1, 경과50.045초.
- 두 경우 실제 부모 분석 버튼의 전 비활성→후 활성, replay POST 각1/HTTP200, 입력5개·대화8개·질문2개·원문 유지가 검사됩니다. CASE1 수량/단위 공란과 CASE2 `1 BOX`를 독립 기대값으로도 검사합니다.
- 정상 응답에 대한 route.fulfill은 없습니다. 의도적 503, 음원404, 같은 caseId의 audioUrl query 변경만 주입합니다. 503 주입 POST1은 실제 성공 POST2와 구분돼 총POST3입니다.
- URL 변경 후 이전 audio를 분리·정지하고 새 분석을 잠급니다. **이 반례에서만** 이전 객체에 가짜 ended를 보냅니다. 정상 두 전체재생을 가짜 ended로 대체하지 않았습니다.
- 끝부분 seek와 마지막 발화 구간 재생으로 전체 완료를 얻을 수 없음을 검사합니다. 404 복구는 0.109초 재생 가능성 확인이며 세 번째 전체재생으로 세지 않습니다.
- 503 후 편집 내용·질문·원문 유지와 재시도 버튼 활성은 확인합니다. 재시도 버튼을 눌러 성공하는 전 과정은 이 항목의 검증 범위가 아닙니다.
- 예상 콘솔503/404 각각1, pageerror0, 예기치 않은 콘솔0, 차단시도0은 JSON과 요청 기록이 일치합니다. 경계 차단은 해당 검사 경로에 한정되며 일반 보안 검증으로 확대하지 않습니다.

첫 실행의 실패4는 두 케이스의 중복 label 선택2, 수정 textarea label 선택1, 앞선 주입 미실행 때문에 POST2를3으로 기대한 종속 실패1입니다. 보존 checker diff는 `#intake-editor` 내부 실제 입력을 고르고 필드별 count1을 확인하도록 변경한 것으로, 결과 기대값을 낮춘 수정은 확인되지 않았습니다. 첫 서버는 종료 시간 초과로 자기 프로세스 SIGTERM, 최종은 Selector 루프/종료 유예 보완 후 stopped=true·exit0·browser disconnected=true입니다. 검사기와 host/run의 수정은 제품 코드 변경과 구분돼 있습니다.

## 92d의 구버전 public 예시와 7ca 수정의 관계

**M3는 API 정본으로 시작했으므로 당시 public 예시의 v2 잔존을 발견하는 검사가 아닙니다.** 다음은 두 커밋의 실제 Git blob을 대조한 값입니다.

| 파일 | 92d2ecb | 7ca0e8b |
|---|---|---|
| data/fixtures/cases.json | 23,090 B, `c7449e66…51449`, v3 URL/query | 같은 바이트 |
| apps/web/public/cases.json | 22,830 B, `071b4599…a8916`, v2 무쿼리 URL | 정본과 동일 23,090 B / `c7449e66…51449` |

92d의 public CASE2는 이전 SHA `333897f4…b914`, 발화4 시작17.55초/마지막 끝49.2초이고, API 정본은 v3 SHA `6fe83afb…baa0`, 17.75초/49.4초입니다. 7ca에서 public도 v3로 동기화됐습니다. 정본 Git LF의 SHA `c7449e66a89c6c2b43b9b09868d651379a376e25a27f3f227b99375c7fa51449`는 CRLF로 변환하면 23,693 B / `5edf80669f7def9d3e10ceea910086c41026ff1252fbc638b97641562f3d84f4`이며 새 메인 묶음 값과 대응합니다.

PC2 host는 `_verified_stamp`를 검증하지만 전체 패키징의 `SYNTHETIC_FIXTURE_COPIES_DIFFER` 가드를 호출하지 않습니다. 92d에서도 source/public/export 내용이 서로 다른 채 standalone Next build stamp는 성립할 수 있습니다. 따라서 PC2 replay 통과와 메인의 실제 bundle 가드 실패는 모순이 아닙니다. 최신 묶음의 동일성 검사는 별도 `reports/deployment/local-bundle-20260921-2200.md` 증거이며 M3의 통과 분모에 추가하지 않습니다.

원격 source fingerprint는 `8198a3dceb74ebd3952a2b8540cd961c73f57060f83deb0ca6e9ec3bcfd2af7d`, output fingerprint는 `cb90493da4b397022185a770d9943d7869a1cf4a70f639007b080e0879f32497`, 출력26파일로 보고돼 있습니다. 전체 출력26개 바이트가 증거 커밋에 포함돼 있지 않아 이번 인수에서 output fingerprint를 독립 재계산하지 않았습니다. stamp 자기 digest 정합을 출력물 전수 재검으로 표현하지 않습니다.

## 수용·보완·보류

수용: 고정92d의 두 v3 통화에 대한 실제 부모 replay 흐름, 명시적 반례·복구·특정 키보드 조작의 원격 기술 증거. 정상/실패 증거 바이트와 검사기의 인과는 서로 맞습니다.

보완: 최신7ca 이후 UI/CCTV/성공 알림·오프라인 예시와 최종 배포의 통합 검수는 별도 버전 고정 증거가 필요합니다. 현재 제한에 따라 이번 인수에서는 새 브라우저 실행을 하지 않았습니다. 3폭 가로넘침0과 일부 키보드 검사는 전체 접근성·시각 품질 판정이 아닙니다. 응답과 UI가 일치한다고 AI 의미 이해의 정확성을 입증하는 것은 아닙니다.

보류: **PC2의 사람 청취 실행은0이나, 최신 사용자에게서 v3가 어색하다는 부정 피드백은1건 존재합니다.** 사람 피드백이 없다고 보고하거나 14/14로 자연스러움 문제를 종결하면 안 됩니다. 음성 수정/사용자 재평가는 남아 있습니다. 라이브 STT/GPT·실업무·영속 배포·전체6회 인수도 미실행입니다.

## 재현 명령과 로컬 증거

저장소 루트에서 `.venv/Scripts/python.exe .local/pc2-m3-intake/audit.py`를 실행하면 외부 호출 없이 원격 커밋의34개 증거, 51개 제품 파일, 두 커밋의 fixture, stamp digest와 원격 분모를 다시 계산합니다. 결과는 `.local/pc2-m3-intake/audit-result.json`입니다. byte-audit.json/static-audit.json 및 실행별 source 보관본과 세 diff도 같은 격리 폴더에 있습니다.

초기 탐색에서 public 경로를 `synthetic-cases.json`으로 잘못 조회해 없음이 반환됐고, 실제 추적 경로 `apps/web/public/cases.json`으로 재조회했습니다. 또 diff 출력 시 cp949가 유니코드 대시를 인코딩하지 못해 로컬 탐색1회 exit1이 있었으며, ASCII JSON 출력으로 바꿔 완료했습니다. 이는 제품/원격 검사 실패가 아니고 최종 순수 감사 결과와 구분합니다.
