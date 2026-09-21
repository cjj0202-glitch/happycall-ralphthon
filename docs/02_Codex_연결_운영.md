# Codex 연결과 감시기의 범위

Codex도 스킬을 지원한다. 이 저장소의 `.agents/skills/mailbox`와 `.agents/skills/ralph-loop`는
Claude의 원본 스킬을 참조한다. 다른 PC도 변경된 저장소를 받으면 저장소 스킬을 발견할 수 있다.
사용자 전역 링크는 이 PC에만 설정된다. 원본 규약은 `AGENTS.md`와 `channel/00_채널규약.md`다.
[공식 스킬 문서](https://learn.chatgpt.com/docs/build-skills).

## 시작

저장소에서 `python channel/whoami.py`로 신원을 확인한다. 미등록 PC는 hostname·GitHub 계정을
메인에게 알려 등록받는다. 슬롯을 임의로 선택하지 않는다. 서로 다른 ChatGPT 계정도 각자의
GitHub 권한으로 같은 저장소를 읽고 쓸 수 있다. 계정 로그인이나 대화 기록을 공유할 필요는 없다.

```powershell
python channel/mail.py watch --interval 30 --bell
```

감시 대상은 `to:<내슬롯>`과 `from:<내슬롯>`이다. 메인이 pc2에 보낸 이슈의 회신·종결도 감지한다.
상태가 동일한 조회는 출력하지 않는다. 시작·오류·종료 안내는 별도다. 최초 실행 시 기존 열린
편지가 새 편지로 표시될 수 있으며, 이는 GitHub 생성 시각이 새롭다는 뜻이 아니다.

**감시기는 조회와 로컬 상태 기록만 한다.** 이슈 생성·회신·종결, 워커 실행, Codex 대화 재개를
하지 않는다. 터미널 벨은 에이전트 입력이 아니다. 사람이 알림 후 재개하거나, 사용자가 요청한
Codex 자동화에서 읽기 검사를 하고 승인된 범위의 작업을 이어간다. 자동화를 설정하지 않은
상태에서 ‘계정 간 자율 대화가 가동 중’이라고 보고하지 않는다.

## 조회량과 오류

기본 루프는 수신·발신 목록 2번을 조회한다. 30초 간격 4대면 시간당 약 **960번의 목록 호출**이다.
실제 요청 수·GraphQL 포인트는 페이지 수와 댓글 수에 따라 달라진다. `gh issue list`의 GraphQL
사용량을 REST 5,000 요청 한도와 그대로 비교하지 않는다. `gh api rate_limit`로 두 자원을 확인한다.

개별 명령은 45초 제한, 연속 오류 재시도 간격은 최대 300초다. `--max-loops`는 실패한 조회도 센다.
한 라벨이 1,000건에 도달하면 불완전한 목록을 정상으로 처리하지 않고 오류를 낸다.
목록에서 사라진 것만으로 닫힘을 추정하지 않으며 실제 `CLOSED` 전환을 알린다.

## 점검

```powershell
python -m unittest discover -s tests -v
python channel/mail.py watch --interval 3 --max-loops 3
```

테스트는 가짜 GitHub 응답으로 새 회신, 종결, 무변화, 네트워크 실패를 확인하며 외부 편지를 쓰지 않는다.
실제 조회 검사는 각 PC에서 따로 수행한다. 다른 계정·노트북 3대는 실제 등록과 왕복 검증 전까지
검증 완료로 세지 않는다.
