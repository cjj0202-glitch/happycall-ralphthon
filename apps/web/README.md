# HappyCall OneFlow 웹

T1 신규 독립 앱. Next.js 15 App Router, React 19, TypeScript strict, `output: export`를 사용합니다. 백엔드는 별도의 로컬 API이며 기본 주소는 `http://127.0.0.1:8100`입니다. 환경 변수 `NEXT_PUBLIC_API_BASE`로 변경할 수 있습니다.

```powershell
cd C:/00.프로젝트/happycall-ralphthon/apps/web
npm.cmd ci
npm.cmd run dev
```

개발 화면은 `http://127.0.0.1:3100`입니다. `npm.cmd run build`는 `out/`에 정적 결과를 생성합니다. 개발 산출물은 `.next-dev/`, 빌드는 `.next/`로 분리합니다.

## 시연 흐름

1. 문의를 선택하고 사전에 생성한 합성 통화를 재생합니다.
2. 기본값인 저장 결과 재생은 AI API를 호출하지 않습니다. 실제 AI 분석을 선택한 경우 통화 재생이 끝난 뒤 버튼으로 전사·정제를 실행합니다.
3. 원문과 AI 제안을 대조하고 접수 정보를 편집합니다. 점포·상품·부서를 선택하고 확인 체크를 해야 센터로 전달할 수 있습니다. 미확인 수량은 비워 둘 수 있습니다.
4. WMS/TMS에서 합성 물류 근거를 확인하고 이관 전에 접수 건에 연결합니다.
5. 센터에서 회신을 편집하고 등록합니다. 남은 조치가 있으면 중간 회신을 등록하며 처리 중 상태를 유지합니다.
6. 경영주 화면에는 등록된 센터 회신만 보입니다.

서버 오류는 오류 문구와 재시도로 표시합니다. 연결 실패 후 사용자가 선택하는 합성 예시 열람은 읽기 전용입니다. 이 예시를 실제 저장 성공으로 표시하지 않습니다.

## 디자인 브리프

CRUD 워크벤치 패턴을 사용합니다. 상단 접수 선택 뒤 원문과 접수 편집 폼을 나란히 배치하고, 상단 메뉴로 경영주·센터·물류 화면을 전환합니다. 768px 이하에서는 한 열로 배치합니다.

색과 크기 값은 공통 디자인 토큰의 semantic/scale 원천에서 생성한 `app/tokens.css`에 있습니다. `scripts/generate-tokens.mjs`는 로컬 정본에서 112개 변수를 재생성합니다. 화면 CSS는 토큰 변수를 참조합니다. 명도 대비를 위해 기본 버튼은 `action.text` 배경과 `text.on-fill` 글자를 사용합니다.

## 검증

`npm.cmd run typecheck`, `npm.cmd run build`, `npm.cmd audit --omit=dev`로 검사합니다. `scripts/check-layout.mjs`는 별도 `tests/e2e`의 Playwright 설치를 사용하며, 1440·921·390px의 5개 탭을 검사하고 `.checks/`에 증거를 저장합니다. 이는 AI 자동 검증이며 실제 사용자 테스트가 아닙니다.
