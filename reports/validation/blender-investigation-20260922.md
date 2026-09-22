# WMS 3D 공정 확인 개선 — 2026-09-22

## 문제와 변경

사용자 피드백: Blender 영상이 제품과 시연 모두에서 잠깐 지나가며, 무엇을 확인하는지 알 수 없었다.

- WMS 진입 시 피킹·출고의 상품, 수량, 단위, 토트를 먼저 비교한다.
- 큰 `3D 소터 공정 확인` 버튼으로 CASE-0002 / W-W3에 등록된 영상을 연다.
- 소터 접근·분기·슈트 이동·정지 네 버튼이 검증된 좌표 파일의 해당 공정 첫 프레임으로 이동하고 정지한다. 이번 자산의 실제 시각은 0 / 3 / 6 / 10초다.
- 현재 공정과 선택 객체를 표시하고, 데스크톱에서는 영상 옆에 피킹·출고 비교를 함께 보여 준다. 기술 메타데이터는 접을 수 있다.
- 독립 화면 검수에서 모바일 비교 카드가 첫 화면 아래로 밀리는 문제를 발견했다. 작은 화면에서는 `피킹 비스킷 · 18 EA → 출고 휴지 · 1 BOX` 핵심 비교를 영상보다 위에 추가하고 브라우저에서 재확인했다.
- 합성 영상임을 유지한다. 시각 객체와 업무 토트는 연결되지 않았으므로 사고 발생 위치나 작업자 귀책을 확정하지 않는다. EA와 BOX를 환산·차감하지 않는다.

## 실제 검증

- `node tests/e2e/cctv-phase-unit.mjs`: 288개 등록 프레임을 대상으로 36개 검사 통과. 공정 첫 프레임, 구간 경계, 좌표 없음, seek·pause·표시 상태를 확인했다. 메모리에서 공정 조건 제거(기대 3초/실측 0초), pause 제거(기대 정지/실측 재생) 변이 2개가 각각 시간·정지 검사에 잡혔다.
- `UX_API=http://127.0.0.1:8127 UX_BASE=http://127.0.0.1:3112 node tests/e2e/blender-investigation-check.mjs`: 최종 수정 후 실제 Edge/Playwright 19개 검사 통과.
- WMS와 영상 모달을 1600 / 1024 / 390px에서 확인했고 가로 넘침이 없었다. 네 공정 seek 시각 및 선택 상태, 1920×1080 영상의 12초 전체 재생 종료를 확인했다.
- 영상 열기·공정 선택·재생·닫기 전후 API 사례 데이터가 동일했고 브라우저 pageerror는 0건이었다.
- `npm --prefix apps/web run typecheck`, `git diff --check`: 통과.
- Python 3.12로 `scripts/build_deployment_bundle.py --build`: Next production export 성공, `apps/web/out/.oneflow-build.json` 생성. 배포 실행과 구분한다.
- 최초 18개 검사 증거: Git 제외 `.local/blender-investigation-1790041514053/`. 모바일 보완 후 19개 검사와 최종 화면: `.local/blender-investigation-1790041985621/`.

## 자산과 범위

- 제품 자산: `apps/web/public/demo/sorter-demo.mp4`, SHA256 `4a640c20e209bf5a43e26c3f1c5afeb41f4157af9017f04b4c3812b1990dca51`.
- 좌표: `apps/web/public/demo/sorter-demo.tracks.json`, 288프레임, 24fps.
- CASE-0002 → W-W3 → SYN-CAM-02 → CH-02 / D-02 연결을 유지한다.
- 시험은 별도 로컬 API 상태로 수행했다. 기존 사용자 API 8112 사례는 변경하지 않았다. 사람 사용성 검증, 실제 CCTV 검출, 새 AWS 배포를 완료했다는 의미는 아니다.

배포 PC는 최신 main을 받은 뒤 `reports/deployment/AI-GO_다른PC_배포인계.md` 절차로 프런트를 새로 빌드해야 한다. 기존 배포가 이 변경을 포함한다고 가정하지 않는다.
