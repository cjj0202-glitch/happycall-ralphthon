# PC4 N04-D2 메인 독립 설계 인수 검토

2026-09-22 07:34 KST / PC1 `최제준`의 별도 검토 에이전트. **설계 문서 인수에 적합하다는 한정 판정입니다. 전달 worker·외부 알림·운영 개통의 완료 판정은 아닙니다.** 검토 범위에서 인수를 막는 설계 결함은 발견하지 못했습니다.

## 입력과 보존

- PC4 결과 커밋: `535e2f218725daefcf4b447831fef07497c0d2e6`
- 비교한 main: `f043c60b357c5341e80959c748036b28d032bd18`
- PC4 설계의 고정 코드 기준: `296cba500808147046ebc4326e44e1ffc70a8629`
- 두 원본은 `git show`로 읽었고 수정하지 않았습니다. 이 검토자는 본 보고서만 작성했습니다. 원본 통합·커밋·push·PC4 후속 배정은 메인 담당입니다.

| 원본 | 바이트 | SHA-256 |
|---|---:|---|
| `planning/notification-delivery-contract.md` | 36,441 | `9ab6fa78bb51517f63e156f56a89ecbf05904bb3be6915510a3ad91567404ea7` |
| `reports/pc4/notification-design-review.md` | 11,497 | `ed8d1bc9d64eba558f1dc79e0987e4e341e2a8f561433f57f71fe32e3df74540` |

## 현재 코드와 계약 대조

`296cba5`와 `f043c60` 사이에서 `server/notifications.py`, `service.py`, `repository.py`, `cas_repository.py`, `vercel_blob_store.py`, `handlers.py`, `apps/web/components/NotificationStatus.tsx`, `apps/web/lib/types.ts`, `api.ts`, `planning/notification-outbox-phase1.md`의 **10파일 차이는 0**입니다. PC4의 고정 코드 해석은 이 비교 범위에서 현재 main에도 적용됩니다.

| 감사 항목 | 직접 대조 결과 |
|---|---|
| 저장된 outbox 형식 | AST에서 정확히 11필드 확인. schemaVersion=1, status=`not_connected`, 허용 역할·채널 조합과 결정적 I 생성 설명 일치 |
| 발생 시점 | 이관1·중간 회신1·종결2. 회신 변경+종결은 `elif`로 최종2만 생성. 같은 회신/조치만/GET/분석은 새 의도 없음 |
| 수신자 원천 | center=departmentId, owner=intake.storeId, counselor=caseId 해시. counselor를 실제 사용자로 취급하지 않는 설명 일치 |
| JSON 저장 | 복사본 transform 안에서 접수와 의도를 함께 변경하고 revision 증가 후 원자 교체. 전송 호출 없음 |
| CAS 저장 | transform 1회. 다른 사건 충돌은 그 결과를 재사용하고, 같은 사건 변경은409. Blob의 확인된412/precondition_failed만 충돌이며 응답 유실은 미저장 확정이 아님 |
| 기존 UI/API 경계 | 업무 PATCH로 outbox 직접 수정 금지, 종결 잠금 유지. 현재 역할 헤더·UI 필터를 인증으로 간주하지 않는 설명 일치 |

계약의 고정 SHA 코드 링크는 파일 링크 13개이며 이 중 줄 앵커가 있는 12개는 모두 해당 파일의 유효한 줄로 연결됩니다. 나머지는 1단계 설계 파일 링크입니다. 링크 존재와 코드 읽기 대조를 실행 검증으로 세지 않았습니다.

## 중복·응답 유실·수신자 변경 논리

다음은 문서에 명시된 불변식의 설계 검토 결과입니다. 새로운 저장소나 worker를 실행해 증명한 결과가 아닙니다.

- `(environment,I)` 단일 Envelope가 예약·activeD·시도 이력·lease를 원자적으로 보존하므로 guard만 생긴 뒤 중단된 상태를 완료로 버리지 않습니다. unresolved 재스캔과 CAS 응답 유실 후 재조회가 문서에 포함돼 있습니다.
- D가 stable binding에 묶이고 per-I guard도 유지되므로 주소·mappingVersion 변경만으로 새 전달을 자동 생성하지 않습니다. 다른 binding 교체는 시도0·lease없음·기대 activeD를 같은 CAS로 검사하고 oldD를 비활성화합니다.
- 시도 기록을 먼저 저장하고 단일 lease 승자만 호출하는 경계가 명시돼 있습니다. lease 만료 후 옛 worker의 지연 호출까지 fencing으로 취소할 수 없다는 한계를 인정하고, 그 가능성을 제거하기 전 재시도하지 않습니다.
- timeout/전송 후5xx/프로세스 종료는 unknown으로 보존합니다. unknown을 자동 queued로 바꾸지 않으며, 신뢰 가능한 미수락 증거와 옛 시도 종료 확인 후에만 같은 D·목적지·payload의 새 attempt를 검토합니다.
- Teams 성공과 Kakao 실패는 서로 다른 I/D로 처리합니다. 한 대상의 실패가 성공한 대상의 재발송을 유발하지 않습니다. 발송 직전 mappingVersion·권한·activeD 확인과 callback 대상·서명·순서 대조를 요구합니다.

따라서 설계 문서는 원격 exactly-once를 보장한다고 오해하게 하지 않습니다. 실제 구현 인수에서는 독립 프로세스 동시 점유, CAS 성공 후 응답 유실, 멈춘 옛 worker 재개 및 공급자 내부 자동 재시도를 따로 재현해야 합니다.

## 공식 문서 재대조

2026-09-22 07:31~07:34 KST에 공개 공식 문서만 조회했습니다. 계정 로그인·tenant 설정·키 조회·실제 수신처 접근은 하지 않았습니다.

| 핵심 주장 | 독립 확인 |
|---|---|
| Workflow 호출자 제한 | Teams 트리거는 제한 모드에서 토큰을 요구합니다. OAuth 문서의 SPN object ID 허용, Specific users의 빈 목록은 tenant 전체라는 주의, public audience가 계약과 일치합니다. [Teams connector](https://learn.microsoft.com/en-us/connectors/teams/#when-a-teams-webhook-request-is-received), [OAuth](https://learn.microsoft.com/en-us/power-automate/oauth-authentication) |
| 옛 Connector 수명 | 2026-04-14 업데이트의 종료 구간 2026-05-18~22가 일치합니다. Workflows 자체의 폐기가 아닙니다. [Microsoft 최종 공지](https://devblogs.microsoft.com/microsoft365dev/retirement-of-office-365-connectors-within-microsoft-teams/) |
| Graph와 RSC | 일반 channel send 표의 delegated ChannelMessage.Send, migration용 Teamwork.Migrate.All, 성공201+chatMessage 및 별도 RSC ChannelMessage.Send.Group를 구분한 설명이 일치합니다. [channel send](https://learn.microsoft.com/en-us/graph/api/channel-post-messages?view=graph-rest-1.0), [RSC](https://learn.microsoft.com/en-us/microsoftteams/platform/graph-api/rsc/resource-specific-consent) |
| 라이선스 | 사용자 라이선스와 flow에 할당하는 Process의 권한을 구분해야 한다는 설명이 일치합니다. 실제 조직의 보유 권한·비용은 미확정입니다. [공식 라이선스 유형](https://learn.microsoft.com/en-us/power-platform/admin/power-automate-licensing/types) |
| 일반 Kakao 메시지 | 같은 서비스 사용자·친구 중심 기능이며 HTTP200에도 수신자 일부 실패가 있을 수 있다는 설명이 일치합니다. [기능 구분](https://developers.kakao.com/docs/ko/kakaotalk-message/common), [수신자별 REST 결과](https://developers.kakao.com/docs/ko/kakaotalk-message/rest-api) |
| 알림톡 | 승인된 정보성 템플릿, 적법하게 수집한 전화번호, 비즈니스 채널 설정 및 공식 딜러별 계약·단가가 필요한 경로라는 설명이 일치합니다. [공식 알림톡 안내](https://kakaobusiness.gitbook.io/main/ad/infotalk) |

공식 Connector 일반 제한에는 private channel 미지원 문구가 남아 있지만 최신 종료 공지는 Workflows의 private channel 지원을 설명합니다. PC4가 구체 템플릿·tenant 조건을 개통 전에 실측하도록 남긴 것은 적절합니다. 이 감사는 모든 채널 조합의 지원을 보장하지 않습니다. Graph chat send·개인 bot 읽음·모든 공급자별 제한 수치까지 전수 재조회하지는 않았으며, 이번 표의 핵심 주장에 한정했습니다.

## 분모와 다음 인수 경계

Markdown의 검사 ID를 추출한 결과 **D01~D31 31개 검사군, D09/D19 하위 입력 포함 35행, 중복 ID 0**입니다. 모두 미실행이며 **실행0/31 검사군(0/35행)**을 유지합니다. 문서 작성·공식 자료 조회·코드 읽기·정적 개수 검사를 이 분자에 더하지 않습니다.

후속 무과금 FakeTransport Bolt는 계약 §8의 D01/D03/D06/D07와 commit 이전 dispatch 변이부터 독립 인수할 수 있습니다. 실제 업무 저장소와 알림11필드는 보존하고, 임시 저장소·합성 binding/링크·외부 네트워크 차단이 선행돼야 합니다. 이 보고서는 후속 배정을 직접 내리거나 worker 전체 구현 완료를 승인하지 않습니다.

실제 인증된 상세 조회, 담당 상담원 이력, 검증된 수신자 매핑, 영속 전달 저장소·worker, Teams tenant/flow 결과 대조, 알림톡 딜러·템플릿·비용 및 외부 수신 증거는 계속 미완료입니다. 원본 문서의 not_connected 유지 조건을 그대로 인수합니다.

이번 감사의 외부 알림 발송0, 외부 수신 검증0, 공급자 인증·키·계정 접근0, 유료 API 호출0, 제품 코드 변경0, commit/push/메일0입니다. 새 테스트·서버·제품 브라우저를 실행하지 않았습니다.
