import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { mkdir, writeFile, readFile } from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const OUT = path.join(ROOT, 'reports/e2e', new Date().toISOString().replace(/[:.]/g, '-'));
const revisionOnly = process.argv.includes('--revision-only');
const only = process.argv.find(arg => arg.startsWith('--only='))?.slice(7);
await mkdir(OUT, { recursive: true });
const report = { started: new Date().toISOString(), suite: 'revision-and-explicit-reference', host: 'pc1/CJJ', executor: 'AI Playwright; not human observation', base: 'http://127.0.0.1:3100', api: 'http://127.0.0.1:8100', checks: [], errors: [], requests: [], responses: [], blockedLive: [], createdCases: [] };
async function sourceHashes() {
  const pairs = await Promise.all(['server/service.py', 'server/repository.py', 'server/app.py', 'apps/web/app/page.tsx', 'apps/web/components/LogisticsView.tsx', 'data/fixtures/cases.json'].map(async name => [name, await readFile(path.join(ROOT, name)).then(data => createHash('sha256').update(data).digest('hex')).catch(() => 'missing')]));
  return Object.fromEntries(pairs);
}
report.sourceHashesStart = await sourceHashes();
const browser = await chromium.launch({ headless: true, executablePath: process.env.E2E_CHROMIUM || 'C:/Users/choi8/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe' });
const context = await browser.newContext({ viewport: { width: 1365, height: 950 } });
const page = await context.newPage();
page.setDefaultTimeout(8000);
page.on('console', m => { if (m.type() === 'error') report.errors.push({ kind: 'console', message: m.text() }); });
page.on('pageerror', e => report.errors.push({ kind: 'pageerror', message: e.message }));
page.on('requestfailed', r => report.errors.push({ kind: 'network', url: r.url(), message: r.failure()?.errorText }));
page.on('request', r => { if (r.url().includes('/api/')) report.requests.push({ method: r.method(), url: r.url(), body: r.postData(), role: r.headers()['x-demo-role'] }); });
page.on('response', async r => { if (r.url().includes('/api/')) report.responses.push({ status: r.status(), url: r.url(), body: await r.json().catch(() => null) }); });
await context.route('**/analyze', async route => {
  const body = route.request().postDataJSON();
  if (body?.mode !== 'replay') { report.blockedLive.push(route.request().url()); await route.abort('blockedbyclient'); }
  else await route.continue();
});
const nav = label => page.getByRole('navigation').getByRole('button', { name: label, exact: true }).click();
const selected = id => page.getByRole('region', { name: '문의 선택' }).getByRole('button').filter({ hasText: id }).click();
const api = async (uri, method = 'GET', data, role = 'counselor') => {
  const res = await context.request.fetch(report.api + uri, { method, data, headers: { 'X-Demo-Role': role } });
  const body = await res.json();
  report.responses.push({ direct: true, method, url: uri, sent: data, role, status: res.status(), body });
  return { status: res.status(), body };
};
// Callers retain the snapshot associated with their edit. Never fetch/retry a revision here.
const patchFrom = (snapshot, delta, role = 'counselor') => {
  assert.ok(Number.isInteger(snapshot.revision), 'Editing snapshot must carry an integer revision');
  assert.ok(!Object.hasOwn(delta, 'expectedRevision'), 'Do not replace the editing snapshot revision');
  return api(`/api/cases/${snapshot.id}`, 'PATCH', { ...delta, expectedRevision: snapshot.revision }, role);
};
const newText = async (referenceCaseId) => {
  const r = await api('/api/intake', 'POST', { storeId: 'SYN-ST01', subject: '당일 1회차 배송 전체', text: `E2E-${Date.now()} revision/reference 독립 검증`, type: 'missing', ...(referenceCaseId ? { referenceCaseId } : {}) }, 'owner');
  assert.equal(r.status, 201, JSON.stringify(r.body));
  report.createdCases.push({ id: r.body.id, referenceCaseId: referenceCaseId || null });
  return r.body;
};
async function check(name, task) {
  if (only && name !== only && name !== 'runtime-positive-control') {
    report.checks.push({ name, status: 'NOT_RUN', reason: `Focused recheck: ${only}` });
    return;
  }
  if (revisionOnly && ['voice-audio-decode-and-playback', 'voice-explicit-replay-refinement', 'case-switch-isolates-intake-and-evidence', 'responsive-1365-921-390'].includes(name)) {
    report.checks.push({ name, status: 'NOT_RUN', reason: 'Focused revision/reference run; preserve existing fixture state and prior media/responsive evidence.' });
    return;
  }
  try { const evidence = await task(); report.checks.push({ name, status: 'PASS', evidence }); }
  catch (e) { report.checks.push({ name, status: 'FAIL_RECHECK', message: e.message }); await page.screenshot({ path: path.join(OUT, `failure-${report.checks.length}.png`), fullPage: true }).catch(() => {}); }
  console.log(`${report.checks.at(-1).status} ${name}`);
  await writeFile(path.join(OUT, 'results.json'), JSON.stringify(report, null, 2));
}
let textId;
try {
  await check('runtime-positive-control', async () => {
    const h = await api('/api/health'); assert.equal(h.status, 200);
    await page.goto(report.base, { waitUntil: 'networkidle', timeout: 60000 });
    await page.getByRole('heading', { name: '상담 작업대', exact: true }).waitFor();
    assert.equal(await page.getByLabel('분석 방식').inputValue(), 'replay');
    const cases = await api('/api/cases'); assert.ok(cases.body.cases.some(c => c.id === 'CASE-0001'));
    return { apiStatus: h.status, caseCount: cases.body.cases.length, selectedMode: 'replay' };
  });
  await check('voice-audio-decode-and-playback', async () => {
    await selected('CASE-0001');
    const audio = page.getByLabel('합성 상담 통화');
    await audio.waitFor();
    await page.waitForFunction(() => { const a = document.querySelector('audio'); return a && (a.readyState >= 2 || a.error); });
    const meta = await audio.evaluate(async a => { if (a.error) return { error: a.error.code, src: a.currentSrc }; await a.play(); return { duration: a.duration, readyState: a.readyState, src: a.currentSrc }; });
    assert.ok(meta.duration > 0, JSON.stringify(meta));
    await page.waitForFunction(() => document.querySelector('audio')?.currentTime > 0.15);
    const playback = await audio.evaluate(a => { const result = { currentTime: a.currentTime, paused: a.paused }; a.pause(); return result; });
    return { ...meta, ...playback, limit: 'Browser decoding/playback measured; Korean auditory quality not human-verified.' };
  });
  await check('voice-explicit-replay-refinement', async () => {
    await selected('CASE-0001');
    const response = page.waitForResponse(r => r.url().endsWith('/CASE-0001/analyze')); response.catch(() => {});
    await page.getByRole('button', { name: '저장된 분석 결과 재생' }).click();
    const r = await response; const body = await r.json();
    assert.equal(r.status(), 200); assert.equal(body.mode, 'replay');
    assert.equal(body.analysis.fields.quantity, null);
    await page.getByText('실제 AI 호출은 하지 않았습니다.', { exact: false }).waitFor();
    assert.equal(await page.getByLabel('수령 수량(경영주 진술)', { exact: true }).inputValue(), '');
    assert.ok(Number.isInteger(body.revision));
    return { mode: body.mode, quantity: body.analysis.fields.quantity, requestId: body.requestId, revision: body.revision };
  });
  await check('case-switch-isolates-intake-and-evidence', async () => {
    await selected('CASE-0002');
    assert.equal(await page.getByLabel('점포코드 필수').inputValue(), 'SYN-ST02');
    assert.ok(!(await page.locator('.desk').innerText()).includes('센터 출고 스캔 기록은 04:20'));
    await selected('CASE-0001');
    assert.equal(await page.getByLabel('점포코드 필수').inputValue(), 'SYN-ST01');
    assert.ok(!(await page.locator('.desk').innerText()).includes('휴지 1박스'));
    return { sequence: ['CASE-0001', 'CASE-0002', 'CASE-0001'], stores: ['SYN-ST01', 'SYN-ST02', 'SYN-ST01'] };
  });
  await check('owner-web-text-intake', async () => {
    await nav('경영주 접수');
    await page.getByLabel('점포코드', { exact: true }).fill('SYN-ST01');
    await page.getByLabel('문의 제목', { exact: true }).fill('당일 1회차 배송 전체');
    const source = `E2E-${Date.now()} 다른 날의 전체 배송 도착 여부와 위치 확인 요청. 수량은 알 수 없습니다.`;
    await page.getByLabel('상세 내용').fill(source);
    const response = page.waitForResponse(r => r.url().endsWith('/api/intake') && r.request().method() === 'POST'); response.catch(() => {});
    await page.getByRole('button', { name: '문의 접수하기' }).click();
    const r = await response; const body = await r.json(); textId = body.id;
    assert.equal(r.status(), 201); assert.ok(textId);
    assert.equal(body.sourceText, source);
    assert.equal(body.revision, 0);
    assert.equal(body.linkedFixtureId, null);
    assert.deepEqual(body.evidence, []);
    assert.ok(!body.wms && !body.tms, 'Matching store/subject must not join another delivery');
    report.createdCases.push({ id: textId, referenceCaseId: null, from: 'owner-ui' });
    await page.getByRole('heading', { name: '접수 진행 상황' }).waitFor();
    return { id: textId, sourceText: body.sourceText, linkedFixtureId: body.linkedFixtureId };
  });
  await check('new-text-unlinked-logistics-ui', async () => {
    assert.ok(textId); await nav('상담 작업대'); await selected(textId);
    await nav('WMS 작업 확인');
    assert.ok((await page.getByRole('region', { name: 'WMS 물류 확인' }).innerText()).includes('연결 가능한 근거가 없습니다'));
    assert.ok(!(await page.getByRole('region', { name: 'WMS 물류 확인' }).innerText()).includes('SYN-OUT01'));
    await nav('TMS 배송 확인');
    assert.ok((await page.getByRole('region', { name: 'TMS 물류 확인' }).innerText()).includes('등록된 방문순서가 없습니다'));
    assert.ok(!(await page.getByRole('region', { name: 'TMS 물류 확인' }).innerText()).includes('SYN-R01'));
    return { id: textId, evidenceCount: 0, priorDeliveryJoined: false };
  });
  await check('revision-missing-stale-and-positive-control', async () => {
    const snapshot = await newText();
    const missing = await api(`/api/cases/${snapshot.id}`, 'PATCH', { intake: { request: 'E2E missing revision' } });
    assert.equal(missing.status, 428); assert.equal(missing.body.error?.code, 'REVISION_REQUIRED');
    assert.deepEqual((await api(`/api/cases/${snapshot.id}`)).body, snapshot);
    const winner = await patchFrom(snapshot, { intake: { request: 'E2E first accepted edit' } });
    assert.equal(winner.status, 200); assert.equal(winner.body.revision, snapshot.revision + 1);
    const loser = await patchFrom(snapshot, { intake: { request: 'E2E stale rejected edit' } });
    assert.equal(loser.status, 409); assert.equal(loser.body.error?.code, 'STATE_CONFLICT');
    assert.deepEqual((await api(`/api/cases/${snapshot.id}`)).body, winner.body);
    return { id: snapshot.id, originalRevision: snapshot.revision, missing: missing.status, acceptedRevision: winner.body.revision, staleRevisionSent: snapshot.revision, stale: loser.status, winningRequestPreserved: winner.body.intake.request };
  });
  await check('stale-ui-form-keeps-reviewed-revision', async () => {
    const created = await newText();
    const stalePage = await context.newPage();
    const patchRequests = [];
    stalePage.on('request', r => { if (r.method() === 'PATCH') patchRequests.push(r.postDataJSON()); });
    try {
      const loadedPromise = stalePage.waitForResponse(r => r.url().endsWith('/api/cases')); loadedPromise.catch(() => {});
      await stalePage.goto(report.base, { waitUntil: 'networkidle' });
      const loaded = (await (await loadedPromise).json()).cases.find(c => c.id === created.id);
      assert.ok(loaded);
      await stalePage.getByRole('region', { name: '문의 선택' }).getByRole('button').filter({ hasText: created.id }).click();
      const staleRequest = 'E2E pending form based on reviewed revision';
      await stalePage.getByPlaceholder('경영주가 요청한 내용을 확인해 주세요.').fill(staleRequest);
      const winner = await patchFrom(loaded, { intake: { request: 'E2E another editor wins' } });
      assert.equal(winner.status, 200);
      const responsePromise = stalePage.waitForResponse(r => r.url().endsWith(`/api/cases/${created.id}`) && r.request().method() === 'PATCH'); responsePromise.catch(() => {});
      await stalePage.getByRole('button', { name: '접수 내용 저장', exact: true }).click();
      const response = await responsePromise; const body = await response.json(); const sent = response.request().postDataJSON();
      assert.equal(sent.expectedRevision, loaded.revision, 'UI attached a newer revision to the stale form');
      assert.equal(sent.intake.request, staleRequest);
      assert.equal(response.status(), 409); assert.equal(body.error?.code, 'STATE_CONFLICT');
      await stalePage.getByRole('alert').filter({ hasText: '다른 작업자가' }).waitFor();
      assert.deepEqual((await api(`/api/cases/${created.id}`)).body, winner.body);
      assert.equal(patchRequests.length, 1, 'Stale UI silently retried a rejected edit');
      await stalePage.screenshot({ path: path.join(OUT, 'stale-form-rejected.png'), fullPage: true });
      return { id: created.id, reviewedRevision: loaded.revision, serverRevision: winner.body.revision, uiSentRevision: sent.expectedRevision, status: response.status(), message: body.error.message, observedPatchRequests: patchRequests.length };
    } finally { await stalePage.close(); }
  });
  await check('owner-reference-selection-preserves-text-and-clears-on-mismatch', async () => {
    await nav('경영주 접수');
    const raw = `E2E-${Date.now()} 연결 선택 중에도 보존할 경영주 원문`;
    await page.getByLabel('상세 내용').fill(raw);
    const reference = page.locator('.owner-form select');
    await reference.selectOption('CASE-0001');
    assert.equal(await page.getByLabel('점포코드', { exact: true }).inputValue(), 'SYN-ST01');
    assert.equal(await page.getByLabel('문의 제목', { exact: true }).inputValue(), '당일 1회차 배송 전체');
    assert.equal(await page.getByLabel('상세 내용').inputValue(), raw);
    await page.getByLabel('점포코드', { exact: true }).fill('SYN-DIFFERENT');
    assert.equal(await reference.inputValue(), '');
    await reference.selectOption('CASE-0001');
    await page.getByLabel('문의 제목', { exact: true }).fill('다른 날의 문의 제목');
    assert.equal(await reference.inputValue(), '');
    await reference.selectOption('CASE-0001');
    await page.locator('.owner-form input[type=radio]').nth(1).check();
    assert.equal(await reference.inputValue(), '');
    assert.equal(await page.getByLabel('상세 내용').inputValue(), raw);
    return { preservedSource: raw, clearedOn: ['storeId', 'subject', 'type'] };
  });
  await check('explicit-reference-only-links-matching-case', async () => {
    const mismatch = await api('/api/intake', 'POST', { storeId: 'SYN-ST01', subject: '당일 1회차 배송 전체', text: 'E2E reject wrong reference', type: 'missing', referenceCaseId: 'CASE-0002' }, 'owner');
    assert.equal(mismatch.status, 422); assert.equal(mismatch.body.error?.code, 'INVALID_REFERENCE_CASE');
    await nav('경영주 접수');
    await page.locator('.owner-form select').selectOption('CASE-0001');
    const raw = `E2E-${Date.now()} 동일사건을 명시 선택한 접수`;
    await page.getByLabel('상세 내용').fill(raw);
    const createdResponse = page.waitForResponse(r => r.url().endsWith('/api/intake') && r.request().method() === 'POST'); createdResponse.catch(() => {});
    await page.getByRole('button', { name: '문의 접수하기' }).click();
    const created = await createdResponse; const linked = await created.json(); textId = linked.id;
    assert.equal(created.status(), 201, JSON.stringify(linked));
    assert.equal(created.request().postDataJSON().referenceCaseId, 'CASE-0001');
    assert.equal(linked.sourceText, raw);
    report.createdCases.push({ id: textId, referenceCaseId: 'CASE-0001', from: 'owner-ui' });
    assert.equal(linked.linkedFixtureId, 'CASE-0001'); assert.equal(linked.revision, 0);
    assert.ok(linked.evidence.some(e => e.id === 'E-M3')); assert.equal(linked.tms.routeId, 'SYN-R01');
    await page.reload({ waitUntil: 'networkidle' });
    return { id: textId, referenceCaseId: linked.linkedFixtureId, revision: linked.revision, wrongReferenceRejected: mismatch.status };
  });
  await check('review-required-negative-and-server-no-mutation', async () => {
    assert.ok(textId, 'Text intake did not create a case');
    await page.reload({ waitUntil: 'networkidle' }); await nav('상담 작업대'); await selected(textId);
    assert.equal(await page.getByRole('button', { name: '확인 후 센터 전달' }).isDisabled(), true);
    const before = await api(`/api/cases/${textId}`);
    const r = await patchFrom(before.body, { status: 'handed_off', departmentId: 'delivery', reviewConfirmed: false });
    assert.equal(r.status, 422); assert.equal(r.body.error?.code, 'REVIEW_REQUIRED');
    const after = await api(`/api/cases/${textId}`);
    assert.deepEqual(after.body, before.body);
    return { before: before.body.status, rejected: r.body.error, after: after.body.status };
  });
  await check('foreign-case-evidence-rejected', async () => {
    assert.ok(textId);
    const snapshot = (await api(`/api/cases/${textId}`)).body;
    const r = await patchFrom(snapshot, { selectedEvidence: ['E-W1'] });
    assert.equal(r.status, 422); assert.equal(r.body.error?.code, 'INVALID_EVIDENCE');
    const after = await api(`/api/cases/${textId}`);
    assert.ok(!after.body.selectedEvidence.includes('E-W1'));
    assert.deepEqual(after.body, snapshot);
    return { rejected: r.body.error, evidence: after.body.selectedEvidence };
  });
  await check('logistics-separate-wms-tms-and-link', async () => {
    assert.ok(textId); await nav('상담 작업대'); await selected(textId);
    const beforeLink = (await api(`/api/cases/${textId}`)).body;
    await nav('WMS 작업 확인'); await page.getByRole('heading', { name: 'WMS 작업 확인', exact: true }).waitFor();
    await page.screenshot({ path: path.join(OUT, 'wms.png'), fullPage: true });
    const wmsText = await page.locator('main').innerText(); assert.ok(wmsText.includes('SYN-OUT01'));
    const link = page.getByRole('button', { name: /근거.*연결|접수.*연결|근거.*추가/ }).first();
    const wmsResponse = page.waitForResponse(r => r.url().endsWith(`/api/cases/${textId}`) && r.request().method() === 'PATCH'); wmsResponse.catch(() => {});
    await link.click();
    const wmsSavedResponse = await wmsResponse; const wmsSaved = await wmsSavedResponse.json();
    assert.equal(wmsSavedResponse.status(), 200, JSON.stringify(wmsSaved));
    assert.equal(wmsSavedResponse.request().postDataJSON().expectedRevision, beforeLink.revision);
    assert.equal(wmsSaved.revision, beforeLink.revision + 1);
    await page.getByRole('status').filter({ hasText: '근거' }).first().waitFor();
    await nav('TMS 배송 확인'); await page.getByRole('heading', { name: 'TMS 배송 확인', exact: true }).waitFor();
    const tmsText = await page.locator('main').innerText(); assert.ok(tmsText.includes('SYN-R01'));
    const tmsResponse = page.waitForResponse(r => r.url().endsWith(`/api/cases/${textId}`) && r.request().method() === 'PATCH'); tmsResponse.catch(() => {});
    await page.getByRole('button', { name: '이 근거 연결', exact: true }).first().click();
    const tmsSavedResponse = await tmsResponse; const tmsSaved = await tmsSavedResponse.json();
    assert.equal(tmsSavedResponse.status(), 200, JSON.stringify(tmsSaved));
    assert.equal(tmsSavedResponse.request().postDataJSON().expectedRevision, wmsSaved.revision);
    assert.equal(tmsSaved.revision, wmsSaved.revision + 1);
    await page.getByRole('status').filter({ hasText: '근거' }).first().waitFor();
    await page.screenshot({ path: path.join(OUT, 'tms.png'), fullPage: true });
    const c = await api(`/api/cases/${textId}`); assert.ok(c.body.selectedEvidence.includes('E-M3')); assert.ok(c.body.selectedEvidence.includes('E-M1'));
    return { linked: c.body.selectedEvidence, wms: 'SYN-OUT01', tms: 'SYN-R01', revisions: [beforeLink.revision, wmsSaved.revision, tmsSaved.revision] };
  });
  await check('null-quantity-handoff-positive', async () => {
    assert.ok(textId); await nav('상담 작업대'); await selected(textId);
    await page.getByLabel('상품·문의 대상 필수').fill('당일 1회차 배송 전체');
    await page.getByLabel('수령 수량(경영주 진술)', { exact: true }).fill('');
    await page.locator('.department-card select').selectOption('delivery');
    await page.getByRole('checkbox').check();
    assert.equal(await page.getByRole('button', { name: '확인 후 센터 전달' }).isEnabled(), true);
    const response = page.waitForResponse(r => r.url().endsWith(`/api/cases/${textId}`) && r.request().method() === 'PATCH'); response.catch(() => {});
    await page.getByRole('button', { name: '확인 후 센터 전달' }).click();
    const r = await response; const body = await r.json(); assert.equal(r.status(), 200, JSON.stringify(body));
    assert.equal(body.intake.quantity, null); assert.equal(body.status, 'handed_off'); assert.equal(body.reviewConfirmed, true);
    await page.getByRole('heading', { name: '센터 회신', exact: true }).waitFor();
    return { id: textId, quantity: body.intake.quantity, status: body.status };
  });
  await check('center-pending-intermediate-reply', async () => {
    assert.ok(textId); await nav('센터 회신'); await selected(textId);
    await page.getByLabel('경영주에게 등록할 회신 필수').fill('E2E 중간 회신: 차량 위치와 인도 상태를 확인 중입니다.');
    await page.getByLabel('남은 조치 내용').fill('E2E 차량 위치 확인');
    await page.getByRole('button', { name: '조치 추가', exact: true }).click();
    assert.equal(await page.getByRole('button', { name: '최종 회신·처리 완료' }).isDisabled(), true);
    const response = page.waitForResponse(r => r.url().endsWith(`/api/cases/${textId}`) && r.request().method() === 'PATCH'); response.catch(() => {});
    await page.getByRole('button', { name: '중간 회신 등록', exact: true }).click();
    const r = await response; const body = await r.json(); assert.equal(r.status(), 200, JSON.stringify(body));
    assert.equal(body.status, 'in_progress'); assert.deepEqual(body.pendingActions, ['E2E 차량 위치 확인']);
    return { id: textId, status: body.status, pending: body.pendingActions, reply: body.reply };
  });
  await check('server-pending-prevents-close', async () => {
    const snapshot = (await api(`/api/cases/${textId}`)).body;
    const r = await patchFrom(snapshot, { status: 'closed' }, 'center');
    assert.equal(r.status, 422); assert.equal(r.body.error?.code, 'ACTIONS_PENDING');
    assert.deepEqual((await api(`/api/cases/${textId}`)).body, snapshot);
    return r.body;
  });
  await check('center-final-after-pending-cleared', async () => {
    await page.getByRole('button', { name: 'E2E 차량 위치 확인 조치 완료', exact: true }).click();
    await page.getByLabel('경영주에게 등록할 회신 필수').fill('E2E 최종 회신: 가상 시연의 확인 조치를 완료했습니다.');
    const response = page.waitForResponse(r => r.url().endsWith(`/api/cases/${textId}`) && r.request().method() === 'PATCH'); response.catch(() => {});
    await page.getByRole('button', { name: '최종 회신·처리 완료' }).click();
    const r = await response; const body = await r.json(); assert.equal(r.status(), 200, JSON.stringify(body));
    assert.equal(body.status, 'closed'); assert.deepEqual(body.pendingActions, []);
    return { status: body.status, reply: body.reply };
  });
  await check('owner-registered-reply-visible', async () => {
    await nav('경영주 접수'); await page.getByLabel('접수 건 선택').selectOption(textId);
    const reply = await page.locator('.registered-reply').innerText(); assert.ok(reply.includes('E2E 최종 회신'));
    assert.ok((await page.locator('.receipt').innerText()).includes('처리 완료'));
    await page.screenshot({ path: path.join(OUT, 'owner-final.png'), fullPage: true });
    return { textId, reply };
  });
  await check('responsive-1365-921-390', async () => {
    const measurements = [];
    for (const width of [1365, 921, 390]) {
      await page.setViewportSize({ width, height: 950 });
      for (const label of ['상담 작업대', '경영주 접수', '센터 회신', 'WMS 작업 확인', 'TMS 배송 확인']) {
        await nav(label); await page.getByRole('heading', { name: label, exact: true }).waitFor();
        const measure = await page.evaluate(() => ({ viewport: innerWidth, body: document.body.scrollWidth, root: document.documentElement.scrollWidth }));
        measurements.push({ width, view: label, ...measure });
        await page.screenshot({ path: path.join(OUT, `${width}-${label.split(' ')[0]}.png`), fullPage: true });
      }
    }
    await writeFile(path.join(OUT, 'responsive.json'), JSON.stringify(measurements, null, 2));
    assert.ok(measurements.every(m => m.root <= m.width + 1), JSON.stringify(measurements.filter(m => m.root > m.width + 1)));
    return measurements;
  });
} finally {
  report.finished = new Date().toISOString();
  report.sourceHashesEnd = await sourceHashes();
  report.createdCaseId = textId;
  report.summary = Object.fromEntries(['PASS', 'FAIL_RECHECK', 'NOT_RUN'].map(s => [s, report.checks.filter(c => c.status === s).length]));
  report.liveRequests = report.requests.filter(r => r.body?.includes('demo-live')).length;
  report.fixtureShaNote = 'Development working tree; recheck after code changes.';
  await writeFile(path.join(OUT, 'results.json'), JSON.stringify(report, null, 2));
  await writeFile(path.join(ROOT, 'reports/e2e/latest-run.txt'), OUT);
  await browser.close();
  console.log(JSON.stringify({ output: OUT, summary: report.summary, errors: report.errors.length, liveRequests: report.liveRequests, createdCaseId: textId }));
  process.exitCode = report.summary.FAIL_RECHECK ? 1 : 0;
}


