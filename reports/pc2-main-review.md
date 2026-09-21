# pc2 CallReview 메인 독립검토

2026-09-21 pc1의 읽기 전용 독립 검토자. pc2 결과 `7ae648eb4bfb8f7e00ab842b39ad86e0df0ac134`, main `3beada0`를 대조했습니다. 실제 React SSR와 독립 loopback Edge에서 실행했고 원격 소유 파일과 기존 API는 수정하지 않았습니다. 전체 앱 통합 완료가 아닙니다.

## P1: 현재 상담 입력과 과거 확인 상태가 함께 표시됨

대상: pc2 `reports/pc2/integration.md` Desk 연결 예시. `intake: form`은 새 입력인데 `reviewConfirmed`는 저장된 `c`에서 상속됩니다.

재현: 실제 main `field()`의 수량을 6→999로 바꾸고 예시의 reviewCase를 구성해 실제 CallReview를 `renderToStaticMarkup`으로 렌더했습니다.

```json
{"savedQuantity":6,"editedQuantity":"999","parentConfirmed":false,"reviewCaseConfirmed":true,"actualReactContainsEdited999":true,"actualReactContainsConfirmedLabel":true,"positiveControlForwardingConfirmedRemovesLabel":true}
```

연결 예시에 `reviewConfirmed: confirmed`를 추가하고 부모에서 유지해야 합니다. 서버 이관 우회를 발견했다는 뜻이 아니라 잘못된 확인 표시입니다. pc1 최종 연결에서 수정·회귀를 수행합니다.

## 실행한 독립 동작 검사

실제 컴포넌트를 TypeScript in-memory compile→React→Edge로 실행하고 1.5초 합성 WAV를 제공했습니다. 전체 자연 종료 콜백1, 끝 seek 후0, 구간0.15~0.5초 재생은0.524326초에서 정지/콜백0, 이후 처음부터 전체 재생1, disabled 일시정지/controls false/단순재개 완료0, 사건 교체의 이전 ended/error 무시, 새 사건 전체1, 같은ID 다른URL 재시도 비활성, 텍스트 audio없음/재시도1을 관측했습니다. pageerror0·외부요청0입니다.

검사 서버 초기 charset·WAV Range 누락은 harness를 보정한 뒤 재실행했습니다. 제품 결함으로 세지 않습니다. 두 fixture의 sourceText와8발화 조합은 각각 일치했습니다. 타입검사 대상에 CallReview가 포함됩니다.

## 판정과 남은 범위

연결 예시 P1 수정 필요. 원격 자체26검사와 이번 독립 동작 검사는 최종 main 연결/API 회귀·CSS 시각·실제 한국어 청취를 대신하지 않습니다. 부모 분석함수 내부에서도 음성 전체 완료·잠금·busy·fallback 조건을 검사하고 분석 오류와 저장 오류, 선택모드와 결과 출처를 구분해야 합니다.
