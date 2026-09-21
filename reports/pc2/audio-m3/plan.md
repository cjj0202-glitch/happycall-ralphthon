# N02-M3 실제 부모 화면 검수 계획

2026-09-21 21:37 KST에 메인 #8 comment5760570765를 수신했다. M2 범위 인수와 v3 정본 채택을 확인했다. 이 계획은 새 기준 `92d2ecbad981f366a9e5ffc850d9c2bb7fd5d3a2`의 실제 page·replay API 검수다. M2/pc4 결과와 분모를 합산하지 않는다.

## 입력과 격리

별도 detached clean checkout `C:/Users/Administrator/Desktop/hackerton/.local/pc2-m3-product`를 생성했다. v3 fetch·verify-only 자산3/3을 확인했다. 기존 checkout의 음원·제품은 보존한다. Node/Next/Playwright/Edge는 기존 설치를 사용한다. Python3.12 런타임에는 connexion/uvicorn이 없어 제품 uv.lock의 해시 고정 패키지를 검사용 로컬 경로에만 준비한다. 원래 Python 환경·감시기·보안 설정은 바꾸지 않는다.

새 Next production export를 빌드하고 제공된 build stamp의 source/output fingerprint를 검증한다. 실제 DeploymentRouter/OpenAPI handler/CaseService를 사용하고, 저장소는 새 임시 합성 JSON 저장소로 격리한다. live analyzer와 외부 네트워크·키 읽기는 차단하며 replay API만 허용한다. 기존8100/3100 서버는 건드리지 않는다. 새127.0.0.1 포트와 Playwright pipe의 단일 브라우저를 사용하고 자신이 만든 프로세스만 정리한다.

## 사전 기대값

- 정상2건: CASE1 47.15초 / CASE2 49.75초. rate1, muted=false, volume1, duration오차≤1샘플, trusted ended1, played의 연속구간0~끝, 벽시계≥duration−0.3초. 종료 전 실제 분석 버튼 비활성, 종료 후 replay 분석 실제POST 성공과 UI의 원문/양식/질문 출처를 대조한다.
- v3 계약: CASE2 URL의 SHA query, 발화1~3 유지/4~8+0.20초, 실제파일 SHA 일치. 같은id에서 음원URL만 바뀌면 부모/컴포넌트 완료상태 초기화. API 응답을 통해 변경 입력을 제공한 검사는 주입 경계를 따로 적는다.
- 반례: 끝seek·구간만 재생으로 실제 분석 버튼 활성화 금지. 404/디코딩 중 한 경로의 실제 media error 안내와 복구. 분석 응답실패 후 사람 편집 원문 보존. 실패주입은 브라우저 경계로 한정하며 정상 호출은 실제서버 replay응답을 사용한다.
- 화면390/768/1440: 실제 재생→분석→접수 순서, 넘침0, 키보드 Enter/Space/방향키와 포커스. 예상오류와 예상밖 pageerror/consoleerror/요청실패는 구분한다.
- 증거: 실행 전에 checker/helper 원본바이트·제품 SHA·빌드 fingerprint·음원3SHA를 보존하고 종료 후 제품 tracked파일의 SHA 불변을 대조한다. 각 정상/반례/화면 분모, 원시실패·수정·같은조건 재검을 기록한다.

## 분담과 인계

총괄은 격리 checkout·빌드·서버·실제 실행·증거 검토·회신을 담당한다. 동일pc2의 보조검사기는 `tests/remote/pc2/m3/checker.mjs`만 작성하며 서버/브라우저를 띄우지 않는다. 제품 결함은 재현해 메인에게 전달하고 공용 소스를 고치지 않는다. 수신10분 내 계획,20~30분 내 첫 결과를 같은#8에 회신한다(21:47/21:57~22:07 KST). 지연·차단도 실제 상태대로 보고한다. 사람 청취·최종배포·전체6회 인수는 범위 밖이다.
