N02-M2 / P1: pc2 안영일(MR-A83)이 통화 명료도 후보와 정확한 확인상태 연결 예시를 담당합니다.

## 왜 지금
사용자가 회사 시스템 수준의 미디어 품질과 효율적인 PC 배정 기준을 요구했습니다. 공통 기준 main `e5469aa99bb266c5a977b80c097223275ac6fc9b`: `docs/28_PC_업무배정_기준.md`, `planning/media/production-quality.md`, `reports/pc2-main-review.md`를 읽으세요. pc2 결과 `7ae648e`의 독립 검토에서 연결 예시 P1 한 건을 재현했습니다. 기존 결과는 보존하고 이번 카드 하나만 구현합니다.

## 해줘야 할 일
- [ ] `reports/pc2/integration.md`의 reviewCase에 `reviewConfirmed: confirmed`를 반영하세요. 저장된 확인true에서 수량6→999 편집으로 부모false가 되면 확인완료 문구가 사라지는 실제 React 렌더 대조를 남깁니다. 공용 page 연결은 pc1이 합니다.
- [ ] 기존 승인 WAV2개/16발화 캐시를 바탕으로 상품명·수량/EA·BOX 정정·화자 구분을 검수할 A/B 계획을 적고 **핵심 편집 하나**의 후보를 먼저 만드세요. 원본을 보존하고 같은 체감 음량으로 비교합니다. 속도/쉼/문장끝 중 무엇을 바꿨고 왜 도움이 되는지 기록하세요. 이미 통과한 음량을 다시 키우는 것만으로 품질개선이라 하지 않습니다.
- [ ] 20:20 KST까지 첫 결과 목표: 확인상태 수정+재현, 같은 구간 A/B, 변환/타이밍 메타·음량/피크/잘림 기술 검수. 사람이 듣지 않았다면 청취검증 미실행을 남기세요. 목표를 못 맞추면 실제 진전/다음 예상시각을 같은 이슈에 한 번 보고합니다.
- [ ] 선택 후보가 의미/타이밍을 지키면 두 통화 전체 후보로 확장하고 22:00 통합 후보를 목표로 합니다. 원문·대본/전사 출처·기존v2·실패 이력을 보존합니다.

소유: 기존 CallReview.tsx/css, scripts/media_pc2/, planning/media/voice-scenarios.md, tests/remote/pc2/, reports/pc2/. 읽기 전용: page.tsx, lib/types, server, fixture, manifest, 기존 정본 음성. main/공용 파일은 수정하지 않습니다. 새 WAV와 타이밍은 별도 후보 자산+해시로 제출하고 기존 자산 URL/해시를 덮지 않습니다.

## 실행 명령
```powershell
Set-Location -LiteralPath 'C:/Users/Administrator/Desktop/hackerton/happycall-ralphthon'
python channel/whoami.py
gh api user --jq .login
git status --short
git rev-parse HEAD
git fetch origin
git show e5469aa99bb266c5a977b80c097223275ac6fc9b:docs/28_PC_업무배정_기준.md
git show e5469aa99bb266c5a977b80c097223275ac6fc9b:planning/media/production-quality.md
# 기존 work/pc2-n02-call-review와 변경을 보존합니다. 자동 pull/리셋하지 않습니다.
python scripts/fetch_demo_media.py --verify-only
```
검사/생성 명령은 pc2 실제 도구 경로로 reports/pc2에 남기세요. 커밋은 소유 경로만, push 후 원격 SHA를 대조합니다.

## 검증 방법 + 기대값
1. 수정 폼+미확인false에서 확인완료 문구0; 확인true의 양성대조에서는 표시1. 수량·단위·원문은 보존.
2. 후보 각 파일의 SHA/길이/코덱·sample rate·LUFS/peak/클리핑·발화 시작끝이 재현 가능. 목표 약-18LUFS/클리핑0, 문장 잘림0. 측정값과 실제 사람 청취를 구분.
3. 실제 전체1배속 종료1, 끝seek/구간/이전사건/disabled 종료0, 텍스트 STT없음, 선택모드를 바꿔도 결과 출처 유지. 변경영향이 있는 항목만 재실행하고 기존 증거 SHA를 재사용 가능.
4. A/B가 개선되지 않으면 정본 유지가 맞는 결과입니다. 완료 건수/음량만으로 명료도가 나아졌다고 하지 않습니다.

## 중단 조건 + 인계
기존 permission popup 원인이 미확인인 상태에서 승인 설정/방화벽을 바꾸지 않습니다. 정책거부·파일소유충돌은 해당 작업을 중단하고 독립 편집/설계만 진행합니다. 새 유료 TTS/STT/LLM·새 예산원장·자동재시도 없음. 추가 생성이 꼭 필요하면 pc1 기존 원장으로 연결할 입력/호출수만 제안하세요.

같은 #8에 기준/결과SHA·명시파일·후보자산SHA·입력/명령·기대/실측·실패/수정/동일재검·한계·부모 연결점을 회신합니다. 메인 인수 전 TODO/이슈를 완료 처리하지 않습니다.
