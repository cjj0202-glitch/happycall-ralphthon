# AI-GO 다른 PC 배포 인계 — 2026-09-22

사용자 요청에 따라 CJJ는 커밋·푸시하고, 인증이 준비된 다른 PC가 배포합니다. 원격 `origin/main` 최신 커밋을 기준으로 진행합니다.

## 반영 내용과 확인

- 표시 이름: **AI-GO 무엇이든 물어보살**. 헤더·홈 링크·탭 제목·푸터·아이콘 변경.
- 앞선 `2bc0a45`에는 청취 강제 해제, 접수 대조 후 이관, 회신 제목·본문 생성/적용/등록 수정이 포함됩니다. `cc92cb6`에는 배포 검증 기록이 있습니다.
- 이름 변경 후 TypeScript 검사 통과, 실제 localhost 화면의 헤더·페이지 제목·푸터 표시 확인.
- 이전 기능 기준 브라우저 E2E 28/28 통과. 실제 AI 품질의 남은 한계는 `reports/validation/two-case-live-20260922.md`를 함께 확인합니다.

## 배포 PC 작업

1. 로컬 변경을 보존하고 `git fetch origin` 후 변경 충돌이 없는 경우에만 `git pull --ff-only origin main`을 실행합니다. 기존 작업을 reset/stash로 덮어쓰지 않습니다.
2. 개인 계정 `704995468470`, 서울 `ap-northeast-2`, 기존 프로필 `scmops-lab`을 STS로 확인합니다. 대상 Lambda는 `happycall-oneflow-api`입니다.
3. 웹 의존성을 준비하고 Python 3.12 환경에서 아래 순서로 **새로 빌드**합니다. 과거 2bc0a45 ZIP에는 새 브랜드가 없습니다.

```powershell
python scripts/build_deployment_bundle.py --build
python scripts/build_aws_bundle.py
python scripts/build_aws_bundle.py --verify '<위 명령이 반환한 dist/aws 하위 폴더>'
```

4. 검증된 `oneflow-lambda.zip`으로 기존 함수의 코드만 갱신합니다. 기존 환경변수·키·DynamoDB `happycall-oneflow-state`·기존 데이터·예산 원장을 보존합니다. 과금 원장을 초기화하지 않습니다.
5. 배포 후 HTTPS 화면 브랜드, 상태 조회, 두 사례의 이관·중간/최종 회신을 시연 데이터에서 검증하고 실제 배포 SHA·URL·결과를 회신합니다. 실제 API 검증은 비용 원장 대조 후에만 진행합니다.

기존 서비스 URL: https://yrvhgwajh4zcfalqsdidrnm32a0oeltw.lambda-url.ap-northeast-2.on.aws/

## 구분할 상태

CJJ에서 AWS 로그인 창만 열었고 인증·새 버전 배포는 미완료입니다. 기존 OneFlow 이름의 약 242초 녹화는 참고 원본이며, 새 이름의 자막·CLOVA 더빙 최종 영상은 미완료입니다. 키·원천자료·로컬 영상은 이번 Git 커밋에 포함하지 않습니다.
