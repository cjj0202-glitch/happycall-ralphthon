# 배포 런타임 환경설정 상세설계와 검증

2026-09-21 pc1(CJJ), DEC-018과 docs24·25·26 기준. 이 문서는 구현 전에 작성한 환경설정 설계이며 배포 성공이나 영속 저장 완료를 뜻하지 않습니다.

## 과업과 파일 소유

배포 플랫폼이 서버 프로세스에 주입한 데모 전용 환경값을 live 분석과 health가 동일하게 사용하고, 승인한 프런트엔드 origin에서 API를 호출할 수 있게 합니다. 기존 로컬 실행은 두 loopback origin과 로컬 파일 fallback을 유지합니다.

소유는 `server/runtime_config.py`, `server/live.py`의 클라이언트 설정, `server/app.py`의 CORS 설정, `server/handlers.py`의 health 설정, `tests/test_runtime_config.py`, 이 보고서입니다. 정제 로직·repository·budget·FE는 변경하지 않습니다. 실제 키 파일 열람, 모델 호출, 프로세스 재시작, 배포, Git 변경은 이 작업에 포함하지 않습니다.

## 환경변수 계약

| 변수 | 허용/검증 | 우선순위 |
|---|---|---|
| `ONEFLOW_RUNTIME_MODE` | `demo-live` | 프로세스에 명시되면 우선, 없으면 로컬 파일 |
| `OPENAI_DEMO_BUDGET_USD` | 기존 정책 `30` | 동일 |
| `OPENAI_DEMO_WARN_USD` | 기존 정책 `25` | 동일 |
| `OPENAI_DEMO_PURPOSE` | `demo-only` | 동일 |
| `OPENAI_API_KEY` | 기존 `assert_key` 형식 검사 | 동일 |
| `ONEFLOW_CORS_ORIGINS` | 쉼표로 구분한 정확한 HTTP(S) origin 목록 | 프로세스에 없으면 로컬 기본 두 개 |

데모 reader는 앞의 다섯 키만 읽고 반환합니다. 다른 OpenAI 정책·임의 로컬 키·Blob 토큰은 반환하지 않습니다. 모든 데모 키가 프로세스에 있으면 로컬 파일을 열지 않습니다. 일부만 있으면 누락 키만 로컬 파일로 보완합니다. 프로세스의 빈 문자열도 명시 설정이므로 로컬 값으로 되살리지 않습니다.

로컬 파일은 기존 UTF-8/BOM·주석·`KEY=value` 형식을 유지합니다. 파일 부재는 빈 설정이고, 읽기 오류는 경로/내용을 노출하지 않는 `DEMO_CONFIG_UNAVAILABLE` 오류입니다. 정책 누락·불일치는 `DEMO_POLICY_REQUIRED`, 키 누락·형식 오류는 `API_KEY_MISSING`(각 503)이며 모델 클라이언트 생성 전에 차단합니다. 합성 fixture/replay를 사용하기 위한 앱 기동에는 live 키를 강제하지 않습니다.

health의 `liveReady`는 live 클라이언트와 같은 정책·키 검증을 사용합니다. `runtime`은 배포 여부를 추정하지 않는 `synthetic-demo`로 표시합니다. 이 값과 `liveReady`는 API 자격증명 구성에 한정하며 인증 성공, 실제 모델 사용, 지속 저장, 배포 준비 완료를 주장하지 않습니다. budget 상태는 기존 구현을 그대로 반환합니다.

## CORS와 오류 복구

미설정 기본은 `http://localhost:3100`, `http://127.0.0.1:3100`입니다. 명시 목록은 기본 목록을 **대체**하며 자동 origin 추정·와일드카드·정규식 도메인 확장은 하지 않습니다. 중복은 제거합니다. 빈 항목/빈 전체값, `*`, `null`, 사용자정보, 경로·쿼리·fragment, HTTP(S) 이외 scheme, 잘못된 host/port는 앱 생성 시 정적인 오류 문구로 거부합니다. 값을 오류에 넣지 않습니다.

기존 GET/POST/PATCH/OPTIONS와 Content-Type/X-Demo-Role 허용 범위를 유지하고 credentials는 명시적으로 false입니다. CORS는 브라우저 교차 origin 응답 허용이며 서버 인증을 대신하지 않습니다. 배포 origin은 확인된 URL을 담당자가 정확하게 설정합니다. 오류 시 설정을 고친 뒤 새 인스턴스로 재검증해야 하며 자동으로 로컬 목록으로 되돌리지 않습니다.

## 수용 기준과 테스트 계획

무과금 테스트에서 임시 합성 env 파일과 명시 환경 mapping만 사용합니다. 실제 `.env.demo.local`은 테스트 대상으로 열지 않습니다. OpenAI 생성은 mock, health budget도 mock, CORS는 실제 ASGI middleware의 OPTIONS 요청으로 확인합니다.

- 양성: 합성 로컬 설정만으로 정상 검증, 프로세스 전체 설정으로 파일 없이 정상 검증, 허용 origin preflight 성공.
- 음성: 정책 누락/불일치, 잘못된/빈 키, 빈 CORS·와일드카드·URL 경로 거부, 미허용 origin preflight 차단.
- 우선순위/경계: 프로세스 설정이 파일을 덮음, 명시 빈 값이 fallback되지 않음, 누락만 파일 보완, 중복 origin 정리, 포트/IPv6 경계.
- 노출/도달: 관련 없는 키가 reader에 없음, 예외·health에 합성 비밀값 없음, 실패 전에 OpenAI mock 생성/호출 0, 허용/불허 요청이 동일 middleware에 도달.
- 변이: 환경 우선순위 반전·빈 값 fallback·와일드카드 허용 변이를 메모리 사본에 적용해 대응 테스트가 실제로 실패하는지 확인합니다.

실제 배포의 환경 주입·URL·네트워크 회귀·영속성은 별도 검증 대상입니다.

## 구현 결과

2026-09-21 17:47 KST, pc1 CJJ, 저장소 로컬 작업본, Python 3.12.14에서 확인했습니다. 환경설정 reader/공통 검증, live client 연결, CORS 연결, health 연결, 합성 단위 테스트를 구현했습니다. live API endpoint는 `https://api.openai.com/v1`로 고정해 관련 없는 `OPENAI_BASE_URL`이 데모 키 전송처를 바꾸지 못하도록 했습니다. CORS는 대소문자 host·기본 port·IPv6 표현을 브라우저 origin 형태로 정규화합니다.

| 실행 | 기대 | 실측 |
|---|---|---|
| `.venv/Scripts/python.exe -m pytest tests/test_runtime_config.py -q` | 신규 설정/오류/우선순위/ASGI 모두 통과 | 65 passed, 5 warnings, 4.12초 |
| `.venv/Scripts/python.exe -m pytest tests/test_runtime_config.py tests/test_demo_backend.py tests/test_analysis_semantics.py -q` | 설정 변화가 접수/정제 계약 회귀를 만들지 않음 | 116 passed, 51 subtests passed, 5 warnings, 5.19초 |
| 아래 메모리 변이 실행 | 3개 결함을 대응 테스트가 탐지 | 3/3 KILLED, 저장소 소스 수정 0 |

5개 warning은 설치된 Starlette/httpx·AnyIO·Connexion/jsonschema 의존성의 deprecation입니다. 이 작업에서 의존성 변경은 하지 않았습니다. 테스트 실행 중 모델 요청, 실제 키 파일 읽기, 실행 중 서버 재시작, 배포를 하지 않았습니다. OpenAI 생성은 mock이며 health budget은 합성 mock입니다. 기존 회귀는 격리된 임시 저장소를 사용합니다.

변이 재현은 저장소 루트에서 아래 Python을 `.venv/Scripts/python.exe -`의 표준입력으로 실행합니다. 실제 키 파일과 배포 서비스에는 접근하지 않습니다.

```python
import importlib.util
from pathlib import Path
import tempfile
import types

spec = importlib.util.spec_from_file_location("runtime_tests", "tests/test_runtime_config.py")
suite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(suite)
source = Path("server/runtime_config.py").read_text(encoding="utf-8")
mutations = [
    ("runtime-priority-removed",
     "result = {key: environment[key] for key in DEMO_ENV_KEYS if key in environment}",
     "result = {}",
     lambda path: suite.test_runtime_environment_overrides_every_local_value(path)),
    ("empty-runtime-falls-back", "if key in environment}",
     "if key in environment and environment[key]}",
     lambda path: suite.test_explicit_empty_runtime_value_never_falls_back("OPENAI_API_KEY", path)),
    ("wildcard-accepted",
     '    if not value or "*" in value or any(ch.isspace() for ch in value):',
     '    if value == "*":\n        return value\n    if not value or "*" in value or any(ch.isspace() for ch in value):',
     lambda path: suite.test_invalid_cors_is_rejected_without_echo("*")),
]
killed = 0
with tempfile.TemporaryDirectory(prefix="oneflow-runtime-mutations-") as directory:
    for name, before, after, test in mutations:
        assert source.count(before) == 1, name
        mutant = types.ModuleType("runtime_mutant")
        exec(compile(source.replace(before, after), "<runtime-mutant>", "exec"), mutant.__dict__)
        mutant.ENV_FILE = Path(directory) / "synthetic.env"
        suite.config = mutant
        try:
            test(mutant.ENV_FILE)
        except BaseException as error:
            if type(error).__name__ not in ("AssertionError", "Failed"):
                raise
            killed += 1
            print(f"{name}: KILLED ({type(error).__name__})")
        else:
            print(f"{name}: SURVIVED")
assert killed == len(mutations)
print(f"mutations killed: {killed}/{len(mutations)}; repository files modified: 0")
```

## 인수 시 남은 범위

배포 담당자는 확인한 프런트엔드 origin을 `ONEFLOW_CORS_ORIGINS`에 넣고 서버 전용 다섯 데모 키를 주입해야 합니다. 이번 테스트는 원격 환경 주입, API 계정 인증, 실모델 정답률, 원격 저장의 동시수정/영속성, 실제 브라우저 배포 URL을 검증하지 않았습니다. `liveReady=true`를 그 완료로 해석하지 않습니다. repository/budget의 Blob 등 저장소 선택·구현은 별도 소유자에게 남아 있습니다.
