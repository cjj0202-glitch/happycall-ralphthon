# pc3 N03 메인 인수 검토 — 수정 요청

2026-09-21. 실제 GitHub [인계 회신](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/9#issuecomment-5758639802)을 읽고 `work/pc3-n03-wms-scenes`를 fetch했습니다. 결과 SHA는 `577a31b8511c9bb73a1f66c5763077cd776ef6a7`이며 기준 `d4b4a81` 이후 **23개 추가 파일**이 배정 소유 경로 안에 있었습니다. 원격 자체 49개 브라우저·24개 등록 검사 보고는 수신했으며 메인 인수 완료로 바꾸지 않았습니다.

메인은 `.local/review-pc3-577a31b`의 detached worktree에서 결과를 분리해 읽었습니다. 앱 worktree 도구는 대화 cwd가 저장소 상위라 `Not a git repository`를 반환했으며, 실제 저장소를 명시한 `git worktree add --detach`로 검토 사본을 생성했습니다. 원래 작업 폴더와 미커밋 서버 작업은 유지했습니다.

## 정상 웹접수의 근거 연결 회귀

현재 `server/service.py`는 명시 referenceCaseId와 점포·제목·유형을 대조한 뒤 새 `INT-*` 접수에 `linkedFixtureId` 및 같은 원천 WMS/evidence를 전달합니다. 신규 접수에 replay를 허용하지 않고 media는 복사하지 않습니다.

pc3의 `canonicalCase()`는 현재 접수 id만 fixture에서 찾습니다. 메인이 실제 TSX를 TypeScript로 transpile해 `inspectWms` export를 실행했습니다. 정상 fixture와 그것을 참조한 새 접수형을 같은 함수에 넣었습니다.

| 입력 | 기대 | 실측 |
|---|---|---|
| CASE-0002 원본 | 문맥 오류 없음 | `contextError=""` |
| INT-MAINREVIEW / channel=text / linkedFixtureId=CASE-0002, 같은 점포·물류·근거, media 없음 | 기존 원천 근거 연결 허용, 미등록 영상은 차단 | `등록된 합성 사건이 아닙니다. 사건 연결을 확인하세요.` |

`Scene.link()`와 근거 버튼이 contextError로 차단되므로 신규 웹접수에서 정상 근거 연결을 못 합니다. 모델 호출·운영 접수 수정 없이 재현했습니다. 첫 probe는 기본 import 호환 설정이 빠져 fixture import가 undefined로 실패했고, `esModuleInterop=true`로 실제 default import 규칙을 맞춘 뒤 위 정/부정 대조 결과를 얻었습니다. 이는 UI 전체 검증이 아니라 함수 경계 재현입니다.

## 후속 조치와 인수 경계

같은 #9에 정상 `linkedFixtureId` 지원과 다른 점포·유형·주문·토트·시각·원본행 차단을 함께 요구했습니다. 원본 사건과 현재 접수를 구분해야 하며 미등록 자료의 자동 연결은 허용하지 않습니다. 실제 source 연결을 유지한 후속 커밋과 독립 재검증 전에는 셸에 통합하거나 N03을 인수하지 않습니다.

영상 후보는 `demo-media-20260921-wms-candidates-v1` prerelease로 합성6개와 메타데이터만 전달하도록 요청했습니다. 기존 v2 음성·정본 fixture/manifest는 유지하며 후보 공개는 설치·등록·메인 인수와 별개입니다. 영상은 코드가 만든 공정 설명이며 실제 CCTV나 AI 영상 모델 출력으로 표현하지 않습니다.
