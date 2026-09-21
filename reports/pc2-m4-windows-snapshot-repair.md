# PC2 M4 Windows snapshot 인수 보정

## 범위와 기대값 (수정 전 고정)

- 원격 후보 `ceec704755c3558be03be72938b6cb369bbb1d3b`의 17파일이 메인 작업 트리에 반영된 뒤 발견한 Windows 호환성 결함입니다. 이 보정은 `server/deployment_app.py`의 `_read_regular_snapshot`, `tests/test_deployment_app.py`, 이 보고서만 소유합니다. 원격 17파일 중 앞의 코드·테스트 2파일은 이후 메인 인수 보정본이며 원격 원바이트와 같다고 주장하지 않습니다.
- 공통 서명 `dev/ino/size/mtime_ns/nlink`와 제공되는 `birthtime_ns`는 경로 읽기 전, 열린 핸들 읽기 전·후, 경로 읽기 후의 네 관측에서 같아야 합니다.
- `ctime_ns`는 경로 조회 전·후끼리, 핸들 조회 전·후끼리 각각 같아야 합니다. 서로 다른 조회 방식의 고정된 `ctime` 차이만 허용하며 시간 변화 거부를 삭제하지 않습니다.
- 기대값: Windows 형태의 안정된 경로/핸들 `ctime` 차이는 원본 바이트 반환, 같은 조회 방식의 `ctime` 변화는 `None`, 공통 서명의 변화도 `None`. `birthtime_ns` 없는 Unix 형태도 안정 시 반환·변화 시 거부합니다.
- NS stat 관측을 주입하여 생성/쓰기 타이밍에 의존하지 않는 회귀 검사를 먼저 고정합니다. 인증·등록·해시·링크·크기·응답 계약, 기존 fixture의 미디어 등록 정책은 바꾸지 않습니다.

## 수정 전 실측

- 기존 `.venv` Python 3.12.14, Windows 11 10.0.26200에서 제품 함수를 수정하지 않고 `sys.settrace`로 실제 반환 시점의 `before/opened/after/now`를 관찰했습니다. 기존 M4 합성 fixture를 10번 생성하여 router 초기화 4 PASS / 6 MEDIA_ERROR를 재현했습니다.
- 실패 6건은 모두 `ctime_ns`만 달랐습니다. 경로 `before == now`, 핸들 `opened == after`였고 `dev/ino/size/mtime_ns/nlink/birthtime_ns`는 네 관측 모두 같았습니다.
- 결정적 실파일 대조: 빈 임시 파일 생성 → 30ms 후 합성 28바이트 기록 → mtime을 2000-01-01로 고정 → 변경 없이 5번 읽었습니다. 모두 `None`이고 바이트 SHA-256은 불변이었습니다. 경로·핸들 관측은 각각 다섯 번 내내 안정적이었습니다.

| 필드 | before / now (경로) | opened / after (핸들) |
|---|---:|---:|
| dev | 11422984143271060885 | 11422984143271060885 |
| ino | 2814749767916934 | 2814749767916934 |
| size | 28 | 28 |
| mtime_ns | 946684800000000000 | 946684800000000000 |
| ctime_ns | 1790001963719936900 | 1790001963751021800 |
| nlink | 1 | 1 |
| birthtime_ns | 1790001963719936900 | 1790001963719936900 |

이는 이 로컬 Python/Windows의 두 조회 방식이 반환하는 `ctime` 차이입니다. 읽는 동안 파일이 바뀌었다는 근거는 없으며 모든 OS/버전의 동일 동작을 주장하지 않습니다.

## 보정과 검증 결과

원격 후보 대비 제품 변경은 `_read_regular_snapshot` 한 함수의 비교 부분뿐입니다. 교차 비교에 `birthtime_ns`(없으면 `None`)를 넣고, `ctime`은 같은 조회 방식의 전후 비교로 분리했습니다. 반환 바이트·해시 검증·경로/하드링크 검사·최대 크기·미디어 등록 정책·fixture는 유지했습니다.

| 실행 | 실측 |
|---|---|
| `.venv/Scripts/python.exe -m pytest tests/test_deployment_app.py -k 'snapshot_' -q` (제품 수정 전, 최초 14개) | **1 failed / 13 passed / 142 deselected**. 실패는 안정된 Windows `ctime` 차이를 가진 정상 사례였습니다. |
| 같은 명령 (제품 수정 후, 변이 검사 2개 추가) | **16 passed / 142 deselected**, 6.79s |
| `.venv/Scripts/python.exe reports/pc2/media-m4-server-checks.py` | **23/23 PASS**, 1.539s. 초기 실패한 03/04/12/13/15/16/17/19/21도 모두 PASS |
| `.venv/Scripts/python.exe -m pytest tests/test_deployment_app.py -q` | **155 passed / 3 skipped / 0 failed / 0 errors**, 전체 158개, 9.98s |
| 위의 실제 Windows 28바이트 재현을 수정 후 새 임시 파일로 반복 | **5/5 원본 바이트 반환**, 파일 바이트 불변 |
| `git diff --check -- server/deployment_app.py tests/test_deployment_app.py reports/pc2-m4-windows-snapshot-repair.md` | exit 0 |

새 16개는 안정된 조회 제공자 3종(Windows 차이/동일 값/birthtime 없는 Unix 형태), 두 제공자의 ctime 변화 4종, 공통 필드 변화 6종, birthtime 제공 여부 변화 1종, ctime 가드 삭제 변이 2종입니다. NS 검사는 경로·핸들 관측이 각각 2번 호출됨을 센 후 실제 임시 파일을 읽습니다. 관측 주입 검사에서는 `_regular_file`만 고정하며 기존 ASGI 검사에서 실제 링크·하드링크·open 교체·검증 후 바이트 불변·인증을 별도로 검사합니다. ctime 변이는 정상 바이트 반환 대조군부터 확인한 뒤 각 가드를 하나씩 없앤 메모리 사본이 잘못 허용하는 것을 실제로 잡았습니다.

기존 배포 앱의 실제 Windows 심볼릭 링크 생성 권한이 필요한 세 검사는 skip입니다(코드의 유일한 skip 지점은 `physical_symlink`의 winerror 1314 처리). Unix 형태는 NS 주입 검사이며 Unix 호스트 실행을 뜻하지 않습니다. 기존 의존성 deprecation warning 5개는 남습니다. 서버·외부 소켓·브라우저·설치·API·키·커밋·렌더 PID 13052 조작은 수행하지 않았습니다.

메인이 수정 전에 시작한 초기 3모듈 pytest는 `8 failed / 155 passed / 2 skipped / 86 errors`로 별도 실행이며 이 보정본의 결과가 아닙니다. 이번 담당자의 최종 전체 검사는 `test_deployment_app.py` 1모듈과 ASGI 23개입니다. 다른 모듈의 새 실행 결과는 메인의 인수 근거에 따릅니다.

## 독립 재검과 동결

- 원격 후보 대비 추가 변경 확인: `git diff ceec704755c3558be03be72938b6cb369bbb1d3b -- server/deployment_app.py tests/test_deployment_app.py`.
- 코드 SHA-256: `d900b54a61fc769c7ee05f5f4f04cd2820e73956b1114a837a47e1cc16d73fbd`.
- 테스트 SHA-256: `6873b97d61fb6bb63cb902cfe3bef3529562d79ddb02039a99734eb5154e5a52`.
- 위 실행을 마친 소유 3파일은 독립 인수 검증을 위해 동결합니다. 기존 원격 보고서 10개는 덮어쓰지 않았습니다.
