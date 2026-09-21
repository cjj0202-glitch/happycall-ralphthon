# 모바일 UX 생산 빌드·로컬 묶음

2026-09-22 00:44 KST · 실제 pc1/CJJ · 고정 소스 `5f3bf9d225faeb097d68a87befe8ad709c1917be`

모바일 작업 선택과 대기 목록 복귀가 반영된 고정 소스로 production build 1회와 새 로컬 묶음 생성 1회를 완료했습니다. 빌드 전후·생성 후 프런트 소스 지문이 일치하고, 출력 26개 및 묶음 payload 57개를 실제 파일로 다시 대조했습니다. 메인의 별도 독립 묶음 검증은 이 보고서 이후 단계입니다. v3 미디어를 유지하며 실제 tracks 등록·전체 사용자 흐름·외부 배포 완료를 주장하지 않습니다.

## 범위와 실제 도구

작업 루트는 `C:/00.프로젝트/happycall-ralphthon`입니다. [이전 생산 빌드의 실행법](ux-v2-production-build.md)과 기존 `scripts.build_deployment_bundle.run_build(root)`, `build_bundle(root, root / MEDIA_MANIFEST, revision=고정SHA)`를 사용했습니다. 실행한 검사기 소스 SHA256은 `ec4816bc5338822170faefb09397b252016ad493302ce89306ad18c6e0cab75e`입니다.

소유 쓰기는 ignored `apps/web/.next`·`out`·빌드 완료 기록, 새 `dist/deployment` 하위 폴더, 이 보고서입니다. 제품 소스·등록 manifest·타인 변경을 수정하거나 되돌리지 않았습니다. 기존 renderer PID13052 및 3100/8100 서버에 접근해 재시작·종료하지 않았고, 새 서버·브라우저·API·배포·다운로드·설치·Blender 실행도 하지 않았습니다. .env·키 내용을 열람하거나 출력하지 않았으며 커밋/push는 메인 소유입니다.

- Python: 저장소 `.venv/Scripts/python.exe -B`.
- PATH 앞 Node: `C:/Users/choi8/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin`.
- 실제 선택된 npm: `C:/Users/choi8/AppData/Local/Programs/nodejs/npm.cmd`, npm 11.16.0.
- npm 래퍼 자체 Node: 같은 디렉터리의 node.exe, 실제 `--version` v24.18.0. 래퍼 실행을 bundled Node에서 수행했다고 기록하지 않습니다.
- 기존 run_build는 npm run build만 실행하고 자식 환경을 허용 목록으로 제한합니다. 같은 origin용 `NEXT_PUBLIC_API_BASE=""`를 고정하고 앱 .env 이름은 내용 읽기 전에 거절합니다. npm 상세 stdout/stderr는 기존 도구 내부 capture 대상이며 별도 로그로 출력하지 않았습니다.

## RAM 실행 문턱

실제 각 작업 호출 직전에 Windows `GlobalMemoryStatusEx.ullAvailPhys`를 읽고, 1.5GiB = **1,610,612,736 bytes** 미만이면 호출 없이 `NOT_RUN_LOW_MEMORY`로 종료하는 분기를 두었습니다.

| 시각 KST | 실행 직전 availablePhysicalBytes | 결과 |
|---|---:|---|
| 00:41:01.246683 | 2,500,612,096 | 문턱 이상 → run_build 1회 |
| 00:43:06.771174 | 2,308,612,096 | 문턱 이상 → build_bundle 1회 |

이 수치는 실행 시작 시점 관측이며 실행 도중 최대 메모리 사용량을 측정한 값은 아닙니다.

## 명령과 HEAD 변경 처리

기존 PATH를 임시 보존/복원하고 bundled Node bin을 앞에 붙인 PowerShell에서 다음 Python API를 `.venv/Scripts/python.exe -B -`로 순서대로 호출했습니다.

```python
from pathlib import Path
from scripts.build_deployment_bundle import (
    run_build, build_bundle, source_fingerprint, MEDIA_MANIFEST
)
root = Path.cwd().resolve()
revision = "5f3bf9d225faeb097d68a87befe8ad709c1917be"
# 각 호출 바로 전에 GlobalMemoryStatusEx로 RAM >= 1610612736을 확인.
before = source_fingerprint(root)
stamp_path = run_build(root)
# build 성공 및 기준 소스 동일성 확인 후, 새 RAM 측정 문턱을 별도로 적용.
output = build_bundle(root, root / MEDIA_MANIFEST, revision=revision)
```

빌드 착수 HEAD는 고정 SHA와 일치했습니다. 첫 묶음 사전 확인은 아래 HEAD 불일치 assertion에서 중단됐고 **build_bundle 호출 전이라 새 출력 폴더를 만들지 않았습니다.** 이 실패를 빌드 실패나 성공 실행으로 세지 않습니다.

```text
AssertionError: ('b0f54fe66d0afcd897ff026e08e94a127f70d4f3',
                 '5f3bf9d225faeb097d68a87befe8ad709c1917be')
```

메인이 프런트 추가 변경 없이 배정 문서 한 개만 커밋했으며 고정 빌드 기준을 유지하라고 확인했습니다. `git diff --name-only 5f3bf9d... HEAD`의 실제 차이는 `reports/channel/N04-D2-notification-contract.md` 하나였습니다. 현재 프런트 지문은 빌드 전과 동일했고 `git diff --exit-code <고정SHA> -- <SOURCE_FILES 및 TEMPLATES>`는 0으로 런타임 payload 소스도 기준과 같았습니다. 이 근거를 확인하고 revision 인수를 계속 고정해 묶음을 생성했습니다. 생산 빌드를 다시 실행하지 않았습니다.

## 실제 빌드 결과

`run_build` 종료코드 0, `status=build-recorded`이며 완료 파일은 `apps/web/out/.oneflow-build.json`입니다.

| 항목 | 실제 결과 |
|---|---|
| 완료 시각 | `2026-09-21T15:41:33.734976+00:00` = 2026-09-22 00:41:33.734976 KST |
| sourceBefore = sourceAfter = 생성 후 실측 | `50add18af693736e0e7cfc619b3a5fb3ecd35c53b31ad3fb996d6503eddc56a9` |
| outputFingerprint = 출력 파일 재계산 | `6a804deaa89b5114005a6aebd5ff7cc24f30d89e5693796ad29873e2d395e4e2` |
| 출력 파일 / 실제 바이트 | 26 / 6,823,540 |
| 양성 산출 분모 | JS 16, CSS 2, 등록 media 3 |
| build record digest | `b1a26b277750ea3e8f4fbb02c096c479a4e36e818a5f708eff526bfaddb4c19a` |
| 완료 파일 bytes / SHA256 | 519 / `9bc91b0e673a9ec4f30dfe4345849d43ab492aff9dd0f7c53f5d3e1de4564a3e` |

출력 파일 수와 출력 지문에서 완료 기록 자체는 제외됩니다. 완료 기록은 로컬 실행 검증용 checksum이며 서명자의 인증서는 아닙니다.

## 새 묶음 결과

생성 경로:

```text
dist/deployment/20260921T154306772648Z-5f3bf9d225fa
```

`build_bundle` 종료코드 0, `status=packaged-not-deployed`입니다. 기존 폴더를 재사용하거나 덮어쓰지 않았습니다.

| 항목 | 실제 결과 |
|---|---|
| sourceRevision | `5f3bf9d225faeb097d68a87befe8ad709c1917be` |
| payload 파일 / 실제 전체 파일 | 57 / 58(marker 포함) |
| payload 바이트 / marker 포함 실제 바이트 | 12,834,605 / 12,842,942 |
| .bundle-manifest.json bytes / SHA256 | 8337 / `a97380ff89e5152a3360d26763715fd4ac55800356db0f9932ecac00fdf66082` |
| 실제 payload inventory SHA256 | `0890ed0711eac8e9a40e28230155f507f07a1e8076763ee2caf2e5653b636664` |

00:43:37 KST 읽기 재확인에서 실제 파일 집합은 manifest의 57개 + marker 1개와 같고, payload 57/57의 크기·SHA256 및 총 바이트가 일치했습니다. `apps/web/out`의 실제 26개 파일을 읽어 재계산한 출력 지문도 build stamp·bundle manifest와 일치했습니다. payload inventory SHA256은 경로순으로 정렬한 실제 `{path,size,sha256}` 목록을 `ensure_ascii=False, sort_keys=True, separators=(",",":")` JSON + 마지막 LF로 직렬화한 SHA256이며 marker는 제외합니다. 디렉터리 자체나 압축 파일의 해시가 아닙니다.

## 남은 검증

등록 미디어는 `demo-media-20260921-audio-v3`이며 tracks 등록은 false입니다. 새 전체 음성/영상·CLOVA 타임라인·288프레임 결과를 등록하지 않았습니다. 모바일 브라우저 동작, 전체 6회 사용자 흐름, 실제 저장·영속성, 외부 배포·권한·HTTPS·실모델 호출은 이번 실행 범위가 아닙니다. 기존 서버 상태나 최종 제품 성공을 이 빌드/패키징으로 판정하지 않습니다.

소유 산출물을 메인 인수용으로 동결하며 메인이 새 묶음의 별도 독립 검증·커밋/공유를 수행합니다.

## 메인 지정 독립 대조 — 00:44 KST

별도 읽기 전용 explorer가 생성 함수 없이 실제 파일을 읽고 해시를 재계산했습니다. manifest 선언57개/중복0, 실제 payload57+marker1/누락·추가0, 총12,834,605bytes 및 각 크기·SHA57/57이 일치했습니다. 같은 크기의 메모리 사본에서1바이트를 바꾼 음성 대조군은 SHA 불일치로 검출했습니다.

현재 out와 묶음 프런트26/26, 일반 원본 경로55/55와 deploy/vercel 템플릿2/2가 같은 바이트였습니다. 미디어3개는 public/out/묶음-public/묶음-out의12/12 사본이 정본 크기·SHA와 일치했고, 합성 fixture5개 사본과 media manifest도 일치했습니다. 출력 fingerprint와 build record digest를 독립 계산하여 위 값과 대조했습니다.

실제 번들 JS의 클릭별RAF·모바일 폭/사건/역할/view 가드·preventScroll·instant 이동·목록 앵커·사건별 key, CSS의192px 안전 여백·16−192px 상쇄·모바일 전용 링크도 읽었습니다. 첫 CSS 문자열 검색은 공백 차이로 일치하지 않아 실제 minified 구문을 확인한 뒤 판정했습니다. 수록 확인을 브라우저 실행으로 세지 않습니다.

메인은 실제 빌드 기록과 보고서를 읽고 고정5f3bf9d의 로컬 묶음 범위만 인수했습니다. 외부 배포·새 미디어·전체 저장 흐름은 계속 별도 미완료입니다.
