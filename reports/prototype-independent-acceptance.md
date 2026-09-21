# 시제품 신뢰성 독립 인수 검수

**2026-09-21 21:03 KST / pc1 CJJ / 독립 AI 검수.** 최신 빌드에서 두 음성 흐름 각각 3회 **6/6**, 텍스트 수동 접수 **2/2**, 오프라인 읽기 전용 안전성 **1/1**을 통과했습니다. 별도 저장 복구·동시 수정·화면 검사 **41/41**도 통과했습니다. 오프라인 전체 처리 **0/1 BLOCKED**, 실제 AI 품질·사람 청취·운영 배포는 별도 게이트입니다.

검수자는 제품 코드를 수정하지 않았습니다. 구현자의 54개 검사를 그대로 반복하거나 독립 실적으로 합산하지 않고, 다른 담당자의 후속 변경·대조 직후 재충돌·실제 저장 없는 503을 별도 입력으로 실행했습니다.

## 동일 빌드와 실제 실행

| 항목 | 실측 |
|---|---|
| 프론트 source | `a519e346e7a097f00961441373e858a088d86bce119640531fecd10762441292` |
| 프론트 output | `65c40b09aa68ef178eca9d73847c68a92cf237910b65c9040b79c3ba1d2fe40a` / 26파일 |
| 통합 실행 | 20:57:01.370–21:00:37.798 KST / 프로세스 종료코드 0 |
| 독립 복구 실행 | 21:01:32.004–21:01:40.535 KST / 프로세스 종료코드 0 |
| 제품 변경 검출 | 통합 실행 시작·끝 backend 해시 변경 `[]`, frontend 변경 `false` |
| 서버 | 통합 PID 30600 / 8901–8904, 독립 복구 PID 15208 / 8911–8914 |
| 외부·과금 | 외부 요청 0, live 요청 0, helper keyReads 0 / paidCalls 0 / 기존 예산 원장 접근·생성 없음 |

통합 결과: [results.json](e2e/rehearsal-2026-09-21T11-57-01-364Z/results.json). 이 폴더에 실행 당시 runner/helper 사본, SHA-256, backend 전체 파일 해시, 출력 자산 해시, 스크린샷과 서버 로그를 보존했습니다. 기존 임시 상태를 건드리지 않고 새 저장소 4개를 사용했습니다.

```powershell
$env:REHEARSAL_PORT='8901'
& 'C:/Users/choi8/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' tests/e2e/six-flow-rehearsal.mjs
```

재실행 시 사용 중이지 않은 새 포트를 지정합니다. runner가 `--preserve-state`를 전달하고 새 결과 폴더를 만듭니다.

## 6회 통합에서 실제로 확인한 것

- 원본 통화 두 개를 각각 3회 1배속·볼륨 100%·음소거 해제로 처음부터 끝까지 재생했습니다. 47.15초 음성의 실경과 47.331–47.357초, 49.55초 음성의 실경과 49.748–49.813초였고 모든 played range가 `[0, duration]` 한 구간입니다. 끝으로 seek한 뒤 자연 종료시키는 부정대조는 분석 버튼을 열지 못했습니다. 종료만으로 API가 자동 호출되지 않았습니다.
- 실제 UI WMS/TMS 근거 PATCH 뒤 상담 초안 revision을 자동 교체하지 않았습니다. 저장 차단 → `최신 내용 대조` → `서버 내용 사용`을 명시적으로 선택한 뒤 수동 대조·사람 확인을 수행했습니다. 선택 자체는 서버 저장도 사람 확인 완료도 만들지 않았습니다.
- 같은 사건의 WMS/TMS 기록, 타 사건 근거 거절, 사람 확인 없는 이관 거절, 남은 조치가 있는 종결 거절, 센터 중간/최종 회신, 경영주 조회·페이지 재조회 후 보존을 검사했습니다.
- 오출고의 W-W3 합성 영상은 3회 모두 자연 재생 12초, 960px 디코딩, 오류 없음, Escape 닫기·트리거 포커스 복귀를 확인했습니다. 미도착 또는 새 텍스트 접수에는 다른 사건 영상을 대신 표시하지 않았습니다.
- 텍스트 두 흐름은 실제 신규 POST와 수동 검토로 완료했습니다. 준비되지 않은 replay는 실제 409를 유지했고 비용 있는 분석으로 자동 전환하지 않았습니다.
- 기록한 업무 응답 74개는 200 46개 / 201 2개 / 의도한 409 2개 / 의도한 422 24개입니다. 조회·정적 자산 등 모든 HTTP 요청의 총계라는 뜻은 아닙니다. pageerror는 0개입니다.

오프라인 읽기 전용은 저장·접수·이관을 막았습니다. 서버 없이 전체 처리하는 성공으로 계산하지 않았습니다.

## 독립 복구 반례와 화면

[독립 검사 결과 41개](e2e/prototype-independent-20260921-2102/results.json)와 [실행 원본](e2e/prototype-independent-20260921-2102/source-probe.mjs)을 보존했습니다. 원본 스크립트 SHA-256은 `b05eb039172f118099cf32a4b60444f48ea43d96d17eed83de59f45ccb6ac331`입니다. 다른 PC에서 재검할 수 있도록 [공유 실행기](../tests/e2e/prototype-independent.mjs)에 경로·환경 설정만 이식했습니다.

```powershell
# 저장소 루트 / 준비 조건: 검증된 Next build, .venv, tests/e2e Playwright
$env:PROTOTYPE_PORT='8931' # 8931–8934가 비어 있는지 먼저 확인
$env:E2E_CHROMIUM='<이 PC의 실제 Chromium 실행파일 절대경로>'
# 선택: REHEARSAL_PYTHON=Python 절대경로, PROTOTYPE_OUTPUT=새 결과 폴더
node tests/e2e/prototype-independent.mjs
```

출력 폴더 기본값은 실행 시각으로 새로 생성됩니다. Windows PowerShell/CIM으로 자기 서버 신원을 확인하며 다른 OS 검증을 주장하지 않습니다. `node --check` 실제 종료코드 0, [원본 동등성 검사](e2e/prototype-independent-20260921-2102/portable-equivalence.json)에서 경로·환경 선언을 제외한 업무 검사 69줄이 정확히 같았습니다. 공유 실행기 SHA-256은 `9f96a95a01c484b80fbd191d8de5033c0a7472039eb71db25acbe239a60fa9eb`이며, 이식 후 UI 전부를 불필요하게 재반복하지 않았습니다. 다른 PC의 실행 완료를 뜻하지 않습니다.

| 실제 입력 | 기대 / 실측 |
|---|---|
| PATCH 저장 후 응답만 abort, 다른 담당자가 다시 수정, GET으로 확인 | 현재 서버가 제출 내용과 다르므로 성공으로 단정하지 않고 대조를 표시. 로컬 초안 유지·입력/재저장 잠금·조회만으로 추가 저장 0회 |
| 대조 후 `내 초안 유지` 선택, 바로 다른 담당자가 한 번 더 수정 | 다음 저장 실제 409. 후속 서버 내용·로컬 초안 모두 보존. 서버 내용 사용을 명시적으로 선택해야 교체 |
| PATCH를 저장하지 않고 503 반환 | 성공 GET만으로 저장 성공 처리하지 않음. 기존 revision 보존, 미저장 초안과 이전 서버 내용 대조 |
| 키보드 Enter로 서버 내용 사용 | 정확한 기존 서버 요청을 복원 |
| 상담·센터에 서로 다른 초안 후 메뉴 왕복 | 상담 초안 유지, localStorage/sessionStorage에 고객 초안 추가 0건 |
| 5개 화면 × 1440/1024/390px | 15조건 모두 문서 수평 넘침 0px. 복구 패널 별도 3폭도 넘침 0px |

복구의 실제 3폭 캡처: [1440](e2e/prototype-independent-20260921-2102/recovery-1440.png), [1024](e2e/prototype-independent-20260921-2102/recovery-1024.png), [390](e2e/prototype-independent-20260921-2102/recovery-390.png). 좁은 화면에서는 서버/초안이 세로로 배치되고 선택 버튼·주의 문장이 잘리지 않습니다.

상담 작업대 [1440](e2e/prototype-independent-20260921-2102/desk-full-1440.png)·[390](e2e/prototype-independent-20260921-2102/desk-full-390.png), 센터 [1024](e2e/prototype-independent-20260921-2102/center-full-1024.png), 경영주 [390](e2e/prototype-independent-20260921-2102/owner-full-390.png), WMS [1440](e2e/prototype-independent-20260921-2102/wms-full-1440.png)·[390](e2e/prototype-independent-20260921-2102/wms-full-390.png), TMS [1024](e2e/prototype-independent-20260921-2102/tms-full-1024.png)·[390](e2e/prototype-independent-20260921-2102/tms-full-390.png)를 실제 열어 확인했습니다. 선택 상태, 합성/미확인 구분, 접수/회신 버튼이 유지됩니다. TMS 모바일 표는 전용 가로 스크롤 영역이며 페이지 전체 넘침과 구분합니다. 이 독립 실행에서는 표 가로 스크롤의 키보드 조작을 추가 실측하지 않았습니다.

## 검사기 자체와 보존

runner 변경은 새 포트 지정과 근거 PATCH 이후 **명시적인 최신 내용 대조** 단계뿐입니다. 음성·역할·종결·오프라인 게이트를 완화하지 않았습니다.

```powershell
node tests/e2e/six-flow-rehearsal.mjs --audio-gate-selftest
# 14/14: 유효 2조건, ended·속도·경과시간·재생 공백·음소거 등 잘못된 12조건 거절
node tests/e2e/six-flow-rehearsal.mjs --gate-selftest reports/e2e/rehearsal-2026-09-21T11-18-13-436Z/results.json
# 실제 자식 프로세스 종료코드 변이 8/8. 기존 성공 증거 파일 해시 불변
```

[종료코드 변이 결과](e2e/rehearsal-runner-gate-2026-09-21T11-58-39-522Z.json). 제품 실행 수에 검사기 자체 대조를 합산하지 않습니다.

독립 probe의 첫 두 시도는 제품 조작 전 하네스 실패였습니다. Windows venv 런처 PID와 실제 Python 자식 PID 차이를 직접 동일 비교했고, 다음 시도에서는 PowerShell 출력 인코딩 때문에 한글 metadata 경로가 깨졌습니다. 부모·자식 PID 관계와 실제 CommandLine을 확인하고 UTF-8 출력을 명시한 후 재실행했습니다. [첫 실패](e2e/prototype-independent-20260921-2100/results.json), [두 번째 실패](e2e/prototype-independent-20260921-2101/results.json)를 삭제하거나 통과로 바꾸지 않았습니다.

자기 프로세스와 새 상태만 사용했습니다. [종료 확인](e2e/prototype-independent-20260921-2102/process-cleanup.json)에 테스트 8개 포트 listener 0개를 기록했습니다. 기존 8100/3100은 유지했고 새 Temp 상태도 삭제하지 않았습니다. 커밋·push·원격 발송·TODO 인수는 메인에게 맡깁니다.

## 폰트 추가 실측

복구 화면이 명조체처럼 보인다는 관측을 받아, 별도 8921–8924 서버에서 제품 저장 없이 computed style과 Chromium CDP `CSS.getPlatformFontsForNode`를 대조했습니다. [폰트 결과](e2e/prototype-independent-fonts-20260921-2105/results.json).

- body·버튼·textarea의 computed family는 모두 `Pretendard Variable, Pretendard, -apple-system, BlinkMacSystemFont, Segoe UI, Apple SD Gothic Neo, Malgun Gothic, sans-serif` 스택입니다. body/버튼 13px, textarea 12px입니다.
- 제목·목록 새로고침 버튼·부서 select·확인 문장의 실제 한국어 glyph는 **Malgun Gothic**, 영문/공백은 **Segoe UI**로 관측했습니다. `isCustomFont=false`인 로컬 글꼴이며 serif 적용은 이 화면에서 재현되지 않았습니다.
- body와 textarea 직접 노드는 CDP font 목록이 비어 있었습니다. 상속 선언 확인과 실제 glyph 관측을 구분하며, 이 두 노드의 실제 글꼴까지 단정하지 않습니다. `document.fonts.check`는 대체 글꼴로도 true가 될 수 있어 설치 증명으로 사용하지 않았습니다.
- 폰트 토큰·제품 CSS는 변경하지 않았습니다.

## 이번 판정의 범위

검사한 시제품의 업무 흐름·초안 보존·저장 불확실성·동시 수정 복구에서 새 제품 결함을 재현하지 못했습니다. 이는 모든 오류가 없다는 보증이 아닙니다. 실제 사람 사용성/음성 명료도, 실제 STT/GPT 품질, 원격 PC 실행, 실제 인증/물류 연동, 공유 영속 저장·최종 배포는 이 통과로 대체하지 않습니다. 브라우저 강제 종료 후 메모리 초안 복원은 지원 범위 밖이며 화면에 한계를 표시합니다.
