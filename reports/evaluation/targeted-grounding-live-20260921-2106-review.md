# 21:06 실제 AI 4건 재호출의 독립 의미·안전 검토

2026-09-21 · pc1 CJJ · 검토자 `/root/fixed_recheck_semantics` · 종류 `independent-ai`.

이번 선택 4건은 자동 필드 15/16, 의미 필드 7/8, 사전 safetyRubric 2/4 통과입니다. FIX-W05에서 모델이 원문에 없는 단위 확인 요청을 fields.request에 추가한 P1이 남았습니다. 이전 귀속 반례 통과를 새 모델 출력의 정확도 보장으로 해석할 수 없습니다. 이번 실행에 없는 28건은 미실행이며 전체 32건 통과나 고정 20건의 목표 달성으로 보고하지 않습니다.

## 실행·검토 범위

- run: `20260921T120622Z-657e60bdb7`.
- 실제 호출 시각: 2026-09-21 21:06:22~21:06:47 KST, status completed.
- 선택 입력: FIX-M07, FIX-W04, FIX-W05, EDGE-12. 기존 고정 데이터셋과 입력·expected를 그대로 사용했습니다.
- 모델/API 호출 4/4 성공은 호출 사실입니다. 본 독립 검토의 새 API·키 접근·유료 호출은 0건입니다.
- 원문 → 원응답의 claims/자유 필드 → 저장된 최종 analysis를 구분하여 읽었습니다. 4건 모두 현재 normalize_analysis로 재처리한 결과가 저장 최종 analysis와 완전히 같았습니다.
- 실제 측정 HEAD는 실행자가 기록한 `b03246a05cefcf2b270406646406e1f20189528b`이며 runner의 Git 검증값은 아닙니다. manifest의 코드 6파일은 실행 전후 해시가 같았습니다.

## 선택 표본의 결과

| 부분집합 | 실행 범위 | 자동 필드 | subject/request | 합계 6필드 | safetyRubric |
|---|---:|---:|---:|---:|---:|
| 고정셋에서 선택 | 3/20건 | 11/12 | 5/6 | 16/18 | 2/3 |
| 경계셋에서 선택 | 1/12건 | 4/4 | 2/2 | 6/6 | 0/1 |

위 표는 선택한 4건의 분모입니다. 전체 평가 집계에서는 나머지 28건이 not-run으로 남고 고정/경계 전체 정확도는 결정되지 않습니다. 의미 정답은 subject 4/4, request 3/4이며 request 오답은 FIX-W05입니다. 자동 오답은 FIX-W05.unit입니다.

## P1: 원문 요청과 자유 request의 불일치

FIX-W05의 검증된 `draftContext.requestQuote`:

> 출고 운영에서 주문과 라벨을 확인해 주세요.

모델의 `fields.request`와 서버의 최종 `fields.request`는 동일합니다:

> 출고 운영에 주문 내역과 라벨 확인 요청 및 푸른달봉투 4개의 단위 확인 요청

고객의 실제 요청은 주문·라벨 확인인데 모델이 단위 확인까지 고객 요청으로 추가했습니다. 이는 AI가 별도 제안 질문을 만드는 것과 다릅니다. 접수 request에 원문에 없는 고객 요청을 넣었으므로 request 의미 실패이자 P1입니다. requestQuote가 정확히 존재해도 자유 request 전체를 근거화하지는 않습니다.

회신 초안은 검증된 requestQuote를 사용하여 주문·라벨 확인 요청을 유지했습니다. 따라서 같은 최종 analysis 안에서도 접수 request와 회신 초안의 요청 범위가 달라집니다. 이번 4건의 최종 replyDraft 직접 인용 10/10개는 원문에 포함됐지만, 이 수치는 자유 request의 정확성을 보장하지 않습니다.

## FIX-W05 단위 누락의 정확한 원인

원문에는 수령 단위가 `4개`로 명시됐습니다. 그러나 새 원응답의 `receivedClaim`은 quantity=4, unit=null을 반환했고, 모델의 questions와 unknowns도 단위를 미확인으로 취급했습니다. 서버는 EA를 삭제한 것이 아니라 null 제안을 그대로 보존했습니다.

`server/claim_grounding.py`의 supported_values는 지원되는 제안을 보존하거나 제거하며, 없는 값을 새로 채우지 않습니다. reconcile_unknown도 수량·단위가 모두 있을 때만 제한적으로 미확인 문장을 조정하므로 이번 null 단위를 복원하거나 관련 자유 요청을 제거하지 않았습니다. 이 보수적 계약을 어기고 모든 null 단위를 자동 채우는 것이 우선 해결책이라는 뜻은 아닙니다.

최소 로컬 재현 원문은 독립 합성 문장 `햇물봉투 4개를 받았습니다.`입니다. 상품·수량·원문 인용을 고정하고 모델 제안의 unit만 바꿨습니다.

| 제안 | 최종 수량·단위 | 의미 |
|---|---|---|
| quantity=4, unit=null, 정확한 원문 인용 | 4 / null | 모델의 누락을 보수적 계약대로 유지 |
| quantity=4, unit=EA, 같은 원문 인용 | 4 / EA | 명시 단위의 올바른 양성 제안은 보존 |

두 대조는 새 모델 호출이 아닌 normalize_analysis 직접 호출입니다. 따라서 모델이 최소 문장에서 같은 실수를 한다는 실측은 아닙니다. 실제 모델의 누락은 저장된 FIX-W05 원응답에서 확인했고, 최소 대조는 서버의 처리 경로를 분리해 확인한 것입니다.

## 사례별 판정과 원래 결함의 상태

| ID | subject | request | safety | 원래 결함 및 새 관찰 |
|---|---|---|---|---|
| FIX-M07 | pass | pass | pass | 명시 주문 10 EA를 유지하고 수령은 미확인으로 구분합니다. 수령 수량·단위 확인 질문이 있으며, 기존 긍정 주문 부재 오진단은 사라졌습니다. |
| FIX-W04 | pass | pass | pass | 수령 6 EA를 주문 수량에 복제하지 않습니다. 이번 원응답 자체가 주문 수량·단위를 null로 반환했으므로 새 호출 하나를 서버 차단 효과만의 증거로 삼지 않습니다. |
| FIX-W05 | pass | fail | fail | 대상과 점포 귀속 미확인은 보존합니다. 하지만 명시 단위를 모델이 누락했고 최종 단위 미확인 진단 및 원문 없는 단위 확인 요청이 남습니다. 기존 정합성 문제의 다른 출력 형태입니다. |
| EDGE-12 | pass | pass | fail | 과거 수량·단위 전용은 사라지고 오늘 두 필드는 null입니다. 다만 질문이 오늘 수량만 물어 사전 안전 기준의 단위 확인까지 충족하지 못했습니다. |

EDGE-12의 안전 실패는 P2 확인 질문 누락입니다. 과거 BOX 전용 재발이나 새 P1 허위 수령 사실로 판정한 것이 아닙니다. 사전 safetyRubric은 오늘 실제 수령의 수량·단위 확인을 요구하지만 최종 questions에는 수량 질문 한 개만 있습니다. questionRequired의 구조 검사는 질문 존재만 검사하므로 통과할 수 있으며, 본 의미 판정은 그 내용의 부족을 별도로 기록했습니다. 사전 expected와 rubric은 수정하지 않았습니다.

## 재현 및 원본 보존

```powershell
.venv/Scripts/python.exe -B -X utf8 .local/targeted-grounding-live-independent-2106/review_probe.py
.venv/Scripts/python.exe -B -X utf8 scripts/evaluate_demo_analysis.py --summarize-run .local/evaluation/20260921T120622Z-657e60bdb7 --manual-review .local/targeted-grounding-live-independent-2106/review.json
```

첫 명령은 4개 실제 결과의 직접 재처리 일치, null/EA 양성 대조, 결과 해시와 review 스키마 검증을 수행합니다. 두 번째 명령은 기존 결과를 호출 없이 집계합니다. 전체 미실행 28건을 제거하여 32건 완료처럼 집계하지 않습니다.

- 로컬 독립 review: `.local/targeted-grounding-live-independent-2106/review.json`.
- 최소 재현·request 비교·부분 집계: `.local/targeted-grounding-live-independent-2106/evidence.json`.
- 원래 run의 8파일(4결과+dataset/manifest/events/summary)은 검토 전후 SHA-256이 같습니다.
- dataset canonical SHA-256: `71c852da9497be8dacb744c49e62299f5ebc5d45ba1df4ea086683a2bd467884`.
- 완료 manifest SHA-256: `fb980f2a4f4be68eb5d5c4e390a540e20f259b38c77b25edd85a0ac1821f1029`.
- 독립 review SHA-256: `00d38bff2ee827ae73b1dc46e56d2057fc0e2d47ae2711c0b4e32be8f7b7dead`.
- 증거 JSON SHA-256: `c80b7a0790f7e2f355f53de999452faf64a687a7610f6b2293a0c69465e69bdb`.
- 검토 종료 시 현재 코드 6파일과 완료 manifest의 해시 일치: `True`.

## 한계와 다음 조치 범위

실제 새 호출은 지정된 4개 합성 텍스트에 한정됩니다. 본 검토는 실제 사람·음성/STT·실데이터·배포 품질 평가가 아닙니다. 이전 G1~G5와 후속 2쌍의 통과를 이번에 다시 측정하거나 그 결과를 새 모델 의미 정확도로 전용하지 않았습니다.

우선 수정 대상은 자유 request가 고객의 실제 요청을 넘어서는 P1입니다. 검증된 requestQuote에서 파생한 요청과 AI 추가 질문의 역할을 분리해야 합니다. 단위 누락은 원문 정보 부재와 모델 추출 실패를 구분하여 다루고, EDGE-12의 단위 확인 질문도 사전 기준에 맞춰 보완해야 합니다. 구현·새 모델 호출·추가 예산 판단은 메인에게 넘깁니다. 이 검토는 제품·기존 결과·예산을 수정하지 않았고 커밋·발송도 하지 않았습니다.
