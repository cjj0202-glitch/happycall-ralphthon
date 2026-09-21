import React from 'react';
import { createRoot } from 'react-dom/client';
import { flushSync } from 'react-dom';
import WmsScene, { inspectWms, validateWmsClip } from '../../../apps/web/components/WmsScene';
import fixture from '../../../data/fixtures/cases.json';
import '../../../apps/web/app/tokens.css';
import './harness.css';

type TestCase = (typeof fixture.cases)[number];
type HarnessOptions = { rejectLink?: boolean; holdLink?: boolean };
const root = createRoot(document.getElementById('root')!);
const events: { type: string; id?: string; message?: string }[] = [];
const held: (() => void)[] = [];
let current: TestCase;
let options: HarnessOptions = {};
function render(value: string | TestCase = 'CASE-0002', nextOptions: HarnessOptions = {}) {
  const source = typeof value === 'string' ? fixture.cases.find(item => item.id === value) : value;
  if (!source) throw new Error(`Unknown fixture ${String(value)}`);
  current = structuredClone(source);
  options = nextOptions;
  events.length = 0;
  flushSync(() => root.render(<WmsScene
    caseData={current as never}
    onBack={() => events.push({ type: 'back' })}
    onLinkEvidence={async id => {
      events.push({ type: 'link-attempt', id });
      if (options.holdLink) await new Promise<void>(resolve => held.push(resolve));
      if (options.rejectLink) {
        events.push({ type: 'link-rejected', id, message: 'PC3_TEST_LINK_REJECTED' });
        throw new Error('PC3_TEST_LINK_REJECTED');
      }
      events.push({ type: 'link-resolved', id });
    }}
  />));
}

Object.assign(window, {
  pc3Harness: {
    render,
    state: () => ({ caseData: current, events: [...events], options }),
    fixture: () => structuredClone(fixture),
    validate: validateWmsClip,
    inspect: inspectWms,
    releaseLinks: () => { while (held.length) held.shift()?.(); },
  },
});
render();
