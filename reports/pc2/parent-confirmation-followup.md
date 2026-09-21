# N02 부모 확인 상태 전달 보완

2026-09-21 pc2 / 안영일 / MR-A83. 메인7242c69의 `docs/27_원격PC_실제배정과_인수.md`와 `ops/overnight-tasks.json`에 기록된 N02 검토 의견을 확인했다. 최초 결과는7ae648e이며 이 후속은 연결 예시 문서 수정이다.

## 문제와 수정

기존 `reviewCase` 예시는 `intake: form`만 덮어쓰고 `reviewConfirmed`는 `...c`에서 가져왔다. 실제 부모의 `field()`와 부서 변경은 현재 `confirmed`를false로 바꾸므로, 저장된 확인값이true인 접수를 편집한 뒤 현재 입력과 과거 확인값을 섞어 표시할 수 있었다. 반대로 새로 확인을 체크해도 저장된false가 남을 수 있었다.

`integration.md` 예시에 `reviewConfirmed: confirmed`를 추가했다. 현재 입력과 현재 확인 상태를 함께 전달하고, 이를 서버 저장이나 이관 완료와 구분하도록 설명했다. 공용 page와 제품 컴포넌트는 수정하지 않았다.

| 저장된 c.reviewConfirmed | 현재 confirmed | 기존 예시가 전달하는 값 | 수정 예시가 전달하는 값 |
|---|---|---|---|
| true | false(편집으로 해제) | true, 오래된 확인 상태 | false |
| false | true(현재 폼에서 확인) | false, 현재 체크 누락 | true |
| false | false | false | false |
| true | true | true | true |

위 표는 실제 예시와 부모 상태 갱신 코드를 대조한 **정적 계약 분석**이다. 새 브라우저 실행·UI 동작 실측이나 부모 서비스 통합 PASS가 아니다. 메인의 독립 재현은 메인 문서의 보고로 구분한다. 기존26건 브라우저 PASS를 이 부모 연결의 실행 증거로 확장하지 않는다.

## 정적 확인과 인수

- 현재 부모는 필드 수정, 부서 변경, 분석 성공 후 `setConfirmed(false)`를 호출한다. 저장 요청은 현재 `confirmed`를 사용한다.
- CallReview는 전달받은 `caseData.reviewConfirmed`만 읽는다. 따라서 부모가 현재 폼을 전달할 때 그 폼의 확인 상태도 전달해야 한다.
- 관련 diff와 공용 파일 미변경을 확인했다. 팝업 반복 보고 이후 추가 브라우저·서버·보조 에이전트를 실행하지 않았다.
- 메인 통합 시 저장된true 접수 편집→확인 표시 해제, 현재 체크true→표시 갱신, 사건 변경·분석 성공 후 초기화를 실제 부모 UI에서 확인한다. 기존 저장 revision·이관 게이트는 유지한다.
