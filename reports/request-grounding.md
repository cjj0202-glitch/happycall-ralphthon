# 고객 요청 원문 보존 및 AI 추가 질문 분리

2026-09-21 · pc1 CJJ · `/root/grounding_four_repairs`.

새 실제 4호출에서 발견된 FIX-W05의 **고객이 하지 않은 단위 확인 요청**을 접수 request에서 제거했습니다. 주문·라벨 확인 원문을 유지하며 단위 누락을 추론으로 채우지 않았습니다. 기존 32건과 새 4건을 호출 없이 재처리했고 원본 44파일 해시를 보존했습니다. 후속 명사형 부정과 독립 검수의 네 실패를 수정해 관련 410검사를 통과했습니다. 동일 독립 9반례도 구현자가 재실행한 범위에서 모두 통과했으며, **최종 인수는 독립 재검 대기입니다.**

## 변경 계약

[상세설계](../planning/request-grounding.md)를 먼저 작성하고 새 합성 반례를 실패시킨 뒤 구현했습니다. 공개 JSON 스키마를 바꾸지 않고 `fields.request`의 출처를 제한했습니다.

- 모델 자유문 `fields.request`를 그대로 표시하지 않고, transcript에 실제로 포함된 유효한 `draftContext.requestQuote`를 보존합니다.
- 공백·욕설은 명시적으로 순화할 수 있지만 행동·숫자·기한·조건은 추가하지 않습니다. 욕설 순화 시 강한 불만 표시를 남깁니다.
- 선언·완료·향후 요청 예정·예문·요청 부정은 현재 고객 요청으로 승격하지 않습니다. `내일 확인해 주세요`와 `확정하지 말아 주세요`는 현재 요청으로 보존합니다.
- 유효한 인용이 없으면 request=null과 원문 대조 질문을 남깁니다. 원문 자체가 없다는 뜻이 아니라 자동 채움 근거를 확보하지 못했다는 뜻입니다.
- 요청 행위로 판정되지 않은 실제 발화는 회신 초안에서 **참고 발화 원문**으로 보존합니다. 원문을 없애거나 고객 요청이라고 표시하지 않습니다.
- 수령 수량·단위 필드가 비었고 수령량 문의 맥락이 있으면 **AI 추가 확인** 질문을 보완합니다. 배송 도착·기존 문의 회신처럼 수량이 핵심이 아닌 문의에 수량을 강제하지 않습니다.

소유 변경: `server/live.py`, 새 `server/request_grounding.py`, 새 `tests/test_request_grounding.py`, `tests/test_analysis_repair.py`의 request 계약 assertion 두 곳, 설계와 본 보고서. 메인이 새 모듈을 배포 whitelist 및 평가 코드 해시 목록에 추가한다고 확인했습니다. 이 워커는 해당 소유 밖 파일을 수정하지 않았습니다.

## 실패 → 수정 → 재검증

```powershell
.venv/Scripts/python.exe -B -X utf8 -m pytest -q tests/test_request_grounding.py -rs
.venv/Scripts/python.exe -B -X utf8 -m pytest -q tests/test_request_grounding.py tests/test_analysis_repair.py tests/test_analysis_semantics.py tests/test_analysis_grounding_regression.py tests/test_demo_backend.py tests/test_runtime_config.py tests/test_runtime_storage.py tests/test_evaluation_dataset.py tests/test_deployment_app.py -rs
.venv/Scripts/python.exe -B -X utf8 .local/request-grounding/reproject.py
```

| 검사 | 실제 결과 |
|---|---|
| 구현 전 새 합성 요청 검사 | **18 failed / 5 passed**. 원문 외 요청 삽입, 인용 미확인·부정·미래·완료가 실제 실패 |
| 최초 구현 후 기존 검사 대조 | **4 failed / 90 passed / 146 subtests passed** |
| 최초 실패 4건 처리 | 자유문 request 보존 기대 두 곳은 메인이 허용한 범위에서 원문 일치·허위 요청 제외로 강화. 기존 참고 발화 보존 두 곳은 검사를 약화하지 않고 초안에서 `참고 발화 원문`으로 보존해 해결 |
| 요청·기존 분석 4모듈 | **93 passed / 153 subtests passed / 4.93초** |
| 최종 관련 9모듈 | **404 passed / 3 skipped / 180 subtests passed / 15.63초** |
| 변이 대조 | 요청 검사 우회·모든 요청 null·필수 추가 질문 제거 3종 모두 회귀로 검출 |
| 실제 새 API·키 읽기 | **0건**. 새 테스트와 재처리에서 SDK·키 진입 AssertionError 대조 사용 |

skip 3건은 기존 Windows symlink 권한 제약이며 실행 성공으로 세지 않았습니다. 테스트 통과는 표에 적힌 입력과 경로의 결과이고 일반 언어 안전 통과를 뜻하지 않습니다.

## 저장 원응답 재처리

기준은 실제 호출 run `20260921T112012Z-62da8e1711`의 32건과 `20260921T120622Z-657e60bdb7`의 4건입니다. 같은 입력의 두 실행은 별개 관측으로 유지했습니다. `git show b03246a:server/live.py`를 메모리 모듈에 로드한 이전 경로와 현재 경로를 비교했습니다.

| 대조 | 이전 32건 | 새 4건 |
|---|---:|---:|
| 원문 인용 그대로 보존한 request | 31 | 4 |
| 요청 인용 검증 실패로 null | 1 (EDGE-09) | 0 |
| 자동 4필드의 값 변경 | 0 | 0 |
| 원래 사전 oracle의 자동 4필드 | 128/128 일치 유지 | 15/16 일치 유지 |
| summary·subject·department·facts·issues·unknowns 변경 | 0 | 0 |

**31/32와 4/4는 의미 정확도가 아니라 request 인용 보존 개수입니다.** 기존 의미 판정 또는 expected를 바꾸지 않았습니다. 이전 EDGE-09 인용은 떨어진 원문을 `....`로 합성한 것으로 실제 transcript의 연속 부분 문자열이 아닙니다. 자동 request를 null로 두었지만 실제 고객 요청이 없다고 판단한 것은 아닙니다. 기존 의미 누락이 해결됐거나 해당 사례가 새로 정답이 됐다고 보고하지 않습니다.

새 FIX-W05의 request는 실제 주문·라벨 확인 인용으로 대체되어 허위 단위 확인 요청이 사라졌습니다. `receivedClaim.unit=null`은 모델의 별도 추출 누락이므로 최종 unit도 null이며, 자동 오답 1셀은 그대로 남아 있습니다. 일반 안전 완료로 보고하지 않습니다.

새 EDGE-12는 기존 수량 질문에 더해 AI 추가 확인 질문이 수량·단위 둘을 명시합니다. 고객 요청 자체를 단위 확인 요청으로 바꾸지 않았고 과거 BOX는 여전히 null입니다. 이전 32건에서 추가 questions 변화는 EDGE-09, EDGE-12, FIX-M07이며 새 4건은 EDGE-12, FIX-M07, FIX-W05입니다.

로컬 증거 `.local/request-grounding/reprojected-36-final.json`의 SHA-256은 `f318613af31e861efebfd511addcf7d74f2b1f4e884082d0a9eb844dcac81dd7`입니다. 원본 44파일 해시·각 입력의 이전/이후 결과·변경 필드와 아래 코드 해시가 포함됩니다. 원응답 사본은 Git 공유 대상이 아닙니다.

- `server/live.py`: `4150029e4440dd8d6d843581f181829c825542857cc251def3036827337a5b71`.
- `server/request_grounding.py`: `888631ce1d5844e431f093a1f44a17895187c506992f7bbd4ad9968a8c9ea668`.
- `tests/test_request_grounding.py`: `45998a040acdf148d57b49940bf93befa465bc043538e5be0b882135687b14f7`.
- `tests/test_analysis_repair.py`: `e21101f47ea26586ae27be8d8ce0b7e91b30dc79b2a545310e5f68dfdab55c23`.

## 최초 동결 뒤 발견한 P1 이력과 인수 제한

제품·테스트 코드 동결을 메인에게 알린 뒤 읽기 전용 추가 반례를 실행했습니다.

```python
from server.request_grounding import current_request_quote
quote = '라벨을 확인해 주세요.'
text = '“라벨을 확인해 주세요.”라는 문장은 요청이 아닙니다.'
current_request_quote(quote, [{'text': text}])
# 실제: '라벨을 확인해 주세요.'
# 기대: None
```

당시 인용 뒤 문맥을 읽기는 하지만 `요청이 아니다`라는 명사형 부정을 인식하지 못했습니다. 이를 메인에게 즉시 전달했고 동결 중 임의 제품 수정을 하지 않았습니다. 아래 후속 승인을 받아 고정 반례로 추가해 수정했습니다. 독립 검수의 인용끝 문장 잘림·명사형 부정 축에는 계속 포함해야 합니다.

또한 선택한 requestQuote 자체에 빠진 고객 불만·조건을 이 투영이 복원하지는 않습니다. 고정 EDGE-01의 강한 불만 등 인용 바깥 의미 누락은 기존 한계입니다. 서술·부정·미래 문장 전체의 언어 의미를 인증하지 않으며 실제 모델 재호출·STT·사람 사용성·전체 업무 안전은 검증하지 않았습니다. 유료 호출·커밋·발송·원장 변경은 수행하지 않았습니다.

## 명사형 부정 후속 수정과 두 번째 동결

메인이 자체 발견 P1의 수정과 재검증을 승인했습니다. 명사형 부정·과거 전달·가정 인용 6개 및 실제 요청 양성 5개를 추가했습니다. 구현 전 **5 failed / 12 passed / 27 subtests passed**를 `.local/request-grounding/nominal-v2-before.txt`에 보존했습니다. 이미 차단되던 과거 인용 1개와 양성 요청들은 통과한 상태였습니다.

수정은 `server/request_grounding.py`의 비현재 요청 판정에 명사형 부정, 전달받은 과거 인용, 가정 인용 패턴을 추가한 것입니다. 요청 자체의 `박스 말고 개로`, `수령 확인이 아니라 라벨 확인`, `라벨이 다르다면` 조건은 그대로 보존했습니다. 저장된 실제 사례 ID나 전체 문장 일치 조건은 추가하지 않았습니다.

관련 동일 9모듈 결과는 **406 passed / 3 skipped / 190 subtests passed / 11.40초**, `.local/request-grounding/nominal-v2-after.txt`입니다. skip 사유와 경고는 이전과 같습니다. 제품·테스트 코드를 이 시점에 다시 동결하고 메인에게 독립 검수를 요청했습니다.

새 재처리 증거 `.local/request-grounding/reprojected-36-nominal-v2.json`의 SHA-256은 `e7c29beef02b41b66c5da1fd34e98ced1811195cc8a3bec1a5e7118b3033a051`입니다. 기존 재처리 출력들을 덮어쓰지 않았습니다. 원본 44파일 보존과 32+4건의 자동 필드·인용 보존 개수는 이전 표와 같습니다. EDGE-09의 인용 검증 실패와 새 FIX-W05의 unit null 오답을 그대로 남깁니다.

- 동결 `server/request_grounding.py`: `7dc7d27d4d6b519fb3e4de7c451dce204ff0661432c2b1ab5dede2d126acb29b`.
- 동결 `tests/test_request_grounding.py`: `c743d3963671938b5c9c1ba2b8092baffdf4243ba00509e4cbcccf2f96bc2d34`.
- `server/live.py`와 기존 `tests/test_analysis_repair.py`는 위 첫 동결 해시 그대로입니다.

이 추가 검사 통과는 지정된 표면형과 저장 사례의 결과입니다. 한국어의 모든 인용 범위·화자·부정·조건을 파싱한다는 보장이 아니며, 독립 반례 검증 전 일반 안전성을 완료 처리하지 않습니다.

## 독립 9반례 중 네 실패 보완과 최종 동결

[원 독립 보고서](request-grounding-independent.md)는 R02 명사형 요청 소실, R04 미래 부탁 의도, R05 철회, R06 잘린 종결어미를 실패로 판정했습니다. 원 보고서·기대·결과는 수정하지 않았습니다. 본 보완은 그 네 축에 한정했습니다.

추가 회귀의 구현 전 실측은 **8 failed / 16 passed / 36 subtests passed / 2.42초**입니다. `.local/request-grounding/independent-four-before-complete.txt`에 네 원인과 변형의 실제 실패가 남아 있습니다. 먼저 실행해 일부 assertion에서 중단된 초기 출력도 별도 파일로 보존했습니다.

- `부탁하려고 합니다` 등 요청 행위 자체의 향후 의도는 현재 요청으로 올리지 않습니다. 미래 시각의 실제 현재 요청은 기존대로 보존합니다.
- `반송 방법 안내 요청입니다`처럼 내용이 앞선 명사형 요청을 인식합니다. `주세요`, `해 주세요`처럼 종결 부분만의 인용은 원문 대조를 요구하며 서버가 빠진 동작을 채우지 않습니다.
- 같은 화자의 인용 뒤 문장과 바로 이어지는 같은 화자의 발화를 대조합니다. `그 요청은 취소합니다`는 중간 별도 요청이 없을 때 앞선 요청의 철회로 처리합니다. 다른 대상의 명시 철회는 원래 요청을 지우지 않으며, 중간 별도 요청 다음의 대명사는 그 별도 요청에 연결합니다.
- 양성 대조는 별도 반송 취소, 중간 반송 요청 후 철회, `취소하지 말아 주세요`, 상담원 발언 경계, 명사형·조건형 정상 요청입니다.

동일 9모듈 최종 실측은 **410 passed / 3 skipped / 202 subtests passed / 13.19초**이고 `.local/request-grounding/independent-four-full-after.txt`에 기록했습니다. 분석 4모듈만의 중간 검사는 99 passed / 178 subtests였습니다. skip 3건은 이전과 같은 Windows symlink 권한이며 통과로 계산하지 않았습니다.

원 독립 스크립트에서 **OUT 경로만 변경한 사본** `.local/request-grounding/independent-four/probe-copy.py`로 같은 입력·기대를 재실행했습니다. R01~R09 **9/9 PASS**, 저장 36건 재처리, 원본 44파일 해시 보존을 확인했습니다. 이 실행은 구현자 재현이며 독립자의 최종 판정을 대신하지 않습니다. 원 독립 결과 SHA-256 `15b3c59934e6af5cb20aa407e07b93f8f374ee57addd8dd9cac1edb3e46a096c`도 그대로입니다.

새 `.local/request-grounding/independent-four/results.json`의 SHA-256은 `7cd4af3b1b07af80799e9a2e79211e4692d56b051b3de886cb353ccb2af7f44b`입니다. 같은 폴더의 `comparison.json`에서 직전 `reprojected-36-nominal-v2.json` 대비 **정규화 결과 전체 객체 36/36 동일, 변경 0건**을 assertion으로 확인했습니다. 따라서 128/128·15/16 자동 필드와 EDGE-09 null·FIX-W05 unit null은 이전 결과대로입니다.

최종 동결 해시:

- `server/request_grounding.py`: `7443589ba87c9083d0dbb6820b00bf77a36359e24bc820ecaa68978766615714`.
- `tests/test_request_grounding.py`: `b5cf2e7fcc389859362b209ca24aa3b60b976a3f398f29968df656d30269b756`.
- `server/live.py`: `4150029e4440dd8d6d843581f181829c825542857cc251def3036827337a5b71` 그대로.
- 기존 `tests/test_analysis_repair.py`는 첫 동결 뒤 변경하지 않았습니다.

지원 한계: 철회의 명시 대상 대조는 단순 용어 겹침이며 한국어 전체 의미·대화 공동참조 분석이 아닙니다. 화자가 바뀌어 끼어든 뒤의 장거리 지시, 모호한 여러 요청 묶음, 인용 밖 빠진 조건을 자동 복원한다고 주장하지 않습니다. 이 네 축을 넘는 입력은 별도 검토가 필요하며, 원문 검토 안내와 최종 사람 확인 계약을 유지합니다. 본 수정 단위에서도 유료 API·원본·모델·데이터 정답·기존 독립 판정 변경·커밋·발송은 0건입니다.
