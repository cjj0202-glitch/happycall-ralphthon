import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { spawn, spawnSync, execFileSync } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const RUNNER_VERSION = 'six-flow-rehearsal-v2';
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
async function runnerMetadata() {
  return { version: RUNNER_VERSION, observedAt: new Date().toISOString(), nodeVersion: process.version,
    files: Object.fromEntries(await Promise.all(['tests/e2e/six-flow-rehearsal.mjs', 'tests/helpers/rehearsal_server.py'].map(async name => {
      const bytes = await readFile(path.join(ROOT, name)); return [name, { sha256: sha256(bytes), bytes: bytes.length }];
    }))) };
}
function summarizeRun(run) {
  return { corePassed: run.core.filter(r => r.status === 'PASS').length, coreExecuted: run.core.length, coreTarget: 6,
    manualPassed: run.textManual.filter(r => r.status === 'PASS').length, manualExecuted: run.textManual.length,
    offlineSafetyPassed: run.offline.filter(r => r.safetyStatus === 'PASS').length, offlineExecuted: run.offline.length,
    offlineCompletePassed: run.offline.filter(r => r.completeFlowStatus === 'PASS').length,
    externalRequests: run.externalRequests.length, liveRequests: run.liveRequests.length };
}
function exitGate(run) {
  const summary = summarizeRun(run); const failures = [];
  if (run.fatal) failures.push('fatal');
  if (summary.corePassed !== 6 || summary.coreExecuted !== 6) failures.push('core');
  if (summary.manualPassed !== 2 || summary.manualExecuted !== 2) failures.push('manual');
  if (summary.offlineSafetyPassed !== 1 || summary.offlineExecuted !== 1) failures.push('offline-safety');
  if (summary.externalRequests !== 0) failures.push('external-request');
  if (summary.liveRequests !== 0) failures.push('live-request');
  // Offline full completion remains an independent denominator; BLOCKED is never PASS.
  return { exitCode: failures.length ? 1 : 0, failures, summary,
    scope: 'core 6/6, manual 2/2, offline safety 1/1, zero external/live requests; offline full completion reported separately' };
}
if (process.argv.includes('--gate-evaluate')) {
  let source = ''; for await (const chunk of process.stdin) source += chunk;
  const decision = exitGate(JSON.parse(source)); console.log(JSON.stringify(decision)); process.exit(decision.exitCode);
}
const gateIndex = process.argv.indexOf('--gate-selftest');
if (gateIndex !== -1) {
  const originalPath = path.resolve(process.argv[gateIndex + 1] || '');
  const originalBytes = await readFile(originalPath);
  const original = JSON.parse(originalBytes);
  const controls = [
    ['historical-pass-offline-completion-blocked', () => {}, 0, []],
    ['offline-safety-fail', r => { r.offline[0].safetyStatus = 'FAIL'; }, 1, ['offline-safety']],
    ['offline-not-run', r => { r.offline = []; }, 1, ['offline-safety']],
    ['core-fail', r => { r.core[0].status = 'FAIL'; }, 1, ['core']],
    ['manual-fail', r => { r.textManual[0].status = 'FAIL'; }, 1, ['manual']],
    ['external-request', r => { r.externalRequests.push('https://example.invalid/control-only-not-requested'); }, 1, ['external-request']],
    ['live-request', r => { r.liveRequests.push('control-only-not-requested/analyze'); }, 1, ['live-request']],
    ['fatal', r => { r.fatal = 'control-only'; }, 1, ['fatal']],
  ];
  const checks = controls.map(([name, mutate, expectedExit, expectedFailures]) => {
    const candidate = structuredClone(original); mutate(candidate);
    const child = spawnSync(process.execPath, [fileURLToPath(import.meta.url), '--gate-evaluate'], {
      input: JSON.stringify(candidate), encoding: 'utf8', windowsHide: true, timeout: 10000,
    });
    assert.equal(child.error, undefined, name); assert.equal(child.status, expectedExit, `${name}: ${child.stderr}`);
    const observed = JSON.parse(child.stdout);
    assert.equal(observed.exitCode, child.status, name); assert.deepEqual(observed.failures, expectedFailures, name);
    if (name === 'historical-pass-offline-completion-blocked') {
      assert.equal(observed.summary.offlineCompletePassed, 0); assert.equal(candidate.offline[0].completeFlowStatus, 'BLOCKED');
    }
    return { name, expectedExit, actualProcessExit: child.status, observed, status: 'PASS' };
  });
  assert.equal(sha256(await readFile(originalPath)), sha256(originalBytes), 'Historical evidence was modified');
  const gateReport = { at: new Date().toISOString(), mode: 'aggregation-only; no browser, server, API, or cleanup',
    historicalSource: { path: originalPath, sha256: sha256(originalBytes), modified: false }, runner: await runnerMetadata(), checks };
  const output = path.join(ROOT, 'reports/e2e', `rehearsal-runner-gate-${new Date().toISOString().replace(/[:.]/g, '-')}.json`);
  await writeFile(output, JSON.stringify(gateReport, null, 2));
  console.log(JSON.stringify({ output, passed: checks.length, total: controls.length }));
  process.exit(0);
}
const stamp = new Date().toISOString().replace(/[:.]/g, '-');
const OUT = path.join(ROOT, 'reports/e2e', `rehearsal-${stamp}`);
const VIDEO = path.join(ROOT, 'tests/e2e/test-results/rehearsal', stamp);
await mkdir(OUT, { recursive: true });
await mkdir(VIDEO, { recursive: true });
const fixture = JSON.parse(await readFile(path.join(ROOT, 'data/fixtures/cases.json'), 'utf8'));
const report = { started: new Date().toISOString(), runner: await runnerMetadata(), pc: 'pc1/CJJ', executor: 'AI Playwright, not human observation',
  baselineHead: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: ROOT, encoding: 'utf8' }).trim(),
  mode: 'replay-only; no STT/GPT calls', target: { core: 6, textManual: 2, offline: 1 },
  core: [], textManual: [], offline: [], externalRequests: [], liveRequests: [], videoDirectory: VIDEO,
  limits: ['Isolated temporary state; no production persistence validation.', 'Browser recording does not guarantee audio capture.',
    'Synthetic 2026-09-18 cases; no real logistics action.', 'Replay/manual validation is not live model accuracy or human usability.'] };
await writeFile(path.join(OUT, 'runner-metadata.json'), JSON.stringify(report.runner, null, 2));
for (const [name, metadata] of Object.entries(report.runner.files)) {
  const bytes = await readFile(path.join(ROOT, name));
  assert.equal(sha256(bytes), metadata.sha256, 'Runner/helper changed while preserving startup source');
  await writeFile(path.join(OUT, `source-${path.basename(name)}`), bytes);
}
const save = () => writeFile(path.join(OUT, 'results.json'), JSON.stringify(report, null, 2));
const env = Object.fromEntries(['PATH', 'SystemRoot', 'WINDIR', 'TEMP', 'TMP', 'USERPROFILE'].filter(k => process.env[k]).map(k => [k, process.env[k]]));
const server = spawn(path.join(ROOT, '.venv/Scripts/python.exe'), ['tests/helpers/rehearsal_server.py', '--metadata', path.join(OUT, 'server.json')],
  { cwd: ROOT, env: { ...env, PYTHONUTF8: '1', PYTHONDONTWRITEBYTECODE: '1' }, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
let serverLog = '';
server.stdout.on('data', b => { serverLog += b.toString(); });
server.stderr.on('data', b => { serverLog += b.toString(); });
let browser;
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function waitReady() {
  for (let n = 0; n < 60; n++) {
    if (server.exitCode !== null) throw new Error(`Isolated server exited ${server.exitCode}: ${serverLog}`);
    try {
      const r = await fetch('http://127.0.0.1:8824/api/cases');
      if (r.ok && (await r.json()).cases.length === 2) return;
    } catch {}
    await pause(500);
  }
  throw new Error(`Isolated server did not become ready: ${serverLog}`);
}
async function contextFor(result, base) {
  const context = await browser.newContext({ viewport: { width: 1365, height: 950 }, recordVideo: { dir: VIDEO, size: { width: 1365, height: 950 } } });
  await context.route('**/*', async route => {
    const req = route.request(); const u = new URL(req.url());
    if (u.hostname !== '127.0.0.1' || ![8821, 8822, 8823, 8824].includes(Number(u.port))) {
      report.externalRequests.push(req.url()); return route.abort('blockedbyclient');
    }
    if (u.pathname.endsWith('/analyze') && req.postDataJSON()?.mode !== 'replay') {
      report.liveRequests.push(req.url()); return route.abort('blockedbyclient');
    }
    await route.continue();
  });
  const page = await context.newPage(); page.setDefaultTimeout(10000);
  result.errors = []; result.stages = []; result.responses = [];
  page.on('pageerror', e => result.errors.push({ kind: 'pageerror', message: e.message }));
  page.on('console', m => { if (m.type() === 'error') result.errors.push({ kind: 'console', message: m.text() }); });
  page.on('requestfailed', r => result.errors.push({ kind: 'network', url: r.url(), message: r.failure()?.errorText }));
  const nav = label => page.getByRole('navigation').getByRole('button', { name: label, exact: true }).click();
  const select = id => page.getByRole('region', { name: '문의 선택' }).getByRole('button').filter({ hasText: id }).click();
  const get = async id => {
    const response = await context.request.get(`${base}/api/cases/${id}`); assert.equal(response.status(), 200);
    return response.json();
  };
  const stage = async (name, action) => {
    const started = new Date().toISOString(); result.currentStage = name;
    try { const evidence = await action(); result.stages.push({ name, started, finished: new Date().toISOString(), status: 'PASS', evidence }); return evidence; }
    catch (e) { result.stages.push({ name, started, status: 'FAIL', message: e.message }); throw e; }
  };
  const ui = async (url, method, click, expectedStatus = 200) => {
    const pending = page.waitForResponse(r => r.url().endsWith(url) && r.request().method() === method); pending.catch(() => {});
    await click(); const response = await pending; const body = await response.json(); const request = response.request();
    result.responses.push({ at: new Date().toISOString(), url, method, sent: request.postDataJSON(), role: request.headers()['x-demo-role'], status: response.status(), body });
    assert.equal(response.status(), expectedStatus, JSON.stringify(body)); return body;
  };
  const reject = async (snapshot, delta, role, code, status = 422) => {
    const response = await context.request.patch(`${base}/api/cases/${snapshot.id}`, { data: { ...delta, expectedRevision: snapshot.revision }, headers: { 'X-Demo-Role': role } });
    const body = await response.json();
    result.responses.push({ at: new Date().toISOString(), negativeControl: true, role, status: response.status(), sent: delta, body });
    assert.equal(response.status(), status); assert.equal(body.error.code, code); assert.deepEqual(await get(snapshot.id), snapshot);
    return { status: response.status(), code, unchangedRevision: snapshot.revision };
  };
  return { context, page, nav, select, get, stage, ui, reject };
}

async function completeBusiness(c, id, result, tools, isVoice) {
  const { page, nav, get, stage, ui, reject } = tools;
  const url = `/api/cases/${id}`;
  await stage('same-case-wms-tms-and-media', async () => {
    const links = [];
    for (const [label, key] of [['WMS 작업 확인', 'wms'], ['TMS 배송 확인', 'tms']]) {
      await nav(label); await page.getByRole('heading', { name: label, exact: true }).waitFor();
      const content = await page.locator('main').innerText();
      assert.ok(content.includes(key === 'wms' ? c.wms.shipping.id : c.tms.routeId));
      const available = c.evidence.filter(e => e.system.toLowerCase() === key);
      const before = await get(id);
      const saved = await ui(url, 'PATCH', () => page.getByRole('button', { name: '이 근거 연결', exact: true }).first().click());
      assert.equal(saved.revision, before.revision + 1); assert.ok(saved.selectedEvidence.includes(available[0].id));
      assert.deepEqual(await get(id), saved); links.push({ system: key, id: available[0].id, revision: saved.revision });
      if (key === 'wms') {
        const videoButton = page.getByRole('button', { name: /AI 합성 CCTV 구간 보기/ });
        if (c.type === 'wrong' && isVoice) {
          assert.equal(await videoButton.count(), 1); await videoButton.click();
          const dialog = page.getByRole('dialog'); const text = await dialog.innerText();
          for (const part of [c.id, 'SYN-CAM-02', 'W-W3', '실제 CCTV 아님', '귀책']) assert.ok(text.includes(part));
          const video = dialog.locator('video');
          await video.evaluate(async v => { v.muted = true; await v.play(); });
          await page.waitForFunction(() => { const v = document.querySelector('video'); return v && v.currentTime >= 11.7 && v.paused; }, {}, { timeout: 20000 });
          result.videoPlayback = await video.evaluate(v => ({ currentTime: v.currentTime, duration: v.duration, paused: v.paused, width: v.videoWidth, error: v.error?.code || null }));
          assert.equal(result.videoPlayback.error, null); assert.ok(result.videoPlayback.width > 0);
          await page.screenshot({ path: path.join(OUT, `${result.name}-video.png`), fullPage: true });
          await page.keyboard.press('Escape'); assert.equal(await page.getByRole('dialog').count(), 0);
          assert.equal(await videoButton.evaluate(el => el === document.activeElement), true);
        } else {
          assert.equal(await videoButton.count(), 0);
          result.mediaLimitation = c.type === 'missing' ? 'No registered video for missing case; no substitute video.' : 'New linked text intake does not inherit fixture video; no substitute video.';
        }
      }
      await page.screenshot({ path: path.join(OUT, `${result.name}-${key}.png`), fullPage: true });
    }
    return links;
  });
  await stage('review-gates-and-human-handoff', async () => {
    await nav('상담 작업대');
    const transfer = page.getByRole('button', { name: '확인 후 센터 전달' });
    assert.equal(await transfer.isDisabled(), true);
    const before = await get(id);
    result.reviewRejection = await reject(before, { status: 'handed_off', departmentId: c.type === 'missing' ? 'delivery' : 'warehouse', reviewConfirmed: false }, 'counselor', 'REVIEW_REQUIRED');
    result.foreignEvidenceRejection = await reject(before, { selectedEvidence: [c.type === 'missing' ? 'E-W1' : 'E-M1'] }, 'counselor', 'INVALID_EVIDENCE');
    const request = `리허설 ${result.name}: ${c.type === 'missing' ? '차량 위치와 인도 여부는 센터 확인이 필요합니다.' : '주문 비스킷 18 EA와 수령 진술 휴지 1 BOX를 대조하고 원인은 센터 확인이 필요합니다.'}`;
    await page.getByPlaceholder('경영주가 요청한 내용을 확인해 주세요.').fill(request);
    await page.getByLabel('수령 수량(경영주 진술)', { exact: true }).fill(c.type === 'missing' ? '' : '1');
    await page.getByLabel('수령 단위', { exact: true }).fill(c.type === 'missing' ? '' : 'BOX');
    await page.locator('.department-card select').selectOption(c.type === 'missing' ? 'delivery' : 'warehouse');
    await page.getByRole('checkbox').check(); assert.equal(await transfer.isEnabled(), true);
    await page.getByPlaceholder('경영주가 요청한 내용을 확인해 주세요.').fill(request + ' 합성 업무 검증.');
    assert.equal(await page.getByRole('checkbox').isChecked(), false); assert.equal(await transfer.isDisabled(), true);
    await page.getByRole('checkbox').check();
    const saved = await ui(url, 'PATCH', () => transfer.click());
    assert.equal(saved.status, 'handed_off'); assert.equal(saved.reviewConfirmed, true);
    assert.equal(saved.intake.quantity, c.type === 'missing' ? null : 1);
    if (c.type === 'wrong') { assert.equal(saved.intake.unit, 'BOX'); assert.equal(saved.expected.quantity, 18); assert.equal(saved.expected.unit, 'EA'); }
    assert.deepEqual(await get(id), saved); return { status: saved.status, revision: saved.revision, intake: saved.intake, selectedEvidence: saved.selectedEvidence };
  });
  await stage('center-intermediate-pending-and-final', async () => {
    await page.getByRole('heading', { name: '센터 회신', exact: true }).waitFor();
    const final = page.getByRole('button', { name: '최종 회신·처리 완료', exact: true });
    assert.equal(await final.isDisabled(), true);
    const pending = `리허설 ${result.name} 원본 기록 대조`;
    await page.getByLabel('경영주에게 등록할 회신 필수').fill('합성 시연 중간 회신: 기록 차이를 확인했고 원인은 추가 확인 중입니다.');
    await page.getByLabel('남은 조치 내용').fill(pending); await page.getByRole('button', { name: '조치 추가', exact: true }).click();
    assert.equal(await final.isDisabled(), true);
    const intermediate = await ui(url, 'PATCH', () => page.getByRole('button', { name: '중간 회신 등록', exact: true }).click());
    assert.equal(intermediate.status, 'in_progress'); assert.deepEqual(intermediate.pendingActions, [pending]);
    assert.deepEqual(await get(id), intermediate);
    result.pendingRejection = await reject(intermediate, { status: 'closed' }, 'center', 'ACTIONS_PENDING');
    await nav('경영주 접수'); await page.getByLabel('접수 건 선택').selectOption(id);
    assert.ok((await page.locator('.registered-reply').innerText()).includes(intermediate.reply));
    assert.ok((await page.locator('.receipt').innerText()).includes('처리 중'));
    await nav('센터 회신');
    await page.getByRole('button', { name: `${pending} 조치 완료`, exact: true }).click();
    const reply = `합성 시연 ${result.name} 최종 회신: 원본 대조와 확인 요청 정리를 완료했습니다. 실제 배송·재고 조치는 실행하지 않았으며 원인을 확정하지 않습니다.`;
    await page.getByLabel('경영주에게 등록할 회신 필수').fill(reply); assert.equal(await final.isEnabled(), true);
    const closed = await ui(url, 'PATCH', () => final.click());
    assert.equal(closed.status, 'closed'); assert.deepEqual(closed.pendingActions, []); assert.equal(closed.reply, reply);
    assert.equal(closed.replyRegisteredBy, 'center'); assert.deepEqual(await get(id), closed);
    return { intermediateRevision: intermediate.revision, finalRevision: closed.revision, reply, status: closed.status };
  });
  await stage('owner-reply-and-reload-persistence', async () => {
    await nav('경영주 접수'); await page.getByLabel('접수 건 선택').selectOption(id);
    const saved = await get(id);
    assert.ok((await page.locator('.registered-reply').innerText()).includes(saved.reply));
    assert.ok((await page.locator('.receipt').innerText()).includes('처리 완료'));
    await page.reload({ waitUntil: 'networkidle' }); await nav('경영주 접수'); await page.getByLabel('접수 건 선택').selectOption(id);
    assert.ok((await page.locator('.registered-reply').innerText()).includes(saved.reply));
    assert.deepEqual(await get(id), saved);
    assert.equal(saved.sourceText, result.sourceText);
    await page.screenshot({ path: path.join(OUT, `${result.name}-closed.png`), fullPage: true });
    return { id, status: saved.status, revision: saved.revision, historyCount: saved.history.length, sourcePreserved: true };
  });
}

async function flow(round, c, manual = false) {
  const name = `${manual ? 'text' : `round${round}`}-${c.type}`;
  const result = { name, caseId: c.id, round, channel: manual ? 'text-manual' : 'voice-replay', started: new Date().toISOString() };
  (manual ? report.textManual : report.core).push(result);
  const base = `http://127.0.0.1:${manual ? 8824 : 8820 + round}`;
  const t = await contextFor(result, base); const { page, context, nav, select, stage, ui, get } = t;
  try {
    await page.goto(base, { waitUntil: 'networkidle' }); await page.getByRole('heading', { name: '상담 작업대', exact: true }).waitFor();
    let id = c.id;
    if (manual) {
      await stage('owner-text-intake-and-explicit-reference', async () => {
        await nav('경영주 접수'); await page.getByLabel('관련 기존 접수 연결(선택)').selectOption(c.id);
        result.sourceText = `합성 ${name}: ${c.sourceText}`;
        await page.getByLabel('상세 내용', { exact: true }).fill(result.sourceText);
        const saved = await ui('/api/intake', 'POST', () => page.getByRole('button', { name: '문의 접수하기' }).click(), 201);
        id = saved.id; result.caseId = id; assert.equal(saved.sourceText, result.sourceText); assert.equal(saved.linkedFixtureId, c.id);
        assert.deepEqual(await get(id), saved); await nav('상담 작업대'); await select(id);
        return { id, linkedFixtureId: saved.linkedFixtureId, rawPreserved: true };
      });
      await stage('text-replay-unavailable-visible-no-paid-fallback', async () => {
        const before = await get(id);
        const denied = await ui(`/api/cases/${id}/analyze`, 'POST', () => page.getByRole('button', { name: '저장된 분석 결과 재생' }).click(), 409);
        assert.equal(denied.error.code, 'REPLAY_NOT_AVAILABLE');
        await page.getByRole('alert').filter({ hasText: '사전 리플레이가 없습니다' }).waitFor(); assert.deepEqual(await get(id), before);
        return { code: denied.error.code, actualAiAnalysis: 'NOT_RUN', continuation: 'human manual review' };
      });
    } else {
      await select(id); result.sourceText = c.sourceText;
      await stage('voice-ended-before-explicit-replay', async () => {
        const audio = page.getByLabel('합성 상담 통화');
        await page.getByLabel('분석 방식').selectOption('demo-live');
        const live = page.getByRole('button', { name: 'AI 전사·정제 실행' }); assert.equal(await live.isDisabled(), true);
        await audio.evaluate(async a => { a.playbackRate = 1; a.volume = 1; a.muted = false; await a.play(); });
        await page.waitForFunction(() => document.querySelector('audio')?.currentTime > 0.2);
        assert.equal(await live.isDisabled(), true);
        await page.waitForFunction(() => document.querySelector('audio')?.ended, {}, { timeout: 65000 });
        result.audioPlayback = await audio.evaluate(a => ({ ended: a.ended, currentTime: a.currentTime, duration: a.duration, rate: a.playbackRate, volume: a.volume, muted: a.muted, error: a.error?.code || null }));
        assert.equal(result.audioPlayback.ended, true); assert.equal(result.audioPlayback.rate, 1); assert.equal(result.audioPlayback.error, null);
        assert.equal(await live.isEnabled(), true); await page.getByLabel('분석 방식').selectOption('replay');
        const analyzed = await ui(`/api/cases/${id}/analyze`, 'POST', () => page.getByRole('button', { name: '저장된 분석 결과 재생' }).click());
        assert.equal(analyzed.mode, 'replay'); assert.deepEqual(analyzed.analysis, c.replayAnalysis);
        assert.equal((await get(id)).analysisRequestId, analyzed.requestId);
        await page.getByText('실제 AI 호출은 하지 않았습니다.', { exact: false }).waitFor();
        return { requestId: analyzed.requestId, revision: analyzed.revision, mode: analyzed.mode, audio: result.audioPlayback };
      });
    }
    await completeBusiness(c, id, result, t, !manual);
    assert.equal(result.errors.filter(e => e.kind === 'pageerror').length, 0);
    result.status = 'PASS';
  } catch (e) {
    result.status = 'FAIL'; result.message = e.message;
    await page.screenshot({ path: path.join(OUT, `${name}-failure.png`), fullPage: true }).catch(() => {});
  } finally {
    result.finished = new Date().toISOString(); result.durationSeconds = (Date.parse(result.finished) - Date.parse(result.started)) / 1000;
    result.recording = await page.video().path(); await context.close(); await save();
    console.log(`${result.status} ${name} ${result.durationSeconds}s ${result.message || ''}`);
  }
}

try {
  await waitReady(); report.release = JSON.parse(await readFile(path.join(OUT, 'server.json'), 'utf8'));
  browser = await chromium.launch({ headless: true, executablePath: process.env.E2E_CHROMIUM || 'C:/Users/choi8/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe' });
  for (let round = 1; round <= 3; round++) {
    await Promise.all(fixture.cases.map(c => flow(round, c)));
    if (report.core.some(r => r.status !== 'PASS')) throw new Error('Core round failed; remaining repetitions not run until cause is examined.');
  }
  for (const c of fixture.cases) await flow(4, c, true);
  const result = { name: 'offline-api-unavailable', started: new Date().toISOString() }; report.offline.push(result);
  const t = await contextFor(result, 'http://127.0.0.1:8824'); const { page, context, nav } = t;
  try {
    await context.route('**/api/**', route => route.abort('internetdisconnected'));
    await page.goto('http://127.0.0.1:8824', { waitUntil: 'networkidle' });
    await page.getByRole('alert').filter({ hasText: '서버 연결 확인이 필요합니다' }).waitFor();
    await page.getByRole('button', { name: '합성 예시 열람', exact: true }).click();
    await page.getByText('현재 예시 열람 중입니다. 변경 사항은 저장되지 않습니다.', { exact: true }).waitFor();
    assert.equal(await page.getByRole('button', { name: '접수 내용 저장', exact: true }).isDisabled(), true);
    assert.equal(await page.getByRole('button', { name: '확인 후 센터 전달' }).isDisabled(), true);
    for (const label of ['WMS 작업 확인', 'TMS 배송 확인', '경영주 접수']) await nav(label);
    assert.equal(await page.getByRole('button', { name: '문의 접수하기' }).isDisabled(), true);
    result.safetyStatus = 'PASS'; result.completeFlowStatus = 'BLOCKED'; result.reason = 'Offline example mode is read-only. Entire save/handoff/reply flow cannot complete without API.';
    await page.screenshot({ path: path.join(OUT, 'offline-readonly.png'), fullPage: true });
  } catch (e) { result.safetyStatus = 'FAIL'; result.completeFlowStatus = 'FAIL'; result.reason = e.message; }
  finally { result.finished = new Date().toISOString(); result.recording = await page.video().path(); await context.close(); }
} catch (e) { report.fatal = e.message; }
finally {
  if (browser) await browser.close();
  server.kill(); await writeFile(path.join(OUT, 'server.log'), serverLog);
  report.finished = new Date().toISOString();
  report.sourceHashesEnd = Object.fromEntries(await Promise.all(Object.keys(report.release?.backendHashes || {}).map(async name => [name, createHash('sha256').update(await readFile(path.join(ROOT, name))).digest('hex')])));
  report.backendChangedOnDisk = Object.keys(report.sourceHashesEnd).filter(name => report.sourceHashesEnd[name] !== report.release.backendHashes[name]);
  report.frontendSourceEnd = execFileSync(path.join(ROOT, '.venv/Scripts/python.exe'), ['-c', 'from pathlib import Path; from scripts.build_deployment_bundle import source_fingerprint; print(source_fingerprint(Path.cwd()))'], { cwd: ROOT, env: { ...env, PYTHONUTF8: '1' }, encoding: 'utf8' }).trim();
  report.frontendChangedOnDisk = report.frontendSourceEnd !== report.release?.buildStamp.sourceAfter;
  report.exitGate = exitGate(report);
  report.summary = report.exitGate.summary;
  await save(); console.log(JSON.stringify({ out: OUT, ...report.summary, fatal: report.fatal }));
  process.exitCode = report.exitGate.exitCode;
}
