# 대체 메인의 고정 소스 빌드와 배포 묶음 독립 검증

2026-09-22 · pc1/최제준 · 메인의 production build·패키징 각 1회 성공 이후 별도 검토자가 실제 파일을 읽어 대조했다. **고정 소스의 로컬 배포 묶음 바이트 검증은 통과했다. Vercel 배포·영속 저장·실모델 인수는 아니다.** 검토자는 패키저 함수나 제품 앱을 실행하지 않았으며 소스·묶음·미디어·키·원장을 수정하지 않았다.

- 고정 소스: `190295f6c10f33e777f8ffded623d7a9fe8c20e5`.
- 묶음: `dist/deployment/20260921T220053240866Z-190295f6c10f`.
- 완료 build stamp: `apps/web/out/.oneflow-build.json`, `2026-09-21T22:00:41.774660+00:00` = 9/22 07:00:41 KST.
- stamp의 명령은 `npm run build`, 상태는 `complete`, 공개 API base는 빈 문자열로 동일 origin을 사용한다.

## 검증 방법과 소스 고정

저장소 `.venv/Scripts/python.exe -X utf8 -B -`에 독립 표준라이브러리 검증 코드를 stdin으로 실행했다. `pathlib`로 실제 파일을 열거하고 `hashlib.sha256`으로 원바이트를 계산했으며 `json`으로 manifest·stamp를 읽었다. `git show <고정SHA>:<경로>`로 고정 blob을 직접 가져와 비교했다. 패키저의 검사 함수를 import하거나 그 함수를 다시 호출한 결과로 통과를 판단하지 않았다.

첫 조회에서 로컬 HEAD·origin/main 참조는 고정 SHA와 같고 작업트리는 깨끗했다. 검증 도중 메인이 `CURRENT_TODO.md`와 새 `reports/channel/N03-R1-replacement-main-rehearsal.md`를 작성했다. 그래서 첫 실행의 전역 clean assertion은 payload 검사 전에 중단됐고, 문서 작업을 보존한 채 고정 Git blob 및 payload의 실제 소스 바이트 대조로 재실행했다. 이는 제품 파일이나 묶음 무결성 실패가 아니다. 독립 검사에서 원격 fetch를 실행하지 않았으므로 origin/main은 로컬 추적 참조 대조다.

프런트 입력은 문서화된 app/components/lib/public/scripts와 설정·고정 데이터에서 별도로 35개를 열거해 지문을 다시 계산했다. `next-env.d.ts`는 원래 지문 계약에서 제외하는 생성 파일이다. 재계산한 입력 지문이 stamp의 sourceBefore/sourceAfter 및 bundle marker와 같았고, 출력 27개 지문 및 stamp 자체 recordDigest도 marker와 일치했다.

## 실제 파일과 바이트

| 대조 | 결과 |
|---|---|
| manifest payload 대 실제 전체 payload | 61/61, 추가·누락 0, 총 12,973,857 B |
| marker 포함 실제 묶음 | 62파일, 12,982,734 B |
| 로컬 export 대 묶음 export | 27/27 원바이트 동일, 6,881,691 B |
| 비정적 payload 대 작업트리 원본 | 30/30 원바이트 동일, api/index.py·vercel.json의 원본 매핑 포함 |
| 비정적 payload 대 고정 Git blob | 27/30 원바이트 동일, 아래 3개는 CRLF 차이만 존재 |
| 새 요청 모듈 | `server/request_provenance.py` 포함, 최종 독립 검토 해시와 동일 |
| 로컬 Python 의존 모듈 | AST로 확인한 server/scripts import 44건의 대상이 실제 payload 안에 존재 |
| 승인 미디어 | 4파일 × 4위치 = 16/16 크기·SHA256 일치 |
| 합성 integrity 대조군 | 정상 1/1 수용, 크기·동일크기 바이트·기대크기·기대해시 변형 4/4 거절 |

Git의 줄바꿈 처리만 다른 파일은 `pyproject.toml`, `server/openapi.yaml`, `uv.lock`이다. 이 세 파일도 작업트리 원본과 묶음은 원바이트로 같으며, CRLF→LF 정규화 후 고정 Git blob과 같다. 이를 30/30 Git 원바이트 일치로 보고하지 않는다.

실제 경로 집합이 manifest와 정확히 같았고 symlink·junction·다중 hardlink 파일은 없었다. `.env`, `.local`, 인증 파일, 실행 접수·예산 원장, JSONL, ZIP, 개발 의존 폴더는 payload 경로에 없었다. fixture는 원본 data·public·export·묶음 사본이 같았다. `vercel.json`은 전체 경로를 단일 `api/index.py`로 보내며 정적 outputDirectory 우회가 없었다. 앱 실행을 하지 않았으므로 이 AST/설정 대조를 런타임 HTTP 성공으로 표현하지 않는다.

## 승인 미디어 네 사본

아래 파일은 `demo-media-20260922-v4` manifest의 현재 승인 자산이다. 각 파일을 작업트리 `apps/web/public/demo`, 작업트리 `apps/web/out/demo`, 묶음의 두 동일 경로에서 읽어 검증했다. 과거 처리 전 원본의 sourceSha256과 현행 승인 자산의 sha256을 혼동하지 않았다.

| 파일 | 바이트 | SHA256 |
|---|---:|---|
| CASE-0001.wav | 2,263,278 | `d4eeb6448ff8969f27034ecade9a050ee212468585c6300b19c9a0ebdc372931` |
| CASE-0002.wav | 2,388,044 | `6fe83afb8552765ab92722b838d2a0905f507551c4f98c58fa62a515033abaa0` |
| sorter-demo.mp4 | 991,249 | `4a640c20e209bf5a43e26c3f1c5afeb41f4157af9017f04b4c3812b1990dca51` |
| sorter-demo.tracks.json | 158,546 | `b9b9f50295af799cfdf718b840b0cef703f57ad3e3b778557fcd9fdeb9ac681c` |

tracks 등록의 videoSha256도 현행 MP4 해시와 일치했다. 이번 검사는 로컬 승인 사본의 대조이며 Release 재다운로드·영상 재생·음성 청취는 실행하지 않았다.

## 재대조용 식별값과 범위

- bundle marker SHA256: `3d620e5b7236f1bddc16cd0c5253b6b8963474dabc909e55d29f57d64fe700e5`.
- payload inventory SHA256: `15aca2f6e7ef86e2a498820ebd84c0443e38ef1aedfe413a4f4bb8cdda432b69`.
- frontend source fingerprint: `07f4127d0c16b6cdcc24ecab6693b1153207b5018977ae8dc8a8f5acbb3d7d80`.
- frontend output fingerprint: `78932cb3049ff97fdee59a20d05b3cdbbda1e077b8239f5d32f4179af66330cb`.
- build record digest: `ed653e2c89ba6571cbefbbc472e0072e3c3680f136885fce9fbf43947bde814d`.
- 새 `request_provenance.py` SHA256: `5590e248f62adee421dd771b0f39b1a806a3105c888d81a1751d1a46da6af819`.

검사 끝에 marker와 build stamp의 원바이트가 최초 읽기와 같은지 다시 확인했다. 합성 변형 대조군은 메모리의 검사용 바이트만 바꿨으며 실제 파일은 바꾸지 않았다. 이 검증자는 네트워크·클라우드·과금·키·원장·운영 서버에 접근하지 않았다. 독립 검증으로 생성한 파일은 본 보고서 하나다. 메인의 별도 운영 재시작·HTTP·브라우저 결과는 아래에 추가할 수 있으며 위 파일 검증의 분모와 구별한다.

## 메인의 동일 소스 로컬 재시작

고정190295f 소스에서 관리 실행기의 소유 프로세스만 중지한 뒤, 기존 `.local/main-resume-20260922/replay-state`와 빈 AI 키로 다시 실행했다. UI3100/API8100의 `/api/health`는 status=ok/synthetic=true/runtime=synthetic-demo/liveReady=false였다. 접수 파일 SHA256은 재시작 전후 `16b66a857e9ff367966cf70b9857a772b2df3f191d8de5b8b7a78195c943cc5f`로 같았다.

CASE-0001 revision5/closed, CASE-0002 revision4/closed, 새 텍스트 INT-DE9B8DB5 revision0/draft, 연결 해제 대조 INT-5DA7C39C revision1/review, 근거 저장 재검 INT-E83B2583 revision2/handed_off의 5접수가 보존됐다. 브라우저 reload 후 경영주 화면에서 CASE-0001의 등록 회신과 완료 상태를 확인했다. 이번 로컬 검증의 `demo-usage.json`은 생성되지 않았다. 0원 표시는 기존 CJJ 원장이 없는 새 replay 상태의 값이며 기존29.20달러 지출을 초기화한 결과가 아니다.

이것은 소스의 로컬 개발 서버 재시작이며 생성 bundle을 클라우드에 배포한 결과가 아니다. 실제 Vercel 인증·영속 저장·실모델·외부 알림·Production은 여전히 미완료다. 개발 서버가 자동 변경한 next-env.d.ts는 생성 경로 차이만 확인하고 원복했다. 이후 문서 전용 커밋은 제품190295f 묶음의 소스를 바꾸지 않는다.
