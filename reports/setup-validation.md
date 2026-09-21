# S01 운영 패키지 검증 기록

측정 환경: pc1/CJJ, 2026-09-21 KST. Python 3.14.3, Node 24.18.0, Git 2.54.0.windows.1, gh 2.94.0. 다른 3대의 결과가 아닙니다.

## 실행한 검사

| 검사 | 명령/경로 | 실제 결과 |
|---|---|---|
| 회귀 검사 | `python -m unittest discover -s tests -v` | 27/27 통과: 감시8·작업표16·로그목록3 |
| 게이트 변이 | ops/tasks.py의 WIP 제거/과도 차단, 선행 완료 제거, REVIEW 제거, 미등록 차단 제거를 메모리 사본에서 각각 실행 | 5/5 변이를 해당 테스트가 검출. 작업 원본은 변경하지 않음 |
| 작업표 | `python ops/tasks.py check` | 38개 의존성·WIP·표 생성 일치 확인. 아래 완료 등록 후 재실행 |
| 스킬 형식 | 시스템 quick_validate.py를 UTF-8 모드로 4폴더 검사 | Claude 원본2 + Codex 어댑터2 모두 통과 |
| 실제 Codex 발견 | app-server skills/list, 루트와 해커톤 cwd 각각 | 공통16+해커톤2 = 18개, 오류0, 두 cwd에서 mailbox/ralph-loop 확인 |
| 감시 실제 조회 | `watch --interval 3 --max-loops 3`, `watch --once` | 3회 정상 종료, 변경 없는 once는 출력0. 이슈 발송·변경 없음 |
| 현재 PC 준비 | `python scripts/preflight.py` | 도구·로그인·두 저장소 접근·pc1 등록·계정 일치·킷 모두 PASS |
| PowerShell | Parser.ParseFile | 문법 오류0. 실제 -File 실행은 시스템 실행 정책으로 차단됨. 정책 변경하지 않음 |
| 문서 연결 | 저장소 상대 링크·코드펜스 검사 | 점검 당시 링크83개, 깨진 링크0, 닫히지 않은 펜스0 |
| 공식 자료 | manifest SHA256 대조 | 25/25 파일 일치 |
| 킷 스모크 | `python scripts/smoke_demo.py` | 6/6: 22테이블2133행, TTS2577KB, STT7구간(오프라인), 영상758KB, HTML56KB, 검사77파일/위반0·자체33검사 |

킷 스모크는 도구가 생성·검사한 범위입니다. 최종 제품 통합이나 브라우저 재생 리허설, live STT/API 성공을 대신하지 않습니다. P01의 직접 재현·관측 작업은 별도로 남겼습니다.

## 운영 규약 대조

- 워커는 증거·커밋을 회신하고 pc1이 REVIEW→검증→accept한 뒤에만 TODO를 체크합니다. AGENTS·두 스킬 원본·프롬프트와 옛 진입 문서를 일치시켰습니다.
- 한 PC의 진행+검증대기는 하나입니다. 미등록 PC는 제품 작업을 시작할 수 없습니다. 시작 시 기존 미처리 확인과 watch 변경 감지를 구분합니다.
- docs/03~12, GOAL, PROMPT 두 개, 사전 준비 스크립트와 38작업을 연결했습니다. 공식 마감·점수·로그·Vercel 방법을 반영했습니다.
- Windows 줄바꿈 차이로 검증 해시가 달라지지 않도록 .gitattributes에 문서/JSON/스크립트 LF와 이미지/PDF binary를 지정하고 작업 증거의 텍스트 해시를 LF 정규화했습니다. 완료 후 수정은 reverify에서 이전 해시와 사유를 보존하며 두 동작을 추가 테스트했습니다.
- 원본 로그·인증 정보는 GitHub에 추가하지 않았습니다. .local·.vercel·JSONL을 제외합니다.

## 한계와 미완료

실제 다른 3대의 설치·로그인·등록, 공식 팀 제출 화면, 제품 구현, Goal 실행, 최종 시연, Vercel 인증/연결/배포는 미완료입니다. 작업표의 TODO로 유지합니다. prepare_windows.ps1은 문법만 검증했으며 현재 PC에서는 정책으로 실행되지 않았습니다. 기본 점검은 검증된 Python 명령을 사용합니다.

판정: **이 PC에서 공유할 운영 패키지 준비 통과**. 4PC 전체 준비나 제품 완료 판정이 아닙니다.
