# revision·명시적 사례 연결 독립 재검

2026-09-21 17:30 KST · 대기세션4 · AI/Codex · pc1/CJJ

## 결론

최종 Owner 화면을 포함한 실제 API/브라우저 집중검사 15/15, 격리 서비스 계약 14/14가 통과했다. PATCH의 확인 버전 전달, 누락428·낡은버전409, 기존 사건 자동연결 금지, 명시연결 및 원문 보존을 검증했다. 낡은 폼에 최신 revision을 붙이는 방식이나 실패 후 자동 재시도는 사용하지 않았다.

API 재시작 확인 메시지를 받은 뒤에만 실행했다. 생산 코드 수정·유료 API 호출은 없으며, 실제 서버의 모든 저장/이관/종결은 새 E2E INT 사례로 수행했다. CASE-0001/0002 대상 analyze/PATCH는 0건이다. 본 검사는 모델의 내용 정확성 판정을 대체하지 않는다.

## 기대와 실측

| 항목 | 기대 | 실측 |
|---|---|---|
| revision 없는 PATCH | 428, 기존 상태 불변 | INT-524C4033: REVISION_REQUIRED/428, 전체 저장 객체 동일 |
| 현재 revision 저장 | 수락하고 버전 증가 | snapshot0 사용 → 200/revision1 |
| 이전 snapshot 재사용 | 409, 먼저 저장된 값 보존 | 같은 snapshot0으로 다른 request 저장 → STATE_CONFLICT/409, ‘E2E first accepted edit’ 및 revision1 보존 |
| 실제 화면의 오래된 폼 | 화면을 열 때 받은 revision으로 요청, 충돌 표시 | INT-42BD2701: 화면확인0 → 다른 편집자 저장1 → UI가 여전히0 전송 → 409. 실제 UI PATCH1회, 상대편 저장 내용 보존 |
| 새 웹 문의 자동연결 금지 | 점포·제목이 같아도 참조 없으면 근거 없음 | INT-FF967FC4: linkedFixtureId=null, evidence=[], wms/tms 없음. WMS 근거 없음·TMS 방문순서 없음 표시 |
| 잘못된 명시적 참조 | 다른 사례로의 연결 거부 | CASE-0001 점포·유형·제목에 referenceCaseId=CASE-0002 → INVALID_REFERENCE_CASE/422 |
| Owner의 연결 선택 | 정본 사례 선택 시 점포·유형·제목 채움, 원문 유지 | CASE-0001 선택 후 SYN-ST01/당일1회차 배송 전체, 입력한 원문 그대로 보존 |
| 연결 맥락 변경 | 점포·제목·유형 불일치 시 연결 해제 | 세 필드를 각각 변경해 referenceCaseId 선택 해제 3/3, 원문 유지 |
| 명시 선택 후 웹 접수 | referenceCaseId를 실제 요청에 넣고 해당 근거만 연결 | INT-C4B09829: Owner POST에 CASE-0001 포함, sourceText 동일, 연결 근거 E-M 계열 및 TMS SYN-R01 |
| 물류 근거 연결 | 현재 snapshot에 맞는 revision 연속 사용 | WMS E-M3 연결 expectedRevision0 → 응답1, TMS E-M1 연결 expectedRevision1 → 응답2 |
| 확인·근거 게이트 | 유효 revision이어도 미확인 이관·외부 근거 차단 | REVIEW_REQUIRED/422, INVALID_EVIDENCE/422. 거부 전후 전체 저장 객체 동일 |
| 이관→회신→종결 | 받은 revision을 다음 저장에 사용 | 이관 expectedRevision2, 중간회신3, 최종회신4. null 수령수량 보존, pending 중 종결422, 해제 후 closed·경영주 회신 표시 |

`patchFrom(snapshot, delta)`와 Python `patch_from(snapshot, body)`는 명시적으로 전달받은 snapshot.revision만 사용한다. 내부 GET이나 새 revision 주입, 자동 재시도는 없다. 낡은 revision 대조군은 수락된 저장 이전의 동일 snapshot을 재사용한다. 일반 직접 API 검사는 해당 새 명령을 작성할 때 읽은 GET/직전 응답을 사용하며, 화면의 오래된 입력과 섞지 않는다.

## 실행과 증거

- 최종 실행: **17:29:20~17:29:31 KST**. `2026-09-21T08-29-20-819Z/results.json`에 15 PASS / 0 FAIL / 4 NOT_RUN 및 요청·응답·해시 보존.
- 미실행4개: 기존 fixture 음성 재생, replay 분석, 기존 case 전환, 3폭 렌더 반복. 기존 시연 상태를 보존하고 이번 변경 범위를 검사하기 위해 생략했으며 통과 분모에 넣지 않았다.
- `service-contract-revision.json`: 17:25:53 격리 저장소 14개 서비스 계약 결과. 과거 `service-contract.json`은 덮어쓰지 않았다.
- 최종 실행 폴더의 `stale-form-rejected.png`, `wms.png`, `tms.png`, `owner-final.png`: 실제 UI 경로 증거.
- 주페이지 console/pageerror0, 케이스 선택·이동 중 음성 요청 ERR_ABORTED3건은 원자료에 유지. 실제 stale UI의 409 응답은 의도한 음성 대조군이다. live analyze 요청0.
- 최종 실행 시작/종료에 검사 대상6개 파일의 SHA가 모두 동일했다. UI `7c916572b0832803487f9b17534f22894505cfeb2f2fc8ea1ccb7ac08acf45af`, Service `68fc155357bee36e4fa1c894ebeb1f56b0eef763dd5b3b50e4a03b1ffdd0bf60`.

첫 실행 `2026-09-21T08-25-54-719Z`는 13PASS와 검사기 선택자 실패1건이었다. textarea 내용이 포함되는 정확 label 선택을 placeholder 선택으로 바꾼 뒤 `2026-09-21T08-26-58-776Z`에서 해당 항목만 재검했다. 이 두 실행 사이 Owner 수정으로 UI SHA가 달랐으므로, 이후 Owner 최종 완료 알림을 받고 위의 15개 집중검사를 다시 수행했다. 앞선 메인 회신의 ‘두 실행 UI SHA 동일’ 표현은 정정했다.

## 재현·생성 사례·소유권

저장소 루트에서 다음 명령으로 실행한다.

```powershell
node tests/e2e/replay-check.mjs --revision-only
.venv/Scripts/python.exe -X utf8 tests/e2e/service-contract-check.py
```

특정 실패만 재검하려면 `node tests/e2e/replay-check.mjs --only=stale-ui-form-keeps-reviewed-revision`을 사용한다. 전체 기존 replay 스크립트를 인자 없이 실행하면 기존 CASE-0001 분석 경로도 포함하므로, 동시 시연 중에는 위 집중 실행을 사용한다.

최종 실행 생성 사례: INT-FF967FC4(신규 문의), INT-524C4033(API 경쟁저장), INT-42BD2701(UI 경쟁저장), INT-C4B09829(명시연결→종결). 앞선 시행에서 생성된 INT-70C17DE3/INT-931ECDCC/INT-DE72A392/INT-51BB3232/INT-3034AECB도 기록을 보존했다. 기존 fixture 삭제·상태복구·공유 저장소 초기화는 하지 않았다.

변경 소유 파일은 `tests/e2e/replay-check.mjs`, `tests/e2e/service-contract-check.py` 및 이번 `reports/e2e` 실행 증거·보고서다. 검증을 마쳤으며 해당 경로의 소유권을 메인에 반환한다.
