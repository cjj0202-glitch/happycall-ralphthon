# 최신 보호 Preview 배포와 HTTP 검증

2026-09-22 03:47~04:01 KST · pc1/CJJ · 52g Studio / g-28

[최신 Preview](https://g-28-lg9o6yhjv-52g-studio.vercel.app)에 고정 `3cf7b0a9764a7916d79922ca43ba9e1dd638eadf`를 배포했습니다. 실제 배포 API의 READY와 정적27파일·음성/영상 바이트 일치를 확인했습니다. 영속 저장이 없어 접수 API는503이며, 이 결과는 화면·합성 미디어를 제공하는 제한 Preview의 인수입니다. 최종 Production·전체 업무 저장·클라우드 실모델 완료는 아닙니다.

## 입력과 배포 대상

- [실행 전 설계](../../planning/protected-preview-refresh.md), [기존 생산 빌드](call-playback-production-build.md), [명사형 요청 수정](../nominal-request-cancellation.md)을 기준으로 했습니다.
- 새 폴더 `dist/deployment/20260921T185503517118Z-3cf7b0a9764a`: payload60파일 12,955,379 B, marker 포함61파일 12,964,126 B. 기존 폴더를 덮어쓰지 않았습니다.
- frontend 입력 지문 `60a39e97b6038c936bf1de701312d60e0c954bc9c2a50b7089f304d12ba681a0`과 03:41 완료 기록이 유효하여 프런트 재빌드0회, 새 패키징1회입니다. 출력은27파일 6,881,209 B입니다.
- 별도 검토자가 이전7b50 묶음과 실제61파일을 비교했습니다. 추가/삭제0, 변경2개는 `server/request_grounding.py`와 marker입니다. 정적27파일은 동일하고 새 요청 코드8,067 B는 고정 Git blob과 일치합니다.
- marker SHA256: `85e037e80f3b38d2b95b1b9cc95b561b95e4b9054c1680ebc80bf56a669c2ae4`.
- payload inventory SHA256: `0a8274629e4cb523469ac23edfabae7591e2fb0ecfb7d83fde3e49cb59341a70`.
- 메인 패키지 검사에서 payload60/60·정적27/27·미디어4파일×4위치16/16을 확인했습니다. CLI dry의61경로·bytes·SHA1도 실제 파일과61/61 일치합니다. 원천자료·로컬 원장·`.env`·JSONL을 배포 입력에 넣지 않았습니다.

Vercel CLI59.23.2에서 명시 project=`prj_VUk0C5e3thVOU9GgT8pc9tAoCczs`, scope=`52g-studio`, target=`preview`로 dry1회·실제 deploy1회를 실행했습니다. 새 OpenAI 키·환경변수·권한·접근 토큰을 생성하거나 설정하지 않았습니다.

| 실제 관측 | 결과 |
|---|---|
| project API | g-28 / project id와 team account id 일치 |
| 보호 설정 | `all_except_custom_domains` 유지 |
| 03:47 storage status | exit0, 현재 계정에 보이는 연결 stores0 |
| dry | exit0,61파일/12,964,126 B, ignored0, framework Other |
| actual deploy | exit0, `dpl_FecPJfwJ31PSio7eNifBuqpP4SYZ` |
| 03:57:13 deployment API | 위 ID·URL·project id 일치, READY, target=null(Preview), aliases=[] |

이전 Production 별칭은 이번 작업에서 변경하지 않았습니다. 18시대 첫 Production의500과 이전 Preview의 검증은 [이전 보고](cloud-preview-20260921.md)에 보존합니다. 새 Preview 성공으로 그 실패를 소급 수정하지 않습니다.

## 실제 URL HTTP 검사

기존 비밀 설정은 ignored 로컬 파일에서만 읽고 검증한 새 Preview origin에만 보냈습니다. 리다이렉트를 따라가지 않았으며 URL·보고서·Git에는 인증값을 넣지 않았습니다. 합성 미디어와 HTML/JS/CSS를 GET으로 검사했고 POST/PATCH·AI 호출은0입니다.

| 요청 | 기대와 실측 |
|---|---|
| 무인증 `/` | 302,15 B, Location host vercel.com, no-store |
| 플랫폼 접근만 있는 `/` | 401,12 B, private/no-store |
| 기존 앱 인증 `/healthz` | 200,15 B, private/no-store |
| 기존 앱 인증 `/` | 200,7,381 B, 로컬 index.html과 바이트 동일 |
| export27개 파일 각각 GET | 27/27 모두200·전체6,881,209 B·개별 bytes/SHA256 일치 |
| MP4 Range `bytes=0-63` | 206,64 B, `bytes 0-63/991249`, 원본 앞64 B 일치 |
| MP4 Range `bytes=-64` | 206,64 B, `bytes 991185-991248/991249`, 원본 끝64 B 일치 |
| `/api/cases` | 503, `error.code=STORAGE_CONFIG_INVALID` |

27파일에는 빠른 재생 코드가 포함된 `page-45b66b6648186293.js`, CSS2개, WAV2개, 1080p MP4와 tracks JSON이 포함됩니다. 원격 다운로드 바이트 검증이며 이번 새 URL에서 브라우저 렌더·전체 재생을 실행했다는 뜻은 아닙니다. 기존 로컬 탭은 이동·재시작·접수 변경하지 않았습니다.

첫 HTTP 기록은 오류 JSON의 top-level `code`를 읽어 null을 기록했습니다. 원본을 보존하고 04:01 후속 GET에서 실제 계약 `error.code`를 읽어 `STORAGE_CONFIG_INVALID`를 확인했습니다. HTTP503 자체를 성공한 업무로 세지 않습니다.

별도 검토자는 배포 묶음의 코드/설정7파일을 marker와7/7 대조하고 합성 설정으로 실제 `handlers.list_cases()`를 호출했습니다. backend 미설정·Blob 필수설정 누락은503 CONFIG_INVALID, 기존 케이스 원장 없음·읽기 실패·예산 원장 없음은503 STORAGE_UNAVAILABLE로5/5 일치했습니다. 업무 목록 호출·저장·외부 연결은0입니다. Connexion/FileLock 의존성을 대역 처리한 오프라인 handler 검사이며 실제 원격 환경/스토리지 검사로 세지 않습니다. 정적 라우터와 `/healthz`는 저장소 준비검사를 거치지 않고 업무 API는 통과해야 한다는 코드 경로를 별도로 확인했습니다. `/api/health`는 저장소 준비검사를 하므로 `/healthz`의 결과와 구분합니다.

정제된 원시 측정은 ignored `.local/nominal-request-package-20260921T185505.json`, `.local/preview-refresh-3cf7-http-initial.json`, `.local/preview-refresh-3cf7-http-assets.json`에 보존합니다. CLI deploy/dry 응답도 같은 `.local/preview-refresh-3cf7-*` 경로에 보존하며 외부 제출물로 삼지 않습니다.

## 남은 완료 조건

저장소 미연결503을 임시 JSON이나 새 예산으로 우회하지 않았습니다. 권한 있는 저장소 연결 후 CAS·기존 전역 예산·상태 지속을 검증해야 하며, 그 뒤 실제 배포 URL의 두 전체 흐름·충돌/복구·실모델 검증과 최종 Production 인수가 필요합니다. 로컬 API 재시작 거부와 새 브라우저 실행 제한은 그대로입니다.

국내 TTS 공식 음원 수신·사람 청취, 실제 카카오톡/Teams 전송, 실제 WMS/TMS 연동, 최종 로그 내용 검토·제출도 이 HTTP 인수에 포함되지 않습니다.
