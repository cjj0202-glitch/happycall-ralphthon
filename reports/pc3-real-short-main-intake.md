# PC3 실제 72프레임 수신검사 독립 인수 검토

2026-09-21 22:40 KST · 검토 PC: pc1 / CJJ · 대상: N03-M3 실제 패키지 수신검사

PC3의 **수신검사 범위는 인수 가능**합니다. 고정 결과 커밋 `c7fd1c06a4bd167d7d02fc1b3c9869193eec76d2`의 보고서 9개를 메인의 기존 ZIP·72 PNG·MP4·좌표·실행기록과 대조했으며, 인수를 막는 불일치는 발견되지 않았습니다. 이는 최종 CCTV 품질, 제품 등록, 전체 N03 완료 판정이 아닙니다.

## 비교 대상과 실행

- 메인 착수 HEAD: `1d517cb`. 다른 작업자의 미커밋 변경을 보존했습니다.
- PC3 생성 소스: `33fa0e4edeb88c0d4ad5e9cc0194ffc7e96cebcd`.
- PC3 검사기: `9be72090021c550c6e27746469f926baf57fea2e`.
- PC3 결과: 위 `c7fd1c0`의 `reports/pc3/render-package-real-*` 9개 Git blob. 브랜치 최신 파일 대신 고정 SHA를 사용했습니다.
- 비교 원본: `.local/pc3-render-intake/short-33fa0e4-01/`, `.local/media-releases/wms-short-33fa0e4-20260921/`, [기존 영상 검사](media/pc3-short-video-review.md).

```powershell
git fetch origin work/pc3-n03-wms-scenes
git ls-tree -r --name-only c7fd1c06a4bd167d7d02fc1b3c9869193eec76d2 -- reports/pc3
.venv/Scripts/python.exe -X utf8 .local/pc3-real-review/audit.py
```

fetch는 한 번 수행했고, 고정 Git blob은 Python `subprocess.check_output(['git','show', '<SHA>:<path>'])`의 원 바이트로 저장했습니다. 실제 비교 출력은 `count=538, passed=538, failed=[]`, exit 0입니다. 이 숫자는 파일·값 비교 관측 수이며 538개 제품 기능 테스트를 뜻하지 않습니다. 같은 PNG의 바이트·선언·시각 등 서로 다른 비교도 포함합니다. 바이트 1개 추가와 프레임 시작 번호 변경을 메모리에서 구성한 음성 대조 2건도 차이를 검출했습니다.

## 기대와 실측

| 항목 | 메인 독립 대조 결과 | 판정 범위 |
|---|---|---|
| Release 후보 3개 | ZIP 82,333,801B / 기대 JSON 2,067B / MP4 544,733B, 3/3 SHA·바이트 일치 | 기존 메인 파일과 PC3 수신 선언의 동일성 |
| ZIP | 121 엔트리, 비압축 85,483,552B. 모든 엔트리를 읽으며 CRC 검사 | 새 다운로드·원격 파일 재관측 아님 |
| 패키지 선언 | 120/120 선언 SHA·바이트가 ZIP 내용과 일치, 제외된 1개는 `package-files.json` 자신 | 자신도 ZIP의 고정 SHA와 별도 manifest SHA로 검증 |
| PC3 archive 보고 | 120/120 행이 원 ZIP manifest와 일치, 경로 집합 동일 | 보고서 선언이 실제 발송 ZIP을 지칭함 |
| strict 검사 입력 | 75/75 SHA·바이트가 메인 `short/` 원본과 일치 | render-report·tracks·blend 3개 + PNG 72개 |
| PNG 번호·시각 | 73~144 연속 72개, 경과초 `(frame-1)/24` 모두 일치 | 새 픽셀 디코딩이나 시각 품질 평가는 수행하지 않음 |
| 생성 소스 | 생성기와 의존 4개, 5/5 고정 33fa Git blob 해시·크기 일치 | 실행 출처의 암호학적 서명 인증은 아님 |
| 검사기·기대값 | 검사기 29,547B/SHA 일치. 원 기대값에서 바뀐 키는 `fixture`, `mode` 2개뿐 | 입력을 맞추기 위한 계약 완화 없음 |
| 외부 실행 증거 | PC3가 참조한 15/15 파일 해시·바이트가 메인 원본과 일치 | PC3의 24/24 외부기록 비교를 새 Blender 실행으로 세지 않음 |
| 런타임 주요 값 | 4.5.14 LTS/EEVEE/FIXED 2/96 samples/4 shadow rays, core 268+환경 48=316 일치 | 저장된 독립 readback 대조 |
| 프로세스 기록 | short exit 0, 896.578초 / prepare exit 0, 5.187초 일치 | 지금 실행 중인 프로세스라는 주장이 아님 |
| MP4 디코드 | PC3 14/14 기술 검사 보고. 72개 PTS가 메인 기존 디코드 결과와 72/72 일치 | 이번 검토에서 새 FFmpeg 실행은 하지 않음 |
| 좌표·식별 | 288행, CASE-0002/W-W3/SYN-CAM-02, CH-02/D-02, 업무 토트 null, occlusionTested=false 일치 | 실제 업무 토트·귀책 판정 불가 |
| 원본 보존 | PC3의 3 다운로드+121 raw+75 strict=199 산식과 대상 구분 일치 | PC3 디스크의 현재 mtime·199개 재관측은 하지 못함 |

고정 해시는 ZIP `10fa9981105eaecfe07a5c715d19c3e7bd932f8aa4b8bb375f93447f73f80891`, MP4 `21ac21351803125334deba303fd249909774aba98058bc787e38121058f70ccf`, tracks `9fb424be0fd212bbf3faa057097bec56c63a89e4b8ae08c524e5fd76b80fd44b`입니다.

PC3의 strict 복사본에서 제외한 `independent-scene-readback.json`은 원본 `short/` 76개 중 추가 1개입니다. 전체 raw 121개 중 strict 75개 밖의 46개를 삭제했다는 뜻이 아닙니다. 해당 readback을 포함한 외부 기록의 바이트가 메인 원본과 일치합니다.

## 실패·회복과 남은 범위

첫 래퍼는 검사기 실행 전 `KeyError: 'dependencies'`로 실패했습니다. 제출한 수정 스크립트는 실제 필드 `sourceDependencies`를 읽으며, `--reuse-verified-raw` 경로에서 같은 ZIP과 이미 푼 모든 바이트를 재검사한 뒤 별도 strict 사본을 만듭니다. 검사기나 수신 입력 변경으로 통과시킨 흔적은 없습니다. 최초 실패 스크립트의 보존·mtime은 PC3 보고의 범위이며 메인에서 해당 로컬 파일을 직접 관찰하지는 못했습니다. 공개 수정 스크립트는 제출 SHA와 일치합니다.

검사기 결과는 `PASS_WITH_PENDING`, failures 0이며 다음 6개를 그대로 유지합니다: `FIXTURE_RUNTIME_UNVERIFIED`, `THREADS_RUNTIME_UNVERIFIED`, `PIXEL_DECODE_NOT_RUN`, `VIDEO_DECODE_NOT_RUN`, `VISUAL_REVIEW_PENDING`, `AUTHENTICITY_UNVERIFIED`. PC1의 별도 런타임 기록과 PC3의 별도 영상 디코드가 있다고 해서 원 검사기 필드를 통과로 덮지 않았습니다.

짧은 영상은 원 장면 `[3,6)`초를 영상 `[0,3)`초로 옮긴 후보입니다. 시간 차이 +3초, `trackBinding=null`, `full288TracksRegisteredToClip=false`를 확인했습니다. 288행 좌표를 짧은 클립의 0초에 그대로 연결하면 안 됩니다.

후속 작업은 전체 288프레임·1080p 결과의 품질 확인과 동일 영상에 맞는 좌표 등록·실제 플레이어 검수입니다. 이번 검토는 새 렌더·디코드·브라우저·서버·다운로드·배포·발송·커밋을 수행하지 않았습니다. TEST 왕복과 전체 N03은 여전히 미완료입니다.

로컬 재현 자료는 `.local/pc3-real-review/audit.py` 및 `main-comparison.json`입니다. 검사 스크립트 SHA는 `42f53ba521f67d1dfc0fd7aa5e4e75d835e9ffeca55af21da720737a7bbbb440`, 22:40:50 결과 JSON SHA는 `abee0479396773d19a5bd6a1af5f34a2c76ed891dc4d00e2986598a33e5420a1`입니다. raw·영상·로컬 실행자료는 Git에 추가하지 않았습니다.
