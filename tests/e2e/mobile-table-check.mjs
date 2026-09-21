import { chromium } from 'playwright';
import { writeFile, readFile, copyFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const out = path.join(root, 'reports/e2e');
for (const ext of ['json', 'png']) {
  const before = path.join(out, `mobile-tms-table-before.${ext}`);
  try { await readFile(before); } catch { await copyFile(path.join(out, `mobile-tms-table.${ext}`), before); }
}
const browser = await chromium.launch({ headless: true, executablePath: process.env.E2E_CHROMIUM || 'C:/Users/choi8/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe' });
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 950 } });
  const errors = [];
  let analyzeRequests = 0;
  page.on('pageerror', e => errors.push(e.message));
  await page.route('**/analyze', async route => { analyzeRequests += 1; await route.abort('blockedbyclient'); });
  await page.goto('http://127.0.0.1:3100', { waitUntil: 'networkidle' });
  await page.getByRole('navigation').getByRole('button', { name: 'TMS 배송 확인', exact: true }).click();
  const table = page.getByRole('table');
  const measured = await table.locator('tbody tr td:nth-child(2) button').evaluateAll(nodes => nodes.map(node => {
    const r = node.getBoundingClientRect(); const s = getComputedStyle(node);
    const range = document.createRange(); range.selectNodeContents(node);
    const textLineTops = [...new Set([...range.getClientRects()].map(rect => rect.top))];
    return { text: node.textContent, width: r.width, height: r.height, fontSize: s.fontSize, lineHeight: s.lineHeight, whiteSpace: s.whiteSpace, textLineCount: textLineTops.length };
  }));
  const wrapper = table.locator('..');
  const dimensions = await wrapper.evaluate(el => ({ clientWidth: el.clientWidth, scrollWidth: el.scrollWidth, overflowX: getComputedStyle(el).overflowX, scrollLeft: el.scrollLeft }));
  await wrapper.screenshot({ path: path.join(out, 'mobile-tms-table.png') });
  const scroll = await wrapper.evaluate(el => { el.scrollLeft = el.scrollWidth; return { scrollLeft: el.scrollLeft, maxScrollLeft: el.scrollWidth - el.clientWidth, lastHeaderRight: el.querySelector('th:last-child').getBoundingClientRect().right, wrapperRight: el.getBoundingClientRect().right }; });
  await wrapper.screenshot({ path: path.join(out, 'mobile-tms-table-scrolled.png') });
  const documentSize = await page.evaluate(() => ({ viewport: innerWidth, body: document.body.scrollWidth, root: document.documentElement.scrollWidth, scrollX }));
  const cssHash = createHash('sha256').update(await readFile(path.join(root, 'apps/web/components/LogisticsView.module.css'))).digest('hex');
  const checks = {
    storesAreSingleLine: measured.length === 3 && measured.every(x => x.whiteSpace === 'nowrap' && x.textLineCount === 1),
    tableScrolls: dimensions.scrollWidth > dimensions.clientWidth && ['auto', 'scroll'].includes(dimensions.overflowX) && scroll.scrollLeft > 0 && Math.abs(scroll.scrollLeft - scroll.maxScrollLeft) < 2 && scroll.lastHeaderRight <= scroll.wrapperRight + 1,
    noPageOverflow: documentSize.viewport === 390 && documentSize.root === 390 && documentSize.body === 390 && documentSize.scrollX === 0,
    noPageErrorsOrAnalyze: errors.length === 0 && analyzeRequests === 0,
  };
  const report = { at: new Date().toISOString(), viewport: 390, cssHash, measured, dimensions, scroll, documentSize, errors, analyzeRequests, checks };
  await writeFile(path.join(out, 'mobile-tms-table.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  assert.ok(Object.values(checks).every(Boolean), 'Mobile TMS recheck failed; see report evidence.');
} finally { await browser.close(); }
