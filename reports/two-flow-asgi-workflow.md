# 미도착·오출고 신규 접수 ASGI 연속 검증

2026-09-22 01:06 KST / pc1 CJJ / 로컬 보조 에이전트. 독립검토자의 P2 검사 공백 지적을 보완했고 아래 메인 인수 재검을 추가했습니다.

**두 유형의 새 웹접수→정제→사람 수정·확인·재수정→근거 선택→이관→센터 중간/최종 회신→경영주 조회를 실제 ASGI 라우팅과 서비스 코드로 끝까지 실행했습니다. 보완 후 4/4 테스트, ASGI 요청 80건이 기대 응답과 일치했습니다.** 모델 응답과 예산은 작성한 메모리 대조군이므로 실제 모델 정확도·유료 API·기존 실행 서버·배포 성공의 증거가 아닙니다.

## 설계와 소유 범위

- 사용자 과업: 상담원은 원문과 AI 제안을 보존하며 내용을 수정하고, WMS/TMS 근거를 선택해 확인 후 이관합니다. 센터는 남은 조치를 보존하며 중간 회신하고, 확인 완료 후 최종 회신·종결합니다. 경영주는 등록된 결과를 조회합니다.
- 구현 소유: `tests/test_two_flow_asgi_workflow.py`, 이 보고서만 추가했습니다. 제품 코드·fixture·기존 저장 데이터는 변경하지 않았습니다.
- 검증 경로: `create_app()` → OpenAPI/Connexion → 실제 `handlers` → 실제 `CaseService` → 실제 `LiveAnalyzer.normalize_analysis` → `CasCaseRepository(InMemoryCasStore())`.
- 주입 경계: `handlers.service`만 격리 서비스로 연결하고, `LiveAnalyzer`의 provider와 budget을 메모리 대조군으로 주입합니다. 라우트·업무 상태 전이·근거/권한 검증을 mock하지 않습니다.
- 같은 메모리 CAS를 새 repository 객체로 다시 읽어 응답, revision, history, 원문, 사람 수정, 최종 회신 일치를 확인합니다. 이는 프로세스 재시작·클라우드 영속성 증거가 아닙니다.
- `server.handlers.get_runtime_storage`, 실제 SDK 생성, 키 조회는 호출하면 실패하는 sentinel로 보호했습니다. STT 호출도 0회를 assert합니다. 실제 서버/브라우저/소켓 listener를 시작하지 않았고 기존 22건 저장소·예산 원장을 열거나 수정하지 않습니다. TestClient의 in-process ASGI 실행만 사용합니다.

## 실행 기준과 재현

최초 기준 HEAD: `f280e2babb253d381bd466cefb921b28f58828de`. P2 검사 보완·재실행 HEAD: `37de103d1f69959baca9a19e0b1a9ea679c06e23`. 중간 추가된 PC2 도구 파일은 아래 서버 경로를 바꾸지 않았습니다. 아래 12파일의 path/bytes/SHA256 배열을 순서대로 JSON 직렬화(`ensure_ascii=True, sort_keys=True, separators=(',', ':')`)한 SHA256:

`9e32f1adbe28314667503e2175b705cc262210d5f81537ef462316b8f8b2e374`

순서: `server/app.py`, `server/handlers.py`, `server/service.py`, `server/live.py`, `server/analysis_schema.py`, `server/claim_grounding.py`, `server/request_grounding.py`, `server/cas_repository.py`, `server/cas_store.py`, `server/intake_idempotency.py`, `server/openapi.yaml`, `data/fixtures/cases.json`.

주요 파일 SHA256:

| 경로 | SHA256 |
|---|---|
| server/service.py | e9eb913baeca788095a0dc39b9565df1a01458dd570aa973e5cfdc2967a39a5a |
| server/live.py | 4150029e4440dd8d6d843581f181829c825542857cc251def3036827337a5b71 |
| data/fixtures/cases.json | 5edf80669f7def9d3e10ceea910086c41026ff1252fbc638b97641562f3d84f4 |

실행 위치는 저장소 루트입니다.

```powershell
.venv/Scripts/python.exe -B -m pytest tests/test_two_flow_asgi_workflow.py -v -p no:cacheprovider
```

실측: Python 3.12.14 / pytest 9.1.1, 보완 후 정상 검사 `4 passed, 5 warnings in 3.89s`, exit 0. 검사 전후 위 12파일 fingerprint가 동일했습니다. 최종 테스트 파일 SHA256은 `55d4a37b624619c56158aba62296982cdab1d25f195e8d46c7c3fd9b9be03e1d`입니다. 경고 5건은 Starlette/httpx, AnyIO 별칭, Connexion/jsonschema의 deprecated API이며 패키지를 설치·변경하지 않았습니다.

초기 셸 기본 Python 3.14로 실행한 명령은 `No module named pytest`, exit 1로 실제 테스트가 시작되지 않았습니다. 이미 설치된 프로젝트 `.venv` 경로를 명시해 해결했습니다. 첫 변이 결과 출력은 cp949 인코딩 오류로 보고용 상위 명령이 exit 1이었으며, stdout UTF-8과 짧은 assertion 출력으로 수정해 동일 변이 4개를 다시 실행했습니다. 제품 실패를 숨기거나 테스트 기대값을 제품에 맞춰 낮추지 않았습니다.

## 실측 분모와 결과

| 검사 | 실제 실행 | 기대/실측 |
|---|---:|---|
| missing 새 접수부터 경영주 최종 조회 | 1흐름, ASGI 34요청 | 통과, 신규 접수 revision 0→11, history 12건 |
| wrong 새 접수부터 경영주 최종 조회 | 1흐름, ASGI 34요청 | 통과, revision 0→11/history 12건, 수령 1 BOX 보존, 주문 18 EA와 분리 |
| missing 분석 실패→명시 재시도 | 1흐름, ASGI 6요청 | 502 때 원문/draft/revision 보존, 재시도 때 review/revision 1 |
| wrong 분석 실패→명시 재시도 | 1흐름, ASGI 6요청 | 위와 동일 |
| 실제 공급자/실제 STT/예산 원장 접근 | 0/0/0 | 호출 금지 sentinel 및 STT 0회 assert |
| 작성 모델 호출 | 총 6회 | 정상 2 + 실패/재시도 4, 모두 메모리 Mock |

정상 흐름당 HTTP 응답 분포도 실제 response hook으로 수집·assert했습니다: **200×16, 201×3, 403×3, 404×1, 409×5, 422×5, 428×1 = 34**. 실패/복구당 **200×4, 201×1, 502×1 = 6**. 합계 80은 여러 반복 실행을 합산한 실적이 아니라 보완 후 suite 한 번의 요청 분모입니다.

두 정상 흐름에 각각 다음 14개 거절을 실행하고 **CAS payload와 transport version 모두 무변경**인지 대조했습니다. 별도 실패/복구 2개의 502도 무변경을 대조하여 총 30개 거절의 저장 무변경을 확인했습니다.

1. 같은 UUID v4 키로 다른 텍스트 제출 → 409 `IDEMPOTENCY_CONFLICT`.
2. 신규 접수에서 사전 replay 요청 → 409 `REPLAY_NOT_AVAILABLE`.
3. review 상태에서 owner가 내부 접수 수정 → 403 `READ_ONLY_ROLE`.
4. 다른 사건의 근거 ID 선택 → 422 `INVALID_EVIDENCE`.
5. 근거 변경으로 확인이 해제된 상태에서 이관 → 422 `REVIEW_REQUIRED`.
6. 낡은 상담원 form으로 확인 → 409 `STATE_CONFLICT`.
7. expectedRevision 누락 → 428 `REVISION_REQUIRED`.
8. 센터 회신 없는 종결 → 422 `REPLY_REQUIRED`.
9. 상담원 역할의 센터 회신 등록 → 403 `CENTER_ROLE_REQUIRED`.
10. 잔여 조치가 있는 종결 → 422 `ACTIONS_PENDING`.
11. 새 잔여 조치 추가 후 낡은 센터 form의 종결 → 409 `STATE_CONFLICT`.
12. 종결 후 owner의 회신 수정 → 403 `READ_ONLY_ROLE`.
13. 이관/종결된 문의에 재분석 → 409 `ANALYSIS_STATE`.
14. 확인 완료 후 접수 내용 재수정으로 확인이 해제된 상태에서 이관 → 422 `REVIEW_REQUIRED`.

정상 대조군에서는 점포/대상/부서를 확인하면 미도착의 null 수량·단위를 유지한 채 이관됩니다. 동일 접수 재전송은 생성 직후와 종결 후 모두 같은 case를 반환하며, 종결 후에는 최신 revision/회신을 돌려줍니다. 기존 fixture 2건도 최종 전체 값이 초기 값과 같음을 대조합니다. 원문 텍스트·transcript·정제된 AI analysis는 사람 수정과 센터 회신 이후에도 불변이고, 사람 수정은 `intake.request`에 별도로 남습니다.

## 검증자 자체의 변이 대조

`CaseService.patch` 소스를 읽어 별도 Python 프로세스의 메모리에서만 다음 조건을 `if False:`로 바꿨습니다. 제품 파일을 수정하지 않았습니다. 각 변이에서 동일 missing 연속검사를 실행했고, 모두 pytest exit 1과 assertion 실패로 검출했습니다.

| 제거한 가드 | 거짓 성공 | 검사 결과 |
|---|---|---|
| reviewConfirmed 확인 | 이관 200, 기대 422 | 검출 |
| pendingActions 종결 제한 | 종결 200, 기대 422 | 검출 |
| expectedRevision 충돌 검사 | 낡은 form 200, 기대 409 | 검출 |
| owner 읽기 전용 | review 접수 수정 200, 기대 403 | 검출 |

재현할 때 다음 Python을 `.venv/Scripts/python.exe -B -`에 전달합니다. 원본 파일을 쓰지 않으며 각 변이는 별도 프로세스 안에서 폐기됩니다.

```python
import inspect, textwrap, sys, pytest
import server.service as module
old = 'if case.get("reviewConfirmed") is not True:'  # 표의 가드별로 교체
source = textwrap.dedent(inspect.getsource(module.CaseService.patch))
assert source.count(old) == 1
namespace = dict(vars(module))
exec(compile(source.replace(old, 'if False:'), '<memory-mutant>', 'exec'), namespace)
module.CaseService.patch = namespace['patch']
sys.exit(pytest.main([
    'tests/test_two_flow_asgi_workflow.py::test_new_text_to_center_final_reply_and_owner_read[missing]',
    '-q', '-x', '-p', 'no:cacheprovider'
]))
```

나머지 `old` 값은 `if case.get("pendingActions"):`, `if case["revision"] != expected_revision:`, `if role == "owner":`입니다. 이 명령의 **예상 종료코드는 1**입니다. 정상 원본 suite의 예상 종료코드 0과 혼동하지 않습니다.

### 독립검토에서 살아남은 추가 변이와 보완

독립검토자 `clova_audio_intake_plan`이 메인 인수 전에 P2 검사 공백을 보고했습니다. 최초 테스트 SHA `abac9cd75b5becded45424214be2468699782f1c8c9055c9de1a20d2c7b70713`에서는 사람 수정이 최초 확인 전에만 이루어져 이미 `reviewConfirmed=False`였습니다. 따라서 `server/service.py`의 접수 수정 분기에서 확인을 해제하는 한 줄을 메모리로 제거해도 missing 연속검사 **1 passed**로 변이가 살아남았습니다. 이 생존 결과는 독립검토자의 실제 재현을 메인이 전달한 증거이며, 이 보완 작업에서 원래 공백을 중복 재실행한 실적으로 세지 않습니다. 최초 suite의 4/4·74요청·저장 무변경 28건은 당시 실행 결과로 보존하지만 해당 가드까지 검증한 것으로 해석하지 않습니다.

두 유형의 연속 흐름에 **확인 완료(revision 3, true)→접수 내용 재수정(revision 4, false)→재확인 없는 이관 422/저장 무변경→재확인(revision 5, true)** 단계를 추가했습니다. 재수정 후 원문·transcript·AI analysis 보존과 수정된 `intake.request`도 대조합니다. 이후 기존 근거 선택/확인/이관/센터 절차를 이어가므로 최종 revision 11/history 12가 됩니다.

보완 후 추가 변이는 기존 4개 가드 변이와 별도로 실행했습니다. 접수 수정의 확인 해제만 제거한 **1개 변이 × missing/wrong 2유형**에서 모두 `assert (4 == 4 and True is False)`로 실패했습니다. 실측 `2 failed, 6 warnings in 1.58s`, pytest exit 1, 변이 검사기 exit 0입니다. 정상 suite 4/4와 함께 검출 여부를 확인했으며 제품 소스는 수정하지 않았습니다. 기존 4개 가드 검출은 앞 절의 최초 실행 증거이고 이번 결과를 더해 한 번에 5개를 재실행했다고 쓰지 않습니다.

추가 변이 재현 코드:

```python
import inspect, textwrap, sys, pytest
import server.service as module
source = textwrap.dedent(inspect.getsource(module.CaseService.patch))
old = '            case["reviewConfirmed"] = False\n            self._validate_source_context(case)'
assert source.count(old) == 1
namespace = dict(vars(module))
exec(compile(source.replace(old, '            self._validate_source_context(case)'),
             '<intake-invalidation-removed>', 'exec'), namespace)
module.CaseService.patch = namespace['patch']
sys.exit(pytest.main([
    'tests/test_two_flow_asgi_workflow.py::test_new_text_to_center_final_reply_and_owner_read',
    '-q', '-p', 'no:cacheprovider'
]))
```

예상은 두 유형 모두 실패하고 종료코드 1입니다. 정상 소스에서의 기대값은 4/4 PASS입니다.

## 메인 인수 재검

2026-09-22 01:08 KST / pc1 CJJ. 메인은 최종 테스트 SHA256 `55d4a37b624619c56158aba62296982cdab1d25f195e8d46c7c3fd9b9be03e1d`를 대조하고 `.venv/Scripts/python.exe -B -X utf8 -m pytest tests/test_two_flow_asgi_workflow.py -q -p no:cacheprovider`를 실행했습니다. **4 passed, 5 warnings in 4.13s**, exit 0입니다. 실제 연속 경로의 확인 완료 후 재수정·이관 거절·재확인 단계와 80요청/저장 무변경 30건의 assertion을 코드로 대조했습니다. 이전 74/28과 합산하지 않습니다. 독립 검토의 살아남은 변이와 보완 후 두 유형 검출 결과를 함께 보존하며, 이 결과로 실제 브라우저·실모델·영속 저장·배포까지 인수하지 않습니다.

## 남은 검증

이번 검사는 텍스트 ASGI 계약 2유형과 실패복구에 한정됩니다. 통화 종료·실제 음성 재생/STT·실제 모델 정확도·브라우저 CORS·WMS/TMS 화면 클릭·CCTV 재생·로그인 인증·다른 프로세스의 저장 지속·실제 배포·동일 릴리스 6회 UI 완주·사람 사용성 검증은 증명하지 않습니다. 데모 `X-Demo-Role`은 실제 인증이 아닙니다. 기존 로컬 API의 소스 드리프트나 정책 거부, Blob 권한 문제를 우회하거나 해소했다고 쓰지 않습니다.

메인은 소유 파일 diff, 재현 결과, 최신 서버 변경 영향을 독립 확인한 뒤 명시 경로로 커밋합니다. 원격 pc2/3/4의 수행 실적으로 세지 않습니다. 공식 점수와의 연결은 실제 경로 실행·반례·변이 검출이라는 검증 증거이며 예상 점수나 제품 완료율로 환산하지 않습니다.
