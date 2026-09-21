# N03-M2 EEVEE 그림자 설정 전달

**현재 상태: pc1의 실제 렌더 관측을 읽고 생성기 옵션·명령으로 전달하는 문서다. PC3에서 Blender를 실행하거나 새 이미지를 렌더한 결과가 아니다.** root가 인증한 pc1 #9 comment `5760328590`의 명시적 다음 후보는 **EEVEE / samples96 / shadow rays4 / threads2**다. 기존 기본값 samples32/rays1은 유지한다. 환경 추가 48개 geometry와 배치·조명·look·사건 경로는 이번 설정 전달에서 변경하지 않는다.

## 읽은 정본과 실제 관측의 귀속

읽기 기준은 `origin/main`의 `de68b137dad0cc5c5a2f5e026ff3a95c061c47f8`이다.

- [pc1의 32→96 samples 보고](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/de68b137dad0cc5c5a2f5e026ff3a95c061c47f8/reports/media/pc3-sampling-review.md): pc1 검증 에이전트가 동일 구버전 geometry `d67b2c7c60c9bf08ec7d29555366e0e33a9790f6`와 B look으로 대표 1/133/288을 실제 렌더하고 직접 관찰했다. 넓은 바닥 그림자의 거친 입자는 줄었지만 발판의 밝은 점상 입자가 남았다고 보고했다. 정량 노이즈 감소율은 측정하지 않았다.
- [pc1의 shadow rays·엔진 보고](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/de68b137dad0cc5c5a2f5e026ff3a95c061c47f8/reports/media/pc3-engine-shadow-review.md): pc1이 같은 frame133에서 EEVEE96의 rays1→4를 단독 변경하여 발판 입자가 뚜렷하게 줄고 금속판·롤러·접촉이 읽힌다고 보고했다. Cycles CPU16+OIDN은 바닥 그림자가 부드럽지만 금속 반사에 거친 흔적이 남았다고 보고했다.
- 위 관측은 이번 작성자가 새 PNG를 내려받거나 직접 열어 확인한 관측이 아니다. 이전 geometry의 결과를 새 `staging_v1` 품질 증거로 대체하지 않는다.

| pc1 실측 항목 | 값 | 적용 한계 |
|---|---|---|
| 32→96 대표 3장 전체 프로세스 | 16.656→33.203초 | 96 실행은 30초 목표를 3.203초 넘었다. 다음 실행 완료시간을 보증하지 않는다 |
| EEVEE96/rays4, frame133 1장 | 프로세스 28.453초 / render 호출 27.360초 | cold frame 준비 비용을 포함한다 |
| Cycles CPU16+OIDN, frame133 1장 | 프로세스 34.953초 / render 호출 34.110초 | 엔진·samples·denoise 묶음 비교이며 EEVEE rays 한 변수 실험과 다르다 |
| 실제 Blender / threads | 4.5.14 LTS / FIXED 2 | PC1 런타임 관측이다 |
| 독립 대조 | sampling 8/8, engine/shadow 15/15 PASS | 비교 조건·파일·로그·기하 보존의 검사이며 최종 시각 인수 점수가 아니다 |
| `scene.eevee.shadow_ray_count` 실제 RNA | hard range 1..4, 원본값 1 | 8은 이 런타임에서 지원되지 않는다. clamp된 값을 요청값으로 보고하지 않는다 |

PC1의 기존 EEVEE inspector가 Cycles 결과에도 EEVEE property 값96을 남긴 한계가 보고됐다. Cycles 실효값은 별도 `runtimeAfter.cyclesSamples=16`과 `Sample 16/16` 로그로 확인한 값이다. EEVEE readback을 Cycles sample 증거로 쓰지 않는다. 한 프레임 실측을 72/288프레임·1080p·추가 환경의 시간 보장으로 환산하지 않는다.

## PC3 root의 별도 수신·원본 관찰

root는 `D:\hwana\Downloads\happycall-blender-shadow-review-20260921`에 Release 자산 4개를 받았고, GitHub 선언 byte/SHA 대조 4/4와 manifest의 PNG 대조 3/3을 확인했다고 보고했다. 실제 수신 해시와 관측은 `reports/pc3/shadow-release-intake.json`에 별도로 기록한다. 생성은 PC1, 다운로드·원본 이미지 열람은 PC3 root의 수행으로 구분한다.

root는 3개 원본 이미지를 직접 열어 EEVEE96/rays4의 발판 밝은 점·바닥 입자가 줄고 롤러·가드 선이 유지되는 반면, Cycles16+denoise의 롤러·프레임 반사선은 거칠게 보였다고 보고했다. **PC3 root가 확보한 비교는 32/rays1 대 96/rays4의 묶음 효과**다. 96/rays1 이미지는 이번에 받지 않았으므로 PC3 관찰을 rays 단독 변경의 인과 증거로 추가하지 않는다. rays만의 실험은 앞 절의 PC1 정본 보고서에 귀속한다. 이 수신 확인으로 새 환경 렌더나 최종 영상 품질을 통과 처리하지 않는다.

## 생성기 옵션과 엄격한 readback

- `--samples` 기본32 유지. `--shadow-rays`는 정수1..4만 허용하고 기본1이다. 0·5·8·비정수·별칭을 받아 clamp하지 않는다.
- `shadow_settings.py`가 EEVEE의 실제 RNA `hard_min`/`hard_max` 안에 요청값이 있는지 먼저 확인한 후 설정하고 다시 읽는다. property 누락, 런타임 범위 초과, clamp, 반환 타입·값 불일치가 있으면 오류로 끝낸다. 이 검사는 tracks/save/render 전에 수행한다.
- report의 `shadowRays`는 `requested`, `actual`, `applied`, `property`, `range`, `note`를 가진다. `range.cli=[1,4]`, EEVEE의 `range.runtime`은 실제 `{min,max}`다. 성공 때도 요청값을 복사해 actual로 기록하지 않는다.
- Cycles에서 기본 rays1은 EEVEE 설정을 적용하지 않는다. `applied=false`, `actual=null`, `property=null`, `range.runtime=null`로 기록한다. Cycles와 비기본 rays2..4 조합은 parser와 helper가 거부한다. EEVEE 전용 설정의 성공을 Cycles에 주장하지 않는다.
- `shadow_settings.py` 해시를 항상 sourceDependencies에 넣는다. 기본 의존 모듈은 3개, `staging_v1`은 `environment_detail.py`를 포함하여 4개다. 예전 소스·의존 해시와 새 전달본 해시를 동일하다고 쓰지 않는다.

## 새 후보 명령과 이전 예시의 대체

21:18 전달 예시의 samples32 후보 명령은 pc1의 명시적 **96/4** 요청에 따라 아래 명령으로 대체한다. 이는 기본값 변경이나 과거 렌더 보고서 수정이 아니다. Blender의 thread 옵션은 원문과 같이 `--threads 2`로, Python 인자 구분자 `--`보다 앞에 둔다. 실행 PC에서 이미 확인한 실제 `$blenderExe`를 사용하고 각 output은 새 빈 경로여야 한다.

```powershell
& $blenderExe --background --factory-startup --threads 2 --python-exit-code 1 --python scripts/media_pc3/build_scene.py -- --layout planning/media/scene-layout-v1.json --fixture data/fixtures/cases.json --output .local/pc3-blender/staging-shadow4-prepare-01 --mode prepare --engine eevee --camera cctv --resolution 1280 720 --samples 96 --shadow-rays 4 --look contrast_material_v1 --environment-detail staging_v1
& $blenderExe --background --factory-startup --threads 2 --python-exit-code 1 --python scripts/media_pc3/build_scene.py -- --layout planning/media/scene-layout-v1.json --fixture data/fixtures/cases.json --output .local/pc3-blender/staging-shadow4-representatives-01 --mode representatives --engine eevee --camera cctv --resolution 1280 720 --samples 96 --shadow-rays 4 --look contrast_material_v1 --environment-detail staging_v1
```

prepare는 실제 Blender scene과 metadata를 만들지만 PNG 렌더가 아니다. representatives는 1/133/288 세 장만 만든다. 새 환경의 대표 장면을 pc1이 수용한 뒤에만 같은 조건의 short 73..144/72장을 고려한다. short 명령은 [BLENDER.md](../../scripts/media_pc3/BLENDER.md)를 따른다. **이번 전달은 288프레임 animation 후보·영상 등록을 허용하지 않는다.**

## 전달 뒤 확인할 증거와 미완료 항목

1. 고정 커밋·생성기/의존 모듈/layout/fixture 해시, 환경48개 목록과 사건·경로 계약을 기록한다.
2. 실제 engine=EEVEE, samples96 property/readback와 완료 로그, shadow requested4/actual4/appliedtrue, 실제 RNA 범위와 threads2를 기록한다. 설정 요청만으로 PASS를 쓰지 않는다.
3. 새 대표 3장과 report/tracks SHA를 확인하고 상자·가드·바닥 접촉, 분기 판독, 물성, 점상 입자, 새 환경 가림을 다시 검수한다. 원본 PNG를 blur/DOF로 덮어 문제를 숨기지 않는다.
4. 실제 입력·출력과 실행시간을 기록한다. PC1의 기존 28.453초 관측을 새 환경 또는 전체 영상의 완료 약속으로 쓰지 않는다.

## PC3 최종 코드 검증

21:24:54 KST 독립 검증은 **33/33 PASS**다. 새 shadow 설정 11개(0.514초), 변경 영향이 있는 환경 11개와 look 11개(1.983초)를 검사했다. 기존 scene contract 12개는 소스가 바뀌지 않아 이번에는 반복하지 않았으며 8823de2의 이전 검증과 구분한다.

```powershell
python -B -m unittest discover -s scripts/media_pc3 -p test_shadow_settings.py -v
python -B -m unittest discover -s scripts/media_pc3 -p test_environment_detail.py -v
python -B -m unittest discover -s scripts/media_pc3 -p test_look_presets.py -v
```

모의 RNA에서 요청1..4 성공, 범위 밖0/5/8·bool·비정수 거부, 누락 속성6종·잘못된 범위7종·setter 예외/값 보정/미적용/거짓 타입6종의 실패 처리를 확인했다. 런타임 범위1..2에 요청4이면 설정 전에 거부한다. Cycles는 EEVEE 속성 접근 없이 actual=null/applied=false를 반환하고 비기본값은 거부한다. 실제 main의 새 호출 AST를 모의 scene으로 실행해 tracks/save/render 이전 검증과 반환 객체의 보고서 기록을 확인했다.

8823de2 대비 기존 build와 장면 helper AST가 동일하고, main은 shadow 설정 한 줄·보고 필드·의존 해시 추가만 허용해 대조했다. 환경 재검의 41,472 경로 쌍 충돌0·331,776 광선/AABB 쌍 교차0도 유지됐다. 정확한 분모·코드 SHA·미검증 범위는 `shadow-settings-checks.json`, 수신한4파일의 bytes/SHA와 이미지 관찰은 `shadow-release-intake.json`에 기록했다. 최초 A/B 수신기는 과거2의존성 계약 전용이므로 새3/4의존성 산출물을 자동 통과시키지 않는다.

이 결과는 순수 Python의 모의 scene/RNA 검사이며 PC3가 Blender의 실제 readback을 측정한 증거가 아니다. 새 환경의 대표 렌더, 시간상 깜빡임, 72/288 렌더, 인코딩, 웹 통합 인수는 미완료다. 최종 품질 수용은 여전히 false다.
