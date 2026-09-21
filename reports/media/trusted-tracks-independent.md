# CCTV 좌표 연결 독립 검토

2026-09-21, `tracks_independent_review`의 읽기 전용 실측 결과를 메인이 보존합니다. 검토자는 파일을 생성·수정하지 않았습니다. 새 정확성 결함은 재현하지 못했습니다. 실제 영상 재생·좌표 픽셀 정렬·브라우저 검수 완료를 뜻하지 않습니다.

## 고정 입력

| 파일 | 원시 SHA256 |
|---|---|
| WmsScene.tsx | d87c23f6d762271c31d386bc654ad10a15d165951488a6e93c4404d9bd6b66ef |
| CctvInspector.tsx | 92b2a68e3630344a93aa8307d15e84cbbd175dbd19dfb4e80cac7a9337bc652e |
| cctv-tracks.ts | db2d6bac5b8d353b9fb85741879cdd72442df920b3c60bb619995f7ca9ffdfd4 |
| data/fixtures/cases.json | 5edf80669f7def9d3e10ceea910086c41026ff1252fbc638b97641562f3d84f4 |
| data/demo-media-manifest.json | ae2fdf24bd168ea9af512f5e1f7bbfce26dd234d9de2dabbed35087bfa88b52c |

WMS의 후속 backLabel/readOnly props 추가는 이 고정 검토 뒤에 메인이 수행했습니다. 기존 함수 연결 회귀49/49를 다시 실행한 WMS SHA는 `1d86effc330a33386be0b4d20af140ce861ce59238bffe238803e644566dbbeb`입니다. 역할 props UI 동작은 별도 역할 검수 대상입니다.

## 독립 실행 결과

- 케이스 media에 위조 tracks/processAnchor를 주입해도 manifest 값만 채택했습니다. CH/D 교환·null 토트에 업무 토트 삽입·타사건·신규 INT·미등록 W-W2는 차단했습니다.
- 독립3fps·36프레임 입력11건: 정상1 허용, 관계/기하/시각/프레임 반례10 거부.
- 실제 verifiedBytes에 메모리 Response를 제공한4건: 정상만 허용, 같은 길이 교체·HTTP404·개행 추가는 거부. 실제 네트워크 호출은 없습니다.
- 실제 Inspector JSX/effect6상태: 미등록·등록오류·SHA오류·JSON오류·업무토트모순·정상에서 모두 video JSX 유지, 정상만 bbox 표시. 실제 재생을 뜻하지 않습니다.
- descriptor SHA·등록 해제·processAnchor·registrationError 변경4종에서 remount key가 달라졌습니다.
- 기존 step/seek14개 입력을 파일 기록 부분만 제외한 메모리 실행으로 대조했습니다. 끝 프레임 clamp 제거 변이는 기대287/실측288로 검출했습니다.
- SHA 비교 제거 변이는 같은12byte 입력을 정상구현이 거부하고 변이체가 허용했습니다.
- 실제 tsconfig 해석에서 변경3개파일 각각1회 검사 대상에 포함됐습니다.

구/신 clip 전체 비교는 label·notice 제거 때문에 처음에 달랐습니다. 재생계약12필드와 reason은 동일하고 안내는 Inspector에 별도로 유지되므로 재생 결함으로 분류하지 않았습니다. effect 검사의 첫 실행에서는 비동기 hash 완료 전 조기 관측2건이 있어 실제 verifiedBytes Promise 완료를 기다리도록 검사 어댑터를 정정했습니다. 제품 코드는 바꾸지 않았습니다.

## 재현 명령과 관측

저장소 루트의 Node와 TypeScript transpileModule로 실제 TS 함수를 로드하고 메모리 fetch를 주입했습니다. 아래 명령은 SHA 검출을 최소 재현합니다.

```javascript
const fs=require('node:fs'),crypto=require('node:crypto');
const ts=require('./apps/web/node_modules/typescript');
const source=fs.readFileSync('apps/web/lib/cctv-tracks.ts','utf8');
function compile(s){
  const m={exports:{}};
  new Function('module','exports',ts.transpileModule(s,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText)(m,m.exports);
  return m.exports;
}
const baseline=compile(source);
const mutant=compile(source.replace("if (hash !== expectedSha) throw new Error('등록 SHA256 불일치');",''));
const hash=crypto.createHash('sha256').update(Buffer.from('trusted-data')).digest('hex');
const saved=globalThis.fetch;
globalThis.fetch=async()=>new Response(Buffer.from('mutated-data'));
(async()=>{try{for(const [name,api] of [['baseline',baseline],['mutant',mutant]]){
  try{await api.verifiedBytes('/demo/test.json',12,hash,new AbortController().signal);console.log(name,'ACCEPT');}
  catch(e){console.log(name,e.message);}
}}finally{globalThis.fetch=saved;}})();
```

실측: baseline 거부(`등록 SHA256 불일치`), mutant 허용(`ACCEPT`). 전체 자체 검사 명령은 `node tests/e2e/cctv-trusted-tracks-unit.mjs`(49/49), `node tests/e2e/cctv-inspector-step-unit.mjs`(14/14)입니다. 이 자체검사 분모를 독립 검사 분모에 합치지 않습니다.

실제 public 영상은1,097,133B, SHA `e6cad3cf9f999b596a0fef3e3d463170e0d279568a31a4be49366e5383908881`이며 manifest와 일치했습니다. 현재 실제 manifest의 tracks 등록은 없습니다. 최종288프레임 영상·좌표를 함께 등록한 뒤 실제 재생/탐색/정렬을 별도 검사해야 합니다.
