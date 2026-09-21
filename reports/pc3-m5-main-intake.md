# N03-M5 메인 통합 인수 기록

2026-09-21 23:49 KST · 실제 pc1/CJJ 로컬 보조 에이전트 · Python 3.12.14 / Windows 11 10.0.26200

PC3 수신 검사기와 재현 의존 파일 30개를 원격 Git blob 바이트 그대로 main 작업트리에 반영했습니다. M5 18개 검사 집계는 17 PASS·1 SKIP·FAIL 0·ERROR 0입니다. 기본 인코딩 실행에는 junction 명령 출력의 보조 스레드 디코딩 예외가 있었으며, UTF-8 모드의 동일 junction 반례 1개 재검증은 예외 없이 통과했습니다. 기존 검사기와 승인 게이트 36개는 34 PASS·2 SKIP입니다. 실제 전체 렌더 검수·제품 인수는 남아 있습니다.

## 출처·신원·소유

- 실제 신원 명령: `.venv/Scripts/python.exe -B channel/whoami.py`. 23:44:02 KST 출력은 pc1 / CJJ / cjj0202-glitch / main입니다. 로컬 보조 에이전트 결과이며 원격 pc3 실행으로 세지 않습니다.
- 기준 HEAD 및 최종 바이트 대조 시 HEAD: `5af3617dcf18a30854d018693cff3bcb7a8fb461`.
- M5 수신 SHA: `de2c790a5e739a4aa9cdb2fc481fb10db3e43e29`. 기존 검사 의존 SHA: `a39cd664758575a81e1fcce437db245f60fc2c1b`.
- 계약: [N03-M5 배정](channel/N03-M5-full-output-intake.md), [메인 독립 코드 검토](pc3-m5-main-code-review.md), [PC3 인계](pc3/full-output-handoff.md).
- 시작 때 다른 소유자의 변경 9개가 있었습니다. 이 작업은 아래 30개 신규 경로와 이 보고서 1개만 소유합니다. 중앙 작업표·CURRENT_TODO·다른 소유 파일·커밋·push는 메인이 맡습니다.
- 읽은 실행 지침: AGENTS.md, PROMPT_team.md, TODO.md, docs21/24/27/28, planning 결정, 공유 verification 상세, happycall-night-ops 공유 정본. `ops/tasks.py status/check`는 작업 45개, DONE 3 / TODO 42, 형식 검사 PASS였고 변경하지 않았습니다. 외부 API 계정 재조회는 이 배정의 API 금지 경계에 따라 실행하지 않았습니다.

## 발견한 재현 의존 문제와 해결

최초 지정 M5 5개 경로는 존재·추적·수정이 모두 없었습니다. 추가 확인에서 main의 `scripts/media_pc3` 자체도 존재하지 않았습니다(`Test-Path False`, 해당 범위 `git ls-files`·`git status` 출력 0줄). 새 검사기는 기존 `verify_render_package.py`, `full_render_gate.py`와 테스트 보조 모듈을 가져오므로 M5 5개만 적용해서는 실행할 수 없습니다.

메인이 범위를 명시 확대하여 a39cd664의 `scripts/media_pc3` 기존 23개를 함께 반영했습니다. 이어 테스트가 직접 읽는 `reports/pc3/render-package-expectations.json` 및 `render-package-test-layout.json` 2개도 main에 없어 실행 전 보류·보고했고, 메인의 명시 승인 후 같은 a39cd664에서 반영했습니다. 이들은 SYN 독립 합성 검사 입력입니다. expectations의 sourceCommit은 `33fa0e4edeb88c0d4ad5e9cc0194ffc7e96cebcd`, mode는 `representatives`로, 과거 대표 3장 검사용입니다. 현재 전체 렌더의 승인 기대 manifest가 아니며 메인이 실물·검수 receipt에서 별도로 고정해야 합니다.

파일 적용은 `git show <정확 SHA>:<경로>`를 Python subprocess bytes로 받아, 경로 부재/추적 없음/수정 없음 확인 후 `open("xb")`로 생성했습니다. 셸 텍스트 리디렉션이나 줄바꿈 변환은 사용하지 않았습니다. 총 23+5+2=30개가 원본과 일치했으며, 테스트 후 2026-09-21T23:49:31.044983+09:00에도 30/30 원바이트 일치를 다시 확인했습니다. 이 보고서를 포함한 소유 산출물은 31개입니다.

## 실제 실행과 원격 결과 대조

작업 루트는 `C:/00.프로젝트/happycall-ralphthon`입니다. 아래 세 실행은 모두 인공 temp 출력만 사용했으며 새 Blender 실행은 0회입니다.

| 실제 실행 | 분모 | PASS | SKIP | FAIL / ERROR | 시간 | 종료 |
|---|---:|---:|---:|---:|---:|---:|
| PC1 M5 지정 suite | 18 | 17 | 1 | 0 / 0 | 102.283초 | 0 |
| PC1 junction UTF-8 재검증 | 1 | 1 | 0 | 0 / 0 | 4.839초 | 0 |
| PC1 기존 package 19 + full gate 17 | 36 | 34 | 2 | 0 / 0 | 35.859초 | 0 |
| PC3 보고 M5 suite | 18 | 17 | 1 | 0 / 0 | 87.593초 | 원격 기록 |

1. 요청된 명령을 기본 환경 그대로 실제 실행했습니다.

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s scripts/media_pc3 -p test_full_animation_package.py -v
```

실제 종료 출력:

```text
Ran 18 tests in 102.283s
OK (skipped=1)
```

M5의 양성 대조군은 PNG 288개·좌표 288행·총 291파일인 인공 묶음입니다. API/CLI의 정상 통과, 마지막 시각 287/24, 입력 바이트 보존, PASS_WITH_PENDING과 미검수 플래그 보존을 실제 assertion으로 확인했습니다. 누락·중복·PNG 바이트/SHA/CRC·720p·72장 보고서·다른 입력/receipt·좌표/시각/범위·readback·자기 기대값·경로이탈·입력 변경 반례가 실행됐습니다.

실제 hardlink와 junction 가드는 도달 후 차단됐습니다. `test_disabled_png_hash_guard_is_killed_by_independent_negative`도 통과하여 메모리의 PNG 해시 가드 제거 변이가 실제 독립 assertion 실패로 검출됐습니다(1/1). 원본 파일은 바꾸지 않았습니다. 이 테스트에서 AST 실행의 `ImportWarning`이 출력됐으며 테스트 실패가 아닙니다.

심볼릭 링크 생성은 `WinError 1314`로 OS가 거부하여 `test_symlink_asset_rejected_if_os_permits_creation` 1개가 SKIP입니다. 권한을 바꾸거나 우회하지 않았고 symlink 가드 통과로 세지 않습니다. PC3의 같은 1개 SKIP 사유와 일치합니다.

PC3 보고에는 별도 수집기로 센 거부 반례 129개가 있습니다. 이번 PC1의 지정 unittest CLI는 그 전역 카운터를 출력하지 않으므로 129를 PC1 재집계 값으로 옮기지 않습니다. 18개 테스트 메서드 분모와 129개 원격 반례 분모는 다릅니다.

2. 기본 인코딩에서 발견한 환경 반례와 재검증:

```text
test_junction_package_rejected_by_actual_reparse_guard ...
Exception in thread Thread-5 (_readerthread)
UnicodeDecodeError: 'cp949' codec can't decode byte 0xed in position 27: illegal multibyte sequence
ok
```

`subprocess.run(..., text=True)`가 junction 생성 명령의 UTF-8 출력을 cp949로 읽으면서 보조 스레드 예외를 냈습니다. unittest 본체는 성공으로 집계했으므로 위 18개 결과를 예외 없는 실행으로 표현하지 않습니다. 수신 소스는 그대로 보존하고 자식 Python의 `PYTHONUTF8=1`만 지정하여 동일 junction 테스트를 다시 실행했습니다. 작업 폴더는 `scripts/media_pc3`입니다.

```powershell
$priorPythonUtf8 = $env:PYTHONUTF8
try {
    $env:PYTHONUTF8 = '1'
    & 'C:/00.프로젝트/happycall-ralphthon/.venv/Scripts/python.exe' -B -m unittest test_full_animation_package.FullAnimationPackageTests.test_junction_package_rejected_by_actual_reparse_guard -v
    $testExitCode = $LASTEXITCODE
} finally {
    if ($null -eq $priorPythonUtf8) { Remove-Item Env:PYTHONUTF8 -ErrorAction SilentlyContinue }
    else { $env:PYTHONUTF8 = $priorPythonUtf8 }
}
exit $testExitCode
```

```text
test_junction_package_rejected_by_actual_reparse_guard ... ok
Ran 1 test in 4.839s
OK
```

이 재검증은 보조 스레드 예외 없이 끝났습니다. 본체 코드 수정은 없으며, 이 Windows 환경에서 텍스트 출력을 수집하는 회귀 명령에는 UTF-8 모드를 적용했습니다.

3. 기존 검사기 영향 범위는 같은 UTF-8 환경 설정·복원 안에서 다음 명령으로 실행했습니다.

```powershell
# cwd: C:/00.프로젝트/happycall-ralphthon/scripts/media_pc3
& 'C:/00.프로젝트/happycall-ralphthon/.venv/Scripts/python.exe' -B -m unittest test_render_package test_full_render_gate -v
```

```text
Ran 36 tests in 35.859s
OK (skipped=2)
```

기존 720p 검사기의 정상 4모드, 해시·시각·환경·추가파일 가드 제거 4변이, 경로/링크/불완전 파일, 입력 보존을 실행했습니다. full gate의 승인 receipt·설정/readback/입력 변경·두 번째 검증·receipt SHA 가드 제거 변이도 실행했습니다. `build_scene.py`의 실제 main/인수 파서/수집 함수는 AST로 추출해 bpy·render stub에 연결하며 최초 render stub에서 멈춥니다. Blender 프로세스를 호출하지 않습니다. SKIP 2개는 각 suite의 실제 symlink 생성 권한 제한이며 hardlink/junction은 통과했습니다.

## 최종 바이트 대조

아래 SHA256은 PC1 작업트리 실제 파일값이며 표시된 Git SHA의 blob bytes와 30/30 일치합니다. 원격 보고의 본문을 PC1 실측으로 덮어쓰지 않았습니다.

| 파일 | 출처 Git | bytes | SHA256 |
|---|---|---:|---|
| `scripts/media_pc3/BLENDER.md` | a39cd664 | 11388 | `b4d19cd501422c90e0b566ddeebe6726195e01b373b894cf4b9ec1b8b1167c0a` |
| `scripts/media_pc3/README.md` | a39cd664 | 3035 | `8b62ff48278cd2ca4ecbe2e338bdd0fbc2e43cb63882c6b89d9129ace12d39b2` |
| `scripts/media_pc3/audit_guard_supports.py` | a39cd664 | 14677 | `c86199ac17d658ce6b21518340784de65d3e6ebb49dfa07592af0367f7c325a5` |
| `scripts/media_pc3/build_review_page.py` | a39cd664 | 19121 | `e917bf1e33b30cbba40c63c9cb6f77b7b270a6b09c36a8884a84ca398ad25951` |
| `scripts/media_pc3/build_scene.py` | a39cd664 | 28295 | `c255e94d9f93a08734bf49cc0a7da1edc5304f4b0a9955e6508864dc72998320` |
| `scripts/media_pc3/compare_representatives.py` | a39cd664 | 11551 | `fd6b3ee4b451f4f9dc39f3ef638e7b407668d40d4864efc9de947028604e5412` |
| `scripts/media_pc3/environment_detail.py` | a39cd664 | 3714 | `e4a82164a828e165f86b496883d539311fd4f2a98e7581edca4cc197f7a19c36` |
| `scripts/media_pc3/full_render_gate.py` | a39cd664 | 23306 | `382d764b06da18abd710a50edecdf874883038fffea1a5e55bbd747e61fa12c5` |
| `scripts/media_pc3/generate_candidates.py` | a39cd664 | 9690 | `5bfd67a9bf81a4b10604fc26b0d0384255bad2b707e284d14b4090ae4ce7302f` |
| `scripts/media_pc3/look_presets.py` | a39cd664 | 1762 | `91c3852386c48729d24f69fff1049602451646a41c7d532d4dc4f8f008cd3e33` |
| `scripts/media_pc3/media_contract.py` | a39cd664 | 7778 | `1d7e6f094d9838c839c7e2cc242ea86f29c7aae81f3926c301b1169599e7fad2` |
| `scripts/media_pc3/requirements.txt` | a39cd664 | 37 | `632ed6a2203d994ab4340c918c2618d0d9b1a278884e8e6c281698acc2680982` |
| `scripts/media_pc3/scene_contract.py` | a39cd664 | 14278 | `670638cae0357da1bf934b7c4b9287ea0780180214e53a181166dd53a8a554bf` |
| `scripts/media_pc3/shadow_settings.py` | a39cd664 | 2643 | `4d1357cde51530be813e3a1505972b253b9b23ae8c35a99cbb1b304fe5c374fe` |
| `scripts/media_pc3/test_compare_representatives.py` | a39cd664 | 13193 | `f0c65f9ee14e610381a53c522704132a0d1e588791e67df7d4e8d238ccb8dab7` |
| `scripts/media_pc3/test_environment_detail.py` | a39cd664 | 23414 | `768483c7e1627ca35929191d60a923c1b2f75fe36c92a4ddf50079e7f5921f23` |
| `scripts/media_pc3/test_full_render_gate.py` | a39cd664 | 28727 | `85e2f89abf1fc0fe326400d88d094be8a558f0bcd9f877ac4bada36a71e47955` |
| `scripts/media_pc3/test_look_presets.py` | a39cd664 | 18867 | `5befb2602001f8c40a52d0670717729c8bc46b4bb83e73955523ccd1288a8446` |
| `scripts/media_pc3/test_media_contract.py` | a39cd664 | 4431 | `84a5d8801480125cb09a4e427ee23553101089b6eadd3f75ffab34d2fe097995` |
| `scripts/media_pc3/test_render_package.py` | a39cd664 | 28542 | `a5a1b448763955ba1542be73abfb67c7a4445c7faccf3b504f5dbb9cefec51ad` |
| `scripts/media_pc3/test_review_package.py` | a39cd664 | 13933 | `aec79018a4c8f117d1216d52cbb178a377ba6e0f894eb3be2e79304d1506fd2e` |
| `scripts/media_pc3/test_shadow_settings.py` | a39cd664 | 13816 | `fcc9a2f9cbb2a20f5821fa978f4f46c13225508b4b0f29180bbf7961d5560293` |
| `scripts/media_pc3/verify_render_package.py` | a39cd664 | 29547 | `36b4e2f3de8f0517da6cb26719e346e0fbfec221f5d1b673e494a73c31af30cc` |
| `reports/pc3/render-package-test-layout.json` | a39cd664 | 1772 | `c6aece6692c6b78beb85d4f1167868f2bd095b3ab8366e837466715b82bd6cb6` |
| `reports/pc3/render-package-expectations.json` | a39cd664 | 25709 | `0cf8ba1d87759fcf6e0cbca0a6c6fbfd0a7be828233ed93ca386e407662683bb` |
| `scripts/media_pc3/verify_full_animation.py` | de2c790a | 21052 | `a711fed3ce821bb1e24caafadcf2c6161f266e9b031cfea29b73d46e0d716075` |
| `scripts/media_pc3/test_full_animation_package.py` | de2c790a | 25007 | `bc6dd3735da0b435fa38fca982a2677b344371076beb9db62babcc92fadcb5b9` |
| `reports/pc3/full-output-design.md` | de2c790a | 2924 | `a654cd92fd33e1ba72ddccdf2a63a5ebad6132fcaba5f488667eec2f4975a3fa` |
| `reports/pc3/full-output-handoff.md` | de2c790a | 7833 | `e3701ba03fcc37ad8b2aa940ffb224065da1bb2dd8c30178a1aa249b3f64a5ab` |
| `reports/pc3/full-output-checks.json` | de2c790a | 15974 | `acb9cca56bc92f7669f792e361767e62a54d1f488f200dab00928855542d03ec` |

## 동결 범위와 남은 인수

기존 PID13052 또는 `.local/pc3-render-intake/full1080-a39cd66-01`의 상태·파일·진도는 이 작업에서 읽거나 검사하지 않았습니다. 재시작·변경·새 렌더·설치·서버·브라우저·외부 API·키·사내 원천 경로 접근도 하지 않았습니다. 인공 테스트는 자체 `.local/pc3-m5-intake`, `.local/pc3-tests/render-package`, `.local/pc3-full-render-gate` 아래 임시 묶음만 사용했습니다.

실제 288 PNG + report + tracks + blend 완주 묶음에 대한 독립 full 기대 manifest/CLI 검사, 픽셀 디코딩, 최종 blend 검사, MP4 인코딩·재생/탐색, 시각 품질·좌표 시간축·제품 등록/배포는 미실행입니다. 원격 TEST 왕복·사람 검수·전체 제품 인수도 이 보고서로 완료하지 않습니다.

작업트리 31개 소유 산출물을 메인 인수용으로 동결합니다. 커밋·push·중앙 원장 갱신·배정 이슈 회신은 메인이 수행합니다.
