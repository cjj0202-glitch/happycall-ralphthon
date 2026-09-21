# 명사형 요청 누락과 복합 취소 보완

2026-09-22 pc1/CJJ · 기준 `da33d4dfd72b59aa1301d9ed97f713c2f43dc44e`

`배송 시각 안내 요청입니다`가 별도 반송 취소 뒤에도 남도록 보완했습니다. 같은 조사 과정에서 기존 명령형 요청도 `배송 시각과 반송 요청은 취소합니다` 뒤에 되살아나는 P1을 재현하여 함께 수정했습니다. 반환값은 원문 인용 또는 null이며 요청을 새로 쓰거나 수량·단위를 보정하지 않습니다.

## 설계와 실패 선고정

[설계](../planning/nominal-request-cancellation.md)의 한정 문법을 적용합니다. 기존 단순 정보명사구에 `안내/확인 요청입니다` 종결을 추가하고, 명사형 물류행위 추가분은 전체 단순 명사구와 일치할 때만 구분합니다. 기존 정보명사5개가 `시각과`, `라벨도`처럼 조사와 붙어도 별도문의 예외에서 보수적으로 제외합니다. 일반 한국어 공동참조 해석이나 어휘 사전 확장이 아닙니다.

메인은 제품 코드 수정 전에 신규4개 메서드를 추가하고 아래 명령에서 exit1을 확인했습니다. 정상 명사형5건·양쪽 명사형 순서2건은 null로 잘못 지워졌고, 기존 명령형의 복합 취소2건은 잘못 유지됐습니다. 실측 출력은 `9 failed, 4 passed, 22 deselected, 22 subtests passed`입니다. 부모 메서드와 하위 사례 집계를 합쳐 통과 수로 재해석하지 않습니다.

```powershell
.venv/Scripts/python.exe -B -X utf8 -m pytest -q tests/test_request_grounding.py -k 'nominal_information or two_nominal or information_with_particle or nominal_inquiry' -rs
```

읽기 전용 보조는 제품 수정 전 별도50개 합성 입력을 실행했습니다. 현행41/50, 양쪽 종결만 늘린 첫 메모리 후보36/50, 최종 제한 후보50/50입니다. 단순 후보는 정보 명사의 조사·복합문 및 과거/계획/부정/예문 속 명사형 작업 때문에 기존 대비13건의 신규 회귀가 생겼습니다. 이 후보는 제품에 적용하지 않았습니다.

## 제품 수정과 재검

소유 변경은 server/request_grounding.py, tests/test_request_grounding.py, 이번 설계·보고서입니다. 기존 파일·원응답·예산 원장·키·UI·음원·런타임 프로세스는 변경하지 않았습니다. 메인 입력은 실제 normalize_analysis를 호출하며 OpenAI와 키 조회 함수를 실패하도록 막았습니다.

| 검사 | 실제 결과 |
|---|---|
|요청 근거화 검사 전체|28 passed / 116 subtests, 2.96초, exit0|
|분석 관련4모듈|111 passed / 250 subtests, 7.76초, exit0|
|추가 변이|정보명사 차단을 옛 단어집합으로 복원하면 복합 취소 검사 실패; 명사형 fullmatch를 search로 바꾸면 과거 인용 검사 실패. 두 변이 모두 AssertionError 검출|
|기존 변이|기존 요청 무조건 채택/항상null/추가질문 제거와 취소범위 예외 항상허용/항상차단 검사가 그대로 실행됨|
|공백 검사|git diff --check exit0|

```powershell
.venv/Scripts/python.exe -B -X utf8 -m pytest -q tests/test_request_grounding.py -rs
.venv/Scripts/python.exe -B -X utf8 -m pytest -q tests/test_request_grounding.py tests/test_analysis_repair.py tests/test_analysis_semantics.py tests/test_analysis_grounding_regression.py -rs
```

검증 당시 SHA256:

- server/request_grounding.py: `78f8e778ff1d86eb1b02f88ead80bebec1e5e3c599304c5b79c0408f42d17f22`
- tests/test_request_grounding.py: `01c22785b8734824b60ba19e9d51a9f875d8ce90fdee176c1f044166da90d657`

## 독립 제품 대조와 인수 경계

읽기 전용 보조가 실제 수정 파일과 앞선 메모리 후보의 AST 전체 일치 및 실행 전후 SHA 보존을 확인했습니다. 앞선 기대값50/50, 명사형/명령형 혼합·양방향 최근요청8/8, 탭·연속공백·줄바꿈·종결 부호 경계8/8, 실제 normalize_analysis 통합12/12입니다. 통합은 원문/null·허위 AI 요청 제외·수량/단위 null·검토질문·결과 스키마·입력 불변을 대조했습니다. API/키/환경파일 함수 호출은0회입니다.

독립 통합 최초 import는 외부 filelock 패키지의 임시파일 기능 탐지가 읽기 전용 audit guard에 차단됐습니다(실제 쓰기0). filelock 의존성만 호출 시 실패하는 대역으로 격리한 뒤 실제 normalizer를 재실행했고, 대역 호출도0회인 상태로12/12를 확인했습니다. 파일락·저장소 동작을 검증했다는 결과가 아니며, 메인의111/250 검사는 이 대역 없이 실행했습니다.

위 한정 계약의 코드 보완을 인수합니다. 기존 API8100 재시작은 하지 않았으므로 실행 화면의 AI 결과가 이 수정으로 바뀌었다고 보고하지 않습니다. 새 유료 평가·전체 UI·사람 검증·실제 배포도 별도입니다. 수식어가 많은 표현이나 지원 밖 명사형은 여전히 보수적인 null과 사람 대조가 필요할 수 있습니다.
