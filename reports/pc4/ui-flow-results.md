# N04 기존 제품 UI 실제 HTTP 재현 결과

기준 HEAD: `a952edee271574401332148f42969621a81a74d7`. 제품 소스 해시 전후 동일: **True**. API `http://127.0.0.1:18105`, UI `http://127.0.0.1:13105`. 실제 pc4/장준호 Windows에서 AI Playwright로 관측했습니다.

**두 합성 사례 각 3회, 총 6/6 UI 완료. 별도 경계 검사 6/6 통과.** 제품 공유 소스 수정 없이 입력·버튼으로만 분석/review·근거 연결·이관·센터 회신·종결·경영주 조회를 수행했습니다. 상태 조회 GET은 검증에만 사용했습니다.

| 실행 | 음성 방식 | 실제 재생 대기(초) | UI 완료 |
|---|---|---:|---|
| CASE-0001-1 | 처음부터 끝까지 1배속 | 47.782 | PASS |
| CASE-0001-2 | 실제 재생 시작 후 끝부분 탐색 → 실제 ended | 1.437 | PASS |
| CASE-0001-3 | 실제 재생 시작 후 끝부분 탐색 → 실제 ended | 1.434 | PASS |
| CASE-0002-1 | 처음부터 끝까지 1배속 | 49.693 | PASS |
| CASE-0002-2 | 실제 재생 시작 후 끝부분 탐색 → 실제 ended | 1.438 | PASS |
| CASE-0002-3 | 실제 재생 시작 후 끝부분 탐색 → 실제 ended | 1.415 | PASS |

각 사례 첫 회의 WAV 전체 실제 재생 종료를 확인했습니다. 반복 2~3회는 탐색을 사용했으므로 전체 길이 청취 6회가 아닙니다. 가짜 ended 이벤트는 0회이며 실제 사람의 청취·내용 이해·사용성 관찰을 뜻하지 않습니다.

## 수행한 흐름

실제 음성 종료 → 저장된 replay 분석 → WMS/TMS 원본 펼침·현재 사건의 근거 연결 → 요청사항 편집·부서 확인·확인 체크·센터 전달 → 중간 회신·남은 조치가 있는 동안 종결 버튼 비활성 → 조치 완료·최종 회신 → 경영주 화면의 등록 회신·처리 완료 확인. 저장 원문 보존·최종 center 역할·빈 잔여 조치도 GET으로 대조했습니다.

## 경계 관측

| 검사 | 결과 |
|---|---|
| new-text-different-day-no-implicit-evidence | PASS |
| explicit-reference-text-media-missing | PASS |
| media-404-and-retry | PASS |
| api-error-and-recovery-no-false-save | PASS |
| api-offline-example-and-reconnect | PASS |
| browser-offline-save-and-recovery | PASS |

신규 텍스트는 동일 점포·제목을 써도 자동 근거가 붙지 않았고 원문이 보존됐습니다. 신규 텍스트 replay 분석은 409로 설명되며 실제 AI 정제는 **미실행**입니다. 명시적으로 CASE-0002를 연결한 신규 텍스트도 media를 자동 복사하지 않아 WMS 영상 미등록이 표시됐습니다.

영상 404 때 원본 스캔은 유지되며 재시도 후 실제 video 시간이 진행됐고 Escape로 닫혔습니다. API 503·브라우저 offline 상태에서는 거짓 저장 성공 없이 오류가 표시되고 원본 revision은 보존됐으며 재연결 후 UI 저장이 성공했습니다. API만 끊긴 경우 읽기 전용 합성 예시와 복구도 확인했습니다.

## 실패·수정 이력

첫 탐색 `ui-flow-20260921T102639552019Z`는 두 음성 전체 재생·분석·WMS/TMS 연결 뒤 정확 label 매칭 locator에서 2회 실패했습니다. 제품 결함이 아닌 검사 코드의 locator 결함으로, 테스트 소유 파일만 수정하고 동일 제품 소스에서 위 6회를 다시 실행했습니다. 초기 실패와 PNG는 보존합니다.

## 보존·실행 경계

- 유료 분석기 호출 `0`, 외부 연결 시도 `0`.
- 기존 `.local/cases-store.json`·`demo-usage.json` 전후 해시 동일: `True`.
- 본 실행이 만든 API 정지 `True`, Next 프로세스 트리 정리 exit `0`. 기존 8100/3100 서버는 조작하지 않았습니다.
- `.env`와 실제 과금 원장을 로드하지 않았습니다. 각 run은 새 임시 사례 저장소이며 테스트 종료 후 정리됩니다.
- 브라우저 pageerror는 `0`건. console error 5건은 409/404/503/연결거부/offline 반례의 의도된 응답입니다.
- 새 pc4 TmsScene은 page/LogisticsView에 미통합입니다. 이 결과는 기존 TMS 화면의 검사이며 신규 TMS 인수 증거가 아닙니다.
- 이 실행은 desktop 1365×950이고 새 컴포넌트의 3폭·키보드·reduced-motion 검사는 별도입니다. 실제 STT/GPT 정확도, 사람 검수, 운영 인증, 배포, 전체 공식 평가를 완료한 결과가 아닙니다.

## 재현과 증거

```powershell
. '..\Start-HappyCall.ps1'
python tests/remote/pc4/flow-ui-run.py
```

- 실제 결과: [results.json](ui-flow-20260921T102917851879Z/results.json)
- HEAD·소스·실사용상태 보존·프로세스 정리: [harness.json](ui-flow-20260921T102917851879Z/harness.json)
- 화면: [CASE-0002 최종 조회](ui-flow-20260921T102917851879Z/CASE-0002-1-owner.png), [영상 404](ui-flow-20260921T102917851879Z/media-404.png), [오프라인 저장](ui-flow-20260921T102917851879Z/browser-offline-save.png)
- 실행 로그: `.local/ui-flow-20260921T102917851879Z/` (Git 제외).
