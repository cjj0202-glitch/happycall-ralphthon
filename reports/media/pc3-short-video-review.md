# PC3 3초 검토용 MP4 — 파일 기반 인수 검증

2026-09-21 KST. 원본 SHA `33fa0e4edeb88c0d4ad5e9cc0194ffc7e96cebcd`에서 생성한 72 PNG를 새 로컬 폴더에 인코딩했습니다. **검토용 파일 후보이며 제품 미디어 등록이나 브라우저 재생 검수 완료가 아닙니다.**

## 결과물

- MP4: `.local/pc3-render-intake/short-33fa0e4-01/review-video/case-0002-ww3-short-review.mp4`
- 크기: **544,733B**
- SHA-256: **`21ac21351803125334deba303fd249909774aba98058bc787e38121058f70ccf`**
- 후보 명세: 같은 폴더 `candidate.json`
- 원본 72프레임 목록·각 PNG SHA·영상 시간·디코딩 RGB SHA: `frame-index.json`
- 전체 실제 실행 명령·PID·시각·종료 코드: `commands.json`

인코딩은 설치되어 있던 `ffmpeg version 7.1-essentials_build-www.gyan.dev`를 사용했습니다. 새 도구 설치나 다운로드는 하지 않았습니다. 실행 PID 11704, 21:59:51.132~21:59:52.095 KST, **exit 0, 0.953초**입니다. 버전 확인·인코딩·순차 디코딩·6회 seek·끝 경계 검사는 각각 정상 종료했고 전체 실행 기록을 보존했습니다.

## 시간과 추적 계약

| 구분 | 값 |
|---|---|
| 원본 PNG 번호 | **73~144**, 72장 |
| MP4 디코딩 프레임 번호 | **0~71**, 72장 |
| MP4 재생 구간 | **[0, 3)초**, 시작 0, 길이 3초 |
| 대응하는 원 장면 구간 | **[3, 6)초**, 마지막 표본 5.958333초 |
| 변환 | **원 장면 경과초 = MP4 경과초 + 3** |
| 업무 사건 시각 | 위 경과초와 별도. 실제 사건 시각에 경과초를 임의 합산하지 않음 |
| 추적 바인딩 | `candidate.json`의 **`trackBinding: null`** |
| 288프레임 tracks | 원본 증거 해시만 참조. **3초 클립에 등록하지 않음** |
| 대상 식별 | 시각 객체 `SYN-VIS-PARCEL02`; 실제 businessToteId는 **null** |

원본 tracks SHA는 `9fb424be0fd212bbf3faa057097bec56c63a89e4b8ae08c524e5fd76b80fd44b`입니다. 원본 타임라인을 유지한 288프레임 파일을 0초부터 시작하는 3초 영상에 그대로 연결하면 3초 오차가 생기므로, 이 후보는 연결을 비워두고 offset만 명시합니다.

## 실제 디코딩 검사

단순 파일 metadata 확인과 별도로 FFmpeg가 H.264를 디코딩하도록 실행하고 `showinfo`의 각 프레임을 파싱했습니다. RGB 전체 프레임도 다시 디코딩해 72개 해시를 기록했습니다.

| 검증 | 기대 | 실측 |
|---|---|---|
| 코덱·색 형식 | H.264 / yuv420p | H.264 High / yuv420p progressive |
| 차원 | 1280×720 | 1280×720, SAR 1:1 |
| 프레임 수 | 72 | **72/72 디코딩** |
| 시작·길이 | 0 / 3초 | **0.000000 / 3.00초** |
| 프레임율 | 24fps | 24/1 |
| PTS 연속성 | 1/24초 간격 | timebase 1/12288, PTS 0~36352, **각 간격 512** |
| 마지막 표시 시각 | 71/24초 | 2.958333초 |
| 오디오 | 0개 | **0개** |
| keyframe | 영상 0/1/2초 | 프레임 **0/24/48** |

증거: `decode-timestamps.log`, `decoded-timestamps.json`, `decode-rgb.log`, `frame-index.json`. 프레임 metadata와 실제 RGB 바이트 수 **1280×720×3×72**를 모두 대조했습니다.

## 파일 seek 검사

입력 앞 `-ss`를 사용해 실제 파일 탐색과 디코딩을 수행했습니다. 각 결과 RGB SHA가 순차 디코딩의 대응 프레임과 동일했습니다. keyframe과 중간 프레임 모두 검사했습니다.

| MP4 seek(초) | 디코딩 프레임 | 원본 PNG | 원 장면 경과초 | 결과 |
|---:|---:|---:|---:|---|
| 0 | 0 | 73 | 3 | 일치 |
| 0.5 | 12 | 85 | 3.5 | 일치 |
| 1 | 24 | 97 | 4 | 일치 |
| 1.5 | 36 | 109 | 4.5 | 일치 |
| 2 | 48 | 121 | 5 | 일치 |
| 2.5 | 60 | 133 | 5.5 | 일치 |

끝 경계인 MP4 3초로 seek했을 때 RGB 출력은 **0바이트**였습니다. `[0,3)` 밖의 프레임을 만들어내지 않았습니다. 증거: `seek-validation.json`, 개별 `seek-*.log`. 이 검사는 파일 디코더 검증이며 웹 플레이어 seek 이벤트나 HTTP Range 요청 검증을 뜻하지 않습니다.

## 원 PNG와 압축 결과 대조

원본 73/96/112/124/133/144에 대응하는 **6개 디코딩 프레임**을 PNG로 추출하고 원본 RGB와 수치 대조했습니다. PSNR은 **40.565~41.019dB**, RGB 평균 절대 차이는 **1.410~1.492(0~255 척도)**입니다. H.264/yuv420p 손실 압축이므로 원본 픽셀과 완전히 같다고 주장하지 않습니다. 이 수치는 압축 차이이며 사진급 사실성의 점수가 아닙니다.

디코딩된 원본 대응 73/133/144 세 PNG를 실제로 열었습니다. 상자·테이프·빈 라벨, 분기 구조와 주변 소품이 읽히며, 원본의 `SYNTHETIC SCENE / NOT CCTV`, `business tote UNKNOWN` 표시가 남아 있습니다. 상단 22행의 원본 대비 평균 절대 차이는 1.585~1.756입니다. 워터마크를 별도 덮거나 잘라내지 않았습니다.

증거: `source-frame-comparison.json`, `decoded-source-0073.png` 등 6장. 출력은 정돈된 CG 합성 장면이며 실제 CCTV·사진급 품질·실제 토트 식별·사고 원인 판정으로 확대하지 않습니다. 전체 72프레임 실시간 재생의 부드러움, 브라우저 코덱 지원, 반복 재생 경계는 아직 관찰하지 않았습니다.

## 원본 보존

인코딩 전후 **93개 파일**의 바이트와 SHA-256을 비교했습니다. 원본 PNG 72장, 기록된 생성 소스 Python, 동결 입력, saved blend, tracks, 렌더 결과·독립 readback이 모두 불변입니다.

`protected-before.json`과 `protected-after.json`의 SHA가 모두 `78f37dddea804cb8bcd35610f4b274269accfe2c256f0151336ce546623d399d`입니다. 공유 정본·제품 소스·media manifest·Release를 변경하지 않았으며 서버·브라우저·Blender를 기동하지 않았습니다. 이 검증자가 수행한 커밋·발송·업로드·배포는 없습니다.

## 재현 명령

기존 결과 덮어쓰기를 금지한 `-n`을 사용했습니다. 재실행하려면 새 출력 폴더를 사용합니다. 아래는 프로젝트 루트 기준의 인코딩 명령이며 실제 절대경로 인자 전체는 `commands.json`에 있습니다.

```powershell
$reviewFfmpeg = 'C:/Users/choi8/AppData/Local/Programs/Python/Python314/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
& $reviewFfmpeg -hide_banner -nostdin -n -threads 2 -framerate 24 -start_number 73 `
  -i '.local/pc3-render-intake/short-33fa0e4-01/short/frame-%04d.png' `
  -frames:v 72 -an -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -r 24 `
  -g 24 -keyint_min 24 -sc_threshold 0 -threads 2 -movflags +faststart `
  -metadata 'title=HappyCall synthetic 3-second review candidate' `
  -metadata 'comment=SYNTHETIC SCENE / NOT CCTV; source frames 73-144; clip time 0-3 seconds maps to illustrative source time 3-6 seconds; no real tote identity.' `
  '<새-출력-폴더>/case-0002-ww3-short-review.mp4'
```

인코딩과 검증 구현은 로컬 `review-video/encode-review.py`입니다. 전체 목록·원본 보존·실제 디코딩·seek·손실 대조를 하나씩 assert한 뒤에만 `candidate.json`을 작성합니다. 출력 파일이 이미 있으면 재실행을 거부합니다.

이 검증 단위의 소유 파일은 **새 `review-video/` 폴더와 이 보고서**뿐입니다. 후속 실제 플레이어 검수·적절한 짧은 track 구성·최종 등록·전체 288프레임 제작 결정은 메인 인수 단계에 남습니다.
