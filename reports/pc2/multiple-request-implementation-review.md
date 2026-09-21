# N02-R2 — 고정 복수 요청 구현의 PC2 독립 대조

2026-09-22 pc2 안영일 / GitHub MR-A83. 카드 #8 comment5768103236을 07:03 KST 수신했다. 대상은 **`4af2756acc086de8903461ec4729623989b0017f` 하나**이며 이후 main의 프런트 변경까지 통과로 확대하지 않는다. 작업 branch는 `work/pc2-n02-call-review`, 검사 시작 HEAD는 `af288becf6e53261c242d8afae3336718b37250b`다.

**판정: 지정 회귀 233개·250 subtests는 통과했지만, 추가 독립 입력 20개 중 8개에서 기대와 달랐다. 5개 문제 유형을 서버 소유자인 pc1에 수정 검토로 인계한다.** 원문 요청을 잘못 유지하거나 지우는 결과가 순수 resolver뿐 아니라 `normalize_analysis`의 공개 `fields.request`에도 나타난다. 전체 N02/실모델/배포 인수는 아니다.

## 범위와 실제 실행

- 기존 N02-R1 JSON 31행과 원보고는 수정하지 않았다. 고정 Git blob과 실행 전후 SHA256을 대조했다. 원래 기대 활성·거절·검토 사유·출처 span·시각 및 입력 불변은 공개된 `tests/test_multi_request_provenance.py`의 31행 검사와 31행 HTTP 투영 검사에서 통과했다.
- `git archive`로 Git 추적 파일만 `.local/multi-request-r2-4af2756/source/`에 복사했다. 기존 checkout에 pull/merge/reset/stash를 하지 않았다. 서버·프런트·공통 파일은 수정하지 않았으며 이번 제출 소유 파일은 이 보고서 하나다.
- 기본 Python과 기존 `.local/pc2-m3-python`에는 pytest가 없었다. **검토용 ignored 경로에만 pytest 9.1.1과 실행 의존성 5개를 설치**했다. 기존 서버 의존성은 재사용했다. 전역 설치·정책·방화벽·권한 변경은 없다. 설치는 검사 준비이며 제품 검증 횟수로 세지 않는다.
- Python 3.12.14, `-X utf8 -B`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `-p no:cacheprovider`로 실행했다. `PYTHONPATH`는 검토 전용 dependencies와 기존 pc2-m3 Python 의존성 경로다.
- 기존 동일 PC 보조 검토자는 고정 Git 소스를 읽고 반례 후보만 제안했다. 총괄이 실행기·독립 기대값을 작성하고 resolver/공개 투영을 실제 실행했다. 다른 물리 PC 또는 메인 역할로 작업하지 않았다.

지정 명령(검토 사본 cwd):

```text
python -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_multi_request_provenance.py tests/test_request_grounding.py tests/test_analysis_repair.py tests/test_analysis_grounding_regression.py tests/test_analysis_semantics.py tests/test_receipt_review_guidance.py tests/test_two_flow_asgi_workflow.py
```

| 실행 | 실제 결과 | 의미 |
|---|---|---|
| 07:06:23 지정 7파일 첫 실행 | exit 1, 224 PASS / 9 setup ERROR / 238 subtests PASS, 5 deprecation warnings, pytest 32.79초 | PC2 검토 사본에서 `reports/e2e/live-analysis-before.json`이 누락되어 `AnalysisSemanticsTests` 9개가 시작하지 못했다. 제품 반례와 구분한다. |
| 07:09:37 누락 복구 후 오류 클래스만 실행 | exit 0, 9 PASS / 12 subtests PASS, pytest 0.26초 | 고정 SHA의 before/after JSON 두 개를 바이트 그대로 추가한 뒤 `tests/test_analysis_semantics.py::AnalysisSemanticsTests`만 재검했다. 이미 통과한 224개는 반복하지 않았다. |
| 합산 고유 검사 | **233 PASS / 250 subtests PASS**, 미해결 setup 오류 0 | 두 실행을 합친 고유 검사 수다. 한 번의 완전한 7파일 재실행 결과로 표시하지 않는다. |
| 07:09:00 PC2 추가 독립 관측 | 실행기 exit 0, **12/20 기대 일치, 8/20 불일치** | exit 0은 관측·JSON 저장 성공이다. 제품 통과가 아니다. 아래의 5유형 8행은 모두 공개 요청 투영에서도 불일치한다. |

첫 실행 로그와 오류를 덮어쓰지 않았다. 공개 저장된 합성 회귀 자료를 오프라인으로 읽었으며 이전 PC의 비공개 실제 원응답이나 원장을 가져오지 않았다. 메인 보고의 로컬 전용 독립 15개 실행기를 수신한 것은 아니므로 **동일 15개 재현**이라고 주장하지 않는다. 대신 공개 회귀 검사와 이 보고서의 별도 20개 입력을 구분한다.

## 수정 검토가 필요한 재현 5유형

아래는 모두 합성 입력이며 P2로 보고한다. 독립 기대값은 코드 출력으로 계산하지 않았다. 원문의 현재 요청·명시 철회·익명 화자·정정값 보존이라는 기존 계약으로 작성했다. 서버는 수정하지 않았다.

### 1. 같은 상품의 조사 차이가 명시 철회를 무시한다 — D01

같은 `customer`가 `치약을 반송해 주세요.`라고 요청한 다음 `치약 반송 요청은 취소합니다.`라고 말한다. 제안은 첫 문장 하나다.

- 기대: 활성 `[]`, 해당 요청 `WITHDRAWN`, 공개 요청 `null`.
- 실측: `치약을 반송해 주세요.`가 활성·공개 요청에 남고 거절·검토 사유는 없다.
- 원인: `server/request_grounding.py:98–115`의 명시 작업 분리에서 상품 집합 `치약을`과 `치약`을 조사 정규화 없이 비교하여 다른 대상으로 본다. `_target_terms`에 있는 조사 처리가 이 분기에 적용되지 않는다.
- 대조: D02의 조사 없는 동일 상품 요청은 철회된다. D03에서 실제로 다른 `컵`을 철회하면 치약 요청은 유지된다.

### 2. “요청만” 철회하면 관련 없는 상품·작업도 사라진다 — D04/D06

순서대로 `customer`의 `치약 반송 방법을 알려 주세요.`, `컵 반송 방법을 알려 주세요.`, `agent`의 `확인하겠습니다.`, `customer`의 `컵 반송 방법 요청만 취소합니다.`다. 제안은 앞의 두 요청이다.

- 기대: 치약 요청 유지, 컵 요청만 `WITHDRAWN`, 공개 요청은 치약 문장.
- 실측: 두 요청 모두 `WITHDRAWN`, 공개 요청 `null`.
- D06의 `반송 방법을 알려 주세요.` / `교환 방법을 알려 주세요.` / `교환 방법 요청만 취소합니다.`도 원래 반송까지 지운다.
- 원인: `request_grounding.py:104`의 명시 대상 분리 패턴은 `요청` 뒤 `은/는/을/를`만 허용한다. `만`에서는 분리 가드가 실패하고 공통 `방법`·`반송` 등의 교집합으로 두 요청을 같은 대상으로 처리한다.
- 대조: D05/D07은 철회 문장의 `만` 한 글자를 `은`으로 바꾸면 정확히 대상 요청만 철회된다.

### 3. 인용 안 연속 문장부호가 부정 문맥을 자른다 — D08/D09

`customer`의 `반송 방법을 알려 주세요.`, `agent`의 `확인하겠습니다.`, `customer`의 `저는 "반송 방법 요청은 취소합니다?!"라고 말한 적이 없습니다.`다.

- 기대: 원래 반송 요청 유지, 철회 사유 없음.
- 실측: 신형 `requestQuotes`와 구형 `requestQuote` 모두 `WITHDRAWN`, 공개 요청 `null`.
- 원인: `request_grounding.py:121–126`은 첫 `?`까지만 문장 경계를 잡는다. 남은 꼬리가 `!`로 시작하므로 닫는 따옴표/`라고` 검사가 작동하지 않고 부정된 인용을 실제 철회로 처리한다.
- 대조: D10은 인용 안 마침표 하나일 때 유지한다. D11은 부정 인용이 아닌 실제 `반송 방법 요청은 취소합니다?!`에서 정상 철회된다. 모든 문장부호 철회를 무시하는 수정은 D11을 깨뜨린다.

### 4. 구형 계약에서 익명 화자 철회 방어가 우회된다 — D12/D15

`speaker='unknown'`인 두 구간의 텍스트가 각각 `반송 방법을 알려 주세요.`, `반송 방법 요청은 취소합니다.`이고 구형 `requestQuote`가 첫 문장이다. `speaker='화자'`도 동일하다.

- 기대: 익명 라벨만으로 같은 사람의 철회를 확정하지 않는다. 요청 후보와 `SPEAKER_ROLE_UNVERIFIED`, `OTHER_SPEAKER_CANCELLATION` 검토를 유지한다. 후보 보존은 고객 신원 확정이 아니다.
- 실측: 위 두 검토 사유를 만들고도 `NON_CURRENT_CONTEXT`로 원요청을 제거하며 공개 요청은 `null`이다.
- 원인: `request_provenance.py:120–123`의 익명 방어 이후, 구형 분기 `240–243`이 전체 전사를 `current_request_quote`에 다시 전달한다. `request_grounding.py:174–178`은 truthy인 같은 `unknown/화자` 라벨을 연속 동일 화자로 따라가 철회한다.
- 대조: D13 신형 배열의 `unknown`, D14 구형의 `None`은 요청 후보를 유지한다. D16의 명시 `customer`는 구형에서도 실제 철회한다.
- 호환 계약의 기존 “가장 가까운 지시어” 정책과는 다른 문제다. 익명 라벨의 동일인 추정 금지는 메인 구현 보고에 명시되어 있으므로, 구형 경로의 추가 가드가 필요한 것으로 판단한다.

### 5. “아닌” 정정에서 정정값 없는 짧은 인용을 활성화한다 — D17

`customer` 한 구간이 `한 개가 아닌 한 박스예요. 단위를 기록해 주세요.`이고 제안은 `단위를 기록해 주세요.`만이다.

- 기대: 정정 대상·값이 없는 단축 인용은 `MISSING_CORRECTION_CONTEXT`로 검토 유보한다. 공개 요청 `null`. 원문을 임의 확장하지 않는다.
- 실측: 단축 인용이 활성·공개 요청이 되고 요청 거절·문맥 검토 사유가 없다.
- 원인: `request_provenance.py:92`는 `아니라`만 검사한다.
- 대조: D18 전체 원문 제안은 보존한다. D19에서 같은 단축 인용 앞의 연결어를 `아니라`로 바꾸면 정상 유보한다.
- 일반 한국어 의미 해석 전체를 요구하는 결과는 아니다. 현재 R28의 단위 정정 문맥 보존 요구와 직접 비교 가능한 한 연결어 변형이다. 확장 범위의 최종 채택은 pc1이 판단한다.

## 독립 20개 입력의 분모

각 행은 resolver 한 번과 `normalize_analysis` 한 번을 직접 호출했다. 직접 호출은 각각 20회이며 normalizer 내부에서도 resolver가 20회 호출된다. 이 관측 전 순수 resolver로 후보 4개를 먼저 확인했으므로, 그 4회는 최종 20행의 별도 성공 분모로 더하지 않는다. 지정 pytest 내부 호출 수는 별도 집계하지 않았다.

| ID | 경계 | 결과 |
|---|---|---|
| D01 | `치약을` 요청 / `치약` 철회 | FAIL: 철회된 요청 유지 |
| D02 | 같은 상품의 조사 없는 명시 철회 | PASS |
| D03 | 다른 상품의 철회 | PASS |
| D04 | 컵 요청`만` 철회 | FAIL: 치약도 제거 |
| D05 | 컵 요청`은` 철회 | PASS |
| D06 | 교환 요청`만` 철회 | FAIL: 반송도 제거 |
| D07 | 교환 요청`은` 철회 | PASS |
| D08 | 신형 `?!` 부정 취소 인용 | FAIL: 원요청 제거 |
| D09 | 구형 `?!` 부정 취소 인용 | FAIL: 원요청 제거 |
| D10 | 마침표 하나인 부정 취소 인용 | PASS |
| D11 | `?!`가 있는 실제 철회 | PASS |
| D12 | 구형 `unknown` 익명 화자 철회 | FAIL: 원요청 제거 |
| D13 | 신형 `unknown` 익명 화자 철회 | PASS |
| D14 | 구형 `None` 익명 화자 철회 | PASS |
| D15 | 구형 `화자` 익명 화자 철회 | FAIL: 원요청 제거 |
| D16 | 구형 명시 화자의 실제 철회 | PASS |
| D17 | `아닌` 정정값이 빠진 짧은 인용 | FAIL: 문맥 누락 인용 활성 |
| D18 | `아닌` 정정의 전체 원문 인용 | PASS |
| D19 | `아니라` 정정값 누락 | PASS |
| D20 | 동일한 현재 원문 요청의 반복 | PASS: 승인된 `AMBIGUOUS_OCCURRENCE` 유보 |

활성·거절·검토 이유·공개 요청 값이 모두 기대와 같은 경우만 PASS로 셌다. 8개 실패 모두 활성과 공개 요청 값 자체가 다르므로 사유 라벨만 다른 실패는 없다. D20의 보수적 정책은 결함으로 세지 않았다.

입력과 모델·접수·부서 객체는 모든 20행에서 deep equality로 불변을 확인했다. 실제 남은 활성 9인용·9span의 출처 문자열 조각/화자/원래 시각은 정확했다. 독립 20행 실행기는 거절 인용의 출처를 검사하지 않았다. **활성이 없는 11행의 출처 반복문은 공집합이므로, 이를 기대한 활성 요청의 출처까지 맞았다는 뜻으로 해석하지 않는다.** 정확한 출처가 붙어도 현재 요청 선택 의미가 잘못될 수 있다.

20행 모두 공개 schema 검증을 통과하고 수량·단위는 `null`로 유지됐다. 공개 요청 투영은 순수 함수 호출로 관측했으며 새 HTTP 수신 서버를 띄우지 않았다. 지정 ASGI 회귀는 TestClient의 메모리 저장소·작성 모델 대역을 사용하는 것으로 실제 배포 HTTP와 구분한다.

## 원본·소스·한계

R1 JSON SHA256은 `3c08e84c88c56454dea186c099b66324e18682eaef34b78153ee17af0d0c3617`, 원보고는 `42a838886173af60fe5064e874456e0c8adf31ce433b09af93aa7fb793c872fe`다. 원본 31행의 기대값을 실패에 맞춰 변경하지 않았다.

독립 실행기는 아래 소스 4개와 R1 JSON의 해시를 실행 전후 대조했다. 모든 검사 후 별도로 검토 사본의 Git 추적 132파일 전체 해시를 최초 복사본과 비교해 변경 0을 확인했다. 공개 `ANALYSIS_SCHEMA`와 그 정의에 필요한 앞부분 AST는 직전 `e4868f6`과 같고 `server/openapi.yaml`도 같은 Git blob이다. 원증거는 `final-integrity.json`에 기록했다.

| 실행 소스 | SHA256 |
|---|---|
| `server/request_provenance.py` | `5590e248f62adee421dd771b0f39b1a806a3105c888d81a1751d1a46da6af819` |
| `server/request_grounding.py` | `635f24a061ecbd0edf38ac20ab36ee64a78762b89f221ff767ee45c69a73d6bc` |
| `server/live.py` | `7acff20ab7c8391e5636d1bcd2740df72f7829d6a81c6200684a81baa9830e2b` |
| `server/analysis_schema.py` | `04b3be292133036231857793654e12da8310529c961a84d7008034f68abd2630` |

실모델·새 과금·키·실제 예산 원장·브라우저·새 수신 서버·Production 변경은 0이다. 독립 관측은 `OpenAI`, `require_demo_api_key`, `Budget`을 실패 대역으로 막고 호출 0을 확인했다. 모델 정확도·사람 청취·사용성·실제 알림·새 배포의 영속 저장·TEST는 검사하지 않았다. 이전 실제 canary 실패 기록을 이 합성 테스트로 교체하지 않는다.

메인은 5유형의 입력·기대·실측을 검토하고 자기 소유 서버에서 수정한 고정 SHA를 전달해야 한다. 이 보고서는 수정 완료나 최종 인수가 아니다. 기존 09:00 KST 인계 경계를 유지한다.

## 재현 코드와 원증거

원증거는 ignored `.local/multi-request-r2-4af2756/`의 `source-manifest.json`, `source-manifest-added.json`, `pytest-output.txt`, `pytest-result.json`, `pytest-missing-fixture-retry.txt/json`, `first-probes.json`, `independent-results.json`에 보존했다. 아래 코드는 원검증 실행기의 그대로인 사본이다. JSON에 입력·기대·resolver 전체 결과·공개 요청·회신 초안·검토 질문·각 대조 결과를 저장한다.

재현 시 `4af2756`의 `server`, `tests`, `data`, `demo`, `scripts`, `pyproject.toml`, `reports/e2e/live-analysis-before.json`, `reports/e2e/live-analysis-after.json`을 별도 Git blob 사본으로 준비한다. 원격 결과 보고가 아니라 이 보고서의 코드를 추출해 검사 환경의 Python으로 실행한다. 제품 소스를 수정하지 않는다.

```powershell
$reportText = Get-Content reports/pc2/multiple-request-implementation-review.md -Raw -Encoding utf8
$checkText = [regex]::Match($reportText, '(?ms)^<!-- r2-verifier:start -->\r?\n```python\r?\n(.*?)^```\r?\n<!-- r2-verifier:end -->').Groups[1].Value
# 실제 실행에서 재사용한 Python 의존성 경로를 PYTHONPATH에 지정한 뒤:
$checkText | python -X utf8 -B - .local/multi-request-r2-4af2756/source .local/multi-request-r2-4af2756/reproduced-results.json
# 실행기 exit 0은 관측 성공. JSON의 failedIds 8개가 이번 고정 후보의 결함 재현이다.
```

<!-- r2-verifier:start -->
```python
"""PC2 R2: fixed synthetic expectations, resolver and public projection only."""
import copy
import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

source = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(source))
from jsonschema import validate
from server.analysis_schema import ANALYSIS_SCHEMA
from server.live import normalize_analysis
from server.request_provenance import resolve_requests

Q = '반송 방법을 알려 주세요.'
PASTE = '치약 반송 방법을 알려 주세요.'
CUP = '컵 반송 방법을 알려 주세요.'
EXCHANGE = '교환 방법을 알려 주세요.'
UNIT = '단위를 기록해 주세요.'

def rows(*parts):
    return [{'id': f't{i+1}', 'speaker': speaker, 'text': text,
             'startSeconds': i * 4.0, 'endSeconds': i * 4.0 + 3.5}
            for i, (speaker, text) in enumerate(parts)]

def one(q, cancellation, speaker='customer', legacy=False, interruption=False):
    parts = [(speaker, q)]
    if interruption:
        parts.append(('agent', '확인하겠습니다.'))
    parts.append((speaker, cancellation))
    return ({'requestQuote': q} if legacy else {'requestQuotes': [q]}, rows(*parts))

def two(a, b, cancellation):
    return ({'requestQuotes': [a, b]}, rows(('customer', a), ('customer', b),
            ('agent', '확인하겠습니다.'), ('customer', cancellation)))

cases = []
def add(id, name, inputs, active, rejected=(), review=()):
    context, transcript = inputs
    cases.append({'id': id, 'name': name, 'draftContext': context, 'transcript': transcript,
                  'expectedActiveQuotes': active,
                  'expectedRejected': [{'proposalIndex': i, 'quote': q, 'reason': reason}
                                       for i, q, reason in rejected],
                  'expectedReviewReasons': list(review)})

add('D01', '목적격 조사 차이가 있는 동일 상품 철회',
    one('치약을 반송해 주세요.', '치약 반송 요청은 취소합니다.'), [],
    [(0, '치약을 반송해 주세요.', 'WITHDRAWN')], ['WITHDRAWN'])
add('D02', '같은 상품 명시 철회 대조', one(PASTE, '치약 반송 요청은 취소합니다.'), [],
    [(0, PASTE, 'WITHDRAWN')], ['WITHDRAWN'])
add('D03', '다른 상품 철회는 기존 요청 보존',
    one('치약을 반송해 주세요.', '컵 반송 요청은 취소합니다.'), ['치약을 반송해 주세요.'])
add('D04', '컵 요청만 철회', two(PASTE, CUP, '컵 반송 방법 요청만 취소합니다.'), [PASTE],
    [(1, CUP, 'WITHDRAWN')], ['WITHDRAWN'])
add('D05', '컵 요청은 철회 대조', two(PASTE, CUP, '컵 반송 방법 요청은 취소합니다.'), [PASTE],
    [(1, CUP, 'WITHDRAWN')], ['WITHDRAWN'])
add('D06', '교환 요청만 철회', two(Q, EXCHANGE, '교환 방법 요청만 취소합니다.'), [Q],
    [(1, EXCHANGE, 'WITHDRAWN')], ['WITHDRAWN'])
add('D07', '교환 요청은 철회 대조', two(Q, EXCHANGE, '교환 방법 요청은 취소합니다.'), [Q],
    [(1, EXCHANGE, 'WITHDRAWN')], ['WITHDRAWN'])
denial = '저는 "반송 방법 요청은 취소합니다?!"라고 말한 적이 없습니다.'
add('D08', '신형 연속 문장부호 부정 인용', one(Q, denial, interruption=True), [Q])
add('D09', '구형 연속 문장부호 부정 인용', one(Q, denial, legacy=True, interruption=True), [Q])
add('D10', '단일 문장부호 부정 인용 대조',
    one(Q, '저는 "반송 방법 요청은 취소합니다."라고 말한 적이 없습니다.', interruption=True), [Q])
add('D11', '연속 문장부호 실제 철회 대조', one(Q, '반송 방법 요청은 취소합니다?!'), [],
    [(0, Q, 'WITHDRAWN')], ['WITHDRAWN'])
for id, speaker, legacy in [('D12', 'unknown', True), ('D13', 'unknown', False),
                            ('D14', None, True), ('D15', '화자', True)]:
    add(id, f'익명 화자 {speaker!r}, legacy={legacy}',
        one(Q, '반송 방법 요청은 취소합니다.', speaker=speaker, legacy=legacy), [Q],
        review=['SPEAKER_ROLE_UNVERIFIED', 'OTHER_SPEAKER_CANCELLATION'])
add('D16', '구형 명시 동일 화자 철회 대조', one(Q, '반송 방법 요청은 취소합니다.', legacy=True), [],
    [(0, Q, 'WITHDRAWN')], ['WITHDRAWN'])
correction = '한 개가 아닌 한 박스예요. '
add('D17', '아닌 정정 문맥이 빠진 짧은 인용',
    ({'requestQuotes': [UNIT]}, rows(('customer', correction + UNIT))), [],
    [(0, UNIT, 'MISSING_CORRECTION_CONTEXT')], ['MISSING_CORRECTION_CONTEXT'])
add('D18', '아닌 정정 전체 인용 대조',
    ({'requestQuotes': [correction + UNIT]}, rows(('customer', correction + UNIT))), [correction + UNIT])
add('D19', '아니라 정정 문맥 누락 대조',
    ({'requestQuotes': [UNIT]}, rows(('customer', '한 개가 아니라 한 박스예요. ' + UNIT))), [],
    [(0, UNIT, 'MISSING_CORRECTION_CONTEXT')], ['MISSING_CORRECTION_CONTEXT'])
add('D20', '동일 현재 요청 반복은 승인된 보수적 유보',
    ({'requestQuotes': [Q]}, rows(('customer', Q), ('agent', '확인하겠습니다.'), ('customer', Q))), [],
    [(0, Q, 'AMBIGUOUS_OCCURRENCE')], ['AMBIGUOUS_OCCURRENCE'])

def project(case):
    transcript = copy.deepcopy(case['transcript'])
    source_case = {'id': 'SYNTHETIC-PC2-R2', 'channel': 'text',
        'text': '\n'.join(row['text'] for row in transcript),
        'store': {'id': 'SYN-PC2-R2', 'name': '가상검토점'},
        'intake': {'storeId': 'SYN-PC2-R2', 'subject': '합성 검토',
                   'quantity': None, 'unit': None, 'request': None}, 'evidence': []}
    empty_claim = {'product': None, 'quantity': None, 'unit': None, 'evidenceQuote': None}
    model = {'summary': '합성 분석 입력', 'fields': {'subject': None, 'request': None},
        'draftContext': {'subjectQuote': None, **copy.deepcopy(case['draftContext'])},
        'orderedClaim': copy.deepcopy(empty_claim), 'receivedClaim': copy.deepcopy(empty_claim),
        'storeClaim': {'name': None, 'evidenceQuote': None}, 'issues': [], 'questions': [], 'unknowns': [],
        'department': {'id': 'cs', 'name': '고객 지원', 'reason': '합성 검토'}, 'replyDraft': ''}
    departments = [{'id': 'cs', 'name': '고객 지원'}]
    before = copy.deepcopy((model, transcript, source_case, departments))
    with patch('server.live.OpenAI', side_effect=AssertionError('NO_API')) as api, \
         patch('server.live.require_demo_api_key', side_effect=AssertionError('NO_KEY')) as key, \
         patch('server.live.Budget', side_effect=AssertionError('NO_LEDGER')) as ledger:
        actual = normalize_analysis(model, transcript, source_case, departments)
    for boundary in (api, key, ledger):
        boundary.assert_not_called()
    assert before == (model, transcript, source_case, departments)
    validate(actual, ANALYSIS_SCHEMA)
    assert actual['fields']['quantity'] is None and actual['fields']['unit'] is None
    return actual

paths = ['server/request_provenance.py', 'server/request_grounding.py', 'server/live.py',
         'server/analysis_schema.py', 'tests/evaluation/multi-request-cases.json']
before_hashes = {p: hashlib.sha256((source / p).read_bytes()).hexdigest() for p in paths}
results = []
for case in cases:
    before = copy.deepcopy(case)
    actual = resolve_requests(case['draftContext'], case['transcript'])
    projection = project(case)
    active = [item['quote'] for item in actual['active']]
    rejected = [{k: item[k] for k in ('proposalIndex', 'quote', 'reason')} for item in actual['rejected']]
    expected = case['expectedActiveQuotes']
    expected_http = None if not expected else expected[0] if len(expected) == 1 else '\n'.join(
        f'{i+1}. {q}' for i, q in enumerate(expected))
    provenance_ok = True
    for item in actual['active']:
        for occurrence in item['occurrences']:
            slices = []
            for span in occurrence['spans']:
                row = case['transcript'][span['segmentIndex']]
                slices.append(row['text'][span['startChar']:span['endChar']])
                provenance_ok &= (span['startSeconds'], span['endSeconds']) == (row['startSeconds'], row['endSeconds'])
                provenance_ok &= occurrence['speaker'] == row['speaker']
            provenance_ok &= ' '.join(slices) == item['quote']
    checks = {'active': active == expected, 'rejected': rejected == case['expectedRejected'],
              'reviewReasons': actual['reviewReasons'] == case['expectedReviewReasons'],
              'httpRequest': projection['fields']['request'] == expected_http,
              'inputUnchanged': before == case, 'actualProvenanceExact': bool(provenance_ok)}
    results.append({**case, 'actualResolver': actual, 'expectedHttpRequest': expected_http,
                    'actualHttpRequest': projection['fields']['request'],
                    'actualReplyDraft': projection['replyDraft'],
                    'actualQuestions': projection['questions'], 'checks': checks,
                    'passed': all(checks.values())})
after_hashes = {p: hashlib.sha256((source / p).read_bytes()).hexdigest() for p in paths}
assert before_hashes == after_hashes
output = {'sourceCommit': '4af2756acc086de8903461ec4729623989b0017f',
          'checkedAtKst': datetime.now(timezone(timedelta(hours=9))).isoformat(),
          'pythonVersion': sys.version, 'caseCount': len(results),
          'passed': sum(r['passed'] for r in results),
          'failedIds': [r['id'] for r in results if not r['passed']],
          'sourceHashes': before_hashes, 'sourceUnchanged': True,
          'modelKeyLedgerBoundaryCalls': 0, 'results': results}
pathlib.Path(sys.argv[2]).write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k: v for k, v in output.items() if k != 'results'}, ensure_ascii=False))
for r in results:
    print(json.dumps({'id': r['id'], 'passed': r['passed'], 'checks': r['checks'],
                      'expectedRequest': r['expectedHttpRequest'], 'actualRequest': r['actualHttpRequest']}, ensure_ascii=False))
```
<!-- r2-verifier:end -->
