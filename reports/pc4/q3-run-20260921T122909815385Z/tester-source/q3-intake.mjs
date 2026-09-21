// N04-Q3: real UI/HTTP intake retry checks. No repository, key ledger or product writes.
import assert from 'node:assert/strict';

const OWNER = { 'X-Demo-Role': 'owner' };
const uuid4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const snapshot = value => structuredClone(value);
const ids = cases => cases.map(item => item.id).sort();
const byId = cases => [...cases].sort((a, b) => a.id.localeCompare(b.id));
function capture(request) {
  return { key: request.headers()['x-idempotency-key'], body: request.postDataJSON(), rawBody: request.postData(), method: request.method(), url: request.url() };
}
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  // Route errors are surfaced through the awaited promise, without unhandled rejection races.
  promise.catch(() => {});
  return { promise, resolve, reject };
}
async function within(promise, label) {
  let timer;
  try { return await Promise.race([promise, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(`${label}: no actual HTTP observation within 20 seconds`)), 20000); })]); }
  finally { clearTimeout(timer); }
}
async function list(request, check, label) {
  const result = await request('GET', '/api/cases');
  await check(`${label}: actual list HTTP`, result.status, 200);
  assert.ok(Array.isArray(result.body?.cases), 'Actual case list required');
  return result.body.cases;
}
async function prepareForm(page, nav, openCase, name) {
  await openCase('CASE-0001');
  await nav('경영주 접수');
  const form = page.locator('.owner-form');
  const body = { storeId: `SYN-${name}`, subject: `${name} 접수 응답 복구 확인`, text: `${name}: 실제 합성 문의입니다. 접수 결과가 불확실해도 같은 문의를 중복 등록하지 마세요.`, type: 'missing' };
  await form.getByLabel('점포코드', { exact: true }).fill(body.storeId);
  await form.getByLabel('문의 제목', { exact: true }).fill(body.subject);
  await form.getByLabel('상세 내용', { exact: true }).fill(body.text);
  const reference = form.locator('select[aria-describedby="reference-case-help"]');
  assert.equal(await reference.count(), 1);
  assert.equal(await reference.inputValue(), '');
  return { form, body, submit: form.getByRole('button', { name: '문의 접수하기', exact: false }) };
}
async function checkUncertainForm(form, expected, check, prefix) {
  for (const [label, key] of [['점포코드', 'storeId'], ['문의 제목', 'subject'], ['상세 내용', 'text']]) {
    const control = form.getByLabel(label, { exact: true });
    await check(`${prefix}: ${key} preserved`, await control.inputValue(), expected[key]);
    await check(`${prefix}: ${key} editing locked`, await control.isDisabled(), true);
  }
  await check(`${prefix}: fresh-key submit locked`, await form.getByRole('button', { name: '문의 접수하기', exact: false }).isDisabled(), true);
}
async function storedCase(request, check, id, label) {
  const result = await request('GET', `/api/cases/${id}`);
  await check(`${label}: actual case HTTP`, result.status, 200);
  return result.body;
}

export async function run(h) {
  await h.axis('Q3-03', async ({ page, context, base, check, request, nav, openCase, screenshot, record }) => {
    const before = await list(request, check, 'before UI intake');
    const { form, body, submit } = await prepareForm(page, nav, openCase, 'Q3-03');
    const url = `${base}/api/intake`;
    const first = deferred(), retry = deferred(), posts = [];
    let lookupFaults = 0, lookupUrl;
    const postHandler = async route => {
      if (route.request().method() !== 'POST') { await route.fallback(); return; }
      const index = posts.length, sent = capture(route.request());
      posts.push(sent);
      try {
        // The original body and key go to the real server. Only its first response is lost.
        const upstream = await route.fetch({ maxRedirects: 0 });
        const received = { status: upstream.status(), body: await upstream.json() };
        await record({ kind: 'actual-intake-http', attempt: index + 1, sent: snapshot(sent), received, responseDisposition: index === 0 ? 'abort-after-real-server-response' : 'unaltered-real-response' });
        if (index === 0) { await route.abort('failed'); first.resolve({ sent, received }); }
        else { await route.fulfill({ response: upstream }); retry.resolve({ sent, received }); }
      } catch (error) {
        (index === 0 ? first : retry).reject(error);
        await route.abort('failed').catch(() => {});
      }
    };
    const lookupHandler = async route => {
      if (route.request().method() !== 'GET') { await route.fallback(); return; }
      lookupFaults += 1;
      await record({ kind: 'intentional-fault-injection', method: 'GET', url: route.request().url(), injectedStatus: 404, reason: 'Exercise unresolved lookup after an independently verified committed intake; not a real server absence claim.' });
      await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ error: { code: 'INTAKE_ATTEMPT_NOT_FOUND', message: 'Q3 injected lookup 404: saved outcome not visible to this browser response.' } }) });
    };
    await context.route(url, postHandler);
    try {
      await submit.click();
      const committed = await within(first.promise, 'initial UI POST');
      await check('real initial server response was 201 before response loss', committed.received.status, 201);
      await check('browser created UUID v4 attempt key', uuid4.test(committed.sent.key || ''), true);
      await check('initial actual JSON equals UI input', committed.sent.body, body);
      const saved = committed.received.body;
      assert.match(saved?.id || '', /^INT-[0-9A-F]{8}$/);
      await form.getByRole('button', { name: '접수 저장 여부 확인', exact: true }).waitFor();
      await checkUncertainForm(form, body, check, 'after lost 201 response');
      await check('no automatic resubmit after response loss', posts.length, 1);
      await check('retry unavailable before result lookup', await form.getByRole('button', { name: '같은 내용으로 접수 확인·재시도', exact: true }).count(), 0);
      await check('one initial history entry', saved.history?.map(item => item.action), ['text_intake']);
      const afterCommit = await list(request, check, 'after committed lost response');
      await check('server already contains exactly one added intake', ids(afterCommit), [...ids(before), saved.id].sort());
      await check('actual stored intake equals real 201 response', await storedCase(request, check, saved.id, 'committed case'), saved);
      const attemptPath = `/api/intake-attempts/${committed.sent.key}`;
      const actualLookup = await request('GET', attemptPath, undefined, OWNER);
      await check('independent actual lookup sees committed intake', actualLookup.status, 200);
      await check('independent actual lookup returns original case', actualLookup.body, saved);
      lookupUrl = `${base}${attemptPath}`;
      await context.route(lookupUrl, lookupHandler);
      await form.getByRole('button', { name: '접수 저장 여부 확인', exact: true }).click();
      await form.getByRole('alert').filter({ hasText: '첫 요청이 처리 중일 수 있어 입력을 유지합니다' }).waitFor();
      const retryButton = form.getByRole('button', { name: '같은 내용으로 접수 확인·재시도', exact: true });
      await retryButton.waitFor();
      await check('exact attempt lookup received one declared 404 fault', lookupFaults, 1);
      await checkUncertainForm(form, body, check, 'after injected lookup 404');
      await check('404 does not itself submit another intake', posts.length, 1);
      await screenshot('Q3-03-unresolved-404-keeps-input');
      await context.unroute(lookupUrl, lookupHandler); lookupUrl = undefined;
      await retryButton.click();
      const repeated = await within(retry.promise, 'same-content UI retry');
      await check('UI retry uses identical actual key', repeated.sent.key, committed.sent.key);
      await check('UI retry uses identical actual JSON', repeated.sent.body, committed.sent.body);
      await check('UI retry preserves exact serialized body', repeated.sent.rawBody, committed.sent.rawBody);
      await check('real replayed intake HTTP', repeated.received.status, 201);
      await check('retry returns original case without revision/history mutation', repeated.received.body, saved);
      await page.locator('.receipt').filter({ hasText: saved.id }).waitFor();
      const after = await list(request, check, 'after UI retry');
      await check('final new intake count is exactly one', after.length - before.length, 1);
      await check('final case IDs contain only the one new intake', ids(after), [...ids(before), saved.id].sort());
      await check('all original cases unchanged', byId(after.filter(item => item.id !== saved.id)), byId(before));
      await check('original created case fully unchanged after retry', await storedCase(request, check, saved.id, 'retried case'), saved);
      await check('exactly two actual UI POSTs', posts.length, 2);
      await check('successful result unlocks and clears inquiry text', await form.getByLabel('상세 내용', { exact: true }).inputValue(), '');
      await screenshot('Q3-03-single-created-intake-after-retry');
      return { scope: 'real UI POST201 then only response aborted; explicit lookup404 injection; same-key same-body UI retry', caseId: saved.id, key: committed.sent.key, actualPostStatuses: [committed.received.status, repeated.received.status], addedCases: 1, originalRevision: saved.revision, historyEntries: saved.history.length, injectedLookup404: lookupFaults };
    } finally {
      await context.unroute(url, postHandler);
      if (lookupUrl) await context.unroute(lookupUrl, lookupHandler);
    }
  });

  await h.axis('Q3-04', async ({ page, base, check, request, nav, openCase, screenshot, record }) => {
    const before = await list(request, check, 'before conflict setup');
    const { body, submit } = await prepareForm(page, nav, openCase, 'Q3-04');
    const url = `${base}/api/intake`;
    const responsePromise = page.waitForResponse(response => response.url() === url && response.request().method() === 'POST');
    await submit.click();
    const response = await responsePromise, sent = capture(response.request()), saved = await response.json();
    await check('ordinary UI intake setup real HTTP', response.status(), 201);
    await check('ordinary UI attempt uses UUID v4', uuid4.test(sent.key || ''), true);
    await check('ordinary actual UI payload', sent.body, body);
    await page.locator('.receipt').filter({ hasText: saved.id }).waitFor();
    const afterCreate = await list(request, check, 'after conflict setup');
    await check('setup adds one original intake', ids(afterCreate), [...ids(before), saved.id].sort());
    const changed = { ...sent.body, text: `${sent.body.text}\nQ3-04 changed payload must not overwrite the original intake.` };
    const conflict = await request('POST', '/api/intake', changed, { ...OWNER, 'X-Idempotency-Key': sent.key });
    await record({ kind: 'actual-http-counterexample', scope: 'public API with key observed in actual UI request; no disabled UI or server ledger manipulation', originalRequest: sent, attemptedRequest: { key: sent.key, body: changed }, received: conflict });
    await check('same key changed body real conflict HTTP', conflict.status, 409);
    await check('conflict is idempotency-specific', conflict.body?.error?.code ?? conflict.body?.code, 'IDEMPOTENCY_CONFLICT');
    const latest = await storedCase(request, check, saved.id, 'after conflicting body');
    await check('conflict preserves original source text', latest.sourceText, saved.sourceText);
    await check('conflict preserves original revision', latest.revision, saved.revision);
    await check('conflict preserves original history', latest.history, saved.history);
    await check('conflict preserves entire original case', latest, saved);
    const lookup = await request('GET', `/api/intake-attempts/${sent.key}`, undefined, OWNER);
    await check('original attempt remains queryable', lookup.status, 200);
    await check('attempt still resolves to unchanged original intake', lookup.body, saved);
    await check('409 preserves full list and count', byId(await list(request, check, 'after conflict')), byId(afterCreate));
    await screenshot('Q3-04-original-ui-receipt-after-api-conflict');
    return { scope: 'ordinary real UI creation followed by real public HTTP same-key/different-body rejection', originalCaseId: saved.id, actualConflictStatus: conflict.status, originalRevision: saved.revision, originalHistoryEntries: saved.history.length, addedCases: 1, conflictShownInUI: false };
  });
}
