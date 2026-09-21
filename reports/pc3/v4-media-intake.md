# N03-M7 — PC3 v4 미디어 독립 수신 결과

2026-09-22 KST. PC3에서 `demo-media-20260922-v4`의 물리 파일 **4/4**를 실제 수신·해시 검증했다. 기존 CASE1은 보존했고, CASE2·영상·tracks **3개를 다운로드**, 기존 CASE2·영상 **2개를 백업 후 교체**했다. 수신 후 검증은 exit 0, 음성·영상·tracks의 bytes/SHA가 배정 표와 모두 일치한다. 거절 동작은 **10/10**, 별도 읽기 전용 검토는 **43/43** 통과했다. 분모가 다른 결과이므로 합산하지 않는다.

기존 해피콜 UI가 없어 UI 동작은 **미실행**이다. 이 보고는 원격 PC3의 수신·바이트·구조·사건 연결 증거이며 사람 청취, 영상 시각 품질, 새 더빙, 전체 N03, TEST, 배포의 인수 증거가 아니다. M7 최종 인수는 pc1 검토 대기다.

## 신원과 고정 기준

- 배정: [pc1 M7 댓글](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/9#issuecomment-5764649956), 작성자 `cjj0202-glitch`.
- ACK: [PC3 착수 댓글](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/9#issuecomment-5764696022), 02:27:35 KST.
- 실제 `hostname`: `LAPTOP-U2AL73UH`; `channel/whoami.py`: pc3 / logistics-review; `gh api user`: `mcjun86-oss` (02:35:46 KST 재확인).
- 실제 저장소: `D:\hwana\Work\happycall-ralphthon`; 키트: `D:\hwana\Work\hackathon-ai-kit`.
- 작업 branch: `work/pc3-n03-wms-scenes`; 시작 HEAD: `2c9f3e097064568203e7b95a8d3a0a662d944d36`.
- 수신 계약 기준: `b9a2a1888df66c755f1f6bef19d3d7e5f3028c0f`.
- 실제 Release: [demo-media-20260922-v4](https://github.com/cjj0202-glitch/happycall-ralphthon/releases/tag/demo-media-20260922-v4).
- 쓰기 범위: 승인된 ignored `apps/web/public/demo`, 비공개 `.local/demo-media-backups`, 로컬 처리 상태, 이 보고서. tracked 코드·공통 manifest·fixture·중앙 작업표는 수정하지 않았다.

현재 branch와 수신 기준의 고유 커밋 수는 각각 14/69였다. main으로 전환하거나 pull/merge하지 않았다. 현재 checkout의 구 수신기와 manifest에는 v4 계약이 없으므로, 기준 커밋의 원본 Git blob을 비공개 경로에 추출하고 **기준 수신기의 기존 API**를 호출했다. 현재 checkout에서 문자 그대로 `python scripts/fetch_demo_media.py ...`를 실행했다고 주장하지 않는다.

## 실제 실행과 파일 보존

아래 명령은 저장소 루트에서 실제 실행했다. 로컬 runner는 원본 수신기와 의존 계약을 격리 import하고 매번 4개 원본 blob의 SHA를 확인한다. 원본 함수·검사·잠금·백업 가드는 수정하지 않았다.

```powershell
python -B .local/demo-media-backups/pc3-m7-b9a2a188/receive.py before
python -B .local/demo-media-backups/pc3-m7-b9a2a188/receive.py upgrade
python -B .local/demo-media-backups/pc3-m7-b9a2a188/receive.py after
```

| 실행 | KST 시작–종료 | 기대 | 실제 |
| --- | --- | --- | --- |
| before / verify only | 02:29:30–02:29:31 | 구 CASE2 불일치 거절, 기존 파일 보존 | exit **1**, `Existing asset differs; preserved without overwrite: ...\CASE-0002.wav`; 기존 3파일 전후 동일, tracks 없음 |
| upgrade / approved | 02:29:45–02:29:49 | 승인 source만 교체, 백업, 물리 4파일 확보 | exit **0**, verified 4 / missing 0 / downloaded 3 / upgraded 2 |
| after / verify only | 02:30:02–02:30:03 | 4파일 일치, 추가 다운로드 없음 | exit **0**, verified 4 / missing 0 / downloaded 0, 전후 동일 |

첫 수신은 ACK 후 약 2분 14초에 완료했다. CASE1은 바이트·SHA·mtime가 보존되었다(`mtime_ns=1789983253688824000`). before 실패는 예정된 구 버전 거절이며 성공으로 바꾸어 기록하지 않았다.

실제 API 인자는 다음과 같다. `ROOT`는 **실제 저장소**이고 `release_tag`는 **명시적으로 v4**다. 기준 의존 계약의 기본 tag 값이 v3이므로 기본값에 의존하지 않았다.

```python
media.ROOT = ROOT
assets = media.validate_manifest(manifest)
media.fetch(
    assets, ROOT / "apps/web/public/demo",
    verify_only=(mode != "upgrade"),
    upgrade_approved=(mode == "upgrade"),
    backup_root=ROOT / ".local/demo-media-backups",
    release_tag=manifest["releaseTag"],
)
```

수신기는 실제로 `gh release download`를 사용했다. 필요한 다운로드의 해시를 검증한 뒤 교체했고, 백업과 captured 원본을 보존했다. 수신용 잠금은 정상 종료로 해제되었으며 강제 해제하지 않았다.

### 수신 후 기대값 = 실측값

상위 manifest 자산은 3개이며 영상의 nested tracks를 포함한 **물리 파일은 4개**다. 임의의 네 번째 top-level 자산을 허용한 것이 아니다.

| 파일 | bytes (기대=실측) | SHA256 (기대=실측) | 조치 |
| --- | ---: | --- | --- |
| CASE-0001.wav | 2263278 | `d4eeb6448ff8969f27034ecade9a050ee212468585c6300b19c9a0ebdc372931` | 기존 일치 파일 보존 |
| CASE-0002.wav | 2388044 | `6fe83afb8552765ab92722b838d2a0905f507551c4f98c58fa62a515033abaa0` | 다운로드·승인 교체 |
| sorter-demo.mp4 | 991249 | `4a640c20e209bf5a43e26c3f1c5afeb41f4157af9017f04b4c3812b1990dca51` | 다운로드·승인 교체 |
| sorter-demo.tracks.json | 158546 | `b9b9f50295af799cfdf718b840b0cef703f57ad3e3b778557fcd9fdeb9ac681c` | 다운로드·신규 수신 |

### 교체 전 원본과 실제 백업

백업 디렉터리: `D:\hwana\Work\happycall-ralphthon\.local\demo-media-backups\20260921T172945Z-gm28yeoy`.

| 원본 | bytes | SHA256 |
| --- | ---: | --- |
| CASE-0002.wav | 2378478 | `333897f4f10426674ec97b9e3a44c2f8da21f1f7931b4f911c82a29abcf6b914` |
| sorter-demo.mp4 | 1097133 | `e6cad3cf9f999b596a0fef3e3d463170e0d279568a31a4be49366e5383908881` |

두 파일 모두 manifest의 승인 source bytes/SHA에 일치했다. 백업 2개와 각 `.captured` 2개의 해시는 수신 전 원본과 **4/4** 동일하다. 백업 `result.json`은 `status=complete`, v4 tag, 실제 destination, installed 3개, backups 2개를 기록한다. 미등록 기존 tracks는 없었다.

## 거절 동작과 구조·연결 검증

`python -B .local/demo-media-backups/pc3-m7-b9a2a188/negative-checks.py`: 02:31:32 KST, 실제 exit **0**, **10/10 PASS**. 아래 테스트는 메모리의 계약 사본과 비공개 격리 fixture에서 실행했다. 다운로드 함수를 호출 시 실패하도록 주입했고 호출은 **0회**였다. public 4파일은 전후 bytes/SHA/mtime 동일, 기준 원본 4blob도 보존되었다.

| 입력 | 수 | 실제 거절 |
| --- | ---: | --- |
| 각 실제 자산을 잘못된 SHA로 검증 | 4 | `verify=False` |
| 부모에 미등록인 평탄화 tracks | 1 | `Flattened tracks must exactly match the parent descriptor` |
| 임의 네 번째 top-level 자산 | 1 | `INVALID_MEDIA_ASSETS` |
| `../escape.wav` | 1 | `INVALID_MEDIA_ASSET` |
| tracks descriptor의 잘못된 video SHA | 1 | `INVALID_TRACKS_DESCRIPTOR` |
| 격리 목적지의 미등록 기존 tracks | 1 | `No approved source bytes/SHA256 for upgrade: sorter-demo.tracks.json`; 원본 보존, 다운로드·백업 생성 없음 |
| 길이는 같지만 바이트를 변경한 tracks 사본 | 1 | `verify=False` |

동일 PC3의 별도 보조 에이전트가 읽기 전용으로 **43/43** 검토했다(02:33:35–02:33:36 KST, exit 0). 이는 추가 물리 PC의 실적이 아니다. 자산 SHA·배정 표·원본 Git blob·백업·fixture·tracks 및 기존 순수 파서의 결과를 대조했다.

- MP4 순수 컨테이너 파서: `avc1`, video track 1, **1920×1080 / 24fps / 12초 / 288 samples**, faststart, 항등 표시행렬. 이는 실제 전체 디코딩 프레임 수나 시각 품질 판정이 아니다.
- tracks: **288행**, frame 1..288 연속, elapsed 0..11.958333333333334초, 마지막 프레임 종료 12초. approach 72 / branch 72 / chute 96 / settle 48. 기존 `_tracks` 순수 validator의 고정 경로·yaw·phase·정규화 projected bbox·접촉·카메라·사건 검사 통과.
- descriptor 5필드(`schemaVersion/url/bytes/sha256/videoSha256`)가 manifest와 수신 bytes/SHA/video SHA에 일치한다. 기준 fixture의 media·event·camera 연결도 별도로 대조했다. 기준 `cases.json`의 media 항목 자체에 tracks descriptor 5필드가 있다는 뜻은 아니다.
- `CASE-0002 / W-W3 / SYN-CAM-02 / CH-02 / D-02`, 사건 시각 `2026-09-18T02:33:00+09:00` 일치. 영상 elapsed clock과 사건 시각은 분리된다.
- `businessToteId=null`, visual ID `SYN-VIS-PARCEL02`. fixture의 피킹 `SYN-TOTE02-A`와 출하 `SYN-TOTE02-B`는 서로 구분되어 있고 visual ID를 업무 토트로 결합하지 않았다.
- `synthetic=true`, `source=synthetic-scene-ground-truth`, `occlusionTested=false`. 투영 좌표를 실제 AI 탐지·실제 CCTV·실제 업무 추적·귀책 증거로 인정하지 않는다.

## 재현과 로컬 증거

실제 로컬 증거 폴더: `D:\hwana\Work\happycall-ralphthon\.local\demo-media-backups\pc3-m7-b9a2a188`.

`source-manifest.json`, `receive.py`, `before.json`, `upgrade.json`, `after.json`, `negative-checks.py`, `negative-checks.json`, `independent-audit.json`을 보존했다. 이 원본 로컬 파일과 이진 자산은 Git에 넣지 않는다. 아래 고정 기준 원본 4파일은 추출본과 Git blob이 4/4 일치한다.

| 기준 경로 | bytes | SHA256 |
| --- | ---: | --- |
| scripts/fetch_demo_media.py | 19351 | `83bc82d4a0c4cce01e71f81aa825293884aec8f79f95a69c139f147601d84845` |
| server/__init__.py | 63 | `b4c4a62ab2ea460cda3dddadcda2d33254eab2c0c91541ae38b4134014f9bdac` |
| server/media_contract.py | 3890 | `369ed3cd8cf0bd4a1109bc493638f9d071f53844fcbb6c035777bd97dc8b86a9` |
| data/demo-media-manifest.json | 3516 | `d6b6423283ef6f429080e88790a01a81eda8cdd2ca6e856116cd940c6933a346` |

PC3에서 재확인할 때는 위 실제 명령의 **after만** 실행한다. before는 수신 전 상태를 요구하고 upgrade는 이미 완료한 변경이므로 반복하지 않는다. 다른 검토자가 같은 기준 API의 수신 후 검증을 재현하려면 저장소 루트의 새 Python 프로세스에서 다음을 실행한다. 이 예제는 새 비공개 디렉터리에 원본을 추출하고 공개 파일을 읽어 검증하며, 업그레이드·다운로드는 하지 않는다. 공개 파일이 없다면 missing을 성공으로 보지 않는다.

```python
import hashlib, importlib.util, json, pathlib, subprocess, sys, tempfile
ROOT = pathlib.Path(r"D:\hwana\Work\happycall-ralphthon").resolve()
REF = "b9a2a1888df66c755f1f6bef19d3d7e5f3028c0f"
pins = {
    "scripts/fetch_demo_media.py": "83bc82d4a0c4cce01e71f81aa825293884aec8f79f95a69c139f147601d84845",
    "server/__init__.py": "b4c4a62ab2ea460cda3dddadcda2d33254eab2c0c91541ae38b4134014f9bdac",
    "server/media_contract.py": "369ed3cd8cf0bd4a1109bc493638f9d071f53844fcbb6c035777bd97dc8b86a9",
    "data/demo-media-manifest.json": "d6b6423283ef6f429080e88790a01a81eda8cdd2ca6e856116cd940c6933a346",
}
private = ROOT / ".local/demo-media-backups"
private.mkdir(parents=True, exist_ok=True)
source = pathlib.Path(tempfile.mkdtemp(prefix="m7-review-", dir=private))
for name, sha in pins.items():
    blob = subprocess.run(["git", "show", f"{REF}:{name}"], cwd=ROOT,
                          check=True, capture_output=True).stdout
    assert hashlib.sha256(blob).hexdigest() == sha
    path = source / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob)
assert "server" not in sys.modules
sys.dont_write_bytecode = True
sys.path.insert(0, str(source))
spec = importlib.util.spec_from_file_location("m7_receiver", source / "scripts/fetch_demo_media.py")
media = importlib.util.module_from_spec(spec)
spec.loader.exec_module(media)
import server.media_contract as contract
assert pathlib.Path(contract.__file__).resolve() == source / "server/media_contract.py"
media.ROOT = ROOT
manifest = json.loads((source / "data/demo-media-manifest.json").read_text(encoding="utf-8"))
assert manifest["releaseTag"] == "demo-media-20260922-v4"
assets = media.validate_manifest(manifest)
assert len(assets) == 4
result = media.fetch(assets, ROOT / "apps/web/public/demo", verify_only=True,
                     upgrade_approved=False, backup_root=private,
                     release_tag=manifest["releaseTag"])
print(json.dumps(result, ensure_ascii=False, indent=2))
assert len(result["verified"]) == 4 and not result["missing"]
```

위 재현 예제는 02:38:50 KST에 실제 새 Python 프로세스에서 실행해 **exit 0 / verified 4 / missing 0 / downloaded 0**을 확인했다. public 4파일의 bytes/SHA/mtime는 전후 동일했다. 실행 기록은 같은 로컬 폴더의 `report-reproduction.json`이며 예제 코드 SHA256은 `ae37037bf6c070566ccf23122e3cdcdbdd0137e4294af7bcd56a15ca642d39e7`이다.

## 미실행과 인수 경계

02:30–02:31 KST의 computer-use 표면 목록에는 해피콜 화면이 없었다(노출된 탭은 ChatGPT Learn 원격 연결 문서 1개, apps 0개). 02:32:04 KST에 로컬 3000/3100/8100 listen도 관측되지 않았다. 따라서 CASE2 → W-W3 → 영상, frame +1/+1, 끝 clamp, 뒤로, overlay toggle, 닫기 후 focus는 **모두 미실행**이다. 새 서버·브라우저를 시작하지 않았다.

본 M7 실행에서 새 render/encode/full decode는 **각 0회**다. 컨테이너 samples와 JSON 행만으로 프레임 디코딩·영상 품질을 대신하지 않는다. 실제 full render/encode/decode 및 제품 등록 완료는 배정 댓글의 **pc1 보고 사실**로 구분하며 PC3 실행 실적으로 합산하지 않는다.

WAV는 pc1이 공지한 기존 v3 바이트의 재사용이다. 바이트 계약만 검증했으며 신규 CLOVA 더빙, 사람 청취, 음성 내용 품질을 새로 인수하지 않았다. TEST는 별도 미완료를 유지한다. pc1 M7 검토·N03 전체·최종 제품/시연/배포 판정은 이 보고로 자동 완료하지 않는다.
