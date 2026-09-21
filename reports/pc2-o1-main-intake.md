# PC2 N02-O1 — 메인 격리 인수 검증

2026-09-22 / pc1 CJJ 로컬 독립 검토 / 검토 대상 `c127a565a087684de1c968f563f68c3236da0b1a`.

**소비자별 감시 상태 분리 계약에 적합하며, 명시된 3파일 통합을 권고합니다.** 격리된 원격 커밋에서 unittest **23/23 PASS**, 실제 CLI 도움말 exit 0을 확인했습니다. 별도로 작성한 A/B 오라클에서 각 소비자가 회신 1건을 탐지했고, 상태 분리 제거 변이는 B의 회신 누락으로 검출됐습니다. 실제 운영 소비자 적용이나 원격 메시지 전달 검증은 하지 않았습니다.

## 계약·변경 검토

`reports/channel/N02-O1-watch-consumer.md`와 원격 커밋의 `channel/mail.py`, `tests/test_mail_watch.py`, `reports/pc2/watch-consumer-review.md` 전체를 `git show`로 읽었습니다. `channel/whoami.py`도 import 부작용·필요 의존을 확인했습니다. 배정 기준 `37de103d1f69959baca9a19e0b1a9ea679c06e23`에서 현재 main까지 채널/테스트/신원 파일의 차이는 없었습니다.

- 새 `--consumer`는 이름을 상태 파일 suffix에만 사용하며 `me()`·등록 슬롯·수신 라벨을 바꾸지 않습니다.
- 이름은 `[a-z][a-z0-9_-]{0,31}`로 제한되고 argparse와 `_state_path`에서 검증됩니다. 점·슬래시·역슬래시·대문자 별칭·비ASCII·상위 경로를 허용하지 않습니다.
- 미지정/None 및 예전 Namespace는 `.mailbox_state.<slot>.json`을 유지합니다. 새 경로는 `.mailbox_state.<slot>.<consumer>.json`입니다.
- `watch --help`와 상주 시작 문구에 첫 조회, 이름 미지정/동일 이름의 공유, 탐지와 ACK 구분을 명시합니다.
- 새 이름의 최초 조회는 기존 열린 편지를 알립니다. 같은 이름의 동시 실행, 기존 스냅샷 기반 조회·보존 한계는 해결하지 않는다고 보고서에 명시되어 있습니다.
- 스냅샷 쓰기 실패를 무시하는 기존 동작, 같은 이름의 파일 경쟁은 이번 diff가 새로 만든 기능이 아닙니다. 이번 계약의 서로 다른 소비자 분리에 대한 통합 차단 결함은 재현하지 않았습니다.

## 실행 안전과 격리

실행 전에 테스트를 읽었습니다. `cmd_watch`를 부르는 테스트는 `me()`와 네트워크 경계를 대체하고 임시 디렉터리로 상태 파일을 돌립니다. `sh()` 자체를 시험하는 한 테스트도 `subprocess.run`을 mock합니다. CLI 도움말은 argparse에서 종료되어 실제 `watch`를 실행하지 않습니다. `whoami.py` import 시 콘솔 인코딩 설정 외에 신원 카드·GitHub 조회·소켓 함수는 실행되지 않습니다.

존재하지 않음을 확인한 새 폴더 `.local/pc2-o1-intake-c127a56`에 위 3파일과 import에 필요한 `channel/whoami.py` **4개만** Git blob 바이트로 추출했습니다. 원격 blob과 추출 파일의 바이트 비교 **4/4 일치**를 실행 전후 확인했습니다. main 파일에 cherry-pick·복사·수정하지 않았습니다.

| 격리 파일 | bytes | SHA256 |
|---|---:|---|
| channel/mail.py | 21921 | 5cb2a08c09649985123af2d1c8f91e16faf037813a27301d7493db1a9b92a9d0 |
| tests/test_mail_watch.py | 13121 | 4363f6d986c04ee7fe4b6a6f8bbfbce80de0ba6490d40e3c17c28327d531d32d |
| reports/pc2/watch-consumer-review.md | 7241 | faead80d87ecb43843e6ea5c7962890ae69e755225aed8d8d17a0ecb6b64452d |
| channel/whoami.py | 5822 | 88aef88b19c8fba409cf40b0cf4f2209925eab0106e6d6435ecff0da68b80829 |

## 재현 명령과 결과

작업 디렉터리: `C:/00.프로젝트/happycall-ralphthon/.local/pc2-o1-intake-c127a56`.

```powershell
C:/00.프로젝트/happycall-ralphthon/.venv/Scripts/python.exe -B -X utf8 -m unittest discover -s tests -p test_mail_watch.py -v
C:/00.프로젝트/happycall-ralphthon/.venv/Scripts/python.exe -B -X utf8 channel/mail.py watch --help
```

실측: **Ran 23 tests in 0.162s / OK**, exit 0, 실패·skip 0. 기존 8개와 신규 15개의 분모이며 제공된 변이 대조도 이 23개에 포함됩니다. CLI 도움말 exit 0으로 `--consumer NAME`, 1~32자 제한, 슬롯/수신처 불변, 무출력·ACK 한계 문구를 확인했습니다.

원격의 23/23·0.205초는 원격 PC2 결과이고, 위 23/23·0.162초는 메인 격리 실행입니다. 두 실행을 46개의 서로 다른 테스트로 합산하지 않습니다.

## 별도 작성 A/B 오라클

원격 테스트의 helper를 재사용하지 않고 격리 `mail` 모듈에 합성 snapshot 함수, 임시 ROOT, pc1 신원을 주입했습니다. `sh`는 호출하면 즉시 실패하는 sentinel로 두었습니다. 합성 이슈는 #91이고 댓글 수만 0→1로 변경했습니다.

| 조건 | 기대 / 실제 |
|---|---|
| alpha와 beta가 각각 댓글 0 기준점 보유, alpha가 먼저 댓글 1 조회 | alpha 회신 1건, 뒤의 beta 회신 1건 |
| 두 소비자 재조회 | 둘 다 정확히 빈 출력 |
| named 조회 전후 기본 snapshot | 파일 바이트 불변, 기본 소비자도 뒤에 회신 1건 탐지 |
| 1자·32자 이름 | 그대로 허용 |
| 경로·슬래시·역슬래시·점·대문자·33자·빈 값·한글·개행 9개 | 모두 ArgumentTypeError |
| 소비자 이름 `pc4`, 실제 슬롯 pc1 | `.mailbox_state.pc1.pc4.json`, 신원 변경 없음 |
| `_state_path`만 기본 경로로 축소한 메모리 변이 | alpha 1건, beta 0건 → `B lost independent reply` AssertionError 검출 |

관측 출력:

```text
CONTROL A_reply 1 B_reply 1
CONTROL silent repeats/default unchanged/1,32-char bounds/9 invalid names/slot isolation PASS
MUTANT A_reply 1 B_reply 0
ISOLATION MUTANT detected
```

CONTROL과 변이는 서로 다른 새 임시 디렉터리를 쓰며 파일 분리 함수 외 입력과 판정은 같았습니다. 실제 GitHub 댓글을 생성하거나 조회하지 않았습니다. 제공된 suite 내부 변이 1건과 이 독립 변이 1건은 같은 계약을 다른 오라클로 대조한 것이며 작업 완료율로 환산하지 않습니다.

## 기존 상태 보존

main 원본 파일은 실행 전후 다음 SHA256으로 동일했습니다.

| main 파일 | SHA256 |
|---|---|
| channel/mail.py | 72fd7630d24b180b5aa588c703f23e38fc51b0a021daad4ba20f5c9517f71790 |
| tests/test_mail_watch.py | 28663f8fb2049fa049b9bc0a71c9ecf246ddf9524794fe656cf1b0f3dfe88e73 |
| channel/whoami.py | 88aef88b19c8fba409cf40b0cf4f2209925eab0106e6d6435ecff0da68b80829 |

읽기 전용 프로세스 조회에서 기존 상주 감시 **PID 9744 / 생성 2026-09-21 16:47:02 KST**를 실행 전후 동일하게 확인했습니다. 시작·정지·재시작·환경 변경을 하지 않았습니다.

실제 `.mailbox_state.pc1.json`은 읽기 전용 hash 관측만 했습니다. 전 SHA `c97b54201650c4e14fc488de3226a600b1ebecca42370d7424ca73ba2a615d91`, 후 SHA `eaf842ce50155c2bd905fa15914ee422d14b0e774d6e45e6ed246df78945a5c0`로 상주 감시가 있는 동안 갱신되어, 실제 snapshot이 불변이었다고 주장하지 않습니다. 이 테스트의 모든 쓰기는 새 격리 폴더와 자체 임시 디렉터리 안입니다.

`git check-ignore -v`에서 기본·main-loop·pc4 소비자 경로 3개 모두 기존 `.gitignore:43`의 `.mailbox_state.*.json`에 포함됐습니다. ignore 파일도 변경하지 않았습니다.

## 판정과 운영 적용 경계

검토 대상 3파일은 소유·계약 범위 내이며 메인이 통합할 수 있습니다. 이 보고서는 코드 인수 근거이고 아직 통합·실제 소비자 설정·원격 수신·TEST 왕복·작업 ACK의 완료 기록이 아닙니다. 실제 main에 통합한 뒤 별도 소비자 이름을 사용하는 시점과 첫 기준점 생성은 메인이 결정합니다. 이 작업에서는 `watch --once --consumer ...`를 실제 계정에 실행하지 않았고 편지·API 쓰기·커밋도 없습니다.

원격 PC2의 다른 음성/M5 완료와는 별개입니다. 인수 보고서와 판정을 여기서 동결하며, 메인이 명시 3파일 통합 여부를 결정합니다.

## 메인 통합·최초 적용

메인은 2026-09-22 01:36 KST에 원격의 명시 3파일만 `92aac431a172412085b6fc751f091437a169308a`로 통합했습니다. 통합 커밋의 세 Git blob을 원격 `c127a565…`와 비교해 **3/3 바이트 일치**를 확인했습니다. 기존 미추적 PC4 인수 보고서는 포함하지 않았습니다.

같은 시각 실제 pc1 계정에서 `python -B channel/mail.py watch --once --consumer main-loop`를 한 번 실행했습니다. exit0이며 01:36:57 KST에 기존 열린 #8·#9·#10을 최초 기준점으로 알렸습니다. 이는 새로 발송된 세 편지나 원격 ACK가 아니라 **새 소비자의 초기 이력 탐지**입니다. 상주 감시기의 기본 상태와 분리된 `.mailbox_state.pc1.main-loop.json`을 사용하며 다음 메인 재개도 같은 소비자 이름을 사용합니다. 같은 이름의 동시 실행 문제까지 해결한 것은 아닙니다.
