# N04-D1 발표 초안 인계

작성 2026-09-21T22:08:30.177996+09:00 / pc4 장준호 / j324rst-svg / work/pc4-n04-tms-qa.
배정 [#10 comment5760793161](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/10#issuecomment-5760793161), 첫 구성 회신 [5760849411](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/10#issuecomment-5760849411).

**5장 PDF와300초 계획·대본·조작 순서·증거 대응·장애 복구 계획을 작성했습니다.** 입력 main은 e1ef36f174f9bf8f68d82a6fbc77eca77bf859cb, pc4 결과는 d7841717e8181d4f9315a20dee5099c073251019에 고정했습니다. 계획→실제실행→미실행을 구분하며 제품 변경은 없습니다.

## 결과물

- [PDF](../../presentation/pc4-draft/happycall-five-minute-draft.pdf), [안내](../../presentation/pc4-draft/README.md)
- [5장 구성·시간](../../presentation/pc4-draft/storyboard.md), [대본·조작 순서](../../presentation/pc4-draft/speaker-script.md)
- [증거 대응](../../presentation/pc4-draft/evidence-map.md), [실패 복구](../../presentation/pc4-draft/failure-recovery.md)
- [원문19입력 해시](../../presentation/pc4-draft/input-manifest.json), [기존 화면3개 원본](../../presentation/pc4-draft/assets/manifest.json)
- [생성 원본](../../presentation/pc4-draft/build_pdf.py), [레이아웃](../../presentation/pc4-draft/pdf-layout.json), [검수 JSON](../../presentation/pc4-draft/qa.json), rendered/page-1.png~5.png

## 기대/실측

| 항목 | 기대 | 실제 |
|---|---|---|
| 페이지 | 최대5 | 5/5 |
| 시간 | 총300초 이하 계획 | 30+65+95+65+45=300초, 실제 사람 리허설 미실행 |
| 파일 | 90MiB 이하 | 499,964 B / 약0.48MiB |
| 한글 | 글자 누락·대체 없음 | 맑은 고딕 regular/bold 내장·ToUnicode, 사용 글자 glyph누락0,5장 직접 시각 검토 |
| 레이아웃 | 잘림·겹침 없음 | 58개 텍스트 영역 경계와 텍스트/이미지 겹침0, 기존 화면 발췌3개 별도표시 |
| 증거 | 버전·주체·분모·미실행 구분 | main16+pc4 3 입력 원본SHA일치, 기존 이미지3개 바이트일치, 고정 GitHub 경로28개 존재 확인 |
| 안전 경계 | 제품·서버·브라우저·설치·과금0 | 모두0, 로컬 PDF 생성/Poppler 렌더만 실행 |
| 인수 | pc1 증거검토 | 결과공유 후 대기. 이슈·TODO 자체완료 안 함 |

PDF SHA-256: `ffd794cd5a55dc2fc56b4cd2498acff13e0c38260dae2bab70c8a4686a43ce3c`.

## 수정·검토·한계

초안4장 이미지와 캡션이 겹쳐 높이를 줄인 뒤 재렌더했습니다. 출처 E번호와 대응표 M/B/P 식별자 불일치를 고쳤습니다. 한글 문장 줄바꿈을 정리했고 최종 5장을 다시 확인했습니다. 초기 Python은 프로젝트 venv에 Pillow가 없어 중단했으며 설치 없이 이미 준비된 bundled Python을 사용했습니다. pdffonts 실행파일은 없어 pypdf로 실제 FontFile2와ToUnicode를 확인했습니다.

같은 pc4의 별도 읽기 검토자가19개 고정 입력 중 담당원문과 원고·실제렌더를 대조했고, 제품SHA/출력지문/실행주체/분모/미실행의 추가 오류를 발견하지 못했습니다. 이는 사람 사용성 평가나 원격 다른PC의 인수가 아닙니다.

슬라이드에 두 Bolt(저장32응답의 귀속 수정, 근거 내용카드0→2), 실제17:22:02 Goal, pc4 Q3의3/8·7/8·8/8과 원본33개를 담았습니다. 최신 e1ef36f 제품통과, 새32건live평가, 128/128의 전체 의미정확도, 처리시간·만족도, 확보점수, 실제CCTV/물류연동을 주장하지 않습니다.

남은 중요 조건을 본문에서 공개했습니다. Q3토스트P2·요청과잉철회P2, 오프라인전체0/1 BLOCKED, 원격영속저장 미연결, 최종배포·사람검증·수정CCTV브라우저·v3부모흐름 미완료/미확인입니다. 발표복구 순서는 계획이며 새실행 완료로 표시하지 않았습니다. 공식 제출·업로드·외부발송·과금0. 메인은 최종사용 빌드/자산을 확정하고300초 실제리허설·증거·제출규격을 검토해야 합니다.
