# 승인 음성 파일 업그레이드

2026-09-21 pc1(CJJ). 설계: `--upgrade-approved`를 명시한 경우에만 manifest의 `sourceBytes`·`sourceSha256`과 정확히 같은 기존 두 WAV를 v2로 교체합니다. 일반 다운로드는 다른 기존 파일을 계속 보존·거부합니다. MP4는 승인 교체 대상이 아닙니다.

다운로드 전체를 임시 폴더에서 검증한 다음 기존 승인 파일을 `.local/demo-media-backups/<고유 실행 ID>/`에 바이트 그대로 보존합니다. 백업은 `public/demo` 밖에 둡니다. 모든 원본을 재확인하고 파일별 교체하며, 최종 경로에 경쟁 파일이 나타나면 덮어쓰지 않습니다. 링크·junction·알 수 없는 원본은 거부합니다. 중간 실패는 이미 바뀐 v2와 남은 승인 v1의 혼합 상태일 수 있으므로 완료로 보고하지 않고, 같은 명령의 재시도로 남은 파일만 처리합니다. 실행 기록과 백업은 실패해도 보존합니다.

## 실행 결과

- 구현: `scripts/fetch_demo_media.py`, 격리 검증: `tests/test_demo_media_upgrade.py`.
- pc1/CJJ, Python 3.12.14, 2026-09-21. `.venv/Scripts/python.exe -m pytest tests/test_demo_media_upgrade.py -q -rs` → **35 PASS / 1 SKIP**. 실행 시간 1.86초.
- SKIP은 Windows 실제 symlink 생성 권한 부족(WinError 1314)입니다. 실제 hardlink 거부는 실행했고, junction/reparse 속성과 링크 부모 거부는 주입 테스트로 확인했습니다. 실제 junction을 생성해 시험한 것은 아닙니다.
- `python scripts/fetch_demo_media.py --self-test` → 기존 8개 검증 PASS, 네트워크 0회.
- `python scripts/fetch_demo_media.py --verify-only` → 현재 v2 WAV 2개·MP4 1개 **3/3 bytes·SHA256 일치**, missing 0, downloaded 0. 이는 메인이 앞서 설치한 파일의 읽기 검증입니다.
- 알 수 없는 원본은 다운로드 전에 거부됩니다. 같은 크기의 손상 다운로드도 첫 교체 전에 거부됩니다. 원본 다운로드 중 변경, 캡처 직전 변경, 최종 경로 경쟁 파일, staging 변경을 주입해 다른 작업자의 바이트를 덮어쓰지 않는 것을 확인했습니다.
- 두 번째 WAV 게시 실패 주입 시 첫 번째 v2는 유지되고 두 번째 v1은 복원됩니다. 다시 실행하면 두 번째만 업데이트하며 최초 백업도 남습니다.
- 4개 메모리상 변이(원본 승인 가드 제거, 선행 다운로드 검증 제거, Windows rename을 overwrite로 변경, 승인 WAV를 과도하게 거부)를 실행했습니다. 각각 다운로드 0회·백업 생성 순서·경쟁 바이트 보존·정상 성공의 수용 판정을 깨는 것을 관측했습니다. 소스 파일을 변이한 채 저장하지 않았습니다.
- 최초 변이 테스트는 변경할 문자열이 기본 다운로드/업그레이드 두 곳에 있어 1건 실패했습니다. 업그레이드 루프를 포함한 유일 앵커로 수정한 뒤 동일 검사와 추가 경계 검사를 재실행한 결과가 위 35 PASS / 1 SKIP입니다.

이 작업에서 실제 Release 다운로드, API/과금 호출, 공유 public 파일 교체, Git commit/push는 실행하지 않았습니다. manifest의 `sourceBytes` 추가 및 v2 Release 발행은 메인 작업입니다.

## 다른 PC에서 사용할 명령

본인의 저장소 루트에서 최신 코드와 `data/demo-media-manifest.json`을 받은 후 실행합니다. GitHub CLI에 저장소 읽기 권한이 있어야 합니다.

```powershell
python scripts/fetch_demo_media.py --upgrade-approved
python scripts/fetch_demo_media.py --verify-only
```

- v1 원본인 두 WAV만 백업 후 교체합니다. 승인 v1 크기는 CASE-0001 2,263,244 B, CASE-0002 2,378,444 B이며 실제 허용 SHA256은 manifest가 정본입니다. 파일명/크기만 같아도 SHA256이 다르면 보존·실패합니다.
- 이미 v2이면 다운로드·수정하지 않습니다. 없는 자산은 검증 후 설치합니다. MP4는 기존 정확한 v2 파일을 유지하거나 없을 때 설치하며 기존 불일치 파일을 교체하지 않습니다.
- 명령 결과의 `backupDirectory`에 실행별 `result.json`, 바이트 원본, 다운로드 파일, 캡처 파일이 남습니다. `.local/demo-media-backups/`는 Git/웹 배포에 포함하지 않습니다. 임시 디스크 공간은 최대 원본·다운로드·캡처 복사본을 포함하므로 자산 용량의 약 3배 여유를 둡니다.
- 일반 명령 `python scripts/fetch_demo_media.py`는 기존 v1도 덮어쓰지 않고 오류로 안내합니다. 업그레이드 옵션을 붙이지 않은 동작을 자동 승인으로 확대하지 않았습니다.

## 실패와 복구

1. 정상적인 예외는 `result.json`에 `failed`와 이미 설치한 파일을 기록하고 lock을 해제합니다. 원래 파일을 캡처한 직후 실패하면 최종 경로가 비어 있을 때만 원래 바이트를 복원합니다. 경쟁 파일이 생겼다면 그것을 유지하고 원래 바이트는 백업/캡처에 보존합니다.
2. v1/v2 혼합 상태이고 다른 파일이 생기지 않았다면 같은 `--upgrade-approved` 명령을 다시 실행합니다. 새 실행 폴더를 사용하며 이전 실패 기록·백업은 삭제하지 않습니다.
3. 알 수 없는 파일·링크 또는 경쟁 파일이 있으면 자동으로 복원하거나 덮어쓰지 않습니다. 해당 파일과 출력된 백업의 크기·SHA256을 대조하고 파일 작성 주체와 경로를 확인해야 합니다. 이 도구에는 강제 덮어쓰기/강제 롤백 옵션이 없습니다.
4. 강제 종료/전원 중단이면 `.local/demo-media-backups/.upgrade.lock/owner.json`이 남을 수 있습니다. 기록된 PID가 실제로 끝났고 해당 실행이 중단된 것을 확인한 뒤 그 lock의 `owner.json`과 빈 lock 디렉터리만 정리합니다. 원본 백업/실패 실행 폴더를 재귀 삭제하지 않습니다. 최종 경로가 비었어도 승인된 Release 자산을 다시 받는 재시도가 가능합니다.

파일별 게시는 원자적이지만 두 WAV 전체를 한 번에 교체하는 트랜잭션은 아닙니다. 업그레이드 중에는 생성기나 다른 파일 작성자를 동시에 실행하지 않는 것이 전제입니다. lock은 같은 도구의 중복 실행을 막고, 경쟁 변경 검사와 덮어쓰지 않는 게시는 관측한 경쟁 파일을 보존하지만 관리자 권한의 적대적 파일시스템 조작 전체를 격리하는 보안 경계는 아닙니다. Windows에서 파일을 다른 프로세스가 잠그거나 백업·대상 볼륨이 다르면 실패할 수 있으며 실제 원본과 기록을 보존한 채 원인을 확인합니다.
