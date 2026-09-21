# 대기세션4 독립 검증 1차 결과

작성: 2026-09-21 16:52 KST · AI/Codex · pc1/CJJ · localhost:3100 + API:8100

모바일 표 수정 독립 재검: 2026-09-21 16:55:39 KST.

## 결론

핵심 업무 흐름 14/14, 격리 서비스 계약 9/9 통과. 음성 2개와 영상 1개는 브라우저에서 정상 속도로 끝까지 재생됐다. 발견했던 390px TMS 점포명 줄바꿈 문제는 수정 후 독립 재검을 통과했다. 이번 검증에서 보고한 열린 결함은 0건이다. 실제 사람 관찰·청취 시험, live AI 검증, 전체 제품 완료 판정은 아니다.

## 실측 근거

| 범위 | 실측 |
|---|---|
| 브라우저 | Playwright 1.58.2 / 독립 Chromium 151.0.7922.34 context |
| 주 실행 | 16:49:48~16:50 KST, 14/14 PASS, 시작/종료 대상 소스 SHA 동일 |
| 음성 | CASE-0001: 47.15/47.15초, CASE-0002: 49.55/49.55초, ended=true, media error 없음 |
| 영상 | CASE-0002 소터 설명: 12/12초, 960×540, ended=true, media error 없음 |
| replay | 응답 mode=replay·화면 재생 표기 확인. live analyze 요청 0건 |
| 웹 접수 | 새 INT-5472B4DC 생성·원문 동일·CASE-0001 합성 키 연결 |
| 확인 게이트 | 확인 전 UI 이관 비활성, 직접 API REVIEW_REQUIRED 422, 저장 상태 불변 |
| null 경계 | 수량 null 유지한 전체 배송 문의 확인 후 handed_off |
| 근거 | 다른 사례 E-W1 거절 422, 현재 사례 WMS E-M3 / TMS E-M1 연결 |
| 전환 | CASE-0001 → CASE-0002 → CASE-0001 점포/접수·요약 혼입 없음 |
| 센터 | 중간 회신+pending은 in_progress, pending 중 최종 UI 비활성·API ACTIONS_PENDING 422, 해제+최종 회신 후 closed |
| 경영주 | 등록된 최종 회신 및 처리 완료 표시 |
| 반응형 | 1365/921/390px × 5뷰 = 15개 렌더·스크린샷, 문서 가로 넘침 0/15 |
| 모바일 표 수정 재검 | 390px 점포명 3/3 한 줄, 표 내부 가로 이동 306px, 문서/body 폭 390px, pageerror 0, analyze 요청 0 |
| 오류 | 주 실행 console error 0 / pageerror 0. 케이스 전환·새로고침 중 음성 요청 ERR_ABORTED 4건은 원자료에 유지. 별도 무전환 완주 재생에서 음성/영상 error 0 |

## 모바일 표 수정 재검: 통과

최초 P2: 390px TMS 방문 표에서 ‘가상 한빛점 · 문의 점포’가 한 글자씩 줄바꿈됐다. 점포 버튼 width=40.72px, height=194px였고 나머지 점포도 height=104px였다. 기존 JSON/화면은 `mobile-tms-table-before.*`로 보존했다.

대기세션1의 CSS 수정 후 16:55:39 KST에 새 독립 Chromium으로 재검했다. 실행 명령은 저장소 루트에서 `node tests/e2e/mobile-table-check.mjs`다. 생산 코드를 수정하지 않았으며 전체 14항목을 다시 실행한 결과로 합산하지 않는다.

| 판정 기준 | 기대 | 실측 | 판정 |
|---|---|---|---|
| 점포명 줄바꿈 | 3개 모두 nowrap·실제 텍스트 한 줄 | white-space=nowrap, DOM Range 줄 수=1 각각 3/3. 한빛점 150.11×32px, 푸른점·나무점 각각 89.31×32px | 통과 |
| 표 내부 가로 스크롤 | 좁은 컨테이너 안에서 마지막 열까지 이동 | clientWidth=322px, scrollWidth=628px, overflow-x=auto. scrollLeft 0→306px, 최댓값306px. 마지막 헤더 우측356.47px ≤ 컨테이너 우측357px | 통과 |
| 페이지 넘침 | 문서/body 모두 뷰포트390px 이내 | documentElement.scrollWidth=390, body.scrollWidth=390, window.scrollX=0 | 통과 |
| 오류·API | 화면 오류·분석 호출 없음 | pageerror=0, analyze 요청=0 | 통과 |

좌측 점포명과 우측 마지막 열을 각각 캡처해 시각적으로 대조했다. 수정 CSS SHA256: `62d44b23f06eccdc44268b686c17d38c3ff6de1fa184df72e5ee0c9b30b812f0`.

## 증거 파일

- `2026-09-21T07-49-48-363Z/results.json`: 14항목 결과, 요청/응답, 소스 SHA, 오류 원자료.
- 같은 폴더 `responsive.json`, 15개 폭별 화면, WMS/TMS·경영주 최종 화면.
- `service-contract.json`: 실제 서버와 별도인 임시 저장소 계약 9개 결과. 검증 후 임시 저장소 제거.
- `media-playback.json`: 두 합성 상담음성 및 합성 소터영상 정상 속도 완주 결과.
- `mobile-tms-table-before.json`, `mobile-tms-table-before.png`: 수정 전 모바일 표 문제.
- `mobile-tms-table.json`, `mobile-tms-table.png`, `mobile-tms-table-scrolled.png`: 수정 후 독립 재검 수치와 좌/우 가로 스크롤 화면.
- `initial.json`, `initial.png`: 16:47:45 개발 중 root 500 관측. 주 실행에서는 해소.
- `2026-09-21T07-48-53-233Z/`: 첫 검사기 선택자 실패 기록. 부서 label의 option 텍스트 포함으로 정확 매치가 실패했으며 실제 DOM select로 수정한 뒤 통과. 제품 결함으로 계산하지 않음.

## 재현과 상태 영향

저장소 루트에서 `tests/e2e`로 이동 후 `npm ci --ignore-scripts`, `node replay-check.mjs`, `node media-check.mjs`, `node mobile-table-check.mjs`를 실행한다. Chromium 경로가 다르면 `E2E_CHROMIUM` 환경변수에 설치된 실행파일을 지정한다. 서비스 계약은 루트에서 `.venv/Scripts/python.exe tests/e2e/service-contract-check.py`로 실행한다.

공유 저장소 초기화·생산 코드 수정·live API 호출은 하지 않았다. CASE-0001은 replay 분석으로 review 상태가 됐다. 첫 검사기 실행에서 INT-B8DDEF12(draft), 성공 실행에서 INT-5472B4DC(closed)가 생성됐다. 테스트 원문에 E2E 접두어를 넣었다. 시연 정리 필요 여부를 메인에 전달했으며 임의 삭제하지 않았다.

새 웹 접수는 원문 보존과 수동 확인/이관으로 검증했다. 신규 텍스트용 replay 결과는 서버 계약상 없으며 실제 AI 정제 품질은 이번 검증 범위에 포함하지 않는다. 화면의 모든 접근성·오프라인·경계 조합을 검증했다는 의미도 아니다.
