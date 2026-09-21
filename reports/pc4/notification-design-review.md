# N04-D2 — 알림 전달 설계 검토 기록

2026-09-22 / pc4 장준호 / GitHub j324rst-svg. **문서·코드 읽기 검토이며 제품 동작 테스트 결과가 아닙니다.**

## 요청과 기준

00:42 KST의 [D2 배정](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/10#issuecomment-5763228727)과 후속 outbox 1단계/메인 인계 댓글을 대조했습니다. 07시대 backlog 점검에서 미착수 문서 두 개를 확인하고 [착수·수신 회신](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/10#issuecomment-5768251356)을 게시·재조회 검증했습니다. 기존 U1 결과를 재구현하거나 공용 파일을 수정하지 않았습니다.

| 항목 | 실제 기준 |
|---|---|
| 작업 checkout | work/pc4-n04-tms-qa, 작성 전 79d763acd2985c32e0eb853d17a7d68dce0174d0 |
| 설계 코드 기준 | 296cba500808147046ebc4326e44e1ffc70a8629 (새 pc1 인계 기준) |
| 읽기 비교 대상 | origin/main=f043c60b357c5341e80959c748036b28d032bd18, 이번 실행에서 fetch 한 번 |
| 소유 산출물 | planning/notification-delivery-contract.md, reports/pc4/notification-design-review.md |
| 읽기 전용 의존 | server/service.py·notifications.py·repository.py·cas_repository.py·vercel_blob_store.py·handlers.py, apps/web의 page·api·types·NotificationStatus, outbox/역할 정본 |
| 지시 대조 | AGENTS, PROMPT_team, docs24·25·28, mailbox 원본, happycall-night-ops 및 #10 카드·후속 댓글 |

고정 기준과 f043c60 사이의 notifications/service/repository/CAS/NotificationStatus/types/API/outbox 설계는 차이 0입니다. page.tsx에는 근거 저장 후 acceptOwnEvidenceSave 연결, drafts.ts에는 확인된 근거 전용 PATCH 후 초안 revision 보정이 있습니다. **이 읽기 비교가 최신 main 전체 동작 검증을 뜻하지 않습니다.**

## 배정 수용 기준 대조

| 수용 기준 | 이번 산출물 / 판정 범위 |
|---|---|
| 저장 시점·사건·역할·채널·키·상태·재시도 연결 | 계약 §2의 네 행, §5~6. 고정 SHA 실제 함수에 링크. 추가확인 요청은 미구현으로 표시 |
| Teams·Kakao 공식 경로와 조건 | 계약 §3. Workflows/Graph/RSC 구분, 알림톡과 일반 메시지 구분. 실제 계정 권한/가격은 미확정 |
| 저장 실패·중복·불명확한 전송 결과 | 계약 §5~6. Case 의도 불변, 별도 delivery/attempt 제안, unknown 자동 재발송 금지 |
| 수신자·개인정보·상세 링크 | 계약 §4. 현재 counselor ref는 사람 아님, 권위 있는 매핑/인증 링크 전까지 전송0 |
| 12개 이상 반례 | 계약 §7 D01~D31, 31개 검사군·35개 행의 **미실행 시나리오**. N/A/S 정의와 실제 외부 전송0 분리 |
| BMAD와 작은 Bolt | 계약 §8. 4관점·4개 첫 입력·하나의 변이 대조군·같은 조건 재시험 제안. 실행하지 않음 |
| 독립 검토·수정·동일 조건 재대조 | 아래 독립 검토 기록에 실제 지적·처리·재검 결과를 기재 |
| 공유 | 두 파일만 명시 커밋·본인 branch push·원격 SHA 대조 후 #10 결과 회신. 인수는 pc1 |

## 공식 자료 조사 범위

Teams 공식 문서: 2026-09-22 **07:13:09~07:14:52 KST**, 별도 읽기 검토자가 비로그인 웹 조회. Kakao 공식 자료: **07:14~07:17 KST**, 주 작성자가 비로그인 웹 조회. 원문을 대량 복사하지 않고 필요한 조건만 정리했습니다. 1차 검토 후 OAuth 빈 목록·Process 라이선스 조건을 07시대에 추가 재조회했습니다. 실제 tenant·운영 계정·딜러 관리자 화면을 열거나 설정하지 않았습니다.

- Teams: [Workflows 설정](https://support.microsoft.com/en-us/workflows/send-messages-in-teams-using-incoming-webhooks), [Connector 최종 폐기 공지](https://devblogs.microsoft.com/microsoft365dev/retirement-of-office-365-connectors-within-microsoft-teams/), [OAuth 인증](https://learn.microsoft.com/en-us/power-automate/oauth-authentication), [일반 send 권한표](https://learn.microsoft.com/en-us/graph/api/channel-post-messages?view=graph-rest-1.0), [RSC](https://learn.microsoft.com/en-us/microsoftteams/platform/graph-api/rsc/resource-specific-consent).
- Kakao: [상품 비교](https://developers.kakao.com/docs/ko/kakaotalk-message/common), [REST 인증·친구 수신자·부분 성공](https://developers.kakao.com/docs/ko/kakaotalk-message/rest-api), [알림톡 공식 딜러·템플릿·개설](https://kakaobusiness.gitbook.io/main/ad/infotalk), [심사 가이드](https://kakaobusiness.gitbook.io/main/ad/infotalk/audit).
- 선택 근거와 한계: Workflows는 후보이며 tenant 적합성을 확인하지 않았습니다. Graph 일반 app-only/migration 권한과 RSC를 분리했습니다. 카카오는 정보성 알림톡을 후보로 두되 딜러 미선정이므로 endpoint·인증·멱등키·상태 조회·단가를 발명하지 않았습니다. 본 계약은 메시지 도착·열람을 보장하지 않습니다.

## 독립 검토 기록

검토 역할은 같은 pc4 안의 별도 보조 에이전트입니다. 원격 pc1/pc2/pc3의 검증·실제 사람 관찰로 세지 않습니다. 주 작성자가 두 파일을 작성하고, 코드 경계 검토자와 공급자 검토자는 파일을 수정하지 않고 반례·근거를 제출했습니다.

1차 독립 검토 후 아래 6건을 수정했습니다. 이는 문서 결함의 수정이며 실제 전송 구현 결함을 재현·수정했다고 보고하지 않습니다.

| ID / 검토자 | 초안 문제·반례 | 주 작성자 처리 / 근거 |
|---|---|---|
| R1 / 코드 경계 / P1 | per-I guard 생성 후 D 생성 전에 종료하면 중복으로 오판해 영구 누락 가능 | 계약 §5에 단일 DeliveryEnvelope, unresolved/ready, activeD와 D의 원자적 CAS·재조회 복구 추가. 다른 binding 교체는 시도0/lease없음·동일 CAS로 oldD 비활성화. D27~D29 추가 |
| R2 / 코드 경계 / P2 | unknown 상태표는 재조회만 허용하는데 본문은 멱등성 주장만으로 재개 허용 | 해당 예외 제거. 확정 미수락·옛 worker 지연 dispatch 제거 후 failed→queued, 같은 D/payload/대상·새 attempt로 한정. 공급자 멱등 보장은 아직 미확정 |
| R3 / 코드 경계 / P2 | D19의 0또는1 조합은 호출0/수락1도 허용; D09 대상별 수와 D17 기존 기록 전제가 모호 | D19a/b/c를 (0,0)/(1,0)/(1,1)로 분리, D09a/b/c 대상 누락 분리, D17 기존 의도 처리/제외 전제 명시. 현재 outbox 동작은 유지 |
| R4 / 공급자 / P2 | Teams 제한 모드만으로 제품 SPN 제한 안 됨; Specific users의 빈 목록은 tenant 전체 허용 | 공식 OAuth 문서 재조회 후 Specific users+비어 있지 않은 승인 SPN oid allowlist, 빈 목록 개통 금지와 다른 tenant/oid/audience 음성 검사 D30/D31 추가 |
| R5 / 공급자 / P3 | 라이선스를 무조건 소유자 기준으로 읽을 여지 | 사용자 라이선스 기반 flow와 Process를 flow에 할당한 경우를 구분. 실제 라이선스·비용은 미확정 유지 |
| R6 / 공급자 / P3 | 채널 읽음 기본 not_supported와 D01의 unknown 표현 불일치 | D01 채널 읽음을 not_supported로 일치. 메시지 생성·게시를 사람 읽음으로 바꾸지 않음 |

R1/R2의 저장소와 전이 문법은 이 문서의 **신규 제안**입니다. 실제 fixed 코드의 [원자적 업무 저장](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/296cba500808147046ebc4326e44e1ffc70a8629/server/repository.py#L93)과 [기존 outbox 불변 검증](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/296cba500808147046ebc4326e44e1ffc70a8629/server/notifications.py#L26)을 침범하지 않도록 구분했습니다. R4/R5는 [OAuth 조건](https://learn.microsoft.com/en-us/power-automate/oauth-authentication)과 [라이선스 유형](https://learn.microsoft.com/en-us/power-platform/admin/power-automate-licensing/types)의 실제 본문으로 주 작성자도 확인했습니다.

수정본을 두 검토자에게 다시 전달했고, 07:28 KST 무렵 동일 반례로 R1~R3 및 R4~R6가 설계상 해소됐다는 회신을 받았습니다. 두 검토자 모두 이번 읽기 범위에서 추가 차단 문제를 발견하지 못했습니다. 31개 검사군·35개 행 분모도 대조했습니다. **읽기 검토 통과이며 인증·발송·worker 실행 통과가 아닙니다.**

## 재현 가능한 읽기 점검과 실측

PowerShell에서 작업 루트의 Start-HappyCall.ps1을 dot-source한 뒤 저장소에서 다음 읽기 명령을 사용했습니다. git show로 고정 SHA를 읽었으며 작업 checkout을 main으로 바꾸지 않았습니다.

```text
python channel/whoami.py
gh api user --jq .login
git status --short
git rev-parse HEAD
git fetch origin
git show 296cba500808147046ebc4326e44e1ffc70a8629:server/notifications.py
git show 296cba500808147046ebc4326e44e1ffc70a8629:planning/notification-outbox-phase1.md
git diff 296cba500808147046ebc4326e44e1ffc70a8629 f043c60b357c5341e80959c748036b28d032bd18 -- server/notifications.py server/service.py server/repository.py server/cas_repository.py apps/web/components/NotificationStatus.tsx
python ops/tasks.py status
python ops/tasks.py check
```

문서 정적 점검(07:28 KST)에서 UTF-8 읽기·코드 fence 짝·줄끝 공백 검사를 통과했습니다. 고정 SHA 소스 링크 13개의 파일/줄 존재와 시나리오 31개 검사군·35개 행을 대조했습니다. 이는 링크 대상 코드의 실행 검사가 아닙니다.

신원 기대 pc4/장준호/j324rst-svg와 실측이 일치했습니다. task CLI는 기존 45개 작업표의 의존성/WIP/TODO 일치 검사를 통과했고 DONE3/TODO42였습니다. **그 수치는 N04 제품 완료율이 아니며 D2 인수 증거도 아닙니다.** 중앙 작업표를 수정하지 않았습니다.

D01~D31 실행 **0/31 검사군(0/35 행)**. 외부 API 전송 **0**, 외부 수신 검증 **0**, provider 로그인/가입/구독/동의 **0**, 배포·서버 시작·브라우저 제품 조작 **0**. 원문 로그·키·토큰·인증번호·실제 연락처를 문서나 GitHub에 싣지 않았습니다. 제품 테스트를 다시 돌리지 않은 이유는 배정이 문서·읽기 검토에 한정되고 코드 변경이 없기 때문입니다.

## 인계와 남은 게이트

후속 엔지니어는 계약 §8 순서로 fake Bolt → 31개 검사군 검증 → 공급자/수신자/인증/비용/결과 대조 개통 조건 → 별도 외부 수신 검증을 수행해야 합니다. 실제 추가확인 요청 모델, counselor 배정 이력, 인증된 상세 route, 영속 delivery 저장소·worker는 아직 없습니다. 현재 알림 상태는 계속 not_connected입니다.

pc1이 설계 인수·통합·후속 소유권을 정합니다. pc4가 main에 통합하거나 이슈/중앙 TODO를 완료 처리하지 않습니다. 기존 API503/STORAGE_CONFIG_INVALID 및 정책 거부는 이번 문서 작업으로 해소되지 않았으며 우회하지 않았습니다. N04 전체 두 흐름 6회·실제 연동·실제 사람 사용성·공식 제출도 완료로 바꾸지 않습니다.

공식 배점과의 연결은 실제 작성·독립 검토 기록(활용20), 기존 Goal과 이 카드의 연결 근거(Goal20), 검토 가능한 배정 산출물(위임30), 반례·수정·재대조 증거(검증30)입니다. 예상 득점·Goal 신규 실행·인수 완료를 주장하지 않습니다.
