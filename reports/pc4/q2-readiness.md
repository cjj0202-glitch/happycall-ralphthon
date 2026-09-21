# N04-Q2 준비 결과 — 최종 제품 검증 미실행

2026-09-21 20:06 KST · pc4 / 장준호 / j324rst-svg. 배정: #10 댓글 `5759287396`. 준비 참고 main: `e5469aa99bb266c5a977b80c097223275ac6fc9b`, 기존 제품 결과: `1b82f1d7fad1b31545d512b28896bfcba40189ec`. 작업 브랜치는 `work/pc4-n04-tms-qa`를 유지했습니다. 최종 통합 SHA를 받지 않았습니다.

**준비한 검사기는 실제 최종 앱에서 아직 검증하지 않았습니다. 핵심 0/6, 경계 0/15, production build 0회, 제품 API·브라우저·음성/영상 재생 0회입니다.** 이전 TMS 자체검사와 기존 셸 결과는 그대로 과거 이력이며 이 분모에 포함하지 않습니다.

## 이번 산출물과 실제 자체검사

- [실행 매트릭스](q2-plan.md): 두 사례 각각 3회 전체 음성 1배속 자연 종료, 실제 UI 저장·센터 회신·경영주 조회, 별도 경계 15개, 1365/921/390 폭, 기대값·미실행 기준.
- [UI 검사기 준비](q2-ui-checker-notes.md): 끝 seek·구간·이전 사건 native callback 반례, 현재 source·case·session·played 관측, CCTV 등록 구간 재생·Escape·포커스, 수정 확인 해제, 409/503/404·오프라인, 미래 계획/실적 구분, 선택 방문/행/이전다음.
- `tests/remote/pc4/q2-build.py`: **명시된 최종 SHA의 별도 clean checkout**에서 production build 1회를 만들 때 웹 밖 overlay/fixture까지 포함한 제품 입력 해시 전후를 기록합니다. 설치·배포·서버 실행은 하지 않습니다. 이번에는 실행하지 않았습니다.
- `q2_contract.py` / `q2-run.py`: 최종 SHA·clean 제품 소스·생산 빌드 기록·전체 입력·canonical manifest와 public/out/HTTP 자산·fixture 3본을 대조합니다. 같은 정적 산출물과 fixture 사본, 새 임시 저장소, 한 loopback origin에서 실행하며 run nonce를 검증합니다. 최종 실행 후 소스/빌드/검사기/원장 불변 및 6개 고유 회차·15개 필수 경계를 집계합니다.

| 이번 실행 | 기대 | 실제 |
|---|---|---|
| `python tests/remote/pc4/q2-contract-selftest.py` | 허용 입력과 잘못된 SHA/출처/자산/분모/이전 overlay 빌드·필수 선택자 누락의 변이 구분 | 37/37 PASS |
| `node tests/remote/pc4/flow-ui-check.mjs --self-test` | 합성 관측의 자연 종료 양성/seek·구간·다른 사건/세션·source·rate 반례 및 origin/nonce 대조 | 16/16 PASS |
| 최종 입력 없이 UI checker 호출 | 브라우저 시작 전 NOT_RUN, 종료코드 2 | 기대/실제 2/2, browserStarted=false |
| Node/Python 구문, git diff 공백 검사 | 오류 없음 | PASS |
| `python tests/remote/pc4/q2-run.py --prepare-only` | 누락 입력을 보존, 제품 실행 0 | PREPARED_NOT_RUN, 0/6 |

자체검사 원자료: [q2-checker-selftests.json](q2-checker-selftests.json), 준비 상태: [q2-preparation.json](q2-preparation.json). 53개의 자체검사와 구문 검사는 제품 검증 건수가 아닙니다. 원본 로그는 Git 제외 `.local/q2-preparation/`에 남겼으며 게시하지 않습니다.

## 독립 코드 검토와 보완

같은 pc4의 보조 검토자가 실행 전에 다음 네 가지를 찾아 보완했습니다. pc1 인수나 별도 물리 PC의 검증을 뜻하지 않습니다.

1. 웹 바깥 overlay가 빌드 지문에서 빠짐 → 최종 HEAD 및 전체 추적 제품 입력을 빌드 전후 기록하고 실행 시 대조. 이전 overlay 빌드는 자체 반례로 거부.
2. manifest와 제공 자산의 연결 누락 → canonical manifest ↔ 계약 ↔ public ↔ out ↔ 실제 HTTP bytes, fixture data/public/out 일치 필수.
3. 오류 시 격리 패치가 서버보다 먼저 해제됨 → 브라우저/API 종료 후만 해제, API 종료 실패 시 프로세스 종료까지 격리 유지. 실제 timeout/서버 정리 동작은 최종 실행 전에 별도 확인해야 합니다.
4. 빈 경계/중복 회차/guard 누락도 성공 가능 → 필수 ID·상태·고유 회차·고유 저장소·자연 종료 증거·실행 identity를 hard gate로 검사.

수정 후 읽기 전용 재검토에서 해당 네 반례의 코드상 해소를 확인했고, 관련 집계·출처 변이 검사를 통과했습니다. 실제 앱 실행으로 재현·해소한 제품 결함이라고 보고하지 않습니다.

## 최종 입력 수신 후 재현

메인이 최종 통합 SHA, 확정 manifest/자산의 해시·길이·구간·사건 관계, 실제 통합 UI 선택자를 같은 #10으로 전달해야 합니다. `q2-release.template.json`의 null/false/빈 assets는 미확정 값입니다. 임의의 HEAD나 과거 자산으로 채우지 않습니다. capability 선언만으로는 통과하지 않으며 실제 DOM/HTTP를 대조합니다.

사전 게이트의 필수 선택자는 `naturalCompletionControl`, `segmentControl`, `differentToteNotice`, `tmsRegion`, `tmsRawSourceControl`입니다. 기존 셸과 새 TMS 영역·원본 열기 이름이 달라 기본 locator로 실행하면 미실행될 수 있다는 후속 검토를 반영했습니다. 나머지 optional override도 최종 DOM에서 대조하며 불일치를 성공으로 처리하지 않습니다.

이 PC의 준비 자체검사는 저장소 루트에서 다음과 같습니다.

```powershell
python tests/remote/pc4/q2-contract-selftest.py
node tests/remote/pc4/flow-ui-check.mjs --self-test
python tests/remote/pc4/q2-run.py --prepare-only
```

최종 실행은 아래 구조로 수행합니다. `<최종...>`은 아직 미수신이므로 현재 실행할 명령이 아닙니다.

```text
python tests/remote/pc4/q2-build.py --product-root <최종SHA의별도cleancheckout절대경로> --final-sha <메인확정40자리SHA> --npm-cli <설치된npm-cli.js절대경로>
python tests/remote/pc4/q2-run.py --release-contract <확정계약JSON절대경로> --product-root <같은최종checkout절대경로> --execute
```

첫 명령의 `.local/pc4-q2-build.json`과 생산 export의 지문을 계약에 대조한 뒤 두 번째 명령을 실행합니다. `E2E_CHROMIUM`은 이 PC의 `.happycall-tools/playwright/chromium-1208/chrome-win64/chrome.exe` 절대경로입니다. 다른 PC 경로를 사용하지 않습니다. 이미 설치된 의존성이 필요하며 실행기가 자동 설치하지 않습니다.

실행기는 production 정적 사본과 실제 제품 API를 연결한 자기 소유 서버만 기동합니다. 기존 서버·감시기는 정지하지 않습니다. 저장 상태는 테스트마다 새 임시 경로이고, 합성 상태 사본은 검토를 위해 로컬에 보존합니다. 서버/브라우저 종료 실패, 누락 선택자, 지원되지 않는 최종 manifest/빌드 helper 계약은 실패/미실행 사유로 회신하고 공용 제품을 직접 고치지 않습니다.

최종 결과는 `reports/pc4/q2-final-<UTC>/results.json`, `harness.json`, 화면 증거입니다. 핵심 6/6과 경계 15/15가 모두 실제 같은 릴리스에서 통과하고 필수 보존·비용·정리 가드도 통과해야 최종 검사 PASS입니다. 인수와 이슈 종결은 pc1이 수행합니다.
