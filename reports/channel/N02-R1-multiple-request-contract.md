# N02-R1 / P1 — 복수 고객 요청의 독립 경계 입력

## 왜 지금

PC2 안영일 / MR-A83에게 상담원이 여러 요청을 놓치지 않는 계약의 독립 검증을 배정합니다. 코드 기준은 `dce4e66c0815e477f51977cbd9e023db101b9d58`, 문서 기준은 이 카드를 전달하는 #8 댓글의 고정 SHA입니다. PC2의 이전 O1 결과는 `c127a565a087684de1c968f563f68c3236da0b1a`이며 메인 인수와 구분합니다.

메인의 실제 두 WAV canary에서 오출고 STT는 세 요청을 보존했지만 모델은 비연속 발화를 한 requestQuote로 합쳤고 최종 request가 null이 됐습니다. 같은 화자의 인접 구간과 다른 화자가 끼어 있는 구간을 구분해야 합니다. 원응답은 PC1 로컬에 보존하며 PC2에 전달하지 않습니다. 공개된 독립 가상 대본과 새로 작성한 합성 문장으로 경계를 검증합니다.

정본: `planning/multi-request-provenance.md`, `reports/evaluation/voice-canary-20260922-oracle.json`, 실제 결과 보고 `reports/evaluation/voice-canary-20260922-review.md`. 서버 구현은 PC1 소유입니다. 공식 CLOVA 음원 수신 대기는 유지하되 같은 실패 export·미리듣기 대체는 시작하지 않습니다.

## 해줘야 할 일

소유는 신규 `tests/evaluation/multi-request-cases.json`과 `reports/pc2/multiple-request-contract-review.md` 두 파일뿐입니다. 다른 작업자가 같은 저장소에서 작업 중이므로 기존 변경을 되돌리지 말고 공통 코드·schema·TODO를 편집하지 마세요.

- 상담 과업·원문 대조 UX·호환 계약·검증 관점에서 설계 초안의 누락/반례를 확인합니다. 제안은 실제 문장과 기대 결과로 설명합니다.
- 적어도12개의 독립 합성 입력을 작성합니다. 행별 id, transcript(화자·원문·시각), 제안 인용 목록, expectedActiveQuotes, expectedRejectedQuotes, expectedReviewReasons, 근거 설명을 둡니다. 기대값은 제품 출력에서 복사하지 않습니다.
- 단일 요청, 같은 발화의 여러 요청, 인접 같은 화자의 단위 정정+기록 요구, 서로 떨어진 세 요청, 다른 화자 사이를 가짜로 연결한 인용, 원문에 없는 의역, 과거/예시/부정, 화자 미확인, 한 요청만 철회, 화자 교대 후 같은 화자의 철회, 중복/역순, 구형 단일 인용을 포함합니다.8개/9개 경계도 별도로 제안해 주세요.
- 첫 Bolt는 단위 정정·잘못 온 상품 처리·주문 상품 처리 세 요청입니다. 세 항목을 유지하되 인용을 창작하지 않는 기대값부터 고정합니다.
- 제품의 현재 동작을 관찰했다면 무과금 순수 함수만 사용하고 사용한 SHA·실제 호출·실패를 기록합니다. 새 계약이 아직 구현되지 않았다는 이유로 기대값을 현행 null에 맞추거나 PASS로 바꾸지 않습니다.

## 실행 명령

보고받은 PC2 저장소는 `C:\Users\Administrator\Desktop\hackerton\happycall-ralphthon`입니다. 실제 경로가 달라졌으면 변경 사실을 회신하고 타 PC 경로를 추정하지 않습니다.

```powershell
Set-Location -LiteralPath 'C:\Users\Administrator\Desktop\hackerton\happycall-ralphthon'
python channel/whoami.py
gh api user --jq .login
git status --short
git rev-parse HEAD
git fetch origin
git show dce4e66c0815e477f51977cbd9e023db101b9d58:server/request_grounding.py
# 이번 전달 댓글의 고정 문서 SHA로 위 정본을 git show하여 읽습니다.
# 기존 work/pc2-n02-call-review 브랜치를 보존하며 소유 두 파일만 커밋·push합니다.
```

새 서버/브라우저·API·과금 호출은 없습니다. 가상 문장 입력·JSON 파싱·현재 순수 함수의 필요한 범위만 실행합니다. 모듈 import가 비밀이나 원장을 읽는 경우 그 경로는 사용하지 않고 문서/입력 작성 부분을 진행합니다.

## 검증 방법 + 기대값

첫 결과는 실제 ACK 후20분, 완성 보고는40분을 목표로 하되 확약이 아닙니다. 09시 이후에는 새 작업을 시작하지 않습니다.

JSON 파싱·고유 ID·빈 기대값의 이유·원문 근거를 전수 확인합니다. 올바른 인접 인용을 모두 지우는 구현, 원문에 없는 인용을 전부 허용하는 구현, 한 건 철회 시 모든 요청을 지우는 구현이 각각 어떤 행에서 실패해야 하는지 적습니다. 최소3방향의 검사기 변이/대조군을 실제 실행했는지와 설계만 했는지를 구분합니다.

PC1은 수신 파일의 고정 SHA·기대값 독립성·정상/반례 균형을 대조한 뒤 공통 구현과 연결합니다. PC2 결과 제출은 메인 인수나 실제 모델 개선의 증거가 아닙니다.

## 중단 조건 + 인계

소유 충돌·정책 거부·비밀/원천자료 노출·과금 필요 시 해당 경로를 중단합니다. 실패 export·저장소403·API 재시작 거부를 다른 도구로 우회하지 않습니다. 같은 실패3회 또는30분 진전 없음은 원인과 독립 진행 가능 부분을 남깁니다.

#8에 실제 hostname/GitHub/기준·결과 SHA/명시 두 파일/행 수/실행 명령/기대·실측/발견 반례/미실행/PC1 연결점을 회신합니다. 원응답·음성전문·키·원장은 첨부하지 않습니다. 기존 PC2 변경을 포함한 일괄 add·reset·stash를 하지 마세요.
