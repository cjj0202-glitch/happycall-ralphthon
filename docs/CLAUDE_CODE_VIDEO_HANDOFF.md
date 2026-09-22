# Claude Code 인계: 시연 영상 전체 재편집

사용자가 기존 영상 전체를 수정해 최종 마무리하도록 요청했습니다. 아래 파일은 **편집용 원본과 후보**이며 최종 제출 승인을 받은 영상이 아닙니다. 이 문서부터 읽고, 화면 흐름·속도·한국어 설명·3D 활용을 함께 수정해 주세요.

## 다운로드

[편집 자료 GitHub Release](https://github.com/cjj0202-glitch/happycall-ralphthon/releases/tag/video-edit-handoff-20260922)

| 파일 | 내용 |
|---|---|
| `video-edit-sources.zip` | 171파일. 원본 녹화 WEBM 10개, MP4 8개, WAV 20개, 자막·타임라인·검수·스크립트·Blender 원본 포함 |
| `blender-lossless-frames.zip` | Blender 1920×1080 무손실 PNG 288장, 24fps / 12초 전체 |
| `ai-go-demo-audience-candidate.mp4` | 최신 약 5분 후보. 주 편집 기준. 긴 무음·초반 3D 화면 잘림 수정 필요 |
| `ai-go-demo-dynamic-legacy-fast.mp4` | 이전 132초 버전. 사용자가 너무 빠르다고 지적한 참고본 |
| `ai-go-demo-legacy-static.mp4` | 이전 정적인 화면 위주 버전. 참고본 |
| `sorter-demo.mp4` | 현재 시스템의 Blender 12초 영상 |
| `release-assets.json` | ZIP/MP4별 정확한 크기·SHA256. ZIP 내부 `handoff-manifest.json`은 모든 항목의 크기·SHA256 |

ZIP에는 시연용 합성 자료만 넣었습니다. API 상태 저장소, 인증정보, 세션 JSONL, 사내 운영 원천데이터는 영상 재편집에 필요하지 않아 포함하지 않았습니다. 원본 녹화의 중단본·반려본도 보존했으며 `timeline.json`의 `complete`와 파일명의 `rejected`를 확인하세요.

## 바로 작업 환경 준비

기존 변경은 보존합니다. 사용자에게 받은 저장소의 실제 경로에서 실행하고, 아래 예시의 출력 경로를 다른 PC의 CJJ 경로로 바꾸어 쓰지 마세요.

```powershell
git fetch origin
# 변경 충돌과 분기를 확인한 뒤 안전한 경우에만 최신 main 반영
git pull --ff-only origin main
gh release download video-edit-handoff-20260922 --repo cjj0202-glitch/happycall-ralphthon --pattern video-edit-sources.zip --pattern release-assets.json --dir .local/video-handoff-download
Expand-Archive -LiteralPath .local/video-handoff-download/video-edit-sources.zip -DestinationPath .local/video-handoff-download/unpacked
python scripts/prepare_video_edit.py --package .local/video-handoff-download/unpacked
```

준비 도구는 모든 항목의 크기·SHA·경로를 검증한 뒤 복사합니다. 같은 내용은 건너뛰고 기존 내용이 다르면 덮어쓰지 않고 중단합니다. 복구 대상 `.local/demo-video` 원본 메타데이터는 보존하고, 새 `audience-edit-...` 폴더와 이 PC 경로로 변환한 `timeline.json`을 만듭니다. 출력의 `timeline`을 이후 명령에 사용하세요. 원본의 CJJ 절대 경로를 그대로 실행하지 마세요.

렌더 환경이 없다면 별도 가상환경을 준비할 수 있습니다.

```powershell
python -m venv .venv-video
& .venv-video/Scripts/python.exe -m pip install imageio-ffmpeg numpy
$videoFfmpeg = & .venv-video/Scripts/python.exe -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())'
& .venv-video/Scripts/python.exe scripts/render_dynamic_demo.py '<준비 도구가 반환한 timeline 경로>' --ffmpeg $videoFfmpeg --plan-only
# 편집을 마친 뒤 --plan-only를 빼서 렌더하고, 새 폴더의 verify_audience.py 실행
```

렌더러의 기본 FFmpeg 경로는 CJJ 경로이므로 다른 PC에서는 `--ffmpeg`를 지정합니다. 검증기는 새 폴더의 `ai-go-demo-audience-ko.mp4`와 새로 생성된 `dynamic-render-plan.json`을 읽습니다. 기존 후보 검수 JSON에는 이름 변경 전 MP4 이름이 남아 있으므로 새 검증 결과로 갱신해야 합니다.

무손실 Blender 프레임이 필요하면 두 번째 ZIP을 별도 폴더에 풀어 사용하세요. 첫 번째 ZIP의 `.local/video-handoff/blender/animation/case-0002-ww3.blend`, `source/`, `input/`, 등록 좌표·렌더 검수 자료를 함께 사용합니다. 과거 `run-full.py`는 당시 PC 경로·검토 hash를 고정한 실행 기록이므로 그대로 재실행하지 마세요. 현재 소스 안내는 `scripts/media_pc3/BLENDER.md`입니다.

## 편집 기준과 반드시 고칠 지점

1. 제품 작업 흐름은 통화/텍스트 접수 → AI 정리·원문 대조 → 부서 이관 → 센터 확인·회신 → 경영주 수신입니다. 메뉴 설명 나열보다 실제 클릭·스크롤·처리 결과가 보이게 합니다.
2. 최신 원본은 약 299.775초, 1600×800 실제 브라우저 녹화입니다. 사람에게 보일 화면을 추가 가속하지 말고 각 결과를 읽을 3~4.5초를 확보합니다. 필요하면 녹화 구간을 다시 촬영합니다.
3. 최신 후보의 발화 기준 최장 무음 **35.044초**를 고쳐야 합니다. 클릭 효과음은 발화가 아닙니다. 공백은 대략 86.83–103.28 / 113.60–134.83 / 228.36–263.41 / 284.85–299.77초입니다.
4. 3D 재생 버튼을 클릭하면 모달이 아래로 스크롤되어 재생 초반 상자가 화면 위로 일부 벗어납니다. 영상 재생 전에 전체 장면이 보이도록 해당 구간을 다시 녹화하거나 재구성하세요. 재생 3.33초부터 상자가 보였다는 검수 결과이지 처음부터 잘 보인다는 뜻이 아닙니다.
5. 3D는 장식이 아니라 피킹·출고의 상품/수량/단위 비교와 연결합니다. 접근(0초)·분기(3초)·슈트(6초)·정지(10초) 탐색, 객체 선택, 원본 대조를 보여 주세요. 실제 CCTV·AI 검출·작업자 과실을 확인한 것으로 표현하지 않습니다.
6. 큰 두 줄 한국어 자막과 필요한 키워드 색상, 클릭 강조, 단계 진행을 유지하되 화면 버튼·입력값을 가리지 않게 합니다. 상시 AI 더빙 푸터는 제거한 상태입니다. CLOVA 출처는 영상 내 마지막 4초 상단에만 표시했습니다.
7. 통화 2개는 UI와 음원 모두 1.25배로 일치합니다. CLOVA 해설은 원속도·원음량입니다. 음성을 임의로 늘리거나 잘라 말끝을 손상시키지 마세요.

## 보충 해설 G~J — 생성됐지만 로컬 WAV 미수령

[CLOVA 프로젝트 5161648](https://clovadubbing.naver.com/project/5161648)에 기존 A~F 6개와 보충 G~J 4개가 저장되어 있습니다. 목소리는 아나운서 조수빈, 보통 속도입니다. ZIP의 `narration/audience-20260922/supplement-pending.json`에 보충 원문·UI 원음 시각·권장 배치가 있습니다.

| 보충 | 설명 | 전체 CLOVA 음원에서 관측한 구간 | 시연 배치안 |
|---|---|---|---|
| G | 센터 회신 등록·경영주 수신 확인 | 58.47–73.30초 | 116초 |
| H | 배송 기록에서 센터 이관 | 73.30–83.92초 | 89초 |
| I | 분기·슈트 선택과 피킹·출고 비교 | 83.92–105.42초 | 234.5초 |
| J | 두 사례 마무리 | 105.42–116.49초 | 287초 |

위 시각은 UI 소수점 2자리 관측입니다. 실제 WAV를 받은 뒤 길이·무음 경계·발화를 확인하고 확정합니다. 다운로드 동작은 실행했지만 앱 저장 창을 도구로 조작하지 못했고, 사용자에게 Downloads 저장을 요청했습니다. **로컬 파일이 없으므로 이 네 WAV는 ZIP에 없습니다.** 기존 A~F 6개는 모두 포함되어 있습니다. CLOVA에서 다시 다운로드하기 전에 최근 Downloads 파일과 프로젝트 상태를 먼저 확인하세요. 마지막 다운로드 화면에서 잔여 다운로드는 1회였고 그 동작을 실행했으므로 추가 잔여분이 있다고 가정하지 마세요.

`--supplement` 렌더 옵션과 보충 음성 4개 검증은 아직 구현하지 않았습니다. 이를 구현하거나 별도의 편집 도구로 합성해 주세요. 기존 26개 음성 기준점 검사에서 새 음성 4개가 추가되면 34개로 늘리고 실제 파형을 대조합니다.

## 현재 제품·검증 상태

- 제품 UI: `129c706`에 WMS 비교·4단계 3D 탐색·모바일 핵심 비교가 반영됨. 브라우저 19개, 단위 36개, 오류 변이 2개 검사와 production build 통과.
- 영상 코드: `874f21b`, 한계 기록: `4aa2178`. 후보 전체 디코드 7,487프레임 성공, 기존 음성 26개 기준점 최대 오차 0.5ms. 이것은 영상 최종 품질 승인과 다릅니다.
- 검증 보고: `reports/validation/blender-investigation-20260922.md`, `reports/validation/audience-demo-20260922.md`.
- 배포 인계: `reports/deployment/blender-ui-handoff-20260922.md`. 이 UI를 실제 AWS에 배포한 것으로 가정하지 마세요.
- 현재 영상 자료는 replay/합성 시연입니다. 실제 유료 AI 호출을 새로 만들 필요는 없습니다. 기존 비용 원장과 사용자 시연 상태를 초기화하지 마세요.

## 마무리할 때

새 MP4를 전체 디코드하고, 모든 발화의 앞뒤 싱크·긴 무음·자막 가림·클릭 효과·3D 전체 화면·회신 수신까지 실제 프레임으로 확인합니다. 실제 사람 검수와 자동 검수를 구분하고, 새 영상과 편집 소스는 Release 자산에 올립니다. 코드·인계·검증 보고는 명시 경로만 커밋하고 푸시한 뒤 파일명·SHA·링크·남은 한계를 사용자에게 보고합니다.
