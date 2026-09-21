# 이전 저장 성공 알림 잔류 P2 수정

2026-09-21 / pc1 CJJ. 원격 근거: PC4 `d7841717e8181d4f9315a20dee5099c073251019:reports/pc4/q3-c6f734f-results.md`, Q3-08. PC4의 첫 저장200 이후 다음 응답 유실 화면에서 직전 성공 문구와 현재 미확정 안내가 공존했습니다. 원격 297/297 결과는 별도 메인 인수 대상이며 이 순수 단위 검사에 합산하지 않습니다.

## 수정 범위

page.tsx **10줄 추가/6줄 변경**. 공통 Home.save에서 이전 성공 알림을 비워 상담 저장/이관, 센터 회신, WMS/TMS 근거 연결을 함께 처리합니다. 분석·경영주 접수/재시도·저장 여부 조회·목록 재조회·합성 예시 불러오기 시작에도 초기화합니다. Owner에 기존 setToast 콜백만 전달했습니다.

성공 메시지와 성공 판정, 초안 보존, expectedRevision, 멱등키, uncertain/복구 분기, 6초 타이머는 그대로입니다. busy 등의 조기 반환으로 작업이 시작되지 않은 호출은 이전 알림을 유지합니다. 수정·검사 소유 파일 외 변경은 하지 않았습니다.

## 순수 검사 결과

**48/48 PASS**, 초기화 제거 변이 **3/3 검출**. 제품 action을 실제 소스에서 TypeScript AST로 추출·transpile하고 지연 Promise I/O·setter·draft 대역으로 실행했습니다. success→현재 요청 대기→503/응답 유실/성공의 토스트와 요청 본문을 기록했습니다. 실제 Home JSX onCreated/onLinkEvidence와 sameMutation도 추출해 실행했습니다.

| 대상 | 기대 / 확인 |
|---|---|
| 공통 저장, 상담 저장/이관, 센터 중간/최종 회신 | 요청 대기에 이전 성공 제거. 실패/유실 후 성공 없음. 성공 응답 뒤 새 성공. expectedRevision=4 유지, 유실 uncertain payload 보존 |
| AI 분석 | 이전 성공 제거, 실패 안내 유지, 성공 응답 뒤 기존 분석 성공 문구 |
| 경영주 신규 접수·결과 확인 | 이전 성공 제거, 실제 성공 대역 응답 뒤 실제 Home onCreated 메시지. 원문·멱등키 요청 형태 유지 |
| 상담/센터 최신 대조 | 일반 GET200을 저장 성공으로 표시하지 않음. uncertain payload와 일치한 기존 복구 분기만 새 확인 메시지 |
| WMS/TMS 공통 JSX 근거 callback | 실제 Home.save를 경유해 알림 초기화, 실패 시 성공 없음, 성공 시 기존 연결 메시지. expectedRevision 및 근거 배열 유지 |
| 미착수 guard 6개 | busy/blocked/attempt 없음 등의 조기 반환은 요청0·기존 상태 보존 |
| 변이 3개 | Home.save, Desk.analyze, Owner.submit의 초기화를 각각 제거하면 이전 성공이 남아 검출 |

수정 전 `.local/save-toast-unit-1789995145507/`: **6/44**. 미착수 guard만 통과했으며 시작 시점 이전 성공 제거 기대가 실패했습니다. 이를 38개의 독립 제품 결함으로 세지 않습니다.

수정 후 `.local/save-toast-unit-1789995182608/`: **44/44**, 이후 실제 JSX 연결과 콜백 검사를 추가한 최종 `.local/save-toast-unit-1789995237491/`: **48/48**, 변이3/3. 각 폴더 results.json·actual-actions.json·source-harness.mjs를 보존했습니다.

```powershell
& 'C:/Users/choi8/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' tests/e2e/save-toast-unit.mjs
& 'C:/Users/choi8/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' --check tests/e2e/save-toast-unit.mjs
& 'C:/Users/choi8/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' apps/web/node_modules/typescript/bin/tsc --noEmit --project apps/web/tsconfig.json
```

node --check, tsc --noEmit, page.tsx git diff --check exit0. 제품 전체 빌드·커밋은 메인 소유입니다.

## 미실행과 경계

메인 독립 검토는 실제 Home.save·Desk.persist·Center.submit 및 ApiError/초안 초기화를 AST로 추출하여 **22/22**, 초기화 제거 변이 **1/1**, Owner 콜백 배선 **1/1**을 확인했습니다. 실제 상담 저장 성공으로 이전 토스트를 만든 뒤 지연 요청의400/503/응답 유실/성공을 대조했습니다. expectedRevision=41과 미확정 payload를 유지했고 성공 setter는 응답 뒤에만 호출됐습니다. 소스 SHA `56f2a9dcacd0ebfccb58f6cb36b43e10df1f51d4a5e7b6a857dd1d5c1f5887eb`가 실행 전후 같았습니다. 첫 독립 검사21/22는 같은 성공 문구가 반복되면 실패로 보는 검사기 오탐이었으며, 제품 변경 없이 초기화→성공 setter 순서를 대조하여22/22로 정정했습니다.

메인의 실제 Next 빌드는 21:56:19 KST 완료했습니다. sourceBefore=sourceAfter `716e1cdc1a2b738b50f74c5cbcb62f8564e92e4d34e8b49f0b3d38790a7048be`, output26개 fingerprint `2b2889efda74036be37a2936763f05a376c4a83fb4e9f65a1134918077b571aa`입니다. 이 빌드는 CCTV 조사 화면과 아래 v3 public fixture 정정도 포함하며, 브라우저 실행 증거는 아닙니다.

새 브라우저 회귀 **0/1 NOT_RUN**, 실제 HTTP·React 화면 페인트·토스트 타이머·메뉴 이동 후 화면은 재측정하지 않았습니다. 이번 증거는 순수 action 실행이며 PC4 실브라우저 반례의 재실행을 대신하지 않습니다. 이미 진행 중인 다른 작업이 나중에 성공하는 동시 완료 순서 제어는 이번 최소 수정 범위가 아닙니다.

메인이 전달한 자동 승인 검토에서 서버 `http.listen(0)` + Chromium 실행이 **blocked by policy**로 거부됐고 상세 이유는 제공되지 않았습니다. 다른 방법·에이전트로 우회하지 않았습니다. 이번 작업의 서버 시작0·브라우저 시작0·네트워크 호출0입니다.
