# N03 WMS 공정·합성 영상 상세설계

기준 d4b4a8137fbc608911e9f6f71bd4b5e289e0a958 / 이슈 #9 / pc3 LAPTOP-U2AL73UH, mcjun86-oss.
2026-09-21 사용자 “N03 구현 시작” 승인. TEST 왕복은 미완료이며 이 작업으로 대체하지 않는다.

## 사용자 결과와 화면

상담원이 같은 사건의 피킹→소터 투입→분기/슈트→출고 기록을 선택하고, 기록의 상품·수량·단위·토트 차이 및 다음 확인 행동을 읽는다. CASE1의 미수령 진술과 센터 출고 기록을 분리한다. CASE2의 비스킷 18 EA와 휴지 1 BOX를 차감/환산하지 않고 병렬 비교한다. 발생 공정·작업자 귀책 및 토트 A→B 연결은 미확인으로 남긴다.

상단 사건·점포·기준시각 → 차이/미확인 요약 → 네 공정 버튼·설명 애니메이션 → 선택 기록/다음 행동 → 영상·원본 → 상담 근거 순서. 애니메이션은 기본 정지, 시작/정지와 모션 감소 지원. 이는 공정 설명이고 실시간 위치 추적이 아니다. snapshot 누계를 이벤트처럼 재구성하지 않는다. 입력 events를 원본 순서로 보존하고 시각 역전/누락/미래시각을 경고한다.

## 키·시간·출처 및 영상 연결

- 현 fixture에는 event-level 점포/주문/토트/카메라 키가 없다. 원천 실물 연결을 검증했다고 주장하지 않는다. 확인 범위는 합성 fixture에 등록된 사건/이벤트/카메라 관계다.
- caseData.id/store.id, picking.orderId/toteId, shipping.id/toteId를 읽기 전용 기준 fixture와 대조한다. event id/time/source/location 및 optional relation fields 불일치는 영상 연결을 차단한다. 다른 날짜/점포/토트의 자료를 유사 영상으로 대체하지 않는다.
- pc1 후속 검토에 따라 신규 `INT-*` 텍스트 접수는 명시 `linkedFixtureId`로 원본 CASE를 찾는다. 현재 접수와 원본 ID를 화면에 분리하고 점포/type/asOf 및 복사 WMS·evidence 전체를 대조한다. 객체 키 순서는 허용하지만 배열 순서·원본 행 변형은 차단한다. 원본 근거 연결과 영상 등록은 별개이며 신규 INT에 원본 media를 자동 상속하지 않는다. 상세 계약·반례는 linked-intake-fix.md에 있다.
- 기존 sorter-demo는 CASE-0002 / W-W3 / SYN-CAM-02만 허용. media id/case/system/camera/eventIds/occurredAt/url/구간을 등록 행과 정확히 대조하고 중복 후보는 거부한다. 등록되지 않은 후보는 영상 미등록이다.
- SHA256/bytes/duration은 공용 manifest를 읽고, fetch한 실제 영상 바이트를 Web Crypto로 검증한 뒤 Blob URL로 재생한다. URL은 등록된 같은 origin /demo 경로만 사용. 해시/구간/404 실패는 인라인 복구와 원본 열람을 제공한다.
- occurredAt=event.time, 명시된 timezone, event.time<=case.asOf가 필요하다. 과거 사례를 현재시간과 비교해 임의 stale 처리하지 않으며 사건의 asOf를 표시한다. 시각 역전은 정렬로 감추지 않는다.
- 후보 6개(2사건×피킹/분기/출고)는 코드 애니메이션으로 별도 생성하며 data/overlays/pc3-wms.json에 메타데이터·방법·해시를 기록한다. 원본은 .local만 보관. 메인의 승인·설치·정본 등록 전 자동 병합하지 않는다.

## 상태·권한·복구

WmsScene 기본 export props: caseData: CaseData, onLinkEvidence(id): Promise<void>|void, onBack():void. main 소유 page/LogisticsView/types/API/fixture/manifest는 변경하지 않는다. callback 성공 후에만 근거 연결 완료 표시, 처리 중 중복 클릭 방지. 실패 시 사유와 재시도. 이관 이후 읽기 전용. 사건·asOf·revision 변경 시 미디어/선택/에러 상태를 초기화한다. 모달 닫기/Escape 시 정지·objectURL 해제·호출 버튼 초점 복귀. 자동 재생하지 않는다.

## BMAD·Grill-me·Bolt

- 업무: 관측값과 원인을 분리한 올바른 확인 요청이 결과다.
- UX: 선택한 공정의 사실/미확인/다음 행동과 연결 영상을 함께 보여준다.
- 구조: 공용 계약은 읽기 전용, 소유 컴포넌트/overlay/미디어 생성기/테스트/보고만 작성한다.
- 검증: 실제 렌더·재생·음성 없는 반례와 해시 변조를 검사한다. 기술 검증이며 실제 사람 Silent Test가 아니다.
- 기존 결정 재질문 없음. pc1이 지정한 후보 Release 태그로 6개 MP4와 메타데이터 공유·재수신 검증을 마쳤다(media-release.md). 정본 등록/셸 통합·최종 인수는 pc1이 진행하며 기존 영상은 등록된 설명 범위만 허용한다.
- 작은 Bolt: 선택 이벤트가 맞는 영상만 열리는 병목 하나. 기존 느슨한 event→clip 조건의 반례를 고정하고 엄격한 등록 대조/해시 검사 후 같은 반례와 정상 재생을 다시 검사한다.

## 인수

scenario-test-plan.md의 분모별 실측·명령·화면·실패/수정은 verification.md에 기록한다. 자체 완료/중앙 작업표 변경/이슈 종결 금지. pc1의 리뷰·셸 통합·독립 적대검증·최종 인수는 별도다.
