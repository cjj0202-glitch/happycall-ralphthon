# 테스트 임시 폴더 삭제 정책 거부

2026-09-21 pc1/CJJ. 아래 경로는 이 검사에서 만든 임시 정적 사본과 합성 상담 저장소입니다.

- `C:/Users/choi8/AppData/Local/Temp/oneflow-rehearsal-h78cenes`, 최초 서버 PID 1764.
- `C:/Users/choi8/AppData/Local/Temp/oneflow-rehearsal-juzfagvr`, 재검증 서버 PID 4868.

삭제 전에 Resolve-Path로 두 절대경로가 지정된 사용자 Temp 바로 아래의 `oneflow-rehearsal-*`임을 확인했고 두 PID 모두 존재하지 않음을 읽기 확인했습니다. 기존 3100/8100 서비스의 종료/재시작과 무관한 테스트 정리였습니다.

`exec_command`에서 PowerShell `Remove-Item -LiteralPath <검증한 경로> -Recurse -Force` 실행을 요청했으나 자동 승인 검토가 `rejected: blocked by policy`를 반환했습니다. 추가 사유는 제공되지 않았습니다. 명령은 실행되지 않았으며 다른 도구/스크립트/에이전트로 우회하지 않았습니다. 두 디렉터리는 보존 상태입니다.
