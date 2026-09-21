# 등록 PC의 TEST 발송 대기

2026-09-21 pc1. 등록42e03be와 킷read 초대3건은 실제 반영했습니다. TEST 자동발송 명령은 자동승인검토에서 blocked by policy로 거부되어 실행하지 않았습니다. 아래는 **수동 발송용 준비본이며 아직 이슈가 생성되지 않았습니다.** 같은 TEST가 이미 있으면 중복 생성하지 말고 재사용합니다.

메인 pc1의 현재 happycall-ralphthon 작업폴더에서 본문을 검토한 뒤 실행할 명령입니다.

```powershell
python channel/mail.py send --to pc2 --type A --title "[TEST] pc2 안영일 왕복 확인" --body-file reports/channel/pc2-test-request.md
python channel/mail.py send --to pc3 --type A --title "[TEST] pc3 정준화 왕복 확인" --body-file reports/channel/pc3-test-request.md
python channel/mail.py send --to pc4 --type A --title "[TEST] pc4 장준호 왕복 확인" --body-file reports/channel/pc4-test-request.md
```

본문: [pc2](../reports/channel/pc2-test-request.md) · [pc3](../reports/channel/pc3-test-request.md) · [pc4](../reports/channel/pc4-test-request.md).
회신 검증과 종결은 [docs17](17_편지함_왕복테스트.md)을 따릅니다. 발송 성공만으로 수신·왕복 완료를 체크하지 않습니다.
