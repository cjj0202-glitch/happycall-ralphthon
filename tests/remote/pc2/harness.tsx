import React, { useLayoutEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import CallReview from '../../../apps/web/components/CallReview';
import '../../../apps/web/app/tokens.css';
import '../../../apps/web/app/globals.css';
import type { CaseData } from '../../../apps/web/lib/types';
import { makeCase, freezeDeep } from './fixtures';

type Config = {
  caseData: CaseData;
  disabled?: boolean;
  analysisState?: 'idle' | 'loading' | 'error';
  analysisError?: string;
  transcriptMode?: 'replay' | 'demo-live';
};
declare global { interface Window { __n02: any; } }

function Harness() {
  const [config, setConfig] = useState<Config>({ caseData: freezeDeep(makeCase('comparison')), transcriptMode: 'replay' });
  const [events, setEvents] = useState<object[]>([]);
  const [retries, setRetries] = useState(0);
  const [generation, setGeneration] = useState(0);
  const [mountId, setMountId] = useState(0);
  useLayoutEffect(() => {
    window.__n02 = {
      ready: true,
      config,
      events,
      retries,
      generation,
      mount(name: string, props: Omit<Partial<Config>, 'caseData'> = {}) {
        setEvents([]); setRetries(0); setMountId(x => x + 1);
        setConfig({ caseData: freezeDeep(makeCase(name)), transcriptMode: 'replay', ...props });
        setGeneration(x => x + 1);
      },
      update(patch: Partial<Config>) {
        setConfig(old => ({ ...old, ...patch, ...(patch.caseData ? { caseData: freezeDeep(patch.caseData) } : {}) }));
        setGeneration(x => x + 1);
      },
      switchCase(name: string, override: Partial<CaseData> = {}) {
        setConfig(old => ({ ...old, caseData: freezeDeep({ ...makeCase(name), ...override }) }));
        setGeneration(x => x + 1);
      },
      snapshot: JSON.stringify(config.caseData),
    };
  });
  return <main style={{ maxWidth: 1440, margin: '0 auto', padding: 16 }}>
    <header style={{ marginBottom: 16 }}><h1>N02 통화 검토 독립 렌더</h1><p>합성 입력 · 실제 CallReview 컴포넌트 · 외부 API 없음</p></header>
    <CallReview key={mountId} {...config} onPlaybackEnded={() => setEvents(old => [...old, { caseId: config.caseData.id, audioUrl: config.caseData.audioUrl, at: Date.now() }])} onRetryAnalysis={() => setRetries(old => old + 1)} />
    <aside aria-label="검증 관측값" style={{ marginTop: 16, fontSize: 12 }}>
      <span id="ended-count">{events.length}</span> / <span id="retry-count">{retries}</span>
    </aside>
  </main>;
}

createRoot(document.getElementById('root')!).render(<Harness />);
