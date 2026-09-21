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

## 후속 d6aa6b3 독립 재검증

2026-09-21 pc1 읽기 전용 독립 검토. detached 사본 HEAD `d6aa6b38ab18836789eb77e9034560a5e7890eef`, 변경0. 실제 main CaseService.intake를 메모리 repository로 실행한 두 신규 INT 출력에 실제 TSX inspectWms/validateWmsClip과 ReactSSR을 적용했습니다. 주 검사58/58 기대값 일치입니다.

- CASE1/2 연결 접수의 contextError 빈값, 근거 버튼1/1·4/4 활성. 현재 INT와 원본 CASE를 별도로 표시합니다.
- 동일 입력의 577a31b→d6aa6b3 대조에서 기존 거부문구→빈 오류로 바뀌었습니다.
- 같은 점포/제목/유형이라도 명시 참조가 없으면2/2 차단. 점포·주문·토트·asOf·유형·WMS/evidence 값/행/배열순서21변형×2사례42개는 오류/근거버튼0입니다.
- 객체 키순서만 역전2/2 허용. 영상 미제공/원본 복사/명시 전달/ID변경4형태×2사례×4이벤트32회는 모두 clip0입니다.
- 양성대조 CASE2/W-W3는 원본 `SYN-CCTV-CASE2-SORTER`를 반환합니다. canonical 두 사례·8이벤트의 구/신 결과는 동일합니다.
- 정상 강제거부/변조 강제허용 두 in-memory 변이체는 모두 기대값 검사에서 탈락했습니다. tsconfig 대상8파일에 WmsScene 포함을 확인했으나 이번에 전체 타입검사는 재실행하지 않았습니다.

첫 시스템 Python probe는 jsonschema 미설치로 실패해 기존 프로젝트 venv로 재실행했습니다. 첫 변이 치환은 CRLF 때문에 적용되지 않아 적용여부 검사를 추가한 뒤 재시험했습니다. 제품 결함으로 세지 않습니다.

판정: 기존 linked INT P1은 지정 함수/SSR 범위에서 해결됐습니다. **브라우저 클릭·실제 PATCH·상태 재렌더·영상 바이트·최종 셸 통합은 별도**이며 N03 전체 인수/새 영상 등록은 아직 아닙니다. 검토 TSX SHA256 `c770b4d832d42eaad74e7cc9875d2a34850f097e1943518b621fc8227590f568`.

핵심 회귀 재현(pc1 저장소, Node 경로 환경 준비 후):

```javascript
const fs=require('fs'),cp=require('child_process'),root=process.cwd(),review=root+'/.local/review-pc3-577a31b';
const ts=require(root+'/apps/web/node_modules/typescript'),fixture=require(review+'/data/fixtures/cases.json');
const source=fs.readFileSync(review+'/apps/web/components/WmsScene.tsx','utf8');
function load(text){const m={exports:{}};new Function('require','module','exports',ts.transpileModule(text,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText)(id=>id.endsWith('.css')?{}:id==='react'||id.startsWith('react/')?require(root+'/apps/web/node_modules/'+id):id.endsWith('cases.json')?fixture:require(review+'/data/demo-media-manifest.json'),m,m.exports);return m.exports;}
const before=load(cp.execFileSync('git',['show','577a31b:apps/web/components/WmsScene.tsx'],{cwd:review,encoding:'utf8'})),after=load(source);
for(const f of fixture.cases){const c=structuredClone(f);c.id='INT-MAINREVIEW';c.channel='text';c.linkedFixtureId=f.id;delete c.media;console.log(JSON.stringify({case:f.id,before:before.inspectWms(c).contextError,after:after.inspectWms(c).contextError,media:after.validateWmsClip(c,f.wms.events[2],f.media).reason}));c.wms.picking.orderId+='-ALTERED';console.log(JSON.stringify({case:f.id,alteredOrder:after.inspectWms(c).contextError}));}
```
