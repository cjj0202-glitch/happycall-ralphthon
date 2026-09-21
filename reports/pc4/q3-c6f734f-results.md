# N04-Q3 독립 복구 검수 결과 — c6f734f 고정

2026-09-21 / pc4 장준호 / GitHub j324rst-svg / 작업 브랜치 work/pc4-n04-tms-qa.
배정: [#10 comment5760348790](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/10#issuecomment-5760348790).

**독립 8축의 명시적 관측 297/297이 통과했습니다. 별도로 P2 성공 알림 잔류 1건이 남습니다.** 저장 상태와 초안 잠금 검사는 통과했지만, 아래 UI 혼선을 포함해 무결점으로 판정하지 않습니다. pc1 인수 대기이며 제품 변경·배포는 하지 않았습니다.

## 기준과 격리

- 제품 SHA: `c6f734f60d0dbe0151a69e35b8dfd8a41f3c5bd5`의 별도 깨끗한 `happycall-q3-c6f734f` worktree.
- 새 빌드 source fingerprint: `4d6d0f6b9dc00b874efbb2549d7ffc5369cfdde62af86f3f36cd8d2b1764a9b8`.
- production output fingerprint: `3d1be22730f4f84d1e7933099818f3ee6dd354b149774cdad4558fbe1623eab7`.
- 최종 실행: **21:30:23.564–21:30:54.084 KST**, [harness](q3-run-20260921T123023563161Z/harness.json), [실제 관측](q3-run-20260921T123023563161Z/results.json), [무결성 대조](q3-run-20260921T123023563161Z/integrity-crosscheck.json).
- 실제 Next production export와 제품 create_app/CaseService/JsonCaseRepository를 same-origin `127.0.0.1:8941`에서 사용했습니다. 축마다 새 합성 저장소와 브라우저 컨텍스트(고유 저장소 8개)를 사용했습니다. 다른 담당자 변경·센터 선행 상태는 기록된 공개 HTTP 요청으로만 만들었습니다.
- 기존 운영 원장·키를 제품 실행에 연결하지 않았습니다. API·브라우저 외부 연결 차단, 과금 analyzer 호출 0, analyze 요청 0, 기존 상태 보존, 자체 API 종료를 확인했습니다. 기존 감시기와 다른 서버는 종료하지 않았습니다. 합성 Temp는 보존했습니다.
- Python 3.12.14 / Node 24.19.0 / Playwright 1.58.2 / Chromium 145.0.7632.6. 실행파일 절대경로와 Chromium 실행파일 SHA는 harness에 있습니다.

## 기대값과 실측

| 축 | 초기 상태·입력 / 기대 | 실제 결과 | 관측 수 |
|---|---|---|---:|
| Q3-01 | CASE-0001/0002의 상담·센터 초안, 추가/미추가 조치. 메뉴·사례 왕복 뒤 각 초안 유지, 미저장 내용은 서버에 없음 | WMS/TMS·사례 왕복, 역할별 초안과 조치 보존 PASS. 센터 선행 handoff는 실제 HTTP setup으로 별도 기록 | 57 |
| Q3-02 | 별도 담당자 실제 PATCH 뒤 목록 새로고침. 자동 덮어쓰기 없이 대조·명시 선택 | 상담·센터 초안/서버 대조, 서버 선택/초안 유지, 확인 초기화, 상담의 명시 저장 PASS | 37 |
| Q3-03 | 실제 UI POST201 저장 후 응답만 유실, 조회404 주입, 같은 키·같은 본문 UI 재시도. 신규 정확히1건 | 실제 POST201 두 번, 동일 `INT-B8CDBAEB`, 신규 +1, revision0/history1, 기존 사례 불변 PASS | 42 |
| Q3-04 | UI 생성 키로 다른 본문을 공개 HTTP로 재전송. 실제409, 원접수 불변 | `IDEMPOTENCY_CONFLICT`409, `INT-573C819D` revision0/history1 및 목록 불변 PASS. UI의 409 표시 검사는 아님 | 17 |
| Q3-05 | 실제 PATCH 저장 후 응답 유실. 동일 내용 조회 또는 다른 담당자 후속 수정 대조 | 유실2회 모두 실제200 commit 확인. 첫 GET은 정확한 저장 확인, 후속 변경은 대조·명시 서버 선택, 자동 덮어쓰기0 PASS | 50 |
| Q3-06 | 서버에 전달하지 않은503 후 정상 GET. 조회 성공만으로 저장 성공 처리 금지 | GET200은 원래 revision0/내용, 미저장 초안 유지·대조·잠금, 유지 선택 자체는 저장 안 함 PASS | 24 |
| Q3-07 | 대조 후 초안 유지 직후 제3자 실제 수정. 재시도409, 초안 유지·재대조 | 실제 UI409 두 번, 대조한 revision으로만 요청, 제3자 revision2 유지, 명시 서버 선택까지 초안 유지 PASS | 35 |
| Q3-08 | 저장 응답 보류·유실 때 메뉴 왕복과390px 키보드 조작. 편집·중복 저장 잠금 | 실제 commit2건, 보류/유실 각1회. 추가 PATCH0, 사례별 잠금, Enter 조회로 복구 PASS. 이전 성공 토스트 잔류는 아래 P2 | 35 |

8축 전부 실행했고 NOT_RUN은 0입니다. Q3-03의 404와 Q3-06의 503은 선언된 실패 주입입니다. 성공 응답은 모두 실제 서버에서 받았습니다. Q3-08의 비활성 버튼에 대한 DOM click 시도는 중복 요청이 발생하지 않는 추가 요청 차단 검사이며, 정상 저장·이동·키보드 선택과 구분합니다.

브라우저 pageerror 0 / setup 오류0. 콘솔에는 의도한 오류8건이 있습니다: 응답 유실4, 조회404 1, 미저장503 1, 실제충돌409 2. 이를 콘솔 오류0으로 보고하지 않습니다. 화면14장은 최종 실행 폴더에 보존했습니다.

## P2 — 직전 성공 알림과 새 저장 미확정 안내가 함께 표시됨

[390px 원본 화면](q3-run-20260921T123023563161Z/Q3-08-q3-08-uncertain-390.png)에 녹색 `상담원이 편집한 접수 정보를 저장했습니다.`와 현재 `저장 여부 확인이 필요합니다`가 동시에 있습니다.

실측 순서는 첫 저장 revision1(21:30:50.339)의200 응답을 UI에 전달한 뒤, 다음 저장 revision2(21:30:50.779)는 실제 반영됐지만 응답을 유실시킨 것입니다. 즉 두 번째 실패 경로가 새 성공 판정을 낸 증거는 아니며 **첫 성공 알림의 잔류**입니다. 저장 여부 미확정 상태·편집 잠금·추가 저장 차단 자체는 작동했습니다.

고정 제품 [page.tsx:45](https://github.com/cjj0202-glitch/happycall-ralphthon/blob/c6f734f60d0dbe0151a69e35b8dfd8a41f3c5bd5/apps/web/app/page.tsx#L45)의 전역 토스트는6초 후 사라집니다. 상담 저장 시작/실패186–194행은 기존 토스트를 지우지 않으며 센터346–352행에도 같은 패턴이 있습니다. 따라서 직전 성공6초 이내 새 변경의 **미저장503에서도 이전 성공 문구가 남을 가능성은 소스에서 추론**됩니다. 이 조합의 추가 브라우저 실행은 하지 않았습니다. Q3-06은 깨끗한 컨텍스트였고 Q3-05는 이전 토스트가 만료된 뒤 다음 반례를 실행했으므로 그 통과 결과로 이 조합을 덮지 않습니다.

pc1 개선 제안: 새 저장 시작 때 이전 성공 토스트를 제거하고, 성공→다른 내용 저장503→GET 원본 응답 순서에서 새 초안이 저장됐다는 오해가 없는지 별도 회귀검사하십시오. 제품 소유권에 따라 pc4는 수정하지 않았습니다. 같은 PC의 별도 검토자도 소스·실제 HTTP·화면을 읽고 P2로 판단했습니다. 이는 원격 다른 PC의 인수 실적이 아닙니다.

## 실패·검사기 수정·재실행을 보존함

[전체 시도 요약](q3-attempts-summary.json). 같은 제품·빌드·자산으로 세 번 실행했습니다.

| 실행 폴더 | KST | 결과 | 검사기 오류와 수정 |
|---|---|---|---|
| [122615](q3-run-20260921T122615781324Z/harness.json) | 21:26:15–21:27:54 | 3/8 PASS, 5 FAIL | 관련접수 select와 요청사항 label의 exact locator가 실제 접근성 이름과 불일치. 실제 select·고유 placeholder로 한정 |
| [122909](q3-run-20260921T122909815385Z/harness.json) | 21:29:09–21:29:58 | 7/8 PASS, 1 FAIL | Q3-03 실제201 이후 입력값이 label 이름에 합쳐져 상세내용 exact locator 실패. 해당 form의 고유 textarea로 한정 |
| [123023](q3-run-20260921T123023563161Z/harness.json) | 21:30:23–21:30:54 | 8/8 PASS, 297/297 | 같은 입력·제품으로 재검증. 제품 수정0 |

실패를 제품 결함이나 PASS로 바꾸지 않았습니다. 각 실행 전 **실제 검사기/helper11개 원본**을 tester-source에 복사했고 실행 전후 SHA와 보존본을 대조했습니다. 첫 실패 원본도 남아 있습니다. Q2의 과거31f1ffd2… 원본은 별도 백업을 찾지 못했으며 당시 해시·실행 증거만 보유한 P2 이력으로 유지합니다. 재구성본을 원본으로 제출하지 않습니다.

## 지문·줄바꿈·승인 자산

[실행 계약](q3-c6f734f-contract.json), [빌드](q3-c6f734f-build.json), 각 실행의 release-contract.json과 integrity-crosscheck.json에 원본 해시를 보존했습니다. 빌드 입력67개와 output26개 전후 일치. fixture·manifest·TMS overlay를 source fingerprint에 포함했습니다. fixture/manifest는 LF이고 고정 Git blob과 바이트 동일합니다. 검사기·보존 소스도 LF이며 Git 저장 전후 바이트 대조를 시행합니다. 보존 디렉터리의 .gitattributes는 tester-source 변환을 끕니다. 공유용 빌드 JSON 사본만 기존 CRLF를 LF로 정규화했으며 실행한 원본 빌드 기록·제품·검사기는 바꾸지 않았습니다.

계약 도구의 `referenceMainSha`와 사용하지 않는 Q2 UI selector는 이전 도구의 호환 메타데이터입니다. Q3 제품 식별은 `finalSha=c6f734f…`이며 Q3는 독립 모듈을 실행했습니다. 메타데이터를 사후 조작하지 않고 실행 당시 계약을 그대로 보존했습니다.

승인 Release는 `demo-media-20260921-audio-v2`만 사용했습니다. 새 음성/영상을 가져오지 않았으며 각 파일의 전체 실제 HTTP 바이트 SHA와 Range206을 확인했습니다.

| 파일 | bytes | SHA-256 |
|---|---:|---|
| CASE-0001.wav | 2263278 | d4eeb6448ff8969f27034ecade9a050ee212468585c6300b19c9a0ebdc372931 |
| CASE-0002.wav | 2378478 | 333897f4f10426674ec97b9e3a44c2f8da21f1f7931b4f911c82a29abcf6b914 |
| sorter-demo.mp4 | 1097133 | e6cad3cf9f999b596a0fef3e3d463170e0d279568a31a4be49366e5383908881 |

## 재현과 인수 범위

로컬 도구 PATH와 `E2E_CHROMIUM` 실제 경로를 준비하고, 같은 Git SHA의 별도 worktree/승인 자산/계약에 맞는 production export를 준비합니다. 다른 빌드를 사용하는 경우 새 fingerprint와 결과를 분리하십시오.

```powershell
python tests/remote/pc4/q3-run.py --release-contract reports/pc4/q3-c6f734f-contract.json --product-root ../happycall-q3-c6f734f --execute
```

재현은8941이 비어 있고 필수 제품/소스/자산/출력 지문이 같을 때만 실행됩니다. 환경 준비·빌드 원본 명령과 절대 실행파일은 q3-c6f734f-build.json 및 harness에 있습니다. 본 실행의 tester Git HEAD는 ca00b2f였고 미커밋 검사기는 원본 SHA로 고정했습니다. 공유 커밋은 같은 이슈에 별도 회신합니다.

합성·격리 UI/API 검수이며 사람 검증·실제 과금 AI·영속 배포·브라우저 종료 후 복구를 뜻하지 않습니다. 공유 기준 검사41개나 이전 Q2음성6회를 여기에 합산하지 않았습니다. Q2 인수는 bfc8543에 한정됩니다. 제품/공통 API/fixture/중앙 작업표 변경0, 실제 배포0. TEST 편지 왕복은 별도 미완료로 유지합니다. P2 알림 개선 및 최종 인수는 pc1에 요청합니다.
