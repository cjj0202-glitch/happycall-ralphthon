# N03-M2 조명·재질 A/B 대표 프레임 실험 준비

**현재 상태: 설정 모듈과 생성기 CLI 통합. 새 A/B 렌더는 미실행이며 품질 개선을 확인하지 않았다.** `scripts/media_pc3/look_presets.py`는 Python 표준 라이브러리만 사용한다. 기하 수정 `03291cca16310926a28a5b7d01ff02b9c0d2ec2e`를 pc1에 먼저 전달한 뒤 이 비교 설정을 추가했다. pc1의 Blender 런타임에서 대표 프레임만 비교한다.

## 실제로 확인한 자료와 한계

- 기존 대표 PNG `frame-0001.png`, `frame-0133.png`, `frame-0288.png`와 `render-report.json`을 `D:\hwana\Downloads\happycall-blender-representatives-20260921`에서 읽고 세 이미지를 직접 확인했다.
- 기준 이미지 `.local/pc3-blender/input/warehouse-look-v1.png`와 `scripts/media_pc3/build_scene.py`를 읽었다. 원본 회사 도면에는 접근하지 않았다.
- 기존 세 PNG는 바닥이 밝고 균일한 회색으로 보이고, 롤러·프레임·노란 가드의 밝은 면 구분이 약하다. 다리 주변과 컨베이어 아래에 점상 입자가 보인다. 정지 이미지로 그림자 샘플링과 재질 노멀 중 원인을 확정하지 않는다.
- 기존 `render-report.json`은 Blender 4.5.14 LTS / EEVEE / 1280×720 / `requestedSamples=32` / 대표 프레임 3개를 기록한다. 생성기 SHA256은 `561d2a9b0b53e5cb944465eb9cae315e4c47d739b2b0341b2c21a96939406375`다.
- **기존 3개 PNG는 이전 geometry의 참고 자료다. 이번 비교의 A로 재사용하지 않는다.** geometry 변경과 조명 변경의 영향을 섞지 않도록 새 geometry가 반영된 동일 커밋에서 A와 B를 모두 새로 렌더해야 한다.

## 가설과 하나의 B 후보

`contrast_material_v1`은 fill 비중과 바닥 확산광을 줄여 접촉면 명암을 드러내고, 콘크리트의 미세 노멀 요철을 줄이면서 강철에는 좁은 반사를 남기려는 후보다. 여러 조명·재질 값을 함께 바꾸므로 비교에서 확인할 수 있는 것은 이 preset 전체의 효과다. 개별 파라미터의 인과 효과나 점상 그림자 제거를 미리 주장하지 않는다.

| 설정 | A: `baseline` | B: `contrast_material_v1` |
|---|---:|---:|
| World Background Strength | 0.32 | 0.12 |
| Large soft loading-side light / W | 3800 | 1800 |
| Ceiling key / W | 3300 | 3300 |
| Warehouse fill / W | 2100 | 650 |
| Chute rim / W | 1700 | 900 |
| Concrete Base Color | (0.28, 0.30, 0.31) | (0.20, 0.215, 0.225) |
| Concrete Roughness | 0.36 | 0.43 |
| Concrete Bump Strength | 0.16 | 0.06 |
| Concrete Bump Distance / m | 0.008 | 0.002 |
| Steel Base Color | (0.42, 0.46, 0.49) | (0.32, 0.35, 0.38) |
| Steel Metallic | 0.78 | 0.88 |
| Steel Roughness | 0.29 | 0.24 |

색은 기존 Blender 노드에 전달하는 RGB 값과 같은 의미다. 재질의 기존 Noise→ColorRamp 연결과 ramp 배율은 유지한다. Concrete bump 변경을 다른 noise 재질인 belt/card에 적용하지 않는다. 이 설정은 그림자 필터나 전역 이미지 필터가 아니다.

## 모듈 계약과 통합 경계

`settings_for(name)`은 `worldStrength`, `lightEnergies`, `concrete`, `steel` 네 키를 가진 새 중첩 dict를 반환한다. `lightEnergies`의 네 키는 위 표의 Blender light 이름과 정확히 일치한다. `concrete`는 `color`, `roughness`, `bumpStrength`, `bumpDistance`; `steel`은 `color`, `metallic`, `roughness`를 가진다. RGB는 세 원소 list다.

- 허용 이름은 `baseline`, `contrast_material_v1` 두 개뿐이다. 대소문자 변경, 공백 보정, `A`/`B` 등의 별칭을 허용하지 않는다. 그 밖의 이름이나 문자열이 아닌 입력은 `ValueError`다.
- 반환값은 매 호출마다 deep copy한다. 한 실행의 설정값 변경이 다음 실행에 남지 않는다.
- 모듈은 Blender import, 파일·네트워크 I/O, 환경 변경을 수행하지 않는다. `build_scene.py --look baseline|contrast_material_v1`이 명시적으로 선택하고 적용하도록 통합했다. 기본값은 `baseline`이며 B는 prepare/representatives만 허용하고 short/animation은 거부한다. 실제 Blender 실행 결과는 아직 없다.
- preset으로 지정하지 않은 geometry, 접촉 높이, 경로, 보호대 틈, 노이즈 좌표·스케일, 조명 위치·target·size·색, 다른 재질은 A/B 사이에서 동일해야 한다.

## 같은 geometry에서 실행하는 A/B 절차

1. geometry 수정과 preset 통합을 마친 **하나의 고정 커밋**을 정한다. A/B는 그 커밋과 동일한 미변경 소스를 사용한다. 실행 직전 HEAD, 생성기·preset·layout·motion contract SHA256을 기록한다. HEAD나 코드 해시가 다르면 해당 결과는 비교 대상에서 제외한다.
2. 기존 파일을 덮어쓰지 않고 새 실행 디렉터리를 만든다. 예: `.local/pc3-blender/look-ab/<새 run-id>/baseline/`과 `.local/pc3-blender/look-ab/<새 run-id>/contrast_material_v1/`. 두 출력 폴더는 각각 비어 있어야 한다.
3. A/B 모두 EEVEE, 1280×720, 고정 CCTV `SYN-CAM-02`, 같은 camera transform/lens, 같은 경로·seed `20260921`, `representatives` 모드, 프레임 **1/133/288**을 사용한다. 시각은 각각 0 / 5.5 / 11.958333…초이며 eventAnchor 시각과 별개다.
4. 같은 Blender 버전·장치·렌더 옵션으로 `samples=32`를 요청한다. AgX, exposure=0, gamma=1, 조명 크기, 원본 프레임 출력 형식을 고정한다. DOF, motion blur, 전역 blur 또는 추가 후처리로 결함을 감추지 않는다.
5. **요청 샘플 수와 실효 샘플 수를 구분한다.** `requestedSamples=32`만으로 런타임 적용을 입증하지 않는다. pc1에서 해당 Blender EEVEE 버전의 실제 render-sample 속성·값을 읽어 기록한다. 실효값이 다르거나 확인되지 않으면 `unverified`로 남기고 32샘플 비교 PASS라고 쓰지 않는다.
6. A/B 각각 세 PNG, render report, tracks, 설정 이름과 전체 값, 런타임·소스 정보, 파일 SHA256을 보존한다. 워터마크·사건 연결·businessToteId=null 계약을 유지한다. 대표 PNG를 생성한 사실과 시각 수용 판정을 별도 필드로 기록한다.

geometry 대표 프레임 검수 뒤 pc1이 확인한 `$blenderExe`로 실행할 재현 명령은 다음과 같다. 두 폴더가 비어 있어야 하며, 이미 결과가 있으면 다른 새 run 번호를 사용한다.

```powershell
& $blenderExe --background --factory-startup --python-exit-code 1 --python scripts/media_pc3/build_scene.py -- --layout planning/media/scene-layout-v1.json --fixture data/fixtures/cases.json --output .local/pc3-blender/look-ab-01/baseline --mode representatives --resolution 1280 720 --samples 32 --look baseline
& $blenderExe --background --factory-startup --python-exit-code 1 --python scripts/media_pc3/build_scene.py -- --layout planning/media/scene-layout-v1.json --fixture data/fixtures/cases.json --output .local/pc3-blender/look-ab-01/contrast_material_v1 --mode representatives --resolution 1280 720 --samples 32 --look contrast_material_v1
```

새 render report는 `look.name/settings`, `colorManagement`, `runtimeSamples.property/value`, `sourceDependencies`를 기록한다. EEVEE 실효값은 `scene.eevee.taa_render_samples`를 런타임에서 읽고 해당 속성이 없으면 null을 남긴다. null을32로 대체하지 않으며 Blender 버전 차이를 성공으로 숨기지 않는다. `requestedSamples`는 별도 유지된다. 이 코드는 실제 장치의 내부 샘플링 알고리즘이나 노이즈 감소를 측정하지 않는다.

## 수용 판정과 선택적 진단

| 확인 항목 | 기대 | 보류 조건 |
|---|---|---|
| 재질 구분 | 세 프레임의 원본 100% 보기에서 바닥/강철/벨트/노란 가드가 구분되고 금속 반사가 남는다 | 단순히 전체가 어두워졌거나 강철이 회색 플라스틱처럼 보인다 |
| 접촉과 사건 판독 | 상자 라벨, 상자와 벨트 접촉, 다리의 바닥 접촉, 분기 틈이 A보다 읽기 어렵지 않다 | 암부에 접촉이 묻히거나 밝은 면이 뭉개지고 geometry 결함 판독이 어려워진다 |
| 점상 입자와 경계 | 같은 그림자·발판 crop에서 입자가 더 커지거나 강해지지 않고 접촉 경계가 보존된다 | 어둡게 숨기거나 경계를 퍼뜨린 것을 노이즈 개선으로 주장한다 |
| 비교 통제 | 같은 geometry·카메라·경로·실효 샘플·노출과 같은 크기에서 A/B를 대조한다 | 설정 이름 외 코드나 장면 조건이 달라 효과를 분리할 수 없다 |

선택적 수치 진단은 1280×720 원본의 빈 바닥 ROI `[x0,y0,x1,y1]=[1020,150,1180,210]`다. 새 geometry의 A에서 먼저 빈 바닥인지 확인한다. 물체·큰 경계가 겹치면 두 결과를 보기 전에 대체 ROI를 정하고 좌표·이유를 기록하거나 이 진단을 생략한다. 같은 ROI에서 각 pixel의 8-bit sRGB 밝기값 `Y'=0.2126R+0.7152G+0.0722B`를 구하고 중앙값의 B/A 비율을 비교한다. 이는 선형 물리 휘도가 아니다.

**B/A 0.65~0.90은 제안한 관찰 범위이며 측정 결과가 아니다.** 이 범위를 단독 합격 기준으로 쓰지 않는다. 범위를 만족해도 재질·접촉·노이즈 시각 검사를 통과해야 하며, 범위를 벗어나면 원인을 설명한다. 상자·반사·그림자 경계를 섞은 단순 pixel 표준편차로 샘플링 노이즈 감소를 단정하지 않는다. 세 정지 프레임은 영상의 temporal flicker 검증을 대체하지 못한다.

## 실행 기록과 종료 범위

PC3의 별도 보조검토에서 `python -m unittest discover -s scripts/media_pc3 -p test_look_presets.py -v`를 실제 실행해 **11/11 PASS**(0.609초)를 확인했다. 실제 생성기의 CLI 함수와 재질·광원 생성 호출을 AST에서 꺼내 Python recorder로 검사했으며 bpy는 실행하지 않았다. baseline의11개 재질·4개 광원·world 값은 `03291cca`와 같고, B는 지정한 floor/steel 필드·worldStrength·세 광원 에너지만 변경한다. 반환값 변이 격리, 미등록 이름/타입 거부, B의 short/animation 차단과 검사기 반례도 포함한다.

기하 감사기가 추출하는33개 cuboid(받침18개와 상자3개 부분 포함)는 이전 기하 커밋과 정확히 같다. 정규화 결과의 공통 SHA256은 `09c328e45bfe92443ea068ab2277815f1abb0882a9447eba791a7c67124ff032`다. 전체 Blender 장면 메쉬나 실제 카메라/그림자 렌더를 비교했다는 뜻은 아니다.

root는 실제 report의 `runtimeSamples` AST 표현식을 별도 가짜 scene으로 대조했다: EEVEE 컨테이너 없음→null, 샘플 속성 없음→null, 요청16/속성32→32, 요청16/Cycles속성64→64의 **4/4** 확인. 실제 Blender 실효샘플 값은 여전히 미확인이다. 생성기/preset py_compile와 git diff --check도 exit0이며, 검사 중 렌더·과금·설치는 없었다.

| 항목 | A | B |
|---|---|---|
| 상태 | 새 geometry A 미렌더 | B 미렌더 |
| 고정 커밋 / 소스 SHA256 / layout SHA256 | 실행 시 기록 | A와 동일 여부 기록 |
| preset 이름·전체 설정 | `baseline` / 본문 계약 | `contrast_material_v1` / 본문 계약 |
| Blender 버전 / engine / 실제 device | 실행 시 기록 | 실행 시 기록 |
| 요청 / 실효 샘플 | 32 / 미확인 | 32 / 미확인 |
| 대표 PNG 3개·SHA256·출력 경로 | 미생성 | 미생성 |
| 재질·접촉·그림자 시각 판정 | 미검사 | 미검사 |
| 선택 ROI 좌표 / 중앙값 / B:A | 미측정 | 미측정 |
| pc1 수용 여부 / 선택 이유 | 미판정 | 미판정 |

이 실험의 끝은 대표 프레임 A/B 대조와 pc1의 명시적 판정이다. **72프레임 short 또는 288프레임 전체 영상으로 확대하지 않는다.** 기존 세 PNG를 개선 증거로 재사용하거나 B 설정 작성만으로 품질 통과·영상 완성·배포 완료를 표시하지 않는다. 다음 렌더 범위는 pc1의 별도 배정에서 정한다.
