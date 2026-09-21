# PC3 N03-M6 보완본 — 메인 격리 인수 검증

검증 종료: 2026-09-22 01:51:13 KST. 대상은 `origin/work/pc3-n03-wms-scenes`의 `2c9f3e097064568203e7b95a8d3a0a662d944d36`입니다. **제공된 최종 suite 30/30 PASS, 실패 0, 오류 0, unittest SKIP 0, 343.322초, 실제 프로세스 exit 0**을 확인했습니다. 한 번 시작한 실행 handle `66357`을 끝까지 유지했고 재시작하지 않았습니다.

이번 결과는 패키징 도구의 합성 입력 검사입니다. 실제 Blender 장면, 실제 MP4 디코딩, 제품 등록·배포, 시각 품질 또는 전체 N03 완료 판정이 아닙니다. 메인의 별도 적대검토 결과와 아래 인수 조건을 함께 적용합니다.

## 범위와 사전 확인

- 계약: `reports/channel/N03-M6-followup-review.md`. 최초 제출 `3a223f160941212d4d8608a53806563ec2ef9318` 및 보완 제출 `2c9f3e...`의 `git diff-tree --no-commit-id --name-status -r <SHA>`를 각각 확인했습니다. 최초는 아래 5파일 추가, 보완은 같은 5파일 수정이며 기존 생성기/M5/제품 파일 변경이 없습니다.
- 배정 시 메인 기준은 `e2157c4`; 실제 추출 시 HEAD는 문서 커밋을 포함한 `806ce27a2f878fbdb200133f0483969a0c0243fa`였습니다. 메인 브랜치나 기존 변경을 되돌리지 않았습니다. 최초 M6는 아직 메인에 통합되지 않은 상태에서 검증했습니다.
- 원격 전체 브랜치에는 과거 보고서 차이도 있으므로 전체 diff를 통합 대상으로 간주하지 않았습니다. 검증 대상은 M6 소유 5파일에 한정했습니다.
- 두 스크립트와 세 보고서의 현재/과거 증거 구분, 테스트의 실제 실행 경로를 먼저 읽었습니다. `full-media-checks.json`의 최상위 `sources`·19개 suite 등은 원 제출 이력이며 현재 증거는 명시된 `currentEvidenceSection=reviewCorrection`입니다.
- 제공 suite의 미디어 subprocess는 `FakeProcesses`로 대체합니다. 의존 생성기 파일은 fixture의 바이트/해시 용도로 읽고 복사하며 Blender를 import하거나 실행하지 않습니다. 테스트가 만드는 인공 291파일과 junction은 신규 격리 폴더 아래에만 있습니다.

## Git blob 추출 및 보존

처음에 존재하지 않음을 확인한 `.local/pc3-m6-corrected-intake-2c9f3e/`에 `git show <SHA>:<path>`의 stdout 바이트를 그대로 기록했습니다. 신규 5파일은 원격 `2c9f3e...`, 의존 16파일은 메인 `806ce27...`에서 추출했습니다. 추출 후 **21/21 Git blob 바이트 일치**, 의존 파일은 **16/16 메인과 원격 blob 동일**을 확인했습니다.

| 원격 파일 | 바이트 | SHA256 |
|---|---:|---|
| `scripts/media_pc3/package_full_animation_media.py` | 40,523 | `cad81122ffb8225c35e58d7ca8b6327701e504e8ddbd8c6dd7d5b667d12b9396` |
| `scripts/media_pc3/test_full_animation_media.py` | 41,324 | `672ad99b52c06df95a53ee1b051a9d3e0c9c0e2c2c6b620fa031fcdb94b8f398` |
| `reports/pc3/full-media-checks.json` | 77,974 | `e1c15593ea9005a6dd218b62b730841f0fb37ac7e3bd139a677fa095a8e2d595` |
| `reports/pc3/full-media-design.md` | 7,244 | `ed42b3e5c95556cb0cdb9a566e4cf5d4fe47df4009b0d6996043d2b865ad163b` |
| `reports/pc3/full-media-handoff.md` | 14,388 | `8c1992c703093bae7292d19fb1ecdd55117e9a12c6e469bb19dce7f75997ce1d` |

의존 16파일: `scripts/media_pc3/`의 `verify_full_animation.py`, `verify_render_package.py`, `full_render_gate.py`, `build_scene.py`, `scene_contract.py`, `look_presets.py`, `environment_detail.py`, `shadow_settings.py`, `test_full_animation_package.py`, `test_render_package.py`, `test_full_render_gate.py`, `test_environment_detail.py`, `test_look_presets.py`, `audit_guard_supports.py`와 `reports/pc3/render-package-expectations.json`, `render-package-test-layout.json`입니다. 기존 fixture 2파일도 최초 준비에 포함하여 setup 실패 없이 실행했습니다.

실행 전후 **격리 사본 21/21 동일**, 읽기 전용 메인 의존 파일 **16/16 동일**입니다. 상세 바이트·SHA는 로컬 `intake-manifest.json` 및 `main-intake-result.json`에 있습니다. Git blob과 Windows checkout의 줄바꿈 차이를 혼동하지 않도록 메인 파일은 자신의 실행 전 해시와 실행 후 해시를 비교했습니다.

## 실제 실행과 분모

메인 repo에서 실행한 명령은 다음과 같습니다. Python은 `.venv`의 3.12.14이며 `-B -X utf8`를 사용했습니다.

```powershell
.venv/Scripts/python.exe -B -X utf8 .local/pc3-m6-corrected-intake-2c9f3e/run-main-intake.py
```

이 로컬 수집기는 격리 루트로 작업 경로를 바꾸고 원격 테스트 소스를 수정하지 않은 채 `unittest.defaultTestLoader.loadTestsFromModule(test_full_animation_media)`로 제공 suite 전체를 실행합니다. 테스트 전후 해시, unittest 결과, 테스트 모듈의 음성 사례·변이 기록 및 Python audit 이벤트를 저장합니다. 별도의 추가 반례는 이번 담당 범위에 포함하지 않았습니다.

| 항목 | 실측 |
|---|---:|
| unittest 메서드 | 30/30 PASS |
| 성공한 outer subtest 관측 | 104 |
| 실패 / 오류 / unittest SKIP | 0 / 0 / 0 |
| 수집기 경과 시간 | 343.321739초 |
| 원본 unittest 로그 시간 | 343.321초 |
| 실제 명령 종료 코드 | 0 |
| 제공 suite의 고유 음성 사례 | 118 |
| 제공 가드 제거 변이 검출 | 3/3 |
| mock 미디어 호출 | encode 70 / decode 58 / probe 17 |

메서드 수, subtest 수, 고유 음성 사례, 변이 수는 서로 겹치는 별도 분모이며 합산하지 않습니다. mock `videoDecoded=True`는 코드 경로 결과이며 실제 디코딩 성공으로 보고하지 않습니다.

실제 subprocess audit에는 격리된 junction 음성 검사를 위한 `cmd /c mklink /J` 한 건만 있습니다. junction 목적지와 삭제·이동 대상은 해당 `TemporaryDirectory` 안에 제한됐고 테스트의 부모 경로 확인을 통과했습니다. 미디어 실행 0, 서버·브라우저·렌더 실행 0, socket connect/bind 이벤트 0입니다. API/메일/Git 쓰기 및 권한·프로세스 조작은 수행하지 않았습니다.

**별도 실제 FFmpeg 작은 인공 입력 검사: SKIP.** 커밋된 제공 suite에는 실제 도구 샘플 실행이 없습니다. PC3가 보고한 별도 로컬 64×64 3프레임 샘플 및 기존 1080p 출력 비교는 이번 메인이 다시 실행한 증거가 아닙니다. unittest SKIP 0과 이 범위 밖 실도구 재실행 미실시를 구분합니다.

## 보완 두 항목과 변이 증거

1. 정상 무회전 metadata와 v0/v1 항등행렬은 통과하고, 비영 회전·누락/변형/미지원 행렬·크롭·비정방 픽셀은 거절했습니다. `disable-matrix-guard-in-memory`는 해당 음성 테스트에서 1 failure / 0 error로 검출됐습니다.
2. 최종 입력 검사 실패와 cleanup `PermissionError`를 함께 주입한 경우 staged report까지 도달했으나 공개 `candidate-report.json`은 존재하지 않았고 소비자는 `valid=False`였습니다. 실제 unlink 시도는 0회이므로 실패 안전성이 성공 마커 삭제 허용에 의존하지 않았습니다. 실제 Windows 파일 잠금이나 ACL 변경 실험은 아닙니다.
3. 소비자 inventory 가드 2곳을 함께 비활성화한 하나의 변이는 성공 report와 failure marker가 함께 있는 음성 사례에서 1 failure / 0 error로 검출됐습니다. 기존 288프레임 full decode 가드 변이도 1 failure / 0 error로 검출됐습니다. 변이는 메모리에서만 적용했고 원본은 바뀌지 않았습니다.

## 메인 인수 조건과 남은 한계

제공 suite 재현은 통과했습니다. 메인이 전달한 별도 적대검토의 인수 조건을 함께 유지합니다.

- 생산자를 **`2c9f3e...`의 고정 소스**로 한정하고, 해당 생산자의 실제 실행이 성공을 반환한 새 후보만 인수합니다.
- 인수 시 `validate_candidate(directory)`를 다시 실행하여 `valid is True`, `status == "PASS_WITH_PENDING"`와 전체 4파일 결합을 확인합니다.
- **구본 생산자의 후보는 사용하지 않습니다.** legacy 후보에 4파일이 남아 있다는 사실과 consumer 성공만으로 어떤 생산자가 끝까지 성공했는지 인증할 수 없습니다. consumer는 신뢰할 생산자와 성공한 실행 이력을 대신하는 인증 수단이 아닙니다.
- 마지막 검증 이후 외부 변경을 영구 방지하지 않습니다. 소비 시점 재검증 및 파일 통제, 실제 디코딩·렌더·시각 품질과 UI seek·제품 등록 확인은 메인의 별도 게이트입니다.

원본 Blender PID `13052`는 시작 시각 2026-09-21 23:11:14인 동일 프로세스로 실행 중임을 전후 조회했습니다. 렌더 입력·출력은 이 검증의 입력으로 사용하지 않았고 파일 변경, 종료, 재시작을 하지 않았습니다. 288프레임 완성 여부나 실제 영상 품질을 이 보고서에서 새로 판정하지 않습니다.

## 로컬 원증거

모두 `.local/pc3-m6-corrected-intake-2c9f3e/` 아래이며 테스트 코드나 제품에 추가하지 않았습니다.

| 파일 | 바이트 | SHA256 |
|---|---:|---|
| `intake-manifest.json` | 5,201 | `44f2eb5996ff70641011a3b1740cf3c6506533d0131d6c116de4b421149268fd` |
| `run-main-intake.py` | 3,494 | `5ab4265b5e5d4218dae879e5d36f7f44092a097bb7a18508cf9dc0f91a96cc8e` |
| `unittest-main.log` | 5,562 | `edb1794f279e2c795f4d089eec369331bc8345324a910cf1c299e3ca10a45214` |
| `main-intake-result.json` | 146,743 | `ff3074807b9a68f13a783b9c5c0140666c1876c76e01a4b57f2678b5f22965c3` |

이번 담당자가 메인 추적 영역에 새로 작성한 것은 이 보고서 한 파일입니다. 통합·커밋·메일·원격 완료 판정은 메인 담당이며 아직 이 검증에서 수행하지 않았습니다.

## 메인 별도 반례 검토·통합

메인은 다른 읽기 전용 검토자에게 제공 suite를 반복하지 않고 실제 함수의 메모리 A/B를 요청했습니다. 수정본의 원격 Git blob을 AST로 읽고 파일 I/O와 미디어 응답만 대체했습니다. 검사 전후 원격 소스/테스트 바이트는 위 SHA와 같았습니다.

| 독립 관측 | 결과 |
|---|---|
| 표시행렬10입력 | 항등 v0/v1·pasp4:4 정상3개 허용, 회전·이동·표시크기·pasp4:3 음성7개 TRANSFORM 거절. 구본은10개 모두 허용 |
| 메타데이터6입력 | text/ffprobe의0도 허용, -180/360도 거절. 구본은모두 허용 |
| 정상 생산 | 생산자·소비자 PASS_WITH_PENDING, 마지막 파일 작업이 공개 report rename |
| 최종 입력 변경+삭제/실패진단쓰기 모두 거부 | 구본 FAIL인데 public report 남고 소비자는PASS, 수정본 FAIL이며 public report 없음·unlink0·소비자 INVENTORY 거절 |
| 마지막 공개 rename PermissionError | FAIL:READ, public report 없음, 소비자 INVENTORY 거절 |
| 소비자8음성입력 | failure/staged/누락/바이트변경/단독report/읽기거부/중간실패마커/회전영상+맞춘해시 모두 거절 |
| 독립 가드 변이2개 | 항등성 제거는회전소비자오수용, 마지막입력검사제거는변경입력오수용으로 검출 |

독립 함수 실행은 실제 미디어/파일쓰기/Windows 잠금·rename 검증이 아닙니다. 정상 경로와 추가 반례를 보완하는 증거이며 위30개 suite와 수를 합산하지 않습니다. 기존4파일만 남은 구본 후보는 새 소비자가 PASS할 수 있음을 확인했고, 위 생산자 고정·성공 반환·새 후보·재검증 조건으로 채택 범위를 제한합니다.

메인은 명시5파일만 최초 제출 `df8aacbb7169531917849340468d3b5fb83c842b`, 보완 `1a46f54147683100c335de7c71f8a89ae3358a41`로 통합했습니다. 통합 최종5개 Git blob은 원격2c9f3e와5/5 바이트 일치합니다. 기존 렌더 입력/실행·제품 manifest·UI·음성·원장은 변경하지 않았습니다. 다음 실제 영상 인수는 `planning/media/full-cctv-registration.md`의 별도 순서로 진행합니다.
