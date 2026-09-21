# PC4 N04-Q2 수신 결과의 메인 독립 대조

**판정: 제품 후보 `bfc8543`의 6회 업무 흐름·15개 경계 검증 증거는 제한된 범위에서 인수 가능.** 원격 실행을 새로 반복하지 않고, 공유 커밋의 원문과 실행 시 해시·관측값을 독립적으로 재계산했습니다. 증거 대조 220조건 중 **220조건 일치**이며 새 제품 결함은 확인하지 못했습니다. **첫 실패 당시 검사기 원본 보존은 P2 보완 항목**입니다.

수신 커밋: `ca00b2fb23b5f2e252dba5c0930f6aea3a8416c5` / pc4 장준호, j324rst-svg. [실제 회신](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/10#issuecomment-5760172352). 이 문서는 pc1 CJJ의 읽기 전용 독립 검토이며, 원격 PC를 대신하여 브라우저·Temp 파일·프로세스 종료를 직접 관측했다고 주장하지 않습니다.

## 대조한 기준과 원문

| 항목 | 독립 대조 결과 |
|---|---|
| 실제 검수 제품 | `bfc8543aa65316682948f2e3d5b77a3ee56b21ff` |
| 최종 검사 실행 | 2026-09-21 20:52:53.070–20:59:07.789 KST |
| 최종 checker SHA-256 | `0367a0a525a284fdefa5cfd8e4e137e39220d05109b74c360d76abeea8600565` |
| source fingerprint | `0e80c944bd7a870d4228b355a54266a88b5d99bc7c9c72b1e3b6826cf6bccc47` |
| output fingerprint | `b769128ff1443dcd7bc361efa23d40709d411dba2aebfc6682d600c48d310f67` |
| 최종 결과 JSON 원문 | 1,144,752 bytes / SHA-256 `589fd55906a9f368410e6536a2229d7b9f9c1e7c33762a92e852a5859cdcb114` |
| 최종 harness JSON 원문 | 51,326 bytes / SHA-256 `d66cffaba91c4c05272a43454964802d557acc4dddb3bcf3e89c96ba54338019` |

검토 대상은 [결과 보고](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/ca00b2fb23b5f2e252dba5c0930f6aea3a8416c5/reports/pc4/q2-candidate-bfc8543.md), [최종 results](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/ca00b2fb23b5f2e252dba5c0930f6aea3a8416c5/reports/pc4/q2-final-20260921T115253068033Z/results.json), [harness](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/ca00b2fb23b5f2e252dba5c0930f6aea3a8416c5/reports/pc4/q2-final-20260921T115253068033Z/harness.json), evidence-crosscheck, 빌드 기록, 릴리스 계약 및 실제 [checker](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/ca00b2fb23b5f2e252dba5c0930f6aea3a8416c5/tests/remote/pc4/flow-ui-check.mjs)입니다. 앞선 실패 결과도 같은 커밋의 `q2-final-20260921T114440146468Z/`에서 대조했습니다.

## 바이트와 동일 제품 검증

1. 64개 제품 입력 모두 bfc8543 Git blob과 비교했습니다. **38개는 원바이트 일치**, **26개는 내용 변경 없이 LF→CRLF 변환 시 일치**했습니다. 임의 공백·JSON 정규화·해시 생략은 사용하지 않았습니다.
2. 원격 입력 해시에 맞는 줄바꿈만 재현하고 승인 음성/영상 세 파일을 넣은 별도 읽기용 사본에서, **bfc8543 자체 `source_fingerprint`를 실행하여 위 `0e80c944…`를 동일하게 재계산**했습니다. 제품 파일은 수정하지 않았고 새 빌드도 하지 않았습니다.
3. fixture는 LF `071b4599…` / CRLF `79c3b01a…`, manifest는 LF `0caf2965…` / CRLF `6e09467b…`로 정본 Git 내용과 전달 해시의 관계를 직접 확인했습니다.
4. 최종 checker Git blob 원바이트 SHA는 runtime 시작·끝 checkerHash와 정확히 같습니다. Python runner 6개도 공유 Git blob과 runtime 시작·끝 해시가 모두 일치합니다. 실행 당시 tester HEAD d7ff5ee 자체를 실행 파일과 같다고 취급하지 않았습니다.
5. 두 실행의 제품 입력·build stamp·output fingerprint는 같습니다. 원격 output bytes 전체를 pc1에서 직접 다시 읽어 계산한 것은 아니며, 원격 빌드 기록과 실행 전후 측정값의 일치입니다. output과 실제 공급한 세 미디어의 HTTP 해시·206 Range 기록은 별도로 대조했습니다.

첫 독립 계산은 모든 입력이 LF라는 가정으로 26개 원바이트와 source fingerprint 차이를 보고했습니다. 이를 제품 수정으로 단정하지 않고 위 두 줄바꿈 변형을 각각 해시하여 원인을 분리했습니다. 최초 결과 `.local/pc4-q2-independent/verification-raw-blob-only.json`도 보존했습니다.

## 자연 재생과 전체 21개 판정

최종 results의 고유 `(caseId, repetition)`은 정확히 두 사례 × 3회이며, 6개 모두 서로 다른 저장소 `run-02`~`run-07`을 사용했습니다. 경계 15개 ID는 계획된 집합과 동일하며 `run-08`~`run-22`의 서로 다른 저장소를 사용하여 정상 회차와 섞이지 않았습니다.

| 대상 | 실제 기록 재계산 |
|---|---|
| 미도착 음성 3회 | duration 47.15초, wall 47.486 / 47.285 / 47.284초 |
| 오출고 음성 3회 | duration 49.55초, wall 49.849 / 49.728 / 49.768초 |
| 음성 6개 전체 | seek/seeked 이벤트 0, 모든 event/sample rate 1, 같은 case/source/session·연결 상태, trusted play/playing/ended, `played=[[0,duration]]` |
| 합성 영상 3회 | 정확히 0~12초 연속 played, wall 12.091 / 12.063 / 12.130초, source·rate 고정, seek 0, trusted 종료 |
| 실제 영상 blob | 1,097,133 bytes / `e6cad3cf9f999b596a0fef3e3d463170e0d279568a31a4be49366e5383908881` 승인 자산과 일치 |
| 6회 업무 상태 | 각각 replay POST 200, PATCH 5회 sentRevision 1→5, 최종 closed/revision 6 |
| 최종 연결 근거 | CASE1 `E-M3/E-M1`, CASE2 `E-W1/E-W5`; fixture 사건과 일치 |

검사기 원문도 직접 읽었습니다. 자연 재생은 전체 재생 후 native 관측을 평가하고 실제 분석 버튼 활성화를 검사하며, 업무 단계는 실제 UI PATCH 뒤 GET을 읽어 중간 회신·남은 조치·최종 회신·원문 보존을 assert합니다. 마지막 경영주 화면의 등록 회신과 처리 완료 문구도 검사합니다. 완료 상태를 로컬 JSON에 직접 써서 만든 경로는 사용하지 않습니다.

**15개 경계의 실제 범위**는 다음과 같습니다.

- 음성 끝 seek / 부분 구간 / 이전 사례 native 종료: 현재 전체 완료 게이트는 세 경우 모두 비활성. 정상 6회 성공 분자에 포함하지 않음.
- 새 텍스트에 과거 근거 자동 연결 안 됨, 명시적 기존 접수 참조에 영상 자동 복제 안 됨. 새 텍스트 replay 409를 실제 AI 성공으로 바꾸지 않음.
- 영상 404 표시 후 같은 승인 자산 재시도·native 재생, Escape와 원래 버튼 포커스 복귀.
- 저장 전 주입한 503, API 단절 예시 열람, 실제 browser offline, 독립 UI 두 개의 실제 409에서 허위 성공·최신 내용 덮어쓰기 방지와 복구.
- 07:00 정상 기준의 05:00 근거, 04:30 기준 반례, +1시간 미래 actual/GPS를 구분. 미래 계획은 계획으로 남으며 미래 실적은 근거 채택하지 않음.
- 서로 다른 picking/shipping 업무 토트를 연속 추적했다고 표시하지 않음.
- 1365/921/390px × 5개 화면의 문서 넘침, 실제 키보드 방문 이동·선택 행 동기화, reduced-motion 제어. 전체 스크린리더·Tab 순서·색 대비 감사라는 뜻은 아님.

68개 기록된 업무 HTTP 응답은 GET 200 24 / POST replay 200 6 / PATCH 200 33 / POST 접수 201 2 / POST 409 1 / PATCH 503 1 / PATCH 409 1입니다. 브라우저 pageerror 0, console 기록은 **6개**이며 의도한 409·404·503·연결 거부·offline·409와 대응합니다. 외부/live 차단 목록과 paid analyzer 호출은 0입니다. **콘솔 전체 오류 0**으로 표현하지 않습니다.

## 실패 보존과 남은 기록 보완

앞선 실행은 핵심 3/6, 경계 13/15, 프로세스 종료코드 1입니다. 오출고 3건의 `Registered segment did not begin native playback`, 영상 404 재시도 timeout, 충돌 메시지의 strict locator 오류를 그대로 보존했습니다. 초기 `INCOMPLETE_NEXT_EXPORT` 빌드 실패도 남아 있습니다. 두 번째 결과를 첫 번째 실패 행에 덮어쓰지 않았고, 최종 6/6을 서로 다른 실행의 성공 건으로 조합하지 않았습니다.

**P2 — 첫 실행 검사기 원본 미확인:** 첫 harness는 checker SHA `31f1ffd2dc53a671a01d5f537a446f82e7db75e5d57e8ae10bb84ce54ffbaf1a`를 기록합니다. 현재 내려받은 Git 전체 ref에서 해당 경로의 고유 버전 3개와 각각 LF/CRLF 바이트를 대조했으나 이 해시는 발견하지 못했습니다. d7ff5ee 버전의 원바이트 SHA는 `b64bf8e0…`, 최종 ca00b2f는 `0367a0a5…`입니다. 따라서 **첫 실패 결과·스크린샷·해시 보존은 확인**, **첫 실행 검사기 원본까지 보존은 미확인**입니다. PC4에 정확히 31f1ffd2…인 파일이 남아 있으면 실패 증거와 함께 전달받는 것이 좋습니다. 파일을 재구성한 후 원본이라고 표시하면 안 됩니다. 최종 검사기와 최종 실행은 이미 일치하므로 최종 6/6의 직접 차단 사항으로 보지는 않습니다.

## 직접 확인하지 못한 것과 인수 범위

- pc4의 원격 Temp 상태·실제 프로세스에는 접근하지 않았습니다. `temporaryStateHashes`, 원본 보존, API 종료는 원격 runner의 기록입니다. 직접 재해시/종료 확인 PASS로 승격하지 않습니다.
- originalStateBefore/After에서 기존 상담 JSON·예산 JSON은 모두 **null(원래 없음)**입니다. 이 대조는 없던 파일을 만들지 않았다는 범위이며, 실제 기존 상담 데이터가 있는 상태를 보존한 시험으로 표현하지 않습니다.
- 최종 GET의 전체 본문은 검사기가 실제 assert하지만 compact final에는 closed/revision/선택 근거/원문 보존 플래그만 남습니다. 전체 저장 문서에 대한 pc1 재검증은 원격 Temp의 직접 접근·추가 안전한 합성 사본 인수 없이 할 수 없습니다.
- 음성 기록은 자연 1배속 재생을 뒷받침합니다. mute·volume·사람이 실제로 들은 명료도까지 이 관측으로 확인하지 않았습니다.
- **현재 새 초안/저장 복구 UI의 source `a519e346…`에는 소급하지 않습니다.** 그 빌드는 [별도 독립 인수 결과](prototype-independent-acceptance.md)가 기준입니다. 실제 AI 평가·새 음성/CCTV·영속 저장·최종 배포·공식 제출도 별도입니다.

재계산 스크립트와 전체 판정은 메인 로컬 `.local/pc4-q2-independent/verify.py`, `verification.json`에 보존했습니다. 실행 명령은 아래와 같으며 제품·원격 PC·과금·브라우저 실행을 변경하지 않습니다.

```powershell
$env:PYTHONUTF8='1'
.venv/Scripts/python.exe .local/pc4-q2-independent/inspect.py
.venv/Scripts/python.exe .local/pc4-q2-independent/verify.py
# 최종: status PASS / passed 220 / total 220 / failed [] / process exit 0
```

이 220은 **기존 제출 증거를 대조한 조건 수**이며 UI 220회 실행이나 제품 테스트 총수로 합산하지 않습니다. 이 검토자는 제품·기존 증거·TODO를 수정하거나 커밋·발송하지 않았습니다.
