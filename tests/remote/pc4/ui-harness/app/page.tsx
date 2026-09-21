'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import TmsScene from '@/components/TmsScene';
import type { CaseData } from '@/lib/types';
import fixture from '../../../../../data/fixtures/cases.json';

// Test-only host: demonstrates the assigned props without modifying pc1's shell.
export default function Harness() {
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  const [caseId, setCaseId] = useState('CASE-0001');
  const [variant, setVariant] = useState('baseline');
  const [saveMode, setSaveMode] = useState('success');
  const [saved, setSaved] = useState<string[]>([]);
  const [calls, setCalls] = useState(0);
  const [backs, setBacks] = useState(0);
  const [lastLink, setLastLink] = useState('');
  const [revision, setRevision] = useState(0);
  const pending = useRef<(() => void) | null>(null);
  const current = useRef(caseId);
  current.current = caseId;
  const data = useMemo(() => {
    const source = fixture.cases.find(c => c.id === caseId)!;
    const c = structuredClone(source) as unknown as CaseData;
    const tms = c.tms as { bizDate: string; stops: Record<string, unknown>[] };
    const stop = tms.stops.find(s => s.id === c.store.id)!;
    if (variant === 'future') {
      stop.actual = '2026-09-18T08:00:00+09:00';
      for (const e of c.evidence || []) if (e.system === 'TMS') e.time = '2026-09-18T08:00:00+09:00';
    }
    if (variant === 'cross-day') tms.bizDate = '2026-09-19';
    if (variant === 'cross-store') c.store.id = 'SYN-OTHER';
    if (variant === 'cross-case') c.id = 'CASE-OTHER';
    if (variant === 'linked-intake') {
      // CaseService.intake's public response shape, with an explicit validated reference.
      c.id = 'INT-A1B2C3D4'; c.channel = 'text'; c.synthetic = true; c.linkedFixtureId = caseId;
      c.storeId = source.store.id; c.subject = source.intake.subject; c.title = source.intake.subject;
    }
    if (variant === 'invalid-calendar') stop.actual = '2026-02-30T05:10:00+09:00';
    if (variant === 'no-timezone') stop.actual = '2026-09-18T05:10:00';
    if (variant === 'null-zero') { stop.actual = null; stop.mobileEntry = 0; stop.mobileExit = ''; }
    if (variant === 'local-plan') stop.planned = '23:55';
    if (variant === 'invalid-asof') c.asOf = 'invalid';
    if (variant === 'empty') { tms.stops = []; c.evidence = []; }
    if (variant === 'foreign-evidence') {
      const foreign = fixture.cases.find(s => s.id !== caseId)!;
      c.evidence = [...(c.evidence || []), ...structuredClone(foreign.evidence).filter(e => e.system === 'TMS')] as CaseData['evidence'];
    }
    c.selectedEvidence = saved;
    c.revision = revision;
    return c;
  }, [caseId, variant, saved, revision]);
  function selectCase(value: string) { setSaved([]); setLastLink(''); setCaseId(value); }
  return <>
    <header className="harness" aria-label="검사 하네스" data-ready={ready}>
      <strong>pc4 TMS 계약 검사 · 제품 통합 전</strong>
      <label>사례<select aria-label="검사 사례" value={caseId} onChange={e => selectCase(e.target.value)}>{fixture.cases.map(c => <option key={c.id}>{c.id}</option>)}</select></label>
      <label>반례<select aria-label="검사 반례" value={variant} onChange={e => { setSaved([]); setVariant(e.target.value); }}>{['baseline','future','cross-day','cross-store','cross-case','linked-intake','invalid-calendar','no-timezone','null-zero','local-plan','invalid-asof','empty','foreign-evidence'].map(v => <option key={v}>{v}</option>)}</select></label>
      <label>저장<select aria-label="검사 저장 모드" value={saveMode} onChange={e => setSaveMode(e.target.value)}>{['success','fail','deferred'].map(v => <option key={v}>{v}</option>)}</select></label>
      <button onClick={() => { pending.current?.(); pending.current = null; }}>지연 응답 반환</button>
      <button onClick={() => { setSaved([]); setRevision(n => n + 1); }}>서버 최신 선택 해제</button>
      <output className="harness-output" data-testid="callback-count">{calls}</output>
      <output className="harness-output" data-testid="last-link">{lastLink}</output>
      <output className="harness-output" data-testid="back-count">{backs}</output>
    </header>
    <main className="harness-main"><TmsScene caseData={data} onBack={() => setBacks(n => n + 1)} onLinkEvidence={async id => {
      const requestedCase = caseId;
      setCalls(n => n + 1);
      if (saveMode === 'fail') throw new Error('검사용 저장 실패 · 연결되지 않았습니다.');
      if (saveMode === 'deferred') await new Promise<void>(resolve => { pending.current = resolve; });
      if (current.current === requestedCase) { setSaved(old => [...new Set([...old, id])]); setLastLink(id); }
    }}/></main>
  </>;
}
