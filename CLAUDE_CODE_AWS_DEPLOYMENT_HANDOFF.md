# Claude Code 개인 AWS 배포 인수인계 — AI-GO

작성 기준: 2026-09-22. Claude Code가 사용자의 개인 AWS에 AI-GO 최신 코드를 안전하게 재배포하기 위한 실행 절차입니다. API 키·AWS 자격·로그인 비밀번호·세션 서명 비밀은 이 문서에 포함하지 않습니다.

## 고정 배포 대상

| 항목 | 값 |
|---|---|
| AWS 계정 | `704995468470` |
| 기존 프로필 | `scmops-lab` |
| 리전 | `ap-northeast-2` |
| Lambda | `happycall-oneflow-api` |
| DynamoDB | `happycall-oneflow-state` |
| 실행 역할 | `happycall-oneflow-lambda` |
| Function URL | https://yrvhgwajh4zcfalqsdidrnm32a0oeltw.lambda-url.ap-northeast-2.on.aws/ |
| 현재 AWS 버전 | published version `5`, `$LATEST` Active/Successful |
| 현재 AWS 소스 | `2e5454217707a956e8173a376f65ff949ee2607b` |
| 현재 AWS CodeSha256 | `Gl631VmelUu3jENXLfugYMTTnND1YqdLsNa400bAiak=` |

저장소 `main`은 현재 AWS 소스보다 진행되었습니다. 따라서 현재 AWS가 최신 `main`이라고 가정하지 말고, 배포 직전 실제 `origin/main` SHA를 기록한 뒤 새 production export와 Lambda ZIP을 만들어야 합니다. 과거 ZIP에 새 HEAD를 덧붙이거나 기존 `.next`를 그대로 재사용하지 않습니다.

이 배포는 최근 게임의 개인 AWS 계정을 사용하지만 해피콜 전용 Lambda·DynamoDB만 변경합니다. 기존 게임 S3 `dawn-return-line-704995468470-ap-northeast-2`, CloudFront `E16QMH54EOX6NE`, 다른 SCM 자원은 수정하지 않습니다.

## 1. 로컬 상태와 최신 SHA 확인

먼저 공통 규칙과 저장소 규칙을 읽습니다. 사용자·다른 도구의 미커밋·미추적 파일은 보존합니다. 현재 작업 트리에 변경이 있으면 자동 reset, clean, checkout, stash, 전체 add를 하지 않습니다.

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git fetch origin main
git rev-parse origin/main
git log --oneline -5 origin/main
```

작업 트리가 안전하고 현재 브랜치가 `main`이며 fast-forward 가능한 경우에만 실행합니다.

```powershell
git pull --ff-only origin main
```

배포할 SHA를 별도 변수나 메모에 고정합니다. 빌드 뒤 HEAD가 달라지면 기존 ZIP을 배포하지 않고 다시 빌드합니다.

## 2. AWS 계정과 함수 일치 확인

AWS CLI를 찾지 못하면 공식 설치본 `C:\Program Files\Amazon\AWSCLIV2\aws.exe`를 확인합니다. 새 자격을 만들거나 다른 업무 계정으로 우회하지 않습니다. 기존 승인된 `scmops-lab` 프로필을 사용합니다.

```powershell
aws sts get-caller-identity `
  --profile scmops-lab `
  --region ap-northeast-2 `
  --query Account `
  --output text

aws lambda get-function-configuration `
  --function-name happycall-oneflow-api `
  --profile scmops-lab `
  --region ap-northeast-2 `
  --query '[FunctionArn,State,LastUpdateStatus,Runtime,Architectures]' `
  --output json `
  --no-cli-pager
```

계정은 반드시 `704995468470`, 함수 ARN은 `arn:aws:lambda:ap-northeast-2:704995468470:function:happycall-oneflow-api`, 런타임은 Python 3.12/x86_64여야 합니다. Lambda 환경변수 전체를 콘솔이나 로그에 출력하지 않습니다.

비공개 접속 정보를 현재 PC에 복원해야 할 때만 아래 도구를 사용합니다. 기존 결과가 있으면 덮어쓰지 않고 보존하는 것이 정상 동작입니다.

```powershell
python scripts/restore_main_pc_access.py --profile scmops-lab
```

결과는 Git 제외 `.local/main-pc-handoff-20260922`에만 저장됩니다. 값을 문서·이슈·커밋·화면 캡처에 붙이지 않습니다.

## 3. 테스트와 production 빌드

화면·서버 변경 범위에 맞는 테스트를 먼저 실행합니다. 최소 기준은 다음과 같습니다.

```powershell
npm --prefix apps/web run typecheck
python -m pytest -q `
  tests/test_reply_draft.py `
  tests/test_deployment_app.py `
  tests/test_deployment_login.py `
  tests/test_deployment_bundle.py `
  tests/test_dynamodb_store.py -rs
python scripts/build_deployment_bundle.py --build
```

`.venv`에 패키징용 pip가 없으면 AWS 번들 생성에는 시스템 Python 3.12를 사용합니다. Python 3.14나 Windows 전용 wheel로 대체하지 않습니다.

```powershell
python --version
python -m pip --version
python scripts/build_aws_bundle.py
```

마지막 명령이 반환한 `dist/aws/<timestamp>-<HEAD>/` 디렉터리를 그대로 사용해 별도 검증합니다.

```powershell
python scripts/build_aws_bundle.py --verify 'dist/aws/<실제 생성 디렉터리>'
```

기대 조건은 `verified-local-only`, Linux x86_64 의존성, `.env`·`.local`·AWS 자격·키 제외, manifest와 ZIP 파일 수·크기·SHA 일치입니다. 빌드 전후 프런트 source fingerprint가 달라지거나 HEAD가 바뀌면 배포하지 않습니다.

## 4. 코드 전용 배포

이 절차는 Lambda **코드만** 바꿉니다. 환경변수, 역할, timeout, 메모리, Function URL, DynamoDB, 기존 데이터와 원장은 그대로 둡니다. `update-function-configuration`은 사용하지 않습니다.

배포 직전에 revision ID를 다시 읽고, 다른 배포가 먼저 들어오면 실패하도록 guard를 겁니다.

```powershell
$awsExe = 'C:\Program Files\Amazon\AWSCLIV2\aws.exe'
$revision = & $awsExe lambda get-function-configuration `
  --function-name happycall-oneflow-api `
  --profile scmops-lab `
  --region ap-northeast-2 `
  --query RevisionId `
  --output text `
  --no-cli-pager

& $awsExe lambda update-function-code `
  --function-name happycall-oneflow-api `
  --zip-file 'fileb://dist/aws/<실제 생성 디렉터리>/oneflow-lambda.zip' `
  --publish `
  --revision-id $revision `
  --profile scmops-lab `
  --region ap-northeast-2 `
  --query '[FunctionName,Version,State,LastUpdateStatus,CodeSha256,RevisionId]' `
  --output json `
  --no-cli-pager
```

revision 충돌이면 다른 배포가 있었던 것이므로 새 상태를 읽고 중단합니다. 이전 revision을 무시해 강제 갱신하지 않습니다.

```powershell
& $awsExe lambda wait function-updated-v2 `
  --function-name happycall-oneflow-api `
  --profile scmops-lab `
  --region ap-northeast-2 `
  --no-cli-pager

& $awsExe lambda get-function-configuration `
  --function-name happycall-oneflow-api `
  --profile scmops-lab `
  --region ap-northeast-2 `
  --query '[FunctionArn,Version,State,LastUpdateStatus,CodeSha256,RevisionId]' `
  --output json `
  --no-cli-pager
```

로컬 ZIP SHA-256 바이트를 Base64로 변환한 값이 AWS `CodeSha256`과 일치해야 합니다.

```powershell
$zipHash = (Get-FileHash -LiteralPath 'dist/aws/<실제 생성 디렉터리>/oneflow-lambda.zip' -Algorithm SHA256).Hash
$expectedCodeSha256 = [Convert]::ToBase64String([Convert]::FromHexString($zipHash))
$expectedCodeSha256
```

## 5. 배포 후 무료 기능 검증

실제 AI 분석·STT·회신 생성은 실행하지 않습니다. 최신 공유 원장은 29.95/30달러이고 AWS health는 29.50/30달러로 45센트 차이가 있습니다. 보수적으로 29.95를 기준으로 삼아 유료 호출을 차단합니다.

다음을 확인합니다.

1. Function URL 루트 HTTP 200, 페이지 제목·헤더·푸터에 `AI-GO 무엇이든 물어보살` 표시.
2. `/api/health` HTTP 200, 상한 30달러. 원장 숫자는 관측값으로 기록하되 수정하지 않음.
3. `/api/cases`에서 기존 사례와 revision 보존. 목록 응답은 `{ "cases": [...] }` 형태.
4. stale `expectedRevision` 쓰기가 409이고 재조회 데이터가 변하지 않음.
5. WAV 원바이트 일치, MP4 Range 요청 206, `/.env` 404.
6. 실제 브라우저에서 상담원·센터·경영주 역할 전환과 접수 목록 표시.
7. 콘솔 예외, 정적 JS/CSS 404, 가로 넘침이 없는지 확인.

기본 화면은 현재 공개 모드입니다. `ONEFLOW_REQUIRE_LOGIN=1`일 때만 기존 로그인 보호를 사용합니다. 로그인 정책 변경은 코드 배포와 분리하고 사용자의 명시 지시 없이 환경변수를 바꾸지 않습니다.

## 6. 실패와 롤백

- 빌드·테스트 실패: AWS를 건드리지 않고 실패 로그와 고정 SHA를 보고합니다.
- STS 계정·함수 ARN 불일치: 즉시 중단합니다.
- revision 충돌: 새 원격 상태를 대조하고 강제 배포하지 않습니다.
- 업데이트 후 `Failed`: Lambda `LastUpdateStatusReason`과 전용 CloudWatch 로그만 확인하며 환경·데이터를 초기화하지 않습니다.
- 새 코드의 실행 결함: 보존한 직전 검증 ZIP을 동일한 revision guard와 `update-function-code --publish`로 다시 올립니다. 현재 version 5의 검증 ZIP은 `dist/aws/20260922T010144695869Z-2e5454217707/oneflow-lambda.zip`, SHA-256은 `1a5eb7d5599e954bb78c43572dfba060c4d39cd0f562a74bb0d6b8d346c089a9`입니다. 다른 PC에 이 파일이 없으면 추정해 재생성했다고 표시하지 않습니다.

롤백이나 재배포 모두 DynamoDB bootstrap, 원장 초기화, 환경변수 전체 교체를 사용하지 않습니다.

## 7. 완료 보고

다음 값을 남깁니다.

- 배포한 Git SHA와 원격 `origin/main` 일치 여부.
- 새 ZIP 경로·SHA-256·파일 수·크기.
- Lambda published version, Active/Successful, AWS CodeSha256 일치.
- 실제 URL과 HTTP/브라우저 검사 분모·결과.
- 새 AI 호출 수와 비용 변화. 무료 검사만 했다면 0으로 명시.
- 기존 데이터·환경·게임 자원 보존 여부.
- 발견된 결함과 미완료 범위.

검증 없이 배포 완료라고 쓰지 않습니다. 배포 기록은 `reports/deployment/`에 추가하고 비밀값은 포함하지 않습니다.
