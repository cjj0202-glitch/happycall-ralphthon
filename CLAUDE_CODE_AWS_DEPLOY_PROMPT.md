# Claude Code 개인 AWS 배포 프롬프트

아래 내용을 저장소 루트에서 시작한 Claude Code에 그대로 붙여 넣으세요.

```text
AI-GO 최신 main을 기존 개인 AWS에 안전하게 배포해 주세요. 먼저 C:/Users/Administrator/.claude/CLAUDE.md, 현재 저장소와 상위 AGENTS.md, 저장소 CLAUDE.md, 수정 대상에 가까운 CLAUDE.md를 읽으세요. 이어서 CLAUDE_CODE_AWS_DEPLOYMENT_HANDOFF.md, CLAUDE_CODE_UI_HANDOFF.md, reports/deployment/aws-aigo-v5-deployment-20260922.md를 읽고 고정 계정·함수·데이터 보존 계약을 인수하세요.

배포 대상은 account 704995468470, profile scmops-lab, ap-northeast-2, Lambda happycall-oneflow-api, DynamoDB happycall-oneflow-state입니다. 다른 AWS 계정이나 기존 게임·SCM 자원을 사용하거나 수정하지 마세요. 현재 AWS version 5는 소스 2e5454217707a956e8173a376f65ff949ee2607b이므로 최신 origin/main보다 뒤에 있을 수 있습니다.

먼저 git status, branch, HEAD, origin/main을 읽고 사용자·다른 도구의 미커밋 및 미추적 변경을 보존하세요. reset --hard, clean, 자동 stash, git add 전체를 사용하지 마세요. 안전하게 fast-forward 가능한 경우에만 최신화하고 배포 SHA를 고정하세요. 관련 테스트, TypeScript, production export, build_aws_bundle 생성과 --verify를 모두 통과한 새 ZIP만 사용하세요.

AWS STS account와 FunctionArn을 제한된 query로 확인하고 환경변수 전체나 비밀값을 출력하지 마세요. 배포 직전 RevisionId를 읽어 update-function-code --publish에 --revision-id를 전달하세요. update-function-configuration은 사용하지 말고 기존 환경변수·OpenAI 키·ONEFLOW_SESSION_SECRET·Function URL·IAM·DynamoDB 데이터·원장을 그대로 보존하세요. 로컬 ZIP SHA-256의 Base64와 AWS CodeSha256이 일치하고 Active/Successful인지 확인하세요.

배포 후 실제 AI·STT·회신 생성 없이 Function URL, AI-GO 브랜드, health, 사례 목록과 revision 보존, stale write 409, WAV, MP4 Range, /.env 차단, 상담원·센터·경영주 실제 화면을 검증하세요. 최신 공유 원장 29.95/30달러와 AWS health 29.50/30달러가 불일치하므로 추가 유료 호출과 원장 초기화는 금지합니다. 기본 공개 화면과 ONEFLOW_REQUIRE_LOGIN=1 선택 로그인 계약을 임의로 바꾸지 마세요.

실패하면 강제 배포하거나 데이터를 초기화하지 말고 정확한 단계와 증거를 보고하세요. 성공하면 배포 Git SHA, ZIP SHA/크기/파일 수, published version, CodeSha256 일치, HTTP/브라우저 검사 결과, AI 호출 0, 보존한 자원과 남은 결함을 reports/deployment의 새 Markdown에 기록하고 명시 경로만 커밋·push하세요.
```
