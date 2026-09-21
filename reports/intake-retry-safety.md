# 웹 접수 응답 유실·중복 방지 검증

2026-09-21 pc1, 새 코드의 로컬 검증입니다. 브라우저 응답 유실을 저장 실패로 단정하지 않고, 같은 시도 키로 기존 접수를 조회·재시도할 수 있게 했습니다. 상세 계약은 `planning/intake-retry-safety.md`입니다.

## 변경

신규 접수는 UUID v4 시도 키와 JSON 본문의 해시를 접수와 **같은 저장 문서·원자적 쓰기**에 기록합니다. 동일 키·내용은 같은 접수의 최신 상태를 반환하고, 다른 내용은 409로 막습니다. 키 조회는 저장 여부 확인을 지원하며 아직 결과가 없는 404와 실패를 구분합니다. 원문 키는 일반 접수 목록에 추가하지 않습니다. 키 없는 기존 호출은 유지되지만 중복 방지 대상은 아닙니다.

local FileLock/atomic replace와 CAS 저장소 둘 다 구현했습니다. 후자는 주입한 메모리 CAS 및 경합·오류 대조군을 사용했으며 실제 Vercel 영속 저장 통과를 뜻하지 않습니다. 합성 자료와 격리된 임시 저장소만 사용했고 기존 상담 상태·API 키·예산 원장은 건드리지 않았습니다.

## 검증 결과

```powershell
.venv/Scripts/python.exe -m pytest tests/test_intake_idempotency.py tests/test_demo_backend.py tests/test_cas_storage.py tests/test_runtime_storage.py tests/test_runtime_config.py tests/test_deployment_bundle.py -q
```

**254 passed, 48 subtests passed, 35.50초.** 새 idempotency 검사는 이 중 17건입니다. 기존 HTTP 클라이언트·JSON schema 사용 중단 예정 경고 5개는 남아 있습니다.

- 동일 키/본문 재시도, JSON 키 순서·UUID 대소문자, repository 재생성 후 조회: 새 접수 1건·최초 이력 1개.
- 접수 수정 후 같은 시도 조회/재전송: 최초 revision으로 되돌리지 않고 최신 상태 반환.
- 같은 키/다른 내용 409, 무효 키 422, 아직 저장되지 않은 유효 키 404. 원래 상태 불변.
- 다른 키 및 키 없는 기존 요청은 별개 접수로 유지.
- local/CAS 동시 4호출에서 같은 키 접수 1건. CAS의 같은 내용/다른 내용 각각 강제 쓰기 경합 대조.
- CAS·local 모두 저장 직후 응답 유실 대조군: 실패를 먼저 보존하고 조회·동일 키 재시도로 기존 접수를 회수. CAS 두 번째 쓰기 0건.
- 시도 기록이 null이거나 없는 접수를 가리키면 503이며 새 접수로 조용히 대체하지 않음.
- 실제 ASGI POST/GET 및 헤더 CORS: 동일 접수 반환, 내용 충돌 거부, 복구 조회 확인.

## 실패와 수정

초기 OpenAPI의 인라인 description 쉼표가 YAML 속성으로 나뉘어 schema 검사가 실패했습니다. 문자열을 따옴표로 고쳤습니다. 다음으로 직접 호출하는 기존 runtime 검사가 request context 접근으로 4건 실패했습니다. 헤더를 단순 함수 인자로 받는 시도는 실제 HTTP에서 헤더가 전달되지 않아 중복 방지 양성 검사가 실패했습니다. 최종 구현은 HTTP context가 있으면 실제 헤더를 읽고, 직접 호출에서는 선택 인자를 사용합니다. 관련 68건을 재검한 뒤 위 254건을 통과했습니다. 기대값을 낮추지 않았습니다.

## 검사기 대조

제품 파일을 바꾸지 않고 테스트 프로세스 메모리에서 조회 제거·본문 해시 결합 제거·시도 기록 쓰기 제거·모든 키 동일화의 4개 변이를 주입했습니다. 각 변이의 해당 local/CAS 검사 2건이 실제 실패(exit1)하여 **4/4 검출**했습니다. 실행기와 원출력은 `.local/idempotency-mutation-check.py`, `.local/idempotency-mutation-results.json` 및 개별 로그로 보존했습니다. 이는 선택한 보호 규칙의 검사 도달을 보이며 모든 변이에 대한 증명은 아닙니다.

## 남은 인수

후속 UI에서 실제 POST/PATCH 저장 뒤 응답만 끊는 브라우저 검사, 미확정 요청의 본문/키 보존, 세 역할의 최신 조회를 검증합니다. 별도 독립 코드 검토와 실제 원격 저장 환경도 남아 있으며 이번 백엔드 검사만으로 전체 제품을 인수하지 않습니다.

후속 독립 검토는 `reports/intake-retry-independent.md`에 연결했습니다. 참조 fixture 변경 시 같은 요청의 재시도가422로 거부되는 계약 결함을 찾아 수정했고, 새 local/CAS 회귀2건을 추가해 현재 신규 검사는19건입니다. 메인의 수정 후 관련106 tests·24 subtests가 통과했으며 원래 실패를 위 문서에 보존했습니다.
