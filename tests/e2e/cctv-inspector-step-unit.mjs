// Pure execution of the actual production step/seek functions. No server/browser/network.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const root = path.resolve(import.meta.dirname, '../..');
const ts = require(path.join(root, 'apps/web/node_modules/typescript'));
const sourcePath = path.join(root, 'apps/web/components/CctvInspector.tsx');
const source = fs.readFileSync(sourcePath, 'utf8');
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const output = path.resolve(process.env.CCTV_STEP_OUTPUT || path.join(root, '.local', 'cctv-step-unit-' + Date.now()));
fs.mkdirSync(output, { recursive: true });
const ast = ts.createSourceFile(sourcePath, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const functions = {};
function visit(node) {
  if (ts.isFunctionDeclaration(node) && ['step', 'seek'].includes(node.name?.text)) functions[node.name.text] = node.getText(ast);
  ts.forEachChild(node, visit);
}
visit(ast);
if (Object.keys(functions).length !== 2) throw new Error('Actual step/seek declarations not uniquely found');
const code = ts.transpileModule(functions.seek + '\n' + functions.step, { compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS } }).outputText;
function execute(sample, script = code) {
  let pauses = 0, displayedTime = null;
  const player = { currentTime: sample.currentTime, pause() { pauses += 1; } };
  const trackData = sample.noTracks ? null : { fps: 24, frameCount: 288 };
  const video = { current: sample.noPlayer ? null : player };
  const step = new Function('video', 'validatedTracks', 'clip', 'setTime', script + '\nreturn step;')(video, trackData, { startSeconds: sample.start, endSeconds: sample.end }, time => { displayedTime = time; });
  step(sample.direction);
  const frame = Math.min(287, Math.floor(player.currentTime * 24 + 1e-6)) + 1;
  return { time: player.currentTime, frame, pauses, displayedTime };
}
const samples = [
  { name: 'full end previous 288 to 287', start: 0, end: 12, currentTime: 12, direction: -1, expectedTime: 286 / 24, expectedFrame: 287 },
  { name: 'full end next remains 288', start: 0, end: 12, currentTime: 12, direction: 1, expectedTime: 287 / 24, expectedFrame: 288 },
  { name: 'last sampled frame previous', start: 0, end: 12, currentTime: 287 / 24, direction: -1, expectedTime: 286 / 24, expectedFrame: 287 },
  { name: 'partial end previous 145 to 144', start: 3, end: 6, currentTime: 6, direction: -1, expectedTime: 143 / 24, expectedFrame: 144 },
  { name: 'partial end next stays 145', start: 3, end: 6, currentTime: 6, direction: 1, expectedTime: 6, expectedFrame: 145 },
  { name: 'clip start previous stays', start: 3, end: 6, currentTime: 3, direction: -1, expectedTime: 3, expectedFrame: 73 },
  { name: 'clip start next advances', start: 3, end: 6, currentTime: 3, direction: 1, expectedTime: 73 / 24, expectedFrame: 74 },
  { name: 'non-frame clip start previous stays in bounds', start: 3.01, end: 6.01, currentTime: 3.01, direction: -1, expectedTime: 3.01, expectedFrame: 73 },
  { name: 'non-frame clip start next advances', start: 3.01, end: 6.01, currentTime: 3.01, direction: 1, expectedTime: 73 / 24, expectedFrame: 74 },
  { name: 'non-frame interior previous advances one frame', start: 3, end: 6, currentTime: 3.103, direction: -1, expectedTime: 73 / 24, expectedFrame: 74 },
  { name: 'non-frame interior next advances one frame', start: 3, end: 6, currentTime: 3.103, direction: 1, expectedTime: 75 / 24, expectedFrame: 76 },
  { name: 'non-frame clip end previous', start: 3, end: 6.01, currentTime: 6.01, direction: -1, expectedTime: 143 / 24, expectedFrame: 144 },
  { name: 'no tracks no movement', start: 0, end: 12, currentTime: 12, direction: -1, noTracks: true, expectedTime: 12, expectedFrame: 288 },
  { name: 'no player no movement', start: 0, end: 12, currentTime: 12, direction: -1, noPlayer: true, expectedTime: 12, expectedFrame: 288 },
];
const checks = samples.map(sample => {
  const actual = execute(sample);
  const noAction = sample.noTracks || sample.noPlayer;
  return { name: sample.name, input: sample, actual, pass: Math.abs(actual.time - sample.expectedTime) < 1e-9 && actual.frame === sample.expectedFrame && actual.pauses === (noAction ? 0 : 1) && (noAction ? actual.displayedTime === null : Math.abs(actual.displayedTime - sample.expectedTime) < 1e-9) };
});
const fixedExpression = 'Math.min(validatedTracks.frameCount - 1, Math.floor(player.currentTime * fps + 1e-6))';
let mutation = { status: 'FIX_NOT_PRESENT', detected: false };
if (functions.step.includes(fixedExpression)) {
  const oldStep = functions.step.replace(fixedExpression, 'Math.floor(player.currentTime * fps + 1e-6)');
  const oldCode = ts.transpileModule(functions.seek + '\n' + oldStep, { compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.CommonJS } }).outputText;
  const actual = execute(samples[0], oldCode);
  mutation = { status: 'REMOVED_CURRENT_INDEX_CLAMP', actual, detected: actual.frame !== samples[0].expectedFrame, expectedFrame: samples[0].expectedFrame };
}
const report = { measuredAt: new Date().toISOString(), host: process.env.COMPUTERNAME, method: 'TypeScript AST extracted actual step/seek functions, transpileModule and pure JS execution with minimal player state', sourceSha256: sha(source), harnessSha256: sha(fs.readFileSync(import.meta.filename)), serverStarts: 0, browserStarts: 0, networkCalls: 0, browserRecheck: 'NOT_RUN', checks, mutation, passed: checks.filter(check => check.pass).length, total: checks.length };
fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify(report, null, 2));
fs.writeFileSync(path.join(output, 'actual-functions.ts'), functions.seek + '\n' + functions.step);
fs.writeFileSync(path.join(output, 'actual-functions.js'), code);
fs.copyFileSync(import.meta.filename, path.join(output, 'source-harness.mjs'));
console.log(JSON.stringify({ output, passed: report.passed, total: report.total, mutation }));
if (report.passed !== report.total || !mutation.detected) process.exitCode = 1;
