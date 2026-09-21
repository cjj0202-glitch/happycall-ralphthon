/* Independent pc3 review regression cases. Uses in-memory registrations only.
 * Run from any directory: node tests/remote/pc3/registration-review.cjs
 * Does not change fixture/manifest, install media, open a browser, or call APIs.
 */
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');

const root = path.resolve(__dirname, '../../..');
const webRequire = createRequire(path.join(root, 'apps/web/package.json'));
const ts = webRequire('typescript');
const React = webRequire('react');
const { renderToStaticMarkup } = webRequire('react-dom/server');
const read = relative => fs.readFileSync(path.join(root, relative), 'utf8');
const parse = relative => JSON.parse(read(relative).replace(/^\uFEFF/, ''));
const fixturePath = 'data/fixtures/cases.json';
const manifestPath = 'data/demo-media-manifest.json';
const fixtureSource = read(fixturePath);
const manifestSource = read(manifestPath);
const fixture = parse(fixturePath);
const manifest = parse(manifestPath);
const overlay = parse('data/overlays/pc3-wms.json');
const copy = value => JSON.parse(JSON.stringify(value));
const compiled = ts.transpileModule(read('apps/web/components/WmsScene.tsx'), {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    jsx: ts.JsxEmit.ReactJSX,
    esModuleInterop: true,
  },
}).outputText;

function load(fixtureCopy = fixture, manifestCopy = manifest) {
  const moduleObject = { exports: {} };
  const localRequire = specifier => {
    if (specifier.endsWith('/fixtures/cases.json')) return fixtureCopy;
    if (specifier.endsWith('/demo-media-manifest.json')) return manifestCopy;
    if (specifier.endsWith('.module.css')) return {};
    return webRequire(specifier);
  };
  new Function('require', 'module', 'exports', compiled)(
    localRequire, moduleObject, moduleObject.exports,
  );
  return moduleObject.exports;
}

const api = load();
const wrongCase = () => copy(fixture.cases.find(item => item.id === 'CASE-0002'));
const sorter = caseData => caseData.wms.events.find(item => item.id === 'W-W3');
const render = caseData => renderToStaticMarkup(React.createElement(api.default, {
  caseData, onBack() {}, onLinkEvidence() {},
}));
const results = [];
function check(name, fn) {
  try { fn(); results.push({ name, passed: true }); }
  catch (error) { results.push({ name, passed: false, error: error.message }); }
}
function rejected(result) {
  assert.equal(result.clip, undefined);
  assert.ok(result.reason.length > 0);
}

check('existing CASE2 W-W3 registration remains playable', () => {
  const caseData = wrongCase();
  assert.equal(api.validateWmsClip(caseData, sorter(caseData)).clip.id, 'SYN-CCTV-CASE2-SORTER');
});
check('CASE1 remains without registered video', () => {
  const caseData = copy(fixture.cases[0]);
  rejected(api.validateWmsClip(caseData, caseData.wms.events[0]));
});
check('previous-business-day process rows block same-day video', () => {
  const caseData = wrongCase();
  caseData.wms.picking.pickedAt = '2026-09-17T02:15:00+09:00';
  caseData.wms.sorting.sortedAt = '2026-09-17T02:33:00+09:00';
  caseData.wms.shipping.time = '2026-09-17T03:02:00+09:00';
  assert.ok(api.inspectWms(caseData).contextError);
  rejected(api.validateWmsClip(caseData, sorter(caseData)));
});
for (const [key, value] of [['caseId', 'CASE-0001'], ['system', 'TMS']]) {
  check(`foreign event ${key} rejected`, () => {
    const caseData = wrongCase();
    sorter(caseData)[key] = value;
    rejected(api.validateWmsClip(caseData, sorter(caseData)));
  });
}
for (const [key, value] of [
  ['businessDate', '2026-09-17'], ['asOf', '2026-09-17T07:00:00+09:00'],
]) {
  check(`foreign media relations.${key} rejected`, () => {
    const caseData = wrongCase();
    caseData.media[0].relations = { [key]: value };
    rejected(api.validateWmsClip(caseData, sorter(caseData)));
  });
}
check('CASE1 evidence E-M3 cannot be linked from CASE2', () => {
  const caseData = wrongCase();
  caseData.evidence.push(copy(fixture.cases[0].evidence.find(item => item.id === 'E-M3')));
  const html = render(caseData);
  const button = html.match(/<button[^>]*data-testid="link-E-M3"[^>]*>(.*?)<\/button>/);
  assert.ok(button, 'Foreign evidence should have an explicit disabled state');
  assert.match(button[0], /\bdisabled=""/);
  assert.match(button[1], /사건 근거 불일치/);
});
check('missing sorter-input event preserves subsequent stage labels', () => {
  const caseData = wrongCase();
  caseData.wms.events = caseData.wms.events.filter(item => item.id !== 'W-W2');
  const html = render(caseData);
  const branch = html.match(/data-testid="event-W-W3"[^>]*><small>(.*?)<\/small>/);
  const shipping = html.match(/data-testid="event-W-W4"[^>]*><small>(.*?)<\/small>/);
  assert.match(branch?.[1] || '', /분기 \/ 슈트/);
  assert.match(shipping?.[1] || '', /출고/);
});
check('selected branch after preceding events omitted has branch next action', () => {
  const caseData = wrongCase();
  caseData.wms.events = caseData.wms.events.filter(item => item.id === 'W-W3' || item.id === 'W-W4');
  assert.match(render(caseData), /계획·실적 슈트와 분기 전후 연결을 확인하세요/);
});

function registration(candidate, append = false) {
  const fixtureCopy = copy(fixture), manifestCopy = copy(manifest);
  const registered = copy(candidate);
  registered.registrationStatus = 'registered-for-memory-review';
  const caseData = fixtureCopy.cases.find(item => item.id === registered.caseId);
  caseData.media = append ? [...caseData.media, registered] : [registered];
  manifestCopy.assets.push({
    name: registered.url.slice('/demo/'.length), bytes: registered.bytes,
    sha256: registered.sha256, durationSeconds: registered.durationSeconds,
    synthetic: true,
  });
  return { caseData, registered, api: load(fixtureCopy, manifestCopy) };
}

for (const candidate of overlay.mediaCandidates) {
  check(`${candidate.id}: unregistered candidate stays blocked`, () => {
    const caseData = copy(fixture.cases.find(item => item.id === candidate.caseId));
    caseData.media = [copy(candidate)];
    rejected(api.validateWmsClip(caseData, caseData.wms.events.find(item => item.id === candidate.eventIds[0])));
  });
  check(`${candidate.id}: explicit fixture + nested manifest registration accepted`, () => {
    const registered = registration(candidate);
    const event = registered.caseData.wms.events.find(item => item.id === candidate.eventIds[0]);
    const result = registered.api.validateWmsClip(registered.caseData, event);
    assert.equal(result.clip?.id, candidate.id, result.reason);
    assert.equal(result.clip?.sha256, candidate.sha256);
    assert.equal(result.clip?.bytes, candidate.bytes);
  });
}
check('old plus new W-W3 active registrations remain blocked as ambiguous', () => {
  const candidate = overlay.mediaCandidates.find(item => item.id === 'SYN-PC3-0002-SORTING');
  const registered = registration(candidate, true);
  const result = registered.api.validateWmsClip(registered.caseData, sorter(registered.caseData));
  rejected(result);
  assert.match(result.reason, /중복/);
});
check('fixture and manifest files remain byte-for-byte unchanged', () => {
  assert.equal(read(fixturePath), fixtureSource);
  assert.equal(read(manifestPath), manifestSource);
});

const failed = results.filter(item => !item.passed);
console.log(JSON.stringify({
  scope: 'Same physical pc3; in-memory contract and static React rendering review. No browser/media playback or main acceptance claim.',
  passed: results.length - failed.length, total: results.length, failed: failed.length, results,
}, null, 2));
process.exitCode = failed.length ? 1 : 0;
