# 역할별 UI 독립 코드 재검

2026-09-21 pc1의 읽기 전용 `role_ui_independent` 검토. 실제 Home JSX·콜백을 순수 Node로 실행했으며 파일 쓰기·서버·브라우저·네트워크 호출은 0건입니다. 메인이 이 응답을 기록했습니다.

원본에서 P2 두 건을 재현했습니다. 경영주의 이관된 CASE-2에서 상담 작업대로 이동하면 CASE-0이 표시됐고, 센터 CASE-2에서 WMS를 연 뒤 지연된 저장 응답 또는 목록 갱신이 처리 중 상태를 반환하면 OTHER의 근거로 바뀌었습니다. 수정 후 같은 입력과 삭제 경계 7건을 재검했습니다.

| 입력 | 기대·실측 |
|---|---|
| 경영주 handed_off CASE-2 → 상담 | CASE-2 / handed_off |
| WMS 중 저장 응답 | CASE-2 유지 → 센터 CASE-2 / in_progress / revision5 |
| WMS 중 목록 갱신 | 위와 동일 |
| TMS 중 저장 응답 | 위와 동일 |
| TMS 중 목록 갱신 | 위와 동일 |
| 조회 중 사건 삭제 | 물류 컴포넌트 없음, 해당 접수 부재 문구 |
| 삭제 후 명시적인 목록 복귀 | center / all / selected 빈 값 / OTHER |

7/7 일치. 수정본 원시 SHA256은 page.tsx `a113465982f01ff1d8c73d288e09cdf15854b22cfebe94c90859999480e445cc`, workflow.ts `8192f69979832e241f3bfa6166572c16038b8a6860e01150511f92b3d3e8218f`입니다. Git의 줄바꿈 정규화 전 작업 사본 해시입니다.

브라우저 렌더, React effect 타이밍, 실제 서버 및 실제 draft hook은 이 재검 범위 밖입니다. 전체 초안 보존이나 TmsScene 내부 UI 인수를 이 결과로 대신하지 않습니다.

## 실제 재현 코드

저장소 루트에서 아래 JS를 Node stdin으로 실행했습니다. Node는 `C:/Users/choi8/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe`입니다. 기존 하네스의 compile/instance만 메모리에서 재사용하고 request를 지연 Promise로 바꾸어 작성자 검사에 없던 응답 순서를 주입했습니다.

```javascript
const fs=require('fs'),path=require('path'),crypto=require('crypto'),AF=Object.getPrototypeOf(async()=>{}).constructor;
let s=fs.readFileSync('tests/e2e/role-workflow-unit.mjs','utf8');s=s.slice(s.indexOf('const ts = '),s.indexOf('let app = instance()'));
s=s.replace(/request: async \(\.\.\.args\) => \{ calls\.push\(args\);.*?revision: 5 \}; \}/,"request: (...args)=>{calls.push(args);return new Promise(r=>states.resolve=r)}");
const run=`const out=[];let a=instance({role:'owner',view:'owner',selected:'CASE-2'}),t=a.render();a.child(t,'Owner').props.onDesk();t=a.render();out.push(['owner',a.child(t,'Desk').props.caseData.id,a.states.queue]);
for(const kind of ['wms','tms'])for(const mode of ['save','reload']){a=instance({role:'center',view:'center',queue:'handed_off',selected:'CASE-2',cases:[cases[2],{...cases[2],id:'OTHER'}]});t=a.render();let p;if(mode==='save')p=a.child(t,'Center').props.onSave('CASE-2',{expectedRevision:4,status:'in_progress'});a.child(t,'Center').props.onView(kind);t=a.render();if(mode==='reload')a.button(t,'목록 새로고침').props.onClick();let u={...cases[2],status:'in_progress',revision:5};a.states.resolve(mode==='save'?u:{cases:[u,{...cases[2],id:'OTHER'}]});if(p)await p;else await Promise.resolve();t=a.render();const during=a.child(t,'LogisticsScene').props.caseData.id;a.child(t,'LogisticsScene').props.onBack();t=a.render();out.push([kind,mode,during,a.child(t,'Center').props.caseData.id,a.states.role,a.states.queue,a.child(t,'Center').props.caseData.revision]);}
a=instance({role:'center',view:'wms',queue:'handed_off',selected:'CASE-2',cases:[cases[2],{...cases[2],id:'OTHER'}]});t=a.render();a.button(t,'목록 새로고침').props.onClick();a.states.resolve({cases:[{...cases[2],id:'OTHER'}]});await Promise.resolve();t=a.render();out.push(['deleted',!a.child(t,'LogisticsScene'),textOf(t).includes('선택한 접수를 찾을 수 없습니다')]);a.button(t,'접수 목록으로 돌아가기').props.onClick();t=a.render();out.push(['return',a.states.view,a.states.queue,a.states.selected,a.child(t,'Center').props.caseData.id]);console.log(JSON.stringify(out));`;
new AF('require','fs','path','crypto','root',s+run)(require,fs,path,crypto,process.cwd()).catch(e=>{console.error(e);process.exitCode=1});
```

실측 출력:

```json
[["owner","CASE-2","handed_off"],["wms","save","CASE-2","CASE-2","center","in_progress",5],["wms","reload","CASE-2","CASE-2","center","in_progress",5],["tms","save","CASE-2","CASE-2","center","in_progress",5],["tms","reload","CASE-2","CASE-2","center","in_progress",5],["deleted",true,true],["return","center","all","","OTHER"]]
```
