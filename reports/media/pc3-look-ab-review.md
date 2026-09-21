# PC3 조명·재질 A/B 독립 검수

2026-09-21 20:58 KST, pc1 CJJ의 별도 검증 에이전트. 대상은 `d67b2c7c60c9bf08ec7d29555366e0e33a9790f6`입니다. **동일 소스 A/B 대표 6장을 실제 렌더하고 모두 직접 관찰했습니다. B는 재질 구분이 개선돼 다음 짧은 동작 검토의 후보로 권고하지만 최종 영상 품질은 미통과입니다.** 그림자 입자와 비어 보이는 주변 공간이 남아 있습니다.

20:39~20:43에는 가용 RAM이 2GiB보다 낮아 렌더 0/6으로 중단했습니다. 메인의 브라우저/빌드 종료 통보 후 현재 RAM을 다시 확인하고 20:55~20:56에 실행했습니다. 이전 미기동 기록은 실패/대기 이력으로 보존하며 현재 완료한 대표 렌더와 구분합니다.

작업 공간은 `.local/pc3-render-intake/look-ab-02/`, 고정 detached worktree는 그 아래 `review-d67b2c7/`입니다. 이전 기하 검토 `guard-02`와 그 3장은 보존했습니다. 이전 이미지를 이번 A/B의 A 또는 B로 재사용하지 않습니다.

## 검토한 변경과 비교 조건

기하 수정 커밋 `03291cca16310926a28a5b7d01ff02b9c0d2ec2e` 이후 바뀐 5개 파일은 A/B 보고서, Blender 사용 문서, 생성기, preset 모듈, preset 검사입니다. 해당 코드와 `reports/pc3/blender-look-ab.md`를 읽었습니다.

A는 `baseline`, B는 `contrast_material_v1`입니다. B는 world 강도·광원 3개의 에너지·콘크리트 색/거칠기/bump·강철 색/metallic/거칠기를 함께 바꿉니다. **설정 묶음의 효과를 비교하는 것이며 단일 노출 변경 실험이 아닙니다.** AgX, exposure 0, gamma 1은 둘 다 고정하도록 구현됐습니다.

실제 실행은 동일한 소스·layout·fixture·카메라·경로·seed에서 각각 대표 frame 1/133/288만 생성했습니다. EEVEE, 1280×720, 요청 32 samples, 단일 Blender 프로세스 `--threads 2`를 사용했습니다. 두 실행 모두 실제 property readback `scene.eevee.taa_render_samples=32`와 각 3회의 `Rendering 32 / 32 samples` 로그를 확인했습니다. 노출·gamma·AgX도 실제 런타임에서 각각 0·1·AgX였습니다.

## 실제 실행한 준비 검사

2026-09-21 20:39:48 KST에 기록한 결과입니다.

| 검사 | 기대 | 실측 |
|---|---|---|
| `python -B -m unittest discover -s scripts/media_pc3 -p test_look_presets.py -v` | 11개 검사 | **11/11 PASS**, unittest 내부 0.248초 |
| `python -B -m unittest discover -s tests/remote/pc3 -p test_scene_contract.py -v` | 12개 계약 검사 | **12/12 PASS**, 프로세스 전체 0.281초 |
| 고정 HEAD | `d67b2c7…` | 동일 |
| 대표 렌더 | A 3장 + B 3장 | **3장 + 3장, 완료** |
| A/B 시각 비교 | 6 PNG 직접 관찰 | **6장 직접 관찰, B 대비 개선/그림자 품질 보완** |
| 실제 결과 독립 대조 | 소스·기하·카메라·경로·설정·파일 확인 | **42/42 PASS**, 아래 범위 한정 |

11개 검사는 실제 생성기 AST를 사용해 baseline의 11개 재질·4개 광원·world가 이전 기하 커밋과 일치하는지, B가 허용한 설정만 바꾸는지, 잘못된 preset과 B의 short/animation이 거부되는지, 반환값 변경이 다른 호출에 새지 않는지 확인합니다. 원시 cuboid의 기하 동일성과 재질·광원·받침 변이 검출도 포함합니다. 이 결과는 bpy 실행·실제 mesh·시각 품질의 검증이 아닙니다.

메인의 layout/fixture를 `input/`에 바이트 그대로 복사했습니다. preset 검사가 요구하는 worktree의 ignored `.local/pc3-blender/input/scene-layout-v1.json`에도 같은 layout을 복사했습니다. 공용 planning·fixture·제품 코드를 수정하지 않았습니다.

| 고정 입력 | SHA256 |
|---|---|
| layout | `c6aece6692c6b78beb85d4f1167868f2bd095b3ab8366e837466715b82bd6cb6` |
| fixture | `79c3b01aed139352b5cc0a695f2829e76f78eabb61d7cfd6b8055db32f61a73b` |
| build_scene.py | `f54f3452fa276dd7480efc6fbeb00b05bf2c2b0d9b223d8b68a31c91841771b2` |
| scene_contract.py | `670638cae0357da1bf934b7c4b9287ea0780180214e53a181166dd53a8a554bf` |
| look_presets.py | `91c3852386c48729d24f69fff1049602451646a41c7d532d4dc4f8f008cd3e33` |

## 실제 메모리 게이트와 첫 중단 이력

첫 렌더 명령은 `run_ab.py baseline`이었습니다. 래퍼가 Blender 시작 전에 메모리를 확인하고 `WAITING_MEMORY_NO_RENDER_STARTED`를 반환했습니다. Blender PID나 baseline 출력은 생성되지 않았습니다.

| KST | 실제 가용 메모리 | 판정 |
|---|---:|---|
| 20:39:55 | 1,986,654,208B, 약 1.850GiB | 2GiB 미만, Blender 미기동 |
| 20:41:38 | FreePhysicalMemory 1,728,688KiB, 약 1.649GiB | 계속 대기 |
| 20:42:56 | FreePhysicalMemory 1,471,908KiB, 약 1.404GiB | 계속 대기 |

첫 미기동 기록은 `.local/pc3-render-intake/look-ab-02/memory-blocked-baseline-203955.json`입니다. 다른 API·웹·브라우저 프로세스를 중지하지 않았습니다. 첫 검수 turn을 종료한 뒤 메인의 후속 배정을 받아 RAM을 새로 확인하고 재개했습니다. 과거 여유 메모리로 현재 게이트를 대신하지 않았습니다.

## 실제 재개·렌더와 독립 readback

준비 검사·입력 해시는 `pre-render-checks.json`, 실제 검사 출력은 `look-tests.log`, `contract-tests.log`에 있습니다. `run_ab.py`는 기존 출력 덮어쓰기와 입력 변경을 거부하고 각 렌더 직전에 2GiB를 다시 확인합니다. prepare를 재실행하거나 입력/결과 폴더를 삭제하지 않았습니다. 아래 두 명령을 순서대로 실제 실행했습니다. 현재 결과가 존재하므로 반복 실행으로 덮지 않습니다.

```powershell
& 'C:/00.프로젝트/happycall-ralphthon/.venv/Scripts/python.exe' -B 'C:/00.프로젝트/happycall-ralphthon/.local/pc3-render-intake/look-ab-02/run_ab.py' baseline
# A의 정상 종료를 확인한 뒤 B를 실행했습니다.
& 'C:/00.프로젝트/happycall-ralphthon/.venv/Scripts/python.exe' -B 'C:/00.프로젝트/happycall-ralphthon/.local/pc3-render-intake/look-ab-02/run_ab.py' contrast_material_v1
```

| 실측 | A baseline | B contrast_material_v1 |
|---|---|---|
| 시작 RAM | 2,899,079,168B, 약 2.700GiB | 2,736,324,608B, 약 2.548GiB |
| PID | 29584 | 20668 |
| KST | 20:55:53.379 → 20:56:13.048 | 20:56:19.495 → 20:56:36.147 |
| 전체 프로세스 시간 | 19.656초 | 16.656초 |
| 생성기 내부 시간 | 16.417초 | 15.738초 |
| 종료코드 | 0 | 0 |
| 프레임별 생성 시간 | 6.985 / 3.204 / 3.055초 | 6.230 / 3.048 / 3.092초 |
| 요청 / 런타임 / 로그 샘플 | 32 / 32 / 3프레임 32/32 | 32 / 32 / 3프레임 32/32 |
| 실제 threads | FIXED / 2 | FIXED / 2 |
| 실제 색 관리 | AgX / exposure 0 / gamma 1 | AgX / exposure 0 / gamma 1 |
| 결과 파일 | 7개 | 7개 |

각 결과는 PNG 3개·blend·tracks·생성기 report·독립 readback JSON입니다. `inspect_scene.py`를 생성기 다음 `--python` 인자로 지정해 **같은 Blender 프로세스에서 실제 실행**했습니다. 268개 evaluated mesh의 local vertices/topology는 렌더 마지막 시점에 읽고, 비광원 object의 world transform은 frame 1/133/288에서 읽었습니다. Blender 장치의 정확한 GPU 드라이버 이름을 측정했다고 주장하지 않습니다.

`compare_ab.py`가 결과를 다시 읽어 비교한 **42/42 항목 PASS**는 아래 범위입니다. 이 42개 대조를 사람 사용성 검증이나 품질 점수로 세지 않습니다.

- 생성기/의존 모듈/layout/fixture는 A/B 및 각 실행 전후 동일합니다.
- evaluated mesh **268개**의 local vertices/topology SHA는 모두 `3a3be19bb13f09a1dd8d2b773f840885d81ca9f0d126e0e0b0a7c8a7b0c8d563`입니다.
- 3시점 비광원 object transform SHA는 `6f858447876cbafc8802aa28cdb36728fe8491569e86933ee00c24fd19d498f2`로 동일합니다. 카메라 SYN-CAM-02의 32mm lens와 행렬도 동일합니다.
- `tracks.json`은 바이트까지 동일하고 SHA는 `9fb424be0fd212bbf3faa057097bec56c63a89e4b8ae08c524e5fd76b80fd44b`입니다. 프레임 288개, `SYN-VIS-PARCEL02`, 업무 토트 null 288/288, 동일 W-W3 시각·CH-02·D-02입니다.
- 광원 위치/크기/색은 같고 설정한 에너지 값만 다릅니다. belt/yellow/cardboard의 실제 material readback은 동일합니다. 물성 B의 효과는 concrete/steel/world/에너지 묶음의 효과입니다.
- 6 PNG의 실제 크기·SHA·1280×720 RGB 8bit 헤더가 report와 일치합니다. 실제 6장 모두 열었습니다.
- 실행 종료 후 PID 29584/20668 조회 결과 **0개**입니다. worktree tracked diff도 없습니다.

## 6장 직접 관찰과 품질 판정

| 관찰 대상 | A → B 차이와 판정 |
|---|---|
| 바닥·금속·벨트 | A의 밝은 회색 면들이 B에서는 구분됩니다. 금속 롤러의 가는 반사가 남고 어두운 프레임/벨트와 대비됩니다. 단순 검정 플라스틱처럼 모두 뭉개지지는 않았습니다. |
| 노란 가드·받침 | B에서 노란색과 진한 받침 연결이 더 선명합니다. 북/남/출구 가드의 지지 구조와 분기 개구부를 읽을 수 있습니다. |
| frame 1 / 접근 | 좌상단의 작은 상자와 흰 라벨이 모두 보입니다. B에서도 크기·위치·경계가 유지됩니다. |
| frame 133 / 분기 | 상자 회전·라벨·벨트 접촉을 읽을 수 있고 새 가드가 상자를 가리지 않습니다. B의 벨트와 상자 경계가 구분됩니다. |
| frame 288 / 출구 | 상자 바닥과 벨트의 관계, 출구 받침을 읽을 수 있습니다. 암부 때문에 접촉이 사라지지는 않았습니다. |
| 그림자 입자 | B에서도 컨베이어 다리 주변 바닥과 밝은 발판 가장자리의 점상 입자가 남고 대비가 높아 일부에서 더 눈에 띕니다. 노이즈 감소를 통과 처리하지 않습니다. 원인은 이 정지 6장만으로 확정하지 않습니다. |
| 공간 완성도 | 큰 빈 바닥과 적은 주변 설비 때문에 설명용 CG 인상이 남습니다. 실제 회사 시스템용 최종 CCTV 품질이라고 할 수준은 아닙니다. |
| 합성 표시 | 6장 모두 raw PNG의 SYNTHETIC SCENE / NOT CCTV·W-W3·business tote UNKNOWN 표시가 유지됩니다. |

빈 바닥 ROI의 밝기 비율은 선택적 진단이며 이번에는 측정하지 않았습니다. 값이 없는 목표 범위 0.65~0.90을 실측으로 옮기지 않았고, 단순 이미지 표준편차로 노이즈 감소를 주장하지 않았습니다. 사용자가 요구한 완성도에 도달했다는 판정과 대표 3장 비교에서 B가 더 읽기 쉽다는 판단을 구분합니다.

**선택 권고:** B를 다음 짧은 분기 동작 검토의 후보로 선택할 수 있습니다. 추가 배정으로 B의 short 제한을 명시적으로 조정한 뒤 [3,6)초의 72프레임만 검토하면 이동 연속성·상자/설비 관계·시간상 그림자 깜빡임을 확인할 수 있습니다. 이 보고에서 그 72프레임을 실행하거나 승인 처리하지 않았습니다. 그림자 품질이 미달이면 B의 기하·색/조명 값을 유지한 채 샘플 또는 그림자 설정 한 가지를 별도 작은 비교로 검증하는 것이 타당합니다. 12초/288프레임 최종 렌더·1080p 등록으로 바로 확대하지 않습니다.

## PNG 해시와 남은 범위

| 설정 / 파일 | 크기(B) | SHA256 |
|---|---:|---|
| A frame-0001.png | 1,006,002 | `dddacf3e8711f425e2d40892d3bd17ea75986f20594c36dcaf39ecf6fd4c2628` |
| A frame-0133.png | 1,010,001 | `b6f781a0019ce79ced0799e6b08b243283906e55b1aa9a6e3a418f136519b3a6` |
| A frame-0288.png | 1,010,917 | `2ce1ff3d0753ce10a95ed258d40ae5ae41de643c84613c3db26bcbe06e51e2e0` |
| B frame-0001.png | 1,046,436 | `cffd53357b58c4515456c69409843d4528ebb217b015b72e01cf778015c699d5` |
| B frame-0133.png | 1,050,075 | `8882290042f2fe11cca1ae04a1a62d14403152ed668384caf47682557dd5399c` |
| B frame-0288.png | 1,051,585 | `8fc083ee57d0d343782d074f7522220becee755447ade42c8a8aa09e2da57e29` |

전체 파일 SHA·명령·RAM·시각은 두 `*-process.json`, 런타임 관측은 각 `independent-scene-readback.json`, 독립 대조는 `independent-ab-comparison.json`에 있습니다. 대표 정지 6장은 연속 영상·전 시각의 mesh 충돌/가림·그림자 flicker·웹 재생·최종 빌드 인수를 대신하지 않습니다.

제품·ops·배포·Release·편지·유료 API·커밋 변경은 하지 않았습니다. 이번 소유 변경은 이 보고와 ignored `look-ab-02/` 검토 자료·렌더 결과입니다.
