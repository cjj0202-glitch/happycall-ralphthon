# 저장 성공 알림 수명 — P2 최소 수정

2026-09-21 / pc1. 근거는 PC4 고정 c6f734f의 Q3-08 실제 화면·HTTP 증거이며 공유 결과 커밋 d7841717e8181d4f9315a20dee5099c073251019입니다.

## 문제와 사용자 결과

첫 저장 성공 뒤 6초 안에 다음 저장 응답이 유실되면 직전 성공 토스트와 현재 저장 여부 미확정 안내가 동시에 나타납니다. 성공 판정 자체가 잘못된 것은 아니며, 이전 작업의 알림이 현재 작업에 붙어 보이는 문제입니다. 새 작업이 시작되면 이전 성공 알림을 지우고, 현재 요청의 기존 성공 경로에서만 새 알림을 표시합니다.

## 변경 위치와 경계

- Home.save 시작의 setToast('')로 상담 저장/이관, 센터 중간/최종 회신, WMS/TMS 근거 연결의 공통 PATCH 경로를 처리합니다.
- Desk.analyze 시작, Owner.submit/verifyAttempt 시작에서 기존 onToast('')를 사용합니다. Owner에는 같은 기존 setter를 전달합니다.
- Desk/Center.inspectLatest 및 Home.reload/loadExample 시작에도 이전 작업 알림을 비웁니다. 대조 GET200을 저장 성공으로 바꾸지 않으며 기존 sameMutation 성공 분기만 새 성공 토스트를 냅니다.
- busy/stale 등의 조기 반환으로 실제 작업을 시작하지 않는 호출은 기존 상태를 유지합니다. 폼 편집·미저장 초안·revision·pendingActions·idempotency key·복구 분기·성공 조건·6초 타이머는 변경하지 않습니다.

## 검증 방법

실제 page.tsx의 Home/Desk/Owner/Center 함수 안의 action을 TypeScript AST로 추출·transpile하여 setter·draft·deferred request만 대역으로 제공한 순수 실행을 합니다. 이전 성공→현재 요청 대기→실패503/응답 유실/성공과 복구 조회를 대조합니다. 공통 저장 초기화/분석/접수 초기화를 제거한 변이가 이전 성공을 남기는지 검사합니다. 서버·브라우저·네트워크 시작은 하지 않습니다. 이는 화면 페인트/React 타이머/원격 HTTP를 실제 재검증한 결과가 아닙니다.

소유: page.tsx, tests/e2e/save-toast-unit.mjs, 이 설계, reports/save-toast.md. 다른 파일 수정·전체 빌드·브라우저 재실행은 메인 범위입니다.
