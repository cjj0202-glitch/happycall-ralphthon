// N04-Q3 independent inputs against real UI/HTTP. No product changes or analyzer calls.
import assert from 'node:assert/strict';

const roleHeaders = role => ({ 'X-Demo-Role': role });
const requestField = page => page.getByPlaceholder('경영주가 요청한 내용을 확인해 주세요.', { exact: true });
const replyField = page => page.getByPlaceholder('확인한 사실, 처리 내용과 후속 안내를 적어 주세요. 확인되지 않은 배송 시각이나 원인은 단정하지 않습니다.', { exact: true });
const actionField = page => page.getByRole('textbox', { name: '남은 조치 내용', exact: true });
const saveButton = page => page.getByRole('button', { name: '접수 내용 저장', exact: true });
const reviewBox = page => page.getByRole('checkbox', { name: '점포·상품·전달 부서를 원문과 대조하고, 접수 정보를 편집·확인했습니다.', exact: true });
const recovery = page => page.getByRole('region', { name: '최신 서버 내용과 초안 대조', exact: true });

async function bounded(promise, label) {
  let timer;
  try {
    return await Promise.race([promise, new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error(`${label}: actual PATCH was not observed within 12 seconds`)), 12_000);
    })]);
  } finally { clearTimeout(timer); }
}

async function selectCase(page, id, check, keyboard = false) {
  const button = page.getByRole('region', { name: '문의 선택', exact: true }).getByRole('button').filter({ hasText: id });
  assert.equal(await button.count(), 1, `Unique case selector required: ${id}`);
  if (keyboard) { await button.focus(); await page.keyboard.press('Enter'); } else await button.click();
  await page.waitForFunction(caseId => {
    const section = document.querySelector('[aria-label="문의 선택"]');
    return Array.from(section?.querySelectorAll('button') || []).some(item => item.textContent.includes(caseId) && item.getAttribute('aria-pressed') === 'true');
  }, id);
  await check(`selected case ${id}`, await button.getAttribute('aria-pressed'), 'true');
}
async function refresh(page, check) {
  const response = page.waitForResponse(item => new URL(item.url()).pathname === '/api/cases' && item.request().method() === 'GET');
  await page.getByRole('button', { name: '목록 새로고침', exact: true }).click();
  await check('list refresh actual HTTP status', (await response).status(), 200);
  await page.getByRole('button', { name: '목록 새로고침', exact: true }).waitFor({ state: 'visible' });
}
async function getCase(request, id, check) {
  const result = await request('GET', `/api/cases/${id}`);
  await check(`GET ${id}`, result.status, 200);
  return result.body;
}
async function patch(request, id, payload, role, check, record, label) {
  const result = await request('PATCH', `/api/cases/${id}`, payload, roleHeaders(role));
  await record({ label, method: 'PATCH', caseId: id, role, expectedRevision: payload.expectedRevision, status: result.status, response: result.body });
  await check(label, result.status, 200);
  return result.body;
}
async function handoff(request, id, check, record) {
  const current = await getCase(request, id, check);
  return patch(request, id, { expectedRevision: current.revision, intake: current.intake,
    departmentId: id === 'CASE-0001' ? 'delivery' : 'warehouse', reviewConfirmed: true, status: 'handed_off' },
  'counselor', check, record, `fixture setup: real handoff ${id}`);
}
async function compare(page, check, localMarker, remoteMarker) {
  await page.getByRole('button', { name: '최신 내용 대조', exact: true }).click();
  await recovery(page).waitFor({ state: 'visible' });
  const content = await recovery(page).innerText();
  await check('comparison contains preserved local draft', content.includes(localMarker), true);
  await check('comparison contains actual remote value', content.includes(remoteMarker), true);
}
async function uiSave(page, id, check) {
  const response = page.waitForResponse(item => new URL(item.url()).pathname === `/api/cases/${id}` && item.request().method() === 'PATCH');
  await saveButton(page).click();
  const result = await response;
  await check('UI save actual response status', result.status(), 200);
  return { body: await result.json(), submitted: result.request().postDataJSON() };
}
async function keyboardNav(page, label, check) {
  const button = page.getByRole('navigation', { name: '주 메뉴', exact: true }).getByRole('button', { name: label, exact: true });
  await button.focus();
  await check(`keyboard focus ${label}`, await button.evaluate(element => element === document.activeElement), true);
  await page.keyboard.press('Enter');
  await page.getByRole('heading', { name: label, exact: true }).first().waitFor({ state: 'visible' });
  const size = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth }));
  await check(`390px no document overflow ${label}`, size.scroll <= size.width + 1, true);
}

export async function run(h) {
  await h.axis('Q3-01', async ({ page, check, request, nav, openCase, screenshot, record }) => {
    const ids = ['CASE-0001', 'CASE-0002'];
    const desk = { 'CASE-0001': 'Q3 independent desk A: 현장 확인 초안 731', 'CASE-0002': 'Q3 independent desk B: 단위 대조 초안 842' };
    const replies = { 'CASE-0001': 'Q3 center A: 배송 기록 조사 중 153', 'CASE-0002': 'Q3 center B: 출고 대조 중 264' };
    const pending = { 'CASE-0001': 'Q3 등록 전 조치 A 375', 'CASE-0002': 'Q3 등록 전 조치 B 486' };
    const added = { 'CASE-0001': 'Q3 추가된 미저장 조치 A 597', 'CASE-0002': 'Q3 추가된 미저장 조치 B 608' };
    await openCase(ids[0]); await nav('상담 작업대');
    const before = {};
    for (const id of ids) {
      before[id] = await getCase(request, id, check);
      await selectCase(page, id, check);
      await requestField(page).fill(desk[id]);
      await reviewBox(page).check();
      await requestField(page).fill(desk[id] + ' 수정');
      desk[id] += ' 수정';
      await check(`${id} editing clears human confirmation`, await reviewBox(page).isChecked(), false);
      for (const view of ['WMS 작업 확인', 'TMS 배송 확인']) {
        await nav(view); await nav('상담 작업대');
        await check(`${id} counselor draft survives ${view}`, await requestField(page).inputValue(), desk[id]);
      }
    }
    for (const id of ids) {
      await selectCase(page, id, check);
      await check(`${id} counselor case-keyed buffer`, await requestField(page).inputValue(), desk[id]);
      const saved = await getCase(request, id, check);
      await check(`${id} unsaved counselor draft not persisted`, saved.intake.request, before[id].intake.request);
      await check(`${id} unsaved draft keeps revision`, saved.revision, before[id].revision);
    }
    await screenshot('q3-01-counselor-buffers');
    // Real role-authorized setup makes both cases eligible for center editing; this is not UI handoff coverage.
    for (const id of ids) await handoff(request, id, check, record);
    await refresh(page, check); await nav('센터 회신');
    for (const id of ids) {
      await selectCase(page, id, check);
      await replyField(page).fill(replies[id]);
      await actionField(page).fill(added[id]);
      await page.getByRole('button', { name: '조치 추가', exact: true }).click();
      await actionField(page).fill(pending[id]);
      for (const view of ['WMS 작업 확인', 'TMS 배송 확인']) {
        await nav(view); await nav('센터 회신');
        await check(`${id} center reply survives ${view}`, await replyField(page).inputValue(), replies[id]);
        await check(`${id} unsubmitted action survives ${view}`, await actionField(page).inputValue(), pending[id]);
        await check(`${id} added action survives ${view}`, await page.locator('.pending-item').filter({ hasText: added[id] }).count(), 1);
      }
    }
    for (const id of ids) {
      await selectCase(page, id, check);
      await check(`${id} center case-keyed reply`, await replyField(page).inputValue(), replies[id]);
      await check(`${id} center case-keyed action input`, await actionField(page).inputValue(), pending[id]);
      await nav('상담 작업대');
      await check(`${id} counselor draft separate from center role`, await requestField(page).inputValue(), desk[id]);
      await check(`${id} dispatched counselor form remains locked`, await requestField(page).isDisabled(), true);
      await nav('센터 회신');
      await check(`${id} center role buffer restores`, await replyField(page).inputValue(), replies[id]);
      const saved = await getCase(request, id, check);
      await check(`${id} unsaved center reply not published`, saved.reply ?? null, before[id].reply ?? null);
      await check(`${id} unsaved center actions not stored`, saved.pendingActions ?? [], before[id].pendingActions ?? []);
    }
    await screenshot('q3-01-center-buffers');
    return { cases: ids, roles: ['counselor', 'center'], mode: 'real UI drafts; real HTTP setup only for role-eligible handoff', limitation: 'page-memory persistence only; no full reload or crash recovery claim' };
  });

  await h.axis('Q3-02', async ({ page, check, request, nav, openCase, screenshot, record }) => {
    const id = 'CASE-0001';
    await openCase(id); await nav('상담 작업대');
    let current = await getCase(request, id, check);
    const local1 = 'Q3 local observer draft alpha 917';
    const remote1 = 'Q3 other counselor committed beta 028';
    await requestField(page).fill(local1);
    current = await patch(request, id, { expectedRevision: current.revision, intake: { request: remote1 } }, 'counselor', check, record, 'other counselor real HTTP edit 1');
    await refresh(page, check);
    await check('refresh does not overwrite local counselor draft', await requestField(page).inputValue(), local1);
    await check('stale save locked before comparison', await saveButton(page).isDisabled(), true);
    await compare(page, check, local1, remote1);
    await check('comparison is read-only until explicit choice', (await getCase(request, id, check)).intake.request, remote1);
    await page.getByRole('button', { name: '서버 내용 사용', exact: true }).click();
    await check('explicit server choice replaces local draft', await requestField(page).inputValue(), remote1);

    const local2 = 'Q3 keep my checked draft gamma 139';
    const remote2 = 'Q3 other counselor committed delta 240';
    await requestField(page).fill(local2); await reviewBox(page).check();
    current = await patch(request, id, { expectedRevision: current.revision, intake: { request: remote2 } }, 'counselor', check, record, 'other counselor real HTTP edit 2');
    await refresh(page, check); await compare(page, check, local2, remote2);
    await page.getByRole('button', { name: '내 초안 유지 · 다시 확인', exact: true }).click();
    await check('explicit keep restores chosen local value', await requestField(page).inputValue(), local2);
    await check('explicit keep clears counselor confirmation', await reviewBox(page).isChecked(), false);
    await check('keep choice alone does not write server', (await getCase(request, id, check)).intake.request, remote2);
    const saved = await uiSave(page, id, check);
    await check('explicit save uses compared server revision', saved.submitted.expectedRevision, current.revision);
    await check('explicit local save persists', (await getCase(request, id, check)).intake.request, local2);
    await screenshot('q3-02-counselor-explicit-choice');

    await handoff(request, id, check, record); await refresh(page, check); await nav('센터 회신');
    const centerLocal = 'Q3 local center draft epsilon 351';
    const centerRemote = 'Q3 other center committed zeta 462';
    await replyField(page).fill(centerLocal); await actionField(page).fill('Q3 아직 추가하지 않은 조치 573');
    current = await getCase(request, id, check);
    current = await patch(request, id, { expectedRevision: current.revision, reply: centerRemote, pendingActions: ['Q3 다른 담당자 실제 조치 684'], status: 'in_progress' }, 'center', check, record, 'other center real HTTP edit');
    await refresh(page, check);
    await check('refresh preserves center reply draft', await replyField(page).inputValue(), centerLocal);
    await check('refresh preserves unsubmitted action', await actionField(page).inputValue(), 'Q3 아직 추가하지 않은 조치 573');
    await compare(page, check, centerLocal, centerRemote);
    await page.getByRole('button', { name: '서버 내용 사용', exact: true }).click();
    await check('explicit center server choice replaces reply', await replyField(page).inputValue(), centerRemote);
    await check('explicit center server choice resets unsubmitted action', await actionField(page).inputValue(), '');
    await check('explicit server action restored', await page.locator('.pending-item').filter({ hasText: 'Q3 다른 담당자 실제 조치 684' }).count(), 1);
    await check('comparison/choice does not increase revision', (await getCase(request, id, check)).revision, current.revision);
    await screenshot('q3-02-center-explicit-choice');
    return { scope: 'counselor and center; actual independent HTTP writers plus explicit UI conflict choices', directWrites: 'recorded external actor mutations and handoff setup; UI save is separately observed' };
  });

  await h.axis('Q3-08', async ({ page, check, request, openCase, screenshot, record, base }) => {
    const id = 'CASE-0001';
    await page.setViewportSize({ width: 390, height: 900 });
    await openCase(id); await keyboardNav(page, '상담 작업대', check);
    const original = await getCase(request, id, check);
    const first = 'Q3 pending HTTP commit keeps draft eta 795';
    await requestField(page).fill(first);
    const url = `${base.replace(/\/$/, '')}/api/cases/${id}`;
    let patchCount = 0;
    let release;
    let received;
    const held = new Promise(resolve => { release = resolve; });
    const committed = new Promise(resolve => { received = resolve; });
    const delayed = async route => {
      if (route.request().method() !== 'PATCH') return route.continue();
      patchCount++;
      try {
        const response = await route.fetch({ maxRedirects: 0 });
        const body = await response.json();
        await record({ label: 'real save committed; response temporarily held', actualStatus: response.status(), response: body, submitted: route.request().postDataJSON() });
        received({ status: response.status(), body });
        await held;
        await route.fulfill({ response });
      } catch (error) { received({ error: error.message }); await route.abort().catch(() => {}); }
    };
    await page.route(url, delayed);
    try {
      await saveButton(page).click();
      const result = await bounded(committed, 'held response'); assert.ok(!result.error, result.error); await check('held response belongs to actual successful commit', result.status, 200);
      await check('pending save locks save button', await saveButton(page).isDisabled(), true);
      await check('pending save locks edit field', await requestField(page).isDisabled(), true);
      await saveButton(page).evaluate(button => button.click());
      for (const label of ['TMS 배송 확인', '상담 작업대']) await keyboardNav(page, label, check);
      await check('menu return preserves pending draft', await requestField(page).inputValue(), first);
      await check('menu return preserves pending operation lock', await saveButton(page).isDisabled(), true);
      await saveButton(page).evaluate(button => button.click());
      await check('duplicate disabled activation emits only one PATCH', patchCount, 1);
      await screenshot('q3-08-pending-390');
      const observed = page.waitForResponse(item => item.url() === url && item.request().method() === 'PATCH');
      release(); await check('released actual response status', (await observed).status(), 200);
      await page.waitForFunction(() => Array.from(document.querySelectorAll('button')).some(button => button.textContent === '접수 내용 저장' && !button.disabled));
      await check('single pending operation stored once', (await getCase(request, id, check)).revision, original.revision + 1);
    } finally { release(); await page.unroute(url, delayed); }

    // A real second commit is made, then only its response is lost. No fake 200 or synthetic storage response.
    const uncertainText = 'Q3 response lost, committed content theta 806';
    await requestField(page).fill(uncertainText);
    let lossCount = 0;
    let lossObserved;
    const loss = new Promise(resolve => { lossObserved = resolve; });
    const loseResponse = async route => {
      if (route.request().method() !== 'PATCH') return route.continue();
      lossCount++;
      try {
        const response = await route.fetch({ maxRedirects: 0 }); const body = await response.json();
        await record({ label: 'real commit followed by response-only abort', actualStatus: response.status(), response: body, submitted: route.request().postDataJSON() });
        lossObserved({ status: response.status(), body }); await route.abort('failed');
      } catch (error) { lossObserved({ error: error.message }); await route.abort().catch(() => {}); }
    };
    await page.route(url, loseResponse);
    try {
      await saveButton(page).click();
      const actual = await bounded(loss, 'lost response'); assert.ok(!actual.error, actual.error); await check('lost response had real commit success', actual.status, 200);
      const verify = () => page.getByRole('button', { name: '저장 여부 확인', exact: true });
      await verify().waitFor({ state: 'visible' });
      await check('uncertain save locks retry', await saveButton(page).isDisabled(), true);
      await check('uncertain save locks editing', await requestField(page).isDisabled(), true);
      await keyboardNav(page, 'WMS 작업 확인', check); await keyboardNav(page, '상담 작업대', check);
      await check('uncertain draft survives menu roundtrip', await requestField(page).inputValue(), uncertainText);
      await check('uncertain lock survives menu roundtrip', await saveButton(page).isDisabled(), true);
      await selectCase(page, 'CASE-0002', check, true);
      await check('another case does not inherit uncertain save lock', await requestField(page).isDisabled(), false);
      await selectCase(page, id, check, true);
      await check('original uncertain draft remains case-keyed', await requestField(page).inputValue(), uncertainText);
      await check('original uncertain lock remains', await requestField(page).isDisabled(), true);
      await screenshot('q3-08-uncertain-390');
      await verify().focus(); await page.keyboard.press('Enter');
      await page.getByRole('status').filter({ hasText: '서버에 요청한 접수 내용이 저장되어 있음을 확인했습니다.' }).waitFor({ state: 'visible' });
      await check('verification unlocks recovered editor', await requestField(page).isDisabled(), false);
      await check('verification never retransmits PATCH', lossCount, 1);
      const current = await getCase(request, id, check);
      await check('response-loss commit preserved once', current.revision, original.revision + 2);
      await check('verification observes exact committed content', current.intake.request, uncertainText);
      await screenshot('q3-08-recovered-390');
    } finally { await page.unroute(url, loseResponse); }
    return { viewport: 390, pendingPatchCount: patchCount, lostResponsePatchCount: lossCount, scope: 'native UI click/focus/Enter; two real HTTP commits; one held response and one response-only abort; no direct duplicate save' };
  });
}
