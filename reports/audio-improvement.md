# N01 합성 음성 음량 보완 — 설계와 검증

## 구현 전 상세설계 · 2026-09-21

사용자 과업은 상담 통화를 1배속으로 듣고 점포·상품·수량·단위 정정을 이해하는 것입니다. 이번 작은 실험은 기존 두 음원의 **음량만 보정**하여 별도 A/B 후보를 만드는 것입니다. 발음·대본·속도·음색은 변경하지 않습니다. 현재 -22 LUFS 수준인 원본을 -18 LUFS 후보와 비교하되 수치 통과를 청취 품질 통과로 바꾸지 않습니다.

- 입력·출처: 현재 public의 CASE-0001/0002 WAV, 기존 생성 metadata의 구간. SHA-256으로 원본을 식별하고 생성 전후 일치를 확인합니다. 사본은 `.local/audio-normalized/` 아래에만 생성합니다.
- 사용자 진입·다음 행동: 메인이 원본/후보를 같은 장치·1배속·같은 volume에서 A/B로 듣습니다. 후보는 제품 UI와 자동 연결하지 않습니다. 의미 전달을 확인한 뒤 교체 여부와 Release를 메인이 결정합니다.
- 상태: 입력/의존성 점검 → 원본 보존 사본 → pass 1 측정 → pass 2 보정 → 별도 최종 측정 → 수치 기준 적합 후보 인계. 입력 불일치·FFmpeg 실패·비유한 음량·길이/포맷/피크 실패는 실패 기록을 남기고 미완성 결과를 후보로 승격하지 않습니다.
- 신호 처리: FFmpeg loudnorm 2-pass, I=-18, LRA=7, TP=-1.2로 출력 리샘플링 여유를 둡니다. 최종 수용선은 I=-18±0.3 LUFS, true peak≤-1.0 dBTP, clipped sample=0, 원본 sample rate/channel/PCM depth/frame count 완전 일치입니다. linear 조건이 충족되지 않으면 FFmpeg의 dynamic 처리 결과를 기록합니다.
  - 검토 후 보강: ebur128 요약 피크가 0.1 dB 반올림값이므로 코드 판정은 보수적으로 **표시값≤-1.1 dBTP**를 요구합니다. 표시값 -1.0만으로 실제 -0.96을 통과시키지 않습니다.
- 키·시간: case ID와 전체 파일 해시, 발화 start/end를 보존합니다. metadata와 WAV duration 일치 및 구간 범위를 확인합니다. 중요한 CASE-0002 발화 4(17.55–23.10초)는 원본/후보 RMS·LUFS·피크·클리핑·길이를 별도 측정합니다.
- 실패·복구: 매 실행마다 고유 작업 폴더를 사용하고 모든 파일은 그 안에만 씁니다. 실패하면 `.failed`로 남기고 이전 성공 후보·원본·현재 public에는 쓰지 않습니다. 완료 폴더는 모든 검증이 끝난 뒤에만 생성합니다. 중단된 `.incomplete` 폴더는 완료 후보가 아닙니다.
- TTS 캐시 수정: model/speed/instructions/input/voice/response_format의 동일 parameter dict를 캐시 해시와 실제 API 호출에 사용합니다. 기본 생성조건을 유지하고 speed=1.0을 명시합니다. 단위검사는 설정 각각의 변경·canonical 순서·API 인자 일치를 mock으로 확인하며 유료 호출을 하지 않습니다.
- 검증: 원본 보존/경로 차단/길이·클리핑·비유한 측정의 정상·불량·경계 대조, FFmpeg 실패 시 복구, 실제 두 파일 전후 측정, 캐시 parameter별 반례와 변이 검증. UI·출력장치·직접 청취·새 STT 평가는 이번 범위 밖이며 완료로 세지 않습니다.

소유 파일: `scripts/normalize_demo_audio.py`, `tests/test_audio_preparation.py`, 이 보고서, `.local/audio-normalized/`, 그리고 기존 `scripts/generate_demo_audio.py`의 캐시/생성 parameter 일치 부분입니다. 원격 pc2의 미디어·CallReview·fixture·manifest·현재 public WAV는 수정하지 않습니다. 상세 실측과 재현 명령은 실행 뒤 아래에 추가합니다.

## 실제 결과 · 2026-09-21 pc1/CJJ

기준 HEAD는 착수 시 `88ba3b1`입니다. 다른 세션의 기존 미커밋 변경을 보존했습니다. 결과 커밋은 만들지 않았습니다.

**두 후보 모두 수치 기준 적합, 청취·명료도 인수는 미검증입니다.** 기존 public WAV 두 개는 그대로이며 원본 보존 사본과 현재 public의 SHA-256이 일치합니다. 음량 변화만으로 기존 STT의 점포/상품/업무용어 오류가 해결됐다고 주장하지 않습니다.

| 항목 | CASE-0001 원본 → 후보 | CASE-0002 원본 → 후보 |
|---|---|---|
| Integrated loudness | -22.0 → -18.0 LUFS | -22.1 → -17.9 LUFS |
| 전체 RMS | -22.13 → -18.05 dBFS | -22.32 → -18.13 dBFS |
| Sample peak | -3.61 → -1.20 dBFS | -3.36 → -1.21 dBFS |
| True peak, ebur128 | -3.6 → -1.2 dBTP | -3.3 → -1.2 dBTP |
| 레일 도달 클리핑 샘플 | 0 → 0 | 0 → 0 |
| 길이 | 47.150 → 47.150초 | 49.550 → 49.550초 |
| 정확한 frame 수 | 1,131,600 → 1,131,600 | 1,189,200 → 1,189,200 |
| 포맷 | 24 kHz / mono / PCM16 유지 | 24 kHz / mono / PCM16 유지 |
| 정확한 zero sample 비율 | 6.91 → 6.84% | 8.46 → 8.37% |
| 20 ms RMS < -50 dBFS 비율 | 26.73 → 24.69% | 29.39 → 27.57% |
| pass 2 실제 처리 모드 | dynamic | dynamic |

음량이 올라가면서 낮은 음성 구간이 무음 임계값 위로 이동할 수 있으므로 무음 비율 감소를 새 발화 생성이나 내용 복구로 해석하지 않습니다. loudnorm은 true peak 제한과 목표 음량을 함께 맞추며, 이번 입력은 단순 선형 증폭의 피크 조건을 만족하지 않아 dynamic 모드가 사용됐습니다. 내부 192 kHz 처리 뒤 출력 `-ar 24000`을 명시했습니다. 알고리즘·2-pass·출력 표본률·dynamic 전환의 근거는 [FFmpeg 공식 loudnorm 문서](https://ffmpeg.org/ffmpeg-filters.html#loudnorm)입니다.

### 중요 단위 정정 구간

CASE-0002 발화 4, 17.55–23.10초의 “휴지 한 개가 아니라 한 박스예요. 단위를 제대로 적어 주세요.” 구간입니다.

| 항목 | 원본 | 후보 |
|---|---:|---:|
| RMS | -24.15 dBFS | -19.77 dBFS |
| Integrated loudness | -23.7 LUFS | -19.3 LUFS |
| Sample peak | -6.79 dBFS | -2.49 dBFS |
| True peak | -6.7 dBTP | -2.4 dBTP |
| 클리핑 샘플 | 0 | 0 |
| 길이 / frames | 5.550초 / 133,200 | 5.550초 / 133,200 |

이 구간 RMS는 약 4.38 dB, 통합 음량은 4.4 LU 높아졌습니다. 상대적으로 작은 경영주 발화라는 성격은 남아 있으며 화자 간 모든 음량을 같게 만든 것은 아닙니다. 모든 16개 발화의 전후 RMS/LUFS/피크/클리핑/길이도 각 케이스 `metrics.json`과 전체 `comparison.json`에 기록했습니다.

## 후보 위치와 재현 명령

완료 폴더:

```text
C:/00.프로젝트/happycall-ralphthon/.local/audio-normalized/20260921T085716Z-f7492cbb/
  comparison.json
  CASE-0001/original.wav
  CASE-0001/candidate.wav
  CASE-0001/metrics.json
  CASE-0002/original.wav
  CASE-0002/candidate.wav
  CASE-0002/metrics.json
```

각 case 폴더에는 pass1/pass2 명령 JSON과 FFmpeg 원문 로그, 전체·발화별 측정 로그, source-metadata.json도 있습니다. 명령 기록의 `.incomplete` 경로는 당시 실제 처리 위치이며, 모든 검증 후 현재 완료 폴더로 이동했습니다.

| 파일 | SHA-256 |
|---|---|
| CASE-0001 원본/public/보존사본 | `1432d1b44b66d7edd53408811ab73ede98303555235b14b4587671a390a51b92` |
| CASE-0001 후보 | `d4eeb6448ff8969f27034ecade9a050ee212468585c6300b19c9a0ebdc372931` |
| CASE-0002 원본/public/보존사본 | `f9fa70afaeb575876ab2dd18f1f395fbd38d6fec99b7cc0f70cb723650fb2e0c` |
| CASE-0002 후보 | `333897f4f10426674ec97b9e3a44c2f8da21f1f7931b4f911c82a29abcf6b914` |

재현은 저장소 루트에서 다음과 같습니다. 원본 baseline hash가 달라지면 자동으로 새 원본을 채택하지 않고 실패합니다. 원격 pc2 음원이 들어온 경우에는 메인이 baseline·metadata를 새로 검토한 뒤 사용해야 합니다.

```powershell
Set-Location 'C:/00.프로젝트/happycall-ralphthon'
python -X utf8 scripts/normalize_demo_audio.py
python -X utf8 -m unittest discover -s tests -p test_audio_preparation.py -v
```

이 PC의 system Python 3.14에는 imageio_ffmpeg가 설치되어 있습니다. FFmpeg는 `7.1-essentials_build-www.gyan.dev`입니다. 가상환경이나 다른 PC에서 FFmpeg가 검색되지 않으면 **이미 설치된** FFmpeg의 절대 경로를 `--ffmpeg`로 넘깁니다. 자동 설치·다운로드하지 않습니다.

```powershell
python -X utf8 scripts/normalize_demo_audio.py --ffmpeg 'C:/Users/choi8/AppData/Local/Programs/Python/Python314/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
```

### 메인 A/B 검증과 교체 인계

위의 원본/후보 WAV를 같은 브라우저·출력 장치에서 각각 1배속, volume 1로 비교합니다. 파일을 직접 열거나 비어 있는 로컬 포트에서 해당 완료 폴더만 임시 제공할 수 있습니다. 아래 3126은 메인이 점유 여부를 확인한 뒤 사용하는 예이며, 이번 작업에서는 서버를 띄우지 않았습니다.

```powershell
python -m http.server 3126 --bind 127.0.0.1 --directory 'C:/00.프로젝트/happycall-ralphthon/.local/audio-normalized/20260921T085716Z-f7492cbb'
```

CASE-0002 비교 URL 경로는 `/CASE-0002/original.wav`, `/CASE-0002/candidate.wav`입니다. 비교 서버는 localhost에서만 사용하고 종료는 해당 터미널의 Ctrl+C입니다. 실제 앱 교체는 메인 인수 후 수행하며 후보를 public에 반영할 때 새 hash·자산버전·브라우저 캐시·Release manifest와 후속 STT 입력 파일을 함께 대조해야 합니다. 이 작업은 현재 public이나 manifest를 교체하지 않았습니다. 되돌릴 때 사용할 원본 사본도 같은 폴더에 있습니다.

## 검증·발견·수정 기록

- 단위/실제 FFmpeg 테스트: `python -X utf8 -m unittest discover -s tests -p test_audio_preparation.py -v`의 최종 실제 결과는 **15개 통과, 실패 0, 오류 0, 건너뜀 0**입니다(1.625초, exit 0). 정상/불량/경계, 실제 tone 2-pass, 원본 hash·exact frames, 2-pass 중간 실패 시 부분 WAV 격리, 기존 후보 보존, 빈 입력, source 변경, 캐시 실제 mock 호출과 두 번째 캐시 재사용을 포함합니다.
- 독립 검토에서 열린 구간(start>0,end=None)의 RMS/LUFS 측정 범위 불일치를 발견해 FFmpeg에도 동일 start trim을 적용했습니다. 현재 두 실제 후보는 start/end 쌍을 사용하여 영향이 없으며 새 회귀 검사로 보호합니다.
- true peak 소수 1자리 반올림 문제를 발견해 표시값 -1.0을 거부하고 ≤-1.1을 요구하도록 보강했습니다. 두 기존 실제 후보를 보강된 판정기로 재확인해 2/2 적합입니다.
- 빈 케이스가 0건 성공으로 승격되지 않도록 차단했습니다. NaN·무음/측정 부재·길이 변경·1개라도 클리핑이 있는 반례는 거부합니다.
- 변이 검증: speed를 캐시 지문에서 제외한 변이는 2개 assertion 실패로, 클리핑을 무시한 변이는 1개 assertion 실패로 검출했습니다. 검사 중 임시 메모리 변이만 사용했으며 제품 코드는 복원되어 있습니다. 증거는 `.local/audio-normalized/validation-evidence.json`입니다.
- FFmpeg 실패는 `.failed/failure.json`으로 남고 이전 후보·원본은 보존됩니다. 중단 시 남을 수 있는 `.incomplete` 및 `.failed` 디렉터리는 인수 후보가 아닙니다. 자동 삭제·재시도·원본 교체는 하지 않습니다.

## TTS 캐시 수정과 남은 한계

`build_speech_parameters()`가 모델·speed·instructions·input·voice·response_format의 정본 dict를 만들고, canonical JSON 지문과 실제 `client.audio.speech.create(**request_parameters)`에 동일 dict를 사용합니다. 값이 같은 dict는 순서가 달라도 같은 지문이고, 여섯 필드 중 하나만 달라도 새 지문입니다. 기존 한국어 지시·모델·음색을 유지하며 speed=1.0을 명시했습니다. helper import로 서버/키 로딩이 시작되지 않도록 실제 생성 분기까지 해당 import를 지연했습니다.

**캐시 형식 변경 때문에 다음 실제 `--generate`는 기존 캐시를 재사용하지 않고 새 유료 생성으로 이어질 수 있습니다.** 이 작업에서 실제 TTS 생성 스크립트는 실행하지 않았습니다. 테스트의 `main()` 호출은 임시 ROOT·가짜 client/Budget로 격리했으며 외부 호출은 없습니다. 기존 캐시·기존 WAV는 삭제하지 않았습니다.

이 환경에서 수행한 것은 PCM/FFmpeg 측정과 자동 검증입니다. 실제 소리를 직접 듣지 않았고, OS/브라우저 출력장치·사람의 핵심어 인지·발음 개선·기존 STT 오류 개선은 미검증입니다. 유료 TTS/STT, 제품 UI 수정, Git 커밋/푸시, Release는 메인 담당으로 남겼습니다.
