# AI-GO 개인 AWS 배포 및 기능 검증 — 2026-09-22

원격 `main`의 `2e5454217707a956e8173a376f65ff949ee2607b`을 개인 AWS 계정 `704995468470`, 서울 `ap-northeast-2`의 기존 Lambda `happycall-oneflow-api`에 코드만 갱신했습니다. 기존 환경변수·OpenAI 키·DynamoDB `happycall-oneflow-state`·Function URL·IAM·게임 자원은 변경하지 않았습니다.

## 배포 결과

- Function URL: https://yrvhgwajh4zcfalqsdidrnm32a0oeltw.lambda-url.ap-northeast-2.on.aws/
- published version: `5`; `$LATEST` 상태 `Active`, 마지막 갱신 `Successful`.
- 산출물: `dist/aws/20260922T010144695869Z-2e5454217707/oneflow-lambda.zip`.
- ZIP SHA-256: `1a5eb7d5599e954bb78c43572dfba060c4d39cd0f562a74bb0d6b8d346c089a9`.
- 로컬 ZIP과 AWS CodeSha256: `Gl631VmelUu3jENXLfugYMTTnND1YqdLsNa400bAiak=` 일치.
- 압축 33,361,880 bytes, 확장 58,988,795 bytes, 4,338파일. 빌더 생성 검사와 별도 `--verify` 모두 `verified-local-only`.
- 최신 변경 계약에 따라 기본 화면은 공개 모드이며 `ONEFLOW_REQUIRE_LOGIN=1`일 때만 로그인 보호를 사용합니다. 이번 작업은 기존 환경변수를 바꾸지 않았습니다.

## 코드·패키지 검사

- TypeScript `tsc --noEmit`: 통과.
- Python reply draft·deployment app/login·bundle·DynamoDB 묶음: **296 passed**, 기존 deprecation warning 5.
- Next production export와 `.oneflow-build.json` 기록: 성공.
- 소스 작업 트리는 배포 전 원격 `main`으로 fast-forward했고 제품 파일의 별도 로컬 수정은 없었습니다.

## 실제 AWS 기능 검사

유료 AI 분석·STT·회신 생성은 실행하지 않았습니다. replay/read와 충돌이 확정된 쓰기 요청만 사용했습니다.

- HTTPS 자동 검사 **12/12 통과**: 공개 루트와 AI-GO 브랜드, health/30달러 상한, 사례 목록 4건, `CASE-0001`, `CASE-0002`, `INT-53E58A50`, revision 5 종결 데이터 보존, stale revision 409와 저장 불변, WAV 원바이트 일치, MP4 Range 206/1024 bytes, `/.env` 404.
- 실제 브라우저: 제목·헤더·푸터의 `AI-GO 무엇이든 물어보살`, replay 기본 선택, 접수 4건을 확인했습니다.
- 상담원: 대기 2건, CASE-0001 원문·AI 정제·필수정보 대조·이관 UI 표시 정상.
- 센터: 새 이관 1건, CASE-0002 이관 내용·WMS/TMS 근거·회신 작성 진입 UI 표시 정상.
- 경영주: 신규 문의 폼, 전체 4건 선택, CASE-0001 진행 상태와 미등록 회신 상태 표시 정상.
- 실제 외부 Teams·카카오 알림, 사람 사용성·음성 품질, 새 실제 AI 답변 품질은 이번 배포 검사 범위가 아닙니다.

원본 자동 검사 결과는 Git 제외 `.local/aws-deploy-20260922/aigo-v5-functional-checks.json`에 보존합니다.

## 발견 사항

원격 `/api/health`의 보수 예약액은 **29.50/30달러**입니다. 최신 CJJ 공유 원장 문서와 로컬 증거의 **29.95/30달러**와 45센트 차이가 있습니다. 코드 배포 전후 AWS DynamoDB 데이터를 초기화하거나 원장 값을 수정하지 않았고, 이번 검사에서 새 AI 호출도 하지 않았습니다. 따라서 기능을 차단하지는 않지만 **공유 원장과 AWS 영속 원장의 병합 미완료**로 분류합니다. 후속 유료 호출은 금지한 채 원본 109건 원장과 AWS 문서의 항목별 합계를 대조해야 합니다.

이번 검증에서 배포 중단이 필요한 P1/P2 실행 결함은 재현되지 않았습니다. 비용 원장 불일치는 완료로 숨기지 않고 후속 차단 항목으로 유지합니다.
