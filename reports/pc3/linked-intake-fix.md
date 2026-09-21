# N03 신규 접수 원본 연결 회귀 수정

2026-09-21 / pc3 LAPTOP-U2AL73UH / mcjun86-oss.

pc1의 [#9 후속 검토](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/9#issuecomment-5758712286)에 따라, `577a31b`에서 정상 신규 웹접수까지 미등록으로 거부하던 오류를 수정했다. 기존 구현은 현재 ID만 fixture에서 찾았지만 실제 `CaseService.intake`는 새 `INT-*` ID에 명시적인 `linkedFixtureId`를 붙이고 원본 WMS·근거를 복사한다. 미디어는 복사하지 않는다.

## 수정 계약

- 정본 CASE는 기존 ID로, 신규 텍스트 접수는 유효한 `INT-*` ID와 명시적인 `linkedFixtureId`로 원본을 찾는다. 복사된 행이나 점포명만 보고 원본을 추정하지 않는다.
- 점포·문의 유형·기준시각과 주문·토트·공정시각을 대조한다. 신규 접수의 WMS와 evidence는 원본 전체와 일치해야 한다. 객체 키 순서는 무관하며 원본 배열 순서는 유지한다. 새 접수 본문·상담 제목을 원본 본문으로 덮거나 원본과 같도록 강제하지 않는다.
- 신규 접수의 원본 WMS 근거는 media가 없어도 연결할 수 있다. 수동으로 복사한 media도 신규 접수의 등록 영상으로 취급하지 않는다. replay 허용·백엔드 계약 변경은 없다.
- 화면에서 현재 접수 ID와 원본 사건 ID를 각각 보여주며, 연결 원본·유형·근거가 바뀌면 이전 공정 선택·완료 표시를 초기화한다.

## 실패 재현과 수정 후 실측

| 검사 | 기대 | 실측·증거 |
|---|---|---|
| 수정 전 CASE2 연결 INT | 정상 원본이므로 근거 허용 | 실제 미등록 오류로 **0 PASS / 1 FAIL**, [red 결과](linked-intake-red-results.json) |
| 수정 후 컴포넌트 브라우저 전체 | 기존49개+신규29개 통과 | **78/78 PASS**, [green 결과](linked-intake-browser-results.json) |
| 실제 입력 모양의 두 INT 및 pc1 `INT-MAINREVIEW` | 원본 구분·근거 저장 성공·영상 미상속 | 모두 PASS |
| 부적절한 원본·점포·유형·시각·주문·토트·원본 행/근거·ID 23개 | 버튼 비활성·callback0 | 모두 PASS |
| 수동 media 복사 및 현재 INT로 caseId 변조 | 영상 차단·정상 근거는 허용 | 두 경우 모두 PASS |
| 원본 변경 | 이전 성공 표시·선택 초기화 | PASS |
| TypeScript / production build | 타입·빌드 오류0 | 각각 exit0, 정적5페이지 생성 |
| 독립 기존 등록·SSR 반례 재검 | 관계 혼입 차단·정본 등록 유지 | `node tests/remote/pc3/registration-review.cjs` **24/24 PASS** |

RED 실행은 19:08:20 KST의 `.local/pc3-tests/2026-09-21T10-08-20-905Z/`, GREEN은 19:10:50 KST의 `.local/pc3-tests/2026-09-21T10-10-50-917Z/`에 보존했다. RED는 기존 TSX `d9f1dbe73480cc0081e927bef8bd790b5163c0980790e3595b00ea181aed67e1`, GREEN은 `6f7c00558195323f41ba5d6da43fa0b82bad2d73e7a4e59249907b436c5e7222`이며 실행 도중 소스 변경은 0개다. 기존 실제 영상 재생·bytes/SHA256 차단·오류 복구·반응형·모션 감소·저장 응답 검증도 같은 전체 실행에 포함했다.

재현: `tests/remote/pc3`에서 `node run.mjs`; 문제만 선택하면 `node run.mjs --only=linked-intake-positive-CASE-0002`. TypeScript와 build는 `apps/web`에서 각각 `node node_modules/typescript/bin/tsc --noEmit`, `node node_modules/next/dist/bin/next build`.

독립 검토는 추가 결함을 발견하지 못했다. 실제 `server/service.py`의 CaseService 클래스 메서드를 그대로 실행한 좁은 intake/patch 계약 **10/10**, 그 결과 INT 2개를 입력한 WMS·SSR·변조 반례 **36/36**도 통과했다([계약 결과](service-intake-review.json), [입력/SSR 결과](intake-source-review-results.json)). 이 PC의 Python에는 정상 서비스 import에 필요한 jsonschema/openai/filelock이 설치되지 않아, 외부 모듈 import만 제외하고 메모리 저장소 및 호출 시 실패하는 analyzer를 사용했다. 정상 서비스 import·HTTP/API 통합·서버 기동 검증이 아니다. 이 숫자는 브라우저78개와 별도의 제한된 계약 검사이며 합산하지 않는다. 재현 scratch는 `.local/pc3-tests/`에만 보존했다.

## 후보 전달과 남은 경계

pc1이 지정한 [prerelease](https://github.com/cjj0202-glitch/happycall-ralphthon/releases/tag/demo-media-20260921-wms-candidates-v1)를 결과 커밋 `577a31b8511c9bb73a1f66c5763077cd776ef6a7`에 만들었다. 합성 MP4 6개와 메타데이터 1개만 게시했으며, 원격 digest와 새 다운로드 bytes/SHA256을 각각 **7/7** 대조했다. 각 자산의 크기·해시·다운로드 증거는 [media-release.md](media-release.md) 및 [media-release.json](media-release.json)에 있다.

정본 fixture·manifest·public 설치·백엔드·main은 변경하지 않았다. 이 결과는 pc3 컴포넌트 회귀 수정과 후보 전달이며, pc1의 셸/API 연결 인수·실제 배포·전체 흐름·사람 평가·원격 TEST 왕복 완료를 뜻하지 않는다. TEST 미완료는 그대로 유지한다. 코드 애니메이션 후보를 실제 CCTV·원인/귀책 증거로 사용하지 않는다.

pc1의 origin/main `2312380` 공식 배점·실제 로그 준비 보고서를 읽었다. 실제 발견→수정→같은 조건 재검증을 증거로 연결하며, 위 통과 개수를 전체 제품 정확도나 확보 점수로 표현하지 않는다. 원본 로그나 원천자료를 외부로 올리지 않았다.
