# 최소 접수 초안 수정본 — 배포 묶음 독립 바이트 검증

2026-09-22 07:52 KST / PC1 `최제준` / 메인 빌드 담당과 별도 검토. **고정 소스의 로컬 배포 묶음 검증은 PASS입니다. Vercel 배포·원격 API·영속 저장·실제 AI 분석 검증을 뜻하지 않습니다.**

- 고정 제품: `ceaf9ffe0ed7907edb051255575bb0b86d5ad943`
- 검증 묶음: `dist/deployment/20260921T224935939491Z-ceaf9ffe0ed7`
- 이전 비교 묶음: `dist/deployment/20260921T220053240866Z-190295f6c10f`
- 완료 stamp: `2026-09-21T22:48:54.684554+00:00` = 9/22 07:48:54 KST, `npm run build`, status=complete, 공개 API base는 빈 문자열로 동일 origin 사용.

## 직접 확인한 파일

패키저 함수를 호출하지 않았습니다. 표준라이브러리 `pathlib/hashlib/json/ast`와 고정 `git show`로 실제 파일을 읽고, manifest·완료 stamp·원본·이전 묶음의 바이트를 비교했습니다.

| 검사 | 결과 |
|---|---|
| manifest payload ↔ 실제 파일 집합·크기·SHA256 | 61/61, 추가·누락0, 12,974,901 B |
| marker 포함 실제 묶음 | 62파일, 12,983,778 B |
| 로컬 Next export ↔ 묶음 export | 27/27 원바이트 동일, 6,881,827 B |
| 프런트 입력 재열거·지문 | 35입력, sourceBefore/sourceAfter/bundle 지문 일치 |
| 출력 지문·build record digest | 실제27파일과 stamp/manifest 일치 |
| 비정적 payload ↔ 작업트리 원본 | 30/30 원바이트 동일, api/index.py·vercel.json 원본 매핑 포함 |
| 비정적 payload ↔ 고정 Git blob | 27/30 원바이트 동일; 나머지3은 CRLF→LF 정규화 후 동일 |
| 승인 미디어 | 4파일 × public/export/묶음public/묶음export = 16/16 크기·SHA256 일치 |
| 바이트 검사 양성·변이 대조 | 정상1/1 수용; 크기·동일크기 바이트·기대크기·기대해시 변형4/4 거절 |

Git 원바이트와 줄바꿈만 다른 파일은 `pyproject.toml`, `server/openapi.yaml`, `uv.lock`입니다. 이를 Git 원바이트30/30이라고 표현하지 않습니다. 완료 stamp 자체와 bundle marker는 검사 전후 원바이트가 같았습니다.

## 이전 묶음과 달라진 부분

같은 경로 중 바이트가 바뀐 파일은 `apps/web/out/404.html`, `index.html`, `index.txt`, `server/request_grounding.py`, `server/request_provenance.py`의5개입니다. Next build ID의 manifest2개와 app page chunk1개는 이전 경로3개를 새 경로3개로 대체했습니다. 미디어는 동일합니다.

서버 payload의 변경은 요청 처리 모듈2개에 한정됩니다. 프런트 `page.tsx`·`workflow.ts`가 고정 제품 blob과 줄바꿈 정규화 후 같고 35입력 지문에 포함됨을 확인했습니다. 새 `page-f64e69499826ddea.js`에는 부서명 매핑 및 `hasOwn` 분기가 포함돼 있습니다. 이것은 제품 기능의 브라우저 재검사가 아니라 새 UI 입력이 이 export로 묶였다는 검사입니다.

| 소스 | SHA256 |
|---|---|
| server/request_grounding.py | `5dc1bfdb294aede851126a73147cb513ac08fc3852b4b6a4ed4a8971c19c005a` |
| server/request_provenance.py | `02d18b82b7ceec3b73630e1a14db9c2e2a011da5e708be8b84bcc3eec4785445` |
| apps/web/app/page.tsx | `531bafcc04967b5d24101e5381e51fc927453fd22ff15012c78cb87acb7ff68e` |
| apps/web/lib/workflow.ts | `ef22af7efc893d945fcfd4e1bb7c5d25e6a17946ab6c21f0b749b32e4c9e5902` |

## 포함 경로와 실제 import

전체 경로 집합에서 `.env`, `.local`, auth/credentials, 접수 저장 파일·예산 원장, node_modules, JSONL, ZIP, private-key 확장자 등 금지 경로를 발견하지 않았습니다. symlink·junction·다중 hardlink도 없었습니다. 원문을 출력하지 않고 일반적인 OpenAI/GitHub/Blob 토큰 및 private-key 표식도 대조했으며 검출0입니다. 이 제한된 패턴 검사를 모든 가능한 비밀 형식의 탐지 보장으로 확대하지 않습니다.

AST에서 server/scripts 로컬 import의 서로 다른 소스파일→모듈 연결44건을 찾아 각 대상 파일이 payload에 존재함을 확인했습니다. 같은 모듈에서 여러 이름을 가져오는 개별 참조까지 세면71건이며 이 두 분모를 혼용하지 않습니다.

추가로 `.venv/Scripts/python.exe -I -B -`에서 bundle만 소스 검색 경로 앞에 넣고 `server.request_provenance`, `server.request_grounding`, `server.live`를 실제 import했습니다. 직접3개와 전이 의존성을 합친 로컬 모듈11개 모두 이 bundle 안의 파일에서 로드됐습니다. Python 격리 모드1·bytecode 쓰기 비활성화 상태였고 원래 저장소 모듈을 빌려오지 않았습니다. 외부 Python 의존성은 현재 설치된 `.venv`를 사용했으며 Vercel의 의존성 설치 검사는 아닙니다.

`vercel.json`의 전체 경로는 `api/index.py`로 연결되며 `outputDirectory`로 정적 라우팅을 우회하지 않습니다. 서버 앱 생성·실행·HTTP 요청은 수행하지 않았습니다.

## 재대조용 지문과 한계

- bundle marker SHA256: `e0261bf159d11463aa13e0c9326484eaa3aebfcca48edffbc6b984d75b4df497`
- payload inventory SHA256: `cb88a10e38cd942c49c8f019e69b4cebeef28149cc300d209d61f4262f8c8ffe`
- frontend source fingerprint: `20af32c58c4bb00303c695913111e763109f43ffbc584ff5ea693e3390a8bde4`
- frontend output fingerprint: `7b61a74de0dde7db2f0e731c04b772951e3411cde7937e215294f63a976d185c`
- build record digest: `8bfa9abbe899572974b861c023c92040fe9289efa2a41ad9accc997c2a670aee`

검토자는 제품·묶음·미디어를 수정하거나 새 build/package를 실행하지 않았습니다. 네트워크·클라우드·인증·키·원장·유료 API·알림 전송에 접근하지 않았으며 생성한 파일은 본 보고서 하나입니다. Vercel 계정/저장소 권한, 공급자 빌드와 최종 의존성 크기, HTTPS 접근 및 실제 AI 호출은 별도 미검증으로 남습니다.
