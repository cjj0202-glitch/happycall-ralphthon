// Execute the actual Home -> Desk -> CallReview TSX, hooks, keys and event handlers.
// Media events/ranges are explicit offline controls; this does not emulate audible playback.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
const require = createRequire(import.meta.url), root = path.resolve(import.meta.dirname, '../..');
const ts = require(path.join(root, 'apps/web/node_modules/typescript'));
const paths = { page: 'apps/web/app/page.tsx', call: 'apps/web/components/CallReview.tsx' };
const revision = process.argv.find(arg => arg.startsWith('--revision='))?.split('=')[1];
const source = Object.fromEntries(Object.entries(paths).map(([name, file]) => [name, revision
  ? execFileSync('git', ['show', `${revision}:${file}`], { cwd: root, encoding: 'utf8' })
  : fs.readFileSync(path.join(root, file), 'utf8')]));
function compile(text, imports = {}) {
  const module = { exports: {} };
  const js = ts.transpileModule(text, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  new Function('require', 'module', 'exports', js)(name => {
    if (!(name in imports)) throw new Error(`Unexpected import ${name}`);
    return imports[name];
  }, module, module.exports);
  return module.exports;
}
const workflow = compile(fs.readFileSync(path.join(root, 'apps/web/lib/workflow.ts'), 'utf8'));
const cases = [0, 1, 2].map(index => ({ id: `CASE-RATE-${index}`, status: index === 2 ? 'handed_off' : 'draft', revision: 1,
  channel: 'voice', title: `합성 통화 ${index}`, audioUrl: `/offline-${index}.wav`, type: 'missing',
  store: { id: `SYN-RATE-${index}`, name: `합성점${index}` }, sourceText: '합성 검사', selectedEvidence: [],
  transcript: [{ speaker: '경영주', text: '확인 요청', start: 2, end: 4 }] }));
const jsx = (type, props, key) => ({ type, props: props ?? {}, key });
const textOf = node => typeof node === 'string' || typeof node === 'number' ? String(node)
  : Array.isArray(node) ? node.map(textOf).join('') : node && !node.props?.['aria-hidden'] ? textOf(node.props?.children) : '';
function all(node, predicate, found = []) {
  if (!node || typeof node !== 'object') return found;
  if (Array.isArray(node)) { node.forEach(item => all(item, predicate, found)); return found; }
  if (predicate(node)) found.push(node);
  all(node.props?.children, predicate, found); return found;
}
function harness(inputs = source) {
  let active, dirty = true, tree, cursor = 0, uid = 0;
  const instances = new Map(), hosts = new Map(), drafts = new Map(), calls = [], writes = [], effects = [], completions = [];
  const remoteCases = structuredClone(cases);
  const seenInstances = new Set(), seenHosts = new Set(), typeIds = new Map();
  const listeners = new Map(), frames = new Map();
  globalThis.document = { hidden: false, addEventListener: (name, fn) => listeners.set(fn, name), removeEventListener: (name, fn) => listeners.delete(fn), getElementById: () => null };
  globalThis.window = { matchMedia: () => ({ matches: false }), addEventListener() {}, removeEventListener() {} };
  globalThis.requestAnimationFrame = fn => { frames.set(++uid, fn); return uid; };
  globalThis.cancelAnimationFrame = id => frames.delete(id);
  const same = (a, b) => a && b && a.length === b.length && a.every((v, i) => Object.is(v, b[i]));
  const slot = factory => { const i = cursor++; if (!(i in active.hooks)) active.hooks[i] = factory(); return active.hooks[i]; };
  const react = {
    useState(initial) { const owner = active; const state = slot(() => ({ value: typeof initial === 'function' ? initial() : initial })); return [state.value, value => { const next = typeof value === 'function' ? value(state.value) : value; if (!Object.is(next, state.value)) { state.value = next; if (owner.mounted) dirty = true; } }]; },
    useRef(initial) { return slot(() => ({ current: initial })); },
    useId() { return slot(() => `test-${++uid}`); },
    useCallback(fn, deps) { const state = slot(() => ({})); if (!same(state.deps, deps)) { state.deps = deps; state.value = fn; } return state.value; },
    useEffect(fn, deps) { const state = slot(() => ({})); if (!same(state.deps, deps)) { state.deps = deps; effects.push(() => { state.cleanup?.(); state.cleanup = fn(); }); } },
  };
  function useSessionDraft(key, initial) {
    if (!drafts.has(key)) drafts.set(key, structuredClone(initial));
    return { value: drafts.get(key), set(field, value) { writes.push({ key, field }); const current = drafts.get(key); current[field] = typeof value === 'function' ? value(current[field]) : value; dirty = true; }, replace(value) { writes.push({ key, replace: true }); drafts.set(key, structuredClone(value)); dirty = true; } };
  }
  const runtime = { jsx, jsxs: jsx, Fragment: 'fragment' };
  const CallReview = compile(inputs.call, { react, 'react/jsx-runtime': runtime, './CallReview.module.css': { default: new Proxy({}, { get: (_, key) => key }) } }).default;
  const Home = compile(inputs.page, { react, 'react/jsx-runtime': runtime, '@/components/CallReview': { default: CallReview },
    '@/components/NotificationStatus': { default: () => null }, '@/components/WmsScene': { default: () => null }, '@/components/TmsScene': { default: () => null },
    '@/lib/api': { ApiError: class extends Error {}, request: async (...args) => { calls.push(args); assert.equal(args[0], '/api/cases'); assert.equal(args.length, 1); return { cases: structuredClone(remoteCases) }; } },
    '@/lib/drafts': { useHasUnsavedDrafts: () => true, useSessionDraft }, '@/lib/workflow': workflow }).default;
  function render(node, location) {
    if (Array.isArray(node)) return node.map((child, i) => render(child, `${location}/${child?.key ?? i}`));
    if (!node || typeof node !== 'object') return node;
    if (typeof node.type === 'function') {
      // Unrelated role/logistics children are opaque; actual Home navigation still runs.
      if (['Owner', 'Center', 'LogisticsScene'].includes(node.type.name)) return node;
      if (!typeIds.has(node.type)) typeIds.set(node.type, ++uid);
      const key = `${location}:${typeIds.get(node.type)}:${node.key ?? ''}`;
      let instance = instances.get(key);
      if (!instance) { instance = { hooks: [], mounted: true }; instances.set(key, instance); }
      seenInstances.add(key); active = instance; cursor = 0;
      const props = node.type === CallReview ? { ...node.props, onPlaybackEnded: () => { completions.push(node.props.caseData.id); node.props.onPlaybackEnded?.(); } } : node.props;
      const result = node.type(props);
      return render(result, key);
    }
    const key = `${location}:${node.type}:${node.key ?? ''}`;
    const result = { ...node, props: { ...node.props } };
    if (node.type === 'audio') {
      seenHosts.add(key); let host = hosts.get(key);
      if (!host) { host = { currentTime: 0, duration: 10, playbackRate: 1, volume: 1, muted: false, preservesPitch: false, paused: true, ended: false, error: null,
        played: { length: 0, start() { throw new Error('No range'); }, end() { throw new Error('No range'); } }, pauseCalls: 0,
        pause() { this.paused = true; this.pauseCalls++; }, play() { this.paused = false; return Promise.resolve(); } }; hosts.set(key, host); }
      host.ref = node.props.ref; host.ref.current = host; result.media = host;
    }
    result.props.children = render(node.props.children, key); return result;
  }
  function flush() {
    let rounds = 0;
    do {
      assert.ok(++rounds < 15, 'Render must converge'); dirty = false; seenInstances.clear(); seenHosts.clear();
      tree = render(jsx(Home, {}), 'root');
      for (const [key, instance] of instances) if (!seenInstances.has(key)) { instance.mounted = false; instance.hooks.forEach(hook => hook?.cleanup?.()); instances.delete(key); }
      for (const [key, host] of hosts) if (!seenHosts.has(key)) { if (host.ref.current === host) host.ref.current = null; hosts.delete(key); }
      effects.splice(0).forEach(effect => effect());
    } while (dirty);
    return tree;
  }
  const one = predicate => { const found = all(tree, predicate); assert.equal(found.length, 1, 'One matching rendered node'); return found[0]; };
  const label = value => one(node => node.props['aria-label'] === value);
  const button = value => one(node => node.type === 'button' && textOf(node).trim() === value.trim());
  const audio = () => one(node => node.type === 'audio');
  const event = (name, target = audio(), extra = {}) => { target.props[name]({ currentTarget: target.media, nativeEvent: { isTrusted: true }, ...extra }); flush(); };
  const setRate = value => { label('통화 재생 속도').props.onChange({ target: { value: String(value) } }); flush(); };
  const ranges = (values, target = audio()) => { target.media.played = { length: values.length, start: i => values[i][0], end: i => values[i][1] }; };
  const click = value => { button(value).props.onClick({ stopPropagation() {} }); flush(); };
  const selectCase = index => { one(node => node.type === 'button' && node.props.className?.split(' ').includes('queue-open') && node.props['data-case-id'] === cases[index].id).props.onClick({ stopPropagation() {} }); flush(); };
  const playbackComplete = () => /전체 (통화 )?재생 완료/.test(textOf(one(node => node.type === 'strong' && node.props.role === 'status')));
  return { flush, audio, event, setRate, ranges, click, selectCase, one, label, playbackComplete, calls, writes, drafts, completions, remoteCases,
    async ready() { flush(); await Promise.resolve(); flush(); return this; },
    destroy() { instances.forEach(instance => instance.hooks.forEach(hook => hook?.cleanup?.())); },
  };
}
const checks = [], mutations = [];
async function test(name, action, inputs = source, record = true) {
  const app = await harness(inputs).ready();
  try { const detail = await action(app); if (record) checks.push({ name, pass: true, detail }); }
  finally { app.destroy(); }
}
const preference = app => {
  app.event('onLoadedMetadata');
  assert.equal(app.label('통화 재생 속도').props.value, 1.25);
  assert.equal(app.audio().media.playbackRate, 1.25);
  assert.equal(app.audio().media.preservesPitch, true);
  // No native ratechange is dispatched before the next case: the select must update Home now.
  app.setRate(1.5); const old = app.audio(); app.selectCase(1); app.event('onLoadedMetadata');
  assert.notEqual(app.audio().media, old.media);
  assert.equal(app.audio().media.playbackRate, 1.5);
  assert.equal(app.label('통화 재생 속도').props.value, 1.5);
  assert.equal(app.playbackComplete(), false);
  return { default: 1.25, selected: 1.5, afterCase: app.audio().media.playbackRate, nativeRateEvents: 0 };
};
const normal = rate => app => {
  app.event('onLoadedMetadata'); app.setRate(rate); app.event('onPlay');
  app.audio().media.currentTime = 10; app.audio().media.ended = true; app.ranges([[0, 10]]); app.event('onEnded');
  assert.equal(app.playbackComplete(), true);
  app.event('onEnded'); assert.equal(app.playbackComplete(), true);
  assert.deepEqual(app.completions, [cases[0].id]);
  return { rate, completion: true, callbackCount: app.completions.length };
};
const blocked = (rate, kind) => app => {
  app.event('onLoadedMetadata'); app.setRate(rate);
  if (kind !== 'no-start') app.event('onPlay');
  if (kind === 'seek') { app.audio().media.currentTime = 7; app.event('onSeeking'); }
  if (kind === 'clip') {
    const clip = app.one(node => node.type === 'button' && node.props['aria-label']?.includes('발화 1 구간 재생'));
    clip.props.onClick(); app.flush(); app.audio().media.currentTime = 4.2; app.event('onTimeUpdate');
    assert.equal(app.audio().media.currentTime, 4); assert.equal(app.audio().media.paused, true);
  }
  app.audio().media.currentTime = 10; app.audio().media.ended = kind !== 'not-ended';
  app.ranges(kind === 'gap' ? [[0, 2], [4, 10]] : kind === 'empty' ? [] : [[0, 10]]);
  app.event('onEnded', app.audio(), { nativeEvent: { isTrusted: kind !== 'untrusted' } });
  assert.equal(app.playbackComplete(), false, `${kind} must not mark full playback complete`);
  assert.equal(app.completions.length, 0);
  return { rate, kind, completion: false, callbackCount: app.completions.length };
};
await test('stored recording can be analyzed before playback', app => { assert.equal(app.one(node => node.type === 'button' && textOf(node).includes('대화록 변환 · AI 접수 정리')).props.disabled, false); assert.equal(app.playbackComplete(), false); });
await test('default and immediate Home -> Desk -> CallReview preference transfer', preference);
await test('WMS/TMS and both other roles retain selected preference', app => {
  app.event('onLoadedMetadata'); app.setRate(2);
  for (const kind of ['wms', 'tms']) {
    app.click(kind === 'wms' ? 'WMS 작업 확인 ' : 'TMS 배송 확인 ');
    const scene = app.one(node => typeof node.type === 'function' && node.type.name === 'LogisticsScene');
    assert.equal(scene.props.kind, kind); scene.props.onBack(); app.flush(); app.event('onLoadedMetadata');
    assert.equal(app.audio().media.playbackRate, 2);
  }
  for (const role of ['센터 작업대', '경영주 화면']) {
    app.click(role); assert.equal(all(app.flush(), node => node.type === 'audio').length, 0);
    app.click('상담원 작업대'); app.event('onLoadedMetadata'); assert.equal(app.audio().media.playbackRate, 2);
  }
  assert.equal(app.writes.length, 0); assert.deepEqual(app.calls, [['/api/cases']]);
  return { roundTrips: 4, rate: 2, draftWrites: 0, initialReadOnlyMockRequests: 1 };
});
await test('native ratechange, finite boundaries and invalid input recovery', app => {
  app.event('onLoadedMetadata');
  for (const value of [0.75, 1, 1.1, 1.25, 1.5, 2]) {
    app.audio().media.playbackRate = value; app.event('onRateChange');
    assert.equal(app.label('통화 재생 속도').props.value, value);
    app.selectCase(1); app.event('onLoadedMetadata'); assert.equal(app.audio().media.playbackRate, value); app.selectCase(0); app.event('onLoadedMetadata');
  }
  for (const value of [NaN, 0, Infinity, -1, 0.749, 2.001]) {
    app.setRate(value); assert.equal(app.audio().media.playbackRate, 2);
    app.audio().media.playbackRate = value; app.event('onRateChange'); assert.equal(app.audio().media.playbackRate, 2);
    assert.equal(app.label('통화 재생 속도').props.value, 2);
  }
  return { validValues: 6, invalidValuesBothPaths: 6, preservedRate: 2 };
});
await test('restart preserves preference, stale audio cannot mutate rate or completion', app => {
  app.event('onLoadedMetadata'); app.setRate(1.5); const old = app.audio();
  app.event('onPlay'); app.click('처음부터 전체 통화 재생'); app.event('onLoadedMetadata');
  assert.notEqual(app.audio().media, old.media); assert.equal(app.audio().media.playbackRate, 1.5);
  old.media.playbackRate = 2; old.media.currentTime = 10; old.media.ended = true; app.ranges([[0, 10]], old);
  for (const name of ['onRateChange', 'onPlay', 'onEnded', 'onSeeking', 'onError']) app.event(name, old);
  assert.equal(app.label('통화 재생 속도').props.value, 1.5); assert.equal(app.playbackComplete(), false);
  app.event('onCanPlay'); app.event('onPlay'); app.audio().media.currentTime = 10; app.audio().media.ended = true; app.ranges([[0, 10]]); app.event('onEnded');
  assert.equal(app.playbackComplete(), true);
  app.click('처음부터 전체 통화 재생'); assert.equal(app.playbackComplete(), true); // Existing completed-source policy.
  app.selectCase(1); app.event('onLoadedMetadata'); assert.equal(app.playbackComplete(), false); assert.equal(app.audio().media.playbackRate, 1.5);
  return { replacedAudio: true, rejectedStaleEventTypes: 5, newCaseComplete: false, completedSourceRestartPreserved: true };
});
await test('same-case source replacement resets completion and rejects old source events', async app => {
  normal(1.5)(app); const old = app.audio();
  app.remoteCases[0].audioUrl = '/offline-replaced.wav'; app.click('목록 새로고침'); await Promise.resolve(); app.flush();
  app.event('onLoadedMetadata'); assert.equal(app.audio().props.src, '/offline-replaced.wav');
  assert.equal(app.audio().media.playbackRate, 1.5); assert.equal(app.playbackComplete(), false);
  assert.notEqual(app.audio().media, old.media);
  old.media.playbackRate = 0.75;
  for (const name of ['onRateChange', 'onPlay', 'onEnded']) app.event(name, old);
  assert.equal(app.label('통화 재생 속도').props.value, 1.5); assert.equal(app.playbackComplete(), false);
  assert.equal(app.completions.length, 1);
  // Editing another case still uses its own draft, not the first case's draft object.
  app.label('요청사항').props.onChange({ target: { value: '첫 사례 미저장 내용' } }); app.flush();
  app.selectCase(1); assert.equal(app.label('요청사항').props.value, '');
  app.label('요청사항').props.onChange({ target: { value: '둘째 사례 미저장 내용' } }); app.flush();
  app.selectCase(0); assert.equal(app.label('요청사항').props.value, '첫 사례 미저장 내용');
  assert.equal(app.audio().media.playbackRate, 1.5);
  return { newSourceComplete: false, staleSourceEvents: 3, independentlyRetainedDrafts: 2, completionCallbacks: 1 };
});
for (const rate of [1.25, 1.5]) {
  await test(`normal full playback ${rate}`, normal(rate));
  for (const kind of ['seek', 'gap', 'empty', 'untrusted', 'clip', 'no-start', 'not-ended']) await test(`blocked ${rate} ${kind}`, blocked(rate, kind));
}
// Every mutant is run through a behavioral acceptance scenario, never a string-only check.
function replaceOnce(text, before, after) { const normalized = text.replace(/\r\n/g, '\n'); assert.equal(normalized.split(before).length, 2, `Unique mutation anchor: ${before}`); return normalized.replace(before, after); }
const mutantCases = [
  ['Home resets preference on case change', 'page', 'setSelected(id); setView(roleView[role]);', 'setPlaybackRate(1.25); setSelected(id); setView(roleView[role]);', preference],
  ['Home omits parent preference callback', 'page', 'onPlaybackRateChange={setPlaybackRate}', 'onPlaybackRateChange={() => {}}', preference],
  ['Desk omits preference value', 'page', 'playbackRate={playbackRate}\n        onPlaybackRateChange', 'playbackRate={1.25}\n        onPlaybackRateChange', preference],
  ['trusted-ended guard removed', 'call', '!event.nativeEvent.isTrusted || ', '', blocked(1.5, 'untrusted')],
  ['played coverage guard removed', 'call', ' || !playedWholeAudio(audio)', '', blocked(1.25, 'gap')],
  ['seeking guards weakened', 'call', 'if (disabled || selected || sought.current || !fullAttempt.current || mediaError', 'if (disabled || selected || mediaError', blocked(1.5, 'seek')],
  ['duplicate completion callback guard removed', 'call', 'if (!completeNotified.current)', 'if (true)', normal(1.25)],
];
if (!revision) for (const [name, file, before, after, scenario] of mutantCases) {
  const mutant = { ...source, [file]: replaceOnce(source[file], before, after) };
  let error; try { await test(name, scenario, mutant, false); } catch (caught) { error = caught; }
  assert.ok(error, `Mutant survived: ${name}`); assert.equal(error.code, 'ERR_ASSERTION', `Mutant must reach a behavioral assertion: ${name}`);
  mutations.push({ name, detected: true, evidence: error.message });
}
console.log(JSON.stringify({ status: 'PASS', revision: revision ?? 'working-tree', checks, checksPassed: checks.length, mutations, mutationsDetected: mutations.length,
  sourceSha256: Object.fromEntries(Object.entries(source).map(([name, value]) => [paths[name], crypto.createHash('sha256').update(value).digest('hex')])),
  paidCalls: 0, realApiCalls: 0, browserStarts: 0, serverStarts: 0, limitation: 'Offline TSX and mocked media events; not browser timing, audible clarity, or live integration proof.' }, null, 2));
