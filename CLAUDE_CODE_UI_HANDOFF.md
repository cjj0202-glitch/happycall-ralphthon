# Claude Code 화면 작업 인수인계 — AI-GO

작성 기준: 2026-09-22. 이 문서는 Claude Code가 최신 AI-GO 화면 작업을 이어가기 위한 공개 저장소용 인계입니다. API 키·AWS 자격·로그인 비밀·비공개 원장은 포함하지 않습니다.

## 현재 기준

- 저장소: `cjj0202-glitch/happycall-ralphthon`, 브랜치 `main`.
- 화면 제품 기준: `2e5454217707a956e8173a376f65ff949ee2607b`.
- 서비스 표시 이름: **AI-GO 무엇이든 물어보살**.
- AWS: 개인 계정 `704995468470`, 서울 `ap-northeast-2`, Lambda `happycall-oneflow-api`, DynamoDB `happycall-oneflow-state`.
- 실제 배포: Lambda published version `5`, `$LATEST` Active/Successful. Function URL은 [AI-GO](https://yrvhgwajh4zcfalqsdidrnm32a0oeltw.lambda-url.ap-northeast-2.on.aws/)입니다.
- 배포와 기능 검증 상세: [AWS version 5 보고](reports/deployment/aws-aigo-v5-deployment-20260922.md).

작업 시작 전 전역 규칙, 저장소 `AGENTS.md`, 루트 `CLAUDE.md`, 수정 대상에 더 가까운 `CLAUDE.md`를 먼저 읽습니다. 기존 변경이 있으면 보존하고 `reset --hard`, `clean`, 자동 stash로 덮지 않습니다. 깨끗하고 fast-forward 가능한 경우에만 `git pull --ff-only origin main`을 사용합니다.

## 현재 화면과 업무 흐름

상단 역할 전환은 상담원, 센터, 경영주 세 화면입니다. 기본 분석 방식은 `저장 결과 재생 · API 호출 없음`입니다.

1. 상담원은 접수표에서 사례를 선택하고 통화·원문을 확인합니다. AI 정제 결과의 점포·상품·수량·단위·요청사항을 대조하고 사람 확인 후 담당 부서에 이관합니다.
2. 센터는 이관 내용과 WMS/TMS 근거를 확인합니다. AI 답변 초안은 자동 발송·저장되지 않으며 담당자가 제목과 본문을 적용·편집한 뒤 중간 또는 최종 회신을 등록합니다.
3. 경영주는 새 텍스트 문의를 접수하거나 기존 접수의 진행 상태와 센터 회신을 조회합니다.

현재 AWS에는 사례 4건이 있습니다. 합성 음성 사례는 `CASE-0001` 미도착과 `CASE-0002` 오출고입니다. `INT-53E58A50`은 revision 5 종결 데이터이며 보존해야 합니다. `INT-36C35094`는 웹 접수 사례입니다. 화면 수정을 위해 기존 상태를 재초기화하거나 bootstrap으로 덮지 않습니다.

실제 브라우저에서 다음을 확인했습니다.

- 상담원: 대기 2건, CASE-0001 원문·AI 정제·대조·이관 UI.
- 센터: 새 이관 1건, CASE-0002 이관 내용·WMS/TMS·회신 UI.
- 경영주: 신규 문의 폼, 접수 4건 선택, CASE-0001 진행 상태.
- 1440/921/390 폭의 이전 격리 검증에서 가로 넘침이 없었습니다. 새 수정 뒤에는 다시 확인해야 합니다.

## 화면 수정 주요 파일

| 경로 | 역할 |
|---|---|
| `apps/web/app/page.tsx` | 역할별 화면, 접수표, 업무 단계, 상태 전환의 중심 |
| `apps/web/app/workflow-ux.css` | 상담원·센터 단계 안내와 새 업무 UI 스타일 |
| `apps/web/app/globals.css` | 전역 토큰·레이아웃·반응형 기본 스타일 |
| `apps/web/components/CallReview.tsx` | 통화·대화록·재생·AI 정제 검토 |
| `apps/web/components/CallReview.module.css` | 통화 검토 컴포넌트 스타일 |
| `apps/web/components/WmsScene.tsx` | WMS 근거와 등록 영상 |
| `apps/web/components/WmsScene.module.css` | WMS 화면 스타일 |
| `apps/web/lib/api.ts` | 화면 API 호출과 응답 처리 |
| `apps/web/lib/types.ts` | 프런트 타입 계약 |
| `server/openapi.yaml` | 서버 API 공개 계약 |
| `server/service.py`, `server/handlers.py` | 저장 상태와 역할별 동작 |
| `server/live.py` | 실제 AI 분석·회신 지시. UI 작업만 할 때 호출하지 않음 |

화면 문구나 필드를 바꿀 때 API 필드·저장 상태·role guard와 어긋나지 않는지 확인합니다. `actual` 실패를 replay 성공으로 바꾸거나, 생성된 초안을 자동 발송·자동 저장하거나, 확인하지 않은 물류 사실을 확정 표현하지 않습니다.

## 안전한 로컬 실행

UI 수정은 replay 모드로 시작합니다. 기존 `.local/main-resume-20260922/replay-state`가 있으면 보존하고 별도 상태가 필요하면 새 명시 경로를 사용합니다. API 키 없이도 화면 작업이 가능합니다.

```powershell
$env:PYTHONUTF8='1'
$env:ONEFLOW_RUNTIME_MODE='replay'
$env:OPENAI_API_KEY=''
python scripts/start_demo.py
```

기본 주소는 화면 `http://127.0.0.1:3100/`, API health `http://127.0.0.1:8100/api/health`입니다. 포트가 이미 사용 중이면 기존 프로세스를 임의 종료하지 말고 소유자를 확인합니다. 개발 `.next-dev`와 production `.next`를 혼동하지 않습니다.

## 최소 검증 게이트

수정 범위에 맞춰 실행하되, 화면 변경에는 최소한 다음을 적용합니다.

```powershell
npm --prefix apps/web run typecheck
node tests/e2e/workflow-ux-check.mjs
python -m pytest -q tests/test_deployment_app.py tests/test_reply_draft.py
python scripts/build_deployment_bundle.py --build
```

실제 브라우저에서 상담원·센터·경영주 역할 전환, 1440/921/390 폭, 키보드 접근, 접수 선택 후 작업 영역, 긴 제목·본문·빈 상태를 확인합니다. UI만 수정했더라도 production export가 성공하고 소스 지문이 빌드 전후 일치해야 합니다. 서버 계약을 바꾸면 관련 pytest와 `tests/test_deployment_bundle.py`, `tests/test_dynamodb_store.py`도 실행합니다.

현재 기준 검증은 TypeScript 통과, 관련 Python **296 passed**, AWS HTTPS 12/12, 실제 세 역할 렌더링 정상입니다. 기존 deprecation warning 5는 실패로 세지 않았습니다.

## 반드시 보존할 제한

- 최신 공유 원장은 **29.95/30달러**, AWS `/api/health`는 **29.50/30달러**로 45센트 불일치합니다. 보수적으로 29.95를 기준으로 삼고 실제 AI·STT·회신 호출을 추가하지 않습니다. 두 원장을 합치거나 0으로 초기화하지 않습니다.
- 두 실제 AI 회신은 기록을 실제 정상 출고·인도로 과대확정한 문제가 있었습니다. 지시문은 보강했지만 실제 모델 재검증은 하지 않았습니다.
- 실제 Teams·카카오 알림은 연결되지 않았습니다. UI에서 연결 완료로 표시하지 않습니다.
- 공식 CLOVA 음원·사람 사용성·실제 고객/통화/물류·운영용 사용자 인증·공식 제출은 완료가 아닙니다.
- 최신 변경은 기본 공개 화면이고 `ONEFLOW_REQUIRE_LOGIN=1`일 때만 로그인 보호를 켭니다. 인증 정책을 화면 수정 과정에서 임의로 바꾸지 않습니다.
- `.local`, `.env*`, AWS 자격, OpenAI 키, 원본 세션 JSONL을 Git에 추가하지 않습니다.

## 완료 보고 형식

작업을 마치면 변경한 사용자 동작, 수정 파일, 실행한 테스트와 결과, 확인한 화면 폭·역할, 남은 결함을 기록합니다. AWS 배포는 사용자가 별도로 요청한 경우에만 기존 함수의 코드만 갱신하며, 환경변수·DynamoDB·원장·게임 자원은 보존합니다.
