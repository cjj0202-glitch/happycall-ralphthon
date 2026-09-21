// Pure production-module and actual Home JSX/action execution. No browser/server/socket/network.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url), root = path.resolve(import.meta.dirname, '../..');
const ts = require(path.join(root, 'apps/web/node_modules/typescript'));
const files = ['apps/web/lib/workflow.ts', 'apps/web/app/page.tsx'];
const source = Object.fromEntries(files.map(file => [file, fs.readFileSync(path.join(root, file), 'utf8')]));
const checks = [], mutations = [];
const check = (name, condition, detail = null) => { checks.push({ name, pass: !!condition, detail }); if (!condition) throw new Error(name); };
function compile(text, imports = {}) {
  const module = { exports: {} };
  const js = ts.transpileModule(text, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  new Function('require', 'module', 'exports', js)(name => { if (!(name in imports)) throw new Error('Unregistered import: ' + name); return imports[name]; }, module, module.exports);
  return module.exports;
}
const workflow = compile(source[files[0]]);
const cases = ['draft', 'review', 'handed_off', 'in_progress', 'closed', 'unexpected', undefined].map((status, index) => ({ id: `CASE-${index}`, status, revision: 4, channel: index ? 'text' : 'voice', title: `${index ? '오출고' : '미도착'} 문의`, store: { id: 'SYN-' + index, name: `새봄${index}점` }, type: index ? 'wrong' : 'missing', selectedEvidence: [] }));
for (const [role, queue, expected] of [
  ['counselor', 'attention', [0, 1]], ['counselor', 'handed_off', [2, 3]], ['counselor', 'closed', [4]],
  ['center', 'handed_off', [2]], ['center', 'in_progress', [3]], ['center', 'closed', [4]],
  ['counselor', 'all', [0, 1, 2, 3, 4, 5, 6]], ['center', 'all', [0, 1, 2, 3, 4, 5, 6]],
]) check(role + ' queue ' + queue, JSON.stringify(workflow.filterCases(cases, role, queue, '').map(c => c.id)) === JSON.stringify(expected.map(n => 'CASE-' + n)), expected);
for (const [query, expected] of [['새봄2', 2], ['syn-3', 3], ['case-4', 4], ['미도착', 0]]) check('search ' + query, workflow.filterCases(cases, 'center', 'all', query)[0]?.id === 'CASE-' + expected);
check('nonmatching search has zero results', workflow.filterCases(cases, 'center', 'all', 'not-a-store').length === 0);
check('empty stage has zero results', workflow.filterCases([cases[0]], 'center', 'handed_off', '').length === 0);
for (const role of ['counselor', 'center', 'owner']) for (let index = 0; index < cases.length; index++) check('evidence guard ' + role + ':' + index, workflow.isEvidenceEditable(cases[index], role) === (role === 'counselor' && index < 2));
check('one current step before analysis', workflow.deskStep(cases[0], false, false) === 1);
check('one current step after analysis', workflow.deskStep(cases[1], true, false) === 2);
check('one current step after confirmation', workflow.deskStep(cases[1], true, true) === 3);
check('handed-off stays step three', workflow.deskStep(cases[2], false, false) === 3);
check('text action does not instruct listening', !workflow.nextAction({ ...cases[0], channel: 'text' }, 'counselor').includes('통화'));
check('unknown status has explicit recovery instruction', workflow.nextAction(cases[5], 'center') === '처리 상태 확인 필요');

const ast = ts.createSourceFile(files[1], source[files[1]], ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const home = ast.statements.find(node => ts.isFunctionDeclaration(node) && node.name?.text === 'Home');
const stateNames = [];
for (const statement of home.body.statements) if (ts.isVariableStatement(statement)) for (const declaration of statement.declarationList.declarations) if (ts.isCallExpression(declaration.initializer) && declaration.initializer.expression.getText(ast) === 'useState') stateNames.push(declaration.name.elements[0].name.text);
const jsx = (type, props, key) => ({ type, props: props ?? {}, key });
function findAll(tree, predicate, results = []) {
  if (!tree || typeof tree !== 'object') return results;
  if (Array.isArray(tree)) { for (const item of tree) findAll(item, predicate, results); return results; }
  if (predicate(tree)) results.push(tree);
  findAll(tree.props?.children, predicate, results); return results;
}
const textOf = tree => typeof tree === 'string' || typeof tree === 'number' ? String(tree) : Array.isArray(tree) ? tree.map(textOf).join('') : tree && typeof tree === 'object' ? textOf(tree.props?.children) : '';
function instance(overrides = {}, moduleSource = source[files[1]], workflowApi = workflow) {
  const states = { view: 'desk', role: 'counselor', queue: 'attention', query: '', cases: structuredClone(cases), selected: 'CASE-0', loading: false, error: '', toast: '', fallback: false, mode: 'replay', lastSync: '', ...overrides };
  const calls = [], draftWrites = []; let cursor = 0;
  const react = { useState(initial) { const name = stateNames[cursor++]; if (!(name in states)) states[name] = initial; return [states[name], next => { states[name] = typeof next === 'function' ? next(states[name]) : next; }]; }, useEffect() {}, useCallback(fn) { return fn; }, useRef(value) { return { current: value }; } };
  class ApiError extends Error {}
  const api = compile(moduleSource, { react, 'react/jsx-runtime': { jsx, jsxs: jsx, Fragment: 'fragment' }, '@/components/CallReview': function CallMarker() {}, '@/components/NotificationStatus': function NotificationMarker() {}, '@/components/WmsScene': function WmsMarker() {}, '@/components/TmsScene': function TmsMarker() {}, '@/lib/api': { ApiError, request: async (...args) => { calls.push(args); if (args[0] === '/api/cases') return { cases: structuredClone(states.remoteCases ?? states.cases) }; return { ...states.cases.find(c => c.id === args[0].split('/').at(-1)), ...args[2], revision: 5 }; } }, '@/lib/drafts': { acceptOwnEvidenceSave: () => false, useHasUnsavedDrafts: () => true, useSessionDraft: () => { draftWrites.push('unexpected'); throw new Error('Home must not write drafts'); } }, '@/lib/workflow': workflowApi });
  const render = () => { cursor = 0; return api.default(); };
  const button = (tree, label) => findAll(tree, node => node.type === 'button' && textOf(node) === label)[0];
  const child = (tree, name) => findAll(tree, node => typeof node.type === 'function' && node.type.name === name)[0];
  return { states, calls, draftWrites, render, button, child };
}
let app = instance(), tree = app.render();
check('actual primary navigation has only three role tabs', findAll(findAll(tree, n => n.type === 'nav' && n.props['aria-label'] === '업무 역할')[0], n => n.type === 'button').length === 3);
check('actual counselor defaults to attention queue, selected case visible', app.child(tree, 'Desk').props.caseData.id === 'CASE-0');
app.button(tree, '센터 작업대').props.onClick(); tree = app.render();
check('role change sets center and new-handoff queue', app.states.role === 'center' && app.states.view === 'center' && app.states.queue === 'handed_off');
check('center default opens only handed-off case', app.child(tree, 'Center').props.caseData.id === 'CASE-2');
let center = app.child(tree, 'Center'); center.props.onView('wms'); tree = app.render();
let logistics = app.child(tree, 'LogisticsScene');
check('center WMS preserves role and selected case', app.states.role === 'center' && logistics.props.caseData.id === 'CASE-2' && logistics.props.readOnly === true && logistics.props.backLabel === '센터 업무로 돌아가기');
let rejection = ''; try { await logistics.props.onLinkEvidence('E-1'); } catch (error) { rejection = error.message; }
check('actual center WMS link action rejects before API', rejection.includes('변경할 수 없습니다') && app.calls.length === 0, rejection);
logistics.props.onBack(); tree = app.render();
check('actual WMS back restores center, not counselor', app.states.view === 'center' && app.child(tree, 'Center').props.caseData.id === 'CASE-2');
center = app.child(tree, 'Center'); await center.props.onSave('CASE-2', { expectedRevision: 4, reply: '기록 확인' });
check('actual center PATCH retains center role and revision', app.calls[0][3] === 'center' && app.calls[0][2].expectedRevision === 4, app.calls[0]);
tree = app.render(); app.child(tree, 'Center').props.onView('tms'); tree = app.render();
check('actual center TMS is also read-only and returns to center', app.child(tree, 'LogisticsScene').props.readOnly && app.states.role === 'center');
app.child(tree, 'LogisticsScene').props.onBack();
check('no draft clearing while changing roles and evidence pages', app.draftWrites.length === 0);

app = instance({ cases: [cases[0]], role: 'center', view: 'center', queue: 'handed_off' }); tree = app.render();
check('empty center queue does not borrow a draft case', !app.child(tree, 'Center') && textOf(tree).includes('선택한 처리 단계에 접수가 없습니다'));
app.button(tree, '전체 접수 보기').props.onClick(); tree = app.render();
check('all-list recovery explicitly shows draft for viewing', app.child(tree, 'Center').props.caseData.id === 'CASE-0' && app.states.queue === 'all');
app.child(tree, 'Center').props.onView('tms'); tree = app.render();
check('center viewing pre-handoff is read-only too', app.child(tree, 'LogisticsScene').props.readOnly);
app = instance({ query: 'nonexisting' }); tree = app.render();
check('search zero hides detail rather than showing unmatched selection', !app.child(tree, 'Desk') && textOf(tree).includes('검색 결과가 없습니다'));
app.button(tree, '검색 지우기').props.onClick(); tree = app.render();
check('search clearing restores selected case', app.child(tree, 'Desk').props.caseData.id === 'CASE-0');
app.child(tree, 'Desk').props.onView('wms'); tree = app.render();
logistics = app.child(tree, 'LogisticsScene'); await logistics.props.onLinkEvidence('E-W1');
check('editable counselor links exact active case with expected revision', app.calls[0][0] === '/api/cases/CASE-0' && app.calls[0][3] === 'counselor' && app.calls[0][2].expectedRevision === 4 && app.calls[0][2].selectedEvidence[0] === 'E-W1');
app = instance({ selected: 'CASE-2', queue: 'handed_off' }); tree = app.render(); app.child(tree, 'Desk').props.onView('tms'); tree = app.render();
rejection = ''; try { await app.child(tree, 'LogisticsScene').props.onLinkEvidence('E-2'); } catch (error) { rejection = error.message; }
check('handed-off counselor cannot bypass read-only through TMS', !!rejection && app.calls.length === 0);
const unlocked = instance({ role: 'center', view: 'wms', queue: 'handed_off', selected: 'CASE-2' }, source[files[1]].replace("if (!isEvidenceEditable(active, role)) throw new Error('센터에 전달된 접수 또는 센터 열람 화면에서는 근거를 변경할 수 없습니다.');", ''));
await unlocked.child(unlocked.render(), 'LogisticsScene').props.onLinkEvidence('X');
mutations.push({ name: 'evidence-lock-removed', detected: unlocked.calls.length > 0 });
// Exercise the actual save closure while a center worker is looking at a logistics view.
let saveExpression;
for (const statement of home.body.statements) if (ts.isVariableStatement(statement)) for (const declaration of statement.declarationList.declarations) if (declaration.name.getText(ast) === 'save') saveExpression = declaration.initializer.getText(ast);
function actualSave(expression, role, view) {
  const sent = [], context = { role, view, fallback: false, setToast() {}, update() {}, request: async (...args) => { sent.push(args); return {}; } };
  const js = ts.transpileModule('const action = ' + expression + ';', { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText;
  return { sent, run: new Function(...Object.keys(context), js + '\nreturn action;')(...Object.values(context)) };
}
const savedFromEvidence = actualSave(saveExpression, 'center', 'wms');
await savedFromEvidence.run('CASE-2', { expectedRevision: 4, reply: '확인 회신' });
check('actual save closure uses work role while view is WMS', savedFromEvidence.sent[0][3] === 'center');
const lostRole = actualSave(saveExpression.replace("role === 'center'", "view === 'center'"), 'center', 'wms');
await lostRole.run('CASE-2', { expectedRevision: 4, reply: '확인 회신' });
mutations.push({ name: 'center-role-lost', detected: lostRole.sent[0][3] !== 'center' });
const ownerSave = actualSave(saveExpression, 'owner', 'owner');
rejection = ''; try { await ownerSave.run('CASE-2', { expectedRevision: 4 }); } catch (error) { rejection = error.message; }
check('owner cannot invoke counseling PATCH closure', !!rejection && ownerSave.sent.length === 0);
const lostBack = instance({ role: 'center', view: 'wms', queue: 'handed_off', selected: 'CASE-2' }, source[files[1]].replace("onBack={returnToWork}", "onBack={() => setView('desk')}"));
lostBack.child(lostBack.render(), 'LogisticsScene').props.onBack(); mutations.push({ name: 'center-return-lost', detected: lostBack.states.view !== 'center' });
const weakened = compile(source[files[0]].replace("if (queue === 'all') return true;", "if (queue === 'all') return item.status !== 'unexpected';"));
mutations.push({ name: 'unknown-status-hidden', detected: weakened.filterCases(cases, 'center', 'all', '').length !== cases.length });
for (const [index, expectedQueue] of [[0, 'attention'], [1, 'attention'], [2, 'handed_off'], [3, 'handed_off'], [4, 'closed'], [5, 'all']]) {
  const owner = instance({ role: 'owner', view: 'owner', selected: cases[index].id });
  owner.child(owner.render(), 'Owner').props.onDesk();
  const result = owner.child(owner.render(), 'Desk');
  check('Owner selected case to counselor keeps ID and queue ' + index, result?.props.caseData.id === cases[index].id && owner.states.queue === expectedQueue);
}
const other = { ...structuredClone(cases[2]), id: 'CASE-OTHER', title: '다른 접수' };
async function refreshWhileInspecting({ role = 'center', kind = 'wms', nextStatus = 'in_progress', remove = false, moduleSource = source[files[1]], workflowApi = workflow } = {}) {
  const app = instance({ role, view: role === 'center' ? 'center' : 'desk', queue: 'handed_off', selected: 'CASE-2', cases: [structuredClone(cases[2]), other] }, moduleSource, workflowApi);
  app.child(app.render(), role === 'center' ? 'Center' : 'Desk').props.onView(kind);
  app.states.remoteCases = remove ? [other] : [{ ...structuredClone(cases[2]), revision: 5, status: nextStatus }, other];
  await app.button(app.render(), '목록 새로고침').props.onClick();
  await Promise.resolve();
  return app;
}
for (const role of ['center', 'counselor']) for (const kind of ['wms', 'tms']) for (const status of ['in_progress', 'closed']) {
  const refreshed = await refreshWhileInspecting({ role, kind, nextStatus: status });
  const scene = refreshed.child(refreshed.render(), 'LogisticsScene');
  check(role + ' ' + kind + ' refresh keeps exact case at ' + status, scene?.props.caseData.id === 'CASE-2' && scene.props.caseData.status === status && scene.props.caseData.revision === 5 && refreshed.states.selected === 'CASE-2');
  scene.props.onBack();
  const detail = refreshed.child(refreshed.render(), role === 'center' ? 'Center' : 'Desk');
  check(role + ' ' + kind + ' back follows current-status queue ' + status, detail?.props.caseData.id === 'CASE-2' && refreshed.states.queue === workflow.queueForCase({ ...cases[2], status }, role));
}
for (const kind of ['wms', 'tms']) {
  const removed = await refreshWhileInspecting({ kind, remove: true });
  const current = removed.render();
  check(kind + ' missing refreshed case is explicit without replacement', !removed.child(current, 'LogisticsScene') && textOf(current).includes('선택한 접수를 찾을 수 없습니다') && textOf(current).includes('CASE-2') && removed.states.selected === 'CASE-2');
  removed.button(current, '접수 목록으로 돌아가기').props.onClick();
  check(kind + ' missing-case recovery returns to explicit all list', removed.states.view === 'center' && removed.states.queue === 'all' && removed.child(removed.render(), 'Center')?.props.caseData.id === 'CASE-OTHER');
}
const missingHandoff = compile(source[files[0]].replace("if (item.status === 'handed_off') return 'handed_off';", ''));
const ownerMutation = instance({ role: 'owner', view: 'owner', selected: 'CASE-2' }, source[files[1]], missingHandoff);
ownerMutation.child(ownerMutation.render(), 'Owner').props.onDesk();
mutations.push({ name: 'handoff-queue-missing', detected: ownerMutation.states.queue !== 'handed_off' });
const unpinned = await refreshWhileInspecting({ moduleSource: source[files[1]].replace("const active = logistics || role === 'owner'", "const active = role === 'owner'") });
mutations.push({ name: 'evidence-case-swapped-on-refresh', detected: unpinned.child(unpinned.render(), 'LogisticsScene').props.caseData.id !== 'CASE-2' });
const wrongReturnQueue = await refreshWhileInspecting({ moduleSource: source[files[1]].replace("setQueue(current ? queueForCase(current, role) : 'all');", "setQueue(defaultQueue(role));") });
wrongReturnQueue.child(wrongReturnQueue.render(), 'LogisticsScene').props.onBack();
mutations.push({ name: 'return-queue-stale-after-refresh', detected: wrongReturnQueue.child(wrongReturnQueue.render(), 'Center').props.caseData.id !== 'CASE-2' });
check('all seven regressions activate their controls', mutations.length === 7 && mutations.every(m => m.detected), mutations);
const output = path.join(root, '.local', 'role-workflow-unit-' + Date.now()); fs.mkdirSync(output, { recursive: true });
const report = { startedAt: new Date().toISOString(), sourceSha256: Object.fromEntries(files.map(file => [file, crypto.createHash('sha256').update(source[file]).digest('hex')])), serverStarts: 0, browserStarts: 0, networkCalls: 0, browserRecheck: 'NOT_RUN', passed: checks.filter(c => c.pass).length, total: checks.length, checks, mutations };
fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify({ output, passed: report.passed, total: report.total, mutations }));
