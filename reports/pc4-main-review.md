# pc4 TMS 독립 인수 전 검토

2026-09-21 pc1의 읽기 전용 검토 에이전트가 pc4 `1b82f1d7fad1b31545d512b28896bfcba40189ec`를 검토했습니다. 기준 main e5469aa, 19:50 이후 시작하여 20:02:01 이전 결과를 전달했습니다. 종료시각은 별도 계측하지 않았습니다. 메인이 전달받은 실행 결과를 이 문서에 보존합니다.

**신규 P0/P1은 재현되지 않아 통합 단계 진행 가능**입니다. 검토 당시 main은 이전 LogisticsView를 사용했습니다. 이후 새 컴포넌트의 메인 통합·실제 PATCH·최종 빌드 검증은 이 결과에 포함되지 않습니다.

## 실측과 범위

- 실제 `CaseService.intake()`의 두 linked INT → 정상 TMS 근거 2/1개 허용. 14개 관계 변형 → 14/14 차단. 키 순서만 바꾼 2개 → 2/2 허용. canonical 두 사례 → 2/1개 허용. INT 대조 합계18/18.
- null/빈시각은 미등록, 숫자0·시간대없음·2월30일은 invalid, 자정/UTC동치는00:00KST, 미래실적은 미채택.
- 실제 제출 TSX/CSS를 메모리 CommonJS로 transpile한 독립 loopback Chromium에서 callback 실패→연결됨0, 재시도→1(총2호출). pending 더블클릭→추가1호출. 다른 사건/같은 사건 새revision 뒤 늦은 응답→거짓연결0. 서버선택해제/내용변조→이전연결0.
- CASE2 문서폭1440/1024/390 각각viewport와 같음. 모바일 표client326/scroll658로 내부스크롤. CASE1은1440만 검사했습니다. 2사례×3폭 완료가 아닙니다.
- 키보드 Enter/Space 이전·다음 방문 선택, 타점포연결차단/문의점포허용 확인. reduced-motion 설명재생비활성, 두 실행 pageerror0.
- tsconfig 파싱8파일에 TmsScene 포함 확인. 전체타입검사·production빌드·SSR hydration·실제HTTP저장·전체6회·화면픽셀·사람사용성·실데이터연동은 이 검토에서 실행하지 않았습니다. pc4 자체39/25검사도 메인실적으로 복사하지 않았습니다.

## P2와 철회한 주장

CASE1 asOf04:30에서 예정05:00 상세는 `기준 이후 계획`인데 E-M1 카드는 `조회 기준 이후 · 현재 실적 미채택`으로 표시됩니다. 계획에 실적 문구를 쓰는 P2가 남습니다.

초기 '미래계획 연결차단=P1'은 독립 claim 검증 점수0으로 철회했습니다. HEAD^도 동일입력에서 카드를 숨겨 연결불가였으므로 신규결함으로 계산하지 않았습니다. canonical 비문의방문에 다른사건/루트가 명시되어도 비교방문으로 표시되는 현상 역시 기존동작이며 근거연결은 차단됩니다.

## 재현 명령과 출력

검토 cwd는 `.local/review-pc4-1b82f1d`입니다. `git rev-parse HEAD`는 위 SHA, `git status --short`와 `git diff --cached --name-status`는 각각0줄이었습니다. TSX의 worktree SHA256은 `CA33ACF7F77667F746E49C2EC87B07570DB48CA12F3F227EAB751942B1AF21DE`입니다(CRLF checkout; 가져온 Git blob 해시와 구분).

```powershell
@'
const fs=require('fs'),p='C:/00.프로젝트/happycall-ralphthon/apps/web/node_modules/',ts=require(p+'typescript');
const f=JSON.parse(fs.readFileSync('data/fixtures/cases.json')),m={exports:{}};
new Function('require','module','exports',ts.transpileModule(fs.readFileSync('apps/web/components/TmsScene.tsx','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText)(
 id=>id.endsWith('.css')?{}:id.includes('pc4-tms')?JSON.parse(fs.readFileSync('data/overlays/pc4-tms.json')):id.includes('fixtures/cases')?f:require(p+id),m,m.exports);
for(const asOf of ['2026-09-18T07:00:00+09:00','2026-09-18T04:30:00+09:00']){
 const c=structuredClone(f.cases[0]);c.asOf=asOf;
 console.log(JSON.stringify({asOf,relation:m.exports.tmsRelationIssue(c),evidenceIssue:m.exports.tmsEvidenceIssue(c,c.evidence[0]),planned:m.exports.tmsTime(c.evidence[0].time,c.asOf,c.tms.bizDate,true).label,card:m.exports.tmsTime(c.evidence[0].time,c.asOf,c.tms.bizDate).label}));
}
'@ | node
```

```json
{"asOf":"2026-09-18T07:00:00+09:00","relation":null,"evidenceIssue":null,"planned":"05:00 KST","card":"05:00 KST"}
{"asOf":"2026-09-18T04:30:00+09:00","relation":null,"evidenceIssue":"조회 기준 이후 또는 다른 업무일 근거는 연결할 수 없습니다.","planned":"05:00 KST · 기준 이후 계획","card":"조회 기준 이후 · 현재 실적 미채택"}
```

P1 철회 대조는 `git show HEAD^:apps/web/components/LogisticsView.tsx | Select-String -SimpleMatch 'const evidence ='`이며 기존 `atOrBefore(row.time, caseData.asOf)` 필터가 확인됐습니다.

UI하네스는 파일을 만들지 않고 PowerShell here-string→node로 메모리에 실행했습니다. 실제결과 발췌:

```json
{"name":"reject","connected":0,"calls":1}
{"name":"retry","connected":1,"calls":2}
{"name":"double_pending","calls":3,"pending":1}
{"name":"revision_unlink","connected":0,"enabled":true}
{"name":"late_other_case","caseId":"CASE-0002","connected":0,"actual":"05:10 KST"}
{"name":"same_case_revision_late","connected":0,"enabled":true,"feedback":""}
{"name":"selected_content_changed","connected":0,"firstDisabled":true}
{"name":"viewport_390","viewport":390,"document":390,"tableClient":326,"tableScroll":658}
{"name":"errors","errors":[]}
```

최초 Playwright기본Chromium1208부재와 메모리하네스UTF8헤더누락으로 실패했습니다. 실제설치1234명시·하네스헤더수정 후 위결과를 얻었고 제품파일은 수정하지 않았습니다. 검사종료 후13224 LISTEN0건, 기존8100/3100조작0, 유료호출0입니다. 전체일회성UI스크립트는 보존되지 않았으므로 이 발췌를 재사용가능한 전체테스트로 부르지 않습니다.
