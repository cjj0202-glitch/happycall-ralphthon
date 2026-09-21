# 공유 상태의 명시적 최초 준비 도구

**현행 배포 방향:** [DEC-026](../../planning/decisions.md)에 따라 기존 개인 AWS의 해피콜 전용 Lambda+DynamoDB가 대상이다. 이 도구는 `--backend dynamodb`를 지원하며 기존 Vercel 기능도 보존한다. 아래 검증은 오프라인 도구·어댑터 검사이고 실제 인프라 생성·인증·원격 적용·운영 검증은 메인의 별도 증거를 따른다.

2026-09-22 메인 인수 준비. 기존 `scripts`에서 bootstrap/migration/seed 파일과 CAS 최초 생성 호출을 검색했고 중복 도구가 없어 `scripts/bootstrap_deployment_state.py`를 추가했다. 후속 AWS 배정으로 `server/dynamodb_store.py`와 runtime의 `dynamodb` 선택을 연결했다. `ExistingDocumentsStore`의 운영 중 누락 문서 생성 금지는 유지했다. 이 구현 담당자는 실제 Blob/AWS/키 조회/과금 호출을 수행하지 않았으며 실행 담당은 메인이다.

기본 실행은 **오프라인 dry-run**이다. 명시 JSON 입력과 0 이상의 명시 정수 센트 baseline이 필수이고, 환경변수와 네트워크에 접근하지 않는다. 금액을 자동으로 선택하지 않는다. 입력 원문·경로·토큰·저장소 ID·예외 본문을 출력하지 않는다. 출력은 고정 상태/오류 코드, 문서·접수·예약 개수와 금액 합계뿐이다. 입력은 중복 JSON 키·NaN·잘못된 접수 ID/revision·깨진 intake 참조·4MiB 초과를 거절한다. DynamoDB는 메타데이터를 포함한400KiB item 한도에 여유를 두어 UTF-8 JSON payload를350KiB 이하로 더 제한하며 환경/쓰기 접근 전에 검사한다. 원문의 필드/이력/revision을 바꾸지 않고 전체 JSON 객체를 보존한다.

```powershell
# 준비 확인만. 2920은 DEC-026의 최신 공개 예약 증거를 계승하는 보수적 기준이다.
.venv/Scripts/python.exe -X utf8 -B scripts/bootstrap_deployment_state.py --backend dynamodb --cases <명시-접수-JSON-경로> --baseline-reserved-cents 2920

# 과거 호출 중지·기준금액 출처/한도 검토·중복 합산 방지를 확인한 메인이 적용한다.
# 인증은 이미 구성된 프로세스 환경만 사용하며 값은 명령에 넣지 않는다.
.venv/Scripts/python.exe -X utf8 -B scripts/bootstrap_deployment_state.py --backend dynamodb --cases <명시-접수-JSON-경로> --baseline-reserved-cents <검토한센트> --apply --confirm-baseline-reviewed
```

`dynamodb` 적용은 `ONEFLOW_DYNAMODB_TABLE`을 읽고 boto3 표준 자격증명·region 설정을 사용한다. 테이블의 단일 partition key는 `pk`(String)이며 payload는 JSON 문자열, version은 UUID 문자열이다. Lambda의 SDK는 실제 요청 때만 로드하고 자동 재시도를 끈다. `vercel-blob` 적용은 `BLOB_READ_WRITE_TOKEN`, `ONEFLOW_BLOB_STORE_ID`를 프로세스 환경에서 읽는다. 이 스크립트는 `.env`나 Vercel 인증 파일을 자동으로 찾지 않는다. 배포 runtime에는 별도로 해당 `ONEFLOW_STORAGE_BACKEND`와 **같은 baseline**의 `ONEFLOW_BUDGET_INITIAL_RESERVED_CENTS`를 설정한다. 전역 예산은 모든 유료 배포가 같은 저장소의 `oneflow/budget.json`을 사용해야 하며 독립 원장을 만들어 남은 예산을 중복 부여하지 않는다. Lambda에서 backend가 빠지거나 local-json이면 닫힌 상태로 실패한다.

## 기존 상태와 부분 실패

쓰기 전에 `oneflow/cases.json`과 `oneflow/budget.json`을 둘 다 읽어 검사한다. 접수는 유효한 문서이며 명시 입력과 객체 값이 같아야 한다. 기존 접수가 이미 진행돼 달라졌다면 이 도구로 복구하거나 덮어쓰지 않는다. 예산은 실제 `CasBudget` 문서 검증으로 schema·초기액·상한3000·경고2500·예약 ID/금액/상태를 확인한다. 유효한 기존 새 예약 entries는 보존하며 total=initial+모든 예약을 보고한다.

| 원격 상태 | 동작 |
|---|---|
| 두 문서 없음 | budget, cases 순서로 각각 raw CAS `expected_version=None` 생성 |
| 두 문서 존재, 접수/예산 계약 일치 | `already_initialized`, 쓰기 0; 예약액을 다시 더하지 않음 |
| 기존 접수 불일치 또는 기존 예산 baseline/형식 불일치 | 쓰기 전에 거절 |
| cases 존재, budget 없음 | `MISSING_EXISTING_BUDGET`; 소실 원장 재초기화 금지, resume도 불가 |
| budget 존재, cases 없음 | 기본 거절. 실제 부분 생성 경위를 확인하고 `--resume-partial`을 추가한 경우에만 재개 가능 |
| 위 부분 재개에서 예산 entries가 비어 있지 않음 | `PARTIAL_STATE_NOT_PRISTINE`, 접수 재생성 금지 |
| CAS 생성 경합/네트워크 오류/불명확 응답 | 자동 재시도·overwrite·삭제/rollback 없음; 성공 확인 수와 쓰기 시도 수만 보고 |

부분 재개는 baseline이 같은 **예약 entries가 비어 있는 budget-only 상태**만 허용한다. 두 문서는 원자적 트랜잭션이 아니므로 두 번째 쓰기가 실패하면 첫 문서를 남긴다. 단순 재실행으로 자동 복구하지 않으며, 불명확 응답에서는 `createdDocuments`가 실제 저장 개수를 모두 뜻하지 않는다. 메인이 원격 문서를 다시 읽고 보존 여부를 확인해야 한다. 성공 PUT 응답 뒤에도 두 문서를 재조회·검증해야 최종 성공을 출력한다.

## 원장 이관의 한계

baseline은 검토한 합계를 이월하는 값이고 이전 원장의 개별104개 예약, 원문 로그, 과거 접수를 복원하는 기능이 아니다. DEC-026의2920센트는 최신 공개 증거의 보수적 예약 기준을 계승하는 결정이며 공급자 실청구액이나 미수신 원장의 최종 합계를 확정한 것이 아니다. `--confirm-baseline-reviewed`는 과거 호출 중지·금액 출처/한도 검토·중복 합산 방지를 확인했다는 표시다. 원본104건 복원 또는 실청구 최종 확정을 뜻하지 않는다. baseline을0으로 추정하거나 현재 replay의0원 표시로 대체하지 않는다. 과거 합계를 initial에 넣으면서 같은 과거 entries를 다시 더하지 않으며 상한3000센트·기존 문서 불일치/누락 차단은 유지한다.

## 오프라인 검증

`tests/test_deployment_state_bootstrap.py`는 in-memory fake CAS만 사용한다. 최초 생성·입력 보존·동일 재실행 쓰기0·기존 예약 보존·baseline 변경 거절·접수 불일치·원장 소실·부분 실패와 명시 재개·활성 예약이 있는 부분 상태 거절·생성 경합·readback 부재·입력 형식·dry-run 환경 접근0·기준금액 검토 확인 게이트·예외 비밀 비노출을 검사한다. 원격 저장소의 권한·영속성이나 실제 이전 원장의 최종성을 검증한 테스트가 아니다.

Vercel 도구 초기 검사23개 통과 후 AWS 어댑터·runtime·bootstrap 묶음은 **109 passed / 2.05s**, 기존 deprecation warning5개였다. DynamoDB fake는 strong read·최초 생성/오래된 버전 조건 거절·두 인스턴스 경합·공유 예산 상한·응답 유실 무재시도·UTF-8 정확 경계·SDK lazy import/재시도0을 검증했다. runtime 검사는 Lambda 로컬 fallback 차단과 원장 누락 시 analyzer 호출0을 포함한다. 공개 합성 fixture로 DynamoDB CLI dry-run도 확인했으며 접수2개·baseline2920·생성0·쓰기0이었다. 이는 실제 원격 상태나 원본 원장 복원 증거가 아니다. scoped `git diff --check`는 exit0이다. 이 구현 담당자의 키 조회·네트워크·과금·실제 적용은0이다.

DEC-026에 맞춘 확인 플래그·메시지 명칭 정정 뒤 같은 묶음을 재실행해 **109 passed / 1.92s**, 기존 warning5개를 확인했다. 금액 자동 선택이나 저장/예산 조건의 변경 없이 `--confirm-baseline-reviewed`와 `BASELINE_REVIEW_CONFIRMATION_REQUIRED`로 표기를 맞췄다.

```powershell
.venv/Scripts/python.exe -X utf8 -B -m pytest tests/test_dynamodb_store.py tests/test_deployment_state_bootstrap.py tests/test_runtime_storage.py -q -p no:cacheprovider
```
