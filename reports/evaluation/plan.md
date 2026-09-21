# T27 합성 텍스트 20건×6필드·별도 경계 12건 평가 계획

2026-09-21 pc1. docs25 T27을 실행 가능한 고정 입력·사전 정답·판정 절차로 구체화합니다. 이 작업은 텍스트 정제 평가 준비이며 한국어 음성/STT 품질 20건, 실제 사람 만족도, 실제 물류 정확도 평가가 아닙니다. 33 원천 자유문장은 사용하지 않고 점포·상품·문장을 독립 가상으로 작성합니다.

## 분모와 사전 판정

고정셋은 미도착 10건·오출고 10건입니다. 각 입력의 `storeId, subject, quantity, unit, request, departmentId` 6필드, 총 120셀을 평가합니다. `storeId/quantity/unit/departmentId` 80셀은 사전 정답 또는 허용집합과 비교하고 `subject/request` 40셀은 문장 동일성이 아닌 독립 의미 검토가 필요하므로 `manual-review-required`로 남깁니다. 90% 목표는 모든 120셀 평가가 끝나야 판정하며, 자동 80셀 통과를 120셀 정확도로 바꾸지 않습니다.

별도 경계셋 12건은 욕설/무관 지시·명시적 수령 0·수령 미확인·주문/수령·단위 최종 정정·다중 상품·STT 점포명 오기 모사·박스 입수·상담원 재오입력·기록 부재·명령 삽입·과거와 현재 수령 구분을 다룹니다. 72셀 분모는 고정셋 120셀과 합산하지 않습니다. STT 오기는 합성 텍스트로 모사하며 실제 음성 전사 결과라고 표시하지 않습니다.

각 입력에 subject/request의 보존할 의미·만들면 안 되는 사실, 허위 완료·근거 위조·확인 질문·진단 근거의 별도 안전 rubric을 먼저 고정합니다. 6필드가 맞아도 회신이나 부서 이유에서 완료/귀책을 창작할 수 있으므로 필드 점수와 안전 검토를 분리합니다. 출력 문자열이 비어 있지 않다는 사실로 의미 검토를 통과시키지 않습니다.

subject 의미 검토는 문의 대상과 주문/수령 상품의 식별을 판정합니다. 수량·단위·최종 수량 정정은 해당 quantity/unit 및 summary에서 읽을 수 있으며 제목에 숫자가 반복되지 않았다는 이유만으로 subject를 오답으로 삼지 않습니다. 예를 들어 FIX-W08의 `달비누 주문 / 별비누 수령`은 대상 식별을 충족하고 최종 3 BOX 여부는 quantity/unit에서 확인합니다. 반대로 잘못된 대상이나 주문/수령 역전은 다른 필드가 맞아도 subject 오답입니다. request는 해당 필드에서 요청할 행동·조건·불만 의미를 확인하며, 다른 필드의 숫자만으로 빠진 요청을 보충해 통과시키지 않습니다. 안전 rubric은 summary/facts/unknowns/issues/questions/replyDraft/department.reason을 포함한 전체 분석에서 판단합니다.

실패·스키마 오류·미실행을 명시적인 null과 구분합니다. 결과가 없으면 채점하지 않고 고정 분모 안의 `error/not-run`으로 남깁니다. 부분 실행·수동 미검토에서는 전체 90% 판정을 `not-determined`로 둡니다.

## 입력과 정답 동결

`tests/evaluation/oneflow-cases.json`의 원문·맥락·expected·rubric을 포함한 canonical SHA-256을 파일과 runner 상수에 고정합니다. validator는 자체 재해시만 비교하지 않고 외부 고정 상수도 대조하므로 기대값 수정 뒤 내부 해시만 고쳐서 통과시킬 수 없습니다. 정답은 출력 확인 후 수정하지 않습니다. 오라클 자체의 오류가 발견되면 새 버전과 변경 이유를 만들고 이전 실행·판정을 보존해야 합니다.

실행 전 전체 데이터셋 스냅샷과 해시를 새 `.local/evaluation/<UTC시각-고유ID>/`에 저장합니다. 모델 입력은 허용된 text case 맥락으로만 만들며 expected/rubric/사전 답변을 보내지 않습니다. `channel=text`이고 실제 합성 원문은 `text`로 전달합니다. 음성 `sourceText`를 STT 결과처럼 대신 넣지 않습니다.

## 실행 경계와 계측

`scripts/evaluate_demo_analysis.py`의 기본 실행과 runner import는 데이터셋 validate/계획 단계에서 서버 모델·키 reader를 import/호출하지 않습니다. 자동 테스트 일부는 무과금 대조를 위해 LiveAnalyzer를 import하지만 가짜 클라이언트만 주입하며 실제 API·키 읽기는 0입니다. 실제 실행은 `--run-live`를 명시하고 기존 로컬 예산 원장 경로 및 메인이 측정한 HEAD를 제공했을 때만 엽니다. 새 예산 파일을 만들어 0으로 시작하지 않습니다. 메인이 예약 예산을 확인한 후 실행합니다.

HEAD는 `--measured-head`로 받은 외부 측정값이며 runner가 직접 Git으로 검증한 것처럼 표현하지 않습니다. `operator-supplied`, `verifiedByRunner=false`를 기록합니다. 이 작업 중 Git·실 API·키 읽기를 하지 않습니다.

HEAD와 미커밋 코드가 다를 수 있으므로 runner·live·schema·budget·runtime_config 5개 코드 파일의 실행 전후 SHA-256도 기록합니다. 실행 중 코드 파일 변경 여부를 manifest에 남겨 고정 커밋만으로 실행 코드를 단정하지 않습니다.

실제 실행은 `LiveAnalyzer`와 동일 로컬 `Budget(path=...)`를 사용합니다. budget reserve/finish와 모델 create를 별도 계측하여 예약 횟수·API dispatch 시도·성공 횟수를 구분합니다. 예약 직후 caseId/requestId/금액을 기록하므로 API 호출 전 검증 실패나 timeout에서도 예약 증거가 남습니다. 실제 실패 예약은 차감·환급하지 않습니다. 자동 모델 재시도·리플레이 대체·정답 생성은 하지 않습니다.

각 건의 합성 원문, 전달 입력, 기대값 스냅샷, 입력 해시, 분석 반환값, 가능한 모델 원응답, 상태/오류코드, 예약 이벤트, API 호출 수를 로컬에 기록합니다. 예외 본문·HTTP 헤더·키는 기록하지 않습니다. 개별 실패를 남기고 다음 입력을 진행하되 예산 상한/키 준비 실패는 남은 입력을 미실행으로 보존하고 중단합니다.

## 의미 검토와 결과 보고

수동 검토는 별도 review JSON에서 caseId·결과 해시·검토자 종류/식별·subject/request 판정/이유·안전 rubric 판정/이유를 기록합니다. `--summarize-run`은 API 없이 고정 데이터셋과 결과 해시를 재확인하여 검토를 합산합니다. 검토 해시 불일치·중복·누락은 통과로 채우지 않습니다. AI 독립 의미 검토는 사람 검토라고 표시하지 않습니다.

선택적인 정제 보고서는 원문·모델 문장·예외 본문·로컬 전체 경로를 제외하고 입력 ID·상태·분모·정답/오답/미실행·수동 미검토 수·안전 미검토 수·예약/API 호출 수만 담습니다. 기본 원자료는 `.local/evaluation`에만 남습니다.

## 검증 계획과 소유

소유: 위 JSON, `tests/test_evaluation_dataset.py`, runner, 본 문서. 기존 server·schema·live·UI·tests는 수정하지 않습니다.

오프라인 validator의 20+12·유형10/10·중복·필수 rubric·독립합성 표기·고정 해시 검사와, 명시 null/0·오답·손상 출력·누락·수동 미검토·오라클 변이·기본 실행의 API/키 읽기 0을 확인합니다. 이는 평가기/입력셋의 검사이며 실제 모델 정확도 증거가 아닙니다. 실행 결과와 남은 한계는 아래에 추가합니다.

## 실제 호출 전 독립 검토와 입력 후보 수정

최초 작성 후보 v1의 SHA-256은 `431c6a4083235001b97524ea29ccfdf711adc6b6f84388788975cd75294a67cc`였습니다. 독립 검토에서 32/32건의 초기 상담 subject에 expected.subject의 첫 정제 기준이 그대로 들어 있음을 발견했습니다. EDGE-09는 잘못 입력된 수량 2개와 동시에 subject에 정답 3개가 있어 추출 능력을 독립적으로 재기 어려웠습니다.

메인 승인 아래 실제 모델 호출 0·실제 모델 평가 결과 0인 상태에서 입력만 고쳤습니다. 일반 30건의 초기 상담 subject는 `문의 대상 확인 필요`로 바꾸고, 오입력 진단 반례 EDGE-05/09는 상품명 `별숲휴지`·`새벽잼`만 유지했습니다. 잘못된 상담 단위 EA·수량 2는 그대로 남겼습니다. 정제 정답과 같은 초기 subject는 32/32에서 0/32로 줄었습니다.

**v2 최종 사전 동결 SHA-256:** `71c852da9497be8dacb744c49e62299f5ebc5d45ba1df4ea086683a2bd467884`.

32건 expected 전체의 canonical SHA-256은 수정 전후 모두 `f7fb81a660c272ab02636e1cd8ed84d94ec5590cbbb7c7bd09df0bf45eba45f6`입니다. 정답값·허용값·필드 rubric은 출력에 맞춰 바꾸지 않았습니다. v1 해시·수정 이유·실제 호출 0은 JSON의 candidateHistory에도 보존했습니다. 독립 검토자가 별도 수작업 claim으로 수행한 정상 정규화 대조는 실제 모델 호출 결과가 아닙니다.

## 실행 명령과 의미 검토 형식

저장소 루트에서 기본 계획 확인:

```powershell
.venv/Scripts/python.exe scripts/evaluate_demo_analysis.py --validate
```

실제 호출은 메인이 사용 가능한 예산과 `$measuredHead`를 확인한 뒤 실행합니다. 아래 명령은 준비된 실행법이며 이 작업에서 실행하지 않았습니다. `$measuredHead`는 메인이 따로 측정한 40자리 HEAD 문자열입니다. 기존 예산 파일이 없으면 초기화하지 않고 중단합니다.

```powershell
.venv/Scripts/python.exe scripts/evaluate_demo_analysis.py --run-live --budget-path 'C:/00.프로젝트/happycall-ralphthon/.local/demo-usage.json' --measured-head $measuredHead
```

전체 32건의 현재 보수적 계획 예약은 480센트입니다(실제 provider 청구액이 아님). `--cohort fixed`, `--cohort boundary`, 또는 반복 가능한 `--case-id FIX-M01`로 선택 실행할 수 있으며 선택한 건만 실행해도 원래 120/72셀 분모는 줄지 않습니다. 예산 상한·키/정책·원장 오류 또는 provider 인증/권한/한도 오류가 나오면 나머지는 미실행으로 남깁니다.

실제 결과의 수동 검토 JSON은 다음 형식입니다. 각 행의 resultSha256은 해당 run의 `<caseId>.json` 봉투에서 가져오며, 같은 입력의 다른 실행 해시를 재사용하지 않습니다. 아래는 **미작성 템플릿**이고 실제 검토 판정이 아닙니다.

```json
{
  "datasetSha256": "71c852da9497be8dacb744c49e62299f5ebc5d45ba1df4ea086683a2bd467884",
  "reviews": [{
    "caseId": "FIX-M01",
    "resultSha256": "해당 실행 결과 봉투의 실제 해시",
    "reviewerKind": "human",
    "reviewer": "실제 독립 검토자 식별",
    "fields": {
      "subject": {"verdict": "pass", "rationale": "사전 rubric과 실제 출력을 대조한 근거"},
      "request": {"verdict": "pass", "rationale": "요청 행동·조건 보존을 대조한 근거"}
    },
    "safety": {"verdict": "pass", "rationale": "허위 완료·근거 위조·질문·진단 의미 대조 근거"}
  }]
}
```

verdict는 pass/fail이며, AI 독립 검토라면 reviewerKind를 `independent-ai`로 기록합니다. 의미 검토 전에는 자동 비교 결과가 전부 맞아도 90% 목표를 판정하지 않습니다.

```powershell
.venv/Scripts/python.exe scripts/evaluate_demo_analysis.py --summarize-run $runDir --manual-review $reviewFile --redacted-report "$runDir/summary-reviewed-redacted.json"
```

이 재요약은 API·키 읽기가 없고 기존 report를 덮어쓰지 않습니다. 정제 보고서에는 원문·모델 문장·원시 예외가 없으며, 원자료 공개는 별도 선택입니다.

## 실제 준비 검증 결과

2026-09-21 18:24~18:32 KST, pc1 CJJ Windows에서 실행했습니다. 현재 실제 모델 평가 결과는 **0/32건, 6필드 정확도 미측정**입니다. 아래는 입력셋·평가기·기록 기능의 무과금 검사입니다.

```powershell
.venv/Scripts/python.exe -m pytest tests/test_evaluation_dataset.py tests/test_analysis_semantics.py -q
# 65 passed, 27 subtests passed in 3.08s
.venv/Scripts/python.exe scripts/evaluate_demo_analysis.py --validate
# validated-plan-only; fixed20/boundary12; 120 cells=80 automatic+40 manual
# plannedReservationCents=480; modelCalls=0; keyReads=0; modelAccuracy=not-measured
```

65개는 신규 평가 준비 검사 44개와 기존 분석 의미 검사 21개입니다. 기존 하위 입력 27개도 통과했습니다. 최초 실행에서 1개 테스트가 Windows 기본 cp949로 UTF-8 로컬 결과 파일을 읽어 실패했고, 테스트의 읽기 인코딩을 UTF-8로 명시한 뒤 같은 검사를 재실행해 통과했습니다. runner의 실제 저장/읽기는 처음부터 UTF-8이었습니다.

| 검사 | 실제 결과 |
|---|---|
| 코퍼스 구조·중복·6필드·rubric·동결 해시 | 고정20(미도착10/오출고10)+경계12 통과, 잘못된 후보 거부 |
| 기대값 변경 후 파일 내부 해시만 재계산 | runner의 외부 고정 해시가 거부 |
| 원문→모델 입력 | text만 허용, expected/rubric/replayAnalysis/sourceText/transcript 정답 누설 없음 |
| 기본 CLI 5조건·새 프로세스 import | 실제 API 0·키 읽기 0·live/key 모듈 import 차단 대조 통과·실행 폴더 미생성 |
| 결과 없음/오류/누락 필드/NaN/bool | 명시적 null 정답으로 채점하지 않고 미실행·오류·출력불량으로 분리 |
| 자동 80셀 정답·수동 40셀 미검토 | 전체 120셀·accuracy null·목표 not-determined |
| 90% 경계의 합성 판정 | 108/120은 met, 107/120은 not-met, 안전 실패는 별도 유지 |
| 실제 LiveAnalyzer+Mock의 입력 크기 실패 | 예약 1·API 0·실패 reservation ID 보존·15센트 유지 |
| 주입한 가짜 실행의 1성공+1실패 | 예약 2·dispatch 2·성공 1·30센트 유지·원문/출력/해시/코드5개해시 저장 |
| 키·예산 상한·원장 누락·provider 인증 오류 | 다음 입력으로 반복하지 않고 남은 입력을 미실행으로 보존 |
| 결과 파일 변경·검토 hash 불일치·이유 없는 검토 | 재요약 거부, 수동 통과로 보충하지 않음 |
| 정제 보고서 | 입력 ID·상태·분모·판정·호출 수만, 원문·모델 문장·예외 본문 제외 |

최종 v2에서 원본 파일을 수정하지 않고 메모리 변이 8개를 개별 행동 테스트에 주입했습니다. **8/8 탐지**: 외부 oracle pin 제거, null=0 혼동, unit 채점 제거, 스키마 게이트 제거, 수동 미검토 무시, 안전성 자동 통과, 명시적 live flag 게이트 제거, 실패 예약 추적 누락. 각 변이는 대상 검사에서 실패했습니다.

독립 읽기 전용 검토자가 발견한 subject 정답 힌트와 subject 숫자 요구의 오탐 가능성을 수정·명시한 뒤 재검토했습니다. 최종 확인은 힌트 0/32, expected 통합 해시 동일, v1 이력 보존, v2 validator 오류 `[]`였습니다. 같은 PC의 별도 에이전트 검토이며 실제 사용자 관찰이나 실 모델 결과를 대신하지 않습니다.

남은 작업은 메인의 실제 예산/HEAD 확인, 명시적 live 실행, 고정 120셀과 경계 72셀의 결과 수집, 독립 의미·안전 검토 및 그 해시를 연결한 재요약입니다. 20개 음성 품질 평가·STT 정확도·사람 만족도·외부 저장소 검증은 본 범위에 포함되지 않습니다.
