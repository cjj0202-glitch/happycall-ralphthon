# N02-M3 후속: 정상 API와 오프라인 예시의 검증 범위

2026-09-21 22:10 KST에 [메인의 22:02 정정 알림](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/8#issuecomment-5760919013)을 확인했다. 알림은 pc2 결과 회신(22:03:29) 직전에 발송돼 이번 감시 주기에서 읽었다. 기존 결과 커밋은 `d65a798b62395a1ec1ad6c02e118f2dc9a2f9409`, 제품 기준은 `92d2ecbad981f366a9e5ffc850d9c2bb7fd5d3a2`로 유지한다.

**14/14 PASS는 고정 제품의 정상 API 상담 흐름에 한정한다. 오프라인 합성 예시의 v3 정합성은 포함하지 않았다.** 이번 후속은 Git blob과 이미 보존된 실제 요청 기록의 정적 대조다. 새 브라우저·서버·빌드·제품 수정은 없다.

## 정정 알림과 기존 증거 대조

- 기존 최종 `parent-2026-09-21T12-51-25-545Z/results.json`에는 `GET /api/cases` 9회, `GET /cases.json` 0회가 기록돼 있다. 정상 replay 성공 POST2와 의도503 POST1은 기존 결과 그대로다. 오프라인 예시 버튼이나 서비스 중단 후 그 경로를 실행한 증거로 쓰지 않는다.
- 제품 `92d2ecb`의 Git 정본과 public 사본을 JSON으로 대조해 **17경로 차이**를 독립 확인했다. CASE2 audioUrl1, 발화4~8의 start/end10, transcriptTiming6이다. public 사본의 옛 시각과 메타데이터는 실제 v3 음원에 맞는 자료가 아니다.
- 메인 수정 `7ca0e8ba85dbfa7bff85577d4b0d019756e53e35`에서는 두 Git blob 모두 **23,090B / SHA256 c7449e66a89c6c2b43b9b09868d651379a376e25a27f3f227b99375c7fa51449**, JSON 차이0이다.
- 메인이 보고한 Windows 정본/public/export **23,693B / SHA256 5edf80669f7def9d3e10ceea910086c41026ff1252fbc638b97641562f3d84f4**는 위 Git blob의 LF를 CRLF로만 변환한 바이트와 정확히 일치했다. 메인의 export를 pc2에서 새로 실행·다운로드했다는 뜻은 아니다.

전체 차이값, Git blob 크기/SHA, 기존 요청 기록 SHA와 경로별 횟수는 [offline-scope-review.json](offline-scope-review.json)에 있다. 기존 실행 원본과 `evidence-index.json`은 변경하지 않았다.

## 인계

기존 보고의 “이번 범위에서 공용 제품 수정이 필요한 결함을 발견하지 못했다”는 문장은 정상 API 검사 범위의 관측이다. 오프라인 경로에는 메인이 발견한 위 결함이 존재했음을 이 후속 문서로 명시한다. 메인 수정본의 브라우저 동작·배포 묶음 통과를 pc2의 PASS로 소급하지 않는다. 기존 임시 실행 거부 경계를 우회하거나 추가 재검을 맡은 것으로 해석하지 않는다.

현재 M3는 결과 제출 후 메인 인수 대기이며, 사람 청취·실운영·최종 배포·전체6회 인수·별도 TEST는 계속 별도다. 이 문서는 새 기능 인수나 중앙 작업표 완료를 선언하지 않는다.
