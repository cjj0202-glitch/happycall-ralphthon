# Vercel Blob CAS 최소 HTTP 계약

조사: 2026-09-21 17:50 KST · pc1/CJJ · deployment_readiness · 제품 코드 변경 없음

대상 인터페이스:

```python
CasStore.read(key) -> CasValue(payload: dict, version: str) | None
CasStore.compare_and_swap(key, payload: dict, expected_version: str | None) -> str
```

`expected_version=None`은 생성 전용이고 기존 blob을 덮어쓰면 안 됩니다. 호출자는 `CasConflict`만 재조회·재계산 후 재시도합니다. 이 문서는 공식 SDK 소스 대조 결과이며 Vercel 계정·키·실 API를 사용한 실증이 아닙니다. 새 로컬 모의 테스트도 실행하지 않았습니다.

## 판정

Python httpx로 공식 TypeScript SDK와 같은 wire protocol을 구현할 수 있는 근거를 확보했습니다. PUT endpoint, private origin GET, 인증/조건부 헤더, 본문과 ETag 응답은 소스로 확정됩니다. 단, **최초 생성 중복의 정확한 오류 응답과 동시 최초 생성의 서버 원자성은 실환경 인수 게이트로 남습니다.** 이를 일반 400/409 재시도로 추정 구현하지 않습니다.

기준은 공식 `vercel/storage` SHA `8817cbad75d009fedebd33fb46748c2c0200ea46`, `packages/blob/package.json` 버전 `2.8.0`, SDK의 `BLOB_API_VERSION=12`입니다. SDK 내부 HTTP를 고정한 호환 어댑터이며 독립된 안정 REST 계약이라고 표현하지 않습니다.

## 1. 세 가지 주소를 구분

| 용도 | SDK가 사용하는 요청 | 근거 |
|---|---|---|
| JSON blob PUT | `PUT https://vercel.com/api/blob/?pathname=<query-encoded-key>` | `helpers.ts:13`, `put.ts:130` |
| private 최신 본문 GET | `GET https://<bare-store-id>.private.blob.vercel-storage.com/<key>?cache=0` | `helpers.ts:538`, `get.ts:169`, `get.ts:180` |
| SDK head 메타데이터 조회 | `GET https://vercel.com/api/blob?url=<query-encoded-path-or-url>` | `head.ts:69` |

`head()`는 HTTP HEAD가 아니며 본문 JSON을 받는 관리 API의 GET입니다. CasStore.read는 head를 사용할 필요가 없습니다. private 최신 GET 한 응답의 JSON body와 `ETag`를 함께 사용해야 하며, 별도 head의 최신 ETag와 캐시된 본문을 조합하면 덮어쓰기 방지가 무너집니다. [PUT 소스](https://github.com/vercel/storage/blob/8817cbad75d009fedebd33fb46748c2c0200ea46/packages/blob/src/put.ts#L130), [GET 소스](https://github.com/vercel/storage/blob/8817cbad75d009fedebd33fb46748c2c0200ea46/packages/blob/src/get.ts#L169), [HEAD 소스](https://github.com/vercel/storage/blob/8817cbad75d009fedebd33fb46748c2c0200ea46/packages/blob/src/head.ts#L69)

`store_<id>`의 `store_` 접두어는 제거하며 원래 ID의 대소문자는 유지합니다. SDK는 read-write token의 네 번째 `_` 구간에서 store ID를 파싱하지만, 어댑터는 서버 설정의 store ID를 명시적으로 받고 검증하는 편이 명확합니다. 키는 예를 들어 `oneflow/v1/cases.json`처럼 고정된 ASCII 경로만 허용하면 query와 path 인코딩 차이를 제거할 수 있습니다. arbitrary URL을 키로 받지 않습니다. [인증·ID·URL 소스](https://github.com/vercel/storage/blob/8817cbad75d009fedebd33fb46748c2c0200ea46/packages/blob/src/helpers.ts#L245)

## 2. read(key) HTTP 계약

```http
GET /oneflow/v1/cases.json?cache=0 HTTP/1.1
Host: <bare-store-id>.private.blob.vercel-storage.com
Authorization: Bearer <server credential>
```

이는 SDK `get(key, {access:'private', useCache:false})`와 대응합니다. SDK는 `cache=0` query parameter를 실제로 붙입니다. 단순 `Cache-Control:no-cache` 요청 헤더나 랜덤 query로 대체하지 않습니다. public blob에서는 이 옵션을 무시하므로 **CAS 데이터 store는 private이어야 합니다.** 공식 문서는 private origin 읽기가 최신 쓰기를 반영한다고 설명합니다. [Private consistent reads](https://vercel.com/docs/vercel-blob/private-storage#consistent-reads)

| 응답 | CasStore 처리 |
|---|---|
| 200, JSON object, 비어 있지 않은 ETag | `CasValue(payload, exact_etag)` 반환 |
| 404 | 해당 고정 private blob URL의 미존재로 `None` 반환. 잘못된 store ID를 정상 신규상태로 쓰지 않도록 provisioning·쓰기 권한 확인은 별도 필요 |
| 304 | 이 인터페이스는 If-None-Match를 보내지 않으므로 예상 외 응답; 정상 read로 해석하지 않음 |
| 401/403 | 인증/권한 오류; `None` 또는 `CasConflict`로 바꾸지 않음 |
| 429/5xx/네트워크 timeout | 저장소 오류; `None` 또는 `CasConflict`로 바꾸지 않음 |
| 200이지만 HTML/잘못된 JSON/list/null/ETag 없음 | 데이터/프로토콜 오류; 빈 문서로 복구하지 않음 |

SDK `get.ts`는 GET 404에만 null을 반환하고 기타 비성공 응답은 일반 BlobError로 끝냅니다. 정상 200의 ETag를 response header에서 그대로 읽습니다. 어댑터가 payload object·비어 있지 않은 ETag를 요구하는 것은 CasStore 계약을 위한 추가 검증입니다. [GET 응답 분기](https://github.com/vercel/storage/blob/8817cbad75d009fedebd33fb46748c2c0200ea46/packages/blob/src/get.ts#L219)

## 3. compare_and_swap PUT 계약

요청 body는 JSON UTF-8 byte string입니다. `httpx`에서 JSON object를 이중 직렬화하지 않고, non-finite float를 금지하여 전송할 실제 바이트를 만든 뒤 길이를 계산합니다. 아래 표는 **확인한 SDK가 보내는 헤더**와 어댑터 필수값입니다. 각 헤더를 하나씩 제거한 서버 최소조건 실험은 하지 않았습니다.

| 헤더 | 값·조건 | 의미 |
|---|---|---|
| `Authorization` | `Bearer <server credential>` | 서버 read-write token 또는 허용된 OIDC token |
| `x-vercel-blob-store-id` | bare store ID | OIDC에는 store ID가 인코딩되지 않아 SDK가 별도 전송. read-write 경로에서도 보냄 |
| `x-api-version` | `12` | 조사한 SDK 응답·프로토콜 버전 |
| `x-vercel-blob-access` | `private` | store와 접근 방식 일치 |
| `x-content-type` | `application/json` | 저장될 blob의 MIME; HTTP request Content-Type과 구분 |
| `x-add-random-suffix` | `0` | 동일 key가 항상 동일 blob을 가리킴 |
| `x-allow-overwrite` | 신규 `0`, 기존 CAS `1` | 아래 생성/갱신 분기 |
| `x-if-match` | 기존 CAS에만 exact ETag | SDK가 쓰는 조건부 헤더. 일반 `If-Match`로 멋대로 바꾸지 않음 |
| `x-api-blob-request-id` | 논리 HTTP 요청별 고유 ID | SDK가 보내는 추적값. idempotency 보장을 뜻하지 않음 |
| `x-api-blob-request-attempt` | 어댑터 단일 요청이면 `0` | SDK 추적값 |
| `Content-Length` | JSON UTF-8 바이트 수 | httpx가 계산 가능. SDK의 `x-content-length`는 upload progress/특정 개발 경로에서만 추가되므로 무조건 필수라 하지 않음 |

헤더 생성은 [put-helpers.ts:172](https://github.com/vercel/storage/blob/8817cbad75d009fedebd33fb46748c2c0200ea46/packages/blob/src/put-helpers.ts#L172), 공통 헤더는 [api.ts:340](https://github.com/vercel/storage/blob/8817cbad75d009fedebd33fb46748c2c0200ea46/packages/blob/src/api.ts#L340)에 있습니다. HTTP request의 `Content-Type: application/json`을 함께 설정해도 저장 MIME를 결정하는 `x-content-type`을 생략하지 않습니다.

### 3-A. expected_version=None: 생성 전용

```http
PUT /api/blob/?pathname=oneflow%2Fv1%2Fcases.json HTTP/1.1
Host: vercel.com
Authorization: Bearer <server credential>
x-vercel-blob-store-id: <bare-store-id>
x-api-version: 12
x-vercel-blob-access: private
x-content-type: application/json
x-add-random-suffix: 0
x-allow-overwrite: 0

{"cases":[]}
```

`x-if-match`는 보내지 않습니다. HEAD/GET으로 비존재를 확인하고 무조건 overwrite하는 방식은 금지합니다. 공식 계약은 overwrite=false일 때 같은 pathname이 있으면 오류이며, SDK는 서버에게 한 번의 PUT으로 이 조건을 전달합니다. SDK 주석에는 overwrite=false와 ifMatch를 함께 보내면 backend의 If-Match/If-None-Match가 충돌한다고 설명되어 있어 backend 조건부 쓰기 의도를 확인할 수 있습니다. 다만 공개 SDK는 서버 구현 자체가 아니므로 동시 최초 생성 두 요청의 원자성 실측은 별도입니다. [overwrite 공식 설명](https://vercel.com/docs/vercel-blob#overwriting-blobs), [조건부 헤더 상충 소스](https://github.com/vercel/storage/blob/8817cbad75d009fedebd33fb46748c2c0200ea46/packages/blob/src/put-helpers.ts#L194)

생성 중복 오류의 정확한 HTTP status/code는 공개 SDK에서 전용 분류를 확인하지 못했습니다. `bad_request`는 일반 오류로 처리됩니다. 확정되지 않은 `400/409` 전체를 CasConflict로 바꾸면 잘못된 키·권한·정책 오류를 재시도하게 됩니다. 배포 계정 확보 후 중복 생성의 응답 status와 error.code/검증된 비민감 메시지 패턴을 관측하여 좁은 매핑을 추가해야 합니다. 그 전에는 식별 불가 생성 실패를 저장소 오류로 종료하는 쪽으로 제한합니다.

### 3-B. expected_version=str: 기존 ETag 갱신

위 공통 PUT에 다음 두 헤더를 사용합니다.

```http
x-allow-overwrite: 1
x-if-match: "opaque-etag-from-read"
```

SDK는 ifMatch 지정 시 allowOverwrite를 자동으로 true로 보완하고, ifMatch와 allowOverwrite=false를 함께 주면 호출 전에 오류를 냅니다. 조건부 쓰기에 필요한 이전 ETag는 **그 payload를 읽은 동일 GET**에서 받은 값이어야 합니다. 실패 뒤 fresh ETag만 다시 가져와 낡은 payload를 덮어쓰지 않습니다. [ifMatch 구현](https://github.com/vercel/storage/blob/8817cbad75d009fedebd33fb46748c2c0200ea46/packages/blob/src/put-helpers.ts#L194)

## 4. PUT 응답·ETag·오류 매핑

성공 PUT의 JSON에는 `url`, `downloadUrl`, `pathname`, `contentType`, `contentDisposition`, `etag`가 있고 SDK는 `etag`를 그대로 반환합니다. CasStore는 성공 상태와 JSON object, 요청 key와 응답 pathname의 일치, 비어 있지 않은 ETag를 확인한 후 해당 ETag를 반환해야 합니다. 성공 응답을 받지 못한 timeout은 미저장 증거가 아닙니다.

ETag는 opaque string입니다. SDK 테스트 예시는 문자열 안에 큰따옴표가 포함된 `"abc123"`이고 SDK는 인용부호 제거·추가·해시 재계산 없이 전달합니다. 숫자 revision과 ETag는 다릅니다. JSON 문자열 디코딩을 한 번 한 결과를 HTTP header에 그대로 넣고 CR/LF 같은 비정상 값은 거절합니다. [PUT 응답](https://github.com/vercel/storage/blob/8817cbad75d009fedebd33fb46748c2c0200ea46/packages/blob/src/put.ts#L146), [공식 테스트 소스](https://github.com/vercel/storage/blob/8817cbad75d009fedebd33fb46748c2c0200ea46/packages/blob/src/index.node.test.ts)

| 응답/코드 | SDK 분류 | CasStore 분류 |
|---|---|---|
| 412 + `error.code=precondition_failed` | BlobPreconditionFailedError; 공식 테스트가 해당 fixture를 사용 | `CasConflict` |
| `forbidden` 또는 HTTP 401/403 | BlobAccessError 또는 GET 일반 BlobError | 인증/권한 저장소 오류 |
| `oidc_environment_not_allowed` | 환경 연결 권한 오류 | 설정 오류; 재시도 대상 아님 |
| `store_not_found`, `store_suspended` | 별도 store 오류 | 저장소 설정/상태 오류; 초기 빈 예산으로 대체 금지 |
| PUT `not_found` | BlobNotFoundError | 이 작업의 신규/갱신 의미를 확정할 수 없어 일반 저장소 오류로 제한 |
| `bad_request`, `not_allowed`, 타입/크기/경로 제약 오류 | 일반 또는 전용 BlobError | 저장소 오류; 생성중복 확인 전 CasConflict로 매핑 금지 |
| `rate_limited`, 429 | BlobServiceRateLimited, Retry-After 읽음 | 저장소 가용성 오류; CasConflict 아님 |
| 5xx/서비스 장애/네트워크 timeout | SDK는 일부 자동 재시도 | 본 인터페이스는 자동 재시도하지 않고 결과 불확실/가용성 오류 |
| 알 수 없는 body/코드·기대 밖 3xx | Unknown/프로토콜 오류 | 저장소 오류; 원문 응답·token 로깅 금지 |

SDK 자체는 `error.code`를 분기하며 `precondition_failed`를 전용 예외로 매핑합니다. 위 `412+code` 조합은 우리의 최소 보수적 매핑입니다. bare 412 또는 다른 status의 같은 code를 확대 지원하려면 실제 응답 근거를 추가해야 합니다. 오류 body 전체를 사용자에게 전달하지 말고 비민감 내부 오류 코드로 변환합니다. [오류 분기](https://github.com/vercel/storage/blob/8817cbad75d009fedebd33fb46748c2c0200ea46/packages/blob/src/api.ts#L185)

공식 SDK의 기본 network/unknown/service 오류 자동 재시도 10회는 이 CasStore 요구에 그대로 복제하지 않습니다. httpx 기본 요청 하나로 끝내며 상위 계층은 `CasConflict`만 제한 횟수 재시도합니다. timeout을 conflict로 바꾸거나 예약 금액을 환급하면 이미 저장된 예산 예약·유료 호출 상태와 어긋날 수 있습니다. [SDK 재시도 소스](https://github.com/vercel/storage/blob/8817cbad75d009fedebd33fb46748c2c0200ea46/packages/blob/src/api.ts#L405)

## 5. 인증과 Python 적용 범위

두 인증 방식 모두 Bearer token을 보냅니다. OIDC는 store ID와 배포 환경 연결이 필요하며 SDK는 token 만료를 관리합니다. Python 직접 HTTP는 이 자동 갱신 기능을 재현했다고 가정할 수 없습니다. 장기 static read-write token은 server-only 설정으로 주입할 수 있으나 키/계정 준비는 이번 조사에서 수행하지 않았습니다. [Blob SDK 인증](https://vercel.com/docs/vercel-blob/using-blob-sdk#authentication)

httpx 어댑터의 초기 범위는 고정 private store·서버 credential provider·작은 JSON 문서·단일 PUT·응답검증으로 한정할 수 있습니다. 필요 조건은 다음과 같습니다.

1. credential 값이 아닌 공급 함수를 받아 매 요청 적절한 자격을 얻고, 누락·만료·거부 시 fail closed 합니다.
2. Blob 관리 API와 해당 private store 두 origin으로만 요청합니다. 임의 사용자 URL·redirect로 credential을 전달하지 않습니다.
3. read에 본문 JSON/ETag를 같은 response에서 반환하고, expected_version 문자열이 있을 때만 조건부 overwrite를 보냅니다.
4. 성공 PUT의 etag를 다음 version으로 쓰며 SDK request ID를 exactly-once 증거로 사용하지 않습니다.
5. 케이스 revision 검사·이력 mutation은 상위 CAS loop 안에서 최신 문서에 다시 적용합니다. 예산은 예약 성공 전 live 호출을 시작하지 않고, 저장 오류를 예산 0으로 초기화하지 않습니다.

Python 공식 SDK에 `use_cache`는 있지만 `put(if_match=...)`는 조사한 source에 없습니다. 따라서 `httpx` 호환 어댑터는 SDK 기능 누락을 보완하는 구현이며 실환경 검증 의무가 남습니다. [Python client 기준 소스](https://github.com/vercel/vercel-py/blob/532bc6e4c7fdb857cd3ce20ece10e6b42c45ee61/src/vercel/blob/client.py)

## 6. 인수 전 반드시 남길 실제 증거

| 미실행 게이트 | 기대값 |
|---|---|
| 같은 key에 동시 None 생성 2회 | 1회 성공·1회 식별 가능한 생성중복. 기존 payload 불변 |
| 같은 ETag로 서로 다른 갱신 2회 | 1회 성공·1회 412/precondition_failed |
| 쓰기 직후 private cache=0 GET | 성공 payload와 새 ETag 동시 일치 |
| 이전 ETag/없는 key ETag 갱신 | 성공하지 않음; 정확한 오류 분류 기록 |
| key가 실제 없음/잘못된 store/잘못된 credential | 비존재와 설정·인증 오류 구별, live 호출 0회 |
| 잘못된 JSON/ETag 없는 성공 모양 응답 | 저장소 오류, 빈 상태로 복구하지 않음 |
| PUT 직후 응답 유실 | 성공으로 꾸미지 않음; 예산 예약을 보수적으로 유지 |
| 새 함수 인스턴스·재배포 | 저장된 케이스/예산 유지 |

현재 결과는 `HTTP 계약 조사 완료 / 실제 Blob 호환 검증 미실행 / 최초 생성 중복 분류 미확정`입니다. 보고서에 제시한 공식 테스트는 소스만 읽었으며 실행·통과 실적으로 계산하지 않습니다.
