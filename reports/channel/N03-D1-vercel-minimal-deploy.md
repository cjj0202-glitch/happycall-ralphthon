# N03-D1 — 기존 Vercel 세션으로 최소 배포 연결

2026-09-22 07:51 KST, pc1 최제준/cjj0202-glitch → pc3 LAPTOP-U2AL73UH/mcjun86-oss.

07:50의 기존 hackathon02-1948 /52g Studio/g-28 브라우저 접근 보고를 확인했습니다. 사용자 최신 목표는09:00까지 최소 기능 서버 배포·API 연결·빠른 저가형 AI 응답입니다. 기존 승인된 프로젝트 접근으로 아래 작업을 진행합니다. 비밀을 pc1이나 GitHub로 전달할 필요가 없습니다.

## 즉시 병렬 준비

1. 최신 main 고정 `ceaf9ffe0ed7907edb051255575bb0b86d5ad943`를 fetch하고 기존 작업·미커밋·프로세스를 보존한 별도 worktree/checkout으로 준비합니다. root는 해당 소스에서 생산 빌드·묶음 생성에 성공했습니다. 원 미디어v4를 재사용하며 새 렌더/음원 생성은 하지 않습니다.
2. 현재 g-28의 Storage 연결 상태와 환경변수 **이름/설정 유무만** 확인해 즉시 회신합니다. 최소 항목은 `OPENAI_API_KEY`, `ONEFLOW_RUNTIME_MODE`, 기존 접근 인증2개, `ONEFLOW_STORAGE_BACKEND`, `BLOB_READ_WRITE_TOKEN`, `ONEFLOW_BLOB_STORE_ID`, `ONEFLOW_BUDGET_INITIAL_RESERVED_CENTS`, 기존 AI예산 정책3개입니다. 값·키·비밀번호를 보고서/이슈/출력에 싣지 않습니다.
3. 기존 계정에서 CLI 정규 로그인이 가능하면 공식 Vercel CLI59.23.2와 기존 브라우저 인증 흐름을 사용할 수 있습니다. 새 계정/권한 확대/새 토큰 수동 생성/다른팀 우회는 하지 않습니다. CLI가 불가능하면 관리 화면의 기존 파일/폴더 배포 경로를 확인합니다.

## 배포 고정과 검증

원본 소스는 위 SHA이며 메인 결과는 서버286PASS/250subtests, PC2 원20/20·기존15/15·31/31·추가18/18·3/3, UI131/131·87/87·타입검사 통과입니다. 기존 `scripts/build_deployment_bundle.py --build` 후 같은 스크립트로 비밀없는 묶음을 만드십시오. 이 묶음만 기존 `prj_VUk0C5e3thVOU9GgT8pc9tAoCczs` /scope `52g-studio`에 배포합니다. 기존 접근 보호를 유지합니다. 로컬 .env/.local/키/원장은 업로드하지 않습니다.

현재 메인 묶음은 `dist/deployment/20260921T224935939491Z-ceaf9ffe0ed7`이며 독립 바이트 검수 중입니다. PC3의 별도 빌드는 출력 fingerprint가 다를 수 있으니 본인의 build stamp·소스SHA·미디어4/4를 확인하고 기존프로젝트에 먼저 Preview로 배포해 API/저장을 검증합니다. Production 승격은 같은 프로젝트의 업무 API 저장·재조회가 성공한 고정 배포로 한정합니다. 기존 API키가 없거나 저장소가 없으면 503/미연결로 즉시 보고하며 성공으로 처리하지 않습니다.

## 경계와 후속

기존 Blob403은 다른 도구/계정으로 우회하지 않습니다. 연결 가능한 이미 승인된 private store가 없으면 설정 화면과 정확한 차단만 보고합니다. 메인은 원장을 초기화하지 않는 create-if-absent bootstrap을 준비 중입니다. 기존 관측2920센트/30달러 상한이며 이관·잔여한도 확인 전 유료 호출은0입니다. 텍스트 gpt-4.1-mini 유지, 음성 모델 교체/새 알림 구현은 하지 않습니다. 실제 최소AI1회는 메인과 중복되지 않게 후속 명시합니다.

결과 파일은 `reports/pc3/minimal-vercel-deployment.md` 하나, 제품 수정이 필요하면 먼저 결함을 회신합니다. 보고할 때 계정/프로젝트·소스SHA·실제URL·API/저장 결과·남은 차단만 간결히 구분합니다. 환경설정과 배포 변경은 비밀값 없이 기록하고09:00에 결과를 인계합니다.
