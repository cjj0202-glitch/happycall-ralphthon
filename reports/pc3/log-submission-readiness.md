# N03-L1 — PC3 현재 작업 로그의 로컬 보존·제출 준비 메타데이터

2026-09-22 KST. 현재 해피콜 지원 대화의 실제 세션 1개를 확인하고, **시작 길이 70,877,292바이트의 원본 접두사**를 새 로컬 snapshot으로 보존했다. 원본 접두사와 snapshot의 SHA256은 일치하며 JSON 객체 **10,899행**, 불량·빈 행·잘린 tail은 각각 **0**이다. 원본 로그·snapshot의 외부 전송은 **0회**다. snapshot은 **NOT-APPROVED**이며 비밀정보 검토나 제출 승인을 뜻하지 않는다.

구조상 시작 251건 중 명시적 완료와 대응하는 턴은 **250건**, 진행 중인 턴은 **1건**이다. 이 숫자는 성공한 제품 작업 수나 연속 생산 시간·공식 HowLong 결과가 아니다. 현재 지원한 호출 형태에서 실제 Goal 호출을 찾지 못했으며 pc1의 Goal을 복제하거나 이 파일을 Goal 포함 주요 로그로 인증하지 않았다.

## 신원·범위·선택 근거

- 배정: [pc1 N03-L1](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/9#issuecomment-5765078031).
- ACK: [PC3 착수 확인](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/9#issuecomment-5765130813), 03:01:07 KST.
- 첫 실측 회신: [고정 snapshot·구조 결과](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/9#issuecomment-5765219738), 03:07:56 KST, ACK 후 6분 49초.
- 실제 신원: `LAPTOP-U2AL73UH / mcjun86-oss / pc3`, 역할 logistics-review.
- 실제 루트 `D:\hwana\Work\happycall-ralphthon`, 키트 `D:\hwana\Work\hackathon-ai-kit`.
- branch `work/pc3-n03-wms-scenes`, 시작 HEAD `b9e8b706d61a4052dcfcb8c4e1ceb56781403fdb`, tracked clean에서 시작했다.
- 고정 기준 `17350d9ec547fae828e68156b642fc0a615c9b2e`의 docs/09, docs/10, `planning/submission-log-refresh.md`, `scripts/log_inventory.py`를 읽었다. main pull/merge나 공통 파일 교체는 하지 않았다.
- tracked 쓰기는 이 보고서 1개뿐이다. 나머지는 새 Git 제외 `.local/pc3-l1-20260922-0259`에 보존했다.

런타임 `CODEX_THREAD_ID`와 정확히 일치하는 파일명을 찾아 **1개만** 선택했다. 그 파일의 첫 `session_meta` ID가 런타임 ID와 일치하며 cwd도 현재 대화의 작업 폴더와 일치함을 확인했다. 다른 세션 본문·다른 PC 로그는 열지 않았다. 원본은 기존 Codex 관리 경로 `C:\Users\hwana\.codex\sessions\2026\09\21` 아래에 유지했다. 정확한 파일명·ID·경로는 비공개 `selection.json`에 보존하고, 새 대용량 사본은 D: 저장소 아래에 만들었다.

현재 대화의 고정 snapshot 안에서 실제 구조의 도구 호출 입력에 해피콜 저장소 표기가 있는 기록 801건, PC3 미디어 스크립트 표기 186건을 관측했다. 이들은 서로 겹칠 수 있는 선택 보조 근거이며 독립 작업 수·성공 건수가 아니다. 이 세션에는 준비 작업·실패 수정·수신 검증·watcher heartbeat도 포함된다. 내용을 잘라 시간을 유리하게 만들거나 pc1 로그를 대신 넣지 않았다.

## 보존 실측

| 항목 | 실측 |
| --- | --- |
| 고정 복사 시작–종료 | 2026-09-22 03:03:08.909–03:03:11.100 KST |
| 시작 시 원본 길이 / snapshot 길이 | 각각 70,877,292 B |
| 복사 직후 원본 길이 | 70,877,292 B |
| 복사 중 관측된 시작 길이 밖 append | 0 B |
| 원본 고정 접두사 SHA256 = snapshot SHA256 | `d4fe148f17af34561dd4774407f0aa32112112dc85da91dd1a66368a61938f16` |
| JSON 객체 / 전체 물리 행 | 10,899 / 10,899 |
| 불량 JSON / 비객체 JSON / 빈 행 | 0 / 0 / 0 |
| 끝의 미완성 행·tail bytes | 0행 / 0 B |
| 고정 접두사 내부에서 누락·제거한 tail | 0 B |
| 첫 사건 시각 | 2026-09-21 14:50:10.861 KST (`2026-09-21T05:50:10.861Z`) |
| 끝 사건 시각 | 2026-09-22 03:03:07.647 KST (`2026-09-21T18:03:07.647Z`) |
| 시각이 있는 객체 / 잘못된 시각 / 역행 | 10,899 / 0 / 0 |

이 시각은 파일 순서의 첫·끝 유효 사건 시각이며 그 차이를 실행 시간이나 최장 완료 턴으로 계산하지 않았다. 시작 길이 이후의 후속 활동은 이 snapshot에 포함하지 않는다. 활성 원본이 나중에 정상적으로 append되는 것과 고정 접두사의 변경을 구분한다.

원본 및 경로의 symlink/reparse 여부와 단일 링크 regular file을 검사했다. 원본은 `rb`로만 열고 처음 열린 파일의 device/inode와 종료 시 경로·핸들을 대조했다. 사본은 `xb`로 새로 생성해 fsync한 뒤, 같은 길이의 원본 접두사를 다시 읽은 SHA와 사본 전체 SHA를 대조했다. 원본 쓰기 0회, 기존 사본 덮어쓰기 0회이며 원본 접두사가 보존되었다. 합성 기존 파일에 `xb`로 쓰려는 시도가 거절되고 바이트가 보존됨도 확인했다.

03:11:57 KST의 최종 읽기 전용 재대조에서도 snapshot 전체와 원본 첫 70,877,292바이트의 SHA가 동일했다(exit 0). 당시 원본은 71,159,733바이트로 282,441바이트가 정상 추가되었으며, 이 추가 부분은 고정 사본에 포함하지 않았다. 원본 파일 identity와 snapshot 길이도 유지되었다(`final-preservation.json`).

기존 `.local/log-manifest.json`은 시작 시 없었고 기존 CLI를 실행하거나 그 파일을 생성하지 않았다. 다른 기존 snapshot 전체의 내용을 일괄 열어 감사한 것은 아니다. 이번 도구는 지정한 원본의 읽기와 새 감사 폴더의 독점 생성만 수행했으며, 기존 사본 불변 주장을 다른 파일 전체의 해시 검사로 확대하지 않는다.

## 파일 크기 대조

기준 커밋에 보존된 docs/09의 제한과 비교했다. 공식 사이트 재확인·로그 입력·등록은 수행하지 않았다.

| 대조 | 한도 | 실측 | 이 파일 판정 |
| --- | ---: | ---: | --- |
| 공식 제출, 파일당 | 1,073,741,824 B (1 GiB) | 70,877,292 B (67.593853 MiB) | 크기 이내, 여유 1,002,864,532 B |
| HowLong, 파일당 | 268,435,456 B (256 MiB) | 70,877,292 B | 크기 이내, 여유 197,558,164 B |

팀 합계 10 GiB, HowLong 전체 512 MiB·100파일, 다른 PC 로그와의 중복·포크 겹침은 **미검증**이다. 한 파일의 크기 통과를 팀 전체 통과나 공식 수용으로 바꾸지 않는다.

## 호출·결과·완료 구조

03:07:22 KST에 고정 사본을 streaming 분석했다. duplicate key, nonfinite number, invalid UTF-8도 불량으로 분리하며 16 MiB보다 긴 행은 파싱하지 않고 별도 불량으로 표시한다. 이 사본에서 해당 불량·초과 행은 각각 0이었다. 인자·출력 본문·ID·알 수 없는 필드값은 결과로 반환하지 않는다.

| 구조 | 실측과 의미 |
| --- | --- |
| `event_msg.task_started` | 251 |
| `event_msg.task_complete` | 250, 시작과 `turn_id`로 대응하는 완료 250 |
| abort / 고아 완료 / 중복 시작 / ID 누락 | 각각 0 |
| 시작했지만 명시적 완료가 없는 턴 | **1** — 현재 진행 턴, 완료로 세지 않음 |
| function call / 대응 output | 222 / 222 |
| custom tool call / 대응 output | 840 / 839 |
| 도구 호출 합계 / 대응 결과 합계 | 1,062 / 1,061 |
| 결과가 아직 없는 호출 | **1** — snapshot 경계의 진행 호출 |
| 고아 output / output 종류 불일치 / 중복 call ID | 각각 0 |

`call_id`와 호출/결과 종류가 일치하는 쌍만 대응 결과로 셌다. 도구 결과가 존재한다는 사실은 exit 성공·제품 검증 통과를 뜻하지 않는다. assistant final 문구만으로 턴을 완료하지 않았다. snapshot 생성 자체의 실행 결과도 그 snapshot 뒤에 기록되므로 이후 활동을 소급 합성하지 않는다.

분석한 top-level 형식은 session_meta 1, response_item 3,977, turn_context 264, event_msg 5,027이다. 그 외 top-level 객체 **1,630**은 JSON 문법·시각만 검사하고 의미는 해석하지 않았다. response_item 중 직접 호출/결과 이외 **1,854**, event_msg 중 시작/완료/abort 이외 **4,526**도 완료 판정에 쓰지 않았다. 이 수들은 중첩 분모이므로 서로 합산하지 않는다.

인식한 직접 `create_goal/get_goal/update_goal` 호출은 각각 **0**이다. 실행 wrapper 입력의 명시적인 `tools.create_goal(`/`get_goal(`/`update_goal(` 후보도 각각 0이다. 이는 지원한 형태에서 Goal 증거를 찾지 못했다는 뜻이다. 해석하지 않은 별칭·다른 형식까지 전수 증명한 것은 아니며, pc1 Goal을 복제하지 않고 이 파일의 Goal 포함 주요 로그 적격성은 **미확인**으로 유지한다. 토큰 누적값을 합산하거나 점수·비용·최장 시간으로 환산하지 않았다.

## 검사기 대조·재현

기준 `scripts/log_inventory.py`의 `inspect` 함수만 고정 사본에 적용했다. 기존 `main()`/CLI는 `.local/log-manifest.json`을 덮어쓸 수 있어 실행하지 않았다. `inspect.json_lines`는 비공백 행 수이므로, 별도 strict parser의 실제 객체 행 수와 대조해 10,899행 일치를 확인했다.

- 고정 inspect의 합성 정상 파일 1개: 객체 1 / 불량 0. 합성 불량 파일 1개: 비공백 행 1 / 불량 1. **2/2 PASS**, 실제 exit 0.
- 합성 기존 파일의 독점 생성 거절·바이트 보존: **1/1 PASS**. 실제 원본을 쓰기 모드로 열어 검사한 것이 아니다.
- 같은 PC3 보조 에이전트는 실제 세션·selection 경로를 열지 않고 구조 검사기를 합성 입력으로 검토했다. 최초 **80/81 PASS**, 실패 1건은 숫자 `8`이 들어간 고정 출력 키를 테스트 정규식이 잘못 거절한 검증 하네스 오류였다. 최초 결과를 보존하고 소스 변경 없이 관련 출력 검사만 **4/4 재검 PASS**했다. 최초 전체 실행을 81/81로 다시 쓴 것이 아니다.
- 합성 정상 구조는 시작 3 / 완료 1 / abort 1 → 완료 쌍 1 / 중단 쌍 1 / 진행 1을 유지했고, assistant final이 있어도 진행 턴을 완료하지 않았다. 합성 잘린 마지막 행은 불량 및 tail로 남겼다.
- 고정 실제 사본 함수 분석: exit **0**, 객체 10,899 / 진행 턴 1 / 진행 호출 1. 아래 CLI도 03:08:54 KST에 실제 실행해 exit **0**, 숫자 필드 55개가 함수 결과와 일치하고 stderr 0 B임을 확인했다.

로컬 재현은 저장소 루트에서 **이미 고정된 사본**에만 실행한다. 원본을 다시 복사하거나 capture 스크립트를 재실행하지 않는다.

```powershell
python -B .local/pc3-l1-20260922-0259/analyze_structure.py --input .local/pc3-l1-20260922-0259/current-thread-prefix-NOT-APPROVED.jsonl
```

원본 추출의 실제 명령은 `python -B .local/pc3-l1-20260922-0259/capture_prefix.py`였고 exit **0**이었다. snapshot·감사 폴더의 Git ignore를 확인했고 이 폴더의 tracked 파일은 0개다. 다른 PC에서 재현하려고 원본 JSONL을 전달하지 않는다.

| 검사기 | bytes / SHA256 |
| --- | --- |
| 고정 원본 `scripts/log_inventory.py` | 2,543 B / `435b064b4bac2f5c33256b21daf40f7358a1ad0a70bd8e665375cff74ae25f30` |
| 로컬 `analyze_structure.py` | 11,351 B / `2cdc9bef6a3a3f0b893918cad72a6048e8b1826ab4ff974618db697404d4a3a5` |

로컬 증거는 `selection.json`, `capture.json`, `inspect-controls.json`, `structure.json`, `schema-counts.json`, `relevance-goal-counts.json`, `synthetic-results.json`, `synthetic-recheck.json`, `cli-reproduction.json`에 있다. 원본·snapshot·로컬 상세 JSON·검사기·합성 fixture는 GitHub/Release에 올리지 않는다. 공유 대상은 이 메타데이터 보고서 1개다.

## 미달·공유 경계

자격증명·회사자료·자유서술·임베디드 미디어·opaque/encrypted 내용의 안전성은 모두 **미검토**다. 구조 분석이 문자열을 파싱했다는 사실을 비공개 해제나 시크릿 부재 확인으로 해석하지 않는다. 발견값·본문·주변 문맥을 stdout·보고서·이슈로 출력하지 않았다.

본 L1 수행 중 원본/사본 로그 외부 전송, 정제본 생성, ZIP 생성, 외부 HowLong 입력, 공식 제출, 업무용 API·유료 서비스 호출은 각각 **0회**다. 정본 문서 수신 및 승인된 메타데이터 댓글·보고서 공유용 GitHub 통신은 별도로 수행했으며 이를 네트워크 0회라고 주장하지 않는다. 새 서버·브라우저·미디어 실행도 하지 않았다.

이 작업은 PC3 로컬 증거 보존과 준비 상태 보고다. 민감정보 검토·Goal 포함 주요 로그 선정·팀 중복/총량·HowLong 분석·공식 수용/제출은 별도 미완료이며, pc1 인수 전 중앙 완료 표시나 #9 종결은 하지 않는다.
