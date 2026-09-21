# N01 별도 Vercel 배포 폴더 설계

작성: 2026-09-21 pc1 대기세션5, 구현 인수: portable_deployment_app. 현재 이 절은 구현 전 계약을 정정한 상세설계입니다. 실제 Vercel 빌드·계정 제한·배포 런타임은 미검증입니다.

## 배포 경계

`dist/deployment/<UTC시각>-<Git SHA>` 아래 새 폴더 하나만 만듭니다. 기존 폴더가 있으면 실패하며 기존 산출물을 지우거나 덮어쓰지 않습니다. 원본 저장소는 allowlist의 입력으로만 읽습니다. `.env*`, `.local`, `.git`, 인증 키, 원격 원천자료, API 로그, 테스트·개발 의존성 디렉터리를 복사하지 않습니다. 실제 계정 연결과 `.vercel` 주입, 배포는 메인 작업입니다.

Vercel 후보는 하나의 Python ASGI 함수로 Next 정적 export·합성 media·API를 모두 처리합니다. `api/index.py`는 자기 배포 루트 안의 서버와 `apps/web/out`만 사용합니다. `ONEFLOW_STATIC_DIR`를 그 절대경로로 고정해 `create_deployment_app`에 전달합니다. 접근 제어는 별도 작업자의 factory가 맡으며 `/healthz` 외 요청은 인증을 거칩니다. 정적 경로를 CDN에 직접 연결하는 filesystem bypass를 구성하지 않습니다.

## 입력과 포함 목록

| 입력 | 배포 위치·조건 |
|---|---|
| 명시한 `server/*.py`와 `server/openapi.yaml` | 같은 경로. 실행에 필요한 API·deployment·runtime storage·CAS·Blob 모듈만 포함 |
| `data/fixtures/cases.json`, `scripts/demo_openai_env.py` | 같은 경로. 승인 합성 fixture와 환경 어댑터 코드이며 실제 env 파일은 제외 |
| `pyproject.toml`, `uv.lock` | 원본 바이트 보존. Python 3.12 제약 확인. 설치 명령은 `uv sync --frozen --no-dev` |
| `deploy/vercel/index.py`, `deploy/vercel/vercel.json` | 각각 `api/index.py`, `vercel.json` |
| `apps/web/out` | 정해진 root entry와 `_next/static` 허용 확장만 포함. 소스맵·실행 파일·미허용 파일은 거절 |
| 승인 합성 미디어 | manifest SHA256와 public 원본·out 사본을 모두 대조해 out와 `apps/web/public/demo`에 각각 포함 |
| 생성 manifest | 배포 파일별 상대경로·크기·SHA256, 원본 SHA·FE 지문·총 바이트·미검증 범위 기록 |

필수 정적 파일은 index.html, 404.html, index.txt, cases.json, JS/CSS 자산 각 1개 이상 및 세 기본 미디어입니다. 심볼릭 링크·Windows junction·경로 이탈은 파일뿐 아니라 모든 상위 구성요소에서 거절합니다. 파일명과 정적 텍스트의 명백한 credential 패턴을 검사하되 비밀값을 오류에 출력하지 않습니다.

승인 media manifest는 저장소의 **`data/demo-media-manifest.json` 정본 하나만** 받습니다. 기존 초안의 별도 schema는 폐기하며 `schemaVersion=1`, `repository=cjj0202-glitch/happycall-ralphthon`, `assets=[{name,bytes,sha256,synthetic}]` 계약을 따릅니다. `CASE-0001.wav`, `CASE-0002.wav`, `sorter-demo.mp4`가 중복 없이 정확히 있어야 하며 모든 synthetic은 true, bytes는 양의 정수, sha256은 64자리 hex여야 합니다. public 원본·out 사본을 크기와 SHA256으로 모두 대조합니다. 실미디어나 manifest를 이 작업에서 갱신하지 않습니다.

## 낡은 빌드 방지

기본 실행은 빌드 완료 서명 `.oneflow-build.json`이 없으면 중단합니다. 서명에는 성공 상태, 빌드 명령, 전후 FE source SHA256, out 파일 전체 지문을 담습니다. 패키징 시 현재 소스와 out를 다시 계산해 대조합니다. 이것은 로컬 완료 기록이며 암호학적 작성자 서명이 아닙니다.

선택적 `--build`는 npm build 성공과 소스 지문의 전후 일치를 확인한 뒤 **완료 기록만** 만듭니다. 패키지는 별도 기본 실행에서 만듭니다. 기존 완료 기록은 빌드 시작 때 무효화하고 실패·소스 변경 때 정상 완료로 바꾸지 않습니다. `NEXT_PUBLIC_API_BASE`는 빈 문자열로 강제해 같은 origin으로 빌드하고 npm 자식 환경에 서버 비밀값을 전달하지 않습니다. Next가 자동으로 읽는 apps/web/.env* 파일은 내용 열람 없이 거절합니다. 메인만 실제 npm build를 수행하며 이 작업은 subprocess mock과 임시 합성 산출물로 검증합니다. 완료 기록은 검증값의 checksum을 포함하지만 암호학적 작성자 서명은 아닙니다.

FE 지문은 app/components/lib/scripts/public의 파일과 root의 TS/JS/JSON/CSS 설정·lock을 포함합니다. Next가 생성하는 `next-env.d.ts`, `.next`, `.next-dev`, out, node_modules, .checks, tsbuildinfo는 제외합니다. 명시한 소스 폴더의 숨김/비밀파일·링크는 거절하며 내용·상대경로를 함께 해시합니다. 서버/런타임 파일은 패키징 때 별도 전체 inventory로 검증하고 복사 도중 변화를 다시 대조합니다.

패키징 검증 실패는 완료 manifest를 만들지 않습니다. 쓰기 도중 오류가 나면 새로 생성한 불완전 폴더를 보존하며, 기존 산출물과 불완전 폴더 모두 다음 실행에서 덮어쓰지 않습니다. `.bundle-manifest.json`은 모든 파일 복사·해시·입력 재검증을 마친 뒤 마지막에 생성합니다.

## 용량과 배포 한계

후보 설정은 모든 route를 `/api/index.py`로 보내고 함수 maxDuration을 240초로 지정합니다. 계정별 실제 허용 여부는 별도 확인 대상입니다. Python 함수는 기본적으로 빌드에 도달한 프로젝트 파일을 포함하며, 표준 비압축 번들 제한은 500 MB입니다. 패키저는 입력 바이트에 이 한도를 적용하고 파일 목록을 기록하지만, 설치될 Python 패키지와 생성 bytecode를 포함한 최종 크기는 Vercel 실제 빌드에서 다시 확인해야 합니다. [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python), [설정 문서](https://vercel.com/docs/project-configuration/vercel-json), [함수 실행시간](https://vercel.com/docs/functions/configuring-functions/duration).

## 수용 검사

임시 repo와 합성 media/out로 정상 자기완결성, media 변조, symlink/junction, 비밀 파일·credential 패턴, 미허용 정적 파일, 필수 누락, 완료 기록 누락·소스 변경·out 변경, 용량 초과, 기존 산출물 보존을 검사합니다. 성공 폴더의 전체 파일과 manifest의 크기·해시를 대조합니다. 인증과 cloud state/ledger guard 자체는 해당 담당자의 테스트 결과로 인수하며 이 패키징 테스트가 대체하지 않습니다.

## 구현과 검증 결과

2026-09-21 18:19 KST pc1 CJJ에서 구현·합성 검증을 완료했습니다. 소유 파일은 `scripts/build_deployment_bundle.py`, `deploy/vercel/index.py`, `deploy/vercel/vercel.json`, `tests/test_deployment_bundle.py`, 이 문서입니다. 실제 npm·실미디어·정본 media manifest·계정·원격 배포는 변경하지 않았습니다.

| 검사 | 실측 |
|---|---|
| `.venv/Scripts/python.exe -m pytest tests/test_deployment_bundle.py -q` | **55 passed**, 61.54초 |
| 기존 인수 계약 | 최초 43/43 통과 후 빌드 mock·라우팅·자가완결성·변이 검사 추가 |
| 격리 번들의 실제 코드 import/ASGI | 별도 Python `-I -B` 프로세스, 원본 repo가 import 경로에 없는 임시 번들에서 모든 server/scripts 모듈 위치가 번들 내부임을 확인. 공개 health 200, 미인증 화면/미디어/API 401, 인증 화면 200, MP4 Range 206, unknown API 404 |
| npm mock | 성공 때 완료 기록만 생성, 실패/소스 변경 때 이전 기록 제거와 새 기록 거부, 서버 키·Blob token·접근 암호를 자식 환경에 전달하지 않음, 실패 stdout/stderr 원문 비노출 |
| 변이 대조 | 동일 위치·구조의 무변이 CONTROL 4/4 통과. credential 검사 제거·FE 소스 지문 결합 제거·media hash 검사 제거·정적 우회 라우팅 허용 변이 **4/4 탐지** |

Windows 파일 symlink 2건은 OS가 `WinError 1314`로 생성 자체를 거부하여 해당 테스트가 동일 바이트의 정상 파일에 `Path.is_symlink` 판정을 합성 주입했습니다. junction 3건도 합성 판정으로 검사했습니다. 이 5건은 링크 감지 분기·상위 경계 검증이며 **실물 Windows 링크 검증은 미실행**입니다. 최종 호스트에서 실제 symlink/junction(해당 OS)을 추가 검증해야 합니다. 테스트는 실제 `.env`/로컬 저장소/유료 API에 접근하지 않았습니다. 입력 크기 경계는 설치 의존성을 제외한 payload의 정확한 바이트 수와 1바이트 부족 한도를 각각 실행했습니다.

Vercel 공식 문서에서 `/api` 안 Python 파일의 `app` ASGI 진입점과 `functions` 설정을 확인했습니다. [Python API directory](https://vercel.com/docs/functions/runtimes/python/api-directory). 모든 route를 단일 함수로 먼저 보내며 filesystem handler·rewrites·정적 outputDirectory를 허용하지 않는 로컬 설정을 검증했습니다. 실제 Vercel 빌드가 원래 요청 경로·Range·Basic 인증을 보존하는지는 배포 후 검증 대상입니다. [Routes configuration](https://vercel.com/docs/build-output-api/configuration).

## 메인 실행 명령과 완료 경계

메인은 UI·media·정본 manifest가 확정된 상태에서 아래 첫 명령을 실행합니다. 성공해도 패키지를 만들거나 배포하지 않으며 `apps/web/out/.oneflow-build.json`만 완료 기록으로 추가합니다.

```text
.venv/Scripts/python.exe scripts/build_deployment_bundle.py --root C:/00.프로젝트/happycall-ralphthon --build
```

성공 후 별도로 패키지를 생성합니다. 기본 manifest는 정본 경로이며 다른 파일을 지정하면 거부합니다. 이 명령의 Git 사용은 HEAD SHA 읽기 1회이며 커밋·상태 변경을 하지 않습니다.

```text
.venv/Scripts/python.exe scripts/build_deployment_bundle.py --root C:/00.프로젝트/happycall-ralphthon
```

결과는 `dist/deployment/<UTC시각>-<HEAD앞12자리>`의 새 폴더입니다. `.bundle-manifest.json`의 status=complete와 파일별 size/SHA256을 확인한 다음 그 폴더만 호스트 입력으로 사용합니다. `.env`, `.local`, `.git`, 원천자료, 원본 JSONL, 개발 의존성을 더 넣지 않습니다. 현재 원격 Blob 권한 403 상태를 이 로컬 패키징 성공으로 해소했다고 표현하지 않습니다. 실제 provider build·의존성 포함 최종 용량·HTTPS/라우팅·브라우저 인증/미디어·cloud storage·실모델·배포 완료는 별도 확인이 필요합니다.
