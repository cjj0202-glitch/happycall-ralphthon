# PC3 B 설정 32→96 samples 독립 비교

2026-09-21 21:02 KST, pc1 CJJ의 별도 검증 에이전트. **96 samples 대표 3장을 실제 렌더하고 직접 확인했습니다. 넓은 바닥 그림자의 거친 입자는 줄었지만 발판의 밝은 점상 입자는 남습니다. 샘플 수만 계속 올려 최종 품질을 통과 처리하지 않습니다.**

대상은 동일 `d67b2c7c60c9bf08ec7d29555366e0e33a9790f6`의 `contrast_material_v1`입니다. 비교 기준은 직전에 실제 렌더한 `look-ab-02/contrast_material_v1`의 32 samples 3장입니다. 출력은 신규 `.local/pc3-render-intake/sampling-96-01/contrast-material-96/`로 분리했습니다. 기존 소스·그림·검사기를 보존했습니다.

## 작은 실험과 실제 실행

가설은 조명·재질·장면을 고정하고 샘플만 32→96으로 올리면 접촉 그림자의 입자가 줄어드는지입니다. 원격 제품 스크립트를 수정하지 않았고 출력 경로와 `--samples 96`만 바꿨습니다. 72/288프레임 전체 렌더나 동영상 인코딩은 하지 않았습니다.

21:00:08 첫 메모리 관측은 1,829,732KiB, 약 1.745GiB여서 시작하지 않았습니다. 새 단일 실행기를 준비한 뒤 실제 시작 직전에 다시 확인한 가용 RAM은 **2,778,722,304B, 약 2.588GiB**로 2GiB 게이트를 충족했습니다. 다른 API·브라우저·서버 프로세스를 중지하지 않았습니다.

실제 호출:

```powershell
& 'C:/00.프로젝트/happycall-ralphthon/.venv/Scripts/python.exe' -B 'C:/00.프로젝트/happycall-ralphthon/.local/pc3-render-intake/sampling-96-01/run_sampling.py'
```

래퍼는 검증된 Blender 4.5.14 LTS를 숨김 단일 프로세스로 시작합니다. 인자는 `--background --factory-startup --threads 2 --python-exit-code 1`, 기존 고정 생성기와 독립 readback 검사기, 기존 layout/fixture, `--mode representatives --resolution 1280 720 --samples 96 --look contrast_material_v1`입니다. 전체 명령은 `sampling-96-01/render-process.json`에 있습니다. 이 실행기는 기존 output이 있으면 거부하며 자동 재시도하지 않습니다.

| 측정 | 32 samples 기준 | 96 samples 이번 실행 |
|---|---:|---:|
| 실제 시작/종료 KST | 20:56:19.495 → 20:56:36.147 | 21:00:44.507 → 21:01:17.720 |
| PID / 종료 | 20668 / exit 0 | 29960 / exit 0 |
| 전체 프로세스 시간 | 16.656초 | **33.203초** |
| 생성기 내부 시간 | 15.738초 | 32.210초 |
| frame 1 / 133 / 288 시간 | 6.230 / 3.048 / 3.092초 | 12.000 / 8.454 / 8.450초 |
| 실제 samples | 32 | 96 |
| 로그 완료 표기 | 32/32 × 3프레임 | 96/96 × 3프레임 |
| threads | FIXED / 2 | FIXED / 2 |
| AgX / 노출 / gamma | AgX / 0 / 1 | AgX / 0 / 1 |

전체 실행은 요청한 **30초 목표보다 3.203초 길었으며**, 32 samples 대비 **1.993배**입니다. 30초 안에 완료했다고 기록하지 않습니다. 이미 제한한 대표 3장으로 종료했고 추가 샘플/전체 렌더를 이어 실행하지 않았습니다. 완료 후 해당 PID 조회는 0개입니다.

## 비교 조건의 독립 확인

`compare_sampling.py`가 기존 32 결과와 이번 96 결과를 읽고 아래 **8/8 PASS**를 기록했습니다. 이는 비교 통제와 산출물 정합성 검사이며 시각 품질 점수가 아닙니다.

1. 실제 `independent-scene-readback.json`의 달라진 키는 `runtimeSamples` 하나입니다.
2. 실제 값이 32→96이고 요청값을 복사한 것이 아닙니다.
3. 실행 명령에서 달라진 값도 output 경로와 samples 두 값뿐입니다.
4. 소스·layout·fixture·의존 모듈·검사기 SHA가 32 기준 및 실행 전후 동일합니다.
5. tracks가 바이트까지 같습니다.
6. preset 전체·색 관리·사건·seed·카메라·소스 의존 계약이 같습니다.
7. 실제 로그에 `Rendering 96 / 96 samples`가 정확히 세 번 있습니다.
8. PNG 3장의 실제 크기·SHA가 생성기 report와 같습니다.

실제 evaluated mesh 268개의 local vertices/topology SHA는 `3a3be19bb13f09a1dd8d2b773f840885d81ca9f0d126e0e0b0a7c8a7b0c8d563`, 대표 3시점 비광원 transform SHA는 `6f858447876cbafc8802aa28cdb36728fe8491569e86933ee00c24fd19d498f2`로 기준과 같습니다. tracks SHA는 `9fb424be0fd212bbf3faa057097bec56c63a89e4b8ae08c524e5fd76b80fd44b`이며 CASE-0002/W-W3, SYN-CAM-02, CH-02/D-02, `SYN-VIS-PARCEL02`, 업무 토트 null을 유지합니다.

핵심 입력 SHA:

| 입력 | SHA256 |
|---|---|
| build_scene.py | `f54f3452fa276dd7480efc6fbeb00b05bf2c2b0d9b223d8b68a31c91841771b2` |
| look_presets.py | `91c3852386c48729d24f69fff1049602451646a41c7d532d4dc4f8f008cd3e33` |
| scene_contract.py | `670638cae0357da1bf934b7c4b9287ea0780180214e53a181166dd53a8a554bf` |
| layout | `c6aece6692c6b78beb85d4f1167868f2bd095b3ab8366e837466715b82bd6cb6` |
| fixture | `79c3b01aed139352b5cc0a695f2829e76f78eabb61d7cfd6b8055db32f61a73b` |

## 원본 3장 관찰

새 frame 1/133/288을 모두 직접 열었고, 기존 B frame 133도 다시 열어 같은 분기 장면을 대조했습니다. 32의 세 장은 직전 A/B 검수에서 모두 직접 관찰한 원본입니다.

- 96에서는 컨베이어 아래 넓은 바닥 그림자의 거친 얼룩이 더 고르게 보입니다. 32에서 눈에 띄던 다리 주변의 굵은 입자가 일부 완화됩니다. 이는 이 세 정지 이미지의 시각 관찰이며 정량적 노이즈 감소율을 계산한 것은 아닙니다.
- 금속 발판의 테두리·윗면에 밝은 흰 점과 어두운 점이 남습니다. 넓은 그림자가 개선돼도 이 부분은 깨끗해졌다고 판정하기 어렵습니다. 샘플링이 일부 영향을 준 것으로 볼 수 있으나 잔존 원인을 그림자·반사·표면 겹침 중 하나로 확정하지 않습니다.
- 상자 라벨·가드 지지·롤러 반사·분기 개구부·접촉 경계는 유지됩니다. 형태를 흐리거나 노출을 낮춰 결함을 가린 변경이 아닙니다.
- 합성 장면·실 CCTV 아님·업무 토트 미확인 문구가 세 PNG에 남아 있습니다. 빈 주변 공간과 설명용 CG 인상은 이번 샘플 조정의 해결 대상이 아니며 그대로 남습니다.

**다음 권고:** 렌더 예산을 더 쓰며 samples를 계속 늘리기보다, 발판 한 구간의 재질 반사/그림자/겹침 원인을 한 가지씩 분리해 확인하는 것이 우선입니다. 96은 부분 개선과 약 2배 비용이 확인된 후보이지 전체 영상 최종값이 아닙니다. 이후 짧은 움직임에서 시간상 깜빡임을 확인하기 전에는 최종 CCTV 품질로 인수하지 않습니다. 별도 주변 환경 개선과 이 샘플 실험의 효과를 섞지 않습니다.

## 실제 산출물

| 파일 | 크기(B) | SHA256 |
|---|---:|---|
| frame-0001.png | 1,023,262 | `2dda8fa2a460b117559acde22917cbf747803c7a1d324c9258c3da56791c50aa` |
| frame-0133.png | 1,027,221 | `749d47be231245148a15347436d9bad71a1551d5ed6a16504e4c3b7f950cdd9f` |
| frame-0288.png | 1,028,262 | `22bf28f2ad4bef3abcc9275d7def1edf4ce9084ea40f59480ab9615356eb659f` |
| render-report.json | 3,860 | `405f08f9bab37f36929aa263dee09270b0e6a7d26f2874b83a2e4aaa33b0d4ae` |
| independent-scene-readback.json | 5,680 | `58364c23e795746cf07ce2ef07a3d3cf192b04965b3867349129cd9af5dba859` |

산출물은 신규 로컬 폴더에만 있습니다. 공용 제품 스크립트·메인 UI·manifest·배포·Release·편지·커밋은 변경하지 않았습니다. 대표 3장과 288개 위치 metadata를 전체 영상·전 프레임 충돌/가림·temporal flicker 검증으로 확대하지 않습니다.
