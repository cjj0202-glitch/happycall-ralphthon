# 통화 재생 속도 선호 유지 구현·오프라인 검증

2026-09-22 03:35 KST · CJJ / pc1 로컬 구현 보조 · 배정 기준 `3b67bf4ec2ba1041d1861ec8e2909f466416953d`

기본 통화 속도를 1.25배로 바꾸고 Home에서 선호를 보유하도록 수정했습니다. 접수·WMS/TMS·센터·경영주 화면 이동과 음원 재시작 후에도 선택값이 유지됩니다. 실제 TSX 오프라인 검사 21/21, 변이 7/7 검출, 기존 영향 검사 224/224 및 타입검사가 통과했습니다. 이 보고는 브라우저 배속·음성 명료도·실제 저장/이관 통합 검증을 완료했다는 뜻이 아닙니다.

## 구현과 소유

- `apps/web/app/page.tsx`: Home의 `playbackRate` 기본값 1.25, Desk를 거쳐 CallReview에 값·콜백 전달.
- `apps/web/components/CallReview.tsx`: select 이벤트에서 부모 상태를 즉시 갱신. `ratechange`도 같은 경로로 정합성을 유지합니다. finite 0.75~2 범위의 native 값은 허용하고 NaN/0/Infinity/범위 밖 값은 직전 유효값으로 복구합니다. 표준 옵션은 기존 0.75/1/1.25/1.5/2이며 native 1.1 같은 중간 값도 표시합니다. `preservesPitch=true`를 새 오디오와 metadata 경로에 명시합니다.
- `tests/e2e/call-playback-preference-unit.mjs`: 실제 Home·Desk·CallReview를 컴파일해 훅 상태, key 재생성, 효과 정리, 실제 JSX 이벤트를 실행합니다. 미디어·저장소·초기 조회만 mock입니다. 기대 동작을 별도 구현한 비교 모형으로 검사하지 않습니다.
- 이 보고 외 문서·기존 검사기·CSS·API·음원은 수정하지 않았습니다. 완료 source/attempt key, seek/clip, native played 범위, trusted ended, 기존 접수별 초안·완료 보존 코드는 그대로입니다. 영속 저장은 추가하지 않아 새 페이지는 1.25배로 시작합니다.

## 실패 재현과 같은 조건 재검증

작업 폴더는 `C:/00.프로젝트/happycall-ralphthon`입니다. 신원 조회는 pc1/CJJ, 작업표 검사는 45개 일치 PASS였습니다. 작업 중 메인이 문서만 커밋하여 검증 시 HEAD는 `955f5c6e37b2752da72df25a4e4cd48f7b8af2f8`입니다.

초기 mock 모듈 연결 오류로 audio를 찾지 못했던 검사기는 default export 연결을 바로잡았습니다. 이후 제품 수정 전에 실제 렌더 경로에 도달하여 기본값 기대 1.25, 실측 1로 실패했습니다. 최종 검사기의 `--revision` 옵션으로 과거 제품 소스에 같은 실패를 재현했습니다.

| 명령 | 기대 / 실측 |
|---|---|
| `node tests/e2e/call-playback-preference-unit.mjs --revision=3b67bf4ec2ba1041d1861ec8e2909f466416953d` | exit 1, `1 !== 1.25` 재현 |
| `node tests/e2e/call-playback-preference-unit.mjs` | exit 0, 21/21, 변이 7/7 검출 |
| `npm run typecheck` (apps/web) | exit 0, `tsc --noEmit` |
| `node tests/e2e/role-workflow-unit.mjs` | exit 0, 87/87, 변이 7/7 |
| `node tests/e2e/mobile-work-navigation-unit.mjs` | exit 0, 89/89, 변이 9/9 |
| `node tests/e2e/save-toast-unit.mjs` | exit 0, 48/48, 변이 3/3 |
| `git diff --check` | exit 0, 공백 오류 없음. 기존 LF→CRLF Git 안내는 출력됨 |

영향 검사 산출물: `.local/role-workflow-unit-1790015681283/results.json`, `.local/mobile-work-navigation-unit-1790015680295/results.json`, `.local/save-toast-unit-1790015679825/results.json`.

## 신규 검사 분모와 관측

21개 시나리오는 선호·격리 5개와 배속별 완료 게이트 16개입니다.

| 실행 조건 | 실측 |
|---|---|
| 기본값과 select 직후 다른 접수 선택 | 기본 1.25, 선택 1.5, native ratechange 0회인 상태에서 새 오디오 1.5 |
| WMS/TMS/센터/경영주 왕복 | 4경로 모두 선택 2배 유지, 이 이동의 mock 초안 쓰기 0 |
| native 유효값 6개 | 0.75/1/1.1/1.25/1.5/2 선택 표시·접수 변경 후 적용 일치 |
| 잘못된 값 6개 × select/native 2경로 | NaN/0/Infinity/-1/0.749/2.001 모두 직전 2배로 복구 |
| 처음부터 재생과 이전 audio 이벤트 | 새 요소에 1.5 유지, 이전 rate/play/ended/seek/error 5종이 현재 상태를 바꾸지 않음 |
| 동일 접수의 audioUrl 교체 | 새 source 완료 false, 배속 1.5 유지. 이전 source 이벤트 3종 무효 |
| 접수별 초안 | 실제 입력 이벤트로 서로 다른 두 mock 초안을 편집하고 왕복 후 각 값 유지 |
| 1.25·1.5 각각 정상 전체 재생 | 완료 true, ended 재수신에도 callback 각각 1회 |
| 각 속도 × seek/played 공백/played 없음/가짜 ended/구간/처음 재생 없음/native ended false | 14조건 모두 완료 false, callback 0회. 구간은 4.2초 이벤트에서 4초로 제한하고 pause |
| 이미 완료한 동일 source의 처음부터 재생 | 기존 부모 완료 true 보존. 다른 접수·다른 source는 false |

실행한 변이는 ① 접수 변경 시 부모 배속 초기화 ② Home 콜백 전달 제거 ③ Desk 값 전달 제거 ④ trusted ended 제거 ⑤ played 범위 검사 제거 ⑥ seek/처음부터 재생 게이트 약화 ⑦ 중복 완료 통지 방지 제거입니다. 각각 실제 행동 assertion에서 실패했으며 문법 오류나 문자열 유무로 검출했다고 세지 않았습니다.

## 동결 대상 해시와 남은 검증

검증한 제품 소스 SHA-256:

- page.tsx: `fa11d3912b5baa75745e94e3d532755a7e5af653ab86dc3b4c0c81ac302ee943`
- CallReview.tsx: `95f5f238173477c164aeaa83209782e8a245ad51c040ce67fa0c73e7d5f25e7f`
- call-playback-preference-unit.mjs: `0e3dd32c6adbb17d905bf4a08fe5d331c4dab8959fb43a2e8f1e4f818c0591d6`

새 서버/브라우저 시작 0, 실제 API·유료 호출 0입니다. 기존 실제 22접수·미저장 초안에는 이 워커가 접근하거나 변경하지 않았습니다. mock의 `isTrusted`와 played 범위는 주입한 값이므로 실제 브라우저가 생성한 증거가 아닙니다. React 스케줄링·실제 청취시간·음성 자연스러움도 이 검사의 분모 밖입니다.

메인은 기존 3100 탭에서 HMR과 세 폭 레이아웃, 실제 1.25/1.5배 청취·사례/역할/WMS/TMS 왕복·분석 준비 조건을 독립 검증합니다. 실제 API 8100 재시작과 기존 저장자료/초안 초기화는 하지 않습니다. 기존 1배 리허설의 의미를 유지하려면 실행 시 `selectOption('1')`을 명시합니다. 결과 커밋·push·배포 묶음 작성과 인수 판정은 메인 소유입니다.
