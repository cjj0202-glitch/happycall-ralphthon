# UX v2 생산 빌드·로컬 배포 묶음 검증

2026-09-21 23:57 KST · 실제 pc1/CJJ · 로컬 빌드/정적 패키지 검사

UX v2 생산 빌드가 23:54:08 KST에 완료됐고, 고정 통합 커밋 `faf52a688d0713143d4677b31503746cbb5987cc`에서 새 배포 묶음을 생성했습니다. 프런트 소스 지문은 빌드 전후·현재 모두 일치합니다. 생산 출력 26개와 묶음 payload 57개를 실제 파일로 대조했으며, 묶음 전체 57/57 크기·SHA256이 manifest와 일치합니다. 현재 등록 미디어는 v3이며 실제 tracks는 미등록입니다. 외부 배포·영속 저장 완료를 뜻하지 않습니다.

## 입력·실행 범위

- 작업 루트: `C:/00.프로젝트/happycall-ralphthon`.
- 프런트 고정 기준: `9de36c449e6be9bc32a1ad61c3bf45eb5f143601`의 globals.css, page.tsx, CallReview.module.css, CallReview.tsx. 4/4 내용 일치이며 3개 파일은 Git blob과 작업트리의 CRLF/LF 차이만 있습니다.
- 빌드 착수 당시 HEAD는 `5af3617dcf18a30854d018693cff3bcb7a8fb461`였습니다. 메인의 통합 커밋 작업과 생산 빌드를 분리하여, 빌드 완료 후 패키징을 대기했습니다. 메인이 확정한 `faf52a688d0713143d4677b31503746cbb5987cc`를 HEAD에서 확인하고 공개 `build_bundle(..., revision=전체SHA)` API에 고정했습니다.
- 참고: [기존 23:09 빌드](pc4-tms-role-main-intake.md), [배포 묶음 계약](deployment/bundle-design.md), `scripts/build_deployment_bundle.py --help` 및 전체 소스.
- 쓰기 범위는 ignored `apps/web/.next`, `apps/web/out`, 빌드 완료 기록, 새 `dist/deployment` 폴더와 이 보고서입니다. `next.config.ts`는 개발을 `.next-dev`, production을 `.next`로 분리합니다.
- 기존 3100/8100 서버 재시작·종료, 새 서버/브라우저/API 요청, 설치, .env/키 내용 열람, Blender 실행, 기존 렌더 PID/출력 접근을 하지 않았습니다. 소스·등록 manifest·ops/CURRENT 수정이나 커밋·push도 하지 않았습니다.

## 자원·실제 도구

메모리는 `Get-CimInstance Win32_OperatingSystem`의 `FreePhysicalMemory * 1024`로 측정했습니다. 생산 빌드 착수 문턱은 1.5GiB = 1,610,612,736 bytes입니다.

| 측정 시각 KST | 시점 | availablePhysicalBytes | 관측 |
|---|---|---:|---|
| 23:51:28 | 최초 사전 점검 | 1,873,317,888 | 문턱 이상 |
| 23:52:57 | 실제 생산 빌드 직전 | 2,489,192,448 | 문턱 이상으로 실행 |
| 23:55:56 | 생산 빌드 종료 후 묶음 생성 직전 | 1,596,219,392 | 문턱보다 14,393,344 bytes 낮음 |

마지막 측정 뒤에는 새 Next 빌드를 실행하지 않고 약 5초의 새 폴더 묶음 생성만 실행했습니다. 메인에 이 낮아진 수치를 별도로 회신했습니다.

실제 PATH 앞에는 요청된 `C:/Users/choi8/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin`을 붙였습니다. 이 디렉터리에는 node.exe(v24.19.0)만 있어, 처음 가정한 그 경로의 npm.cmd 실행은 “명령을 찾지 못함”으로 끝났습니다. 이 단계에서는 빌드를 시작하지 않았습니다. 기존 설치된 npm 래퍼 사용을 메인에게 확인받고 표준 run_build 경로를 유지했습니다.

| 도구 선택 | 실제 경로·버전 |
|---|---|
| PATH의 node.exe | `C:/Users/choi8/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe` / v24.19.0 |
| run_build가 찾은 npm.cmd | `C:/Users/choi8/AppData/Local/Programs/nodejs/npm.cmd` / npm 11.16.0 |
| npm 래퍼가 선택한 Node | `C:/Users/choi8/AppData/Local/Programs/nodejs/node.exe` / v24.18.0 |
| Python | 저장소 `.venv/Scripts/python.exe` / 3.12.14 |

npm 래퍼의 소스는 자기 디렉터리의 node.exe가 있으면 그것을 선택합니다. 따라서 npm 래퍼 실행을 bundled Node v24.19.0에서 수행했다고 기록하지 않습니다. 각 Next 하위 프로세스의 실행 파일 경로를 별도로 추적하지는 않았습니다.

## 재현 명령·생산 빌드 결과

PowerShell에서 기존 PATH를 보존하고 해당 자식 실행 동안만 앞에 bundled bin을 붙였습니다. 아래 호출 직전 메모리 조건을 검사했고 1.5GiB 미만이면 `--build`를 호출하지 않는 분기를 사용했습니다.

```powershell
$priorBuildPath = $env:PATH
try {
    $env:PATH = 'C:/Users/choi8/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin;' + $env:PATH
    $availableBuildBytes = [int64](Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory * 1024
    if ($availableBuildBytes -lt 1610612736) { $buildExitCode = 3 }
    else {
        & '.\.venv\Scripts\python.exe' -B scripts/build_deployment_bundle.py --root 'C:/00.프로젝트/happycall-ralphthon' --build
        $buildExitCode = $LASTEXITCODE
    }
} finally { $env:PATH = $priorBuildPath }
exit $buildExitCode
```

실제 종료코드는 0이고 표준 스크립트는 `status=build-recorded`, `apps/web/out/.oneflow-build.json`을 반환했습니다. 명령은 npm run build만 실행합니다. npm 자식 환경은 허용 목록으로 구성하고 CI/production, telemetry off, 같은 origin용 `NEXT_PUBLIC_API_BASE=""`를 고정합니다. 앱 루트 .env 이름은 내용 열람 없이 거절하는 소스 검사를 먼저 수행합니다.

| 빌드 대조 항목 | 실제 값 |
|---|---|
| 완료 시각 | `2026-09-21T14:54:08.604074+00:00` = 23:54:08.604 KST |
| sourceBefore = sourceAfter = 재측정 | `cdb3de3f4c2549f4bd082f320b933b1ea6b058898289b88048be533e019e2946` |
| outputFingerprint = 재측정 | `db31d9429fe14169081b33a69619d24287c84cfd7846841131d296ceec01a4f9` |
| 출력 파일 수 / 바이트 | 26 / 6,822,511 |
| 양성 출력 분모 | JavaScript 16, CSS 2, 등록 media 3 |
| build record digest | `5dca53e43778886265f3f29b86d1ac9d91a5680658f9fc0582f428d25d2eff99` |
| 빌드 완료 파일 자체 SHA256 | `7db08e59b8f9faf3c1821ff72b42785fe91173b6442d827c396baa0fc97e41d6` |

빌드 완료 파일은 519 bytes이며 출력 26개 분모에서는 제외됩니다. 완료 기록은 서명자의 인증서가 아니라 로컬 검증 기록입니다. npm 상세 stdout/stderr는 기존 run_build가 내부에서 capture하며 여기서 별도 로그로 노출하지 않았습니다. 빌드 실패나 재시도는 없었습니다.

## 고정 커밋의 새 묶음

메인의 정확한 커밋 회신을 받은 뒤 아래 공개 API를 호출했습니다. Git HEAD 일치 assertion 후 revision 인수도 고정하여, 동시 문서 커밋이 sourceRevision을 바꾸는 것을 피했습니다.

```python
root = Path.cwd().resolve()
revision = subprocess.check_output(["git", "rev-parse", "faf52a6"]).decode().strip()
assert subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip() == revision
output = build_bundle(root, root / MEDIA_MANIFEST, revision=revision)
```

실행기는 `.venv/Scripts/python.exe -B -`이고 import는 기존 `scripts.build_deployment_bundle`의 `build_bundle, MEDIA_MANIFEST`입니다. 새 산출 경로는 다음과 같습니다.

```text
dist/deployment/20260921T145556559445Z-faf52a688d07
```

| 묶음 항목 | 실제 값 |
|---|---|
| 상태 / 종료코드 | packaged-not-deployed / 0 |
| sourceRevision | `faf52a688d0713143d4677b31503746cbb5987cc` |
| manifest payload 파일 / 실제 전체 파일 | 57 / 58(marker 포함) |
| payload 총 바이트 | 12,833,576 |
| .bundle-manifest.json bytes / SHA256 | 8337 / `8f1e81be6201eabc5c51f11042d75cc856be58150a97cf29d6973dbd801cbbb2` |
| source 지문 | `cdb3de3f4c2549f4bd082f320b933b1ea6b058898289b88048be533e019e2946` |
| output 지문 | `db31d9429fe14169081b33a69619d24287c84cfd7846841131d296ceec01a4f9` |

기존 묶음의 파일 목록/크기/SHA 대조 방법을 재사용해, 새 묶음을 읽기 전용으로 독립 재검사했습니다. 실제 파일 집합이 manifest 57개 + marker 1개와 정확히 같고, 경로 이탈/링크 없음, 57/57 크기와 SHA256, 총 바이트를 직접 다시 계산했습니다. 패키저의 status만 통과 근거로 쓰지 않았습니다.

PC2의 새 공통 media 계약과 수정된 snapshot 제공 코드도 실제 묶음에서 읽어 작업트리 원바이트 및 고정 커밋 내용과 대조했습니다. Git blob 대조에서는 줄바꿈만 정규화했습니다.

| 실제 묶음 파일 | bytes | SHA256 |
|---|---:|---|
| `server/media_contract.py` | 3890 | `369ed3cd8cf0bd4a1109bc493638f9d071f53844fcbb6c035777bd97dc8b86a9` |
| `server/deployment_app.py` | 13780 | `d900b54a61fc769c7ee05f5f4f04cd2820e73956b1114a837a47e1cc16d73fbd` |
| `data/demo-media-manifest.json` | 3081 | `ae2fdf24bd168ea9af512f5e1f7bbfce26dd234d9de2dabbed35087bfa88b52c` |

`server/deployment_app.py`의 `_read_regular_snapshot`은 72행부터 존재하며, AST에서 추출한 UTF-8 함수 소스 구간의 SHA256은 `7367175e3d313f6dd08e815f6c2049968f1a71771dd3e82add88c2cf2e217b3a`입니다. 이는 파일 SHA와 다른 분모입니다. 본 작업에서는 이 서버 모듈을 기동하거나 API 요청을 보내지 않았습니다. 메인이 수행한 ASGI·단위 검사 결과를 이 빌드 작업의 새 실행으로 세지 않습니다.

## 프런트 입력 고정표

| 파일 | bytes | PC1 작업트리 SHA256 | 9de36c4와 비교 |
|---|---:|---|---|
| `apps/web/app/globals.css` | 40567 | `3568d4424a5838ff951a907098c13a59bcbadde07843cf948ecb79cbb32eed27` | CRLF/LF 정규화 후 일치 |
| `apps/web/app/page.tsx` | 66507 | `a85ebd72b018ae955ca3af2c2743c403e761fcfdd1bcfec39a343980f521de0d` | CRLF/LF 정규화 후 일치 |
| `apps/web/components/CallReview.module.css` | 9951 | `99e05ba3a7c4b2f53feda75cfd4016d5d7b77504ecf8d16f54bad09fb0bae05d` | 원바이트 일치 |
| `apps/web/components/CallReview.tsx` | 27929 | `f5df2066049a5bd05b264c38e6847c5e06ab82f3f65c836826a08501cf6a3f2d` | CRLF/LF 정규화 후 일치 |

## 메인의 별도 검증자 인수

2026-09-21 23:58 KST, 제작 워커와 다른 읽기 전용 검증자가 고정 묶음과 `faf52a688d0713143d4677b31503746cbb5987cc` Git blob을 직접 읽었습니다. 제작 워커의 판정값을 복사하지 않고 파일 bytes·SHA256 및 정렬된 `{path,size,sha256}` 목록의 canonical JSON 지문을 다시 계산했습니다.

- manifest 57개 payload 전부 크기·SHA 일치, 총 12,833,576 bytes 일치, 추가·누락 0개. marker 포함 실제58파일입니다.
- 프런트 출력26/26 원바이트 일치, 입력33개 source 지문·output 지문·buildRecordDigest 재계산 일치.
- 등록 v3 미디어3개 × 원본/묶음의 public/out 4위치 = 12/12 크기·SHA 일치.
- runtime28개 모두 작업트리와 원바이트 일치. Git blob과26개 원바이트·2개 CRLF 차이만 있습니다. 프런트 추적30개는21개 원바이트·9개 CRLF 차이만 있습니다.
- 새로운 업무 앵커7/7이 출력 app JS에 존재합니다. 이것은 묶음 포함 증거이며 클릭·저장 기능 재실행 증거가 아닙니다.
- 재현 실행기 `.venv/Scripts/python.exe -B -X utf8 -`; 파일 `read_bytes()`/`len()`/`hashlib.sha256()`과 `git show faf52a688d0713143d4677b31503746cbb5987cc:<경로>` 대조. 서버·브라우저·API 실행 및 키 열람은 하지 않았습니다.

읽기 전후 묶음 manifest SHA는 `8f1e81be6201eabc5c51f11042d75cc856be58150a97cf29d6973dbd801cbbb2`로 같았습니다. 확정 불일치0건은 위 정적 묶음 범위에 한정합니다.

## 미실행·동결

등록 releaseTag는 `demo-media-20260921-audio-v3`이고 manifest의 tracks 등록은 false입니다. 묶음의 모든 payload 경로에서도 tracks 파일은 0개였습니다. 미등록 실제 288프레임 결과나 새 영상/좌표를 넣지 않았습니다.

이번 결과는 production export와 로컬 배포 입력입니다. Vercel 권한·provider build와 최종 의존성 용량, HTTPS/라우팅·인증·브라우저 접근, 원격 영속 저장·실모델 호출·배포 완료는 미검증입니다. 기존 서버의 실행/저장 상태를 이 묶음 검증으로 대체하지 않습니다.

이 보고서와 새 묶음을 메인 인수용으로 동결합니다. 추가 소스 변경·등록·배포·커밋·원장 갱신은 이 작업에서 수행하지 않습니다.
