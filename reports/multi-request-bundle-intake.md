# 복수 요청 모듈의 배포 묶음 인수

2026-09-22 새 메인 PC의 배포 담당 검사. 메인의 사전 실행에서 실제 런타임을 격리 묶음으로 옮기는 검사가 `INVALID_RUNTIME_INPUT(RUNTIME_MODULE_OUTSIDE_BUNDLE)`로 실패했다. `server/live.py`가 새 `server/request_provenance.py`를 import하지만 명시적 배포 파일 목록에는 그 모듈이 없었다.

`scripts/build_deployment_bundle.py`의 `SOURCE_FILES`에 `server/request_provenance.py` 한 경로를 추가했다. 재귀 복사나 검증 예외를 도입하지 않았다. 기존 비밀 탐지·원천자료 제외·소스/빌드 지문·미디어 해시·파일 링크 차단·인증 라우팅 검증은 그대로 사용한다. 새 파일도 다른 서버 소스와 같은 payload 검사를 통과해야 한다.

기존 `test_real_runtime_imports_and_asgi_work_without_original_repository`에 새 모듈을 명시적으로 import하고 그 파일이 원본 저장소가 아닌 생성된 묶음 내부에 있는지 확인하도록 보완했다. 임시 합성 fixture·미디어·환경값으로 독립 Python 프로세스를 실행하며 실제 키·원장·모델 접근은 차단한다.

## 실행과 관측

실행 환경은 저장소 `.venv`의 Python이며 작업트리 점검 시 HEAD는 `e4868f6b33b8e58f4d727e8fc3241185acf387a0`이었다. 메인과 별도 빌더가 다른 소유 파일을 작업 중이므로 이 HEAD만으로 모든 작업트리 바이트가 고정됐다고 주장하지 않는다. 이 작업의 소유 파일은 패키저·관련 테스트·본 보고서 세 개다.

```powershell
.venv/Scripts/python.exe -X utf8 -B -m pytest tests/test_deployment_bundle.py::test_real_runtime_imports_and_asgi_work_without_original_repository tests/test_deployment_bundle.py::test_missing_local_runtime_dependency_is_rejected tests/test_deployment_bundle.py::test_packaging_guard_mutants_are_killed_with_same_location_controls tests/test_deployment_bundle.py::test_frontend_dotenv_is_rejected_before_reading_it tests/test_deployment_bundle.py::test_vercel_configuration_cannot_create_static_authentication_bypass -q
# 8 passed in 53.66s

git diff --check -- scripts/build_deployment_bundle.py tests/test_deployment_bundle.py
# exit 0, 출력 없음
```

| 검사 | 관측 |
|---|---|
| 실제 모듈을 복사한 격리 bundle | 새 요청 모듈을 포함한 런타임 import 성공, 모든 확인 대상의 파일 경로가 bundle 내부 |
| 동일 bundle ASGI | health 200, 무인증 보호 경로 401, 인증 HTML 200, MP4 Range 206/4바이트, 없는 API 404 |
| 미포함 로컬 모듈 import | 기존 차단 유지 |
| 패키징 검증기 변이 | 비밀 탐지·소스 지문·미디어 해시·인증 라우팅의 4개 변이 검출; 위 8개 검사 중 한 테스트의 내부 대조군 |
| 프런트 dotenv | 내용 읽기 전에 거절 |
| Vercel 인증 우회 설정 4종 | filesystem route·추가 함수·outputDirectory·rewrite 모두 거절 |

과금/API·원격 배포·커밋·push는 수행하지 않았다. 현재 제품 resolver의 의미 정확성, 실제 Next 산출물 패키징, Vercel Preview 및 영속 저장의 인수를 대신하지 않는다. 이 수정은 새 런타임 의존성이 배포 허용 목록에서 누락된 결함과 격리 실행 회귀만 검증한다.
