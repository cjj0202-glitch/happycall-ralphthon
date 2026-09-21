import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

// Actual local API + browser integration only. No response/fixture interception,
// analysis, replay, or mutation of any case that this invocation did not create.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const stamp = new Date().toISOString().replace(/[:.]/g, '-');
const OUT = path.join(ROOT, 'tests/e2e/test-results', `evidence-cards-${stamp}`);
const WEB = 'http://127.0.0.1:3100';
const API = 'http://127.0.0.1:8100';
const executablePath = process.env.E2E_CHROMIUM || 'C:/Users/choi8/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe';
const created = new Set();
const protectedIds = ['CASE-0001', 'CASE-0002'];
const report = {
  suite: 'evidence-cards-bolt', started: new Date().toISOString(), host: 'pc1/CJJ',
  executor: 'AI Playwright local technical verification; not human Silent Test or remote-PC verification',
  base: WEB, api: API, executablePath, checks: [], requests: [], blocked: [], errors: [], createdCases: [],
  limitations: ['Uses independent SYN fixtures, not operational WMS/TMS data.', 'Does not measure human judgment speed or satisfaction.', 'Does not run AI analysis, replay, handoff, or paid API calls.', 'Synthetic INT records created by this run are retained as auditable test evidence.'],
};
await mkdir(OUT, { recursive: true });
const fixture = JSON.parse(await readFile(path.join(ROOT, 'data/fixtures/cases.json'), 'utf8'));
assert.equal(fixture.synthetic, true, 'This suite only uses explicitly synthetic fixtures');
async function hashes() {
  return Object.fromEntries(await Promise.all(['apps/web/app/page.tsx', 'apps/web/app/globals.css', 'apps/web/components/LogisticsView.tsx', 'data/fixtures/cases.json', 'server/service.py', 'tests/e2e/evidence-cards-bolt.mjs'].map(async file => [file, createHash('sha256').update(await readFile(path.join(ROOT, file))).digest('hex')])));
}
report.sourceHashesStart = await hashes();
const browser = await chromium.launch({ headless: true, executablePath });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
const page = await context.newPage();
page.setDefaultTimeout(15000);
const normalize = value => String(value).replace(/\s+/g, ' ').trim();
const section = () => page.getByRole('region', { name: '연결한 물류 근거', exact: true });
const requestInput = () => page.getByPlaceholder('경영주가 요청한 내용을 확인해 주세요.');
const nav = label => page.getByRole('navigation').getByRole('button', { name: label, exact: true }).click();
const card = id => section().locator(`article[data-evidence-id="${id}"]`);
const casePath = id => `/api/cases/${encodeURIComponent(id)}`;
const caseIdAt = pathname => /^\/api\/cases\/([^/]+)$/.exec(pathname)?.[1];
const selectedState = c => ({ revision: c.revision, selectedEvidence: c.selectedEvidence, reviewConfirmed: c.reviewConfirmed, sourceText: c.sourceText, intake: c.intake });
let protectedBefore;

// Browser and direct-request guards are separate because context.request does
// not pass through browser routing. Abort forbidden requests; never fake data.
await context.route('**/api/**', async route => {
  const req = route.request();
  const uri = new URL(req.url());
  const method = req.method();
  const id = caseIdAt(uri.pathname);
  const forbidden = /\/analyze(?:\/|$)/.test(uri.pathname)
    || (!['GET', 'HEAD', 'OPTIONS'].includes(method) && !(method === 'PATCH' && id && created.has(id)));
  if (forbidden) {
    report.blocked.push({ via: 'browser', method, url: req.url() });
    await route.abort('blockedbyclient');
  } else await route.continue();
});
page.on('request', req => {
  if (req.url().includes('/api/')) report.requests.push({ via: 'browser', method: req.method(), url: req.url(), body: req.postDataJSON() });
});
page.on('pageerror', error => report.errors.push({ kind: 'pageerror', message: error.message }));
page.on('console', message => {
  // HTTP 409 is deliberately exercised below and is not a renderer exception.
  if (message.type() === 'error') report.errors.push({ kind: 'console', message: message.text() });
});
page.on('requestfailed', req => report.errors.push({ kind: 'requestfailed', url: req.url(), message: req.failure()?.errorText }));

async function api(uri, method = 'GET', data, role = 'counselor') {
  const id = caseIdAt(uri);
  assert.ok(!uri.includes('/analyze'), 'Direct analyze/replay is forbidden');
  assert.ok(method === 'GET' || (method === 'POST' && uri === '/api/intake') || (method === 'PATCH' && id && created.has(id)), `Refused ${method} ${uri}: only this run's created INT IDs may be changed`);
  const response = await context.request.fetch(API + uri, { method, data, timeout: 15000, headers: { 'X-Demo-Role': role } });
  const body = await response.json();
  report.requests.push({ via: 'direct', method, url: API + uri, body: data, status: response.status() });
  return { status: response.status(), body };
}
async function readCase(id) {
  const result = await api(casePath(id));
  assert.equal(result.status, 200, JSON.stringify(result.body));
  assert.equal(result.body.id, id);
  return result.body;
}
async function newIntake(referenceId, label) {
  const source = fixture.cases.find(c => c.id === (referenceId || 'CASE-0001'));
  assert.ok(source);
  const text = `EVIDENCE-CARDS-${stamp} ${label}: 합성 접수이며 원문을 보존합니다. 실제 물류 조치는 요청하지 않습니다.`;
  const result = await api('/api/intake', 'POST', {
    storeId: source.intake?.storeId || source.store.id,
    subject: source.intake?.subject || source.title,
    type: source.type, text, ...(referenceId ? { referenceCaseId: referenceId } : {}),
  }, 'owner');
  assert.equal(result.status, 201, JSON.stringify(result.body));
  assert.match(result.body.id, /^INT-[A-Z0-9]+$/);
  assert.ok(!created.has(result.body.id));
  created.add(result.body.id);
  report.createdCases.push({ id: result.body.id, referenceCaseId: referenceId || null, sourceText: text });
  assert.equal(result.body.sourceText, text);
  assert.equal(result.body.linkedFixtureId, referenceId || null);
  assert.deepEqual(result.body.selectedEvidence, []);
  return result.body;
}
async function select(id) {
  await nav('상담 작업대');
  await page.getByRole('region', { name: '문의 선택' }).getByRole('button').filter({ hasText: id }).click();
  await section().waitFor();
  assert.equal(await section().getAttribute('data-case-id'), id);
}
async function linkEvidence(id, evidenceId) {
  assert.ok(created.has(id));
  const before = await readCase(id);
  const row = before.evidence.find(e => e.id === evidenceId);
  assert.ok(row, `Evidence ${evidenceId} must belong to ${id}`);
  await nav(row.system === 'WMS' ? 'WMS 작업 확인' : 'TMS 배송 확인');
  const article = page.getByRole('article').filter({ has: page.getByText(row.label, { exact: true }) });
  assert.equal(await article.count(), 1, `Expected exactly one source article for ${evidenceId}`);
  const responsePromise = page.waitForResponse(r => new URL(r.url()).pathname === casePath(id) && r.request().method() === 'PATCH');
  responsePromise.catch(() => {});
  await article.getByRole('button', { name: '이 근거 연결', exact: true }).click();
  const response = await responsePromise;
  const saved = await response.json();
  assert.equal(response.status(), 200, JSON.stringify(saved));
  assert.equal(response.request().postDataJSON().expectedRevision, before.revision);
  assert.equal(saved.revision, before.revision + 1);
  assert.deepEqual(saved.selectedEvidence, [...before.selectedEvidence, evidenceId]);
  await article.getByRole('button', { name: '연결됨', exact: true }).waitFor();
  return { id, evidenceId, previousRevision: before.revision, revision: saved.revision };
}
async function verifyCards(id) {
  const current = await readCase(id);
  assert.equal(await section().getAttribute('data-case-id'), id);
  const renderedIds = await section().locator('article[data-evidence-id]').evaluateAll(nodes => nodes.map(n => n.dataset.evidenceId));
  const expectedIds = [...new Set(current.selectedEvidence || [])];
  assert.deepEqual([...renderedIds].sort(), [...expectedIds].sort());
  const measurements = [];
  for (const evidenceId of expectedIds) {
    const row = current.evidence.find(e => e.id === evidenceId);
    assert.ok(row);
    const item = card(evidenceId);
    assert.equal(await item.getAttribute('data-evidence-state'), 'ready');
    assert.equal(normalize(await item.locator('h4').innerText()), normalize(row.label));
    assert.equal(normalize(await item.locator('.desk-evidence-value').innerText()), normalize(row.value));
    const meta = await item.locator(':scope > .desk-evidence-meta').innerText();
    assert.ok(meta.includes(row.source), `Original source missing from ${evidenceId}: ${meta}`);
    const text = await item.innerText();
    assert.ok(text.includes(row.system));
    assert.match(text, /합성/, 'Synthetic source must not be presented as operational evidence');
    assert.match(text, row.status === 'fact' ? /기록 확인/ : /미확인/);
    if (row.time == null) assert.match(meta, /시각 미등록|미등록/, 'Null record time must remain unregistered');
    else {
      const kst = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Seoul', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(row.time));
      assert.ok(meta.includes(kst), `Observed timestamp missing: ${row.time} / ${meta}`);
      assert.ok(meta.includes('2026'), `Full record date must be visible: ${meta}`);
    }
    measurements.push({ id: evidenceId, label: row.label, value: await item.locator('.desk-evidence-value').innerText(), meta, status: row.status, time: row.time });
  }
  return { id, selectedEvidence: expectedIds, cards: measurements, revision: current.revision };
}
async function check(name, task) {
  const start = Date.now();
  try {
    const evidence = await task();
    report.checks.push({ name, status: 'PASS', durationMs: Date.now() - start, evidence });
    console.log(`PASS ${name}`);
  } catch (error) {
    report.checks.push({ name, status: 'FAIL_RECHECK', durationMs: Date.now() - start, message: error.message, stack: error.stack });
    await page.screenshot({ path: path.join(OUT, `failure-${report.checks.length}.png`), fullPage: true }).catch(() => {});
    console.error(`FAIL_RECHECK ${name}: ${error.message}`);
    throw error;
  } finally {
    await writeFile(path.join(OUT, 'results.json'), JSON.stringify(report, null, 2));
  }
}

let missing, wrong, unlinked;
try {
  await check('runtime-and-protected-case-baseline', async () => {
    const health = await api('/api/health');
    assert.equal(health.status, 200);
    protectedBefore = Object.fromEntries(await Promise.all(protectedIds.map(async id => [id, selectedState(await readCase(id))])));
    // Positive and negative checks of the mutation guard do not send a request.
    await assert.rejects(api(casePath('CASE-0001'), 'PATCH', { expectedRevision: 0 }), /Refused/);
    await assert.rejects(api('/api/cases/CASE-0002/analyze', 'POST', { mode: 'replay' }), /forbidden/);
    return { health: health.body, protected: protectedBefore, deniedBeforeNetwork: ['CASE-0001 PATCH', 'CASE-0002 analyze replay'] };
  });
  await check('create-linked-and-unlinked-synthetic-intakes', async () => {
    missing = await newIntake('CASE-0001', '미도착 명시 연결');
    wrong = await newIntake('CASE-0002', '오출고 명시 연결');
    unlinked = await newIntake(null, '같은 점포·제목의 다른 문의, 근거 연결 없음');
    assert.equal(unlinked.evidence.length, 0);
    assert.ok(!unlinked.wms && !unlinked.tms);
    await page.goto(WEB, { waitUntil: 'networkidle', timeout: 60000 });
    await page.getByRole('heading', { name: '상담 작업대', exact: true }).waitFor();
    assert.equal(await page.getByLabel('분석 방식').inputValue(), 'replay');
    return report.createdCases;
  });
  await check('empty-selection-and-actual-wms-tms-linking', async () => {
    await select(missing.id);
    assert.equal(await section().locator('article[data-evidence-id]').count(), 0);
    assert.match(await section().innerText(), /연결/);
    const links = [];
    for (const id of ['E-M3', 'E-M2', 'E-M1']) links.push(await linkEvidence(missing.id, id));
    await select(missing.id);
    const cards = await verifyCards(missing.id);
    assert.equal(cards.cards.find(c => c.id === 'E-M2').time, null);
    assert.equal(cards.cards.find(c => c.id === 'E-M2').status, 'unknown');
    await section().screenshot({ path: path.join(OUT, 'missing-linked-cards.png') });
    return { links, ...cards };
  });
  await check('wrong-case-cards-and-case-switch-isolation', async () => {
    await select(wrong.id);
    assert.equal(await section().locator('article[data-evidence-id]').count(), 0);
    const links = [];
    for (const id of ['E-W1', 'E-W3', 'E-W4']) links.push(await linkEvidence(wrong.id, id));
    await select(wrong.id);
    const wrongCards = await verifyCards(wrong.id);
    assert.ok(!(await section().innerText()).includes('SYN-OUT01'));
    await section().screenshot({ path: path.join(OUT, 'wrong-linked-cards.png') });
    await select(unlinked.id);
    const unlinkedCards = await verifyCards(unlinked.id);
    assert.equal(unlinkedCards.cards.length, 0);
    assert.ok(!(await section().innerText()).includes('SYN-OUT01'));
    assert.equal(await section().locator('article[data-evidence-id]').count(), 0);
    await select(missing.id);
    const restored = await verifyCards(missing.id);
    assert.ok(!(await section().innerText()).includes('E-W1'));
    return { links, wrongCards, unlinkedCards, restored };
  });
  await check('keyboard-reading-preserves-input-selection-confirmation-and-revision', async () => {
    const before = await readCase(missing.id);
    const pendingText = `미저장-${stamp}: 근거를 읽은 뒤에도 남아 있어야 하는 상담원 요청사항`;
    await requestInput().fill(pendingText);
    const checkbox = page.getByRole('checkbox');
    await checkbox.check();
    const writesBefore = report.requests.filter(r => r.via === 'browser' && r.method === 'PATCH').length;
    const detail = card('E-M3').locator('details');
    const summary = detail.locator('summary');
    assert.equal(normalize(await summary.innerText()), '원본 기록과 연결 정보');
    await summary.focus();
    await page.keyboard.press('Shift+Tab');
    await page.keyboard.press('Tab');
    assert.equal(await summary.evaluate(el => document.activeElement === el), true);
    const focus = await summary.evaluate(el => {
      const style = getComputedStyle(el); const box = el.getBoundingClientRect();
      return { visible: el.matches(':focus-visible'), outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth, outlineColor: style.outlineColor, boxShadow: style.boxShadow, top: box.top, bottom: box.bottom, viewport: innerHeight };
    });
    assert.equal(focus.visible, true);
    assert.ok((focus.outlineStyle !== 'none' && parseFloat(focus.outlineWidth) > 0) || focus.boxShadow !== 'none', JSON.stringify(focus));
    await page.keyboard.press('Enter');
    await page.waitForFunction(() => document.querySelector('article[data-evidence-id="E-M3"] details')?.open === true);
    const raw = await detail.innerText();
    const record = before.evidence.find(e => e.id === 'E-M3');
    assert.ok(raw.includes(record.id));
    assert.ok(raw.includes(record.time));
    assert.ok(raw.includes(record.source));
    await section().screenshot({ path: path.join(OUT, 'keyboard-details-open.png') });
    await page.keyboard.press('Space');
    await page.waitForFunction(() => document.querySelector('article[data-evidence-id="E-M3"] details')?.open === false);
    assert.equal(await requestInput().inputValue(), pendingText);
    assert.equal(await checkbox.isChecked(), true);
    assert.deepEqual(await readCase(missing.id), before);
    assert.equal(report.requests.filter(r => r.via === 'browser' && r.method === 'PATCH').length, writesBefore);
    return { id: missing.id, focus, pendingText, checkboxPreserved: true, before: selectedState(before), after: selectedState(await readCase(missing.id)), writesFromReading: 0 };
  });
  await check('responsive-1440-1024-390-card-readability', async () => {
    const measurements = [];
    for (const width of [1440, 1024, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      await section().scrollIntoViewIfNeeded();
      const result = await section().evaluate(el => ({
        viewport: innerWidth, documentWidth: document.documentElement.scrollWidth,
        sectionWidth: el.getBoundingClientRect().width,
        cards: [...el.querySelectorAll('article[data-evidence-id]')].map(item => {
          const box = item.getBoundingClientRect();
          const value = item.querySelector('.desk-evidence-value');
          const meta = item.querySelector('.desk-evidence-meta');
          return { id: item.dataset.evidenceId, left: box.left, right: box.right, width: box.width, clientWidth: item.clientWidth, scrollWidth: item.scrollWidth, valueFontSize: parseFloat(getComputedStyle(value).fontSize), metaFontSize: parseFloat(getComputedStyle(meta).fontSize), value: value.textContent, meta: meta.textContent };
        }),
      }));
      assert.ok(result.cards.length > 0, 'Readability test must reach rendered cards');
      assert.ok(result.documentWidth <= width + 1, JSON.stringify(result));
      for (const item of result.cards) {
        assert.ok(item.left >= -1 && item.right <= width + 1, JSON.stringify(item));
        assert.ok(item.scrollWidth <= item.clientWidth + 1, JSON.stringify(item));
        assert.ok(item.width >= 240, `Card too narrow: ${JSON.stringify(item)}`);
        assert.ok(item.valueFontSize >= 13 && item.metaFontSize >= 12, JSON.stringify(item));
      }
      await section().screenshot({ path: path.join(OUT, `${width}-evidence-cards.png`) });
      await page.screenshot({ path: path.join(OUT, `${width}-desk.png`), fullPage: true });
      measurements.push({ width, ...result });
    }
    return measurements;
  });
  await check('stale-form-409-retains-typed-text-and-selected-evidence', async () => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    // Mount from a known snapshot, then increment only this run's new INT externally.
    await page.reload({ waitUntil: 'networkidle' });
    await select(missing.id);
    const reviewed = await readCase(missing.id);
    const pendingText = `충돌 후 보존-${stamp}: 아직 저장되지 않은 상담원 수정`;
    await requestInput().fill(pendingText);
    const originalSelected = [...reviewed.selectedEvidence];
    const winner = await api(casePath(missing.id), 'PATCH', { expectedRevision: reviewed.revision, intake: { request: `다른 화면에서 먼저 저장-${stamp}` } });
    assert.equal(winner.status, 200, JSON.stringify(winner.body));
    assert.equal(winner.body.revision, reviewed.revision + 1);
    const writesBefore = report.requests.filter(r => r.via === 'browser' && r.method === 'PATCH').length;
    const responsePromise = page.waitForResponse(r => new URL(r.url()).pathname === casePath(missing.id) && r.request().method() === 'PATCH');
    responsePromise.catch(() => {});
    await page.getByRole('button', { name: '접수 내용 저장', exact: true }).click();
    const response = await responsePromise;
    const rejected = await response.json();
    const sent = response.request().postDataJSON();
    assert.equal(response.status(), 409, JSON.stringify(rejected));
    assert.equal(rejected.error?.code, 'STATE_CONFLICT');
    assert.equal(sent.expectedRevision, reviewed.revision, 'Stale form must keep the revision reviewed by its editor');
    assert.equal(sent.intake.request, pendingText);
    await page.getByRole('alert').filter({ hasText: '다른 작업자가' }).waitFor();
    assert.equal(await requestInput().inputValue(), pendingText);
    await verifyCards(missing.id);
    assert.deepEqual((await readCase(missing.id)).selectedEvidence, originalSelected);
    assert.deepEqual(await readCase(missing.id), winner.body);
    // Wait for the actual UI save control to leave its busy state, not a blind delay.
    await page.getByRole('button', { name: '접수 내용 저장', exact: true }).waitFor();
    assert.equal(report.requests.filter(r => r.via === 'browser' && r.method === 'PATCH').length - writesBefore, 1, 'Rejected edit must not be silently retried');
    await page.screenshot({ path: path.join(OUT, 'stale-409-retained-input.png'), fullPage: true });
    return { id: missing.id, reviewedRevision: reviewed.revision, serverRevision: winner.body.revision, sentRevision: sent.expectedRevision, status: response.status(), pendingText, selectedEvidence: originalSelected, browserPatchAttempts: 1 };
  });
} catch (error) {
  report.abortedAfterFailure = error.message;
} finally {
  if (protectedBefore) {
    try {
      await check('protected-original-cases-unchanged-and-no-analysis', async () => {
        const after = Object.fromEntries(await Promise.all(protectedIds.map(async id => [id, selectedState(await readCase(id))])));
        assert.deepEqual(after, protectedBefore, 'Original case changed during the run; inspect concurrent editors before attributing the change');
        const forbiddenSent = report.requests.filter(r => r.method !== 'GET' && r.method !== 'OPTIONS' && (r.url.includes('/analyze') || (caseIdAt(new URL(r.url).pathname) && !created.has(caseIdAt(new URL(r.url).pathname)))));
        assert.deepEqual(forbiddenSent, []);
        assert.deepEqual(report.blocked, []);
        assert.equal(report.errors.filter(e => e.kind === 'pageerror').length, 0, JSON.stringify(report.errors));
        return { before: protectedBefore, after, forbiddenSent, blocked: report.blocked, observedPageErrors: 0 };
      });
    } catch { /* check() preserves the failure evidence */ }
  }
  report.finished = new Date().toISOString();
  report.sourceHashesEnd = await hashes();
  report.summary = { PASS: report.checks.filter(c => c.status === 'PASS').length, FAIL_RECHECK: report.checks.filter(c => c.status === 'FAIL_RECHECK').length };
  report.analyzeRequests = report.requests.filter(r => r.url.includes('/analyze')).length;
  await writeFile(path.join(OUT, 'results.json'), JSON.stringify(report, null, 2));
  await browser.close();
  console.log(JSON.stringify({ output: OUT, summary: report.summary, createdCaseIds: [...created], analyzeRequests: report.analyzeRequests }));
  process.exitCode = report.summary.FAIL_RECHECK || report.abortedAfterFailure ? 1 : 0;
}
