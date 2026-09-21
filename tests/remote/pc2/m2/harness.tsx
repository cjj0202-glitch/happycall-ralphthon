import React, { useEffect, useLayoutEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import CallReview from '@product/components/CallReview';
import '@product/app/tokens.css';
import '@product/app/globals.css';
import manifest from '../../../../reports/pc2/audio-m2/playback-manifest.json';

declare global { interface Window { __m2: any; } }
function Harness() {
  const [variant, setVariant] = useState<'A'|'B'>('A');
  const [disabled, setDisabled] = useState(false);
  const [complete, setComplete] = useState(false);
  const [callbacks, setCallbacks] = useState<any[]>([]);
  const [generation, setGeneration] = useState(0);
  const [mountId, setMountId] = useState(0);
  const c = manifest.cases[variant];
  useEffect(() => setComplete(false), [c.id,c.audioUrl]);
  useLayoutEffect(() => { window.__m2={ready:true,variant,disabled,complete,callbacks,generation,
    reset(v: 'A'|'B') { setVariant(v);setDisabled(false);setComplete(false);setCallbacks([]);setMountId(x=>x+1);setGeneration(x=>x+1); },
    setDisabled,
    expected:manifest.turns.map(t=>({speaker:t.speaker,text:t.text,...t[variant]})),
  }; });
  const switchVariant = (v:'A'|'B') => { setVariant(v);setGeneration(x=>x+1); };
  return <main style={{maxWidth:1440,margin:'0 auto',padding:16}}>
    <h1>N02-M2 합성 통화 A/B 검토</h1>
    <p>후보 독립 검증 · 실제 bfc8543 컴포넌트 · 사람 청취 미완료 · 외부 API 없음</p>
    <div style={{display:'flex',gap:8,flexWrap:'wrap',marginBottom:16}}>
      <button type="button" aria-pressed={variant==='A'} onClick={()=>switchVariant('A')}>A 정본 v2</button>
      <button type="button" aria-pressed={variant==='B'} onClick={()=>switchVariant('B')}>B 쉼 후보</button>
      <label><input type="checkbox" checked={disabled} onChange={e=>setDisabled(e.target.checked)}/>검증용 잠금</label>
    </div>
    <CallReview key={mountId} caseData={c as any} disabled={disabled} transcriptMode="replay"
      onPlaybackEnded={()=>{setComplete(true);setCallbacks(old=>[...old,{variant,url:c.audioUrl,at:Date.now()}]);}}
      analysisActions={<div><button id="analysis-gate" disabled={!complete||disabled}>전체 재생 후 분석 준비 확인</button><p>관측용 버튼이며 분석 API를 호출하지 않습니다.</p></div>}
      intakeEditor={<section aria-label="후보 비교 읽기 전용 접수"><h2>현재 접수 대조</h2><p>후보 {variant} · {manifest.assets[variant].duration}초</p><label>수령 수량<input readOnly value={c.intake.quantity ?? ''}/></label><p>수령 단위 {c.intake.unit} · 점포 미확인</p><p>정정 발화의 의미·원문을 바꾸지 않고 쉼 한 곳만 비교합니다.</p></section>}/>
  </main>;
}
createRoot(document.getElementById('root')!).render(<Harness/>);
