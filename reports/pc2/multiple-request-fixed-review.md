# N02-R2 — 고정 수정 SHA의 PC2 재검

2026-09-22 07:54 KST 검증 기록 · 메인 후속 카드 대조

### 대상과 보존

메인 `ceaf9ffe0ed7907edb051255575bb0b86d5ad943`의 요청 철회 수정과 `DRAFT_HANDOFF.md`의 PC2 수정 SHA 재검 담당을 확인해 같은 N02-R2 검토를 이어갔다. 새 이슈나 범위를 만들지 않았다. `reports/pc2-r2-main-intake.md`에 인수된 원보고는 PC2 `4c200dec13433d7139151a92aac89d8a13a076f4`의 Git blob과 바이트가 같았다. 원보고 `reports/pc2/multiple-request-implementation-review.md`·실패 결과·실행기와 R1 두 원본 파일은 보존한다.

검사 종료 후 같은 #8의 메인 댓글 `5768616784`(07:52:15 KST)를 후속 조회에서 확인했다. 기준 SHA와 원20행 재검은 동일하며, 08:10 인계·새 범위 금지·산출물 `reports/pc2/multiple-request-fixed-review.md` 한 파일 지시에 맞춰 이 보고서로 분리했다. 아래 7파일 회귀는 이 댓글 수신 전에 앞선 R2 검토 계약의 변경 영향 확인으로 이미 실행한 추가 실측이다. 댓글 수신 후 재실행하거나 범위를 더 확장하지 않았다.

실행자는 같은 pc2 `안영일/안영일\administrator`, GitHub `MR-A83`다. 작업 브랜치는 `work/pc2-n02-call-review`이며 main을 merge/pull하거나 server·프런트를 편집하지 않았다. 고정 SHA에서 `git archive`로 별도 ignored 디렉터리 `.local/multi-request-r2-ceaf9ff/source`를 만들었다. 테스트에 필요한 `server`, `tests`, `data`, `demo`, `scripts`, `pyproject.toml`, `reports/e2e/live-analysis-before.json`, `reports/e2e/live-analysis-after.json`의 **133파일**을 인수하고 실행 전후 SHA256 불변을 확인했다.

Python 3.12.14와 앞선 R2의 로컬 pytest 9.1.1·기존 서버 의존성을 재사용했다. 이번 재검의 새 설치·브라우저·수신 서버·실API·과금·실제 비용 원장 변경은 0이다. ASGI 회귀는 기존 테스트의 프로세스 내 TestClient다. 같은 PC 보조 에이전트 1개를 재사용해 source diff를 읽기 전용으로 검토했으며, 그 검토는 아래 제품 실행 수에 포함하지 않는다.

### 같은 입력의 기대 / 실측

2026-09-22 **07:53:08~07:53:34 KST**에 원 실행기와 지정 7파일 회귀를 각각 한 번 실행했다. 분모를 합쳐 정확도나 전체 제품 완료율로 표시하지 않는다.

| 검사 | 고정 기대 | PC2 수정 후 실측 |
|---|---|---|
| 원 R2 D01~D20 | 원 입력·기대값 그대로 20개 일치 | **20/20 PASS**, 실패 0, 관측 실행 exit 0 |
| 지정 7파일 회귀 | 변경된 서버의 계약·투영·ASGI 영향 유지 | **286 PASS / 250 subtests PASS**, 5 의존성 폐기 예정 경고, exit 0, pytest 20.54초 |
| R1 원본 계약·공개 투영 | 원 31행의 기대 active/rejected/review/provenance 및 공개 값 유지 | 회귀 안의 원 31행 계약과 31행 투영 모두 PASS; 별도 실행·추가 분모로 세지 않음 |
| 입력·기대값 비교 | 수정 전 20행과 동일 | 20행 원문·화자·시각·제안·기대 active/rejected/review/public request 전부 동일 |
| 활성 출처 | 실제 활성 인용과 원문·화자·구간 시각 일치 | **13인용 / 13span 일치**; 활성 없는 7행은 출처 양성 검사에 포함하지 않음 |
| 소스·공개 계약 | 실행 중 소스 불변, 기존 공개 schema 유지 | 133/133파일 불변, `c20d411` 대비 공개 schema AST 동일, OpenAPI Git blob 동일 |

기존 8개 실패의 수정 후 결과는 다음과 같다. 나머지 대조군 12개도 같은 기대값으로 통과했다.

| 유형 / ID | 같은 입력의 수정 후 결과 |
|---|---|
| 동일 상품 조사 D01 | `치약을` 요청은 뒤의 `치약` 취소에 따라 WITHDRAWN, 공개 요청 null |
| 요청만 D04/D06 | 컵/교환만 철회하고 각각 치약/반송 요청 보존 |
| 연속 문장부호 부정 인용 D08/D09 | 신형·구형 모두 취소 발언을 부인한 원문을 보고 기존 요청 보존 |
| 구형 익명 화자 D12/D15 | 요청 후보와 SPEAKER_ROLE_UNVERIFIED / OTHER_SPEAKER_CANCELLATION 유지; NON_CURRENT_CONTEXT 오거절 해소 |
| 아닌 단위 정정 D17 | 정정값이 빠진 단축 요청은 MISSING_CORRECTION_CONTEXT, 공개 요청 null |

원 실행기 바이트는 SHA256 `94345b7acef3104d39097990b65e1d1067682eaa0844708162dbd1d2cfed98e6` 그대로다. **출력의 `sourceCommit=4af2756...`은 원 실행기에 들어 있는 과거 상수이며 이번 검사 대상이 아니다.** 실제 검사 대상은 위 `ceaf9ff...`, `source-manifest.json`, `independent-execution.json`과 아래 측정 소스 해시로 판별한다. 입력·기대값의 정렬 JSON SHA256은 `1f2f45643fe0cddb952377c948156c65b251dd3bb47d1e6162dd537e815b2c12`로 수정 전후 동일하다.

- `server/request_grounding.py`: `5dc1bfdb294aede851126a73147cb513ac08fc3852b4b6a4ed4a8971c19c005a`
- `server/request_provenance.py`: `02d18b82b7ceec3b73630e1a14db9c2e2a011da5e708be8b84bcc3eec4785445`
- `server/live.py`: `7acff20ab7c8391e5636d1bcd2740df72f7829d6a81c6200684a81baa9830e2b`
- `server/analysis_schema.py`: `04b3be292133036231857793654e12da8310529c961a84d7008034f68abd2630`
- `server/openapi.yaml` Git blob (`c20d411`과 검사 SHA 공통): `12c4c005d6cdf975cab22453bd44513a50d5af7c`

R1 JSON SHA256 `3c08e84c88c56454dea186c099b66324e18682eaef34b78153ee17af0d0c3617`과 R1 보고 SHA256 `42a838886173af60fe5064e874456e0c8adf31ce433b09af93aa7fb793c872fe`도 작업 브랜치·고정 main·원 제출 사이에 동일하다. 원 실행기에서 공개 schema 검증·수량/단위 null·입력 불변과 모델/키/원장 경계 호출 0을 확인했다. 공개 요청 투영은 normalizer 직접 호출이며, 별도 원격 HTTP 검증으로 표시하지 않는다.

### 재현과 증거

아래 경로는 저장소 루트 기준이다. 재실행 시 기존 결과를 덮어쓰지 않는 새 파일명을 사용한다. 원 실행기는 기존 원보고의 `r2-verifier:start/end` 마커 블록에서 바이트 그대로 추출한다.

```powershell
. ..\enter-happycall.ps1
$env:PYTHONPATH = (Resolve-Path .local\multi-request-r2-4af2756\dependencies).Path + ';' + (Resolve-Path ..\.local\pc2-m3-python).Path
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
python -X utf8 -B .local/multi-request-r2-ceaf9ff/original-verifier.py .local/multi-request-r2-ceaf9ff/source .local/multi-request-r2-ceaf9ff/reproduced-results.json
Push-Location .local/multi-request-r2-ceaf9ff/source
python -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_multi_request_provenance.py tests/test_request_grounding.py tests/test_analysis_repair.py tests/test_analysis_grounding_regression.py tests/test_analysis_semantics.py tests/test_receipt_review_guidance.py tests/test_two_flow_asgi_workflow.py
Pop-Location
```

로컬 증거는 `.local/multi-request-r2-ceaf9ff/`의 `source-manifest.json`, `original-verifier.py`, `independent-results.json`, `independent-execution.json`, `independent-output.txt`, `pytest-execution.json`, `pytest-output.txt`, `final-integrity.json`에 보존했다. 수정 전 `.local/multi-request-r2-4af2756/`과 원보고는 그대로 남는다. 이 재검은 기존 반례 해소 확인으로 동결하며 새 언어 형태로 범위를 확장하지 않았다.

메인의 별도 15/15·일반화18/18·명사3/3은 `reports/pc2-r2-main-intake.md`의 메인 보고치이고 이 PC에서 재실행하지 않았다. 이번 PASS를 실모델 canary의 기존 4실패 해소·부모 브라우저·사람 청취·운영 배포·전체 N02 최종 인수·편지함 TEST 성공으로 확대하지 않는다. 중앙 인수·완료표·이슈 종결은 pc1이 수행한다.
