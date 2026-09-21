# 실제 Vercel Preview 검증 — 읽기 전용 범위

2026-09-21 pc1/CJJ, 대상 52g Studio / g-28. **Preview의 화면·음성·영상은 실제 URL에서 검증했습니다. 영속 저장이 연결되지 않아 접수/이관/회신 저장과 클라우드 실모델 호출은 미완료입니다.**

## 배포와 실제 target 대조

패키지: `dist/deployment/20260921T093023172612Z-3c5e5a35dff7`. 소스 기준 `3c5e5a35dff7afb3a8c59bd93814bd1699d9915a`, 입력 53파일 12,630,082 B, manifest 포함 CLI 업로드 목록 54파일. 원천자료·로컬 원장·비밀파일은 포함하지 않았습니다. Python 3.12, uv.lock 설치·bytecode 컴파일이 원격 빌드에서 성공했고 첫 함수 산출물은 inspect 기준 **31.66 MB**였습니다.

1. `vercel deploy --target preview ...` 첫 실행은 요청 의도와 달리 실제 응답이 **target=production**이었고 `g-28.vercel.app`·`g-28-52g-studio.vercel.app` 별칭을 받았습니다. ID `dpl_3GvnMRm8L2ktwhCRssERtzwK5iYp`. Preview 환경에만 접근 비밀값이 있어 이 첫 배포의 실제 health는 500이었습니다. 실행 로그에서 `ONEFLOW_ACCESS_USER/PASSWORD` 구성 오류를 확인했습니다. READY를 제품 정상으로 판정하지 않았습니다. 이 Production 별칭은 최종 검증 URL이 아닙니다.
2. Preview에 `--skip-domain`을 추가하려던 명령은 CLI가 Production 전용 옵션이라며 배포 전에 거부했습니다. 코드/데이터를 변경하지 않았습니다.
3. 같은 파일의 후속 `--target preview` 실행은 CLI **Preview**, API target=null, READY로 반환됐습니다. ID `dpl_ByC9km4G9rUevPYUu5pHVmLNjG6N`, URL [읽기 전용 Preview](https://g-28-arxz4aubg-52g-studio.vercel.app). 이 응답과 실제 요청을 기준으로 검증했습니다.

실행 원문과 실패 로그는 `.local/vercel-preview-deploy*.json`, `.stderr`, `.local/first-deployment-errors.json`에 보존합니다. CLI target의 요청과 실제 결과를 항상 대조해야 합니다. [공식 CLI 배포 문서](https://vercel.com/docs/cli/deploy), [Python 런타임](https://vercel.com/docs/functions/runtimes/python).

## 접근·API·Range 실측

Preview 환경에는 공유 데모 접근 user/password와 `ONEFLOW_STORAGE_BACKEND=vercel-blob`만 설정했습니다. 기존 원장이 준비되지 않았으므로 OpenAI 키를 올리지 않았습니다. 개인 접근정보는 `.local/deployment-access.json`이며 Git 제외입니다. Vercel 프로젝트 보호 `all_except_custom_domains`를 유지했습니다.

공식 `vercel curl`이 프로젝트의 자동화 접근 토큰을 생성한 뒤 이를 사용해 앱 경계를 검사했습니다. 이 토큰과 Basic 인증은 로컬 검사 설정에서만 읽고, 브라우저 검사는 확인한 Preview origin에만 헤더를 보내도록 제한했습니다. 프로젝트 보호를 끄거나 다른 프로젝트를 수정하지 않았습니다.

| 검사 | 기대/실측 |
|---|---|
| 플랫폼 인증을 통과한 `/healthz`, 앱 Basic 없음 | 200 / `status=ok`, 15 B, no-store |
| 플랫폼 인증을 통과한 `/`, 앱 Basic 없음 | 401 / 12 B |
| 앱 인증 포함 `/` | 200 / 7,634 B HTML |
| 앱 인증 포함 `/api/cases` | 503 / `STORAGE_CONFIG_INVALID`, 162 B |
| 앱 인증 포함 CASE2 WAV Range 0–63 | 206 / 64 B / 로컬 승인 파일 앞 64 B와 일치 |

API 503은 성공한 업무 기능이 아니라 영속 상태 부재 시 요청을 닫는 동작의 확인입니다. Blob 생성403이 해소되지 않았으므로 임시 로컬 JSON이나 새 예산으로 후퇴하지 않았습니다.

별도 무인증 외부 요청도 확인했습니다. Preview `/`는 **302 → `https://vercel.com/sso-api`**, 첫 Production 별칭 `https://g-28.vercel.app/`는 **500 / 96 B / Location 없음**이었습니다. 모든 별칭이 SSO로 보호된다고 일반화하지 않습니다. 첫 Production은 접근 구성 부재로 시작에 실패한 상태이며 사용 가능한 최종 배포가 아닙니다.

## 실제 브라우저

`tests/e2e/cloud-readonly.mjs`를 실제 Preview에서 실행했습니다. 최초 검사는 Next의 숨은 route announcer도 alert로 잡는 locator 중복으로 실패했습니다. 제품 문제가 아니라 검사 범위 오류임을 DOM 두 요소로 확인한 뒤 저장 불가 안내문을 가진 alert로 좁혀 동일 검사를 재실행했습니다. [실패 기록](../e2e/cloud-readonly-2026-09-21T09-37-44.192Z.json)과 [재검증 기록](../e2e/cloud-readonly-2026-09-21T09-37-57.660Z.json)을 모두 보존했습니다.

- 합성 예시 열람 안내·저장 불가를 확인한 상태에서 **2사례 × 5화면 × 3폭(1440/1024/390) = 30뷰**를 검사했습니다. 문서 수평 넘침 0, pageerror 0, 쓰기/분석 요청 0입니다.
- 실제 응답 WAV의 바이트·SHA256을 v2 manifest와 대조한 뒤 두 건을 1배속으로 끝까지 재생했습니다. CASE1 47.15초, CASE2 49.55초, 디코딩 오류 0입니다.
- CASE2 WMS 이벤트 버튼의 합성 CCTV dialog를 열고 12초, 960×540 영상을 끝까지 재생한 뒤 닫았습니다. 영상 오류 0입니다.
- 접수 저장·경영주 제출은 예시 열람에서 비활성화됐습니다. 서버 상태를 바꾸는 요청은 0건입니다.

결과는 **PASS_READ_ONLY_PREVIEW**입니다. 30뷰는 6회 전체 업무 리허설이 아니며, 브라우저 재생은 사람 청취·OS 출력·음성 의미 정확도 검증이 아닙니다. 아직 Production 정상화/승격, Blob 실제 CAS·공유 예산·상담 지속성, 클라우드 실모델, 두 전체 흐름 검증이 남았습니다.
