# 실제 CCTV 연결 통합 검수

검수 시각: 2026-09-21 17:38:40 KST (2026-09-21T08:38:40.522Z)  
대상: localhost:3100의 CASE-0002 → WMS → W-W3 분기 이동  
환경: 새 Chromium 브라우저 컨텍스트, 1280 × 1000 화면. 기존 메인 시연 페이지와 별도 컨텍스트를 사용하고 검수 뒤 닫았다.

## 판정

요청한 실제 데이터 연결·영상 열기·메타데이터·재생·Escape 종료·포커스 복귀·타 이벤트 미등록 항목은 통과했다. fixture/API/영상 응답을 가로채거나 대체하지 않았다. 코드 수정은 수행하지 않았다.

이 결과는 **로컬 AI 브라우저 자동화 검수이며, 원격 PC 또는 다른 사람이 수행한 검수·사용성 평가가 아니다.** 1280 × 1000 한 화면 폭에서 이번 경로를 확인했다. 타 브라우저·모바일·영상 오류 복구는 이번 검수의 판정 범위에 포함하지 않는다.

## 기대값과 실측

| 항목 | 기대 | 실측 | 판정 |
|---|---|---|---|
| 실제 API | 실제 사례 API에서 media 읽기 | GET http://127.0.0.1:8100/api/cases → HTTP 200 | 통과 |
| 연결 범위 | CASE-0002, WMS, W-W3에만 연결 | 실제 media.caseId=CASE-0002, system=WMS, eventIds=[W-W3] | 통과 |
| 작업 이벤트 CTA | 분기 이동에 영상 버튼 1개 | 이벤트 목록 4개 중 CCTV 버튼 수 [0, 0, 1, 0] | 통과 |
| 팝업 메타데이터 | 사건·카메라·이벤트·시각·구간 표시 | CASE-0002 / SYN-CAM-02 / W-W3 / 09.18 02:33 KST / 0–12초 | 통과 |
| 합성 표시 | 실제 CCTV로 오인하지 않게 표시 | AI 합성 · 실제 CCTV 아님, REFERENCE ONLY, 귀책 확정 금지 문구 확인 | 통과 |
| 실제 MP4 | 등록된 URL에서 12초 영상 로드 | GET /demo/sorter-demo.mp4 → HTTP 206, duration=12, 960×540, media.error=null | 통과 |
| 재생 | 재생 시간이 증가하고 paused=false | 0.003096초 → 0.614190초, 두 시점 paused=false | 통과 |
| Escape 종료 | 팝업 닫힘·영상 정지 | dialog 0개, 원래 video 노드 connected=false, paused=true | 통과 |
| 닫힌 뒤 정지 유지 | 시간이 더 증가하지 않음 | 닫힘 후 0.998097초, 350ms 뒤에도 0.998097초 | 통과 |
| 포커스 복귀 | 영상을 연 이벤트 버튼으로 복귀 | document.activeElement가 원래 CTA와 동일 | 통과 |
| 다른 이벤트 | 피킹·소터 투입·출고에 영상 재사용 금지 | 세 이벤트 모두 연결 영상 미등록, CCTV 버튼 0개 | 통과 |
| 원본 대조 | 관측값과 원인 미확인을 구분 | 피킹 비스킷 18 EA / 출고 휴지 1 BOX, 발생 공정·귀책 미확인 표시 | 통과 |
| 읽기·재생 범위 | 상태 변경·분석·유료 호출 없음 | 관측된 non-GET 요청 0개, PATCH/analyze/replay 요청 0개 | 통과 |
| 화면 오류 | 현재 경로의 페이지 예외 없음 | pageerror 0개. API 200·영상 206·재생 증가를 함께 확인 | 통과 |

## 재현 절차

1. 새 브라우저 컨텍스트에서 http://127.0.0.1:3100 을 연다. 라우트 가로채기를 등록하지 않는다.
2. 상단 WMS 작업 확인 → 주문 상품과 다른 상품 입고(CASE-0002)를 선택한다.
3. 작업 이벤트 중 02:33 분기 이동의 AI 합성 CCTV 구간 보기를 누른다.
4. 팝업의 사건·카메라·이벤트·시각·구간·합성 라벨과 오른쪽 스캔 비교를 읽는다.
5. 실제 video 요소를 재생한다. 검수에서는 음소거 상태로 재생하고 600ms 사이의 currentTime을 비교했다.
6. 재생 중 Escape를 누른다. DOM에서 분리된 기존 video 요소 핸들을 유지해 paused 및 currentTime 정지를 두 시점에서 확인한다. 원래 CTA에 포커스가 돌아왔는지 확인한다.
7. 나머지 세 작업 이벤트가 영상 미등록인지 확인한다.

## 실제 API의 연결 정보

```json
[
  {
    "id": "SYN-CCTV-CASE2-SORTER",
    "caseId": "CASE-0002",
    "system": "WMS",
    "cameraId": "SYN-CAM-02",
    "eventIds": [
      "W-W3"
    ],
    "url": "/demo/sorter-demo.mp4",
    "synthetic": true,
    "startSeconds": 0,
    "endSeconds": 12,
    "occurredAt": "2026-09-18T02:33:00+09:00",
    "label": "분기02 → D-02 공정 합성 영상",
    "notice": "AI로 만든 공정 설명 영상. 실제 작업·휴먼에러·귀책 증거가 아님."
  }
]
```

## 재생·닫기 실측 원자료

```json
{
  "at": "2026-09-21T08:38:40.522Z",
  "viewport": {
    "width": 1280,
    "height": 1000
  },
  "metadata": {
    "src": "http://127.0.0.1:3100/demo/sorter-demo.mp4",
    "duration": 12,
    "readyState": 1,
    "width": 960,
    "height": 540,
    "error": null
  },
  "before": {
    "time": 0.003096,
    "paused": false
  },
  "playing": {
    "time": 0.61419,
    "paused": false
  },
  "afterClose": {
    "time": 0.998097,
    "paused": true,
    "connected": false
  },
  "later": {
    "time": 0.998097,
    "paused": true
  },
  "dialogCount": 0,
  "focusReturned": true,
  "responses": [
    {
      "url": "http://127.0.0.1:8100/api/cases",
      "status": 200
    },
    {
      "url": "http://127.0.0.1:3100/demo/sorter-demo.mp4",
      "status": 206
    }
  ],
  "nonGetRequests": [],
  "forbiddenApiRequests": [],
  "pageErrors": []
}
```

