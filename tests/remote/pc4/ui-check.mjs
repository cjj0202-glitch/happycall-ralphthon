import { chromium } from '../../e2e/node_modules/playwright/index.mjs';
import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const base = process.env.PC4_UI_BASE || 'http://127.0.0.1:13104';
if (!['127.0.0.1','localhost'].includes(new URL(base).hostname)) throw new Error('Local test harness only');
const out = path.join(root, 'reports/pc4', `tms-ui-${new Date().toISOString().replace(/[:.]/g,'-')}`);
await mkdir(out, { recursive: true });
const files = ['apps/web/components/TmsScene.tsx','apps/web/components/TmsScene.module.css','data/overlays/pc4-tms.json','data/fixtures/cases.json','tests/remote/pc4/ui-check.mjs'];
const hashes = async () => Object.fromEntries(await Promise.all(files.map(async f => [f, createHash('sha256').update(await readFile(path.join(root,f))).digest('hex')])));
const report = { started: new Date().toISOString(), host: 'pc4/장준호', base, head: execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim(), scope: 'Assigned TmsScene in test-only host; callbacks simulated. Not pc1 integration or six full product flows.', sourceHashesStart: await hashes(), checks: [], pageErrors: [], blockedExternal: [] };
const browser = await chromium.launch({ headless: true, ...(process.env.E2E_CHROMIUM ? { executablePath: process.env.E2E_CHROMIUM } : {}) });
const context = await browser.newContext({ viewport: { width:1440,height:1000 }, reducedMotion:'no-preference' });
await context.route('**/*', async route => {
  const url = new URL(route.request().url());
  if (url.protocol.startsWith('http') && !['127.0.0.1','localhost'].includes(url.hostname)) { report.blockedExternal.push(url.origin); await route.abort(); }
  else await route.continue();
});
const page = await context.newPage();
page.setDefaultTimeout(10000);
page.on('pageerror', e => report.pageErrors.push(e.message));
const scene = () => page.getByTestId('tms-scene');
const evidence = () => page.getByRole('region',{name:'TMS 상담 근거 연결',exact:true});
const firstLink = () => evidence().getByRole('button',{name:'이 근거 연결',exact:true}).first();
async function choose(caseId='CASE-0001', variant='baseline') {
  await page.goto(base);
  await page.locator('[data-ready="true"]').waitFor();
  await scene().waitFor();
  await page.getByLabel('검사 사례').selectOption(caseId);
  await page.getByLabel('검사 반례').selectOption(variant);
  await page.getByRole('region',{name:'선택 방문 상세',exact:true}).waitFor().catch(() => { if(variant !== 'empty') throw new Error('Selected visit panel missing'); });
}
async function check(name, fn) {
  if (process.env.PC4_UI_ONLY && !name.includes(process.env.PC4_UI_ONLY)) return;
  try { const measured = await fn(); report.checks.push({name,status:'PASS',measured:measured ?? null}); }
  catch (error) {
    const screenshot = `failure-${report.checks.length+1}.png`;
    await page.screenshot({path:path.join(out,screenshot),fullPage:true}).catch(()=>{});
    report.checks.push({name,status:'FAIL',error:String(error),screenshot});
  }
}
try {
  for (const width of [1440,1024,390]) for (const caseId of ['CASE-0001','CASE-0002']) {
    await check(`${caseId}-${width}-semantic-responsive`, async () => {
      await page.setViewportSize({width,height:1000}); await choose(caseId);
      const actual = await page.getByTestId('tms-actual').innerText();
      assert.equal(actual, caseId === 'CASE-0001' ? '미등록' : '05:10 KST');
      assert.match(await scene().innerText(),/실물 인도 여부는 별도 확인/);
      assert.match(await scene().innerText(),/실제 GPS 궤적 아님/);
      assert.match(await scene().innerText(),/TMS 이벤트 영상: 미등록/);
      assert.equal(await scene().locator('video').count(),0);
      const size = await page.evaluate(() => ({doc:document.documentElement.scrollWidth,viewport:innerWidth}));
      assert.ok(size.doc <= size.viewport+1,JSON.stringify(size));
      const table = page.getByRole('region',{name:'방문 시각 표 · 좁은 화면에서 가로 스크롤'});
      const tableSize = await table.evaluate(e => ({client:e.clientWidth,scroll:e.scrollWidth}));
      if(width===390) assert.ok(tableSize.scroll>tableSize.client,'Narrow table must scroll inside its container');
      const screenshot = `${caseId}-${width}.png`;
      await page.screenshot({path:path.join(out,screenshot),fullPage:true});
      return {actual,document:size,table:tableSize,screenshot};
    });
  }
  await page.setViewportSize({width:1440,height:1000});
  await check('keyboard-previous-next-back', async () => {
    await choose();
    const next=page.getByRole('button',{name:'다음 방문 →',exact:true});
    await next.focus(); await page.keyboard.press('Enter');
    assert.match(await page.getByRole('region',{name:'선택 방문 상세'}).innerText(),/가상 푸른점/);
    assert.ok(await firstLink().isDisabled());
    await page.getByRole('button',{name:'← 이전 방문',exact:true}).focus(); await page.keyboard.press('Space');
    assert.ok(await firstLink().isEnabled());
    await page.getByRole('button',{name:'← 상담으로 돌아가기'}).click();
    assert.equal(await page.getByTestId('back-count').innerText(),'1');
  });
  await check('animation-holds-moves-and-pauses', async () => {
    await choose();
    const initial=await page.getByTestId('tms-truck').getAttribute('transform');
    await page.getByRole('button',{name:'설명 재생',exact:true}).click();
    await page.waitForTimeout(300);
    assert.equal(await page.getByTestId('tms-truck').getAttribute('transform'),initial,'One-second stop before movement');
    await page.waitForFunction(start => document.querySelector('[data-testid="tms-truck"]').getAttribute('transform')!==start,initial);
    await page.getByRole('button',{name:'설명 재생 일시정지',exact:true}).click();
    const paused=await page.getByTestId('tms-truck').getAttribute('transform');
    await page.waitForTimeout(250);
    assert.equal(await page.getByTestId('tms-truck').getAttribute('transform'),paused);
    await page.getByRole('button',{name:'처음으로',exact:true}).click();
    assert.equal(await page.getByTestId('tms-truck').getAttribute('transform'),initial);
  });
  await check('reduced-motion', async () => {
    await page.emulateMedia({reducedMotion:'reduce'}); await choose();
    assert.ok(await page.getByRole('button',{name:'설명 재생',exact:true}).isDisabled());
    assert.match(await scene().innerText(),/동작 줄이기 적용/);
    await page.emulateMedia({reducedMotion:'no-preference'});
  });
  await check('save-failure-retry-no-false-success', async () => {
    await choose(); await page.getByLabel('검사 저장 모드').selectOption('fail');
    await firstLink().click();
    await evidence().getByRole('alert').waitFor();
    assert.match(await evidence().getByRole('alert').innerText(),/연결되지 않았습니다/);
    assert.equal(await evidence().getByRole('button',{name:'연결됨',exact:true}).count(),0);
    await page.getByLabel('검사 저장 모드').selectOption('success');
    await firstLink().click(); await evidence().getByRole('button',{name:'연결됨',exact:true}).waitFor();
    assert.equal(await page.getByTestId('callback-count').innerText(),'2');
    assert.equal(await page.getByTestId('last-link').innerText(),'E-M1');
  });
  await check('pending-double-click-and-case-change', async () => {
    await choose(); await page.getByLabel('검사 저장 모드').selectOption('deferred');
    await firstLink().dblclick();
    assert.equal(await page.getByTestId('callback-count').innerText(),'1');
    assert.ok(await evidence().getByRole('button',{name:'연결 중…'}).isDisabled());
    await page.getByLabel('검사 사례').selectOption('CASE-0002');
    await page.getByRole('button',{name:'지연 응답 반환',exact:true}).click();
    await page.waitForTimeout(100);
    assert.equal(await page.getByTestId('last-link').innerText(),'');
    assert.equal(await evidence().getByRole('button',{name:'연결됨',exact:true}).count(),0);
    assert.doesNotMatch(await evidence().innerText(),/CASE-0001 상담에 연결했습니다/);
    assert.ok(await firstLink().isEnabled());
  });
  await check('regression-authoritative-server-unlink', async () => {
    await choose(); await firstLink().click();
    await evidence().getByRole('button',{name:'연결됨',exact:true}).waitFor();
    await page.getByRole('button',{name:'서버 최신 선택 해제',exact:true}).click();
    assert.equal(await evidence().getByRole('button',{name:'연결됨',exact:true}).count(),0);
    assert.ok(await firstLink().isEnabled());
  });
  await check('regression-explicit-linked-text-intake', async () => {
    await choose('CASE-0002','linked-intake');
    assert.ok(await firstLink().isEnabled());
    await firstLink().click();
    await evidence().getByRole('button',{name:'연결됨',exact:true}).waitFor();
    assert.equal(await page.getByTestId('last-link').innerText(),'E-W5');
  });
  for (const variant of ['future','cross-day','cross-store','cross-case','invalid-calendar','no-timezone','invalid-asof','local-plan']) {
    await check(`reject-${variant}`, async () => {
      await choose('CASE-0002',variant);
      for(const button of await evidence().getByRole('button').all()) assert.ok(await button.isDisabled());
      assert.equal(await page.getByTestId('callback-count').innerText(),'0');
      if(variant==='future') assert.equal(await page.getByTestId('tms-actual').innerText(),'조회 기준 이후 · 현재 실적 미채택');
      if(['invalid-calendar','no-timezone'].includes(variant)) assert.equal(await page.getByTestId('tms-actual').innerText(),'시각 형식·시간대 확인 필요');
    });
  }
  await check('null-is-not-zero-or-midnight', async () => {
    await choose('CASE-0002','null-zero');
    assert.equal(await page.getByTestId('tms-actual').innerText(),'미등록');
    const detail=await page.getByRole('region',{name:'선택 방문 상세'}).innerText();
    assert.doesNotMatch(detail,/00:00|0분/); assert.match(detail,/시각 형식·시간대 확인 필요/);
  });
  await check('foreign-evidence-never-links', async () => {
    await choose('CASE-0001','foreign-evidence');
    const foreign=evidence().getByRole('article').filter({hasText:'E-W5'});
    assert.ok(await foreign.getByRole('button').isDisabled());
    assert.match(await foreign.innerText(),/이 사건의 허용 근거가 아닙니다/);
  });
  await check('empty-is-unregistered', async () => {
    await choose('CASE-0001','empty');
    assert.match(await scene().innerText(),/등록된 TMS 방문행이 없습니다/);
    assert.equal(await evidence().getByRole('button').count(),0);
  });
  await check('no-script-errors-or-external-calls', async () => {
    assert.deepEqual(report.pageErrors,[]); assert.deepEqual(report.blockedExternal,[]);
  });
} finally {
  report.finished=new Date().toISOString(); report.sourceHashesEnd=await hashes();
  report.sourceStable=JSON.stringify(report.sourceHashesStart)===JSON.stringify(report.sourceHashesEnd);
  report.summary={executed:report.checks.length,passed:report.checks.filter(c=>c.status==='PASS').length,failed:report.checks.filter(c=>c.status==='FAIL').length};
  await writeFile(path.join(out,'results.json'),JSON.stringify(report,null,2));
  await browser.close(); console.log(JSON.stringify({out,...report.summary,sourceStable:report.sourceStable}));
  if(report.summary.failed || !report.sourceStable) process.exitCode=1;
}
