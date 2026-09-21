/* N04: no browser/API/payable calls. Fixed expectations for synthetic TMS contracts. */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');

const root = path.resolve(__dirname, '../../..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
const ts = require(path.join(root, 'apps/web/node_modules/typescript'));
const modulePath = 'apps/web/components/TmsScene.tsx';
const compiled = ts.transpileModule(read(modulePath), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
}).outputText;
const loaded = { exports: {} };
const loader = id => id.endsWith('.css') ? {} : id.includes('pc4-tms.json')
  ? JSON.parse(read('data/overlays/pc4-tms.json'))
  : id.includes('fixtures/cases.json') ? JSON.parse(read('data/fixtures/cases.json'))
  : require(path.join(root, 'apps/web/node_modules', id));
new Function('require', 'module', 'exports', compiled)(loader, loaded, loaded.exports);
const { tmsTimestamp, tmsTime, tmsRelationIssue, tmsEvidenceIssue } = loaded.exports;
const cases = JSON.parse(read('data/fixtures/cases.json')).cases;
const inputPaths = [modulePath, 'apps/web/components/TmsScene.module.css', 'data/overlays/pc4-tms.json', 'data/fixtures/cases.json', 'tests/remote/pc4/tms-contract-check.cjs'];
const results = [];
const mutate = (original, mutation) => { const next = structuredClone(original); mutation(next); return next; };

// Expected values below are human-selected outcomes, not recomputed by the implementation.
function check(name, expected, observed, predicate) {
  let actual;
  try {
    actual = observed();
    predicate(actual);
    results.push({ name, expected, actual, status: 'PASS' });
    process.stdout.write(`PASS ${name}\n`);
  } catch (error) {
    results.push({ name, expected, actual: actual ?? null, status: 'FAIL', error: error.message });
    process.stdout.write(`FAIL ${name}: ${error.message}\n`);
  }
}
const equals = expected => actual => assert.deepEqual(actual, expected);
const rejected = actual => assert.ok(typeof actual === 'string' && actual.length > 0, 'Expected explicit rejection reason');

check('two synthetic relations accepted', [null, null], () => cases.map(tmsRelationIssue), equals([null, null]));
check('known TMS evidence accepted', [null, null, null], () => cases.flatMap(c => c.evidence.filter(e => e.system === 'TMS').map(e => tmsEvidenceIssue(c, e))), equals([null, null, null]));
check('null remains missing', '미등록', () => tmsTime(null, cases[0].asOf, '2026-09-18').label, equals('미등록'));
check('numeric zero rejected', 'invalid', () => tmsTime(0, cases[0].asOf, '2026-09-18').state, equals('invalid'));
check('real midnight accepted', '00:00 KST', () => tmsTime('2026-09-18T00:00:00+09:00', cases[0].asOf, '2026-09-18').label, equals('00:00 KST'));
check('invalid calendar rejected', null, () => tmsTimestamp('2026-02-30T05:00:00+09:00'), equals(null));
check('timezone missing rejected', null, () => tmsTimestamp('2026-09-18T05:00:00'), equals(null));
check('HH:mm preserved without invented date', 'local', () => tmsTime('05:00', cases[0].asOf, '2026-09-18').state, equals('local'));
check('future actual masked', 'future', () => tmsTime('2026-09-18T07:01:00+09:00', cases[0].asOf, '2026-09-18').state, equals('future'));
check('prior day retains date', '2026-09-17 23:59 KST', () => tmsTime('2026-09-17T23:59:00+09:00', cases[0].asOf, '2026-09-18').label, equals('2026-09-17 23:59 KST'));
check('same instant UTC displayed KST', '00:00 KST', () => tmsTime('2026-09-17T15:00:00Z', cases[0].asOf, '2026-09-18').label, equals('00:00 KST'));
check('unknown asOf not confirmed', 'unbounded', () => tmsTime('2026-09-18T05:00:00+09:00', null, '2026-09-18').state, equals('unbounded'));

const relationAttacks = [
  ['store', c => { c.store.id = 'OTHER'; }],
  ['date', c => { c.tms.bizDate = '2026-09-19'; }],
  ['vehicle', c => { c.tms.vehicle = 'OTHER'; }],
  ['route', c => { c.tms.routeId = 'OTHER'; }],
  ['center', c => { c.tms.centerId = 'OTHER'; }],
  ['duplicate sequence', c => { c.tms.stops[1].sequence = 1; }],
  ['target record time', c => { c.tms.stops[0].planned = '2026-09-19T05:00:00+09:00'; }],
  ['target row foreign identity', c => { c.tms.stops[0].caseId = 'OTHER'; }],
  ['TMS foreign identity', c => { c.tms.caseId = 'OTHER'; }],
  ['unlinked relation', c => { c.tms.relationStatus = 'unlinked'; }],
  ['different confirmed intake store', c => { c.intake = { storeId: 'OTHER' }; }],
];
for (const [name, mutation] of relationAttacks) check(`${name} blocked`, 'explicit rejection reason', () => tmsRelationIssue(mutate(cases[0], mutation)), rejected);
check('foreign evidence rejected', 'explicit rejection reason', () => tmsEvidenceIssue(cases[0], cases[1].evidence.find(e => e.system === 'TMS')), rejected);
check('evidence date injection rejected', 'explicit rejection reason', () => {
  const c = mutate(cases[0], c => { c.evidence[0].time = '2026-09-19T05:00:00+09:00'; });
  return tmsEvidenceIssue(c, c.evidence[0]);
}, rejected);
check('explicit evidence wrong store rejected', 'explicit rejection reason', () => {
  const c = mutate(cases[0], c => { c.evidence[0].storeId = 'OTHER'; });
  return tmsEvidenceIssue(c, c.evidence[0]);
}, rejected);
check('same evidence ID duplicate rejected', 'explicit rejection reason', () => {
  const c = mutate(cases[0], c => { c.evidence.push(c.evidence[0]); });
  return tmsEvidenceIssue(c, c.evidence[0]);
}, rejected);

// This follows CaseService.intake's return shape: explicit reference, copied immutable source context.
const textIntake = source => ({ ...structuredClone(source), id: 'INT-A1B2C3D4', channel: 'text', synthetic: true,
  linkedFixtureId: source.id, storeId: source.store.id, subject: source.intake.subject, title: source.intake.subject,
  intake: { storeId: source.store.id, subject: source.intake.subject, quantity: null, unit: null, request: '합성 확인 요청' },
  selectedEvidence: [], revision: 0 });
check('explicitly linked text relations accepted', [null, null], () => cases.map(source => tmsRelationIssue(textIntake(source))), equals([null, null]));
check('explicitly linked text TMS evidence accepted', [null, null, null], () => cases.flatMap(source => {
  const c = textIntake(source); return c.evidence.filter(e => e.system === 'TMS').map(e => tmsEvidenceIssue(c, e));
}), equals([null, null, null]));
for (const [name, mutation] of [
  ['missing explicit reference', c => { delete c.linkedFixtureId; }],
  ['wrong explicit reference', c => { c.linkedFixtureId = 'CASE-0001'; }],
  ['unknown explicit reference', c => { c.linkedFixtureId = 'CASE-UNKNOWN'; }],
  ['different store', c => { c.store.id = 'OTHER'; }],
  ['different date', c => { c.tms.bizDate = '2026-09-19'; }],
  ['different type', c => { c.type = 'missing'; }],
  ['different asOf', c => { c.asOf = '2026-09-19T07:00:00+09:00'; }],
  ['different original subject', c => { c.subject = '다른 문의'; }],
  ['changed TMS neighbour row', c => { c.tms.stops[0].actual = null; }],
  ['changed copied evidence', c => { c.evidence[0].value = '다른 근거'; }],
]) check(`linked text ${name} blocked`, 'explicit rejection reason', () => tmsRelationIssue(mutate(textIntake(cases[1]), mutation)), rejected);

const failed = results.filter(result => result.status === 'FAIL').length;
const report = {
  task: 'N04', scope: 'TMS module self-check; not independent acceptance or end-to-end workflow',
  executedAt: new Date().toISOString(), timezone: 'UTC; Korea UTC+09:00',
  head: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(),
  node: process.version, platform: `${process.platform}/${process.arch}`,
  command: 'node tests/remote/pc4/tms-contract-check.cjs',
  sources: inputPaths.map(name => ({ path: name, sha256: crypto.createHash('sha256').update(fs.readFileSync(path.join(root, name))).digest('hex') })),
  total: results.length, passed: results.length - failed, failed, apiCalls: 0, results,
};
const output = path.join(root, 'reports/pc4/tms-contract-results.json');
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n');
process.stdout.write(`TOTAL ${results.length} · PASS ${results.length - failed} · FAIL ${failed}\n`);
process.exitCode = failed ? 1 : 0;
