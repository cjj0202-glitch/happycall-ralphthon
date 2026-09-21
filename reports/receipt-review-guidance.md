# 수령 단위 누락의 원문 검토 안내

2026-09-22 01:29 KST / pc1 CJJ 로컬 보조 에이전트 / 메인 인수 전 자체 검증.

**수령 단위를 자동 확인하지 못한 경우 정확한 인용문을 상담원에게 보여 주고, 원문 대조 후 불명확한 항목만 경영주에게 확인하도록 안내를 정리했습니다. 신규 8개 포함 영향 검사 167개 및 213 subtest가 통과했고, 변이 3개 모두 검출했습니다.** 단위 값은 계속 null이며 실제 모델 추출 정확도가 개선됐다는 뜻이 아닙니다.

## 기준·소유·설계

- 기준 HEAD: `4297dca6291e9c68ee3824d42825de0bfd991aeb`.
- 메인의 최신 `planning/ai-missing-unit-review.md`를 읽은 뒤 수정 전 검사를 작성했습니다. 해당 설계와 UI 라벨은 메인 소유이며 이 작업자가 편집하지 않았습니다.
- 소유 수정: `server/live.py`, 신규 `tests/test_receipt_review_guidance.py`, 기존 `tests/test_analysis_repair.py`의 안내 assertion 1곳, 이 보고서만.
- 이전에 인수된 `server/claim_grounding.py`는 변경하지 않았습니다. SHA256 `19c755aa2c9c9d549b989a377b2193c20ad89409518100f967557dc2861c9e23`로 유지됩니다.
- 실제 API·실행 서버·브라우저·운영 저장 데이터·기존 예산 원장은 사용하지 않았습니다. 영향 범위의 ASGI 검사는 별도 메모리 CAS와 작성 provider/budget을 사용합니다. 커밋은 메인이 수행합니다.

## 수정 전 실패

기존 `checked_claim`은 수령 단위가 null이면 `경영주에게 확인해 주세요`를 먼저 추가하고, 뒤의 `receipt_followup`이 원문 우선 안내를 다시 추가했습니다. 원문에 `4개`가 있어도 모델이 단위를 누락하면 상담원이 이미 받은 정보를 바로 재질문할 수 있었습니다. 단위 누락 항목에 원문 인용을 직접 보여 주는 안내도 없었습니다.

신규 검사 8개를 먼저 작성해 **5 failed, 3 passed in 2.86s**, exit 1을 확인했습니다. 실패는 단위 null 2사례, 수량/단위 모두 null 1사례, 주문 누락 원문 우선 안내 2사례입니다. 정상 EA/BOX 2사례 및 거절된 인용 안내 부재 1사례는 통과했습니다.

## 수정 동작

1. 수령 상품과 인용문이 기존 검사를 통과해 남아 있고 최종 단위가 null일 때만 `issues.field=unit`을 추가합니다. `evidence`에는 그 인용문을 그대로 넣습니다.
2. 안내문은 다음과 같습니다: `AI가 수령 단위를 자동 확인하지 못했습니다. 인용문을 원문과 대조해 주세요. 원문에서도 불명확하면 경영주에게 추가 확인해 주세요.` 원문에 특정 단위가 있다거나 실제 인도가 확인됐다고 단정하지 않습니다.
3. 수령 누락값의 고정 질문은 기존 `receipt_followup`으로 일원화했습니다. 주문 누락값도 주문 문맥에서 원문 대조→원문에서도 불명확할 때 경영주 확인 순서로 안내합니다.
4. 단위 후보 추출, EA/BOX 자동 선택, null 자동 채움, 단위 환산을 하지 않습니다. 요약의 `단위 미확인`은 그대로 유지합니다. 추가 확인 문장을 고객 `request`에 합치지 않습니다.
5. 모델의 자유 질문과 미확인 문장을 광범위하게 삭제하지 않습니다. 기존 AI 검토 제안 표시를 유지하고, 원문·transcript·원모델 응답 불변을 검사합니다.

제품 diff는 `server/live.py` 10줄 추가/2줄 삭제입니다. 기존 회귀 assertion은 무조건 재질문 문구 대신 원문 우선 고정 질문 1개를 확인하도록 바꿨습니다. `git diff --check -- server/live.py tests/test_analysis_repair.py` exit 0입니다.

## 정상·반례·영향 검사

```powershell
.venv/Scripts/python.exe -B -X utf8 -m pytest tests/test_receipt_review_guidance.py tests/test_receipt_unit_binding.py tests/test_analysis_grounding_regression.py tests/test_analysis_repair.py tests/test_analysis_semantics.py tests/test_request_grounding.py tests/test_two_flow_asgi_workflow.py -q -p no:cacheprovider
```

실측 **167 passed, 5 warnings, 213 subtests passed in 14.48s**, exit 0. 167개 안에 신규 8개와 기존 ASGI 4개가 포함되어 있습니다. 213 subtest를 별도 사용자 흐름 완주 수로 더하지 않습니다. 5개 경고는 기존 Starlette/httpx·AnyIO·Connexion/jsonschema deprecation이며 설치/업그레이드를 하지 않았습니다.

| 신규 입력/상황 | 기대 및 실측 |
|---|---|
| 원문 `하늘솔티백 4개를 받았습니다.` / 모델 `(4, null)` | `(4, null)` 보존, 정확한 인용 issue, 수령 고정 질문 1개 |
| 원문 `하늘솔티백 수령량은 4입니다.` / 모델 `(4, null)` | 위와 동일. 원문에 없는 단위를 추정하지 않음 |
| 정상 4 EA / 4 BOX | 값 보존, 누락 단위 issue·수령 고정 질문 없음 |
| 상품/인용이 있지만 수량·단위 모두 null | 두 null 보존, 인용 issue 1개, 수량·단위 원문 대조 질문 1개 |
| 주문 단위 null / 주문 수량·단위 모두 null | 주문 누락 항목에 대한 원문 우선 질문 각 1개 |
| 원문에 없는 수령 인용문 | 인용 거절, 허위 인용을 단위 issue의 evidence로 표시하지 않음 |

각 검사에서 원문·원모델·transcript가 호출 전후 같고, 고객 요청은 실제 요청 인용문 그대로이며, 모델 자유 질문/미확인/관련 라벨 제안이 보존되는 것도 확인했습니다. 현재 값이 null이라는 안내이며 값 정답으로 채점하지 않습니다.

## 변이 검출

정상 파일을 바꾸지 않고 별도 Python 프로세스 메모리에서 `normalize_analysis`만 변형한 뒤 신규 8개를 실행했습니다.

| 메모리 변이 | 실측 | 판정 |
|---|---|---|
| 단위 issue 생성 조건을 False로 변경 | 3 failed, 5 passed, 1 warning in 0.36s | 누락 안내 검출 |
| checked receipt의 unit null을 EA로 자동 채움 | 4 failed, 4 passed, 1 warning in 0.28s | 무단 값 변경 검출 |
| 무조건 경영주 재질문을 다시 추가 | 3 failed, 5 passed, 1 warning in 0.44s | 중복·순서 회귀 검출 |

모두 pytest exit 1이며 orchestration 명령은 기대 실패 3개를 확인해 exit 0이었습니다. 재현 틀은 다음과 같습니다. `.venv/Scripts/python.exe -B -X utf8 -`에 전달하며 파일을 쓰지 않습니다.

```python
import inspect, textwrap, sys, pytest
import server.live as module
source = textwrap.dedent(inspect.getsource(module.normalize_analysis))
old = 'if received["product"] and received["evidenceQuote"] and received["unit"] is None:'
new = 'if False:'
assert source.count(old) == 1
namespace = dict(vars(module))
exec(compile(source.replace(old, new), '<guidance-mutant>', 'exec'), namespace)
module.normalize_analysis = namespace['normalize_analysis']
sys.exit(pytest.main(['tests/test_receipt_review_guidance.py', '-q', '--tb=no', '-p', 'no:cacheprovider']))
```

자동 채움 변이는 `received = checked_claim("receivedClaim", "수령")` 다음에 `received["unit"] = received["unit"] or "EA"`를 넣습니다. 중복 질문 변이는 `ordered = checked_claim("orderedClaim", "주문")` 앞에 모델 수령 quantity/unit 중 null이 있을 때 `question("수령 수량 또는 단위가 미확인입니다. 경영주에게 확인해 주세요.")`를 호출하도록 넣습니다. 들여쓰기는 해당 함수 본문과 같게 유지합니다. 변이의 기대 종료코드는 1입니다.

## 해시와 남은 인수

| 파일 | bytes | SHA256 |
|---|---:|---|
| server/live.py | 30731 | 16743e03e0de1c94d2a16ab24f9b021a346a7e7844d5c114897738247f48105e |
| tests/test_receipt_review_guidance.py | 5948 | ab6c777a65cbb2b751dfb2a23ea241b690d99f49df21dc9b4e19b671b51d8289 |
| tests/test_analysis_repair.py | 35320 | 9861d61ad42fee16fecd23e82f2d64d0228bc801a079e853531a76fa36382a68 |

기존 live.py SHA는 `4150029e4440dd8d6d843581f181829c825542857cc251def3036827337a5b71`였습니다. 여기까지 source/test를 동결합니다.

## 메인 독립 인수와 화면 보완

독립 검토자 `clova_audio_intake_plan`은 위 `16743e03…` 소스에서 신규 합성14입력을 직접 `normalize_analysis`에 넣었습니다. **14/14 기대 일치**, 원문·모델·transcript14/14 불변, 고객 요청·모델 자유 질문·미확인 보존14/14입니다. 유효/허위 인용, product=null, 빈 수령, 정상 EA/BOX, 주문과 수령 구분, 과거/부정으로 값이 제거된 경우를 포함합니다. 이 범위에서 P1/P2를 발견하지 않았습니다.

메인은 저장된21:06 실제 FIX-W05 응답을 같은 소스의 `LiveAnalyzer.analyze`에 provider/budget double로 공급했습니다. 원본 파일 SHA256은 `085a956bcc47108828e6ce5210f1dbb04c33e207735b10e5dc8f5dd99b870c08`입니다. 수령4/null 유지, 정확한 원문 인용, 원문 우선 고정질문1개, 과거 무조건 재질문 부재, 고객 요청 보존, transcript 보존, 입력/파일 불변, 요약의 미확인 유지 **8항목을 확인**했습니다. 실제 SDK/키/Budget 생성은 호출 시 실패하도록 막았고 작성 client 호출1회, 실제 모델/STT/예산 원장 접근0회입니다. 자유 모델 질문을 포함한 전체 질문은4개이며 전체가1개라는 뜻은 아닙니다. 기록 원본은 Git에 올리지 않습니다.

독립 검토의 비차단 문구 지적 `수량를`은 메인이 주문/수령의 수량-only 안내에서 `수량을`로 고쳤습니다. 이 문구 보완으로 `server/request_grounding.py`의 조사 선택1곳도 메인 소유로 바꿨습니다. 두 수량-only 입력을 직접 실행해 주문/수령 각각 `수량을 원문과 대조` 안내가 나오는 것을 확인했습니다. 그 뒤 위7파일 영향 명령은 **167 passed, 5 warnings, 213 subtests passed in 15.04s**, exit0입니다. 앞의 독립14입력과 저장 응답8항목은 조사 보완 전 증거이며, 이후 전체 영향검사와 구분합니다.

최종 메인 소스 SHA256:

- `server/live.py`: `bce1c3f73a93f1849437f5a024b2ac8d756d52e624339a66183778a483ed770c`
- `server/request_grounding.py`: `cb865f42520a3f3cb0d852c2d7cc27c7e4b48a1a9eecbbdfdf8edc34fcfc89a2`

메인은 상담 편집기 제목/메모를 `확인할 항목`/`추가 확인 메모`로, 대조 상세 제목을 `통화 후 확인할 항목`으로 바꿨습니다. 값 저장·메모 반영 동작은 바꾸지 않았습니다. 기존 IAB에서 두 제목과 메모 placeholder가 실제 바뀌고, 선택한 오출고 사건과 미저장 초안 알림이 유지됨을 확인했습니다.

실제 화면에서 번호 `01`이 너비7.367px/높이33px로 두 줄에 갈라진 것도 발견했습니다. `globals.css`에서 번호·추가 아이콘의 flex 축소를 막고 번호의 한 줄 표시를 지정했습니다. 수정 후 실제390/768/1280px에서 번호 높이는 모두16.5px(한 줄), 너비11.859px입니다. 문서 scrollWidth는 각각375/753/1265px로 viewport보다 작았습니다. 임시 viewport는 reset했고, 기존 서버 재기동·reload·접수 저장은 하지 않았습니다. `npm.cmd run typecheck`도 exit0입니다.

최신 서버 안내를 기존 API 런타임에서 실제 호출해 화면에 표시한 검사는 미완료입니다. 새 생산 빌드·외부 배포·새 모델 정확도·음성 인식·사람 만족도도 이 인수의 증거 범위가 아닙니다.
