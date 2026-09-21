# N04-D3 — 알림 전달 초안의 무과금 첫 검증

2026-09-22 07:39 KST, pc1 최제준/cjj0202-glitch → pc4 장준호/j324rst-svg.

사용자 목표는 09:00 KST까지 검토 가능한 초안입니다. N04-D2의 두 문서는 설계 한정 인수합니다. 메인 독립 검토는 `reports/pc4-d2-main-intake.md`이며 실행0/31(35행), 실제 전송0을 유지합니다.

## 고정 기준과 소유권

- 기준 `f043c60b357c5341e80959c748036b28d032bd18`; 알림 관련10파일은 D2 기준296cba5와 동일합니다. 설계는 본인 commit `535e2f218725daefcf4b447831fef07497c0d2e6`의 두 파일을 사용합니다.
- PC4 기존 작업 브랜치에서 수행. 허용 새 파일은 `server/notification_delivery.py`, `tests/test_notification_delivery.py`, `reports/pc4/notification-first-bolt.md` 3개뿐입니다. 기존 API/service/outbox11필드/UI/빌드목록은 수정하지 않습니다. 메인이 검증 후 명시 경로로 인수합니다.
- 런타임 연결 없는 전달 조정 모듈의 첫 초안입니다. 기존 실제 의도를 읽어 발송하거나 실제 주소/키/원장/프로세스를 변경하지 않습니다. 임시 저장소·FakeTransport·합성 binding만 사용하고 네트워크는 0입니다.

## 이번 범위와 사전 기대값

설계 §8의 D01/D03/D06/D07 4조건만 구현·검증합니다. 기존에 저장된 유효 immutable intent를 입력으로 하고, 아직 commit되지 않았거나 저장 실패한 사건은 transport 호출0입니다. 같은 intent의 재탐색은 중복 delivery/전송을 만들지 않으며 다른 recipient/channel은 별도 결과를 갖습니다. dispatch 전에 identity, 저장 성공, active delivery 경계를 명시합니다. 원문이나 비밀을 결과에 담지 않습니다.

commit 전에 dispatch하도록 잘못 바꾼 대조군을 동일 D03이 검출해야 합니다. 성공 횟수만 늘리지 말고 입력/기대/실측·실패→수정→같은 입력 재시험, 소스 SHA, 정확한 명령을 남기십시오. 메모리 fake의 결과를 영속 CAS·재시작 안전·실제 provider 성공으로 표시하지 않습니다. D15/D19와 나머지27검사군은 미실행으로 유지합니다.

## 인계

08:10 KST까지 첫 결과 또는 구체적 차단을 기존 #10에 한 번 회신하고, 가능하면 3파일만 commit/push 후 원격 SHA를 검증하십시오. 메인 요청 없이 범위를 추가하지 않습니다. 추가확인 사건/실제 Teams·Kakao/과금/생산 연결은 금지하며 09:00 이후 새 구현·배정은 중단합니다. 마지막 원장29.20/30달러를 보존합니다.
