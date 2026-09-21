# 사용자 요청에 따른 로컬 병렬 구현 착수

> 아래는 작성 시점의 역사적 관측입니다. 현재 등록·Goal·배포 상태는 CURRENT_TODO.md와 planning/decisions.md의 후속 결정을 따릅니다.

2026-09-21 KST. DEC-013·014. 기존 45개 작업표의 설계·4PC·실사용자 게이트가 완료되었다는 뜻이 아니다. 실제 Goal도 아직 실행하지 않았다.

사용자는 시간 제약으로 즉시 구현, AI Playwright 검증, 역할 자동 배분, 대기세션1~6 활용을 요청했다. 로컬 합성 데모 구현을 진행하고 실제 4PC 신원 등록·왕복은 별도로 수행한다. 사람 4명의 의견이나 사람 사용성 테스트 결과를 생성하지 않는다.

| 책임 | 소유 경로 | 상태 판정 |
|---|---|---|
| 메인 pc1 | data/fixtures, planning, 통합·음성 준비 | 실제 결과로 인수 |
| Ultra app_ui | apps/web (LogisticsView 제외) | build+기능검증 |
| 대기세션1 | LogisticsView.tsx/module.css | 별도 WMS/TMS 화면 |
| 대기세션2 | mailbox 감시 실행기·docs19 | 신원 게이트·중복/종료 검증 |
| 대기세션3 | 합성 MP4·생성기 | 디코딩·워터마크 확인 |
| 대기세션4 | tests/e2e·reports/e2e | replay 기반 독립 Playwright |
| 대기세션5 | server·백엔드 테스트 | 중단된 Ultra worker 인수 |
| 대기세션6 | 로컬 실행기·docs20 | 재현 가능한 실행 안내 |

Vercel/AWS 배포는 이번 착수에 포함하지 않는다. API 키는 로컬 데모 전용이며 코드·보고·GitHub에 노출하지 않는다. 실제 API 호출과 replay를 분리한다. 음성 준비·명시적 live 시연 외 개발 자동검사는 API를 호출하지 않는다.
