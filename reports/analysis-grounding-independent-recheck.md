# 수량 귀속 후속 수정의 독립 재검토

2026-09-21 20:51 KST · pc1 CJJ · `/root/fixed_recheck_semantics` · 제품 읽기 전용 검토.

기존 독립 반례 G1~G5는 5/5 통과했고, 원래 안전 결함 4건의 수정도 유지됐습니다. 특히 새 회귀였던 G3는 올바른 7 EA 보존과 잘못된 BOX 차단을 동시에 충족했습니다. 그러나 새 양성/음성 2쌍에서 양성 2건은 보존했지만 부정·명사형 미래 예정 2건을 모두 실제 수령 진술로 채택했습니다. 따라서 기존 지적의 제한된 수정은 인정하되 일반 수령 귀속 안전 기준의 인수는 계속 보류해야 합니다.

## P1 잔존: 부정 및 명사형 예정의 실제 수령 채택

관측 시각은 2026-09-21 20:51 KST이며 다음 두 반례 때문에 안전 기준을 닫지 못했습니다. 검토 시간·실행 권한 문제로 막힌 것이 아니라 실제 실행에서 필드와 summary가 원문 의미와 다르게 나왔습니다.

| 쌍 | 원문 | 제안된 수령 값 | 기대 | 실측 |
|---|---|---|---|---|
| P1 양성 | 햇살차 4개를 받았습니다. | 4 EA | 4 EA 보존 | 4 EA, 통과 |
| P1 부정 | 햇살차 4개를 받은 것이 아닙니다. | 4 EA | 긍정 수령 4 EA를 채택하지 않음 | 4 EA, 실패 |
| P2 양성 | 달샘물 2박스를 수령했습니다. | 2 BOX | 2 BOX 보존 | 2 BOX, 통과 |
| P2 예정 | 달샘물 2박스 수령 예정입니다. | 2 BOX | 예정 값을 현재 실수령 필드에 채택하지 않음 | 2 BOX, 실패 |

P1 부정의 summary는 수령 진술에 햇살차 4 EA를, P2 예정의 summary는 달샘물 2 BOX를 넣었습니다. 실제 인도는 별도 확인이라는 공통 문장이 붙어도 원래 없었던 긍정 수령 진술을 구성한 오류는 남습니다. 부정 문장에서 올바른 수량을 0으로 새로 추출하라는 요구가 아닙니다. 지원되지 않는 제안 값을 자동 채우지 않는 계약의 검사입니다.

코드 위치는 `server/claim_grounding.py:14–15`의 부정·미래 패턴과 `:108–109`의 수령 범위 필터입니다. 현재 부정 패턴은 `받지 않음/못 받음/받은 적 없음` 등의 형태를 포함하지만 `받은 것이 아님`을 포함하지 않습니다. 미래 패턴은 `받을/수령할/도착할` 또는 내일·다음 배송처럼 명시 시점이 앞선 표현을 포함하지만 `수령 예정` 명사형을 놓칩니다. 두 경우 모두 수량 토큰 지지를 통과합니다.

이 두 원문은 독립 재검에서 새로 작성했고, 기존 G1~G5 문장·기대값을 바꿔 만든 통과가 아닙니다. 미래·부정의 표면 표현을 모두 해석할 수 있다고 일반화하면 안 되며, 위 일상적인 두 표현은 재현 가능한 미완 항목으로 남겨야 합니다.

## 인정하는 수정 범위

| 검사 | 독립 실측 | 판정 범위 |
|---|---|---|
| 원래 G1~G5 | 5/5 통과 | 기존 정확한 입력·기대값의 수정 인정 |
| G3 올바른 제안 | 수령 7 EA 유지 | 과도한 null 회귀 해소 |
| G3 잘못된 제안 | 수량 7 유지, BOX 단위는 null | 주문 단위 전용 차단 |
| G5 unknowns | 다른 날짜·다른 상품·복합 라벨 미확인 3개 보존, 단순 현재 수령 미확인 1개만 진술 존재로 조정 | 이 제한된 정합성 수정 인정 |
| 원래 FIX-M07 | 주문 10 EA 복구 및 긍정 주문 부재 오진단 제거 유지 | 해당 원응답 결함 해소 |
| 원래 FIX-W04 | 주문 수량·단위만 미확인, 수령 6 EA 유지 | 해당 원응답 결함 해소 |
| 원래 FIX-W05 | 수령 4 EA 진술 존재와 실제 인도 확인 구분, 점포 귀속 미확인 유지 | 해당 원응답 결함 해소 |
| 원래 EDGE-12 | 오늘 수량·단위 모두 null | 과거 단위 전용 해소 |
| 저장 응답 재처리 | 32/32가 구현자 후속 결과와 일치, 원래 대비 4변경·28동일 | 신규 라이브 평가가 아님 |
| 자동 4필드 | 128/128 사전 oracle 일치 | subject/request·전체 안전 판정과 구분 |
| 추가 2쌍 | 양성 2/2 통과, 음성 0/2 통과 | 일반 안전 게이트 미충족 |

원래 32건 전체의 안전을 이번에 새로 판정한 것이 아니며 안전 32/32라고 보고하지 않습니다. 4개 수정 결과와 28개 불변 사실을 구분했습니다. 기존 subject/request 의미 오류도 그대로 남아 있습니다.

## 재현 명령과 실행 결과

```powershell
.venv/Scripts/python.exe -B -X utf8 -m pytest -q tests/test_analysis_grounding_regression.py tests/test_analysis_repair.py tests/test_analysis_semantics.py -rs
.venv/Scripts/python.exe -B -X utf8 .local/grounding-independent-recheck/run_recheck.py
```

첫 명령: `81 passed, 124 subtests passed in 4.94s`, 종료 코드 0.

두 번째 명령: 기존 스크립트의 출력 경로만 메모리에서 바꾸어 별도 네임스페이스로 실행했습니다. 원래 5종 `passed=true`, 32 재처리·자동 128·원본 보존 확인 후 새 두 쌍을 기록했습니다. 출력의 `positivePass=true` 2건, `negativePass=false` 2건이 실제 평가값입니다. 종료 코드 0은 증거 저장·불변성 assertion 성공이며 모든 안전 테스트 통과를 의미하지 않습니다.

원래 `.local/grounding-independent/probe.py`와 `independent-results.json`을 수정하지 않았습니다. 원래 run 36파일 해시와 코드 3파일 해시도 실행 전후 일치했습니다. 키·SDK 진입은 AssertionError 대조로 금지했으며 새 API·과금 호출은 0건입니다.

## 증거와 해시

- 실행 래퍼: `.local/grounding-independent-recheck/run_recheck.py`.
- 원래 5종의 새 실행 stdout: `.local/grounding-independent-recheck/original-probe.stdout.log`.
- 원래 5종 및 32 재처리 결과: `.local/grounding-independent-recheck/independent-results.json`.
- 새 두 쌍과 원본 보존 해시: `.local/grounding-independent-recheck/additional-pairs.json`.

원래 5종 새 결과 SHA-256: `de8eab048e207d43a77baace5aaa6016478d7ad0bc9b12056cd797f0eb55dc33`.

새 두 쌍 결과 SHA-256: `42a88b7e13ce2b1e25e66b8834bf45490c5850d02fa3c51cce3203998e0ed8eb`.

검토 코드 SHA-256:

- `server/live.py`: `51cbce2c274436803d9ecca5ea6adaa6684073605d64cac06ff04b53b0dd6e51`.
- `server/claim_grounding.py`: `c2503010ce4e4ae3523057a58fe7f724aafd05061a25ef256b3f19163fae83c9`.
- `tests/test_analysis_grounding_regression.py`: `040b40ca4e1e1ebacbc7ca78646f9277c872be27149f458cd1b91cb5a7a61a4f`.

## 인수 한계와 다음 조건

기존 G1~G5의 수정과 저장 원응답 4건 보완은 제한적으로 인정할 수 있습니다. 그러나 위 두 P1 잔존을 수정·동일 양성/음성 쌍으로 확인하기 전에는 일반 수령 귀속 방어 완료 또는 전체 안전 인수를 권하지 않습니다. 양성도 함께 보존해야 하므로 모든 수량을 비우는 우회는 수용 기준이 아닙니다.

이번 검토는 분석 함수와 제한된 회귀에 한정됩니다. 소유 밖 backend 재시도·idempotency·프런트엔드·라이브 모델/STT·배포는 검사하지 않았습니다. 제품·평가기준·기존 결과·원장·기존 검토 보고서를 편집하지 않았고 커밋·발송도 하지 않았습니다.
