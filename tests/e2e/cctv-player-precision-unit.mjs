// Actual frameAt and step/seek code with microsecond player timestamps; no browser/server/network.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
const require = createRequire(import.meta.url), root = path.resolve(import.meta.dirname, '../..');
const ts = require(path.join(root, 'apps/web/node_modules/typescript'));
const componentPath = 'apps/web/components/CctvInspector.tsx', tracksPath = 'apps/web/lib/cctv-tracks.ts';
const currentComponent = fs.readFileSync(path.join(root, componentPath), 'utf8');
const currentTracks = fs.readFileSync(path.join(root, tracksPath), 'utf8');
const transpile = source => ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText;
function load(componentSource, tracksSource, fps, quantize) {
  const ast = ts.createSourceFile(componentPath, componentSource, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX), functions = {};
  function visit(node) { if (ts.isFunctionDeclaration(node) && ['step', 'seek'].includes(node.name?.text)) functions[node.name.text] = node.getText(ast); ts.forEachChild(node, visit); }
  visit(ast); assert.equal(Object.keys(functions).length, 2);
  const exports = {}; new Function('exports', transpile(tracksSource))(exports);
  const count = Math.round(fps * 12), tracks = { fps, frameCount: count, frames: Array.from({ length: count }, (_, i) => ({ frame: i + 1 })) };
  let clock = 0;
  const player = { get currentTime() { return clock; }, set currentTime(value) { clock = quantize(value); }, pause() {} };
  const step = new Function('video', 'validatedTracks', 'clip', 'setTime', transpile(functions.seek + '\n' + functions.step) + '\nreturn step;')({ current: player }, tracks, { startSeconds: 0, endSeconds: count / fps }, () => {});
  return { player, step, frame: () => exports.frameAt(tracks, player.currentTime)?.frame, frameAt: time => exports.frameAt(tracks, time)?.frame, count };
}
const truncate = time => Math.floor(time * 1e6) / 1e6;
const oldRevision = 'b1ca8f2e780356f5b995fe8bb9db799313a3d3a1';
const oldComponent = execFileSync('git', ['show', oldRevision + ':' + componentPath], { cwd: root, encoding: 'utf8' });
const oldTracks = execFileSync('git', ['show', oldRevision + ':' + tracksPath], { cwd: root, encoding: 'utf8' });
const old = load(oldComponent, oldTracks, 24, truncate);
old.step(1); const oldFirst = { time: old.player.currentTime, frame: old.frame() }; old.step(1);
assert.deepEqual(oldFirst, { time: 0.041666, frame: 1 });
assert.equal(old.player.currentTime, oldFirst.time); // Reproduces the observed IAB two-click stall.
let transitions = 0, boundaries = 0;
for (const fps of [24, 25, 29.97, 30, 60, 120]) {
  for (const quantize of [time => time, truncate, time => Math.round(time * 1e6) / 1e6]) {
    const actual = load(currentComponent, currentTracks, fps, quantize);
    for (let index = 1; index < actual.count; index++) {
      actual.step(1); assert.equal(actual.frame(), index + 1); assert.ok(Math.abs(actual.player.currentTime - index / fps) <= 1.000001e-6); transitions++;
    }
    const end = actual.player.currentTime; actual.step(1); assert.equal(actual.player.currentTime, end); boundaries++;
    for (let index = actual.count - 2; index >= 0; index--) { actual.step(-1); assert.equal(actual.frame(), index + 1); transitions++; }
    actual.step(-1); assert.equal(actual.player.currentTime, 0); boundaries++;
    assert.equal(actual.frameAt(1 / fps - 2e-6), 1); // Do not round a clearly earlier frame forward.
    assert.equal(actual.frameAt(1 / fps), 2);
    assert.equal(actual.frameAt(-1e-7), undefined);
    assert.equal(actual.frameAt(actual.count / fps), undefined); boundaries += 4;
  }
}
// Each fix is required: removing either reintroduces the observed two-click failure.
let mutantsDetected = 0;
for (const [componentSource, tracksSource] of [[oldComponent, currentTracks], [currentComponent, oldTracks]]) {
  const mutant = load(componentSource, tracksSource, 24, truncate); mutant.step(1); mutant.step(1);
  assert.notEqual(mutant.frame(), 3); mutantsDetected++;
}
console.log(JSON.stringify({ status: 'PASS', oldRevision, oldFirst, oldRepeatedTime: old.player.currentTime, transitions, boundaries, mutantsDetected, paidCalls: 0, serverStarts: 0, browserStarts: 0 }));
