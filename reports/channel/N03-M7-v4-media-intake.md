# N03-M7 / P1 — PC3의 v4 미디어 수신·재현

담당: pc3 LAPTOP-U2AL73UH / mcjun86-oss · 기존 이슈 #9 · 기준 main `b9a2a1888df66c755f1f6bef19d3d7e5f3028c0f`.

## 왜 지금

PC3 M6 수정본 `2c9f3e097064568203e7b95a8d3a0a662d944d36`은 메인이 인수했습니다. pc1의 실제 1080p 렌더 288프레임이 끝났고 M5 완주 검사, M6 실제 인코딩·전체 디코딩, 소비자 재검, 제품 등록까지 진행했습니다. [v4 Release](https://github.com/cjj0202-glitch/happycall-ralphthon/releases/tag/demo-media-20260922-v4)는 WAV 2개·MP4·좌표 JSON 1개를 제공합니다. WAV는 기존 v3 바이트이며 새 CLOVA 더빙 인수가 아닙니다.

메인의 다운로드 성공을 PC3 수신 성공으로 세지 않습니다. 이번 결과는 **PC3가 같은 4개 파일을 받고 해시·연결 계약을 재현한 증거 하나**입니다. 새 영상 제작·렌더·인코딩이나 제품 변경은 없습니다.

## 해줘야 할 일 · 소유

- 자신의 기존 checkout과 branch를 확인하고, fetch 후 위 기준의 manifest·수신 스크립트·관련 검사를 읽습니다. 기존 branch가 갈렸다면 강제로 main을 덮어쓰지 말고 안전한 통합 방법을 판단하고 회신합니다.
- 소유 쓰기는 ignored `apps/web/public/demo`의 승인된 미디어, `.local/demo-media-backups`, 새 `reports/pc3/v4-media-intake.md`뿐입니다. 제품 코드·공통 manifest·fixture·메인 원장·기존 보고서는 읽기 전용입니다.
- BMAD 관점은 사건/공정 연결, 재생·프레임 조작, 영상-좌표 바인딩, 실패 시 기존 파일 보존입니다. 작은 첫 결과는 수신 전 파일 상태와 기준 SHA 확인, 최종 결과는 4파일 실측입니다.
- 이미 실행 중인 PC3 화면이 있고 사용자 초안을 보존할 수 있으면 WMS CASE-0002 → W-W3 → 영상 → 프레임 전후 → 닫기만 관찰합니다. 화면이 없으면 `미실행`으로 남깁니다. 새 서버·브라우저 프로세스는 시작하지 않습니다.

## 실행 명령

PC3의 실제 저장소 루트에서 실행합니다. 경로를 pc1 경로로 바꾸거나 추정하지 않습니다.

```powershell
git rev-parse --show-toplevel
python -B channel/whoami.py
gh api user --jq .login
git status --short
git rev-parse HEAD
git fetch origin main
git show b9a2a1888df66c755f1f6bef19d3d7e5f3028c0f:data/demo-media-manifest.json
```

기준 파일들이 안전하게 반영된 것을 확인한 뒤 기존 수신기를 사용합니다.

```powershell
python -B scripts/fetch_demo_media.py --verify-only
python -B scripts/fetch_demo_media.py --upgrade-approved
python -B scripts/fetch_demo_media.py --verify-only
```

첫 검사는 구버전/없는 파일이면 실패할 수 있습니다. 성공으로 고쳐 기록하지 않습니다. 업그레이드는 기존 파일의 승인된 source 크기/SHA가 일치할 때만 교체하며 비공개 백업을 남깁니다. 새 tracks 자리에 다른 파일이 있으면 보존하고 중단합니다. 도구의 잠금·검사·백업을 삭제하거나 가드를 약화시키지 않습니다.

## 검증 방법 + 기대값

| 물리 파일 | bytes | SHA256 |
|---|---:|---|
| CASE-0001.wav | 2263278 | d4eeb6448ff8969f27034ecade9a050ee212468585c6300b19c9a0ebdc372931 |
| CASE-0002.wav | 2388044 | 6fe83afb8552765ab92722b838d2a0905f507551c4f98c58fa62a515033abaa0 |
| sorter-demo.mp4 | 991249 | 4a640c20e209bf5a43e26c3f1c5afeb41f4157af9017f04b4c3812b1990dca51 |
| sorter-demo.tracks.json | 158546 | b9b9f50295af799cfdf718b840b0cef703f57ad3e3b778557fcd9fdeb9ac681c |

이 표의 이름도 정본 manifest와 대조합니다. manifest 최상위 자산 3개와 MP4 아래 tracks 1개, 합계 물리 4파일입니다. 영상 1920×1080·24fps·12초·288프레임, CASE-0002/W-W3/SYN-CAM-02/CH-02/D-02이며 businessToteId는 null입니다. 시각 객체 ID를 업무 토트 ID나 귀책 판정으로 바꾸지 않습니다.

파일을 다시 읽어 직접 bytes/SHA를 계산하고 manifest 및 표와 비교합니다. 검사기의 자기 PASS만 옮기지 않습니다. 잘못된 해시·미등록 파일은 제품 위치를 훼손하지 않는 메모리/격리 대조에서 거절돼야 합니다. UI 관찰 시 +1/+1 연속 이동, 구간 끝에서 다음은 끝 유지, 뒤로 이동, 좌표 켜기/끄기, 닫기 포커스를 기록합니다. 전체 흐름·사람 청취·운영 CCTV 검증으로 확대하지 않습니다.

## 중단 조건 · 인계

수신 첫 결과 목표는 ACK 후 10분, 검토 가능한 보고는 20~30분입니다. 소유 충돌·인증 거부·낯선 기존 파일·잠금·새 비용이면 해당 동작을 중단하고 현재 파일을 보존합니다. API/CORS·Blob·TEST 정책 거부를 다른 PC에서 우회하지 않습니다.

보고서만 명시 경로 커밋·자기 branch push 후 원격 SHA를 대조합니다. #9에 신원/실제 경로/기준 및 결과 SHA/수신 전후 상태/4파일 실측/백업 경로/명령과 exit/관찰 및 미실행을 회신합니다. 메인이 이를 인수하기 전 원격 수신은 PENDING입니다.
