# 서버리스 공유 접수·예산 CAS 상세설계

2026-09-21, pc1 로컬 구현. 범위는 저장 전송 계층을 주입하는 도메인과 메모리 대조군입니다. 실제 원격 저장소·Vercel 인증·키·프로비저닝·배포·모델 호출 검증은 이 문서의 통과 범위가 아닙니다. DEC-018 및 docs24의 지속저장·동시수정·예산 게이트를 위한 구현이며 실제 배포 검증은 메인이 수행합니다.

## 사용자 과업과 상태

상담원은 새 접수와 수정 내용을 다른 서버 인스턴스에서도 조회하고, 센터의 새 조치가 오래된 폼으로 지워지지 않아야 합니다. 실제 AI 호출 전에는 전체 인스턴스가 같은 예산 원장에서 예약하여 상한을 넘지 않아야 합니다. 저장 실패는 성공으로 표시하지 않고, 같은 접수 충돌은 409로 새 내용을 확인하도록 합니다. 지속적인 문서 경합은 제한 횟수 후 503으로 반환합니다.

## 전송 계약과 데이터

- `CasStore.read(key) -> CasValue(payload: dict, version: str) | None`: 최신 읽기. `None`은 확인된 부재뿐이며 인증·시간초과·파싱 실패를 부재로 바꾸지 않습니다.
- `CasStore.compare_and_swap(key, payload, expected_version) -> str`: 문서 전체의 원자적 조건부 쓰기. `expected_version=None`은 존재하지 않을 때만 생성입니다. 성공은 새 버전, 확정된 사전조건 불일치만 `CasConflict`입니다. 애매한 네트워크 실패를 충돌로 변환하지 않습니다.
- 버전은 불투명하며 같은 키에서 성공한 변경마다 달라집니다. 읽은 본문과 버전이 같은 객체여야 하고, 캐시된 본문에 최신 버전을 붙이지 않습니다. 잠금·확인 후 무조건 put은 이 계약을 만족하지 않습니다.
- 기본 키는 `oneflow/cases.json`, `oneflow/budget.json`입니다. 테스트의 `InMemoryCasStore`는 단일 프로세스용 가짜이며 운영 저장소가 아닙니다.
- 접수 원장은 기존 `{cases: [...]}` 구조, case ID, 원문·근거·이력·revision을 보존합니다. fixture는 로컬 읽기 전용 합성 파일이며 fixture가 원격 최신 접수를 덮어쓰지 않습니다. revision이 없던 기존 접수는 읽을 때 0으로 해석합니다.
- 예산 원장은 `schemaVersion`, `initialReservedCents`, `limitCents`, `warnCents`, `entries`를 가집니다. 금액은 정수 센트이며 초기 이관액과 모든 예약액의 합계가 상한 판정의 기준입니다. 원문·STT·키를 넣지 않습니다.

## 수정과 충돌

초기 fixture 및 예산 원장은 create-if-absent로 생성합니다. 승자 문서를 다시 읽는 패자는 자기 초기값으로 덮어쓰지 않습니다. 생성 중 같은 case ID가 경쟁하면 한 건만 성공하며 나머지는 `DUPLICATE_CASE`입니다.

수정은 처음 읽은 접수의 사본에 `transform`을 한 번만 적용하고 revision을 1 올립니다. 문서 CAS가 충돌하면 최신 문서를 읽어 대상 접수가 처음의 본문·revision과 같은지 확인합니다. 같으면 다른 접수의 변경을 보존하여 이미 계산한 결과를 병합하고 제한 횟수 안에서 저장합니다. 대상 접수가 달라졌으면 `STATE_CONFLICT`입니다. 최신 revision을 오래된 폼에 붙이거나 transform·실제 모델 호출을 다시 실행하지 않습니다. service의 `expectedRevision` 검사와 분석 시작 revision 검사를 그대로 사용합니다.

전송 장애·구조 손상·경합 도중 문서 소실은 실패로 종료하며 로컬 저장으로 대체하지 않습니다. 부정확한 예산 원장을 0원으로 재초기화하지 않습니다. 외부 변경으로 원장이 삭제되는 운영 사고는 저장소 권한·복구 절차에서 막아야 하며, 새 저장소의 최초 부재와 구분할 외부 상태는 이 프로토콜에 없습니다.

## 예산과 이관

`CasBudget(..., initial_reserved_cents=N)`은 최초 생성 시 기존 로컬 보수적 예약 합계 N을 `initialReservedCents`에 고정합니다. 예산 초과 이관액도 보존하여 이후 예약을 차단하며 0으로 낮추지 않습니다. 기존 cloud 원장과 초기액·상한·경고 기준 설정이 다르면 `BUDGET_CONFIG_MISMATCH`로 실패합니다. 이관값은 매번 추가하지 않습니다. 기존 원장이 있으면 기존 값이 기준이며 구성 불일치를 조용히 수용하지 않습니다.

실제 전환은 메인이 로컬 유료 호출을 정지하고 로컬 원장을 보존·합산하여 같은 N으로 모든 cloud 인스턴스를 구성한 뒤 공유 원장을 검증하는 순서입니다. 로컬 호출을 계속하면서 한 번 읽은 합계만 이관하면 누락되므로 이 구현만으로 전환 완료를 선언하지 않습니다. 개별 로컬 예약 ID의 이관은 하지 않으며 기존 호출의 완료 정리 후 전환해야 합니다.

`reserve(cents, purpose)`는 전역 합계 검사와 예약 추가를 하나의 CAS로 실행합니다. 경합 시 최신 합계로 검사하므로 상한 정확히 일치는 허용하고 1센트 초과는 `BUDGET_LIMIT`입니다. 완료·실패 후에도 금액을 차감하지 않습니다. `finish(request_id, success)`는 최초 종결 상태를 보존하며 중복·순서가 바뀐 재시도에서 상태와 금액을 다시 바꾸지 않습니다. 존재하지 않는 ID는 기존 계약처럼 아무 변경 없이 종료합니다.

## 연결 위치와 소유

메인은 `server/handlers.py`의 service factory에서 `CaseService(CasCaseRepository(store), analyzer=LiveAnalyzer(budget=CasBudget(store, ...)))`를 구성하고 health의 예산 조회에도 같은 factory를 연결합니다. 기존 `LiveAnalyzer`는 budget 인자를 이미 받습니다. Vercel 원격 transport와 환경 구성은 별도이며 이 작업은 SDK를 호출하지 않습니다.

편집 소유는 `server/cas_store.py`, `server/cas_repository.py`, `server/cas_budget.py`, `tests/test_cas_storage.py`, 본 문서입니다. 기존 repository/budget/handlers/service/live는 읽기 전용입니다.

## 수용 기준과 검증 계획

공유 가짜 저장소를 주입한 독립 인스턴스로 초기 생성·신규 생성·동일 case 수정·다른 case 수정·예산 예약 경쟁을 실제 스레드와 결정적인 장벽으로 재현합니다. 정상 생성/조회/사본 분리, 중복·누락·손상·전송 실패, revision 0·상한 일치/1센트 초과·이관액 초과, 오래된 센터 폼·모델 1회 호출, retry 상한을 확인합니다. CAS·대상 변경 검사·상한 비교를 제거한 변이에서 해당 테스트가 실패하는지도 측정합니다. 실행 결과는 아래에 추가합니다.

## 실제 로컬 검증 결과

pc1 CJJ, Windows, 2026-09-21 17:52~17:53 KST. 저장소 루트에서 실행했습니다. 모든 CAS 원장은 메모리 가짜이고 실제 모델 호출은 Mock입니다. `.local` 실행 원장·키·실제 원격 저장소는 읽거나 쓰지 않았습니다.

```powershell
.venv/Scripts/python.exe -m pytest tests/test_cas_storage.py -q
# 34 passed, 24 subtests passed in 1.74s
.venv/Scripts/python.exe -m pytest tests/test_demo_backend.py tests/test_runtime_config.py tests/test_analysis_semantics.py -q
# 116 passed, 5 warnings, 51 subtests passed in 4.90s
```

기존 회귀의 5개 경고는 Starlette/httpx·anyio·Connexion/jsonschema의 deprecation 안내입니다. 기존 검사 통과는 CAS remote transport 통과를 뜻하지 않습니다.

| 검사 | 기대 | 실제 |
|---|---|---|
| 동시에 처음 시작한 인스턴스의 신규 접수 | fixture 2건+신규 2건 | 4건 모두 보존 |
| 같은 ID 동시 생성 | 1건 성공·1건 중복 거부 | `DUPLICATE_CASE` 1건, 저장 1건 |
| 같은 접수 동시 수정 | 1건 저장·1건 충돌, transform 각각 1회 | `STATE_CONFLICT` 1건, revision 1 |
| 다른 접수 동시 수정 | 두 수정·각 revision 증가 보존 | 각각 revision 1, transform 각각 1회 |
| 오래된 센터 종결 폼 | 새 미완료 조치 보존 | 409, 새 조치·처리 중 유지 |
| 분석 저장 직전 다른/같은 접수 충돌 | 다른 접수면 병합, 같은 접수면 거부, 모델 1회 | 두 경로 모두 analyzer 1회 |
| 총 100센트·이관 10센트·12건×15센트 경쟁 | 6건 승인·6건 상한 거부 | 6/6, 합계 100센트 |
| 79센트 이관 후 1+20센트 예약 | 80센트부터 경고·100센트 허용·101센트 거부 | 기대와 일치 |
| 실패/중복 finish·서로 다른 완료 결과 경쟁 | 금액 보존·최초 종결 고정 | 차감·중복 예약·종결 재변경 없음 |
| 저장 완료 뒤 응답 시간초과 | 자동 반복 없음, 이미 예약된 금액 보존 | 1회 호출, 30센트 예약 유지 |
| 충돌 후 원장 소실·손상·설정 불일치 | 초기화/로컬 대체 없이 실패 | 해당 503, 추가 쓰기 없음 |

변이는 원본 파일을 고치지 않고 소스를 메모리에서 한정 치환하여 개별 행동 테스트에 주입했습니다. 7/7이 실패하여 보호 조건 제거를 탐지했습니다. 아래 표의 테스트명은 `tests/test_cas_storage.py`에 있습니다.

| 변이 | 실행한 테스트 | 실제 실패 근거 |
|---|---|---|
| 저장소 버전 비교 제거 | `CasCaseTests.test_competing_different_case_edits_are_merged_without_repeating_transform` | 한 접수 label 유실, `KeyError: label` |
| 같은 접수 본문 비교 두 곳 제거 | `CasCaseTests.test_competing_same_case_edits_reject_one_without_repeating_transform` | 저장 성공 수 2, 기대 1 |
| 충돌 경로에서 transform 재실행 | `CasCaseTests.test_competing_different_case_edits_are_merged_without_repeating_transform` | transform 실행 횟수 2/1, 기대 1/1 |
| 예산 상한 검사 제거 | `CasBudgetTests.test_parallel_global_reservations_never_exceed_limit` | 승인 수 12, 기대 6 |
| 예산 비교 `>`를 `>=`로 변경 | `CasBudgetTests.test_migrated_total_counts_once_on_reopen_and_exact_limit_is_allowed` | 정확히 상한인 예약에서 `BUDGET_LIMIT` 발생 |
| 이관액 합산 제거 | 같은 이관액 경계 테스트 | 80센트 경고가 False |
| 실패 예약을 합계에서 제외 | `CasBudgetTests.test_failed_and_completed_reservations_remain_and_finish_is_idempotent` | 합계 0.25달러, 기대 0.50달러 |

남은 원격 인수는 실제 provider의 부재 조건 생성·같은 ETag 동시 쓰기·private 최신 읽기·프로세스 재시작 후 지속성·원격 budget 경합·이관 실행입니다. SDK/HTTP 어댑터가 본 프로토콜을 구현했다는 사실만으로 provider의 원자성을 검증한 것으로 세지 않습니다.

독립 읽기 전용 검토자는 파일 쓰기 fixture 검사 1건을 제외한 메모리 검사 33/33을 0.173초에 통과했고, 별도 Python 재현에서도 결함 0건을 보고했습니다. 실행은 PowerShell here-string을 `.venv/Scripts/python.exe -B -`에 전달했습니다. 이 검토는 한 PC의 별도 에이전트이며 원격 PC 검증이 아닙니다.

```text
OTHER_CASE [('A', 1, 'A1'), ('B', 1, 'B1')] TRANSFORMS 1
SAME_CASE STATE_CONFLICT KEPT A2
AMBIGUOUS_UPDATE writes 1 saved B2 revision 2
GLOBAL_BUDGET accepted 13 blocked 19 total 1.0
FINISH ['failed-cost-uncertain']
```

독립 예산 재현의 분모는 32개 동시 예약이며 이관 9센트+건당 7센트·상한 100센트 조건입니다. 13건 승인·19건 거부로 최종 100센트를 보존했습니다. 독립 검토 중 기본 Python은 `filelock` 의존성이 없어 실패했고 가상환경 Python으로 재실행했습니다. 신원 지침의 `channel/whoami.py`는 내부 읽기 전용 Git 상태를 출력하므로 Git 관련 읽기가 전혀 없었다고 표현하지 않습니다. Git 변경·네트워크·실 SDK 호출은 수행하지 않았습니다.
