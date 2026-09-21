# 합성 데모 미디어 공유 준비

2026-09-21 17:03 KST / pc1 CJJ. **Release 발행 전 준비 결과**입니다. 이 작업에서는 업로드·커밋·push·유료 API 호출을 하지 않았습니다. 원격 Release의 실제 발행 여부와 다른 PC의 다운로드 성공은 메인 통합 작업에서 별도로 확인해야 합니다.

## 공유 계약

- 저장소: `cjj0202-glitch/happycall-ralphthon`
- 예정 태그: `demo-media-20260921`
- 정본: `data/demo-media-manifest.json`
- 다운로드 도구: `scripts/fetch_demo_media.py` (Python 3.11 이상, 다운로드 시 인증된 `gh` 필요)
- 수신 위치: `apps/web/public/demo`
- 3개 모두 독립 합성 시연 자산이며 실제 통화·CCTV·물류 실적의 증거가 아닙니다.

| 파일 | 바이트 | 길이 | SHA256 |
|---|---:|---:|---|
| CASE-0001.wav | 2,263,244 | 47.15초 | `1432d1b44b66d7edd53408811ab73ede98303555235b14b4587671a390a51b92` |
| CASE-0002.wav | 2,378,444 | 49.55초 | `f9fa70afaeb575876ab2dd18f1f395fbd38d6fec99b7cc0f70cb723650fb2e0c` |
| sorter-demo.mp4 | 1,097,133 | 12.00초 | `e6cad3cf9f999b596a0fef3e3d463170e0d279568a31a4be49366e5383908881` |

WAV 길이는 Python `wave`가 읽은 실제 PCM 바이트 수를 채널·샘플레이트·샘플폭으로 나누어 측정했습니다. 두 파일 모두 24,000Hz 모노입니다. MP4는 `imageio-ffmpeg`가 읽은 컨테이너 메타데이터로 960×540, 24fps, H.264, 12초를 확인했습니다. 이 PC의 PATH에는 `ffprobe`가 없어 독립 ffprobe 측정은 하지 않았습니다. 영상 전체 디코딩 검증은 별도 `reports/demo-video.md`에 있습니다.

## 다른 PC에서 실행

메인이 Release를 발행하고 이 manifest를 포함한 기준 커밋을 전달한 뒤 저장소 루트에서 실행합니다.

```powershell
python scripts/fetch_demo_media.py
python scripts/fetch_demo_media.py --verify-only
```

스크립트는 고정된 저장소·태그의 위 세 파일만 `gh release download --pattern <파일명>`으로 받습니다. 모든 다운로드를 목적지와 같은 볼륨의 임시 디렉터리에 저장한 뒤 **3개 모두 크기·SHA256 검증을 통과해야** 파일별 `os.replace`로 설치합니다. 파일 전체 집합의 트랜잭션은 아니며, 다운로드/검증 실패 시 설치를 시작하지 않습니다. 기존 파일이 일치하면 네트워크 요청 없이 건너뛰고, 기존 파일이 다르면 덮어쓰지 않고 명시적으로 실패합니다. 다른 파일로 교체하려는 경우 기존 파일의 보존 여부를 사람이 판단한 뒤 별도로 이동해야 합니다. 다운로더가 임의로 삭제하거나 유료 생성기로 대체하지 않습니다.

`--verify-only`는 네트워크·쓰기 없이 3개를 검사하며 누락 또는 불일치 시 종료코드 1입니다. 최초 다운로드에는 해당 저장소 접근 권한과 `gh` 인증이 필요합니다. Release 404/인증 실패는 준비 미완료로 보고하며 성공으로 대체하지 않습니다.

## 무네트워크 검증 실측

2026-09-21 17:03 KST, pc1 CJJ에서 실행했습니다.

```powershell
python scripts/fetch_demo_media.py --self-test
python scripts/fetch_demo_media.py --verify-only
python scripts/fetch_demo_media.py
```

- 자체 검증 **8/8 PASS**, `networkCalls: 0`: 3개 누락의 읽기 전용 탐지, 모의 다운로드 3개 설치, 동일 파일 재실행 시 다운로드 0·mtime 불변, **같은 크기의 1바이트 SHA 변이 거부 및 원본 보존**, 바이트 크기 경계 오류 거부, 세 번째 파일 손상 시 3개 모두 설치 안 됨, 다른 저장소/태그 거부, 허용 목록 밖 상대경로 거부를 실행했습니다.
- 실제 로컬 자산 검증 **3/3 일치**, `missing: []`, `downloaded: []`, 종료코드 0입니다.
- 실제 로컬 자산으로 기본 명령 재실행 시에도 **다운로드 0건**, 종료코드 0입니다. 원격 네트워크 다운로드 성공을 검증한 결과는 아닙니다.

남은 조치: 메인의 Release 발행·3개 자산 업로드 → 다른 PC의 다운로드·해시 검증 → 브라우저 재생 확인. 이 보고서의 준비 완료와 다른 PC 배포 완료를 구분합니다.
