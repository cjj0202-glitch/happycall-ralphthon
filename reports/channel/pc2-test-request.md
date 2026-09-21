## 결론
pc2 편지함 왕복을 확인해 주세요. 테스트 문구: MAILTEST-pc2-20260921-42e03be

## 왜 지금
등록 커밋42e03be를 공유했습니다. 실제 hostname=안영일, GitHub=MR-A83입니다. 킷 read 초대를 발송했으므로 본인 계정으로 수락 후 preflight를 재검사하세요. 최신 P0·Goal 정합본을 확인하기 전 제품 수정은 배정하지 않습니다.

## 해줘야 할 일
- [ ] 등록표를 안전하게 받고 신원 일치 확인
- [ ] 킷 초대 수락과 접근 확인
- [ ] 자기 TEST 문구 수신·같은 이슈 회신
- [ ] 30초 감시·중복방지·snapshot 확인

## 실행 명령
작업 폴더: C:\Users\Administrator\Desktop\hackerton\happycall-ralphthon
등록표 변경과 로컬 변경을 검토한 뒤 안전하게 현재 main을 받습니다. 그 다음 실행합니다.
```powershell
python channel/whoami.py
gh api user --jq .login
python scripts/preflight.py
python scripts/mailbox_watch.py check
python channel/mail.py inbox
python scripts/mailbox_watch.py once
python scripts/mailbox_watch.py start
```

## 검증 방법 + 기대값
테스트 문구 MAILTEST-pc2-20260921-42e03be, 슬롯 pc2, 실제 hostname 안영일, GitHub MR-A83, HEAD, 실제 절대경로, 수신KST, 실행 명령, preflight, 감시PID/기동시각/snapshot을 같은 이슈에 회신합니다. 기대는 자기 TEST1건 수신과 동일문구 회신입니다. 메인이 회신자·등록값·HEAD를 대조해 종결합니다. 종결 확인 후 추가변화 없는 watch --once가 출력0인지 검사합니다.

## 중단 조건
신원 불일치·충돌·권한 오류이면 관측 결과만 회신하세요. 다른PC 슬롯강제·키공유·권한우회·강제초기화는 하지 않습니다. 워커가 이슈를 닫거나 다른워커에게 지시하지 않습니다.
