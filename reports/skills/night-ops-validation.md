# 야간 운영 스킬 검증

2026-09-21 18:37 KST, pc1 작업 폴더에서 수행했습니다. 사용자가 요청한 9/22 09시까지의 반복 작업을 [happycall-night-ops 정본](../../.claude/skills/happycall-night-ops/SKILL.md)으로 만들었습니다. **형식 3/3, 로컬 링크 17/17, 독립 모의행동 6/6에서 대상 경계가 유지됐습니다.** 실제 원격 작업·예약 실행·제품 완주를 검증한 결과는 아닙니다.

## 산출물과 적용 범위

| 파일 | 역할 | 검증 시 SHA256 |
|---|---|---|
| `.claude/skills/happycall-night-ops/SKILL.md` | 공유 정본, 54행 | `6d9d8752ee2794636e826bca978d872f8f9919f5d23ef6e886268cc316182dca` |
| `.agents/skills/happycall-night-ops/SKILL.md` | 상대경로로 정본을 읽는 저장소 진입점, 10행 | `ce421680bce0d01d7eaca00bb88dd4bf1f573856dccdb97ac16fc2b101c9e631` |
| `C:/Users/choi8/.codex/skills/happycall-night-ops/SKILL.md` | 기존 파일 부재 확인 후 생성한 pc1 발견용 연결, 8행·Git 밖 | `3151b381fa4b46b55ccc51277526bd985b2bd4a39a85ec7739f183b9ef381721` |

정본은 신원·실제 Goal·기한 확인 → 기존 #8~#10 회신 → 소유 작업 한 덩어리 → 설계·실행·독립 검증 → 명시 경로 커밋·원격 SHA → 메인 인수를 연결합니다. 기존 45개 작업표와 N01~N04 인수는 구분합니다. 기존 mailbox·Ralph·docs24/25/27을 연결하고 명령 실행기를 새로 만들지 않았습니다.

AGENTS·PROMPT_team·자동화·Git·계정은 이 스킬 제작 작업에서 변경하지 않았습니다. 메인이 정본 연결·기존 heartbeat 프롬프트 반영·커밋을 수행할 수 있도록 전달합니다. 스킬 설치만으로 실행 중 대화의 목록 갱신이나 다른 PC의 자동 실행이 완료됐다고 하지 않습니다.

## 형식·링크 검사

저장소 루트에서 다음 세 명령을 실행했고 각각 종료 코드 0과 `Skill is valid!`를 반환했습니다.

```powershell
.venv/Scripts/python.exe -X utf8 C:/Users/choi8/.codex/skills/.system/skill-creator/scripts/quick_validate.py .claude/skills/happycall-night-ops
.venv/Scripts/python.exe -X utf8 C:/Users/choi8/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/happycall-night-ops
.venv/Scripts/python.exe -X utf8 C:/Users/choi8/.codex/skills/.system/skill-creator/scripts/quick_validate.py C:/Users/choi8/.codex/skills/happycall-night-ops
```

`quick_validate`는 frontmatter·이름·미완성 틀 검사이며 행동 검증은 아래 독립 검토로 분리했습니다. 메모리에서만 이름을 `Invalid_Skill`로 바꿔 `Path.read_text`를 mock한 음성 대조군은 `False / Name 'Invalid_Skill' should be hyphen-case`로 거부됐습니다. 실제 파일은 바꾸지 않았습니다.

3개 파일의 Markdown 링크 중 HTTP(S)를 제외한 17개를 각 파일 위치 기준으로 해석하여 **존재 17, 누락 0**을 확인했습니다. 두 저장소 파일에는 pc1 절대경로가 없고 둘 다 세 단계 위의 같은 checkout 루트를 가리킵니다. 재현할 핵심은 다음과 같습니다.

```python
links = re.findall(r'\]\(([^)]+)\)', skill_path.read_text(encoding='utf-8'))
local_links = [s for s in links if not s.startswith(('https://', 'http://'))]
assert all((skill_path.parent / s).resolve().is_file() for s in local_links)
```

검사 중 최초 Windows 경로 정규식이 `https://`의 `s:/`를 드라이브 경로로 오탐해 실패했습니다. 대상 문서를 고치지 않고 검사식을 `(?<![A-Za-z0-9])[A-Za-z]:[/\\](?![/\\])[^\s)]+`로 좁혔습니다. `C:/actual/pc1` 양성·HTTPS 음성 대조군을 먼저 실행한 뒤 재검사한 결과 pc1 절대경로 0개였습니다. 외부 이슈 3개 링크의 실시간 상태는 이 작업에서 조회하지 않았습니다.

추가 보고서 링크 검사에서는 인라인 정규식을 링크로 읽는 오탐이 나와 코드 블록·인라인 코드를 제외하고 재검했습니다. 스킬 3파일의 링크 수는 각각 15/1/1, 이 보고서 링크는 1개이며 전부 존재합니다. 최종 스킬 SHA도 독립 검토 시점과 3/3 동일합니다.

## 독립 전방 행동 검토

별도 에이전트 `night_ops_forward_test`에 스킬 경로와 아래 합성 상태만 주고 다음 행동·금지 행동·보고 범위를 판단하게 했습니다. 작성자의 의도한 답이나 추론을 넘기지 않았고 실제 Git·편지·Goal·예약·API·파일 변경 및 네트워크 호출을 금지했습니다. 검토자는 스킬과 필요한 로컬 정본만 읽었습니다.

| 입력 상태 | 검토자가 선택한 행동 | 완료 주장 경계 |
|---|---|---|
| pc1 20:10, #8~#10 댓글 0, watcher 무출력, N01 단위 15 PASS | 첫 세션 편지 대조 후 N01 다음 소유 기능/화면 검사, 중복 발송·불필요 반복 검사 없음 | 단위 15 PASS와 원격 ACK 미확인만 보고 |
| pc3 N03 자체 5 PASS·branch push, 다른 작업자의 page 수정 | #9에 SHA·증거 회신, 소유 경로만 검증 | 메인 인수·main 통합·이슈 종결하지 않음 |
| pc1 READY/URL, API503, Blob403, 재시작 정책거부, 원장 예약 $17, 음성 후보 2개 | 원인·target 확인과 독립 replay/mock, 차단 동작과 과금 자동 반복 없음 | URL 발급과 전체 흐름 미달을 구분 |
| pc1 09:01, heartbeat/Goal ACTIVE, N03 미인수, Preview만 검증 | 새 구현·배정·과금 중단, 실측 인계, 기존 heartbeat PAUSED | 미달 Goal complete 없음·미인수 보존 |
| hostname 미등록, 계정만 pc2 일치 | 제품/편지 중단·실제 신원 보고, 읽기 전용 준비만 가능 | 계정만으로 슬롯을 추정하지 않음 |
| pc1 N02 결과·독립검사 증거, 기존 tasks.json에는 N02 없음 | UI/기능/반례 포함 여부 대조 후 야간 원장·#8로 인수 | `ops/tasks.py accept N02`를 만들지 않음 |

검토자는 이 6개 상태 범위에서 지시 충돌 때문에 위험하거나 막히는 행동을 찾지 못했습니다. N02의 독립검사가 실제 UI/기능·반례까지 포함하지 않았다면 해당 누락만 보완해야 한다고 조건을 남겼습니다. 검토 결과에 따른 스킬 수정은 없으며 위 SHA와 같은 파일을 평가했습니다.

## 남은 한계

- 정적 형식·링크 및 모의 판단 검증입니다. 밤새 실행·자동 재개·실제 PC별 설치/ACK·원격 인수 성공은 아직 이 검사로 입증되지 않았습니다.
- 실제 사용 첫 주기에서 확인한 불일치만 좁게 수정합니다. 메인이 기존 예약 설정과 현재 Goal·배포 상태를 확인해야 합니다.
- 09시 제한은 지시문과 기존 예약 중지 절차입니다. 앱·전원·네트워크가 중단된 동안 정확한 시각에 실행된다는 보장은 없습니다.

## 메인 연결과 첫 실제 적용 · 18:39 KST 이후

메인이 정본을 직접 읽고 quick_validate를 다시 실행해 `Skill is valid!`를 확인했습니다. AGENTS.md·PROMPT_team.md에 공유 진입점을 연결했고, 기존 heartbeat `automation`을 새로 만들지 않고 **ACTIVE / 30분**으로 유지하면서 스킬을 먼저 읽도록 프롬프트를 갱신했습니다. 도구가 업데이트 성공을 반환했습니다.

첫 적용에서는 실제 Goal active, 작업표45개 check PASS, 30초 watcher의 새 댓글 감지를 확인했습니다. 이어 실제 GitHub 댓글 작성자·수신처를 대조해 #8 MR-A83/pc2와 #9 mcjun86-oss/pc3의 착수 보고, #10 j324rst-svg/pc4의 수신·감시 복구 보고를 구분했습니다. pc4가 제품 미착수를 명시했으므로 착수로 올리지 않았습니다. 워커 결과 인수·제품 완주·예약에 의한 첫 자동 재개는 이 관측에 포함되지 않습니다.
