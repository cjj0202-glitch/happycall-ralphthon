# 알림 의도 원자 저장 1단계 구현·검증

2026-09-22 · pc1 메인 하위 구현 · 설계 기준 `853e215d8ef7fba7062109f7e2d66aa4c9a216d1`, 최종 검사 당시 HEAD `31dbd6646bdb60172ff50b5bcd6328556fd399e9`

접수 이관과 센터 회신의 알림 의도를 접수와 같은 저장에 포함했습니다. 독립 검토에서 발견된 저장 경계 두 건을 보완한 뒤 신규 검사 72개와 기존 영향 범위를 합친 최종 실행은 140 PASS·48 subtests PASS·실패 0·skip 0·exit 0입니다. 모든 새 의도는 `not_connected`이며 Teams·카카오톡으로 실제 발송하지 않습니다. 제품 소스 인수, 실행 중 API 반영, 외부 수신 검증은 각각 별도 단계입니다.

## 설계와 변경 범위

착수 전에 [상세 설계](../planning/notification-outbox-phase1.md)와 역할별 알림 정본, 실제 `CaseService.patch`·JSON/CAS 저장소를 읽었습니다. 소유 파일은 신규 `server/notifications.py`, 기존 `server/service.py`, 신규 `tests/test_notification_outbox.py`, 본 보고서 네 개입니다. repository·UI·공통 타입·OpenAPI·묶음 빌더는 다른 작업자의 소유이며 수정하지 않았습니다.

`CaseService.patch`는 기존 역할·revision·전이·필드·근거·검토 확인·미완료 조치 검증을 마친 뒤 같은 transform 안에서 다음 생산자를 호출합니다.

```python
append_notification_intents(
    case: dict,
    *,
    previous_status: str,
    previous_reply: str | None,
    created_at: str,
) -> None
```

`created_at`은 이 저장의 `case.updatedAt`과 같습니다. 내부 `case.revision`은 저장 전 값이므로 각 의도의 `caseRevision`은 여기에 1을 더하며 repository가 실제 저장하는 revision과 일치합니다. 저장 후 별도 기록이나 외부 부작용은 없습니다.

| 확정 변경 | 새 의도 | 논리 수신 대상 |
|---|---:|---|
| draft/review → handed_off | handoff 1 | teams / center / 허용 부서 ID의 해시 |
| 이관 이후 회신 본문 변경, 종결 전 | interim_reply 1 | teams / counselor / caseId의 해시 |
| 센터 closed 전이 | final_reply 2 | teams / counselor 및 kakao / owner |
| 본문과 종결을 같은 PATCH로 저장 | final_reply 2 | 중간 회신 의도는 생성하지 않음 |
| 기존 회신을 유지한 채 조치 완료 후 종결 | final_reply 2 | PATCH 본문에 reply가 없어도 생성 |
| 같은 회신 재저장·동일 상태 저장·조치 목록만 변경 | 0 | 기존 의도 보존 |
| 단순 조회·초안 부서 편집·분석 | 0 | 기존 필드 미존재 상태도 보존 |

11개 필드는 `schemaVersion`, `id`, `caseId`, `caseRevision`, `kind`, `channel`, `recipientRole`, `recipientRef`, `createdAt`, `status`, `reason`입니다. schemaVersion은 정수 1입니다. recipientRef는 `역할:SHA256(원본 식별값의 UTF-8)`이며, owner는 저장된 `intake.storeId`만 사용하고 상위 `store.id`로 대체하지 않습니다. owner 식별값이 null·빈 문자열·공백이면 ref=null, reason=`missing_recipient`입니다. 나머지는 reason=`delivery_not_configured`입니다. counselor 식별값은 현재 담당자 계정이 아닌 사건 단위의 논리 대상이며 실제 수신자 검증으로 해석하지 않습니다.

ID는 `[1, caseId, caseRevision, kind, channel, recipientRole, recipientRef]`를 `ensure_ascii=False, separators=(",", ":")` JSON으로 직렬화한 SHA256 소문자 64자리입니다. 시각과 회신 본문은 ID 재료가 아닙니다. 같은 ID는 다시 추가하지 않습니다. PATCH transform 진입 시 저장된 outbox를 별도로 검사하여 기존 기록의 revision이 현재 저장 revision 이하인지 확인합니다. 생산자 내부에서는 같은 transform의 두 번째 호출을 멱등하게 처리하기 위해 새 revision의 기록까지 허용합니다. 이 두 검증의 입력 경계를 분리했습니다.

기존 outbox가 깨진 배열·레코드·필드·스키마·역할/채널·식별값·시각이면 원시 내용을 노출하지 않고 `STORAGE_INVALID(503)`로 거절합니다. counselor ref는 해당 사건의 caseId에서 재계산한 값과 같아야 합니다. 과거에 변했을 수 있는 owner/center의 원천 값에는 같은 재계산을 적용하지 않고 기존 유효 기록을 보존합니다. 원본 저장 문서는 오류 시 보존하며, 조회에서 과거 기록을 고치거나 소급 생성하지 않습니다.

## 수정 전 반례와 추가 검토

신규 양성 검사를 먼저 작성하고 기존 서비스를 실행했습니다.

```text
.venv/Scripts/python.exe -B -X utf8 -m pytest -p no:cacheprovider
  tests/test_notification_outbox.py::test_handoff_interim_final_are_atomic_and_reopen_with_same_revision
  -q --tb=short -x
1 failed in 1.71s, exit 1
```

임시 JSON에서 이관은 revision 1·status handed_off로 저장됐지만 outbox는 0개여서 기대 1개에 실패했습니다. 이 실패는 기존 기능이 없다는 실행 근거이며 실패를 삭제하거나 PASS로 재분류하지 않습니다.

첫 구현 48 PASS/3.90초 이후 메인 검토에서 기존 저장 문서의 부서 ID 검증 공백을 지적했습니다. 원래 서비스는 PATCH 본문에 `departmentId`가 들어 있을 때만 허용 목록을 대조했고, 본문에 부서가 없는 이관에서는 저장된 부서가 문자열인지 확인했습니다. `UNREGISTERED-CENTER`를 가진 임시 사건으로 다음 반례를 실제 재현했습니다.

```text
.venv/Scripts/python.exe -B -X utf8 -m pytest -p no:cacheprovider
  tests/test_notification_outbox.py::test_legacy_unregistered_department_cannot_become_an_intent_recipient
  -q --tb=short -x
1 failed in 1.47s, exit 1; DID NOT RAISE DemoError
```

이관 gate에서 현재 `self.departments()`의 허용 목록을 추가 대조하도록 두 줄을 보완했습니다. 고정 기본 부서 세 개를 생산자에 하드코딩하지 않았습니다. fixture에 등록된 `custom-center`는 정상 허용하고, 등록되지 않은 legacy 부서는 `INVALID_DEPARTMENT(422)`로 저장 없이 거절하는 양성/음성 검사를 JSON과 CAS 양쪽에 추가했습니다. 기존 역할별 허용 범위는 변경하지 않았습니다.

### 독립 검토에서 발견된 P1 두 건

첫 영향 실행의 124 PASS·48 subtests PASS·6.11초 결과만으로 인수하지 않았습니다. 별도 검토자가 다음 두 범주를 지적했고, 임시 JSON과 메모리 CAS에서 같은 의미의 반례를 직접 실행했습니다.

1. 현재 revision 10의 저장 문서에 미래 `interim_reply` revision 11 기록이 미리 들어 있으면, 새 회신 저장이 revision 11로 성공하면서 새 의도의 ID가 기존 미래 기록과 같아 생성이 억제됐습니다. 이전 생성 시각이 남고 새 회신 사건은 별도로 기록되지 않았습니다.
2. 사건 A의 기존 `counselor` ref를 사건 B의 해시로 바꾸고 ID까지 일관되게 다시 계산하면 그대로 보존됐습니다. counselor 원천은 caseId로 고정되므로 ID 자체의 일관성만 확인해서는 충분하지 않았습니다.

수정 전 새 경계 검사 두 함수의 실행 결과는 다음과 같습니다.

```text
test_stored_event_cannot_reserve_the_next_revision_and_suppress_new_reply
test_stored_counselor_binding_is_case_fixed_but_other_roles_preserve_history
4 failed, 8 passed in 1.94s, exit 1
```

실패 네 건은 미래 revision 11 × JSON/CAS와 다른 사건 counselor × JSON/CAS의 `DID NOT RAISE`였습니다. 동시에 현재 revision 10의 정상 기록, 이미 거절하던 revision 12, 과거 owner/center ref를 보존하는 여덟 양성·경계 대조도 실행했습니다.

`validate_stored_notification_outbox(case)`를 transform 진입 시 호출하여 기존 배열에는 `caseRevision <= 현재 저장 revision`을 적용했고, 생산자의 같은 transform 내 두 번 호출에는 별도의 next-revision 허용을 유지했습니다. counselor ref의 caseId 바인딩도 추가했습니다. 이 보완 직후 신규 파일은 68 PASS/2.29초였으며, 두 가드를 다시 제거한 변이 네 실행을 추가한 최종 범위는 아래와 같습니다.

## 검증 범위와 실제 결과

모든 저장 경로는 pytest 임시 디렉터리의 합성 JSON 또는 `InMemoryCasStore`입니다. 실제 `.local/cases-store.json`·사용자 원장·예산 원장·시크릿을 열지 않았습니다. 실제 API·새 서버·브라우저·네트워크 공급자·실모델 호출은 0회입니다. 제공자 생성과 키 조회가 일어나면 실패하도록 새 fixture에 sentinel을 두었습니다. 기존 ASGI 검사는 in-process TestClient이며 실제 listening 서버를 만들지 않습니다.

| 검증 묶음 | 실제 대조 |
|---|---|
| 정상 연속 흐름 | 두 유형 × JSON/CAS에서 이관1 → 중간회신1 → 같은 본문0 → 조치만 변경0 → 기존 회신 그대로 종결2; 재독출 문서와 반환값 일치 |
| 동일 요청/버전 | 낡은 revision은 STATE_CONFLICT, 최신 revision 동일 의미 재저장은 새 의도0; 종결 이후 수정 잠금 보존 |
| 음성 검사 | 미확인 이관·owner 변경·미완료 종결·낡은 버전·직접 주입·역할 위반·빈 회신·종결 후 변경 8종 × 저장소2; 원본 문서/버전 불변, 생산자 호출0 |
| JSON 확정 실패 | 임시 파일에는 변경 접수와 의도1이 함께 존재; os.replace 직전 실패 후 기존 bytes 불변, 저장 의도0 |
| CAS 확정 미저장 | transform/생산자1회·CAS3회 후 STORAGE_BUSY; 시도 payload마다 의도1, 실제 문서·버전 불변 |
| 다른 사건 CAS 경합 | 생산자1회·CAS2회; 다른 사건의 승자 수정 보존, 대상 사건에 의도 한 세트 및 저장 revision 일치 |
| 같은 사건 CAS 경합 | 생산자1회·CAS1회 뒤 STATE_CONFLICT; 승자 수정만 보존, 패자 의도0 |
| 성공 후 응답 유실 | CAS 저장 뒤 TimeoutError; 재조회에는 revision1·의도1 보존. 낡은 재시도 거절, 최신 동일 의미 저장에도 기존 의도1 유지 |
| 개인정보·대상 분리 | 원문·욕설·전화번호·URL sentinel은 outbox에 없음. sourceText/reply 자체는 그대로 보존. 두 사건의 event ID/owner/counselor ref 분리 |
| legacy/비정상 | 읽기만 하면 bytes/CAS 버전 불변·배열 생성0. owner 식별 null/빈/공백은 missing_recipient; malformed 배열4종 × 저장소2는 원본 보존 거절 |
| 저장된 기록 경계 | 현재 revision10 기록은 정상 신규 의도 추가, 미래11/12는 거절·문서 불변; 다른 사건 counselor ref 거절, 과거 owner/center ref는 보존 |

최종 실행 명령:

```text
.venv/Scripts/python.exe -B -X utf8 -m pytest -p no:cacheprovider
  tests/test_notification_outbox.py tests/test_demo_backend.py
  tests/test_cas_storage.py tests/test_two_flow_asgi_workflow.py
  -q --tb=short --disable-warnings -ra
140 passed, 5 warnings, 48 subtests passed in 4.41s
exit 0
```

이전 중간 결과는 신규 파일 `56 passed in 2.02s` 및 영향 범위 `124 passed, 5 warnings, 48 subtests passed in 6.11s`였고, 둘 다 exit 0이었습니다. 이 값은 독립 P1 지적 이전 결과로 보존합니다. 최종 140개에는 신규 파일 72개가 포함됩니다. 140개와 48개 하위 사례는 서로 다른 분모이며 합쳐 독립 검사 188개라고 주장하지 않습니다. 최종 실행에 실패·skip은 없고 경고 5개는 숨겨 성공으로 지우지 않았습니다.

## 변이가 실제 반례에서 발화하는지

생산 파일을 바꾸지 않고 메모리에서만 다섯 변이를 컴파일해 원래 검사를 실행했습니다. 아래 변이 검사는 정상 테스트가 변이에서 실패해야 PASS가 되며, 내부 실패 지점을 명시합니다.

| 변이 | 원래 검사에서 검출되는 차이 | 실행 분모 |
|---|---|---:|
| event ID 중복 억제 조건을 True로 변경 | 두 번째 같은 이벤트 호출 후 배열이 1개에서 2개로 늘어 불변 assertion 실패 | 1 |
| 같은 transform 안의 의도 추가를 repository.update 반환 후로 이동 | JSON 교체 직전 payload에 의도가 0개여서 1개 기대 assertion 실패 | 1 |
| legacy 이관 부서 허용 목록 검사를 제거 | 비등록 부서를 거절하지 않아 DID NOT RAISE 발생 | JSON/CAS 2 |
| 저장 문서 진입 revision 검사를 제거 | 미래 revision11 기록이 새 회신 의도를 억제하는 입력을 거절하지 않아 DID NOT RAISE 발생 | JSON/CAS 2 |
| counselor ref의 사건 바인딩 검사를 제거 | 다른 사건의 ref를 거절하지 않아 DID NOT RAISE 발생 | JSON/CAS 2 |

총 5개 결함 범주·8개 변이 실행을 검출했습니다. 실제 발송을 허용하는 변이나 실제 외부 채널 호출은 만들지 않았습니다.

## 인수용 소스 동결

P1 보완 이후 최종 실행 직후 동결한 세 파일의 SHA256은 다음과 같습니다. 최초 인수 후보의 지문은 아래 이력에 따로 보존합니다.

| 파일 | SHA256 |
|---|---|
| `server/notifications.py` | `79b3a0af7e896aa9d3519fe7575bf1a1717e140bd3e3fee0dc8a54c7cab037a9` |
| `server/service.py` | `af8db5c0344defd961e53c68e1697813544d8a2d2571ee46d91e805d14ea6a3f` |
| `tests/test_notification_outbox.py` | `52a29d293da69491060ddd6b1bc5f6f5f0f9e2b054cd60baf25e40518e23842b` |

P1 보완 전 124 PASS 시점의 source 지문: notifications `83429a7b90329bb555def4a37bb18ae4b5bf13bd95c301f904fe678e2cf20a75`, service `f62d9e918a5c3de227876e09b62f7414825eeb8ecd2d7aef86fe58831652e91b`, test `b8708309d3dd1158b90a8120e437fcdac94096f8b35c172a842e434b6fc83159`입니다. 이를 현재 통과 소스로 혼동하지 않습니다.

메인에게 소스/검사 동결을 전달했습니다. 메인이 별도 독립 검토·UI 인수·빌더 포함·명시 경로 커밋을 진행합니다. 본 작업은 시제품의 논리 알림 의도 저장이며 실제 계정 인증, 실제 담당자 매핑, 공급자 연결, 전송 결과 저장 worker, 외부 채널 수신 또는 실행 중 서버 반영을 완료했다고 표시하지 않습니다.

## 독립 재현과 메인 인수

02:44 KST 읽기 전용 검토자가 위 최종 소스 SHA를 실행 전후 대조했습니다. 자기 입력과 메모리 CAS를 실제 CaseService에 넣어 이전 P1 두 건을 재검했습니다. 미래 revision11/12, 다른 caseId, 다른 사건 counselorRef는 각각 STORAGE_INVALID503·문서 불변·CAS 쓰기0이었습니다. 정상 revision10 행은 불변이며 새 revision11 행과 생성 시각이 정확히 추가됐습니다.

다른 사건 경합은 producer1/CAS2/기존1+최종2, 같은 사건 경합은 STATE_CONFLICT·producer1/CAS1/신규0, 저장 후 응답 유실은 TimeoutError 뒤 재조회 기존1+최종2였습니다. 동일 transform helper 재호출은 의도1개를 유지했습니다. 명령은 `.venv/Scripts/python.exe -X utf8 -B -`, exit0, 파일 쓰기0·네트워크0입니다. 최초 future 입력의 의도1개/새 생성 시각 불일치와 다른 counselor 입력의 잘못된 행 수용을 보존하고, 수정 후 거절 결과와 구분했습니다.

이 독립 검토는 전체 suite 재실행이 아니며 실제 원장·실행 API·외부 발송을 검사하지 않았습니다. 현재 코드와 격리 저장 계약의 인수 범위입니다.
