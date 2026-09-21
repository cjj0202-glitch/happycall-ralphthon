# 편지함 감시 준비 검증

> 아래는 작성 시점의 역사적 관측입니다. 현재 등록·Goal·배포 상태는 CURRENT_TODO.md와 planning/decisions.md의 후속 결정을 따릅니다.

작성: 2026-09-21 16:48 KST / 대기세션2 / 대상: CJJ의 pc1 및 다른 실제 PC에 전달할 실행 패키지.

## 결론

Python 런처와 다른 PC용 복붙 프롬프트를 준비했고 CJJ pc1에서 30초 숨김 감시를 실행했습니다. 원격 pc2~4는 미등록이며 실제 기동·TEST 왕복을 검증하지 않았습니다. 대기세션1~4는 모두 CJJ의 세션이며 원격 PC 슬롯이 아닙니다. GitHub 커밋·push는 메인이 수행합니다.

## 파일

- `scripts/mailbox_watch.py`: 주 실행 경로. start/check/status/stop/once/foreground, hostname 유일 등록과 GitHub/inbox 일치, RALPH_PC 차단, hidden 실행, 잠금, PID·생성시각·실행파일·정확한 명령 검증.
- `scripts/start_mailbox_watch.ps1`, `scripts/stop_mailbox_watch.ps1`: 같은 Python 런처의 선택 래퍼.
- `docs/19_4PC_편지함_감시_빠른시작.md`: 다른 PC용 복붙 프롬프트, clone/안전 수동 업데이트, 등록 요청, 로그/재시작, docs17 왕복 연결.
- `tests/test_watch_launcher.py`: 신원·프로세스·잠금·실제 잘못된 PID 거부 검사.

## 실측

| 항목 | 기대 | CJJ pc1 실측 |
|---|---|---|
| 등록 | hostname/slot/GitHub 일치 | CJJ / pc1 / cjj0202-glitch |
| 열린 편지 최초 확인 | 자기 편지함 조회 | `python channel/mail.py inbox`: 열린 편지 없음 |
| Check | 자기 등록 검증 | `READY slot=pc1`, 최초 watchers=0 |
| Once | 1회 성공 | `python scripts/mailbox_watch.py once` 성공, 변화 알림 없음 |
| Background | 실제 프로세스 1개 | 최초 PID 5484, 30초 |
| 중복 시작 | 기존 PID 유지 | `ALREADY_RUNNING process_id=5484` |
| 중지·재시작 | 정확 대상만 중지, 새 PID | 5484 중지 → PID 9744 재시작 |
| 생존·신원 | state만 보지 않고 실제 process 대조 | `watchers=1 verified_process=True process_id=9744` |
| 기동 시각 | 현재 기동 기록 | 2026-09-21T07:47:02.782165+00:00 |
| 실제 폴링 | snapshot 후속 갱신 | `.mailbox_state.pc1.json` 606 bytes, 16:47:04 → 16:47:37 KST |
| 무변화 로그 | 불필요 반복 출력 없음 | stdout 385 bytes, 시작 3줄; stderr 0 bytes (16:47:37 관측) |

PowerShell 5의 직접 `.ps1` 실행은 이 PC 실행 정책에서 거부됐습니다. 정책을 변경하지 않았으며 메인 지시에 따라 Python 주경로로 검증했습니다. PowerShell 래퍼는 실제 실행 완료로 주장하지 않습니다. Python은 프로세스 정보를 읽을 때만 PowerShell CIM 조회를 사용하며 실행 정책을 변경하거나 `.ps1`을 우회 실행하지 않습니다.

## 검증 명령과 한계

```powershell
python -m unittest discover -s tests -p 'test_watch_launcher.py' -v
python -m unittest discover -s tests -p 'test_mail_watch.py' -v
python scripts/mailbox_watch.py status
```

신규 6개 검사: 강제 슬롯, 미등록/계정 불일치/정상 등록, 정확한 프로세스와 6개 필드 변이, 직접 실행 감시기 탐지, 동시 잠금, 실제 테스트 Python PID를 잘못 가리킨 stop 거부. 잠금 검사가 처음 실패해 잠금 획득 전 파일 읽기를 제거한 후 6/6 통과했습니다(1.145초). 기존 감시기 검사도 8/8 통과했습니다(0.015초). 최종 상태 재조회는 `watchers=1 verified_process=True process_id=9744`였습니다.

감시기는 GitHub 편지의 변화만 기록하며 Codex 세션 자동 재개·작업 실행을 제공하지 않습니다. 숨김 모드는 데스크톱/소리 알림을 보장하지 않습니다. PC별 TEST 왕복은 실제 등록 반영 뒤 docs17에 따라 별도 기록해야 합니다. 이 작업에서는 반복 알림 이슈나 TEST 이슈를 생성하지 않았습니다.
