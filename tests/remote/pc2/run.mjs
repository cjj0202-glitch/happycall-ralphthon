import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { buildHarness, ROOT } from './build.mjs';
import { startServer } from './server.mjs';

const e2eRequire = createRequire(path.join(ROOT, 'tests/e2e/package.json'));
const { chromium } = e2eRequire('playwright');
const REPORT = path.join(ROOT, 'reports/pc2');
const SHOTS = path.join(REPORT, 'screenshots');
const RESULT_NAME = process.env.N02_CHECK_FILTER ? 'browser-focused-results.json' : 'browser-results.json';
await mkdir(SHOTS, { recursive: true });
const report = {
  suite: 'N02 isolated actual CallReview browser acceptance',
  startedAt: new Date().toISOString(), base: 'http://127.0.0.1:3122',
  harness: 'tests/remote/pc2/harness.tsx imports the actual component, CSS module, app tokens/globals and read-only synthetic fixture',
  executor: 'AI Playwright technical observation, not human listening or Silent Test',
  checkFilter: process.env.N02_CHECK_FILTER || null,
  checks: [], pageErrors: [], consoleErrors: [], unexpectedRequests: [], media: [],
  limitations: [
    'No paid AI/API calls; no real customer, operational data, server mutation or shared product-file edits.',
    'Headless browser media completion proves decoding and event/clock behavior, not OS speaker output or human intelligibility.',
    'Artificial short/silent/invalid WAV and timestamps are explicit test fixtures; timestamp tests do not prove linguistic alignment of v2 STT.',
    'The harness tests component props and local callbacks. Parent analysis gating, API persistence and whole-service integration remain pc1 acceptance work.',
    'Comparison is AI suggestion versus current caseData.intake. This component cannot restore operator input already overwritten upstream.',
  ],
};
try {
  const previous = JSON.parse(await readFile(path.join(REPORT, RESULT_NAME), 'utf8'));
  report.previousRuns = [...(previous.previousRuns || []), {
    startedAt: previous.startedAt, finishedAt: previous.finishedAt || null,
    checkFilter: previous.checkFilter || null,
    passed: previous.passed, failed: previous.failed, total: previous.total,
    failures: previous.checks.filter(c => c.status === 'FAIL'),
    checks: previous.checks,
    media: previous.media || [],
    backgroundSegmentObservation: previous.backgroundSegmentObservation || null,
    sourceHashes: previous.sourceHashesStart,
    sourceUnchangedDuringRun: previous.sourceUnchangedDuringRun,
    note: 'Prior assertions, successful media measurements and environment errors retained; current results below are separate re-execution.',
  }];
} catch (error) { if (error.code !== 'ENOENT') throw error; }
const sourceFiles = ['apps/web/components/CallReview.tsx', 'apps/web/components/CallReview.module.css', 'apps/web/app/tokens.css', 'apps/web/app/globals.css', 'apps/web/lib/types.ts', 'data/fixtures/cases.json', 'data/demo-media-manifest.json', 'reports/e2e/normalized-voice-live.json'];
async function hashes() { return Object.fromEntries(await Promise.all(sourceFiles.map(async name => [name, createHash('sha256').update(await readFile(path.join(ROOT, name))).digest('hex')]))); }
async function save() {
  report.passed = report.checks.filter(x => x.status === 'PASS').length;
  report.failed = report.checks.filter(x => x.status === 'FAIL').length;
  report.total = report.checks.length;
  await writeFile(path.join(REPORT, RESULT_NAME), JSON.stringify(report, null, 2) + '\n');
}
async function check(id, expected, work) {
  if (process.env.N02_CHECK_FILTER && !new RegExp(process.env.N02_CHECK_FILTER).test(id)) return;
  const start = Date.now();
  try {
    const actual = await work();
    report.checks.push({ id, status: 'PASS', expected, actual: actual ?? {}, durationMs: Date.now() - start });
    console.log(`PASS ${id}`);
  } catch (error) {
    report.checks.push({ id, status: 'FAIL', expected, error: error.stack || String(error), durationMs: Date.now() - start });
    console.log(`FAIL ${id}: ${error.message}`);
  }
  await save();
}

await buildHarness();
report.sourceHashesStart = await hashes();
const service = await startServer(3122); // Fails on occupied port; never terminates another process.
let browser;
let browserServer;
async function boundedCleanup(name, action, timeoutMs = 10000) {
  console.log(`CLEANUP ${name} begin`);
  const started = Date.now();
  let timer;
  const result = await Promise.race([
    Promise.resolve().then(action).then(() => ({ status: 'complete' }), error => ({ status: 'error', error: String(error) })),
    new Promise(resolve => { timer = setTimeout(() => resolve({ status: 'timeout', timeoutMs }), timeoutMs); }),
  ]);
  clearTimeout(timer);
  (report.cleanup ||= []).push({ name, ...result, elapsedMs: Date.now() - started });
  console.log(`CLEANUP ${name} ${result.status}`);
  return result.status === 'complete';
}
try {
  // The browser control endpoint is local to this test, like the HTTP harness.
  // Do not leave Playwright's host unspecified (which binds all interfaces).
  const options = { headless: true, host: '127.0.0.1' };
  if (process.env.E2E_CHROMIUM) options.executablePath = process.env.E2E_CHROMIUM;
  else options.channel = process.env.N02_BROWSER_CHANNEL || 'msedge';
  browserServer = await chromium.launchServer(options);
  browser = await chromium.connect(browserServer.wsEndpoint());
  report.ownedBrowserPid = browserServer.process().pid;
  report.browserVersion = browser.version();
  report.browserLaunch = options;
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
  await context.route('**/*', async route => {
    const req = route.request();
    if (new URL(req.url()).origin !== service.origin || !['GET', 'HEAD'].includes(req.method())) {
      report.unexpectedRequests.push({ method: req.method(), url: req.url() });
      await route.abort('blockedbyclient');
    } else await route.continue();
  });
  async function open() {
    const p = await context.newPage();
    p.setDefaultTimeout(8000);
    p.on('pageerror', e => report.pageErrors.push(e.stack || e.message));
    p.on('console', msg => { if (msg.type() === 'error') report.consoleErrors.push(msg.text()); });
    await p.goto(service.origin);
    await p.waitForFunction(() => window.__n02?.ready);
    return p;
  }
  async function mount(p, name, props = {}) {
    const generation = await p.evaluate(() => window.__n02.generation);
    await p.evaluate(({ name, props }) => window.__n02.mount(name, props), { name, props });
    await p.waitForFunction(g => window.__n02.generation > g, generation);
  }
  async function state(p) {
    return p.evaluate(() => {
      const a = document.querySelector('audio');
      return { callbacks: window.__n02.events.length, retries: window.__n02.retries, audio: a ? { paused: a.paused, currentTime: a.currentTime, duration: Number.isFinite(a.duration) ? a.duration : null, ended: a.ended, rate: a.playbackRate, muted: a.muted, volume: a.volume, controls: a.controls, error: a.error?.code || null, src: a.currentSrc, played: Array.from({ length: a.played.length }, (_, i) => [a.played.start(i), a.played.end(i)]) } : null };
    });
  }
  async function metadata(p) { await p.waitForFunction(() => { const a = document.querySelector('audio'); return a && Number.isFinite(a.duration) && a.duration > 0; }); }
  const fullButton = p => p.getByRole('button', { name: '처음부터 전체 통화 재생', exact: true });
  const segmentButtons = p => p.getByRole('button', { name: /발화 .*구간 재생/ });

  // Both genuine WAVs run concurrently in separate browser pages at 1x. No
  // time mock, seek, rate increase or synthetic ended event in these checks.
  const manifest = JSON.parse(await readFile(path.join(ROOT, 'data/demo-media-manifest.json'), 'utf8'));
  await Promise.all([1, 2].map(async n => {
    await check(`C01-${n}-real-v2-complete`, 'Real v2 WAV matches manifest, decodes and naturally ends at 1x; exactly one completion callback, error=0', async () => {
      const asset = manifest.assets.find(x => x.name === `CASE-000${n}.wav`);
      const bytes = await readFile(path.join(ROOT, 'apps/web/public/demo', asset.name));
      const hash = createHash('sha256').update(bytes).digest('hex');
      assert.equal(hash, asset.sha256);
      const p = await open();
      try {
        await mount(p, `real-${n}`);
        await metadata(p);
        const before = await state(p);
        assert.ok(before.audio.controls);
        assert.ok(Math.abs(before.audio.duration - asset.durationSeconds) < 0.03);
        assert.equal(before.audio.rate, 1);
        const wall = Date.now();
        await fullButton(p).click();
        await p.waitForFunction(() => window.__n02.events.length === 1, null, { timeout: 75000 });
        const after = await state(p);
        assert.equal(after.audio.error, null); assert.ok(after.audio.ended);
        assert.equal(after.audio.rate, 1);
        assert.ok(Date.now() - wall >= (asset.durationSeconds - 1) * 1000, 'must play the real duration');
        await p.locator('audio').evaluate(a => a.dispatchEvent(new Event('ended')));
        assert.equal((await state(p)).callbacks, 1, 'duplicate ended must not duplicate callback');
        await p.screenshot({ path: path.join(SHOTS, `real-v2-${n}-complete.png`), fullPage: true });
        const result = { name: asset.name, hash, expectedSeconds: asset.durationSeconds, wallElapsedMs: Date.now() - wall, ...after };
        report.media.push(result);
        return result;
      } finally { await boundedCleanup(`real-${n}-page`, () => p.close()); }
    });
  }));
  const p = await open();
  await check('C02-segment-clock', 'Selected timed utterance plays the same source, pauses around its end, completion callback remains 0', async () => {
    await mount(p, 'comparison'); await metadata(p);
    const src = (await state(p)).audio.src;
    const label = await segmentButtons(p).first().getAttribute('aria-label');
    assert.match(label, /0:00\.150~0:00\.800/);
    await segmentButtons(p).first().click();
    await p.waitForFunction(() => { const a = document.querySelector('audio'); return a.paused && a.currentTime >= 0.7; });
    const actual = await state(p);
    assert.equal(actual.audio.src, src); assert.ok(actual.audio.currentTime <= 1.15); assert.equal(actual.callbacks, 0);
    return { label, ...actual };
  });
  await check('C03-quantity-context', 'Current intake 1 EA, AI suggestion 1 BOX and order18EA remain distinct; quote visible; no input mutation', async () => {
    await mount(p, 'comparison');
    const original = await p.evaluate(() => window.__n02.snapshot);
    const text = await p.locator('main').innerText();
    assert.match(text, /1\s*EA/); assert.match(text, /1\s*BOX/); assert.match(text, /18\s*EA/);
    assert.match(text, /1 EA가 아니라 1 BOX/);
    assert.match(text, /미확인/);
    assert.deepEqual(await p.getByRole('region', { name: '수령 단위(경영주 진술) 비교', exact: true }).locator('dd').allTextContents(), ['BOX', 'EA']);
    assert.deepEqual(await p.getByRole('region', { name: '수령 수량(경영주 진술) 비교', exact: true }).locator('dd').allTextContents(), ['1', '1']);
    assert.equal(await p.evaluate(() => JSON.stringify(window.__n02.config.caseData)), original);
    await p.screenshot({ path: path.join(SHOTS, 'comparison-1440.png'), fullPage: true });
    return { current: '1 EA', proposal: '1 BOX', order: '18 EA', unchanged: true };
  });
  await check('C04-null-zero', 'Unknown AI store/quantity remain unknown; explicit operator quantity0 stays0; no store fallback', async () => {
    await mount(p, 'null-zero');
    const text = await p.locator('main').innerText();
    assert.match(text, /미확인/); assert.match(text, /(?:^|\s)0(?:\s|$)/);
    assert.deepEqual(await p.getByRole('region', { name: '점포 ID 비교', exact: true }).locator('dd').allTextContents(), ['미확인', '미확인']);
    assert.deepEqual(await p.getByRole('region', { name: '수령 수량(경영주 진술) 비교', exact: true }).locator('dd').allTextContents(), ['미확인', '0']);
    const actual = await p.evaluate(() => window.__n02.config.caseData);
    assert.equal(actual.analysis.fields.storeId, null); assert.equal(actual.analysis.fields.quantity, null); assert.equal(actual.intake.quantity, 0);
    return { immutableInput: { aiStore: actual.analysis.fields.storeId, aiQuantity: actual.analysis.fields.quantity, intakeQuantity: actual.intake.quantity }, visibleText: text };
  });
  await check('C05-analysis-states-retry', 'Loading/error visible; retry disabled before full playback, calls only supplied callback after full playback, disabled prop blocks', async () => {
    await mount(p, 'comparison', { analysisState: 'loading' });
    assert.match(await p.locator('main').innerText(), /분석 중|분석하고|분석을 진행/);
    await p.evaluate(() => window.__n02.update({ analysisState: 'error', analysisError: 'N02 합성 분석 오류' }));
    await p.getByRole('alert').filter({ hasText: 'N02 합성 분석 오류' }).waitFor();
    const retry = p.getByRole('button', { name: 'AI 분석 다시 시도', exact: true });
    assert.ok(await retry.isDisabled());
    await fullButton(p).click();
    await p.waitForFunction(() => window.__n02.events.length === 1);
    await retry.click(); assert.equal((await state(p)).retries, 1);
    await p.evaluate(() => window.__n02.update({ disabled: true }));
    await p.waitForFunction(() => window.__n02.config.disabled === true);
    assert.ok(await retry.isDisabled());
    return await state(p);
  });
  await check('C06-source-provenance', 'Explicit replay/demo-live labels and unknown default; original text remains distinct, no source inference from fixture presence', async () => {
    const transcript = p.getByRole('region', { name: '화자별 대화록', exact: true });
    const replayLabel = '합성 대화록 · 저장 결과 재생';
    const liveLabel = '실제 STT 결과 · 인식 오류 확인 필요';
    const unknownLabel = '전사 출처 미확인';
    await mount(p, 'comparison', { transcriptMode: 'replay' });
    await transcript.getByText(replayLabel, { exact: true }).waitFor();
    assert.equal(await transcript.getByText(liveLabel, { exact: true }).count(), 0);
    await p.evaluate(() => window.__n02.update({ transcriptMode: 'demo-live' }));
    await transcript.getByText(liveLabel, { exact: true }).waitFor();
    assert.equal(await transcript.getByText(replayLabel, { exact: true }).count(), 0);
    await p.evaluate(() => window.__n02.update({ transcriptMode: undefined }));
    await transcript.getByText(unknownLabel, { exact: true }).waitFor();
    assert.equal(await transcript.getByText(liveLabel, { exact: true }).count(), 0);
    await p.evaluate(() => window.__n02.update({ caseData: { ...window.__n02.config.caseData, analysisMode: 'demo-live' } }));
    await transcript.getByText(liveLabel, { exact: true }).waitFor();
    await p.evaluate(() => window.__n02.update({ transcriptMode: 'replay' }));
    await transcript.getByText(replayLabel, { exact: true }).waitFor();
    await mount(p, 'stored-live');
    await p.evaluate(() => window.__n02.update({ transcriptMode: undefined }));
    await transcript.getByText(liveLabel, { exact: true }).waitFor();
    const lines = transcript.locator('li');
    assert.equal(await lines.count(), 14);
    const speakerA = transcript.getByText('A', { exact: true }).first();
    const speakerB = transcript.getByText('B', { exact: true }).first();
    await speakerA.waitFor(); await speakerB.waitFor();
    assert.equal(await transcript.getByText('경영주', { exact: true }).count(), 0);
    assert.equal(await transcript.getByText('상담원', { exact: true }).count(), 0);
    await transcript.getByText('아니요, 휴지 1개가 아니라 한 박스예요.', { exact: true }).waitFor();
    const colors = { A: await speakerA.evaluate(el => getComputedStyle(el).color), B: await speakerB.evaluate(el => getComputedStyle(el).color) };
    assert.notEqual(colors.A, colors.B, 'Stored anonymous A/B speakers should be visually distinguishable without guessing identities');
    assert.equal(await p.getByRole('region', { name: '점포 ID 비교', exact: true }).locator('dd').first().innerText(), '미확인');
    await p.screenshot({ path: path.join(SHOTS, 'stored-live-transcript.png'), fullPage: true });
    return { scope: 'region: 화자별 대화록, exact text only', replayLabel, liveLabel, unknownLabel, analysisModeFallback: 'demo-live', explicitPropOverridesFallback: true, storedResponse: 'reports/e2e/normalized-voice-live.json', storedSegments: 14, storedSpeakerColors: colors, storeId: null, newApiCalls: 0 };
  });
  for (const kind of ['missing', '404', 'damaged', 'zero']) {
    await check(`C07-${kind}`, 'Missing/unusable media visibly distinguished; completion0 and no other case substituted', async () => {
      await mount(p, kind);
      if (kind !== 'missing') await p.getByRole('alert').filter({ hasText: /음원|음성/ }).waitFor({ timeout: 10000 });
      const actual = await state(p);
      assert.equal(actual.callbacks, 0);
      const text = await p.locator('main').innerText(); assert.match(text, /없|오류|실패|불가|불러오|재생할 수/);
      if (kind === 'missing') assert.equal(actual.audio, null);
      else assert.match(actual.audio.src, new RegExp(kind === '404' ? 'not-found' : kind));
      return { ...actual, visibleText: text };
    });
  }
  await check('C08-invalid-timestamps', 'Missing/negative/reversed/equal/NaN/infinite/out-of-range timestamps cannot initiate segment playback; text preserved', async () => {
    await mount(p, 'invalid-timestamps'); await metadata(p);
    const buttons = segmentButtons(p);
    const count = await buttons.count();
    for (let i = 0; i < count; i++) assert.ok(await buttons.nth(i).isDisabled());
    const text = await p.locator('main').innerText();
    for (const phrase of ['시각 없음', '음수 시각', '역전 시각', 'NaN 시각', '음원보다 긴 시각', '끝 시각 없음']) assert.ok(text.includes(phrase));
    assert.match(text, /구간|시각|타임/);
    return { invalidInputs: 8, segmentButtons: count, ...await state(p) };
  });
  await check('C09-seek-cannot-unlock', 'Seeking to end and synthetic ended without continuous playback must not emit callback', async () => {
    await mount(p, 'comparison'); await metadata(p);
    await p.locator('audio').evaluate(async a => { a.currentTime = a.duration - 0.15; await a.play(); });
    await p.waitForFunction(() => document.querySelector('audio').ended, null, { timeout: 5000 });
    assert.equal((await state(p)).callbacks, 0);
    await p.locator('audio').evaluate(a => a.dispatchEvent(new Event('ended')));
    assert.equal((await state(p)).callbacks, 0);
    return await state(p);
  });
  await check('C10-controls-keyboard', 'Native controls retained; speed/mute/volume UI matches actual audio; keyboard can start full playback with visible focus', async () => {
    await mount(p, 'comparison'); await metadata(p);
    assert.ok(await p.locator('audio').getAttribute('controls') !== null);
    const speed = p.getByLabel('통화 재생 속도', { exact: true });
    await speed.selectOption('1.5');
    assert.equal((await state(p)).audio.rate, 1.5);
    const mute = p.getByRole('button', { name: '통화 음소거', exact: true });
    await mute.click(); assert.equal((await state(p)).audio.muted, true);
    const volume = p.getByLabel('통화 볼륨', { exact: true });
    await volume.focus(); await p.keyboard.press('Home');
    assert.equal((await state(p)).audio.volume, 0);
    const display = await p.locator('main').innerText(); assert.match(display, /1\.5|150%/); assert.match(display, /음소거|0%/);
    await speed.focus(); await p.keyboard.press('Tab');
    const tabTarget = await p.evaluate(() => ({ tag: document.activeElement.tagName, name: document.activeElement.getAttribute('aria-label') || document.activeElement.textContent }));
    await fullButton(p).focus();
    const outline = await fullButton(p).evaluate(el => getComputedStyle(el).outlineStyle);
    assert.notEqual(outline, 'none');
    await p.keyboard.press('Enter');
    await p.waitForFunction(() => !document.querySelector('audio').paused);
    return { tabTarget, focusOutline: outline, ...await state(p) };
  });
  await check('C11-case-url-stale-event', 'Case and same-ID URL switches stop old audio, clear completion and ignore detached ended/error events', async () => {
    await mount(p, 'comparison'); await metadata(p); await fullButton(p).click();
    await p.locator('audio').evaluate(a => { window.__oldAudio = a; });
    await p.evaluate(() => window.__n02.switchCase('comparison', { id: 'SYN-N02-SWITCH', audioUrl: '/test-audio/silent.wav' }));
    await p.waitForFunction(() => document.querySelector('audio').currentSrc.includes('silent.wav'));
    const oldPaused = await p.evaluate(() => window.__oldAudio.paused);
    assert.ok(oldPaused); assert.equal((await state(p)).callbacks, 0);
    await p.evaluate(() => { window.__oldAudio.dispatchEvent(new Event('ended')); window.__oldAudio.dispatchEvent(new Event('error')); });
    assert.equal((await state(p)).callbacks, 0);
    await p.evaluate(() => window.__n02.update({ caseData: { ...window.__n02.config.caseData, audioUrl: '/test-audio/short.wav' } }));
    await p.waitForFunction(() => document.querySelector('audio').currentSrc.includes('short.wav'));
    assert.equal((await state(p)).callbacks, 0);
    await fullButton(p).click(); await p.waitForFunction(() => !document.querySelector('audio').paused);
    await p.evaluate(() => window.__n02.update({ disabled: true }));
    await p.waitForFunction(() => document.querySelector('audio').paused);
    assert.ok(await fullButton(p).isDisabled());
    return { oldPaused, ...await state(p) };
  });
  for (const width of [1440, 1024, 390]) {
    await check(`C12-layout-${width}`, 'Long unbroken transcript/fields/question/error preserve zero document horizontal overflow and visible focus', async () => {
      await p.setViewportSize({ width, height: 1000 });
      await mount(p, 'long', { analysisState: 'error', analysisError: 'LONG_ERROR_'.repeat(60) });
      const dimensions = await p.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth, inner: innerWidth }));
      assert.ok(dimensions.scroll <= dimensions.client, JSON.stringify(dimensions));
      await fullButton(p).focus();
      const bounds = await fullButton(p).boundingBox(); assert.ok(bounds.x >= 0 && bounds.x + bounds.width <= width + 1);
      await p.screenshot({ path: path.join(SHOTS, `long-layout-${width}.png`), fullPage: true });
      await p.evaluate(() => window.scrollTo(0, 0));
      await p.screenshot({ path: path.join(SHOTS, `viewport-${width}.png`) });
      return { ...dimensions, fullButton: bounds };
    });
  }
  await check('C13-silent-technical-only', 'Silent WAV may decode/end, but UI/test makes no human intelligibility or speaker-output success claim', async () => {
    await p.setViewportSize({ width: 1440, height: 1000 }); await mount(p, 'silent'); await metadata(p);
    await fullButton(p).click();
    await p.waitForFunction(() => document.querySelector('audio').ended);
    const actual = await state(p);
    assert.equal(actual.audio.error, null);
    assert.ok(!/명료도\s*(합격|통과)|청취\s*(합격|성공)/.test(await p.locator('main').innerText()));
    return { ...actual, humanListeningVerified: false, actualSampleContent: 'all PCM samples0' };
  });
  await check('C14-frozen-props', 'Playback, transcript interaction and repeated prop updates do not mutate frozen source/analysis/intake', async () => {
    await mount(p, 'comparison'); await metadata(p);
    const before = await p.evaluate(() => JSON.stringify(window.__n02.config.caseData));
    await segmentButtons(p).first().click();
    await p.getByLabel('대화록 표시', { exact: true }).click();
    await p.getByLabel('대화록 표시', { exact: true }).click();
    const after = await p.evaluate(() => JSON.stringify(window.__n02.config.caseData));
    assert.equal(after, before);
    assert.ok(await p.evaluate(() => Object.isFrozen(window.__n02.config.caseData.analysis.fields)));
    return { unchanged: true, frozenNestedFields: true };
  });
  await check('C16-disabled-midplay-and-resume', 'Disabled mid-play pauses audio and blocks controls; reenable + jump to end cannot unlock, fresh full replay can', async () => {
    await mount(p, 'comparison'); await metadata(p); await fullButton(p).click();
    await p.waitForFunction(() => document.querySelector('audio').currentTime > 0.25);
    await p.evaluate(() => window.__n02.update({ disabled: true }));
    await p.waitForFunction(() => window.__n02.config.disabled === true && document.querySelector('audio').paused);
    assert.ok(await fullButton(p).isDisabled());
    assert.equal((await state(p)).audio.controls, false);
    await p.evaluate(() => window.__n02.update({ disabled: false }));
    await p.waitForFunction(() => window.__n02.config.disabled === false);
    await p.locator('audio').evaluate(async a => { a.currentTime = a.duration - 0.1; await a.play(); });
    await p.waitForFunction(() => document.querySelector('audio').ended);
    assert.equal((await state(p)).callbacks, 0);
    await fullButton(p).click(); await p.waitForFunction(() => window.__n02.events.length === 1);
    return await state(p);
  });
  await check('C17-seek-outside-segment', 'Seeking outside a selected interval pauses it and cannot emit whole-call completion', async () => {
    await mount(p, 'comparison'); await metadata(p);
    await segmentButtons(p).first().click();
    await p.locator('audio').evaluate(a => { a.currentTime = 2.5; });
    await p.waitForFunction(() => document.querySelector('audio').paused);
    assert.equal((await state(p)).callbacks, 0);
    return await state(p);
  });
  await check('C18-background-segment', 'A real short-WAV segment stops at its boundary when requestAnimationFrame callbacks are suspended; this injected condition is not proof of real hidden-tab behavior', async () => {
    await mount(p, 'comparison'); await metadata(p);
    await p.evaluate(() => {
      window.__originalRAF = window.requestAnimationFrame;
      window.__originalCAF = window.cancelAnimationFrame;
      window.requestAnimationFrame = () => 0;
      window.cancelAnimationFrame = () => {};
      window.__segmentProbe = [];
      document.querySelector('audio').addEventListener('timeupdate', event => {
        const a = event.currentTarget;
        window.__segmentProbe.push({ time: a.currentTime, paused: a.paused, trusted: event.isTrusted });
      });
    });
    try {
      // No Playwright actionability wait after RAF suspension: start from the real
      // button handler; media time, timeupdate and decoder remain unmodified.
      await segmentButtons(p).first().evaluate(button => button.click());
      await p.waitForFunction(() => document.querySelector('audio').currentTime > 0.3, null, { polling: 50, timeout: 8000 });
      await p.waitForTimeout(1450);
      const actual = { injected: 'requestAnimationFrame and cancelAnimationFrame suspended', actualVisibility: await p.evaluate(() => document.visibilityState), expectedEnd: 0.8, ...await state(p), timeUpdates: await p.evaluate(() => window.__segmentProbe) };
      report.backgroundSegmentObservation = actual;
      assert.ok(actual.audio.paused && actual.audio.currentTime <= 1.15, JSON.stringify(actual));
      assert.ok(Math.max(...actual.audio.played.map(range => range[1])) <= 1.15, 'played range must remain within 350 ms of the segment end, not merely rewind its cursor after overrun');
      assert.equal(actual.callbacks, 0);
      await p.evaluate(() => {
        window.requestAnimationFrame = window.__originalRAF;
        window.cancelAnimationFrame = window.__originalCAF;
      });
      const frontPage = await context.newPage();
      let switchedVisibility;
      try {
        await frontPage.goto(service.origin); await frontPage.bringToFront();
        switchedVisibility = await p.evaluate(() => ({ hidden: document.hidden, visibilityState: document.visibilityState }));
      } finally { await frontPage.close(); await p.bringToFront(); }
      // Headless tabs may all remain visible. Exercise the branch explicitly and
      // keep this synthetic visibility event separate from real browser behavior.
      await mount(p, 'comparison'); await metadata(p);
      await segmentButtons(p).first().click();
      await p.waitForFunction(() => document.querySelector('audio').currentTime > 0.3);
      await p.evaluate(() => {
        Object.defineProperty(document, 'hidden', { configurable: true, value: true });
        Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' });
        document.dispatchEvent(new Event('visibilitychange'));
      });
      await p.waitForFunction(() => document.querySelector('audio').paused);
      const hiddenSegment = await state(p);
      assert.equal(hiddenSegment.callbacks, 0);
      assert.equal(hiddenSegment.audio.error, null);
      await segmentButtons(p).first().evaluate(button => button.click());
      assert.ok((await state(p)).audio.paused, 'hidden state must reject a new segment start');
      await p.evaluate(() => { delete document.hidden; delete document.visibilityState; document.dispatchEvent(new Event('visibilitychange')); });
      await mount(p, 'comparison'); await metadata(p); await fullButton(p).click();
      await p.waitForFunction(() => document.querySelector('audio').currentTime > 0.3);
      await p.evaluate(() => {
        Object.defineProperty(document, 'hidden', { configurable: true, value: true });
        Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' });
        document.dispatchEvent(new Event('visibilitychange'));
      });
      assert.equal((await state(p)).audio.paused, false, 'selected-clip hide policy must not pause full-call playback');
      await p.waitForFunction(() => window.__n02.events.length === 1, null, { polling: 50 });
      return { rafSuspension: actual, realTabSwitchObservation: switchedVisibility, realHiddenTabVerified: switchedVisibility.hidden, injectedVisibilitySegment: hiddenSegment, injectedVisibilityFullPlayback: await state(p) };
    } finally {
      await p.evaluate(() => {
        window.requestAnimationFrame = window.__originalRAF;
        window.cancelAnimationFrame = window.__originalCAF;
        delete document.hidden; delete document.visibilityState;
        document.dispatchEvent(new Event('visibilitychange'));
        document.querySelector('audio').pause();
      });
    }
  });
  await check('C19-completed-source-reset', 'After a completed call enables retry, case-ID and then same-ID audio-URL changes each reset the retry gate and ignore old events', async () => {
    await mount(p, 'comparison', { analysisState: 'error', analysisError: '합성 재시도 상태' }); await metadata(p);
    const retry = p.getByRole('button', { name: 'AI 분석 다시 시도', exact: true });
    await fullButton(p).click(); await p.waitForFunction(() => window.__n02.events.length === 1);
    assert.equal(await retry.isDisabled(), false);
    await p.locator('audio').evaluate(a => { window.__completedOldAudio = a; });
    await p.evaluate(() => window.__n02.switchCase('comparison', { id: 'SYN-N02-COMPLETED-SWITCH' }));
    await p.waitForFunction(() => window.__n02.config.caseData.id === 'SYN-N02-COMPLETED-SWITCH');
    assert.ok(await retry.isDisabled());
    await p.evaluate(() => window.__completedOldAudio.dispatchEvent(new Event('ended')));
    assert.equal((await state(p)).callbacks, 1);
    await metadata(p); await fullButton(p).click(); await p.waitForFunction(() => window.__n02.events.length === 2);
    assert.equal(await retry.isDisabled(), false);
    await p.evaluate(() => window.__n02.update({ caseData: { ...window.__n02.config.caseData, audioUrl: '/test-audio/silent.wav' } }));
    await p.waitForFunction(() => document.querySelector('audio').currentSrc.includes('silent.wav'));
    assert.ok(await retry.isDisabled());
    assert.equal((await state(p)).callbacks, 2);
    return { idChangeLockedRetry: true, sameIdUrlChangeLockedRetry: true, completedCallbacks: 2, ...await state(p) };
  });
  await check('C20-text-intake', 'Text intake has no audio gate, keeps its input visible, allows error retry immediately and still honors disabled', async () => {
    await mount(p, 'text', { analysisState: 'error', analysisError: '합성 텍스트 분석 오류' });
    assert.equal(await p.locator('audio').count(), 0);
    assert.equal(await fullButton(p).count(), 0);
    assert.equal(await segmentButtons(p).count(), 0);
    await p.getByText('텍스트 접수 · 음성 전사 없이 입력 원문과 분석 내용을 대조합니다.', { exact: true }).waitFor();
    await p.getByText('합성 텍스트 접수: 주문 18 EA, 수령 1 BOX의 단위를 확인해 주세요.', { exact: true }).waitFor();
    const retry = p.getByRole('button', { name: 'AI 분석 다시 시도', exact: true });
    assert.equal(await retry.isDisabled(), false);
    await retry.click(); assert.equal((await state(p)).retries, 1);
    await p.evaluate(() => window.__n02.update({ disabled: true }));
    await p.waitForFunction(() => window.__n02.config.disabled === true);
    assert.ok(await retry.isDisabled());
    assert.equal((await state(p)).callbacks, 0);
    await p.screenshot({ path: path.join(SHOTS, 'text-intake.png'), fullPage: true });
    return { voiceGateNotRequired: true, ...await state(p) };
  });
  await check('C15-no-external-no-render-error', 'No product API/external network attempt or React page exception', async () => {
    assert.deepEqual(report.unexpectedRequests, []);
    assert.deepEqual(report.pageErrors, []);
    return { externalRequests: 0, paidCalls: 0, pageErrors: 0, intentional404OrDecodeConsoleMessages: report.consoleErrors };
  });
  await boundedCleanup('final-page', () => p.close());
} finally {
  if (browser) await boundedCleanup('browser-connection', () => browser.close());
  if (browserServer) {
    const stopped = await boundedCleanup('owned-browser-server', () => browserServer.close());
    if (!stopped) await boundedCleanup('owned-browser-kill', () => browserServer.kill());
  }
  await boundedCleanup('owned-http-server', () => service.stop());
  report.serverRequests = service.requests;
  report.sourceHashesEnd = await hashes();
  report.sourceUnchangedDuringRun = JSON.stringify(report.sourceHashesStart) === JSON.stringify(report.sourceHashesEnd);
  report.finishedAt = new Date().toISOString();
  await save();
}
console.log(JSON.stringify({ passed: report.passed, failed: report.failed, total: report.total, output: `reports/pc2/${RESULT_NAME}` }));
if (report.failed) process.exitCode = 1;
