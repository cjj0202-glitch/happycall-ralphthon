import { chromium } from 'playwright';
import { writeFile, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';

const browser = await chromium.launch({ headless: true, executablePath: process.env.E2E_CHROMIUM || 'C:/Users/choi8/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe' });
const manifest = JSON.parse(await readFile('../../data/demo-media-manifest.json', 'utf8'));
const report = { started: new Date().toISOString(), mode: 'read-only playback, no analysis API', releaseTag: manifest.releaseTag, checks: [], mutationRequests: 0, limits: ['Playback progression and decoded media only; human listening and OS output are not verified.'] };
try {
  await Promise.all(['CASE-0001', 'CASE-0002'].map(async id => {
    const context = await browser.newContext({ viewport: { width: 1365, height: 950 } });
    const page = await context.newPage(); const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.route('**/api/**', route => {
      if (!['GET', 'HEAD', 'OPTIONS'].includes(route.request().method())) {
        report.mutationRequests += 1;
        return route.abort();
      }
      return route.continue();
    });
    await page.goto('http://127.0.0.1:3100', { waitUntil: 'networkidle' });
    await page.getByRole('region', { name: '문의 선택' }).getByRole('button').filter({ hasText: id }).click();
    const a = page.getByLabel('합성 상담 통화');
    const asset = manifest.assets.find(item => item.name === `${id}.wav`);
    const response = await context.request.get(`http://127.0.0.1:3100/demo/${id}.wav`);
    assert.equal(response.status(), 200);
    const body = await response.body();
    assert.equal(body.length, asset.bytes);
    assert.equal(createHash('sha256').update(body).digest('hex'), asset.sha256);
    await a.evaluate(async el => { el.volume = 1; el.muted = false; el.playbackRate = 1; await el.play(); });
    await page.waitForFunction(() => document.querySelector('audio')?.ended, { }, { timeout: 65000 });
    const audio = await a.evaluate(el => ({ duration: el.duration, currentTime: el.currentTime, ended: el.ended, volume: el.volume, muted: el.muted, playbackRate: el.playbackRate, error: el.error?.code || null }));
    assert.equal(audio.ended, true); assert.equal(audio.error, null);
    assert.ok(audio.currentTime >= audio.duration - 0.1);
    assert.ok(Math.abs(audio.duration - asset.durationSeconds) < 0.01);
    const result = { id, sha256: asset.sha256, bytes: body.length, audio, errors };
    if (id === 'CASE-0002') {
      await page.getByRole('navigation').getByRole('button', { name: 'WMS 작업 확인', exact: true }).click();
      await page.getByRole('button', { name: /AI 합성 CCTV 구간 보기/ }).first().click();
      const dialog = page.getByRole('dialog');
      const v = dialog.locator('video');
      await v.evaluate(async el => { await el.play(); });
      await page.waitForFunction(() => document.querySelector('video')?.ended, {}, { timeout: 45000 });
      result.video = await v.evaluate(el => ({ duration: el.duration, currentTime: el.currentTime, ended: el.ended, width: el.videoWidth, height: el.videoHeight, error: el.error?.code || null }));
      assert.equal(result.video.error, null); assert.ok(result.video.width > 0);
      await dialog.getByRole('button', { name: '연결 영상 닫기', exact: true }).click();
    }
    report.checks.push(result);
    assert.deepEqual(errors, []);
    console.log(JSON.stringify(result));
    await context.close();
  }));
  assert.equal(report.mutationRequests, 0);
  report.status = 'PASS_SCOPED';
} catch (e) { report.error = e.message; process.exitCode = 1; }
finally {
  report.finished = new Date().toISOString();
  await writeFile(`../../reports/e2e/media-playback-${report.started.replaceAll(':', '-')}.json`, JSON.stringify(report, null, 2));
  await browser.close();
}
