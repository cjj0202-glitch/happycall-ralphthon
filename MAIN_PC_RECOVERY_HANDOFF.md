# 복구된 원메인 PC 인계 — HappyCall OneFlow

작성 기준: 2026-09-22 09:00 KST 최종 인계. 사용자가 원메인 PC 복구와 현재 작업의 Git 커밋·Markdown 인계를 요청했습니다. **원메인 CJJ의 복구는 사용자 보고이며, 이 문서 작성자가 직접 접속하거나 신원을 재검증하지 않았습니다.** 현재 PC는 새 구현·배정·과금을 중지하고 아래 검증된 상태를 인계합니다.

## 현재 기준과 메인 소유권

- 저장소: [cjj0202-glitch/happycall-ralphthon](https://github.com/cjj0202-glitch/happycall-ralphthon), `main`.
- 현재 실제 hostname은 `최제준`, GitHub 계정은 `cjj0202-glitch`입니다. 현재 `channel/pcs.json`의 활성 pc1도 **최제준 한 대**입니다. CJJ가 켜졌다는 이유만으로 두 PC가 동시에 메인 배정·통합·배포를 실행하지 않습니다.
- 최신 제품 커밋: `49c78604fa29fa2613800284f1514c42084094c1` — AWS 로그인 폼·서명 세션·사용자 요청 계정 적용. 현 pc1이 커밋·push·원격 main 일치를 확인했습니다. 이 인계 문서의 후속 커밋은 제품 SHA와 구분합니다.
- 최초 AWS 배포 제품: `f4916ca5b55a599dc9ba430d4b9642f9c2f88fcf`. 최신 로그인 수정은 Lambda version 4로 배포했고 실제 HTTPS25/25와 브라우저 접속을 확인했습니다.
- 현재 저장소 절대 경로: `C:\Users\Administrator\Documents\Codex\2026-09-22\pc-pc\happycall-ralphthon`.

## 개인 AWS 배포 — 기존 게임과 별도 자원

**접속 주소:** [HappyCall OneFlow](https://yrvhgwajh4zcfalqsdidrnm32a0oeltw.lambda-url.ap-northeast-2.on.aws/)

| 항목 | 고정 대상 / 상태 |
|---|---|
| 계정·프로필·리전 | 개인 AWS `704995468470` / `scmops-lab` / `ap-northeast-2` |
| Lambda | `happycall-oneflow-api`, Python 3.12 / x86_64, 1024 MB, timeout 240초 |
| HTTPS | 같은 Function URL에서 정적 화면과 API 제공 |
| 영속 저장 | DynamoDB `happycall-oneflow-state`, 문자열 파티션 키 `pk`, PAY_PER_REQUEST |
| 실행 역할 | `happycall-oneflow-lambda`; 해당 테이블 GetItem/PutItem과 전용 로그 쓰기 |
| 로그 | 전용 Lambda 로그 보존 3일 |
| 기존 자원 | 게임 `dawn-return-line`의 S3/CloudFront와 기존 SCM 자원은 변경하지 않았으며 계속 보존 |

최초 배포에서 실제 HTTPS **19/19**, 업무 흐름 **6/6**, 음성·영상 바이트/Range와 별도 Lambda cold start 후 동일 종결 기록을 확인했습니다. 이는 최초 제품 검증이며 로그인 수정 후 검증 수치와 합산하지 않습니다. AWS에는 기본 합성 2건과 검증 접수 `INT-53E58A50` 1건, 총 3건이 있습니다. 검증 접수는 API 담당 확인→이관→회신→종결 revision 5까지 저장됐습니다. 실제 사람 검수를 수행한 것은 아닙니다.

기존 AWS 외부 응답의 401에 `WWW-Authenticate`가 없어 사용자 브라우저에 Basic 창이 나타나지 않는 현상을 재현했습니다. 최신 코드는 미인증 `GET /`를 `/login`으로 보내고 한국어 로그인 폼을 제공합니다. 기존 Basic API 인증은 유지하며 성공 시 8시간 이내의 Secure/HttpOnly/SameSite=Strict 서명 쿠키를 사용합니다. API·미디어 인증, 동일 출처 쓰기 제한과 쿠키 위변조·중복·만료 차단은 유지합니다. 실제 브라우저에서 드러난 Origin null/403은 로그인 응답의 Referrer-Policy를 same-origin으로 수정했습니다. 사용자 요청 짧은 PIN은 명시적인 데모 설정과 별도 난수 서명 비밀이 있을 때만 허용합니다.

### 최신 로그인 배포 검증 — 완료

- 제품 SHA: `49c78604fa29fa2613800284f1514c42084094c1`, published version **4**, Active/Successful. URL은 같은 코드·설정의 `$LATEST`를 가리킵니다.
- zip: `dist/aws/20260921T235527002287Z-49c78604fa29/oneflow-lambda.zip`; SHA256 `bacdd975c8372afcbcda85f752fba5a81d9214bd53e00d36a341436471dc5e8a`; 원격 CodeSha256 `us3Zdcg3Kvy82oX3UvulqB2SFL1T4A02o0FDZHHcXoo=` 일치.
- 신규 로그인27 + 앱160 = **187 PASS**, 기존 경고5. 앞선 광범위 검사에서 구식 문자열에 의존한 테스트1건을 수정한 이력은 보존하며 전체 재실행 성공으로 바꾸지 않습니다. 당시 AWS 묶음70검사는 통과했습니다.
- 실제 AWS **25/25**: 로그인 성공·실패, 루트 이동, 쿠키 속성·CSRF, 정적8파일, API·음성·영상 Range, `.env` 차단, 종결 접수 revision5와 예산 보존.
- **08:56:41 KST 실제 내장 브라우저 로그인 성공**, 상담원 화면·접수3건(대기2/종결1) 표시 확인. 세 역할 전체 최종 회귀·사람 검수까지 완료한 것은 아닙니다.
- 증거: `.local/aws-deploy-20260922/deployment-login.json`, `login-cloud-checks.json`. 이전 v2 결과도 별도 보존했습니다. 로그인 확인의 새 AI 호출0입니다.

## Git으로 이전되지 않는 자료와 비용

아래는 **현 PC 저장소 루트 기준 경로**입니다. Git clone/pull은 이 파일, AWS 프로필, API 키, 로그인 비밀, 실행 중 서버, 예약을 옮기지 않습니다. 비밀값은 이 문서에 포함하지 않았습니다. 인계가 필요하면 승인된 비공개 경로로 별도 이전하고, 비밀이 포함된 파일을 Git·이슈·공개 로그·Lambda zip에 넣지 않습니다.

| 경로 | 용도 |
|---|---|
| `.local/aws-deploy-20260922/접속안내.md`, `access.json` | 브라우저 접속 정보. 비밀파일이며 내용 출력·Git 추가 금지 |
| `.local/aws-deploy-20260922/lambda-environment.json` | 서버 환경 준비 자료. API 키 등 비밀 포함 가능; 내용 출력·Git 추가 금지 |
| `.local/main-pc-handoff-20260922/PRIVATE_ACCESS.md` | API 키와 최종 로그인 정보를 함께 기록한 비공개 인계. 실제 AWS 복원·일치 검증 완료, Git 제외 |
| `.local/aws-deploy-20260922/` | 최초 배포·HTTP·AI 1회·업무·영속 저장 검증 원본. `deployment.json`, `final-status.json`, `http-checks.json`, `live-attempt.json`, `workflow-checks.json`, `case-completed.json`, `persistence-checks.json` |
| `.local/main-resume-20260922/replay-state/` | 현 PC 로컬 replay 접수 5건. AWS 3건과 다른 상태이며 자동 합치기·덮어쓰기 금지 |
| `dist/aws/` | 현 PC에서 만든 AWS zip과 검증 자료. 복구 PC에서는 해당 제품 SHA로 재생성·검증 |
| 복구 CJJ의 기존 `.local`, `.env`, 키·원장·원본 로그 | 아직 실제 확인·이전하지 않은 원본. 복구 시 우선 보존 |

현재 AWS 보수 비용 원장은 **2,935/3,000센트(29.35/30달러)**, 잔여 65센트입니다. 과거 공개 관측 2,920센트 이월 + AWS 텍스트 분석 1회 예약 15센트이며 실제 공급자 청구액이 아닙니다. **원본 104건 원장은 복원하지 않았습니다.** 최초 AWS 연결 검증 이후 모델 검토·로그인 수정·인계 중 추가 유료 호출은 0입니다. 복구 PC의 원장을 찾더라도 이월액과 원본 합계를 중복 합산하거나 예산을 0으로 초기화하지 않습니다. 기존 DynamoDB 문서는 유지하고 bootstrap을 재초기화 용도로 실행하지 않습니다.

사용자는 API 키까지 함께 인계하도록 명시했습니다. `scripts/restore_main_pc_access.py`는 기존 개인 AWS의 Lambda 환경에서 필요한 값을 읽어 **동일 계정·Lambda ARN을 검증한 뒤** Git 제외 비공개 안내·환경·접속 파일로 복원합니다. 실제 AWS 복원·키 일치·반복 실행 시 기존 파일 보존을 검증했습니다. 비밀값을 콘솔에 출력하지 않고 기존 파일을 덮어쓰지 않습니다. 복구 PC에서 아래 명령을 실행합니다. 결과 안내는 `.local/main-pc-handoff-20260922/PRIVATE_ACCESS.md`이며 이 파일이나 키값을 GitHub에 올리지 않습니다. 같은 폴더의 `openai.env`는 자동 로드되지 않습니다.

```powershell
python scripts/restore_main_pc_access.py --profile scmops-lab
```

각 PC에는 AWS CLI와 기존 계정 로그인/자격 설정이 필요합니다. 프로필이 없거나 읽기 권한이 부족하면 기존 승인 자격 설정부터 확인하며 새 IAM 권한을 확대하거나 다른 계정으로 우회하지 않습니다. 도구와 현 PC 비공개 안내 생성은 완료했으며 복구 PC에서의 실행·수신은 아직 확인하지 않았습니다.

## 복구 PC가 이어받는 5단계

1. **작업 중복부터 막습니다.** 복구 PC의 예전 유료 호출·자동 배포·예약을 재개하지 않은 상태로 기존 작업을 보존합니다. 현 PC의 heartbeat(ID `automation`)는 **08:54 KST PAUSED 확인**, 소유 감시 프로세스는 최종 중지 검사에서 **NOT_RUNNING**입니다. 로컬 시연 서버는 보존했습니다. 새 예약을 중복 생성하지 않습니다.
2. **복구 PC 신원과 로컬 변경을 확인한 뒤 최신화합니다.** 아래 읽기 명령으로 실제 hostname·GitHub 계정·브랜치·HEAD·변경을 확인합니다. 미커밋·미추적 작업이 있으면 먼저 별도 보존하고 자동 reset/clean/stash로 덮지 않습니다. 기존 checkout의 `main`이 안전하게 fast-forward 가능할 때만 `git pull --ff-only origin main`을 실행합니다. 실패하면 기존 커밋을 보존한 채 분기 원인을 대조합니다. 저장소가 없을 때만 새 경로에 clone합니다.

   ```powershell
   python channel/whoami.py --hostname
   gh api user --jq .login
   git status --short
   git branch --show-current
   git rev-parse HEAD
   git pull --ff-only origin main
   python scripts/preflight.py
   ```

3. **pc1을 명시적으로 인계·재등록합니다.** 복구 메인이 위 실측 결과와 최신 인계 커밋을 대조한 뒤 `channel/pcs.json`의 pc1 hostname을 확인된 복구 PC 한 대로 이전하고 시각을 기록합니다. CJJ라고 추정해 강제 지정하지 않습니다. 현 PC의 자동 작업은 중지했으며 사용자 지시에 따라 복구 메인이 단일 책임을 이어받습니다. 기존 #8/#9/#10과 PC2~4의 신원·소유 작업을 유지하고 [편지함 감시](docs/19_4PC_편지함_감시_빠른시작.md)와 [왕복 확인](docs/17_편지함_왕복테스트.md)을 참조합니다.
4. **AWS 접속과 현재 상태를 먼저 확인합니다.** 복구 PC에서 승인된 기존 AWS 자격으로 `scmops-lab`의 계정·리전 일치를 확인합니다. 프로필 이름만 같다고 같은 계정으로 간주하지 않습니다. 비밀은 별도 안전하게 인계하며 기존 Lambda 환경변수·DynamoDB 3건·2,935센트 원장을 보존합니다. 최신 로그인 배포 결과와 실제 브라우저 접속을 확인하고, 확인만을 위해 AI 분석·접수 생성을 반복하지 않습니다.
5. **남은 품질·시연 작업을 새 메인 단일 책임으로 진행합니다.** 아래 미완료 항목과 DEC-027의 품질 기준을 우선합니다. 09:00 이후 새 구현·배정·과금은 기존 마감 결정과 최신 사용자 지시를 대조하고 진행 범위를 정합니다. 공식 제출 또는 새 모델 평가 완료를 현재 연결 검증만으로 선언하지 않습니다.

## 재빌드·코드 배포 시 보존할 계약

- AWS 패키징은 저장소 루트에서 **시스템 Python**으로 `python scripts/build_aws_bundle.py`를 실행합니다. 현 PC `.venv` Python은 pip 부재로 패키징에 실패한 이력이 있습니다. 복구 PC도 Python/pip·웹 빌드·등록 미디어 준비를 확인하고 성공한 산출물만 사용합니다. 런타임은 Linux Python 3.12/x86_64이며 Windows 의존성 폴더를 복사하지 않습니다.
- 기존 Lambda를 코드만 갱신할 때 `update_function_code` 범위를 사용하고 환경변수·실행역할·Function URL·테이블을 보존합니다. 전체 환경변수를 빈 값이나 추정 값으로 교체하지 않습니다. zip에 `.env`, `.local`, AWS 자격·API 키를 넣지 않습니다.
- 유지할 설정 이름은 `ONEFLOW_RUNTIME_MODE=demo-live`, `ONEFLOW_STORAGE_BACKEND=dynamodb`, `ONEFLOW_DYNAMODB_TABLE=happycall-oneflow-state`, `ONEFLOW_BUDGET_INITIAL_RESERVED_CENTS=2920`, `ONEFLOW_ACCESS_USER`, `ONEFLOW_ACCESS_PASSWORD`, `ONEFLOW_DEMO_PIN_LOGIN=1`, **`ONEFLOW_SESSION_SECRET`**, `OPENAI_API_KEY` 및 기존 모델 정책입니다. 키·비밀번호·서명 비밀은 출력하거나 추정 값으로 교체하지 않습니다. baseline 2920은 현재 총액 2935와 다른 초기 이월 기준이므로 재산정하거나 덮어쓰지 않습니다.
- Lambda에서 local-json 저장으로 전환하지 않습니다. 기존 문서 누락·불일치는 차단 상태로 다루고 새 빈 원장으로 우회하지 않습니다. DynamoDB 단일 문서의 앱 제한 350KiB는 대규모 운영 전에 재설계할 항목입니다.

## 완료·미완료·차단과 담당

| 상태 | 항목 | 인계 후 담당 |
|---|---|---|
| 완료 | 개인 AWS 최초 배포, API·영속 저장·실제 텍스트 AI 1회, 업무 6/6, 기존 게임 보존 | 현 pc1 증거 인계 → 복구 메인 운영 |
| 완료 | 로그인 수정·187PASS·AWS25/25·실제 화면 접속, 비공개 복원 도구·안내, 현 PC heartbeat 중지 | 복구 메인 운영 |
| 미완료 | 원메인 직접 접속·신원 재확인, pc1 재등록, 비공개 원본 자료 이전·수신 ACK | 복구 메인 |
| 미완료 | DEC-027 답변 품질 우선 모델 비교. 현재 `gpt-4.1-mini`; 단일 응답 6.625초는 최종 품질 선정 근거가 아님 | 복구 메인 + PC2 안영일/MR-A83 |
| 미완료 | 전용 파인튜닝·사내 정책 RAG·모범 답안 예시 주입. 현재는 업무 지시·strict schema·원문 근거 검사·서버 답변 초안 | 복구 메인 |
| 차단 / 미완료 | 기존 실제 음성 canary 12필드 중 4실패의 새 실모델 해결 검증, 공식 CLOVA 음원·사람 검수. 코드 반례 통과와 구분 | 복구 메인 + PC2 |
| 미완료 | 로그인·상담원 접수3건은 확인, 세 역할 전체 최종 브라우저 회귀·사람 검수는 남음 | 복구 메인 + PC3 LAPTOP-U2AL73UH/mcjun86-oss |
| 미연결 | Teams·카카오 실제 알림. 검증 사건 알림 의도 4건은 모두 `not_connected`; PC4 fake 구현은 별도 브랜치 | 복구 메인 + PC4 장준호/j324rst-svg |
| 미완료 | 실제 고객·통화·물류 운영 데이터 연동, 사용자별 운영 인증, 공식 제출 | 복구 메인 / 사용자 최종 확인 |

상세 근거는 [최소 초안 인계](DRAFT_HANDOFF.md), [AWS 실측 보고](reports/deployment/aws-minimal-deployment-20260922.md), [현재 TODO](CURRENT_TODO.md), [DEC-025~027](planning/decisions.md), [PC2 독립 인수](reports/pc2-r2-main-intake.md)를 참조합니다. 기존 보고서의 Basic 팝업 안내와 최초 배포 SHA는 당시 관측이며, 로그인 수정의 실제 반영 여부는 이 문서의 최신 배포 검증란과 새 증거로 판단합니다.
