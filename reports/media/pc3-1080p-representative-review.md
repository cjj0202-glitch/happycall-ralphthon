# PC3 합성 CCTV 1080p 대표 3장 실측 검수

2026-09-21, 메인 PC CJJ / pc1의 로컬 렌더 검증자. 대상은 독립 합성 장면이며 실제 센터 CCTV나 작업자 귀책 증거가 아닙니다.

## 판정과 범위

33fa0e4의 같은 장면을 1920×1080으로 frame 1·133·288, **3장 실제 렌더**했습니다. 세 PNG를 원본 크기로 직접 열어 상자·롤러·분기·환경 소품·합성 표지를 확인했습니다. 실제 bpy readback 24개 최상위 필드가 기존 720p short와 전부 같고, 별도 runtime 검사에서 1080p 100%·EEVEE 96·shadow 4·FIXED 2 threads를 확인했습니다.

대표 이미지의 기술·시각 검토는 다음 렌더 계획의 근거로 사용할 수 있습니다. 메인의 전체 동작 승인·288프레임 완주·MP4·UI/seek·제품 등록을 완료한 결과는 아닙니다. 전체 동작 모드의 기존 생성기 가드는 수정하지 않았습니다.

## 격리·재현

- 신규 ignored 폴더: `.local/pc3-render-intake/reps1080-33fa0e4-01/`.
- 원본: `.local/pc3-render-intake/short-33fa0e4-01/source/`, detached HEAD `33fa0e4edeb88c0d4ad5e9cc0194ffc7e96cebcd`.
- 원본 생성기 15개 Python 파일을 위 신규 폴더 `source/scripts/media_pc3/`로 복사하고 각각 SHA·바이트를 고정했습니다. 기하/가드/스크립트 수정 없이 실행했습니다.
- 독립 scene readback helper는 기존 `staging-01/inspection-scene.py`를 동일 바이트로 복사했습니다. 기존 helper에는 해상도 필드가 없어 신규 `inspection-runtime.py`가 실제 bpy 해상도·비율을 추가로 기록합니다.
- 생성기·입력·원 helper **18/18개 원본 보존**, 새 생성기 사본 **15/15개 SHA 유지**를 종료 후 대조했습니다. 제품 파일·기존 렌더·배포·커밋·Release는 변경하지 않았습니다.

```powershell
.venv/Scripts/python.exe -B .local/pc3-render-intake/reps1080-33fa0e4-01/run-representatives.py
.venv/Scripts/python.exe -B .local/pc3-render-intake/reps1080-33fa0e4-01/post-checks.py
```

첫 명령은 기존 출력이 있으면 덮어쓰지 않고 중단합니다. 새 실행은 새 검증 폴더와 입력 동결이 필요합니다. 실제 전체 argv는 `render-process.json`에 있습니다. 공식 설치본 `.local/tools/blender/blender-4.5.14-windows-x64/blender.exe`만 사용했습니다.

| 고정 입력 | 바이트 | SHA-256 |
|---|---:|---|
| build_scene.py | 24,994 | `ff03e34ae903272af3a99659ed36964a6e52c20518b2489939a22b067d3ea854` |
| scene-layout-v1.json | 1,772 | `c6aece6692c6b78beb85d4f1167868f2bd095b3ab8366e837466715b82bd6cb6` |
| cases.json | 23,430 | `79c3b01aed139352b5cc0a695f2829e76f78eabb61d7cfd6b8055db32f61a73b` |

이 fixture는 이전 장면 검증 입력입니다. 최신 제품 음성/전사 fixture를 반영한 것으로 해석하지 않습니다. 대표 렌더의 목적은 동일 장면의 해상도 변경 실측입니다.

## 실제 프로세스와 자원

| 항목 | 실측 |
|---|---|
| 시작 / 종료 KST | 22:31:54.164798 / 22:34:05.565470 |
| Blender PID / terminal session | 3392 / 7586 |
| 종료 / 전체 시간 | exit 0 / 131.391초 |
| 시작 가용 RAM | 2,278,281,216B, 2GiB 최소 게이트 통과 |
| 중복 Blender | 시작 전 0, 단일 렌더 PID만 실행 |
| 실제 설정 | `representatives`, `cctv`, 1920×1080 100%, EEVEE, samples 96, shadow rays 4, FIXED 2 threads |
| look / 환경 | `contrast_material_v1` / `staging_v1` |
| 실제 96/96 samples 완료 로그 | frame 1·133·288, 3/3 |
| 프레임별 생성 시간 | 42.337921 / 38.675977 / 43.006083초 |

렌더 중 가용 RAM 1,013,036KiB(약 0.97GiB)를 관측했습니다. 새 프로세스를 추가하지 않았고 메인에게 알렸습니다. 종료 직후 가용 RAM은 3,212,452KiB(약 3.06GiB), Blender 프로세스 0이었습니다. 별도 앱을 종료하거나 시스템 자원을 강제로 정리하지 않았습니다.

Blender 렌더 실패는 이번 실행에서 발생하지 않았습니다. 초기 자원 조회 명령의 PowerShell `ConvertTo-Json -Property` 오류는 `Select-Object ... | ConvertTo-Json`으로 고쳤고, 실행 게이트는 Python `GlobalMemoryStatusEx`의 별도 실측으로 판정했습니다. 최초 명령 오류를 렌더 실패 또는 제품 결함으로 분류하지 않습니다.

## 파일 전수 대조

| PNG | 실제 해상도 | 바이트 | SHA-256 |
|---|---|---:|---|
| frame-0001.png | 1920×1080 | 2,258,267 | `edb2d069c47b6d97a22cfc4af1680327fea3fd9f7456ba81bf602cd1c48f15f0` |
| frame-0133.png | 1920×1080 | 2,264,479 | `300869793172958560cb9b6e1d6ecfe6ff1a76f554f008384fc87b7760121257` |
| frame-0288.png | 1920×1080 | 2,266,390 | `bcecad934b61f9209e566210680d161b7e43dd45b1f9805dfaaf3aa23deebfdf` |

파일명 집합 3/3, PNG signature·IHDR 해상도 3/3, 실제 SHA·바이트와 생성기 render-report 일치 3/3입니다. 합계 6,789,136B입니다. 대표 시각은 각각 0초·5.5초·11.958333초이며 중간 285프레임을 렌더하지 않았습니다.

## 실제 장면과 추적 비교

| 항목 | 실측·기대 대조 |
|---|---|
| mesh | 기존 268 + 환경 48 = 316, 이전 short와 같음 |
| 전체 evaluated mesh SHA | `51567277b813fd0f4414241100c396993db1e4c721c00eb239e849ac3e2d9f79`, 동일 |
| 기존 evaluated mesh SHA | `3a3be19bb13f09a1dd8d2b773f840885d81ca9f0d126e0e0b0a7c8a7b0c8d563`, 동일 |
| frame 1·133·288 전체 비광원 transform SHA | `ac4723d5c5c26b86e3297356e15e3f304dd2b495f00dd60a68010ab9953a1094`, 동일 |
| 실효 카메라 | SYN-CAM-02, lens 32mm, matrix 전체 동일 |
| 광원·재질·색·stamp | 이전 readback과 전체 동일, AgX / exposure 0 / gamma 1 |
| 실제 환경 bounds 접촉 | 바퀴·기둥·바닥선·선반 상자 20/20, 오차 0.00001m 미만 |
| 원본 tracks SHA | `9fb424be0fd212bbf3faa057097bec56c63a89e4b8ae08c524e5fd76b80fd44b` |
| 1080p tracks SHA | `b9b9f50295af799cfdf718b840b0cef703f57ad3e3b778557fcd9fdeb9ac681c` |
| tracks 재귀 차이 | `resolution[0]` 1280→1920, `resolution[1]` 720→1080, 정확히 2필드 |
| 나머지 tracks / 정규화 bbox | 288개 설계 표본 전체 동일 |

`occlusionTested=false`, 모든 `businessToteId=null`을 보존했습니다. 288개 좌표 metadata는 288장 렌더 완료나 실제 토트 추적 증거가 아닙니다. 기존 720p short에서 별도로 수행한 가림 검사를 이 1080p의 새 가림 검사로 재사용하지 않았습니다.

별도 읽기 전용 검증자 `independent_1080_checks`도 실제 PNG IHDR·해시·바이트를 다시 계산해 3/3 일치를 확인했습니다. 해당 검증자의 재귀 비교는 tracks 말단 값 4,343개 중 위 2개만 다름을 확인했고, scene readback 말단 값 788개 및 파일 바이트가 같음을 확인했습니다. 양쪽 readback은 32,478B, SHA `a6a7eb2eb3c7555f18db906a9b844cd450fa513aab57d9ab862d1cd92fd15b2d`입니다. 해당 검증자는 frame 133을 별도로 열어 합성 표지와 실제 촬영 시각 부재도 확인했습니다. 자체 생성기의 report만 반복 인용한 검사가 아니며, 그 범위는 파일 3장·별도 시각 확인 1장입니다.

## 세 이미지 직접 검수

- frame 1: 상자가 진입 롤러 위에 있고 상자 테이프·빈 라벨, 금속 롤러·프레임·노란 안전대가 구분됩니다. 배경 롤테이너 두 대와 랙/상자가 작업 구역을 설명하며 진입 경로를 가리지 않습니다.
- frame 133: 분기 중앙에서 방향이 바뀐 상자의 모서리·상면·라벨이 읽힙니다. 분기 안쪽의 개방부와 주변 프레임 연결을 확인했습니다. 상자 및 받침 그림자와 접촉 실측은 서로 모순되지 않습니다.
- frame 288: 상자가 분기 출구 벨트 쪽에 있고, 검토 대상 상자를 배경 소품이 가리지 않습니다. 이 정지 장면만으로 실제 출고 완료·오출 원인·휴먼 에러를 확정할 수 없습니다.
- 상단 `SYNTHETIC SCENE / NOT CCTV`, `W-W3`, `business tote UNKNOWN`, `illustrative elapsed frames`가 세 이미지에 남아 있으며 원본 크기에서 읽힙니다. 합성 표기를 제거하거나 실제 CCTV 시각으로 위장하지 않았습니다.
- 남는 품질 차이: 현장은 매우 정돈된 CG이고 사람·복잡한 작업 밀도·실사 재질 흔적이 없습니다. 1080p로 디테일이 더 보이지만 해상도 증가 자체가 실사성을 만들지는 않습니다. 기능 시연용 합성 장면 후보이며 사용자가 기대하는 회사 시스템의 최종 영상 품질까지 충족했다고 판정하지 않습니다.

## 전체 렌더 시간 추정과 다음 경계

이번 세 프레임 실측 최소/최대 × 288 = 11,138.681~12,385.752초, 약 **186~206분(3시간 6분~3시간 26분)**입니다. 평균 × 288은 11,905.918초(약 198분)입니다. 초기 준비·인코딩·검사·시스템 부하 변화는 별도이며 표본 3장의 단순 외삽으로 완료 시간을 보장하지 않습니다. 기존 720p 실측 시간을 1080p 예상으로 그대로 쓰지 않습니다.

메인은 이 결과·시연 시각·자원 상태를 보고 전체 렌더의 별도 승인 계약과 실행 PC를 결정할 수 있습니다. 현재 생성기의 전체 animation 가드는 그대로이고 이 작업에서 전체 렌더를 시작하지 않았습니다. 전체 동작 후에는 288장 전수·MP4 decode/seek·타임라인·해시·자산/track 등록·실제 UI 재생을 별도로 검증해야 합니다.

원본 증거: `source-intake.json`, `protected-before.json`, `preflight.json`, `render-process.json`, `render-cli.log`, `verification.json`, `post-checks.json`, `representatives/render-report.json`, `representatives/independent-scene-readback.json`, `representatives/independent-runtime.json`.
