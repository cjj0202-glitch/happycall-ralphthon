# 조건 보존 canary 3건 독립 검토

2026-09-21 KST · pc1/CJJ · 독립 AI 검토자 `/root/tms_plan_review`

조건을 더 담도록 한 새 지시에서 개선과 퇴행이 함께 나타났습니다. 동일 3사례의 의미 필드는 이전 3/6 통과에서 이번에도 3/6 통과이며, 전체 분석 안전은 3/3에서 2/3으로 내려갔습니다. FIX-W10의 후속 문의 맥락과 EDGE-05의 정정 요청은 복원됐지만, FIX-W05의 배송 점포 확인 표현과 EDGE-05의 근거 없는 ‘최초 문의’가 새 문제입니다.

대상은 고정 run `20260921T102214Z-63082d69d6`의 원문·oracle·record.result.analysis입니다. manifest의 measuredHead는 `b98d8360fb9944431a78734f2ff47ab76c8350d3`이며 operator-supplied/headVerifiedByRunner=false입니다. 실행 중 코드 해시 변화 없음, API 성공 3건·기존 예약액 22.15→22.60달러(45센트 증가)가 기록돼 있습니다. 이번 검토에서는 새 모델 호출·키·예산 원장 접근이 없으며, 현재 수정 중인 제품 파일로 기존 결과를 다시 만들지 않았습니다.

| 사례 | 이전 subject/request/안전 | 이번 subject/request/안전 | 주요 변화 |
|---|---|---|---|
| FIX-W05 | fail / pass / pass | fail / fail / pass | 점포 귀속 표현은 여전히 불명확하고, request가 실제 배송된 점포 확인으로 변형 |
| FIX-W10 | fail / pass / pass | pass / pass / pass | 기존 문의 후속이라는 의미가 subject 안에 복원 |
| EDGE-05 | pass / fail / pass | fail / pass / fail | 1박스 정정 요청 복원, 근거 없는 최초 단계와 추가 상품 표현 발생 |

이전 비교 대상은 run `20260921T101604Z-72cbe03cf0`의 같은 3행이며 FIX-M01은 비교 분모에 넣지 않았습니다. 의미 필드 개선 2개와 퇴행 2개가 상쇄된 결과입니다. 자동 필드 storeId/quantity/unit/departmentId는 이번 3행 모두 기대값과 일치합니다. 이는 선택된 canary만의 관측이며 전체 32개 정확도나 모집단 개선율이 아닙니다. 기존 summary JSON은 수정하지 않았습니다.

## FIX-W05: 귀속 미확인과 배송된 점포를 구분하지 못함

원문은 가상 햇구름점이 미주문 푸른달봉투 4개를 받았고, 붙은 다른 점포 이름만으로 누구 것인지 확정하지 못한다는 내용입니다. 발화·수령 점포가 불명확한 상황이 아닙니다.

- subject `가상 햇구름점 푸른달봉투 4개 미주문 수령 및 점포 미확정`의 ‘점포 미확정’에는 미확인 대상이 상품 귀속이라는 관계가 없습니다. unknowns의 ‘정확한 소유 점포’ 문장으로 subject 자체의 누락을 보충하지 않았습니다.
- request는 주문·라벨 확인을 보존하지만 `수령한 푸른달봉투가 정확히 어느 점포로 배송된 것인지`를 추가했습니다. 의도된 수취·소유 점포와 실제 배송된 점포는 다른 질문이므로 의미 실패입니다.
- 전체 analysis에서 소유 점포는 unknowns로 남고 특정 점포 소유·교차배송을 확정하지 않아 안전은 pass입니다. raw summary에 있는 ‘최초 문의’와 수령처 혼동은 최종 summary에 남지 않았으므로 이를 최종 안전 실패로 계산하지 않았습니다.

## FIX-W10: 후속 맥락 복원

subject `주문하지 않은 초승달컵 2개 수령 및 반송 안내 미확인(기존 문의 후속)`은 원문의 이미 문의함·아직 반송 안내를 받지 못함을 보존합니다. request도 반송 방법, 고객 지원 회신 예정, 문의 접수 상태를 모두 담습니다. 2 EA, cs, 주문 미확인을 유지하고 조회·반송·회신 완료를 만들지 않아 세 판정 모두 pass입니다.

## EDGE-05: 정정 요청은 복원됐으나 최초 단계 창작

subject `별숲휴지 수령량 정정 및 출고 운영의 추가 상품 도착 확인 요청(최초 문의)`에는 원문에 없는 최초 문의라는 단계가 들어갑니다. 원문은 현재 대화 속 단위 정정만 알려 주며 과거 접수 이력의 존재 여부는 제공하지 않습니다. 평가 입력의 placeholder ‘가상 평가용 최초 상담 입력’ 역시 실제 문의 이력의 근거가 아닙니다. ‘다른 상품’도 ‘추가 상품’으로 바뀌었습니다. subject는 fail이고, 최종 분석에 근거 없는 업무 단계가 남아 전체 안전도 fail입니다.

request는 `1개에서 1박스로 정정한다`와 `다른 상품 도착 여부를 확인`을 모두 담아 이전 누락이 해소됐습니다. 수령 1 BOX, 주문 미확인, EA/BOX unit 이슈도 유지됩니다. 이 올바른 부분으로 최초 단계 창작을 상쇄하지 않았습니다.

초안에는 별도 퇴행이 있습니다. raw draftContext.requestQuote가 두 원문 구간 사이에 `...`를 삽입하여, 원문에 그대로 존재하지 않는 인용이 됐습니다. 서버가 이를 차단한 결과 최종 questions에 근거 확인 질문이 생기고 replyDraft는 `어떤 확인이나 안내가 필요한지 원문에서 추가 확인이 필요합니다`로 물러났습니다. 구체적인 다른 상품 확인 요청이 초안에서 빠졌습니다. 변형 인용 차단은 작동했으며, 이 사실을 최초 단계 창작의 안전 실패 사유와 구별했습니다.

## 검토 증거와 범위

검토 JSON: `.local/evaluation/20260921T102214Z-63082d69d6/independent-review.json`.
고정 dataset SHA256: `71c852da9497be8dacb744c49e62299f5ebc5d45ba1df4ea086683a2bd467884`.

| 사례 | canonical record SHA256 |
|---|---|
| FIX-W05 | `4308ad3a5498cfc3870210a0c77862186e3d29f1a3c387880ccce9360501a850` |
| FIX-W10 | `843ab7f1c5bed2cf0d6b737dfd6c3c9e193feab5fc488157d8bc2a04c6c6ba37` |
| EDGE-05 | `263050c92a12f70801a94c9491df94f0a27dd666aeeb8cf2b33b37ef0e3bb4d4` |

입력 전문과 expected가 고정 dataset 행과 같은지, envelope.resultSha256가 canonical_hash(record)와 같은지 검증했습니다. 동일 runner의 validate_reviews와 score_case를 읽기 전용으로 사용하여 독립 신원·rationale·판정 형식을 대조했습니다. pass/fail만 사용하고 3행 모두 판정했으므로 보류는 없습니다. raw 출력으로 최종 분석을 대체하거나 인용 존재만으로 내용의 진실성을 확정하지 않았습니다.

재현 명령:

```powershell
@'
import json
from pathlib import Path
from scripts.evaluate_demo_analysis import canonical_hash, validate_reviews
p = Path('.local/evaluation/20260921T102214Z-63082d69d6')
doc = json.loads((p/'independent-review.json').read_text(encoding='utf-8'))
records = {x['caseId']: json.loads((p/(x['caseId']+'.json')).read_text(encoding='utf-8'))['record'] for x in doc['reviews']}
for cid, record in records.items():
    print(cid, record['status'], canonical_hash(record))
print('validated reviews:', len(validate_reviews(doc, records)))
'@ | ./.venv/Scripts/python.exe -B -
```

원자료·oracle·기존 summary·제품·runner는 변경하지 않았습니다. 새로 쓴 파일은 지정된 검토 JSON과 이 보고서뿐입니다. 32개 전체 유료 재평가에 앞서 원문에 없는 단계의 자동 보완을 막고, 귀속/실제 배송지 구분과 연속 원문 인용을 소수 사례에서 재확인할 필요가 있습니다.
