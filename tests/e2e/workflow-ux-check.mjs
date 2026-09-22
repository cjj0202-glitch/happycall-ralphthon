import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

// Run only against an isolated local replay server, never the deployed system.
const base = process.env.UX_BASE || 'http://127.0.0.1:3112';
assert.equal(new URL(base).hostname, '127.0.0.1');
const out = path.resolve('.local/workflow-ux-check');
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true, ...(process.env.E2E_CHROMIUM ? { executablePath: process.env.E2E_CHROMIUM } : { channel: 'msedge' }) });
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const report = { checks: [], errors: [], requests: [], screenshots: [], mode: 'isolated replay; no paid AI; not human usability acceptance' };
const check = (name, actual, expected) => { assert.deepEqual(actual, expected, name); report.checks.push({ name, actual, expected }); };
await context.route('**/*', async route => {
  const request = route.request(); const url = new URL(request.url());
  if (url.hostname !== '127.0.0.1') return route.abort();
  if (url.pathname.endsWith('/analyze') || url.pathname.endsWith('/reply-draft')) assert.equal(request.postDataJSON().mode, 'replay');
  if (url.pathname.startsWith('/api/') && process.env.UX_API) {
    const target = new URL(process.env.UX_API); assert.equal(target.hostname, '127.0.0.1');
    const response = await route.fetch({ url: target.origin + url.pathname + url.search });
    return route.fulfill({ response });
  }
  return route.continue();
});
const page = await context.newPage();
page.setDefaultTimeout(12000);
page.on('pageerror', error => report.errors.push(error.message));
page.on('response', response => { if (response.url().includes('/api/')) report.requests.push({ path: new URL(response.url()).pathname, status: response.status() }); });
const snap = async name => { const file = path.join(out, name + '.png'); await page.screenshot({ path: file, fullPage: false }); report.screenshots.push(file); };
// The three-pane console keeps the queue, the case thread and its context side by side.
const queue = () => page.getByRole('complementary', { name: /접수 목록$/ });
const thread = () => page.locator('.console-thread');
const analyzeButton = () => page.getByRole('button', { name: 'AI로 정리하기', exact: true });
const handoffButton = () => thread().getByRole('button', { name: /센터로 넘기기/ });
try {
  await page.goto(base, { waitUntil: 'networkidle' });
  await queue().waitFor();
  check('queue rail replaces the seven column table', await page.locator('.queue-table').count(), 0);
  check('work stage stepper is gone', await page.locator('.workflow-steps').count(), 0);
  for (const width of [1440, 921, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    check('no document overflow at ' + width, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true);
    await snap('source-' + width);
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  for (const [index, title] of ['아침 배송 미도착 확인', '주문 상품과 다른 상품 입고'].entries()) {
    if (index) await page.getByRole('button', { name: '상담원 작업대', exact: true }).click();
    await queue().locator('.queue-filters').getByRole('button', { name: /^전체/ }).click();
    await page.getByRole('button', { name: title + ' 접수 열기', exact: true }).click();
    check(title + ': recorded call can be analyzed without forced playback', await analyzeButton().isEnabled(), true);
    check(title + ': handoff blocked before review', await handoffButton().isEnabled(), false);
    await page.getByLabel('통화 재생 속도').selectOption('2');
    await page.getByRole('button', { name: '처음부터 전체 통화 재생', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('audio')?.ended, null, { timeout: 45000 });
    check(title + ': AI enabled after natural playback', await analyzeButton().isEnabled(), true);
    await analyzeButton().click();
    await page.getByLabel('점포 코드 필수', { exact: true }).waitFor();
    check(title + ': intake editor appears in the same thread', await page.locator('#intake-editor').isVisible(), true);
    await snap('review-' + index);
    const request = page.getByLabel('점포가 바라는 것', { exact: true });
    if (index) await request.fill((await request.inputValue()) + '\n합성 UI 검수: 확인 후 회신 요청');
    else check('unchanged AI intake can be reviewed without dummy edit', (await request.inputValue()).length > 0, true);
    check(title + ': handoff still blocked before the human check', await handoffButton().isEnabled(), false);
    await page.getByRole('checkbox', { name: /원문과 맞는지 확인했습니다/ }).check();
    check(title + ': handoff ready', await handoffButton().isEnabled(), true);
    await snap('handoff-' + index);
    await thread().getByRole('button', { name: index ? /센터 작업 기록 보기/ : /배송 기록 보기/ }).click();
    if (index) {
      await page.getByTestId('case-video-shortcut').click();
      const video = page.locator('dialog video');
      await video.waitFor();
      await video.evaluate(v => v.play());
      await page.waitForFunction(() => document.querySelector('dialog video')?.currentTime > 1);
      check('wrong shipment: linked sorter video plays', await video.evaluate(v => v.videoWidth > 0), true);
      await page.keyboard.press('Escape');
      check('wrong shipment: the 3D scene also plays inline on the record page', await page.locator('.console-evidence video').first().isVisible(), true);
    }
    await page.getByRole('button', { name: /상담으로 돌아가기/ }).click();
    check(title + ': review state kept after visiting the records', await handoffButton().isEnabled(), true);
    await handoffButton().click();
    const reply = page.getByRole('textbox', { name: /경영주에게 등록할 회신/ });
    await reply.waitFor();
    await reply.fill('합성 검수 회신: 기록을 확인했습니다. 추가 확인이 필요한 내용은 별도로 안내하겠습니다.');
    await page.getByRole('button', { name: 'AI 답변 초안 생성', exact: true }).click();
    await page.getByRole('button', { name: '제목·본문을 답변에 적용', exact: true }).waitFor();
    check(title + ': AI preview preserves typed reply', await reply.inputValue(), '합성 검수 회신: 기록을 확인했습니다. 추가 확인이 필요한 내용은 별도로 안내하겠습니다.');
    check(title + ': generated draft nonempty', (await page.locator('.draft-reply').innerText()).length > 40, true);
    await page.getByRole('button', { name: '제목·본문을 답변에 적용', exact: true }).click();
    const finalReply = await reply.inputValue();
    const finalTitle = await page.getByRole('textbox', { name: '회신 제목', exact: true }).inputValue();
    check(title + ': generated title applied', finalTitle.length > 5, true);
    await page.getByRole('textbox', { name: '남은 조치 내용', exact: true }).fill('합성 시연: 원본 기록 추가 확인');
    await page.getByRole('button', { name: '조치 추가', exact: true }).click();
    await page.locator('.thread-dock').getByRole('button', { name: '중간 회신 등록', exact: true }).click();
    await page.getByText('중간 회신 등록 완료', { exact: true }).waitFor();
    check(title + ': interim registration visibly confirmed', true, true);
    await snap('center-' + index);
    const pending = page.getByRole('button', { name: /조치 완료$/ });
    for (let count = await pending.count(); count > 0; count--) await pending.first().click();
    await page.locator('.thread-dock').getByRole('button', { name: /최종 회신·처리 완료/ }).click();
    await page.getByRole('button', { name: /경영주 화면에서 보기/ }).waitFor();
    await page.getByRole('button', { name: /경영주 화면에서 보기/ }).click();
    await page.locator('.registered-reply').getByText(finalReply, { exact: true }).waitFor();
    await page.locator('.registered-reply').getByRole('heading', { name: finalTitle, exact: true }).waitFor();
    check(title + ': registered reply visible to owner', true, true);
  }
  check('browser exceptions', report.errors, []);
} catch (error) { report.failure = error.stack; await snap('failure'); process.exitCode = 1; }
finally { await writeFile(path.join(out, 'report.json'), JSON.stringify(report, null, 2)); await browser.close(); console.log(JSON.stringify(report)); }
