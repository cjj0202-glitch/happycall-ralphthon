# 근거 연결 후 자기 저장 충돌 수정

- 관측·검증 시점: 2026-09-22 06:57 KST, PC1 `최제준`
- 기준: `e4868f6` 이후 작업 트리. 이 문서는 커밋·배포·사람 검증 완료를 뜻하지 않습니다.
- 범위: 상담원 접수 검토 → WMS/TMS 근거 연결 → 상담으로 복귀.

## 문제와 수정

메인의 실제 브라우저 CASE-0001/0002 관측에서는 근거 연결에 성공했는데도 상담 화면 복귀 시 `서버의 접수 내용이 변경되었습니다`가 표시됐습니다. 근거 PATCH가 서버 revision을 증가시키는 동안 Desk는 화면에서 내려가고, 메모리 초안의 `formRevision`은 이전 값으로 남았습니다. 사용자는 자신의 저장을 다른 저장과 대조하는 복구 절차를 거쳐야 했습니다.

`Home.onLinkEvidence`는 근거 PATCH의 성공 응답을 받은 뒤 `acceptOwnEvidenceSave`를 호출합니다. 다음을 모두 만족할 때만 해당 접수의 메모리 초안 revision을 한 단계 진행합니다.

- 기존 초안과 요청 전 접수 revision이 일치하고, 같은 접수의 응답 revision이 정확히 +1입니다.
- 상담원의 이관 전 접수이며, 이전 저장 결과가 불확실하거나 저장·분석 작업이 진행 중이지 않습니다.
- 저장된 근거가 이번 요청의 근거 목록과 일치하고, 서버의 확인 해제 상태가 일치합니다.
- 접수 필드·부서·상태·분석·원문·전사·기타 본문 내용이 바뀌지 않았습니다.

사용자가 작성한 폼·부서·메모·edited와 미저장 표시를 보존하고, 확인 체크는 해제해 새로 연결한 근거를 다시 확인하게 합니다. 조회·이동·409·실패·응답 유실·이미 낡은 초안은 revision을 갱신하지 않습니다. 다른 접수의 초안도 변경하지 않습니다.

메인의 코드 검토에서 분석 응답이 `history`, `updatedAt`, `analysisRequestId`를 Home에 반환하지 않는 경계가 확인됐습니다. 이 서버 생성 메타데이터는 비교에서 제외합니다. 접수 5필드는 실제 폼과 같은 null/빈칸 의미 및 고정된 키 순서로 대조합니다. 정확한 요청 revision을 서버가 원자적으로 검사한 성공 응답이라는 조건은 유지합니다.

## 실행 검증

| 명령 | 실측 |
|---|---|
| `node tests/e2e/evidence-self-save-unit.mjs` | 45/45 PASS, 동작 변이 5/5 감지 |
| `node tests/e2e/role-workflow-unit.mjs` | 87/87 PASS, 변이 7/7 감지 |
| `node tests/e2e/save-toast-unit.mjs` | 48/48 PASS, 변이 3/3 감지 |
| `node tests/e2e/mobile-work-navigation-unit.mjs` | 89/89 PASS, 변이 9/9 감지 |
| `node tests/e2e/call-playback-preference-unit.mjs` | 21/21 PASS, 변이 7/7 감지 |
| `node tests/e2e/notification-status-unit.mjs` | 124/124 PASS, 변이 4/4 감지 |
| `npm.cmd run typecheck --prefix apps/web` | PASS |
| `git diff --check` | PASS |

신규 검사는 실제 JSX 콜백, 실제 Home.save, 실제 메모리 초안 저장소를 실행합니다. 네트워크 응답만 제어하며 정상 저장, 수정 전 대기, 저장 실패·응답 유실, 낡은 초안, 저장 중, 잘못된 응답, 본문 변경, 다른 접수, 중복 선택, 연속 저장과 예전 응답 재사용을 대조합니다. 분석 직후 누락된 메타데이터/정규화된 null 및 역순으로 직렬화된 접수 필드도 양성 대조에 포함했습니다.

Windows 작업 트리의 CRLF 때문에 기존 음성 배속 변이 검사의 LF 고정 anchor가 처음에는 실행 중단됐습니다. `replaceOnce` 안에서 변이 대상 텍스트 줄바꿈만 정규화했고, 실제 동작 검사·실패 조건은 유지한 뒤 21/21과 7/7을 재확인했습니다.

로컬 상세 증거: `.local/evidence-self-save-unit-1790027776674/results.json`, `.local/role-workflow-unit-1790027697528/results.json`, `.local/save-toast-unit-1790027697896/results.json`, `.local/mobile-work-navigation-unit-1790027699016/results.json`. 원본 실행 로그는 로컬에 유지합니다.

## 한계·인수

이 담당 범위에서는 브라우저·서버를 시작하거나 실제 HTTP 요청·AI 유료 호출·Git 커밋·push를 수행하지 않았습니다. 메인이 별도 브라우저에서 합성 텍스트 접수의 근거 연결과 확인·이관을 재검증합니다. 위 결정론 검사만으로 실제 사용자 검증이나 운영 배포 완료를 주장하지 않습니다.

## 별도 담당자의 독립 검토

2026-09-22 별도 검토자는 `acceptOwnEvidenceSave`, 실제 `onLinkEvidence` 콜백, `Home.save`, Desk의 revision/저장 경로와 HTTP 오류 처리를 읽었다. 이 한정 범위에서 낡은 revision의 서버 검사를 우회하거나 로컬 초안을 덮어쓰는 결함을 재현하지 못했다. 근거 연결은 요청 당시 revision으로 PATCH하고 성공 응답을 기다린 뒤만 helper에 도달한다. 서버 CAS를 대신하는 최신 revision의 임의 주입은 없으며, 초안 revision이 이미 다르거나 저장 결과가 불확실하면 helper가 거절한다.

독립 Node 실행기는 실제 TS helper와 JSX 콜백을 메모리에서 실행하고 네트워크 경계만 제어했다. **7/7 통과**: 성공 응답 전 불변 및 대기 중 추가 편집 보존, 이미 수용한 응답 재사용 거절, 기존 낡은 초안 거절, 다른 작업 진행 중 거절, 이전 저장 불확실 시 거절, 서버 접수 본문이 달라진 응답 거절, 실패한 실제 콜백에서 helper 미호출. 정상 경로에서도 폼·부서·메모·edited를 유지하고 확인만 해제하며 미저장 상태를 보존했다.

```powershell
node .local/main-resume-20260922/independent-evidence-review.mjs
# passed 7 / total 7, networkCalls 0, browserStarts 0
```

독립 결과는 `.local/main-resume-20260922/independent-evidence-review.json`에 있다. 검사 전후 소스 바이트 불변을 확인했으며 SHA256은 `drafts.ts`의 `80d0512f42e831775b0ad4acd23874edcb848aa11edb5276466ffee53f0a2fe6`, `page.tsx`의 `c3b1ea6437468a19298e48f8e4a6e1b0406f562fe77be011ac7a8cccf03abb23`이다. 이 검토자는 제품 파일·기존 검사 파일을 수정하지 않았다. 실브라우저·서버 저장·이관 인수는 메인의 별도 관측이며 위 7개와 합쳐 같은 검사 분모로 보고하지 않는다.
