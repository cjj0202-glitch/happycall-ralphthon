# PC3 환경 소품 및 정식 shadow CLI 메인 독립 검증

검증일: 2026-09-21 KST. 검증 범위는 합성 장면이며 실제 CCTV·실제 물류 사고·작업자 귀책을 재구성하거나 판정하지 않습니다.

## 현재 판정

- 환경 후보 `8823de240e769dd7c5ed668a11ea4800a155b404`의 대표 3장(1/133/288)을 직접 열어 검수했습니다. 짧은 동작 검토로 진행할 수 있습니다.
- 정식 shadow CLI 후보 `33fa0e4edeb88c0d4ad5e9cc0194ffc7e96cebcd`를 새 detached worktree로 수신했습니다. 테스트 45/45 및 실제 Blender prepare·독립 readback을 통과했습니다.
- 두 후보의 evaluated 기하, 세 시각 변환, 카메라·조명·재질·렌더 설정, 추적 데이터가 일치했습니다. 동일한 대표 3장을 다시 렌더하지 않았습니다.
- 승인된 72프레임(73~144, 24fps의 3초 구간)을 정식 CLI로 실제 생성했습니다. 72/72 파일·SHA·샘플 로그·기하·추적·원본 보존을 검증했고, 6장을 직접 열었습니다. 동작 구간의 유한 ray 15,886개에서 가림이 없었으며 양성 대조 199/199를 통과했습니다.
- **판정: 720p 짧은 합성 동작 PNG 후보는 후속 UI/재생 검토에 인계 가능합니다.** MP4 재생·전체 288프레임·1080p·제품 등록·Release 업로드·실제 사고 귀책 검증까지 완료한 것은 아닙니다.

## 출처와 격리

| 구분 | 위치 / 값 |
|---|---|
| 기존 환경 대표 렌더 | `.local/pc3-render-intake/staging-01/representatives/` |
| 기존 8823de2 원본·초기 실패 보존 | `.local/pc3-render-intake/staging-01/source/`, `source-checks.json`, 최초 `*-tests.log` |
| 보완 후 34/34 테스트 | 같은 폴더 `source-checks-v2.json`, `*-tests-v2.log` |
| 신규 정식 CLI 격리 수신 | `.local/pc3-render-intake/short-33fa0e4-01/source/` — HEAD `33fa0e4edeb88c0d4ad5e9cc0194ffc7e96cebcd` |
| 신규 입력 동결 | `.local/pc3-render-intake/short-33fa0e4-01/input/` |
| 신규 출처·테스트 manifest | 같은 폴더 `source-intake.json` |
| 대표 장면 독립 실측 | `staging-01/inspection-actual/independent-scene-readback.json` |
| 새 CLI 독립 실측 | `short-33fa0e4-01/prepared/independent-scene-readback.json`, `equivalence.json` |

초기 8823de2 선별 수신에 `audit_guard_supports.py`가 누락되어 unittest import 2건이 실패한 이력이 있습니다. 메인의 `recheck.py`로 필요한 원본을 추가한 후 environment 11 + look 11 + contract 12 = 34건이 통과했습니다. 최초 실패 결과를 삭제하거나 성공으로 덮어쓰지 않았습니다.

33fa0e4는 전체 detached worktree를 새로 만들었습니다. 이 검증자가 메인 제품 파일이나 PC3 생성기를 수정하지 않았으며, 원격 source에도 override를 넣지 않았습니다. 실제 입력은 8823de2 대표 렌더에 사용한 로컬 동결본을 새 ignored input으로 복사했습니다.

| 입력 | 바이트 | SHA-256 |
|---|---:|---|
| `scene-layout-v1.json` | 1,772 | `c6aece6692c6b78beb85d4f1167868f2bd095b3ab8366e837466715b82bd6cb6` |
| `cases.json` | 23,430 | `79c3b01aed139352b5cc0a695f2829e76f78eabb61d7cfd6b8055db32f61a73b` |

## 정식 CLI 및 실제 장면 대조

독립 읽기 전용 diff 검토에서 8823de2→33fa0e4의 build/tracks 기하 생성과 7개 helper AST가 같음을 확인했습니다. 새 shadow 모듈은 타입·RNA 범위·readback을 검사하며, 이 설치본의 `shadow_ray_count` 지원 범위는 실제 RNA의 **1~4**입니다. 8을 지원한다고 기록하지 않았습니다.

```powershell
.venv/Scripts/python.exe -B .local/pc3-render-intake/short-33fa0e4-01/prepare-intake.py
```

이 명령은 원본 worktree 및 입력을 보존하고 아래 테스트, 기존 blend 읽기, 공식 CLI prepare를 순차 실행했습니다. 상세 전체 command 배열·PID·시각·RAM은 `inspection-882-process.json`, `prepare-cli-process.json`에 있습니다.

| 테스트 | 실행 파일 | 실제 결과 |
|---|---|---:|
| shadow 설정 | `test_shadow_settings.py` | 11/11 PASS |
| 환경 소품 | `test_environment_detail.py` | 11/11 PASS |
| look preset | `test_look_presets.py` | 11/11 PASS |
| scene contract | `test_scene_contract.py` | 12/12 PASS |
| 합계 | 새 33fa0e4 소스, Python unittest | **45/45 PASS** |

각 테스트는 `python -B -m unittest discover -s <directory> -p <filename> -v`로 실행했고 로그를 개별 보존했습니다. “shadow 단독 33건”이 아니라 위 실측 합계입니다.

prepare 실제 호출의 주요 인자:

```text
blender.exe --background --factory-startup --threads 2 --python-exit-code 1
  --python <33fa0e4-source>/scripts/media_pc3/build_scene.py
  --python <inspection-scene.py> --
  --layout <frozen-layout> --fixture <frozen-cases> --output <new-prepared>
  --mode prepare --engine eevee --camera cctv --resolution 1280 720
  --samples 96 --shadow-rays 4 --look contrast_material_v1 --environment-detail staging_v1
```

prepare: 21:36:45.967~21:36:51.145 KST, PID 4988, exit 0, **5.187초**. 시작 RAM 3,934,961,664B. prepare의 PNG 생성 수는 **0장**입니다. 기존 대표 blend의 읽기 전용 검사는 PID 10284, exit 0, 1.047초였습니다.

| 실제 bpy readback 항목 | 8823de2 wrapper / 33fa0e4 정식 CLI |
|---|---|
| Blender | 4.5.14 LTS / 동일 |
| 엔진 | BLENDER_EEVEE_NEXT / 동일 |
| samples | 96 / 96 |
| shadow rays | 4 / 4 |
| threads | FIXED 2 / FIXED 2 |
| 색 | AgX, exposure 0, gamma 1 / 동일 |
| 기존 mesh 수 | 268 / 268 |
| 추가 환경 mesh 수 | 48 / 48 |
| 전체 mesh 수 | 316 / 316 |
| 기존 evaluated local mesh SHA | `3a3be19bb13f09a1dd8d2b773f840885d81ca9f0d126e0e0b0a7c8a7b0c8d563` / 동일 |
| 전체 evaluated local mesh SHA | `51567277b813fd0f4414241100c396993db1e4c721c00eb239e849ac3e2d9f79` / 동일 |
| 기존 세 시각 world transform SHA | `6f858447876cbafc8802aa28cdb36728fe8491569e86933ee00c24fd19d498f2` / 동일 |
| 전체 세 시각 world transform SHA | `ac4723d5c5c26b86e3297356e15e3f304dd2b495f00dd60a68010ab9953a1094` / 동일 |
| tracks SHA | `9fb424be0fd212bbf3faa057097bec56c63a89e4b8ae08c524e5fd76b80fd44b` / 동일 |

검사기는 object 이름순 evaluated vertex/topology의 canonical JSON을 해시하고, frame 1/133/288의 비광원 world transform을 별도로 해시했습니다. 전체 JSON을 비교했으므로 카메라 행렬·렌즈, 4개 조명, 5개 주요 재질, world strength, 합성 stamp도 일치합니다. 같은 SHA라는 이유로 연속 충돌이나 모든 픽셀의 가림까지 증명한 것으로 해석하지 않습니다.

## 실제 환경 접촉 및 추적 제외

`inspection-environment.py`는 Blender에서 읽은 evaluated world bounds를 사용했습니다. 바퀴 8개, 랙 기둥 4개, 바닥선 4개, 선반 위 상자 4개의 접촉 20건 모두 허용오차 0.00001m 이내입니다. 바퀴 바닥 오차 -1.1365e-9m, 가장 큰 상자/선반 간격 1.4901e-8m입니다. 설계 좌표값을 다시 계산하는 것과 달리 실제 blend mesh를 읽었습니다.

환경 48개 모두 `synthetic=true`, `tracked=false`, `motion=static`, animation data 없음입니다. Blender custom property의 business ID는 null을 저장할 수 없어 `null (unassigned environment prop)` 안내 문자열이며, 공식 JSON에는 `businessToteId: null`입니다. 이 문자열을 실제 토트 ID로 해석하지 않습니다.

tracks는 288개 시간표본 전체에서 시각 객체 `SYN-VIS-PARCEL02` 한 개만 포함하고 businessToteId는 모두 null입니다. 환경 소품을 추적 객체로 추가하지 않았습니다. projected bounds의 화면 내 판정은 288/288, 수학적 접촉면 최대 오차는 3.5763e-8m입니다. **원 tracks의 `occlusionTested=false`는 그대로 유지**했으며, 화면 안에 있다는 수치로 가림 없음까지 주장하지 않습니다.

## 대표 3장 직접 픽셀 검수

메인 대표 렌더 실행: 21:27:34.446~21:28:21.457 KST, PID 30612, exit 0, **47.016초**. 이 실행은 8823de2 source를 그대로 두고 wrapper에서 EEVEE 96 / shadow 4 / threads 2를 설정한 실행이며, 정식 CLI 33fa0e4 실행과 구분합니다.

| 실제 PNG | 바이트 | SHA-256 |
|---|---:|---|
| frame-0001.png | 1,071,011 | `66ac9fa197cb948e99673a61d244fa4349ee61ae407f89f061b604372d0e6c2a` |
| frame-0133.png | 1,074,241 | `e2bb4a7df6842a69fec4d88fe7d3144f942fe5db7521cd90c43b973bdde8768a` |
| frame-0288.png | 1,075,306 | `b110f2c0a928b4f7a496f06db7507aa724499f09972cdcc498f51658285b42f7` |

세 PNG를 원본 크기로 직접 열었습니다.

- 뒤쪽 롤테이너 2대와 랙·상자 4개가 작업 공간의 맥락을 더합니다. 소품이 컨베이어 분기 안쪽이나 이동 상자 앞에 놓이지 않아 대표 세 시각의 기존 시야를 보존합니다.
- 롤테이너 바퀴와 랙 기둥이 바닥에 닿아 보이고, 상자가 선반에 얹혀 있습니다. 위 실측 접촉 검사와 픽셀 관찰이 같은 방향입니다.
- 북쪽·남쪽·출구 측면의 받침과 프레임 연결이 유지됩니다. 분기 출구의 개방부를 소품이 가리지 않습니다.
- shadow 4의 발판·다리 그림자가 이전 shadow 1보다 정리된 상태를 유지했습니다. 검정 벨트, 금속 프레임, 노랑 안전대, 상자 테이프·빈 라벨이 구분됩니다.
- `SYNTHETIC SCENE / NOT CCTV`, business tote UNKNOWN 안내가 원 PNG에 남아 있습니다.
- **남는 품질 차이:** 배경과 바닥이 매우 정돈돼 있으며 CG 재질과 형태가 읽힙니다. 실제 창고 사진 수준의 재질 불규칙성·생활감·다양한 작업 밀도까지 도달하지 않았습니다. 합성 장면의 기술 시연 후보로 적합하지만 “실제 CCTV” 또는 “실사 수준 완성”이라고 판정하지 않습니다.

## 72프레임 짧은 동작 — 실제 생성 및 검증 완료

```powershell
.venv/Scripts/python.exe -B .local/pc3-render-intake/short-33fa0e4-01/run-short.py
```

시작: 21:37:33.942 KST, 종료: **21:52:30.526 KST**, PID **17656**, **exit 0**, 전체 **896.578초(14분 56.6초)**. 시작 가용 RAM **3,994,533,888B**. 신규 `short/` 출력이며 기존 프레임을 덮지 않았습니다. `--mode short`만 변경했고 sample/shadow/카메라/기하/입력은 위 공식 prepare와 같습니다. 단일 Blender 프로세스의 FIXED 2 threads이며 다른 서버나 프로세스를 중단하지 않았습니다.

생성 중 21:43에 가용 RAM이 약 1.76GiB로 내려간 시점이 있었습니다. 기존 렌더만 유지하고 추가 Blender/브라우저/서버를 시작하지 않았습니다. 후속 Blender 검사는 렌더 종료와 가용 RAM 3,948,613,632B를 다시 확인한 뒤 순차 실행했습니다. 원 실행과 검사 PID 모두 정상 종료했습니다.

| 실측 항목 | 결과 |
|---|---|
| 프레임 파일명 | frame-0073.png~frame-0144.png, 누락·초과 없이 72장 |
| 전체 PNG 바이트 | **77,243,527B** |
| 실제 샘플 완료 로그 | 72개 프레임 모두 `Rendering 96 / 96 samples` |
| 프레임별 생성 시간 | 최저 10.821초 / 최고 15.481초 / 평균 12.364초 |
| 생성기 내부 전체 시간 | 895.277초; 프로세스 전체 896.578초와 구분 |
| 직접 연 원본 PNG | 73, 96, 112, 124, 133, 144 — 6장 |
| 모든 PNG SHA | `short-verification.json` 72건과 실제 파일 72/72 일치 |
| 공식 prepare/short readback | 전체 동일 — mesh 268+48, 기하·transform·카메라·조명·재질·설정·stamp |
| tracks | SHA `9fb424be0fd212bbf3faa057097bec56c63a89e4b8ae08c524e5fd76b80fd44b`, 기존/prepare/short 동일 |
| 원본 보존 | 기록한 `scripts/media_pc3/*.py` 전체·동결 입력 해시 불변, detached worktree `git status --short` 출력 없음 |
| saved blend | 3,056,663B, SHA `923503614759a5351bfac0d06d8883691d190b1fe43e3ce14b0f4d360fa89d5d` — 후속 검사 전후 동일 |

실제 영상 시각 표본은 3.0~5.958333초이고, 24fps로 재생할 경우 3초 분량입니다. 생성기 metadata의 `candidateDurationSeconds=12`, `candidateFrameCount=288`은 전체 후보 설계를 뜻하며, **실제 렌더 수 72를 288로 해석하지 않습니다.** 이 검증 단위에서 MP4를 만들거나 재생하지 않았습니다.

직접 연 6개 시각에서 상자가 롤러→중앙 벨트→분기 방향으로 진행하고 회전하며, 선택 상자의 접촉 그림자·테이프·라벨이 읽힙니다. 뒤쪽 롤테이너·선반이 시야를 가리지 않고 합성 표시도 유지됩니다. 6개의 정지 이미지를 확인했다는 사실을 72프레임 전체의 실시간 재생 검수로 부풀리지 않습니다.

| 표본 PNG | SHA-256 |
|---|---|
| frame-0073.png | `faf2f8fd163b2cf3ada06c7fcc4dfa7140a4fdbd266647d1e31e991527281a48` |
| frame-0133.png | `5b419d3a62329370615aab83fc317e88cef6e8aa4b2327cec9ae58bbcab709d1` |
| frame-0144.png | `fc1863d382d32867b22fd7b2feb73ddb3890b34a26637425e6f9d4a396e124ea` |

### 별도 가림 검사와 양성 대조

```powershell
.venv/Scripts/python.exe -B .local/pc3-render-intake/short-33fa0e4-01/post-review.py
```

PID 13992, 21:52:41.774~21:52:44.038, exit 0, **2.266초**. 저장된 short blend를 읽고 실제 evaluated 상자·테이프·라벨 mesh의 BVH와 전체 장면 first-hit를 비교했습니다. 각 frame의 projected bounds 안 21×15 격자에서 실제 상자 표면을 맞힌 광선만 집계했습니다.

- frame 73~144 **72시각**, 대상 표면 광선 **15,886개** 모두 보임. 환경 소품 가림 **0개**, 기타 가림 **0개**, 시각별 최소 표본 가시율 **1.0**.
- 검사기가 가림을 놓치지 않는지 확인하기 위해 frame 144에서 카메라 앞에 임시 가림판을 넣었습니다. 대상 표면 광선 **199/199개**가 가림판에 막힌 것으로 검출됐습니다.
- 임시 가림판은 메모리에서 제거했고 blend를 저장하지 않았습니다. 검사 전후 blend SHA가 동일합니다. 원 `tracks.json`의 `occlusionTested=false`도 변경하지 않았습니다.
- 이 결과는 **72개의 이산 시각과 유한한 광선 표본**에 대한 합성 기하 검사입니다. 프레임 사이 연속 시간, 모든 픽셀, 실제 카메라·실물 물류, 작업자 귀책까지 증명하지 않습니다.

### 시간에 따른 픽셀 변화 및 대표 비교

`inspect-pixel-stability.ps1`은 이미지 편집 없이 정적 랙 영역 `(900,120)~(1220,360)`을 8픽셀 간격으로 읽었습니다. frame 73을 기준으로 나머지 71장을 각 1,200개 RGB 표본으로 비교한 결과 평균 절대 채널 차이 **0**, 최대 차이 **0**입니다. 비교 대상이 잘못 고정되지 않았는지 확인한 이동 상자 영역의 73↔144 양성 대조는 1,989개 표본 중 **371개 변화**를 검출했습니다. 이 정적 영역 표본 결과를 전체 화면에 깜빡임이 없다는 보증으로 확대하지 않습니다.

기존 대표 frame 133과 short frame 133은 파일 SHA뿐 아니라 raw BGRA SHA도 서로 다릅니다. 추가 `inspect-representative-diff.ps1`로 921,600개 픽셀 전체를 비교한 결과 **8픽셀(약 0.000868%)**, 최대 채널 차이 **1**, RGB 평균 절대 차이 **0.000003979(0~255 척도)**입니다. 1을 초과한 채널 차이를 가진 픽셀은 0개입니다. 육안 검수에 영향을 주는 구조 변화로 관찰되지 않았지만, 원인을 별도로 분리하지 않았으므로 “바이트/픽셀 완전 동일”이라 쓰지 않습니다.

증거 위치: `short-verification.json`, `short-visibility.json`, `pixel-stability.json`, `representative-pixel-diff.json`, `post-review.json`. `final-summary.json`에는 이 증거 파일들의 SHA와 직접 확인한 6개 PNG의 SHA를 모았습니다.

다음 판단 단위는 이 72 PNG를 3초 재생 후보로 연결한 뒤 실제 플레이어의 재생·seek·track 동기화·시각 표기 검수입니다. 전체 288프레임/1080p 확대는 이 검증에서 실행하지 않았습니다. 메인·PC3 승인 절차와 최종 미디어 인수는 별도입니다.

## 변경 경계

검증자 소유 보고서는 이 파일 하나입니다. 실행/증거는 ignored `.local/pc3-render-intake/staging-01/inspection-*` 및 새 `short-33fa0e4-01/`에만 추가했습니다. 기존 대표 결과와 이전 검증 결과를 보존했습니다. 제품 코드·배포·공유 편지·커밋·Release 작업은 수행하지 않았습니다.
