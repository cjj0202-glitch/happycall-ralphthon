# CJJ AWS 배포 준비 실측 — 2026-09-22

현재 CJJ에서는 최종 프런트 빌드와 Lambda 번들 생성에 필요한 Python 3.12·pip를 사용할 수 있습니다. **지정 개인 AWS 계정의 기존 인증 경로와 실행 가능한 배포 Action은 확인되지 않아 이 PC에서 실제 배포할 준비는 미완료**입니다. 신규 자격 발급·다른 업무 계정 사용·AWS 자원 변경·배포는 하지 않았습니다.

## 고정 대상과 조사 범위

- 개인 AWS 계정 `704995468470`, profile `scmops-lab`, 리전 `ap-northeast-2`.
- 기존 Lambda `happycall-oneflow-api`; 기존 DynamoDB `happycall-oneflow-state`, Lambda 환경변수·Function URL·IAM·게임 S3/CloudFront·SCM 자원을 보존합니다.
- 기준 증거: `reports/deployment/aws-minimal-deployment-20260922.md`, `scripts/restore_main_pc_access.py`, `scripts/build_aws_bundle.py`, `scripts/build_deployment_bundle.py`.
- 앞선 배포 증거의 실제 PC는 hostname `최제준`입니다. `git show 49c7860:channel/pcs.json`의 pc1 hostname과 배포 보고가 일치합니다. 현재 CJJ로 메인을 이전한 사실과 이전 PC의 AWS 설정 보유 여부는 서로 다른 사실입니다.

## CJJ에서 확인한 상태

| 검사 | 실제 결과 |
|---|---|
| `C:/Users/choi8/.aws` | 디렉터리 없음 |
| 현재 프로세스의 `AWS_*` 환경변수 | 이름 목록 0개; 값은 읽거나 출력하지 않음 |
| PATH의 AWS CLI | 없음 |
| `C:/Program Files/Amazon/AWSCLIV2/aws.exe` | 없음 |
| 로컬 Windows 사용자 디렉터리 | `choi8`, `Public`; 다른 사용자 프로필의 자격을 열람하지 않음 |
| 지정 키 인벤토리 | 관련 키 이름·목차·경로 형식만 선별 조사. AWS 문자열 6곳은 ECOS/JIRA/KOSIS/NAVER/OPINET 관련 절에 있었으며 지정 계정·profile·개인 AWS 자격 경로는 확인되지 않음. 원문 값 전수 출력 없음 |
| 원 저장소 및 worktree `.local`의 aws/handoff/recovery 이름 디렉터리 | 해당 이름 패턴의 디렉터리 미관측. `.local` 모든 파일이나 다른 PC의 상태 부재까지 주장하지 않음 |
| GitHub Actions 원격 목록 | `gh api repos/cjj0202-glitch/happycall-ralphthon/actions/workflows` → `total_count: 0`, `workflows: []` |
| 저장소 내 Action 파일 | `.github/_pending/reply-gate.yml`만 발견. 편지 종결 검증용 대기 파일이며 배포 workflow가 아님 |
| Python 3.12 | `C:/Users/choi8/AppData/Roaming/uv/python/cpython-3.12.14-windows-x86_64-none/python.exe` |
| 위 Python의 pip | `pip 26.2.1` 실제 실행 성공 |

지정 인벤토리: `C:/Users/choi8/OneDrive - GS Retail Co., Ltd/_시크릿관리/2026-09-07_키_인벤토리.md`. 이 인벤토리에서 발견된 타 업무 키나 설정은 이번 개인 AWS 인증에 사용하지 않았습니다. GitHub workflow 목록 읽기는 성공했으므로 단순히 조회 권한 오류를 0건으로 보고한 것이 아닙니다.

## 최종 빌드 이후 번들 생성 절차

이번 조사에서는 빌드를 실행하지 않았습니다. 메인이 최종 제품 변경을 마친 뒤 아래 순서로 실행합니다. `build_aws_bundle.py`는 AWS 로그인 없이 완료된 Next export를 확인하고 hash가 고정된 공개 Linux wheel을 내려받아 Lambda ZIP을 만듭니다.

```powershell
Set-Location -LiteralPath 'C:/00.프로젝트/happycall-workflow-ux'
& 'C:/Users/choi8/AppData/Roaming/uv/python/cpython-3.12.14-windows-x86_64-none/python.exe' scripts/build_deployment_bundle.py --build
& 'C:/Users/choi8/AppData/Roaming/uv/python/cpython-3.12.14-windows-x86_64-none/python.exe' scripts/build_aws_bundle.py
```

첫 명령은 프런트 source fingerprint와 output fingerprint를 기록합니다. 제품 소스가 바뀌면 기록도 다시 생성해야 합니다. 두 번째 명령은 Python 3.12를 강제하고 프런트 완료 기록·소스 정합·미디어 whitelist·시크릿 제외·Linux x86_64 wheel·ZIP/확장 크기·SHA를 검증합니다. 기본 Python 3.14로 대체하면 안 됩니다.

출력은 `C:/00.프로젝트/happycall-workflow-ux/dist/aws/<출력 시각>-<HEAD 앞12자리>/oneflow-lambda.zip` 및 `manifest.json`입니다. 정확한 신규 디렉터리명은 아직 빌드하지 않았으므로 미정이며, 생성 결과의 경로를 사용해야 합니다. 이후 같은 Python으로 `scripts/build_aws_bundle.py --verify <생성된 디렉터리>`를 실행할 수 있습니다. 최종 HEAD와 프런트/서버 내용이 바뀌지 않은 상태의 ZIP만 전달합니다.

## 배포 실행 환경 인계

우선 기존 개인 AWS 배포를 수행한 **hostname `최제준`의 현재 로그인 사용자 환경**에서 `scmops-lab` profile을 확인해야 합니다. 기존 자격의 후보 위치는 그 PC의 `%USERPROFILE%/.aws/config`, `%USERPROFILE%/.aws/credentials` 및 기존 인증 캐시입니다. 이것은 Windows AWS 표준 위치이며, 이번 CJJ 조사로 원격 파일의 존재나 실제 사용자 절대경로를 확인한 것은 아닙니다. 원격 저장소 루트를 임의로 C: 또는 D:로 정하지 않습니다.

그 환경에서 먼저 아래 읽기 전용 명령으로 대상 일치를 확인합니다. 응답은 계정·함수 ARN만 제한하며 Lambda 환경변수 전체를 콘솔에 출력하지 않습니다.

```powershell
aws sts get-caller-identity --profile scmops-lab --region ap-northeast-2 --query Account --output text
aws lambda get-function-configuration --function-name happycall-oneflow-api --profile scmops-lab --region ap-northeast-2 --query FunctionArn --output text
```

기대값은 각각 `704995468470`, `arn:aws:lambda:ap-northeast-2:704995468470:function:happycall-oneflow-api`입니다. 성공 뒤 CJJ에서 검증한 동일 ZIP·manifest와 최종 커밋을 전달하여 **기존 함수 코드만** 갱신할 수 있습니다. 계정·함수 일치가 확인되기 전에 다른 profile로 우회하지 않습니다. 신규 자격 발급이나 조직 AWS 설정 복사는 이 인계에 포함하지 않습니다.

계정·함수 일치 후 기존 비공개 접속 정보 복구가 필요하면 저장소의 `scripts/restore_main_pc_access.py --profile scmops-lab`가 이미 준비되어 있습니다. 이 스크립트는 개인 계정·함수 ARN을 검증하고 Git 제외 `.local/main-pc-handoff-20260922/{PRIVATE_ACCESS.md,openai.env,access.json}`에만 신규 저장하며 기존 파일은 덮어쓰지 않습니다. 이번 조사에서는 비밀정보 복구 스크립트를 실행하지 않았습니다.

## 비용·남은 검증

AWS 이전 관측 원장은 2,935센트였으나 이후 CJJ 실제 AI 4작업을 합산한 보수 예약은 **2,995/3,000센트**입니다. 최신 정본 증거는 `.local/verified-live-demo/demo-usage.json`과 `reports/validation/two-case-live-20260922.md`입니다. 배포 검증은 무료 replay로 수행하며 기존 원장을 초기화하거나 낡은 2,935센트를 전체 잔여 기준으로 사용하면 안 됩니다.

최종 ZIP 생성, AWS STS 현재 세션, 함수 코드 갱신, 원격 코드 해시 대조, 배포 후 제목·회신 저장 및 두 사례 UI 검증은 아직 이 조사에서 수행하지 않았습니다. 기존 AWS 인증 환경 복구가 필요한 것은 실행 권한·접속 상태의 문제이며 사용자 배포 승인 여부를 다시 묻는 단계가 아닙니다.

## 후속 실측 — 최종 제품 2bc0a458 번들 생성 완료

위의 빌드 미실행 상태는 후속 실행으로 갱신되었습니다. 제품 기준 커밋은 `2bc0a458eb2d526ec006d260287afd8c4acc4b8c`입니다. 2026-09-22 09:44:43 KST에 `build_deployment_bundle.py --build`가 완료 기록을 생성했습니다. `sourceBefore`와 `sourceAfter`가 일치했고, 프런트 산출물은 27개입니다. `.next-dev` 개발 서버와 별도의 `.next` 빌드 경로를 사용했습니다.

- ZIP 절대경로: `C:/00.프로젝트/happycall-workflow-ux/dist/aws/20260922T004514388301Z-2bc0a458eb2d/oneflow-lambda.zip`
- manifest: 동일 디렉터리의 `manifest.json`
- ZIP SHA-256: `82a3a7b52592aef1ff1cf517011bb7280ed83cb41414fadc26d915b31d323254`
- 압축 크기 **33,361,315 bytes**, 확장 크기 **58,988,425 bytes**
- **4,338파일**, Linux 의존성 wheel **41개**
- 프런트 source fingerprint: `854597a3976620b692ef8a6358307382319952f71092c0d24c83d90ebd3b9db9`
- 프런트 output fingerprint: `0abd5115109a421a1868f50d2aeebb0254783659fa330707f02df442dbd6d3d6`

빌드 결과의 자동 검증과 별도의 `build_aws_bundle.py --verify`가 모두 `verified-local-only`를 반환했습니다. 독립 ZIP 열람으로 manifest 파일 4,338개와 archive 항목 4,338개가 일치하고 CRC 오류 없음, 금지 경로 `.local/.aws/.ssh/.env*` 0개, 검사한 OpenAI 키·개인키 시그니처 해당 파일 0개를 확인했습니다. 이 패턴 검사는 모든 종류의 비밀값 부재를 보장하는 검사는 아니며 빌더의 whitelist·내용 검사와 함께 적용한 결과입니다.

**출력 인코딩 이슈:** 첫 AWS 번들 생성에서 부모 Python `-X utf8`와 pip 자식의 Windows 출력 인코딩 차이로 로그 읽기 스레드에 `UnicodeDecodeError`가 나타났습니다. 빌더는 완료 후 ZIP을 검증했고, UTF-8 강제 옵션 없이 별도로 재실행한 `--verify`는 예외 없이 exit 0으로 완료했습니다. 로그 디코딩 이슈와 최종 ZIP 바이트·manifest·CRC 검증 결과를 구분합니다. 이 조사에서 빌더 제품 코드는 수정하지 않았습니다.

### 로컬 회귀 검사

1. `pytest tests/test_reply_draft.py tests/test_deployment_app.py tests/test_deployment_login.py -q`: **205 passed, 3 skipped, 5 warnings**. skip은 Windows 실제 symlink 생성 권한 부족 경로이며 성공으로 합산하지 않았습니다. 경고는 기존 라이브러리 deprecation입니다.
2. `pytest tests/test_deployment_bundle.py tests/test_dynamodb_store.py -q -rs`: 최초 **87 passed, 1 failed**. 실패는 독립 번들의 로그인 검사 fixture가 명시 opt-in 없이 과거 기본 로그인 리다이렉트 303을 기대한 항목이었습니다. 현재 제품은 사용자 요청으로 공개 기본 모드이며 `ONEFLOW_REQUIRE_LOGIN=1`일 때 기존 로그인 모드를 사용합니다.
3. 메인에게 추가 소유권을 받아 `tests/test_deployment_bundle.py`의 해당 선택적 로그인 fixture에 `ONEFLOW_REQUIRE_LOGIN=1`을 명시했습니다. 제품 코드는 변경하지 않았습니다. 같은 실패 테스트 `test_real_runtime_imports_and_asgi_work_without_original_repository`를 다시 실행하여 **1 passed**를 확인했습니다. 전체 묶음을 다시 실행했다고 주장하지 않으며, 기존 통과 87개와 변경 대상 재검 1개를 구분합니다.

증거 파일은 `.local/final-check/aws-build.txt`, `aws-verify.txt`, `zip-independent-check.json`, `pytest-bundle-dynamodb.txt`, `pytest-bundle-runtime-recheck.txt`입니다. 기존 파일에 비밀값을 출력하거나 복사하지 않았습니다. 최종 E2E는 별도 담당이며, 이번 결과는 **로컬 배포 ZIP 생성·검증 완료**입니다. AWS 인증 복구·실제 배포·원격 코드 해시 대조는 여전히 미실행입니다.
