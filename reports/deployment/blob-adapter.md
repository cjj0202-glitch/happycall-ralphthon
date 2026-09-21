# Vercel private Blob HTTP 어댑터 설계와 검증

2026-09-21 · pc1/CJJ · blob_http_adapter. 구현 전에 작성한 설계입니다. 소유 파일은 `server/vercel_blob_store.py`, `tests/test_vercel_blob_store.py`, 이 문서입니다. 다른 작업자의 CAS 도메인·환경 구성은 읽기 전용이며 Git 작업·실제 키·네트워크·store 생성·배포를 실행하지 않습니다. 구현 중 메인이 전달한 개인 AWS 전환·Vercel 추가 로그인/배포 중단 상태에 따라 이 어댑터를 현재 배포 대상으로 연결하지 않습니다.

## 목적과 근거

서버리스의 접수·예산 원장이 읽은 본문과 같은 버전에만 갱신되도록 `CasStore` 전송을 구현합니다. DEC-018과 [배포 준비 조사](../deployment-readiness.md)의 공유 저장 게이트를 지원하지만 이 구현의 로컬 통과를 원격 CAS 안전성으로 판정하지 않습니다.

전송 근거는 [HTTP 계약 조사](blob-http-contract.md), 공식 TypeScript SDK `@vercel/blob` 2.8.0 / SHA `8817cbad75d009fedebd33fb46748c2c0200ea46` / API version 12입니다. 독립된 안정 REST API 계약이나 공식 Python SDK 기능이라고 표현하지 않습니다.

## 인터페이스와 제한

`VercelBlobCasStore(token=..., store_id=..., namespace="oneflow")`가 `read(key)`와 `compare_and_swap(key, payload, expected_version)`를 제공합니다. token은 호출자가 문자열 또는 매 요청 자격을 반환하는 공급 함수로 주입합니다. 파일·환경변수·CLI 자격을 탐색하지 않습니다. `store_` 접두어가 있는 설정 ID와 bare ID를 허용하고 영숫자만 받습니다. HTTP DNS host의 대소문자 정규화 외에 관리 API로 보내는 ID는 보존합니다.

키는 지정 namespace 아래의 ASCII 경로만 허용합니다. 빈 segment, `.`/`..`, 역슬래시, URL, query/fragment, percent escape, 공백을 요청 전에 거절합니다. 임의 host·endpoint 설정은 제공하지 않고 HTTPS의 공식 관리 API와 지정 private store만 접근합니다. redirect·환경 proxy·자동 network retry를 사용하지 않습니다. 테스트에는 `httpx.MockTransport`만 주입합니다.

문서는 UTF-8의 JSON object이며 non-finite number, 중복 JSON key, 유효하지 않은 Unicode와 직렬화 불가능 객체를 거절합니다. 기본 본문 한도는 4MiB, PUT 메타데이터/오류 응답은 64KiB입니다. 수신은 스트리밍으로 상한을 적용합니다. 강한 인용 ETag만 사용하고 `W/`, wildcard, 누락·빈 값·제어문자는 거절하며 인용부호를 추가/제거하지 않습니다.

## 요청과 결과

- GET은 `https://<store>.private.blob.vercel-storage.com/<key>?cache=0` 한 번이며 200의 body/ETag를 같은 응답에서 읽습니다. 실제 404만 `None`입니다. 304·redirect·403·429·5xx·파싱/크기/ETag 오류는 저장소 오류입니다.
- PUT은 `https://vercel.com/api/blob/?pathname=<encoded key>` 한 번입니다. API version 12, private, random suffix 0, JSON MIME를 고정합니다. 신규는 overwrite 0, 기존은 overwrite 1과 읽은 ETag 그대로의 `x-if-match`입니다.
- PUT 성공에는 200/201, JSON object, 요청과 같은 `pathname`, 올바른 `etag`가 필요합니다. 동일 본문의 성공에서 같은 ETag를 반환할 수 있으므로 응답 ETag가 이전과 같다는 이유로 성공을 오류로 바꾸지 않습니다. ETag를 산술 revision으로 사용하지 않습니다.
- HTTP 412이면서 `error.code == "precondition_failed"`인 경우만 `CasConflict`입니다. 400/409, bare 412, 다른 status의 같은 code를 충돌로 확대하지 않습니다. 실제 duplicate-create 응답이 미검증이므로 초기화 경합의 일반 400은 저장소 오류로 끝납니다.
- network timeout·PUT 응답 유실·성공 모양의 잘못된 metadata는 성공 또는 실패를 추정하지 않는 오류입니다. 일반 저장소 오류는 고정된 비민감 code·HTTP status·쓰기 결과 불확실 flag만 보유하며 URL·키·token·본문·원본 exception을 외부 예외 메시지에 붙이지 않습니다.

## 검증 계획과 실환경 잔여 게이트

MockTransport로 정상 read/create/update, 인용 ETag 보존·동일 ETag 성공, 같은 응답 본문/버전, cache=0, 404와 오류 status 구분, 412+code 경계, 잘못된 JSON/key/ETag, 수신/송신 크기 경계, redirect 무추적, timeout 한 번 호출, 공급자/HTTP 예외 비밀 제거를 검증합니다. 핵심 cache bypass·조건부 헤더·충돌 분류를 약화한 변이가 해당 검사를 실패시키는지 대조합니다.

실계정에서는 최초 생성 경쟁(한 번 성공·한 번 중복, 기존 문서 불변), 동일 ETag의 서로 다른 갱신 경쟁, 쓰기 직후 최신 읽기, 응답 유실, 새 함수 인스턴스/재배포 지속성을 별도로 측정해야 합니다. 최초 생성 중복의 정확한 status/code를 확인하기 전 넓은 오류 매핑을 추가하지 않습니다. 잘못된 store ID의 404와 올바른 store의 최초 부재 구별은 provisioning 검증이 필요합니다. 이것은 어댑터 로컬 검사로 완료되지 않습니다.

## 실행 결과

저장소 루트에서 `.venv/Scripts/python.exe -m pytest tests/test_vercel_blob_store.py -q`를 실행하여 **155 passed in 0.41s**, 종료코드 0을 확인했습니다. 모든 HTTP는 `httpx.MockTransport`이며 token·store ID·본문은 합성입니다. 정상 요청 헤더·UTF-8 크기·최신 GET 2회의 서로 다른 본문/ETag를 양성으로 확인했고, 인증/가용성 오류·잘못된 JSON·크기·경로·ETag·쓰기 불확실성을 음성/경계로 확인했습니다.

추가로 원본 파일을 수정하지 않고 소스를 메모리의 `types.ModuleType('server.vercel_blob_store')`에 로드한 뒤 한 조건씩 변이하여 동일 pytest 함수를 실행했습니다. 무변이 대조군 38건 통과/117건 제외, 아래 **6개 변이 모두 검사 실패로 검출**했습니다. 변이 코드는 디스크·제품에 남기지 않았습니다.

| 변이 | 같은 검사 선택(`pytest -k`) | 결과 |
|---|---|---|
| `params={"cache": "0"}` → cache 1 | `read_origin_cache_bypass` | 1 failed / 154 deselected |
| `headers["x-if-match"] = expected_version` 제거 | `create_or_update_is_one_exact` | 2 failed / 2 passed / 151 deselected |
| 신규 `x-allow-overwrite` 0 → 1 | `create_or_update_is_one_exact` | 2 failed / 2 passed / 151 deselected |
| `if status == 412` → status in 400,409,412 | `uncertain_put_errors` | 2 failed / 13 passed / 140 deselected |
| `precondition_failed` code 검사 → 무조건 참 | `malformed_412_body or uncertain_put_errors` | 9 failed / 11 passed / 135 deselected |
| GET 404 부재 판정 → 403도 포함 | `read_non_200_non_404` | 1 failed / 16 passed / 138 deselected |

이 검사는 어댑터의 요청·응답 판정과 대조군 발화를 확인한 것입니다. 실제 Blob 호출·실환경 CAS 안전성·최초 생성 중복 분류·지속성·배포는 **미실행**이며, 성공한 mock PUT을 실서비스 저장 성공으로 계산하지 않습니다.
