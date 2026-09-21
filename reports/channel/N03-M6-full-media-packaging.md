# N03-M6 — 검수한 전체 프레임을 동일 좌표의 MP4로 묶기

2026-09-21 pc1 후속 배정. M5 코드·인공 검사의 인수와 별개로 실제1080p/288프레임 렌더는 pc1에서 진행 중입니다. 생성 중 폴더를 검사하거나 새 렌더를 시작하지 않습니다.

| 항목 | 계약 |
|---|---|
| 사용자 결과 | CCTV 영상과 클릭 좌표가 같은12초/24fps/1920×1080 시간축으로 재생되도록, 완성 PNG를 MP4와 원본 tracks 묶음으로 만들고 잘못된 조합을 거부 |
| 담당·소유 | pc3/LAPTOP-U2AL73UH/mcjun86-oss. 신규 `scripts/media_pc3/package_full_animation_media.py`, `test_full_animation_media.py`, `reports/pc3/full-media-*`만 편집. 기존 생성기/검사기/제품manifest/fixture/frontend/Release 변경 금지 |
| 기준·입력 | pc3 소스 de2c790a5e739a4aa9cdb2fc481fb10db3e43e29의 M5. 메인이 제공하는 별도 expected manifest와 **완주된** animation291파일. 메인 고정값은 reports/pc3-full-render-main-start.md에 연결. 실행 바이너리는 호출자가 명시하는 기존 ffmpeg 경로, 자동다운로드/설치 없음 |
| 완료 조건 | M5 구조·해시 검사 통과 후 프레임1..288을24fps/H.264/yuv420p/1080p/faststart로 인코딩. crop/pad/리타이밍/오프셋 없이12초. 최종영상 전프레임 디코딩·실제메타데이터 대조 후 원본tracks 바이트 그대로 복사. MP4 SHA에 결합된 정확한5필드 descriptor 생성 |
| 검증 | 독립 정상/검사실패/인코더실패·부분출력/프레임수·길이·크기불일치/원본변경/출력경로겹침·덮어쓰기/가드삭제변이. 실제 인코딩을 못 하면 명령·출력검증 단위와 미실행을 구분하며 인공decoder를 실제영상검수로 세지 않음 |
| 인계 | 기존 issue9 ACK→20~40분 첫결과→소유경로·소스SHA·명령·기대/실측·실패/수정·검증분모를 회신. 전체 N03·실제영상·제품등록 완료 선언/이슈종결 금지 |

## 입력과 출력의 경계

`verify_full_animation.py`의 PASS_WITH_PENDING은 구조검사 완료이며 시각품질 승인 자체가 아닙니다. 먼저 이를 통과해야 패키징할 수 있습니다. expected를 출력 report에서 만들어내지 않습니다. 입력291파일은 읽기 전용으로 보존하고, 출력은 그 밖의 새 디렉터리여야 합니다. 기존 출력이나 링크·상위경로를 덮어쓰지 않습니다. 실패 시 성공보고서/제품등록을 남기지 않으며 부분출력을 성공으로 재사용하지 않습니다.

raw tracks.json 본문은 이미 frontend `validateTracks` 계약과 일치합니다. 별도 좌표 변환·JSON 재직렬화 없이 `sorter-demo.tracks.json`으로 원바이트 복사합니다. `source=synthetic-scene-ground-truth`, normalized-image-top-left, 사건시각/경과시각 분리, businessToteId:null, occlusionTested:false를 유지합니다. 기존3초 단편에12초 tracks를 연결하면 안 됩니다.

출력 descriptor는 정확히 다음5필드입니다: `schemaVersion=oneflow-cctv-tracks-v1`, `url=/demo/sorter-demo.tracks.json`, `bytes`, `sha256`, `videoSha256`. bytes/sha256는 실제 복사 파일, videoSha256는 실제 최종MP4의 값입니다. source/render/expected 해시 등 출처는 descriptor 밖 별도 candidate-report에 기록합니다. manifest의 최상위4번째 asset을 만들지 않습니다.

인코더와 디코더가 있다고 가정하지 마세요. 현재 설치된 공식 도구가 있으면 합성 작은 검사용 PNG로 기능을 검증할 수 있으나, 없으면 새 설치/다운로드/환경 우회 없이 코드 및 인공 실패검사를 인계합니다. FFmpeg 실행이 허용되는 경우도 실제 full render를 대체할 장면생성·Blender 실행은 금지입니다. subprocess는 명시 argv, shell=False, 시간제한, 출력/종료코드 확인, Windows 숨김 실행을 사용합니다. stderr에 나온 성공같은 문구만으로 디코딩통과를 만들지 않습니다.

pc1은 실제 완주 후 고정 expected로 검사하고 시각·물리접촉·가림·깜빡임을 확인한 뒤 이 도구를 실행합니다. 최종 WAV2개+MP4+tracks 물리4파일의 v4 Release, manifest갱신, 새빌드, 영상/좌표 UI 연결·seek 검수는 pc1 소유입니다. 원천데이터·키·API·서버·브라우저·배포·자동과금·다른PC 지시는 이 카드 범위 밖입니다.
