# PC3 그림자 원인 분리와 엔진 비교

2026-09-21 21:10 KST, pc1 CJJ의 별도 검증 에이전트. **동일 분기 프레임에서 EEVEE 96 samples·shadow rays 4가 기존 발판 입자를 뚜렷하게 줄였습니다. Cycles CPU 16 samples+denoise는 바닥 그림자가 부드럽지만 금속 반사에 거친 흔적이 남아, 현재의 빠른 동작 검토 후보는 EEVEE 조합을 권고합니다.** 최종 영상 품질 인수나 전체 렌더 실행은 아닙니다.

구버전 기하 `d67b2c7c60c9bf08ec7d29555366e0e33a9790f6`와 B preset을 고정했습니다. 입력은 직전 96 samples `.blend`이며 SHA256은 `dde1c0d82ff4fe7a8184d2822d71d6e828f8066a5d0919b356818cf45b9fd385`입니다. 원본·생성기·제품 코드를 바꾸지 않고 새 `.local/pc3-render-intake/engine-shadow-01/`에만 진단 코드와 결과를 썼습니다.

## 지원 설정을 실제 확인한 결과

[Blender 4.5 공식 Sampling 문서](https://docs.blender.org/manual/ka/4.5/render/eevee/render_settings/sampling.html)는 그림자 rays를 각 광원에 추적하는 광선 수로 설명하며, 높은 값이 무작위 그림자 샘플링의 노이즈를 줄인다고 설명합니다. 영문 API/매뉴얼 직접 열기는 조회 오류가 있었으므로 허용 범위를 검색 내용만으로 추정하지 않고, 설치된 **Blender 4.5.14 LTS의 실제 RNA**로 다시 읽었습니다.

| 속성 | 실제 원본 값 | 실제 RNA 범위/지원 |
|---|---:|---|
| `scene.eevee.shadow_ray_count` | 1 | **1…4** |
| `scene.eevee.shadow_step_count` | 6 | 1…16 |
| `scene.eevee.taa_render_samples` | 96 | 존재 |
| Cycles device/samples/denoise/adaptive/time_limit | CPU / 4096 / true / true / 0초 | 모두 존재 |

**shadow rays 8은 이 런타임에서 지원되지 않습니다.** 메인에게 실제 범위와 대안을 보고한 뒤 1→4로 진행하라는 후속 지시를 받았습니다. 8을 넣어 clamp된 값을 8이라고 보고하지 않았습니다. `rna-probe.json`에 현재 값·hard/soft 범위·속성 설명이 있습니다.

RNA probe에서 denoiser의 enum default를 읽을 때 매칭 경고가 발생했습니다. 현재 값은 `OPENIMAGEDENOISE`였으며 이를 미확인 기본값 추정으로 바꾸지 않았습니다. 이후 실제 Cycles 렌더에서 같은 denoiser를 사용하고 16/16 완료까지 확인했습니다.

## 두 개의 한 프레임 실험

기존 1280×720, frame **133(시연 5.5초)**, AgX/노출 0/gamma 1, 같은 카메라·기하·재질·광원을 사용했습니다. 후보마다 원본 `.blend`를 새 프로세스에서 읽어 첫 후보 변경이 둘째로 새지 않게 했습니다.

1. **EEVEE 후보:** samples 96과 나머지 설정은 유지하고 shadow rays만 **1→4**로 변경했습니다. 실제 before/after 설정 차이도 `shadowRayCount` 하나입니다.
2. **Cycles 후보:** engine을 CYCLES, device CPU, samples 16, denoise true로 설정했습니다. 정확한 16 samples 비교를 위해 adaptive sampling을 false로 했고 안전 상한으로 `time_limit=150초`를 설정했습니다. 이 후보는 엔진·샘플·denoise의 묶음 비교이며 EEVEE의 한 속성 실험과 인과 범위가 다릅니다.

실제 재현 실행:

```powershell
& 'C:/00.프로젝트/happycall-ralphthon/.venv/Scripts/python.exe' -B 'C:/00.프로젝트/happycall-ralphthon/.local/pc3-render-intake/engine-shadow-01/run_one.py' eevee-shadow4
# 첫 프로세스 종료를 확인한 뒤에만 둘째 실행
& 'C:/00.프로젝트/happycall-ralphthon/.venv/Scripts/python.exe' -B 'C:/00.프로젝트/happycall-ralphthon/.local/pc3-render-intake/engine-shadow-01/run_one.py' cycles-cpu16
```

래퍼는 현재 입력 blend SHA와 기존 output 부재를 확인하며 실행 직전 RAM 2GiB를 다시 검사합니다. 프로세스는 숨김·단일·threads 2입니다. 외부 180초 한도를 넘으면 자신이 만든 Blender 그룹에만 정상 중단 신호를 보내도록 준비했습니다. 두 실행 모두 **36초 이내 정상 종료**해 내부 시간 제한이나 외부 중단 경로는 발동하지 않았습니다. 중단 경로를 실제 검증했다고 쓰지 않습니다. 다른 서버·브라우저 프로세스를 중지하지 않았습니다.

| 실측 | EEVEE96 / rays4 | Cycles CPU16 / denoise |
|---|---:|---:|
| 시작 RAM | 2,699,431,936B, 약 2.514GiB | 2,984,050,688B, 약 2.779GiB |
| PID | 28468 | 23840 |
| KST | 21:07:52.186 → 21:08:20.633 | 21:08:56.579 → 21:09:31.520 |
| 전체 프로세스 | 28.453초 | 34.953초 |
| 실제 render 호출 | 27.360초 | 34.110초 |
| 샘플 완료 로그 | `Rendering 96 / 96 samples` | `Sample 16/16`, `Finished` |
| 실제 CPU threads | FIXED / 2 | FIXED / 2 |
| 종료코드 | 0 | 0 |
| 실제 PNG | 1개 | 1개 |

EEVEE 전체 시간에는 한 프레임의 초기 준비·shader 비용이 포함됩니다. 기존 연속 3장 실행의 두 번째 프레임 8.454초와 이 cold frame 27.360초를 직접 나눠 shadow rays만의 성능 비용이라고 단정하지 않습니다.

## 기하·광원·카메라 보존과 한계

`compare_results.py`의 독립 대조 **15/15 PASS**: 원본 blend SHA 보존, RAM/threads/시간 한도, actual engine/sample 로그, 실제 PNG 크기/SHA, 고정 장면 속성을 확인했습니다. 런타임에서 두 후보 모두 다음 값이 원본과 같았습니다.

- evaluated mesh **268개**, local vertices/topology SHA `3a3be19bb13f09a1dd8d2b773f840885d81ca9f0d126e0e0b0a7c8a7b0c8d563`
- 대표 1/133/288 시점 비광원 transform SHA `6f858447876cbafc8802aa28cdb36728fe8491569e86933ee00c24fd19d498f2`
- 카메라 SYN-CAM-02, 32mm, 같은 matrix; world/광원 위치·에너지·색·크기, 재질 값, 합성 stamp 동일

원본 blend는 CASE-0002/W-W3, CH-02/D-02, 업무 토트 미확인의 기존 합성 장면이며 새 사건이나 물류 사실을 만들지 않았습니다. 소스 blend를 수정·저장하지 않았습니다. 두 Blender PID의 종료 후 재조회는 **0개**입니다.

기존 `inspect_scene.py`의 `runtimeSamples` 키는 **EEVEE property**를 읽으므로 Cycles 출력에도 96으로 남습니다. 이를 Cycles 실효값이라고 쓰지 않습니다. Cycles의 실제 샘플은 새 report의 `runtimeAfter.cyclesSamples=16`과 실제 `Sample 16/16` 로그로 검증했습니다. 새 `render-report.json`은 engine별 설정을 구분해 기록합니다.

## 원본 이미지 직접 관찰

두 새 PNG를 각각 직접 열고 직전 96 samples/rays1의 같은 frame 133과 대조했습니다.

| 대상 | EEVEE96/rays4 | Cycles CPU16+denoise |
|---|---|---|
| 발판 입자 | 기존 발판 테두리의 밝은 점상 입자가 뚜렷하게 줄고 금속판 형태가 읽힙니다. 완전 무입자로 단정하지 않습니다. | 발판 주변은 부드럽지만 일부 얇은 모서리가 정돈되지 않은 모습입니다. |
| 바닥 그림자 | 넓은 접촉 그림자의 거친 얼룩이 줄면서 다리·바닥 연결을 유지합니다. | 그림자가 더 부드럽고 깊으며 바닥이 균일하게 보입니다. denoise 영향과 엔진 차이를 분리했다고 주장하지 않습니다. |
| 금속 롤러·가드 | 가는 반사와 롤러 간격이 안정적으로 읽힙니다. 가드·받침 연결도 유지됩니다. | 롤러와 측면 프레임의 밝은 반사선에 거칠고 끊긴 흔적이 남습니다. 16 samples+denoise를 최종 금속 품질로 선택하기 어렵습니다. |
| 상자·접촉·라벨 | 라벨과 벨트 위 위치, 분기 가시성을 유지합니다. | 같은 상자와 접촉 위치가 보이고 그림자는 더 진하지만, 한 장으로 움직임 중 안정성을 판단할 수 없습니다. |
| 합성 표시 | 실제 CCTV 아님·W-W3·업무 토트 UNKNOWN 유지 | 동일 |

이 장면에서는 shadow ray count를 단독 변경했을 때 문제 영역이 개선됐으므로, **기존 입자에 그림자 샘플링 설정이 기여했다는 근거**가 생겼습니다. 모든 입자가 같은 원인이거나 물리 장면 자체가 완벽하다는 결론은 아닙니다. 수치화하지 않은 노이즈 감소율을 제시하지 않습니다.

**다음 도구 선택 권고:** EEVEE 96 samples / shadow rays 4를 다음 짧은 분기 동작의 후보로 삼는 것이 합리적입니다. 이미 지원 최대 rays 값이므로 더 높은 값을 시도하지 않습니다. Cycles는 다른 조명 표현의 참고로 보존하되 이번 CPU16 결과만으로 전체 288프레임을 선택하지 않습니다. 주변 환경 수정과 합쳐지는 시점에는 같은 프레임·기하 변경 내역을 다시 대조해야 합니다.

## 288프레임 시간 추정과 미실행 범위

**실측은 엔진별 한 프레임뿐**입니다. 단순히 이번 render 호출 시간을 288배 하면 EEVEE는 `27.36×288/60 ≈ 131.3분`, Cycles는 `34.11×288/60 ≈ 163.7분`입니다. 이는 cold frame 준비 비용을 매번 포함하는 단순 외삽이며 전체 실행 시간의 보증이나 엄밀한 상한이 아닙니다. 연속 렌더의 캐시·다른 프레임의 복잡도·CPU/GPU 부하·추가 환경 오브젝트에 따라 달라집니다. 1080p 또는 새 환경에도 이 숫자를 그대로 적용하지 않습니다.

72/288프레임 렌더·temporal flicker·움직임 가림/관통·영상 인코딩·웹 통합은 미실행입니다. 이번 두 장의 성공으로 그 게이트를 체크하지 않습니다.

| 산출물 | 크기(B) | SHA256 |
|---|---:|---|
| eevee-shadow4/frame-0133.png | 1,011,439 | `c08beec1be3263327b00a043f0cc62520c2e5fc8f615180851cbb7073cb5513f` |
| cycles-cpu16/frame-0133.png | 1,062,667 | `5f66cdb1e58badf0fdebcd44a8ac48bc5bdbab4ecc2420dbd315e0de31eccb89` |

명령·시각·RAM·입력 해시는 `*-process.json`, 실제 설정은 각 `settings-before-render.json`과 `render-report.json`, 원본 보존/샘플/mesh 대조는 `independent-engine-comparison.json`에 있습니다. 원격 생성기·메인 제품·기존 보고/이미지·배포·Release·편지·커밋은 변경하지 않았습니다. 소유 변경은 새 진단 폴더와 이 보고뿐입니다.
