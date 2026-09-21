# pc2 N02-M2 합성 통화 원본 패키지

2026-09-21 pc1/CJJ, GitHub `cjj0202-glitch`. 기준 HEAD `cc6c6d1c9353390e5b489a2711c85b78f56d85af`에서 기존 합성 발화 캐시를 읽기 전용으로 포장했습니다. 물리 pc2에서 실행한 결과는 아닙니다.

기존 발화 WAV 16개와 생성 당시 타임라인을 [전용 prerelease](https://github.com/cjj0202-glitch/happycall-ralphthon/releases/tag/demo-voice-sources-20260921)에 게시했습니다. 원격 자산 2개를 별도 폴더로 다시 받아 바이트·SHA-256을 검증했고, 내려받은 16개 WAV 전체를 FFmpeg로 디코딩했습니다. pc2의 수신·편집·청취 결과는 아직 확인하지 않았습니다.

## 전달 파일

| 자산 | 바이트 | SHA-256 |
|---|---:|---|
| [demo-voice-sources-20260921.zip](https://github.com/cjj0202-glitch/happycall-ralphthon/releases/download/demo-voice-sources-20260921/demo-voice-sources-20260921.zip) | 3,474,435 | `4cce238f49c513b9ef068a8a1e5a34c4938d968b16de2a39ac245a3eaac3ac12` |
| [demo-voice-sources-20260921.manifest.json](https://github.com/cjj0202-glitch/happycall-ralphthon/releases/download/demo-voice-sources-20260921/demo-voice-sources-20260921.manifest.json) | 17,735 | `6a734e6437c1e21a9a2d82c62842d58b83856798e01bb1023f914a00406fe75e` |

Release tag는 `demo-voice-sources-20260921`, 게시 시각은 2026-09-21 19:57:56 KST입니다. 기존 동일 tag가 없음을 조회한 후 생성했고 기존 Release·자산은 변경하지 않았습니다. GitHub 자산 digest도 위 2개 SHA와 일치합니다.

ZIP 구성은 `segments/CASE-0001-*.wav` 8개, `segments/CASE-0002-*.wav` 8개, manifest 1개로 총 17개입니다. 별도 manifest와 ZIP 내부 manifest는 바이트가 같습니다. 승인된 두 전체 통화 파일은 패키지에 중복 포함하지 않았습니다.

## 출처와 검증

원본은 `.local/tts-segments/`의 기존 WAV 16개와 `CASE-0001.metadata.json`, `CASE-0002.metadata.json`입니다. 텍스트는 `synthetic: true`인 `data/fixtures/cases.json`의 두 사례 `transcript`에서 화자·대본만 선별했습니다. 기존 생성기 커밋 `5288839`의 `SHA256(voice + text)[:16]`로 16개 캐시 파일명을 재계산해 실제 파일과 대조했습니다. 폴더 전체 복사나 원본 JSON 전달을 사용하지 않았습니다.

모든 WAV는 44바이트의 `RIFF/WAVE`, `fmt `, `data` 헤더와 PCM으로만 구성되어 있습니다. 발화·화자·텍스트·구간·파일명·크기·해시·포맷·v1/v2 관계만 새 manifest에 작성했습니다. 키·인증·원장·provider 응답·원본 실행 로그·운영 원천자료를 포함하지 않았습니다.

| 사례 | 발화 수 | 발화 PCM 합계 | 0.35초 gap × 8 | 전체 길이 | 전체 PCM frame |
|---|---:|---:|---:|---:|---:|
| CASE-0001 | 8 | 44.35초 | 2.80초 | 47.15초 | 1,131,600 |
| CASE-0002 | 8 | 46.75초 | 2.80초 | 49.55초 | 1,189,200 |

포맷은 전체 16개 모두 24,000 Hz, mono, signed PCM16 little-endian입니다. 마지막 발화 뒤에도 0.35초 gap을 붙이는 원 생성기의 방식으로 재조립했습니다.

- 로컬 원본 검사: 16/16 캐시 파일 존재·전체 PCM 읽기·타임라인 일치. 재조립한 WAV가 `.local/audio-normalized/20260921T085716Z-f7492cbb/CASE-0001/original.wav` 및 `CASE-0002/original.wav`와 바이트 단위로 2/2 일치했습니다.
- 승인 원본 대조: 두 v1 보존 파일의 bytes/SHA는 `data/demo-media-manifest.json`의 `sourceBytes/sourceSha256`과 2/2 일치했습니다.
- 승인 v2 대조: 현재 `apps/web/public/demo/CASE-0001.wav`, `CASE-0002.wav`의 bytes/SHA는 manifest와 2/2 일치했습니다. 두 v1/v2의 최종 포맷·정확한 프레임 수·길이는 2/2 같고, PCM 바이트는 2/2 다릅니다.
- 원격 재검사: 별도 다운로드 2/2 bytes/SHA 일치, ZIP CRC·엔트리 집합 17/17, 내려받은 각 WAV를 FFmpeg로 전부 디코딩한 PCM이 캐시 PCM과 16/16 일치했습니다. FFmpeg 비정상 종료·error 출력은 각각 0/16입니다.
- 양성/반례: 원격 정상 자산 2/2가 검사식을 통과했고, ZIP 한 바이트를 메모리에서만 바꾼 같은 크기 변이는 SHA 검사에서 불일치로 검출했습니다. 원본 ZIP은 변경하지 않았습니다.

v1 전체파일 SHA:

| 사례 | v1 SHA-256 | 승인 v2 SHA-256 |
|---|---|---|
| CASE-0001 | `1432d1b44b66d7edd53408811ab73ede98303555235b14b4587671a390a51b92` | `d4eeb6448ff8969f27034ecade9a050ee212468585c6300b19c9a0ebdc372931` |
| CASE-0002 | `f9fa70afaeb575876ab2dd18f1f395fbd38d6fec99b7cc0f70cb723650fb2e0c` | `333897f4f10426674ec97b9e3a44c2f8da21f1f7931b4f911c82a29abcf6b914` |

v2는 기존 FFmpeg loudnorm 2-pass dynamic 처리와 최종 24 kHz 리샘플링을 거친 결과입니다. PCM 값이 달라졌고 WAV 헤더가 34바이트 늘었습니다. 패키지 캐시를 이어 붙여 v2 해시가 나온다고 해석하면 안 됩니다. 이 작업에서 새 정규화·리샘플링은 실행하지 않았습니다.

## pc2에서 받는 방법과 사용 경계

본인 저장소 루트에서 아직 없는 수신 폴더를 지정합니다. `--clobber`는 사용하지 않습니다.

```powershell
gh release download demo-voice-sources-20260921 --repo cjj0202-glitch/happycall-ralphthon --dir '.local/pc2-voice-sources-20260921' --pattern 'demo-voice-sources-20260921.zip' --pattern 'demo-voice-sources-20260921.manifest.json'
Get-FileHash -Algorithm SHA256 -LiteralPath '.local/pc2-voice-sources-20260921/demo-voice-sources-20260921.zip', '.local/pc2-voice-sources-20260921/demo-voice-sources-20260921.manifest.json'
```

해시와 크기를 위 표에 대조한 뒤 새 폴더로 압축을 풀고 복사본으로 편집합니다. 전달 manifest의 `segments[].startSeconds/endSeconds`는 원본 전체파일의 구간입니다. CASE-0002 단위 정정 발화(index 3)는 17.55~23.10초이며 원본 내부 무음도 포함합니다.

- 원 캐시 WAV 16개 모두 스트리밍 헤더가 `2,147,483,647` frames를 선언합니다. 실제 디코딩한 PCM 수가 manifest의 `format.frames/durationSeconds`이며, 헤더 값으로 길이를 계산하지 않습니다. 편집기가 요구하면 복사본의 헤더만 올바르게 다시 쓸 수 있으나 그 파일은 새 SHA가 됩니다.
- 대본은 생성에 사용한 합성 텍스트입니다. STT 전사나 발음·청취 정확성의 증거가 아닙니다. start/end는 생성 당시 발화 파일의 경계이고 단어 정렬·말소리 시작/종료를 새로 추정한 값이 아닙니다.
- 현재 `generate_demo_audio.py`는 캐시 지문 규칙이 변경됐습니다. 이 패키지를 복사한 뒤 `--generate`를 실행하면 재과금 생성이 발생할 수 있으므로 편집용 원본으로 직접 읽습니다.
- 기존 v2·fixture·제품 manifest는 유지합니다. pc2의 A/B 후보는 별도 출력으로 만들고 새 해시·전후 타임라인·표준속도 청취/재생 검증과 함께 메인에게 인계합니다.

## 로컬 재현 기록

`C:/00.프로젝트/happycall-ralphthon/.local/pc2-voice-package/`에 원본 ZIP·정제 manifest·일회성 생성/검증 스크립트·재다운로드·정제 검증 결과가 있습니다. 이 로컬 폴더 전체를 공유하지 않고 위 두 자산만 명시 업로드했습니다. 생성기는 기존 결과를 덮어쓰지 않습니다.

실제 실행한 명령:

```powershell
python -X utf8 .local/pc2-voice-package/prepare_package.py
gh release download demo-voice-sources-20260921 --repo cjj0202-glitch/happycall-ralphthon --dir '.local/pc2-voice-package/remote-redownload' --pattern 'demo-voice-sources-20260921.zip' --pattern 'demo-voice-sources-20260921.manifest.json'
python -X utf8 .local/pc2-voice-package/verify_redownload.py
```

무과금 로컬 패키징·디코딩과 GitHub 자산 공유만 실행했습니다. 새 TTS/STT/API 생성, 공용 서버 변경, 제품 파일 교체, Git 커밋·main push, 이슈 발송은 실행하지 않았습니다. 사람 청취와 pc2 수신 확인은 미검증입니다.
