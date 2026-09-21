// Render the real component. No server, network, paid calls, or fixture edits.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { createRequire } = require('node:module');
const { createHash } = require('node:crypto');
const root = path.resolve(__dirname, '../..');
const file = path.join(root, 'apps/web/components/LogisticsView.tsx');
const req = createRequire(file);
const ts = req('typescript');
const React = req('react');
const { renderToStaticMarkup } = req('react-dom/server');
const source = fs.readFileSync(file, 'utf8');
const fixtures = JSON.parse(fs.readFileSync(path.join(root, 'data/fixtures/cases.json'), 'utf8'));
assert.equal(fixtures.synthetic, true);

function component(text) {
  const compiled = ts.transpileModule(text, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
  } }).outputText;
  const mod = { exports: {} };
  new Function('require', 'module', 'exports', compiled)(
    name => name.endsWith('.css') ? { __esModule: true, default: {} } : req(name), mod, mod.exports,
  );
  return mod.exports.default;
}
const decode = value => value.replace(/&quot;/g, '"').replace(/&#x27;/g, "'")
  .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
function render(View, values, asOf = '2026-09-18T07:00:00+09:00') {
  const c = structuredClone(fixtures.cases[0]);
  c.asOf = asOf;
  c.tms.stops.forEach(stop => Object.assign(stop, { actual: null, mobileEntry: null, mobileExit: null }));
  const target = c.tms.stops.find(stop => stop.id === c.store.id);
  assert.ok(target, 'A matching selected stop is required');
  Object.assign(target, values);
  const html = renderToStaticMarkup(React.createElement(View, {
    kind: 'tms', caseData: c, onBack() {}, onLinkEvidence() {},
  }));
  const originals = Array.from(html.matchAll(/<pre[^>]*>([\s\S]*?)<\/pre>/g))
    .map(match => JSON.parse(decode(match[1]))).filter(value => Object.hasOwn(value, 'planned'));
  assert.equal(originals.length, 1, 'Inspect the selected original stop, not an unrelated element');
  return { html, original: originals[0] };
}
const future = {
  planned: '2026-09-18T07:01:00+09:00', actual: '2026-09-18T07:02:00+09:00',
  mobileEntry: '2026-09-18T07:03:00+09:00', mobileExit: '2026-09-18T07:04:00+09:00',
};
function check(View) {
  const results = [];
  const test = (name, action) => {
    try { action(); results.push({ name, pass: true }); }
    catch (error) { results.push({ name, pass: false, error: error.message }); }
  };
  test('future plan remains visible in map, table, and original', () => {
    const { html, original } = render(View, future);
    assert.equal(original.planned, future.planned);
    assert.ok((html.match(/07:01/g) || []).length >= 3);
    assert.ok(!html.includes('기준시각 이후 / 미표시'));
  });
  test('future actual, mobile entry, and exit remain withheld', () => {
    const { html, original } = render(View, future);
    for (const field of ['actual', 'mobileEntry', 'mobileExit']) assert.equal(original[field], null);
    assert.ok(html.includes('0 / 3개'));
  });
  test('records at exactly asOf are included', () => {
    const exact = Object.fromEntries(Object.keys(future).map(key => [key, '2026-09-18T07:00:00+09:00']));
    const { html, original } = render(View, exact);
    for (const key of Object.keys(exact)) assert.equal(original[key], exact[key]);
    assert.ok(html.includes('1 / 3개'));
  });
  test('null plan stays unregistered', () => {
    const { html, original } = render(View, { ...future, planned: null });
    assert.equal(original.planned, null);
    assert.ok(html.includes('규정 미등록'));
  });
  test('malformed plan shows uncertainty and preserves its original', () => {
    const { html, original } = render(View, { ...future, planned: 'not-a-time' });
    assert.equal(original.planned, 'not-a-time');
    assert.ok(html.includes('시각 확인 필요'));
  });
  test('invalid asOf keeps plan but withholds actual records', () => {
    const { original } = render(View, future, 'invalid-asof');
    assert.equal(original.planned, future.planned);
    for (const field of ['actual', 'mobileEntry', 'mobileExit']) assert.equal(original[field], null);
  });
  return results;
}
const result = check(component(source));
const gate = 'function atOrBefore(value: unknown, asOf: unknown): boolean {';
assert.equal(source.split(gate).length, 2, 'Mutant must reach the actual-record gate');
const mutant = check(component(source.replace(gate, gate + '\n  return true;')));
assert.ok(mutant.some(item => item.name.startsWith('future actual') && !item.pass));
assert.ok(mutant.some(item => item.name.startsWith('invalid asOf') && !item.pass));
const report = {
  suite: 'tms-time-semantics-real-component-ssr',
  sourceSha256: createHash('sha256').update(source).digest('hex'),
  passed: result.filter(item => item.pass).length, total: result.length, result,
  unsafeMutantFailures: mutant.filter(item => !item.pass).map(item => item.name),
  scope: 'SSR meaning and source preservation, not browser layout or keyboard behavior',
};
console.log(JSON.stringify(report, null, 2));
assert.equal(report.passed, report.total);
