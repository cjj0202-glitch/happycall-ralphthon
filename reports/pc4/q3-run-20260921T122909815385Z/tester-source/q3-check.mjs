// PC4 independently authored recovery axes, against one verified product export.
import { chromium } from '../../e2e/node_modules/playwright/index.mjs';
import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import path from 'node:path';
import { run as drafts } from './q3-drafts.mjs';
import { run as intake } from './q3-intake.mjs';
import { run as saves } from './q3-save.mjs';

const base = process.env.PC4_UI_BASE;
const out = process.env.PC4_UI_OUT;
const identity = JSON.parse(process.env.PC4_Q2_RUN_IDENTITY || 'null');
assert.ok(base && out && identity && process.env.PC4_API_BASE === base);
const origin = new URL(base).origin;
assert.equal(origin, base);
assert.equal(new URL(base).hostname, '127.0.0.1');
const expectedIds = Array.from({length: 8}, (_, i) => `Q3-${String(i + 1).padStart(2, '0')}`);
const report = {task: 'N04-Q3', startedAt: new Date().toISOString(), candidateSha: identity.finalSha,
  expectedIdentity: identity, base, axes: [], http: [], external: [], analysisRequests: [],
  pageErrors: [], console: [], setupErrors: [], limitations: [
    'Independent synthetic UI/HTTP recovery checks; not human review, paid AI or deployment.',
    'Fault injection can abort genuine saved responses or return a declared failure; no fabricated success.',
    'A fresh isolated case repository is created for each axis; original ledgers are never used.'
  ]};
const persist = () => writeFile(path.join(out, 'results.json'), JSON.stringify(report, null, 2), 'utf8');
async function request(method, target, body, headers = {}) {
  assert.ok(target.startsWith('/') && !target.startsWith('//'));
  const url = new URL(target, base);
  assert.equal(url.origin, origin);
  assert.ok(!url.pathname.endsWith('/analyze'), 'Analysis is outside Q3');
  const response = await fetch(url, {method, headers: {...(body === undefined ? {} : {'Content-Type': 'application/json'}), ...headers},
    ...(body === undefined ? {} : {body: JSON.stringify(body)}), redirect: 'manual'});
  assert.ok(response.status < 300 || response.status >= 400, 'Redirect response is not accepted');
  const text = await response.text();
  let value;
  try { value = JSON.parse(text); } catch { value = {text}; }
  report.http.push({transport: 'direct-real-http', method, path: url.pathname, status: response.status,
    revision: value?.revision, caseId: value?.id});
  return {status: response.status, body: value, headers: Object.fromEntries(response.headers)};
}
async function checkIdentity() {
  const response = await request('GET', '/__pc4/status');
  assert.equal(response.status, 200);
  for (const [key, value] of Object.entries(identity)) assert.equal(response.body[key], value);
  assert.equal(response.body.ready, true);
  return response.body;
}
let browser;
async function axis(id, fn) {
  assert.ok(expectedIds.includes(id) && !report.axes.some(a => a.id === id));
  const reset = await request('POST', '/__pc4/reset');
  assert.equal(reset.status, 200);
  const row = {id, startedAt: new Date().toISOString(), status: 'RUNNING', store: reset.body, checks: [], details: []};
  report.axes.push(row); await persist();
  const context = await browser.newContext({viewport: {width: 1365, height: 950}});
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin !== origin || !['http:', 'https:'].includes(url.protocol)) {
      report.external.push({axis: id, origin: url.origin, path: url.pathname}); return route.abort('blockedbyclient');
    }
    if (url.pathname.endsWith('/analyze')) {
      report.analysisRequests.push({axis: id, path: url.pathname}); return route.abort('blockedbyclient');
    }
    const response = await route.fetch({maxRedirects: 0});
    if (response.status() >= 300 && response.status() < 400) {
      report.external.push({axis: id, redirect: url.pathname}); return route.abort('blockedbyclient');
    }
    await route.fulfill({response});
  });
  context.on('page', page => {
    page.setDefaultTimeout(15000);
    page.on('pageerror', error => report.pageErrors.push({axis: id, message: error.message}));
    page.on('console', message => { if (message.type() === 'error') report.console.push({axis: id, message: message.text()}); });
    page.on('response', response => {
      const url = new URL(response.url());
      if (url.pathname.startsWith('/api/')) report.http.push({axis: id, transport: 'browser',
        method: response.request().method(), path: url.pathname, status: response.status()});
    });
  });
  const page = await context.newPage();
  const check = (name, actual, expected) => {
    row.checks.push({name, actual, expected, pass: false});
    assert.deepEqual(actual, expected, name); row.checks.at(-1).pass = true;
  };
  const record = detail => row.details.push(detail);
  const nav = label => page.getByRole('navigation', {name: '주 메뉴'}).getByRole('button', {name: label, exact: true}).click();
  const openCase = async id => {
    await page.goto(base, {waitUntil: 'domcontentloaded'});
    const button = page.getByRole('region', {name: '문의 선택'}).getByRole('button').filter({hasText: id});
    await button.waitFor(); await button.click();
    await page.getByPlaceholder('경영주가 요청한 내용을 확인해 주세요.', {exact: true}).waitFor();
  };
  const screenshot = label => page.screenshot({path: path.join(out, `${id}-${label.replace(/[^a-zA-Z0-9_-]/g, '_')}.png`), fullPage: true});
  try {
    row.result = await fn({page, context, base, check, request, nav, openCase, screenshot, record});
    assert.ok(row.checks.length, 'An axis must contain explicit observations');
    row.status = 'PASS';
  } catch (error) {
    row.status = 'FAIL'; row.failure = {message: error.message, stack: error.stack};
    await screenshot('failure').catch(() => {});
  } finally {
    await context.close(); row.finishedAt = new Date().toISOString(); await persist();
    console.log(JSON.stringify({axis: id, status: row.status, checks: row.checks.length, failure: row.failure?.message}));
  }
}
try {
  report.guardStart = await checkIdentity();
  browser = await chromium.launch({headless: true, executablePath: process.env.E2E_CHROMIUM});
  report.browserVersion = browser.version();
  for (const run of [intake, saves, drafts]) await run({axis});
} catch (error) {
  report.setupErrors.push({message: error.message, stack: error.stack});
} finally {
  if (browser) await browser.close();
  try { report.guard = await checkIdentity(); } catch (error) { report.setupErrors.push({message: error.message}); }
  for (const id of expectedIds) if (!report.axes.some(row => row.id === id)) report.axes.push({id, status: 'NOT_RUN', reason: 'Execution did not reach this axis'});
  report.summary = {planned: 8, passed: report.axes.filter(a => a.status === 'PASS').length,
    failed: report.axes.filter(a => a.status === 'FAIL').length, notRun: report.axes.filter(a => a.status === 'NOT_RUN').length};
  report.status = report.summary.passed === 8 && !report.setupErrors.length && !report.pageErrors.length && !report.external.length && !report.analysisRequests.length ? 'PASS' : 'FAIL';
  report.finishedAt = new Date().toISOString(); await persist();
  console.log(JSON.stringify({status: report.status, ...report.summary, setupErrors: report.setupErrors}));
  process.exitCode = report.status === 'PASS' ? 0 : 1;
}
