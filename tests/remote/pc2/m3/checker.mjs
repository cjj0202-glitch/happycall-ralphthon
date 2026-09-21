import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
const require = createRequire(path.join(ROOT, 'tests/e2e/package.json'));
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const PRODUCT = '92d2ecbad981f366a9e5ffc850d9c2bb7fd5d3a2';
const B_SHA = '6fe83afb8552765ab92722b838d2a0905f507551c4f98c58fa62a515033abaa0';
const B_TURNS = [[0, 4.3], [4.65, 12.2], [12.55, 17.2], [17.75, 23.3], [23.65, 29.8], [30.15, 36.55], [36.9, 44.25], [44.6, 49.4]];

/** The caller owns browser launch and the isolated, same-origin product/API server. */
export async function runChecks({ browser, base, productRoot, out }) {
  const origin = new URL(base).origin;
  assert.ok(['127.0.0.1', 'localhost', '[::1]'].includes(new URL(origin).hostname), 'Loopback product only');
  await mkdir(out, { recursive: true });
  const fixtureBytes = await readFile(path.join(productRoot, 'data/fixtures/cases.json'));
  const fixture = JSON.parse(fixtureBytes.toString('utf8'));
  const cases = fixture.cases.filter(c => ['CASE-0001', 'CASE-0002'].includes(c.id));
  assert.equal(cases.length, 2);
  const report = {
    version: 'pc2-m3-parent-replay-v2-scoped-editor-controls', started: new Date().toISOString(), productCommit: PRODUCT,
    fixtureSha256: sha256(fixtureBytes), browser: browser.version(), playwright: require('playwright/package.json').version,
    method: 'Actual exported parent page, actual isolated replay API, native Edge audio; only declared fault/source-input responses are injected.',
    limits: ['AI technical inspection, human listening 0.', 'Replay results are cached synthetic data, not live AI accuracy.', 'No production service, persistence deployment, or final acceptance claim.'],
    target: { normal: 4, sourceChange: 1, completionCounterexamples: 2, failureRecovery: 2, viewportKeyboard: 3, integrity: 2, total: 14 },
    checks: [], requests: [], blockedRequests: [], expectedFaults: [], responses: [], consoleErrors: [], pageErrors: [], screenshots: [], media: [], cleanup: [],
  };
  const save = async () => {
    report.summary = { executed: report.checks.length, passed: report.checks.filter(c => c.status === 'PASS').length, failed: report.checks.filter(c => c.status === 'FAIL').length };
    await writeFile(path.join(out, 'results.json'), JSON.stringify(report, null, 2) + '\n');
  };
  let context, page, phase = 'setup', audioFault = false, analysisFault = false, replacement = false;
  const check = async (id, expected, fn) => {
    phase = id;
    const started = Date.now();
    try { const actual = await fn(); report.checks.push({ id, expected, status: 'PASS', actual, ms: Date.now() - started }); console.log(`PASS ${id}`); }
    catch (e) {
      const entry = { id, expected, status: 'FAIL', error: e.stack || String(e), ms: Date.now() - started };
      try { entry.failureScreenshot = `failure-${id}.png`; await page.screenshot({ path: path.join(out, entry.failureScreenshot), fullPage: true }); entry.pageText = await page.locator('body').innerText(); } catch (captureError) { entry.captureError = String(captureError); }
      report.checks.push(entry); console.log(`FAIL ${id}: ${e.message}`);
    }
    await save();
  };
  try {
    context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce', serviceWorkers: 'block' });
    await context.route('**/*', async route => {
      const request = route.request(), url = new URL(request.url());
      let body; try { body = request.postDataJSON(); } catch { body = request.postData(); }
      const record = { phase, at: new Date().toISOString(), url: request.url(), method: request.method(), body };
      report.requests.push(record);
      const replayPost = request.method() === 'POST' && /^\/api\/cases\/CASE-000[12]\/analyze$/.test(url.pathname) && body?.mode === 'replay';
      if (url.origin !== origin || (!['GET', 'HEAD'].includes(request.method()) && !replayPost) || (url.pathname.endsWith('/analyze') && body?.mode !== 'replay')) {
        report.blockedRequests.push(record); await route.abort('blockedbyclient'); return;
      }
      if (url.pathname === '/favicon.ico') { await route.fulfill({ status: 204, body: '' }); return; }
      if (audioFault && url.pathname === '/demo/CASE-0002.wav') {
        report.expectedFaults.push({ ...record, status: 404, type: 'audio-404' });
        await route.fulfill({ status: 404, contentType: 'text/plain', body: 'pc2 M3 intentional missing synthetic audio' }); return;
      }
      if (analysisFault && replayPost) {
        report.expectedFaults.push({ ...record, status: 503, type: 'analysis-503' });
        await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'pc2 M3 의도한 분석 실패 · 원문과 편집 보존 확인' }) }); return;
      }
      if (replacement && url.pathname === '/api/cases' && request.method() === 'GET') {
        const response = await route.fetch({ maxRedirects: 0 });
        const data = await response.json();
        const item = data.cases.find(c => c.id === 'CASE-0002');
        const changed = new URL(item.audioUrl, origin); changed.searchParams.set('pc2-m3-source', 'replacement');
        record.inputInjection = { id: item.id, previousAudioUrl: item.audioUrl, replacementAudioUrl: changed.pathname + changed.search };
        item.audioUrl = changed.pathname + changed.search;
        await route.fulfill({ response, json: data }); return;
      }
      await route.continue();
    });
    await context.addInitScript(() => {
      window.__pc2M3Media = [];
      let sequence = 0; const ids = new WeakMap();
      for (const type of ['loadedmetadata', 'play', 'playing', 'pause', 'ended', 'seeking', 'seeked', 'error', 'ratechange']) {
        document.addEventListener(type, event => {
          const a = event.target; if (!(a instanceof HTMLAudioElement)) return;
          if (!ids.has(a)) ids.set(a, ++sequence);
          window.__pc2M3Media.push({ type, id: ids.get(a), at: performance.now(), trusted: event.isTrusted, src: a.currentSrc, time: a.currentTime, duration: a.duration, rate: a.playbackRate, error: a.error?.code || null,
            played: Array.from({ length: a.played.length }, (_, i) => [a.played.start(i), a.played.end(i)]) });
        }, true);
      }
    });
    page = await context.newPage(); page.setDefaultTimeout(8000);
    page.on('pageerror', error => report.pageErrors.push({ phase, error: error.stack || error.message }));
    page.on('console', message => {
      if (message.type() !== 'error') return;
      const text = message.text();
      const expectedFault = (phase === 'audio-404-recovery' && /404|ERR_|Failed to load resource/.test(text)) || (phase === 'analysis-failure-preserves-draft' && /503|Failed to load resource/.test(text));
      report.consoleErrors.push({ phase, text, expectedFault, location: message.location() });
    });
    page.on('dialog', dialog => dialog.accept());
    const analysisButton = () => page.getByRole('button', { name: /^저장된 분석 결과 재생/ });
    const fullButton = () => page.getByRole('button', { name: '처음부터 전체 통화 재생', exact: true });
    const summary = () => page.getByText('원문과 화자별 대화록 확인', { exact: true });
    const openSource = async () => { if (await summary().locator('..').getAttribute('open') === null) await summary().click(); };
    const sourceText = () => page.getByRole('region', { name: '2. 합성 통화 원대본', exact: true }).locator(':scope > div').last().textContent();
    const metadata = () => page.waitForFunction(() => { const a = document.querySelector('audio'); return a && Number.isFinite(a.duration) && a.duration > 0 && a.readyState >= 1; });
    const state = () => page.evaluate(() => {
      const a = document.querySelector('audio');
      return a ? { src: a.currentSrc, time: a.currentTime, duration: a.duration, paused: a.paused, ended: a.ended, rate: a.playbackRate, volume: a.volume, muted: a.muted, error: a.error?.code || null,
        played: Array.from({ length: a.played.length }, (_, i) => [a.played.start(i), a.played.end(i)]) } : null;
    });
    const select = async id => {
      const button = page.locator('.case-selector').getByRole('button').filter({ hasText: id });
      await button.click(); await page.getByRole('heading', { name: cases.find(c => c.id === id).title, exact: true }).waitFor();
    };
    const fresh = async id => {
      await page.goto(origin, { waitUntil: 'domcontentloaded' });
      await page.locator('#analysis-mode').waitFor(); assert.equal(await page.locator('#analysis-mode').inputValue(), 'replay');
      await select(id); await metadata(); await page.evaluate(() => { window.__pc2M3Media = []; });
    };
    // Read actual editable controls, excluding similarly named read-only comparison
    // sections. Textarea contents may also enter an implicit label's text matching.
    const editor = () => page.locator('#intake-editor');
    const editorFields = () => ({
      storeId: editor().locator('input[placeholder="점포코드 확인"]'),
      subject: editor().locator('input[placeholder="상품명 또는 문의 대상"]'),
      quantity: editor().locator('input[type="number"]'),
      unit: editor().locator('input[placeholder="개 / 박스 · 미확인"]'),
      request: editor().locator('textarea[placeholder="경영주가 요청한 내용을 확인해 주세요."]'),
    });
    const questionInput = () => editor().locator('textarea[placeholder="추천 질문을 선택하거나 직접 적어 주세요."]');
    const formValues = async () => {
      const values = {};
      for (const [name, control] of Object.entries(editorFields())) {
        assert.equal(await control.count(), 1, `One editable ${name} control in #intake-editor`);
        values[name] = await control.inputValue();
      }
      return values;
    };
    await check('baseline-audio-and-timeline', 'Actual CASE2 version URL and SHA match candidate B; turns4–8 shifted by 0.20 s; CASE1 remains approved audio', async () => {
      const observed = [];
      for (const c of cases) {
        const url = new URL(c.audioUrl, origin); assert.equal(url.origin, origin);
        const response = await context.request.get(url.href, { maxRedirects: 0 }); assert.equal(response.status(), 200);
        const bytes = await response.body(), digest = sha256(bytes);
        assert.equal(digest, c.transcriptTiming.audioSha256);
        observed.push({ id: c.id, url: c.audioUrl, bytes: bytes.length, sha256: digest, transcript: c.transcript });
      }
      const b = cases.find(c => c.id === 'CASE-0002');
      assert.equal(new URL(b.audioUrl, origin).searchParams.get('v'), B_SHA); assert.equal(b.transcriptTiming.audioSha256, B_SHA);
      assert.deepEqual(b.transcript.map(t => [t.start, t.end]), B_TURNS);
      return observed;
    });
    if (report.checks.at(-1).status !== 'PASS') throw new Error('Asset/baseline check failed: stop before product playback as required by the M3 card.');
    for (const c of cases) {
      await check(`${c.id}-natural-full-parent-gate`, 'Natural 1x playback from start to end; trusted ended1; real parent analysis disabled before and enabled after', async () => {
        await fresh(c.id); assert.ok(await analysisButton().isDisabled());
        const expected = c.id === 'CASE-0002' ? 49.75 : 47.15;
        const before = await state(); assert.ok(Math.abs(before.duration - expected) <= 1 / 24000); assert.equal(before.rate, 1); assert.equal(before.muted, false); assert.equal(before.volume, 1);
        const started = Date.now(); await fullButton().click();
        await page.waitForFunction(() => document.querySelector('audio')?.ended === true, undefined, { timeout: (expected + 12) * 1000 });
        await page.waitForFunction(() => [...document.querySelectorAll('button')].some(b => b.textContent.includes('저장된 분석 결과 재생') && !b.disabled));
        const elapsed = (Date.now() - started) / 1000, audio = await state(), events = await page.evaluate(() => window.__pc2M3Media);
        const ended = events.filter(e => e.type === 'ended');
        assert.equal(ended.length, 1); assert.equal(ended[0].trusted, true); assert.equal(audio.rate, 1); assert.equal(audio.error, null);
        assert.ok(elapsed >= expected - 0.3 && elapsed <= expected + 12, `wall ${elapsed}`);
        assert.equal(audio.played.length, 1); assert.ok(audio.played[0][0] <= 0.05 && audio.played[0][1] >= expected - 0.10);
        assert.ok(await analysisButton().isEnabled());
        const evidence = { id: c.id, expectedDuration: expected, elapsed, before, audio, events, parentAnalysisEnabled: true }; report.media.push(evidence); return evidence;
      });
      await check(`${c.id}-real-replay-analysis-and-form`, 'One real POST mode=replay; response fields/8 turns/questions render in parent; original preserved; quantity/unit retain source meaning', async () => {
        assert.ok(await analysisButton().isEnabled());
        const requestStart = report.requests.length;
        const responsePromise = page.waitForResponse(r => new URL(r.url()).pathname === `/api/cases/${c.id}/analyze` && r.request().method() === 'POST');
        await analysisButton().click(); const response = await responsePromise;
        assert.equal(response.status(), 200); assert.deepEqual(response.request().postDataJSON(), { mode: 'replay' });
        const data = await response.json(); report.responses.push({ caseId: c.id, phase, status: response.status(), data });
        assert.equal(data.mode, 'replay'); assert.equal(data.transcript.length, 8);
        await page.locator('.ai-summary').waitFor();
        await page.waitForFunction(expected => document.querySelector('#intake-editor input[placeholder="상품명 또는 문의 대상"]')?.value === expected, data.analysis.fields.subject || '');
        const values = await formValues();
        for (const key of ['storeId', 'subject', 'quantity', 'unit', 'request']) assert.equal(values[key], String(data.analysis.fields[key] ?? ''), key);
        if (c.id === 'CASE-0002') { assert.equal(values.quantity, '1'); assert.equal(values.unit, 'BOX'); }
        else { assert.equal(values.quantity, ''); assert.equal(values.unit, ''); }
        await openSource(); assert.equal(await sourceText(), c.sourceText);
        const transcript = page.getByRole('region', { name: '화자별 대화록', exact: true });
        for (const [index, turn] of data.transcript.entries()) {
          const row = transcript.locator('ol > li').nth(index);
          assert.ok((await row.innerText()).includes(turn.text)); assert.ok((await row.innerText()).includes(turn.speaker));
        }
        assert.deepEqual(data.transcript.map(t => ({ speaker: t.speaker, text: t.text, start: t.start, end: t.end })), c.transcript.map(t => ({ speaker: t.speaker, text: t.text, start: t.start, end: t.end })));
        const questions = await page.locator('#intake-editor .questions button.question').allTextContents();
        assert.equal(questions.length, data.analysis.questions.length);
        for (const [i, question] of data.analysis.questions.entries()) assert.ok(questions[i].includes(question));
        const calls = report.requests.slice(requestStart).filter(r => r.url.endsWith(`/api/cases/${c.id}/analyze`)); assert.equal(calls.length, 1);
        return { request: { method: 'POST', mode: 'replay' }, responseMode: data.mode, fields: values, transcriptRows: 8, sourcePreserved: true, questions: data.analysis.questions, requests: calls.length };
      });
    }
    await check('analysis-failure-preserves-draft', 'Intentional HTTP503 is visible; actual parent edited form/question and original remain byte-for-byte; retry available', async () => {
      await editorFields().request.fill('합성 점검 메모: 정정한 1BOX 확인 후 회송 절차 문의');
      await questionInput().fill('합성 점검 질문: 바깥 박스 라벨을 확인할 수 있나요?');
      const before = await formValues(), question = await questionInput().inputValue();
      await openSource(); const original = await sourceText();
      analysisFault = true;
      try {
        const responsePromise = page.waitForResponse(r => r.url().endsWith('/CASE-0002/analyze'));
        await analysisButton().click(); assert.equal((await responsePromise).status(), 503);
        await page.getByRole('alert').filter({ hasText: 'pc2 M3 의도한 분석 실패' }).waitFor();
        assert.deepEqual(await formValues(), before); assert.equal(await questionInput().inputValue(), question);
        assert.equal(await sourceText(), original); assert.ok(await page.getByRole('button', { name: 'AI 분석 다시 시도', exact: true }).isEnabled());
        return { before, after: await formValues(), question, originalSha256: sha256(original), retryEnabled: true, expectedStatus: 503 };
      } finally { analysisFault = false; }
    });
    await check('same-id-new-audio-parent-reset', 'Actual /api/cases input changes only CASE2 audioURL; real reload resets completion; detached old ended cannot unlock analysis', async () => {
      assert.ok(await analysisButton().isEnabled());
      await page.evaluate(() => { window.__pc2M3OldAudio = document.querySelector('audio'); });
      const before = await state(); replacement = true;
      try {
        await page.getByRole('button', { name: '목록 새로고침', exact: true }).click();
        await page.waitForFunction(() => document.querySelector('audio')?.currentSrc.includes('pc2-m3-source=replacement'));
        await metadata(); assert.ok(await analysisButton().isDisabled());
        const after = await state(); assert.equal(after.time, 0); assert.ok(after.src.includes('pc2-m3-source=replacement'));
        const detached = await page.evaluate(() => { const a = window.__pc2M3OldAudio; a.dispatchEvent(new Event('ended')); return { connected: a.isConnected, paused: a.paused }; });
        assert.equal(detached.connected, false); assert.equal(detached.paused, true); assert.ok(await analysisButton().isDisabled());
        return { before, after, detached, gateReset: true, onlyInputInjection: 'GET /api/cases CASE2 audioUrl query' };
      } finally { replacement = false; }
    });
    await check('end-seek-does-not-complete-parent', 'Native ended after seeking near end does not unlock actual parent analysis', async () => {
      await fresh('CASE-0002');
      await page.evaluate(() => { document.querySelector('audio').currentTime = document.querySelector('audio').duration - 0.08; });
      await page.waitForFunction(() => !document.querySelector('audio').seeking);
      await page.evaluate(() => document.querySelector('audio').play()); await page.waitForFunction(() => document.querySelector('audio').ended);
      assert.ok(await analysisButton().isDisabled()); const audio = await state(); assert.ok(audio.played[0][0] > 49); return { audio, parentDisabled: true, events: await page.evaluate(() => window.__pc2M3Media) };
    });
    await check('segment-does-not-complete-parent', 'Actual final segment 44.60–49.40 pauses at boundary; parent remains disabled', async () => {
      await fresh('CASE-0002'); await openSource();
      const button = page.getByRole('button', { name: /발화 8 구간 재생 / }); await button.click();
      await page.waitForFunction(() => { const a = document.querySelector('audio'); return a.paused && Math.abs(a.currentTime - 49.4) < 0.002; }, undefined, { timeout: 10000 });
      const audio = await state(); assert.ok(await analysisButton().isDisabled()); assert.ok(audio.played.at(-1)[1] <= 49.52);
      return { audio, parentDisabled: true, expected: [44.6, 49.4], events: await page.evaluate(() => window.__pc2M3Media) };
    });
    await check('audio-404-recovery', 'Missing audio produces real error, parent gate stays locked; UI reload after recovery obtains 49.75s metadata and can play', async () => {
      audioFault = true;
      try {
        await page.goto(origin, { waitUntil: 'domcontentloaded' }); await page.locator('#analysis-mode').waitFor(); await select('CASE-0002');
        await page.getByRole('button', { name: '음원 다시 불러오기', exact: true }).waitFor();
        assert.ok(await analysisButton().isDisabled());
        const fault = await state(); assert.ok(fault.error);
        audioFault = false; await page.getByRole('button', { name: '음원 다시 불러오기', exact: true }).click();
        await metadata(); const recovered = await state(); assert.equal(recovered.error, null); assert.ok(Math.abs(recovered.duration - 49.75) <= 1 / 24000);
        assert.equal(await page.getByRole('button', { name: '음원 다시 불러오기', exact: true }).count(), 0);
        await fullButton().click(); await page.waitForFunction(() => document.querySelector('audio').currentTime > 0.1);
        await page.evaluate(() => document.querySelector('audio').pause()); assert.ok(await analysisButton().isDisabled());
        return { fault, recovered, playable: await state(), parentStillDisabledBeforeFullEnd: true };
      } finally { audioFault = false; }
    });
    for (const width of [1440, 768, 390]) await check(`parent-layout-keyboard-${width}`, 'Actual page at target width: 0 horizontal overflow; playback controls, source disclosure, editor link and keyboard reachability', async () => {
      await fresh('CASE-0002'); await page.setViewportSize({ width, height: 1000 });
      await summary().focus(); await page.keyboard.press('Enter'); assert.notEqual(await summary().locator('..').getAttribute('open'), null);
      assert.equal(await page.getByRole('button', { name: /발화 \d+ 구간 재생 / }).count(), 8);
      const rate = page.getByLabel('통화 재생 속도', { exact: true }); await rate.focus(); await page.keyboard.press('ArrowDown');
      await page.waitForFunction(() => document.querySelector('audio').playbackRate === 1.25); await rate.selectOption('1');
      const mute = page.getByRole('button', { name: '통화 음소거', exact: true }); await mute.focus(); await page.keyboard.press('Space');
      assert.equal((await state()).muted, true); await page.keyboard.press('Space'); assert.equal((await state()).muted, false);
      const editorLink = page.getByRole('link', { name: '접수 편집으로 이동 ↓', exact: true });
      await editorLink.focus(); await page.keyboard.press('Enter'); assert.equal(new URL(page.url()).hash, '#intake-editor');
      await page.keyboard.press('Tab');
      const focused = await page.evaluate(() => ({ tag: document.activeElement.tagName, insideEditor: !!document.activeElement.closest('#intake-editor') }));
      assert.ok(focused.insideEditor, 'Keyboard reaches actual editor after anchor');
      const geometry = await page.evaluate(() => {
        const box = selector => { const r = document.querySelector(selector).getBoundingClientRect(); return { x: r.x, y: r.y + scrollY, width: r.width, height: r.height }; };
        return { viewport: innerWidth, overflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - innerWidth, audio: box('audio'), actions: box('.integrated-analysis-action'), editor: box('#intake-editor') };
      });
      assert.equal(geometry.overflow, 0);
      const file = `parent-layout-${width}.png`; await page.screenshot({ path: path.join(out, file), fullPage: true });
      report.screenshots.push({ file, width, sha256: sha256(await readFile(path.join(out, file))) });
      await summary().focus(); await page.keyboard.press('Space'); assert.equal(await summary().locator('..').getAttribute('open'), null);
      return { width, geometry, focused, keyboard: ['source Enter/Space', 'rate ArrowDown', 'mute Space', 'editor link Enter then Tab'], screenshot: file };
    });
    await check('parent-request-and-error-integrity', 'No external/live/non-replay calls; no uncaught page errors or unexpected console errors; real replay POST2 plus deliberate failure1', async () => {
      assert.equal(report.blockedRequests.length, 0); assert.equal(report.pageErrors.length, 0);
      const unexpected = report.consoleErrors.filter(e => !e.expectedFault); assert.deepEqual(unexpected, []);
      const posts = report.requests.filter(r => r.method === 'POST');
      assert.equal(posts.length, 3); for (const post of posts) assert.deepEqual(post.body, { mode: 'replay' });
      assert.equal(report.responses.filter(r => r.status === 200).length, 2);
      assert.equal(report.expectedFaults.filter(r => r.type === 'analysis-503').length, 1);
      assert.ok(report.expectedFaults.some(r => r.type === 'audio-404'));
      return { realReplaySuccess: 2, deliberateAnalysisFailure: 1, totalPOST: 3, pageErrors: 0, unexpectedConsoleErrors: 0, expectedConsoleErrors: report.consoleErrors.length, blockedRequests: 0 };
    });
  } catch (e) { report.fatal = e.stack || String(e); console.log(`FATAL M3 ${e.message}`); }
  finally {
    if (context) { try { await context.close(); report.cleanup.push({ context: 'closed' }); } catch (e) { report.cleanup.push({ context: 'error', error: String(e) }); } }
    report.finished = new Date().toISOString(); await save();
  }
  return report;
}
