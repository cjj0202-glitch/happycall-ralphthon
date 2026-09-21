# CallReview 원문 대조 배치 v2

2026-09-21 23:32 KST · pc1/CJJ · 구현 전 설계를 먼저 기록한 뒤 실행 결과를 추가했습니다.

목표는 원문 확인을 위해 접기를 열어야 하는 단계를 없애고, 실제/저장 대화록과 상담 입력을 같은 작업면에서 대조하는 것입니다. 사람 사용성 검증이나 화면 높이 개선 실측은 아직 수행하지 않았습니다.

## 배치 설계

- 기존: 사건 제목을 재표시하는 큰 헤더 → 재생 영역/편집폼 → 기본 접힌 원문 → 별도 원대본/대화록 순서.
- 변경: 간결한 작업 헤더 → 재생 영역/편집폼과 기본 펼친 원문. 음성은 화자별 대화록을 먼저 두고 합성 음성 제작 원대본은 그 아래 명시적인 접기로 구분합니다. 웹 입력은 접수 원문을 바로 표시합니다.
- 실제 컴포넌트 컨테이너 720px 이상에서 왼쪽 재생·원문 / 오른쪽 편집으로 전환합니다. 그 미만에서는 DOM과 시각 순서를 모두 재생 → 원문 → 편집으로 두어 원문 확인 후 편집에 진입하도록 했습니다. viewport 기준의 기존 2열 전환은 제거합니다. 첫 구현의 900px 컨테이너 기준은 일반 노트북에서 대부분 1열이 된다는 메인 실측·지시에 따라 720px로 조정했습니다. 이 문서는 720px 배치의 렌더 실측 통과를 주장하지 않습니다.
- 긴 대화록은 포커스 가능한 이름 있는 스크롤 영역에 전체 발화를 유지합니다. 잘라내기·발화 개수 제한은 하지 않습니다. 구간 재생 버튼·자막 표시 제어를 그대로 둡니다.
- 분석 오류/재시도와 음성 출처/전체 재생 조건은 노출합니다. 부수 재생 설명만 명시적 접기로 보관합니다. AI 상세 비교 5행과 추가 질문은 편집폼 뒤의 기존 접기를 유지합니다.

## 보존 경계

소유는 `apps/web/components/CallReview.tsx`, `CallReview.module.css`, 이 보고서입니다. 메인은 `page.tsx`, `globals.css`, 업무 흐름 설계를 별도로 편집합니다. 서버·fixture·음원·기존 보고서는 수정하지 않습니다.

`CallReview → ReviewSession` sourceKey, audio attempt key, refs/state/effects, 전체 재생 완료 gate, 모든 audio event handler, 구간 경계/숨김 탭 처리, 음원 오류·재시도, 분석/편집 슬롯을 보존합니다. 새 탭·새 API·새 DOM 분기용 state를 만들거나 기존 세션을 언마운트하지 않습니다. 기본 open은 details의 표시 속성만 변경합니다.

디자인 브리프는 기존 CRUD Split-Pane 워크벤치와 `apps/web/app/tokens.css`의 surface/border/text/action/focus/status·간격·폰트·컨트롤 토큰을 사용합니다. 새 팔레트·폰트·라이브러리는 추가하지 않습니다. 규칙은 `.claude/rules/dashboard-ui.md`, 공용 디자인 시스템 §11과 로컬 업무흐름 설계를 대조했습니다.

## 검증 계획

타입검사와 기존 무과금 코드 검사, 변경 전후 key/state/핸들러 정적 대조를 실행합니다. 새 브라우저·서버·유료 API·키·실저장·커밋은 사용하지 않습니다. 화면 3폭·앵커 이동·원문 초기 표시·키보드 스크롤·음원 연속성은 메인이 기존 IAB에서 별도 확인합니다. 렌더 PID 13052는 조작하지 않습니다.

## 구현과 실행 결과

- `sourcePane` 외곽 details는 기본 `open`입니다. 음성의 화자별 대화록을 먼저 렌더하고 제작 원대본은 별도 details로 보존합니다. 웹 원문은 별도 내부 접기 없이 즉시 렌더합니다.
- 대화록과 긴 원문은 전체 내용을 `role="region"`, `tabIndex={0}`, 제목과 연결된 `aria-labelledby`를 갖춘 스크롤 영역에 담았습니다. 높이는 기존 `--control-xl` 토큰의 8배 상한이고 모든 발화와 구간 버튼을 유지합니다. 실제 키보드 스크롤 동작은 메인 렌더 검증 대상입니다.
- 출처·전체 재생 조건·음원 오류·볼륨 경고·분석 실패/재시도는 노출합니다. 탭을 숨겼을 때의 구간 동작 설명만 접기에 넣었습니다. 헤더에서 사건 제목과 ID를 다시 반복하는 부분을 줄였습니다.
- source 내부 제목/자막 라벨과 발화 헤더는 줄바꿈을 허용했습니다. 카드 간격·폰트·색·포커스는 기존 토큰을 사용합니다.

| 검사 | 실측 | 범위 |
|---|---|---|
| `npm run typecheck -- --incremental false` | exit 0 | `apps/web`의 실제 TypeScript 검사, 캐시 출력 억제 |
| 변경 전 HEAD와 key/state/effects/함수/audio JSX 정적 대조 | 보존 확인 | sourceKey·재생 gate·구간 helper·상태·effect·모든 audio props/handler·5필드 상세 대조 원문 동일 |
| 실제 React SSR + 위 정적 대조 통합 | 33/33 | 두 합성 fixture 및 메모리의 웹입력 1건. 원문 open, 순서, 전체 원문/발화, 전체 구간 버튼, 5행 비교, audio 수, 키보드 진입 속성, 컨테이너 규칙 |
| `git diff --check -- apps/web/components/CallReview.tsx apps/web/components/CallReview.module.css` | exit 0 | 줄끝 변환 안내만 있음 |
| `node tests/e2e/role-workflow-unit.mjs` | 실패 | 60행 `actual primary navigation has only three role tabs`; 동시 변경 중인 page.tsx의 nav 자식 배열 형태를 검사기가 고정 가정. 메인이 자기 소유 범위에서 수정 중임을 회신 |

정적 대조 첫 실행은 CRLF/LF 차이 때문에 `valueText unchanged`에서 실패했습니다. 실제 함수 변경은 없었고 줄끝만 정규화해 재실행한 14/14 대조와 최종 33/33 통합 검사가 통과했습니다. 실패한 기존 nav 검사는 이 작업에서 통과 처리하거나 수정하지 않았습니다.

SSR는 설치된 TypeScript로 해당 컴포넌트를 메모리에서 CommonJS로 변환하고 실제 React `renderToStaticMarkup`을 호출했습니다. CSS 모듈 이름만 사전 주입했고 API·브라우저·서버·소켓을 사용하지 않았습니다. 원문에 모든 발화가 포함되어 있는지, 구간 버튼 수가 제공된 발화 수와 같은지, 편집폼 뒤의 AI 상세 비교가 5행인지 확인했습니다. DOM 속성 및 코드 보존을 확인한 것으로 실제 음성 연속 재생·픽셀 배치·사람 사용성 성공을 대신하지 않습니다.

## 동결 및 메인 확인 항목

23:32 KST 기준 소유 파일 구현을 동결합니다. source/편집 앵커, 원문 기본 표시, 가로 넘침, 스크롤·키보드, 컨테이너 실제 폭, 기존 audio 노드 연속성은 메인이 기존 IAB에서 3폭으로 확인합니다. 새 서버·브라우저·유료 API·키·실저장·커밋 호출 0건이며 렌더 PID 13052를 조작하지 않았습니다.

- `CallReview.tsx` SHA-256: `f5df2066049a5bd05b264c38e6847c5e06ab82f3f65c836826a08501cf6a3f2d`
- `CallReview.module.css` SHA-256: `99e05ba3a7c4b2f53feda75cfd4016d5d7b77504ecf8d16f54bad09fb0bae05d`
