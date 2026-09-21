import { chromium } from 'playwright';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const out = path.resolve('../../reports/e2e');
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true, executablePath: process.env.E2E_CHROMIUM || 'C:/Users/choi8/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe' });
const context = await browser.newContext({ viewport: { width: 1365, height: 950 } });
const page = await context.newPage();
const errors = [];
page.on('console', m => { if (m.type() === 'error') errors.push({ kind: 'console', message: m.text() }); });
page.on('pageerror', e => errors.push({ kind: 'pageerror', message: e.message }));
page.on('requestfailed', r => errors.push({ kind: 'network', url: r.url(), message: r.failure()?.errorText }));
try {
  await page.goto('http://127.0.0.1:3100', { waitUntil: 'networkidle', timeout: 60000 });
  await page.screenshot({ path: path.join(out, 'initial.png'), fullPage: true });
  const snapshot = { at: new Date().toISOString(), url: page.url(), title: await page.title(), body: await page.locator('body').innerText(), errors };
  await writeFile(path.join(out, 'initial.json'), JSON.stringify(snapshot, null, 2));
  console.log(JSON.stringify(snapshot, null, 2));
} finally { await browser.close(); }
