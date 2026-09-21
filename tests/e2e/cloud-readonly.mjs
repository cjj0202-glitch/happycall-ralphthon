import { chromium } from 'playwright';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';

// Credentials stay in an ignored local file and are sent only to this verified host.
const config = JSON.parse(await readFile('../../.local/cloud-preview-auth.json', 'utf8'));
assert.equal(config.url, 'https://g-28-arxz4aubg-52g-studio.vercel.app');
const origin = new URL(config.url).origin;
const headers = {
  authorization: `Basic ${Buffer.from(`${config.ONEFLOW_ACCESS_USER}:${config.ONEFLOW_ACCESS_PASSWORD}`).toString('base64')}`,
  'x-vercel-protection-bypass': config.bypass,
};
const manifest = JSON.parse(await readFile('../../data/demo-media-manifest.json', 'utf8'));
const started = new Date().toISOString();
const report = { started, url: config.url, deploymentId: 'dpl_ByC9km4G9rUevPYUu5pHVmLNjG6N', mode: 'protected read-only synthetic preview', views: [], media: [], mutationRequests: 0, pageErrors: [], limits: ['Storage is unavailable; this does not test persisted workflows or live AI.', 'Official CLI-created automation access retains Vercel project protection.', 'Playback does not verify human listening or OS output.'] };
const browser = await chromium.launch({ headless: true, executablePath: process.env.E2E_CHROMIUM || 'C:/Users/choi8/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe' });
await mkdir('test-results/cloud-readonly', { recursive: true });

async function open(width) {
  const context = await browser.newContext({ viewport: { width, height: 960 } });
  const page = await context.newPage();
  page.on('pageerror', error => report.pageErrors.push(error.message));
  await page.route('**/*', async route => {
    const request = route.request();
    if (new URL(request.url()).origin !== origin) return route.abort();
    if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method())) {
      report.mutationRequests += 1;
      return route.abort();
    }
    return route.continue({ headers: { ...request.headers(), ...headers } });
  });
  const response = await page.goto(origin, { waitUntil: 'networkidle' });
  assert.equal(response.status(), 200);
  await page.getByRole('button', { name: '합성 예시 열람', exact: true }).click();
  await page.getByRole('region', { name: '문의 선택' }).waitFor();
  assert.equal(await page.getByRole('alert').filter({ hasText: '현재 예시 열람 중입니다. 변경 사항은 저장되지 않습니다.' }).count(), 1);
  return { context, page };
}

try {
  for (const width of [1440, 1024, 390]) {
    const { context, page } = await open(width);
    for (const id of ['CASE-0001', 'CASE-0002']) {
      await page.getByRole('navigation').getByRole('button', { name: '상담 작업대', exact: true }).click();
      await page.getByRole('region', { name: '문의 선택' }).getByRole('button').filter({ hasText: id }).click();
      assert.equal(await page.getByRole('button', { name: '접수 내용 저장', exact: true }).isDisabled(), true);
      for (const view of ['상담 작업대', '경영주 접수', '센터 회신', 'WMS 작업 확인', 'TMS 배송 확인']) {
        await page.getByRole('navigation').getByRole('button', { name: view, exact: true }).click();
        assert.equal(await page.getByRole('heading', { level: 1, name: view, exact: true }).isVisible(), true);
        const layout = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth }));
        assert.ok(layout.scroll <= layout.width + 2, `${width}/${id}/${view}: document overflow`);
        if (view === '경영주 접수') assert.equal(await page.getByRole('button', { name: /문의 접수하기/ }).isDisabled(), true);
        report.views.push({ width, id, view, layout });
      }
    }
    await page.screenshot({ path: `test-results/cloud-readonly/tms-${width}.png`, fullPage: true });
    await context.close();
  }
  await Promise.all(['CASE-0001', 'CASE-0002'].map(async id => {
    const { context, page } = await open(1365);
    try {
      await page.getByRole('region', { name: '문의 선택' }).getByRole('button').filter({ hasText: id }).click();
      const asset = manifest.assets.find(value => value.name === `${id}.wav`);
      const response = await page.request.get(`${origin}/demo/${id}.wav`, { headers });
      assert.equal(response.status(), 200);
      const body = await response.body();
      assert.equal(body.length, asset.bytes);
      assert.equal(createHash('sha256').update(body).digest('hex'), asset.sha256);
      const player = page.getByLabel('합성 상담 통화');
      await player.evaluate(async element => { element.volume = 1; element.muted = false; element.playbackRate = 1; await element.play(); });
      await page.waitForFunction(() => document.querySelector('audio')?.ended, {}, { timeout: 65000 });
      const audio = await player.evaluate(element => ({ ended: element.ended, duration: element.duration, currentTime: element.currentTime, error: element.error?.code ?? null }));
      assert.equal(audio.error, null);
      assert.equal(audio.duration, asset.durationSeconds);
      const row = { id, sha256: asset.sha256, audio };
      if (id === 'CASE-0002') {
        await page.getByRole('navigation').getByRole('button', { name: 'WMS 작업 확인', exact: true }).click();
        await page.getByRole('button', { name: /AI 합성 CCTV 구간 보기/ }).first().click();
        const dialog = page.getByRole('dialog');
        await dialog.locator('video').evaluate(async element => { await element.play(); });
        await page.waitForFunction(() => document.querySelector('video')?.ended, {}, { timeout: 30000 });
        row.video = await dialog.locator('video').evaluate(element => ({ ended: element.ended, duration: element.duration, width: element.videoWidth, height: element.videoHeight, error: element.error?.code ?? null }));
        assert.equal(row.video.error, null);
        assert.equal(row.video.width, 960);
        await dialog.getByRole('button', { name: '연결 영상 닫기', exact: true }).click();
      }
      report.media.push(row);
    } finally { await context.close(); }
  }));
  assert.equal(report.views.length, 30);
  assert.equal(report.media.length, 2);
  assert.equal(report.mutationRequests, 0);
  assert.deepEqual(report.pageErrors, []);
  report.status = 'PASS_READ_ONLY_PREVIEW';
} catch (error) {
  report.status = 'FAILED';
  report.error = error.message;
  process.exitCode = 1;
} finally {
  report.finished = new Date().toISOString();
  await writeFile(`../../reports/e2e/cloud-readonly-${started.replaceAll(':', '-')}.json`, JSON.stringify(report, null, 2));
  await browser.close();
  console.log(JSON.stringify({ status: report.status, views: report.views.length, media: report.media.length, mutationRequests: report.mutationRequests, pageErrors: report.pageErrors, error: report.error }));
}
