import { createRequire } from 'node:module';
import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
const { chromium } = createRequire(new URL('../tests/e2e/package.json', import.meta.url))('playwright');
const root = path.resolve(import.meta.dirname, '..');
const base = process.env.UX_BASE || 'http://127.0.0.1:3112';
const api = process.env.UX_API;
assert.ok(api, 'UX_API must name a fresh disposable API');
for (const url of [base, api]) assert.equal(new URL(url).hostname, '127.0.0.1');
assert.ok(!['8100', '8112'].includes(new URL(api).port), 'User workspace APIs are excluded');
const initial = await fetch(`${api}/api/cases`, { headers: { 'X-Demo-Role': 'counselor' } });
assert.ok(initial.ok);
const initialCases = (await initial.json()).cases;
for (const id of ['CASE-0001', 'CASE-0002']) assert.equal(initialCases.find(c => c.id === id)?.status, 'draft');
const out = path.join(root, '.local/demo-video', `dynamic-${new Date().toISOString().replace(/[:.]/g, '-')}`);
await mkdir(out, { recursive: true });
const timeline = { schemaVersion: 2, base, api, viewport: { width: 1920, height: 1080 }, mode: 'replay',
  recordingEpochMs: null, epochMethod: 'midpoint of newPage; media and interaction events use Date.now',
  stages: [], audio: [], audioEvents: [], narration: [], interactions: [], errors: [], requests: [],
  clickRingsRecorded: true, complete: false };
const media = JSON.parse(await readFile(path.join(root, 'data/demo-media-manifest.json'), 'utf8'));
for (const id of ['CASE-0001', 'CASE-0002']) {
  const file = path.join(root, 'apps/web/public/demo', `${id}.wav`);
  const bytes = await readFile(file);
  const entry = media.assets.find(a => a.name === `${id}.wav`);
  assert.equal(createHash('sha256').update(bytes).digest('hex'), entry.sha256);
  timeline.audio.push({ caseId: id, file, sha256: entry.sha256, durationSeconds: entry.durationSeconds, playbackRate: 1.5 });
}
const narrationManifest = JSON.parse(await readFile(path.join(root, '.local/demo-video/narration/clova-5161572-manifest.json'), 'utf8'));
const narratorText = [
  '에이아이 고, 무엇이든 물어보살. 점포 문의를 상담원과 물류센터가 함께 처리하는 업무 시스템입니다.',
  '저장된 통화를 에이아이가 대화록과 접수서로 정리합니다. 상담원이 원문과 담당 부서를 확인합니다.',
  '미도착 문의는 티엠에스 배송 기록을 대조합니다. 기록이 없다고 미배송을 단정하지 않습니다.',
  '오출고 문의는 피킹과 출고 기록을 비교하고 소터 영상을 확인합니다. 영상은 시연용 합성 장면입니다.',
  '센터는 제목과 답변을 함께 생성하고, 검토한 내용을 경영주에게 회신합니다.',
  '미확인 사항은 남은 조치로 유지합니다. 분석은 저장 결과 재생이며, 실제 에이피아이 연결은 별도로 검증했습니다.',
];
const browser = await chromium.launch({ headless: true, channel: 'msedge' });
const context = await browser.newContext({ viewport: timeline.viewport,
  recordVideo: { dir: out, size: timeline.viewport }, reducedMotion: 'no-preference' });
await context.route('**/*', async route => {
  const request = route.request(), url = new URL(request.url());
  if (url.hostname !== '127.0.0.1') return route.abort();
  if (url.pathname.endsWith('/analyze') || url.pathname.endsWith('/reply-draft')) assert.equal(request.postDataJSON().mode, 'replay');
  if (url.pathname.startsWith('/api/')) {
    const response = await route.fetch({ url: new URL(api).origin + url.pathname + url.search });
    return route.fulfill({ response });
  }
  return route.continue();
});
await context.exposeBinding('__dynamicAudio', (_, event) => timeline.audioEvents.push(event));
await context.exposeBinding('__dynamicClick', (_, event) => timeline.interactions.push(event));
await context.addInitScript(() => {
  for (const type of ['playing', 'pause', 'ended', 'seeking', 'ratechange']) document.addEventListener(type, e => {
    if (e.target instanceof HTMLAudioElement) void window.__dynamicAudio({ type, epochMs: Date.now(),
      currentTime: e.target.currentTime, playbackRate: e.target.playbackRate, src: e.target.currentSrc });
  }, true);
  document.addEventListener('DOMContentLoaded', () => {
    const style = document.createElement('style');
    style.textContent = `html{scroll-behavior:smooth!important} *{scroll-margin-top:170px}
      [role=region]{scroll-behavior:smooth!important}
      #demo-pointer{position:fixed;left:0;top:0;width:30px;height:38px;z-index:2147483647;pointer-events:none;filter:drop-shadow(0 2px 3px #0008);will-change:transform}
      .demo-ripple{position:fixed;width:30px;height:30px;border:3px solid #0b79e6;border-radius:50%;pointer-events:none;z-index:2147483646;transform:translate(-50%,-50%);background:#43b1ff33;animation:demoRipple .7s ease-out forwards}
      @keyframes demoRipple{from{opacity:1;scale:.35}to{opacity:0;scale:3.5}}
      .demo-click-target{outline:3px solid #0787ec!important;outline-offset:5px;transition:outline-color .5s;box-shadow:0 0 0 8px #009cff20!important}`;
    document.head.appendChild(style);
    const cursor = document.createElement('div'); cursor.id = 'demo-pointer'; cursor.setAttribute('aria-hidden', 'true');
    cursor.innerHTML = '<svg viewBox="0 0 30 38"><path d="M3 2v28l7-7 6 12 5-3-6-11h11Z" fill="#0879d5" stroke="white" stroke-width="2.5" stroke-linejoin="round"/></svg>';
    document.body.appendChild(cursor);
    document.addEventListener('mousemove', e => { cursor.style.transform = `translate(${e.clientX}px,${e.clientY}px)`; });
    document.addEventListener('pointerdown', e => {
      const target = e.target instanceof Element ? e.target.closest('button,input,select,a') : null;
      const label = target?.getAttribute('aria-label') || target?.textContent?.trim().slice(0, 90) || '';
      const ring = document.createElement('div'); ring.className = 'demo-ripple';
      ring.style.left = `${e.clientX}px`; ring.style.top = `${e.clientY}px`;
      document.body.appendChild(ring); setTimeout(() => ring.remove(), 750);
      target?.classList.add('demo-click-target'); setTimeout(() => target?.classList.remove('demo-click-target'), 650);
      void window.__dynamicClick({ type: 'click', epochMs: Date.now(), x: e.clientX, y: e.clientY, label });
    }, true);
  });
});
const before = Date.now();
const page = await context.newPage();
timeline.recordingEpochMs = (before + Date.now()) / 2;
const video = page.video();
page.setDefaultTimeout(15000);
page.on('pageerror', e => timeline.errors.push(e.message));
page.on('response', r => { if (new URL(r.url()).pathname.startsWith('/api/')) timeline.requests.push({ path: new URL(r.url()).pathname, status: r.status() }); });
const wait = ms => page.waitForTimeout(ms);
const save = () => writeFile(path.join(out, 'timeline.json'), JSON.stringify(timeline, null, 2));
const stage = async (title, detail) => { timeline.stages.push({ epochMs: Date.now(), title, detail }); await save(); console.log(title); };
let pointer = { x: 400, y: 140 };
async function move(x, y, ms = 320) {
  const origin = { ...pointer }, steps = 16;
  for (let n = 1; n <= steps; n++) {
    const t = n / steps, eased = t * t * (3 - 2 * t);
    await page.mouse.move(origin.x + (x - origin.x) * eased, origin.y + (y - origin.y) * eased);
    await wait(ms / steps);
  }
  pointer = { x, y };
}
async function reveal(locator, align = 'center') {
  await locator.waitFor({ state: 'visible' });
  const beforeY = await page.evaluate(() => window.scrollY);
  await locator.evaluate((el, block) => el.scrollIntoView({ behavior: 'smooth', block, inline: 'nearest' }), align);
  await wait(550);
  const afterY = await page.evaluate(() => window.scrollY);
  if (Math.abs(afterY - beforeY) > 10) timeline.interactions.push({ type: 'scroll', epochMs: Date.now() - 550, fromY: beforeY, toY: afterY, durationMs: 550 });
}
async function point(locator) {
  await reveal(locator);
  const box = await locator.boundingBox(); assert.ok(box);
  await move(box.x + box.width / 2, box.y + box.height / 2);
}
async function click(locator, { scroll = true } = {}) {
  assert.equal(await locator.count(), 1, 'Click target must be unique');
  if (scroll) await reveal(locator);
  assert.ok(await locator.isEnabled());
  const box = await locator.boundingBox(); assert.ok(box);
  await move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down(); await wait(90); await page.mouse.up(); await wait(180);
}
async function narration(number, action) {
  const clip = narrationManifest.clips[number - 1];
  const file = path.join(root, '.local/demo-video/narration', clip.file);
  assert.equal(createHash('sha256').update(await readFile(file)).digest('hex'), clip.sha256);
  const epochMs = Date.now();
  timeline.narration.push({ file, epochMs, sha256: clip.sha256, text: narratorText[number - 1],
    source: 'CLOVA Dubbing', projectUrl: narrationManifest.projectUrl, durationSeconds: clip.sourceEndSeconds - clip.sourceStartSeconds });
  await action();
  await wait(Math.max(0, epochMs + (clip.sourceEndSeconds - clip.sourceStartSeconds) * 1000 - Date.now()) + 70);
  await save();
}
const primary = () => page.locator('.workflow-primary').getByRole('button');
const button = name => page.getByRole('button', { name, exact: typeof name === 'string' });
async function listen(id) {
  await stage(id === 'CASE-0001' ? '미도착 문의 · 통화 확인' : '오출고 문의 · 통화 확인', '저장된 합성 통화를 듣고 화자별 대화록을 확인합니다');
  await reveal(button('처음부터 전체 통화 재생'));
  await page.getByLabel('통화 재생 속도').selectOption('1.5');
  await click(button('처음부터 전체 통화 재생'));
  const deadline = Date.now() + 45000;
  let lastSpeech = '';
  while (Date.now() < deadline && !(await page.locator('audio').evaluate(el => el.ended))) {
    const current = page.locator('li[aria-current="true"]');
    if (await current.count()) {
      const speech = await current.textContent();
      if (speech !== lastSpeech) {
        lastSpeech = speech;
        await current.evaluate(el => { const region = el.closest('[role="region"]'); if (region) region.scrollTo({ top: region.scrollTop + el.getBoundingClientRect().top - region.getBoundingClientRect().top - 25, behavior: 'smooth' }); });
        timeline.interactions.push({ type: 'scroll', epochMs: Date.now(), region: 'transcript', label: '현재 발화로 대화록 스크롤' });
      }
    }
    await wait(220);
  }
  assert.ok(await page.locator('audio').evaluate(el => el.ended), 'Full call must end naturally');
  await wait(100);
  assert.ok(timeline.audioEvents.some(e => e.src.includes(`${id}.wav`) && e.type === 'ended'));
}
async function analyzeAndReview() {
  await click(primary());
  await page.getByLabel('점포코드 필수', { exact: true }).waitFor();
  await point(page.getByLabel('점포코드 필수', { exact: true }));
  const checkbox = page.getByRole('checkbox', { name: /점포·상품·전달 부서를 원문과 대조/ });
  await click(checkbox);
  assert.ok(await checkbox.isChecked());
}
async function transferToCenter() {
  await click(button(/상담으로 돌아가기/));
  await click(page.locator('.workflow-primary').getByRole('button', { name: /확인하고 센터로 이관/ }));
  await button(/2 처리 · 최종 회신/).waitFor();
  await click(button(/2 처리 · 최종 회신/));
}
async function centerReply(index) {
  await click(button('AI 답변 초안 생성').filter({ visible: true }));
  await button('제목·본문을 답변에 적용').waitFor();
  await click(button('제목·본문을 답변에 적용'));
  if (!await button(/조치 완료$/).count()) {
    const field = page.getByRole('textbox', { name: '남은 조치 내용', exact: true });
    await click(field);
    await field.pressSequentially(index ? '피킹·출고 토트 연결과 실제 수령 상품 확인' : '기사 확인 후 실제 도착·인도 여부 안내', { delay: 24 });
    await click(button('조치 추가'));
  }
  await click(page.locator('.panel-actions').getByRole('button', { name: '중간 회신 등록', exact: true }));
  await page.getByText('중간 회신 등록 완료', { exact: true }).waitFor();
  await click(button(/경영주 수신 화면 확인/));
  await page.locator('.registered-reply').waitFor();
  await reveal(page.locator('.registered-reply'));
}
try {
  await page.goto(base, { waitUntil: 'networkidle' });
  await page.getByRole('table', { name: '처리할 접수 목록 · 열 제목으로 정렬' }).waitFor();
  await page.getByRole('link', { name: 'AI-GO 무엇이든 물어보살 홈', exact: true }).waitFor();
  await page.getByLabel('분석 방식', { exact: true }).selectOption('replay');
  await move(730, 245, 200);
  await stage('AI-GO 무엇이든 물어보살', '실제 화면 조작으로 두 가지 문의를 처리합니다');
  await narration(1, async () => {
    await point(page.getByRole('table'));
    await click(button('아침 배송 미도착 확인 접수 열기'));
    await reveal(button('처음부터 전체 통화 재생'));
  });
  await listen('CASE-0001');
  await stage('AI가 접수 내용을 정리합니다', '상담원이 점포·수량·부서를 대조하고 확인합니다');
  await narration(2, analyzeAndReview);
  await click(page.locator('.workflow-primary').getByRole('button', { name: /이관 내용 확인/ }));
  await stage('TMS 배송 기록 확인', '계획 시각과 실제 방문 기록을 나란히 확인합니다');
  await narration(3, async () => {
    await click(button(/TMS 배송 확인/));
    await click(button('설명 재생'));
    await reveal(page.getByTestId('tms-scene'));
    await wait(1800);
  });
  await click(button('설명 재생 일시정지'));
  await transferToCenter();
  await stage('센터 담당자가 답변을 등록합니다', 'AI 제목·본문을 확인하고 경영주에게 중간 회신합니다');
  await narration(5, () => centerReply(0));
  await stage('두 번째 문의 · 오출고', '상담원 작업대에서 다른 문의를 선택합니다');
  await click(button('상담원 작업대'));
  await click(button('주문 상품과 다른 상품 입고 접수 열기'));
  await listen('CASE-0002');
  await stage('오출고 접수 정리와 원문 대조', '상품·수량·단위를 확인한 뒤 WMS 기록을 엽니다');
  await analyzeAndReview();
  await click(page.locator('.workflow-primary').getByRole('button', { name: /이관 내용 확인/ }));
  await click(button(/WMS 작업 확인/));
  await stage('WMS 공정과 소터 영상', '피킹·출고 기록을 확인하고 연결된 합성 영상을 재생합니다');
  await narration(4, async () => {
    await click(page.getByTestId('motion-toggle'));
    await reveal(page.getByTestId('process-diagram'));
    await wait(900);
    await click(page.getByTestId('case-video-shortcut'));
    await click(button('영상 재생'));
    await page.waitForFunction(() => document.querySelector('dialog video')?.currentTime >= .2);
    await wait(2600);
  });
  await click(button('영상 일시정지'));
  await click(button('연결 영상 닫기'));
  await transferToCenter();
  await stage('회신은 전달하고 미확인 조치는 남깁니다', '저장 결과 재생 시연 · 추가 확인이 남으면 처리 중으로 유지합니다');
  await narration(6, () => centerReply(1));
  await stage('접수 → AI 정리 → 물류 확인 → 센터 회신', '두 문의 모두 경영주 수신 화면까지 연결했습니다');
  await wait(750);
  for (const id of ['CASE-0001', 'CASE-0002']) {
    const response = await fetch(`${api}/api/cases/${id}`, { headers: { 'X-Demo-Role': 'center' } });
    assert.ok(response.ok); const saved = await response.json();
    assert.equal(saved.status, 'in_progress'); assert.ok(saved.reply && saved.replyTitle && saved.pendingActions.length);
  }
  assert.deepEqual(timeline.errors, []);
  assert.equal(timeline.narration.length, 6);
  assert.ok(timeline.interactions.filter(e => e.type === 'click').length >= 20);
  timeline.complete = true;
} catch (e) { timeline.failure = String(e.stack || e); process.exitCode = 1; }
finally {
  timeline.endEpochMs = Date.now(); await context.close(); timeline.rawVideo = await video.path();
  await browser.close(); await save(); console.log(JSON.stringify({ out, complete: timeline.complete, failure: timeline.failure }));
}
