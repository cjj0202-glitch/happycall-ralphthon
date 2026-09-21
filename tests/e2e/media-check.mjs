import { chromium } from 'playwright';
import { writeFile } from 'node:fs/promises';
import assert from 'node:assert/strict';

const browser = await chromium.launch({ headless: true, executablePath: process.env.E2E_CHROMIUM || 'C:/Users/choi8/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe' });
const report = { started: new Date().toISOString(), mode: 'read-only playback, no analysis API', checks: [] };
try {
  await Promise.all(['CASE-0001', 'CASE-0002'].map(async id => {
    const context = await browser.newContext({ viewport: { width: 1365, height: 950 } });
    const page = await context.newPage(); const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto('http://127.0.0.1:3100', { waitUntil: 'networkidle' });
    await page.getByRole('region', { name: '문의 선택' }).getByRole('button').filter({ hasText: id }).click();
    const a = page.getByLabel('합성 상담 통화');
    await a.evaluate(async el => { await el.play(); });
    await page.waitForFunction(() => document.querySelector('audio')?.ended, { }, { timeout: 65000 });
    const audio = await a.evaluate(el => ({ duration: el.duration, currentTime: el.currentTime, ended: el.ended, error: el.error?.code || null }));
    assert.equal(audio.ended, true); assert.equal(audio.error, null);
    assert.ok(audio.currentTime >= audio.duration - 0.1);
    const result = { id, audio, errors };
    if (id === 'CASE-0002') {
      await page.getByRole('navigation').getByRole('button', { name: 'WMS 작업 확인', exact: true }).click();
      const v = page.locator('video');
      await v.evaluate(async el => { await el.play(); });
      await page.waitForFunction(() => document.querySelector('video')?.ended, {}, { timeout: 45000 });
      result.video = await v.evaluate(el => ({ duration: el.duration, currentTime: el.currentTime, ended: el.ended, width: el.videoWidth, height: el.videoHeight, error: el.error?.code || null }));
      assert.equal(result.video.error, null); assert.ok(result.video.width > 0);
    }
    report.checks.push(result);
    console.log(JSON.stringify(result));
    await context.close();
  }));
} catch (e) { report.error = e.message; process.exitCode = 1; }
finally {
  report.finished = new Date().toISOString();
  await writeFile('../../reports/e2e/media-playback.json', JSON.stringify(report, null, 2));
  await browser.close();
}
