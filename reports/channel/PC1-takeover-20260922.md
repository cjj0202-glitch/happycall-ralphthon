# pc1 메인 인수 — 기존 #8/#9/#10에서 업무를 이어갑니다

## 왜 지금

2026-09-22 06:33 KST, 사용자가 기존 메인 CJJ의 전원 중단을 알리고 현재 PC의 메인 인수와 계속 진행을 직접 지시했습니다. 새 pc1 hostname은 `최제준`, GitHub는 기존 `cjj0202-glitch`입니다. API 사용자와 저장소 ADMIN 접근을 확인했습니다. 인수 커밋 `296cba500808147046ebc4326e44e1ffc70a8629`은 main push 및 원격 SHA 대조를 마쳤습니다. 결정 정본은 `planning/decisions.md` DEC-025입니다.

## 해줘야 할 일

- 먼저 `python channel/whoami.py --oneline`과 `gh api user --jq .login`을 확인하십시오. 본인 등록 hostname/계정이 pc2 `안영일/MR-A83`, pc3 `LAPTOP-U2AL73UH/mcjun86-oss`, pc4 `장준호/j324rst-svg` 중 자신의 이슈 담당과 다르면 작업을 중단하고 신원 출력만 회신하십시오.
- 기존 branch·미커밋·실행 상태·소유 경로를 보존하고, 본인 이슈에서 이 인수의 수신과 현재 HEAD·실행 중인 카드·미공유 결과 유무를 한 번 회신하십시오. 기존 main CJJ의 종료 전 미커밋을 복구했다고 가정하지 않습니다.
- pc2: N02-R1 결과 `af288becf6e53261c242d8afae3336718b37250b`와 두 파일을 수신했습니다. 메인이 독립 입력 검증과 공통 서버 구현을 진행합니다. 기존 두 파일과 원검증 증거를 보존하며 공통 server 파일은 계속 pc1 소유입니다. 제품 후보가 고정되면 같은 이슈로 독립 검증을 요청합니다.
- pc3: 인수한 v4 합성 미디어와 N03-L1 로컬 보존 결과를 유지하십시오. 새 pc1은 Release v4의 4파일을 다운로드하고 manifest SHA/크기 4/4를 확인했습니다. 진행 중이거나 아직 공유하지 못한 결과만 회신하십시오. 새 렌더 배정이 아닙니다.
- pc4: 기존 N04-D2의 `planning/notification-delivery-contract.md`, `reports/pc4/notification-design-review.md` 소유를 유지합니다. ACK나 결과가 준비됐으면 같은 이슈로 전달하십시오. 실제 공급자 발송은 구현/검증된 것으로 처리하지 않습니다.

## 실행 명령

각자의 기존 checkout에서 실행하며 다른 PC 절대경로를 사용하지 않습니다.

```text
python channel/whoami.py --oneline
gh api user --jq .login
git status --short
git rev-parse HEAD
git fetch origin
git show 296cba500808147046ebc4326e44e1ffc70a8629:planning/decisions.md
```

자동 pull/merge나 남의 변경 stash/reset 없이 인수 문서를 먼저 읽습니다. 이전 CJJ가 다시 실행되면 새 pc1과 인계하기 전 main에 동시에 쓰지 않습니다.

## 검증 방법 + 기대값

슬롯/계정/현재 HEAD/배정 카드/소유 파일을 실제 관측으로 한 번 회신합니다. 전달 성공과 ACK·착수·결과·인수는 별개입니다. 동일 최종 빌드 전체 검증은 아직 미완료입니다.

## 중단 조건 + 인계

소유 충돌·권한 거부·비밀 공개·예산 미확인은 해당 동작을 멈추고 독립 가능한 검증만 이어갑니다. 이전 pc1의 `.local` 원장·원본 로그·키는 GitHub에 올리지 않습니다. 새 pc1은 이전 예산 원장이 없으므로 live 호출을 시작하지 않으며, 이번 인수는 예산을 새로 만드는 승인이 아닙니다. 현재 원격 배포의 저장소 오류와 실제 알림 연결 미완료도 보존합니다. 기존 09시 인계 목표를 유지합니다.
