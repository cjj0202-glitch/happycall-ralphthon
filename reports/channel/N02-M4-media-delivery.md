# N02-M4 / P1 — 최종 CCTV와 좌표 파일을 한 제품에 전달

## 결론
pc2 안영일 / MR-A83이 다운로드·배포 묶음·정적 전달 코드를 담당합니다. 더빙 대기 대신 실제 시스템 연결 작업을 진행합니다. 기존 M3 인수 범위는 보존합니다.

## 왜 지금
2026-09-21 사용자 중간점검 요청은 발표 PDF가 아니라 작동하는 통합 시스템입니다. 기준 main은 `663bbe5bb0ae0a780e328dce9a69188112de8d0e`, 기존 pc2 결과는 `d65a798b62395a1ec1ad6c02e118f2dc9a2f9409`입니다. 저장소는 `C:/Users/Administrator/Desktop/hackerton/happycall-ralphthon`입니다. 최종 새 영상은 아직 미등록이며 테스트에는 명시적 합성 입력만 사용합니다.

## 해줘야 할 일
- 소유권을 이번 카드에 한해 `scripts/fetch_demo_media.py`, `scripts/build_deployment_bundle.py`, `server/deployment_app.py`, 관련 `tests/test_demo_media_upgrade.py`, `tests/test_deployment_bundle.py`, `tests/test_deployment_app.py`, `reports/pc2/media-m4-*`로 확장합니다. 필요하면 `server/media_contract.py` 하나를 추가하고 bundle SOURCE_FILES에도 포함합니다. 다른 작업자 변경을 되돌리지 않습니다.
- frontend·fixture·실제 manifest·Release 등록은 메인 소유입니다. 현재 2 WAV + 1 MP4 구성을 유지하며 sorter-demo.mp4의 선택적 tracks 하나만 추가 지원합니다.
- 신뢰 정본은 `data/demo-media-manifest.json`의 MP4 항목입니다. `tracks={schemaVersion:'oneflow-cctv-tracks-v1', url:'/demo/sorter-demo.tracks.json', bytes:양의 정수(최대10000000), sha256:64자리소문자hex, videoSha256:부모MP4.sha256}`를 고정합니다. 케이스 데이터의 descriptor를 신뢰하지 않습니다.
- 다운로드→public→out→배포 묶음에 같은 파일을 SHA/크기/부모 영상 결합 확인 후 전달합니다. 등록이 없으면 기존3개만 유지하고 임의 demo JSON은 노출하지 않습니다. 등록됐으나 파일 누락·불일치면 실패합니다.
- 배포 서버는 패키지의 정본 manifest를 사용하여 정확한 sidecar 경로만 허용합니다. 테스트가 명시적으로 주입하는 합성 manifest도 동일 검증을 통과해야 합니다. 기존 생성자 호출의 호환을 보존하고 manifest 없는 기본 상태는 sidecar 미허용입니다.
- MP4 교체도 현재 WAV처럼 sourceBytes/sourceSha256 일치·원본 백업을 요구합니다. 현재 Release 태그와 `demo-media-20260922-v4`만 명시 허용하고 실제 다운로드/등록은 이번에 실행하지 않습니다.
- BMAD의 사용자 행동·상태·계약·검증을 짧게 설계한 뒤 정상 선택적 sidecar 전달 한 건을 먼저 구현하고 반례를 추가합니다. 이 카드는 새 음원 제작이나 자연스러움 검수가 아닙니다.

## 실행 명령
본인 저장소에서 `python channel/whoami.py`, `git status --short`, `git fetch origin`, 고정 main과 기존 브랜치 차이를 확인합니다. 기존 변경을 보존하고 위 소유 파일만 수정합니다. 관련 Python unittest/pytest와 서버 소켓 없는 ASGITransport 검사를 실행합니다. 자기 브랜치 명시 경로 커밋·push 후 원격 SHA를 대조합니다.

## 검증 방법 + 기대값
정상 기존3개/정상3개+sidecar, 잘못된 schema/크기/SHA/영상결합, 미등록·추가 JSON, 누락, 경로이탈·symlink, MP4 원본 불일치, 중간 실패 시 원본 보존을 검사합니다. public/out/패키지 바이트 동일을 확인합니다. 첫 작은 결과는 착수 후20분, 검토 가능한 코드 결과는40분을 목표로 하되 실제 시각을 보고합니다. 실행 분모·실패·수정·재검·미실행을 구분합니다.

## 중단 조건 + 인계
새 브라우저·서버·소켓 기동, 설치·과금·실제 다운로드·Release·배포·키 읽기는 없습니다. 메인의 정책 거부 작업을 다른 PC에서 우회하는 카드가 아닙니다. 권한/소유 충돌은 해당 작업을 멈추고 독립 작업만 진행합니다. #8에 ACK, 기준/결과 SHA, 파일 목록, 명령·기대/실측, 실패와 수정, 메인 연결점을 회신하세요. N02 전체 완료나 최종 자산 등록을 선언하지 않습니다.
