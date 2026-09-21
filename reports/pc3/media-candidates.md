# N03 합성 공정 영상 후보

2026-09-21 pc3 실제 생성 결과. 외부 API 호출 0건. Python Pillow 코드가 프레임을 그리고 FFmpeg H.264로 인코딩했다. 실제 CCTV나 AI 영상 모델 출력이 아니다. 원인·작업자 귀책의 증거로 사용할 수 없다.

## 실측

두 사건 × 피킹/분기/출고 = MP4 6개. 각 960×540, 18fps, 6초, 108프레임. 총 648프레임을 실제 디코딩했고, 6개 총 443,580 bytes다. 파일마다 4개 시점의 프레임이 서로 다른지 확인했다. 한국어·불일치·미확인 표시는 디코딩한 contact sheet를 직접 검수했다.

| 파일 | bytes | SHA256 |
|---|---:|---|
| case-0001-picking.mp4 | 69153 | 94b5076150c739dc13fe1d10c370c040dd8a49f4848e581cedaca98536d63cc7 |
| case-0001-sorting.mp4 | 80031 | f2b21ea3fb2ab5427a581c4e66a8625711f43ed9155fbcf36b8aad2b7757812c |
| case-0001-shipping.mp4 | 70888 | dffdf1d94c9324aaecf8a04dacf9d4701d4a356d0a8696c3c008cba307717857 |
| case-0002-picking.mp4 | 71660 | 57e8d39e9c4d0c5de2889f6d87dbb5d9cc4c56d843194b39e1e47f2012c3b9f7 |
| case-0002-sorting.mp4 | 80507 | 0482a749d028f2f1a9d6b76cda2a7ad252914fcc3051e6b005239ca23eb11414 |
| case-0002-shipping.mp4 | 71341 | ebbcca8b7eaba36efc89a79c170332c47123a490db8cb616879d97ed627eeb3c |

로컬 경로: `D:\hwana\Work\happycall-ralphthon\.local\pc3-media\`. 결과 `generation-result.json`, 시각 검수 `decoded-contact-sheet.jpg`. Git에는 스크립트·overlay·이 보고서만 포함한다.

첫 생성본에서 분기 그림의 계획/실적 텍스트가 서로 다른 갈래처럼 보일 여지가 있었다. 두 슈트를 동일한 대조행으로 수정한 뒤 전체 6개를 재생성하고 648프레임 디코딩·해시를 다시 검사했다. 두 분기와 CASE1 출고의 토트는 원본에 없어서 null/needs_review로 유지했다. 피킹·출고 토트의 연속성을 만들지 않았다.

## 메인의 통합 결정

후보는 `candidate-not-registered`, URL은 `/demo/pc3/*.mp4` 제안이다. 실제 URL 설치·Release 게시·공용 정본 등록은 수행하지 않았다. 별도 Release 후보 태그가 필요하며 pc1이 검토 후 정한다. 소스가 있으므로 같은 런타임/글꼴로 재생성하거나 검증한 원본 파일을 Release로 전달할 수 있다.

기존 CASE2 W-W3 sorter-demo는 현재 활성 등록이다. 새 분기 후보를 같은 event에 단순 추가하면 중복으로 차단된다. 기존 영상을 유지하면서 후보는 보류하거나, pc1이 검토한 **하나의 활성 등록으로 명시 교체**해야 한다. 여러 활성 영상 중 첫 행을 자동 선택하지 않는다. 해당 결정 전 pc3는 원본 등록을 바꾸지 않는다.

정본 등록 시 fixture media에 후보의 case/event/camera/occurredAt/relations/구간/sha256/bytes를 보존하고 manifest의 name은 `pc3/<파일명>`으로 등록한다. 실제 파일은 `/demo/pc3/<파일명>`에 있어야 한다. 공용 fetcher는 현재 세 자산으로 제한되어 있으므로 새 Release/manifest 확장은 pc1 소유 작업이다. 후보의 존재만으로 설치·통합이 완료됐다고 보고하지 않는다.

재현: `scripts/media_pc3/README.md`. 의존성 Pillow12.3.0, imageio-ffmpeg0.6.0, FFmpeg7.1, Malgun 글꼴 해시와 런타임은 overlay에 기록했다. `python -m unittest discover -s scripts/media_pc3 -p 'test_*.py' -v`: 8/8, 키·시각·미디어 변이20개 포함. `generate_candidates.py --verify-only`: 메타데이터·파일크기·SHA 확인 통과. 신규 생성/검증의 의존성·캐시는 D:를 사용했다.
