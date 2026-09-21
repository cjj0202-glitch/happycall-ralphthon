// Focused N02-M2 React SSR. No browser, HTTP server, API or fake product copy.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const appRequire = createRequire(path.join(root, 'apps/web/package.json'));
const React = appRequire('react');
const { renderToStaticMarkup } = appRequire('react-dom/server');
const ts = appRequire('typescript');
const sha = text => createHash('sha256').update(text).digest('hex');
const read = name => readFile(path.join(root, name), 'utf8');
const git = (...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trim();
const files = ['apps/web/components/CallReview.tsx', 'apps/web/app/page.tsx',
  'reports/pc2/integration.md', 'data/fixtures/cases.json'];
const sources = Object.fromEntries(await Promise.all(files.map(async file => [file, await read(file)])));
const compile = source => ts.transpileModule(source, { compilerOptions: {
  jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020,
  esModuleInterop: true,
} }).outputText;
const componentModule = { exports: {} };
new Function('require', 'module', 'exports', compile(sources[files[0]]))(
  name => name.endsWith('.css') ? new Proxy({}, { get: (_, key) => String(key) }) : appRequire(name),
  componentModule, componentModule.exports);
const CallReview = componentModule.exports.default;
assert.equal(typeof CallReview, 'function');

function makeCase(document, c, form, confirmed) {
  const match = document.match(/const reviewCase: CaseData = (\{[\s\S]*?\n\});/);
  assert.ok(match, 'Use actual integration example, fail if its structure changes');
  return new Function('c', 'form', 'confirmed', 'transcript', 'analysis', 'resultMode',
    `return ${match[1]}`)(c, form, confirmed, c.transcript, c.analysis, 'replay');
}
const fixture = JSON.parse(sources[files[3]]).cases.find(c => c.id === 'CASE-0002');
const saved = { ...fixture, reviewConfirmed: true, intake: { ...fixture.intake, quantity: 6 } };
let form = { ...saved.intake };
let confirmed = true;
let edited = false;
const fieldSource = sources[files[1]].match(/const field = .*?; \};/)[0];
const field = new Function('setForm', 'setEdited', 'setConfirmed',
  compile(`${fieldSource}\nreturn field;`))(
  fn => { form = fn(form); }, value => { edited = value; }, value => { confirmed = value; });
field('quantity', '999');
assert.equal(form.quantity, '999');
assert.equal(confirmed, false);
assert.equal(edited, true);
const oldDocument = git('show', '7ae648eb4bfb8f7e00ab842b39ad86e0df0ac134:reports/pc2/integration.md');
const confirmedText = '부모 화면에 상담원 확인 완료로 기록된 접수입니다.';
const count = html => html.split(confirmedText).length - 1;
const render = data => renderToStaticMarkup(React.createElement(CallReview, { caseData: data, transcriptMode: 'replay' }));
const checks = [];
const output = [];
const record = (name, pass, detail) => checks.push({ name, status: pass ? 'PASS' : 'FAIL', ...detail });
const oldCase = makeCase(oldDocument, saved, form, confirmed);
const oldHTML = render(oldCase);
record('original-failure-reproduced', count(oldHTML) === 1 && oldHTML.includes('999'),
  { expectedBug: true, confirmationLabels: count(oldHTML), edited999Visible: oldHTML.includes('999') });
for (const [savedFlag, currentFlag] of [[true, false], [false, true], [false, false], [true, true]]) {
  const c = { ...saved, reviewConfirmed: savedFlag };
  const review = makeCase(sources[files[2]], c, form, currentFlag);
  const html = render(review);
  const labelCount = count(html);
  record(`saved-${savedFlag}-current-${currentFlag}`, labelCount === Number(currentFlag)
    && html.includes('999') && review.intake.unit === form.unit && review.sourceText === c.sourceText
    && JSON.stringify(review.transcript) === JSON.stringify(c.transcript),
  { expectedLabels: Number(currentFlag), actualLabels: labelCount, currentQuantity: review.intake.quantity,
    unit: review.intake.unit, sourceAndTranscriptUnchanged: review.sourceText === c.sourceText
      && JSON.stringify(review.transcript) === JSON.stringify(c.transcript), markupSha256: sha(html) });
  output.push({ savedFlag, currentFlag, html });
}
// Mutation control: restoring the old omission must restore the stale-confirmation failure.
const mutated = sources[files[2]].replace(/^  reviewConfirmed: confirmed,.*\r?\n/m, '');
const mutatedHTML = render(makeCase(mutated, saved, form, false));
record('missing-prop-mutation-caught', count(mutatedHTML) === 1, { staleLabels: count(mutatedHTML) });
const beforeHashes = Object.fromEntries(files.map(file => [file, sha(sources[file])]));
const afterHashes = Object.fromEntries(await Promise.all(files.map(async file => [file, sha(await read(file))])));
record('inputs-unchanged', JSON.stringify(beforeHashes) === JSON.stringify(afterHashes), {});
const report = { at: new Date().toISOString(), head: git('rev-parse', 'HEAD'),
  node: process.version, react: React.version, typescript: ts.version,
  method: 'Actual TSX in-memory transpile and React renderToStaticMarkup; actual parent field callback invoked with state collectors; actual old/new documentation object expressions evaluated.',
  limits: 'No browser, clicks, hydration, CSS layout, full parent page, save/API or media playback executed.',
  original: { savedQuantity: 6, editedQuantity: form.quantity, parentConfirmed: confirmed,
    reviewCaseConfirmed: oldCase.reviewConfirmed, confirmationLabels: count(oldHTML) },
  beforeHashes, afterHashes, checks, passed: checks.filter(c => c.status === 'PASS').length,
  failed: checks.filter(c => c.status === 'FAIL').length };
await mkdir(path.join(root, 'reports/pc2'), { recursive: true });
await writeFile(path.join(root, 'reports/pc2/confirmation-ssr.json'), JSON.stringify(report, null, 2) + '\n');
await mkdir(path.join(root, '.local/pc2-confirmation-ssr'), { recursive: true });
for (const item of output) await writeFile(path.join(root, '.local/pc2-confirmation-ssr', `saved-${item.savedFlag}-current-${item.currentFlag}.html`), item.html);
console.log(JSON.stringify(report, null, 2));
if (report.failed) process.exitCode = 1;
