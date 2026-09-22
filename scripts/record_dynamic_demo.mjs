import { createRequire } from 'node:module';
import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
const { chromium } = createRequire(new URL('../tests/e2e/package.json', import.meta.url))('playwright');
const root = path.resolve(import.meta.dirname, '..');
const base = process.env.UX_BASE || 'http://127.0.0.1:3112';
const api = process.env.UX_API;
const pace = process.env.UX_PACE || 'audience';
const narrationSource = process.env.UX_NARRATION || 'new';
assert.ok(['new', 'existing'].includes(narrationSource), 'UX_NARRATION must be new or existing');
assert.equal(pace, 'audience', 'This recording preserves audience pacing without edit acceleration');
assert.ok(api, 'UX_API must name a fresh disposable API');
for (const url of [base, api]) assert.equal(new URL(url).hostname, '127.0.0.1');
assert.ok(!['8100', '8112'].includes(new URL(api).port), 'User workspace APIs are excluded');
const initial = await fetch(`${api}/api/cases`, { headers: { 'X-Demo-Role': 'counselor' } });
assert.ok(initial.ok);
const initialCases = (await initial.json()).cases;
for (const id of ['CASE-0001', 'CASE-0002']) assert.equal(initialCases.find(c => c.id === id)?.status, 'draft');
const out = path.join(root, '.local/demo-video', `audience-${new Date().toISOString().replace(/[:.]/g, '-')}`);
await mkdir(out, { recursive: true });
const timeline = { schemaVersion: 3, base, api, pace, narrationSource, viewport: { width: 1600, height: 800 }, mode: 'replay',
  editPlaybackRate: 1, pacing: { pointerMoveMs: 650, beforeClickMs: 450, afterClickMs: 1100, scrollMs: 650, scrollSettleMs: 400 },
  recordingEpochMs: null, epochMethod: 'midpoint of newPage; media and interaction events use Date.now',
  stages: [], audio: [], audioEvents: [], narration: [], interactions: [], errors: [], requests: [],
  clickRingsRecorded: true, complete: false };
const media = JSON.parse(await readFile(path.join(root, 'data/demo-media-manifest.json'), 'utf8'));
for (const id of ['CASE-0001', 'CASE-0002']) {
  const file = path.join(root, 'apps/web/public/demo', `${id}.wav`);
  const bytes = await readFile(file);
  const entry = media.assets.find(a => a.name === `${id}.wav`);
  assert.equal(createHash('sha256').update(bytes).digest('hex'), entry.sha256);
  timeline.audio.push({ caseId: id, file, sha256: entry.sha256, durationSeconds: entry.durationSeconds, playbackRate: 1.25 });
}
const narrationManifest = JSON.parse(await readFile(path.join(root, '.local/demo-video/narration/clova-5161572-manifest.json'), 'utf8'));
assert.equal(narrationManifest.clips.length, 6, 'All six existing narration clips are required');
for (const clip of narrationManifest.clips) {
  const file = path.resolve(root, '.local/demo-video/narration', clip.file);
  assert.ok(file.startsWith(path.join(root, '.local/demo-video/narration') + path.sep));
  assert.ok(Number.isFinite(clip.sourceEndSeconds - clip.sourceStartSeconds) && clip.sourceEndSeconds > clip.sourceStartSeconds);
  assert.equal(createHash('sha256').update(await readFile(file)).digest('hex'), clip.sha256);
}
const audienceDir = path.join(root, '.local/demo-video/narration/audience-20260922');
const audienceManifest = narrationSource === 'new' ? JSON.parse(await readFile(path.join(audienceDir, 'manifest.json'), 'utf8')) : null;
if (audienceManifest) {
assert.equal(audienceManifest.status, 'READY', 'Six supplementary CLOVA clips must be READY before recording');
assert.ok(audienceManifest.projectUrl);
assert.deepEqual(audienceManifest.clips.map(clip => clip.key).sort(), ['A', 'B', 'C', 'D', 'E', 'F']);
for (const clip of audienceManifest.clips) {
  assert.ok(typeof clip.file === 'string' && clip.file && !path.isAbsolute(clip.file));
  const file = path.resolve(audienceDir, clip.file);
  assert.ok(file.startsWith(audienceDir + path.sep), 'Narration must remain inside its manifest directory');
  assert.ok(typeof clip.text === 'string' && clip.text.trim());
  assert.ok(Number.isFinite(clip.durationSeconds) && clip.durationSeconds > 0);
  assert.match(clip.sha256, /^[a-f0-9]{64}$/);
  assert.equal(createHash('sha256').update(await readFile(file)).digest('hex'), clip.sha256);
}
}
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
      .demo-ripple{position:fixed;width:30px;height:30px;border:3px solid #0b79e6;border-radius:50%;pointer-events:none;z-index:2147483646;transform:translate(-50%,-50%);background:#43b1ff33;animation:demoRipple 1s ease-out forwards}
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
      document.body.appendChild(ring); setTimeout(() => ring.remove(), 1000);
      target?.classList.add('demo-click-target'); setTimeout(() => target?.classList.remove('demo-click-target'), 1000);
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
const stage = async (title, detail, chapter, keyMessage, accentWords = []) => {
  assert.ok(chapter && keyMessage);
  timeline.stages.push({ epochMs: Date.now(), title, detail, chapter, keyMessage, accentWords }); await save(); console.log(title);
};
const hold = async (label, ms = 3500) => {
  timeline.interactions.push({ type: 'hold', epochMs: Date.now(), label, durationMs: ms });
  await wait(ms);
};
let pointer = { x: 400, y: 140 };
async function move(x, y, ms = 650) {
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
  const box = await locator.boundingBox();
  if (box && box.y >= 170 && box.y + box.height <= 760 && box.x >= 0 && box.x + box.width <= timeline.viewport.width) return;
  const beforeY = await page.evaluate(() => window.scrollY);
  const epochMs = Date.now();
  await locator.evaluate((el, block) => el.scrollIntoView({ behavior: 'smooth', block, inline: 'nearest' }), align);
  await wait(650);
  const afterY = await page.evaluate(() => window.scrollY);
  timeline.interactions.push({ type: 'scroll', epochMs, fromY: beforeY, toY: afterY, durationMs: 650, settleMs: 400 });
  await wait(400);
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
  await wait(450);
  await page.mouse.down(); await wait(90); await page.mouse.up(); await wait(1100);
}
async function narration(key, action) {
  if (narrationSource === 'existing' && ['A', 'E'].includes(key)) {
    await action();
    await hold(`${key} 화면 전환 · 추가 음성 없이 읽기`, 3000);
    await save();
    return;
  }
  const sourceKey = narrationSource === 'existing' && typeof key === 'string' ? ({ B: 2, C: 3, D: 5, F: 4 })[key] : key;
  const supplementary = typeof sourceKey === 'string';
  const manifest = supplementary ? audienceManifest : narrationManifest;
  const clip = supplementary ? manifest.clips.find(item => item.key === sourceKey) : manifest.clips[sourceKey - 1];
  assert.ok(clip, `Missing narration ${key}`);
  const file = path.join(supplementary ? audienceDir : path.join(root, '.local/demo-video/narration'), clip.file);
  const durationSeconds = supplementary ? clip.durationSeconds : clip.sourceEndSeconds - clip.sourceStartSeconds;
  assert.ok(Number.isFinite(durationSeconds) && durationSeconds > 0);
  assert.equal(createHash('sha256').update(await readFile(file)).digest('hex'), clip.sha256);
  const epochMs = Date.now();
  timeline.narration.push({ key, sourceKey, narrationSource: supplementary ? 'new' : 'existing', file, epochMs, sha256: clip.sha256, text: supplementary ? clip.text : narratorText[sourceKey - 1],
    source: 'CLOVA Dubbing', projectUrl: manifest.projectUrl, durationSeconds, playbackRate: 1 });
  await action();
  await wait(Math.max(0, epochMs + durationSeconds * 1000 - Date.now()) + 500);
  await save();
}
const primary = () => page.locator('.workflow-primary').getByRole('button');
const button = name => page.getByRole('button', { name, exact: typeof name === 'string' });
async function listen(id) {
  await stage(id === 'CASE-0001' ? '미도착 문의 · 통화 확인' : '오출고 문의 · 통화 확인', '저장된 합성 통화를 듣고 화자별 대화록을 확인합니다', '01 통화 접수', '통화를 끝까지 듣고 원문을 확인합니다', ['통화', '원문']);
  await reveal(button('처음부터 전체 통화 재생'));
  await page.getByLabel('통화 재생 속도').selectOption('1.25');
  await click(button('처음부터 전체 통화 재생'));
  const deadline = Date.now() + 60000;
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
  await hold('통화 종료와 원문 확인', 3000);
  assert.ok(timeline.audioEvents.some(e => e.src.includes(`${id}.wav`) && e.type === 'ended'));
}
async function analyzeAndReview() {
  await click(primary());
  await page.getByLabel('점포코드 필수', { exact: true }).waitFor();
  await point(page.getByLabel('점포코드 필수', { exact: true }));
  await hold('AI 정리 결과와 원문 대조', 4000);
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
async function draftReply() {
  await click(button('AI 답변 초안 생성').filter({ visible: true }));
  await button('제목·본문을 답변에 적용').waitFor();
  await reveal(button('제목·본문을 답변에 적용'));
  await hold('생성된 제목과 회신 본문 검토', 4000);
  await click(button('제목·본문을 답변에 적용'));
  await hold('회신 편집란에 적용된 내용', 3000);
}
async function registerReply(index) {
  if (!await button(/조치 완료$/).count()) {
    const field = page.getByRole('textbox', { name: '남은 조치 내용', exact: true });
    await click(field);
    await field.pressSequentially(index ? '피킹·출고 토트 연결과 실제 수령 상품 확인' : '기사 확인 후 실제 도착·인도 여부 안내', { delay: 24 });
    await click(button('조치 추가'));
  }
  await click(page.locator('.panel-actions').getByRole('button', { name: '중간 회신 등록', exact: true }));
  await page.getByText('중간 회신 등록 완료', { exact: true }).waitFor();
  await hold('센터 중간 회신 등록 완료', 3000);
  await click(button(/경영주 수신 화면 확인/));
  await page.locator('.registered-reply').waitFor();
  await reveal(page.locator('.registered-reply'));
  await stage('경영주가 같은 회신을 확인합니다', '센터가 검토한 제목과 본문이 경영주 수신 화면에 표시됩니다', '05 경영주 확인', '등록한 회신이 경영주에게 연결됩니다', ['같은 회신', '경영주']);
  await hold('경영주 수신 제목과 본문', 4000);
}
try {
  await page.goto(base, { waitUntil: 'networkidle' });
  await page.getByRole('table', { name: '처리할 접수 목록 · 열 제목으로 정렬' }).waitFor();
  await page.getByRole('link', { name: 'AI-GO 무엇이든 물어보살 홈', exact: true }).waitFor();
  await page.getByLabel('분석 방식', { exact: true }).selectOption('replay');
  await move(730, 245);
  await stage('AI-GO 무엇이든 물어보살', '실제 화면 조작으로 두 가지 문의를 처리합니다', '01 통화 접수', '문의 목록에서 오늘 처리할 건을 선택합니다', ['문의 목록', '두 가지 사례']);
  await narration(1, async () => {
    await point(page.getByRole('table'));
    await hold('오늘 처리할 문의 목록', 4000);
  });
  await narration('A', async () => {
    await click(button('아침 배송 미도착 확인 접수 열기'));
    await reveal(button('처음부터 전체 통화 재생'));
    await hold('미도착 문의의 통화와 대화록', 3000);
  });
  await listen('CASE-0001');
  await stage('AI가 접수 내용을 정리합니다', '상담원이 점포·수량·부서를 대조하고 확인합니다', '02 AI 정리', '원문과 접수서를 나란히 대조합니다', ['원문 대조', '담당 부서']);
  await narration('B', analyzeAndReview);
  await click(page.locator('.workflow-primary').getByRole('button', { name: /이관 내용 확인/ }));
  await stage('TMS 배송 기록 확인', '계획 시각과 실제 방문 기록을 나란히 확인합니다', '03 물류 확인', '배송 계획과 실제 도착 기록을 구분합니다', ['배송 계획', '실제 도착', '미확인']);
  await narration('C', async () => {
    await click(button(/TMS 배송 확인/));
    await hold('TMS 계획과 실제 기록 비교', 3500);
    await click(button('설명 재생'));
    await reveal(page.getByTestId('tms-scene'));
    await hold('TMS 배송 흐름 설명', 4000);
  });
  await click(button('설명 재생 일시정지'));
  await transferToCenter();
  await stage('센터 담당자가 답변을 등록합니다', 'AI 제목·본문을 확인하고 경영주에게 중간 회신합니다', '04 센터 회신', '제목과 본문을 검토한 뒤 회신합니다', ['제목·본문', '검토', '중간 회신']);
  await narration('D', async () => { await draftReply(); await registerReply(0); });
  await stage('두 번째 문의 · 오출고', '상담원 작업대에서 다른 문의를 선택합니다', '01 통화 접수', '주문한 상품과 받은 상품이 다른 문의입니다', ['오출고', '주문 상품', '받은 상품']);
  await narration('E', async () => {
    await click(button('상담원 작업대'));
    await click(button('주문 상품과 다른 상품 입고 접수 열기'));
    await reveal(button('처음부터 전체 통화 재생'));
    await hold('오출고 문의의 통화와 대화록', 3000);
  });
  await listen('CASE-0002');
  await stage('오출고 접수 정리와 원문 대조', '상품·수량·단위를 확인한 뒤 WMS 기록을 엽니다', '02 AI 정리', '상품과 수량을 원문에 맞게 확인합니다', ['상품', '수량', '원문']);
  await narration(2, analyzeAndReview);
  await click(page.locator('.workflow-primary').getByRole('button', { name: /이관 내용 확인/ }));
  await click(button(/WMS 작업 확인/));
  await stage('WMS 공정과 소터 영상', '피킹·출고 기록을 확인하고 연결된 합성 영상을 재생합니다', '03 물류 확인', '피킹·출고 기록과 물건의 이동을 확인합니다', ['피킹', '출고', '합성 시연']);
  await narration(4, async () => {
    await click(page.getByTestId('motion-toggle'));
    await reveal(page.getByTestId('process-diagram'));
    await hold('WMS 공정별 기록 비교', 3500);
  });
  await click(page.getByTestId('case-video-shortcut'));
  await stage('Blender로 제작한 3D 소터 공정', '오출고 CASE-0002 · 피킹 기록과 출고 기록을 연결해 확인합니다', '03 물류 확인', '3D 소터 영상 전체를 보며 물건의 이동을 확인합니다', ['3D 소터', '물건의 이동']);
  await narration('F', async () => {
    await click(button('영상 재생'));
    await page.waitForFunction(() => document.querySelector('dialog video')?.currentTime >= .2);
    const playbackStart = Date.now();
    await page.waitForFunction(() => document.querySelector('dialog video')?.ended, undefined, { timeout: 20000 });
    timeline.interactions.push({ type: 'hold', label: 'Blender 3D 소터 12초 전체 재생', epochMs: playbackStart,
      durationMs: Date.now() - playbackStart, fullVideoCompleted: true });
    const clip = await page.locator('dialog video').evaluate(el => ({ duration: el.duration, currentTime: el.currentTime, src: el.currentSrc, ended: el.ended }));
    assert.ok(clip.ended && clip.currentTime >= 11.9 && clip.duration >= 11.9);
    timeline.blenderVideo = { ...clip, synthetic: true, referenceCaseId: 'CASE-0002', evidenceId: 'W-W3' };
  });
  await stage('3D 장면과 피킹·출고 기록을 함께 확인합니다', '비스킷 18 EA와 휴지 1 BOX 기록을 대조합니다 · 작업자 과실은 미확인', '03 물류 확인', '영상과 업무 기록을 대조하고 미확인 사항을 남깁니다', ['업무 기록', '미확인']);
  await click(page.getByTestId('cctv-phase-branch'));
  await hold('분기 구간을 선택해 해당 장면에서 정지', 3000);
  await click(page.getByTestId('cctv-phase-chute'));
  await hold('슈트 이동 장면과 연결 기록 확인', 3000);
  await hold('영상과 피킹·출고 기록 대조', 4500);
  await click(button('연결 영상 닫기'));
  await transferToCenter();
  await stage('센터가 제목과 답변을 검토합니다', 'AI가 생성한 초안을 검토하고 답변 편집란에 적용합니다', '04 센터 회신', '검토한 제목과 답변만 회신에 적용합니다', ['답변 초안', '검토']);
  await narration(5, draftReply);
  await stage('회신은 전달하고 미확인 조치는 남깁니다', '저장 결과 재생 시연 · 추가 확인이 남으면 처리 중으로 유지합니다', '04 센터 회신', '확인되지 않은 내용은 남은 조치로 유지합니다', ['남은 조치', '처리 중']);
  await narration(6, () => registerReply(1));
  await stage('접수 → AI 정리 → 물류 확인 → 센터 회신', '두 문의 모두 경영주 수신 화면까지 연결했습니다', '05 경영주 확인', '접수부터 경영주 회신 확인까지 연결됩니다', ['접수', '확인', '회신']);
  await hold('두 사례 시연 마무리', 4000);
  for (const id of ['CASE-0001', 'CASE-0002']) {
    const response = await fetch(`${api}/api/cases/${id}`, { headers: { 'X-Demo-Role': 'center' } });
    assert.ok(response.ok); const saved = await response.json();
    assert.equal(saved.status, 'in_progress'); assert.ok(saved.reply && saved.replyTitle && saved.pendingActions.length);
  }
  assert.deepEqual(timeline.errors, []);
  assert.deepEqual(timeline.narration.map(item => item.key), narrationSource === 'existing'
    ? [1, 'B', 'C', 'D', 2, 4, 'F', 5, 6] : [1, 'A', 'B', 'C', 'D', 'E', 2, 4, 'F', 5, 6]);
  for (let i = 1; i < timeline.narration.length; i++) {
    const previous = timeline.narration[i - 1];
    assert.ok(timeline.narration[i].epochMs >= previous.epochMs + previous.durationSeconds * 1000, 'Narration clips must not overlap');
  }
  assert.ok(timeline.interactions.filter(e => e.type === 'click').length >= 20);
  timeline.complete = true;
} catch (e) { timeline.failure = String(e.stack || e); process.exitCode = 1; }
finally {
  timeline.endEpochMs = Date.now(); await context.close(); timeline.rawVideo = await video.path();
  await browser.close(); await save(); console.log(JSON.stringify({ out, complete: timeline.complete, failure: timeline.failure }));
}
