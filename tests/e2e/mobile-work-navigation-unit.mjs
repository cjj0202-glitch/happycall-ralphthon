// Execute the actual Home selectCase closure in a controlled DOM/scheduler double.
// No server, browser, network, React remount, storage, or media playback is started.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';

const root = path.resolve(import.meta.dirname, '../..');
const require = createRequire(import.meta.url);
const ts = require(path.join(root, 'apps/web/node_modules/typescript'));
const files = ['apps/web/app/page.tsx', 'apps/web/lib/workflow.ts'];
const source = Object.fromEntries(files.map(file => [file, fs.readFileSync(path.join(root, file), 'utf8')]));
const ast = ts.createSourceFile(files[0], source[files[0]], ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const home = ast.statements.find(node => ts.isFunctionDeclaration(node) && node.name?.text === 'Home');
const declarations = home.body.statements.filter(ts.isVariableStatement).flatMap(node => [...node.declarationList.declarations]);
const actionNodes = declarations.filter(node => node.name.getText(ast) === 'selectCase');
if (actionNodes.length !== 1) throw new Error('Expected exactly one actual Home.selectCase declaration');
const actionSource = actionNodes[0].initializer.getText(ast);
const transpile = text => ts.transpileModule(text, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
const workflowModule = { exports: {} };
new Function('module', 'exports', transpile(source[files[1]]))(workflowModule, workflowModule.exports);
const { roleView } = workflowModule.exports;
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

function fixture(expression, options = {}) {
  const role = options.role ?? 'counselor';
  const states = { selected: 'CASE-OLD', view: roleView[role], toast: '이전 안내' };
  const protectedState = { draft: { text: '사용자가 작성한 미저장 초안', confirmed: true }, audio: { currentTime: 12.3, paused: false, ended: false } };
  const protectedBefore = JSON.stringify(protectedState);
  const writes = [], frames = [], effects = [], lookups = [], queries = [], forbidden = [];
  let width = options.width ?? 390;
  let target = {
    dataset: { caseId: states.selected, workRole: role, workView: roleView[role] },
    focus(settings) { effects.push({ type: 'focus', settings }); },
    scrollIntoView(settings) { effects.push({ type: 'scroll', settings }); },
  };
  const deny = name => (...args) => { forbidden.push({ name, args }); throw new Error('Forbidden side effect: ' + name); };
  const storage = { setItem: deny('storage.setItem'), removeItem: deny('storage.removeItem'), clear: deny('storage.clear') };
  const window = {
    matchMedia(query) {
      const maximum = /^\(max-width: (\d+)px\)$/.exec(query);
      if (!maximum) throw new Error('Unexpected media query: ' + query);
      const matches = width <= Number(maximum[1]);
      queries.push({ query, width, matches }); return { matches };
    },
    requestAnimationFrame(callback) { frames.push(callback); return frames.length; },
    localStorage: storage, sessionStorage: storage, fetch: deny('window.fetch'),
  };
  const document = { getElementById(id) { lookups.push(id); return id === 'selected-work' ? target : null; } };
  const context = { role, roleView, window, document, localStorage: storage, sessionStorage: storage,
    fetch: deny('fetch'), request: deny('request'), setCases: deny('setCases'), setForm: deny('setForm'),
    setCompletedAudioSource: deny('setCompletedAudioSource'), draft: protectedState.draft, audio: protectedState.audio,
    ...Object.fromEntries(['Selected', 'View', 'Toast'].map(name => ['set' + name, value => { const key = name[0].toLowerCase() + name.slice(1); states[key] = value; writes.push({ key, value }); }])) };
  const action = new Function(...Object.keys(context), transpile('const action = ' + expression + ';') + '\nreturn action;')(...Object.values(context));
  return { role, states, protectedState, protectedBefore, writes, frames, effects, lookups, queries, forbidden,
    select: action, resize(next) { width = next; },
    commit(id = states.selected, nextRole = role, nextView = roleView[nextRole]) { target.dataset = { caseId: id, workRole: nextRole, workView: nextView }; },
    removeCaseIdentifier() { delete target.dataset.caseId; },
    removeTarget() { target = null; },
    flush() { while (frames.length) frames.shift()(0); },
  };
}

function runActionSuite(expression) {
  const checks = [];
  const check = (name, condition, detail = null) => checks.push({ name, pass: !!condition, detail });
  const scenario = (name, run) => { try { run(); } catch (error) { check(name + ': no exception', false, error.message); } };
  const expectedEffects = [{ type: 'focus', settings: { preventScroll: true } }, { type: 'scroll', settings: { block: 'start', behavior: 'instant' } }];
  const preserved = (name, app) => check(name + ': no draft, audio, storage, or API writes', JSON.stringify(app.protectedState) === app.protectedBefore && app.forbidden.length === 0, app.forbidden);
  for (const role of ['counselor', 'center']) for (const channel of ['voice', 'text']) scenario(role + '/' + channel, () => {
    const app = fixture(expression, { role });
    // First select another case, then reselect that same case twice. No effect hook is needed.
    for (let click = 0; click < 3; click++) {
      const name = role + '/' + channel + (click ? ': same case repeat ' + click : ': another case');
      const previousEffects = app.effects.length, previousWrites = app.writes.length;
      const id = 'CASE-' + channel.toUpperCase();
      app.select(id);
      check(name + ': selects case, own work view and clears toast only', same(app.writes.slice(previousWrites), [{ key: 'selected', value: id }, { key: 'view', value: roleView[role] }, { key: 'toast', value: '' }]));
      check(name + ': defers focus until the next frame', app.frames.length === 1 && app.effects.length === previousEffects);
      app.commit(); app.flush();
      check(name + ': focus then instant scroll on committed case', same(app.effects.slice(previousEffects), expectedEffects), app.effects.slice(previousEffects));
      preserved(name, app);
    }
  });
  for (const width of [768, 769, 1280]) scenario('width ' + width, () => {
    const app = fixture(expression, { width }); app.select('CASE-A');
    check('width ' + width + ': frame scheduling boundary', app.frames.length === (width <= 768 ? 1 : 0), { frames: app.frames.length });
    app.commit(); app.flush();
    check('width ' + width + ': focus boundary', app.effects.length === (width <= 768 ? 2 : 0), app.effects);
    preserved('width ' + width, app);
  });
  for (const [initial, next] of [[390, 769], [768, 769], [769, 390]]) scenario('resize ' + initial + '→' + next, () => {
    const app = fixture(expression, { width: initial }); app.select('CASE-A'); app.commit(); app.resize(next); app.flush();
    check('resize ' + initial + '→' + next + ': no stale focus or scroll', app.effects.length === 0, app.effects);
  });
  for (const [name, change] of [
    ['different case', app => app.commit('CASE-B')],
    ['missing case identifier', app => app.removeCaseIdentifier()],
    ['different role', app => app.commit('CASE-A', 'center', 'desk')],
    ['WMS view', app => app.commit('CASE-A', 'counselor', 'wms')],
    ['TMS view', app => app.commit('CASE-A', 'counselor', 'tms')],
    ['target removed', app => app.removeTarget()],
  ]) scenario(name, () => {
    const app = fixture(expression); app.select('CASE-A'); change(app); app.flush();
    check(name + ': no stale focus or scroll', app.effects.length === 0, app.effects);
    preserved(name, app);
  });
  scenario('rapid case switch', () => {
    const app = fixture(expression); app.select('CASE-A'); app.select('CASE-B'); app.commit('CASE-B'); app.flush();
    check('rapid case switch: only current case focuses', same(app.effects, expectedEffects) && app.states.selected === 'CASE-B', app.effects);
    check('rapid case switch: both callbacks inspected current DOM', same(app.lookups, ['selected-work', 'selected-work']), app.lookups);
    preserved('rapid case switch', app);
  });
  return checks;
}

const checks = runActionSuite(actionSource);
const check = (name, condition, detail = null) => checks.push({ name, pass: !!condition, detail });
// Execute JSX attribute expressions from production, rather than accepting matching source text.
function findNodes(node, predicate, found = []) { if (predicate(node)) found.push(node); ts.forEachChild(node, child => { findNodes(child, predicate, found); }); return found; }
const tag = node => ts.isJsxElement(node) ? node.openingElement : node;
function attributes(node, values) {
  return Object.fromEntries(tag(node).attributes.properties.map(attribute => {
    if (!ts.isJsxAttribute(attribute)) throw new Error('Unexpected spread in navigation target');
    const initializer = attribute.initializer;
    const value = !initializer ? true : ts.isStringLiteral(initializer) ? initializer.text : new Function(...Object.keys(values), transpile('const value = ' + initializer.expression.getText(ast) + ';') + '\nreturn value;')(...Object.values(values));
    return [attribute.name.getText(ast), value];
  }));
}
const openingNodes = findNodes(home, node => ts.isJsxOpeningElement(node));
const targets = openingNodes.filter(node => node.attributes.properties.some(attribute => ts.isJsxAttribute(attribute) && attribute.name.getText(ast) === 'id' && attribute.initializer?.text === 'selected-work'));
check('exactly one Home navigation focus target', targets.length === 1, targets.length);
if (targets.length === 1) for (const role of ['counselor', 'center']) for (const view of [roleView[role], 'wms', 'tms']) {
  const actual = attributes(targets[0], { active: { id: 'CASE-RENDERED', title: '선택한 합성 문의' }, role, view });
  check(role + '/' + view + ': actual target binds current case, role, view and programmatic focus', actual.id === 'selected-work' && actual.tabIndex === -1 && actual['data-case-id'] === 'CASE-RENDERED' && actual['data-work-role'] === role && actual['data-work-view'] === view, actual);
}
const queues = openingNodes.filter(node => node.tagName.getText(ast) === 'aside' && node.attributes.properties.some(attribute => ts.isJsxAttribute(attribute) && attribute.name.getText(ast) === 'id' && attribute.initializer?.text === 'work-queue'));
check('one Home native queue return target', queues.length === 1, queues.length);
if (queues.length === 1) {
  const actual = attributes(queues[0], { role: 'center', roleNames: workflowModule.exports.roleNames });
  check('native queue target can receive focus', actual.id === 'work-queue' && actual.tabIndex === -1, actual);
}
for (const name of ['Desk', 'Center']) {
  const component = ast.statements.find(node => ts.isFunctionDeclaration(node) && node.name?.text === name);
  const links = findNodes(component, node => ts.isJsxElement(node) && node.openingElement.tagName.getText(ast) === 'a').filter(node => node.openingElement.attributes.properties.some(attribute => ts.isJsxAttribute(attribute) && attribute.name.getText(ast) === 'className' && attribute.initializer?.text === 'queue-return'));
  check(name + ': one queue return link', links.length === 1, links.length);
  if (links.length === 1) {
    const actual = attributes(links[0], {});
    check(name + ': native queue link has no click mutation handler', actual.href === '#work-queue' && actual.onClick === undefined, actual);
  }
}

const mutationSpecs = [
  ['desktop scheduling guard removed', "if (!window.matchMedia('(max-width: 768px)').matches) return;", ''],
  ['callback viewport guard removed', "!window.matchMedia('(max-width: 768px)').matches || ", ''],
  ['case guard removed', 'target?.dataset.caseId !== id || ', ''],
  ['role guard removed', 'target.dataset.workRole !== role || ', ''],
  ['view guard removed', ' || target.dataset.workView !== roleView[role]', ''],
  ['focus removed', 'target.focus({ preventScroll: true });', ''],
  ['scroll removed', "target.scrollIntoView({ block: 'start', behavior: 'instant' });", ''],
  ['focus causes extra scroll', 'preventScroll: true', 'preventScroll: false'],
  ['center returns to counselor view', 'setView(roleView[role]);', "setView('desk');"],
];
const mutations = mutationSpecs.map(([name, from, to]) => {
  const occurrences = actionSource.split(from).length - 1;
  if (occurrences !== 1) return { name, detected: false, error: 'Mutation anchor count ' + occurrences };
  const failed = runActionSuite(actionSource.replace(from, to)).filter(result => !result.pass);
  return { name, detected: failed.length > 0, failedChecks: failed.map(result => result.name) };
});
check('all nine behavioral mutations detected', mutations.length === 9 && mutations.every(result => result.detected), mutations);
const output = path.join(root, '.local', 'mobile-work-navigation-unit-' + Date.now());
fs.mkdirSync(output, { recursive: true });
const report = { measuredAt: new Date().toISOString(), sourceSha256: Object.fromEntries(files.map(file => [file, crypto.createHash('sha256').update(source[file]).digest('hex')])), actualActionSha256: crypto.createHash('sha256').update(actionSource).digest('hex'), serverStarts: 0, browserStarts: 0, networkCalls: 0, browserRecheck: 'NOT_RUN', limits: 'Controlled scheduler/DOM doubles validate the production closure and target bindings, not browser layout, native anchor focus, React remount behavior, audible playback, or user usability.', passed: checks.filter(result => result.pass).length, total: checks.length, checks, mutations };
fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify({ output, passed: report.passed, total: report.total, failed: checks.filter(result => !result.pass), mutations }));
if (report.passed !== report.total) process.exitCode = 1;
