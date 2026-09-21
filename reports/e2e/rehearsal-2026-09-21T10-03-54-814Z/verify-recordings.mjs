import { chromium } from '../../../tests/e2e/node_modules/playwright/index.mjs';
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';
const dir = path.dirname(fileURLToPath(import.meta.url));
const run = JSON.parse(await readFile(path.join(dir, 'results.json'), 'utf8'));
const results = { started: new Date().toISOString(), method: 'Chromium local-file decode, first progression and final ended; no audio capture claim', recordings: [] };
const browser = await chromium.launch({ headless: true, executablePath: 'C:/Users/choi8/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe' });
try {
  for (const item of [...run.core, ...run.textManual, ...run.offline]) {
    const page = await browser.newPage();
    try {
      assert.ok(!path.relative(run.videoDirectory, item.recording).startsWith('..'));
      const bytes = await readFile(item.recording);
      await page.goto(pathToFileURL(item.recording).href);
      await page.waitForFunction(() => document.querySelector('video')?.readyState >= 2);
      const video = page.locator('video');
      await video.evaluate(async v => { v.muted = true; await v.play(); });
      await page.waitForFunction(() => document.querySelector('video')?.currentTime > 0.15);
      const start = await video.evaluate(v => ({ duration: v.duration, currentTime: v.currentTime, width: v.videoWidth, height: v.videoHeight, error: v.error?.code || null }));
      await video.evaluate(async v => { v.currentTime = Math.max(0, v.duration - 0.3); await v.play(); });
      await page.waitForFunction(() => document.querySelector('video')?.ended);
      const end = await video.evaluate(v => ({ ended: v.ended, currentTime: v.currentTime, error: v.error?.code || null }));
      assert.equal(start.error, null); assert.equal(end.error, null); assert.ok(start.width > 0); assert.equal(end.ended, true);
      results.recordings.push({ name: item.name, path: item.recording, bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex'), start, end, status: 'PASS' });
    } catch (e) { results.recordings.push({ name: item.name, status: 'FAIL', message: e.message }); }
    finally { await page.close(); }
  }
} finally { await browser.close(); }
results.finished = new Date().toISOString();
await writeFile(path.join(dir, 'recordings.json'), JSON.stringify(results, null, 2));
console.log(JSON.stringify({ passed: results.recordings.filter(x => x.status === 'PASS').length, total: results.recordings.length }));
if (results.recordings.some(x => x.status !== 'PASS')) process.exitCode = 1;
