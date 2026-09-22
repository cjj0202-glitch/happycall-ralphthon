// Execute production phase lookup/seek against registered track times; no browser or API.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
const root = path.resolve(import.meta.dirname, '../..');
const require = createRequire(import.meta.url);
const ts = require(path.join(root, 'apps/web/node_modules/typescript'));
const source = fs.readFileSync(path.join(root, 'apps/web/components/CctvInspector.tsx'), 'utf8');
const ast = ts.createSourceFile('CctvInspector.tsx', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const functions = {};
function visit(node) {
  if (ts.isFunctionDeclaration(node) && ['firstPhaseFrame', 'seekPhase', 'seek'].includes(node.name?.text)) functions[node.name.text] = node.getText(ast);
  ts.forEachChild(node, visit);
}
visit(ast); assert.equal(Object.keys(functions).length, 3);
const productionFunctions = Object.values(functions).join('\n');
const compile = input => ts.transpileModule(input, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText;
const code = compile(productionFunctions);
const tracks = JSON.parse(fs.readFileSync(path.join(root, 'apps/web/public/demo/sorter-demo.tracks.json'), 'utf8'));
let checks = 0;
for (const phase of ['approach', 'branch', 'chute', 'settle']) {
  let paused = 0, displayed = null, selected = false, overlay = false, playing = true;
  const player = { currentTime: 11, pause() { paused++; } };
  const clip = { startSeconds: 0, endSeconds: 12 };
  const api = new Function('exports', 'video', 'validatedTracks', 'clip', 'setTime', 'setPlaying', 'setSelected', 'setOverlay', code + '\nreturn {firstPhaseFrame, seekPhase};')({}, { current: player }, tracks, clip, t => { displayed = t; }, v => { playing = v; }, v => { selected = v; }, v => { overlay = v; });
  const expected = tracks.frames.find(frame => frame.phase === phase);
  assert.ok(expected, `Registered phase missing: ${phase}`);
  api.seekPhase(phase);
  assert.equal(player.currentTime, expected.elapsedSeconds);
  assert.equal(displayed, expected.elapsedSeconds);
  assert.equal(paused, 1); assert.equal(playing, false); assert.ok(selected && overlay); checks += 6;
  assert.equal(api.firstPhaseFrame(null, clip, phase), null); checks++;
  const partial = { startSeconds: expected.elapsedSeconds + 0.001, endSeconds: 12 };
  assert.equal(api.firstPhaseFrame(tracks, partial, phase), tracks.frames.find(frame => frame.phase === phase && frame.elapsedSeconds >= partial.startSeconds) ?? null); checks++;
  assert.equal(api.firstPhaseFrame(tracks, { startSeconds: 12, endSeconds: 12 }, phase), null); checks++;
}
// Run the same observable assertions against production and memory-only mutants.
// The independent expectation is the first registered branch frame, not mutated lookup output.
const targetPhase = 'branch';
const targetFrame = tracks.frames.find(frame => frame.phase === targetPhase);
assert.ok(targetFrame && targetFrame.elapsedSeconds > tracks.frames[0].elapsedSeconds);
const expected = { time: targetFrame.elapsedSeconds, pauseCalls: 1, paused: true };
function observe(script) {
  let pauseCalls = 0;
  const player = { currentTime: 11, paused: false, pause() { pauseCalls++; this.paused = true; } };
  const api = new Function('exports', 'video', 'validatedTracks', 'clip', 'setTime', 'setPlaying', 'setSelected', 'setOverlay', script + '\nreturn {seekPhase};')({}, { current: player }, tracks, { startSeconds: 0, endSeconds: 12 }, () => {}, () => {}, () => {}, () => {});
  api.seekPhase(targetPhase);
  return { time: player.currentTime, pauseCalls, paused: player.paused };
}
function assertOutcome(actual) {
  assert.equal(actual.time, expected.time, 'Seek must reach the first registered frame of the requested phase');
  assert.equal(actual.pauseCalls, expected.pauseCalls, 'Phase navigation must call the media pause method');
  assert.equal(actual.paused, expected.paused, 'The media must remain paused after phase navigation');
}
const baseline = observe(code);
assertOutcome(baseline);
const mutations = [
  { name: 'REMOVE_PHASE_FILTER', remove: 'frame.phase === phase && ', fault: 'Requested branch incorrectly seeks to the first approach frame' },
  { name: 'REMOVE_MEDIA_PAUSE', remove: 'video.current.pause();', fault: 'UI may report stopped while the media remains playing' },
].map(mutation => {
  assert.equal(productionFunctions.split(mutation.remove).length - 1, 1, `Mutation anchor must occur exactly once: ${mutation.name}`);
  const actual = observe(compile(productionFunctions.replace(mutation.remove, '')));
  let failure = null;
  try { assertOutcome(actual); } catch (error) {
    assert.equal(error.code, 'ERR_ASSERTION');
    failure = { message: error.message, expected: error.expected, actual: error.actual, operator: error.operator };
  }
  assert.ok(failure, `Mutation survived the production outcome assertions: ${mutation.name}`);
  return { name: mutation.name, fault: mutation.fault, targetPhase, targetRegisteredFrame: targetFrame.frame, expected, actual, detected: true, assertionFailure: failure, scope: 'in-memory only; production file unchanged' };
});
console.log(JSON.stringify({ passed: checks, registeredFrames: tracks.frames.length, phases: 4, source: 'production functions', browserExecuted: false, mutationBaseline: { expected, actual: baseline }, mutations }));
