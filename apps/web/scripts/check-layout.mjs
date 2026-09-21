import { chromium } from '../../../tests/e2e/node_modules/playwright/index.mjs';
import fs from 'node:fs/promises';
await fs.mkdir('.checks', { recursive: true });
const browser = await chromium.launch({ headless: true, executablePath: process.env.E2E_CHROMIUM || 'C:/Users/choi8/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe' });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
page.on('pageerror', e => errors.push(e.message));
await page.goto('http://127.0.0.1:3100', { waitUntil: 'networkidle', timeout: 60000 });
if (await page.getByRole('button', { name: '합성 예시 열람' }).isVisible()) await page.getByRole('button', { name: '합성 예시 열람' }).click();
await page.getByRole('heading', { name: '문의 원문' }).waitFor();
const result = [];
for (const width of [1440, 921, 390]) {
  await page.setViewportSize({ width, height: 1000 });
  for (const name of ['상담 작업대', '경영주 접수', '센터 회신', 'WMS 작업 확인', 'TMS 배송 확인']) {
    await page.getByRole('navigation').getByRole('button', { name, exact: true }).click();
    await page.screenshot({ path: `.checks/${width}-${name}.png`, fullPage: true });
    const overflow = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
    result.push({ width, name, ...overflow });
  }
}
await fs.writeFile('.checks/layout.json', JSON.stringify({ result, errors }, null, 2));
console.log(JSON.stringify({ result, errors }, null, 2));
await browser.close();
if (errors.length || result.some(r => r.document > r.viewport)) process.exitCode = 1;
