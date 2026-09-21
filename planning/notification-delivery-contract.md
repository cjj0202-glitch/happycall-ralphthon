# N04-D2 — 저장된 사건에서 외부 알림으로 이어지는 전달 계약

작성: pc4 / 장준호 / j324rst-svg, 2026-09-22 KST. **설계 제안이며 발송 구현·실행 결과가 아닙니다.**
배정: [#10 D2 카드](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/10#issuecomment-5763228727). 코드 기준은 `296cba500808147046ebc4326e44e1ffc70a8629`입니다. 최초 카드의 `5f3bf9d225faeb097d68a87befe8ad709c1917be` 이후 구현된 outbox 1단계를 반영했습니다. 작업 branch는 `work/pc4-n04-tms-qa`, 작성 전 HEAD는 `79d763acd2985c32e0eb853d17a7d68dce0174d0`입니다.

## 1. 사용자 결과와 현재 경계

상담원·센터·경영주는 사건 저장과 외부 알림의 처리 결과를 구분할 수 있어야 합니다. 업무 저장이 실패하면 알림을 보내지 않고, 같은 확정 사건은 대상별로 한 전달 작업만 만들며, 전송 결과가 불명확하면 성공 표시나 무조건 재전송을 하지 않습니다.

- 현재 구현: 사건과 같은 원자적 저장 안에 발송 **의도**를 보존하며 모든 상태가 `not_connected`입니다. 실제 주소·전송 worker·provider 인증·실제 수신 확인은 없습니다.
- 이번 산출물: 이 문서와 `reports/pc4/notification-design-review.md` 두 파일. 공통 서버·UI·테스트·중앙 작업표는 바꾸지 않습니다.
- 후속 구현은 pc1의 별도 카드와 인수가 필요합니다. 여기서 제안하는 저장소·함수·상태·인증 링크가 이미 존재한다고 해석하지 않습니다. 외부 전송·외부 수신 검증은 각각 0건입니다.
- 기존 [outbox 1단계](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/296cba500808147046ebc4326e44e1ffc70a8629/planning/notification-outbox-phase1.md)와 역할 흐름을 유지합니다. 09:00 이후 새 구현을 시작하지 않고 남은 게이트를 인계합니다.

## 2. 실제 저장 지점 → 사건 → 대상

아래의 N은 현재 코드가 생성하는 새 의도 수이며 외부 전송 수가 아닙니다. 모든 행은 `CaseService.patch` 검증 후 같은 repository transform에 들어갑니다. D는 후속 전달 작업 키입니다. 재시도·대조는 §5~6을 공통 적용합니다.

| 실제 확정 저장 조건 / 코드 | 사건·N | 논리 수신자 → 채널 | 현재 키·상태 / 후속 전달 |
|---|---|---|---|
| draft/review에서 handed_off로 전이; [notifications.py L78](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/296cba500808147046ebc4326e44e1ffc70a8629/server/notifications.py#L78) | handoff · 1 | 검증된 departmentId의 center → Teams | I에 저장 revision·center ref·teams 포함; not_connected → 매핑 검증 후 D 1개. 저장 불명확 시 재조회 |
| handed_off/in_progress에서 비어 있지 않은 reply의 strip 결과가 직전과 다름; [L83](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/296cba500808147046ebc4326e44e1ffc70a8629/server/notifications.py#L83) | interim_reply · 1 | caseId로 표시한 미배정 counselor → Teams | I의 kind=interim_reply; not_connected → 실제 담당자 확정 후 D 1개. owner 발송 없음 |
| 이전 상태가 closed가 아니고 closed로 저장; [L80](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/296cba500808147046ebc4326e44e1ffc70a8629/server/notifications.py#L80) | final_reply · 2 | counselor → Teams 및 intake.storeId의 owner → Kakao | 채널·역할별 서로 다른 I/D. 한 대상 실패가 다른 대상의 재발송을 유발하지 않음 |
| 센터의 독립된 추가 확인 요청 | 현재 모델·API·event 없음 · 0 | 제안: 센터→담당 상담원 Teams. 아직 생성 금지 | 별도 저장 전이·필드·권한 계약을 pc1이 먼저 확정. 임의 kind 추가 금지. [상담 화면 L251](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/296cba500808147046ebc4326e44e1ffc70a8629/apps/web/app/page.tsx#L251)의 질문 문자열은 이 모델이 아님 |

회신 변경과 종결을 함께 저장하면 `elif` 우선순위로 final_reply 2개만 생깁니다. 같은 회신 재저장, 조치 목록만 수정, 초안 부서 변경, 분석, GET에는 새 의도가 없습니다. 업무 revision 증가 자체는 발송 사건이 아닙니다.

[현재 식별 코드 L19](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/296cba500808147046ebc4326e44e1ffc70a8629/server/notifications.py#L19), [대상 생성 L93](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/296cba500808147046ebc4326e44e1ffc70a8629/server/notifications.py#L93):

```text
recipientRef = role + ':' + SHA256(원본 식별값 UTF-8)
I = SHA256(JSON([1, caseId, caseRevision, kind, channel, recipientRole, recipientRef],
                ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
```

해시는 원본 문자열에 적용하며 strip은 부재 판단에만 씁니다. 생성 시각은 키에 포함하지 않습니다. center 원천은 departmentId, owner는 저장된 intake.storeId만이며 상위 store.id로 대체하지 않습니다. counselor의 caseId 해시는 **사람 식별자·배정·연락처가 아닙니다**. owner 원천 부재는 `recipientRef=null/reason=missing_recipient`, 정상 논리 참조는 `delivery_not_configured`입니다. 해시는 인증도 암호화도 아니므로 공개하거나 역산하여 수신 주소를 찾지 않습니다.

현재 outbox는 `schemaVersion, id, caseId, caseRevision, kind, channel, recipientRole, recipientRef, createdAt, status, reason` **11필드**, 정수 schemaVersion=1, status=not_connected만 허용합니다. [검증 코드 L26](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/296cba500808147046ebc4326e44e1ffc70a8629/server/notifications.py#L26). 여기에 queued/providerMessageId 등을 추가하면 기존 저장 검증과 UI 계약이 깨집니다. 후속 전달 상태는 별도 저장소·별도 읽기 모델에 둡니다.

## 3. 공식 공급자 경로와 개통 조건

공식 문서는 2026-09-22 07:13~07:17 KST에 비로그인으로 조회했습니다. 아래는 문서상 가능성과 **설계 선택 제안**이며 현재 계정의 권한·계약·가격을 확인한 결과가 아닙니다.

| 후보 | 공식 조건 / 현재 판단 | 수신·비용·미지원 경계 |
|---|---|---|
| Teams Workflows webhook — 우선 검토 후보 | Teams webhook 트리거와 채팅/채널 게시 action, Workflows 앱 허용, 운영 소유자·공동 소유자·Teams 연결 계정 필요. tenant/team/channel 또는 chat, workflow를 검증된 배포 설정에 고정 | 사용자 소유 flow이므로 소유자 퇴사·연결 만료 책임자 필요. Standard connector라는 사실만으로 전체 운영 무료를 확정할 수 없음. private/shared channel은 실제 템플릿·tenant 조건을 확인 |
| Graph 메시지 API — 대안 | 일반 채널/채팅 send 권한표의 최소 delegated 권한은 ChannelMessage.Send / ChatMessage.Send. 일반 application 표의 Teamwork.Migrate.All은 migration용이며 운영 알림 권한으로 사용하지 않음 | RSC의 ChannelMessage.Send.Group application은 별도 검증 후보. Teams 앱 설치·resource 동의·tenant 정책과 endpoint 지원을 대조해야 함. activity feed·chat·channel 메시지는 서로 다른 기능 |
| Kakao 알림톡 — 경영주 정보성 안내 후보 | 비즈니스 채널, 공식 딜러 계약, 승인된 정보성 템플릿과 적법하게 수집한 대상 전화번호가 필요. 채널 공개·고객센터 정보 등 공식 개설 조건 확인 | 친구가 아닌 대상도 정보성 안내 가능하나 임의 전체 점포 발송 권한은 아님. 딜러별 비용·endpoint·인증·멱등성·상태조회·callback 규격은 딜러 선정 전 미확정. SMS/광고 대체발송 기본 금지 |
| 일반 KakaoTalk Message API — 본 과업의 전체 점포 알림 경로로 채택하지 않음 | 같은 서비스 사용자 간 기능. Kakao Login, talk_message 동의, 사용자 access token 및 친구 발송 사용 권한 등이 필요. 나에게 보내기는 로그인한 자기 자신 | 친구 UUID를 얻어 제한된 대상에게 보내며 전화번호 목록으로 임의 발송하는 API가 아님. 지도 API 키는 메시지 발송 권한·사용자 토큰·알림톡 딜러 인증을 대신하지 않음 |

Teams 근거: [Workflows 설정](https://support.microsoft.com/en-us/workflows/send-messages-in-teams-using-incoming-webhooks), [소유권·연결 제한](https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook), [Graph channel send](https://learn.microsoft.com/en-us/graph/api/channel-post-messages?view=graph-rest-1.0), [Graph chat send](https://learn.microsoft.com/en-us/graph/api/chat-post-messages?view=graph-rest-1.0), [RSC 권한](https://learn.microsoft.com/en-us/microsoftteams/platform/graph-api/rsc/resource-specific-consent).
Kakao 근거: [메시지 상품 구분](https://developers.kakao.com/docs/ko/kakaotalk-message/common), [REST 요청·응답](https://developers.kakao.com/docs/ko/kakaotalk-message/rest-api), [알림톡 개설·딜러·비용](https://kakaobusiness.gitbook.io/main/ad/infotalk), [템플릿 심사](https://kakaobusiness.gitbook.io/main/ad/infotalk/audit).

### 인증·수명·비용

Teams의 옛 Office/Microsoft 365 Connector webhook은 신규 설계에서 제외합니다. [2026-04-14 최종 공지](https://devblogs.microsoft.com/microsoft365dev/retirement-of-office-365-connectors-within-microsoft-teams/)의 종료 일정은 2026-05-18~22입니다. 이를 Workflows의 폐기로 혼동하지 않습니다.

Workflows의 webhook **호출 인증**과 Teams **게시 연결 인증**은 별개입니다. 제한 모드는 Bearer 토큰을 요구하고, 특정 사용자 설정에는 service principal object ID도 사용할 수 있습니다. public cloud audience는 `https://service.flow.microsoft.com/`이며 실제 cloud/issuer/tenant/oid 조건을 검증해야 합니다. 이것으로 사용자 Teams 연결이 app-only가 되는 것은 아닙니다. 본 제안의 호출 모드는 Specific users로 고정하고 Allowed users에 비어 있지 않은 승인된 제품 SPN object ID allowlist를 둡니다. 공식 문서상 Specific users라도 목록이 비면 tenant 전체가 허용되므로, 빈 목록은 설정 오류로 개통을 차단합니다. 같은 tenant의 다른 oid·다른 tenant·잘못된 audience를 거부하는 음성 검증이 필요합니다. Anyone 및 Any user in tenant 모드는 본 제안에서는 사용하지 않습니다. 연결 계정·공동 소유자·DLP·재인증 담당·토큰 회전 절차가 없으면 not_connected를 유지합니다. [트리거 인증](https://learn.microsoft.com/en-us/connectors/teams/#when-a-teams-webhook-request-is-received), [OAuth 조건](https://learn.microsoft.com/en-us/power-automate/oauth-authentication).

Power Automate는 사용자 라이선스 기반 flow이면 운영 소유자 기준을 확인하고, Process 라이선스를 flow에 할당하면 그 권한·한도를 따로 확인합니다. 공유·공동 운영 조건, premium/custom 작업 여부와 요청량도 검토합니다. Kakao는 선정 딜러 견적에서 성공/실패/대체발송 과금 단위와 제한을 확인합니다. 실제 가격·라이선스·예산 미확정은 개통 차단 조건입니다. [라이선스](https://learn.microsoft.com/en-us/power-platform/admin/power-automate-licensing/types), [요청량·FAQ](https://learn.microsoft.com/en-us/power-platform/admin/power-automate-licensing/faqs). 구매·trial·신규 동의는 이번 작업에서 하지 않았습니다.

### 응답을 해석하는 기준

Graph의 `201 + chatMessage`는 생성 증거이며 사람의 읽음 증거가 아닙니다. Workflows의 HTTP 수락만으로 Teams 게시 완료를 확정하지 않습니다. 비동기 `202 + Location` 패턴은 [공식 비동기 설계](https://learn.microsoft.com/en-us/power-automate/guidance/coding-guidelines/asychronous-flow-pattern)의 한 방식이며 모든 webhook 템플릿의 보장이 아닙니다. flow 완료 결과와 게시 action의 [message/conversation ID](https://learn.microsoft.com/en-us/connectors/teams/#posttoconversationresponse)를 인증된 결과 경로로 돌려받도록 **후속 구현에서 설계·검증**해야 합니다. 이 경로가 없으면 `accepted`에서 `posted`로 승격하지 않습니다.

일반 Kakao API의 HTTP 200은 전체 수신자 성공을 뜻하지 않을 수 있습니다. 친구 발송의 successful_receiver_uuids/failure_info를 대상별로 대조해야 합니다. 알림톡은 이 응답 규격을 그대로 적용하지 않고 선정 딜러 규격으로 따로 확정합니다. 공급자 수락·채널 게시/전달·사람 열람·제품 내 확인은 각각 다른 증거입니다. Teams 일반 채널 읽음은 기본 `not_supported`; [개인 bot 읽음 이벤트](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/build-conversational-capability#receive-a-read-receipt)의 한정된 지원을 채널로 일반화하지 않습니다.

## 4. 대상과 상세 링크: 보내기 직전까지 검증

다음 `RecipientBinding` 레지스트리는 **신규 내부 계약 제안**입니다. outbox 원본을 바꾸지 않습니다. tenant, role, canonical 대상, 대상이 접근할 사건 범위, 검증 시각·검증 주체, 활성/철회, mappingVersion을 서버 내부에서 관리합니다. 원문 자유입력에서 전화번호나 URL을 추출해 자동 등록하지 않습니다.

| 논리 대상 | 필요한 권위 있는 연결 | 불충분하면 |
|---|---|---|
| center:department 해시 | 저장 revision 당시 부서 원천 ↔ 검증된 부서 레지스트리 ↔ 허용된 tenant/channel, 채널 구성원의 해당 업무 접근 범위 | 0회 전송; missing_mapping 또는 unauthorized_target |
| counselor:caseId 해시 | 사건 담당 상담원 배정 이력 ↔ 실제 사용자 ID 또는 모든 구성원이 허용된 업무 채팅 | 실제 담당자 모델이 없으므로 현재 0회. caseId를 사용자로 취급 금지 |
| owner:store 해시 | 저장된 점포 식별 원천 ↔ 점포·경영주 권한 ↔ 검증된 채널 수신처 | null·동명이점포·역할 불일치·복수 후보면 0회. 상위 store나 현재 화면 선택으로 보정 금지 |

과거 의도의 center/owner를 현재 사건 필드로 다시 해석하지 않습니다. 저장 시점의 권위 있는 이력 또는 검증된 레지스트리 후보와 원본 그대로의 해시 대조가 필요합니다. 대조 불가 시 발송하지 않습니다. 해시 일치만으로 권한을 인정하지 않고 role/tenant/case scope까지 검사합니다. 발송 직전에 매핑 활성·접근권한을 다시 확인하며, 철회되면 큐를 `failed/authorization_revoked`로 종료합니다. 이미 불명확한 시도는 unknown을 보존하고 결과 대조를 계속합니다.

**최소 메시지 허용 목록:** 서비스명, 외부 공개용 불투명 사건 참조, 해당 event의 종류/상태 고정 문구, 인증된 상세 링크. 원문·욕설·STT·자유입력 회신·점포명·연락처·토큰·recipientRef·내부 caseId는 템플릿 변수로 넘기지 않습니다. 모델이 요약해 준 문장도 자동 채택하지 않습니다. 합성 예: `해피콜 · HC-DEMO-001 · 최종 회신이 등록되었습니다 · 상세 보기`.

링크는 서버가 canonical HTTPS origin allowlist와 공개용 사건 참조로 구성합니다. 사용자 입력 URL·외부 redirect·query bearer·수신 전화번호를 포함하지 않습니다. 경로는 아직 미구현이며 구체 URL을 현재 존재하는 route처럼 제시하지 않습니다. 링크 클릭 때 로그인, tenant, 사건/점포, 역할·현재 접근권한을 다시 검사하고 다른 사건·권한 없음은 본문을 반환하지 않습니다. 링크 미리보기는 사건 본문을 노출하지 않습니다. 잘못된 사건 참조, 불허 origin, 인증된 상세 경로 부재는 **전송 전 0회 차단**입니다. 클릭 시 권한 철회는 열람 차단이며 이미 보낸 메시지를 회수했다고 주장하지 않습니다.

현재 `X-Demo-Role`은 시연 헤더입니다. [handlers.py L73](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/296cba500808147046ebc4326e44e1ffc70a8629/server/handlers.py#L73). NotificationStatus의 역할 필터도 인증·ACL이 아닙니다. 실인증과 상세 조회 권한이 완성되기 전 외부 전달을 켜지 않습니다.

## 5. 원자적 저장과 별도 전달 저장소

### 이미 구현된 저장 경계

[CaseService.patch L142](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/296cba500808147046ebc4326e44e1ffc70a8629/server/service.py#L142)는 역할·expectedRevision·전이·필수값·종결 조건을 검사한 후 같은 transform에서 의도를 추가합니다. [JSON repository L93](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/296cba500808147046ebc4326e44e1ffc70a8629/server/repository.py#L93)는 복사본 변경과 revision 증가 후 flush/fsync·os.replace로 문서를 교체합니다. 저장 전 메모리 이벤트나 HTTP 요청 본문에서 전송하지 않습니다.

[CAS repository L106](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/296cba500808147046ebc4326e44e1ffc70a8629/server/cas_repository.py#L106)는 transform을 한 번 실행합니다. 다른 사건의 문서 충돌은 같은 결과를 재시도하고, 같은 사건이 바뀌면 409입니다. [Blob 쓰기 L269](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/296cba500808147046ebc4326e44e1ffc70a8629/server/vercel_blob_store.py#L269)는 확인된 412/precondition_failed만 CAS 충돌로 취급합니다. timeout은 미저장 확정이 아닙니다. 응답 유실 시 저장된 사건 revision과 I를 다시 조회하며, 이를 보정하려고 별도 의도를 만들거나 임의 발송하지 않습니다.

### 제안하는 Discovery → Delivery → Attempt

1. Discovery는 **다시 읽은 확정 저장 snapshot**의 유효한 의도만 읽습니다. 업무 요청·초안·실패 transform은 읽지 않습니다. 미리 정한 개통 시점/허용 I 목록으로 과거 backlog의 자동 소급 발송을 막습니다. 기존 22건을 GET만으로 이벤트화하지 않습니다.
2. 별도 영속 저장소의 `(environment, I)` unique 키에 단일 `DeliveryEnvelope` 문서를 생성합니다. 이는 guard와 현재 작업·시도 이력을 논리적으로 구분하되 같은 원자적 CAS로 갱신하는 aggregate 제안입니다. 처음에는 reservation=unresolved, activeD=null, not_connected이며 재스캔은 이 행을 중복 완료로 버리지 않고 미해결 예약으로 처리합니다. 검증된 단일 RecipientBinding이 생기면 **D 생성·payload 고정·activeD 연결·reservation=ready를 한 CAS**로 저장합니다. CAS 전에 죽으면 unresolved, 성공 후 응답 유실이면 다시 읽어 ready를 확인합니다. 1단계 한 의도당 실제 대상 하나이며 다중 broadcast는 별도 계약입니다. 불일치/유출은 failed, 채널별 대상이 다르면 원래 I도 다릅니다.
3. 전달 키 `D = SHA256(canonical JSON([deliverySchemaVersion=1, environment, I, channel, stableRecipientBindingId]))`. binding ID는 주소·credential 회전마다 새로 만들지 않습니다. mappingVersion·payloadHash·createdAt은 키에 넣지 않습니다. 대상 변경이 새로운 D를 자동 생성하지 않도록 `(environment,I)` guard도 반드시 함께 사용합니다.
4. 작업 필드 제안: D, I, caseId, eventRevision, channel, role, bindingId, mappingVersion, destinationDigest, templateVersion, payloadHash, state, reasonCode, deliveryRevision, createdAt, updatedAt. 실제 목적지·credential은 접근 제한된 별도 매핑/secret 참조에서 가져오며 UI·로그·Git에는 남기지 않습니다. immutable payload snapshot에는 허용 목록만 둡니다.
5. 각 시도는 attemptId, D, sequence, lease/fencing token, startedAt, finishedAt, outcome, providerRequestId/messageId(있을 때), sanitized errorCode, nextAttemptAt, evidenceRef를 논리적으로 별도 보존합니다. Envelope 내부의 현재 D·시도 이력·lease·deliveryRevision은 같은 원자적 CAS로 갱신합니다. 여러 문서에 분리하는 구현은 동일 불변식을 보장하는 transaction 없이는 허용하지 않습니다. 업무 revision/history와 closed 잠금을 건드리지 않습니다.
6. Discovery 중단은 같은 I를 재스캔해 복구합니다. unresolved는 매핑 해결을 재시도하고 ready는 activeD를 재사용합니다. 무응답 CAS도 재조회로 승패를 확인합니다. unique insert가 재실행되어도 Envelope는 하나입니다. 업무 저장과 별도 queue 사이 분산 transaction을 가정하지 않으며 실제 저장소의 durable unique insert/원자적 CAS는 구현 게이트입니다.
7. Worker는 activeD와 mappingVersion이 여전히 맞는지 검증하여 queued→in_flight를 lease+CAS로 단독 점유하고 **시도 기록을 먼저 영속 저장**한 뒤 네트워크를 호출합니다. 두 worker가 잡으면 승자만 호출합니다. transport·SDK·flow 내부의 숨은 자동 재시도도 통제 대상입니다.
8. in_flight에서 프로세스가 죽거나 lease가 끝나면 unknown으로 바꿉니다. 전송하지 않았다는 증거가 없는 한 새 worker가 다시 보내지 않습니다. 이전 worker는 호출 직전에 lease를 확인하고 유효하지 않으면 호출을 중단합니다. 이 확인 직후 정지되는 분산 경계까지 fencing만으로 원격 부작용을 취소할 수는 없으므로, 옛 worker가 뒤늦게 호출할 가능성이 제거되기 전 재시도하지 않습니다. 지연 결과는 같은 attempt에 대한 증거만 대조하고, 만료 token으로 상태를 직접 덮거나 신규 dispatch하지 않습니다.
9. 설정/주소가 바뀌어도 과거 payload·대상은 몰래 재해석하지 않습니다. 같은 binding의 설정 교정은 전송 시도 0회일 때만 재검토합니다. 다른 bindingId로 교체하려면 명시적 재배정 결정 후 한 Envelope CAS에서 시도 0회·lease 없음·기대 activeD를 검사하고, oldD를 failed/binding_superseded로 보존하면서 새 D와 activeD를 교체합니다. oldD를 가진 worker의 이후 점유는 실패해야 합니다. 어느 시도든 이미 있으면 이 교체 경로를 막습니다. unknown/accepted 작업의 새 주소 재발송·과거 소급 발송은 자동 수행하지 않습니다.

### 전달 상태와 화면 문구 — 신규 projection 전용

| 내부 상태 | 사용자 문구 / 증거 | 가능한 다음 상태 |
|---|---|---|
| not_connected | 연결 안 됨 · 매핑/권한/템플릿/라이선스/링크/개통 승인 중 미완료 | 검증 후 queued 또는 failed |
| queued | 발송 대기 · 저장된 작업이며 아직 전송 아님 | in_flight, failed |
| in_flight | 발송 결과 확인 중 · 시도 기록만 존재 | accepted, posted, delivered, unknown, failed, 확정 거부 후 queued |
| accepted | 공급자 접수 확인 · 최종 게시/전달·열람은 미확인 | posted/delivered, 확인된 최종 실패로 failed |
| posted / delivered | Teams 게시 확인 / 공급자 전달 확인 · 대응하는 ID와 신뢰 가능한 결과 증거 필요 | 읽음 상태와 별개. 중복/낡은 callback으로 하향하지 않음 |
| unknown | 발송 여부 확인 필요 · 성공/실패 미확정, 자동 재발송 보류 | 같은 시도의 결과 대조 후 accepted/posted/delivered/failed |
| failed | 발송 불가 또는 실패 · reasonCode와 확인된 사유 | 설정 오류 교정/확정 미수락만 검토 후 queued; 이미 성공한 대상은 재시도하지 않음 |

`readState=unknown/not_supported/confirmed`는 별도입니다. confirmed는 정확한 사용자·메시지의 지원되는 읽음 증거가 있을 때만 씁니다. 버튼 클릭이나 웹페이지 조회를 채널 읽음으로 간주하지 않습니다. 현 NotificationStatus는 이 상태들을 아직 받지 않으므로 pc1이 별도 인증된 projection/API·표시 계약을 구현하고 기존 outbox 표시와 구분해야 합니다.

## 6. 실패·재시도·결과 대조

- **429:** 문서상 확정 미수락이면 Retry-After를 먼저 따릅니다. 없으면 bounded exponential backoff+jitter. 초기 제안 한 작업 최대 3회 시도, 최대 30분, 예산 상한 우선. 값은 fake 검증 후 운영 설정으로 고정합니다. 큐 적체가 업무 저장을 롤백하지 않습니다.
- **5xx/네트워크 timeout:** 전송 후의 오류는 보수적으로 unknown. HTTP 실패만으로 수신 측 미처리를 단정하지 않습니다. 공급자 조회 등 신뢰 가능한 증거가 미수락을 확정하고 옛 시도의 지연 dispatch 가능성이 제거된 경우에만 failed/confirmed_not_accepted로 옮긴 뒤 검토하여 queued로 재개합니다. 같은 D·같은 목적지·같은 payload에 새 attemptId/sequence를 부여합니다. 이번 조사에서 채택 경로의 provider 멱등 보장을 확보하지 않았으므로, 멱등키가 있다는 주장만으로 unknown→queued를 허용하지 않습니다. 향후 그 예외는 공급자별 유효기간·같은 키/본문·대상 범위의 검증과 계약 개정이 필요합니다. SDK의 자동 POST 재시도는 기본 비활성화합니다.
- **Teams 중첩 재시도:** flow 게시 action 자체의 재시도와 애플리케이션 재시도를 겹치지 않습니다. 실제 flow에서 action retry/중복 trigger를 통제·검증할 수 없으면 개통하지 않습니다. 내부 unique key만으로 원격 exactly-once를 보장할 수 없습니다.
- **401/403·템플릿/주소 거부:** 재인증·설정 검토로 보내고 반복 발송하지 않습니다. 임의 새 계정·권한·채널·SMS 대체를 시도하지 않습니다.
- **대조:** provider별 request/message ID 또는 보증된 correlation key로 같은 I/D/attempt/대상을 식별합니다. callback 서명·issuer·tenant·timestamp/replay·허용 상태전이를 확인하고, 실패한 검증은 반영하지 않습니다. 규격이 없으면 인증된 운영자 수동 대조를 기다립니다. 임의 POST의 sent 주장은 증거가 아닙니다.
- **조회 불가:** unknown을 유지합니다. 수신이 없었다는 단순 관찰만으로 미발송을 확정하지 않습니다. 사람의 재전송 결정이 필요하면 중복 가능성·원래 시도·대상을 명시한 별도 감사 기록을 남깁니다. 자동 resend 버튼을 일반 업무 화면에 추가하지 않습니다.
- **rate/cost:** Workflows 성능 프로필, Teams connector 연결 제한, Graph tenant/app/대상별 제한, 딜러 계약 중 적용되는 최저 한도를 따릅니다. 연결별 queue와 예산 차단을 둡니다. 기존 webhook의 초당 4회를 모든 경로에 적용하지 않습니다. 수신자 한 명 실패가 최종회신의 다른 채널 재발송을 유발하지 않습니다.

근거: [Graph 429](https://learn.microsoft.com/en-us/graph/throttling), [Graph 오류 처리](https://learn.microsoft.com/en-us/graph/best-practices-concept#handling-expected-errors), [Flow 재시도](https://learn.microsoft.com/en-us/power-automate/limits-and-config#retry-policy), [Teams connector 제한](https://learn.microsoft.com/en-us/connectors/teams/#throttling-limits), [Graph Teams 제한](https://learn.microsoft.com/en-us/graph/throttling-limits#microsoft-teams-service-limits). 공급자의 재시도 권고와 애플리케이션의 중복 방지 정책을 구분하며, 지원이 확인되지 않은 idempotency header를 발명하지 않습니다.

## 7. 검증 계약 — 아래 시나리오는 모두 미실행

테스트 전제는 SYN-* 사건, 합성 recipient 레지스트리, 임시 영속 저장소, 외부 네트워크를 차단한 FakeTransport입니다. N=새 업무 의도 수, A=fake transport 호출 수, S=fake가 기록한 수락 수입니다. 실제 외부 전송/수신은 모든 행 0입니다. 현재 구현에 없는 worker 검사를 통과한 것으로 쓰지 않습니다.

| ID | 입력·재현 조건 | 기대 N / A / S | 기대 상태·대조 |
|---|---|---|---|
| D01 | 정상 이관, 매핑·인증 링크·개통 gate 충족 | 1 / 1 / 1 | Teams 채널 게시 결과가 있으면 posted; 읽음 not_supported |
| D02 | 같은 저장에서 회신 변경+closed | 2 / 2 / 2 | counselor Teams와 owner Kakao 별도; interim 없음 |
| D03 | replace 전 확정 저장 실패 | 0 / 0 / 0 | 업무/의도 불변; delivery 없음 |
| D04 | 같은 사건 expectedRevision 충돌 | 0 / 0 / 0 | 409; 낡은 입력을 최신 revision으로 강제 재발송하지 않음 |
| D05 | 다른 사건 CAS 충돌 후 성공 | 1 / 1 / 1 | transform1회, 저장 의도1, discovery 중복0 |
| D06 | 같은 I 재스캔·같은 revision 요청 중복 | 최초 1 이후 0 / 총1 / 총1 | unique guard1; 업무 재요청은409; timestamp 변경으로 새 키 금지 |
| D07 | 두 사건/두 수신자 각각 정상 이관 | 2 / 2 / 2 | I/D/대상/링크 분리, 한 대상 성공이 다른 대상 성공 아님 |
| D08 | 최종회신 owner의 intake.storeId 누락 | 2 / 1 / 1 | Teams만 posted, owner not_connected/missing_recipient; store fallback0 |
| D09a | 최종회신, counselor 매핑 없음·owner 정상 | 2 / 1 / 1 | counselor not_connected; owner delivered. caseId를 상담원 ID로 전송0 |
| D09b | 최종회신, owner 매핑 없음·counselor 정상 | 2 / 1 / 1 | owner not_connected; counselor posted |
| D09c | 최종회신, 양쪽 실제 매핑 없음 | 2 / 0 / 0 | 두 대상 not_connected |
| D10 | 이관 대상 role/tenant/case scope 불일치 | 1 / 0 / 0 | failed/unauthorized_target; 원래 의도 보존 |
| D11 | 자유입력 원문·욕설·전화·키 sentinel을 payload에 주입 | 1 / 0 / 0 | failed/payload_rejected; 에러에도 sentinel 노출0 |
| D12 | 다른 case 링크·임의 origin 또는 인증 상세 route 미구현 | 1 / 0 / 0 | failed/link_mismatch 또는 not_connected/link_not_ready |
| D13 | 확정 미수락429 1회, Retry-After 이후 성공 | 1 / 총2 / 총1 | queued 대기→posted; 대기 이전 재호출0 |
| D14 | 전송 후500, 수락 여부 조회 불가 | 1 / 1 / 0 또는1(oracle만 앎) | unknown; 앱은 S 추정 금지, 자동 재호출0 |
| D15 | 원격 수락 직후 timeout | 1 / 1 / 1(oracle만 앎) | unknown→신뢰 결과 대조 후 posted; 추가 호출0 |
| D16 | 중간 reply 저장 후 별도 종결 | 1+2 / 3 / 3 | 중간 Teams1, 최종 Teams+Kakao2; 의미 다른 event를 중복으로 합치지 않음 |
| D17 | 기존 의도는 처리 완료 또는 개통 제외; 같은 reply 재저장·조치만 수정·GET | 0 / 새0 / 새0 | 새 의도 없음; 기존 기록 그대로. 미처리 기존 의도의 정상 discovery는 이 검사에서 제외 |
| D18 | 업무 저장 성공 후 응답 유실 | 1 / 총1 / 총1 | GET의 저장 revision/I로 대조; UI 오류가 의도 삭제·중복 생성 아님 |
| D19a | 시도 기록 후 호출 직전 종료, 옛 worker 종료 확인 | 1 / 0 / 0 | lease 만료→unknown; 미호출 증거 대조 전 신규 호출0 |
| D19b | 호출 후 미수락, 결과 기록 전 종료 | 1 / 1 / 0 | unknown; 확정 미수락 대조 전 신규 호출0 |
| D19c | 원격 수락 후 결과 기록 전 종료 | 1 / 1 / 1 | unknown; 지연 정상 결과로 posted, 신규 호출0 |
| D20 | 두 worker 동시 점유 | 1 / 1 / 1 | unique insert+CAS lease 승자 하나; 패자 호출0 |
| D21 | 위조/재생/다른 대상 callback, 정상 callback 중복 | 1 / 총1 / 총1 | 위조·다른 대상 상태변경0; 정상 중복은 멱등, posted 하향0 |
| D22 | Teams webhook HTTP202만 반환 | 1 / 1 / 1(수락) | accepted; 게시·전달·읽음 확인으로 표시0 |
| D23 | 미래 revision·다른 caseId·불허 필드의 저장 의도 | 불량 입력 / 0 / 0 | 검증 거부; 원시 내용 노출0; client 주입도거부 |
| D24 | queued 이후 권한 철회 또는 주소 변경 | 1 / 0 / 0 | 철회 failed; 주소 변경은 자동 새 D 생성0, 재검토 |
| D25 | 개통 전 과거 의도·legacy 22건 재조회 | 새0 / 0 / 0 | 자동 backlog 전송0; 승인 replay 목록 없는 과거 의도 보류 |
| D26 | Teams 성공·Kakao 확정 실패 | 2 / 총2 / 1 | Teams posted 유지; Kakao만 failed, Teams 재시도0 |
| D27 | unresolved Envelope 생성 후 중단; 매핑 등록 후 재스캔 | 1 / 총1 / 총1 | 같은 Envelope를 ready로 완성, activeD1; 영구 누락0 |
| D28 | D/activeD CAS 성공 후 응답 유실; 재스캔 두 번 | 1 / 총1 / 총1 | 재조회로 동일 activeD 재사용, reservation/D 분리 쓰기0 |
| D29 | 시도0 oldD를 명시 재배정한 직후 old worker 점유 | 1 / 새D만1 / 1 | oldD 점유 실패, activeD 하나; 중복 dispatch0 |
| D30 | Workflow Specific users의 Allowed users 빈 목록 | 1 / 0 / 0 | 개통 차단 not_connected/auth_configuration_invalid |
| D31 | 개통 전 인증 음성검사: 다른 oid·tenant·audience | 별도 합성 요청 / 각 거부 / Teams 게시0 | 제품 SPN 외 호출 차단. fake 단계는 외부 요청0, 실제 tenant 검증은 별도 gate |

표는 D01~D31의 31개 검사군, D09/D19의 하위 입력을 포함한 35개 행입니다. 모두 설계이며 실행하지 않았습니다. 실제 외부 수신 검증은 별도 gate입니다. 양쪽 합성/동의 대상의 provider ID·시각·사건·템플릿·수신 확인을 대조하고 원문·연락처·URL 비밀은 보고서에 넣지 않습니다. 이를 수행하기 전 “Teams/카카오 연동 완료”로 표시하지 않습니다.

## 8. BMAD·작은 Bolt·인계 순서

| 관점 | 이번 결정 | 후속 수용 기준 |
|---|---|---|
| 업무 | 확정 저장 사건과 실제 전달·열람을 분리 | 저장 실패 전송0, 대상별 독립 결과 |
| UX | 기존 경영주/상담원/센터 3역할 흐름과 사건 내부 WMS/TMS 유지 | 알림 상태 때문에 업무 성공을 바꾸지 않음; 연결 안 됨/확인 필요를 읽을 수 있음 |
| 구조 | immutable Case outbox + 별도 delivery/attempt + 인증된 binding·링크 | 영속 unique/CAS, 응답 유실 대조, 권한 없는 대상0 |
| 검증 | D01~D31를 fake로 먼저 수행하고 외부 검증과 분리 | 실제 입력·기대/실측·FAIL/SKIP·수정·같은 조건 재시험 기록 |

첫 Bolt의 병목은 **commit 전 dispatch 또는 discovery 재실행으로 발생하는 거짓/중복 발송**입니다. 후속 담당자는 임시 저장소와 fake transport만으로 D01(양성), D03(실패0), D06(동일사건1), D07(다른대상분리)을 실행합니다. 잘못된 대조군은 commit 전에 dispatch하도록 한 변이 하나이며 D03이 검출해야 합니다. 이 한 경계만 수정한 뒤 같은 네 입력으로 재시험합니다. 이어 D15/D19의 응답 유실을 독립 단위로 확장합니다. **이번 D2에서는 Bolt를 실행하지 않았으며 사람 Silent Test도 하지 않았습니다.**

메인이 인수할 순서:

1. 이 두 문서의 설계 검토와 미결정 목록 확인. 기존 11필드 outbox 및 accepted U1 파일 유지.
2. 추가확인 요청 모델은 별도 카드로 결정. 현재 3종 사건만 대상으로 합성 binding·링크·delivery 저장소·FakeTransport 구현 카드 배정.
3. D01~D31와 변이 검사 후 독립 검증. 테스트 저장소·네트워크 차단·정확한 기준 SHA를 기록.
4. 실제 tenant·운영 소유자·recipient 매핑·인증 조회·딜러/템플릿·권한·가격/예산·결과 대조 규격을 확인. 하나라도 미확정이면 not_connected 유지.
5. 별도 허용된 최소 외부 전송으로 수락/게시/전달을 대조. 전달 실패·unknown 복구와 비용 한도를 검증한 뒤 운영 개통 판단.

현재 미결정은 Teams tenant/cloud·관리 정책·연결 계정·수신 위치·라이선스·flow 결과 대조 경로, Kakao 딜러·채널·승인 템플릿·대상 동의/수집 근거·단가·조회/callback, 실제 담당자 이력·인증 링크·delivery 저장소입니다. 이 문서 작성이나 지도 키 존재가 이 항목들을 해결하지 않습니다. 메인 인수 전 N04 전체 완료로 올리지 않습니다.
