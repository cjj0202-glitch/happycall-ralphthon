# 실제 1080p 렌더 완주와 M5 구조 검사

2026-09-22 02:08:44 KST 기준, 기존 Blender 렌더가 완주한 뒤 **M5 구조 검사를 한 번 실행해 `PASS_WITH_PENDING`, `valid=true`, 실패 0, exit 0**을 확인했습니다. 검사 시간은 **4.843초**, 검사 대상은 **288 PNG와 report·tracks·blend를 합친 291파일, 총 655,063,910바이트**입니다.

이 판정은 저장된 입력의 구조·해시·계약 대조입니다. 픽셀 또는 영상 디코드, 실제 영상 시각 품질, 제품 등록·배포 완료를 의미하지 않습니다.

## 원본 프로세스와 완주 관측

대상은 `.local/pc3-render-intake/full1080-a39cd66-01/animation/`입니다. 기존 PID `13052`, 시작 시각 `2026-09-21T23:11:14.3325311+09:00`을 식별하여 조회했습니다. 신규 렌더를 띄우거나 기존 프로세스를 종료·재시작하지 않았습니다.

- 지정 기대 파일 `pc1-full-expectations.json`의 SHA256을 먼저 대조했고 `1917e27f15157f14f95ad849386bdc93663b11bb62a5970810274efd9118c24b`와 일치했습니다.
- private 관측 로그는 01:57:30~02:08:21의 14건입니다. 관측 간격 최대 50.060212초로 60초 이내였고, live 관측은 같은 시작 시각의 PID였습니다. 미완성 상태에서 M5를 실행하지 않았습니다.
- 02:07:31에는 동일 PID가 live였고 PNG 287개, 최종 report가 없었습니다.
- 02:08:21에는 PID가 존재하지 않았고, PNG `frame-0001.png`~`frame-0288.png`와 `render-report.json`, `tracks.json`, `case-0002-ww3.blend`로 정확한 291파일이 있었습니다.
- 최종 `render-cli.log`에서 해당 animation 경로에 대한 `rendered: 288`, `clippedFrames: []`, `seconds: 10593.372327566147`과 `Blender quit`을 확인했습니다. 관측 세션 `7879`는 이 완주 조건을 만족한 후 exit 0으로 종료했습니다.

메인은 원본 exec 세션 `17508`을 별도로 수집하여 exit 0을 전달했습니다. 메인 전달 wrapper 기록은 `pid=13052`, `state=exited`, `exitCode=0`, `endedAt=2026-09-22T02:08:16.450348+09:00`, `wallSeconds=10622.297`, `framesPresent=288`입니다. 이 보고서 담당자는 세션 `17508`을 소비하지 않았습니다. wrapper 경과 시간과 렌더 스크립트의 `seconds`는 서로 다른 측정 구간입니다.

## 한 번의 M5 실행

완주 게이트를 확인한 후 PID 종료·291파일·완주 로그·기대 파일 SHA를 다시 대조했습니다. 다음 CLI를 02:08:39.831502에 시작하여 02:08:44.692872에 완료했습니다.

```powershell
.venv/Scripts/python.exe -B -X utf8 scripts/media_pc3/verify_full_animation.py --package .local/pc3-render-intake/full1080-a39cd66-01/animation --expectations .local/pc3-render-intake/full1080-a39cd66-01/pc1-full-expectations.json
```

실행은 private `run-structure-once.py` 수집기가 위 인자를 절대경로 argv로 전달했습니다. 기존 `verification-start.json`이 있으면 재실행을 거부하며 이번 실행은 한 번뿐입니다. 기존 검사기와 제품 소스는 수정하지 않았습니다.

| 관측 항목 | 결과 |
|---|---|
| CLI 종료 | 0 |
| 상태 | `valid=true`, `PASS_WITH_PENDING` |
| 실패 목록 | `[]` |
| 검사 PNG | 288 |
| 입력 해시 목록 | 291 |
| stderr | 0바이트 |
| 실행 시간 | 4.843271700초 |
| manifest | 지정 SHA 일치, 28,743바이트, 전후 동일 |
| 검사기 및 관측 의존 5파일 | 전후 바이트·SHA 동일 |
| 패키지 291파일 | 검사 전후 크기·mtime 동일 |

M5는 정확한 파일 inventory, report의 288프레임 순서와 24fps 시간, 1920×1080 PNG 구조·CRC, 각 저장 파일의 바이트·SHA, tracks 및 독립 기대 manifest와의 계약 대조를 수행합니다. 검사 내부에서도 파일 identity/size/mtime과 inventory 변경을 거절합니다. `sourceCommit=a39cd664758575a81e1fcce437db245f60fc2c1b`는 기대 manifest·보고서에서 대조한 선언이며, 이 검사만으로 실행 출처를 인증하지 않습니다.

| 주요 입력 | 바이트 | SHA256 |
|---|---:|---|
| `render-report.json` | 109,071 | `ebe4d9d7f6af7ef6b67cfea979d7fe9a9f6e55ed86a2c5f5745f846fa4ea34a1` |
| `tracks.json` | 158,546 | `b9b9f50295af799cfdf718b840b0cef703f57ad3e3b778557fcd9fdeb9ac681c` |
| `case-0002-ww3.blend` | 3,056,663 | `118c35e1b7b28cb510b611f4d25bceadc2174cdb7bb230068271706084674c3e` |

실행 검사기 `scripts/media_pc3/verify_full_animation.py`는 21,052바이트, SHA256 `a711fed3ce821bb1e24caafadcf2c6161f266e9b031cfea29b73d46e0d716075`입니다. 함께 관측한 `verify_render_package.py`, `full_render_gate.py`, `environment_detail.py`, `scene_contract.py`의 전후 해시는 private start/finish 기록에 보존했습니다.

## 유지되는 6개 보류 항목

M5 출력의 `visualAccepted`, `pixelDecoded`, `videoDecoded`, `authenticityVerified`는 모두 `false`입니다.

1. 원본 source/layout/fixture/receipt 및 검토 증거를 다시 열어 해시하지 않았습니다. 패키지의 선언을 독립 manifest와 대조했습니다.
2. 최종 Blender 장면을 새로 열거나 렌더 후 scene readback을 실행하지 않았습니다.
3. PNG 구조·CRC·해상도를 확인했으며 압축 픽셀을 디코드하지 않았습니다.
4. MP4 인코딩·컨테이너·영상 디코드를 확인하지 않았습니다.
5. 가림·접촉·움직임·깜박임 등 실제 시각 품질 검수는 남아 있습니다.
6. 선언과 해시만으로 발급자 또는 실행 커밋을 인증하지 않습니다.

M6 인코딩, Release, UI, API, 메일, 키, 커밋 및 최종 인수는 메인의 후속 범위입니다. 이 작업에서는 실행하지 않았습니다. 02:25까지 기다려야 하는 미완주 상태는 발생하지 않았습니다.

## Private 원증거

모두 `.local/pc3-full1080-structure-intake-20260922-0156/` 아래에 새로 작성했습니다. 원본 렌더 파일과 기존 로그는 읽기만 했습니다.

| 증거 | 바이트 | SHA256 |
|---|---:|---|
| `observations.jsonl` | 7,703 | `fa3af45aef2fb12f0e34f0482a047039af4b262412ace25deb6fcf07c678ee85` |
| `completion-gate.json` | 904 | `89d0195f7b4186783c38c547418cb6bec1b3a58a4899b13a7f0183e4f286d091` |
| `verification-start.json` | 23,911 | `ab0b52f68e68ab304ae07e8cf15b1a8b211de0b3d3de989b6d1714b63bc2f163` |
| `verification-finish.json` | 1,541 | `5c4f3fbbbcd6f79d647e4dbf8fd03a47421ec2d6a4dad7fe106f2743e6861ba9` |
| `verify-stdout.json` | 110,657 | `176a269cea3467ebc7487f00220bc29d70337f0eb37482c38fe247ad032c5807` |
| `verify-stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

이 담당자의 메인 문서 변경은 본 보고서 한 파일입니다. 다른 작업자의 파일과 기존 변경을 보존했습니다.
