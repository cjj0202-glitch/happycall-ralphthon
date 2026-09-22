import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '../..');
const base = process.env.UX_BASE || 'http://127.0.0.1:3112';
const api = process.env.UX_API;
assert.ok(api && new URL(api).hostname === '127.0.0.1');
assert.ok(!['8100', '8112'].includes(new URL(api).port), 'Use an isolated test API');
const output = path.join(root, '.local', `blender-investigation-${Date.now()}`);
await mkdir(output, { recursive: true });
const tracks = JSON.parse(await readFile(path.join(root, 'apps/web/public/demo/sorter-demo.tracks.json'), 'utf8'));
const report = { checks: [], errors: [], output, paidApiCalls: 0, humanUsabilityTest: false };
const check = (name, actual, expected) => { assert.deepEqual(actual, expected, name); report.checks.push({ name, actual, expected }); };
const getCase = async () => (await fetch(`${api}/api/cases/CASE-0002`, { headers: { 'X-Demo-Role': 'counselor' } })).json();
const browser = await chromium.launch({ headless: true, channel: 'msedge' });
const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
await context.route('**/*', async route => {
  const url = new URL(route.request().url());
  if (url.hostname !== '127.0.0.1') return route.abort();
  if (url.pathname.endsWith('/analyze')) assert.equal(route.request().postDataJSON().mode, 'replay');
  if (url.pathname.startsWith('/api/')) return route.fulfill({ response: await route.fetch({ url: new URL(api).origin + url.pathname + url.search }) });
  return route.continue();
});
const page = await context.newPage();
page.setDefaultTimeout(15000);
page.on('pageerror', error => report.errors.push(error.message));
try {
  await page.goto(base, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: '주문 상품과 다른 상품 입고 접수 열기', exact: true }).click();
  await page.locator('.workflow-primary').getByRole('button').click();
  await page.getByLabel('점포코드 필수', { exact: true }).waitFor();
  await page.getByRole('checkbox', { name: /점포·상품·전달 부서를 원문과 대조/ }).check();
  await page.locator('.workflow-primary').getByRole('button', { name: /이관 내용 확인/ }).click();
  const before = await getCase();
  await page.getByRole('button', { name: /WMS 작업 확인/ }).click();
  const entry = page.getByTestId('case-video-shortcut');
  check('3D entry is explicit', (await entry.innerText()).includes('3D 소터 공정 확인'), true);
  for (const width of [1600, 1024, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    check(`WMS overflow ${width}`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true);
    await page.screenshot({ path: path.join(output, `wms-${width}.png`) });
  }
  await page.setViewportSize({ width: 1600, height: 1000 });
  await entry.click();
  await page.getByTestId('cctv-phase-branch').waitFor();
  for (const phase of ['approach', 'branch', 'chute', 'settle']) {
    const target = tracks.frames.find(frame => frame.phase === phase);
    await page.getByTestId(`cctv-phase-${phase}`).click();
    await page.waitForFunction(expected => {
      const video = document.querySelector('dialog video');
      return video && !video.seeking && Math.abs(video.currentTime - expected) < 0.045 && video.paused;
    }, target.elapsedSeconds);
    check(`${phase} exact registered phase selected`, await page.getByTestId(`cctv-phase-${phase}`).getAttribute('aria-pressed'), 'true');
    report.checks.push({ name: `${phase} registered seek seconds`, actual: await page.locator('dialog video').evaluate(v => v.currentTime), expected: target.elapsedSeconds });
  }
  for (const width of [1600, 1024, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    check(`dialog overflow ${width}`, await page.locator('dialog').evaluate(el => el.scrollWidth <= el.clientWidth + 1), true);
    if (width === 390) {
      const summary = page.getByTestId('cctv-compact-comparison');
      const box = await summary.boundingBox();
      check('mobile record comparison visible before video', await summary.isVisible() && box.y < 220 && (await summary.innerText()).includes('비스킷 · 18 EA → 출고 휴지 · 1 BOX'), true);
    }
    await page.screenshot({ path: path.join(output, `dialog-${width}.png`) });
  }
  await page.setViewportSize({ width: 1600, height: 1000 });
  await page.getByTestId('cctv-phase-approach').click();
  await page.getByRole('button', { name: '영상 재생', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('dialog video')?.ended, undefined, { timeout: 20000 });
  const final = await page.locator('dialog video').evaluate(v => ({ duration: v.duration, time: v.currentTime, ended: v.ended, width: v.videoWidth, height: v.videoHeight }));
  check('full Blender video completes', final.ended && final.time >= 11.9 && final.duration === 12, true);
  report.video = final;
  await page.getByRole('button', { name: '연결 영상 닫기', exact: true }).click();
  check('all read-only interactions preserve case', await getCase(), before);
  check('browser errors', report.errors, []);
  report.complete = true;
} catch (error) {
  report.failure = String(error.stack || error); process.exitCode = 1;
  await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: false }).catch(() => {});
} finally {
  await writeFile(path.join(output, 'results.json'), JSON.stringify(report, null, 2));
  await browser.close();
  console.log(JSON.stringify({ complete: report.complete, checks: report.checks.length, failure: report.failure, output }));
}
