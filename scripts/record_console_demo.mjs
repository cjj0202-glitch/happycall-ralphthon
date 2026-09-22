// 3-Pane 콘솔 UI 시연 녹화. 실제 화면을 사람이 쓰듯 조작하고 Playwright 가 영상을 직접 만든다.
// 해설 음원이 없어도 화면 자막만으로 흐름을 따라올 수 있게 만든다(ffmpeg 불필요).
// 실행: UX_BASE=http://127.0.0.1:3100 UX_API=http://127.0.0.1:8123 node scripts/record_console_demo.mjs
import { createRequire } from 'node:module';
import assert from 'node:assert/strict';
import { mkdir, writeFile, rename } from 'node:fs/promises';
import path from 'node:path';

const require = createRequire(new URL('../tests/e2e/package.json', import.meta.url));
const { chromium } = require('playwright');
const root = path.resolve(import.meta.dirname, '..');
const base = process.env.UX_BASE || 'http://127.0.0.1:3100';
const api = process.env.UX_API;
assert.ok(api, 'UX_API must name a disposable replay API');
for (const url of [base, api]) assert.equal(new URL(url).hostname, '127.0.0.1');
assert.ok(!['8100'].includes(new URL(api).port), 'The user workspace API is excluded');

const initial = await fetch(`${api}/api/cases`, { headers: { 'X-Demo-Role': 'counselor' } });
assert.ok(initial.ok, 'The disposable API must answer');
const cases = (await initial.json()).cases;
for (const id of ['CASE-0001', 'CASE-0002']) assert.equal(cases.find(c => c.id === id)?.status, 'draft', `${id} must start from the fixture state`);

const stamp = new Date().toISOString().replace(/[:.]/g, '-');
const out = path.join(root, '.local/demo-video', `console-${stamp}`);
await mkdir(out, { recursive: true });
const timeline = { schemaVersion: 1, base, api, viewport: { width: 1600, height: 900 }, stages: [], interactions: [], errors: [], requests: [] };

const browser = await chromium.launch({ headless: true, channel: 'msedge', args: ['--autoplay-policy=no-user-gesture-required'] });
const context = await browser.newContext({
  viewport: timeline.viewport,
  recordVideo: { dir: out, size: timeline.viewport },
  deviceScaleFactor: 1,
});
await context.route('**/*', async route => {
  const url = new URL(route.request().url());
  if (url.hostname !== '127.0.0.1') return route.abort();
  if (url.pathname.endsWith('/analyze') || url.pathname.endsWith('/reply-draft')) {
    assert.equal(route.request().postDataJSON().mode, 'replay', 'Recording never spends real AI budget');
  }
  if (url.pathname.startsWith('/api/')) {
    const target = new URL(api);
    return route.fulfill({ response: await route.fetch({ url: target.origin + url.pathname + url.search }) });
  }
  return route.continue();
});

// 커서·클릭 표시와 자막 층. 녹화에 그대로 담기도록 페이지 안에 넣는다.
await context.addInitScript(() => {
  document.addEventListener('DOMContentLoaded', () => {
    const style = document.createElement('style');
    style.textContent = `
      html { scroll-behavior: smooth !important; }
      #demo-cursor { position: fixed; left: 0; top: 0; width: 26px; height: 34px; z-index: 2147483647; pointer-events: none; filter: drop-shadow(0 2px 4px rgba(0,0,0,.45)); will-change: transform; }
      .demo-ring { position: fixed; width: 26px; height: 26px; border: 3px solid #0075DE; border-radius: 50%; pointer-events: none; z-index: 2147483646; transform: translate(-50%,-50%); background: rgba(0,117,222,.18); animation: demoRing .85s ease-out forwards; }
      @keyframes demoRing { from { opacity: 1; scale: .4 } to { opacity: 0; scale: 3.2 } }
      .demo-hit { outline: 3px solid #0075DE !important; outline-offset: 4px; border-radius: 8px; }
      #demo-caption { position: fixed; left: 50%; bottom: 34px; transform: translateX(-50%); z-index: 2147483645; pointer-events: none;
        max-width: 1120px; padding: 16px 28px; border-radius: 14px; background: rgba(13,13,13,.9); color: #fff; text-align: center;
        font-family: 'Pretendard Variable','Pretendard','Malgun Gothic',sans-serif; opacity: 0; transition: opacity .35s ease; }
      #demo-caption.on { opacity: 1; }
      #demo-caption b { display: block; font-size: 15px; font-weight: 600; color: #7CC0FF; letter-spacing: .01em; margin-bottom: 6px; }
      #demo-caption span { display: block; font-size: 26px; font-weight: 700; line-height: 1.35; letter-spacing: -0.02em; }
      #demo-caption i { display: block; margin-top: 8px; font-size: 16px; font-style: normal; color: #D8D6D1; line-height: 1.45; }`;
    document.head.appendChild(style);

    const cursor = document.createElement('div');
    cursor.id = 'demo-cursor'; cursor.setAttribute('aria-hidden', 'true');
    cursor.innerHTML = '<svg viewBox="0 0 26 34"><path d="M3 2v25l6-6 5 10 4-2-5-10h9Z" fill="#0075DE" stroke="white" stroke-width="2.4" stroke-linejoin="round"/></svg>';
    document.body.appendChild(cursor);

    const caption = document.createElement('div');
    caption.id = 'demo-caption'; caption.setAttribute('aria-hidden', 'true');
    caption.innerHTML = '<b></b><span></span><i></i>';
    document.body.appendChild(caption);
    window.__demoCaption = (chapter, title, detail) => {
      caption.querySelector('b').textContent = chapter || '';
      caption.querySelector('span').textContent = title || '';
      caption.querySelector('i').textContent = detail || '';
      caption.classList.toggle('on', !!title);
    };

    document.addEventListener('mousemove', e => { cursor.style.transform = `translate(${e.clientX}px,${e.clientY}px)`; });
    document.addEventListener('pointerdown', e => {
      const ring = document.createElement('div');
      ring.className = 'demo-ring'; ring.style.left = `${e.clientX}px`; ring.style.top = `${e.clientY}px`;
      document.body.appendChild(ring); setTimeout(() => ring.remove(), 900);
      const hit = e.target instanceof Element ? e.target.closest('button,input,select,a,label') : null;
      if (hit) { hit.classList.add('demo-hit'); setTimeout(() => hit.classList.remove('demo-hit'), 900); }
    }, true);
  });
});

const page = await context.newPage();
const video = page.video();
page.setDefaultTimeout(20000);
page.on('pageerror', e => timeline.errors.push(e.message));
page.on('response', r => { const u = new URL(r.url()); if (u.pathname.startsWith('/api/')) timeline.requests.push({ path: u.pathname, status: r.status() }); });

const wait = ms => page.waitForTimeout(ms);
const save = () => writeFile(path.join(out, 'timeline.json'), JSON.stringify(timeline, null, 2));
let pointer = { x: 800, y: 300 };

async function say(chapter, title, detail, holdMs = 2600) {
  timeline.stages.push({ epochMs: Date.now(), chapter, title, detail });
  await page.evaluate(([c, t, d]) => window.__demoCaption?.(c, t, d), [chapter, title, detail]);
  await save();
  console.log(`${chapter} | ${title}`);
  await wait(holdMs);
}
const clearCaption = () => page.evaluate(() => window.__demoCaption?.('', '', ''));

async function move(x, y, ms = 620) {
  const from = { ...pointer }, steps = 18;
  for (let n = 1; n <= steps; n++) {
    const t = n / steps, e = t * t * (3 - 2 * t);
    await page.mouse.move(from.x + (x - from.x) * e, from.y + (y - from.y) * e);
    await wait(ms / steps);
  }
  pointer = { x, y };
}
async function reveal(locator) {
  await locator.waitFor({ state: 'visible' });
  await locator.evaluate(el => el.scrollIntoView({ behavior: 'smooth', block: 'center' }));
  await wait(620);
}
async function point(locator, holdMs = 900) {
  await reveal(locator);
  const box = await locator.boundingBox(); assert.ok(box, 'point target must have a box');
  await move(box.x + box.width / 2, box.y + box.height / 2);
  await wait(holdMs);
}
async function click(locator) {
  assert.equal(await locator.count(), 1, 'Click target must be unique');
  await reveal(locator);
  assert.ok(await locator.isEnabled(), 'Click target must be enabled');
  const box = await locator.boundingBox(); assert.ok(box);
  await move(box.x + box.width / 2, box.y + box.height / 2);
  await wait(380);
  await page.mouse.down(); await wait(80); await page.mouse.up();
  timeline.interactions.push({ type: 'click', epochMs: Date.now(), x: pointer.x, y: pointer.y });
  await wait(900);
}

const button = name => page.getByRole('button', { name, exact: typeof name === 'string' });
const thread = () => page.locator('.console-thread');
const queue = () => page.locator('.console-queue');
const context3 = () => page.locator('.console-context');

async function openCase(title) {
  await click(queue().locator('.queue-filters').getByRole('button', { name: /^전체/ }));
  await click(button(`${title} 접수 열기`));
}

async function listenCall(id) {
  const play = button('처음부터 전체 통화 재생');
  await reveal(play);
  await page.getByLabel('통화 재생 속도').selectOption('1.5');
  await click(play);
  const deadline = Date.now() + 80000;
  let last = '';
  while (Date.now() < deadline && !(await page.locator('audio').evaluate(el => el.ended))) {
    const current = page.locator('li[aria-current="true"]');
    if (await current.count()) {
      const text = await current.first().textContent();
      if (text !== last) {
        last = text;
        await current.first().evaluate(el => {
          const region = el.closest('[role="region"]') || el.closest('.console-scroll');
          if (region) region.scrollTo({ top: region.scrollTop + el.getBoundingClientRect().top - region.getBoundingClientRect().top - 40, behavior: 'smooth' });
        });
      }
    }
    await wait(220);
  }
  assert.ok(await page.locator('audio').evaluate(el => el.ended), `${id} call must finish naturally`);
  await wait(900);
}

async function analyzeAndConfirm() {
  await click(button('AI로 정리하기'));
  await page.getByLabel('점포 코드 필수', { exact: true }).waitFor();
  await point(page.getByLabel('어떤 상품인가요 필수', { exact: true }), 1200);
  const check = page.getByRole('checkbox', { name: /원문과 맞는지 확인했습니다/ });
  await click(check);
  assert.ok(await check.isChecked(), 'The human confirmation must be recorded');
}

try {
  await page.goto(base, { waitUntil: 'networkidle' });
  await queue().waitFor();
  await page.getByLabel('분석 방식', { exact: true }).selectOption('replay');
  await move(820, 320);

  await say('AI-GO 무엇이든 물어보살', '점포의 전화 한 통을 끝까지 따라갑니다',
    '상담원·센터·경영주가 같은 사건을 이어받습니다. 데이터는 모두 시연용 합성 자료입니다.', 3400);

  await say('01 접수', '왼쪽에 오늘 처리할 접수가 쌓입니다',
    '점포, 문의 유형, 지금 할 일이 한 줄에 보입니다.', 1400);
  await point(queue().locator('.queue-rail'), 1600);
  await clearCaption();

  await openCase('아침 배송 미도착 확인');
  await say('01 접수', '전화로 들어온 문의를 엽니다',
    '통화 녹음과 화자별 대화록이 가운데 흐름 첫머리에 놓입니다.', 2600);
  await clearCaption();
  await listenCall('CASE-0001');

  await say('02 AI 정리', 'AI가 통화를 접수서로 정리합니다',
    '점포, 상품, 수량, 요청사항으로 나누고 모르는 것은 모른다고 남깁니다.', 2400);
  await clearCaption();
  await analyzeAndConfirm();
  await say('02 AI 정리', '사람이 원문과 맞는지 확인합니다',
    '확인 전에는 다음 단계로 넘어갈 수 없습니다.', 2200);
  await clearCaption();

  await say('03 기록 확인', '배송 기록을 열어 봅니다',
    '계획한 도착 시각과 실제 기록이 남았는지를 먼저 봅니다.', 2000);
  await clearCaption();
  await click(thread().getByRole('button', { name: /배송 기록 보기/ }));
  await wait(1200);
  await say('03 기록 확인', '기록이 없다고 미도착으로 단정하지 않습니다',
    '확인된 것과 확인되지 않은 것을 화면이 구분해 보여 줍니다.', 3000);
  await clearCaption();
  await click(button(/상담으로 돌아가기/));

  await say('04 이관', '확인한 내용을 담당 부서로 넘깁니다',
    'AI가 추천한 부서를 사람이 확인한 뒤 넘깁니다.', 2200);
  await clearCaption();
  await click(thread().getByRole('button', { name: /센터로 넘기기/ }));

  await say('05 센터 회신', '센터는 넘어온 접수와 기록을 함께 봅니다',
    '상담원이 정리한 내용과 연결한 기록이 그대로 따라옵니다.', 2600);
  await clearCaption();
  await click(button('AI 답변 초안 생성'));
  await button('제목·본문을 답변에 적용').waitFor();
  await say('05 센터 회신', 'AI 답변 초안은 저절로 보내지지 않습니다',
    '담당자가 읽고 적용한 뒤에야 답변란에 들어갑니다.', 2800);
  await clearCaption();
  await click(button('제목·본문을 답변에 적용'));
  await wait(900);

  const action = page.getByRole('textbox', { name: '남은 조치 내용', exact: true });
  await click(action);
  await action.pressSequentially('기사 확인 후 실제 도착·인도 여부 안내', { delay: 26 });
  await click(button('조치 추가'));
  await say('05 센터 회신', '남은 조치를 남기고 중간 회신을 등록합니다',
    '조치가 남아 있으면 문의는 처리 중으로 유지됩니다.', 2200);
  await clearCaption();
  await click(page.locator('.thread-dock').getByRole('button', { name: '중간 회신 등록', exact: true }));
  await page.getByText('중간 회신 등록 완료', { exact: true }).waitFor();
  await wait(900);

  await say('06 경영주 수신', '등록한 답변만 경영주에게 보입니다',
    '점포는 진행 상태와 센터 답변을 같은 화면에서 확인합니다.', 2400);
  await clearCaption();
  await click(button(/경영주 화면에서 보기/));
  await page.locator('.registered-reply').waitFor();
  await point(page.locator('.registered-reply'), 1200);
  await say('06 경영주 수신', '센터가 쓴 제목과 본문이 그대로 도착했습니다',
    '', 3000);
  await clearCaption();

  // 두 번째 사례: 오출고와 3D 센터 장면
  await click(button('상담원 작업대'));
  await openCase('주문 상품과 다른 상품 입고');
  await say('07 두 번째 문의', '주문한 것과 다른 상품이 온 경우입니다',
    '이 문의는 센터 안에서 무슨 일이 있었는지까지 봐야 합니다.', 2600);
  await clearCaption();
  await listenCall('CASE-0002');
  await analyzeAndConfirm();

  await say('08 센터 장면', '센터 작업 기록을 엽니다',
    '꺼낸 상품과 내보낸 상품이 다른 것이 한눈에 보입니다.', 2200);
  await clearCaption();
  await click(thread().getByRole('button', { name: /센터 작업 기록 보기/ }));
  await wait(1200);
  await point(page.locator('.console-evidence section').first(), 1400);

  await say('08 센터 장면', '그 시각 센터 장면을 그대로 재생합니다',
    '상품 꺼내기부터 분류기 갈림길, 내보내기까지 이어집니다. 합성 장면이며 실제 CCTV가 아닙니다.', 2600);
  await clearCaption();
  const scene = page.locator('.console-evidence video').first();
  await reveal(scene);
  await scene.evaluate(el => { el.currentTime = 0; return el.play(); });
  await wait(12500);
  await say('08 센터 장면', '기록이 있어도 원인과 책임은 아직 모릅니다',
    '화면은 확인된 것만 확인됐다고 말합니다.', 3000);
  await clearCaption();

  await say('AI-GO 무엇이든 물어보살', '접수부터 회신까지 한 흐름으로 이어집니다',
    'AI는 정리하고 근거를 모읍니다. 판단과 발송은 사람이 합니다.', 3600);
  await clearCaption();
  await wait(800);

  assert.deepEqual(timeline.errors, [], 'The recording must finish without browser exceptions');
} catch (error) {
  timeline.failure = error.stack;
  await page.screenshot({ path: path.join(out, 'failure.png') }).catch(() => {});
  process.exitCode = 1;
} finally {
  await save();
  await context.close();
  await browser.close();
  if (video) {
    const raw = await video.path().catch(() => null);
    if (raw) {
      const target = path.join(out, 'ai-go-console-demo.webm');
      await rename(raw, target).catch(() => {});
      timeline.video = target;
      await save();
      console.log('VIDEO', target);
    }
  }
  console.log(JSON.stringify({ stages: timeline.stages.length, clicks: timeline.interactions.length, errors: timeline.errors, failure: timeline.failure ? timeline.failure.split('\n')[0] : null }));
}
