# PC2 N02-R2 원보고 인수와 메인 독립 재검

## 고정 입력 인수

- PC2 원보고: 커밋 `4c200dec13433d7139151a92aac89d8a13a076f4`의 `reports/pc2/multiple-request-implementation-review.md`.
- 수정 전 실제 메인: `f043c60b357c5341e80959c748036b28d032bd18`, 인수 시 작업트리 clean. Python 3.12.10.
- 원보고 바이트 SHA256: `2e3cb660397a07b45b2ee2d6786823aac143f75ca7ea33728bc9d343735b6e6a`.
- 줄 시작의 `r2-verifier:start/end` 마커 사이 실행기를 그대로 추출했다. 추출 실행기 SHA256: `94345b7acef3104d39097990b65e1d1067682eaa0844708162dbd1d2cfed98e6`.

실행기를 읽고 20행의 기대 active/rejected/review와 공개 요청값이 제품 결과를 재사용하지 않는 고정 입력임을 확인했다. 실제 normalizer를 호출하면서 OpenAI·키·원장 진입점은 실패 대역으로 막고 호출 횟수 0을 검증한다. 쓰기는 지정한 `.local` 결과 JSON 하나뿐이다. 입력 deep equality, 공개 JSON schema, 수량·단위 null 유지, 실제 active의 원문 조각·화자·구간 시간, 실행 전후 소스 해시를 검사한다. 정상·거절·다른 대상 대조를 함께 보존한다.

원 실행기 출력의 `sourceCommit`은 작성자가 넣은 과거 `4af2756acc086de8903461ec4729623989b0017f` 상수다. 이는 현재 실행에서 측정한 HEAD가 아니다. 원본 실행기를 수정하지 않고 실제 HEAD와 원보고/실행기 해시를 별도 `original-metadata.json`에 기록했다. 이후 검증은 각 결과의 측정 소스 해시와 함께 읽어야 한다.

## 수정 전 동일 실패 재현

2026-09-22 07:35 KST, 원 20행은 **12통과 / 8실패**였다. PC2 실패 ID와 정확히 같았다. 요청 `Q`는 `반송 방법을 알려 주세요.`, 단위 요청 `U`는 `단위를 기록해 주세요.`이며 각 구간은 원 실행기 그대로 `t1...`, 시작 `4×인덱스`초, 종료 `시작+3.5`초다. 아래 화자 표기를 생략한 구간은 customer다.

| ID | 원보고의 정확한 입력과 계약 | 기대 | 수정 전 실측 |
|---|---|---|---|
| D01 | 신형 배열, `치약을 반송해 주세요.` → `치약 반송 요청은 취소합니다.` | 요청 거절, `WITHDRAWN`, 공개 요청 null | 요청이 그대로 active, 거절/검토 사유 없음 |
| D04 | 신형 배열, `치약 반송 방법을 알려 주세요.` → `컵 반송 방법을 알려 주세요.` → agent `확인하겠습니다.` → `컵 반송 방법 요청만 취소합니다.` | 치약 요청만 유지, 컵만 `WITHDRAWN` | 두 요청 모두 `WITHDRAWN`, 공개 요청 null |
| D06 | 신형 배열, Q → `교환 방법을 알려 주세요.` → agent `확인하겠습니다.` → `교환 방법 요청만 취소합니다.` | Q만 유지, 교환만 `WITHDRAWN` | 두 요청 모두 `WITHDRAWN`, 공개 요청 null |
| D08 | 신형 배열, Q → agent `확인하겠습니다.` → `저는 "반송 방법 요청은 취소합니다?!"라고 말한 적이 없습니다.` | Q 유지, 거절/검토 사유 없음 | Q `WITHDRAWN`, 공개 요청 null |
| D09 | D08과 동일 발화, 구형 `requestQuote` | D08과 동일 | D08과 동일 |
| D12 | 구형 `requestQuote`, 화자 unknown/unknown, Q → `반송 방법 요청은 취소합니다.` | Q 유지, `SPEAKER_ROLE_UNVERIFIED`, `OTHER_SPEAKER_CANCELLATION` | Q `NON_CURRENT_CONTEXT` 거절, 기대 검토 사유에 `NON_CURRENT_CONTEXT` 추가 |
| D15 | D12와 동일, 화자 화자/화자 | D12와 동일 | D12와 동일 |
| D17 | 신형 배열 제안 U, 원문 `한 개가 아닌 한 박스예요. 단위를 기록해 주세요.` | U `MISSING_CORRECTION_CONTEXT` 거절 | U만 active, 거절/검토 사유 없음 |

수정 전 검사 20행 모두 입력 불변과 공개 schema가 유지됐다. 실제 active 9개/출처 span 9개를 대조했다. 거절되어 active가 없는 행은 출처 대조를 수행한 양성 증거로 세지 않는다. 제품 4개 파일과 R1 고정 JSON의 실행 전후 SHA가 같았으며 모델·키·원장 호출은 0이었다.

실행 증거는 `.local/main-resume-20260922/pc2-r2-intake/`의 `original-verifier.py`, `original-metadata.json`, `before-main-f043c60.json`이다. 원보고의 20행 분모를 줄이거나 기대값을 고치지 않았다.

## 첫 수정 후 독립 재검

2026-09-22 07:39 KST, 편집 종료 통보 뒤 **원 PC2 20/20**, **이전 독립 15/15**, **R1 31/31**이 통과했다. 공개 schema는 고정 `c20d411` 값과 같았고 입력 불변·수량/단위 null·모델/키/원장 호출 0을 유지했다. 새 값의 일반화 검사는 R2의 다섯 규칙에서 새 상품/조사, 연속 문장부호 순서, 익명 화자 변형, `아닌` 정정의 인접 구간과 정상 전체 인용만 별도 18행으로 고정했다.

첫 일반화 결과는 **17/18**이었다. G04의 customer 세 구간은 `재배송 방법을 알려 주세요.` → `교환 방법을 알려 주세요.` → `교환 방법 요청만을 취소합니다.`이고 배열 제안은 앞 두 요청이다. 재배송만 유지되어야 하지만 둘 모두 `WITHDRAWN`이고 공개 요청은 null이었다. 결합 조사 `만을`에서 명시 작업 분리 정규식이 빠져 공통 `방법`만으로 다른 작업까지 철회했다. 원 20행의 통과를 이 결함의 해소로 확대하지 않았다.

메인이 별도로 발견한 한 글자 상품 `컵` 실패를 독립 재현하면서 명사 경계 대조 3개를 추가했다. 이 3개는 기존 18개에 섞지 않는다.

| ID | 정확한 customer 발화, 첫 발화를 배열 제안 | 기대 | 첫 수정 실측 |
|---|---|---|---|
| J01 | `컵을 반송해 주세요.` → `컵 반송 요청만은 취소합니다.` | `WITHDRAWN`, 공개 요청 null | 컵 요청 active 유지 |
| J02 | `파이 반송 방법을 알려 주세요.` → `파 반송 요청만 취소합니다.` | 파이 요청 보존 | 파이 `WITHDRAWN`, 공개 요청 null |
| J03 | `파이를 반송해 주세요.` → `파이 반송 요청만 취소합니다.` | `WITHDRAWN`, 공개 요청 null | 기대와 일치 |

J01은 비교 term의 두 글자 제한으로 `컵`이 사라지고 `반송해`/`반송`은 서로 다른 term인 문제다. J02는 실제 명사 `파이`의 끝 `이`를 조사처럼 처리한 surface/stem 합집합이 `파`와 겹치는 문제다. 같은 J02 입력을 고정 `f043c60`의 grounding/provenance Git blob으로 다시 실행해 보니 기존 코드도 `요청만` 패턴을 인식하지 못해 오철회했다. 따라서 이 정확한 입력의 실패를 이번 패치가 새로 만든 회귀라고 단정하지 않는다. 첫 수정이 명시 상품 간 오철회를 해소하지 못한 추가 인수 차단 사례이며, 조사 정규화가 단순히 기대 입력 하나를 통과하도록 넓어지지 않게 확인한다. 고정 소스 확인 결과는 `noun-j02-fixed-main.json`에 보존했다. 세 결함 입력을 메인·구현 담당자에게 즉시 전달했다.

첫 수정의 measured SHA256은 provenance `02d18b82b7ceec3b73630e1a14db9c2e2a011da5e708be8b84bcc3eec4785445`, grounding `aaed1223c5e8f5d79d471486a3c642b8cf653e54cd539425e8a20f6e8bb3151d`이다. 증거는 `after-r2-first.json`, `after-r2-generalization-first.json`, `noun-boundaries-first.json`, 상위 디렉터리의 `independent-request-review-r2-first.json`이다. 추가 실행기는 같은 디렉터리의 `generalization-verifier.py`, `noun-boundary-verifier.py`다.

## 최종 동일 입력 재검

2026-09-22 07:42 KST, 구현 담당자의 두 번째 편집 종료 통보 후 제품을 수정하지 않고 아래 고정 분모를 재검했다. 입력과 기대값을 결과 JSON끼리 비교해 원 20행, 일반화 18행, 명사 경계 3행이 첫 실행과 완전히 같음을 별도로 확인했다. 원 실행기 바이트 SHA도 인수 시점과 같았다.

| 검증 묶음 | 최종 결과 | 증거 JSON |
|---|---:|---|
| PC2 원 R2 실행기 | 20/20 | `pc2-r2-intake/after-r2-second.json` |
| 이전 독립 요청 검사 | 15/15 | `independent-request-review-r2-second.json` |
| PC2 R1 고정 계약 | 31/31 | `independent-request-review-r2-second.json` |
| R2 규칙 일반화 | 18/18 | `pc2-r2-intake/after-r2-generalization-second.json` |
| 명사 경계 대조 | 3/3 | `pc2-r2-intake/noun-boundaries-second.json` |

표의 증거 기준 디렉터리는 `.local/main-resume-20260922/`다. 각 분모를 합쳐 의미 이해 정확도로 해석하지 않는다. PC2 20행의 최종 실제 active는 13개, 그 출처 span도 13개로 원문/화자/시간이 일치했다. 별도 일반화는 실제 span 15개, 명사 경계는 1개였다. 공개 normalizer 투영 56개가 유효한 schema와 수량·단위 null을 유지했고, 공개 `ANALYSIS_SCHEMA` 값은 고정 `c20d411`과 같았다. R1 31행은 고정 active/rejected/review/provenance 계약 비교이며 공개 투영 56개에 포함하지 않는다. 모든 실행의 입력과 해당 소스는 실행 전후 불변이고 모델·키·원장 호출은 0이었다.

수정은 명시 작업/상품 비교가 확정된 경우 한 글자 상품을 일반 term 길이 제한으로 다시 버리지 않고, 요청 조사의 두 요소 결합을 공통으로 비교한다. 상품명의 모호한 `이/가` 말음 절삭은 하지 않아 `파이`와 `파`를 분리하면서 `파이를`과 `파이`의 대조는 유지한다. 익명 라벨은 신형·구형 후속 구간과 정정 문맥에서 같은 사람의 증거로 쓰지 않는다. 이 변경의 source diff를 읽어 현재 고정 반례의 해소와 맞는지 대조했다.

최종 측정 소스 SHA256:

- `server/request_grounding.py`: `5dc1bfdb294aede851126a73147cb513ac08fc3852b4b6a4ed4a8971c19c005a`
- `server/request_provenance.py`: `02d18b82b7ceec3b73630e1a14db9c2e2a011da5e708be8b84bcc3eec4785445`
- `server/live.py`: `7acff20ab7c8391e5636d1bcd2740df72f7829d6a81c6200684a81baa9830e2b`
- `server/analysis_schema.py`: `04b3be292133036231857793654e12da8310529c961a84d7008034f68abd2630`
- R1 JSON: `3c08e84c88c56454dea186c099b66324e18682eaef34b78153ee17af0d0c3617`

실행 명령은 다음과 같다. 결과 파일을 보존하려면 재실행 시 새로운 출력 이름을 사용한다.

```powershell
.venv/Scripts/python.exe -X utf8 -B .local/main-resume-20260922/pc2-r2-intake/original-verifier.py . .local/main-resume-20260922/pc2-r2-intake/after-r2-second.json
.venv/Scripts/python.exe -X utf8 -B .local/main-resume-20260922/independent-request-review.py independent-request-review-r2-second.json
.venv/Scripts/python.exe -X utf8 -B .local/main-resume-20260922/pc2-r2-intake/generalization-verifier.py after-r2-generalization-second.json
.venv/Scripts/python.exe -X utf8 -B .local/main-resume-20260922/pc2-r2-intake/noun-boundary-verifier.py noun-boundaries-second.json
```

원보고의 8실패와 이 검토에서 고정한 G04/J01/J02 차단 사례는 모두 같은 입력으로 해소 확인했다. 새 언어 형태로 검증 범위를 계속 늘리지 않았다. 전체 회귀·브라우저·운영 재시작 결과는 메인의 별도 검증이며 이 문서의 독립 실행 결과로 계산하지 않는다. `git diff --check`는 exit 0이었다.

일반 한국어 의미 이해 전체를 보장하는 검사가 아니다. 동일 요청의 원문 출처가 둘 이상이면 `AMBIGUOUS_OCCURRENCE`로 유보하는 승인된 정책은 유지하며, R2 D20도 같은 기대값이다. 제품 수정, 과금, 실모델, 네트워크, 배포, Git commit/push, 메일 발송은 이 독립 검토에서 수행하지 않았다.
