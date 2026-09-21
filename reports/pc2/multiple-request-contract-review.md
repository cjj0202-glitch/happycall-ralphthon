# N02-R1 — 복수 요청의 독립 합성 입력과 계약 검토

2026-09-22 · pc2 안영일 / GitHub MR-A83 · `work/pc2-n02-call-review`

## 결과와 범위

독립 합성 입력 **31행**을 작성했다. 제안 인용 64항목, 기대 활성 인용 27개, 원문 출처 span 28개를 전수 대조했다. 상담원이 단위 정정·잘못 온 상품 처리·주문 상품 처리의 세 요청을 각각 대조하고, 철회된 요청만 제외하는 계약을 검토할 수 있다. 이 파일과 [평가 입력](../../tests/evaluation/multi-request-cases.json)만 이번 배정 산출물이다. 제품 코드 변경·새 모델 평가·부모 UI 통합·사람 청취·최종 인수 결과가 아니다.

- 배정: [#8 / 5766164592](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/8#issuecomment-5766164592), 실제 수신 04:24 KST. [ACK](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/8#issuecomment-5766216288) 04:25:22 KST.
- 작업 시작 HEAD: `c127a565a087684de1c968f563f68c3236da0b1a`. 결과 SHA는 이 두 파일을 담은 커밋과 최종 #8 회신으로 식별한다.
- 문서 기준: `c20d411c8b5d430897db6d00fb96bee079a68a6d`의 `planning/multi-request-provenance.md`, `reports/evaluation/voice-canary-20260922-oracle.json`, `reports/evaluation/voice-canary-20260922-review.md`.
- 관측 코드 기준: `dce4e66c0815e477f51977cbd9e023db101b9d58:server/request_grounding.py`. 최신 main이나 실행 API의 결과로 확대하지 않는다.
- 실제 경로: `C:\Users\Administrator\Desktop\hackerton\happycall-ralphthon`. Windows 11 / Python 3.12.14. hostname·등록 pc2·gh 계정 MR-A83 대조 완료.

원문/STT/합성 입력/AI 제안/사람 입력은 다른 출처다. 이번 transcript는 새로 쓴 합성 문장이고 시각도 4초 간격의 검사용 숫자다. 실제 STT·모델 원응답·음원 전문·원장·비밀을 읽거나 첨부하지 않았다. 공개 가상 대본의 과업 구조만 참고해 컵 6개 주문과 치약 1BOX 수령을 분리했다. 제품 출력에서 기대값을 복사하지 않았다.

## BMAD 네 관점

| 관점 | 상담 과업과 계약 제안 | 대응 사례 |
|---|---|---|
| 업무 | 정정·수령 상품 처리·주문 상품 처리 세 요청을 별도로 보존한다. 수령 1BOX와 상담원 1EA 질문을 혼동하거나 개수 환산하지 않는다. | R01, R04, R28 |
| UX | 인용별 화자·구간·원문 대조가 가능해야 한다. 개별 철회와 역할 미확인을 해당 인용에 표시하며 일반 경고를 모든 분석에 붙이지 않는다. AI 확인을 사람 확인으로 체크하지 않는다. | R13, R15~R19, R24, R31 |
| 계약 | 모델 전용 `requestQuotes` 배열과 구형 단일형 변환을 명시한다. 공개 `fields.request: string|null`은 유지한다. 다른 화자/누락 구간을 지워 가짜 연속 인용을 만들지 않는다. | R04~R06, R20~R30 |
| 검증 | 긍정·부정·모호성·상한을 독립 기대값으로 고정한다. 현재 순수 함수 관측과 미래 복수 요청 구현 검증을 구분한다. | 전 31행, 아래 대조군 |

## 제안 계약과 결정이 필요한 경계

1. `expectedActiveQuotes`는 현재 요청 문구의 원문 보존 후보다. 고객 신원 확인·사람 승인·센터 처리 완료를 뜻하지 않는다. `expectedRejectedQuotes`는 자동 활성 목록에서 제외할 제안이며 원문/모델 응답 삭제나 실제 요청 부존재 선언이 아니다. 출처가 있지만 모호하여 유보한 인용도 여기에 포함된다.
2. 같은 **비어 있지 않은** speaker의 인접 구간만 경계에 ASCII 공백 하나를 두고 연결한다. 인용의 첫/끝 구간은 부분 문자열일 수 있지만 중간 문자·구간은 생략할 수 없다. 숫자·단위·띄어쓰기를 교정하지 않는다. 각 span은 Python Unicode code-point 기준 0-based, 끝 제외다. UI가 UTF-16 offset을 사용하면 명시적으로 변환해야 한다.
3. R01의 q1은 단위 정정 문맥까지 포함한다. R04는 인접 두 구간을 증거로 삼는다. R28의 “단위를 제대로 기록해 주세요.”만 채택하면 정정 값이 사라진다. 자동 문맥 확장이나 수령 필드 추출은 이 데이터의 구현 범위가 아니다.
4. 화자 교대가 있어도 동일 발화자의 **명시적인 대상 철회**는 앞 요청에 적용한다(R16). 타인의 취소로 고객 철회를 확정하지 않는다(R17). R18/R19의 모호한 지시어는 대상으로 추정한 항목만 임의 삭제하지 않고 영향 후보의 자동 활성화를 유보한다. 두 요청이 모두 실제 철회됐다는 판정과 다르다.
5. 한 인용에 두 과업이 들어 있고 하나만 철회됐으면 전체를 유효 인용으로 남길 수 없다. R31은 전체 인용과 별도로 제안된 정확한 배송 부분 인용 중 배송만 유지한다. 전체 인용만 제안된 경우에는 유효한 부분을 새 문장으로 창작하지 않고 원문 대조 대상으로 남기는 방향을 제안한다. 후속 구현의 범위 추출 방식은 pc1이 결정한다.
6. 중복은 proposalIndex로 한 항목씩 구분한다. 위치가 명확하면 전사 순서로 정렬하고 중복을 제거한다(R20). R21처럼 과거/현재에 같은 문자열이 반복되면 문자열만으로 발생 위치를 선택하지 않는 **보수적 PC2 제안**을 기록했다. 현재 문맥이 분명한 위치를 선택하고 그 span을 보존하는 대안도 가능하다. R21은 확정된 제품 규칙이나 실측 정확도 정답이 아니며 pc1 결정 대상이다.
7. 신·구 key가 함께 있으면 빈 신형 배열이어도 혼용이다(R23). 원시 배열은 **8개까지**, **9개부터 초과**다. 정본의 “9개 초과” 표현은 최대8이라는 계약과 함께 읽으면 모호하므로 경계를 명확히 할 필요가 있다. R26/R27은 잘라내기·선행 중복제거 대신 전체 후보를 검토로 넘기는 제안이다. 원응답을 보존하며 일부 무관한 사실/질문/센터 회신까지 삭제하지 않는다.
8. R18/R19/R21/R23/R26/R27/R28/R31에는 `policyStatus=pc2-proposal-pending-pc1-contract-decision`을 넣었다. 이유 코드는 평가용 의미 표식이며 제품 enum/schema를 임의 추가한 것이 아니다. null·혼합 타입 배열·빈 항목의 세부 거절 사례는 이번 R30 문자열 타입 반례 밖의 후속 확장 항목이다.

## 독립 검토 → 수정 → 같은 조건 재검토

같은 pc2의 기존 보조 에이전트 `check_github_cli` 한 명이 고정 문서 및 JSON을 읽기 전용으로 검토했다. 다른 물리 PC의 실적이나 사람 사용성 검사로 세지 않는다.

- 최초 R18은 “그 요청”을 최근 배송 요청으로 간주했다. 독립 검토에서 최근성만으로 철회 대상을 확정할 근거가 없다고 반박했다. 원문을 유지한 채 두 후보 모두 자동 활성 유보로 수정했다. R19와 같은 모호성 원칙을 적용한다.
- R21의 과거/현재 중복 발생은 문서보다 강한 정책임을 지적받아 pc1이 선택할 제안임을 명시했다.
- “복합 인용 × 한 과업 철회” 조합 누락을 지적받아 R31을 추가했다. t1 `[15,30)`는 정확히 “배송 시각을 확인해 주세요.”다.
- 수정된 R18/R21/R31을 같은 검토자가 재검토했고 잔여 의미·철회·출처 모순을 발견하지 못했다. 제품 실행은 하지 않았다. 총괄은 아래 실행기로 수정 데이터를 다시 대조했다.
- 최종 보고서도 같은 검토자가 정적으로 대조했다. JSON 해시·31/64/27/28 집계·표의 20/11·대조군 13/4·64+64 분모 설명과 재현 코드 추출을 확인했다. 실행기를 재실행하지 않았으며 실제 함수 반환과 실행 이력은 총괄의 아래 실측에 의존한다.

## 실제 검증과 한계

최종 실행은 **2026-09-22 04:39:10 KST**에 완료했다. 보고서에서 실행기를 추출하는 아래 명령을 실제 사용했다.

| 검사 | 실제 결과 | 뜻 |
|---|---|---|
| JSON·고유 ID·필수 정보·시간·빈 결과 설명 | 31/31 | 데이터 계약/설명 존재 대조 |
| 제안 항목 분할·거절 사유 | 64/64 | active/rejected proposalIndex 전수 대조 |
| 활성 인용 출처 | 27/27, span 28/28 | 독립 구간 열거 및 문자열 복원·인접/화자 대조 |
| 출력 변이 대조군 | 13/13 검출 | 잘못 만든 후보 출력이 독립 기대값과 다름 |
| 데이터 변형 대조군 | 4/4 거절 | 중복 ID·span 손실·화자 접합·설명 누락 검출 |
| 고정 순수 함수 관측 | 최종 실행 64회, 입력 불변 31/31 | 제품 API/모델 호출 아님 |
| 반환 목록과 기대 활성 목록 | 동일 20행 / 차이 11행 | 31행 중 단순 raw 목록 대조; 정확도/PASS율 아님 |

초안 실행의 순수 함수 64회와, R18/R31 관련 출력 대조군 추가 및 보고서 추출 명령을 검증한 최종 실행 64회를 구분한다. 이 작업의 실제 합계는 **순수 함수 128호출**, 외부 API/과금 호출 0이다. 아래 실행 결과는 최종 한 실행의 분모다.

- 입력 파일 SHA256(UTF-8/LF): `3c08e84c88c56454dea186c099b66324e18682eaef34b78153ee17af0d0c3617`.
- 관측한 Git blob 바이트 SHA256: `78f8e778ff1d86eb1b02f88ead80bebec1e5e3c599304c5b79c0408f42d17f22`.
- JSON 기대값은 제품 관측 전에 고정했으며 두 관측 실행 사이에 변경하지 않았다. 출력 변이 대조군만 11→13으로 확장했다.

형식 검사는 임의의 한국어 문장이 의미상 옳음을 증명하지 않는다. 의미 기대값은 과업·원문 계약을 먼저 작성하고 독립 반박으로 검토했다. 실행기는 원문 위치·범위·인접성·화자·제안 분할·이유 코드·정렬·경계 일관성을 대조한다.

실행한 출력 변이 대조군은 아래 재현 코드의 13개다. R04 유효 인접 인용을 지우기, R05/R06 가짜 인용·의역 허용, R15 한 건 철회 시 전부 지우기의 필수 세 방향을 포함한다. 추가로 R16 철회 누락, R26/R27 상한 우회, R28 정정 문맥 생략, R12 금지 요청 삭제, R23 빈 배열 fallback, R01 전부 null, R18 모호성 추정, R31 독립 요청 유실을 검출했다. **후보 출력 변이**이며 제품 소스 변이·제품 수정 성공으로 세지 않는다. 데이터 자체의 중복 ID·잘린 span·다른 화자 접합·빈 결과 설명 누락은 4개 별도 변형을 만들어 검사기가 각각 거절하는지 실제 확인했다.

### 고정 순수 함수 관측

`git show`로 고정 blob을 메모리에서 읽었다. 전체 소스를 검토하고 AST로 module-level 동작이 docstring, `re` import, 정규식 compile, 함수 정의뿐임을 확인한 뒤 `current_request_quote(quote, transcript)`를 호출했다. 앱/server 패키지를 import하지 않았다. 입력의 호출 전후 deep equality를 전 행 대조했다.

각 제안을 **개별 순수 호출**한 반환 목록에서 null만 제외했다. 배열 스키마 검증·중복제거·순서 교정·UI·리뷰 사유 생성은 이 함수에 없다. 따라서 아래의 배열 순서 일치 수는 새 계약의 PASS 비율이나 모델 정확도가 아니다. R23/R26/R27/R30의 raw 반환은 해당 스키마가 실제 API에서 허용된다는 증거가 아니다.

아래 q번호는 각 행의 `proposedRequestQuotes` 순서(1-based)다. 기대 빈 목록은 해당 행의 rationale 및 review 사유와 함께 읽는다.

| 행 | 기대 활성 | 실제 개별 반환에서 null 제외 | 원시 목록 대조 |
|---|---|---|---|
| R01 | q1, q2, q3 | q1, q2, q3 | 동일 |
| R02 | q1 | q1 | 동일 |
| R03 | q1 | q1 | 동일 |
| R04 | q1 | [] | 차이 |
| R05 | q1, q2 | q1, q2 | 동일 |
| R06 | q2 | q2 | 동일 |
| R07 | [] | [] | 동일 |
| R08 | [] | [] | 동일 |
| R09 | [] | [] | 동일 |
| R10 | [] | q1 | 차이 |
| R11 | q1 | q1 | 동일 |
| R12 | q1 | q1 | 동일 |
| R13 | q1 | q1 | 동일 |
| R14 | [] | [] | 동일 |
| R15 | q2 | q2 | 동일 |
| R16 | q2 | q1, q2 | 차이 |
| R17 | q1 | q1 | 동일 |
| R18 | [] | q1 | 차이 |
| R19 | [] | q1 | 차이 |
| R20 | q2, q1 | q1, q2, q3 | 차이 |
| R21 | [] | [] | 동일 |
| R22 | q1 | q1 | 동일 |
| R23 | [] | q1 | 차이 |
| R24 | [] | [] | 동일 |
| R25 | q1, q2, q3, q4, q5, q6, q7, q8 | q1, q2, q3, q4, q5, q6, q7, q8 | 동일 |
| R26 | [] | q1, q2, q3, q4, q5, q6, q7, q8, q9 | 차이 |
| R27 | [] | q1, q2, q3, q4, q5, q6, q7, q8, q9 | 차이 |
| R28 | [] | q1 | 차이 |
| R29 | [] | [] | 동일 |
| R30 | [] | q1 | 차이 |
| R31 | q2 | q2 | 동일 |

구체적인 관측 경계는 다음과 같다.

- **첫 Bolt R01:** 독립 합성 세 인용의 기대값을 먼저 고정했다. 현행 순수 함수는 올바른 인용을 별도 전달했을 때 3개 모두 반환했다. 실제 모델이 세 인용을 추출하거나 HTTP `request`에 보존하는 단계는 실행하지 않았다. 메인의 기존 canary 실패가 해결됐다는 결과가 아니다.
- **R04 인접 분할:** 기대 q1 보존, 실제 null. 현재 함수는 각 전사 구간 내부만 찾는다. 같은 화자의 실제 인접 두 구간 보존 병목을 재현했다.
- **R10 미래 요청 계획:** 기대 제외, 실제 q1 반환. “라고 요청할 생각입니다”를 현재 요청으로 보존했다. R11 현재 요청의 내용이 내일인 정상 사례와 구분해야 한다.
- **R16 화자 교대 뒤 철회:** 기대 배송 q2만, 실제 반송 q1·배송 q2. 같은 화자의 명시 취소가 상담원 개입 뒤에 나오면 놓친다. R15 개입 없는 경우에는 q2만 반환했다.
- **R28 정정 문맥 손실:** 기대 검토 유보, 실제 정정 값 없는 짧은 문구 반환. 단순 exact substring 성공을 상담 과업 보존으로 계산할 수 없다.
- **정책·다른 계층:** R18/R19 모호성, R20 정렬/중복, R23 혼용 key, R26/R27 개수, R30 타입은 위 제안 계약 또는 배열 처리 계층의 검토점이다. 현행 단일 함수의 책임 밖인 사항을 이미 구현된 기능의 실패율에 섞지 않는다. R13/R17의 반환 문자열 일치도 역할 검토 이유가 생성됐다는 뜻이 아니다.

## pc1 연결점과 미실행

pc1은 두 파일을 고정 SHA로 수신한 후 정책 제안 표시가 있는 행의 기대값을 먼저 결정하고 변경 이유를 남긴다. 제품의 `requestQuotes` 처리 결과를 행별 active/rejected/review/provenance로 비교하는 어댑터를 공통 테스트에 붙인다. 이번 순수 호출 관측을 새 normalizer의 대체 검사로 사용하지 않는다. 구형 저장 응답은 명시 호환 변환 뒤 같은 인용 검사를 적용하고 원본 응답은 보존한다.

검증된 복수 인용은 공개 `fields.request: string|null` 안에서 별도 번호/줄바꿈으로 구분할 수 있으나, 문자열 하나의 연속 발언으로 표시하면 안 된다. 원문 위치는 별도 UI 대조 근거로 유지한다. 근거/사람 수정/AI 추가 확인의 레이블을 분리하고 초안 편집 후 기존 사람 확인을 자동 유지하지 않는다. 요청에서 수령 수량·단위·미확인 점포를 자동 확정하지 않는다.

미실행: 새 복수 요청 제품 구현 및 통합, HTTP/schema 실제 처리, 실제 STT/모델 개선 재평가, UI 렌더·청취·사용성, 저장/부모 서비스 전체 흐름, TEST, pc1 인수·이슈 종결. 새 서버·브라우저·API·유료 호출·보안 설정 변경은 0이다. 기존 상주 watcher를 재시작하거나 복제하지 않았다.

점수 연결은 활용20(실제 순수 함수/도구 기록), Goal20(기존 과업 정합성; pc2 새 Goal 실행 주장 없음), 위임30(같은 PC 독립 반박과 수정 재검토), 검증30(입력 고정·실패 관측·검사기 대조군)이다. 배점 획득이나 제출 완료를 주장하지 않는다.

## 재현 명령과 실행기

저장소 루트에서 아래 명령은 보고서에 포함된 Python 실행기만 추출해 표준입력으로 실행한다. stdlib와 Git의 고정 blob만 사용하고 쓰기·외부 네트워크·앱 import는 하지 않는다. `python -O`로 assertion을 끄지 않는다.

```powershell
Set-Location -LiteralPath 'C:\Users\Administrator\Desktop\hackerton\happycall-ralphthon'
. ..\enter-happycall.ps1
$reportText = Get-Content -LiteralPath reports\pc2\multiple-request-contract-review.md -Raw -Encoding utf8
$checkText = [regex]::Match($reportText, '(?ms)^<!-- verifier:start -->\r?\n```python\r?\n(.*?)^```\r?\n<!-- verifier:end -->').Groups[1].Value
$checkText | python -B -
git diff --check -- tests/evaluation/multi-request-cases.json reports/pc2/multiple-request-contract-review.md
```

<!-- verifier:start -->
```python
"""Synthetic fixture audit + oracle controls + fixed pure-function observations.
Run from repository root. This is not a product multi-request implementation.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

FIXTURE = Path('tests/evaluation/multi-request-cases.json')
BASE = 'dce4e66c0815e477f51977cbd9e023db101b9d58'


def occurrences(quote, transcript):
    # Independent enumeration of every contiguous segment interval, not a run
    # flattened once by the fixture generator. Keep only minimal touched spans.
    found = []
    for first in range(len(transcript)):
        for last in range(first, len(transcript)):
            rows = transcript[first:last + 1]
            speaker = rows[0]['speaker']
            if len(rows) > 1 and (not speaker or any(r['speaker'] != speaker for r in rows)):
                continue
            joined = ' '.join(r['text'] for r in rows)
            offset = joined.find(quote)
            while offset >= 0:
                end = offset + len(quote)
                spans, position = [], 0
                for r in rows:
                    stop = position + len(r['text'])
                    if offset < stop and end > position:
                        spans.append({'segmentId': r['id'],
                                      'startChar': max(offset - position, 0),
                                      'endChar': min(end - position, len(r['text']))})
                    position = stop + 1
                if spans and spans[0]['segmentId'] == rows[0]['id'] and spans[-1]['segmentId'] == rows[-1]['id']:
                    item = {'speaker': speaker, 'spans': spans}
                    if item not in found:
                        found.append(item)
                offset = joined.find(quote, offset + 1)
    return found


def audit(data):
    assert data['synthetic'] is True and data['codeBaseline'] == BASE
    assert data['documentBaseline'] == 'c20d411c8b5d430897db6d00fb96bee079a68a6d'
    cases = data['cases']
    assert len(cases) >= 12
    assert len({c['id'] for c in cases}) == len(cases)
    active_count = spans_count = 0
    for c in cases:
        assert c['scenario'].strip() and c['rationale'].strip()
        ts = c['transcript']
        assert ts and len({t['id'] for t in ts}) == len(ts)
        previous_end = -1
        for t in ts:
            assert isinstance(t['speaker'], str) and isinstance(t['text'], str) and t['text']
            assert 0 <= t['startSeconds'] < t['endSeconds']
            assert t['startSeconds'] >= previous_end
            previous_end = t['endSeconds']
        proposed, active = c['proposedRequestQuotes'], c['expectedActiveQuotes']
        rejected, details = c['expectedRejectedQuotes'], c['expectedRejectedDetails']
        reasons = c['expectedReviewReasons']
        assert all(isinstance(q, str) and q.strip() for q in proposed + active + rejected)
        assert len(active) == len(set(active))
        assert len(reasons) == len(set(reasons)) and set(reasons) <= data['reasonCatalog'].keys()
        assert rejected == [r['quote'] for r in details]
        indices = [r['proposalIndex'] for r in details]
        assert len(indices) == len(set(indices))
        for r in details:
            assert 0 <= r['proposalIndex'] < len(proposed)
            assert proposed[r['proposalIndex']] == r['quote']
            assert r['reason'] in data['reasonCatalog']
            assert r['reason'] == 'DUPLICATE_QUOTE' or r['reason'] in reasons
            source = occurrences(r['quote'], ts)
            if r['reason'] in ('NONCONTIGUOUS_QUOTE', 'QUOTE_NOT_IN_SOURCE', 'EMPTY_SPEAKER_JOIN'):
                assert not source
            else:
                assert source
        retained = [q for i, q in enumerate(proposed) if i not in indices]
        assert len(retained) == len(active) and set(retained) == set(active)
        assert [p['quote'] for p in c['expectedProvenance']] == active
        locations = []
        for proof in c['expectedProvenance']:
            source = occurrences(proof['quote'], ts)
            assert source and source == proof['occurrences']
            for occurrence in proof['occurrences']:
                spans = occurrence['spans']
                row_indices = [next(i for i, t in enumerate(ts) if t['id'] == s['segmentId']) for s in spans]
                assert row_indices == list(range(row_indices[0], row_indices[-1] + 1))
                for j, (s, i) in enumerate(zip(spans, row_indices)):
                    assert 0 <= s['startChar'] < s['endChar'] <= len(ts[i]['text'])
                    assert ts[i]['speaker'] == occurrence['speaker']
                    if j > 0:
                        assert s['startChar'] == 0
                    if j < len(spans) - 1:
                        assert s['endChar'] == len(ts[i]['text'])
                if len(spans) > 1:
                    assert occurrence['speaker']
                rebuilt = ' '.join(ts[i]['text'][s['startChar']:s['endChar']] for s, i in zip(spans, row_indices))
                assert rebuilt == proof['quote']
                spans_count += len(spans)
            locations.append((next(i for i, t in enumerate(ts) if t['id'] == source[0]['spans'][0]['segmentId']), source[0]['spans'][0]['startChar']))
        assert locations == sorted(locations)
        dc = c['draftContext']
        if 'TOO_MANY_QUOTES' in reasons:
            assert len(dc['requestQuotes']) > 8 and not active
        elif 'MIXED_CONTRACT_KEYS' in reasons:
            assert 'requestQuotes' in dc and 'requestQuote' in dc and not active
        elif 'INVALID_QUOTES_TYPE' in reasons:
            assert not isinstance(dc['requestQuotes'], list) and not active
        elif 'requestQuotes' in dc:
            assert isinstance(dc['requestQuotes'], list) and len(dc['requestQuotes']) <= 8
        else:
            assert isinstance(dc['requestQuote'], str)
        active_count += len(active)
    by_id = {c['id']: c for c in cases}
    assert len(by_id['R01']['expectedActiveQuotes']) == 3
    assert len(by_id['R04']['expectedProvenance'][0]['occurrences'][0]['spans']) == 2
    assert len(by_id['R25']['expectedActiveQuotes']) == 8
    assert len(by_id['R26']['proposedRequestQuotes']) == len(by_id['R27']['proposedRequestQuotes']) == 9
    assert by_id['R12']['expectedActiveQuotes'] and not by_id['R19']['expectedActiveQuotes']
    assert by_id['R13']['expectedReviewReasons'] == ['SPEAKER_ROLE_UNVERIFIED']
    assert not by_id['R24']['expectedActiveQuotes'] and not by_id['R24']['expectedReviewReasons']
    return {'cases': len(cases), 'activeQuotes': active_count, 'sourceSpans': spans_count,
            'proposalCount': sum(len(c['proposedRequestQuotes']) for c in cases)}


def run(data):
    summary = audit(data)
    cases = {c['id']: c for c in data['cases']}
    # These are candidate-output mutations against an independent oracle. They
    # demonstrate discriminating expectations, NOT that product code was fixed.
    mutants = [
        ('drop-valid-adjacent', 'R04', []),
        ('accept-cross-speaker-fabrication', 'R05', cases['R05']['proposedRequestQuotes']),
        ('accept-paraphrase', 'R06', cases['R06']['proposedRequestQuotes']),
        ('drop-independent-survivor', 'R15', []),
        ('ignore-later-withdrawal', 'R16', cases['R16']['proposedRequestQuotes']),
        ('truncate-nine', 'R26', cases['R26']['proposedRequestQuotes'][:8]),
        ('dedup-before-limit', 'R27', list(dict.fromkeys(cases['R27']['proposedRequestQuotes']))),
        ('accept-contextless-correction', 'R28', cases['R28']['proposedRequestQuotes']),
        ('deny-current-negative-action', 'R12', []),
        ('mixed-key-truthiness-fallback', 'R23', cases['R23']['proposedRequestQuotes']),
        ('all-null-first-bolt', 'R01', []),
        ('guess-ambiguous-cancellation', 'R18', cases['R18']['proposedRequestQuotes'][:1]),
        ('drop-compound-survivor', 'R31', []),
    ]
    for name, cid, candidate in mutants:
        assert candidate != cases[cid]['expectedActiveQuotes'], name
    # Deliberately corrupt data, so the verifier itself must reject bad fixtures.
    corruptions = []
    bad = copy.deepcopy(data)
    bad['cases'][1]['id'] = bad['cases'][0]['id']
    corruptions.append(('duplicate-case-id', bad))
    bad = copy.deepcopy(data)
    bad['cases'][0]['expectedProvenance'][0]['occurrences'][0]['spans'][0]['endChar'] -= 1
    corruptions.append(('truncated-source-span', bad))
    bad = copy.deepcopy(data)
    bad['cases'][3]['transcript'][1]['speaker'] = 'agent'
    corruptions.append(('cross-speaker-adjacency', bad))
    bad = copy.deepcopy(data)
    bad['cases'][23]['rationale'] = ''
    corruptions.append(('empty-no-request-rationale', bad))
    for name, bad in corruptions:
        try:
            audit(bad)
        except AssertionError:
            continue
        raise AssertionError('verifier missed ' + name)
    source = subprocess.check_output(['git', 'show', BASE + ':server/request_grounding.py'])
    tree = ast.parse(source.decode('utf-8'))
    assert [n.names[0].name for n in tree.body if isinstance(n, ast.Import)] == ['re']
    assert not any(isinstance(n, ast.ImportFrom) for n in ast.walk(tree))
    # Audited module-level operations: docstring, re import, regex compilation,
    # function definitions. No application import, settings, ledger or API.
    for n in tree.body:
        assert isinstance(n, (ast.Expr, ast.Import, ast.Assign, ast.FunctionDef))
        if isinstance(n, ast.Expr):
            assert isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
        if isinstance(n, ast.Assign):
            call = n.value
            assert isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
            assert isinstance(call.func.value, ast.Name) and call.func.value.id == 're' and call.func.attr == 'compile'
    ns = {'__name__': 'fixed_request_grounding_observation'}
    exec(compile(tree, BASE + ':server/request_grounding.py', 'exec'), ns)
    observations = []
    for c in data['cases']:
        before = copy.deepcopy(c)
        returns = [ns['current_request_quote'](q, c['transcript']) for q in c['proposedRequestQuotes']]
        assert before == c
        retained = [q for q in returns if q is not None]
        observations.append({'id': c['id'], 'returns': returns,
                             'rawRetained': retained,
                             'expectedActive': c['expectedActiveQuotes'],
                             'sameRawSequence': retained == c['expectedActiveQuotes']})
    return {'python': sys.version.split()[0], 'fixtureSha256': hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
            'groundingSourceSha256': hashlib.sha256(source).hexdigest(), 'audit': summary,
            'oracleOutputControls': [n for n, _, _ in mutants],
            'fixtureCorruptionControls': [n for n, _ in corruptions],
            'pureCalls': summary['proposalCount'],
            'rawSequenceSame': sum(o['sameRawSequence'] for o in observations),
            'rawSequenceDifferent': sum(not o['sameRawSequence'] for o in observations),
            'observations': observations}


if __name__ == '__main__':
    print(json.dumps(run(json.loads(FIXTURE.read_text(encoding='utf-8'))), ensure_ascii=False, indent=2))
```
<!-- verifier:end -->
