# 알림 상태 포함 생산 빌드와 새 로컬 배포 묶음

2026-09-22 · pc1/CJJ · 고정 소스 `d79752aafcf60c1d9f712cb6eb4d9e8cad5d944c`

생산 빌드 1회와 새 묶음 생성 1회가 완료됐고 실제 실행 세션 `68266`은 **exit 0**으로 종료했습니다. 출력 **27개 / 6,880,635 bytes**, 묶음 payload **60개 / 12,954,352 bytes**를 재대조했습니다. marker 포함 전체는 **61개 / 12,963,099 bytes**이며 누락·추가·크기·SHA 차이는 모두 0개입니다. `server/notifications.py`와 v4 미디어 4종도 동일합니다.

새 묶음: `C:/00.프로젝트/happycall-ralphthon/dist/deployment/20260921T174714439133Z-d79752aafcf6`

| 함수 호출 직전 KST | 가용 물리 RAM bytes | 기준 bytes | 실행 |
|---|---:|---:|---|
| 02:46:56.531026 | 3,105,771,520 | 1,610,612,736 | run_build 1회 |
| 02:47:14.438134 | 3,097,948,160 | 1,610,612,736 | build_bundle 1회 |

기존 `reports/media/full1080-production-build.md` 절차와 변경하지 않은 `scripts.build_deployment_bundle.run_build`·`build_bundle`를 사용했습니다. 각 호출 직전에 Windows `GlobalMemoryStatusEx.ullAvailPhys`가 1,610,612,736 bytes 이상인지 검사했습니다. 실패 시 재시도하지 않습니다.

쓰기 범위는 ignored `apps/web/.next`·`apps/web/out`, 새 `dist/deployment` 하위 묶음, 이 보고서입니다. 소스·`.next-dev`·기존 묶음·원장·키를 수정하지 않았습니다. 새 서버·브라우저·API 재시작·배포·실모델 호출·설치를 수행하지 않았습니다. PowerShell `try/finally`로 PATH를 복원하며, 실제 npm 선택과 래퍼의 sibling Node를 확인했습니다. 빌드 자식은 기존 도구의 허용 목록 환경과 고정 production 옵션을 유지합니다. 환경값은 출력하지 않고 키 목록만 기록합니다.

SOURCE_FILES·TEMPLATES·FRONTEND_DATA_FILES·apps/web·builder를 고정 커밋과 대조합니다. 이번 검사에서는 next-env.d.ts도 제외하지 않았습니다. HEAD가 문서 커밋 등으로 이동해도 payload 차이가 없으면 고정 revision을 유지합니다. 소스 지문은 빌드 전·후·묶음 후 각각 측정합니다.

실제 출력 및 묶음 payload 파일을 다시 읽어 경로·bytes·SHA256을 marker와 대조합니다. inventory 해시는 경로순 `{path,size,sha256}` 목록을 `ensure_ascii=False, sort_keys=True, separators=(",",":")` JSON과 마지막 LF로 직렬화한 SHA256입니다. marker는 payload에서 제외됩니다. 미디어 4개는 public/out/bundle-public/bundle-out 4위치에서 대조하고 server/notifications.py의 원본·묶음·marker 일치를 별도 확인합니다.

## 실행 결과

```json
{
  "fixedRevision": "d79752aafcf60c1d9f712cb6eb4d9e8cad5d944c",
  "startedAtUTC": "2026-09-21T17:46:55.929642+00:00",
  "status": "complete-not-deployed",
  "memoryGates": [
    {
      "operation": "run_build",
      "observedAtKST": "2026-09-22T02:46:56.531026+09:00",
      "availablePhysicalBytes": 3105771520,
      "minimumBytes": 1610612736,
      "pass": true
    },
    {
      "operation": "build_bundle",
      "observedAtKST": "2026-09-22T02:47:14.438134+09:00",
      "availablePhysicalBytes": 3097948160,
      "minimumBytes": 1610612736,
      "pass": true
    }
  ],
  "payloadChecks": [
    {
      "stage": "before build",
      "changedCount": 0,
      "untrackedCount": 0,
      "changedPaths": [],
      "untrackedPaths": [],
      "head": "d79752aafcf60c1d9f712cb6eb4d9e8cad5d944c"
    },
    {
      "stage": "after build",
      "changedCount": 0,
      "untrackedCount": 0,
      "changedPaths": [],
      "untrackedPaths": [],
      "head": "d79752aafcf60c1d9f712cb6eb4d9e8cad5d944c"
    },
    {
      "stage": "after bundle",
      "changedCount": 0,
      "untrackedCount": 0,
      "changedPaths": [],
      "untrackedPaths": [],
      "head": "d79752aafcf60c1d9f712cb6eb4d9e8cad5d944c"
    }
  ],
  "sourceFingerprints": [
    {
      "stage": "before build",
      "sha256": "b7f26e34cccd19451292035a957b35a868c240b6bae3b81a1cadfef4c32d11eb"
    },
    {
      "stage": "after build",
      "sha256": "b7f26e34cccd19451292035a957b35a868c240b6bae3b81a1cadfef4c32d11eb"
    },
    {
      "stage": "after bundle",
      "sha256": "b7f26e34cccd19451292035a957b35a868c240b6bae3b81a1cadfef4c32d11eb"
    }
  ],
  "runBuildCalls": 1,
  "buildBundleCalls": 1,
  "newServerStarts": 0,
  "newBrowserStarts": 0,
  "apiRestarts": 0,
  "deployments": 0,
  "modelCalls": 0,
  "installations": 0,
  "builder": {
    "size": 22599,
    "sha256": "1bd8704e87bb17158990a0fd937232f96341727075b7a1cdea5df8b803d092b7"
  },
  "trackedPayloadSourceCount": 62,
  "tools": {
    "python": "C:\\00.프로젝트\\happycall-ralphthon\\.venv\\Scripts\\python.exe",
    "temporaryPathPrefix": "C:/Users/choi8/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin",
    "selectedNpm": "C:\\Users\\choi8\\AppData\\Local\\Programs\\nodejs\\npm.cmd",
    "npmVersion": "11.16.0",
    "npmWrapperSiblingNode": "C:\\Users\\choi8\\AppData\\Local\\Programs\\nodejs\\node.exe",
    "nodeVersion": "v24.18.0",
    "childEnvironmentKeysOnly": [
      "APPDATA",
      "CI",
      "COMSPEC",
      "LOCALAPPDATA",
      "NEXT_PUBLIC_API_BASE",
      "NEXT_TELEMETRY_DISABLED",
      "NODE_ENV",
      "NPM_CONFIG_UPDATE_NOTIFIER",
      "PATH",
      "PATHEXT",
      "SYSTEMROOT",
      "TEMP",
      "TMP",
      "USERPROFILE",
      "WINDIR"
    ]
  },
  "runBuildSeconds": 17.703,
  "buildBundleSeconds": 2.141,
  "bundlePath": "C:\\00.프로젝트\\happycall-ralphthon\\dist\\deployment\\20260921T174714439133Z-d79752aafcf6",
  "build": {
    "stampPath": "C:\\00.프로젝트\\happycall-ralphthon\\apps\\web\\out\\.oneflow-build.json",
    "stampFile": {
      "size": 519,
      "sha256": "a263a3a4fefe7ba07b4796fceab69ec51b2d51fec84a678c12fe95235126a766"
    },
    "status": "complete",
    "completedAt": "2026-09-21T17:47:14.229104+00:00",
    "recordDigest": "6319ed469d27547136f548a41ea697ce6500f467ac1f41b534d2fe5f2823e98b",
    "outputFingerprint": "b6af58ddd1dc93a3a2c04c5245d75d90585427507cc2a64e1c39fcb8265d8328",
    "outputFileCount": 27,
    "outputBytes": 6880635,
    "javascriptFiles": 16,
    "cssFiles": 2,
    "mediaFiles": 4
  },
  "bundle": {
    "status": "complete",
    "sourceRevision": "d79752aafcf60c1d9f712cb6eb4d9e8cad5d944c",
    "payloadFileCount": 60,
    "actualFileCountIncludingMarker": 61,
    "payloadBytes": 12954352,
    "allBytesIncludingMarker": 12963099,
    "markerFile": {
      "size": 8747,
      "sha256": "e14320a009e10aa65f54d020715b9d3761e7bee313654fddc6511e0bc1d90cfb"
    },
    "actualInventorySha256": "1347a576b151a226b63df0765be0f122a2d834f0fb4d2c2ca958ab64743e54e6",
    "missingPaths": 0,
    "extraPaths": 0,
    "byteOrHashMismatches": 0
  },
  "media": [
    {
      "name": "CASE-0001.wav",
      "size": 2263278,
      "sha256": "d4eeb6448ff8969f27034ecade9a050ee212468585c6300b19c9a0ebdc372931",
      "matchedCopies": 4
    },
    {
      "name": "CASE-0002.wav",
      "size": 2388044,
      "sha256": "6fe83afb8552765ab92722b838d2a0905f507551c4f98c58fa62a515033abaa0",
      "matchedCopies": 4
    },
    {
      "name": "sorter-demo.mp4",
      "size": 991249,
      "sha256": "4a640c20e209bf5a43e26c3f1c5afeb41f4157af9017f04b4c3812b1990dca51",
      "matchedCopies": 4
    },
    {
      "name": "sorter-demo.tracks.json",
      "size": 158546,
      "sha256": "b9b9f50295af799cfdf718b840b0cef703f57ad3e3b778557fcd9fdeb9ac681c",
      "matchedCopies": 4
    }
  ],
  "notifications": {
    "path": "server/notifications.py",
    "size": 5752,
    "sha256": "79b3a0af7e896aa9d3519fe7575bf1a1717e140bd3e3fee0dc8a54c7cab037a9",
    "sourceBundleAndManifestMatch": true
  },
  "manifestFile": {
    "size": 3516,
    "sha256": "d6b6423283ef6f429080e88790a01a81eda8cdd2ca6e856116cd940c6933a346"
  },
  "finishedAtUTC": "2026-09-21T17:47:16.847357+00:00",
  "finalHead": "d79752aafcf60c1d9f712cb6eb4d9e8cad5d944c"
}
```

## 인수 경계

이 결과는 생성자 측 로컬 빌드·파일 무결성 대조입니다. RAM은 각 호출 시작 시점 관측이며 최대 사용량 측정이 아닙니다. 실제 브라우저 업무 흐름·채널 외부 수신·원격 저장·HTTPS·배포 완료를 의미하지 않습니다. 메인이 별도 독립 묶음 대조와 보고서 커밋을 수행합니다.

## 생성자와 분리한 실제 파일 대조

2026-09-22 02:51 KST, 읽기 전용 검토자가 builder의 판정 함수를 재사용하지 않고 파일을 직접 순회·해시 계산했습니다. payload 목록/크기/SHA **60/60**, 현재 out와 묶음의 정적 출력 **27/27·6,880,635 bytes**, 미디어4종×4위치 **16/16**이 일치합니다.

실제 inventory SHA256은 `1347a576b151a226b63df0765be0f122a2d834f0fb4d2c2ca958ab64743e54e6`, marker SHA256은 `e14320a009e10aa65f54d020715b9d3761e7bee313654fddc6511e0bc1d90cfb`로 생성자 보고와 같습니다. 별도 계산한 frontend35개 지문·정적 출력 지문·build stamp record digest도 실제 marker/stamp와 일치했습니다. 알림 컴포넌트 import·저장 Case를 전달하는 세 렌더 위치·알림 문구7개가 고정 소스 및 실제 export chunk에 포함됨을 대조했습니다.

고정 Git의 생산 입력62개는 raw bytes **54/62**, LF 정규화 **62/62**였습니다. 8개는 Windows 줄바꿈 차이뿐입니다. 묶음 runtime/template/fixture29개는 현재 작업파일과 raw **29/29**, 고정 Git blob과 raw **28/29**입니다. fixture1개가 LF→CRLF 603개 차이이며 JSON 내용과 정규화 bytes는 동일합니다. Git 원본과 모든 raw hash가 같다는 주장으로 확대하지 않습니다.

정상 inventory 비교60/60을 양성 대조로 두고 메모리에서 `api/index.py` 항목의 크기+1 및 SHA 변경을 각각 주입했습니다. 같은 비교기가 두 경우 모두 `MISMATCH:api/index.py`를 검출했습니다. 디스크 파일은 변경하지 않았습니다. 파일쓰기·네트워크·새 서버·브라우저·재빌드·배포는0입니다.

메인은 이번 고정 소스의 로컬 생산 묶음을 인수합니다. 실행 중 API 반영·실제 두 흐름의 저장/수신·외부 채널 발송·최종 배포 인수는 별도 미완료입니다.
