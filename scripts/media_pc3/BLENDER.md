# N03-M2 독립 합성 Blender 장면

입력 기준은 main `e5469aa99bb266c5a977b80c097223275ac6fc9b`의 `planning/media/scene-layout-v1.json`이다. 원본 회사 도면·렌더·BCR 행을 사용하지 않는다. 움직이는 객체는 `SYN-VIS-PARCEL02`, 업무 토트는 `null`. 첫 대상은 CASE-0002/W-W3/SYN-CAM-02 한 구간이다.

PC3에는 확인한 범위에서 Blender 실행파일이 없어 **생성기를 실제 Blender에서 실행하거나 영상을 렌더하지 않았다.** Python 문법 검사와 별도 좌표·시간·원본 관계 검사만 수행했다. pc1의 검증된 Blender4.5 LTS 환경에서 아래 첫 단계를 실행하고 실제 결과로 검토한다.

## 사전 조건

- 소유 브랜치의 `build_scene.py`와 `scene_contract.py`를 함께 사용한다.
- 공용 기준의 layout JSON과 `data/fixtures/cases.json`을 읽을 수 있어야 한다.
- 기존 `.blend`나 출력 폴더를 덮지 않는다. 실행마다 새로운 빈 output 디렉터리를 선택한다.
- 아래 `$blenderExe`는 **실행하는 PC에서 확인한 실제 경로**다. PC3/pc1의 경로를 서로 추측하거나 복사하지 않는다.
- EEVEE가 해당 PC에서 실패하면 실패 로그를 보존한다. CPU Cycles 대안은 같은 장면에서 저샘플 대표 프레임만 먼저 측정하고 긴 렌더 시간을 가정하지 않는다.

## 첫 실행: scene 준비와 대표 3프레임

PowerShell, 해당 PC의 저장소 루트에서 실행한다. 경로를 변수에 설정할 때는 실제 존재와 `--version`을 먼저 확인한다.

```powershell
& $blenderExe --version
& $blenderExe --background --factory-startup --python-exit-code 1 --python scripts/media_pc3/build_scene.py -- --layout planning/media/scene-layout-v1.json --fixture data/fixtures/cases.json --output .local/pc3-blender/prepare-01 --mode prepare
& $blenderExe --background --factory-startup --python-exit-code 1 --python scripts/media_pc3/build_scene.py -- --layout planning/media/scene-layout-v1.json --fixture data/fixtures/cases.json --output .local/pc3-blender/representatives-01 --mode representatives --resolution 1280 720 --samples 32
```

`--python-exit-code 1`은 Blender 내부 Python 예외도 비정상 종료코드로 관측하기 위한 옵션이다. `prepare`는 실제 Blender 안에서 scene·288개 투영 metadata와 blend를 만들지만 PNG를 렌더하지 않는다. `representatives`는 새 scene에서 **1/133/288 프레임**, 즉 **0/5.5/11.958333초**를 렌더한다. 마지막 표본과 12초 영상 종료 경계를 구분한다.

현재 PC3에서 따로 꺼낸 동일 layout의 로컬 경로는 `.local/pc3-blender/input/scene-layout-v1.json`이다. 공용 planning 파일을 작업 브랜치에 임의 추가하지 않았다. pc1은 공용 경로를 사용할 수 있다.

출력:

- `case-0002-ww3.blend`: seed/카메라/프레임별 위치·회전을 포함하는 3D 장면.
- `frame-0001.png`, `frame-0133.png`, `frame-0288.png`: 대표 렌더일 때만 생성.
- `tracks.json`: 같은 카메라의 정규화 top-left bbox와 world position/yaw, 고정 사건·별도 경과시각. `synthetic-scene-ground-truth`.
- `render-report.json`: 실제 Blender 버전/engine/해상도, 렌더된 수/실측 시간, 입력·생성기·blend·PNG·tracks 해시. `visualGateAccepted=false`, `mainRegistration=false` 유지.

floor/장면은 지지면 상단0.85m, parcel mesh의 실제 바닥0.85m를 사용한다. 원점은 지지면에 두고 몸체 중심을 로컬0.175m에 둔다. runtime의 접촉 간격 검사는 world-space mesh bound의 minZ를 사용하며, 가드 관통·렌더 픽셀·가림까지 검증했다는 뜻은 아니다.

`clippedFrames`는 프레임 밖이나 카메라 뒤의 투영을 기록한다. bbox를 clamp해 정상으로 숨기지 않는다. 가림 검사는 `occlusionTested=false`이며 대표 렌더의 실제 물체 윤곽·마스크와 별도로 대조해야 한다. 전체 개요는 `--camera overview`로 새 output에만 만든다. `SYN-OVERVIEW-NOT-CCTV`의 bbox를 SYN-CAM-02에 등록하지 않는다.

## 검수 뒤에만 짧은 동작·최종 후보

대표3장의 물성·접촉·관통/부유·카메라·분기 방향을 pc1이 확인한 다음, 같은 코드/seed에서 확장한다. 아래 명령은 **현재 미실행**이다.

```powershell
& $blenderExe --background --factory-startup --python-exit-code 1 --python scripts/media_pc3/build_scene.py -- --layout planning/media/scene-layout-v1.json --output .local/pc3-blender/short-01 --mode short --resolution 1280 720 --samples 32
& $blenderExe --background --factory-startup --python-exit-code 1 --python scripts/media_pc3/build_scene.py -- --layout planning/media/scene-layout-v1.json --output .local/pc3-blender/final-01 --mode animation --resolution 1920 1080 --samples 64
```

short는 `[3,6)`초의 frame73..144 72장이다. final은 frame1..288 288장이다. 실제 FFmpeg 경로를 확인한 뒤 각각 다음처럼 인코딩한다. 덮어쓰기 거부 `-n`, H264/yuv420p/faststart를 사용한다.

```powershell
& $ffmpegExe -n -framerate 24 -start_number 73 -i .local/pc3-blender/short-01/frame-%04d.png -frames:v 72 -an -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart .local/pc3-blender/short-01/branch-preview.mp4
& $ffmpegExe -n -framerate 24 -start_number 1 -i .local/pc3-blender/final-01/frame-%04d.png -frames:v 288 -an -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart .local/pc3-blender/final-01/case-0002-ww3-blender.mp4
```

인코딩 성공만으로 재생/탐색/디코딩/전체화면 합성표시/288개 bbox 일치를 통과 처리하지 않는다. 후보는 별도 Release와 해시로 제출하며 기존 v1 Release·정본 fixture/manifest/public을 덮지 않는다. 현재 생성기는 자산 업로드나 등록을 실행하지 않는다.

## Blender 없이 실행 가능한 검사

```powershell
python -m py_compile scripts/media_pc3/build_scene.py scripts/media_pc3/scene_contract.py
python -m unittest discover -s tests/remote/pc3 -p test_scene_contract.py -v
```

이는 문법/순수 데이터·기하 검사이며 bpy API 호환, 실제 장면 생성·렌더·시각 게이트를 대신하지 않는다. 성능 벤치마크·대표이미지·MP4가 없으면 미실행으로 회신한다.
