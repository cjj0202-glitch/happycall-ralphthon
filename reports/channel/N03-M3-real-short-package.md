# N03-M3 실제 72프레임 원본 수신 검증

2026-09-21 pc1. pc3 결과 `9be72090021c550c6e27746469f926baf57fea2e`를 받았습니다. 인공 fixture 검증과 실제 렌더 수신은 분리합니다. 기존 N03-M3의 실제 수신 단계를 이어갑니다.

## 결과 / 기준

기준 생성기 `33fa0e4edeb88c0d4ad5e9cc0194ffc7e96cebcd`, 검사기 `9be7209`입니다. [검수용 Release](https://github.com/cjj0202-glitch/happycall-ralphthon/releases/tag/wms-short-review-20260921-33fa0e4)에 실제 72 PNG·blend·tracks·실행 증거·3초 검수 영상이 있습니다. pc1은 22:12 KST Release 자산 3개의 업로드 상태·크기·서버 SHA를 로컬 값과 대조했습니다.

| 파일 | 바이트 | SHA256 |
|---|---:|---|
| wms-short-33fa0e4-review.zip | 82333801 | 10fa9981105eaecfe07a5c715d19c3e7bd932f8aa4b8bb375f93447f73f80891 |
| intake-expected.json | 2067 | c7066902302d770290bdb28a79cb4ebac2428c3963428ecb66c2236ddbd8e81f |
| case-0002-ww3-short-review.mp4 | 544733 | 21ac21351803125334deba303fd249909774aba98058bc787e38121058f70ccf |

## 소유 / 실행

pc3는 `D:/hwana/Work/happycall-ralphthon`, 기존 브랜치에서 `.local/pc3-real-short-intake/`와 `reports/pc3/render-package-real-*`만 추가합니다. 검사기 수정이 꼭 필요하면 먼저 원본 실패를 보존하고 계약을 완화하지 않는 최소 수정과 반례를 같은 카드에서 제시합니다. 생성기·제품·공용 manifest 변경은 제외합니다.

```powershell
gh release download wms-short-review-20260921-33fa0e4 --repo cjj0202-glitch/happycall-ralphthon --dir .local/pc3-real-short-intake/download
```

실제 다운로드 3개 해시 확인 후 새 빈 폴더에 ZIP을 풉니다. ZIP의 `package-files.json` 전수 대조와 경로 검사부터 합니다. 정식 strict generator package는 ZIP 전체가 아니라 `short/`입니다. 그 안의 pc1 추가 `independent-scene-readback.json`은 원본 위치에 보존하고, 검사기 전용 새 하위 폴더에는 render-report/tracks/blend/72PNG만 **복사**해 검사합니다. 이 복사 전후 바이트 일치를 확인하고 추가 증거를 무시했다고 숨기지 않습니다. 원본 ZIP·풀린 원본은 수정·삭제하지 않습니다.

## 외부 기대값 / 검증

기존 `render-package-expectations.json`의 Git 고정 source/dependencies/settings를 유지한 별도 expected 파일에서 mode=short, fixture SHA=`79c3b01aed139352b5cc0a695f2829e76f78eabb61d7cfd6b8055db32f61a73b`를 지정합니다. layout SHA=`c6aece6692c6b78beb85d4f1167868f2bd095b3ab8366e837466715b82bd6cb6`, tracks SHA=`9fb424be0fd212bbf3faa057097bec56c63a89e4b8ae08c524e5fd76b80fd44b`입니다. 수신 report 자기 값으로 기대값을 만들지 않습니다.

- CASE-0002/W-W3/SYN-CAM-02, 2026-09-18T02:33:00+09:00, CH-02/D-02, businessToteId=null, occlusionTested=false.
- PNG73~144 정확히72장, 1280×720/24fps, 전체좌표288개. source elapsed [3,6)와 검수 MP4 [0,3)는 +3초 차이입니다. 288 좌표를3초 영상에 직접 등록하지 않습니다.
- MP4 H.264/yuv420p/72프레임/3초/무음은 pc1 파일 검사 결과입니다. pc3 독립 디코딩 도구가 이미 있으면 대조하고, 없으면 hash 확인만 기록합니다. 설치·브라우저·서버 실행은 이번 카드에 없습니다.
- 별도 source-intake·process·independent-scene-readback·short-verification은 추가 증거입니다. 33fa report에 없는 fixture/thread 실측을 자동 PASS로 바꾸지 않고 보고서의 PENDING과 외부 실측을 나누어 설명합니다.

## 인계 / 중단

다운로드·전수 바이트·실제 검사기 판정·누락/추가 항목·원본 불변·실패/재검을 보고하고 명시 경로 커밋을 회신합니다. full288 제작·픽셀 품질·귀책·제품 등록·최종 인수는 미완료입니다. 정책 거부 시 우회하지 않으며 기존 서비스/감시기를 중단하지 않습니다. 전체 N03과 이슈는 열린 상태를 유지합니다.
