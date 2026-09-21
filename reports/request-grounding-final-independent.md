# 고객 요청 근거화 최종 수정의 독립 재검

메인 인수(21:31 KST): 원래 네 지적을 막는 수정 단위만 인수합니다. 추가 F1의 P2 과잉 철회는 미완료이며, 요청 원문을 상담원이 대조·수정하는 경로를 유지합니다. 최종 동결 후 메인이 분석·근거화·고정 평가 도구·배포 패키지의 6개 모듈을 실행해 **204 passed / 178 subtests, 40.06초**를 확인했습니다. 최초 실행은 존재하지 않는 `test_claim_grounding.py`를 지정해 수집 0건으로 종료됐고, 실제 `test_analysis_grounding_regression.py` 경로를 확인한 뒤 재실행했습니다. 새 라이브 모델 호출은 하지 않았습니다.

2026-09-21 · pc1 CJJ · `/root/fixed_recheck_semantics` · 제품 읽기 전용.

최종 동결 SHA 7443589에서 원래 9반례는 9/9 통과했습니다. 추가한 지정 범위의 6검사는 5/6 통과했고, 새로운 P1은 이 검사들에서 재현되지 않았습니다. 다만 서로 다른 요청에 공통 단어가 있으면 정상 요청까지 지우는 P2 과잉 철회 1건이 남았습니다. 따라서 기존 네 지적의 보완은 인정하되 모든 요청·철회의 의미를 판별한다고 인수해서는 안 됩니다.

## 원래 네 지적의 동일 조건 재검

원래 `.local/request-grounding-independent/probe.py`, `results.json`, `reports/request-grounding-independent.md`는 수정하지 않았습니다. 원래 코드의 OUT 경로만 메모리에서 바꾸어 별도 네임스페이스로 실행했습니다. 입력·기대값은 동일합니다.

| 원래 검사 | 최종 실측 |
|---|---|
| R01 정상 요청 원문 보존 | 통과 |
| R02 명사형 안내 요청 | null로 지우지 않고 명시 요청 보존 |
| R03 이미 요청·답변 완료 | 현재 request=null |
| R04 향후 부탁 의향 | 현재 request=null |
| R05 바로 뒤에서 철회 | 철회한 request=null |
| R06 잘린 `주세요.` 인용 | 불완전 request=null |
| R07 미래 시각의 현재 요청 | 요청 원문 보존 |
| R08 금지형 현재 요청 | 요청 원문 보존 |
| R09 동일 추가 질문 | 동일 문자열 1개로 유지, request와 단위 null은 불변 |

이 결과는 원래 P1 두 건과 P2 두 건의 정확한 재현 조건이 보완됐다는 증거입니다. 새 독립 변형을 보지 않고 9개 통과만으로 일반 언어 안전을 선언하지 않았습니다.

## 제한된 추가 6검사

| ID | 대조 | 기대 | 실제 | 판정 |
|---|---|---|---|---|
| F1 | 배송 시각 문의 뒤 배송 상품 반송 요청 취소 | 시각 문의 유지 | request=null | P2 실패 |
| F2 | 내일 오후까지 배송 도착 예정 시각을 알려 달라는 현재 요청 | 원문 보존 | 원문 보존 | 통과 |
| F3 | `반송 절차 안내 문의입니다.` | 내용 있는 명사형 요청 보존 | 원문 보존 | 통과 |
| F4 | 위 원문에서 `문의입니다.`만 인용 | 동작·대상 없는 조각을 자동 채택하지 않음 | request=null | 통과 |
| F5 | 경영주 요청 바로 다음 경영주 발화가 그 요청 취소 | request=null | null | 통과 |
| F6 | 같은 요청 다음 상담원 발화가 그 요청 취소 | 고객 요청을 상담원의 말로 철회하지 않음 | 고객 원문 유지 | 통과 |

추가 범위는 요청받은 다른 대상 취소·미래 행위 현재 요청·명사형/잘린 인용·인접 화자 경계에 한정했습니다. 새 문법을 계속 확장해 검사하지 않았습니다.

## 잔존 P2: 공통어 하나로 다른 요청까지 철회

원문: `배송 시각을 알려 주세요. 배송 상품 반송 요청은 취소합니다.`

requestQuote: `배송 시각을 알려 주세요.`

기대: 배송 시각 문의는 유지합니다. 취소한 대상은 상품 반송 요청입니다.

실측: request=null이고 원문 대조 질문으로 넘어갑니다.

`server/request_grounding.py`의 `_target_terms`·`_withdrawn`은 명시 취소 대상과 요청 사이에 단어가 하나라도 겹치면 같은 대상으로 봅니다. 해당 값 기반 대조는 다음과 같습니다.

```text
request_terms = ['배송', '시각']
cancel_terms  = ['반송', '배송', '상품']
intersection  = {'배송'}
_withdrawn(...) = True
```

공통 업무 단어가 같아도 요청 행동은 다릅니다. 이 결함은 고객이 하지 않은 행동을 새로 만들거나 이미 취소한 요청을 활성화하는 문제가 아니라, 정상 요청을 보수적으로 지우고 검토를 요구하는 누락이므로 P2로 구분합니다. 인수 시 이 과잉 차단을 남은 품질 항목으로 알려야 합니다. 단순 불용어 추가만으로 모든 대상 구분이 해결됐다고 보장하지는 않습니다.

## 저장 결과와 실제 비용 경계

| 확인 | 독립 실측 |
|---|---|
| 이전 32 + 새 4 원응답 재처리 | 36건 |
| 직전 독립 결과와 최종 analysis 전체 객체 일치 | 36/36, 변경 0 |
| 구현자 최종 결과와 객체 일치 | 36/36 |
| 이전 32건 자동 4필드 | 128/128 유지 |
| 새 4건 자동 4필드 | 15/16 유지 |
| 원래 평가 run 파일 해시 | 44/44 보존 |
| 원래 독립 코드·결과·보고서 해시 | 3/3 보존 |
| 검토 코드 해시 | 실행 전후 3/3 동일 |
| 새 API·키 접근·과금 | 0건 |

원래 FIX-W05의 허위 단위 확인 요청은 주문·라벨 확인 원문으로 대체된 상태를 유지합니다. unit=null은 이번에 채우지 않았고 자동 오답은 그대로입니다. EDGE-09 request=null과 선택된 인용 바깥 조건·불만 누락도 남아 있습니다. 인용 보존 31/32·4/4를 정답률로 쓰지 않았으며 이 보고서는 전체 32건의 의미·안전을 새로 채점한 결과가 아닙니다.

## 재현 명령·검사 결과

```powershell
.venv/Scripts/python.exe -B -X utf8 .local/request-grounding-final-independent/run_recheck.py
.venv/Scripts/python.exe -B -X utf8 -m pytest -q tests/test_request_grounding.py tests/test_analysis_repair.py tests/test_analysis_semantics.py tests/test_analysis_grounding_regression.py -rs
```

첫 명령의 실측:

```text
originalNinePass=9
additionalSix: F1=false, F2=true, F3=true, F4=true, F5=true, F6=true
storedObjectsUnchanged=36, storedWorkerMatches=36
originalEvidencePreserved=3, sourceFilesPreserved=44, apiCalls=0
```

두 번째 명령: `99 passed, 178 subtests passed in 6.96s`, 종료 코드 0.

로컬 재현 스크립트의 종료 코드 0은 실행·증거 저장·불변성 assertion 통과입니다. 추가 검사 F1의 실제 판정은 false이며 이 실패를 통과 수에 넣지 않았습니다. 기존 회귀가 통과해도 새 P2가 없어지는 것은 아닙니다.

## 증거 및 동결 코드

- 실행 래퍼: `.local/request-grounding-final-independent/run_recheck.py`.
- 원래 9검사 stdout: `.local/request-grounding-final-independent/original-nine.stdout.log`.
- 원래 9검사·36재처리 결과: `.local/request-grounding-final-independent/results.json`.
- 추가 6검사·보존 해시: `.local/request-grounding-final-independent/additional-six.json`.

추가 검사 JSON SHA-256: `66ab4b1cf190115ac43ec8570bbbb5b7de0f5a37347242b7fdac590ca1158aaa`.

최종 실행 코드 SHA-256:

- `server/request_grounding.py`: `7443589ba87c9083d0dbb6820b00bf77a36359e24bc820ecaa68978766615714`.
- `server/live.py`: `4150029e4440dd8d6d843581f181829c825542857cc251def3036827337a5b71`.
- `tests/test_request_grounding.py`: `b5cf2e7fcc389859362b209ca24aa3b60b976a3f398f29968df656d30269b756`.

## 제한된 인수 의견

이전 독립 지적 네 건의 보완과 지정한 정상/반례 검사는 위 실측 범위로 인수할 수 있습니다. 공통어로 다른 요청까지 지우는 P2는 미완료로 남기며, 자동 해석 실패를 원문 대조 및 최종 사람 확인으로 처리하는 범위를 유지해야 합니다. 일반 요청 의미 이해나 전체 업무 안전 완료를 뜻하지 않습니다.

화자 검사는 이미 주어진 speaker 표식의 인접 경계를 대조한 것입니다. 실제 음성 화자 식별 정확성, 장거리 대화 공동참조, 여러 요청 묶음 전체, 라이브 모델·STT·배포·실사용을 검증하지 않았습니다. 제품·기존 결과·정답·예산을 수정하지 않았고 커밋·발송도 하지 않았습니다.
