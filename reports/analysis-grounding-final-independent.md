# 분석 정규화 최종 한정 재검

2026-09-21 KST. 메인이 수정자와 분리해 기존 독립 스크립트를 다시 실행했습니다. 새 모델 호출은 없습니다.

명령: `.venv/Scripts/python.exe .local/grounding-final-independent.py` → exit 0, 4.14초. 원래 독립 스크립트의 출력 디렉터리만 바꾸고 기대값은 유지했습니다.

| 대상 | 결과 |
|---|---|
| 수령 부정·미래·관형 주문·이웃 상품·다른 미확인 보존 G1~G5 | 5/5 통과 |
| 명사형 부정·예정 원래 두 쌍 | 정상 진술 2/2 보존, 부정·예정 2/2 수량/단위 null |
| 저장된 모델 응답 재처리 | 32건, 자동 4필드 128/128 일치 |
| 원본 평가 파일 | 변경 없음 |
| 앞선 독립 재검 증거 4파일 | 실행 전후 해시 동일 |
| 검수 중 제품 코드 | 변경 없음 |

`server/claim_grounding.py` SHA-256: `c98947e06f567560c2d89eb3f75561a9d6bf78e98e42bf774784f60e42b3243e`.

로컬 결과는 `.local/grounding-final-independent-01/`의 `stdout.log`, `additional-pairs.json`, `independent-results.json`에 있습니다. 기존 [1차 결함](analysis-grounding-independent.md), [2차 잔존 결함](analysis-grounding-independent-recheck.md), [수정 내역](analysis-grounding-repair.md)을 보존했습니다.

판정: 보고된 정규화 결함과 독립 반례에 대한 수정을 인수합니다. 128/128은 저장 응답의 네 자동 필드만 평가한 값으로, 32건의 전체 의미·안전 통과율이나 새 라이브 평가가 아닙니다. 모호한 언어·새 문형·대화 전체의 사실성은 사람 확인 대상으로 유지합니다. 이 결과를 기존 고정 116/120·경계64/72의 라이브 결과 대신 표기하지 않습니다.
