# OpenAI API — 데모 전용 연결

상태 기준: 2026-09-21. 사용자가 프로젝트 API 키를 제공했고 **제품 데모에만 사용**, 개발·일반 테스트에는 사용하지 않으며 예상 누적 비용이 $30을 넘을 것 같으면 호출 전에 알리도록 요청했다.

## 보관과 실행 경계

- 실제 키는 각 허가된 PC의 저장소 루트 `.env.demo.local`에만 둔다. `.gitignore`의 `.env.*` 규칙으로 Git에서 제외된다.
- 브라우저 번들, `NEXT_PUBLIC_*`, 화면 HTML, 이슈, 회신, 보고서, 로그에는 키를 넣지 않는다.
- 일반 개발 자동검사는 `replay` 또는 수동 접수 흐름이다. `manual`은 API mode enum이 아니며 HTTP 분석 모드는 `replay`/`demo-live` 두 가지다. 실제 API를 쓰는 경우에만 `ONEFLOW_RUNTIME_MODE=demo-live`를 명시적으로 선택한다.
- `scripts/demo_openai_env.py`는 키 값을 출력하지 않는다. `verify`는 모델 생성 요청을 하지 않고 인증 가능한 모델 목록만 조회한다.
- 앱이 생기면 서버 측 live adapter만 이 파일을 읽는다. 프론트엔드가 OpenAI에 직접 요청하지 않는다.

공식 OpenAI 문서도 API 키를 환경변수 또는 서버의 키 관리 서비스에서 읽고 클라이언트 코드에 노출하지 않도록 안내한다. [OpenAI API Quickstart](https://platform.openai.com/docs/quickstart/make-your-first-api-request), [API 인증 문서](https://platform.openai.com/docs/api-reference/authentication).

## 로컬 준비

```powershell
python scripts/demo_openai_env.py store
python scripts/demo_openai_env.py status
python scripts/demo_openai_env.py verify
```

`store` 프롬프트에 실제 키를 붙여 넣는다. 키는 화면에 표시되지 않는다. 다른 PC에는 키 파일을 Git으로 전달하지 않고, 해당 PC에서 별도로 입력한다.

## 비용 규칙

| 항목 | 값 | 의미 |
|---|---:|---|
| 사전 경고 | $25 | 남은 데모 호출 계획을 다시 계산하고 사용자에게 알림 |
| 사용자 승인선 | $30 | 누적 예상액이 넘을 가능성이 있으면 추가 호출 전에 사용자에게 보고 |
| 개발 기본 | $0 API | fixture/replay로 개발·자동검사 |

`.env.demo.local`의 25/30달러 값은 **우리 애플리케이션 정책 표시**다. 앱의 호출별 사용량 장부가 구현되기 전까지 자동 차단을 보장하지 않는다. OpenAI 프로젝트의 실제 Limits에서 별도의 알림 또는 하드 제한을 설정해야 계정 수준에서 통제된다. 프로젝트 예산·한도 동작은 [OpenAI 프로젝트 관리 안내](https://help.openai.com/en/articles/9186755-managing-projects-in-the-api-platform)를 따른다.

live adapter 구현 시 각 응답의 모델·입출력 토큰·요청 ID·예상 비용을 비밀값 없이 로컬 장부에 적고, 호출 전 누적 예상액을 확인한다. 가격은 모델 확정 시 공식 가격을 다시 조회한다. 모델과 단가가 미정이므로 지금 비용을 임의 계산하지 않는다.

## 현재 완료선

키 파일 저장, Git 제외 확인, 인증 확인까지는 환경 연결이다. 실제 제품의 live 호출, 모델 선택, 프롬프트, 정확도 평가, 비용 장부는 A01에서 별도 구현·검증한다. 연결됐다는 사실을 실제 데모 기능 완료로 해석하지 않는다.
