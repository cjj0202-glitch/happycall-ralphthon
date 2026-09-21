# N02-M5 — 인공 입력 도구 검증 및 첫 인계

2026-09-22 / pc2 안영일 / MR-A83. **도구 준비: 82개 중 81 PASS·1 SKIP·FAIL/ERROR 0. 공식 WAV 0/2·공식 타임라인 0/20 NOT_RUN.** 소스/인공 검사 결과의 검토를 요청하며 실제 음원·N02 전체·TEST를 완료 처리하지 않는다.

## 기준·구현·실행

착수 HEAD `ceec704755c3558be03be72938b6cb369bbb1d3b`, 브랜치 `work/pc2-n02-call-review`. 카드 `535febe1a9cccf351deeab82a8a843b0e891149b:reports/channel/N02-M5-clova-timeline.md`, 대본 기준 `cd262e3425ceaa2710e0d3adc1920a9f87f587c0`. 기존 M4 메인 보정, 공용 파일, frontend, API, manifest/fixture/Release에는 변경이 없다. 결과 커밋 SHA와 원격 확인은 같은 이슈의 전달 댓글에서 확정한다.

실제 checkout은 `C:\Users\Administrator\Desktop\hackerton\happycall-ralphthon`. Python 3.12.14 / Windows 11 / 기존 표준 라이브러리만 사용했다. 착수 가용 메모리는 약 3.50GiB였다. 새 브라우저·서버·소켓·빌드·설치·유료 호출·권한/보안 변경은 0이다. 같은 pc2 보조 작업 한 명이 테스트를 구현하고 다른 한 명이 독립 설계/코드 검토를 수행했으며 총괄이 소스·실행 증거와 별도 실제 CLI 결과를 확인했다.

| 실행 | 실측 | 증거 |
|---|---|---|
| 최종 전체 unittest | 00:32:12~00:33:47 KST / 94.732초 / 82개: 81 PASS, 1 SKIP / exit 0 | `tests-final.txt` 명령·개별 결과·전후 소스 SHA |
| 수정 후 실제 CLI 첫 Bolt | 00:32:46~00:32:51 KST / 정상 exit 0 PASS, 큰 gap exit 2 REJECTED | `first-bolt.json` 실제 명령·출력·입력 전후 SHA |
| 총괄의 최종 소스 문법/CLI | AST 2/2, --help exit 0 | `cli-help.txt`, 실행 로그 |
| 실제 Windows 출력 폴더 rename 반례 수정 후 단독 재검 | 1/1 PASS / 0.908초; 최종 82개 안에서도 PASS | `test_windows_output_rename_during_write_is_blocked` |

검사 명령은 `python -B -m unittest discover -s tests/media_pc2 -p test_clova_timeline.py -v`다. 복사 가능한 인공 생성/실행 명령과 JSON 계약은 [design.md](design.md)에 있다. 원본 대본은 25,175 bytes, SHA256 `47ae253daf158335e92fa136f3e9ba8b3af118fb278b66fcf137e91c3242ade6`로 Git blob에서 원바이트 대조했다.

최종 실행 소스:

| 파일 | 실행 당시 bytes | SHA256 |
|---|---:|---|
| scripts/media_pc2/validate_clova_timeline.py | 25,361 | `577031deb93695eb375c8c49db7cb96eb3588bfc0a346d78469021827233c6a5` |
| tests/media_pc2/test_clova_timeline.py | 32,384 | `4939c444589ff5d048311abe3209a1c0b80eb270c9f804db1f92b5b34c8a24ba` |

전후 소스 SHA는 동일했다. Git 줄바꿈 정규화가 있는 파일은 실행 바이트와 Git blob을 구분해 `source-provenance.json`에 기록한다.

## 첫 Bolt의 사용자 결과

발화가 아닌 작은 인공 PCM16 두 개(8kHz 모노, CASE-0001 8,000프레임/1.0초, CASE-0002 8,800프레임/1.1초)와 인공 관측 20턴을 입력했다. 실제 코드가 전체 WAV를 읽어 원형 크기·SHA 2/2를 전후 보존했고, 고정 대본의 ID·화자·표시/발음 본문·순서 20/20을 유지했다. 20구간의 중간 end와 마지막 EOF가 맞아 `candidate`를 생성했다. `accepted=false`, 공식 검증 분모는 NOT_RUN 상태다. 실제 WAV 길이를 30~40초 제작 목표에 맞춰 바꾸지 않았다.

같은 인공 입력에서 F5-M01의 gap만 0.01→0.20초로 바꾸고 새 기대 관측 파일을 별도로 고정했다. 다음 start=0.1초보다 gap이 커져 `TIME_BOUNDS`로 거절했고 validation.json만 남겼다. 기존 정상 run은 보존했다. 원본 WAV 사본·원관측 파일은 Git에 올리지 않았다. 성공과 실패 후보 파일 목록·오류·전후 입력 해시는 `first-bolt.json`에 있다.

## 발견 결함 → 수정 → 동일 조건 재검

개발 중 실패를 최종 PASS로 덮어 기록하지 않는다. 아래 실패는 당시 소스에 대한 실제 실행/검토이며, 마지막 전체 검사와 구분한다.

| 발견 | 수정 전 실제 관측 | 수정과 재검 |
|---|---|---|
| 소수의 0길이 구간 | start=0.3, next=0.4, gap=0.1인데 float end=0.30000000000000004가 PASS되어 독립 REJECTED 오라클 FAIL 1/1 | Fraction 십진값·정확 EOF 비교. 같은 반례와 최종 suite PASS |
| 깊은 JSON | 1,100단계는 이 Python JSON decoder에서 파싱되어 깊이 자체를 계약 위반으로 보지 않았음. 5,000단계 약10KB는 RecursionError/report 없음 ERROR 1/1 | parser 재귀 예외 처리·100단계 구조 제한. 같은 5,000단계 반례 PASS |
| WAV 매핑 누락 | 안전한 새 output인데 WAV_MAPPING 예외가 보고서 전에 발생, ERROR 1/1 | 매핑 오류를 새 run의 검증 보고서로 반환. 같은 반례 PASS |
| 출력 폴더 교체 | 첫 잠금은 FILE_READ_ATTRIBUTES/share3라 실제 rename가 성공하고 이어 Windows error2/report 없음. 전체 중간 81개는 79 PASS·1 ERROR·1 SKIP | FILE_LIST_DIRECTORY/share1로 수정. 같은 실제 rename 반례 단독 1/1 및 최종 suite PASS, 허용 루트 밖 생성 0 |
| Unicode 오류 보고 | 고립 surrogate source는 정적 지적. 중복 surrogate JSON 키는 검토자가 메모리 parser 1건으로 오류 문자열 UTF-8 실패 확인 | 입력 문자열 UTF-8 확인·duplicate key의 repr 표현. 최종 두 반례 PASS |

첫 기본 suite는 68개 중 67 PASS·1 SKIP였다. 이후 반례 추가/수정으로 최종 82개 중 81 PASS·1 SKIP가 됐다. 같은 실패를 무의미하게 반복하지 않았고, 변경된 가드를 해당 반례와 최종 suite로 확인했다. 실패 run을 재사용하거나 정상 후보로 바꾸지 않았다.

## 범위·변이·안전성 증거

- 대본 SHA, 사례/턴 누락·중복·9/11턴·교환, 화자/본문/발음 혼입, 독립 관측·WAV 해시 불일치를 실제 인공 입력으로 거절했다.
- 음수/역전/동일 start/0길이/EOF 초과/큰 gap/bool/문자열/NaN/Infinity/null 및 중간 미확인 gap을 차단했다. start=0, 관측 gap=0, 마지막 not_displayed/null 및 숫자 gap은 허용했다. 마지막 숫자 gap은 EOF에서 빼지 않았다.
- 잘린 RIFF/chunk/data, 헤더·프레임 정합, stereo PCM16 그대로 계측, 미지원 형식 UNSUPPORTED, 원형 바이트 보존을 검사했다.
- 실제 hardlink, 같은 길이 한 바이트 변경, 같은 바이트로 파일 identity 교체, 기존 output/입출력 충돌/경로이탈, Windows 출력 rename 차단을 확인했다. ctime-only 변경과 reparse flag는 합성 분기 검사로 구분한다.
- **SHA 변이 1개:** 정상 CONTROL PASS → 잘못된 독립 WAV SHA는 원본 검사기 REJECTED → 메모리 사본에서 SHA 비교만 제거하면 잘못된 입력이 PASS → 기존 REJECTED 오라클이 실제 AssertionError를 내어 변이 검출. 원본 검사기 파일 바이트는 보존했다. 이 과정은 최종 82개 중 하나이며 별도 성공 분모로 중복 합산하지 않는다.
- 실제 symlink 생성 1건은 Windows 권한 오류1314로 **SKIP**했다. 권한을 완화하지 않았다. 실제 junction 생성 및 제자리 FSCTL_SET_REPARSE_POINT 공격은 실행하지 않았으며 합성 reparse 검사와 동일하게 취급하지 않는다. 출력은 Windows 전용이고, directory WRITE/DELETE 공유를 제외하는 설계와 실제 rename 차단 결과까지만 확인했다.

## 인계와 미완료

소유 신규 검사기·테스트·보고서만 작업 브랜치로 전달한다. 실제 공식 WAV 2개와 출처·시각·독립 해시가 있는 편집기 20턴 관측 자료를 받으면 새 run에서 같은 도구로 검증한다. 공식 WAV 다운로드나 기존 run 덮어쓰기는 자동 실행하지 않았다. 현재 미전송 공식 산출물은 없으며 아직 공식 후보를 만들지 않았다.

사람 청취, 실제 화자·발화의 음성 일치, STT, 공식 음원 종료 후 제품 분석, 부모 서비스 연결·최종 인수·N02 전체·TEST는 미완료다. pc1이 결과를 독립 확인한 뒤 공용 fixture/manifest, Release/tag와 UI 통합을 결정한다. 이번 인공 PASS를 해당 후속 검사의 PASS로 확대하지 않는다.
