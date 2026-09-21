// Production TSX + real React SSR. No browser, server, network, ledger or case-store access.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url), root = path.resolve(import.meta.dirname, '../..');
const webRequire = createRequire(path.join(root, 'apps/web/package.json'));
const ts = webRequire('typescript'), React = webRequire('react');
const jsxRuntime = webRequire('react/jsx-runtime'), { renderToStaticMarkup } = webRequire('react-dom/server');
const files = ['apps/web/components/NotificationStatus.tsx', 'apps/web/lib/types.ts', 'apps/web/app/page.tsx'];
const sources = Object.fromEntries(files.map(file => [file, fs.readFileSync(path.join(root, file), 'utf8')]));
const checks = [], mutations = [];
function check(name, pass, detail = null) { checks.push({ name, pass: !!pass, detail }); if (!pass) throw new Error(name); }
function compile(source, imports = {}) {
  const module = { exports: {} };
  const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true } }).outputText;
  new Function('require', 'module', 'exports', code)(name => {
    if (!(name in imports)) throw new Error('Unregistered import: ' + name);
    return imports[name];
  }, module, module.exports);
  return module.exports;
}
const componentSource = sources[files[0]], NotificationStatus = compile(componentSource, { 'react/jsx-runtime': jsxRuntime }).default;
const baseCase = { id: 'CASE-UI-1', revision: 7, type: 'missing', title: '합성 문의', store: { id: 'SYN-STORE', name: '합성 점포' }, channel: 'text', sourceText: 'RAW-SOURCE-SENTINEL', status: 'handed_off', reply: 'SAVED-REPLY-SENTINEL', pendingActions: [], selectedEvidence: [] };
const hash = char => char.repeat(64);
const record = (overrides = {}) => ({ schemaVersion: 1, id: hash('a'), caseId: baseCase.id, caseRevision: 4, kind: 'handoff', channel: 'teams', recipientRole: 'center', recipientRef: 'center:' + hash('b'), createdAt: '2026-09-21T17:00:01.123456+00:00', status: 'not_connected', reason: 'delivery_not_configured', ...overrides });
const allRecords = [
  record(),
  record({ id: hash('c'), kind: 'interim_reply', recipientRole: 'counselor', recipientRef: 'counselor:' + hash('d') }),
  record({ id: hash('e'), kind: 'final_reply', recipientRole: 'counselor', recipientRef: 'counselor:' + hash('d') }),
  record({ id: hash('f'), kind: 'final_reply', channel: 'kakao', recipientRole: 'owner', recipientRef: 'owner:' + hash('1') }),
];
function render(outbox, audience = 'workforce', caseChanges = {}, Component = NotificationStatus) {
  return renderToStaticMarkup(React.createElement(Component, { caseData: { ...baseCase, notificationOutbox: outbox, ...caseChanges }, audience }));
}
const recordCount = html => (html.match(/<dt>알림 종류<\/dt>/g) || []).length;
const held = html => html.includes('기록 확인 필요') && recordCount(html) === 0;
const confidential = ['RAW-SOURCE-SENTINEL', 'SAVED-REPLY-SENTINEL', 'center:' + hash('b'), 'counselor:' + hash('d'), 'owner:' + hash('1')];
const safe = html => confidential.every(value => !html.includes(value)) && !html.includes('<script') && !html.includes('javascript:') && !html.includes('https://private.invalid');
const normal = render(allRecords);
const css = fs.readFileSync(path.join(root, 'apps/web/app/globals.css'), 'utf8');
const reusedClasses = [...new Set([...componentSource.matchAll(/className="([^"]+)"/g)].flatMap(match => match[1].split(/\s+/)))];
check('all seven component class tokens already exist in the current stylesheet', reusedClasses.length === 7 && reusedClasses.every(name => css.includes('.' + name)), reusedClasses);
check('component adds no inline style color font or CSS payload', !/style=|<style|#[0-9a-f]{3,8}\b|font-family/i.test(componentSource));
check('all four allowed combinations render actual React markup', recordCount(normal) === 4 && ['센터 전달', '중간 회신', '최종 회신', 'Teams · 담당 센터', 'Teams · 담당 상담원', '카카오톡 · 경영주'].every(label => normal.includes(label)));
check('collapsed summary always shows disconnected and has no open attribute', /^<details class="panel" aria-label="외부 알림"><summary>외부 알림 /.test(normal) && normal.includes('연결 안 됨') && !normal.includes('<details open'));
check('stored time is normalized and explicitly KST', normal.includes('2026-09-21T17:00:01.123Z') && normal.includes('02:00:01') && normal.includes('KST'));
check('normal output hides identifiers hashes source and reply', safe(normal) && !normal.includes(baseCase.id) && !normal.includes(hash('a')));
check('actual delivery is explicitly absent without success affordance', normal.includes('실제 외부 메시지로 전송되지 않았습니다') && !normal.includes('badge success') && !normal.includes('<button') && !normal.includes('<a '));
for (const [name, value] of [['absent optional field', undefined], ['empty array', []]]) {
  const html = render(value);
  check(name + ' says no stored record without inferring historic deliveries', html.includes('저장된 알림 기록 없음') && !html.includes('기록 확인 필요') && !html.includes('전송되지 않았습니다') && recordCount(html) === 0);
}
for (const [name, value] of [['null', null], ['object', {}], ['string', 'RAW-SOURCE-SENTINEL'], ['number', 0], ['boolean', false]]) check(name + ' outbox is withheld', held(render(value)) && safe(render(value)));
for (const [name, value] of [['null', null], ['array', []], ['string', 'RAW-SOURCE-SENTINEL'], ['number', 1], ['boolean', true]]) check(name + ' row is withheld', held(render([value])) && safe(render([value])));
for (const field of Object.keys(record())) {
  const value = record(); delete value[field];
  check('missing required field ' + field + ' is withheld', held(render([value])));
}
const invalid = [
  ['schema version string', { schemaVersion: '1' }], ['schema version boolean', { schemaVersion: true }], ['schema version future', { schemaVersion: 2 }],
  ['id uppercase hash', { id: hash('A') }], ['id wrong length', { id: 'abc' }], ['id object', { id: {} }],
  ['different case', { caseId: 'CASE-OTHER' }], ['case nonstring', { caseId: [baseCase.id] }],
  ['revision zero', { caseRevision: 0 }], ['revision negative', { caseRevision: -1 }], ['revision fraction', { caseRevision: 1.5 }], ['revision string', { caseRevision: '4' }], ['revision future', { caseRevision: 8 }], ['revision unsafe', { caseRevision: Number.MAX_SAFE_INTEGER + 1 }],
  ['kind unknown', { kind: 'sent' }], ['kind prototype name', { kind: 'toString' }], ['kind array', { kind: ['handoff'] }],
  ['channel unknown', { channel: 'email' }], ['channel prototype name', { channel: '__proto__' }], ['channel array', { channel: ['teams'] }],
  ['role unknown', { recipientRole: 'admin' }], ['role array', { recipientRole: ['center'] }],
  ['ref null without missing reason', { recipientRef: null }], ['ref role mismatch', { recipientRef: 'owner:' + hash('b') }], ['ref uppercase', { recipientRef: 'center:' + hash('B') }], ['ref raw recipient', { recipientRef: '010-1234-5678' }], ['ref object', { recipientRef: {} }],
  ['time invalid', { createdAt: 'bad time' }], ['time missing timezone', { createdAt: '2026-09-21T17:00:01' }], ['time date only', { createdAt: '2026-09-21' }], ['time impossible day', { createdAt: '2026-02-30T17:00:01Z' }], ['time impossible month', { createdAt: '2026-13-01T17:00:01Z' }], ['time rollover', { createdAt: '2026-09-21T24:00:00Z' }], ['time invalid offset', { createdAt: '2026-09-21T17:00:01+24:00' }], ['time object', { createdAt: {} }],
  ['status sent', { status: 'sent' }], ['status pending', { status: 'pending' }], ['status array', { status: ['not_connected'] }],
  ['reason unknown', { reason: 'failed' }], ['reason object', { reason: {} }], ['center missing recipient', { reason: 'missing_recipient', recipientRef: null }],
  ['extra raw source', { sourceText: 'RAW-SOURCE-SENTINEL' }], ['extra url', { url: 'https://private.invalid/secret' }],
];
for (const [name, change] of invalid) check(name + ' is withheld with no raw output', held(render([record(change)])) && safe(render([record(change)])));
for (const kind of ['handoff', 'interim_reply', 'final_reply']) for (const channel of ['teams', 'kakao']) for (const role of ['center', 'counselor', 'owner']) {
  const allowed = allRecords.some(row => row.kind === kind && row.channel === channel && row.recipientRole === role);
  const html = render([record({ kind, channel, recipientRole: role, recipientRef: role + ':' + hash('b') })]);
  check('combination ' + [kind, channel, role].join('/') + ' is ' + (allowed ? 'visible' : 'withheld'), allowed ? recordCount(html) === 1 && !html.includes('기록 확인 필요') : held(html));
}
for (const createdAt of ['2024-02-29T23:59:59Z', '2026-09-22T02:00:01+09:00']) check('valid ISO boundary ' + createdAt, recordCount(render([record({ createdAt })])) === 1);
check('current saved revision boundary renders', recordCount(render([record({ caseRevision: 7 })])) === 1);
check('outbox without verifiable saved revision is withheld', held(render([record()], 'workforce', { revision: undefined })));
const missingOwner = { ...allRecords[3], recipientRef: null, reason: 'missing_recipient' };
check('missing owner recipient is disconnected and explicit', recordCount(render([missingOwner], 'owner')) === 1 && render([missingOwner], 'owner').includes('수신 대상 확인 필요'));
check('missing-recipient owner with a ref is withheld', held(render([{ ...missingOwner, recipientRef: 'owner:' + hash('1') }], 'owner')));
const owner = render(allRecords, 'owner');
check('owner sees only own-role Kakao final record', recordCount(owner) === 1 && owner.includes('카카오톡 · 경영주') && !owner.includes('Teams') && !owner.includes('담당 상담원') && !owner.includes('담당 센터'));
check('owner without owner-targeted records has explicit empty state', render(allRecords.slice(0, 3), 'owner').includes('저장된 알림 기록 없음'));
check('other-case owner record is withheld without channel or role detail', held(render([{ ...allRecords[3], caseId: 'CASE-OTHER' }], 'owner')) && !render([{ ...allRecords[3], caseId: 'CASE-OTHER' }], 'owner').includes('카카오톡'));
check('unknown audience cannot reveal records', held(render(allRecords, 'admin')));
check('mixed malformed and valid rows do not hide the review warning', recordCount(render([record(), null])) === 1 && render([record(), null]).includes('기록 확인 필요'));
check('duplicate ids render once and flag review', recordCount(render([record(), record()])) === 1 && render([record(), record()]).includes('기록 확인 필요'));
const htmlAttack = '<script>alert("PRIVATE-HTML-SENTINEL")</script>';
check('HTML payload and raw values never enter component markup', held(render([record({ createdAt: htmlAttack })])) && !render([record({ createdAt: htmlAttack })]).includes('PRIVATE-HTML-SENTINEL'));
check('matching arbitrary case id remains undisclosed', recordCount(render([record({ caseId: htmlAttack })], 'workforce', { id: htmlAttack })) === 1 && !render([record({ caseId: htmlAttack })], 'workforce', { id: htmlAttack }).includes('PRIVATE-HTML-SENTINEL'));

// Render the actual three page components, preserving React hooks and actual notification markup.
// Only unrelated scene components and draft/API IO are replaced by strict local stubs.
const captured = [], draftReads = [];
let draftChanges = {};
function BoundNotification(props) { captured.push(props); return React.createElement(NotificationStatus, props); }
const pageImports = {
  react: React, 'react/jsx-runtime': jsxRuntime,
  '@/components/NotificationStatus': BoundNotification,
  '@/components/CallReview': () => null, '@/components/WmsScene': () => null, '@/components/TmsScene': () => null,
  '@/lib/api': { ApiError: class extends Error {}, request() { throw new Error('Network/API call forbidden in SSR'); } },
  '@/lib/drafts': { useHasUnsavedDrafts: () => true, useSessionDraft(key, initial) { draftReads.push(key); return { value: { ...initial, ...draftChanges }, set() { throw new Error('Draft write forbidden in SSR'); }, replace() { throw new Error('Draft replace forbidden in SSR'); } }; } },
  '@/lib/workflow': compile(fs.readFileSync(path.join(root, 'apps/web/lib/workflow.ts'), 'utf8')),
};
const page = compile(sources[files[2]] + '\nexport { Desk, Center, Owner };', pageImports);
const savedCase = { ...baseCase, notificationOutbox: allRecords };
const noAction = () => { throw new Error('No interactions during SSR'); };
const sharedProps = { caseData: savedCase, mode: 'replay', fallback: false, onUpdate: noAction, onSave: noAction, onView: noAction, onToast: noAction };
for (const [name, expectedAudience] of [['Desk', 'workforce'], ['Center', 'workforce'], ['Owner', 'owner']]) {
  draftChanges = { notificationOutbox: [record({ kind: 'UNSAVED-ALERT-SENTINEL' })], reply: 'UNSAVED-REPLY-SENTINEL' };
  captured.length = 0;
  const props = name === 'Owner' ? { cases: [{ ...baseCase, id: 'CASE-OTHER' }, savedCase], selected: savedCase.id, onSelect: noAction, onCreated: noAction, onToast: noAction, onDesk: noAction, fallback: false } : sharedProps;
  const html = renderToStaticMarkup(React.createElement(page[name], props));
  check(name + ' actual callsite passes exact saved object and audience', captured.length === 1 && captured[0].caseData === savedCase && captured[0].audience === expectedAudience);
  check(name + ' actual callsite renders only saved notifications', recordCount(html) === (name === 'Owner' ? 1 : 4) && !html.includes('UNSAVED-ALERT-SENTINEL'));
  check(name + ' notification follows existing action or reply', html.indexOf('aria-label="외부 알림"') > html.indexOf(name === 'Desk' ? '접수 내용 저장' : name === 'Center' ? '최종 회신·처리 완료' : '센터에서 보낸 회신'));
}
const escaping = renderToStaticMarkup(React.createElement(page.Center, { ...sharedProps, caseData: { ...savedCase, title: htmlAttack } }));
check('actual React page SSR escapes untrusted text instead of injecting HTML', escaping.includes('&lt;script&gt;alert(&quot;PRIVATE-HTML-SENTINEL&quot;)&lt;/script&gt;') && !escaping.includes('<script'));
check('actual three draft roles were reached without writes', ['desk:CASE-UI-1', 'center:CASE-UI-1', 'owner:new'].every(key => draftReads.includes(key)));

for (const mutation of [
  { name: 'case binding removed', from: 'row.caseId !== caseData.id', to: 'false', input: [record({ caseId: 'CASE-OTHER' })], audience: 'workforce', rejects: held },
  { name: 'owner filter removed', from: "if (audience === 'workforce' || (audience === 'owner' && row.channel === 'kakao' && row.recipientRole === 'owner'))", to: 'if (true)', input: allRecords, audience: 'owner', rejects: html => recordCount(html) === 1 && !html.includes('Teams') },
  { name: 'status guard removed', from: "row.status !== 'not_connected'", to: 'false', input: [record({ status: 'sent' })], audience: 'workforce', rejects: held },
  { name: 'future revision guard removed', from: '(row.caseRevision as number) > (caseData.revision as number)', to: 'false', input: [record({ caseRevision: 8 })], audience: 'workforce', rejects: held },
]) {
  check(mutation.name + ' control exists in current source', componentSource.includes(mutation.from));
  const mutant = compile(componentSource.replace(mutation.from, mutation.to), { 'react/jsx-runtime': jsxRuntime }).default;
  const detected = !mutation.rejects(render(mutation.input, mutation.audience, {}, mutant));
  mutations.push({ name: mutation.name, detected });
  check(mutation.name + ' is caught by the same render assertion', detected);
}
const report = { observedAt: new Date().toISOString(), passed: checks.filter(c => c.pass).length, total: checks.length, sourceSha256: Object.fromEntries(files.map(file => [file, crypto.createHash('sha256').update(sources[file]).digest('hex')])), serverStarts: 0, browserStarts: 0, networkCalls: 0, caseStoreReads: 0, caseStoreWrites: 0, browserLayoutAndInteraction: 'NOT_RUN', mutations, checks };
console.log(JSON.stringify(report, null, 2));
