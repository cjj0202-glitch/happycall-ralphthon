# 합성 CCTV 조사 화면 상세설계

2026-09-21 / pc1 로컬 구현. WmsScene의 기존 영상 대화상자를 이 컴포넌트로 교체했습니다. 최종 영상·좌표 등록과 수정본의 통합 브라우저 검수는 미완료입니다.

## 사용자 결과와 정보 위계

센터 담당자가 선택 사건의 공정 영상을 직접 재생하고, 한 프레임의 시각 객체를 선택하여 등록 사건·시각·슈트/도크와 원본 피킹/출고 기록을 비교합니다. 실물 동일성, AI 검출 정확도, 작업자 귀책을 판정하지 않습니다.

`CctvInspector`는 기존 VideoDialog의 clip/event/picking/shipping/opener/onClose 계약을 그대로 받습니다. optional tracks descriptor는 `{url,bytes,sha256,videoSha256,schemaVersion:'oneflow-cctv-tracks-v1'}`입니다. clip/event 유효성은 WmsScene 등록 검증이 선행하며, 조사 화면도 영상 경로·해시·크기·구간과 tracks 관계를 독립 확인합니다.

기존: 영상 재생 + 원본 레코드. 변경: 상단 사건/고정 기록시각 → 큰 영상/시연 경과시간/재생 조작 → 시각 객체와 원본 기록 비교. 전체 화면에서도 합성 표시와 구간 조작은 영상과 함께 유지합니다. 좁은 화면은 영상 다음 상세 패널을 배치합니다. 별도 영구 네비게이션을 추가하지 않습니다.

## 디자인 브리프

시계열 Master-Detail + 보기모드 패턴(DESIGN_SYSTEM §11). 기존 semantic/scale 토큰만 사용하며 별도 색/폰트 팔레트를 도입하지 않습니다. surface/border/text/action/status/focus 및 control/space/radius/font 토큰을 적용합니다. 원본/객체 표시를 독립 보기 전환으로 두며 객체 선택은 버튼+aria-pressed로 제공합니다. 토큰 정본 primitive/semantic/scale/biz를 직접 대조했고, 컨셉 카탈로그는 정보 밀도 참고에 한정합니다.

## 검증과 시간 계약

1. 영상 로컬 경로, SHA256, 바이트 수를 검증한 뒤 Blob URL을 사용합니다. 15초 타임아웃, 재시도, 취소·해제 시 pause/abort/revoke를 유지합니다.
2. tracks는 별도로 해시/크기를 검증합니다. descriptor 영상 SHA와 clip SHA, JSON source/synthetic/좌표계/시계모드, anchor case/event/camera/occurredAt, 필요하면 chute/dock을 대조합니다. W-W3는 사건 이벤트이며 E-W3 근거와 바꾸지 않습니다.
3. 1부터 연속 frame, `(frame-1)/fps` elapsed, 유한하고 정렬된 [0,1] bbox, 양의 정수 해상도, phase(approach→branch→chute→settle 비역전), 단일 visualObjectId, null businessToteId, occlusionTested=false만 현 계약에서 허용합니다.
4. 디코딩된 영상 해상도·길이를 tracks fps/frameCount/resolution과 대조합니다. 현재 승인 960×540 영상과 후보 1280×720 tracks는 다른 장면이므로 결합하지 않습니다. 테스트용 합성 좌표는 실제 영상 정합 증거가 아닙니다.
5. 고정 occurredAt은 움직이지 않습니다. 표시 프레임은 rVFC mediaTime을 우선 사용하고 seeked/timeupdate/RAF fallback으로 동기화합니다. 임의 벽시계로 프레임을 진행하지 않습니다.
6. 등록 `[startSeconds,endSeconds]` 밖 seek를 제한합니다. 재생/정지, 0.5/1/2×, 구간 반복, 검증된 fps가 있을 때만 ±1 프레임을 제공합니다. 부분 구간 끝은 실제 자산의 해당 프레임으로 표시합니다. 자산 전체 길이에 도달한 경우만 마지막 유효 프레임으로 제한합니다.

## 상태·복구·접근성

### 프레임 경계 조작 보완 — 2026-09-22

유효 등록 구간 안에서 `+1 프레임`은 표시 시간을 감소시키지 않고, `−1 프레임`은 증가시키지 않습니다. 마지막 프레임에 이미 도달한 `+1`은 현재 시각과 프레임을 유지합니다. 예: 전체 12초의 끝은 12.000초/288프레임을 유지하고, 부분 구간 끝 6.010초는 6.010초/145프레임을 유지합니다(24 fps). 종료점의 `−1`은 기존대로 이전 유효 프레임으로 이동합니다. 구간 밖 이동 제한, pause, 좌표 미검증 시 비활성화를 보존합니다.

검사 계획: 실제 TS 함수 실행으로 전체/부분/프레임에 맞지 않는 경계와 24·25·30 fps를 확인합니다. 시간 단조성과 구간 경계를 별도 불변식으로 확인하고, 현재 프레임 제한 및 방향별 시간 보존을 제거한 변이를 검출합니다. 이 검사는 브라우저 디코더와 실제 영상 픽셀의 일치를 증명하지 않습니다.

영상 loading/error/ready와 tracks loading/error/ready/없음을 분리합니다. tracks 불량은 좌표만 차단하고 검증 영상은 사용할 수 있습니다. 영상 불량은 재생 자체를 차단합니다. 재시도는 사용자 동작만으로 합니다. 마운트·보기 전환에서 자동 재생하지 않습니다.

native modal dialog + Escape/배경/닫기, 명시적 Tab wrap, opener focus return. 객체는 키보드 선택 가능하고 좌표 없는 프레임은 객체 미표시로 설명합니다. reduced motion은 장식 전환을 제거하며 영상은 사용자 재생으로만 시작합니다. 원본 레코드 펼침, 상품·수량·단위·토트 및 귀책 미확인 문구를 보존합니다.

## 수용 검사

격리 하네스: 정상/해시 오류/다른 사건·이벤트·카메라·시각·영상/해상도/NaN bbox/역전 phase/누락 프레임/범위 이탈/404·재시도, 구간 반복과 frame step, 원본·표시, 선택, 전체 화면, Escape·포커스, 390/768/1440 overflow, reduced motion. 실제 PC3 최종 렌더의 픽셀-좌표 정합은 메인 수신 후 별도 검수해야 합니다. 라이브 AI·유료 API 0회.

## 파일 소유

CctvInspector.tsx / module.css / lib/cctv-tracks.ts / 이 설계 / reports/cctv-inspector.md / 전용 tests/e2e/cctv-inspector-*만 구현자 소유입니다. WmsScene·fixture·manifest·배포는 메인 소유이며 변경하지 않습니다.
