// Pure execution of production TS modules and JSX event/props wiring; no DOM, browser, server or network.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url), root = path.resolve(import.meta.dirname, '../..');
const ts = require(path.join(root, 'apps/web/node_modules/typescript'));
const sourcePaths = ['apps/web/lib/cctv-tracks.ts', 'apps/web/components/WmsScene.tsx', 'apps/web/components/CctvInspector.tsx'];
const sources = Object.fromEntries(sourcePaths.map(p => [p, fs.readFileSync(path.join(root, p), 'utf8')]));
const fixture = JSON.parse(fs.readFileSync(path.join(root, 'data/fixtures/cases.json'), 'utf8'));
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'data/demo-media-manifest.json'), 'utf8'));
const originalCase = fixture.cases.find(c => c.id === 'CASE-0002'), event = originalCase.wms.events.find(e => e.id === 'W-W3');
const sha = data => crypto.createHash('sha256').update(data).digest('hex'), clone = structuredClone;
const checkResults = [];
function check(name, pass, detail = null) { checkResults.push({ name, pass: !!pass, detail }); if (!pass) throw new Error(name); }
function rejects(name, action) { let message = ''; try { action(); } catch (error) { message = error.message; } check(name, !!message, message); }
function compile(source, imports = {}) {
  const module = { exports: {} }, code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true } }).outputText;
  new Function('require', 'module', 'exports', code)(name => { if (!(name in imports)) throw new Error('Unregistered test import ' + name); return imports[name]; }, module, module.exports);
  return module.exports;
}
const tracksSource = sources[sourcePaths[0]], wmsSource = sources[sourcePaths[1]], api = compile(tracksSource);
function wmsModule(registeredManifest = manifest, moduleSource = wmsSource, trackApi = api) {
  const states = []; let cursor = 0;
  const react = { useState(initial) { const index = cursor++; if (!(index in states)) states[index] = typeof initial === 'function' ? initial() : initial; return [states[index], next => { states[index] = typeof next === 'function' ? next(states[index]) : next; }]; }, useEffect() {}, useRef(value) { return { current: value }; } };
  const jsx = (type, props, key) => ({ type, props: props ?? {}, key });
  const inspector = function InspectorMarker() {};
  const exports = compile(moduleSource, { react, 'react/jsx-runtime': { jsx, jsxs: jsx, Fragment: 'fragment' }, '@/lib/api': { ApiError: class extends Error {} }, '../../../data/fixtures/cases.json': clone(fixture), '../../../data/demo-media-manifest.json': clone(registeredManifest), './WmsScene.module.css': {}, './CctvInspector': inspector, '../lib/cctv-tracks': trackApi });
  const render = caseData => { cursor = 0; const outer = exports.default({ caseData, onBack() {}, onLinkEvidence() {} }); return outer.type(outer.props); };
  return { ...exports, render, inspector, states };
}
function find(tree, predicate) {
  if (!tree || typeof tree !== 'object') return undefined;
  if (Array.isArray(tree)) { for (const item of tree) { const found = find(item, predicate); if (found) return found; } return undefined; }
  if (predicate(tree)) return tree;
  return find(tree.props?.children, predicate);
}
function withDescriptor(change = () => {}) {
  const value = clone(manifest), video = value.assets.find(a => a.name === 'sorter-demo.mp4');
  video.tracks = { schemaVersion: 'oneflow-cctv-tracks-v1', url: '/demo/sorter-demo.tracks.json', bytes: 100, sha256: '1'.repeat(64), videoSha256: video.sha256 };
  change(video.tracks, video, value); return value;
}
const noRegistration = wmsModule().validateWmsClip(clone(originalCase), event);
check('current video with no registered coordinates remains available', !!noRegistration.clip && noRegistration.reason === '' && !noRegistration.tracks && !noRegistration.tracksError);
const injected = clone(originalCase); injected.media[0].tracks = { url: 'https://untrusted.invalid/coords.json' };
const ignored = wmsModule().validateWmsClip(injected, event);
check('case media cannot register coordinates or leak them into trusted clip', !!ignored.clip && !ignored.tracks && !Object.hasOwn(ignored.clip, 'tracks'));
const accepted = wmsModule(withDescriptor()).validateWmsClip(injected, event);
check('manifest coordinates override untrusted case metadata', accepted.tracks?.url === '/demo/sorter-demo.tracks.json' && accepted.tracks.sha256 === '1'.repeat(64));
check('canonical process supplies exact chute and dock without changing event', accepted.processAnchor?.chuteId === 'CH-02' && accepted.processAnchor?.dockId === 'D-02' && !Object.hasOwn(event, 'chuteId') && !Object.hasOwn(event, 'dockId'));
for (const [name, change] of [
  ['null registration', (d, a) => { a.tracks = null; }], ['array registration', (d, a) => { a.tracks = []; }], ['missing schema', d => { delete d.schemaVersion; }], ['unsupported schema', d => { d.schemaVersion = 'v2'; }],
  ['alternate JSON filename', d => { d.url = '/demo/other.json'; }], ['external URL', d => { d.url = 'https://example.com/sorter-demo.tracks.json'; }], ['traversal URL', d => { d.url = '/demo/../sorter-demo.tracks.json'; }],
  ['video hash mismatch', d => { d.videoSha256 = '0'.repeat(64); }], ['uppercase sha', d => { d.sha256 = 'A'.repeat(64); }], ['short sha', d => { d.sha256 = 'abc'; }],
  ['zero bytes', d => { d.bytes = 0; }], ['fraction bytes', d => { d.bytes = 1.5; }], ['string bytes', d => { d.bytes = '100'; }], ['oversize coordinates', d => { d.bytes = 10_000_001; }],
]) { const result = wmsModule(withDescriptor(change)).validateWmsClip(clone(originalCase), event); check(name + ' keeps video but rejects coordinates', !!result.clip && !result.tracks && !result.processAnchor && !!result.tracksError, result.tracksError); }
for (const size of [1, 10_000_000]) { const result = wmsModule(withDescriptor(d => { d.bytes = size; })).validateWmsClip(clone(originalCase), event); check('coordinate byte boundary ' + size + ' accepted', result.tracks?.bytes === size); }
for (const [name, change] of [ ['live chute changed', c => { c.wms.sorting.rsltChuteNo = 'CH-99'; }], ['live dock changed', c => { c.wms.shipping.dock = 'D-99'; }] ]) {
  const caseData = clone(originalCase); change(caseData); const result = wmsModule(withDescriptor()).validateWmsClip(caseData, event); check(name + ' rejects inconsistent case', !result.clip && !!result.reason, result.reason);
}
const forgedEvent = { ...event, chuteId: 'CH-99' }, forged = wmsModule(withDescriptor()).validateWmsClip(clone(originalCase), forgedEvent);
check('event chute injection rejects coordinates', !!forged.clip && !forged.tracks && !!forged.tracksError);
const syntheticTracks = { source: 'synthetic-scene-ground-truth', synthetic: true, eventAnchor: { caseId: 'CASE-0002', eventId: 'W-W3', occurredAt: event.time, chuteId: 'CH-02', dockId: 'D-02', visualObjectId: 'SYN-TEST-BOUNDS', businessToteId: null }, cameraId: accepted.clip.cameraId, coordinateSpace: 'normalized-image-top-left', clockMode: 'illustrative-elapsed-separate-from-event-time', occlusionTested: false, fps: 24, frameCount: 288, resolution: [1920, 1080], frames: Array.from({ length: 288 }, (_, i) => ({ frame: i + 1, elapsedSeconds: i / 24, visualObjectId: 'SYN-TEST-BOUNDS', businessToteId: null, phase: i < 96 ? 'approach' : i < 144 ? 'branch' : i < 240 ? 'chute' : 'settle', bboxNormalizedXYXY: [.1, .2, .3, .4], fullyInFrame: true })) };
check('validated canonical anchor accepts all 288 synthetic test frames', api.validateTracks(syntheticTracks, accepted.tracks, accepted.clip, event, accepted.processAnchor).frames.length === 288);
check('standalone explicit chute and dock remain supported', api.validateTracks(syntheticTracks, accepted.tracks, accepted.clip, { ...event, ...accepted.processAnchor }).frames.length === 288);
rejects('missing expected chute and dock cannot skip validation', () => api.validateTracks(syntheticTracks, accepted.tracks, accepted.clip, event));
for (const [name, change] of [ ['wrong chute', t => { t.eventAnchor.chuteId = 'CH-99'; }], ['wrong dock', t => { t.eventAnchor.dockId = 'D-99'; }], ['wrong case', t => { t.eventAnchor.caseId = 'CASE-0001'; }], ['wrong event', t => { t.eventAnchor.eventId = 'W-W2'; }], ['wrong time', t => { t.eventAnchor.occurredAt = '2026-09-18T02:34:00+09:00'; }], ['wrong camera', t => { t.cameraId = 'SYN-CAM-01'; }], ['business tote link', t => { t.eventAnchor.businessToteId = 'SYN-TOTE02-A'; }], ['frame business tote link', t => { t.frames[0].businessToteId = 'SYN-TOTE02-A'; }], ['missing frame', t => { t.frames.pop(); }], ['wrong frame clock', t => { t.frames[3].elapsedSeconds += .1; }] ]) { const value = clone(syntheticTracks); change(value); rejects(name + ' rejected', () => api.validateTracks(value, accepted.tracks, accepted.clip, event, accepted.processAnchor)); }
api.validateTrackVideo(syntheticTracks, 1920, 1080, 12); check('full 1080p twelve-second synthetic fixture metadata matches', true);
rejects('three-second short cannot use 288-frame coordinates', () => api.validateTrackVideo(syntheticTracks, 1920, 1080, 3));
rejects('different resolution cannot share coordinates', () => api.validateTrackVideo(syntheticTracks, 1280, 720, 12));
for (const [name, registeredManifest, expected] of [['registered', withDescriptor(), 'valid'], ['unregistered', manifest, 'none'], ['malformed', withDescriptor(d => { d.videoSha256 = '0'.repeat(64); }), 'invalid']]) {
  const component = wmsModule(registeredManifest); component.states[0] = 2;
  const first = component.render(clone(originalCase)), button = find(first, el => el.props?.['data-testid'] === 'open-video');
  check(name + ' JSX exposes video opener', typeof button?.props.onClick === 'function');
  button.props.onClick({ currentTarget: { isConnected: true, focus() {} } });
  const inspector = find(component.render(clone(originalCase)), el => el.type === component.inspector);
  check(name + ' production event wires correct Inspector props', !!inspector && (expected === 'valid' ? inspector.props.tracks?.url === '/demo/sorter-demo.tracks.json' && inspector.props.processAnchor?.chuteId === 'CH-02' && !inspector.props.tracksError : expected === 'none' ? !inspector.props.tracks && !inspector.props.tracksError : !inspector.props.tracks && !!inspector.props.tracksError));
}
const mutations = [
  { name: 'chute equality removal', from: 'anchor.chuteId !== expectedProcess.chuteId || ', to: '', bad: t => { t.eventAnchor.chuteId = 'CH-99'; } },
  { name: 'dock equality removal', from: 'anchor.dockId !== expectedProcess.dockId || ', to: '', bad: t => { t.eventAnchor.dockId = 'D-99'; } },
];
for (const mutation of mutations) {
  if (!tracksSource.includes(mutation.from)) throw new Error('Mutation anchor absent');
  const mutant = compile(tracksSource.replace(mutation.from, mutation.to)), value = clone(syntheticTracks); mutation.bad(value);
  let admitted = false; try { mutant.validateTracks(value, accepted.tracks, accepted.clip, event, accepted.processAnchor); admitted = true; } catch {}
  check(mutation.name + ' detected by same negative control', admitted);
}
const needle = "if (descriptor.url !== '/demo/sorter-demo.tracks.json') fail('객체 좌표의 등록 파일명이 일치하지 않습니다');";
if (!tracksSource.includes(needle)) throw new Error('Filename mutation anchor absent');
const loosened = compile(tracksSource.replace(needle, ''));
check('exact filename gate mutation detected', !!wmsModule(withDescriptor(d => { d.url = '/demo/other.json'; }), wmsSource, loosened).validateWmsClip(clone(originalCase), event).tracks);
const wiringNeedle = 'tracks: clipResult.tracks, processAnchor: clipResult.processAnchor, tracksError: clipResult.tracksError';
if (!wmsSource.includes(wiringNeedle)) throw new Error('Wiring mutation anchor absent');
const unwired = wmsModule(withDescriptor(), wmsSource.replace(wiringNeedle, ''));
unwired.states[0] = 2; find(unwired.render(clone(originalCase)), el => el.props?.['data-testid'] === 'open-video').props.onClick({ currentTarget: {} });
check('props wiring removal mutation detected', !find(unwired.render(clone(originalCase)), el => el.type === unwired.inspector).props.tracks);
const out = path.join(root, '.local', 'cctv-trusted-tracks-' + Date.now()); fs.mkdirSync(out, { recursive: true });
const report = { measuredAt: new Date().toISOString(), host: process.env.COMPUTERNAME, method: 'Actual TypeScript modules transpiled and executed; JSX handler/props with minimal state adapter; no DOM or media playback', serverStarts: 0, browserStarts: 0, networkCalls: 0, actualSceneAlignment: 'NOT_TESTED', browserRecheck: 'NOT_RUN', sourceHashes: Object.fromEntries(sourcePaths.map(p => [p, sha(sources[p])])), harnessSha256: sha(fs.readFileSync(import.meta.filename)), checks: checkResults, passed: checkResults.filter(c => c.pass).length, total: checkResults.length };
fs.writeFileSync(path.join(out, 'results.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify({ output: out, passed: report.passed, total: report.total, sourceHashes: report.sourceHashes }));
