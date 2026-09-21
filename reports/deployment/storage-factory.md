# 저장소 factory와 운영 원장 소실 차단 설계

2026-09-21 pc1 로컬 구현. DEC-018의 배포 준비 범위이며 실 Blob 호출·키 조회·초기 seed·프로세스 재시작·Git 변경은 수행하지 않습니다. Vercel 연결·원장 bootstrap과 실 원격 검증은 메인이 별도로 수행합니다.

## 사용자 결과와 계약

상담원·센터의 접수와 AI 예산이 선택한 동일 저장소를 사용합니다. health와 분석은 같은 예산 객체를 공유합니다. 운영 중 원장이 없거나 깨지면 과금 분석 전에 실패하고, 비어 있는 새 예산/fixture로 자동 복구하지 않습니다. 오류 응답에는 환경변수 값·키·저장소 URL·전송 예외 본문을 넣지 않습니다.

`get_runtime_storage()`는 현재 환경 설정을 검증하고 `RuntimeStorage(repository, budget, service, backend)`를 돌려줍니다. backend·로컬 경로·Blob 토큰/스토어·이관액이 같은 경우 같은 객체를 재사용하고, 구성 변경은 새 객체로 분리합니다. 생성 잠금으로 동시에 들어온 첫 요청도 한 객체를 공유합니다. 비밀 필드는 구성 객체 repr에서 제외합니다. 요청 처리 중 기존 객체를 강제 close하지 않습니다.

## 환경 선택

| 설정 | 동작 |
|---|---|
| 로컬에서 backend 미설정 | 기존 `local-json` 기본값 |
| `ONEFLOW_STORAGE_BACKEND=local-json` | JsonCaseRepository+Budget |
| `ONEFLOW_STATE_DIR` 지정 | 절대경로만 허용, `cases-store.json`·`demo-usage.json`을 함께 배치 |
| `ONEFLOW_STORAGE_BACKEND=vercel-blob` | VercelBlobCasStore→기존 원장 전용 guard→CasCaseRepository+CasBudget |
| Blob 설정 | `BLOB_READ_WRITE_TOKEN`, `ONEFLOW_BLOB_STORE_ID`, `ONEFLOW_BUDGET_INITIAL_RESERVED_CENTS` 모두 필수 |
| 이관액 | 0 이상의 십진 정수 문자열만 허용. 미설정 기본 0은 금지하며 명시적인 `0`은 허용 |
| Vercel 표시(`VERCEL=1` 또는 비어 있지 않은 `VERCEL_ENV`) | 명시적인 `vercel-blob`만 허용하여 로컬 fallback 차단 |
| 미지원 backend·빈값·불량 설정 | 정적 `STORAGE_CONFIG_INVALID` 503 |

Blob 예산 기본 상한은 기존 3,000센트, 경고 2,500센트입니다. 이관액은 메인이 로컬 예약 합계를 확정하고 명시적으로 seed한 값과 일치해야 합니다. 이 factory는 원장을 만들지 않습니다. config 변경 시 기존 원장을 다른 설정으로 조용히 수용하지 않습니다.

## 운영 원장 guard와 실패 복구

`ExistingDocumentsStore.read`는 `None`을 `STORAGE_UNAVAILABLE` 503으로 바꾸고 `compare_and_swap(..., expected_version=None)`도 외부 쓰기 전에 같은 오류로 막습니다. 확실한 CAS 충돌만 도메인에 그대로 전달하고 전송 오류는 정적 503으로 정리합니다. cases/budget 누락은 cold start와 요청 중간 모두 동일하게 차단합니다.

handlers의 service 선택 시 Blob 사례 목록·예산 상태를 검증한 뒤 해당 서비스로 진입합니다. health도 동일 객체의 사례/예산 검증 결과를 사용합니다. 검증 뒤 상태가 달라지면 이후 실제 repository read나 budget reserve에서 guard/CAS 검증이 다시 작동합니다. 여러 문서에 걸친 트랜잭션을 제공한다는 뜻은 아닙니다. 상태 점검의 읽기 자체는 쓰기를 수행하지 않습니다.

health의 `liveReady`는 기존 demo key/policy 검증만 뜻합니다. 저장소 오류가 있으면 정적 503을 반환하며 키 준비를 원격 모델 인증 성공으로 표현하지 않습니다. 실제 AI API 요청은 기존 LiveAnalyzer가 전역 reserve에 성공한 뒤 실행합니다. 분석 전 상태 점검과 reserve 사이에서 예산이 사라져도 reserve 단계에서 차단합니다.

## 소유와 검증 계획

소유는 새 `server/runtime_storage.py`, `tests/test_runtime_storage.py`, 본 문서와 기존 `server/handlers.py`의 service/health 연결입니다. 메인 승인으로 `tests/test_runtime_config.py`의 기존 health 검사 한 함수만 factory seam으로 변경하되 key/policy/비밀 비노출 assertion은 보존합니다.

격리 mock/메모리 CAS로 backend/env/path/cache 키·동일 budget·동시 최초 생성·원장 생성 금지·누락/손상/timeout의 분석 호출 0·preflight 이후 원장 소실·상태 읽기 중 수정 경쟁을 검증합니다. 실 원격 CAS 원자성과 인증·영속성·bootstrap은 여전히 미검증입니다. 아래에 실제 실행 결과를 추가합니다.

## 실제 검증 결과

pc1 CJJ Windows, 2026-09-21 18:04~18:07 KST. 아래 검사는 환경을 격리하고 가짜 자격증명·메모리 CAS·httpx.MockTransport만 사용했습니다. 실제 네트워크·키 파일·원장 seed·서버 재시작·Git 변경은 수행하지 않았습니다.

```powershell
.venv/Scripts/python.exe -m pytest tests/test_runtime_storage.py -q
# 53 passed, 5 warnings in 4.18s
.venv/Scripts/python.exe -m pytest tests/test_runtime_storage.py tests/test_runtime_config.py tests/test_cas_storage.py tests/test_demo_backend.py tests/test_analysis_semantics.py tests/test_vercel_blob_store.py -q
# 358 passed, 5 warnings, 75 subtests passed in 7.05s
```

5개 경고는 기존 Starlette/httpx·anyio·Connexion/jsonschema deprecation 안내입니다.

| 검증 | 실제 결과 |
|---|---|
| 로컬 기본값·절대 경로 | 기존 두 파일명 보존, 경로 변경 시 독립 runtime |
| Vercel local fallback·미지원/빈 설정·초기액 누락 | 생성자 호출 전 정적 503 |
| 구성 변경 캐시 | backend/path/token/store/initial 변경을 구분, 같은 설정은 동일 객체 |
| 동시 최초 factory 호출 16개 | transport 생성 1회·runtime 1개·budget 1개 |
| cloud factory 단독 생성 | read 0·write 0 |
| cases/budget 누락·손상·예산 설정 불일치·읽기 timeout | 분석 진입 0·원장 쓰기 0·health 정적 503 |
| preflight 뒤 budget 소실 | reserve 단계 차단·STT/GPT 호출 0·원장 쓰기 0 |
| health/분석 예산 공유 | 초기 75센트+15센트 예약→health 90센트, 실패 finish 후에도 90센트 |
| 초기 생성 요청 `expected_version=None` | transport 진입 전에 503 |
| 실제 Blob 어댑터+모의 HTTP PUT 400/503/timeout/잘못된 JSON | intake·reserve 모두 정적 503, 동작당 PUT 1회, 모델 호출 0, 오류 원문·토큰 노출 0 |
| 실제 Blob 어댑터+모의 HTTP GET 404/timeout/손상 JSON | GET 1회·PUT 0·분석 진입 0 |
| health 읽기와 reserve 경쟁 | health는 읽은 75센트 스냅샷, 새 예약은 보존, 다음 health는 90센트 |
| async handler 실행 스레드 | service preflight/health 저장소 읽기 모두 이벤트 루프 밖 |

테스트 보호력을 확인하기 위해 원본 파일을 고치지 않고 메모리 소스 변이 6개를 실행했습니다. 부재 차단 제거·초기 생성 차단 제거·Vercel fallback 허용·이관액 미설정값 0 대입·설정 변경 캐시 무시·오류 원문 노출 변이가 **6/6 실패로 탐지**됐습니다. 각각 1·1·3·1·1·4개의 대상 검사가 실패했습니다.

별도 읽기 전용 검토자는 재현 결함 0건을 보고했습니다. 독립 Mock 재현에서 factory read/write 0/0, 동일 budget True, 부재 list/health 503, 초기생성 write 0, read/write 각 TimeoutError/OSError/ValueError 3종의 비밀 비노출, 동일 CasConflict 객체 보존을 확인했습니다. 기존 health 키/정책 4조건도 직접 실행하여 4/4 통과했고, 검사 중 credential 파일 읽기는 차단 상태에서 0회였습니다. 같은 PC의 독립 에이전트 검토이며 실제 원격 PC·provider 검증은 아닙니다.

통합 참고: `tests/test_deployment_app.py`의 기존 격리 fixture는 과거 `handlers.Budget` 직접생성 seam을 patch합니다. 현재 연결은 `handlers.get_runtime_storage`를 patch해야 하므로 해당 파일 소유자에게 변경을 전달했습니다. 이 문서의 358개 검사는 deployment_app 테스트를 포함하지 않습니다.
