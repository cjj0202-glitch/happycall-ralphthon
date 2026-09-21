# PC3 N03-M7 v4 미디어 수신 보고서 독립 인수 검토

2026-09-22 · pc1 읽기 검토 · 수신 커밋 `b9e8b706d61a4052dcfcb8c4e1ceb56781403fdb`

PC3가 제출한 v4 미디어 수신 보고서를 M7의 한정된 결과로 인수할 것을 권고합니다. 보고된 4파일의 크기·SHA와 교체 전 승인 source 2개의 값이 고정 정본과 일치하며, 격리 수신기의 기준 blob과 명령 인자도 대조했습니다. pc1의 이번 실행은 문서·Git blob·순수 계약 16개 대조입니다. PC3의 실제 파일 수신, 거절 검사 10개, 보조 검토 43개를 pc1이 직접 실행한 것으로 세지 않습니다.

## 검토 대상과 경계

- 배정 정본: `reports/channel/N03-M7-v4-media-intake.md`.
- 수신 기준 main: `b9a2a1888df66c755f1f6bef19d3d7e5f3028c0f`.
- PC3 branch: `work/pc3-n03-wms-scenes`.
- 제출 파일: `reports/pc3/v4-media-intake.md` 한 개, 추가 162행.
- 제출 Git blob: 13,916 bytes, SHA256 `423fcce047544b136793984e9ea45a122efd347606fb171e7b02374fa62c646e`.

`git fetch origin work/pc3-n03-wms-scenes`는 exit 0으로 원격 추적 ref를 `2c9f3e0`에서 `b9e8b70`으로 갱신했습니다. 이후 `git show`와 `git diff-tree`로 보고서와 커밋 범위만 읽었습니다. 제출 커밋의 parent는 기존 인수본 `2c9f3e0`이며 이번 커밋의 변경은 보고서 한 개뿐입니다. PC3의 시작 SHA와 기준 main의 고유 커밋 수는 실제 `git rev-list --left-right --count 2c9f3e0...b9a2a18`에서도 14/69로 일치했습니다.

main과 갈린 branch를 pull·merge·cherry-pick하지 않았습니다. 이 작업의 유일한 저장소 파일 쓰기는 본 보고서입니다. notification 소스, UI, 타입, 배포 빌더, 기존 작업 문서는 그대로 두었습니다. 서버·브라우저·음성·영상 자산·시크릿을 열거나 새 프로세스를 시작하지 않았습니다. Release 자산 다운로드와 수신기 실행은 0회입니다.

## 원격 보고와 정본 대조

PC3는 hostname `LAPTOP-U2AL73UH`, 계정 `mcjun86-oss`, 실제 경로 `D:\hwana\Work\happycall-ralphthon`을 보고했습니다. 이 경로를 pc1 경로로 바꾸지 않았습니다. 신원 명령 결과·디스크 상태는 PC3 보고 사실이며 pc1에서 원격 OS를 직접 조회한 결과는 아닙니다.

| 물리 파일 | PC3 보고 bytes | 정본 bytes | 보고 SHA256 = 정본 SHA256 |
|---|---:|---:|---|
| CASE-0001.wav | 2,263,278 | 2,263,278 | `d4eeb6448ff8969f27034ecade9a050ee212468585c6300b19c9a0ebdc372931` |
| CASE-0002.wav | 2,388,044 | 2,388,044 | `6fe83afb8552765ab92722b838d2a0905f507551c4f98c58fa62a515033abaa0` |
| sorter-demo.mp4 | 991,249 | 991,249 | `4a640c20e209bf5a43e26c3f1c5afeb41f4157af9017f04b4c3812b1990dca51` |
| sorter-demo.tracks.json | 158,546 | 158,546 | `b9b9f50295af799cfdf718b840b0cef703f57ad3e3b778557fcd9fdeb9ac681c` |

표를 정규식으로 추출하여 고정 Git blob의 manifest를 펼친 물리 4개와 이름·크기·SHA 목록을 대조했습니다. 최상위 3자산 + 영상에 종속된 tracks 1개입니다. 현재 main manifest의 bytes도 기준 Git blob과 같았습니다. 자산 자체를 pc1에서 새로 읽어 측정한 값으로 표현하지 않습니다.

PC3가 보고한 처리 결과는 기존 일치 CASE1 보존, CASE2·MP4·tracks 3개 다운로드, 구 CASE2·MP4 2개 백업·승인 교체입니다. 수신 전 verify-only의 exit 1과 기존 파일 보존, 업그레이드 exit 0(verified4/missing0/downloaded3/upgraded2), 수신 후 exit 0(verified4/missing0/downloaded0)을 구분했습니다. 처음 실패를 성공으로 재분류하지 않았습니다.

| 교체 전 승인 원본 | 보고 bytes | 보고 SHA256 = manifest sourceSha256 |
|---|---:|---|
| CASE-0002.wav | 2,378,478 | `333897f4f10426674ec97b9e3a44c2f8da21f1f7931b4f911c82a29abcf6b914` |
| sorter-demo.mp4 | 1,097,133 | `e6cad3cf9f999b596a0fef3e3d463170e0d279568a31a4be49366e5383908881` |

백업 경로는 PC3의 `.local/demo-media-backups/20260921T172945Z-gm28yeoy`입니다. 백업 2개와 captured 2개의 동일성, result.json의 installed3/backups2/complete는 PC3 보고이며 그 비공개 파일을 pc1에서 열람하지 않았습니다. manifest의 승인 source와 보고된 두 원본은 직접 대조해 일치했습니다.

## 기준 코드와 명령의 일관성

PC3는 구 branch의 CLI를 그대로 실행했다고 쓰지 않았습니다. 기준 커밋의 수신기·의존 계약·manifest 4blob을 비공개 경로로 추출하고 그 API를 호출했다고 명시했습니다. 해당 4개를 pc1에서 `git show <고정SHA>:<path>`로 다시 읽어 보고된 bytes/SHA와 대조한 결과 4/4 일치했습니다.

| 기준 원본 | bytes | SHA256 |
|---|---:|---|
| scripts/fetch_demo_media.py | 19,351 | `83bc82d4a0c4cce01e71f81aa825293884aec8f79f95a69c139f147601d84845` |
| server/__init__.py | 63 | `b4c4a62ab2ea460cda3dddadcda2d33254eab2c0c91541ae38b4134014f9bdac` |
| server/media_contract.py | 3,890 | `369ed3cd8cf0bd4a1109bc493638f9d071f53844fcbb6c035777bd97dc8b86a9` |
| data/demo-media-manifest.json | 3,516 | `d6b6423283ef6f429080e88790a01a81eda8cdd2ca6e856116cd940c6933a346` |

실제 `fetch` 함수의 인자와 보고서의 `verify_only`, `upgrade_approved`, `backup_root`, `release_tag` 사용이 맞습니다. 기준 코드의 기본 release tag는 v3이지만 보고서의 호출은 manifest의 v4를 명시적으로 전달합니다. 실제 destination과 backup_root도 명시하며, public 바깥 백업·승인 source·잠금 검사 가드를 변경했다고 보고하지 않습니다. 이 격리 방식은 갈린 branch를 덮어쓰지 않으면서 고정 계약을 사용하는 방식으로 수용할 수 있습니다.

보고서의 Python 예제 두 블록은 AST 파싱에 성공했습니다. 마지막 재현 예제 본문은 마지막 줄바꿈을 제외하면 2,046 bytes·SHA256 `ae37037bf6c070566ccf23122e3cdcdbdd0137e4294af7bcd56a15ca642d39e7`로 보고값과 같습니다. 첫 pc1 검사에서는 임의로 LF를 하나 붙여 다른 해시 `8828dc881852bcd942b25f7fdedce67b6d6252e94c80197ef768519ecb7c5711`이 나와 assertion/exit 1이 발생했습니다. 코드 본문·끝 LF·CRLF 등 여섯 표현을 분리 대조한 결과 원래 본문이 일치함을 확인했습니다. 이는 pc1의 해시 입력 표현 차이였고 PC3 코드 불일치로 판정하지 않았습니다.

재현 코드를 실행하거나 원격 private runner를 읽은 것은 아닙니다. PC3의 02:38:50 재현 exit 0/verified4/missing0/downloaded0은 원격 보고로 남깁니다.

## 독립 실행 분모와 부정 대조

pc1의 `.venv/Scripts/python.exe -B -X utf8 -`에서 Git blob·보고서·정본 manifest만 입력으로 사용한 최종 검사는 16/16, 실제 exit 0입니다. 이 분모는 자동 문서/계약 대조이며 실제 수신·영상 재생 검사가 아닙니다.

| pc1 직접 검사 | 분모 |
|---|---:|
| 현재 manifest의 기준 blob 동일성 | 1 |
| 보고 4미디어 목록과 승인 백업 2개 목록의 정본 일치 | 2 |
| 고정 원본 blob bytes/SHA | 4 |
| 원본 표의 고유 파일 개수 | 1 |
| Python 두 블록 AST 및 재현 코드 digest | 2 |
| 실제 fetch 인자 일치 | 1 |
| 고정 순수 validator의 top3+tracks 승인 및 명시 v4 확인 | 2 |
| 아래 순수 메모리 부정 대조 | 3 |
| 합계 | 16 |

고정 `server/media_contract.py` Git blob을 메모리에서만 로드한 순수 validator에 원본 manifest를 넣으면 물리 4개를 반환했습니다. 세 변형 입력의 실제 결과는 다음과 같습니다.

| 메모리 반례 | 결과 |
|---|---|
| 네 번째 최상위 자산 추가 | `INVALID_MEDIA_ASSETS` |
| tracks.videoSha256을 원 영상과 다르게 변경 | `INVALID_TRACKS_DESCRIPTOR` |
| tracks 경로를 미등록 URL로 변경 | `INVALID_TRACKS_DESCRIPTOR` |

PC3 보고의 잘못된 SHA·미등록 tracks·경로·descriptor·동일 길이 변형 등 10/10 거절과 별도 보조 에이전트 43/43은 원격 결과입니다. 이번 16개와 합산하지 않습니다. 동일 PC3의 보조 검토를 다른 물리 PC 한 대의 수신으로 세지 않습니다.

## 사건 연결·UI·수용 경계

보고된 구조는 1920×1080, 24fps, 12초, 컨테이너 samples288·tracks288행입니다. CASE-0002/W-W3/SYN-CAM-02/CH-02/D-02, 사건시각 `2026-09-18T02:33:00+09:00`, businessToteId=null, visual ID `SYN-VIS-PARCEL02`로 배정과 일치합니다. source=synthetic-scene-ground-truth와 occlusionTested=false를 유지하며 영상 경과시각과 업무 사건시각을 구분합니다. 이 구조값은 PC3가 순수 파서/validator로 확인했다고 보고한 값이며 pc1이 이번에 디코딩한 결과가 아닙니다.

PC3는 기존 해피콜 화면을 찾지 못해 사건 진입·+1/+1·끝 유지·뒤로·overlay·닫기 포커스를 모두 미실행으로 남겼습니다. 새 서버나 브라우저를 시작하지 않았다고 명시했습니다. 새 render/encode/full decode는 각각 0회이며, pc1의 이전 렌더·인코딩 결과를 자신의 실적으로 합산하지 않았습니다. WAV는 기존 v3 바이트이고 신규 CLOVA 더빙·사람 청취의 인수 근거가 아닙니다.

보고서 안에서 M7 수신 계약을 반박하는 값의 불일치나 실행 명령 모순은 발견하지 않았습니다. 메인은 이 결과를 PC3의 v4 수신 보고 범위로만 인수할 수 있습니다. 원격 디스크 재접속·private 원시 로그 재검은 하지 않았다는 한계, UI 미실행, 사람 청취·실제 CCTV·전체 N03·TEST·최종 배포 미완료를 함께 유지해야 합니다. 현재 manifest의 준비 시점 `otherPcReceipts=PENDING`을 이 검토가 자동으로 바꾸지 않았으며 다른 PC의 수신 상태까지 완료로 확장하지 않습니다.

보고서를 메인 검토용으로 동결합니다. 커밋·#9 회신·작업 종결은 메인 소유입니다.

## 메인 판정

2026-09-22 02:48 KST, 위 검토와 #9의 PC3 실제 수신 보고를 근거로 M7의 v4 미디어 수신 보고 범위를 인수했습니다. 원격 원본 보고서를 고정 제출 커밋에서 추출해 main의 `reports/pc3/v4-media-intake.md`에 보존했으며 13,916 bytes/SHA256 `423fcce047544b136793984e9ea45a122efd347606fb171e7b02374fa62c646e`가 원본과 일치합니다. 전체 branch를 통합하지 않았습니다. UI·청취·원격 디스크 직접 재검의 미실행은 유지하며 #9 전체 N03를 종결하지 않습니다.
