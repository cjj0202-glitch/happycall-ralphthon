# 수령 수량·단위의 다른 상품 혼입 수정

2026-09-22 01:22 KST / pc1 CJJ 로컬 보조 에이전트 / 독립 인수 전 자체 결과. 01:17 초안 이후 독립검토의 P2 두 범주를 보완했습니다.

**다른 상품의 단위가 수령 수량에 붙는 결함을 재현하고 수정했습니다. 독립검토 보완 후 신규 50개를 포함한 영향 검사 137개와 134 subtest가 통과했고, 변이 4개 모두 검출했습니다.** 실제 모델 정확도 검증은 아니며 무과금 작성 입력과 격리 ASGI 검사입니다.

## 기준·소유·설계

- 최초 기준 HEAD: `bc2435195eebd0ec8ad0661b04b0c5a18d0d6d1a`; 결과 정리 시 HEAD: `46a602fa00d3b6f2559501f728e9b25e25f5097b`. 중간 메인 변경을 되돌리지 않았습니다.
- 소유 수정: `server/claim_grounding.py`, 신규 `tests/test_receipt_unit_binding.py`, `planning/receipt-unit-binding.md`, 이 보고서만. 커밋은 메인이 수행합니다.
- 상세설계는 수정 전에 `planning/receipt-unit-binding.md`에 기록했습니다. 이번 단위는 상품 귀속과 수량/단위 쌍 대조이며, 별도 FIX-W05의 모델 누락 단위 안내는 구현하지 않았습니다.
- `server/live.py`는 수정하지 않았습니다. SHA256 `4150029e4440dd8d6d843581f181829c825542857cc251def3036827337a5b71`로 유지됩니다.

## 수정 전 반례와 원인

`supported_values`가 같은 범위에서 발견한 수량과 단위를 서로 독립 집합으로 모았습니다. 측정 표현이 하나뿐이면 상품 앞뒤도 제한하지 않아 다른 상품의 값이 지원될 수 있었습니다.

| 합성 진술 / 제안 | 수정 전 | 기대 |
|---|---|---|
| 푸른달봉투 수령량은 4이고 별빛차는 2박스를 받았습니다. / 봉투 4 BOX | 4 BOX | 4 / 단위 미확인 |
| 위 별빛차 수량도 4박스로 변경 / 봉투 4 BOX | 4 BOX | 4 / 단위 미확인 |
| 별빛차는 4박스이고 푸른달봉투 수령량은 4입니다. / 봉투 4 BOX | 4 BOX | 4 / 단위 미확인 |
| 푸른달봉투와 별빛차 4박스를 받았습니다. / 봉투 4 BOX | 4 BOX | 수량·단위 미확인 |
| 푸른달봉투 수령량은 4이고 별빛차 수령량은 2입니다. / 봉투 수량 2 | 2 | 수량 미확인 |

수정 전 신규 suite 최초 38개에서 **6 failed, 32 passed in 3.42s**, exit 1을 확인했습니다. 표의 5개 함수 반례와 실제 `normalize_analysis`에서 첫 반례가 그대로 접수 필드에 남는 1개 통합 반례가 실패했습니다. 양성 대조는 대상 단독 수령량 4→`(4, null)`, 대상 4개→`(4, EA)`로 확인했습니다. 이후 같은 상품의 별도 4 EA/2 BOX 쌍을 교차 결합하는 반례와 해당 2 BOX 양성 2개를 추가해 최종 신규 분모는 40개입니다.

## 최소 수정

1. 기존 역할/시간/부정 판정 `_scopes`는 그대로 유지했습니다. 과거 문의 자체, 현재와 대비되는 과거, 주문과 실제 수령의 구분을 넓혀 바꾸지 않았습니다.
2. `_value_belongs_to_target`을 추가해 값 앞의 같은 상품 이름과 문법적 연결을 대조합니다. 다른 상품 이름/다른 수치가 사이에 끼면 그 값을 해당 상품 근거로 삼지 않습니다. 명시된 생략 범위는 기존 연결 규칙을 이용합니다.
3. 독립 수량/단위 집합을 원문의 쌍 집합으로 바꿨습니다. 수량-only·단위-only는 null과 함께 저장하며 제안된 값만 보존/제거합니다. 추출값 자동 채움·단위 환산·새 상품 추론은 하지 않습니다.
4. 상위 정제에서는 기존 확인 질문 생성 경로를 그대로 사용합니다. 원문·작성 모델 응답을 수정하지 않는 것도 검사합니다.

보완 후 제품 파일 diff는 38줄 추가/18줄 삭제이며 `git diff --check -- server/claim_grounding.py` exit 0입니다.

## 영향 검사

```powershell
.venv/Scripts/python.exe -B -X utf8 -m pytest tests/test_receipt_unit_binding.py tests/test_analysis_grounding_regression.py tests/test_analysis_repair.py tests/test_analysis_semantics.py tests/test_two_flow_asgi_workflow.py -q -p no:cacheprovider
```

보완 후 실측: **137 passed, 5 warnings, 134 subtests passed in 12.87s**, exit 0. 137 안에 신규 50개와 ASGI 4개를 포함하며, subtest를 별도 제품 시나리오 완주 수로 더하지 않습니다. 최초 c5abc1d 초안에서의 127 PASS/134 subtests(11.29s)는 이전 실행 이력이며 아래 독립검토 반례를 포함하지 않았습니다.

- 다른 상품의 같은/다른 숫자, 대상 앞뒤 순서, 공동 명명으로 대상 수량 불확실, 단위-only/수량-only, 0/null, 한글 수량을 검사했습니다.
- 주문 대 수령, 현재 대 과거, 과거 문의 자체, 부정/미래/미확인, 기존 다중 상품·환산 거부·정정 및 상위 정제의 보존 계약이 포함됩니다.
- 같은 신규 텍스트의 상담원 수정·확인·이관→센터 회신/종결→경영주 조회 ASGI 2유형과 명시 실패복구가 포함됩니다. 실제 실행 서버·브라우저·유료 API는 사용하지 않았습니다.
- 기존 5개 deprecation 경고는 Starlette/httpx, AnyIO 및 Connexion/jsonschema 경고입니다. 패키지 설치·변경은 하지 않았습니다.

## 변이 검출

최초 c5abc1d 초안에서는 제품 파일 대신 별도 Python 프로세스 메모리에서 각 가드를 제거한 뒤 당시 신규 40개만 실행했습니다. 다음 2개 결과는 보완 전 이력입니다.

| 메모리 변이 | 실측 | 판정 |
|---|---|---|
| `_value_belongs_to_target`을 항상 True로 변경 | 6 failed, 34 passed in 1.79s / pytest exit 1 | 다른 상품/다른 수량 혼입 검출 |
| 단위의 원문 수량쌍 일치 조건을 True로 변경 | 1 failed, 39 passed, 1 warning in 0.17s / pytest exit 1 | 같은 상품 4 EA와 2 BOX를 4 BOX로 결합하는 오류 검출 |

최초 변이 orchestration 명령은 두 기대 실패를 확인하고 exit 0이었습니다. 이후 보완한 소스에서 신규 50개를 이용해 다시 실행한 결과는 아래와 같습니다.

| 보완 후 메모리 변이 | 실측 | 판정 |
|---|---|---|
| 상품 연결 검사를 항상 True로 변경 | 7 failed, 43 passed in 2.06s | 검출 |
| 수량 제안에 amount=None 단위 진술을 허용하는 예외 복원 | 1 failed, 49 passed, 1 warning in 0.20s | 검출 |
| 새 시간 연결 및 강조부사 지원 제거 | 6 failed, 44 passed in 2.52s | 정상 입력 회귀 검출 |
| 원문 수량쌍 일치 조건을 True로 변경 | 2 failed, 48 passed, 1 warning in 0.21s | 검출 |

네 개 모두 pytest exit 1이고 orchestration 명령은 기대 실패를 확인해 exit 0이었습니다. 변이 4/4 검출은 정상 suite 통과와 다른 분모입니다. 현재 소스의 재현은 다음 Python의 한 변이 블록을 선택해 `.venv/Scripts/python.exe -B -X utf8 -`에 전달합니다.

```python
import inspect, textwrap, sys, pytest
import server.claim_grounding as module
# 변이 1: 상품 연결 검사 제거
module._value_belongs_to_target = lambda *args: True
# 변이 2를 검사할 때는 위 줄 대신 아래를 사용합니다.
# source = textwrap.dedent(inspect.getsource(module.supported_values))
# old = 'quantity is None or quantity == amount'
# assert source.count(old) == 1
# namespace = dict(vars(module))
# exec(compile(source.replace(old, 'True'), '<pairing-mutant>', 'exec'), namespace)
# module.supported_values = namespace['supported_values']
# import server.live
# server.live.supported_values = module.supported_values
sys.exit(pytest.main(['tests/test_receipt_unit_binding.py', '-q', '--tb=no', '-p', 'no:cacheprovider']))
```

amount=None 예외 복원은 위 `source.replace(old, 'True')`의 대체 문자열을 `'quantity is None or amount is None or quantity == amount'`로 바꿉니다. 시간/강조 지원 제거 변이는 다른 변경 없이 `module.VALUE_LINK = re.compile(module.VALUE_LINK.pattern.replace(module.VALUE_TIME, r'(?!)').replace('|정확히|딱', ''))`를 적용합니다(`import re` 필요).

## 독립검토의 P2 두 범주와 보완

메인이 전달한 독립검토에서 초안 제품 SHA `c5abc1db2780d644dcd04118ff2129707ea366a79fd8b373d528334902e446e9`의 다음 결함이 발견돼 인수를 보류했습니다. 두 범주 모두 이 작업자도 같은 입력으로 직접 재현했습니다.

메인의 별도 초안 실행도 `127 passed / 134 subtests in 12.61s`였으나, 위 c5abc1d 소스의 실행으로만 기록하고 이것만으로 인수하지 않았습니다. 이 수치는 메인이 전달한 독립 실행 결과이며 이 작업자의 11.29초 실행과 합산하지 않습니다.

1. 기존 HEAD에서 지원하던 `하늘솔티백도 이번에 다섯 개를 받았습니다.`, `하늘솔티백은 오늘 오전에 다섯 개를 받았습니다.`, `하늘솔티백은 정확히 다섯 개를 받았습니다.`가 초안에서 `(null, null)`이 되는 회귀. 기대는 `(5, EA)`입니다.
2. `하늘솔티백은 다섯 개를 받았습니다. 하늘솔티백은 박스로도 받았습니다.`에서 제안 `(5, BOX)`가 amount=None 예외로 살아남음. 기대 `(5, null)`이며 같은 원문의 `(5, EA)`, `(null, BOX)` 제안은 각각 유지해야 합니다.

추가 대조 10개를 넣은 뒤 초안 코드에서 **7 failed, 43 passed in 1.89s**를 확인했습니다. 기본 3문장에 `오후 2시 30분에`, `7시에`, `방금 딱`을 포함한 정상 표현 6개가 실패하고 잘못된 수량/단위 결합 1개가 실패했습니다. 정확한 두 양성 쌍과 시간 뒤 다른 상품을 연결하지 않는 반례는 이미 통과했습니다.

시간은 날짜/최근 시점+조사, 시간대+조사, 시/분 구조로 허용하고 강조는 `정확히/딱`만 추가했습니다. 숫자 시간은 수량으로 추출하지 않습니다. 또한 수량 제안이 있으면 같은 원문 수량쌍만 단위를 지원하도록 amount=None 예외를 제거했습니다. 수량 제안 null의 단위-only 보존은 유지했습니다. 모든 임의 문자열을 허용하거나 단위 자동 채움으로 해결하지 않았습니다. 보완 후 동일 5개 파일 영향 검사 및 위 변이 4개를 다시 실행했습니다.

## 해시·한계·다음 인수

| 결과 파일 | bytes | SHA256 |
|---|---:|---|
| server/claim_grounding.py | 12010 | 19c755aa2c9c9d549b989a377b2193c20ad89409518100f967557dc2861c9e23 |
| tests/test_receipt_unit_binding.py | 6984 | c777b8f91786f45185a92cc1f056c572527b381c5efe674b207fbc1fa2f7c2b2 |

기존 grounding 원본 SHA는 `c98947e06f567560c2d89eb3f75561a9d6bf78e98e42bf774784f60e42b3243e`였습니다. 실제 저장 데이터·예산 원장·외부 API·서버 기동에는 접근하지 않았습니다.

어휘 연결 범위는 제한되어 복잡한 삽입 설명이나 새 표현을 보수적으로 미확인 처리할 수 있습니다. 모든 자연어 상품 귀속·화자·진술 진위·실제 인도를 판정하는 기능이 아닙니다. 모델이 제안하지 않은 수량/단위 null을 복원하지 않습니다. 실제 모델 정확도 개선율은 이번 검사로 산출하지 않습니다.

## 메인 인수 — 2026-09-22 01:24 KST

독립 검토자 `clova_audio_intake_plan`은 초안의 같은 28입력/기대값을 바꾸지 않고 최종 제품 SHA `19c755aa…`로 직접 함수 재검증했습니다. **28/28 PASS**, 입력 불변28/28입니다. `이번에`, `오늘 오전 9시에`, `정확히` 뒤에 다른 상품 `노을차`가 끼는 추가 음성3개도 모두 `(null, null)`로 차단했습니다. 추가3/3과 입력 불변3/3을 확인했습니다. 이는 전체 자연어 정확도나 브라우저 검사가 아닙니다.

메인은 위 영향 검사 명령을 최종 소스에서 실행해 **137 passed, 5 warnings, 134 subtests passed in 10.79s**, exit 0을 확인했습니다. 독립 검토 31개와 pytest137개를 제품 완주 수로 합산하지 않습니다.

또한 로컬에 보존된 20:20 실제 모델32응답과21:06 실제 모델4응답을 읽어 당시 원문/모델 JSON을 현재 `normalize_analysis`로 다시 처리했습니다. 같은 프로세스에서 `HEAD:server/claim_grounding.py`의 기존 함수와 새 함수를 각각 주입해 비교한 **수령 quantity/unit은36/36 동일**, 입력 record와 원본 파일 바이트도36/36 불변입니다. OpenAI 생성과 키 조회를 호출하면 실패하는 대조군을 적용했고 실제 호출0회입니다. 이 비교는 기존 수령값 회귀 대조이며 전체 분석 문장·주문값을 전수 채점하거나 새 모델 정확도를 평가한 결과가 아닙니다. 사내 원천자료/저장 모델 응답 원본은 Git에 추가하지 않습니다.

메인은 이 범위로 코드 변경을 인수합니다. 새 실행 API 적용·브라우저 통합·실제 모델 재평가·배포는 별도 미완료입니다.
