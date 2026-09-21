// Execute the production JSX callback and memory draft store, with deferred I/O.
// Browser rendering and HTTP persistence are verified separately by the main PC.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
const root = path.resolve(import.meta.dirname, '../..'), require = createRequire(import.meta.url);
const ts = require(path.join(root, 'apps/web/node_modules/typescript'));
const files = ['apps/web/app/page.tsx', 'apps/web/lib/drafts.ts', 'apps/web/lib/workflow.ts'];
const source = Object.fromEntries(files.map(file => [file, fs.readFileSync(path.join(root, file), 'utf8')]));
const transpile = text => ts.transpileModule(text, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
function compile(text, imports = {}) {
  const module = { exports: {} };
  new Function('require', 'module', 'exports', transpile(text))(name => { if (!(name in imports)) throw new Error('Unexpected import: ' + name); return imports[name]; }, module, module.exports);
  return module.exports;
}
const expression = (text, env) => new Function(...Object.keys(env), transpile('const actual = (' + text + ');') + '\nreturn actual;')(...Object.values(env));
const ast = ts.createSourceFile(files[0], source[files[0]], ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const home = ast.statements.find(node => ts.isFunctionDeclaration(node) && node.name?.text === 'Home');
const callbacks = [];
function visit(node) {
  if (ts.isJsxAttribute(node) && node.name.getText(ast) === 'onLinkEvidence') callbacks.push(node.initializer.expression.getText(ast));
  ts.forEachChild(node, visit);
}
visit(home);
if (callbacks.length !== 1) throw new Error('Expected one actual evidence callback');
const declaration = (body, name) => body.filter(ts.isVariableStatement).flatMap(node => [...node.declarationList.declarations]).find(node => node.name.getText(ast) === name).initializer.getText(ast);
const saveExpression = declaration(home.body.statements, 'save');
const normalizeIntake = expression(declaration(ast.statements, 'normalizeIntake'), {});
const initialDraft = expression(declaration(ast.statements, 'deskDraft'), { normalizeIntake, emptyIntake: { storeId: '', subject: '', quantity: '', unit: '', request: '' } });
const deskContent = expression(declaration(ast.statements, 'deskContent'), { normalizeIntake });
const workflow = compile(source[files[2]]);
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const seed = {
  id: 'CASE-SYN-EVIDENCE', revision: 4, status: 'review', channel: 'text', type: 'wrong', title: '합성 문의',
  store: { id: 'SYN-01', name: '합성점포' }, sourceText: '받은 상품을 확인해 주세요.',
  intake: { storeId: 'SYN-01', subject: '합성 상품', quantity: 1, unit: 'BOX', request: '확인 요청' },
  departmentId: 'warehouse', reviewConfirmed: true, selectedEvidence: ['E-W1'],
  history: [{ at: '2026-09-22T00:00:00Z', actor: 'counselor', action: 'review', message: '접수 상태 저장' }],
  updatedAt: '2026-09-22T00:00:00Z', analysis: { summary: '합성 분석' }, transcript: [],
};
function acknowledged(previous, selection) {
  return { ...structuredClone(previous), revision: previous.revision + 1, selectedEvidence: [...selection],
    reviewConfirmed: same(previous.selectedEvidence || [], selection) ? previous.reviewConfirmed : false,
    updatedAt: '2026-09-22T00:01:00Z', history: [...(previous.history || []), { at: '2026-09-22T00:01:00Z', actor: 'counselor', action: previous.status, message: '접수 상태 저장' }] };
}
function instance(draftSource, callbackSource, options = {}) {
  const previous = structuredClone(options.previous ?? seed), key = `desk:${previous.id}`;
  const hooks = { useCallback: fn => fn, useSyncExternalStore: (_subscribe, snapshot) => snapshot() };
  const drafts = compile(draftSource, { react: hooks });
  const read = (id = previous.id) => drafts.useSessionDraft(`desk:${id}`, initialDraft({ ...previous, id }), deskContent);
  if (!options.noDraft) {
    const draft = read();
    draft.set('form', { ...draft.value.form, request: '사용자가 작성한 미저장 요청' });
    draft.set('question', '확인할 메모를 유지합니다.'); draft.set('edited', true); draft.set('confirmed', true);
    for (const [field, value] of Object.entries(options.draft ?? {})) read().set(field, value);
  }
  const requests = [], updates = [], receipts = [];
  let resolve, reject, toast = '이전 성공 알림';
  const pending = new Promise((yes, no) => { resolve = yes; reject = no; });
  const env = { active: previous, role: options.role ?? 'counselor', fallback: false, isEvidenceEditable: workflow.isEvidenceEditable,
    setToast: value => { toast = value; }, update: value => updates.push(value),
    request: (...args) => { requests.push(args); return pending; },
    acceptOwnEvidenceSave: (...args) => { const accepted = drafts.acceptOwnEvidenceSave(...args); receipts.push(accepted); return accepted; } };
  env.save = expression(saveExpression, env);
  return { previous, key, read, drafts, requests, updates, receipts, resolve, reject, toast: () => toast,
    link: expression(callbackSource, env) };
}
async function suite(draftSource, callbackSource) {
  const checks = [], check = (name, pass, detail = null) => checks.push({ name, pass: !!pass, detail });
  for (const status of ['draft', 'review']) {
    const app = instance(draftSource, callbackSource, { previous: { ...seed, status } });
    const before = structuredClone(app.read().value), selected = ['E-W1', 'E-W3'];
    const running = app.link('E-W3');
    check(status + ': draft is unchanged before acknowledgement', same(app.read().value, before) && app.toast() === '');
    app.resolve(acknowledged(app.previous, selected)); await running;
    const after = app.read().value;
    check(status + ': successful own evidence save advances only revision and confirmation', same(after, { ...before, formRevision: 5, confirmed: false }), after);
    check(status + ': unsaved form, department, question and edited flag remain dirty', app.read().dirty && app.drafts.useHasUnsavedDrafts() && after.form.request === before.form.request && after.question === before.question && after.department === before.department && after.edited === true);
    check(status + ': one PATCH uses original revision and exact deduplicated selection', same(app.requests, [[`/api/cases/${seed.id}`, 'PATCH', { expectedRevision: 4, selectedEvidence: selected }, 'counselor']]));
    check(status + ': accepted response updates case and shows success', app.receipts[0] === true && app.updates.length === 1 && app.toast() === '물류 근거를 접수 건에 연결했습니다.');
  }
  for (const outcome of ['409 conflict', '503 rejection', 'response lost']) {
    const app = instance(draftSource, callbackSource), before = structuredClone(app.read().value);
    const running = app.link('E-W3'); app.reject(new Error(outcome));
    let rejection; try { await running; } catch (error) { rejection = error.message; }
    check(outcome + ': no revision/confirmation/draft change or success receipt', rejection === outcome && same(app.read().value, before) && app.receipts.length === 0 && app.updates.length === 0 && app.toast() === '');
  }
  for (const [name, options, change] of [
    ['already stale draft', { draft: { formRevision: 3 } }, () => {}],
    ['draft changed during request', {}, (_saved, app) => app.read().set('formRevision', 3)],
    ['uncertain prior save', { draft: { uncertain: { expectedRevision: 4, intake: seed.intake } } }, () => {}],
    ['save in flight', { draft: { operation: 'save' } }, () => {}],
    ['analysis in flight', { draft: { operation: 'analyze' } }, () => {}],
    ['other case response', {}, saved => { saved.id = 'CASE-OTHER'; }],
    ['revision jump', {}, saved => { saved.revision = 6; }],
    ['unchanged revision', {}, saved => { saved.revision = 4; }],
    ['noninteger revision', {}, saved => { saved.revision = 5.5; }],
    ['missing revision', {}, saved => { delete saved.revision; }],
    ['unexpected evidence', {}, saved => { saved.selectedEvidence = ['E-OTHER']; }],
    ['confirmation not invalidated', {}, saved => { saved.reviewConfirmed = true; }],
    ...['intake', 'departmentId', 'status', 'analysis', 'transcript', 'store', 'sourceText', 'pendingActions', 'reply', 'notificationOutbox', 'unknownNewField'].map(field => [field + ' changed', {}, saved => { saved[field] = 'remote change'; }]),
  ]) {
    const app = instance(draftSource, callbackSource, options), saved = acknowledged(app.previous, ['E-W1', 'E-W3']);
    const running = app.link('E-W3'); change(saved, app); const before = structuredClone(app.read().value);
    app.resolve(saved); await running;
    check(name + ': saved response cannot silently rebase existing draft', same(app.read().value, before) && app.receipts[0] === false);
  }
  {
    const app = instance(draftSource, callbackSource), before = structuredClone(app.read().value);
    const saved = acknowledged(app.previous, ['E-W1', 'E-W3']);
    saved.intake = Object.fromEntries(Object.entries(saved.intake).reverse());
    app.resolve(saved); await app.link('E-W3');
    check('equivalent intake with reversed object key order accepts own save', app.receipts[0] === true && same(app.read().value, { ...before, formRevision: 5, confirmed: false }));
  }
  {
    // Home's actual post-analyze projection omits audit metadata and normalizes
    // nullable fields, although the server has already saved that same revision.
    const previous = { ...structuredClone(seed), reviewConfirmed: false,
      intake: { ...seed.intake, quantity: '', unit: '', request: '' }, departmentId: '' };
    const app = instance(draftSource, callbackSource, { previous });
    const before = structuredClone(app.read().value), saved = acknowledged(previous, ['E-W1', 'E-W3']);
    saved.intake = { ...seed.intake, quantity: null, unit: null, request: null };
    saved.departmentId = null; saved.analysisRequestId = 'replay-synthetic-id';
    saved.history.splice(-1, 0, { at: '2026-09-22T00:00:30Z', actor: 'counselor', action: 'analyzed', message: '사전 분석 리플레이' });
    app.resolve(saved); await app.link('E-W3');
    check('post-analyze projection accepts own save despite omitted audit metadata and normalized nulls', app.receipts[0] === true && same(app.read().value, { ...before, formRevision: 5, confirmed: false }));
  }
  for (const role of ['center', 'owner']) {
    const app = instance(draftSource, callbackSource, { role }), before = structuredClone(app.read().value);
    let rejection; try { await app.link('E-W3'); } catch (error) { rejection = error.message; }
    check(role + ': denied before PATCH and before draft update', !!rejection && app.requests.length === 0 && app.receipts.length === 0 && same(app.read().value, before));
  }
  {
    const app = instance(draftSource, callbackSource), before = structuredClone(app.read().value);
    app.resolve(acknowledged(app.previous, ['E-W1'])); await app.link('E-W1');
    check('duplicate evidence remains deduplicated and requires re-confirmation', same(app.requests[0][2].selectedEvidence, ['E-W1']) && same(app.read().value, { ...before, formRevision: 5, confirmed: false }));
  }
  {
    const app = instance(draftSource, callbackSource, { noDraft: true });
    app.resolve(acknowledged(app.previous, ['E-W1', 'E-W3'])); await app.link('E-W3');
    check('no mounted draft is not manufactured by a save receipt', app.receipts[0] === false && !app.drafts.useHasUnsavedDrafts());
  }
  {
    const app = instance(draftSource, callbackSource); const other = app.read('CASE-OTHER');
    other.set('question', '다른 접수 메모'); const beforeOther = structuredClone(app.read('CASE-OTHER').value);
    app.resolve(acknowledged(app.previous, ['E-W1', 'E-W3'])); await app.link('E-W3');
    check('another case draft is preserved byte for byte', same(app.read('CASE-OTHER').value, beforeOther));
    const current = app.updates[0], next = acknowledged(current, ['E-W1', 'E-W3', 'E-W4']);
    check('consecutive own saves advance from their actual predecessor', app.drafts.acceptOwnEvidenceSave(current, next, next.selectedEvidence) && app.read().value.formRevision === 6);
    check('replaying an older successful response does not rebase a newer draft', !app.drafts.acceptOwnEvidenceSave(app.previous, current, current.selectedEvidence) && app.read().value.formRevision === 6);
  }
  return checks;
}
const checks = await suite(source[files[1]], callbacks[0]);
const mutations = [];
for (const [name, from, to] of [
  ['stale guard removed', 'draft.formRevision !== previous.revision || ', ''],
  ['operation guard removed', ' || draft.operation', ''],
  ['confirmation reset removed', 'formRevision: saved.revision, confirmed: false', 'formRevision: saved.revision'],
  ['unrelated field guard removed', 'if (Array.from(keys).some(key => !allowed.has(key) && serial(previous[key]) !== serial(saved[key]))) return false;', ''],
]) {
  if (!source[files[1]].includes(from)) throw new Error('Mutation target missing: ' + name);
  const mutated = await suite(source[files[1]].replace(from, to), callbacks[0]);
  mutations.push({ name, detected: mutated.some(check => !check.pass), failures: mutated.filter(check => !check.pass).map(check => check.name) });
}
const disconnected = await suite(source[files[1]], callbacks[0].replace('acceptOwnEvidenceSave(active, saved, selectedEvidence);', ''));
mutations.push({ name: 'actual JSX receipt disconnected', detected: disconnected.some(check => !check.pass), failures: disconnected.filter(check => !check.pass).map(check => check.name) });
const output = path.resolve(process.env.EVIDENCE_SELF_SAVE_OUTPUT || path.join(root, '.local', 'evidence-self-save-unit-' + Date.now()));
fs.mkdirSync(output, { recursive: true });
const report = { finishedAt: new Date().toISOString(), method: 'Actual JSX + Home.save + actual memory draft store with deferred request boundary', sourceSha256: Object.fromEntries(files.map(file => [file, crypto.createHash('sha256').update(source[file]).digest('hex')])), serverStarts: 0, browserStarts: 0, networkCalls: 0, browserRecheck: 'NOT_RUN', checks, passed: checks.filter(check => check.pass).length, total: checks.length, mutations };
fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify({ output, passed: report.passed, total: report.total, mutations, failures: checks.filter(check => !check.pass).map(check => check.name) }));
if (report.passed !== report.total || mutations.some(mutation => !mutation.detected)) process.exitCode = 1;
