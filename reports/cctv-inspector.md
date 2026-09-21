# CCTV 조사 화면 구현·격리 검증

2026-09-21 / pc1 CJJ / 메인 기준 de68b13에서 배정 시작. 제품 화면 통합은 메인 소유입니다. 이 보고서는 새 조사 컴포넌트의 격리 검증이며 전체 솔루션 완료를 뜻하지 않습니다.

## 결과

21:42 기준 격리 하네스 **64/64 PASS**, 당시 제품 소스 시작/종료 SHA 동일. 이후 독립검수의 P2 한 건을 수식 한 곳에서 수정했고 순수 단위 **14/14 PASS**, 수정 제거 변이 **1/1 검출**했습니다. 후속 수정의 브라우저 재검은 **NOT_RUN**이며 앞선 64/64를 새 코드의 브라우저 통과로 소급하지 않습니다. 기존 VideoDialog props 6개와 영상 aria-label/검증 문구를 유지하며 optional tracks descriptor만 추가했습니다. 검증된 영상의 구간 재생, 한 프레임 이동, 속도/반복, 시각 객체 선택, 원본/표시, 합성 표시를 포함한 전체 화면, 원본 스캔 비교, 오류별 복구를 구현했습니다.

새 파일은 `apps/web/components/CctvInspector.tsx`, `CctvInspector.module.css`, `apps/web/lib/cctv-tracks.ts`, `planning/cctv-inspector.md`, 이 보고서, `tests/e2e/cctv-inspector-harness.mjs`입니다. WmsScene/fixture/manifest/배포/기존 CSS는 수정하지 않았습니다. 커밋·메인 인수는 메인이 수행합니다.

## 재현·증거

```powershell
& 'C:/Users/choi8/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' tests/e2e/cctv-inspector-harness.mjs
& 'C:/Users/choi8/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' apps/web/node_modules/typescript/bin/tsc --noEmit --project apps/web/tsconfig.json
```

독립 하네스는 ephemeral localhost 포트를 열고 Playwright 1.58.2/로컬 Chromium으로 실제 새 컴포넌트를 번들링·실행합니다. 종료 시 자체 브라우저와 서버를 닫았습니다. 기존 8100/3100은 건드리지 않았습니다. 외부 호출·라이브 AI·유료 API 0회입니다. `CCTV_CHROMIUM`, `CCTV_OUTPUT`으로 환경을 지정할 수 있습니다.

최종 증거: `.local/cctv-inspector-1789994536355/results.json`, `source-harness.mjs`, `width-1440.png`, `width-768.png`, `width-390.png`, `fullscreen.png`, `bundle.js`, 코드 변이 사본. 하네스와 소스 SHA는 results에 기록했습니다. 최종 전체 TypeScript 검사 exit 0(컴포넌트 작성 뒤 및 경계 수정 뒤 수행).

| 검사 | 기대 / 실측 |
|---|---|
| 사건·이벤트·카메라·시각·영상 연결 | CASE/이벤트 E-W3 혼입/카메라/고정시각/영상 SHA/슈트 불일치 거부 |
| 프레임 구조 | 288개 연속 프레임, 유한 정규화 bbox/시간/phase 검증; NaN·역전·누락·외부 경로·업무 토트 값 거부 |
| 코드 변이 | case gate, phase order, bbox bounds, elapsed gate를 각각 제거하면 해당 음성 대조군이 잘못 통과함을 4/4 확인 |
| 바이트·해시 | 정상 확인, 길이 오류 거부, 같은 길이 SHA 오류 거부; 실제 브라우저 MP4 한 바이트 변조도 재생 차단 |
| 등록 구간 3–6초 | 실제 2× 재생→6초 정지, 반복 시 3초로 복귀, 구간 밖 seek 제한, ±프레임과 표시 일치 |
| 구간 끝 프레임 | 부분 구간 6초는 전체 자산의 145번째 프레임. 이전 144번째 프레임으로 오표시하지 않음 |
| 12초 전체 영상 | native rVFC 존재 확인 후 **1× 자연 재생·trusted ended 1회·played 0–12초** 실측. 합성 이벤트를 dispatch하지 않음 |
| 좌표 없음 / 실패 | 검증 영상 유지, 프레임 단위 이동과 bbox 비활성화; 좌표 명시 재시도로 복구 |
| 영상 404 | 재생 차단 후 사용자 재시도로 복구. 다른 영상으로 대체하지 않음 |
| 접근성 | Escape 닫기·opener 복귀, Tab/Shift+Tab 순환, 전체 화면에서 초점/합성 표시 유지, reduced motion 자동 재생 없음 |
| rVFC 미지원 | API를 제거한 별도 하네스 페이지에서 RAF fallback이 실제 currentTime으로 진행 |
| 반응형 | 1440: dialog 1318/1318, 768: 734/734, 390: 356/356(client/scroll). 세 폭 모두 문서 가로 넘침 0 |

## 발견·수정·재검증 이력

- 초기 하네스의 HTTP UTF-8 charset 누락으로 JS 문자열만 깨지고 버튼 선택이 실패했습니다. 제품 파일은 UTF-8이었으며 하네스 응답/HTML charset을 수정했습니다. 실패 DOM/스크린샷 `.local/cctv-inspector-1789994028279/` 보존.
- 실제 rVFC 종료 경계에서 `currentTime=5.96`으로 정지하고 종료 표시가 되감기는 결함을 확인했습니다. 등록 끝으로 seek를 고정하고 pre-seek 예약 프레임이 정지 화면의 새 시간을 덮지 않도록 수정했습니다. 실패 `.local/cctv-inspector-1789994093355/`, 수정 후 43/43 `.local/cctv-inspector-1789994159680/`.
- 확대 하네스에서 작은 불량 JSON이 영상 SHA 검사보다 먼저 끝나는 경합을 발견했습니다. 영상 검증 완료를 기다리는 검사로 고쳤으며 이를 제품 오류로 세지 않았습니다. 실패 `.local/cctv-inspector-1789994255504/` 보존.
- 자체 경계 검토에서 부분 구간 끝에 이전 bbox 프레임을 고르는 문제를 수정했고 60/60, 원본 후보·토큰 검사 추가 63/63, native rVFC 전체 재생 추가 **64/64**로 재검증했습니다. 이전 결과를 삭제하거나 덮어쓰지 않았습니다.

## 실제 장면 정합·디자인 게이트 한계

현재 승인 MP4는 960×540, 실제 PC3 후보 tracks는 1280×720·24fps·288프레임입니다. 후보 JSON SHA `9fb424be0fd212bbf3faa057097bec56c63a89e4b8ae08c524e5fd76b80fd44b`의 구조는 별도 검사에 통과했으나, 승인 MP4와 결합하면 해상도 검증에서 **거부**됩니다. 브라우저 양성 대조군의 `SYN-UI-TEST-ONLY` 좌표는 임의로 생성한 UI 테스트 좌표입니다. 실제 영상 픽셀·3D 경계·물체 이동·가림 정합, 실제 업무 토트 동일성, AI 검출 성능을 증명하지 않습니다. 최종 PC3 영상/좌표 쌍을 수신한 뒤 메인이 별도로 대조해야 합니다.

디자인브리프에 따라 정본 primitive/semantic/scale/biz, DESIGN_SYSTEM §11, 기존 tokens.css를 읽었습니다. 이번 CSS **1파일·토큰 참조 49종·미정의 0·hex 0**을 직접 확인했고 새 색/폰트 팔레트는 추가하지 않았습니다. 3폭/fullscreen 스크린샷을 직접 열어 확인했습니다.

공유 `01_토큰/check.mjs`는 실행했지만 **PASS가 아닙니다**: CSS 46파일/hex272, JS·HTML230파일/hex3119, E601 기존 기준3029 대비 증가. 실제 process exit1이며 출력 안내의 exit2와 차이도 보존합니다. 검사기 고정 소비 경로는 50/91 등으로 이번 happycall 파일을 스캔하지 않습니다. 다른 프로젝트 코드를 수정하거나 기준선을 올리지 않았으며, 이 공통 게이트 결과를 이번 컴포넌트 PASS로 바꾸지 않았습니다.

미실행: 15초 timeout 실제 지연, 브라우저 권한으로 fullscreen 거부되는 환경, Safari/Firefox/모바일 OS, 실제 사람 사용성/청취/가림 검사. 메인 통합 후 기존 WMS 이벤트 연결·전체 6흐름·새 최종 자산 정합 검사가 필요합니다.

## 독립 P2 후속 수정 — 전체 자산 끝에서 이전 프레임

독립검수에서 12초/24fps/288프레임 전체 영상의 끝에 있는 상태로 이전 프레임을 누르면 **표시 288→288**로 남는 결함을 확인했습니다. `floor(12×24)=288`은 유효 인덱스 최대287을 넘으므로, 방향 -1을 적용하기 **전에** 현재 인덱스를 최대287로 제한했습니다. 수정 범위는 실제 step 함수의 현재 index 수식 한 곳입니다. 부분 구간 끝 6초의 **145→144**는 유지했습니다.

실제 제품 소스에서 TypeScript AST로 step/seek 선언을 추출하고 transpile한 함수를 최소 player 상태에 실행했습니다. 별도 복사한 계산식으로 제품을 대신하지 않았습니다. full end·partial end·clip start·non-frame boundary의 양방향, tracks 없음/player 없음 무동작을 포함합니다.

```powershell
& 'C:/Users/choi8/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' tests/e2e/cctv-inspector-step-unit.mjs
```

- 수정 전 `.local/cctv-step-unit-1789994738132/`: **13/14**, 전체 끝 이전 프레임만 실패(실제288/기대287).
- 수정 후 `.local/cctv-step-unit-1789994749488/`: **14/14**, 전체 끝 이전은 11.9166667초/287프레임, 부분 끝 이전은 5.9583333초/144프레임.
- 수정 수식 제거 변이: 다시 11.9583333초/288프레임으로 남아 음성 대조군이 검출, **1/1**.
- pure harness node --check와 전체 tsc --noEmit exit0. 서버 시작0·브라우저 시작0·네트워크 호출0.
- 새 코드의 브라우저 재실행 분모 **0/1 NOT_RUN**. 기존 64/64 결과·스크린샷·하네스 사본은 변경하지 않았습니다.

메인이 전달한 자동 승인 검토 결과로 독립검수의 `http.listen(0) + chromium.launch` 실행이 **blocked by policy**로 거부되었으며 세부 이유는 제공되지 않았습니다. 이 후속에서는 다른 에이전트·방법으로 서버/브라우저 실행을 우회하지 않고 순수 함수 검사만 수행했습니다. 해당 시점 RAM 보고는 1.76GiB였습니다.
