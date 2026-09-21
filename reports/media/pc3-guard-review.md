# PC3 가드 수정본 독립 재검수

2026-09-21 20:36 KST, pc1 CJJ의 별도 검증 에이전트가 `03291cca16310926a28a5b7d01ff02b9c0d2ec2e`를 확인했습니다. **가드 받침 수정은 수치 검사와 대표 3프레임 관찰에서 개선을 확인했습니다. 최종 영상 품질은 아직 미통과입니다.**

원격 브랜치가 조회 시 `d67b2c7`까지 진행됐지만 이번 검수는 요청된 `03291cca`에 고정했습니다. 입력 코드와 출력은 `.local/pc3-render-intake/guard-02/`에 격리했고 이전 `review-c208597`과 대표 렌더를 보존했습니다. 메인 제품·fixture·manifest·ops 파일을 수정하지 않았습니다. 이 보고는 인수 권고이며 메인의 최종 등록이나 N03 완료를 뜻하지 않습니다.

## 변경과 검증 입력

이전 `c208597a318a1934b7ee873299b326619ec23f33` 대비 4개 파일입니다. `build_scene.py`의 받침 생성 부분, 신규 수치 감사기, PC3 보고 2개가 바뀌었습니다. 생성기에서는 기존 북쪽 받침 6개의 폭·위치를 수정하고 남쪽 6개와 출구 6개를 추가했습니다. 카메라·경로·조명·재질·seed·합성 표시는 바꾸지 않았습니다.

메인의 layout와 fixture를 읽기 전용 원본으로 삼고 `guard-02/input/`에 바이트 그대로 복사했습니다. 작업자 fixture와 현재 fixture의 의미 차이는 두 케이스의 발화 start/end 32곳과 `transcriptTiming` 2곳뿐입니다. 장면 관련 사건·분류·도크·토트 관계는 같고 현재 fixture로 관계 검증을 통과했습니다.

| 입력 | SHA256 |
|---|---|
| layout | `c6aece6692c6b78beb85d4f1167868f2bd095b3ab8366e837466715b82bd6cb6` |
| 메인 fixture 복사본 | `79c3b01aed139352b5cc0a695f2829e76f78eabb61d7cfd6b8055db32f61a73b` |
| 생성기 | `7d20c5b1453712dae2bce47bc49e17884ea49b3ea0ff0acce8ae48ed3f386a91` |
| scene contract | `670638cae0357da1bf934b7c4b9287ea0780180214e53a181166dd53a8a554bf` |
| 가드 감사기 | `c86199ac17d658ce6b21518340784de65d3e6ebb49dfa07592af0367f7c325a5` |

## 실행한 검사

- 별도 worktree에서 `python -B -m unittest discover -s tests/remote/pc3 -p test_scene_contract.py -v`: **12/12 PASS**, unittest 내부 0.132초. 임시 입력은 이번 검토 폴더의 `test-temp`를 사용했습니다.
- 같은 worktree의 `audit_guard_supports.py --layout ../input/layout.json --fixture ../input/fixture.json --output ../geometry-audit.json`: **받침 18/18이 가드·프레임 양쪽과 양의 체적으로 겹침**. 가드 5개 구간의 받침 수는 북쪽 6, 남쪽 4+2, 출구 3+3입니다.
- 이전 북쪽 받침의 10mm 수평 단절은 **6/6 거부**했습니다. 의도적 상자 충돌 검출·멀리 떨어진 상자 거부·회전 상자의 AABB 오탐을 SAT로 거부하는 대조 **3/3 PASS**입니다.
- 상자와 받침의 양의 체적 교차는 1ms 간격 **12,001개 자세에서 0**, 실제 정수 프레임 시각 **288개에서 0**입니다. 이는 원시 직육면체 기반 샘플 검사이며 연속 시간 증명이나 Blender 최종 mesh 충돌 판정은 아닙니다.
- 실제 Blender 대표 렌더 전후 입력 5개 SHA가 모두 같고 worktree의 tracked diff는 없습니다. 생성기·감사기를 직접 읽어 이 실행 경로에 네트워크·하위 API·업로드 동작이 없음을 확인했습니다.

감사기를 pc1에서 다시 실행한 사실을 완전히 다른 수학 구현이라고 부르지 않습니다. 수치 판정과 다른 관측으로 실제 Blender 실행·PNG 직접 관찰·산출물 헤더/해시/궤적 대조를 추가했습니다.

## 실제 렌더

시작 직전 가용 RAM은 **2,990,239,744B, 약 2.785GiB**로 2GiB 게이트를 넘었습니다. 검증된 기존 Blender 4.5.14 LTS를 숨김 단일 프로세스, `--threads 2`로 실행했습니다. 다른 서버·브라우저 프로세스를 중지하지 않았습니다.

```powershell
& 'C:/00.프로젝트/happycall-ralphthon/.local/tools/blender/blender-4.5.14-windows-x64/blender.exe' --background --factory-startup --threads 2 --python-exit-code 1 --python 'C:/00.프로젝트/happycall-ralphthon/.local/pc3-render-intake/guard-02/review-03291cc/scripts/media_pc3/build_scene.py' -- --layout 'C:/00.프로젝트/happycall-ralphthon/.local/pc3-render-intake/guard-02/input/layout.json' --fixture 'C:/00.프로젝트/happycall-ralphthon/.local/pc3-render-intake/guard-02/input/fixture.json' --output 'C:/00.프로젝트/happycall-ralphthon/.local/pc3-render-intake/guard-02/representatives' --mode representatives --resolution 1280 720 --samples 32
```

위 명령은 실제 실행한 값입니다. 재실행 시 기존 결과를 덮지 않고 새 output 경로를 정해야 합니다.

| 측정 | 실측 |
|---|---|
| 프로세스 | PID 28496, 20:35:43.220 → 20:35:59.291 KST, exit 0 |
| 전체 / 생성기 내부 시간 | 16.078초 / 15.178초 |
| 엔진·해상도 | BLENDER_EEVEE_NEXT, 1280×720 RGB 8bit PNG |
| 프레임·샘플 | 1 / 133 / 288, 로그에 각 32/32 samples |
| 프레임별 생성기 시간 | 7.001 / 2.961 / 2.901초 |
| 산출물 | PNG 3개, blend 1개, tracks 1개, report 1개 |
| 종료 재확인 | 20:36:46 이후 해당 PID 조회 0개 |

실행 래퍼는 `guard-02/run_review.py`, 명령·RAM·입력 해시·PID·시간은 `render-process.json`, 로그는 `render-stdout.log`에 남았습니다. 별도 `observe_result.py`가 PNG 헤더와 SHA, 288개 metadata를 다시 읽고 `independent-observations.json`을 기록했습니다.

## 직접 연 세 장의 판정

세 PNG를 모두 직접 열었습니다. 노란 가드와 회색 side frame 사이에 진한 받침이 보이고, 이전의 남쪽·출구 가드 부유 인상이 개선됐습니다. 북쪽 받침도 프레임에 연결된 모습입니다. 카메라 구도·주변 설비·워터마크는 유지됩니다.

| 프레임 | 관찰 |
|---|---|
| 1 / 시연 0초 | 상자가 좌상단 롤러 위에 있습니다. 북·남쪽 받침이 가드를 지지하는 모습이며 해당 상자를 가리지 않습니다. 상자 투영 크기 약 52.40×46.09px. |
| 133 / 시연 5.5초 | 상자가 분기부 검은 벨트 위에서 회전한 상태입니다. 분기 개구부에 새 받침이 들어오지 않으며 상자 실루엣이 보입니다. 약 68.15×80.00px. |
| 288 / 시연 11.958초 | 상자가 출구 벨트 끝 구간에 있고 양쪽 가드의 새 받침과 구분됩니다. 표본에서 받침에 의한 관통·가림은 관찰되지 않았습니다. 약 93.69×94.52px. |

`SYNTHETIC SCENE / NOT CCTV`, W-W3, `business tote UNKNOWN` 문구는 세 원본 PNG에 유지됩니다. 실제 작업자 귀책·실제 CCTV·업무 토트 연속 추적으로 표시하지 않았습니다.

**궤적 파일은 이전 렌더와 바이트까지 동일**합니다. SHA `9fb424be0fd212bbf3faa057097bec56c63a89e4b8ae08c524e5fd76b80fd44b`, 연속 frame 1…288, visualObjectId `SYN-VIS-PARCEL02`, 업무 토트 null 288/288, clipped frame 0입니다. 선언 접촉면과 bbox 바닥의 최대 차이는 3.576×10^-8m입니다. 화면 내 투영과 선언면 일치는 실제 mesh 지지·모든 시각의 가림 검사를 대신하지 않습니다.

**전체 제작 품질은 보완 필요**입니다. 바닥·금속·벨트가 여전히 밝고 평탄하며 주변 구성이 비어 있고 접촉 그림자에 입자가 보입니다. 이번 수정은 기하 한 가지 변경으로 판정합니다. 다음에는 구도·경로·형상을 유지하고 조명/노출 한 가지 조건의 A/B를 같은 3프레임으로 비교하는 것이 타당합니다. 긴 전체 렌더나 최종 영상 등록의 승인으로 확대하지 않습니다.

## 산출물 해시와 남은 범위

| 산출물 | 크기(B) | SHA256 |
|---|---:|---|
| frame-0001.png | 1,006,054 | `4effb3e4e70fc63703897a838c08cfe98eefc0828d057f1872b549211c945979` |
| frame-0133.png | 1,010,107 | `b4cdf5f338e83066cfcf5bd117bc53c264c9dedba333d96f4e1f3e6327fc763f` |
| frame-0288.png | 1,010,787 | `d0fefd2f50273c282bbf9a4498c62b907c9a024e26f61c91350ceed801d10b9a` |
| tracks.json | 158,545 | `9fb424be0fd212bbf3faa057097bec56c63a89e4b8ae08c524e5fd76b80fd44b` |
| render-report.json | 2,580 | `9e92e8c25fa4ffafc984cd95f64f2e7f3b3c874acb53e74b4ce8020ead2c3fd0` |
| case-0002-ww3.blend — 로컬 | 2,701,063 | `ed12b1543ca61dfb41eeca54bc43989c5744134f9230700bf981917df337f679` |

288개 위치 metadata는 **렌더 288장이나 12초 영상이 아닙니다**. 이번 범위는 대표 3장입니다. 연속 움직임·전체 mesh 충돌/가림·1080p/MP4·웹 재생/탐색·최종 빌드 통합은 미실행입니다. Release 업로드·편지 발송·커밋·제품 등록은 하지 않았습니다. 메인 변경 파일은 이 보고 하나이며 로컬 검토 자료는 `.local/pc3-render-intake/guard-02/`에 있습니다.
