# 프로젝트 폴더·Git 추적 점검

2026-09-21 18:03 KST, pc1/CJJ, `C:/00.프로젝트/happycall-ralphthon`의 작업본을 읽기 전용으로 점검했습니다. 파일 보관 기준은 [WORKSPACE.md](../WORKSPACE.md)입니다.

| 검사 | 실측 | 판단 |
|---|---:|---|
| Git 추적 파일 | 258개 | 해당 시각 분모, 진행 중 미추적 파일은 별도 |
| ignore 규칙에 걸리지만 이미 추적된 파일 | 0개 | `git ls-files -i -c --exclude-standard` |
| 추적 파일 10 MiB 이상 | 1개, 11,402,530 bytes | 교육 근거 원본 `docs/education/week05/week05_full.png`, 삭제·변환하지 않음 |
| `.git` 실제 파일 합계 | 25,420,294 bytes / 24.24 MiB | 원천 자료를 넣어 정리한 결과가 아님 |
| 비밀 설정·접수·예산·WAV·MP4·웹 출력 ignore | 6/6 | 실재/예상 경로를 `git check-ignore`로 대조 |
| 로컬 pre-commit hook | 없음 | 자동 훅이 동작한다고 주장하지 않음. 현재 명시 파일 점검 후 커밋 |
| skip-worktree 표시 | 0개 | Git 상태에서 변경 숨김 없음 |
| 이번 파일 이동·삭제·히스토리 재작성 | 0건 | 기존 사용자·다른 담당자 변경 보존 |

점검 재현: `git ls-files -i -c --exclude-standard`, `git count-objects -vH`, `git ls-files -v`, `git check-ignore .env.demo.local .local/cases-store.json .local/demo-usage.json apps/web/public/demo/CASE-0001.wav apps/web/public/demo/sorter-demo.mp4 apps/web/out/index.html`. Git 내부 파일 합계·추적 파일 크기 원자료는 로컬 `.local/workspace-hygiene.json`에 있습니다.

원천 30/33/36 자료는 OneDrive에 있으며 구조 조사 상세도 `.local/raw-review/`에만 둡니다. 공유 계약에는 구조·연결 조건·한계를 기록합니다. 앞으로 커밋별 범위·용량·비밀 경로를 확인하고 검증된 산출물만 공유합니다. 이번 점검은 모든 과거 커밋의 비밀값 전수 감사나 원천 내용의 개인정보 전수 검사가 아닙니다.
