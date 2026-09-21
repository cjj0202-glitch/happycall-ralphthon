# v4 등록 후 배포 테스트 fixture 격리

2026-09-22. `tests/test_deployment_app.py`의 임시 3파일 export가 실제 저장소의 v4 manifest를 읽던 결합을 제거했습니다. 제품 무결성 가드는 바꾸지 않았습니다. **최종 영향 검사 265 PASS / 4 SKIP / 실패 0 / 오류 0, 64.55초, exit 0**입니다.

수정 소유는 `tests/test_deployment_app.py`와 본 보고서입니다. `server/`, 실제 등록 manifest, 제품 미디어, `tests/test_deployment_bundle.py`는 편집하지 않았고 다른 작업자의 변경을 보존했습니다.

## 원인과 수정 전 재현

기존 `app(environment)`는 `create_deployment_app(environ=environment, api_app=EchoAPI())`를 호출했습니다. 기본 manifest loader가 실제 repo의 v4 tracks 등록을 읽는 반면 `export_dir`에는 테스트용 `MEDIA` 바이트 3파일만 있었습니다. 실제 v4의 MP4/좌표 해시와 맞지 않아 제품이 정상적으로 fail-closed했습니다.

메인의 최초 영향 검사 보고는 `1 failed, 178 passed, 2 skipped, 86 errors, 67.93초, exit 1`입니다. 이 수치는 메인 관측이며 아래 한 건 재현과 합산하지 않습니다.

직접 실행한 수정 전 반례:

```powershell
.venv/Scripts/python.exe -B -X utf8 -m pytest -p no:cacheprovider tests/test_deployment_app.py::test_public_health_is_constant_and_does_not_call_api -x --tb=short -q
```

`/healthz`의 fixture setup에서 `ValueError: Registered demo media manifest or files failed integrity validation.`이 발생했습니다. **1 error, 1.56초, exit 1**입니다. 짧은 traceback만 출력했고 인증 fixture의 값이나 긴 locals를 출력하지 않았습니다.

## 상세 설계와 구현 경계

1. `legacy_media_manifest`는 임시 export의 세 파일 바이트에서 크기·SHA를 생성합니다. schemaVersion/repository/releaseTag를 포함한 독립 manifest를 일반 app, 임시 Connexion API 및 기존 메모리 변이 검사에 명시 전달합니다. 이 경로도 manifest 구조 validator를 계속 통과합니다.
2. 일반 인증·정적 경로·설정 오류 테스트도 같은 자체 manifest를 전달하므로 관련 가드가 실패하더라도 실제 등록 파일에 의존하지 않습니다.
3. `tracks_registration`은 그 manifest를 deepcopy하고 임시 sidecar를 추가합니다. 등록 안 된 3파일 경로와 등록된 MP4/sidecar 경로를 분리하며 기존 실제 파일 해시 검사·요청 중 재검사·인증·허용목록·hardlink·TOCTOU 검사를 유지합니다.
4. 기본 packaged-manifest 경로는 별도 테스트에서 그대로 실행합니다. `PACKAGE_ROOT`만 임시 package로 지정하여 manifest 부재→tracks 404, v3/v4 정상 등록→tracks 제공, 같은 크기의 MP4 변조→startup 거절, 잘못된 descriptor→기본/명시 두 경로 거절을 확인합니다. 제품 loader 또는 무결성 함수를 성공으로 mock하지 않았습니다.
5. 새 격리 회귀는 packaged loader를 호출하면 실패하도록 설정한 후 `request.getfixturevalue("app")`로 실제 app fixture를 생성합니다. 테스트 본문에 별도 생성 경로를 복제하지 않고 해당 fixture의 명시 주입을 검사합니다.

`tests/test_deployment_bundle.py`는 기존부터 자체 source repo·manifest·미디어를 만들고 있어 수정할 원인이 없었습니다. 최종 영향 검사에 그대로 포함했습니다.

## 최종 실행

```powershell
.venv/Scripts/python.exe -B -X utf8 -m pytest -p no:cacheprovider tests/test_demo_media_upgrade.py tests/test_deployment_app.py tests/test_deployment_bundle.py -q --tb=short --disable-warnings -ra
```

실제 실행 handle `23084`를 완료까지 수집했습니다.

| 항목 | 결과 |
|---|---:|
| 통과 | 265 |
| 실패 / 오류 | 0 / 0 |
| SKIP | 4 |
| 최종 수집 건수 | 269 |
| 시간 | 64.55초 |
| 프로세스 exit | 0 |
| deprecation warning | 5 |

SKIP은 Windows의 물리 symlink 생성 권한 부족입니다. `test_demo_media_upgrade.py` 1건, `test_deployment_app.py` 3건이며 보안 설정을 변경하거나 우회하지 않았습니다. 합성 `is_symlink`/`is_junction` 경로 검사와 hardlink 검사 등 실행된 다른 검사를 대신 물리 symlink 성공으로 세지 않습니다.

기존 인증 우회/전부 거절/API 경로 제거/정적 JSON 허용 가드 변이 4개와 ctime 가드 변이 2개를 제거하지 않았습니다. 최종 suite의 정상 대조·변이 검출 assertion이 통과했습니다. 이 내부 변이 수는 pytest 269건에 추가하지 않습니다.

## 새 격리 회귀의 인과성

최종 테스트 파일을 메모리에만 컴파일하여 `app` fixture 호출의 `media_manifest` 인자 한 개를 제거했습니다. 나머지 fixture 인자와 테스트 기대값은 보존했습니다. pytest collection hook으로 해당 메모리 fixture를 적용하고 새 회귀 한 건을 실행했습니다.

결과는 **1 FAILED, 1.33초, pytest exit 1**이며 실패 문구는 `AssertionError: Explicit test export must not load packaged media`입니다. 실제 repo manifest를 읽기 전에 loader 금지 장치가 원래 결합의 재발을 잡았습니다. 이 실패는 의도한 변이 검출 결과이며 최종 정상 suite의 실패로 합산하지 않습니다. 검증 수집 프로세스는 예상 실패와 소스 불변을 확인하고 exit 0으로 끝났습니다.

소스 SHA256은 변이 전후 모두 `7620266c9721ba417c480eaf46ebf6541607914427f2f04092c2ffbb18f38250`입니다. 디스크의 테스트 및 제품 소스는 변이를 위해 고치지 않았습니다.

## 인수 범위

- 최종 `tests/test_deployment_app.py` SHA256: `7620266c9721ba417c480eaf46ebf6541607914427f2f04092c2ffbb18f38250`.
- `git diff --check -- tests/test_deployment_app.py` 통과. `git diff --numstat -- server tests/test_deployment_bundle.py` 출력 없음.
- 실제 API 과금, 새 서버·브라우저, 기존 원장 접근, 기존 미디어 인코딩·다운로드·업로드, 커밋·push는 수행하지 않았습니다. API 검사는 임시 저장소와 ASGI in-process 호출입니다.
- 이번 결과는 테스트의 배포 입력 격리와 기존 영향 범위 통과입니다. v4 UI 시각 검수 및 별도 프레임 이동 수정의 완료 판정은 메인 범위입니다.
