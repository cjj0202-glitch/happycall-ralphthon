import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { chromium } from 'playwright';
import { ROOT, MEDIA, sourceHashes, browserExecutable, startHarness } from './harness-server.mjs';
import { clipMutations } from './clip-mutations.mjs';

const output = path.join(ROOT, '.local/pc3-tests', new Date().toISOString().replace(/[:.]/g, '-'));
const report = {
  suite: 'N03 actual WmsScene standalone browser checks', startedAt: new Date().toISOString(),
  executor: 'AI Playwright; not human observation or full-app integration', coveragePhase: 'responsive, semantic, registration, media-integrity, interaction',
  sourceHashesStart: await sourceHashes(), checks: [], browserErrors: [], blockedExternal: [], output,
};
const fixture = JSON.parse(await readFile(path.join(ROOT, 'data/fixtures/cases.json'), 'utf8'));
const manifest = JSON.parse(await readFile(path.join(ROOT, 'data/demo-media-manifest.json'), 'utf8'));
const harness = await startHarness(output);
let browser;
try { browser = await chromium.launch({ headless: true, executablePath: browserExecutable(chromium), args: ['--autoplay-policy=no-user-gesture-required'] }); }
catch (error) { await harness.close(); throw error; }
report.browser = browser.version();
report.url = harness.url;
const context = await browser.newContext({ viewport: { width: 1365, height: 950 }, reducedMotion: 'no-preference' });
await context.route('**/*', async route => {
  const url = new URL(route.request().url());
  if (url.origin === harness.url || ['blob:', 'data:'].includes(url.protocol)) await route.continue();
  else { report.blockedExternal.push(url.href); await route.abort('blockedbyclient'); }
});
const page = await context.newPage();
page.setDefaultTimeout(8000);
page.on('pageerror', error => report.browserErrors.push({ type: 'pageerror', message: error.message }));
page.on('console', message => { if (message.type() === 'error') report.browserErrors.push({ type: 'console', message: message.text() }); });
const persist = async () => writeFile(path.join(output, 'results.json'), JSON.stringify({ ...report, requests: harness.state.requests }, null, 2));
const only = process.argv.find(arg => arg.startsWith('--only='))?.slice(7);
async function check(name, task) {
  if (only && name !== only) return;
  const started = Date.now();
  try { const evidence = await task(); report.checks.push({ name, status: 'PASS', elapsedMs: Date.now() - started, evidence }); }
  catch (error) {
    report.checks.push({ name, status: 'FAIL', elapsedMs: Date.now() - started, error: error.stack || String(error) });
    await page.screenshot({ path: path.join(output, `FAIL-${name}.png`), fullPage: true }).catch(() => {});
  }
  console.log(`${report.checks.at(-1).status} ${name}`);
  await persist();
}
async function render(caseOrId = 'CASE-0002', options = {}) {
  await page.evaluate(({ value, opts }) => window.pc3Harness.render(value, opts), { value: caseOrId, opts: options });
  await page.waitForFunction(id => window.pc3Harness.state().caseData.id === id, typeof caseOrId === 'string' ? caseOrId : caseOrId.id);
}
async function snapshot(name) {
  const file = `${name}.png`;
  await page.screenshot({ path: path.join(output, file), fullPage: true });
  return file;
}
async function openVideo() {
  await render('CASE-0002');
  await page.getByTestId('event-W-W3').click();
  await page.getByTestId('open-video').click();
  await page.getByRole('dialog').waitFor();
}
async function closeVideo() {
  if (await page.getByRole('dialog').count()) await page.getByRole('button', { name: '연결 영상 닫기', exact: true }).click();
}
try {
  await page.goto(harness.url, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => Boolean(window.pc3Harness));
  if (process.argv.includes('--probe')) {
    const probe = await page.evaluate(() => ({
      body: document.body.innerText,
      buttons: [...document.querySelectorAll('button')].map(button => ({ text: button.textContent, label: button.getAttribute('aria-label'), testid: button.dataset.testid, disabled: button.disabled })),
      inspected: window.pc3Harness.inspect(window.pc3Harness.state().caseData),
    }));
    await writeFile(path.join(output, 'probe.json'), JSON.stringify(probe, null, 2));
    await snapshot('probe');
    report.probe = probe;
    console.log(JSON.stringify(probe, null, 2));
  } else {
    await check('fixture-scope', async () => {
      assert.equal(fixture.synthetic, true);
      assert.deepEqual(fixture.cases.map(item => item.id), ['CASE-0001', 'CASE-0002']);
      return { ids: fixture.cases.map(item => item.id), synthetic: fixture.synthetic };
    });
    for (const caseId of ['CASE-0001', 'CASE-0002']) {
      for (const width of [390, 921, 1365]) {
        await check(`visible-${caseId}-${width}`, async () => {
          await page.setViewportSize({ width, height: 950 }); await render(caseId);
          const state = await page.evaluate(() => ({
            width: innerWidth, docWidth: document.documentElement.scrollWidth,
            bodyWidth: document.body.scrollWidth,
            text: document.body.innerText,
            buttons: [...document.querySelectorAll('button')].map(button => ({ text: button.textContent, rect: { width: button.getBoundingClientRect().width, height: button.getBoundingClientRect().height } })),
          }));
          assert.ok(state.docWidth <= width + 1 && state.bodyWidth <= width + 1, `Horizontal overflow ${JSON.stringify(state)}`);
          assert.ok(state.text.includes(caseId));
          assert.ok(state.buttons.length >= 4 && state.buttons.every(button => button.rect.width > 0 && button.rect.height > 0));
          return { width, docWidth: state.docWidth, bodyWidth: state.bodyWidth, screenshot: await snapshot(`${caseId}-${width}`) };
        });
      }
    }
    await check('registered-media-file', async () => {
      const bytes = await readFile(path.join(MEDIA, 'sorter-demo.mp4'));
      const actual = { bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') };
      const expected = manifest.assets.find(asset => asset.name === 'sorter-demo.mp4');
      assert.ok(expected, 'Published media manifest must identify sorter-demo.mp4');
      assert.equal(actual.bytes, expected.bytes);
      assert.equal(actual.sha256, expected.sha256);
      return { ...actual, expected, evidence: 'Local file bytes independently matched to tracked media manifest' };
    });
    await page.setViewportSize({ width: 1365, height: 950 });
    for (const caseId of ['CASE-0001', 'CASE-0002']) {
      await check(`event-selection-next-action-${caseId}`, async () => {
        await render(caseId);
        const data = fixture.cases.find(item => item.id === caseId);
        const actions = [];
        for (const event of data.wms.events) {
          await page.getByTestId(`event-${event.id}`).click();
          assert.equal(await page.getByTestId(`event-${event.id}`).getAttribute('aria-pressed'), 'true');
          assert.equal(await page.locator('button[data-testid^="event-"][aria-pressed="true"]').count(), 1);
          const action = await page.getByRole('heading', { name: '다음 확인 행동', exact: true }).locator('..').innerText();
          assert.ok(action.includes('확인') && action.length > 25);
          actions.push({ event: event.id, action });
        }
        assert.equal(new Set(actions.map(item => item.action)).size, 4);
        return actions;
      });
    }
    await check('unregistered-media-remains-unavailable', async () => {
      const checked = [];
      for (const data of fixture.cases) {
        await render(data.id);
        for (const event of data.wms.events.filter(event => event.id !== 'W-W3')) {
          await page.getByTestId(`event-${event.id}`).click();
          assert.equal(await page.getByTestId('open-video').count(), 0);
          assert.ok(await page.getByTestId('media-unavailable').isVisible());
          checked.push(event.id);
        }
      }
      return { eventIds: checked, observed: 'No unrelated clip reused' };
    });
    await check('missing-event-retains-canonical-stage-actions', async () => {
      const data = structuredClone(fixture.cases[1]);
      data.wms.events = data.wms.events.filter(event => event.id !== 'W-W2');
      await render(data);
      await page.getByTestId('event-W-W3').click();
      assert.ok((await page.getByTestId('event-W-W3').innerText()).includes('분기 / 슈트'));
      const sortingAction = await page.getByRole('heading', { name: '다음 확인 행동', exact: true }).locator('..').innerText();
      assert.ok(sortingAction.includes('계획·실적 슈트'));
      await page.getByTestId('event-W-W4').click();
      const shippingAction = await page.getByRole('heading', { name: '다음 확인 행동', exact: true }).locator('..').innerText();
      assert.ok(shippingAction.includes('출고 스캔과 피킹 기록'));
      return { omittedEvent: 'W-W2', sortingAction, shippingAction };
    });
    await check('registered-clip-positive-control', async () => {
      const data = fixture.cases.find(item => item.id === 'CASE-0002');
      const result = await page.evaluate(data => window.pc3Harness.validate(data, data.wms.events[2], data.media), data);
      const expected = manifest.assets.find(asset => asset.name === 'sorter-demo.mp4');
      assert.ok(result.clip); assert.equal(result.reason, '');
      assert.equal(result.clip.sha256, expected.sha256); assert.equal(result.clip.bytes, expected.bytes);
      return result;
    });
    for (const mutation of clipMutations) {
      await check(`reject-${mutation.name}`, async () => {
        const caseData = structuredClone(fixture.cases.find(item => item.id === 'CASE-0002'));
        const input = { caseData, event: caseData.wms.events[2], media: caseData.media };
        mutation.edit(input);
        const result = await page.evaluate(input => window.pc3Harness.validate(input.caseData, input.event, input.media), input);
        assert.ok(!result.clip, `Invalid mapping was playable: ${JSON.stringify(result)}`);
        assert.ok(result.reason?.length > 0);
        return { mutation: mutation.name, result };
      });
    }
    await check('time-reversal-preserved', async () => {
      const data = structuredClone(fixture.cases[1]);
      data.wms.sorting.sortedAt = '2026-09-18T02:00:00+09:00';
      await render(data);
      const inspection = await page.evaluate(() => window.pc3Harness.inspect(window.pc3Harness.state().caseData));
      assert.equal(inspection.timeReversal, true);
      assert.equal(inspection.sorting.sortedAt, data.wms.sorting.sortedAt);
      await page.getByTestId('event-W-W3').click();
      assert.equal(await page.getByTestId('open-video').count(), 0);
      const warnings = await page.getByRole('alert').allTextContents();
      assert.ok(warnings.some(warning => warning.includes('시각 역전')));
      return { originalSortedAt: data.wms.sorting.sortedAt, preservedSortedAt: inspection.sorting.sortedAt, warnings };
    });
    await check('quantity-unit-unknown-preservation', async () => {
      await render('CASE-0002');
      const observed = await page.getByRole('region', { name: '피킹과 출고 기록 비교' }).innerText();
      assert.ok(observed.includes('18 EA') && observed.includes('1 BOX'));
      assert.ok(observed.includes('환산하거나 차감하지 않습니다') && observed.includes('귀책 미확인'));
      const outputs = [];
      for (const quantity of [null, 0]) {
        const data = structuredClone(fixture.cases[1]); data.wms.picking.quantity = quantity;
        await render(data);
        const text = await page.getByRole('region', { name: '피킹과 출고 기록 비교' }).innerText();
        assert.ok(text.includes(quantity === null ? '수량 미확인' : '0 EA'));
        outputs.push({ quantity, text });
      }
      return { observed, variants: outputs };
    });
    await check('media-sha-playback-escape-focus', async () => {
      harness.state.mediaFault = null; await openVideo();
      const video = page.getByLabel('합성 공정 영상', { exact: true });
      await video.waitFor();
      await page.waitForFunction(() => document.querySelector('video')?.readyState >= 2);
      const before = await video.evaluate(async video => { await video.play(); return { duration: video.duration, currentTime: video.currentTime, src: video.currentSrc }; });
      await page.waitForFunction(() => document.querySelector('video')?.currentTime > 0.25);
      const after = await video.evaluate(video => ({ currentTime: video.currentTime, paused: video.paused, error: video.error?.code || null }));
      assert.ok(before.src.startsWith('blob:'));
      assert.ok(before.duration >= 11.9 && before.duration <= 12.1);
      assert.ok(after.currentTime > before.currentTime && !after.paused && after.error === null);
      const screenshot = await snapshot('verified-video-playing');
      await page.keyboard.press('Escape');
      assert.equal(await page.getByRole('dialog').count(), 0);
      assert.equal(await page.evaluate(() => document.activeElement?.getAttribute('data-testid')), 'open-video');
      assert.equal(await page.locator('video').count(), 0);
      return { before, after, screenshot, focusReturned: 'open-video', mediaRequests: harness.state.requests.filter(request => request.path.endsWith('sorter-demo.mp4')).length };
    });
    await check('media-404-retry', async () => {
      harness.state.mediaFault = '404';
      try {
        await openVideo();
        await page.getByRole('alert').waitFor();
        const error = await page.getByRole('alert').innerText();
        assert.ok(error.includes('404')); assert.equal(await page.locator('video').count(), 0);
        assert.ok((await page.getByRole('dialog').innerText()).includes('원본 스캔과 비교'));
        harness.state.mediaFault = null;
        await page.getByRole('button', { name: '영상 다시 불러오기', exact: true }).click();
        await page.getByLabel('합성 공정 영상', { exact: true }).waitFor();
        await page.waitForFunction(() => document.querySelector('video')?.readyState >= 2);
        return { injectedError: error, retryLoaded: true };
      } finally { harness.state.mediaFault = null; await closeVideo(); }
    });
    await check('corrupt-media-sha-rejected', async () => {
      harness.state.mediaFault = 'corrupt';
      try {
        await openVideo(); await page.getByRole('alert').waitFor();
        const error = await page.getByRole('alert').innerText();
        assert.ok(error.includes('SHA256')); assert.equal(await page.locator('video').count(), 0);
        return { error, changedByteCount: 1, originalByteLengthPreserved: true, screenshot: await snapshot('corrupt-video-blocked') };
      } finally { harness.state.mediaFault = null; await closeVideo(); }
    });
    await check('case-switch-disposes-open-video', async () => {
      await openVideo(); await page.getByLabel('합성 공정 영상', { exact: true }).waitFor();
      await render('CASE-0001');
      assert.equal(await page.getByRole('dialog').count(), 0); assert.equal(await page.locator('video').count(), 0);
      assert.equal(await page.getByTestId('event-W-M1').getAttribute('aria-pressed'), 'true');
      assert.ok((await page.getByRole('region', { name: 'WMS 공정 확인' }).innerText()).includes('CASE-0001'));
      return { currentCase: 'CASE-0001', dialogs: 0, videos: 0, selected: 'W-M1' };
    });
    await check('reduced-motion-stops-animation', async () => {
      await render('CASE-0002'); await page.emulateMedia({ reducedMotion: 'no-preference' });
      await page.getByTestId('motion-toggle').click();
      assert.equal(await page.getByTestId('process-diagram').getAttribute('data-playing'), 'true');
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await page.waitForFunction(() => document.querySelector('[data-testid="motion-toggle"]').disabled);
      assert.equal(await page.getByTestId('process-diagram').getAttribute('data-playing'), 'false');
      const running = await page.getByTestId('process-diagram').evaluate(element => element.getAnimations({ subtree: true }).filter(animation => animation.playState === 'running').map(animation => animation.animationName));
      assert.deepEqual(running, []);
      await page.emulateMedia({ reducedMotion: 'no-preference' });
      return { runningAnimationsWithReduce: running, toggleDisabledDuringReduce: true };
    });
    await check('rejected-link-never-reports-success', async () => {
      await render('CASE-0002', { rejectLink: true });
      await page.getByTestId('link-E-W2').click();
      await page.getByRole('alert').waitFor();
      assert.ok((await page.getByRole('alert').innerText()).includes('PC3_TEST_LINK_REJECTED'));
      assert.equal((await page.locator('[role="status"]').allTextContents()).join('').trim(), '');
      assert.ok(!(await page.getByTestId('link-E-W2').innerText()).includes('연결됨'));
      const state = await page.evaluate(() => window.pc3Harness.state());
      assert.equal(state.events.filter(event => event.type === 'link-attempt').length, 1);
      assert.equal(state.events.filter(event => event.type === 'link-resolved').length, 0);
      return { events: state.events, screenshot: await snapshot('link-failure-no-success') };
    });
    await check('pending-link-deduplicates-and-confirms-after-resolution', async () => {
      await render('CASE-0002', { holdLink: true });
      await page.getByTestId('link-E-W2').click();
      assert.ok(await page.getByTestId('link-E-W2').isDisabled());
      assert.equal((await page.locator('[role="status"]').allTextContents()).join('').trim(), '');
      await page.getByTestId('link-E-W2').evaluate(button => { button.click(); button.click(); });
      let state = await page.evaluate(() => window.pc3Harness.state());
      assert.equal(state.events.filter(event => event.type === 'link-attempt').length, 1);
      await page.evaluate(() => window.pc3Harness.releaseLinks());
      await page.waitForFunction(() => document.querySelector('[data-testid="link-E-W2"]').textContent === '연결됨');
      assert.ok((await page.getByRole('status').innerText()).includes('연결했습니다'));
      state = await page.evaluate(() => window.pc3Harness.state());
      assert.equal(state.events.filter(event => event.type === 'link-resolved').length, 1);
      return state.events;
    });
    await check('handed-off-evidence-readonly', async () => {
      const data = structuredClone(fixture.cases[1]); data.status = 'handed_off'; await render(data);
      const buttons = page.locator('button[data-testid^="link-"]');
      assert.equal(await buttons.count(), 4);
      for (const button of await buttons.all()) assert.ok(await button.isDisabled());
      assert.ok((await page.getByRole('region', { name: '상담 근거' }).innerText()).includes('읽기 전용'));
      return { state: data.status, disabledLinks: await buttons.count() };
    });
    await check('foreign-case-evidence-cannot-link', async () => {
      const data = structuredClone(fixture.cases[1]);
      data.evidence.push(structuredClone(fixture.cases[0].evidence.find(item => item.id === 'E-M3')));
      await render(data);
      const foreign = page.getByTestId('link-E-M3');
      assert.equal(await foreign.count(), 1, 'Foreign source should remain inspectable with linking blocked');
      assert.ok(await foreign.isDisabled(), 'CASE-0001 E-M3 must not be linked from CASE-0002');
      await foreign.evaluate(button => button.click());
      const state = await page.evaluate(() => window.pc3Harness.state());
      assert.equal(state.events.filter(event => event.type === 'link-attempt').length, 0);
      return { foreignId: 'E-M3', activeCase: 'CASE-0002', disabled: true, callbackCount: 0 };
    });
    await check('keyboard-selection-and-back-callback', async () => {
      await render('CASE-0002');
      await page.getByTestId('event-W-W3').focus(); await page.keyboard.press('Enter');
      assert.equal(await page.getByTestId('event-W-W3').getAttribute('aria-pressed'), 'true');
      await page.getByRole('button', { name: '상담으로 돌아가기', exact: true }).focus(); await page.keyboard.press('Enter');
      const state = await page.evaluate(() => window.pc3Harness.state());
      assert.equal(state.events.filter(event => event.type === 'back').length, 1);
      return { selected: 'W-W3', events: state.events };
    });
    await check('browser-no-runtime-errors-or-external-calls', async () => {
      assert.deepEqual(report.blockedExternal, []);
      assert.deepEqual(report.browserErrors.filter(error => error.type === 'pageerror'), []);
      const unexpected = report.browserErrors.filter(error => error.type === 'console' && !error.message.includes('404 (Not Found)'));
      assert.deepEqual(unexpected, []);
      return { blockedExternal: report.blockedExternal, pageErrors: 0, expected404ConsoleMessages: report.browserErrors.filter(error => error.message.includes('404 (Not Found)')).length };
    });
  }
} finally {
  report.sourceHashesEnd = await sourceHashes();
  report.changedSources = Object.keys(report.sourceHashesStart).filter(name => report.sourceHashesStart[name] !== report.sourceHashesEnd[name]);
  if (report.changedSources.length) report.checks.push({ name: 'source-stability', status: 'FAIL', error: `Sources changed during this run: ${report.changedSources.join(', ')}` });
  report.finishedAt = new Date().toISOString();
  report.summary = { pass: report.checks.filter(check => check.status === 'PASS').length, fail: report.checks.filter(check => check.status === 'FAIL').length };
  await persist();
  await context.close(); await browser.close(); await harness.close();
  console.log(`RESULTS ${path.join(output, 'results.json')}`);
}
if (report.checks.some(check => check.status === 'FAIL')) process.exitCode = 1;
