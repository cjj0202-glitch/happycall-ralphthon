# 저장된 외부 알림 상태 UI — 로컬 구현·SSR 검증

2026-09-22 02:37:58 KST / pc1 CJJ / 작업 시작 HEAD `31dbd66`. 메인 배정의 표시 UI 구현 결과이며 외부 발송·실제 수신 완료 보고가 아닙니다.

## 사용자가 확인할 수 있는 결과

상담원 저장·센터 전달 영역 아래, 센터 최종 회신 영역 아래, 경영주 선택 접수 회신 영역에 접이식 `외부 알림`을 연결했습니다. 닫혀 있어도 `연결 안 됨`을 표시하고, 정상 기록을 펼치면 알림 종류·채널·논리 수신 역할·한국 시각만 표시합니다. 공급자 미설정과 저장/발송의 차이를 안내합니다.

Props는 `NotificationStatus({ caseData, audience: 'workforce' | 'owner' })`입니다. 세 화면 모두 저장된 `c` 객체를 그대로 넘깁니다. 컴포넌트는 `c.notificationOutbox`만 읽고 초안·회신 본문으로 알림을 만들지 않습니다. 업무 화면은 동일 사건의 정상 기록, 경영주 화면은 동일 사건의 `final_reply/kakao/owner`만 표시합니다. UI 역할 선택은 사용자 인증·공급자 수신 권한의 증거가 아닙니다.

11개 필드의 존재·형식, schemaVersion=1, 64자리 소문자 ID, 동일 caseId, 양의 정수 caseRevision와 저장 revision 상한, 허용된 4조합, 역할에 맞는 해시 참조, ISO 시각, not_connected 상태와 사유를 검증합니다. missing_recipient는 owner/null 조합만 허용합니다. 알 수 없는 추가 속성·잘못된 배열/행·다른 사건·미래 revision·중복 ID는 원시 값을 숨기고 `기록 확인 필요`를 표시합니다. 저장 revision 자체를 확인할 수 없는 알림도 보류합니다. 정상 행과 잘못된 행이 섞이면 정상 행만 표시하면서 경고를 유지합니다.

필드 미존재와 빈 배열은 `저장된 알림 기록 없음`입니다. 과거 외부 발송이 0건이었다고 단정하지 않습니다. 사용자 이름·사건 ID·알림 ID·recipientRef·원문·회신·임의 URL은 이 컴포넌트에서 렌더하지 않습니다.

## 변경 소유

- `apps/web/components/NotificationStatus.tsx`: 읽기 전용 표시·검증 컴포넌트.
- `apps/web/lib/types.ts`: NotificationIntent와 optional outbox 타입.
- `apps/web/app/page.tsx`: import 1곳, 저장된 사건의 호출 위치 3곳.
- `tests/e2e/notification-status-unit.mjs`: 실제 React SSR·호출 위치·반례·변이 검사.
- 본 보고서.

기존 Split-Pane 워크벤치 골격을 유지하고 `panel/details/badge/details-list` 등 기존 클래스 7종을 재사용했습니다. 새 CSS·인라인 스타일·팔레트·폰트·설정 버튼은 추가하지 않았습니다. 현재 22건 저장소·미저장 초안·원장·키를 읽거나 변경하지 않았고 새 서버·브라우저·네트워크도 사용하지 않았습니다. 실제 열린 화면의 보존·상호작용 확인은 메인이 별도 수행합니다.

## 실행 증거

| 명령·대상 | 기대 | 실측 |
|---|---|---|
| `node tests/e2e/notification-status-unit.mjs` | 실제 React 렌더, 정상·음성·경계·변이 검출 | **124/124**, exit 0 |
| `cd apps/web; node node_modules/typescript/bin/tsc --noEmit --incremental false` | 타입 오류 없음 | exit 0, 진단 0 |
| `git diff --check -- apps/web/components/NotificationStatus.tsx apps/web/lib/types.ts apps/web/app/page.tsx tests/e2e/notification-status-unit.mjs` | 추적 diff 공백 오류 없음 | exit 0; types.ts LF/CRLF 경고만 |
| 새 컴포넌트 스타일 검사 | 실제 stylesheet에 기존 클래스 전부 존재, 새 색/스타일 없음 | 클래스 **7/7**, 인라인 스타일·색·폰트 payload **0** |

SSR는 로컬 React 19·react-dom/server와 실제 생산 TSX를 실행합니다. NotificationStatus를 포함한 Desk/Center/Owner의 실제 함수를 렌더하고 저장 `caseData` 객체 identity 및 audience가 정확한지 확인합니다. 다른 장면과 IO만 로컬 스텁으로 막았습니다. API 호출·draft set/replace가 실행되면 검사기가 즉시 실패합니다. 초안 outbox sentinel을 넣어도 세 호출 위치 모두 저장 기록만 렌더했습니다. React HTML escaping, 원문/회신/참조 sentinel 비노출, 모든 필드 누락, 잘못된 형식, 18개 종류/채널/역할 조합, 윤년·시간대, 미래 revision도 실행했습니다.

실제 소스를 메모리에서 변이한 `caseId 일치 제거`, `owner 필터 제거`, `status 가드 제거`, `미래 revision 가드 제거` **4/4**가 동일 렌더 단언을 깨뜨렸습니다. 변이를 제품 파일에 저장하지 않았습니다. 검사 결과의 serverStarts/browserStarts/networkCalls/caseStoreReads/caseStoreWrites는 모두 0입니다.

검사 시 생산 파일 SHA256:

| 파일 | SHA256 |
|---|---|
| NotificationStatus.tsx | `7a15759654f2867835acff0dfffcc20500b699c264d19efc38969a56a38c5045` |
| types.ts | `03da06b8057c8a9a728edf4e9c15cb8040f6277e72f1885e259c0efb6d6313d0` |
| page.tsx | `22e8255e9b06cf2df946ea91e231fcc38c28c34255a8a0c4de0985b9f67cece9` |

## 게이트 한계와 인계

`node C:/00.프로젝트/75_하네스_클라우드배포/01_프론트엔드/01_토큰/check.mjs`는 **exit 2**였습니다. 토큰 244개, CSS 46파일·hex 272건, JS/HTML 230파일·hex 3119건을 스캔했고 E601의 기준선 3029→3119 증가와 경고 14개를 보고했습니다. 이 게이트의 실제 소비처는 50/91/scmops이며 해피콜 TSX는 대상에 없습니다. 따라서 해당 실패를 이번 컴포넌트의 회귀로 단정하거나 이 게이트로 해피콜 디자인 통과를 주장하지 않습니다. 위 7/7 클래스·새 값 0 검사는 이번 컴포넌트에 도달하는 별도 정적 검사입니다.

브라우저 3폭·접기/펼치기·키보드·콘솔·현재 미저장 초안 보존은 이 워커에서 미실행이며 메인 소유입니다. 현재 서버에서 새 알림 저장부터 실제 화면 갱신까지의 통합 흐름과 외부 채널 실제 수신도 미검증입니다. 기존 page.tsx transpile 하네스에는 신규 NotificationStatus import의 mock 등록이 필요할 수 있어 메인에게 알렸습니다. 해당 하네스는 이 워커 소유 밖이므로 수정하지 않았습니다. 커밋·push·최종 인수는 메인이 수행합니다.

## 메인의 열린 화면 검수와 영향 검사

2026-09-22 02:37~02:44 KST, pc1의 기존 3100 탭에서 HMR 반영 화면을 확인했습니다. 상담원·센터·경영주 각각 390/768/1280px, 총 9개 역할/폭 조합의 스크린샷을 직접 확인했습니다. 저장된 알림이 없는 상태만 실제 브라우저에서 확인했으며, 기록이 있는 상태는 위 SSR 검사 범위입니다.

| 역할 | 390px 패널 client/scroll 폭 | 768px | 1280px |
|---|---:|---:|---:|
| 상담원 | 341/341 | 719/719 | 860/860 |
| 센터 | 307/307 | 685/685 | 810/810 |
| 경영주 | 307/307 | 685/685 | 521/521 |

패널의 가로 넘침·문구 겹침·잘림을 관측하지 않았습니다. 각 역할 최초 진입에서는 접혀 있고 연결 안 됨이 보였습니다. 상담원 패널의 클릭 펼침, Enter 접힘, Space 펼침과 summary 포커스 유지·포커스 링을 확인했습니다. 센터 768px 최초 캡처는 패널이 화면 밖이어서 판정에서 제외하고 위치를 맞춘 뒤 다시 확인했습니다. screenshot은 도구 출력으로 확인했으며 저장 파일을 생성했다고 주장하지 않습니다.

검수 후 상담원 CASE-0002로 복귀하고 viewport override를 해제했습니다. DOM의 전체 22건·미저장 초안 있음이 유지됐습니다. 원장 저장·폼 제출·초안 초기화·페이지 reload·새 서버/브라우저 시작은 하지 않았습니다. 기존 탭의 error 로그 limit8 조회는 빈 배열이었으며, 이 관측을 전체 세션에 과거 오류가 없었다는 뜻으로 확대하지 않습니다.

별도 렌더 검토 에이전트는 자기 IAB에 메인 탭이 없어 0/3폭 미실행을 보고했습니다. 다른 세션의 빈 탭을 화면 통과로 세지 않았으며 위 9조합은 메인의 실제 관측입니다. 사람 사용성 관찰은 남아 있습니다.

메인 영향 검사(02:43~02:44, 각 exit0): role-workflow **87/87**·변이7/7, save-toast **48/48**·변이3/3, mobile-work-navigation **89/89**·변이9/9. 첫 검사 mock 목록에 NotificationStatus를 등록했고 나머지 기존 검사는 변경 없이 실행했습니다. 새 서버 모듈의 배포 포함 변경은 test_deployment_bundle.py **70 PASS / 56.95초 / exit0**로 검사했습니다.

별도 읽기 전용 검토자는 실제 SSR 124/124·4개 변이 검출을 재확인하고, 자기 입력으로 두 사건×두 역할×8배열순서의 혼입32건, 원문·회신·초안 변경 불변32건, 11필드×잘못된값5종의 보류55건을 실행했습니다. 업무4행/경영주 카카오1행·Teams0, 혼입 경고 유지, 원문/참조값 비노출을 확인했습니다. 검토 범위에서 추가 결함을 재현하지 못했으며 서버·브라우저·네트워크·원장·파일쓰기는0이었습니다. 이는 SSR 독립 검사이며 사람 관찰을 대신하지 않습니다.
