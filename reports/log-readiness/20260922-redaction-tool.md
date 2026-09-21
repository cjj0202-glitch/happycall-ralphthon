# 로컬 제출 후보 정제 도구 검증

2026-09-22 · pc1/CJJ의 로컬 보조 작업 · 기준 HEAD `1a6a9e2` · 커밋/업로드 없음.

`scripts/prepare_submission_log.py`와 `tests/test_submission_log.py`를 구현했습니다. 고정 UTF-8 JSONL snapshot에서 새 **NOT-APPROVED** 후보와 해시 감사기록을 만듭니다. 이 보고서는 합성 데이터 검증이며 실제 최신 로그 정제·독립 대조·공식 제출의 완료 증거가 아닙니다.

## 실행 계약

```powershell
python scripts/prepare_submission_log.py --input <fixed-snapshot.jsonl> --output-dir <repo/.local/new-directory> --policy <local-policy.json>
python -m unittest discover -s tests -p test_submission_log.py -v
```

`--input`과 `--output-dir`는 필수이고 `--policy`는 선택입니다. 출력은 저장소 `.local` 아래 기존에 없는 디렉터리여야 하며 부모 디렉터리는 이미 있어야 합니다. 기존 출력·원본은 덮어쓰지 않습니다. 모든 경로 구성요소의 symlink/Windows reparse point, 입력 hardlink, 비정규 파일을 거부합니다. 입력의 처음/끝 identity·크기·mtime과 두 번 읽은 전체 SHA256을 비교합니다.

정책 JSON은 `redact_leaf_sha256` 목록과 선택적인 `redact_store_code_sha256` 목록만 받습니다. 각 원소는 **JSON escape를 해석한 원문 문자열의 UTF-8 SHA256**입니다. 임의 정규식은 받지 않습니다.

- 원문 leaf 해시 일치는 문자열 전체를 `[REDACTED:CORPORATE_SOURCE]`로 바꿉니다.
- storeCode는 기존 literal 문법 `(["']?storeCode["']?\s*[:=]\s*["'])([^"'\r\n]{1,200})(["'])`에 대소문자 무시로 일치하며, 값 부분의 해시까지 등록된 경우에만 그 부분을 `[REDACTED_LEGACY_STORE_ID]`로 바꿉니다. 문법 밖 구조화 필드 및 미등록 값은 이 정책으로 추측 정제하지 않습니다.
- 일반 문자열에서 OpenAI/GitHub/AWS 형식, URL 자격증명·Bearer·유효한 Base64 Basic 인증·JWT, 이메일·국내 휴대폰 후보, inline data URL을 종류별 표식으로 바꿉니다. 순수 Base64는 media 유형 문맥의 `data/base64/b64_json/payload/image/audio/video/url` 필드에서 정제하며 일반 alt/caption은 이 문맥 규칙에서 제외합니다. 추가로 **문자열 전체가 유효한 순수 Base64이고 디코딩된 시작 8바이트가 PNG 서명과 일치하면** type/필드명과 무관하게 `EMBEDDED_MEDIA`로 정제합니다. PNG 이외 형식의 서명이나 일반 영문·Base64 설명은 추정하지 않습니다. 자격증명·이메일 경계는 ASCII 문자집합을 사용해 한글에 인접한 값을 놓치지 않습니다. 형태 일치는 실제 계정 소유 여부를 검증한 뜻이 아닙니다.

출력 파일은 `candidate.NOT-APPROVED.jsonl`, `changes.NOT-APPROVED.jsonl`, `manifest.NOT-APPROVED.json`입니다. 완성 전에는 `.partial`로 쓰고 manifest를 마지막에 게시합니다. 오류 때 partial은 남을 수 있으나 완료 manifest는 만들지 않습니다. JSON 불량·빈 입력·빈 행·비객체·중복 key·비유한 숫자·BOM·불완전 마지막 행은 실패합니다. 줄바꿈 없는 완전한 마지막 객체는 허용합니다.

감사기록은 1-based 행·JSONPath·종류·전후 leaf/key SHA256·UTF-8 바이트 길이만 남깁니다. 여러 종류가 있는 한 leaf는 종류별 한 행입니다. 비표준/민감한 객체 키의 경로 구성요소는 `[key-sha256=...]`로 표시하여 원문을 쓰지 않습니다. 의심 객체 키는 원문을 보존하며 `UNRESOLVED_KEY:<종류>` 감사와 `unresolved_key_count`로 집계합니다. manifest는 전체 파일 해시·길이·종류별 leaf 수·미해결 수·미검토 상태를 담습니다. 성공 stdout은 상태·건수·전체 해시, 실패 stderr는 상수 오류코드만 출력합니다.

## 기록 보존과 미해결

사건 순서·수, 객체 키 순서·키 부재, 배열 원소 순서·수, 값 유형, 불리언·null, **숫자의 원문 표기**를 유지합니다. Python float 변환을 하지 않아 큰 정수·고정밀 소수·`-0`·`1e999`도 그대로 직렬화합니다. 각 사건을 변환 후 구조 보존 가드로 대조합니다.

timestamp/time/date/datetime, id/ids 및 `_id`/`_ids`/`_timestamp`, type/role/name/model/effort/reasoning_effort, created_at/updated_at/started_at/completed_at/finished_at, duration_ms/status/namespace/comp_hash/sender/recipient 계열은 보호합니다. camelCase/PascalCase 식별자는 `(?:Id|Ids)$|(?:^|[a-z0-9_])(?:ID|IDs)$` 경계도 보호합니다. `threadId/responseId/callId/nestedID/ResponseID/APIId/threadIds/callIDs`와 배열 원소는 보존하지만 `grid/valid/solid/fluid/Grid/GRID/VALID` 같은 일반 단어를 lowercase `id` 접미사만으로 보호하지 않습니다. 보호 문자열에 알려진 패턴/정책 해시가 있으면 원문을 유지하고 `UNRESOLVED_PROTECTED`로 집계합니다. 없는 ID/필드는 생성하지 않습니다. `encrypted_content`는 검사·치환하지 않고 `OPAQUE_UNREVIEWED` 수로 남깁니다. 오류의 구조·유형·상태는 보호하며 자유문자열 오류 message는 일반 정제 대상입니다.

한 사건씩 streaming 처리하며 메모리 상한은 가장 큰 사건 크기에 좌우됩니다. 큰 data URL을 먼저 분리해 다른 자격증명 정규식이 payload를 재검사하지 않습니다. 전체 파일을 메모리에 읽지 않습니다.

## 합성 검증 결과

명령은 위 `unittest discover`이며 최종 **24 tests: 23 통과, 1 skipped**, 0.403초였습니다. 원본 로그·실제 키·기존 비공개 후보·원장은 열지 않았고 합성 fixture만 사용했습니다.

| 검증 축 | 관측 |
|---|---|
| 양성 | 11종 자격증명/연락처/media 표식과 감사 해시·길이·출력 전체 해시 일치 |
| 음성 | 일반 한글 문장, 짧은 키 비슷한 문구, 잘못된 Basic/일반 URL 등 유지 |
| 구조 경계 | 고정밀/매우 큰·작은 숫자, null/boolean, CRLF, 마지막 완전행, 사건 순서 유지 |
| 실패 경계 | 빈 입력/빈 행/비객체/중복 key/비유한 숫자/BOM/손상 UTF-8/서로게이트/불완전 JSON에서 완료 manifest 없음 |
| 정책 | 전체 leaf 해시와 storeCode 네 인용 형식·중복·미등록·보호 필드 대조 |
| 미디어 | 3 MiB inline Base64와 짧은 image/audio payload 정제; 일반 text 및 image alt/caption의 Base64 유사문자열 유지 |
| 문맥 없는 PNG | 합성 1×1 PNG를 `$.payload.item.result`에서 표식 치환; 같은 원문의 보호 id는 미해결 보존, encrypted_content는 opaque 보존; stdout/manifest/감사파일에 payload 없음 |
| PNG 음성/경계 | 일반 영문·Base64 설명·짧은 `test`·한 글자 틀린 signature·잘린/불법문자 Base64·설명과 함께 있는 문자열 보존 |
| ID 명명 경계 | camel/Pascal ID 필드·Ids/IDs 배열의 의심 문자열 13개는 원문 보존+미해결 집계, opaque 1개 보존. 일반 단어 7개 key의 자격증명 값은 정상 정제 |
| 한글 인접 | OpenAI/GitHub/email/Bearer/Basic/JWT/AWS secret/URL 자격증명/AWS access 9종 × 앞/뒤/양쪽/공백 4조건 = 종단 CLI 36조합에서 토큰 제거·한글 문맥 유지 |
| 원본/경로 | 원본 바이트 불변, 기존 출력 sentinel 불변, `.local` 밖 출력 거부, 처리 중 입력 추가 거부 |
| 링크 | 실제 hardlink 차단 및 reparse 속성 양성 대조 통과. Windows symlink 생성 권한 부재로 실제 symlink 1건 skipped |
| 출력 노출 | stdout/stderr/감사파일에 합성 발견값 없음; 민감 객체 키는 해시 경로+미해결 감사, 키 자체는 보존 |

**변이 대조 12/12 killed**: 마스킹 제거, 보호 필드 가드 제거, 기록 구조 가드 제거, 중복 key 거부 제거, media 필드 제한 제거, 의심 key 미해결 가드 제거, OpenAI 앞 경계를 Unicode `\w`로 회귀, 문맥 없는 PNG 분기 제거, PNG signature 가드 제거, PNG 전체 Base64 유효성 가드 제거, camel ID 보호 제거, ID 경계를 lowercase `id` 접미사 전체로 확대. 변이마다 같은 로딩 경로의 비변이 CONTROL을 먼저 통과시켜 위치/의존성 실패와 구분했습니다.

첫 합성 실행에서 대용량 미디어 케이스의 고정 입력 metadata 비교 실패와 opaque probe가 구조 키 검사까지 막은 문제가 발견됐습니다. Windows 생성시각인 ctime 의존을 없애 identity·크기·mtime·두 번의 전체 SHA로 고정성을 확인하고, opaque probe를 해당 leaf 검사 여부로 좁힌 뒤 같은 suite를 재실행했습니다. 후속 storeCode 정책과 추가 보호축도 같은 suite에 포함했습니다.

메인 독립 합성 probe가 추가로 ① image의 일반 alt까지 Base64로 제거하는 과잉 정제와 ② 객체 키에 있는 알려진 토큰을 보존하면서 미해결 수가 0인 누락을 발견했습니다. 두 사례를 먼저 테스트로 고정해 **19 tests, failures=2, skipped=1**을 재현한 뒤 media 데이터 필드 제한과 의심 key 미해결 감사를 추가했습니다. 이어 독립 검토가 발견한 ③ 한글 인접 자격증명 누락도 먼저 **20 tests, failures=1, skipped=1**로 재현했습니다. 전체 자격증명·이메일 패턴의 Unicode `\w`/`\b` 경계를 ASCII 문자집합으로 교체한 뒤 위 36조합과 최종 suite를 통과했습니다. 세 결함 수정 뒤에도 실제 snapshot은 실행하지 않았습니다.

메인은 실제 candidate-v1 내용 대조 후 ④ media type이 없는 자유문자열 PNG Base64 1개 누락을 전달했습니다. 구현자는 해당 실제 파일을 열지 않고 같은 구조의 합성 PNG CLI 테스트를 추가해 **22 tests, failures=1, skipped=1**을 먼저 재현했습니다. decoded PNG signature와 전체 Base64 형식을 함께 확인하는 분기를 추가한 뒤 최종 22개 suite와 10개 변이를 통과했습니다. 보호필드와 암호문을 우회하여 정제하지 않습니다.

후속 독립 합성 검토는 ⑤ `threadId`의 PNG 문자열이 정제되는 ID 보존 누락을 발견했습니다. camel/Pascal 필드·배열과 일반 단어 대조를 추가해 **24 tests, failures=1, skipped=1**을 먼저 재현했습니다. 명시적인 대소문자 경계를 추가한 뒤 **24 tests, failures=0, skipped=1**과 12개 변이를 통과했습니다. 문자열을 모두 lowercase로 만든 뒤 `id`로 끝난다는 이유만으로 일반 텍스트를 보호하는 과잉 확장도 반대 방향 변이로 검출합니다.

별도 합성 줄바꿈 data URL probe는 여전히 **tail_survives=true, description_preserved=true, changed_leaves=1, audit_entries=1**입니다. 즉 현재 단일 행 URI 패턴은 줄바꿈 뒤 Base64를 전부 제거하지 않습니다. 일반 문장을 삼킬 수 있는 포괄 regex는 추가하지 않았습니다. 메인 추가 분류에 따르면 실제 잔존 URI 8개는 내용 없는 audio 헤더, 꼬리 후보 3개는 하이픈 구분선으로 이번 실제 PNG 누락과 별개입니다. 이 분류는 메인의 독립 관측을 인계받은 것이며 구현자의 실제 원문 확인이 아닙니다.

## 남은 범위

v1 실행 전 독립 검토자는 PNG 보완 전 script SHA `e89b3c2bea79efca5b94def111dc044d6f6d4c36607e087ed51bd8e3603064d5`에서 자기 합성 입력으로 11형식×단독/한글왼쪽/한글오른쪽 **33/33** 마스킹·출력/감사 비노출을 확인했습니다. 설명 보존·payload 제거, 민감 key 원문 보존+미해결1, 상태/ID/Goal/boolean/null/암호문 보존도 확인했습니다. 당시 보완3개를 메모리에서 되돌린 변이는 원본PASS/변이FAIL **3/3**이었습니다. 정책/비일치/보호/감사8조건 **8/8**, 실패경계7개 **7/7**에서 exit2·완료manifest0을 관측했습니다. 소스 전후 해시는 같았고 실제 로그·키·네트워크는 읽지 않았습니다. 이 검사는 PNG 보완 후 후보의 독립 검증을 대신하지 않습니다.

메인이 수정된 도구로 실제 고정 snapshot에 재실행하고 독립 비교기로 보존/정제를 대조해야 합니다. 알려진 패턴과 등록 해시의 일치는 자유서술 전체의 공개 허가를 뜻하지 않습니다. 정책 누락은 `NOT_PROVIDED`, 정책 제공은 `HASH_MATCHES_ONLY`, 의미 검토는 `NOT_PERFORMED`로 남깁니다. 줄바꿈 URI의 Base64 꼬리, PNG 외 문맥 없는 미디어, 새 회사정보·이름/주소·모든 연락처 형식·암호문 의미·다른 PC 중복·HowLong 수용·최종 제출은 미해결 범위입니다. PNG 탐지는 signature 확인이며 파일의 모든 chunk/CRC 또는 이미지 렌더 성공을 검증하지 않습니다.
