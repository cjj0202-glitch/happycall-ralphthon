// Pure execution of actual page.tsx action closures. No server/browser/network.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url), root = path.resolve(import.meta.dirname, '../..');
const ts = require(path.join(root, 'apps/web/node_modules/typescript'));
const sourcePath = path.join(root, 'apps/web/app/page.tsx'), source = fs.readFileSync(sourcePath, 'utf8');
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const output = path.resolve(process.env.TOAST_UNIT_OUTPUT || path.join(root, '.local', 'save-toast-unit-' + Date.now()));
fs.mkdirSync(output, { recursive: true });
const ast = ts.createSourceFile(sourcePath, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const components = new Map(ast.statements.filter(ts.isFunctionDeclaration).map(node => [node.name?.text, node]));
function expression(component, name) {
  const matches = [];
  function visit(node) {
    if (ts.isVariableDeclaration(node) && node.name.getText(ast) === name) {
      const value = node.initializer;
      matches.push(ts.isCallExpression(value) && value.expression.getText(ast) === 'useCallback' ? value.arguments[0].getText(ast) : value.getText(ast));
    }
    ts.forEachChild(node, visit);
  }
  visit(components.get(component));
  if (matches.length !== 1) throw new Error('Actual action lookup not unique: ' + component + '.' + name);
  return matches[0];
}
const captured = {};
function jsxExpression(component, prop) {
  const matches = [];
  function visit(node) {
    if (ts.isJsxAttribute(node) && node.name.getText(ast) === prop && node.initializer && ts.isJsxExpression(node.initializer)) matches.push(node.initializer.expression.getText(ast));
    ts.forEachChild(node, visit);
  }
  visit(components.get(component));
  if (matches.length !== 1) throw new Error('Actual JSX callback lookup not unique: ' + prop);
  return matches[0];
}
function compileExpression(text, env) {
  const js = ts.transpileModule('const actual = (' + text + ');', { compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS } }).outputText;
  return new Function(...Object.keys(env), js + '\nreturn actual;')(...Object.values(env));
}
function action(component, name, env, mutate = text => text) {
  const key = component + '.' + name, original = expression(component, name);
  captured[key] = original;
  return compileExpression(mutate(original), env);
}
class ApiError extends Error { constructor(message, status, uncertain = false) { super(message); this.status = status; this.uncertain = uncertain; } }
const seed = { id: 'CASE-TEST', revision: 4, status: 'review', channel: 'text', intake: { storeId: 'SYN-01', subject: '합성 상품', quantity: 1, unit: 'BOX', request: '확인 요청' }, departmentId: 'warehouse', reviewConfirmed: true };
const report = { startedAt: new Date().toISOString(), host: process.env.COMPUTERNAME, sourceSha256: sha(source), harnessSha256: sha(fs.readFileSync(import.meta.filename)), method: 'AST action extraction and TypeScript transpile with deferred I/O stubs', serverStarts: 0, browserStarts: 0, networkCalls: 0, browserRecheck: 'NOT_RUN', checks: [], mutations: [] };
const add = (name, pass, detail) => report.checks.push({ name, pass: !!pass, detail });
function setup(overrides = {}) {
  const state = { toast: '직전 저장 성공', toastLog: [], busy: '', error: '', requests: [], draftSets: [], replacements: [], updates: [], recovery: null };
  let resolve, reject;
  const deferred = new Promise((yes, no) => { resolve = yes; reject = no; });
  const env = {
    fallback: false, view: 'desk', payload: {}, reloadInFlight: { current: false },
    setToast: value => { state.toast = value; state.toastLog.push(value); }, onToast: value => { state.toast = value; state.toastLog.push(value); },
    request: (...args) => { state.requests.push(args); return deferred; }, fetch: (...args) => { state.requests.push(args); return deferred; },
    update: value => state.updates.push(value), onUpdate: value => state.updates.push(value),
    setCases: value => { state.cases = value; }, setFallback: value => { state.fallback = value; }, setLastSync: value => { state.lastSync = value; },
    setSelected: value => { state.selected = value; }, setLoading: value => { state.loading = value; },
    setError: value => { state.error = value; }, setAnalysisFailure: value => { state.error = value; },
    setBusy: value => { state.busy = value; }, setRecovery: value => { state.recovery = value; }, setLinkNotice: value => { state.linkNotice = value; },
    draft: { replace: (...args) => state.replacements.push(args), set: (...args) => state.draftSets.push(args) },
    c: structuredClone(seed), busy: false, stale: false, uncertain: null, recovery: null, intakeLocked: false, canTransfer: true, question: '', form: structuredClone(seed.intake), formRevision: 4, department: 'warehouse', confirmed: true, edited: true,
    analysisInFlight: { current: false }, mounted: { current: true }, audioEnded: true, mode: 'replay',
    normalizeIntake: value => value, deskDraft: value => value, initial: value => value,
    onView: value => { state.nextView = value; }, errorText: error => error.message, ApiError,
    storeId: 'SYN-01', subject: '합성 상품', text: '원문 유지', type: 'wrong', referenceCaseId: null, attempt: null,
    crypto: { randomUUID: () => '123e4567-e89b-42d3-a456-426614174000' },
    blocked: false, reply: '센터 확인 회신', pending: [], action: '',
    ...overrides
  };
  env.sameMutation = compileExpression(components.get('sameMutation').getText(ast), env);
  env.onCreated = compileExpression(jsxExpression('Home', 'onCreated'), env);
  env.finish = action('Owner', 'finish', env);
  env.onSave = action('Home', 'save', env);
  env.inspectLatest = async () => {};
  return { env, state, resolve, reject };
}
const fail = new ApiError('새 저장 응답 유실', 503, true);
for (const [component, name, args, override] of [
  ['Home', 'save', ['CASE-TEST', { expectedRevision: 4, reply: '수정' }], {}],
  ['Desk', 'persist', [false], {}], ['Desk', 'persist', [true], {}],
  ['Center', 'submit', [false], { view: 'center' }], ['Center', 'submit', [true], { view: 'center' }],
  ['Desk', 'analyze', [], {}], ['Owner', 'submit', [], {}], ['Owner', 'verifyAttempt', [], { attempt: { key: 'existing-key', payload: { text: '원문 유지' } } }],
  ['Desk', 'inspectLatest', [], {}], ['Center', 'inspectLatest', [], {}], ['Home', 'reload', [], {}], ['Home', 'loadExample', [], {}]
]) {
  for (const outcome of ['503', 'response-lost', 'success']) {
    const test = setup(override), { env, state } = test, fn = action(component, name, env);
    const running = fn(...args);
    const during = state.toast;
    const successful = { ...structuredClone(seed), revision: 5, id: component === 'Owner' ? 'INT-TEST' : seed.id };
    if (name === 'analyze') Object.assign(successful, { analysis: { fields: seed.intake, department: { id: 'warehouse' } }, transcript: [], mode: 'replay' });
    if (outcome === 'success') test.resolve(name === 'reload' ? { cases: [successful] } : name === 'loadExample' ? { ok: true, json: async () => ({ cases: [successful] }) } : successful);
    else test.reject(outcome === '503' ? new ApiError('서버 미저장503', 503, true) : fail);
    let rejection = ''; try { await running; } catch (error) { rejection = error.message; }
    const successExpected = outcome === 'success' && ['persist', 'submit', 'analyze', 'verifyAttempt'].includes(name);
    const payload = state.requests[0]?.[2];
    const preservation = ['persist', 'submit'].includes(name) && component !== 'Owner' ? payload?.expectedRevision === 4 : true;
    const uncertainExpected = outcome !== 'success' && ['persist', 'submit'].includes(name) && component !== 'Owner';
    const uncertaintyPreserved = !uncertainExpected || state.draftSets.some(([key]) => key === 'uncertain');
    add(component + '.' + name + '(' + args.join(',') + ') ' + outcome, during === '' && (successExpected ? state.toast !== '' && state.toast !== '직전 저장 성공' : state.toast === '') && preservation && uncertaintyPreserved && state.requests.length === 1, { during, final: state.toast, toastLog: state.toastLog, error: state.error || rejection, requests: state.requests, uncertaintyPreserved, replacements: state.replacements.length });
  }
}
for (const component of ['Desk', 'Center']) {
  const uncertain = component === 'Desk' ? { expectedRevision: 4, intake: seed.intake } : { expectedRevision: 4, reply: '센터 확인 회신' };
  const test = setup({ uncertain });
  const running = action(component, 'inspectLatest', test.env)();
  const during = test.state.toast;
  test.resolve({ ...structuredClone(seed), revision: 5, reply: '센터 확인 회신' }); await running;
  add(component + ' matching recovery alone publishes new confirmation', during === '' && test.state.toast.includes('저장되어 있음을 확인') && test.state.replacements.length === 1, { during, final: test.state.toast });
}
for (const outcome of ['503', 'response-lost', 'success']) {
  const test = setup(), { env, state } = test;
  const actual = jsxExpression('Home', 'onLinkEvidence');
  captured['Home.JSX.onLinkEvidence'] = actual;
  const callback = compileExpression(actual, { ...env, save: env.onSave, active: { ...structuredClone(seed), selectedEvidence: ['E-W1'] } });
  const running = callback('E-W3'), during = state.toast;
  if (outcome === 'success') test.resolve({ ...structuredClone(seed), revision: 5, selectedEvidence: ['E-W1', 'E-W3'] }); else test.reject(outcome === '503' ? new ApiError('서버 미저장503', 503, true) : fail);
  try { await running; } catch {}
  add('actual logistics JSX callback ' + outcome, during === '' && (outcome === 'success' ? state.toast === '물류 근거를 접수 건에 연결했습니다.' : state.toast === '') && state.requests[0][2].expectedRevision === 4 && JSON.stringify(state.requests[0][2].selectedEvidence) === JSON.stringify(['E-W1', 'E-W3']), { during, final: state.toast, payload: state.requests[0][2] });
}
let ownerToastWiring = false;
function inspectOwnerWiring(node) {
  if (ts.isJsxSelfClosingElement(node) && node.tagName.getText(ast) === 'Owner') {
    const prop = node.attributes.properties.find(item => ts.isJsxAttribute(item) && item.name.getText(ast) === 'onToast');
    ownerToastWiring = !!prop && prop.initializer?.expression?.getText(ast) === 'setToast';
  }
  ts.forEachChild(node, inspectOwnerWiring);
}
inspectOwnerWiring(components.get('Home'));
add('Owner action uses actual parent toast setter', ownerToastWiring, { ownerToastWiring });
for (const [component, name, envOverrides, args] of [
  ['Desk', 'persist', { busy: 'save' }, []], ['Desk', 'analyze', { busy: 'analyze' }, []],
  ['Center', 'submit', { blocked: true }, [false]], ['Owner', 'submit', { busy: true }, []],
  ['Owner', 'verifyAttempt', { attempt: null }, []], ['Home', 'reload', { reloadInFlight: { current: true } }, []]
]) {
  const test = setup(envOverrides); await action(component, name, test.env)(...args);
  add(component + '.' + name + ' not-started guard unchanged', test.state.requests.length === 0 && test.state.toast === '직전 저장 성공', { requests: test.state.requests.length, final: test.state.toast });
}
for (const [component, name, args] of [['Home', 'save', ['CASE-TEST', { expectedRevision: 4 }]], ['Desk', 'analyze', []], ['Owner', 'submit', []]]) {
  const test = setup(), original = expression(component, name);
  const marker = component === 'Home' ? "setToast('');" : "onToast('');";
  if (!original.includes(marker)) { report.mutations.push({ name: component + '.' + name, detected: false, status: 'FIX_NOT_PRESENT' }); continue; }
  const running = action(component, name, test.env, text => text.replace(marker, ''))(...args);
  const detected = test.state.toast === '직전 저장 성공'; test.reject(fail); try { await running; } catch {}
  report.mutations.push({ name: component + '.' + name, detected, final: test.state.toast });
}
report.finishedAt = new Date().toISOString(); report.passed = report.checks.filter(check => check.pass).length; report.total = report.checks.length;
fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify(report, null, 2)); fs.writeFileSync(path.join(output, 'actual-actions.json'), JSON.stringify(captured, null, 2)); fs.copyFileSync(import.meta.filename, path.join(output, 'source-harness.mjs'));
console.log(JSON.stringify({ output, passed: report.passed, total: report.total, mutations: report.mutations, failures: report.checks.filter(check => !check.pass).map(check => check.name) }));
if (report.passed !== report.total || report.mutations.some(check => !check.detected)) process.exitCode = 1;
