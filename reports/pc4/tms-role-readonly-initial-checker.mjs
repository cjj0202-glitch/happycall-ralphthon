// Execute actual TmsScene JSX and link closures in memory. No React DOM, server or network.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';

const root = path.resolve(import.meta.dirname, '../..');
const require = createRequire(import.meta.url);
const ts = require(path.join(root, 'apps/web/node_modules/typescript'));
const pinnedMain = 'ed2b188de31091a71f1596f50961239d02813107';
const args = process.argv.slice(2), refIndex = args.indexOf('--source-ref');
const sourceRef = refIndex < 0 ? null : args[refIndex + 1];
if (refIndex >= 0 && (!sourceRef || sourceRef.startsWith('--'))) throw new Error('--source-ref needs a local Git revision');
const readAt = (name, ref = sourceRef) => ref ? execFileSync('git', ['show', `${ref}:${name}`], { cwd: root, encoding: 'utf8' }) : fs.readFileSync(path.join(root, name), 'utf8');
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const sourcePath = 'apps/web/components/TmsScene.tsx';
const source = readAt(sourcePath), fixtureText = readAt('data/fixtures/cases.json'), overlayText = readAt('data/overlays/pc4-tms.json');
const fixtures = JSON.parse(fixtureText).cases;
const report = {
  task: 'N04-U1', scope: 'actual TypeScript component JSX/callback execution with controlled hooks; not browser or build acceptance',
  startedAt: new Date().toISOString(), sourceRef: sourceRef || 'working-tree', baselineExpectedToFail: args.includes('--baseline'),
  sources: { component: sha(source), fixtures: sha(fixtureText), overlay: sha(overlayText), checker: sha(fs.readFileSync(import.meta.filename)) },
  serverStarts: 0, browserStarts: 0, networkCalls: 0, paidCalls: 0,
  limitations: ['Deterministic hook harness executes actual effects and keyed cleanup. matchMedia is explicitly controlled as false; animation timers, DOM focus, layout, native details expansion and browser event dispatch are NOT_RUN.', 'onLinkEvidence is a controlled callback boundary, not an API or repository. Direct invocation intentionally bypasses HTML disabled behavior.', 'Back label and callback are checked inside this component. Parent center navigation integration is NOT_RUN.'],
  checks: [], mutations: []
};
const compile = text => ts.transpileModule(text, { compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true }, reportDiagnostics: true });
let apiClassSource = '';
if (/import\s*\{[^}]*\bApiError\b[^}]*\}\s*from\s*['"]@\/lib\/api['"]/.test(source)) {
  let apiText = readAt('apps/web/lib/api.ts'), apiRef = sourceRef || 'working-tree';
  let apiAst = ts.createSourceFile('api.ts', apiText, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  let declaration = apiAst.statements.find(node => ts.isClassDeclaration(node) && node.name?.text === 'ApiError');
  if (!declaration) {
    apiText = readAt('apps/web/lib/api.ts', pinnedMain); apiRef = pinnedMain;
    apiAst = ts.createSourceFile('api.ts', apiText, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
    declaration = apiAst.statements.find(node => ts.isClassDeclaration(node) && node.name?.text === 'ApiError');
    report.limitations.push('Working-tree ApiError import is absent: actual pinned-main class is used explicitly. Working-tree import/typecheck parity is NOT_RUN here; do not count this as a successful app build.');
  }
  assert.ok(declaration, 'Actual pinned ApiError declaration must exist; no substitute error-class mock');
  apiClassSource = declaration.getText(apiAst);
  report.apiDependency = { mode: 'actual-class-AST-extraction', ref: apiRef, fileSha256: sha(apiText), classSha256: sha(apiClassSource), workingTreeParity: apiRef === 'working-tree' };
} else report.apiDependency = { mode: 'not-imported-by-selected-component' };

function renderer(text, props) {
  let hooks = [], cursor = 0, tree, hold = false, release, reject, previousKey;
  const calls = [], backs = [], lifecycle = { mounts: 0, cleanups: 0 };
  const deferred = new Promise((resolve, fail) => { release = resolve; reject = fail; });
  const react = {
    useState(initial) { const i = cursor++, instance = hooks; if (!(i in instance)) instance[i] = typeof initial === 'function' ? initial() : initial; return [instance[i], next => { instance[i] = typeof next === 'function' ? next(instance[i]) : next; }]; },
    useRef(initial) { const i = cursor++; if (!(i in hooks)) hooks[i] = { current: initial }; return hooks[i]; },
    useId() { const i = cursor++; if (!(i in hooks)) hooks[i] = `pure-tms-${i}`; return hooks[i]; },
    useEffect(callback, dependencies) { const i = cursor++, old = hooks[i]; if (!old || !dependencies || dependencies.some((item, index) => !Object.is(item, old.dependencies?.[index])) || dependencies.length !== old.dependencies?.length) hooks[i] = { effect: true, callback, dependencies, cleanup: old?.cleanup, run: true }; }
  };
  const jsx = (type, props, key) => ({ type, props: props || {}, key });
  const exports = {}, sandbox = { module: { exports }, exports, Error, Promise, console: { log() {}, warn() {}, error() {} }, window: { matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {} }), setInterval() { throw new Error('Animation timer is outside pure checker scope'); }, clearInterval() { throw new Error('Animation timer is outside pure checker scope'); } } };
  let apiExports = {};
  const context = vm.createContext(sandbox);
  if (apiClassSource) {
    const apiModule = { exports: {} };
    const apiContext = vm.createContext({ module: apiModule, exports: apiModule.exports, Error });
    vm.runInContext(compile(apiClassSource).outputText, apiContext, { timeout: 1000 }); apiExports = apiModule.exports;
  }
  sandbox.require = name => {
    if (name === 'react') return react;
    if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx, Fragment: 'fragment' };
    if (name.endsWith('.css')) return new Proxy({}, { get: (_, key) => String(key) });
    if (name.endsWith('pc4-tms.json')) return JSON.parse(overlayText);
    if (name.endsWith('fixtures/cases.json')) return JSON.parse(fixtureText);
    if (name === '@/lib/api' && apiClassSource) return apiExports;
    throw new Error(`Unapproved dependency in pure checker: ${name}`);
  };
  const compiled = compile(text);
  assert.equal((compiled.diagnostics || []).filter(item => item.category === ts.DiagnosticCategory.Error).length, 0, 'Memory transpilation diagnostics');
  vm.runInContext(compiled.outputText, context, { timeout: 1000 });
  let completeProps = deepFreeze({ ...props, onLinkEvidence: id => { calls.push(id); return hold ? deferred : Promise.resolve(); }, onBack: () => backs.push('back') });
  function expand(node) {
    if (Array.isArray(node)) return node.map(expand);
    if (!node || typeof node !== 'object') return node;
    if (typeof node.type === 'function') return expand(node.type(node.props));
    return { ...node, props: { ...node.props, children: expand(node.props.children) } };
  }
  const render = () => {
    cursor = 0; const rootNode = exports.default(completeProps), key = rootNode.key ?? 'unkeyed';
    if (previousKey !== undefined && previousKey !== key) { for (const hook of hooks) if (hook?.effect && typeof hook.cleanup === 'function') { hook.cleanup(); lifecycle.cleanups++; } hooks = []; }
    previousKey = key; cursor = 0; tree = expand(rootNode);
    for (const hook of hooks) if (hook?.effect && hook.run) { if (typeof hook.cleanup === 'function') { hook.cleanup(); lifecycle.cleanups++; } hook.cleanup = hook.callback(); hook.run = false; lifecycle.mounts++; }
    return tree;
  };
  render();
  return { get tree() { return tree; }, calls, backs, render, lifecycle, updateProps(next) { completeProps = deepFreeze({ ...completeProps, ...next }); render(); }, setPending() { hold = true; }, async finishPending(fail = false) { hold = false; if (fail) reject(new Error('Controlled delayed rejection')); else release(); await settle(); render(); }, async invoke(node) { assert.equal(typeof node?.props.onClick, 'function'); node.props.onClick(); await settle(); render(); }, async change(node, value) { assert.equal(typeof node?.props.onChange, 'function'); node.props.onChange({ target: { value } }); await settle(); render(); } };
}
function deepFreeze(value) { if (value && typeof value === 'object' && !Object.isFrozen(value)) { Object.freeze(value); for (const child of Object.values(value)) deepFreeze(child); } return value; }
async function settle() { await Promise.resolve(); await Promise.resolve(); await Promise.resolve(); }
function nodes(tree, predicate, found = []) { if (Array.isArray(tree)) tree.forEach(item => nodes(item, predicate, found)); else if (tree && typeof tree === 'object') { if (predicate(tree)) found.push(tree); nodes(tree.props?.children, predicate, found); } return found; }
function textOf(node) { if (Array.isArray(node)) return node.map(textOf).join(' '); if (node === null || node === undefined || typeof node === 'boolean') return ''; return typeof node === 'object' ? textOf(node.props?.children) : String(node); }
function one(tree, predicate, label) { const matches = nodes(tree, predicate); assert.equal(matches.length, 1, `${label}: actual JSX selection must be unique`); return matches[0]; }
function evidenceButton(r, evidence) { const article = one(r.tree, node => node.type === 'article' && nodes(node, child => child.type === 'h3' && textOf(child) === evidence.label).length === 1, 'actual evidence article'); return one(article, node => node.type === 'button', 'actual evidence button'); }
function readOnlyNotice(r, status) { const notices = nodes(r.tree, node => node.props.role === 'status').map(textOf).filter(value => /조회만/.test(value)); assert.equal(notices.length, 1, 'Exactly one read-only status notice is rendered'); const prefix = { handed_off: '센터 전달', in_progress: '센터 조사 중', closed: '처리완료' }[status]; assert.equal(notices[0], `${prefix} · 이관된 접수의 근거는 조회만 할 수 있습니다.`); return notices[0]; }
const caseData = (status, changes = {}) => ({ ...structuredClone(fixtures.find(item => item.id === 'CASE-0001')), status, ...changes });
const evidenceFor = c => c.evidence.find(item => item.system === 'TMS');
async function suite(text) {
  const checks = [];
  async function test(name, run) { try { const detail = await run(); checks.push({ name, status: 'PASS', detail }); } catch (error) { checks.push({ name, status: 'FAIL', error: error.message }); } }
  for (const status of ['draft', 'review']) await test(`${status}: real JSX enabled and actual link allows one callback`, async () => {
    const c = caseData(status), r = renderer(text, { caseData: c }), item = evidenceFor(c), button = evidenceButton(r, item);
    assert.equal(button.props.disabled, false); await r.invoke(button); assert.deepEqual(r.calls, [item.id]); assert.equal(textOf(evidenceButton(r, item)), '연결됨'); return { disabled: false, callbackIds: r.calls, linkedLabel: '연결됨' };
  });
  for (const status of ['handed_off', 'in_progress', 'closed']) {
    await test(`${status}: actual JSX disables link`, async () => { const c = caseData(status), r = renderer(text, { caseData: c }); assert.equal(evidenceButton(r, evidenceFor(c)).props.disabled, true); return { disabled: true }; });
    await test(`${status}: direct actual onClick cannot invoke link callback`, async () => { const c = caseData(status), r = renderer(text, { caseData: c }); await r.invoke(evidenceButton(r, evidenceFor(c))); assert.deepEqual(r.calls, []); return { bypassDisabled: true, callbackCalls: 0 }; });
    await test(`${status}: visible role reason and existing linked marker retained`, async () => {
      const c = caseData(status), item = evidenceFor(c); c.selectedEvidence = [item.id]; const r = renderer(text, { caseData: c });
      assert.equal(textOf(evidenceButton(r, item)), '연결됨'); assert.equal(evidenceButton(r, item).props.disabled, true);
      const notice = readOnlyNotice(r, status);
      await r.invoke(evidenceButton(r, item)); assert.deepEqual(r.calls, []); return { linkedLabel: '연결됨', notice, completedReason: status === 'closed' };
    });
    await test(`${status}: read-only notice survives zero visits and evidence`, async () => { const c = caseData(status); c.tms.stops = []; c.evidence = []; const r = renderer(text, { caseData: c }); const notice = readOnlyNotice(r, status); assert.equal(nodes(r.tree, node => node.props['aria-label'] === '방문 선택').length, 0); return { notice, visits: 0, evidence: 0 }; });
  }
  await test('comparison visit: disabled plus direct callback guard', async () => {
    const c = caseData('review'), r = renderer(text, { caseData: c }); const list = one(r.tree, node => node.props['aria-label'] === '방문 선택', 'visit list');
    const other = nodes(list, node => node.type === 'button').find(button => button.props['aria-pressed'] === false); assert.ok(other); await r.invoke(other);
    const button = evidenceButton(r, evidenceFor(c)); assert.equal(button.props.disabled, true); await r.invoke(button); assert.deepEqual(r.calls, []); return { callbackCalls: 0 };
  });
  await test('invalid relation: disabled plus direct callback guard', async () => {
    const c = caseData('review'); c.tms.routeId = 'SYN-OTHER-ROUTE'; const r = renderer(text, { caseData: c }), button = evidenceButton(r, evidenceFor(c));
    assert.equal(button.props.disabled, true); await r.invoke(button); assert.deepEqual(r.calls, []); return { callbackCalls: 0 };
  });
  await test('already linked: preserves label and blocks duplicate callback', async () => {
    const c = caseData('review'), item = evidenceFor(c); c.selectedEvidence = [item.id]; const r = renderer(text, { caseData: c }), button = evidenceButton(r, item);
    assert.equal(textOf(button), '연결됨'); assert.equal(button.props.disabled, true); await r.invoke(button); assert.deepEqual(r.calls, []); return { callbackCalls: 0 };
  });
  await test('pending: disabled and repeated stale/current callbacks remain single-flight', async () => {
    const c = caseData('review'), r = renderer(text, { caseData: c }), item = evidenceFor(c), stale = evidenceButton(r, item); r.setPending();
    await r.invoke(stale); const pending = evidenceButton(r, item); assert.equal(pending.props.disabled, true); assert.match(textOf(pending), /연결 중/);
    await r.invoke(stale); await r.invoke(pending); assert.deepEqual(r.calls, [item.id]); await r.finishPending(); assert.equal(textOf(evidenceButton(r, item)), '연결됨'); return { callbackCalls: 1, linkedAfterSettlement: true };
  });
  for (const status of ['handed_off', 'in_progress', 'closed']) for (const outcome of ['resolve', 'reject']) await test(`${status}: status-only transition isolates delayed ${outcome} and stale callback`, async () => {
    const c = caseData('review'), r = renderer(text, { caseData: c }), item = evidenceFor(c), stale = evidenceButton(r, item); r.setPending(); await r.invoke(stale);
    r.updateProps({ caseData: { ...structuredClone(c), status } }); assert.equal(evidenceButton(r, item).props.disabled, true); readOnlyNotice(r, status);
    await r.finishPending(outcome === 'reject'); assert.equal(textOf(evidenceButton(r, item)), '이 근거 연결'); assert.equal(nodes(r.tree, node => node.props.role === 'alert').length, 0);
    const messages = nodes(r.tree, node => node.props.role === 'status').map(textOf).join(' '); assert.ok(!messages.includes('상담에 연결했습니다.')); await r.invoke(stale); assert.deepEqual(r.calls, [item.id]);
    assert.ok(r.lifecycle.cleanups > 0, 'Actual keyed effect cleanup runs for status-only transition'); return { sameCaseId: c.id, sameRevision: c.revision ?? null, outcome, callbackCalls: 1, lifecycle: r.lifecycle };
  });
  await test('read-only to review: valid evidence becomes editable', async () => { const c = caseData('closed'), r = renderer(text, { caseData: c }), item = evidenceFor(c); assert.equal(evidenceButton(r, item).props.disabled, true); r.updateProps({ caseData: { ...structuredClone(c), status: 'review' } }); const button = evidenceButton(r, item); assert.equal(button.props.disabled, false); await r.invoke(button); assert.deepEqual(r.calls, [item.id]); return { callbackCalls: 1 }; });
  await test('read-only query controls: visits, sorting, details markup and back remain usable; frozen props unchanged', async () => {
    const c = caseData('closed'), before = JSON.stringify(c), r = renderer(text, { caseData: c }); const list = one(r.tree, node => node.props['aria-label'] === '방문 선택', 'visit list');
    const other = nodes(list, node => node.type === 'button').find(button => button.props['aria-pressed'] === false); assert.ok(other); assert.notEqual(other.props.disabled, true); await r.invoke(other);
    const detail = one(r.tree, node => node.props['aria-label'] === '선택 방문 상세', 'visit detail'); assert.ok(textOf(detail).includes('비교 방문')); const nav = nodes(detail, node => node.type === 'button' && /이전 방문|다음 방문/.test(textOf(node))).find(button => !button.props.disabled); assert.ok(nav); await r.invoke(nav);
    const sort = one(r.tree, node => node.type === 'select', 'sort select'); assert.notEqual(sort.props.disabled, true); await r.change(sort, 'actual'); assert.equal(one(r.tree, node => node.type === 'select', 'sort select').props.value, 'actual');
    assert.ok(nodes(r.tree, node => node.type === 'details' && nodes(node, child => child.type === 'summary').length > 0).length > 0, 'Native source details and summary markup retained');
    const header = one(r.tree, node => node.type === 'header', 'header'); await r.invoke(one(header, node => node.type === 'button', 'back')); assert.deepEqual(r.backs, ['back']); assert.deepEqual(r.calls, []); assert.equal(JSON.stringify(c), before); assert.ok(Object.isFrozen(c.tms)); return { propsDeepFrozen: true, visitSelection: true, previousOrNext: true, sort: 'actual', detailsMarkup: true, nativeDetailsExpansion: 'NOT_RUN', callbackCalls: 0, backCalls: 1 };
  });
  for (const [label, supplied] of [['상담으로 돌아가기', undefined], ['센터 업무로 돌아가기', '센터 업무로 돌아가기']]) await test(`back action: ${label}`, async () => {
    const r = renderer(text, { caseData: caseData('review'), ...(supplied ? { backLabel: supplied } : {}) });
    const header = one(r.tree, node => node.type === 'header', 'scene header'); const button = one(header, node => node.type === 'button', 'back button');
    assert.ok(textOf(button).includes(label)); await r.invoke(button); assert.deepEqual(r.backs, ['back']); assert.deepEqual(r.calls, []); return { label: textOf(button), callbackCalls: 1 };
  });
  return checks;
}
function mutations(text) {
  const ast = ts.createSourceFile(sourcePath, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX), guards = [], disabled = [];
  const replaceReadOnly = (node, edits) => { if (ts.isIdentifier(node) && node.text === 'readOnly') edits.push([node.getStart(ast), node.end, 'false']); else ts.forEachChild(node, child => replaceReadOnly(child, edits)); };
  function visit(node) {
    if (ts.isFunctionDeclaration(node) && node.name?.text === 'link') for (const statement of node.body.statements) if (ts.isIfStatement(statement)) replaceReadOnly(statement.expression, guards);
    if (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) {
      const attrs = node.attributes.properties, click = attrs.find(item => ts.isJsxAttribute(item) && item.name.getText(ast) === 'onClick');
      if (click?.initializer?.getText(ast).includes('link(item)')) { const attribute = attrs.find(item => ts.isJsxAttribute(item) && item.name.getText(ast) === 'disabled'); if (attribute?.initializer) replaceReadOnly(attribute.initializer, disabled); }
    }
    ts.forEachChild(node, visit);
  }
  visit(ast);
  const apply = edits => [...edits].sort((a, b) => b[0] - a[0]).reduce((value, [start, end, replacement]) => value.slice(0, start) + replacement + value.slice(end), text);
  return [['remove-readOnly-only-from-actual-link-guard', guards], ['remove-readOnly-only-from-actual-button-disabled', disabled]].map(([name, edits]) => ({ name, edits: edits.length, source: apply(edits) }));
}
try {
  report.checks = await suite(source);
  const failed = report.checks.filter(item => item.status === 'FAIL');
  for (const mutant of mutations(source)) {
    if (failed.length || !mutant.edits) { report.mutations.push({ name: mutant.name, status: 'NOT_RUN', reason: failed.length ? 'Baseline functional checks fail; do not claim mutation detection from an already failing baseline.' : 'No actual source guard matched', edits: mutant.edits }); continue; }
    const changed = await suite(mutant.source), failures = changed.filter(item => item.status === 'FAIL');
    const relevant = failures.filter(item => /^(handed_off|in_progress|closed):/.test(item.name));
    report.mutations.push({ name: mutant.name, status: relevant.length ? 'DETECTED' : 'SURVIVED', memorySourceSha256: sha(mutant.source), edits: mutant.edits, failedChecks: failures.map(item => item.name), readOnlyFailures: relevant.map(item => item.name) });
  }
  report.summary = { checks: report.checks.length, passed: report.checks.length - failed.length, failed: failed.length, mutationsDetected: report.mutations.filter(item => item.status === 'DETECTED').length, mutationsNotRun: report.mutations.filter(item => item.status === 'NOT_RUN').length };
  report.status = failed.length || report.mutations.some(item => item.status !== 'DETECTED') ? 'FAIL' : 'PASS';
} catch (error) { report.status = 'NOT_RUN'; report.setupError = { message: error.message, stack: error.stack }; }
report.finishedAt = new Date().toISOString();
console.log(JSON.stringify(report, null, 2));
process.exitCode = report.status === 'PASS' ? 0 : report.status === 'FAIL' ? 1 : 2;
