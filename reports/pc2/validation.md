# N02 메인 인수용 검증 요약

2026-09-21 pc2 / 안영일 / MR-A83. N02 #8의 독립 통화 검토 컴포넌트와 검증 자료를 제출한다. 제품 기준은3c5e5a3, branch는 `work/pc2-n02-call-review`이며 결과 커밋은 같은 이슈 회신에서 확인한다. 공용 page/API/타입/fixture/manifest/중앙 표는 변경하지 않았다.

## 실제 결과

| 검사 | 명령/자료 | 결과 |
|---|---|---|
| 최종 실제 렌더 | `node tests/remote/pc2/run.mjs` | 19:10:27~19:11:52 KST,26/26 PASS, exit0 |
| production build | apps/web에서 `npm.cmd run build` | 수정 후 exit0, 정적 페이지 생성 완료 |
| 타입 | apps/web에서 `npm.cmd run typecheck -- --incremental false` | 구현 담당 수정 후 exit0 |
| PCM 측정 | `python scripts/media_pc2/measure_audio.py --v1-dir .local/demo-media-backups/20260921T093437Z-iwm8nlqd` | 승인 v1/v2 해시·크기 확인, 비교6/6 PASS, 입력8개 전후 SHA 불변 |
| 측정 도구 반례 | `python -m unittest discover -s scripts/media_pc2 -p 'test_*.py' -v` | 루트 재실행7/7 PASS |
| 독립 리뷰 | `independent-review.md` | 별도 담당 정적 검토, RAF 반례 추가→수정→동일 조건 재검. 추가 차단 결함 미발견 |

최종 CallReview SHA256은 `e861bc8ff7775e51be35c67f72364fdda261bd43407f4962be06367831fd6161`이다. 브라우저는 Edge153.0.4234.48 headless. 원래 WAV 두 개를1배속으로 자연 종료하고 played범위0–끝, callback각1, error없음을 확인했다. 페이지 예외·외부/제품 API·유료 호출0, 소스 전후 SHA 동일, 자체 서버/브라우저 종료6/6 complete다. 각 입력과 기대/실측·실패 이력은 `browser-results.json` 및 `browser-focused-results.json`에 있다.

## 구현과 수정

- 원대본/출처가 명시된 전사/AI 제안/현재 상담 입력/추가 질문을 분리한다. 1EA 현재 입력과1BOX 제안·주문18EA를 혼동하지 않고 null점포·수량0을 보존한다.
- native audio, 배속·볼륨·음소거·키보드·구간 재생, 오류/누락·분석 중/실패/재시도를 지원한다. 구간/seek/오류/disabled/이전 사건 이벤트는 전체 완료를 열지 않는다.
- 소수초 표시 결함을 같은0.15–0.8초 입력으로 수정·재검했다. RAF중단 반례의 무제한 구간 초과 재생을 timeupdate 보조 검사와 숨김 중단 정책으로 보완했다. A/B 화자 이름을 추정하지 않고 실제 라벨과 서로 다른 색을 유지한다.
- 1440/1024/390px 긴 내용에서 수평 넘침0을 측정하고 실제 렌더 이미지를 검토했다. 상세 전후 기록은 `work-log.md`, `browser-validation.md`와 `screenshots/`에 있다.

## 남은 메인 인수와 한계

1. `integration.md`의 부모 연결 예시를 검토해 공용 화면에 연결한다. 현재 form/표시 결과의 출처/분석 전용 상태를 전달하고 사건·음원 전환 시 부모 전체재생 게이트도 초기화한다. 최종 저장·이관·전체 서비스 회귀는 pc1 인수 항목이다.
2. 실제 최소화/백그라운드 상태는 headless 환경에서 재현되지 않았다. RAF/visibility 주입으로 분기를 검사했다. 구간 종료는 이벤트 간 지연 후 정지·커서 보정이며 표본 단위 컷이 아니다.
3. 사람 청취·OS 출력·Silent Test·STT 정확도 일반화는 미검증이다. PCM/RMS 실측과 메인 LUFS 인용을 구분한다. 최초 상담 입력의 영구 이력 보존은 부모/서버 계약이다.
4. 사용자 접근 허용 팝업 보고 후 추가 테스트를 중지했다. 하네스의 BrowserServer host를127.0.0.1로 제한하고 구문 검사만 했다. 이 마지막 테스트 실행 설정의 실제 재실행과 팝업 재발 여부는 미검증이다. 제품 SHA는 그대로다.
5. TEST 왕복은 N02 ACK/제품 검증과 별개로 미완료다. 메인 통합·인수·이슈 종결·배포를 이 PC에서 완료 처리하지 않았다.
