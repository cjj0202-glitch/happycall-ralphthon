# pc3 Blender 대표 프레임 독립 검토

검토자: pc1 CJJ의 별도 검증 에이전트. 입력 커밋은 `c208597a318a1934b7ee873299b326619ec23f33`이며, 이전 결과 `d6aa6b3`에서 바뀐 9개 파일을 별도 detached worktree에서 읽었습니다. 주 checkout의 생성기·UI·fixture·manifest를 수정하거나 pc3 결과를 인수 처리하지 않았습니다.

## 현재 판정

2026-09-21 20:13 KST: **대표 3장 실제 렌더는 성공했지만 최종 제작 품질은 미통과**입니다. 정적 안전·순수 계약 검사 후 EEVEE 1280×720/32samples의 frame 1/133/288을 직접 렌더하고 세 PNG 모두 열었습니다. 선택 객체·분기 위치·합성 표시는 읽히지만 빛이 평탄하고 바닥이 과하게 밝으며 주변 구성이 비어 있고 그림자에 노이즈가 남습니다. 기하·작업 위치 검토용 후보로 보존하며 긴 렌더·최종 등록·실제 CCTV 품질로 확대하지 않습니다.

처음 20:07:36 여유 RAM 869,629,952B(0.810GiB), 20:08:54 1,898,479,616B(1.768GiB)여서 Blender를 시작하지 않았습니다. 메인의 브라우저/테스트 종료 통보 후 20:12:41에 2,241,806,336B(2.088GiB)를 새로 확인하고 시작했습니다. 다른 프로세스를 임의 종료하지 않았습니다.

## 입력·안전·계약 검사

- `build_scene.py` 380줄, `scene_contract.py` 266줄과 12개 unittest를 전부 읽었습니다. 생성기에 네트워크·하위 프로세스·외부 업로드 호출은 없습니다. 읽기는 지정 layout/fixture/생성 코드 해시, 쓰기는 지정 output의 blend/PNG/JSON입니다. 비어 있지 않은 output은 거부하며, Blender의 scene object 삭제는 새 `--factory-startup` 프로세스 내부 장면 정리입니다.
- 기본 representative 모드는 frame 1/133/288만 렌더합니다. 별도 animation/short 모드는 이번 실행에 사용하지 않습니다. 입력 해상도 64…3840·samples 1…256, animation의 overview 거부를 구현했습니다.
- 실제 argparse 함수만 AST로 분리해 실행한 CLI 검사 **7/7 PASS**: 정상 representative 1280×720/32samples 1건 허용, 알 수 없는 mode·samples 0/257·해상도 63/3841·animation overview 6건 모두 exit 2. 이 검사는 bpy 호환성 검사가 아닙니다.
- 별도 worktree의 `python -m unittest discover -s tests/remote/pc3 -p test_scene_contract.py -v` 결과 **12/12 PASS, 0.188초**. 임시 테스트 파일은 검토 소유 `.local/pc3-render-intake/test-temp/`에만 생성했습니다. 기존 Windows Temp 폴더는 삭제하지 않았습니다.
- 메인의 현재 layout+fixture를 `load_layout(layout, fixture)`에 직접 넣은 관계 검증도 PASS입니다. 원격 fixture와 메인 fixture의 파일 해시는 다르지만 JSON 의미는 같습니다. CRLF 등의 바이트 차이를 계약 불일치로 세지 않았습니다.

| 입력 | SHA256 |
|---|---|
| 메인 `planning/media/scene-layout-v1.json` | `c6aece6692c6b78beb85d4f1167868f2bd095b3ab8366e837466715b82bd6cb6` |
| 메인 `data/fixtures/cases.json` | `e4bd1cbefee5b32c1d3b00b3cd8a3336524a937923946e0e7323ce6c0bbccd90` |
| worktree `build_scene.py` | `561d2a9b0b53e5cb944465eb9cae315e4c47d739b2b0341b2c21a96939406375` |
| worktree `scene_contract.py` | `670638cae0357da1bf934b7c4b9287ea0780180214e53a181166dd53a8a554bf` |

로컬 증거는 `.local/pc3-render-intake/unit-tests.log`, `pre-render-state.json`, `static-review.json`입니다. 12개 unittest 통과는 접촉·가림·충돌·재질·완성 영상의 통과가 아닙니다. 생성기가 계산하는 `contactPlaneGapMeters`는 선언된 지지 높이와 객체 bbox 바닥의 차이이며, 실제 벨트 형상 지지나 가드 충돌을 대신하지 않습니다.

## 실제 렌더 명령과 결과

검증된 Blender 4.5.14 LTS로 신규 빈 `.local/pc3-render-intake/representatives-01`에만 출력했습니다. 아래 명령은 메모리 시작 기준 충족 후 실제 실행한 명령입니다.

```powershell
& 'C:/00.프로젝트/happycall-ralphthon/.local/tools/blender/blender-4.5.14-windows-x64/blender.exe' --background --factory-startup --python-exit-code 1 --python 'C:/00.프로젝트/happycall-ralphthon/.local/pc3-render-intake/review-c208597/scripts/media_pc3/build_scene.py' -- --layout 'C:/00.프로젝트/happycall-ralphthon/planning/media/scene-layout-v1.json' --fixture 'C:/00.프로젝트/happycall-ralphthon/data/fixtures/cases.json' --output 'C:/00.프로젝트/happycall-ralphthon/.local/pc3-render-intake/representatives-01' --mode representatives --resolution 1280 720 --samples 32
```

단일 실행 래퍼 `run_representatives.py`는 시작 직전 실제 물리 메모리를 다시 읽고 2GiB 미만이면 실행하지 않습니다. 이미 output이 있으면 덮어쓰지 않습니다. 허용 시 자체 Blender 자식 프로세스만 숨김 실행하며, 다른 API/웹/브라우저 프로세스를 조작하지 않습니다. 명령·입력 해시·PID·종료코드·로그를 같은 소유 폴더에 보존합니다.

| 측정 | 실제 결과 |
|---|---|
| 프로세스 | Blender PID 14676, 20:12:41.463 시작 → 20:13:00.083 종료, exit 0 |
| 엔진·해상도 | Blender 4.5.14 LTS / BLENDER_EEVEE_NEXT / 1280×720 / RGB PNG |
| 실제 샘플 | 로그에 각 3프레임 모두 `Rendering 32 / 32 samples` |
| 프로세스 전체 / 생성기 내부 | 18.625초 / 17.565초 |
| frame 1 / 133 / 288 렌더 | 8.205 / 3.159 / 3.173초 |
| 파일 | PNG 3개 + blend + tracks.json + render-report.json = 6개 |
| 궤적 | 연속 index 1…288, 객체 `SYN-VIS-PARCEL02`, 업무 토트 null 288/288 |
| 투영 | clippedFrames 0/288, 선언 지지 높이와 bbox minZ 최대 오차 3.576×10^-8m |
| 입력 보존 | layout/fixture/생성기/contract 4개 모두 렌더 전후 SHA 동일 |

시간·PID·명령은 `render-process.json`, 실제 로그는 `render-stdout.log`, 독립 파일 해시·metadata 재확인은 `independent-render-observations.json`입니다. 종료 후 해당 PID는 조회되지 않았습니다. 렌더 로그는 `Blender quit`으로 끝나며 이번 일반 로그에 ERROR/WARN은 없지만 드라이버 debug 모드 검사를 새로 수행한 것은 아닙니다.

## 실제 3장 관찰과 수정 요청

| 프레임 | 직접 관찰 / metadata 대조 |
|---|---|
| 1, 시연 0초 | 상자가 좌상단 롤러 위에 보이고 가드와 분리됩니다. 투영 bbox 52.399×46.090px로 비교적 작습니다. 지지면에 놓인 모습이며 해당 표본에서 부유·관통은 관찰되지 않았습니다. |
| 133, 시연 5.5초 | 상자가 직선에서 슈트로 분기하는 벨트 위에 회전해 보입니다. bbox 68.148×80.003px. 선택 객체를 가리는 설비는 해당 표본에서 관찰되지 않았습니다. |
| 288, 시연 11.9583초 | 상자가 슈트 끝 구간의 벨트에 보입니다. bbox 93.689×94.516px. 다리·볼트 베이스와 바닥 접촉을 읽을 수 있습니다. |

세 장 모두 위쪽에 `SYNTHETIC SCENE / NOT CCTV`, W-W3, 업무 토트 UNKNOWN 문구가 박혀 있습니다. 별도 워터마크 overlay를 켜지 않아도 raw PNG에 유지됩니다. PNG에는 실제 작업자·고객·센터 도면 문구를 넣지 않았고, 사건 시각과 경과 초의 관계는 metadata로 구분했습니다. 전 프레임 물리 충돌·가림 검사와 실제 시간축 재생은 아직 하지 않았습니다.

**제작 품질 보완:** 공통 구도/카메라/경로를 유지한 채 우선 조명·노출을 한 가지 핵심 변경으로 비교해야 합니다. 현재 콘크리트·금속·벨트가 밝은 회색으로 뭉쳐 대비가 낮고, 롤러 아래와 바닥의 접촉 그림자에 입자가 보입니다. 이 사진 3장의 성공을 사용자 요구의 완성 CCTV 품질로 체크하지 않습니다. 주변을 채우는 작업과 조명 변경을 동시에 한 개선으로 세지 않습니다.

**지지 구조 보완:** 실제 그림에서 보이는 앞쪽 노란 가드의 부유 인상은 코드에서도 근거가 있습니다. `build_scene.py`의 `Guard support`는 북쪽(y=8.28)만 생성합니다. 남쪽 가드 밑면은 1.06−0.10/2=1.01m, main channel 윗면은 0.85−0.12+0.22/2=0.84m로 0.17m 차이입니다. outfeed guard 밑면 1.02−0.14/2=0.95m와 side frame 윗면 0.85−0.13+0.24/2=0.84m 사이도 0.11m이며 별도 가드 받침이 없습니다. 이는 지지 구조 생성 코드와 렌더에 대한 보완 요청이며 상자 충돌 검사를 실행했다는 주장은 아닙니다. 남쪽·outfeed 가드를 실제 프레임과 연결하는 받침을 추가하고 같은 3장으로 재검수할 수 있습니다.

| 실제 산출물 | 크기(B) | SHA256 |
|---|---:|---|
| frame-0001.png | 1,000,500 | `620bf3b4b8d8aae25985c71496dc1b98b684f2924d6770b20c15526aa7952e3a` |
| frame-0133.png | 1,004,677 | `515553f485adfdedb340c7fc8e1ac0cc9ab5cd8ebd26fb37e712ecfaa70ed2a1` |
| frame-0288.png | 1,005,613 | `d3cd9c9c327fccd7e92c6824063e6c174ef5388b22a9a2ff36f75501424008f3` |
| tracks.json | 158,545 | `9fb424be0fd212bbf3faa057097bec56c63a89e4b8ae08c524e5fd76b80fd44b` |
| render-report.json | 2,590 | `6dca73e7cd19fc5a5106bb17ce10d4ca6b13f1900ae6f28c2e43adae73efbab6` |
| case-0002-ww3.blend — 로컬만 | 2,630,923 | `649d2be71b797acc416a057b62c4609e98d62226860a7a0331e2c55a440618c7` |

## pc3에 전달할 후보 Release

메인의 추가 배정으로 [대표 프레임 prerelease](https://github.com/cjj0202-glitch/happycall-ralphthon/releases/tag/demo-wms-blender-representatives-20260921)를 2026-09-21 20:15:44 KST에 공개했습니다. 생성 전 같은 tag의 Release가 없고 원격 tag도 없음을 확인했으며 기존 자산을 덮지 않았습니다. target은 검사한 `c208597a318a1934b7ee873299b326619ec23f33`, prerelease=true, draft=false입니다.

허용된 **PNG 3개 + tracks.json + render-report.json 정확히 5개, 3,171,925B**만 업로드했습니다. 생성 후 GitHub API의 asset 이름 집합·각 size·서버 `digest=sha256:…`를 로컬 값과 대조해 **5/5 동일**을 확인했습니다. `.blend`, 회사 원도면·원천, 실제 실행 로그는 업로드하지 않았습니다. `render-report.json`의 blend 항목은 로컬 산출물의 이름/크기/해시만 기록한 것입니다. Release 설명에도 시각 품질 미통과와 실제 영상/업무 근거 아님을 명시했습니다.

재현 확인: `gh api repos/cjj0202-glitch/happycall-ralphthon/releases/tags/demo-wms-blender-representatives-20260921`. 상세 원격 대조는 로컬 `release-verification.json`입니다. Release 공유를 pc3 수신·수정 착수나 품질 인수로 보고하지 않으며, 이슈 회신과 Git 커밋은 메인 담당입니다.

## 남은 인수 범위

대표 PNG 3장 직접 관찰은 마쳤으나 제작 품질 보완·지지 구조 수정과 같은 조건 재검이 필요합니다. 288개 궤적 metadata는 288장 렌더를 뜻하지 않습니다. 짧은 실제 움직임, 최종 1080p/MP4, 웹 재생·탐색·전체화면, 새 자산의 동일 빌드 통합은 별도 미실행입니다. 공유용 후보를 올리는 것은 이 품질 게이트의 인수가 아닙니다.
