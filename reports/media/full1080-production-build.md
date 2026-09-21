# Full1080 v4 생산 빌드 및 새 로컬 배포 묶음

2026-09-22 02:26 KST · pc1/CJJ 메인 하위 작업 · 고정 소스 `b9a2a1888df66c755f1f6bef19d3d7e5f3028c0f`

v4 미디어와 CCTV 프레임 이동 보완이 포함된 고정 소스로 생산 빌드 1회와 새 로컬 묶음 생성 1회를 완료했습니다. 실제 실행 세션 50638의 종료코드는 0입니다. 출력 27개, 묶음 payload 59개, 미디어 4개를 실제 파일로 재대조했습니다. 이 보고서는 로컬 산출물 검증이며 외부 배포나 전체 업무 흐름 승인 결과는 아닙니다.

## 실행 범위와 도구

기존 [모바일 UX 생산 빌드 절차](../mobile-ux-production-build.md)와 `scripts.build_deployment_bundle.run_build`·`build_bundle`를 사용했습니다. 검사기 파일 SHA256은 `ec4816bc5338822170faefb09397b252016ad493302ce89306ad18c6e0cab75e`입니다.

쓰기 범위는 ignored `apps/web/.next`·`apps/web/out`, 새 `dist/deployment` 하위 폴더와 본 보고서입니다. 제품 소스·미디어 등록 manifest·타인의 문서는 수정하거나 되돌리지 않았습니다. `.next-dev`와 기존 사용자 원장은 작업 대상에서 제외했고 원장 내용이나 건수를 다시 열람하지 않았습니다. 서버·브라우저·API·인코딩·배포·설치·실모델 호출·키 읽기·커밋·push는 수행하지 않았습니다.

| 도구 | 실제 확인 |
|---|---|
| Python | 저장소 `.venv/Scripts/python.exe -B -X utf8 -` |
| 임시 PATH 앞 항목 | `C:/Users/choi8/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin` |
| 선택된 npm | `C:/Users/choi8/AppData/Local/Programs/nodejs/npm.cmd`, 11.16.0 |
| npm 래퍼의 sibling Node | `C:/Users/choi8/AppData/Local/Programs/nodejs/node.exe`, v24.18.0 |

PowerShell `try/finally`에서 기존 PATH를 복원했습니다. npm 래퍼가 bundled Node에서 실행됐다고 추정하지 않았습니다. 기존 `run_build`는 허용 목록 환경만 자식에게 전달하고 `CI=1`, `NEXT_TELEMETRY_DISABLED=1`, `NODE_ENV=production`, `NEXT_PUBLIC_API_BASE=""`를 고정합니다. npm의 상세 stdout/stderr는 기존 도구의 내부 capture 대상이며 별도 출력하지 않았습니다.

호출 순서는 다음과 같습니다. 각 gate는 Windows `GlobalMemoryStatusEx.ullAvailPhys`를 읽고 1,610,612,736 bytes 미만이면 실제 함수 호출 없이 중단하는 분기입니다.

```python
before = source_fingerprint(root)
gate("run_build")
stamp_path = run_build(root)                         # 1회
# 전후 frontend fingerprint 및 고정 revision payload 차이 확인
gate("build_bundle")
output = build_bundle(root, root / MEDIA_MANIFEST,
                      revision="b9a2a1888df66c755f1f6bef19d3d7e5f3028c0f")  # 1회
# 반환된 실제 파일 inventory/크기/SHA 및 소스 지문 재대조
```

## RAM 문턱과 소스 고정

| 함수 호출 직전 KST | 가용 물리 RAM bytes | 기준 bytes | 실행 |
|---|---:|---:|---|
| 2026-09-22T02:25:11.214019+09:00 | 2,803,871,744 | 1,610,612,736 | run_build 1회 |
| 2026-09-22T02:25:48.182265+09:00 | 3,032,535,040 | 1,610,612,736 | build_bundle 1회 |

이는 각 호출 시작 시점의 관측이며 최고 메모리 사용량 측정은 아닙니다. 빌드는 36.825334초, 묶음은 1.709226초가 걸렸습니다. 실패 후 재실행이나 기존 묶음 덮어쓰기는 없었습니다.

착수와 완료 시 HEAD는 `d2fab01cbb273ee1c1d535d0ba6247168e8bc457`였습니다. 고정 revision과 HEAD 차이는 `reports/channel/N03-M7-v4-media-intake.md` 한 파일입니다. 보고서 작성 병행으로 다른 미커밋 보고서가 나타났지만 payload로 읽지 않았습니다.

`git diff --name-only <고정SHA> -- <SOURCE_FILES·TEMPLATES·FRONTEND_DATA_FILES·apps/web·builder>`에서 payload 변경은 착수·빌드 후·묶음 후 모두 0건이었습니다. 빌드에서 생성될 수 있는 `apps/web/next-env.d.ts`는 이 차이 판정에서 제외했으며 완료 Git 상태에도 해당 파일 변경은 없었습니다. 빌드 전·빌드 후·묶음 후 source fingerprint는 모두 아래 값으로 일치합니다.

```text
f64c3eafa5bdd43ae45c8098ba565d0eafa8eb26b3be396a68e916536c25a943
```

## 빌드 출력과 완료 기록

| 항목 | 실측 |
|---|---|
| 실제 완료 기록 status | `complete` |
| 완료 시각 UTC | `2026-09-21T17:25:48.036978+00:00` |
| 완료 파일 | `apps/web/out/.oneflow-build.json` |
| 출력 파일 / 바이트 | 27 / 6,876,703 |
| 양성 산출 분모 | JS 16, CSS 2, 미디어 4 |
| 출력 fingerprint | `9d9f8e0a74788448ebf2780b7f3e35ec4cdf8588129401da0b97172bc9424b2f` |
| build record digest | `e32b53e7b0c3a35ca29d98a3b3b3732509fc30726102085d592ba3a035d56d34` |
| 완료 파일 bytes / SHA256 | 519 / `0b1a6f032553d7562bb608fb625917c17a7c49a0c95674305d9adaa26f97e45f` |

출력 27개는 완료 기록 자체를 제외한 개수입니다. 실제 출력의 경로·크기·SHA 목록을 다시 읽어 계산한 fingerprint가 stamp와 bundle marker 양쪽의 값과 일치했습니다. 완료 기록은 로컬 무결성 checksum이며 서명자의 인증서로 사용하지 않습니다.

## 새 묶음 및 inventory

생성 경로:

```text
C:/00.프로젝트/happycall-ralphthon/dist/deployment/20260921T172548182265Z-b9a2a1888df6
```

| 항목 | 실측 |
|---|---|
| manifest status | `complete` |
| sourceRevision | `b9a2a1888df66c755f1f6bef19d3d7e5f3028c0f` |
| payload 파일 / 실제 파일 | 59 / 60(marker 포함) |
| payload 바이트 / 전체 바이트 | 12,943,794 / 12,952,418 |
| marker bytes / SHA256 | 8624 / `21e8827b2620da89cc2d6007552cb24ecdb15bfa6969ac65ce70f31e083ff8ef` |
| 실제 payload inventory SHA256 | `1831f63a97afaa9655d9119295f8cb847cecd7ef6539d2f0da8adbb5dae762d9` |

실제 파일 집합과 marker가 선언한 59개 항목을 경로·크기·SHA256까지 59/59 대조했습니다. 누락·추가·크기 차이·해시 차이는 각각 0개이며 전체 바이트 합도 일치했습니다. inventory SHA256은 실제 `{path,size,sha256}` 목록을 경로순 정렬 후 `ensure_ascii=False, sort_keys=True, separators=(",",":")` JSON + 마지막 LF로 직렬화한 해시입니다. marker는 제외합니다. 전체 경로별 목록은 묶음의 `.bundle-manifest.json`에 보존됩니다.

| 구성 | 파일 | 바이트 |
|---|---:|---:|
| `apps/web/out` | 27 | 6,876,703 |
| `apps/web/public/demo` | 4 | 5,801,117 |
| `server` | 21 | 148,358 |
| `data` | 2 | 27,209 |
| API 엔트리·배포 설정·Python 의존성·보조 스크립트 | 5 | 90,407 |
| 합계 | 59 | 12,943,794 |

## v4 미디어 4개 대조

원본 public, 생성 out, 묶음 public, 묶음 out의 4개 위치에서 각 파일의 bytes와 SHA256이 일치합니다. public 4개를 기준으로 나머지 사본 12/12를 실제 bytes로 대조했습니다. top-level 등록 3개에 nested tracks 1개를 포함한 물리 파일은 4개입니다.

| 파일 | bytes | SHA256 |
|---|---:|---|
| `CASE-0001.wav` | 2,263,278 | `d4eeb6448ff8969f27034ecade9a050ee212468585c6300b19c9a0ebdc372931` |
| `CASE-0002.wav` | 2,388,044 | `6fe83afb8552765ab92722b838d2a0905f507551c4f98c58fa62a515033abaa0` |
| `sorter-demo.mp4` | 991,249 | `4a640c20e209bf5a43e26c3f1c5afeb41f4157af9017f04b4c3812b1990dca51` |
| `sorter-demo.tracks.json` | 158,546 | `b9b9f50295af799cfdf718b840b0cef703f57ad3e3b778557fcd9fdeb9ac681c` |

묶음의 등록 manifest는 3,516 bytes, SHA256 `d6b6423283ef6f429080e88790a01a81eda8cdd2ca6e856116cd940c6933a346`입니다. 합성 fixture는 out와 data에서 각각 23,693 bytes·SHA256 `5edf80669f7def9d3e10ceea910086c41026ff1252fbc638b97641562f3d84f4`로 일치합니다. 원본 render 재검사나 MP4 재인코딩·재디코딩은 이번 빌드에서 수행하지 않았습니다.

## 인수 경계

메인에게 새 묶음 경로와 실제 exit 0을 전달했으며 별도 읽기 검증을 요청했습니다. 이 보고서의 검증은 생성자 측 파일 대조입니다. 별도 검증자가 수행할 독립 대조·실제 브라우저 동작·인증·원격 저장·HTTPS·모델 호출·외부 배포 완료를 선행 주장하지 않습니다. 묶음 marker에도 제공자 권한, 제공자 빌드와 의존성 크기, HTTPS/브라우저, 원격 저장과 실제 모델 호출은 미검증 항목으로 보존되어 있습니다.

본 보고서와 생성 산출물을 메인 인수용으로 동결합니다.

## 메인 지정 독립 대조 — 02:28 KST

읽기 전용 검토자가 생성 모듈을 import하지 않고 실제 파일을 읽어 지문을 재계산했습니다. 선언/실제 payload59개, 중복·누락·추가0, 크기/SHA59/59와 12,943,794 bytes를 확인했습니다. marker 포함60개/12,952,418 bytes이며 위 inventory·marker 해시와 일치합니다.

현재 out와 bundle out27/27, runtime/source26/26, 배포 템플릿2/2, 미디어4종×4위치16/16, 합성 fixture5/5가 같은 바이트였습니다. 고정 revision의 추적 소스·템플릿56개는 `git diff --quiet` exit0이고, 실제 소스34파일에서 계산한 지문·완료 기록의 before/after·bundle 선언도 일치했습니다. outputFingerprint와 buildRecordDigest도 독립 계산해 위 값과 대조했습니다.

같은 크기의 메모리 사본에서 1바이트를 바꾼 대조군은 SHA 불일치로 검출했고 디스크 원본은 변하지 않았습니다. 실행은 `.venv/Scripts/python.exe -B -` 읽기 코드이며 파일쓰기·네트워크·서버·브라우저 생성0입니다. 영상 descriptor의 videoSha256과 정본 v4 manifest 바인딩도 확인했습니다.

메인은 로컬 묶음의 바이트 정합 범위를 인수합니다. 실제 배포·브라우저 전체 흐름·원격 저장·영상 디코딩은 이 독립 검사의 완료 항목이 아닙니다.
