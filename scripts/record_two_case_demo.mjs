import { createRequire } from 'node:module';
const { chromium } = createRequire(new URL('../tests/e2e/package.json', import.meta.url))('playwright');
import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';

// Only a separately prepared disposable API is used. This script never resets data.
const root = path.resolve(import.meta.dirname, '..');
const base = process.env.UX_BASE || 'http://127.0.0.1:3112';
const api = process.env.UX_API || 'http://127.0.0.1:8115';
for (const url of [base, api]) assert.equal(new URL(url).hostname, '127.0.0.1');
assert.ok(!['8100', '8112'].includes(new URL(api).port), 'Do not record against a user workspace API; prepare an isolated fresh API');
const runId = new Date().toISOString().replace(/[:.]/g, '-');
const out = path.join(root, '.local/demo-video', runId);
await mkdir(out, { recursive: true });
const timeline = { schemaVersion: 1, base, api, mode: 'replay', viewport: { width: 1920, height: 1080 },
  recordingEpochMs: null, epochMethod: 'midpoint of Playwright newPage; audio events use Date.now; render offset is adjustable',
  stages: [], audioEvents: [], audio: [], errors: [], requests: [], complete: false };
const manifest = JSON.parse(await readFile(path.join(root, 'data/demo-media-manifest.json'), 'utf8'));
for (const id of ['CASE-0001', 'CASE-0002']) {
  const file = path.join(root, 'apps/web/public/demo', `${id}.wav`);
  const bytes = await readFile(file); const entry = manifest.assets.find(a => a.name === `${id}.wav`);
  assert.equal(createHash('sha256').update(bytes).digest('hex'), entry.sha256);
  timeline.audio.push({ caseId: id, file, sha256: entry.sha256, durationSeconds: entry.durationSeconds, playbackRate: 1.5 });
}
// Read-only preflight before opening the recording. Never turn a previous run back into draft.
const initial = await fetch(`${api}/api/cases`, { headers: { 'X-Demo-Role': 'counselor' } });
assert.ok(initial.ok, `Isolated API unavailable: ${initial.status}`);
const initialCases = (await initial.json()).cases;
for (const id of ['CASE-0001', 'CASE-0002']) assert.equal(initialCases.find(c => c.id === id)?.status, 'draft', `${id} must be a fresh isolated draft`);

const browser = await chromium.launch({ headless: true, ...(process.env.E2E_CHROMIUM ? { executablePath: process.env.E2E_CHROMIUM } : { channel: 'msedge' }) });
const context = await browser.newContext({ viewport: timeline.viewport, recordVideo: { dir: out, size: timeline.viewport }, reducedMotion: 'no-preference' });
await context.route('**/*', async route => {
  const req = route.request(); const url = new URL(req.url());
  if (!['127.0.0.1'].includes(url.hostname)) return route.abort();
  if (url.pathname.endsWith('/analyze') || url.pathname.endsWith('/reply-draft')) assert.equal(req.postDataJSON().mode, 'replay', 'No paid model calls in this recording');
  if (url.pathname.startsWith('/api/')) {
    const response = await route.fetch({ url: new URL(api).origin + url.pathname + url.search });
    return route.fulfill({ response });
  }
  return route.continue();
});
await context.exposeBinding('__recordDemoAudio', (_, event) => { timeline.audioEvents.push(event); });
await context.addInitScript(() => {
  // Observe media events only. Playback and application state are changed by visible controls.
  for (const type of ['playing', 'pause', 'ended', 'ratechange', 'seeking']) document.addEventListener(type, event => {
    const media = event.target;
    if (!(media instanceof HTMLAudioElement)) return;
    void window.__recordDemoAudio({ type, epochMs: Date.now(), currentTime: media.currentTime, playbackRate: media.playbackRate, src: media.currentSrc || media.src });
  }, true);
});
const beforePage = Date.now();
const page = await context.newPage();
timeline.recordingEpochMs = (beforePage + Date.now()) / 2;
const video = page.video();
page.setDefaultTimeout(20000);
page.on('pageerror', e => timeline.errors.push(e.message));
page.on('response', response => { if (new URL(response.url()).pathname.startsWith('/api/')) timeline.requests.push({ path: new URL(response.url()).pathname, status: response.status() }); });
const save = () => writeFile(path.join(out, 'timeline.json'), JSON.stringify(timeline, null, 2));
const hold = (ms = 3000) => page.waitForTimeout(ms);
const stage = async (title, detail, ms = 3000) => {
  timeline.stages.push({ epochMs: Date.now(), title, detail }); await save(); await hold(ms);
};
const centerAi = () => page.getByRole('button', { name: 'AI 답변 초안 생성', exact: true }).filter({ visible: true });
try {
  await page.goto(base, { waitUntil: 'networkidle' });
  await page.getByRole('table', { name: '처리할 접수 목록 · 열 제목으로 정렬' }).waitFor();
  await page.getByRole('link', { name: 'AI-GO 무엇이든 물어보살 홈', exact: true }).waitFor();
  await page.getByLabel('분석 방식', { exact: true }).selectOption('replay');
  await stage('AI-GO 무엇이든 물어보살 · 두 가지 문의 처리', '실제 화면 조작 · 합성 사례 · 저장 결과 재생', 16000);
  const titles = ['아침 배송 미도착 확인', '주문 상품과 다른 상품 입고'];
  for (const [index, title] of titles.entries()) {
    const id = `CASE-000${index + 1}`;
    if (index) { await page.getByRole('button', { name: '상담원 작업대', exact: true }).click(); await hold(2000); }
    await page.getByRole('button', { name: `${title} 접수 열기`, exact: true }).click();
    await stage(`${index + 1}. ${title}`, '상담원이 접수한 통화를 확인합니다');
    const analysis = page.locator('.workflow-primary').getByRole('button');
    assert.equal(await analysis.isEnabled(), true, 'Recorded call is immediately available for analysis');
    await page.getByLabel('통화 재생 속도').selectOption('1.5');
    await page.getByRole('button', { name: '처음부터 전체 통화 재생', exact: true }).click();
    await stage('통화 듣기', '두 화자 합성 음성 · 전체 통화 1.5배속', 2000);
    await page.waitForFunction(() => document.querySelector('audio')?.ended, null, { timeout: 60000 });
    // The browser's exposed binding reaches Node asynchronously after the DOM event.
    await hold(250);
    const audioEvents = timeline.audioEvents.filter(e => e.src.includes(`${id}.wav`));
    assert.ok(audioEvents.some(e => e.type === 'playing') && audioEvents.some(e => e.type === 'ended'), `${id} audio timing must be recorded`);
    await hold(2000); await analysis.click();
    await page.getByLabel('점포코드 필수', { exact: true }).waitFor();
    await stage('AI 접수 정리 · 상담원 검토', '저장된 분석 결과를 재생하고 원문·수량·미확인을 대조합니다', index ? 4000 : 16000);
    await page.getByRole('checkbox', { name: /점포·상품·전달 부서를 원문과 대조/ }).check();
    await page.locator('.workflow-primary').getByRole('button', { name: /이관 내용 확인/ }).click();
    await stage('부서 이관 준비', '관련 물류 기록을 확인하고 미확인 사항을 함께 전달합니다');
    await page.getByRole('button', { name: index ? /WMS 작업 확인/ : /TMS 배송 확인/ }).click();
    if (index) {
      await stage('WMS · 피킹과 출고 기록 대조', '상품·수량·단위·토트 차이를 확인합니다', 18000);
      await page.getByTestId('case-video-shortcut').click();
      await page.getByRole('button', { name: '영상 재생', exact: true }).click();
      await page.waitForFunction(() => document.querySelector('dialog video')?.currentTime >= 0.1);
      await stage('소터 공정 · 연결된 합성 영상', '설명용 장면입니다. 실제 CCTV·오출 원인 증거가 아닙니다', 8000);
      await page.getByRole('button', { name: '영상 일시정지', exact: true }).click();
      await hold(2000); await page.getByRole('button', { name: '연결 영상 닫기', exact: true }).click();
    } else {
      await stage('TMS · 계획과 방문 기록 대조', '기록 부재와 실제 미도착을 구분합니다', 16000);
      await page.getByRole('button', { name: '설명 재생', exact: true }).click(); await hold(4000);
      await page.getByRole('button', { name: '설명 재생 일시정지', exact: true }).click();
      await stage('도착·인도 여부는 추가 확인', '방문순번 지도는 설명용이며 GPS 실경로가 아닙니다');
    }
    await page.getByRole('button', { name: /상담으로 돌아가기/ }).click(); await hold(2000);
    await page.locator('.workflow-primary').getByRole('button', { name: /확인하고 센터로 이관/ }).click();
    await page.getByRole('button', { name: /2 처리 · 최종 회신/ }).waitFor();
    await stage('센터 · 이관 내용 확인', '상담원의 접수 내용과 연결 근거를 이어받습니다');
    await page.getByRole('button', { name: /2 처리 · 최종 회신/ }).click();
    await centerAi().click();
    await page.getByRole('button', { name: '제목·본문을 답변에 적용', exact: true }).waitFor();
    await stage('센터 AI 답변 초안', '저장 결과 재생 · 담당자가 검토한 뒤 답변에 적용합니다', index ? 4000 : 16000);
    await page.getByRole('button', { name: '제목·본문을 답변에 적용', exact: true }).click();
    // Preserve unknowns: never click an action-complete control for this recording.
    if (!await page.getByRole('button', { name: /조치 완료$/ }).count()) {
      await page.getByRole('textbox', { name: '남은 조치 내용', exact: true }).fill(index ? '피킹·출고 토트 연결과 실제 수령 상품 추가 확인' : '기사 확인 후 실제 도착·인도 여부 안내');
      await page.getByRole('button', { name: '조치 추가', exact: true }).click();
    }
    assert.ok((await page.getByRole('textbox', { name: /경영주에게 등록할 회신/ }).inputValue()).trim());
    await stage('미확인 사항을 남긴 중간 회신', '추가 확인이 남아 있어 처리 완료로 종결하지 않습니다');
    await page.locator('.panel-actions').getByRole('button', { name: '중간 회신 등록', exact: true }).click();
    await page.getByText('중간 회신 등록 완료', { exact: true }).waitFor();
    await hold(2000);
    await page.getByRole('button', { name: /경영주 수신 화면 확인/ }).click();
    await page.locator('.registered-reply').waitFor();
    await stage('경영주 · 등록된 회신 확인', '회신은 전달됐고 남은 조치는 처리 중으로 유지됩니다', 4000);
    const response = await fetch(`${api}/api/cases/${id}`, { headers: { 'X-Demo-Role': 'center' } });
    assert.ok(response.ok);
    const saved = await response.json();
    assert.equal(saved.status, 'in_progress', 'Unknown work must not be marked closed');
    assert.ok(saved.pendingActions?.length && saved.reply?.trim(), 'Intermediate reply and pending actions must both be saved');
  }
  assert.deepEqual(timeline.errors, []);
  timeline.complete = true;
  await stage('접수 → AI 정리 → 이관 → 센터 회신', '두 사례 모두 미확인 사항을 보존한 채 중간 회신까지 연결했습니다', 18000);
} catch (error) { timeline.failure = String(error.stack || error); process.exitCode = 1; }
finally {
  timeline.endEpochMs = Date.now();
  await context.close();
  timeline.rawVideo = await video.path();
  await browser.close(); await save();
  console.log(JSON.stringify({ out, complete: timeline.complete, rawVideo: timeline.rawVideo, failure: timeline.failure }));
}
