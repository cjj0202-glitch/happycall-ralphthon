# OneFlow 작업표

> 정본: ops/tasks.json. 이 파일은 `python ops/tasks.py render`로 생성합니다.
> 체크는 pc1의 증거 검증 뒤에만 붙습니다. 담당 슬롯은 역할 제안이며 PC 등록 전에는 배정되지 않습니다.

전체 31개 중 0개 완료. 준비 작업을 포함한 수치이며 제품 완성률이 아닙니다.

## 0 사전 운영 준비

- [ ] **S01 설계·작업표·사전 준비 패키지 검증** — pc1 · TODO · 45분
  선행: 없음 / 산출물: reports/setup-validation.md
  - C1: 공유 스킬·감시·작업표 검사 결과와 한계를 실제 출력으로 기록
  - C2: 설계 03~08, 프롬프트, 준비 스크립트의 상호 참조와 완료 규약 일치

- [ ] **G01 공식 일정·심사·제출·API 예산 확인** — pc1 · TODO · 30분
  선행: S01 / 산출물: reports/event-constraints.md
  - C1: 공식 안내 출처·일정·발표 시간·필수 AI 조건을 기록
  - C2: 제품 API 사용 여부·건수/금액 상한과 P0 승격 여부 결정

- [ ] **R01 팀원 3명 계정·hostname·역할 등록** — pc1 · TODO · 30분
  선행: S01 / 산출물: reports/team-registration.md
  - C1: pc2~4 각자의 GitHub·hostname·역할이 pcs.json과 일치
  - C2: 두 private 저장소 초대 수락 및 각자 접근 확인

- [ ] **R02 pc2 미디어 노트북 사전 점검** — pc2 · TODO · 45분
  선행: R01 / 산출물: reports/readiness/pc2.json
  - C1: 해당 PC의 도구·GitHub·등록 계정·킷·HEAD 점검 통과
  - C2: 미디어 패키지와 작은 음성·영상 파일 재생 확인

- [ ] **R03 pc3 근거 UI 노트북 사전 점검** — pc3 · TODO · 30분
  선행: R01 / 산출물: reports/readiness/pc3.json
  - C1: 해당 PC의 도구·GitHub·등록 계정·킷·HEAD 점검 통과
  - C2: 브라우저 실행과 계약 샘플 읽기 확인

- [ ] **R04 pc4 접수 노트북 사전 점검** — pc4 · TODO · 30분
  선행: R01 / 산출물: reports/readiness/pc4.json
  - C1: 해당 PC의 도구·GitHub·등록 계정·킷·HEAD 점검 통과
  - C2: Python 실행과 replay/live 권한 상태 분리 기록

## 1 설계 검증

- [ ] **P01 킷 합성 데이터·기본 시연 재현** — pc1 · TODO · 45분
  선행: S01 / 산출물: reports/kit-reproduction.md
  - C1: 킷 SHA·seed·22개 테이블 생성 결과 기록
  - C2: 스모크 각 단계 성공·실패·건너뜀과 생성물 재생 확인

- [ ] **P02 두 케이스 계약·정답 fixture 고정** — pc1 · TODO · 60분
  선행: P01, G01 / 산출물: contracts/case-v1.json, tests/eval/cases.json
  - C1: 실제 생성된 미도착·오출 ID와 조인 키를 확인
  - C2: 20개 입력과 12개 경계 검사 정답·null 규칙을 고정

- [ ] **P03 설계·기술 결정·데이터 계약 대조** — pc1 · TODO · 45분
  선행: P02 / 산출물: reports/design-review.md
  - C1: 설계 03~06과 fixture의 필드·키·상태 일치
  - C2: 미해결 배포·실제 AI·예산 조건을 명시하고 필수 경로 차단 여부 판정

- [ ] **G02 4PC 준비와 설계 확인 후 배정 개시** — pc1 · TODO · 20분
  선행: P03, R02, R03, R04 / 산출물: reports/kickoff.md
  - C1: 4PC 준비 기록과 역할·소유 경로 확인
  - C2: 공식 조건을 반영한 P0 완료선과 첫 작업 ID를 확정

## 2 제품 구현

- [ ] **S02 공통 앱 골격·lock·테스트 명령 고정** — pc1 · TODO · 60분
  선행: G02 / 산출물: reports/app-baseline.md
  - C1: T1 결정에 맞춘 앱 구조·lock·실행 명령을 기록
  - C2: 깨끗한 설치에서 타입 검사·빌드·계약 샘플 실행 성공

- [ ] **M01 미도착·오출 합성 음성 제작** — pc2 · TODO · 60분
  선행: G02 / 산출물: assets/audio-manifest.json
  - C1: 두 케이스 음성·원문·길이·SHA·생성 방법 매핑
  - C2: 키·실제 고객 음성 없이 로컬 재생 성공

- [ ] **M02 근거 영상과 미디어 manifest 제작** — pc2 · TODO · 90분
  선행: M01 / 산출물: assets/manifest.json
  - C1: 두 케이스 clip·토트/차량·센터·시간·SHA 매핑
  - C2: 정상 영상과 누락 대체를 재생하고 Release 전달 경로 기록

- [ ] **E01 근거 조회 repository 구현** — pc3 · TODO · 60분
  선행: G02 / 산출물: reports/E01-result.md
  - C1: 주문·방문·출고 관계를 fixture와 대조
  - C2: null·충돌·다른 점포/토트 제외 검사가 모두 기대 결과

- [ ] **E02 케이스 목록·근거 표 화면 구현** — pc3 · TODO · 90분
  선행: E01, S02 / 산출물: reports/E02-result.md
  - C1: 두 케이스 필터와 원본 행 드릴다운 확인
  - C2: loading/empty/error/stale/ready와 케이스 전환 초기화 확인

- [ ] **E03 영상 연동·누락·재생 실패 처리** — pc3 · TODO · 60분
  선행: E02, M02 / 산출물: reports/E03-result.md
  - C1: manifest와 연결된 영상만 재생
  - C2: 404·잘못된 토트·케이스 전환에서 안전한 화면 표시

- [ ] **I01 접수 추출 공급자·발화 근거 구현** — pc4 · TODO · 60분
  선행: G02 / 산출물: reports/I01-result.md
  - C1: fixture/manual 공급자가 공통 계약과 발화 참조 반환
  - C2: 빈 입력·미식별 필드 null·수량 0 보존 검사 통과

- [ ] **I02 상담 접수 화면 구현** — pc4 · TODO · 90분
  선행: I01, S02 / 산출물: reports/I02-result.md
  - C1: 접수 필드 수정과 발화 하이라이트 확인
  - C2: replay/manual 모드 표시와 필수 필드 확인

- [ ] **I03 근거 기반 답변·사람 확인 상태 구현** — pc4 · TODO · 90분
  선행: I02, E01 / 산출물: reports/I03-result.md
  - C1: 누락을 확정으로 바꾸지 않고 사실·미확인·초안 분리
  - C2: 사람 확인·중복 requestId·낡은 version 검증 통과

## 3 통합 검증

- [ ] **J01 미도착 한 건 전체 흐름 통합** — pc1 · TODO · 60분
  선행: E02, I03 / 산출물: reports/J01-result.md
  - C1: CASE-0001 접수부터 추가 확인 이관까지 실제 통합
  - C2: 도착 실적 없음과 원본 근거를 화면에서 대조

- [ ] **J02 오출과 영상까지 통합** — pc1 · TODO · 60분
  선행: J01, E03 / 산출물: reports/J02-result.md
  - C1: 실제 오출 케이스의 기대/출고 차이와 영상 연결
  - C2: 두 흐름의 이력 저장·초기화·재시작 확인

- [ ] **Q01 20입력·12경계 평가** — pc4 · TODO · 60분
  선행: J02 / 산출물: reports/evaluation.md
  - C1: 필드 정확도 분모·값·실패 입력 공개, 90% 목표 비교
  - C2: 12경계의 근거 없는 확정 0건·기대 상태 일치

- [ ] **Q02 화면 상태·키보드·오프라인 검사** — pc3 · TODO · 60분
  선행: J02 / 산출물: reports/ui-validation.md
  - C1: 세 화면의 5상태·키보드·전환·미디어 오류 확인
  - C2: 네트워크 단절 시 모드 전환을 표시하며 두 흐름 완주

- [ ] **Q03 Before/After 대응 비교 실측** — pc1 · TODO · 60분
  선행: Q01, Q02 / 산출물: reports/benchmark.md
  - C1: 3명×2케이스 원시 시간·화면 전환·교차 순서 기록
  - C2: 중앙값 감소율과 한계 공개, 예시 숫자를 실측으로 사용하지 않음

## 4 시연·제출

- [ ] **F01 기능 동결·핵심 결함 정리** — pc1 · TODO · 30분
  선행: Q03 / 산출물: reports/freeze.md
  - C1: 핵심 경로 차단 결함 0건, 제외 범위·알려진 한계 기록
  - C2: 동결 SHA와 이후 변경 허용 조건 기록

- [ ] **D01 시연 대본·백업 녹화** — pc2 · TODO · 60분
  선행: F01 / 산출물: demo/script.md, assets/presentation-manifest.json
  - C1: 공식 발표 시간에 맞춘 문제·두 흐름·실측·한계 대본
  - C2: 백업 녹화 재생·SHA·다운로드 경로 확인

- [ ] **D02 3회 연속 리허설·장애 시연** — pc1 · TODO · 60분
  선행: D01 / 산출물: reports/rehearsal.md
  - C1: 동일 빌드 두 시나리오×3회=6/6 완주
  - C2: 초기화 절차·시각·담당자·오프라인 1회 성공 기록

- [ ] **D03 제출 묶음 최종 확인** — pc1 · TODO · 30분
  선행: D02 / 산출물: reports/release-check.md
  - C1: 코드·설계·평가·대본·백업·실행 방법을 제출 조건에 대조
  - C2: 다른 PC에서 릴리스 재현, 필요한 접근 권한 확인

## 5 선택 확장 P1

- [ ] **A01 실제 모델·STT 공급자 연결 평가** — pc4 · TODO · 90분
  선행: F01 / 산출물: reports/live-ai.md
  - C1: 허용된 API 권한·예산 내 실제 호출과 모드 표시
  - C2: 동일 20입력 평가와 timeout·오류·fallback 확인

- [ ] **H01 Vercel 로그인·g-23 연결** — pc1 · TODO · 30분
  선행: F01 / 산출물: reports/vercel-link.md
  - C1: whoami 계정과 실제 team/project 권한 확인
  - C2: 제품 앱 폴더의 기존 g-23 연결, 키 없이 설정 근거 기록

- [ ] **H02 Vercel Preview 배포·브라우저 확인** — pc1 · TODO · 60분
  선행: H01 / 산출물: reports/vercel-preview.md
  - C1: Root Directory·빌드·인증·자산 공개 범위와 BE 필요 여부 확인
  - C2: Preview URL에서 JS·데이터·영상·두 흐름·오류 모드 확인
