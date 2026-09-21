import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium } from '../../tests/remote/pc3/node_modules/playwright/index.mjs';
import { browserExecutable } from '../../tests/remote/pc3/harness-server.mjs';
const file = path.resolve(process.argv[2]);
const out = path.resolve('.local/pc3-m3-browser');
await mkdir(out, { recursive: true });
const raw = await readFile(file);
const evidence = { kind: 'N03-M3 local review page on artificial checker fixture', actualBlenderAssets: false, humanReview: false, sourceHtmlSha256: createHash('sha256').update(raw).digest('hex'), checks: [], errors: [], externalRequests: [] };
const browser = await chromium.launch({ headless: true, executablePath: browserExecutable(chromium) });
evidence.browser = browser.version();
const context = await browser.newContext();
await context.route('**/*', async route => {
  const scheme = new URL(route.request().url()).protocol;
  if (['file:', 'data:', 'about:'].includes(scheme)) return route.continue();
  evidence.externalRequests.push(route.request().url());
  return route.abort();
});
const page = await context.newPage();
page.on('pageerror', error => evidence.errors.push(error.message));
async function check(name, fn) { await fn(); evidence.checks.push({ name, result: 'PASS' }); }
try {
  for (const width of [390, 768, 1365]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto(pathToFileURL(file).href);
    await check(`layout-${width}`, async () => assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)));
    await check(`pending-synthetic-${width}`, async () => { const text = await page.locator('body').innerText(); assert.match(text, /visualAccepted=false/); assert.match(text, /SYNTHETIC/); assert.match(text, /PENDING/); assert.match(text, /CASE-0002/); });
    await check(`three-artificial-png-decodes-${width}`, async () => { const items = await page.locator('img').evaluateAll(images => images.map(img => ({ complete: img.complete, w: img.naturalWidth, h: img.naturalHeight, alt: img.alt, source: img.src.startsWith('data:image/png;base64,') }))); assert.equal(items.length,3); assert.ok(items.every(item => item.complete && item.w === 1280 && item.h === 720 && item.alt && item.source)); });
    await check(`keyboard-native-expansion-${width}`, async () => { const detail = page.locator('details').filter({ has: page.locator('img') }).first(); const summary = detail.locator('summary').first(); await summary.focus(); await page.keyboard.press('Enter'); assert.equal(await detail.getAttribute('open'), ''); await page.keyboard.press('Enter'); assert.equal(await detail.getAttribute('open'), null); });
    if (width !== 768) await page.screenshot({ path: path.join(out,`review-${width}.png`), fullPage: true });
  }
  await check('no-page-errors-or-external-requests', async () => { assert.deepEqual(evidence.errors, []); assert.deepEqual(evidence.externalRequests, []); });
  await check('no-input-html-mutation', async () => assert.deepEqual(await readFile(file),raw));
} catch(error) { evidence.failure = String(error); process.exitCode=1; }
finally { await browser.close(); await writeFile(path.join(out,'browser-checks.json'), JSON.stringify(evidence,null,2)); console.log(JSON.stringify(evidence)); }
