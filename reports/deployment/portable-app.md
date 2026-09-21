# 단일 원본 배포 앱 상세설계

2026-09-21 pc1 CJJ. 구현 전에 기록한 설계입니다. Vercel/AWS 인증·프로비저닝·외부 배포·실제 모델 호출은 수행하지 않습니다. 최종 호스트는 미확정입니다.

## 사용자 결과와 연결

HTTPS 한 원본에서 Next 정적 export, 합성 WAV/MP4, 기존 Connexion `/api/*`를 제공하는 ASGI factory를 추가합니다. `server.app`의 기존 로컬 실행은 유지합니다. 새 진입은 `uvicorn --factory server.deployment_app:create_deployment_app`입니다. HTTPS 종단과 외부 접속 제한은 최종 호스트 담당이며, 이 앱을 HTTP 인터넷 포트에 열었다고 배포 완료로 볼 수 없습니다.

소유 파일은 `server/deployment_app.py`, `server/deployment_access.py`, `tests/test_deployment_app.py`, 이 문서입니다. 프런트엔드는 별도 소유자가 `/api/*`를 같은 origin으로 호출하도록 빌드해야 합니다. 기존 live 분석은 `apps/web/public/demo`의 WAV를 읽으므로 패키징 시 서버 입력 경로도 보존해야 합니다.

## 설정과 접근제어

- `ONEFLOW_STATIC_DIR`: 정적 export 전용 디렉터리의 절대경로. `index.html`, `404.html`, `index.txt`, `cases.json`, `_next/static`의 JS/CSS와 `demo/CASE-0001.wav`, `demo/CASE-0002.wav`, `demo/sorter-demo.mp4`가 필요합니다. 누락·빈 필수파일·상대경로·심볼릭링크/Windows junction은 기동 실패입니다.
- `ONEFLOW_ACCESS_USER`: 4~64 ASCII 가시문자, 콜론 금지. 일반적인 기본값/placeholder는 거부합니다.
- `ONEFLOW_ACCESS_PASSWORD`: 24~256 ASCII 가시문자, 최소 12종 문자. 알려진 placeholder와 반복 단순값은 거부합니다. 무작위 비밀번호를 호스트 비밀설정으로 주입하며 명령 인자·저장소에 쓰지 않습니다.
- 위 세 값은 프로세스 환경에서만 읽으며 `.env` 자동 로딩/비밀값 로그/설정값을 포함한 예외는 없습니다. 잘못된 설정은 정적인 오류로 기동을 중단합니다.

Basic 인증은 가장 바깥 ASGI 층에서 화면·미디어·API·없는 경로까지 검사합니다. 자격증명은 SHA-256 고정길이 다이제스트를 각각 constant-time 비교합니다. Authorization 중복·모순·과대 헤더·잘못된 Base64·다른 인증 scheme·인증실패는 모두 같은 401/challenge입니다. 검증한 Authorization은 업무 핸들러로 넘기기 전에 제거합니다. Basic은 TLS 아래 시연용 공유 접근제어이며 실제 경영주/상담원/센터 사용자 인증이나 역할 권한을 제공하지 않습니다. 기존 `X-Demo-Role`의 합성 역할 검사는 API가 유지합니다.

공개 `/healthz`는 GET/HEAD만 `{"status":"ok"}`를 응답하며 실제 설정/키/예산/원문/저장소/기능 readiness를 조회하지 않습니다. 기능 health `/api/health`는 인증 뒤 기존 응답을 유지합니다. WebSocket은 사용하지 않으므로 모두 거부합니다. 응답 캐시는 `private, no-store`, MIME sniffing 차단, referrer 제한을 공통 적용합니다.

## 라우팅과 파일 경계

`/api`와 `/api/` 아래는 원래 ASGI scope/path 그대로 Connexion으로 보냅니다. prefix stripping이나 HTML fallback을 하지 않습니다. API의 404/405/검증 오류를 유지합니다. 나머지는 GET/HEAD만 정적 허용 목록으로 조회합니다. `/`만 `index.html`로 대응하며 없는 경로는 404입니다.

정적 허용 목록은 고정 루트 export 파일(`index.html`, `404.html`, `index.txt`, `cases.json`, `icon.svg`, `favicon.ico`), `_next/static` 아래 JS/CSS/폰트/이미지, `demo` 아래 WAV/MP4입니다. `.env`, Python, 키 파일, 임의 JSON, source map은 허용하지 않습니다. 경로 정규화 이전의 `..`/`.` 세그먼트, 역슬래시, NUL/제어문자, `%` 이중인코딩 잔존, Windows colon/후행 점·공백을 거부합니다. 요청마다 export 루트부터 모든 경로 구성요소의 symlink/junction과 실제 루트 경계를 확인합니다. 정적 산출물은 호스트에서 읽기 전용으로 마운트하며 동시에 교체하지 않습니다.

미디어는 Starlette FileResponse의 GET/HEAD/Range/If-Range와 WAV/MP4 명시 MIME을 사용합니다. 파일 전체를 메모리에 로딩하지 않습니다. 인증 전에는 파일 존재 여부·Range 정보를 반환하지 않습니다.

## 검증 계획

HTTPX ASGITransport와 임시 합성 export만 사용합니다. 실제 `.env.demo.local`, 실행 중 서버, 실제 API를 사용하지 않습니다. 기존 API 통합은 임시 JsonCaseRepository·mock live analyzer·mock health로 격리합니다.

양성은 인증된 화면/JS/WAV/MP4/API와 Range 206·HEAD·같은 origin 호출입니다. 음성은 모든 미인증 경로 401, 잘못된 role 403, 존재하지 않는 static/API 404, traversal·링크·비밀파일 차단입니다. 경계는 헤더 중복/Base64/길이, 필수파일/환경 누락, Range 416입니다. 변이 사본에는 인증 제거·인증 과차단·API prefix 변경·비밀파일 허용을 주입하고 관련 검사가 실제로 실패하는지 확인합니다. 변이 없는 동일 실행 대조도 통과해야 합니다.

## 구현 결과와 실행 증거

2026-09-21 18:02 KST pc1 CJJ, Python 3.12.14 / Starlette 1.6.0, 공유 작업본에서 실행했습니다. 시작 HEAD는 `88ba3b1`, 마지막 회귀 시 공유 HEAD는 `2656c84`이며 이 작업자는 커밋하지 않았습니다. 산출물은 위 네 파일입니다.

| 검사 | 기대 / 실측 |
|---|---|
| `.venv/Scripts/python.exe -m pytest tests/test_deployment_app.py -q` | `119 passed, 3 skipped, 5 warnings` (5.49초) |
| `.venv/Scripts/python.exe -m pytest tests/test_deployment_app.py tests/test_runtime_config.py tests/test_demo_backend.py tests/test_analysis_semantics.py -q` | `235 passed, 3 skipped, 51 subtests passed, 5 warnings` (9.11초) |
| `test_guard_mutations_are_killed_with_unchanged_control` | 동일 메모리 사본 CONTROL 4/4 통과, 인증 제거/과차단·API prefix 변경·임의 JSON 허용 변이 4/4 탐지. 저장소 소스 변경 0 |
| 실제 API 계약 | 임시 fixture/store에서 GET 200, unknown 404, DELETE 405, revision 누락 428, owner 수정 403, draft 조기종결 409, 정상 PATCH revision 증가, 이관 후 counselor 종결 403 확인 |
| 미디어 | 인증 GET/HEAD 200, WAV/MP4 두 경로의 부분/후미 Range 206, 범위 초과 416, stale If-Range 전체 200 확인 |

5개 warning은 기존 Connexion/Starlette/AnyIO/jsonschema deprecation입니다. 초기 실행은 `110 passed, 4 failed`였습니다. 실패 중 하나는 draft 조기종결의 기존 409를 403으로 잘못 예상한 검사였고, 기존 업무 구현을 바꾸지 않고 단계별 기대값과 이관 후 역할 검사를 보강했습니다. 나머지 셋은 Windows 실물 symlink 생성 자체가 `WinError 1314`로 거부된 것입니다. 권한을 바꾸거나 우회하지 않았으며 실물 파일/디렉터리 링크·기동 후 링크 교체·링크 export root 세 검사는 **not-run(3 skipped)** 입니다. 별도 8건은 `Path.is_symlink`/`is_junction` 결과를 합성 주입해 파일·디렉터리·루트 요청 차단과 기동 실패 분기를 실제 실행했습니다. 이 합성 8건을 실물 링크 검증으로 표현하지 않습니다. 최종 Linux/호스트 환경에서 세 실물 검사를 재실행해야 합니다.

## 호스트 인수 연결점

1. 프런트엔드를 동일 origin API 설정으로 export하고 위 필수 파일·미디어를 `ONEFLOW_STATIC_DIR`에 준비합니다. 정적 root는 소스 저장소/상위 폴더가 아닌 export 전용 폴더이며 읽기 전용으로 제공합니다. `index.txt`는 Next App Router export 파일입니다.
2. 접근 user/password는 무작위 값으로 호스트 비밀 환경설정에 주입합니다. runtime-config의 서버 전용 live 키·정책은 별도이며 이 앱의 공유 접근 암호와 다릅니다.
3. 같은 패키지의 `server/`, `server/openapi.yaml`, 합성 fixture, STT 입력 `apps/web/public/demo`와 Python 의존성을 보존합니다. 이 앱은 기존 repository/budget의 저장 방식을 바꾸지 않으므로 영속성·다중 인스턴스 저장 선택은 별도 인수 항목입니다.
4. 호스트가 TLS·방화벽·프로세스 수명·비밀설정·지속 저장을 제공해야 합니다. 인증 헤더를 로깅하지 않도록 호스트 로그 정책을 확인합니다. 승인된 host 설정 아래 factory를 실행합니다.

```text
python -m uvicorn --factory server.deployment_app:create_deployment_app --host 127.0.0.1 --port 8100 --no-access-log
```

위 명령의 loopback은 로컬 인수/동일 호스트 TLS 프록시용입니다. 컨테이너 서비스의 내부 bind는 호스트 계약에 맞춰 지정합니다. HTTP 프로세스 자체를 인터넷에 공개하지 않습니다. 실제 인증·호스트 계정·HTTPS URL·브라우저 Basic prompt/미디어 재생·클라우드 영속성·실모델·배포 후 회귀는 이 합성 검사에서 검증하지 않았습니다.
