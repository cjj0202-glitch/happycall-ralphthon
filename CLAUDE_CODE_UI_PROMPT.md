# Claude Code 시작 프롬프트

아래 내용을 저장소 루트에서 시작한 Claude Code에 그대로 붙여 넣으세요.

```text
AI-GO 화면 작업을 이어서 진행해 주세요. 먼저 C:/Users/Administrator/.claude/CLAUDE.md, 현재 저장소와 상위의 AGENTS.md, 저장소 CLAUDE.md, 수정 대상에 가장 가까운 CLAUDE.md를 읽고 우선순위를 적용하세요. 그다음 CLAUDE_CODE_UI_HANDOFF.md와 reports/deployment/aws-aigo-v5-deployment-20260922.md를 읽어 현재 화면, AWS 배포 상태, 검증 범위, 비용 원장 불일치를 인수하세요.

현재 기준 저장소는 cjj0202-glitch/happycall-ralphthon main이고 화면 제품 기준은 2e5454217707a956e8173a376f65ff949ee2607b입니다. 먼저 git status, branch, HEAD, origin/main을 읽기 전용으로 확인하세요. 기존 변경은 모두 보존하고 reset --hard, clean, 자동 stash를 사용하지 마세요. 깨끗하고 fast-forward 가능한 경우에만 git pull --ff-only origin main을 실행하세요.

서비스명은 “AI-GO 무엇이든 물어보살”입니다. 상담원은 접수 선택→통화/원문→AI 정제 대조→사람 확인→부서 이관, 센터는 이관/물류 근거 확인→답변 제목·본문 생성 및 사람 편집→중간/최종 회신, 경영주는 새 문의 접수와 진행/회신 조회 흐름입니다. actual 실패를 replay 성공으로 바꾸지 말고, AI 초안을 자동 발송·저장하지 말며, 확인되지 않은 물류 사실을 확정 표현하지 마세요.

화면 작업은 OPENAI_API_KEY를 비운 replay 모드로 진행하세요. 최신 공유 원장은 29.95/30달러이고 AWS health는 29.50/30달러로 불일치하므로 실제 AI·STT·회신 호출과 원장 초기화는 금지합니다. .local, .env, AWS 자격, 키, 세션 JSONL은 읽거나 Git에 추가하지 마세요. 기본 공개 화면과 ONEFLOW_REQUIRE_LOGIN=1 선택 로그인 계약도 임의로 바꾸지 마세요.

사용자의 구체적인 화면 수정 요청을 현재 코드와 실제 로컬 화면에서 재현한 뒤, 필요한 범위만 구현하세요. apps/web/app/page.tsx, workflow-ux.css, CallReview, WmsScene, api.ts/types.ts와 서버 계약의 연결을 먼저 확인하세요. npm --prefix apps/web run typecheck, 관련 Python pytest, node tests/e2e/workflow-ux-check.mjs, production build를 실행하고 실제 브라우저에서 상담원·센터·경영주 및 1440/921/390 폭을 확인하세요. 검증 없이 완료라고 말하지 마세요.

끝에는 사용자에게 바뀐 동작, 수정 파일, 테스트 결과, 확인한 화면과 남은 제한을 한국어 존댓말로 간결히 보고하세요. AWS 재배포는 사용자가 명시적으로 요청한 경우에만 기존 happycall-oneflow-api의 코드만 갱신하고 환경변수·DynamoDB·기존 데이터·원장·게임 자원은 보존하세요.
```

사용자가 원하는 화면 수정 내용을 마지막에 한 문단으로 덧붙이면 됩니다. 예: `추가 요청: 상담원 접수표에서 긴 제목이 두 줄로 보이게 하고, 모바일에서 선택한 접수 작업 영역으로 자동 스크롤해 주세요.`
