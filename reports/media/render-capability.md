# pc1 Blender 렌더 실행 환경·720p 실측

작성: 2026-09-21T19:47:04+0900 · 로컬 보조 작업자 · 대상: pc1 / CJJ

공식 Blender 4.5.14 LTS Windows x64 포터블의 SHA-256을 대조하고 실행했습니다. EEVEE 대표 프레임은 3/3, Cycles CPU 확인 프레임은 1/1개가 PNG로 해독됐습니다. 이 표본은 렌더 환경 벤치마크이며 실제 CCTV·물류 실적·완성된 생산 영상이 아닙니다.

## 공식 출처와 설치 경계

- LTS 출처: [Blender 4.5 LTS](https://www.blender.org/download/lts/4-5/)의 4.5.14, 2026-09-15 배포.
- 다운로드: [공식 Windows x64 ZIP](https://download.blender.org/release/Blender4.5/blender-4.5.14-windows-x64.zip) / [공식 SHA-256 목록](https://download.blender.org/release/Blender4.5/blender-4.5.14.sha256).
- ZIP: 398,661,046 bytes. SHA-256 기대·관측 동일: `b9533d2397ac1984db4466fb23a7a4649391cca93f6e84209f9bcc60d071c8b9`.
- 실행파일 SHA-256: `57FA1D294EA76448C3BEC84CA758CAF4629611330ABBA7DCF55BB0C56A0A15AB`. Authenticode 결과 `Signature verified.`, 서명자 `CN=Blender Foundation, O=Blender Foundation, L=Amsterdam, S=Noord-Holland, C=NL`.
- 압축 내 6,312개 항목, 비압축 합계 924,651,575 bytes.
- 다운로드 전 C 드라이브 여유: 121,797,623,808 bytes. 추출 후: 120,433,307,648 bytes.
- 전역 설치·PATH·계정·방화벽·기존 서버 변경 없이 `.local/tools/blender/`에 보관했습니다. 사용자 설정과 임시 폴더도 이 경로 아래로 지정했습니다.
- 패키지·벤치마크는 Git 제외 `.local`에만 있고 이 작업에서 커밋·push·Release 업로드는 실행하지 않았습니다.

## 환경과 실제 선택

- CPU: 11th Gen Intel(R) Core(TM) i7-1185G7 @ 3.00GHz, 4코어 / 8논리 스레드.
- RAM: 16,983,785,472 bytes, 2026-09-21T19:46:02.7782167+09:00 가용 2,276,409,344 bytes. 다른 업무와 동시 실행한 관측입니다.
- OS 표시 GPU: Intel(R) Iris(R) Xe Graphics, 드라이버 32.0.101.6737.
- 실제 Blender: `4.5.14 LTS`, build `62c1db4208e8`.
- EEVEE 실제 엔진: `BLENDER_EEVEE_NEXT`. 렌더 후 GPU 조회: `{"vendor_get": "Intel", "renderer_get": "Intel(R) Iris(R) Xe Graphics", "version_get": "4.6.0 - Build 32.0.101.6737", "backend_type_get": "OPENGL", "device_type_get": "INTEL"}`.
- Cycles 실제 선택: `CPU`. 장치 조회: `[{"name": "11th Gen Intel Core i7-1185G7 @ 3.00GHz", "type": "CPU", "use": false}]`.
- Cycles GPU 렌더는 실행하지 않았습니다. EEVEE의 GPU 성공을 Cycles GPU 지원으로 확대하지 않습니다.

## 동일 장면 실측

장면은 고정 CCTV 각도, 롤러 컨베이어·3개 토트·선반/박스·면광원 3개로 구성했습니다. 외부 모델/텍스처 없이 절차적으로 만들고 합성 워터마크를 넣었습니다. 1280×720 / RGB 8-bit PNG / 100%, 4스레드, 낮은 프로세스 우선순위입니다. EEVEE는 32 samples·ray tracing off, Cycles는 CPU 8 samples·denoise on·4 bounces입니다. 두 엔진의 설정이 다르므로 품질 동등 비교가 아닙니다.

| 엔진 | 프레임 | 렌더 호출 시간(초) | PNG bytes | 해상도 | 해독 |
|---|---:|---:|---:|---|---|
| EEVEE | 1 | 29.873 | 1,088,491 | 1280×720 | 성공 |
| EEVEE | 25 | 2.357 | 1,089,650 | 1280×720 | 성공 |
| EEVEE | 49 | 2.358 | 1,091,311 | 1280×720 | 성공 |
| CYCLES | 25 | 14.182 | 1,002,085 | 1280×720 | 성공 |

EEVEE 프로세스 전체 40.096초 / 종료코드 0; Cycles 전체 16.328초 / 종료코드 0. 프로세스 전체에는 시작·장면 생성·저장·종료를 포함합니다. 개별 렌더 시간에는 이미지 저장을 포함합니다.

Pillow `verify()`와 전체 픽셀 `load()`로 PNG를 해독했고 signature/IHDR 해상도와 파일 SHA-256도 기록했습니다. 위·아래 워터마크 영역을 제외한 장면 영역의 프레임 간 RGB 평균 절대차와 각 토트 좌표를 기록해 단순 동일 이미지 반복을 확인했습니다.
장면 영역 차이: `[[5.742171285377358, 3.643207547169811, 2.8940507075471698], [6.20713295990566, 3.8981618514150944, 3.073130896226415]]`.

## 실패·미실행과 해석 한계

- 웹 조회 도구의 공식 페이지 열기가 HTTP 402로 실패했습니다. 별도로 PowerShell의 공식 HTTPS 응답에서 LTS 본문·파일 목록·크기·checksum을 읽었습니다.
- 최초 Python urllib 전송은 공개 checksum URL에서 HTTP 403을 받아 패키지 다운로드·실행 전에 중단했습니다. 같은 공식 URL은 앞선 PowerShell 조회에서 접근됐고, 다운로드는 PowerShell로 수행했습니다. 인증/계정/정책을 변경하지 않았습니다.
- 첫 로컬 checksum 파싱은 PowerShell 저장 시 붙은 빈 줄을 처리하지 못해 IndexError로 중단했습니다. 빈 줄을 제외하도록 고친 뒤 다운로드 원본을 그대로 재해시했고 공식 값 일치 후에만 추출·실행했습니다.
- EEVEE `--debug-gpu` 로그에는 ERROR 2줄(`GL_INVALID_ENUM : Cubemap Workaround Start`, `GL_INVALID_VALUE : Cubemap Workaround End9`)과 WARN 10줄이 있습니다. 실제 프로세스는 0으로 종료했고 3개 PNG를 해독·화면 확인했지만, 이를 드라이버 경고가 없는 상태나 장시간 안정성 보증으로 표현하지 않습니다. 원문은 `eevee/blender.log`, 집계는 `eevee/gpu-diagnostics.json`에 보존했습니다.
- 첫 렌더 전 `gpu.platform` 조회는 background 모드에서 SystemError를 반환했습니다. EEVEE 렌더 후에는 실제 Intel/OpenGL 정보가 반환됐습니다. Cycles CPU에서는 GPU 조회를 성공으로 기록하지 않았습니다.
- EEVEE: status=complete, skipped=[], errors=[].
- CYCLES: status=complete, skipped=[], errors=[].
- EEVEE 3개와 CPU 1개만 측정했습니다. 장시간 열 부하·배터리·고복잡도 장면·영상 인코딩·운영 영상 품질은 미검증입니다. RAM 가용량과 다른 업무 부하에 따라 시간이 달라질 수 있습니다.
- 기본 OpenGL 경로만 시험하며 Vulkan·Cycles GPU·외부 렌더팜·추가 패키지/모델은 시험하지 않았습니다.
- 직접 열린 EEVEE/CPU 중간 프레임에서 컨베이어·토트·선반·면광원·합성 표시를 확인했습니다. EEVEE 그림자에는 32-sample 노이즈가 있고 하단 프레임 표시는 저대비입니다. 최종 생산 영상의 품질·자막 명암 기준 통과로 사용하지 않습니다.

## 권고와 재현

pc1에서는 EEVEE로 짧은 합성 공정 클립을 제작할 수 있습니다. 첫 프레임 29.873초, 이후 2개 평균 2.357초입니다. 단순한 10초·24fps·240프레임을 같은 평균에 곱하면 약 9.4분이며, 이는 2프레임 표본으로 산술 추정한 값이지 완성 영상 실측이 아닙니다. pc3가 실제 생산 장면의 대표 프레임을 같은 방식으로 다시 측정하고 720p/짧은 클립부터 진행하는 것을 권합니다.

Cycles CPU는 정지 이미지의 선택지로만 평가합니다. 합성 CCTV의 자산·이벤트·case·camera·시간 연결과 최종 품질 판정은 pc3 생산 작업 및 메인 인수에 남습니다.

실행파일: `C:\00.프로젝트\happycall-ralphthon\.local\tools\blender\blender-4.5.14-windows-x64\blender.exe`

```powershell
& 'C:\00.프로젝트\happycall-ralphthon\.local\tools\blender\blender-4.5.14-windows-x64\blender.exe' --version
python 'C:\00.프로젝트\happycall-ralphthon\.local\media-benchmark\run_benchmark.py'
```

재실행은 동일 벤치마크 출력 파일을 갱신하므로 이전 결과를 보존하려면 별도 output 경로로 `render_benchmark.py`를 직접 실행합니다. `run_benchmark.py`가 사용자 설정/임시 경로, 낮은 우선순위, 엔진별 로그와 PNG 전체 검증을 담당합니다.

| 로컬 증거 | 절대경로 |
|---|---|
| 설치·checksum | `C:\00.프로젝트\happycall-ralphthon\.local\tools\blender\installation.json` |
| 하드웨어 | `C:\00.프로젝트\happycall-ralphthon\.local\media-benchmark\host.json` |
| 종합 실측·PNG 검증 | `C:\00.프로젝트\happycall-ralphthon\.local\media-benchmark\summary.json` |
| 버전 출력 | `C:\00.프로젝트\happycall-ralphthon\.local\media-benchmark\version.log` |
| EEVEE 실행 로그/장면/PNG | `C:\00.프로젝트\happycall-ralphthon\.local\media-benchmark\eevee` |
| Cycles 실행 로그/장면/PNG | `C:\00.프로젝트\happycall-ralphthon\.local\media-benchmark\cycles` |
| 생성기 | `C:\00.프로젝트\happycall-ralphthon\.local\media-benchmark\render_benchmark.py` |

경로는 pc1 전용이며 다른 PC에 자동 설치·복제된 상태가 아닙니다. 이 보고서의 숫자를 pc3 성능으로 인용하지 않습니다.
