# N02-M4: CCTV·좌표 파일 전달 코드와 검증 인계

2026-09-21, pc2 / 안영일 / MR-A83. 고정 제품 기준은 `663bbe5bb0ae0a780e328dce9a69188112de8d0e`, 시작 작업 HEAD는 `f0f9d2ae1410a84f23fbcd5540c2645f4a94099b`다. [메인 카드](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/8#issuecomment-5761400803)를 22:39 KST에 수신했고 [ACK](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/8#issuecomment-5761525060)는 22:46:40, [첫 결과](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/8#issuecomment-5761680922)는 22:57:57에 전달했다. 첫 결과 본문의 분 단위 예상 표기22:58보다 GitHub 실제 생성 시각이3초 빠르다. 첫 결과22:59 목표 내다. 코드 전달의 실제 시각/결과 SHA는 같은 이슈의 최종 회신으로 대조한다.

## 변경 결과

기존 2 WAV + 1 MP4는 유지한다. 정본 manifest의 MP4에 선택 `tracks`가 등록되면, 고정 이름 `sorter-demo.tracks.json`을 같은 영상에 결합해 다운로드·public·out·배포 묶음으로 전달한다. case descriptor는 권한을 부여하지 않는다. 등록이 없을 때 임의 demo JSON을 패키지에 넣거나 정적 응답으로 노출하지 않는다.

- `server/media_contract.py`: 정본 구조, 정확한 descriptor5필드, 고정 schema/URL, 양의 정수 크기≤10,000,000, 소문자 SHA256, 부모 MP4 SHA 결합을 공통 검증한다. WAV의 tracks/네 번째 최상위 자산/임의 경로는 거절한다.
- `scripts/fetch_demo_media.py`: 현재 v3와 명시 v4 태그만 다운로드 허용한다. canonical3개 또는 정본에서 도출된 정확한4개 목록을 검증한다. MP4 교체도 synthetic/sourceBytes/sourceSha256 일치와 원본 백업을 요구한다. 기존 sidecar가 새 descriptor와 불일치하면 원본 증명이 없으므로 덮어쓰지 않는다. 중간 실패와 이미 완료된 파일의 보존 규칙을 유지한다.
- `scripts/build_deployment_bundle.py`: 정본 manifest만 사용하고 등록 파일의 public/out 크기·SHA·바이트 동일성을 확인한다. SOURCE_FILES에 공통 helper를 넣는다. 등록 sidecar 누락, export의 추가/미등록 JSON, 변경 후 낡은 build stamp를 거절한다. public에만 있는 등록외 JSON은 패키지 복사 대상에서 제외하며, public 전체의 추가 파일을 모두 거절한다고 주장하지 않는다.
- `server/deployment_app.py`: factory는 패키지의 `data/demo-media-manifest.json`을 읽는다. 파일이 실제로 없으면 sidecar 미허용이며, 있는 정본이 잘못되면 실패한다. 주입 manifest에도 같은 validator를 적용한다. 기존 두 인자 Router는 sidecar 미허용이고 factory의 명시 `media_manifest=None`도 같은 상태다. 등록 영상과 좌표를 시작/각 요청 때 확인하고 검증한 불변 바이트를 응답한다. 링크·hardlink·교체 경로를 거절한다. 등록 MP4는 GET/HEAD 단일 Range를 처리하며 다중 Range는 전체200으로 무시한다. JSON Range도 전체 응답한다. 기존 API 경로·인증 계층은 보존한다. 이 서버 동작은 아래와 같이 구현/정적 검토 상태이며 실제 ASGI 실행 성공 주장은 아니다.

다운로드는 항상 v3/v4만 허용한다. 기존3개만 있는 오프라인 묶음/서버 호출은 기존 태그 호환성을 보존하되, tracks가 있으면 오프라인에서도 v3/v4를 반드시 요구한다. 실제 저장소 manifest는 이전 작업 브랜치의 v2 그대로이며 이번 작업에서 교체하지 않았다.

## 실제 검사와 미실행

|검사|실제 결과|증거/범위|
|---|---|---|
|표준 unittest fetch|17 PASS|`media-m4-fetch-checks.py`; 합성 downloader와 mocked gh 인자 검사, 실제 다운로드0|
|표준 unittest bundle/공통 계약|18건:17 PASS /1 SKIP|`media-m4-bundle-checks.py`; 실제 함수의 fetch→public→out→stamp→bundle를 합성 export에 적용|
|최종 합동 실행|35건:34 PASS /1 SKIP /실패0/오류0|`media-m4-validation.txt/json`, 67.498초 벽시계; runner 자체67.182초|
|Python 구문|10/10 PASS|`media-m4-syntax.json`; AST/compile, 모듈 import나 서버 실행 아님|
|실제 ASGITransport|0 / NOT_RUN|기존 격리 의존성 디렉터리 OS 접근 거부; 기본 Python에는 starlette/httpx 없음|
|기존·추가 pytest|NOT_RUN|기본 Python에 pytest가 없고 설치 금지|
|새 브라우저/실제 Next build/실제 배포|각0|합성 export/runtime placeholder만 사용|

Windows 심볼릭 링크 실제 생성 검사는 WinError1314로1건 SKIP했다. 권한·정책 변경을 하지 않았다. hardlink 검사는 실제 생성해 PASS했다. fetch의 기존 self-test8개를 포함한 한 테스트를 별도8건으로 중복 계산하지 않는다. 추가 pytest/ASGI 파일의 작성된 테스트 수를 실행 분모에 더하지 않는다.

서버 검사는 `reports/pc2/media-m4-server-checks.py`의23개 unittest와 관련 pytest 코드로 인계한다. 격리 의존성 폴더 접근이 거부된 뒤 해당 경로를 다른 계정·도구로 재시도하거나 복사하지 않았다. 기본 Python의 import도 의존성 부재로 실패하여 실제 ASGI 요청은0이다. 프레임워크를 가짜로 대체하거나 설치하지 않았다. 초기 계획의 기존 의존성 사용 가정은 성립하지 않았으며 서버 검증 미달을 남긴다. `connexion`은 api_app 미주입 시에만 지연 import하지만, 이것이 실제 ASGI 실행 성공을 뜻하지 않는다.

## 발견 → 수정 → 재검증

첫 bundle 단독17건에서13 PASS /실패1/오류2/SKIP1이었다. Windows TEMP의 8.3 경로(`ADMINI~1`)와 resolve된 정규 경로를 문자로 비교해 정본 manifest가 오거절된 것이3건의 원인이었다. symlink/hardlink 검사를 유지한 채 양쪽 정본 경로를 resolve해 비교하도록 수정했다.

이후 단독17건은16 PASS/1 SKIP(`media-m4-bundle-run.txt`)였다. 등록 tracks의 태그도 오프라인 예외가 없어야 한다는 반례1건을 추가하고, 공통 계약에서 이를 강제했다. 최종 fetch17+bundle18의35건 합동 결과가34 PASS/1 SKIP다. 최초 실패의 개별 원문은 도구 실행 기록에 있고 별도 원문 파일은 보존하지 못했으므로, 후속 통과 로그를 최초 실패 원문이라고 표시하지 않는다.

## 메인 연결 및 재현

이번 카드의 기존 소유6파일과 helper1파일, `reports/pc2/media-m4-*`만 인수한다. 전체 pc2 브랜치를 main에 무조건 병합하지 않는다. 시작 시 CallReview2파일 add/add 충돌이 예측돼 실제 merge하지 않았다. 소유 파일 중 기준 main과 달랐던 fetch/build/test_bundle3파일만 기준663으로 먼저 맞추고 이번 변경을 적용했다. 그 외 사용자/다른PC 변경·frontend·fixture·실제 manifest·Release는 수정하지 않았다.

현재 작업 브랜치에는 기준main의 `server/intake_idempotency.py`, `server/claim_grounding.py`, `server/request_grounding.py`가 없다. build의 SOURCE_FILES는 기준663의 목록을 보존한다. 합성 테스트에서는 모든 runtime source에 명시 placeholder를 만들었으므로, 이것을 오래된 작업 브랜치 전체가 완전한 배포물을 만드는 증거로 확대하지 않는다. 기준main에 이번 소유 파일을 통합해 평가해야 한다.

실제 실행한 독립 검사 재현(저장소 루트, Python 표준 라이브러리):

```powershell
python reports/pc2/media-m4-fetch-checks.py
python reports/pc2/media-m4-bundle-checks.py
```

서버 미실행 검사의 재현 명령은 **허가된 기존 의존성 환경이 실제로 사용 가능할 때만** 다음과 같다. 이번 인계는 접근 거부 우회나 설치 요청이 아니다.

```powershell
python reports/pc2/media-m4-server-checks.py
python -m pytest tests/test_demo_media_upgrade.py tests/test_deployment_bundle.py tests/test_deployment_app.py
```

정본 등록과 실제 파일 준비·Next export·stamp·배포는 메인 소유다. 등록을 변경하면 새 build stamp가 필요하다. 등록 파일의 누락/불일치를 무시해 인수하지 않는다. 현재 서버23검사의 실제 실행, 기존 pytest 회귀, 실제 새 영상/좌표 연결·재생·최종 배포는 미달 상태다. N02 전체나 최종 자산 등록 완료를 선언하지 않는다.

실제 미디어 다운로드·새 등록·브라우저·서버·소켓·설치·유료 호출·키 읽기·Release·배포·보안 설정 변경은 모두0이다. Git push/같은 이슈 회신만 기존 승인 범위에서 수행한다. 별도 TEST 왕복 완료도 아니다.
