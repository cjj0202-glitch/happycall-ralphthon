# N04-Q2 · bfc8543 통합 후보 검증 결과

작성: 2026-09-21 KST · pc4 장준호 / j324rst-svg. **동일 후보·빌드에서 검사기를 수정한 2차 실행은 핵심 6/6·경계 15/15 PASS입니다. 첫 실행의 3/6·13/15 실패 이력을 보존했습니다. pc1의 증거 검증·인수는 별도 대기입니다.**

## 검증 목적과 고정 입력

BMAD 관점에서 업무는 통화부터 센터 최종 회신·경영주 조회까지 저장된 결과, UX는 완료/오류/선택 맥락, 구조는 동일 사건·revision·고정 릴리스, 검증은 정상·경계·실패 복구의 실제 UI/HTTP·재조회입니다. 전체 음성은 0초부터 1배속 자연 종료로 검사하고 끝 seek·구간 재생은 별도 반례로 분리했습니다.

| 항목 | 확인 값 |
|---|---|
| 제품 후보 SHA | `bfc8543aa65316682948f2e3d5b77a3ee56b21ff` |
| 별도 제품 checkout | `C:/Users/j324r/OneDrive/문서/ChatGPT/해커톤_D-Day/happycall-q2-bfc8543` |
| 검사 checkout | `C:/Users/j324r/OneDrive/문서/ChatGPT/해커톤_D-Day/happycall-ralphthon` |
| 검사 checkout HEAD | `d7ff5eebd180a3805c8aff59fc503d27aa044be2` |
| UI / API | `http://127.0.0.1:18105` / 동일 출처 격리 API |
| 환경 | Windows · Python 3.12.14 · Node v24.19.0 · Playwright 1.58.2 |
| 프런트 소스 지문 | `0e80c944bd7a870d4228b355a54266a88b5d99bc7c9c72b1e3b6826cf6bccc47` |
| 생산 빌드 지문 | `b769128ff1443dcd7bc361efa23d40709d411dba2aebfc6682d600c48d310f67` |

근거는 [로컬 릴리스 계약](q2-bfc8543-local-contract.json)과 [빌드 증거](q2-bfc8543-build-evidence.json)입니다. fixture/manifest의 전달 CRLF 해시와 로컬 Git LF 해시 차이는 줄바꿈만 다름을 대조해 기록했습니다. 조용히 해시 검사를 생략하지 않았습니다.

첫 빌드는 Next 명령 종료 0이었지만 자산 복사 준비가 중단되어 `INCOMPLETE_NEXT_EXPORT` 게이트에 실패했습니다. 이 실패를 보존한 뒤 20:43:36~20:43:51 KST에 다시 빌드했고 제품 HEAD·64개 추적 입력의 전후 일치와 생산 산출물 지문을 확인했습니다. 빌드 성공은 전체 업무 검증 통과와 별개입니다.

승인 자산은 CASE1 음성 47.15초, CASE2 음성 49.55초, CASE2 sorter 영상 12초입니다. 세 자산의 byte/SHA-256은 릴리스 계약에 있으며 1차 하네스에서 실제 HTTP 자산 해시와 Range 206을 대조했습니다.

## 1차 실행 관측

실행: **2026-09-21 20:44:44~20:51:17 KST**, 별도 하네스 종료 20:51:19 KST. 원자료는 [results](q2-final-20260921T114440146468Z/results.json), [harness](q2-final-20260921T114440146468Z/harness.json), [읽기 전용 증거 대조](q2-final-20260921T114440146468Z/evidence-crosscheck.json)입니다.

| 분모 | PASS | FAIL | NOT_RUN | 결과 |
|---|---:|---:|---:|---|
| 핵심 전체 흐름 6 | 3 | 3 | 0 | 미도착 3회 closed/revision 6; 오출고 3회 영상 재생 조작 단계 실패 |
| 별도 경계 15 | 13 | 2 | 0 | 영상 404 복구 재생과 409 오류 선택자 검사 실패 |
| 전체 음성 자연재생 6 | 6 | 0 | 0 | 실제 사례 URL 일치·coverage 1·1배속·native 종료 |

음성 실측 wall time은 CASE1 47.529/47.384/47.273초, CASE2 49.693/49.751/49.700초였습니다. 음성 6건 성공을 전체 업무 6/6으로 쓰지 않습니다. 미도착 3회는 근거 `E-M3`·`E-M1`을 연결하고 최종 저장·조회 및 원문 보존을 확인했습니다.

경계 통과에는 끝 seek/구간 재생의 전체 완료 차단, 이전 사례의 native ended가 현재 완료 게이트를 열지 않음, 텍스트/명시 참조, API 오류·단절/브라우저 offline 복구, 미래 실적과 계획 구분, 토트 연속성 제한, 1365/921/390px 검사가 포함됩니다. 세부 실제 assertion 범위는 원자료를 따릅니다.

1차 실행의 제품 소스·빌드·검사기 전후 일치, 기존 상담 상태 보존, 자체 API 중지를 확인했습니다. 유료 analyzer 호출·외부/live 요청은 0건입니다. pageerror는 0건이나 console 항목 6건이 원자료에 있으므로 모든 콘솔/네트워크 오류가 없었다고 표현하지 않습니다.

## 실패 → 관측 → 검사기 수정 → 동일 조건 재시험

First Bolt의 작은 검증 단위는 **실제 사용자 재생 조작과 오류 표시를 검사기가 정확히 관측하는지**입니다. 제품을 수정해 검사에 맞추지 않고, 잘못된 검사 조작/선택자를 바로잡은 뒤 같은 제품·빌드·자산 전체를 다시 실행합니다.

| 실패 | 확인한 원인·수정 | 재시험 상태 |
|---|---|---|
| CASE2 3회 `Registered segment did not begin native playback` 및 영상 404 복구 timeout | 검사기의 영상 `height - 24` 좌표가 재생 버튼 대신 seek bar를 눌렀습니다. video 포커스를 확인한 뒤 실제 Space 입력으로 재생하며 trusted play/playing·played 범위·벽시계로 판정합니다. | 2차 전체 실행 PASS |
| 409 경계 strict mode violation | `getByRole('alert')`가 제품 오류와 Next route announcer 2개를 선택했습니다. 실제 충돌 오류 문구로 한정했습니다. | 2차 전체 실행 PASS |

1차 검사 파일 `flow-ui-check.mjs` SHA-256은 `31f1ffd2dc53a671a01d5f537a446f82e7db75e5d57e8ae10bb84ce54ffbaf1a`, 수정 파일은 `0367a0a525a284fdefa5cfd8e4e137e39220d05109b74c360d76abeea8600565`입니다. **후자는 Git commit이 아닌 파일 해시**이며 실행 당시 검사 checkout HEAD는 d7ff5ee입니다. 공유 커밋의 Git blob과 실행 파일 해시는 제출 전 별도로 대조합니다.

## 2차 동일 빌드 재검증 결과

실제 실행 **2026-09-21 20:52:53~20:59:07 KST**. [results](q2-final-20260921T115253068033Z/results.json), [harness](q2-final-20260921T115253068033Z/harness.json), [증거 대조](q2-final-20260921T115253068033Z/evidence-crosscheck.json).

| 분모 | PASS | FAIL | NOT_RUN |
|---|---:|---:|---:|
| 새 저장소 6개의 전체 업무 흐름 | 6 | 0 | 0 |
| 고유 경계 검사 15건 | 15 | 0 | 0 |
| 두 사례 전체 음성 자연 재생 | 6 | 0 | 0 |
| CASE2 등록 영상 0~12초 | 3 | 0 | 0 |

음성은 각각 실제 fixture URL과 일치하고 native played coverage=1입니다. CASE1 wall time 47.486/47.285/47.284초, CASE2 49.849/49.728/49.768초. 영상 3회 wall time은 12.091/12.063/12.130초이며 blob의 실제 bytes=1,097,133과 SHA256 `e6cad3cf9f999b596a0fef3e3d463170e0d279568a31a4be49366e5383908881`이 승인 파일과 일치합니다. 동일 source·1배속·native play/playing·played 전 구간과 Escape/포커스 복귀를 확인했습니다.

모든 회차에서 WMS/TMS 근거를 실제 PATCH하고 최종 GET으로 closed·원문 보존·회신·남은 조치 없음 상태를 대조했습니다. CASE1 E-M1은 asOf07:00에서05:00 정상 근거 연결을 실제 저장했습니다. 별도04:30반례와 미래실적/GPS는 채택되지 않으며 미래계획은 계획으로 남습니다. 이전 사례의 실제 native trusted ended를 유발해 현재 사례 완료 게이트가 비활성임을 확인했고 React 내부 콜백 호출 자체를 계측했다고 주장하지 않습니다.

소스/빌드/검사기 전후 동일, 기존 상태 보존, 테스트 API 종료 모두 true. Browser exit 0·guardFailures=[]·pageerror0·과금 호출0·외부/live 호출0입니다. 의도적인 오류/오프라인 경계에 따른 console 항목은 증거에 보존하며 콘솔 전체 무오류로 표현하지 않습니다. 정상 6회와 경계는 같은 두 번째 검사기 해시로 실행했고 첫 결과를 섞어 6/6으로 만들지 않았습니다. 실행 뒤 중복 서버를 남기지 않았고 기존 편지함 감시기는 보존했습니다.

독립 읽기 검토에서 6개 음성 URL·100% played·trusted ended, 3개 영상 승인 해시·12초·trusted 종료, 6개 저장소 ID·15개 고유 경계와 검사기 지문을 다시 대조했으며 P0/P1 불일치를 발견하지 못했습니다. 검토자의 Temp 파일 직접 재해시는 접근 거부로 미확인이며, 원본 상태 보존은 실행기 기록과 실제 HTTP/GET 증거에 근거합니다. 접근 권한을 변경하거나 거부를 우회하지 않았습니다.

## 재현 경로

다음은 검증된 자산과 생산 빌드가 보존된 같은 PC에서 사용하는 경로입니다. 재현 전 해당 포트가 비어 있는지 확인하고 실행 중인 검사와 중복 실행하지 않습니다.

```powershell
. 'C:/Users/j324r/OneDrive/문서/ChatGPT/해커톤_D-Day/Start-HappyCall.ps1'
$env:E2E_CHROMIUM = 'C:/Users/j324r/OneDrive/문서/ChatGPT/해커톤_D-Day/.happycall-tools/playwright/chromium-1208/chrome-win64/chrome.exe'
python 'C:/Users/j324r/OneDrive/문서/ChatGPT/해커톤_D-Day/happycall-ralphthon/tests/remote/pc4/q2-run.py' --release-contract 'C:/Users/j324r/OneDrive/문서/ChatGPT/해커톤_D-Day/happycall-ralphthon/reports/pc4/q2-bfc8543-local-contract.json' --product-root 'C:/Users/j324r/OneDrive/문서/ChatGPT/해커톤_D-Day/happycall-q2-bfc8543' --execute
```

실제 인터프리터는 `.happycall-tools/python/Scripts/python.exe`, Node는 `C:/Users/j324r/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe`입니다. 실행 전 릴리스 계약·현재 검사기 해시·artifact gate를 대조하며, 다른 자산/소스에 이 결과를 소급하지 않습니다.

## 남은 범위

6회/15경계 실측은 완료됐으며 최종 인수는 pc1이 판단합니다. 사람 청취·사용성 관찰, 실제 STT/GPT, 운영 WMS/TMS·실물 인도/귀책, 배포 저장 지속성, 편지함 TEST 왕복, 공식 제출은 이 보고의 검증 대상과 별개입니다. 오프라인 안전한 저장 차단/복구가 오프라인 전체 업무 저장·완주를 뜻하지 않습니다. 새 음성·CCTV 후보를 반영하면 해당 최종 자산의 영향 검사가 다시 필요합니다.
