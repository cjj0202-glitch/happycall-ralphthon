# 신규 접수 재시도 독립 적대검토

2026-09-21 pc1. 읽기 전용 `/root/intake_retry_adversarial`의 실제 실행 결과를 메인이 기록했습니다. 검토자는 제품 파일이나 이 보고서를 쓰지 않았습니다. 최초 대상은 HEAD 74e29ca 위의 미커밋 신규 접수 구현입니다.

## 발견과 실패 증거

최초 검토의 지적 1건: 참조 사례에 연결하여 저장한 접수의 원본 fixture가 이후 변경·제거되면, 동일 키·동일 본문 재전송이 이미 저장된 접수 대신 422 `INVALID_REFERENCE_CASE`를 반환했습니다. service가 중복 방지 조회보다 현재 fixture 검사를 먼저 했습니다. 데이터 중복이나 손실은 없고 별도 GET 조회는 가능하지만 복구 계약 위반입니다.

검토자가 실제 ASGI에서 실행한 순서: 연결 본문으로 `POST /api/intake` → fixture 조회를 빈 목록으로 주입 → `GET /api/intake-attempts/{key}` → 같은 키/본문으로 POST.

```
first=201  recover=200  retry=422
retry_error=INVALID_REFERENCE_CASE
same_saved_case=True  stored_cases=3
```

최초 회귀 테스트 17건은 referenceCaseId 없는 본문을 사용해 이 경로를 놓쳤습니다. 검토자는 원래 17건 통과와 위 실패를 구분했습니다.

## 함께 통과한 독립 경계

- local/CAS 같은 키·다른 본문 동시 요청: 각각 성공1/409충돌1, 접수 증가1.
- 실제 ASGI 저장 직후 timeout: POST503 → GET200 → 재POST201, 저장 시도1.
- 접수 수정 후 재전송: revision1·이력2를 반환, 목록에 키/키 해시/본문 해시/대응표 노출0.
- HTTP 잘못된 헤더 값8종 모두422, 헤더명·UUID 대소문자 변경은 같은 접수.
- null/list 대응표·null 기록·없는 접수 ID·잘못된 해시 타입5종: GET/POST503, 추가 쓰기0.

독립 실행:

```powershell
.venv/Scripts/python.exe -B -m pytest tests/test_intake_idempotency.py -q -p no:cacheprovider
.venv/Scripts/python.exe -B -m pytest tests/test_intake_idempotency.py tests/test_demo_backend.py tests/test_cas_storage.py tests/test_runtime_storage.py tests/test_runtime_config.py tests/test_deployment_bundle.py -q -p no:cacheprovider
```

최초 결과는 17 passed(1.87초), 관련254 passed·48 subtests(37.04초), 사용 중단 예정 경고5개입니다. 경계 검사는 메모리/격리 저장소와 ASGI이며 기존 서비스·키·원장·실제 Vercel에는 접근하지 않았습니다.

## 메인 수정과 재검

기존 시도 조회를 원본 fixture 확인 전에 수행하도록 순서를 고쳤습니다. 조기 반환에서 키 해시뿐 아니라 **본문 해시도 함께 검증**하며, 신규 시도의 참조 검사와 create 내부의 원자적 중복 검사를 유지합니다. 기존 접수를 못 찾았다는 이유로 본문이 바뀐 재시도를 허용하지 않습니다.

local/CAS 두 경로에 참조 fixture 삭제 회귀를 추가했습니다. 같은 키·본문은 기존 건, 변경 본문은409, 새로운 키로 유효하지 않은 참조를 접수하면422입니다. 메인의 수정 후 관련106 tests·24 subtests가 통과했습니다. 검토자에게 원래 ASGI 반례와 동시 요청을 다시 대조하도록 전달했으며 독립 재검 결과는 후속 기록합니다.

20:49:10 KST 독립 재검: 같은 ASGI 반례의 결과가 **201/200/201**로 바뀌었고 세 응답 동일, 신규 접수1·이력1·revision0을 확인했습니다. 같은 키/변경 본문409와 새 키/삭제된 참조422도 유지됐습니다. 두 요청의 사전조회가 모두 None인 상태를 Barrier로 강제한 CAS 경합에서도 동일 본문 성공2/접수1, 다른 본문 성공1+409/접수1을 확인했습니다. 신규19 tests(4.22초) 통과입니다. 이 지적은 검증 범위에서 해결됐으며 검토자가 제품·보고 파일을 변경하지 않았습니다.

브라우저 응답 중단·실제 원격 저장은 별도 검증입니다. 백엔드/ASGI 통과를 전체 제품 인수로 확대하지 않습니다.
