# N04-U1 메인 TMS 역할 동선 인수

2026-09-21 pc1/CJJ. 고정 원격 `79d763acd2985c32e0eb853d17a7d68dce0174d0`의 지정 파일10개를 원 Git 바이트로 가져왔습니다. TmsScene 이외의 제품 파일을 덮어쓰지 않았습니다. 메인 역할 UI 기준은 `7d186fd`입니다.

## 코드와 검사

main 기준 diff는 선택적 backLabel/readOnly props, 상태·부모 읽기전용 OR, remount 키에 상태/부모prop 추가, link 함수 및 버튼 가드, 실제 상태별 안내입니다. 기존 ApiError의 저장 결과 미확정 처리와 방문·관계·시간 판단은 유지했습니다.

메인의 현재 의존 파일을 고정해 실행했습니다:

```powershell
node tests/e2e/tms-role-readonly-unit.mjs --dependencies-ref 7d186fd --json
node apps/web/node_modules/typescript/bin/tsc --noEmit --incremental false -p apps/web/tsconfig.json
```

36/36, 가드 제거 변이2/2 검출, TypeScript exit0입니다. 상세 원시 결과는 `.local/tms-role-readonly-main-results.json`입니다. 순수 검사에서 실제 JSX/콜백/effect 정리는 실행하지만 React DOM·실제 쓰기 취소를 증명하지 않습니다.

## 메인의 실제 기존 화면 대조

기존 IAB tab6, 동일 CASE-0001(상담원 확인 상태)을 두 역할로 열었습니다. 조회·선택·복귀만 수행했으며 근거 저장은 누르지 않았습니다.

| 관측 | 기대·실측 |
|---|---|
| 센터 → 전체 → CASE-0001 → TMS | 센터 역할·CASE-0001 유지, 읽기 전용 안내1개 |
| 센터 근거 연결 | 버튼2개 disabled=true,true |
| 센터로 돌아가기 | 센터 전용 문구, 복귀 후 센터 및 CASE-0001 aria-pressed=true |
| 상담원 → 같은 CASE-0001 → TMS | 버튼2개 disabled=false,false |
| 상담으로 돌아가기 | 기본 문구1개, 기존 상담 작업대 복귀 |

이번 인수 범위는 N04-U1의 역할별 TMS 조회·읽기전용·복귀입니다. 전체 N04, 최신 빌드6회 완주, 영속 저장, 실제 외부 배포는 완료가 아닙니다. 신규 웹 접수의 현재 API CORS 차단은 [별도 실행 기록](role-flow-live-check.md)에 남겼습니다.

23:09:27 KST에 새 production build와 로컬 배포 묶음 생성도 완료했습니다. 산출 파일26개, 빌드 전후 소스 SHA256 `93ef17c8ebe9900743cc71e1d5cb462825fd8b59de43fefa6008a78ee7903b37` 일치, 출력 SHA256 `d1dd1d5f5d374bf5024939f5066020608cca79ce6765e61a71af62b220fbdb97`입니다. 기존 개발 서버와 `.next-dev`는 재시작·교체하지 않았습니다.
