# N03-D1 · Vercel 사전 확인 및 중단 인계

**배포하지 않았다.** PC1이 2026-09-22 07:54 KST에 대상을 개인 AWS로 바꾸며 Vercel 작업 중단을 지시했다. 확인한 기존 설정과 로컬 준비를 보존한다. AWS 작업은 메인이 담당하며 PC3에 새 실행 카드는 배정되지 않았다.

- 요청: [N03-D1](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/9#issuecomment-5768611225)
- 설정 실측 회신: [#9 설정 유무](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/9#issuecomment-5768643119)
- 중단 지시: [개인 AWS로 대상 변경](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/9#issuecomment-5768638034)
- 실행 신원: `pc3/logistics-review · LAPTOP-U2AL73UH · mcjun86-oss`
- 준비 대상 소스: `ceaf9ffe0ed7907edb051255575bb0b86d5ad943`
- 원래 브랜치/시작 HEAD: `work/pc3-n03-wms-scenes` / `d0b75de336259487b71e5285f0b6713f0eb40e87`

## 기존 접근과 설정 실측

기존 Codex 내장 브라우저 로그인 계정 `hackathon02-1948`로 `52g Studio` (`52g-studio`) / `g-28`에 접근했다. 확인 대상은 [프로젝트 Overview](https://vercel.com/52g-studio/g-28), Storage, 환경변수 Project/Shared 목록뿐이다. 비밀값을 펼치거나 인증 파일을 읽지 않았다.

Project 목록을 검색 공란, All Types / All Environments / All Variables 조건으로 확인했다.

| 변수 이름 | 화면에서 확인한 설정 범위 |
|---|---|
| ONEFLOW_STORAGE_BACKEND | Preview |
| ONEFLOW_ACCESS_USER | Preview |
| ONEFLOW_ACCESS_PASSWORD | Preview |
| OPENAI_API_KEY | 목록에 없음 |
| ONEFLOW_RUNTIME_MODE | 목록에 없음 |
| BLOB_READ_WRITE_TOKEN | 목록에 없음 |
| ONEFLOW_BLOB_STORE_ID | 목록에 없음 |
| ONEFLOW_BUDGET_INITIAL_RESERVED_CENTS | 목록에 없음 |
| OPENAI_DEMO_BUDGET_USD | 목록에 없음 |
| OPENAI_DEMO_WARN_USD | 목록에 없음 |
| OPENAI_DEMO_PURPOSE | 목록에 없음 |

- Shared 탭: `No shared variables linked`.
- g-28 Storage: 검색 공란/All에서 `No Results Found`. 연결된 저장소 표시 없음. Connect/Create는 실행하지 않았다. 팀 전체의 private store 존재 여부나 연결 권한까지 판정한 것은 아니다.
- 존재하는 변수도 값의 유효성은 미검증이다. 현재 목록으로 실제 AI/영속 저장/Production 접근 보호가 준비됐다고 주장할 수 없다.
- 현재 PATH와 기존 D: npm 경로에서 **Vercel CLI 런처**를 확인하지 못했고, 알려진 저장소·배포 디렉터리의 `.vercel/project.json`도 확인되지 않았다. 일반 npm 런처는 기존 D: 경로에 있다. Vercel CLI 로그인·CLI 인증·CLI 배포 가능은 미확인이다. 새 CLI 설치/로그인을 시작하지 않았다.
- 기존 `g-28.vercel.app` 및 Preview가 Overview에 표시됐으나 이번 고정 소스를 배포한 URL이 아니다. 업무 API 저장·재조회·실제 503·AI 응답은 이번 작업에서 실행하지 않았다.

## 보존한 로컬 준비

지정 SHA만 fetch했고 다음 detached worktree를 생성했다.

```text
D:\hwana\Work\happycall-ralphthon\.local\pc3-d1-ceaf9ff\source
HEAD ceaf9ffe0ed7907edb051255575bb0b86d5ad943 (detached)
```

고정 소스의 배포 패키저와 가드 문서를 읽고, 기존 PC3 의존성과 package.json/package-lock.json 일치를 확인했다. 격리 worktree의 `apps/web/node_modules`에 기존 PC3 node_modules를 가리키는 junction만 준비했다. 원래 checkout/브랜치/미커밋 작업/기존 watcher를 바꾸지 않았다.

중단 시점에 실행 중인 빌드 명령은 없었다. 미디어 복사, `build_deployment_bundle.py --build`, 번들 생성은 **시작 전**이므로 PC3 build stamp/출력 fingerprint/새 bundle/배포 URL은 없다. PC1이 회신한 생산 빌드·payload/export/미디어 검사 수를 PC3 실적으로 옮기지 않는다. 이전 N03-R1 미디어 4/4 검증은 별도 보고서의 고정 기준에 한정된다.

중단 직후 원래 checkout과 격리 worktree 모두 clean이었다. 격리 `.oneflow-build.json`과 `dist/deployment`는 없었다. 로컬 중단 증거 `.local/pc3-d1-ceaf9ff/stopped-preparation.json`은 4,292 bytes, SHA-256 `dadc1e8b693165b2c739c3d4619814c0beec66383864e2580922b11e555ffc97`이다.

## 외부 변경과 남은 경계

- Vercel 배포·재배포·Production 승격·롤백: 0.
- Vercel 환경설정·Storage 연결/생성·접근 보호 변경: 0.
- CLI 로그인·새 계정/권한/토큰/결제: 0.
- 실제 AI 호출·새 렌더·음원 생성·예산/기존 원장 초기화: 0.
- 기존 Blob403 경로를 다른 도구/계정으로 우회하지 않았다.
- 원래 checkout의 제품 소스/중앙 작업표는 수정하지 않는다. 이번 Git 변경은 이 보고서 한 파일이다. 원본 바이너리·로컬 상태·키·원장은 Git/이슈에 올리지 않는다.
- 현재 대화의 heartbeat는 Vercel 배포를 금지하고 있었다. 로컬 준비와 읽기 전용 확인까지만 진행했으며, 충돌한 배포 지시는 실제 실행 전에 후속 중단됐다. 배포 승인 질문이나 권한 확대를 우회하지 않았다.

로컬 처리 기록은 `.local/pc3-dispatch.json`의 `minimal_vercel_deployment`에 남기며, 설정 확인용 임시 탭은 닫았다. 위 worktree와 이전 R1 합성 상태/증거는 보존한다. 동일 준비·회신을 반복하지 않고 PC1의 새 피드백을 기다린다. TEST, 공식 로그 제출/HowLong, N03 전체 인수는 별도 미완료다.
