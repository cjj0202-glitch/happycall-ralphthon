# N03-R1 · 교체 메인 기준 PC3 독립 리허설

- 지시: [#9 N03-R1](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/9#issuecomment-5768138039), 2026-09-22 07:02 KST.
- 검증 기준: `190295f6c10f33e777f8ffded623d7a9fe8c20e5`. 기준 소스를 별도 로컬 디렉터리에 추출해 실행했다.
- 실행자: `pc3/logistics-review · LAPTOP-U2AL73UH · mcjun86-oss`, Windows 11, Python 3.12.10, Node v24.19.0, Next 15.5.25.
- 실제 검증: 2026-09-22 07:08–07:22 KST. 작업 브랜치 `work/pc3-n03-wms-scenes`, 시작 HEAD `48a429f7f115b9ba1b310b60343160c91dbcca06`.
- 판정: 아래의 **무과금 로컬 합성 리허설 범위 통과**. 센터 부서 표시의 내부 코드 노출 1건을 남긴다. PC1 인수, TEST, N03 전체 완료를 뜻하지 않는다.

## 실제 실행과 기대/실측

| 검증 | 기대 | PC3 실측 |
|---|---|---|
| v4 미디어 | 승인된 4개 파일의 크기와 SHA-256 일치 | `fetch_demo_media.py --verify-only` exit 0, verified 4/4, missing 0, downloaded 0. 기존 PC3 파일을 별도 디렉터리에 복사했고 원본은 불변 |
| CASE-0002 통화/저장 분석 | 합성 통화가 재생되고 외부 AI API 호출 없이 수령 단위 BOX 복원 | 전체 통화 재생 버튼으로 시작, duration/currentTime 49.75초, ended=true, 1.25배속. 저장 결과 재생 후 초기 EA가 BOX로 바뀌고 무과금 안내 표시 |
| CASE-0002 WMS | 주문·피킹 비스킷 18 EA와 출고·수령 휴지 1 BOX 분리, 원인·귀책 미확인 | UI에서 값과 구분 확인. BOX→EA 환산 또는 단순 차감 없음. 피킹 `SYN-TOTE02-A`/02:15와 출고 `SYN-TOTE02-B`/03:02, 연결 미확인 표시 |
| W-W3 등록 영상 | 정확한 사건·공정의 등록 영상 및 합성 객체 확인 | CASE-0002/W-W3/SYN-CAM-02, 2026-09-18 02:33 KST, SHA/크기 검증 후 열림. 1920×1080, 12초, 24fps/288프레임. 재생 중 이동 상자와 bbox를 보고 `SYN-VIS-PARCEL02` 선택. 12/12초 ended=true 확인 |
| 미등록 공정 | 다른 공정 영상으로 자동 대체하지 않음 | CASE-0002 W-W1에는 연결 영상 없음, W-W3에서만 등록 영상 열기 가능 |
| 명시 연결 없는 신규 문의 | 점포·제목이 같아도 기존 사건을 추정 연결하지 않음 | `INT-2EBB19B1`: SYN-ST02/동일 제목으로 생성했지만 원본 미연결, WMS 영상·근거 연결 차단. 서버 linkedFixtureId=null, selectedEvidence=[], media 없음, revision=0/draft |
| 명시 연결한 신규 문의 | 원본 WMS 연결은 허용하되 영상은 자동 복사하지 않음 | `INT-FCA4575D` 생성 시 CASE-0002 명시 선택. WMS 원본 CASE-0002 확인. W-W3도 “신규 접수 영상 미등록 · 원본 사건의 영상을 자동으로 연결하지 않습니다” 표시, 서버 media 없음 |
| 자신의 근거 저장 | 미저장 요청·부서는 보존, 확인 체크 해제, 낡은 revision 충돌 없음 | 요청을 `PC3-R1-DRAFT 보존…`으로 편집하고 출고 운영 선택·확인 체크 후, 저장하지 않고 WMS E-W3 연결. 복귀 시 정확한 요청/부서 보존, 체크 false, 전달 버튼 disabled, 서버 변경 충돌 안내 없음 |
| 재확인 후 센터 전달 | 재확인 전 차단, 재확인 후 편집 내용과 근거를 함께 전달 | 체크를 다시 선택하자 전달 활성화. 실제 전달 후 센터 자동 이동, 정확한 요청·미확인 수량·출고 스캔 불일치 근거·상담원 확인 완료 표시. 서버 revision=2/status=`handed_off`, departmentId=`warehouse`, reviewConfirmed=true, selectedEvidence=[E-W3] |
| 기존 단위/변이 검사 | 근거 저장의 정상·차단 조건과 회귀 감지 | PC3에서 `node tests/e2e/evidence-self-save-unit.mjs` 1회 실행, exit 0, 45/45, 변이 5/5 감지, stderr 비어 있음. 브라우저 결과와 별도 집계 |
| 기존 사건/비용 보존 | 다른 사건을 변경하거나 실제 AI를 호출하지 않음 | CASE-0001 초기/최종 전체 객체 동일. CASE-0002는 저장 분석 재생에 따른 revision=1/review, 확인=false/근거=[] 유지. 초기·최종 health liveReady=false, reservedUsd=0.0 |

영상 객체의 업무 토트 ID는 null이고 CH-02/D-02만 표시됐다. 시각 객체 ID를 업무 토트와 동일시하지 않았다. 가림 검증·실제 CCTV 판독·작업자 귀책 판정은 수행하지 않았다. 영상의 설명용 합성 표시와 원본 기록 시각/영상 경과 시간 구분을 확인했다.

## 초안 보존의 서버 증거

동일 신규 문의 `INT-FCA4575D`를 UI에서 조작했고, 아래 서버 상태는 GET으로만 조회했다. 서버 응답을 직접 수정해 성공 상태를 만들지 않았다.

| 시점 | revision/status | 서버 요청사항 | departmentId / reviewConfirmed / selectedEvidence |
|---|---|---|---|
| E-W3 저장 직후, 전달 전 | 1 / draft | 최초 `PC3-R1-LINKED: CASE-0002와 동일한 합성 배송 사건입니다…` 유지 | null / false / [E-W3] |
| 상담 복귀 | 서버는 위와 동일 | 화면에는 아래 미저장 편집문 보존 | 화면 출고 운영 / 확인 해제 / 전달 차단 |
| 재확인·전달 후 | 2 / handed_off | 아래 편집문과 완전히 일치 | warehouse / true / [E-W3] |

편집문:

> PC3-R1-DRAFT 보존: 비스킷 18 EA 주문과 휴지 1 BOX 수령 기록을 대조하고 회송·주문 상품 처리 방안을 출고 운영에서 확인해 주세요.

신규 문의는 수령 수량·단위를 입력하지 않았다. 최종 quantity=null, unit=""로 남았으며 기존 사건의 1 BOX를 신규 문의 수령값으로 자동 채우지 않았다. 센터 최종 회신·종결은 실행하지 않았다.

## 미달·관찰사항

1. **센터 부서 표시**: 상담 화면 선택은 `출고 운영`인데 센터 “전달 부서”에는 `warehouse`가 그대로 표시된다. 저장 값과 이관은 정상이나 사용자 표시명 정리가 필요하다. 소유 범위가 보고서뿐이므로 코드 수정 없이 PC1에 인계한다.
2. 실제 AI/STT, 사람의 청취 품질 인수, 실제 고객 데이터, 외부 알림, 보호 Preview/배포, 실제 운영 인증·저장소는 검증하지 않았다. 통화 재생 완료는 청취 내용의 정확성 인수가 아니다.
3. PC3 브라우저는 한 로컬 데스크톱 세션에서 위 경로를 실제 실행했다. PC1의 “브라우저 2건”이나 PC1 검사 수를 PC3 결과에 합산하지 않았다. PC3 단위 검사는 별도 서브에이전트가 **동일 PC3 장비**에서 실행했다.
4. 이번 브라우저는 신규 draft의 자신의 근거 저장과 재확인 이관을 검증했다. 실제 동시 사용자 충돌, 오래된 서버 응답/저장 중 경합은 브라우저에서 만들지 않았다. 이들은 기존 단위/변이 검사의 범위와 구분한다.
5. 최초 Next 준비 확인은 시간 초과였고 초기 탭 연결 거부/첫 컴파일 중 탐색 시간 초과가 있었다. 같은 런타임의 준비 완료 후 정상 접근했다. 화면 요소 locator 두 번 불일치는 새 접근성 상태로 재지정해 진행했다. 제품 소스를 바꾸지 않았다.
6. 신원 회신 TEST는 계속 미완료다. 공식 로그 제출/민감정보 검토/HowLong 및 N03 전체 인수도 이 결과로 완료 처리하지 않는다.

## 격리 환경과 재현

원래 checkout과 기존 watcher PID 33460을 보존했다. `git fetch origin <위 고정 SHA>` 후 `git archive`로 `.local/pc3-r1-190295f/source`에 추출했다. branch switch/pull/reset/stash, main push/merge는 하지 않았다. Git 변경 대상은 이 보고서 한 파일뿐이다.

- 독립 상태: `.local/pc3-r1-190295f/replay-state`를 새로 생성하고 `ONEFLOW_STATE_DIR`를 그 절대 경로로 지정했다. 기존 상태/ledger/키를 옮기거나 초기화하지 않았다.
- 실행 환경: `uv sync --frozen --no-python-downloads`로 고정 lock의 Python 환경을 별도 `.venv`에 설치했다. uv/pip cache도 해당 D: 로컬 작업 폴더에 둔다.
- 웹 의존성: baseline과 package-lock 바이트가 같은 기존 PC3 node_modules를 junction으로 참조했다. 새 클린 npm 설치에 대한 검증은 아니다. Next 캐시는 격리 source 아래 생성됐다.
- 실행 후 대조: source-reference의 핵심 8파일 SHA는 8/8 동일. 809개 기준 파일 중 749개 원바이트 동일, 58개는 줄바꿈 차이, 환경 예시 1개는 미열람했다. 내용 차이 1개는 Next가 격리 source의 `apps/web/next-env.d.ts`에 생성한 `.next/types` → `.next-dev/types` 참조 변경이다. 원래 checkout의 제품 소스·계약·lock은 수정하지 않았다.
- child 환경에서 `OPENAI_API_KEY`, `ONEFLOW_RUNTIME_MODE`, `OPENAI_DEMO_BUDGET_USD`, `OPENAI_DEMO_WARN_USD`, `OPENAI_DEMO_PURPOSE`를 **존재하는 빈 문자열**로 설정했다. 파일 fallback으로 실제 키가 로드되지 않게 했고 값은 기록하지 않았다.
- child 환경의 Vercel/Blob 관련 변수는 제거하고 `ONEFLOW_STORAGE_BACKEND=local-json`, `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8100`, `ONEFLOW_CORS_ORIGINS=http://127.0.0.1:3100,http://localhost:3100`, `NEXT_TELEMETRY_DISABLED=1`, `PYTHONDONTWRITEBYTECODE=1`을 사용했다.
- 로컬 health에 표시된 한도 30.0은 이 독립 replay의 기본 메타데이터다. 팀 예산을 새로 부여하거나 기존 예산을 리셋한 것이 아니다. 실제 AI 호출 0, 신규 렌더 0, 미디어 다운로드 0.

재현할 때 기존 디렉터리/프로세스를 덮어쓰지 말고 별도의 새 source/state 경로를 사용하며 3100/8100 포트가 비어 있는지 확인한다. 고정 서버 런처는 127.0.0.1:8100을 사용하므로 점유 시 기존 서버를 종료하지 말고 재현을 보류한다. 위 환경을 **child process에만** 전달한 뒤 다음 고정 소스 명령을 실행한다. 이번 환경의 npm 배치 경로가 기본 런처 예상과 달라 기존 서버/Next 명령을 직접 실행했다.

```text
# cwd: 고정 SHA를 추출한 source
python -B scripts/fetch_demo_media.py --verify-only
node tests/e2e/evidence-self-save-unit.mjs
.venv/Scripts/python.exe scripts/run_demo_server.py

# cwd: 같은 source/apps/web
node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port 3100
```

1. 새 상태로 `http://127.0.0.1:3100/`에 접속한다. 분석 방식은 “저장 결과 재생 · API 호출 없음”으로 둔다.
2. CASE-0002 전체 통화 재생 → 저장 분석 재생 → WMS 수량/토트/미확인 구분 → W-W1 영상 없음 → W-W3 등록 영상 열기·재생·시각 객체 선택을 확인한다.
3. 경영주 화면에서 SYN-ST02, 제목 `비스킷 주문 대신 휴지 입고`로 합성 문의를 만들되 관련 기존 접수는 “연결하지 않음”으로 둔다. WMS의 원본 미연결/영상·근거 차단을 확인한다.
4. 같은 점포·제목으로 두 번째 합성 문의를 만들 때 CASE-0002를 명시 선택한다. 원문에 PC3-R1-LINKED와 합성 사건임을 적는다. WMS 원본 연결과 신규 영상 미등록을 확인한다.
5. 상담 요청사항을 위 편집문으로 바꾸고 출고 운영을 선택해 확인 체크한다. 접수 저장 없이 WMS로 이동하여 E-W3를 연결한다. 돌아와 편집문·부서 유지/체크 해제/전달 차단/충돌 없음 확인 후 재확인하고 센터 전달한다.
6. 센터에서 요청·부서 값·근거·사람 확인을 대조한다. GET `/api/cases` (`X-Demo-Role: agent`)와 `/api/health`로 revision/불변 사건/무과금 상태를 기록한다. 기존 replay-state를 지워 재현하지 않는다.

## 미디어와 보존 증거

v4 `demo-media-20260922-v4`의 실제 크기/SHA-256:

| 파일 | bytes | SHA-256 |
|---|---:|---|
| CASE-0001.wav | 2263278 | d4eeb6448ff8969f27034ecade9a050ee212468585c6300b19c9a0ebdc372931 |
| CASE-0002.wav | 2388044 | 6fe83afb8552765ab92722b838d2a0905f507551c4f98c58fa62a515033abaa0 |
| sorter-demo.mp4 | 991249 | 4a640c20e209bf5a43e26c3f1c5afeb41f4157af9017f04b4c3812b1990dca51 |
| sorter-demo.tracks.json | 158546 | b9b9f50295af799cfdf718b840b0cef703f57ad3e3b778557fcd9fdeb9ac681c |

로컬 `.local/pc3-r1-190295f/`에 source-reference.json, media-verification.json, evidence-unit-summary.json, evidence-unit-run/results.json, processes.json, initial-cases.json, after-evidence-before-transfer.json, final-cases.json, health-initial.json, health-final.json을 보존한다. 새 합성 상태와 브라우저 관찰은 이 실행에서 얻었다. 실제 고객 데이터·원본 대화 JSONL·시크릿·바이너리·런타임 로그를 Git/이슈에 올리지 않는다. 미디어 Release 생성/갱신 요청은 이번 카드에 없다.

07:25 KST 실행파일·명령·생성시각·부모 PID로 이번에 시작한 backend 15004/38652, web 18444/19192만 확인하여 종료했다. 자식 종료 직후 부모 종료 중 신원 재검사 guard가 중단됐으나 후속 조회에서 4개 모두 없음과 3100/8100 listener 없음이 확인됐다. 강제 재시도는 없었다. 합성 상태/증거는 보존하고 임시 검증 탭은 닫았다. 기존 watcher 33460은 그대로 살아 있으며, 07:23:38 snapshot은 #9 OPEN/58댓글이었다. 정리 결과는 cleanup.json에 기록했다.

이 보고서는 PC1 검토용 결과이며 중앙 작업표 변경, 자가 인수, 이슈 종결은 하지 않는다.
