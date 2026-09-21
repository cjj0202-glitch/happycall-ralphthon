N03-M2 / P1: pc3 정준화(mcjun86-oss)가 합성 센터의 소터 한 구간을 고품질 Blender 장면·영상으로 제작합니다.

## 왜 지금
사용자가 센터레이아웃 도면과 30_센터작업모니터링을 참고한 고품질 공간/동작을 요구했습니다. 메인은 도면7/7페이지를 로컬에서 확인하고 실제 코드 구조를 대조했습니다. 기존 `d6aa6b3` linked INT 수정은 함수/SSR 독립58/58에서 기존 P1 해소를 확인했으며 전체 UI 인수와 후보영상 등록은 별도입니다. 기존 v1 후보 Release는 보존합니다.

기준 main `e5469aa99bb266c5a977b80c097223275ac6fc9b`: `docs/28_PC_업무배정_기준.md`, `planning/media/production-quality.md`, `synthetic-center-scene.md`, `scene-layout-v1.json`, `reference/warehouse-look-v1.png`, `reports/pc3-main-review.md`. 이 문서/독립 합성 좌표만 사용하고 회사 도면 원본/렌더를 Git·외부모델·Release로 옮기지 않습니다.

## 해줘야 할 일
- [ ] Blender 실행 가능 여부·버전·CPU/GPU/RAM·예상 렌더 자원을 실제 확인하고, 대표3프레임을 먼저 만드는 상세설계를 reports/pc3에 남기세요. pc1은 공식 Blender4.5.14 LTS portable 실행을 검증했고 작은 벤치마크를 진행 중입니다. pc3에 도구가 없으면 **같은 장면생성 Python 코드를 제출해 pc1 렌더를 활용**할 수 있습니다. 없는 도구를 썼다고 보고하지 않습니다.
- [ ] 독립 합성 좌표를 입력으로 읽는 재현 가능한 장면생성기를 scripts/media_pc3/에 만드세요. 롤러/벨트·안전 가드·플라스틱/골판지·콘크리트·조명·접촉 그림자를 구현하고, 전체 개요와 고정 CCTV 근접 구도를 구분합니다. CASE-0002/W-W3 하나부터.
- [ ] 20:30 KST 첫 결과 목표: 장면생성 코드/seed·카메라/동작설계·실제 렌더 가능하면720p 시작/분기/끝3프레임. 미렌더이면 미렌더로 보고하고 실행 명령/필요경로를 보내세요. 파일 생성이나 작업 시작만으로 시각 게이트를 통과시키지 않습니다.
- [ ] 메인의 대표프레임 검수 결과를 반영해 짧은 동작→1080p24fps12초 최종 후보로 확장합니다. 긴 렌더는 벤치마크와 남은 시간으로 판단. 같은3D 장면에서 객체 bbox/궤적을 내보내되 `synthetic-scene-ground-truth`로 표시합니다.
- [ ] WMS 사용자에게 공정/근거/영상 선택이 같은 사건으로 이어지게 합니다. 합성표시, 일시정지·키보드/초점복귀·로딩/404/미등록, reduced-motion을 유지하고 UI의 미확인 상태를 선명하게 보여줍니다.

소유: WmsScene.tsx/css, scripts/media_pc3/, data/overlays/pc3-wms.json, tests/remote/pc3/, reports/pc3/. 공용 page·LogisticsView·lib·server·fixture·manifest·중앙 문서는 pc1 소유입니다. track 메타는 후보 Release 또는 reports/pc3의 작은 합성 예제로 제출하며 공용 스키마를 임의 변경하지 않습니다.

핵심 계약: W-W3=2026-09-18 02:33 KST·CH-02·D-02·SYN-CAM-02. 해당 분기에서 업무 토트는 미확인(null), 움직이는 객체는 SYN-VIS-PARCEL02. A→B 토트 바꿔치기나 휴먼에러를 꾸미지 않습니다. 시연+초와 고정 기록시각을 분리하세요. 30 모듈의 피킹순서/루프의심은 실제 BCR 궤적이 아닙니다. 여러 도면안을 실제한센터로 합치지 않습니다.

## 실행 명령
```powershell
Set-Location -LiteralPath 'D:/hwana/Work/happycall-ralphthon'
python channel/whoami.py
gh api user --jq .login
git status --short
git rev-parse HEAD
git fetch origin
git show e5469aa99bb266c5a977b80c097223275ac6fc9b:docs/28_PC_업무배정_기준.md
git show e5469aa99bb266c5a977b80c097223275ac6fc9b:planning/media/synthetic-center-scene.md
git show e5469aa99bb266c5a977b80c097223275ac6fc9b:planning/media/scene-layout-v1.json
# 기존 work/pc3-n03-wms-scenes 유지. 필요한 정본은 diff 검토 후 안전하게 반영.
```
블렌더가 있으면 실제 경로의 `--version`/`--background --python <생성기>` 명령을 기록합니다. pc1 경로를 pc3에서 실행하지 않습니다. 결과 소유경로 명시 커밋/push/원격SHA를 회신하세요.

## 검증 방법 + 기대값
1. 대표3프레임: 설비 높이/바닥 접촉, 물체 관통/부유0, 식별 가능한 분기, 왜곡된 사람/손으로 작업을 표현하지 않음. 사진확대/패닝을 작업영상으로 세지 않음.
2. 움직임: 객체ID 일정, 분기 방향/회전 연속, bbox가 영상 객체에 맞음. fps/프레임수/길이·디코딩·탐색·SHA 실제값. 최종 목표12초×24fps=288프레임.
3. 사건/시각/객체: fixture와 등록값 일치, 업무토트null 보존, 다른사건·미등록카메라·기준시각이후·잘못된구간 차단. 정상영상 양성대조 포함.
4. 결과물: 생성코드/seed·Blender버전/engine·blend·MP4·track meta·해시. 이미지와긴영상/blend는 별도 후보 Release에 저장하고 기존 manifest/자산을 덮지 않음. 메인이 영상 등록을 결정합니다.

## 중단 조건 + 인계
권한거부·소유충돌·원천/시크릿전송은 해당 경로 중단. pc1의 기존 정책거부를 해결하라는 지시가 아닙니다. 유료 영상/TTS/LLM이나 새계정/구독/원장 생성 없음. 렌더자원/도구가 병목이면 30분 내 코드·벤치마크·독립 진행을 회신하고 다른 PC라고 가장하지 않습니다.

같은 #9에 실제PC·기준/결과SHA·명시파일·명령·기대/실측·대표이미지/자산경로·결함/수정/동일재검·미실행을 회신하세요. 새 중복이슈/자체TODO완료는 하지 않습니다.
