# N03-M2 pc3 Blender 실행 환경 점검

실측 시각: **2026-09-21 19:51:09.954 KST**. 원본 `.local/pc3-blender/inventory.json`의 `checkedAt=2026-09-21T19:51:09.9543657+09:00`를 사용했습니다. 호스트는 `LAPTOP-U2AL73UH`입니다.

확인한 범위에서 Blender 실행파일을 찾지 못했습니다. 따라서 이 PC의 **실제 Blender 버전·엔진 지원·렌더 시간은 미검증**입니다. 설치, 다운로드, 보안·실행 정책 변경, smoke render 및 긴 렌더는 수행하지 않았습니다.

## 탐색 범위와 결과

| 확인 범위 | 방법 | 결과 |
|---|---|---|
| `D:\hwana\Apps` | `rg --files --hidden --no-ignore -g '*[bB]lender*.exe'` | 일치 실행파일 0개 |
| `C:\Program Files\Blender Foundation`, `C:\Program Files\Blender` | 지정 경로 존재 확인 | 폴더 없음 |
| `C:\Program Files (x86)\Blender Foundation`, `C:\Program Files (x86)\Blender` | 지정 경로 존재 확인 | 폴더 없음 |
| 두 Program Files 최상위 | Blender가 포함된 폴더명 확인 | 0개 |
| PATH | `Get-Command blender, blender.exe -All` | 0개 |
| HKLM/HKCU Uninstall, HKLM WOW6432Node Uninstall | DisplayName에 Blender가 포함된 설치 항목 확인 | 0개 |

전 드라이브나 관계없는 portable 위치는 탐색하지 않았습니다. 위 결과는 이 탐색 범위의 부재이며, PC 전체에 설치가 절대로 없다는 뜻은 아닙니다. `nvidia-smi`도 PATH에서 발견되지 않았습니다.

## 읽기 전용 하드웨어 실측

| 항목 | 관측값 |
|---|---|
| CPU | Intel Core i7-8550U @ 1.80GHz, 물리 4코어·논리 8개 |
| RAM | `8,500,961,280 bytes` = 약 **7.92 GiB** |
| 내장 GPU | Intel UHD Graphics 620, 드라이버 `27.20.100.7987`, WMI 상태 OK |
| 외장 GPU | NVIDIA GeForce MX150, 드라이버 `24.21.13.9907`, WMI 상태 OK |
| WMI AdapterRAM | UHD 620: `1,073,741,824 bytes`; MX150: `2,147,483,648 bytes` |
| D: 전체 | NTFS, `983,852,285,952 bytes` = 약 916.28 GiB |
| D: 여유 | `852,067,274,752 bytes` = 약 **793.55 GiB** |

CPU·RAM·GPU·디스크는 각각 Windows CIM `Win32_Processor`, `Win32_ComputerSystem`, `Win32_VideoController`, `Win32_LogicalDisk`로 읽었습니다. WMI AdapterRAM은 Blender가 감지한 사용 가능 VRAM이나 CUDA/OpenGL 호환성 측정이 아닙니다. 특히 내장 GPU 수치를 전용 VRAM으로 단정하지 않습니다. 드라이버 상태 OK도 Blender 렌더 성공을 뜻하지 않습니다.

## 벤치마크와 선택한 대안

128×128 이하 smoke render **미실행**, 엔진 **미확인**, 측정 프레임 **없음**, 측정 시간 **없음**입니다. 초/프레임, fps 또는 전체 렌더 예상 시간을 계산할 근거가 없으므로 수치를 제시하지 않습니다.

이 PC에는 Blender를 추가 설치하지 않고, pc3 주세션이 작성한 장면 코드를 **pc1의 렌더 환경에 전달**하는 대안을 선택했습니다. pc1이 Blender **4.5.14 LTS portable 실행에 성공했다는 내용은 pc1의 보고**이며, pc3에서 해당 실행파일·버전·성능을 직접 검증한 결과가 아닙니다. 이 문서는 장면 전달 또는 pc1 렌더 완료를 선언하지 않습니다.

D:에는 작업 자산을 보관할 충분한 여유가 확인됐습니다. 반면 이 PC의 Blender 실행 가능성과 처리 속도가 확인되지 않았으므로, 장면 코드의 로컬 정적 검토와 pc1의 실제 렌더 검증을 구분해 인계합니다.
