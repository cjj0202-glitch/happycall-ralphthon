# N03-M3 — 최신 렌더 묶음의 수신 검사

## 왜 지금 / 기준 SHA

pc3의 추가 패킷 제안을 수용합니다. 정식 생성기 기준은 **33fa0e4edeb88c0d4ad5e9cc0194ffc7e96cebcd**입니다. pc1이 72프레임을 렌더하는 동안 pc3는 하나의 수신검사 카드를 같은 PC의 세 보조 세션에 소유 파일을 나누어 진행할 수 있습니다. pc1의 CCTV 조사 React 화면이나 pc2/pc4 소유 파일을 가져오지 않습니다. 코인 추가 승인으로 제품 API 예산 원장을 바꾸지 않습니다.

## 사용자 결과 / 계약

받은 장면·좌표·대표 PNG/short/full 영상이 같은 사건·생성 입력·설정인지 확인하고, 빠졌거나 다른 후보가 섞였을 때 어떤 검사가 실패했는지 재현할 수 있는 결과를 만듭니다. 실제 픽셀 품질·가림·귀책·정본 인수를 자동으로 선언하는 도구가 아닙니다.

- 입력은 생성기의 `pc3-blender-candidate-v1` render-report + tracks + 파일 묶음, 메인이 명시한 예상 source SHA/입력 digest/설정/모드입니다. 기대값을 받은 report 자기 값으로 만들지 않습니다.
- 현재 예상: CASE-0002/W-W3/SYN-CAM-02/2026-09-18T02:33:00+09:00, CH-02/D-02, businessToteId=null, 1280×720/24fps/288 좌표, EEVEE96/rays4, staging_v1의 정적48부품, occlusionTested=false.
- 모드 분모를 구분: prepare0, representatives[1,133,288], short[73..144]72장, animation[1..288]. prepare를 영상완료로, short를12초완료로 세지 않습니다.
- 좌표의 연속 프레임/시간/bbox/단계/객체/해시, 파일 누락/추가/중복·크기·SHA, 생성기와 명시 dependency/입력 대조. 경로 밖 파일·링크·보고서 참조로 임의 파일 읽기를 거부합니다.
- 33fa0e4 보고서에 없는 fixture digest·threads 실측은 **별도 실행 증거 필요/PENDING**으로 표시합니다. requested=actual로 대체하거나 누락을PASS로 세지 않습니다. Blender 세부실측·전체영상 디코딩은 도구/파일이 없으면 NOT_RUN입니다.

## 소유 / 분할

pc3 저장소 `D:/hwana/Work/happycall-ralphthon`, branch work/pc3-n03-wms-scenes를 유지합니다. 타인 변경을 되돌리지 않습니다.

1. 생성기와 독립된 신규 `scripts/media_pc3/verify_render_package.py`: 읽기 전용 검사기/정제된 판정 JSON.
2. 신규 `scripts/media_pc3/test_render_package.py`: 다른 세션이 작성하는 정상·오염·누락·잘못된 사건/프레임/단위/보고서의 반례·검사기 변이.
3. `scripts/media_pc3/build_review_page.py`의 최신 묶음 모드 확장과 신규 `scripts/media_pc3/test_review_package.py`: 원본 PNG/메타데이터를 비교하는 로컬 검수 문서. 기존 모드 보존. 제품 React가 아니라 로컬 검수 보조이며 새 외부 라이브러리 금지.
4. `reports/pc3/render-package-*` 설계/실행/인계. root는 통합·입력 불변·명시 경로 커밋·한 번 회신.

**build_scene.py/scene_contract.py/환경·그림자·레이아웃·공용 fixture/manifest/API 변경은 이번 카드에서 제외**합니다. 현재33fa 소스가 실제 렌더에 사용되고 있으므로 생성기 보고서 보강은 이후 별도 판단합니다.

## 실행 / 기대값

먼저33fa 실제 report 구조와 소스 계약을 읽고 기대값을 문서로 고정합니다. `python -B -m unittest discover -s scripts/media_pc3 -p test_render_package.py -v` 및 별도review 검사를 실행합니다. 기존 A/B d67 검사기를 느슨하게 바꾸지 않습니다.

실제72프레임 원본은 pc1 렌더 중입니다. 지금은 prepare/대표/short의 명백한 **검사기용 fixture**를 작은 가짜 파일로 만들어 양성·음성·경계·변이를 검증할 수 있습니다. 이를 실제 Blender 렌더/수신 건수로 합산하지 않습니다. 실제 묶음의 Release·해시는 메인이 렌더 후 같은 #9로 전달합니다. 메인 디스크에만 있는 파일을 받았다고 쓰지 않습니다.

## 인계 / 중단

계약/반례 설계10분 내, 첫 실행 가능한 검사기20~30분 내. 결과에는 source SHA·수용 기준·실패와 수정·정상/반례 분모·실제/합성 fixture 구분·미실행을 기록합니다. 정확한 원본 바이트/체커를 실행 전 보존하고 커밋을 회신합니다. 새 사용자 질문·유료호출·도구설치·우회·다른 서비스 중지·자기 인수·이슈종결은 하지 않습니다.
