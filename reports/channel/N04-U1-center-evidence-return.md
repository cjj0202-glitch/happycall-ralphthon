# N04-U1 / P1 — 센터의 TMS 조사 흐름과 읽기 전용 상태

## 결론
pc4 장준호 / j324rst-svg는 발표 PDF를 멈추고 TMS 제품 UI를 수정합니다. 사용자 요청은 상담원·센터 담당자의 실제 업무 순서에 맞춘 하나의 시스템입니다.

## 왜 지금
기준 main `ed2b188de31091a71f1596f50961239d02813107`, 저장소 `C:/Users/j324r/OneDrive/문서/ChatGPT/해커톤_D-Day/happycall-ralphthon`입니다. 이전 D1 결과는 보존합니다. 메인은 `page.tsx/globals.css/workflow.ts`의 역할별 작업큐·단계·복귀를 구현 중이고, WmsScene은 메인 소유입니다.

## 해줘야 할 일
소유 `apps/web/components/TmsScene.tsx`, 필요할 때만 `TmsScene.module.css`, 새 `tests/e2e/tms-role-readonly-unit.mjs`, `reports/pc4/tms-role-readonly-*`입니다. 다른 작업자 변경을 되돌리지 마세요.

- TmsScene에 선택적 `backLabel?: string`을 추가합니다. 기본값은 기존 `상담으로 돌아가기`, 메인은 센터 진입 시 `센터 업무로 돌아가기`를 전달합니다. 기존 onBack 콜백은 그대로 호출합니다.
- 추가 계약: `readOnly?: boolean`(기본 false)을 받습니다. 최종 잠금은 부모 readOnly **또는** 기존 사건 상태 잠금이며 false가 상태 잠금을 해제할 수 없습니다. 센터가 전체목록에서 이관 전 접수를 열어도 쓰지 않도록 메인이 true를 전달합니다. true + draft의 버튼/직접 link 호출 차단도 검사하세요.
- 사건 상태 handed_off/in_progress/closed이면 근거 조회는 유지하고 연결 쓰기를 막습니다. 실제 `link()` 진입부와 버튼 disabled 양쪽 모두 가드합니다. pending/연결됨/타점포/관계오류 등의 기존 차단 조건을 약화하지 않습니다.
- readOnly 화면에는 `센터 조사 중 · 이관된 접수의 근거는 조회만 할 수 있습니다`처럼 이유를 알립니다. closed는 처리완료 표현을 쓰고 이관 이후 이유를 유지합니다. 이미 연결된 근거는 그대로 보여줍니다.
- 새권한·로그인·푸시발송은 없습니다. role은 현재 시제품의 업무화면 선택이며 실제 인증으로 표시하지 않습니다. 기존 경로·도착시각·GPS·미확인 구분을 보존합니다.
- 바꾸기 전에 사용자 과업·상태·props·검증을 짧게 설계하고 작은 정상/차단 대조군을 만든 뒤 구현하세요. 새색·폰트·라이브러리 없이 기존 tokens를 사용합니다.

## 실행 명령
whoami·Git 상태 확인, 고정 main파일과 자기 TMS소스 차이 확인 후 기존 브랜치 사용. 순수 TypeScript/JSX 함수 검사와 타입 검사만 수행합니다. 소유 파일만 커밋·push 후 원격 SHA 대조합니다.

## 검증 방법 + 기대값
draft/review의 정상 관련 근거는 기존대로 연결 가능. handed_off/in_progress/closed에서는 직접 link 호출도 onLinkEvidence 호출0, 버튼 disabled. 비교 방문/잘못된관계/중복연결/진행중 기존회귀 보존. 기본/센터 backLabel과 실제 콜백1회 대조. 가드제거 변이로 검증의 검출력을 확인합니다. 첫 코드결과20분 목표, 실제실행/미실행을 나눕니다.

## 중단 조건 + 인계
새 서버·브라우저·소켓·설치·과금·배포·운영데이터·다른 소유 파일 변경은 없습니다. 메인의 거부된 검증을 다른PC에 넘기는 작업이 아닙니다. #10에 ACK와 결과SHA/명시파일/명령·기대·실측/실패수정/한계를 회신하세요. 최신 제품 전체 브라우저 검수나 N04전체 인수를 의미하지 않습니다.
