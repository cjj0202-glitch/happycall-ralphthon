# 배포 준비 조사 — 현재 구성과 완료 게이트

작성: 2026-09-21 17:43 KST · 관측 PC: pc1/CJJ · 읽기 전용 조사자: deployment_readiness

기준 HEAD: `8c7521f97d9c8cab380b76785648159d7746e8e8`. 이 보고서는 배포·인증 완료 보고가 아닙니다. 메인이 전달한 최신 사용자 지시(9/22 오전 9시까지 배포, 별도 승인 질문 없이 진행)를 현재 권한 기준으로 삼았습니다. 기존 Vercel 보류 문구는 메인이 DEC-018로 정리할 예정이며, 본 작업자는 이 파일만 작성했습니다.

## 핵심 판정

현재 코드를 `apps/web`만 Vercel에 올리면 화면은 정적 배포할 수 있지만 접수·분석·이관·센터 회신 전체 흐름은 완료되지 않습니다. 브라우저 API 주소가 `127.0.0.1:8100`이고 서버는 로컬 파일에 케이스와 예산을 저장합니다. Python ASGI 자체는 Vercel 지원 범위이나, 저장소·환경변수·미디어·공개 API 연결을 조정해야 합니다.

현재 차단은 ① CLI 인증 미완료 ② G-28/G-23 대상 불일치의 원천 확인 ③ 영속 API 실행 경로 미구성입니다. 로그인 허용과 로그인 성공은 다른 상태입니다. 팀·프로젝트는 아직 실제 목록으로 확인하지 못했으므로 어느 프로젝트에도 연결하지 않았습니다.

## 1. 실제 확인 결과

| 항목 | 관측 결과 | 근거 |
|---|---|---|
| 작업 신원 | pc1, CJJ, GitHub cjj0202-glitch | `python channel/whoami.py`, 17:39 KST |
| CLI 설치 | Vercel 59.23.2, Node 24.18.0 | `vercel --version`, `vercel whoami` |
| CLI 경로 | `C:/Users/choi8/AppData/Local/Programs/nodejs/vercel.ps1` | `Get-Command vercel` |
| CLI 인증 | `loggedIn:false`, `reason:login_required`, `credentialSource:saved_login` | 실제 `vercel whoami` 결과 |
| 팀·프로젝트 목록 | 조회 불가; 인증된 조회 결과 없음 | 아래 자동 로그인 부작용 기록 |
| 로컬 프로젝트 링크 | 조사한 저장소 루트 및 `apps/web`의 `.vercel/project.json` 2개 경로에서 파일 미관측 | `Get-Item` 명시 경로 검사; 다른 디렉터리 링크 부재까지 주장하지 않음 |
| 프런트엔드 | Next 15.5.25, React 19.1.4, `output:'export'`, `out/` 산출 | `apps/web/package.json`, `next.config.ts`, README |
| API | Connexion `AsyncApp`를 CORS로 감싼 ASGI `server.app:app` | `server/app.py`, `pyproject.toml` |
| Python 버전 | 배포 의존성 선언 `>=3.12,<3.13`; PATH 기본 Python은 3.14 경로 | `pyproject.toml`, `Get-Command python`; 실제 프로젝트는 uv 3.12 환경 사용 전제 |
| 케이스 저장 | `.local/cases-store.json`, 파일 잠금과 atomic replace | `server/repository.py` |
| 예산 저장 | `.local/demo-usage.json`, $30 예약 상한/$25 경고 | `server/budget.py`; 공급자 실청구 잔액이 아님 |
| API 기본 주소 | `NEXT_PUBLIC_API_BASE`가 없거나 빈 문자열이면 `http://127.0.0.1:8100` | `apps/web/lib/api.ts` |
| CORS | `http://localhost:3100`, `http://127.0.0.1:3100`만 허용 | `server/app.py` |
| 서버 키 읽기 | `.env.demo.local` 파일만 파싱, 호스팅 환경변수 읽기 없음 | `scripts/demo_openai_env.py` 코드만 읽음; `.env` 내용은 읽지 않음 |

인증 조사 중 `vercel teams list`가 자격증명 없음에서 자동으로 device 로그인 대기를 시작했습니다. 즉시 해당 명령에 Ctrl+C를 보내 종료했고 종료코드 1을 확인했습니다. 브라우저 열기·이메일/OTP 발송 요청·코드 입력·인증 승인·팀/프로젝트 변경·배포는 하지 않았습니다. device code나 토큰은 이 보고서에 기록하지 않습니다. 이후에는 `whoami`가 성공한 뒤에만 팀·프로젝트 조회를 실행해야 합니다.

## 2. G-28과 기존 g-23의 근거 차이

| 근거 | 실제로 말하는 내용 | 판정 |
|---|---|---|
| 메인의 이번 위임 | 최신 팀 G-28과 기존 문서 g-23의 차이를 확인할 것 | 최신 입력이지만 이 조사자에게 팀 등록 원본은 주어지지 않음 |
| `docs/12_Vercel_행사계정_연결.md` | 사용자 메일에서 G-23을 확인했다고 기록, 프로젝트 g-23 지정 | 과거 기록; 이번 최신 팀 정보와 상충 |
| `docs/official/2026-09-21/vercel-guide.dom.txt` 25~28행 | G-21~44 → hackathon02 그룹/프로젝트 g-21~44 | 두 후보 모두 같은 그룹 계정 범위 |
| 같은 공식 캡처 본문 55행 | 팀 번호와 같은 이름의 프로젝트만 사용 | 특정 팀이 23인지 28인지 식별하지 않음 |
| docs/planning/reports, GOAL, PROMPT 검색 | g-23/G-23 기록은 확인, G-28/g-28 기록은 미관측 | 검색 범위 내 결과이며 사용자 원본·다른 경로까지 부재라고 판단하지 않음 |
| Vercel 실제 프로젝트 | 인증 미완료로 미조회 | 두 프로젝트 존재·소유·연결 모두 미확인 |

따라서 사용자 팀 등록 원천/최신 직접 지시와 행사 프로젝트 목록을 메인이 대조한 뒤 정확히 한 기존 프로젝트만 연결해야 합니다. G-28이면 공식 규칙에 따라 g-28이 대응하는 것은 추론 가능하지만, 현재 보고서가 실제 프로젝트 소유 확인을 대신하지 않습니다. g-23에 먼저 연결하거나 새 프로젝트를 생성해 해결하지 않습니다.

## 3. 배포 경로와 최소 변경

| 경로 | 기술적 가능성 | 최소 변경·조건 | 현재 판정 |
|---|---|---|---|
| 기존 Vercel 프로젝트에 정적 Next + 별도 영속 HTTPS API | 현재 FE/BE 분리를 유지. 지속 디스크가 있는 단일 API 인스턴스면 기존 Json/FileLock 구현을 유지할 수 있음 | 공개 API URL, HTTPS, 정확한 FE origin CORS, 비밀정보를 출력하지 않는 서버 설정, 서버 재시작/동시 접근 검증. 별도 호스트 존재와 접근은 미확인 | 사용 가능한 승인 호스트가 실제 있으면 변경량이 가장 작음 |
| 기존 Vercel 한 프로젝트에 Next + Python Services | 공식 Services가 FE/BE를 한 도메인으로 라우팅. Connexion ASGI용 entrypoint 명시와 Preview 실증 필요 | 서비스별 root/build, `/api/*` 우선 라우팅, 공유 영속 저장소(§7 Blob 조건부 쓰기 후보), 환경변수 loader, 미디어 포함, 함수 시간 한도 | 전체 클라우드 경로로 가능하지만 현재 미구현·미배포 |
| 정적 Next만 배포 | 정적 자산 표시 및 사용자가 고른 읽기 전용 합성 예시 열람 가능 | 정적 파일·미디어 확보, API 미연결 상태 표시 | 중간 Preview/백업. 접수·저장·이관·최종회신 완료로 계산 불가 |

Services는 공식 문서상 모든 플랜에서 Beta이며 한 프로젝트의 여러 서비스를 독립 빌드하고 `vercel.json` rewrites로 공개합니다. 서비스 설정을 쓰면 build/runtime 설정의 위치도 서비스별로 이동합니다. 현재 저장소에는 배포 설정이 없으므로 예시 설정을 검증 없이 정본으로 복사하지 않습니다. 기존 `apps/web` Root Directory 안내도 전체 서비스 구성 시 다시 맞춰야 합니다. [Vercel Services 공식 문서](https://vercel.com/docs/services)

Python 런타임은 ASGI/WSGI와 명시 entrypoint를 지원하며 Python 3.12를 지원합니다. 현재 `server.app:app`를 지정하는 배포 진입점을 만들 수 있습니다. 다만 Connexion 자동 인식·OpenAPI YAML 포함·handler import 경로는 실제 build/Preview에서 확인해야 합니다. Python 번들은 자동 tree-shaking이 없고 표준 크기 한도는 비압축 500MB입니다. 서버 의존 파일·합성 fixture·필요 WAV만 포함하고 사용자 원천자료, `.env*`, `.local`, 원본 로그, 개발 캐시를 패키지에서 제외해야 합니다. [Vercel Python 런타임](https://vercel.com/docs/functions/runtimes/python)

필수 수정은 다음과 같습니다.

1. FE API base: 공개 HTTPS URL 또는 같은 origin 상대경로를 지원합니다. 현재 `||` 때문에 빈 `NEXT_PUBLIC_API_BASE`를 설정하는 것만으로는 상대경로가 되지 않습니다. 정적 Next의 공개 변수는 빌드 시 반영하므로 값 변경 후 재빌드합니다. 연결 실패 문구의 로컬 서버 표현도 배포 모드에 맞춥니다.
2. 저장소: Vercel 경로라면 `CaseRepository` 인터페이스 뒤에 공유 영속 저장 구현을 둡니다. `expectedRevision` 충돌 검사·revision 증가·저장을 원자적으로 처리하며, 분석 중 동시 수정 검사도 유지합니다. 단순 read→write JSON/Blob 전환만으로는 동시성을 보장하지 않습니다. §7에서 확인한 Blob ETag 조건부 쓰기는 검토 가능한 대안입니다.
3. 예산: 케이스와 별도로 예산 예약도 공유 저장소의 원자 연산으로 전환합니다. 로컬 FileLock를 `/tmp`로 옮기면 인스턴스마다 $30 상한이 다시 시작하므로 예산 보호가 사라집니다. 실패·timeout 예약을 되돌리지 않는 현재 계약을 유지합니다.
4. 서버 설정: `.env.demo.local` 전용 reader에 명시적으로 허용한 서버 환경변수 경로를 추가할 수 있습니다. 현재 값/원천 키 파일의 외부 업로드는 이 조사 범위에 포함하지 않습니다. 실제 서버 비밀 설정과 정책 충족 여부는 메인이 별도 확인하며 값을 로그·문서·브라우저 번들에 노출하지 않습니다.
5. 접근: `X-Demo-Role`은 클라이언트가 보내는 합성 시연 역할로 실제 인증이 아닙니다. 비용이 발생하는 live API를 공개하기 전 배포 접근 제어와 심사 접근 방법을 정합니다. CORS 설정만으로 서버 호출 권한을 통제했다고 표현하지 않습니다.
6. 미디어: 클라우드 빌드가 아래 3개 합성 자산을 manifest 크기·SHA로 확인하고 포함해야 합니다. 현재 download 스크립트는 인증된 `gh`를 사용하므로 Vercel 빌드에서 그대로 실행 가능하다고 가정하지 않습니다. 공개 Release HTTPS 다운로드 또는 이미 검증된 배포 산출물 주입 방식을 선택해 확인합니다. STT용 WAV는 FE 공개 폴더뿐 아니라 API 서비스에서도 읽을 수 있어야 합니다.

Vercel Functions의 로컬 저장소는 영속 공유 저장소가 아니며 여러 인스턴스 간 공유되지 않습니다. 이는 현재 파일 기반 케이스와 예산에 직접 해당합니다. 임시 파일 성공이나 한 인스턴스 재조회 성공은 해결 증거가 아닙니다. [Vercel 영속 저장 설명](https://vercel.com/kb/guide/is-sqlite-supported-in-vercel)

## 4. 미디어·시간·요청 제약

| 로컬 자산 | 바이트 | 이번 로컬 SHA 대조 |
|---|---:|---|
| CASE-0001.wav | 2,263,244 | manifest 일치 |
| CASE-0002.wav | 2,378,444 | manifest 일치 |
| sorter-demo.mp4 | 1,097,133 | manifest 일치 |
| 합계 | 5,738,821 | 3/3 일치 |

`Get-FileHash -Algorithm SHA256`로 실제 로컬 3파일을 manifest와 대조했습니다. `data/demo-media-manifest.json`에는 17:25:46 KST Release 공개·3/3 독립 다운로드 검증이 기록돼 있습니다. 이번 조사에서는 원격 다운로드를 다시 실행하지 않았습니다. `.gitignore`의 WAV/MP4 제외 때문에 소스만 받은 클라우드 빌드에는 이 파일들이 자동으로 들어오지 않습니다.

Vercel Function 요청·응답 body는 4.5MB 한도입니다. 현재 `/analyze`는 mode JSON을 받고 서버가 WAV를 읽으므로 브라우저→함수의 대형 음성 업로드는 없습니다. 미디어는 정적 자산 경로로 제공하고 향후 업로드를 추가하면 별도 객체 저장 직접 업로드를 검토해야 합니다. [Functions 한도](https://vercel.com/docs/functions/limitations)

현재 공식 실행시간은 Fluid 기준 기본 300초, Pro/Enterprise 일반 최대 800초, 지정 조건의 Beta 최대 1,800초입니다. 실제 계정 플랜/Fluid/함수 설정은 아직 확인하지 못했습니다. 현재 FE 분석 timeout은 120초이고 SDK timeout은 호출당 90초이며 STT와 정제가 순차 실행됩니다. 따라서 함수 최대 시간만 늘려도 브라우저 120초 중단 문제는 해결되지 않습니다. 합성 두 케이스의 실측에 맞춰 전체 deadline·진행 표시·중복 호출 방지를 검증해야 합니다. [함수 실행시간 공식 문서](https://vercel.com/docs/functions/configuring-functions/duration)

CLI 소스 업로드 총량은 Hobby 100MB/Pro 1GB 기준입니다. 위 미디어 합계와 별개로 실제 배포 파일 전체를 검사해야 합니다. Enterprise는 공식 표가 N/A로 표시하므로 무제한이라고 해석하지 않고 실제 프로젝트 제한을 확인합니다. [Vercel 플랫폼 한도](https://vercel.com/docs/limits)

## 5. 배포 후 인수 게이트

아래 각 항목은 `PASS / FAIL / 판정 불가`와 Preview URL, SHA, 실행 시각, 입력, 기대값, 실측을 기록합니다. 아직 실행하지 않은 항목은 전부 미검증입니다.

| 게이트 | 실행과 완료 조건 |
|---|---|
| 대상·인증 | `whoami` 성공 → 실제 워크스페이스/팀 ID → 사용자 팀 번호와 기존 프로젝트 ID 일치 → 최종 `.vercel/project.json` 대조. 다른 프로젝트 변경 없음 |
| 빌드·비밀 범위 | 배포 SHA와 소스 SHA 연결, Python 3.12·FE build 성공, 금지 파일 제외와 공개 JS에 비밀 없음 확인. 정적 자산 목록을 실제 산출물 기준으로 확인 |
| 라우트·접근 | 심사와 동일한 인증 세션에서 `/`, `/api/health`, `/api/cases`, 없는 경로를 함께 요청. 없는 경로까지 401이면 라우트 미등록으로 판정하지 않음. health 200의 본문·runtime·budget까지 대조 |
| 브라우저 연결 | 네트워크 요청이 배포 HTTPS origin/API로 향하며 localhost 호출·혼합 콘텐츠·CORS 실패 없음. 390/921/1440px 핵심 화면과 JS console 확인 |
| 미디어 | 공개 URL 3/3 GET 성공·크기/SHA 일치, 두 WAV의 종료 이벤트와 MP4 재생·seek 확인. 404/재생 오류 안내, 케이스 변경 초기화 확인 |
| 영속 저장 | 신규 텍스트 접수→이관→센터 중간/최종 회신→경영주 조회. 다른 브라우저 및 새 함수 인스턴스/재배포 뒤 같은 결과 유지. 스토어 초기화가 명시 행동 외 발생하지 않음 |
| 동시성 | 같은 revision의 동시 수정 2개 중 한 개 성공/다른 한 개 409; expectedRevision 누락 428. 분석 도중 변경된 케이스를 낡은 결과가 덮어쓰지 않음 |
| 예산 | 동시 live 예약이 단일 공유 상한을 초과하지 않음. timeout/실패 예약 유지, 경고·상한 오류 표시. 모의 입력으로 경계를 검사하고 실제 유료 호출 횟수·실측은 별도 기록 |
| 실제 AI | 합성 음성 재생 종료→실제 STT→정제, 원문·AI 제안·사람 수정 구분. 실패 때 replay로 조용히 전환하지 않음. 키 없음/정책 없음/응답 지연/오류 동작 |
| 사용자 완료 | 미도착·오출고 각각 3회, 총 6/6 같은 배포 완주; 20입력 정확도/12경계는 기존 평가 분모를 따로 기록. 원인 미확인을 확정으로 바꾸지 않고 최종 회신·잔여 조치 기준으로 종결 |
| 시연 접근 | 심사자가 접근 가능한 실제 링크·보호 방식 확인, 재시작/오류 복구·읽기 전용 백업 표시, 실제 사람 검증과 AI 자동 검증을 구별 |

## 6. 메인 후속 작업

1. 최신 팀 번호 원천을 대조하고 기존 프로젝트 대상을 확정합니다. 과거 g-23 문서는 정정 이력으로 보존합니다.
2. 메인이 허용된 로그인 흐름을 한 번 수행하고 `whoami` 성공 뒤 팀/프로젝트를 조회합니다. 이번 조사에서 인증 완료·계정 제한 해제는 확인되지 않았습니다.
3. 실제 사용할 영속 API 호스트/공유 저장소가 있는지 확인하고 위 경로 중 하나를 선택해 구현합니다. 공개 사이트에서 localhost 서버가 자동 연결된다고 가정하지 않습니다.
4. Preview를 먼저 만들고 위 게이트의 실제 결과를 `reports/vercel-preview.md` 등에 남긴 후 최종 배포를 판정합니다.

본 조사에서 변경한 파일은 이 보고서 1개입니다. 제품 코드·인증 설정·Vercel 프로젝트·배포·환경변수·원천자료는 변경/업로드하지 않았고 `.env` 파일 내용은 읽지 않았습니다. CLI 자동 로그인 대기 시작/즉시 종료 부작용은 §1에 기록했습니다.

## 7. 추가 조사: 기존 Vercel Blob으로 CAS 저장 구현

메인 요청에 따라 외부 Postgres/Redis 계정을 새로 만드는 대신 기존 Vercel 서비스 안에서 해결할 수 있는지 확인했습니다. 결론은 **Blob 자체는 가능하나 Python SDK의 쓰기 기능 차이를 처리해야 합니다.** 아래는 공식 문서와 공개 SDK 소스 확인이며 실제 store/API 호출 성공 증거는 아닙니다.

| 확인 대상 | 확인한 사실 | 적용 판단 |
|---|---|---|
| 조건부 쓰기 | `put/copy/del`의 `ifMatch`에 ETag를 넣으면 현재 ETag와 일치할 때만 쓰고 불일치 때 `BlobPreconditionFailedError` | 케이스·전역 예산 각각 JSON blob CAS 후보 |
| 최신 읽기 | private `get(useCache:false)`는 origin 최신 내용을 반환. 기본 CDN 경로는 overwrite 후 최대 60초 지연 | CAS 입력의 본문과 ETag를 같은 원본 GET 결과로 얻어야 함 |
| Python 일반 지원 | private storage는 `vercel>=0.5.0`, Python `>=3.10` | 프로젝트 Python 3.12와 버전 범위는 양립 |
| Python CAS 쓰기 | 공개 `vercel-py` main의 동기/비동기 `put()` 서명에 `if_match` 없음. `get()`에는 `use_cache`·`if_none_match` 존재 | Python SDK 설치만으로 조건부 put이 된다고 판단 불가 |
| TS SDK 실제 구현 | `ifMatch`를 HTTP `x-if-match`로 변환하고 overwrite 허용. `precondition_failed`를 전용 오류로 매핑 | TS SDK CAS 어댑터가 가장 직접적으로 문서화된 경로 |
| 직접 HTTP | 공식 private 문서는 인증 헤더로 직접 GET하는 방법을 설명. 조건부 PUT의 wire header는 공식 SDK 소스에서 확인 | 독립 공식 REST 계약은 미확인. Python 직접 HTTP 어댑터는 실서비스 검증 전 지원 완료 주장 불가 |

조건부 쓰기와 캐시 설명: [Blob 개요](https://vercel.com/docs/vercel-blob), [Private storage 최신 읽기](https://vercel.com/docs/vercel-blob/private-storage#consistent-reads). SDK 옵션·ETag 응답: [Blob SDK 참조](https://vercel.com/docs/vercel-blob/using-blob-sdk).

소스 대조는 `gh api`로 공식 공개 저장소를 읽었습니다. Python 기준 SHA `532bc6e4c7fdb857cd3ce20ece10e6b42c45ee61`의 [client.py](https://github.com/vercel/vercel-py/blob/532bc6e4c7fdb857cd3ce20ece10e6b42c45ee61/src/vercel/blob/client.py), TS 기준 SHA `8817cbad75d009fedebd33fb46748c2c0200ea46`의 [put-helpers.ts](https://github.com/vercel/storage/blob/8817cbad75d009fedebd33fb46748c2c0200ea46/packages/blob/src/put-helpers.ts)·[api.ts](https://github.com/vercel/storage/blob/8817cbad75d009fedebd33fb46748c2c0200ea46/packages/blob/src/api.ts)를 확인했습니다. 로컬 SDK 설치나 dependency 변경은 하지 않았습니다.

Provisioning 조건은 다음과 같습니다. Blob은 모든 플랜에서 가능하고 owner/member/developer 역할이 접근할 수 있습니다. 올바른 기존 프로젝트에 연결한 뒤 private store를 생성하고 Production/Preview 연결 범위를 지정합니다. Vercel의 프로젝트 연결은 store ID와 OIDC 환경변수를 관리하며, 서버 SDK가 인증정보를 처리하는 구성이 가능합니다. 이 계정의 실제 역할·store 생성 권한·이용 한도/요금·OIDC/Python 호환은 인증 후 실측해야 합니다. 별도 외부 공급자 계정은 공식 생성 절차에 요구되지 않습니다. [공식 생성 절차](https://vercel.com/docs/vercel-blob/manage-blob-storage), [기능 역할과 프로젝트 연결](https://vercel.com/docs/vercel-blob/using-blob-sdk)

권장 설계는 작은 private JSON 문서를 원본 GET→본문 검증→ETag 조건부 PUT으로 갱신하는 것입니다. 케이스는 사용자가 읽은 revision과 저장 revision을 대조하고, 충돌을 무조건 최신값으로 덮어쓰지 않습니다. 예산은 동일 공급자 키를 쓰는 모든 배포가 하나의 전역 ledger를 공유하고, 예약 성공 뒤에만 유료 API를 호출합니다. CAS 재시도는 원본을 다시 읽고 한도를 다시 계산하며 제한된 횟수 후 오류로 끝냅니다. 예산 blob의 미존재·손상·저장 실패를 $0으로 해석해 호출을 허용하지 않습니다. 초기 생성에는 overwrite 금지 경쟁 제어가 필요하고, 케이스/예산 두 문서 사이의 다중 문서 트랜잭션이 생겼다고 주장하지 않습니다.

실환경 필수 증거는 ① 같은 ETag로 두 쓰기 중 정확히 한 개 성공 ② 바로 재조회한 본문/ETag 일치 ③ 최초 생성 경쟁 시 한 개만 생성 ④ 예산 한도 근처 동시 예약의 초과 0건 ⑤ cold start/재배포 뒤 유지 ⑥ 잘못된 credential/저장 오류 때 live 호출 0건입니다. 이 증거 전에는 Blob 경로를 완료로 표시하지 않습니다.
