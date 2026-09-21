# 팀원 계정과 PC 등록 확인

## 추가 확인 — 2026-09-21 17:01 KST

사용자가 실제 준비보고를 전달했습니다. pc3의 원격 e3149cc 변경만 안전하게 fast-forward로 받고 기존 등록을 보존했습니다. 42e03bef0495b94aa69553a6351429fd5dcff075를 push하고 원격 main 해시 일치를 확인했습니다.

| 슬롯 | 사용자 보고 hostname | 계정 | 배정 역할(제품작업 미배정) |
|---|---|---|---|
| pc2 | 안영일 | MR-A83 | 접수·경영주·센터 UX 검토 |
| pc3 | LAPTOP-U2AL73UH | mcjun86-oss | WMS/TMS 정합 검토, 정준화 |
| pc4 | 장준호 | j324rst-svg | 독립 시연·경계 QA |

킷은 기존 협업자 cjj0202-glitch1명·대기초대0건을 확인한 후 세 계정에 read 초대를 발송했습니다. invitation id는 MR-A83=333954794, j324rst-svg=333954798, mcjun86-oss=333954802입니다. 초대수락·해당PC 접근은 별도 확인합니다.

TEST 자동발송 명령은 자동승인검토의 blocked by policy로 거부되어 발송하지 않았습니다. docs/23과 reports/channel/*-test-request.md에 본문·수동명령을 준비했습니다. 원격PC 준비완료·왕복완료·제품배정으로 확대하지 않습니다. 아래는 최초 관측 기록입니다.

## 최초 확인 기록

확인: 2026-09-21 15:59~16:00 KST, 메인 CJJ / pc1. R01은 미완료다.

사용자가 전달한 계정 세 개를 GitHub의 실제 협업자 목록과 대조했다. 사용자는 초대를 이미 보냈다고 알렸다. 이번 세션에서 중복 초대를 발송하지 않았다.

| GitHub 계정 | happycall-ralphthon 실제 권한 | 초대 상태 | hostname / 슬롯 / 역할 |
|---|---|---|---|
| MR-A83 | write | 협업자 등록 확인 | 미확인 / 미배정 / 미확인 |
| j324rst-svg | write | 협업자 등록 확인 | 미확인 / 미배정 / 미확인 |
| mcjun86-oss | write | 협업자 등록 확인 | 미확인 / 미배정 / 미확인 |

검증 명령:

```text
gh api repos/cjj0202-glitch/happycall-ralphthon/invitations --paginate --jq '.[] | {id, login: .invitee.login, permissions}'
gh api repos/cjj0202-glitch/happycall-ralphthon/collaborators --paginate --jq '.[] | {login, role_name}'
```

대기 초대 출력은 0건이며, 협업자 응답에는 관리자 cjj0202-glitch와 위 세 계정의 write 권한이 있었다. 계정 등록은 확인했지만 각 PC에서 두 private 저장소를 실제로 읽고 쓸 수 있는지는 검증하지 않았다.

다음 단계는 docs/14의 [PC 준비 보고]에서 실제 hostname·GitHub·희망 역할·두 저장소 경로/HEAD를 받는 것이다. 보고를 대조한 뒤 channel/pcs.json에 슬롯을 등록하고 공유한다. 계정 나열 순서만으로 pc2~4를 배정하지 않는다. 이후 docs/17에 따라 실제 등록 PC마다 TEST 한 건의 수신·회신·검증·종결·무변화 감시를 확인한다.

현재 channel/pcs.json의 pc2~4와 TODO 완료 표시는 변경하지 않았다. hackathon-ai-kit 접근, PC 준비, 편지함 왕복은 미확인이다.
