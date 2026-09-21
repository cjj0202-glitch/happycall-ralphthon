# N02-M5 — 원형 WAV와 관측 타임라인 검증 계약

pc2 / 안영일 / MR-A83. 카드 [#8 / 5762811455](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/8#issuecomment-5762811455), ACK [5762920918](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/8#issuecomment-5762920918), 2026-09-22 00:20 KST.

사용자는 공식 편집기에서 받은 전체 음원 원형을 유지하면서 같은 음원의 자막 후보를 검토한다. 이 도구는 원음을 편집하거나 재생하지 않는다. 실제 화자·발음·STT·사람 청취·부모 UI는 별도 검사다. 공식 WAV 0/2, 실제 관측 타임라인 0/20은 **NOT_RUN**이다.

## BMAD와 첫 Bolt

| 관점 | 구현 결정 | 판단 근거 |
|---|---|---|
| 업무 | 원형 음원을 보존하고 공용 반영 전 후보만 제공 | 읽기 전후 크기·SHA·파일 동일성 대조, WAV 출력 없음 |
| UX | 미확인 gap, 미지원 형식, 실패 사유를 노출 | validation.json의 errors/unresolved, 실패 시 후보 없음 |
| 구조 | 대본·별도 기대 descriptor·관측·명시 WAV 매핑을 분리 | 후보에서 기대 SHA를 만들지 않음; 최종 인수는 pc1 |
| 검증 | 작은 실제 PCM16 2개·20턴 정상과 큰 gap 하나를 비교 | 인공 양성 PASS/후보 생성, 반례 REJECTED/후보 없음 |

정합 결과는 `candidate=true`, 후보 상태 `candidate`, `accepted=false`다. **공용 manifest/fixture, 제품 UI, Release, 중앙 인수표는 pc1 소유**이며 이 변경에 포함되지 않는다. 사용자에게 새 결정을 요구할 항목 없이 카드의 계산·보존 규칙을 구현한다.

## 고정 대본

- 기준 `cd262e3425ceaa2710e0d3adc1920a9f87f587c0:planning/media/korean-call-v5-fast-script.json`.
- 원바이트 25,175 / SHA256 `47ae253daf158335e92fa136f3e9ba8b3af118fb278b66fcf137e91c3242ade6`.
- schema `oneflow-korean-call-v5-fast-candidate-2`, CASE-0001 F5-M01~10와 CASE-0002 F5-W01~10, 정확히 이 순서의 20턴.
- 표기 `text`와 발음 `spokenText`가 다른 5턴을 각각 보존한다. `editorInputText`는 `spokenText`와 일치해야 한다. fixture 후보 표시는 `text`다.
- 상담원 F5-W03의 “휴지 1개” 오청과 경영주 F5-W04의 “1개가 아니라 1박스” 정정을 자동 교정하지 않는다. 제안 `pauseAfterMs`를 관측 gap으로 사용하지 않는다.
- 줄바꿈 변경으로 SHA를 맞추지 않는다. 로컬 Git blob의 원바이트 사본을 새 ignored run에 둔다.

## 입력 JSON 계약

`--expected`는 **pc1이 독립적으로 고정해 전달하는 파일**이다. 공식 입력에서는 검사기 사용자가 실제 파일에서 즉석 계산한 값을 기대 descriptor로 대체하면 안 된다. 검사기는 작성자의 신원/전자서명을 인증하지 않으며, 입력 파일이 독립 기대값과 맞는지만 확인한다. 인공 테스트 생성기는 명시적으로 인공 입력의 고정값을 만든다.

| 파일 | 필수 구조 |
|---|---|
| expected | `schemaVersion=clova-timeline-input-descriptors-v1`, `origin`, `script={bytes,sha256}`, `observations={bytes,sha256,source,observedAt}`, `wavs=[{caseId,bytes,sha256}, ...]` |
| observations | `schemaVersion=clova-timeline-observations-v1`, `origin`, `source`, 시간대 포함 ISO8601 `observedAt`, `uiResolutionSeconds=0.01`, `cases=[{caseId,turns:[...]}]` |
| 각 turn | `id`, `speaker`, `text`, `spokenText`, `editorInputText`, `startSeconds`, `officialGapAfterSeconds`, `gapObservationStatus` |

`origin`은 두 문서에서 동일한 `artificial` 또는 `official_clova`다. WAV 배열과 관측 사례는 CASE-0001→CASE-0002 순서이며 각각 10턴이다. `source`, `observedAt`는 기대 descriptor와 관측 파일에서 정확히 같아야 한다. 숫자는 bool/문자열/null/NaN/Infinity를 허용하지 않는다. JSON 중복 키·100단계 초과 중첩·고립 surrogate도 거절한다. 추가 키는 판정에 사용하지 않는다.

`gapObservationStatus=observed`는 유한한 비음수 gap이 필요하다. 마지막 10턴에만 `not_displayed`와 `null` 조합을 허용한다. 중간 gap 미확인/null은 `unresolved`와 REJECTED이며 0으로 채우지 않는다. 원관측이 마지막 숫자 gap을 포함하면 그대로 남기고 EOF에서 다시 빼지 않는다.

## 파생 시간과 원음 계측

중간 end는 `다음 start - 현재 officialGapAfterSeconds`, 마지막 end는 `실제 PCM 프레임 수 / sampleRate`다. UI 관측 수치의 십진 표현과 EOF를 Fraction으로 정확히 비교한다. `0.4-0.1`의 이진 소수 오차 때문에 start=0.3인 0길이 구간을 허용하지 않는다. start 엄격 증가와 `0 <= start < end <= EOF`를 검사한다. 출력에는 읽기 쉬운 endSeconds 외에 exact numerator/denominator와 계산식·피연산자를 남긴다. UI 0.01초 분해능은 실제 정확도 ±0.01초 보장이 아니다.

RIFF/WAVE 파일의 실제 크기, chunk 경계·패딩, 단일 fmt/data 순서, PCM16의 채널/sampleRate/blockAlign/byteRate/전체 프레임 정합을 확인한다. PCM16은 실제 전체 data bytes를 읽은 프레임 수로 계측한다. 다른 형식은 `UNSUPPORTED`로 헤더 사실만 보고하며 변환하지 않는다. 파생 end는 실제 발화 끝을 샘플 단위로 측정한 값이 아니다.

## 파일과 실패 계약

- 출력은 저장소 `.local/clova-v5-intake/` 아래 존재하지 않는 새 디렉터리이며, 부모는 이미 있어야 한다. 기존 run/파일은 고치지 않는다.
- 경로 `..`, UNC, symlink/reparse/junction, 입력 hardlink·파일 중복·입출력 충돌을 거절한다. 원본은 읽기 전용으로 열고 전후 전체 SHA·identity를 비교한다.
- Windows path.stat과 fstat의 ctime를 교차 비교하지 않는다. 공통 identity는 서로 대조하고 ctime는 path 전후와 handle 전후 각각 대조한다. 같은 길이 바이트 변경도 마지막 재읽기 SHA로 차단한다.
- 출력 디렉터리와 조상 디렉터리를 Windows 파일 handle로 잡고 삭제 공유를 허용하지 않아 검사~배타적 파일 생성 사이 rename/링크 교체를 차단한다. ACL·방화벽·정책 변경이 아니다. **출력 발행은 Windows에서만 지원**하며 다른 OS는 `OUTPUT_PLATFORM`으로 중단한다.
- 안전한 새 run에서는 입력 실패를 validation.json에 남기고 후보 파일을 만들지 않는다. unsafe output은 출력 전에 오류를 반환한다. 출력 I/O 자체가 실패하면 CLI는 오류 종료하며 PASS validation.json이 없으므로 후보를 인수할 수 없다.
- 성공도 타임라인·fixture **제안** 2개를 먼저 쓰고 validation.json을 마지막에 쓴다. 중간에 중단된 run은 재사용하지 않는다. 후보를 읽는 쪽은 마지막 validation.json의 PASS와 입력 SHA를 먼저 확인하고 pc1 검토를 거쳐야 한다.

## 실제 실행법

기존 설치된 Python 표준 라이브러리만 사용한다. 아래 PowerShell은 실제 pc2 checkout에서 실행하며 매번 새 인공 run을 만든다. 공식 파일 경로를 가짜로 채운 명령은 제공하지 않는다.

```powershell
Set-Location C:\Users\Administrator\Desktop\hackerton\happycall-ralphthon
. ..\enter-happycall.ps1
python -B scripts/media_pc2/validate_clova_timeline.py --help
python -B -m unittest discover -s tests/media_pc2 -p test_clova_timeline.py -v
$m5run = Join-Path (Get-Location) ('.local/clova-v5-intake/artificial-' + [guid]::NewGuid().ToString('N'))
$m5inputs = python -B tests/media_pc2/test_clova_timeline.py --prepare-artificial $m5run | ConvertFrom-Json
python -B scripts/media_pc2/validate_clova_timeline.py --script $m5inputs.script --case-0001-wav $m5inputs.wavs.'CASE-0001' --case-0002-wav $m5inputs.wavs.'CASE-0002' --expected $m5inputs.expected --observations $m5inputs.observations --output $m5inputs.output
```

종료 코드는 PASS=0, REJECTED=2, UNSUPPORTED=3이다. `--help`는 파일을 읽거나 생성하지 않는다. 인공 helper는 대본 Git blob과 1.0/1.1초 작은 PCM16 파일을 사용하며 발화 오디오가 아니다. 공식 파일 수신 후에는 pc1의 독립 descriptor와 원관측을 이 스키마에 옮긴 새 전달 묶음으로 같은 명시 인자를 사용한다. 다운로더·음원 편집·후보 자동 통합은 없다.

## 남은 공식 입력과 pc1 후속

공식 전체 WAV 2개, 각 case별 독립 크기/SHA, 편집기 시작·쉼 20턴, 마지막 gap UI 부재 여부, 원관측 출처·시각·파일 해시가 필요하다. 중간 gap 하나라도 미확인이면 정합 후보로 인수할 수 없다. 이후 pc1이 사람 전체 1배속 청취, 숫자·단위·부정·정정 의미, 실제 종료 후 STT→정제, 공용 fixture·manifest, UI 및 두 흐름 6회를 별도로 확인한다. N02 전체·TEST·최종 인수는 이 도구의 PASS와 구분한다.
