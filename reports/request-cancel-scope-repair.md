# 요청 취소 범위의 제한적 보완

2026-09-21 23:16 KST 갱신 · pc1/CJJ · `/root/request_cancel_scope_repair` · 착수 HEAD `7d186fd`.

원래 F1의 `배송 시각을 알려 주세요.`는 별도 `배송 상품 반송 요청` 취소 뒤에도 유지됩니다. 첫 수정의 독립검토에서 동사형 물류행위가 되살아나는 P1을 발견하여, 정보 단어 포함 여부가 아닌 명시된 단순 명사구 형식만 별도 문의로 보존하도록 더 좁혔습니다. 최종 관련 테스트 파일은 **22 passed / 79 subtests**이며 동사형·복합행위 10개 반례가 null을 유지합니다. 아래 4개 모듈 104/203 및 저장 응답 36/36 동일 결과는 첫 수정 `7b90e8c7`에서의 이전 측정입니다. 이번 재수정 후에는 메인 지시에 따라 관련 테스트만 다시 실행했습니다. 일반 한국어 취소·공동참조 해결로 인수할 범위는 아닙니다.

## 변경과 보호 범위

소유 파일은 `server/request_grounding.py`, `tests/test_request_grounding.py`, 이 보고서뿐입니다. 실제 업무 저장데이터·원응답·기존 보고서·키·라이브 모델·브라우저·서버·의존성·커밋은 변경하거나 호출하지 않았습니다.

- 기존 `_target_terms` 불용어는 그대로입니다. 일반적인 단어 교집합만 있으면 같은 대상으로 보는 보수적 기본값을 유지합니다.
- 별도 문의로 인정하는 입력은 `배송/출고 + 시각/시간/일정`, `상품 라벨`, `주문 내역`이라는 단순 명사구에 `알려/안내해/확인해 주세요/주십시오`가 붙는 전체 문장뿐입니다. 선택적인 목적격 조사와 종결 문장부호를 허용합니다. 명사구 앞·사이에 다른 수식절이나 행위가 들어가면 분리하지 않습니다. `돌려보낼 시간` 등 새 동의어를 금지 목록에 추가한 방식이 아닙니다.
- 다른 문장 끝에는 `반송·반품·회송·교환·재배송`의 명시 요청이 있어야 합니다. 다른 문장에도 위 정보 대상이 있거나 부정·대조 표현이 있으면 분리하지 않습니다.
- 뒤의 요청과 `그 요청`을 연결할 때도 같은 비교를 사용합니다. 공통 업무 단어만으로 이전 요청까지 철회하지 않습니다. 이미 주어진 화자 표식의 인접 경계는 그대로 유지합니다.
- 취소 검사에는 추출 인용 전체를 전달합니다. 여러 요청을 한 인용에 담았을 때 첫 요청만 비교해 뒤의 취소된 요청까지 활성화하는 것을 막기 위한 보수적 처리입니다.

## 기대값 선고정과 재현

제품 코드 수정 전에 별도 범위, 동일·부분 범위, 대명사, 화자 경계의 기대값을 테스트에 추가했습니다. 구 코드에서 F1을 포함한 별도 요청 4개와 동일 화자 경계 1개, 대명사 1개가 실패했습니다. 해당 실행은 `6 failed, 102 passed, 193 subtests passed`였으며, 기존 검사나 실패 기대값을 통과시키기 위해 바꾸지 않았습니다.

| 대조 | 기대 | 최종 실측 |
|---|---|---|
| 배송 시각 문의 / 배송 상품 반송 요청 취소 | 시각 문의 유지 | 유지 |
| 출고 시각 문의 / 출고 상품 교환 요청 취소 | 시각 문의 유지 | 유지 |
| 상품 라벨 확인 / 상품 반송 요청 취소 | 라벨 요청 유지 | 유지 |
| 주문 내역 확인 / 주문 상품 재배송 요청 취소 | 내역 요청 유지 | 유지 |
| 배송 시각 문의 / 배송 시각 안내 요청 취소 | null | null |
| 배송 도착 예정 시각 문의 / 시각 안내 요청 철회 | 부분 이름으로도 null | null |
| 배송 시각 문의 / 배송 요청 취소 | 포괄 이름 취소는 null | null |
| 출고 상품 라벨 확인 / 라벨 확인 요청 철회 | 부분 이름으로도 null | null |
| 주문 상품 반송 방법 / 주문 상품 반송 절차 문의 취소 | 같은 범위는 null | null |
| 배송 상품 반송 / 배송 상품 반송 요청 취소 | 실제 행위 취소는 null | null |
| 배송 상품 반송 시각 문의 / 배송 상품 반송 요청 취소 | 모호한 같은 범위는 null | null |
| 주문 내역과 라벨 확인 / 주문 내역 확인 요청 취소 | 병렬 대상 일부 취소는 null | null |
| 배송 차량 도착 시각 / 배송 차량 도착 시간 문의 취소 | 표현 차이에도 null | null |
| 상품 반송 절차 / 상품 반송 방법 문의 취소 | 표현 차이에도 null | null |
| 상품 라벨 다시 보내기 / 상품 재배송 요청 취소 | 안내 요청으로 오인하지 않고 null | null |
| 배송 시각 문의+배송 상품 반송을 한 인용에 포함 / 반송 취소 | 복합 인용은 null | null |
| 배송 시각 문의 / 반송이 아니라 배송 요청 취소 | 대조 뒤 실제 취소는 null | null |
| 배송 시각 문의 / 반송 없이 배송 요청 취소 | 부수 언급으로 취소 해제 금지 | null |
| 시각 문의→반송 방법 요청→그 요청 취소 | 첫 문의 유지, 두 번째 null | 일치 |
| 위 두 요청의 순서를 반대로 배치→그 요청 취소 | 앞 반송 방법 유지, 뒤 시각 문의 null | 일치 |
| 같은 배송 시각 문의를 다시 말한 뒤 그 요청 취소 | 이전 인용도 null | null |
| 동일 대상 취소를 다음 경영주/상담원 발화에 배치 | 경영주 null / 상담원 발화는 유지 | 일치 |
| 별도 대상 취소를 다음 경영주/상담원 발화에 배치 | 두 경우 모두 문의 유지 | 일치 |

단어 교집합에 마지막 의미 단어 일치까지 요구하는 초기 아이디어는 적용하지 않았습니다. 읽기 전용 보조 검토가 위 병렬 대상·시각/시간·절차/방법 3개에서 기존 null을 다시 활성화하는 P1 회귀를 확인했습니다. 이 반례들을 고정한 뒤 더 좁은 정보문의/물류행위 구분을 적용했습니다.

중간 구현도 `반송 없이 배송 요청은 취소합니다.`에서 P1을 재현했습니다(`1 failed, 1 passed, 13 subtests passed`). 단순히 행위 단어가 등장하는지만 보던 조건을 버리고, 문장 끝의 실제 명시 요청 형식까지 확인하도록 좁힌 후 같은 기대값으로 null을 확인했습니다. 최종 성공만 남기지 않고 이 수정 경위를 보존합니다.

변이 대조 3개도 발화했습니다. 별도 범위 판정을 항상 false로 되돌리면 정상 요청 유지와 최근 요청 대명사 검사가 실패하고, 항상 true로 넓히면 동일·부분 대상 취소 검사가 실패합니다. 최종 테스트는 이 세 실패가 실제 AssertionError인지 확인합니다.

## 독립검토의 동사형 P1과 재수정

첫 동결 코드 `7b90e8c7`는 명사형 물류행위 단어가 없으면 `돌려보낼 시간`, `다시 보낼 시간`, `바꿀 일정`을 별도 정보 문의로 오인했습니다. 명시 반송·재배송·교환 취소에 종속된 문의도 그대로 유지되어, 첫 수정 이전의 보수적 null을 되돌린 P1입니다. 독립검토의 지적 3건과 변형 5건을 코드 수정 전에 기대 null로 고정하여 `8 failed, 1 passed, 21 deselected`를 재현했습니다.

| 고정한 요청 인용 | 뒤의 취소 대상 | 재수정 결과 |
|---|---|---|
| 배송 상품을 돌려보낼 시간을 알려 주세요. | 배송 상품 반송 요청 | null |
| 배송 상품을 돌려 보낼 시간을 알려 주세요. | 배송 상품 반송 요청 | null |
| 배송 상품을 다시 보낼 시간을 알려 주세요. | 배송 상품 재배송 요청 | null |
| 배송 상품을 다시 보내 주실 시간을 알려 주세요. | 배송 상품 재배송 요청 | null |
| 배송 상품을 바꿀 일정을 알려 주세요. | 배송 상품 교환 요청 | null |
| 배송 상품을 바꿔 받을 일정을 알려 주세요. | 배송 상품 교환 요청 | null |
| 배송 상품을 돌려보내는 시간을 알려 주세요. | 배송 상품 반송 요청 | null |
| 배송 상품을 다시 보내려고 하는 시간을 알려 주세요. | 배송 상품 재배송 요청 | null |
| 배송 상품을 돌려보내 주시고 처리 시간을 알려 주세요. | 배송 상품 반송 요청 | null |
| 배송 상품을 다시 보내 주시고 배송 시간을 알려 주세요. | 배송 상품 재배송 요청 | null |

마지막 복합행위 2건은 재수정 중 메인이 추가 전달했습니다. 해당 기대값을 테스트에 추가하고, 첫 수정의 넓은 inquiry guard만 메모리에서 복원하여 두 건 모두 이전에는 앞 인용 전체를 유지했고 현재는 null인 것을 대조했습니다. 제품 파일을 구버전으로 되돌리거나 기존 증거를 다시 쓰지 않았습니다.

```powershell
.venv/Scripts/python.exe -B -X utf8 -m pytest -q tests/test_request_grounding.py -rs
```

최종 실측은 `22 passed, 79 subtests passed in 4.85s`, exit 0입니다. 원래 F1·공통 업무어 4건·동일/부분 이름 취소·대명사 최근 요청·화자 경계·변이 대조도 이 파일에 포함됩니다. `git diff --check -- server/request_grounding.py tests/test_request_grounding.py`는 exit 0입니다.

## 첫 수정의 이전 실행 결과와 원본 보존

```powershell
.venv/Scripts/python.exe -B -X utf8 -m pytest -q tests/test_request_grounding.py tests/test_analysis_repair.py tests/test_analysis_semantics.py tests/test_analysis_grounding_regression.py -rs
```

첫 수정 `7b90e8c7`의 이전 실측: `104 passed, 203 subtests passed in 6.98s`, exit 0. 당시 신규 5개 메서드를 제외한 같은 명령은 `99 passed, 5 deselected, 178 subtests passed in 7.17s`, exit 0. 기존 파일의 99/178 검사와 당시 신규 5개/25개 하위 검사를 구분한 수치입니다. 동사형 P1 반례는 당시 집합에 없었으며, 이 통과 수치로 해당 결함이 없다고 판정할 수 없습니다.

원래 `.local/request-grounding-independent/probe.py`를 읽어 결과 쓰기 1줄만 메모리에서 제거해 실행했습니다. 입력·기대값·정규화·schema 검증·원본 hash 검사는 그대로이며, 기존 증거 폴더에 새 결과를 쓰지 않았습니다. 이 재처리는 추가 라이브 API의 정확도 평가가 아닙니다.

| 확인 | 첫 수정에서의 이전 실측 |
|---|---:|
| 원래 독립 요청 대조 | 9/9 통과 |
| 저장된 모델 원응답 재처리 | 36건 |
| 직전 독립 결과의 analysis 전체 객체와 일치 | 36/36, 변경 0건 |
| 평가 run 원본 파일 SHA-256 보존 | 44/44 |
| 기존 독립 코드·결과·보고서 SHA-256 보존 | 8/8 |
| API·키 접근 | NO_API / NO_KEY 가드 아래 0건 |

다음 PowerShell 명령은 결과를 메모리에만 만들고 위 수치를 재현합니다.

```powershell
@'
import json, hashlib, contextlib, io
from pathlib import Path
probe = Path('.local/request-grounding-independent/probe.py')
protected = [probe, Path('.local/request-grounding-independent/results.json'), Path('reports/request-grounding-independent.md'), Path('reports/request-grounding-final-independent.md'), *Path('.local/request-grounding-final-independent').glob('*')]
protected = [p for p in protected if p.is_file()]
before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
source = probe.read_text(encoding='utf-8-sig')
write = "(OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\\n',encoding='utf-8')"
assert source.count(write) == 1
source = source.replace(write, 'assert result["sourceFilesUnchanged"] and result["codeUnchanged"]')
ns = {'__name__': '__main__', '__file__': str(probe)}
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(source, str(probe), 'exec'), ns)
r = ns['result']
prior = json.loads(Path('.local/request-grounding-final-independent/results.json').read_text(encoding='utf-8'))
rows = {(x['runId'], x['caseId']): x['analysis'] for x in prior['reprocessed']}
changed = [x['caseId'] for x in r['reprocessed'] if x['analysis'] != rows[(x['runId'], x['caseId'])]]
assert not changed
assert before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
print(json.dumps({'originalNinePass': sum(x['pass'] for x in r['probes']), 'storedRows': len(r['reprocessed']), 'storedAnalysisChanges': changed, 'sourceFilesPreserved': len(r['sourceFileSha256']), 'priorEvidenceFilesPreserved': len(protected), 'codeSha256': r['codeSha256']}, ensure_ascii=False))
'@ | .venv/Scripts/python.exe -B -X utf8 -
```

## 동결과 인수 한계

최종 제품·테스트 SHA-256:

- `server/request_grounding.py`: `f23f2eb93e9a46baf7e2403261cc3afd7bf004ae9561020b97c3a8f0d1e489e8`
- `tests/test_request_grounding.py`: `aa28758544f221042650f3bb817ff80f633179173e230c0e805366a88ba942cc`
- 읽기 전용 `server/live.py`: `4150029e4440dd8d6d843581f181829c825542857cc251def3036827337a5b71`

F1 및 위 대비 검사 범위에서 독립 인수를 요청합니다. 수정·테스트·이 보고서는 작성자 검증이며 메인의 독립 검증 완료가 아닙니다.

## 메인 재검과 제한 인수 — 최종 f23f2eb9

2026-09-21 23:20 KST 이후, 별도 읽기 전용 검토자가 앞서 사용한 독립11입력을 그대로 재실행했습니다. 동사형3건·명시 복합행위2건의 회귀가 모두 null로 수정됐고 정상 정보문의 대조도 유지되어11/11, 소스 해시 보존을 확인했습니다. 메인의 위4개 모듈 영향 검사는105 passed / 213 subtests(15.70초)입니다. 최종 코드로 기존 모델 원응답을 메모리에서 다시 처리한 결과 analysis36/36동일, 원본44/44·기존증거8/8 해시 보존, 기존 독립9/9 유지입니다. 새 API·키 접근·실저장 변경은 없습니다.

이 인수는 단순 명사구 정보문의와 명시 물류행위 취소의 구분 및 위 회귀에 한정합니다. 실행 중인 기존 API 프로세스에 새 코드가 적용됐다는 판정이나 일반 한국어 의미 이해 완료가 아닙니다.

표현 범위를 좁혀 P1 위험을 줄인 대신 P2 과잉 차단은 일부 남습니다. 예를 들어 `배송 시각 안내 요청입니다. 배송 상품 반송 요청은 취소합니다.`에서 명사형 첫 문장을 선택하면 null이었던 기존 한계를 유지합니다. 허용한 단순 명사구 밖의 수식어·정상 정보 문의도 보수적으로 null이 될 수 있습니다. 동사형 작업 의미를 전반적으로 해석한 수정이 아니며, 장거리 공동참조·전체 한국어·실제 STT 화자 정확도·새 라이브 응답·배포·실사용은 검증하지 않았습니다. 원문 대조와 사람의 최종 확인을 유지해야 합니다.
