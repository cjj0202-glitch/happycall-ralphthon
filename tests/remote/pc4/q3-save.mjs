// Independent N04-Q3 save/reconciliation axes. Only the parent owns execution.
// All successful replies come from the real isolated API. Fault injection is
// restricted to a lost response after an actual commit, or an unsaved 503.
const CASE = 'CASE-0001';
const CASE_PATH = `/api/cases/${CASE}`;
const SAVED_NOTICE = '서버에 요청한 접수 내용이 저장되어 있음을 확인했습니다.';
const REVIEW_LABEL = '점포·상품·전달 부서를 원문과 대조하고, 접수 정보를 편집·확인했습니다.';

function controls(page) {
  return {
    input: page.locator('#intake-editor .form-grid textarea'),
    save: page.getByRole('button', { name: '접수 내용 저장', exact: true }),
    verify: page.getByRole('button', { name: '저장 여부 확인', exact: true }),
    recovery: page.getByRole('region', { name: '최신 서버 내용과 초안 대조', exact: true }),
    keep: page.getByRole('button', { name: '내 초안 유지 · 다시 확인', exact: true }),
    useServer: page.getByRole('button', { name: '서버 내용 사용', exact: true }),
    reviewed: page.getByRole('checkbox', { name: REVIEW_LABEL, exact: true }),
    savedNotice: page.getByText(SAVED_NOTICE, { exact: true }),
  };
}

function watchUiPatches(page, base) {
  const rows = [];
  const listener = request => {
    if (request.url() === base + CASE_PATH && request.method() === 'PATCH') {
      rows.push({ method: 'PATCH', url: request.url(), body: request.postDataJSON() });
    }
  };
  page.on('request', listener);
  return { rows, close: () => page.off('request', listener) };
}

async function getCase(request, check, label) {
  const result = await request('GET', CASE_PATH);
  await check(`${label}: actual GET status`, result.status, 200);
  await check(`${label}: case identity`, result.body.id, CASE);
  return result.body;
}

async function otherEditor(request, check, current, text, label) {
  const payload = { expectedRevision: current.revision, intake: { request: text } };
  const result = await request('PATCH', CASE_PATH, payload, { 'X-Demo-Role': 'counselor' });
  await check(`${label}: real other-editor PATCH`, result.status, 200);
  await check(`${label}: increment exactly once`, result.body.revision, current.revision + 1);
  await check(`${label}: saved different content`, result.body.intake.request, text);
  return { payload, result: result.body };
}

async function dropCommittedResponse(context, base) {
  const observed = { injected: 0, upstreamStatus: null, upstreamBody: null, sent: null, error: null };
  const target = base + CASE_PATH;
  const handler = async route => {
    if (route.request().method() !== 'PATCH' || observed.injected) return route.fallback();
    observed.injected += 1;
    observed.sent = route.request().postDataJSON();
    try {
      // The server commits the original UI request before its response is lost.
      const response = await route.fetch({ maxRedirects: 0 });
      observed.upstreamStatus = response.status();
      observed.upstreamBody = await response.json();
    } catch (error) {
      observed.error = String(error?.message || error);
    }
    await route.abort('failed');
  };
  await context.route(target, handler);
  return { observed, close: () => context.unroute(target, handler) };
}

async function lostSave({ page, context, base, check, request }, text, before, label) {
  const ui = controls(page);
  await ui.input.fill(text);
  const loss = await dropCommittedResponse(context, base);
  try {
    await ui.save.click();
    await ui.verify.waitFor({ state: 'visible' });
    await check(`${label}: one lost response`, loss.observed.injected, 1);
    await check(`${label}: upstream fetch succeeded`, loss.observed.error, null);
    await check(`${label}: real PATCH committed before abort`, loss.observed.upstreamStatus, 200);
    await check(`${label}: UI used its observed revision`, loss.observed.sent.expectedRevision, before.revision);
    await check(`${label}: committed request`, loss.observed.upstreamBody.intake.request, text);
    await check(`${label}: committed revision`, loss.observed.upstreamBody.revision, before.revision + 1);
    await check(`${label}: draft survives lost response`, await ui.input.inputValue(), text);
    await check(`${label}: blind retry is disabled`, await ui.save.isEnabled(), false);
    const saved = await getCase(request, check, label);
    await check(`${label}: GET confirms upstream commit`, saved, loss.observed.upstreamBody);
    return { saved, sent: loss.observed.sent, upstreamStatus: loss.observed.upstreamStatus };
  } finally {
    await loss.close();
  }
}

async function verifyThroughUi(page, base) {
  const responsePromise = page.waitForResponse(response =>
    response.url() === base + CASE_PATH && response.request().method() === 'GET');
  await controls(page).verify.click();
  const response = await responsePromise;
  return { status: response.status(), body: await response.json() };
}

async function realUiSave(page, base) {
  const responsePromise = page.waitForResponse(response =>
    response.url() === base + CASE_PATH && response.request().method() === 'PATCH');
  await controls(page).save.click();
  const response = await responsePromise;
  return { status: response.status(), body: await response.json(), sent: response.request().postDataJSON() };
}

export async function run(h) {
  await h.axis('Q3-05', async args => {
    const { page, base, check, request, openCase, screenshot, record } = args;
    await openCase(CASE);
    const ui = controls(page);
    await ui.input.waitFor({ state: 'visible' });
    const patches = watchUiPatches(page, base);
    try {
      const baseline = await getCase(request, check, '05 baseline');
      const firstText = 'PC4 Q3-05 응답은 유실됐지만 실제로 저장한 합성 접수입니다.';
      const first = await lostSave(args, firstText, baseline, '05 matching save');
      const verified = await verifyThroughUi(page, base);
      await check('05 UI verification used real GET', verified.status, 200);
      await check('05 UI GET observes exact committed case', verified.body, first.saved);
      await ui.savedNotice.waitFor({ state: 'visible' });
      await check('05 matching GET reports verified save', await ui.savedNotice.isVisible(), true);
      await check('05 matching GET needs no comparison', await ui.recovery.count(), 0);
      await check('05 verified draft remains correct', await ui.input.inputValue(), firstText);
      await check('05 verification does not resend PATCH', patches.rows.length, 1);
      await screenshot('05-committed-response-lost-verified');
      // Let the real toast expire so the second subcase cannot mistake an old
      // success notice for a newly reported result. No browser clock is changed.
      await ui.savedNotice.waitFor({ state: 'hidden', timeout: 10000 });

      const localText = 'PC4 Q3-05 두 번째 저장의 초안: 응답 유실 후 다른 담당자가 변경합니다.';
      const second = await lostSave(args, localText, first.saved, '05 changed-after-commit');
      const thirdText = 'PC4 Q3-05 다른 담당자가 후속으로 확인한 내용이며 자동 덮어쓰면 안 됩니다.';
      const third = await otherEditor(request, check, second.saved, thirdText, '05 other editor');
      const changedGet = await verifyThroughUi(page, base);
      await check('05 later GET is successful but different', changedGet.status, 200);
      await check('05 later GET preserves third-party content', changedGet.body, third.result);
      await ui.recovery.waitFor({ state: 'visible' });
      await check('05 changed GET is not reported as our verified save', await ui.savedNotice.count(), 0);
      await check('05 local draft preserved for comparison', await ui.input.inputValue(), localText);
      const comparison = await ui.recovery.innerText();
      await check('05 comparison includes local request', comparison.includes(localText), true);
      await check('05 comparison includes current server request', comparison.includes(thirdText), true);
      await check('05 changed GET blocks blind retry', await ui.save.isEnabled(), false);
      await check('05 no automatic overwrite during comparison', patches.rows.length, 2);
      await check('05 server unchanged before explicit selection', await getCase(request, check, '05 pre-selection'), third.result);
      await screenshot('05-later-editor-requires-comparison');
      await ui.useServer.click();
      await ui.recovery.waitFor({ state: 'hidden' });
      await check('05 explicit server choice replaces draft', await ui.input.inputValue(), thirdText);
      await check('05 choosing server issues no PATCH', patches.rows.length, 2);
      const final = await getCase(request, check, '05 final');
      await check('05 other-editor save is not overwritten', final, third.result);
      await check('05 synthetic source remains unchanged', final.sourceText, baseline.sourceText);
      await record({ caseId: CASE, firstLostCommit: first, secondLostCommit: second,
        otherEditor: third, verificationGetStatuses: [verified.status, changedGet.status],
        uiPatches: patches.rows, finalRevision: final.revision,
        scope: 'Actual server commits; only returned PATCH responses were deliberately dropped. No success responses are fabricated.' });
      return { lostCommittedResponses: 2, matchingVerified: true, laterChangeRequiresChoice: true, automaticOverwrites: 0 };
    } finally { patches.close(); }
  });

  await h.axis('Q3-06', async ({ page, context, base, check, request, openCase, screenshot, record }) => {
    await openCase(CASE);
    const ui = controls(page);
    const baseline = await getCase(request, check, '06 baseline');
    const localText = 'PC4 Q3-06 서버에 저장되지 않은 초안: 503 뒤 조회 성공과 저장 성공은 다릅니다.';
    await ui.input.fill(localText);
    const patches = watchUiPatches(page, base);
    let injected = 0;
    const handler = async route => {
      if (route.request().method() !== 'PATCH' || injected) return route.fallback();
      injected += 1;
      // Deliberate failure only: do not forward this request to the server.
      await route.fulfill({ status: 503, contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'PC4_UNSAVED_503', message: 'PC4 합성 저장 전 503: 서버 반영 없음' } }) });
    };
    await context.route(base + CASE_PATH, handler);
    try {
      const failed = await realUiSave(page, base);
      await check('06 injected real UI response is 503', failed.status, 503);
      await check('06 failure injected once', injected, 1);
      await ui.verify.waitFor({ state: 'visible' });
      await check('06 uncertain save blocks retry', await ui.save.isEnabled(), false);
      await check('06 unsaved draft survives error', await ui.input.inputValue(), localText);
      await check('06 server unchanged by unsent failed request', await getCase(request, check, '06 after 503'), baseline);
      const verified = await verifyThroughUi(page, base);
      await check('06 UI verification GET succeeds', verified.status, 200);
      await check('06 GET still has the original revision and data', verified.body, baseline);
      await ui.recovery.waitFor({ state: 'visible' });
      await check('06 GET 200 is not false save success', await ui.savedNotice.count(), 0);
      await check('06 retry remains blocked until explicit choice', await ui.save.isEnabled(), false);
      await check('06 request remains in local draft', await ui.input.inputValue(), localText);
      await check('06 no automatic retry PATCH', patches.rows.length, 1);
      await screenshot('06-unsaved-503-get200-is-not-success');
      await ui.keep.click();
      await ui.recovery.waitFor({ state: 'hidden' });
      await check('06 keep preserves unsaved request', await ui.input.inputValue(), localText);
      await check('06 keep clears human confirmation', await ui.reviewed.isChecked(), false);
      await check('06 keep selection itself does not save', await getCase(request, check, '06 final'), baseline);
      await check('06 revision remains original after keep', (await getCase(request, check, '06 revision')).revision, baseline.revision);
      await check('06 still exactly one unsuccessful UI PATCH', patches.rows.length, 1);
      await record({ caseId: CASE, injectedFailure: { status: 503, forwardedToServer: false, count: injected },
        originalRevision: baseline.revision, finalRevision: verified.body.revision,
        verifyGetStatus: verified.status, uiPatches: patches.rows, falseSuccess: false });
      return { unsaved503: true, successfulGetIsNotSaveSuccess: true, revisionUnchanged: true };
    } finally { await context.unroute(base + CASE_PATH, handler); patches.close(); }
  });

  await h.axis('Q3-07', async ({ page, base, check, request, openCase, screenshot, record }) => {
    await openCase(CASE);
    const ui = controls(page);
    const baseline = await getCase(request, check, '07 baseline');
    const localText = 'PC4 Q3-07 보존해야 할 상담원 초안: 대조 후에도 제3자 변경을 덮어쓰지 않습니다.';
    await ui.input.fill(localText);
    await ui.reviewed.check();
    const patches = watchUiPatches(page, base);
    try {
      const second = await otherEditor(request, check, baseline,
        'PC4 Q3-07 첫 번째 다른 담당자의 실제 저장', '07 second editor');
      const firstConflict = await realUiSave(page, base);
      await check('07 first stale UI PATCH gets actual 409', firstConflict.status, 409);
      await check('07 first request retains original revision', firstConflict.sent.expectedRevision, baseline.revision);
      await check('07 first conflict code', firstConflict.body.error?.code, 'STATE_CONFLICT');
      await ui.recovery.waitFor({ state: 'visible' });
      await check('07 first conflict preserves local draft', await ui.input.inputValue(), localText);
      await check('07 first comparison contains latest server', (await ui.recovery.innerText()).includes(second.result.intake.request), true);
      await ui.keep.click();
      await ui.recovery.waitFor({ state: 'hidden' });
      await check('07 keep clears prior confirmation', await ui.reviewed.isChecked(), false);
      await check('07 keep itself does not write', patches.rows.length, 1);
      await check('07 first saved content remains after keep', await getCase(request, check, '07 after keep'), second.result);

      // No UI refresh occurs between keep and this real third-party write. The
      // following UI save must use the revision the user actually compared.
      const third = await otherEditor(request, check, second.result,
        'PC4 Q3-07 keep 직후 제3자가 새로 저장한 내용', '07 third editor after keep');
      const secondConflict = await realUiSave(page, base);
      await check('07 post-keep stale UI PATCH gets actual 409', secondConflict.status, 409);
      await check('07 UI submits compared revision, not unseen newest revision', secondConflict.sent.expectedRevision, second.result.revision);
      await check('07 second conflict code', secondConflict.body.error?.code, 'STATE_CONFLICT');
      await ui.recovery.waitFor({ state: 'visible' });
      await check('07 second conflict preserves exact draft', await ui.input.inputValue(), localText);
      const comparison = await ui.recovery.innerText();
      await check('07 renewed comparison includes local draft', comparison.includes(localText), true);
      await check('07 renewed comparison includes third-party request', comparison.includes(third.result.intake.request), true);
      await check('07 save blocked until renewed choice', await ui.save.isEnabled(), false);
      await check('07 third-party content and revision survive conflict', await getCase(request, check, '07 pre-choice'), third.result);
      await check('07 exactly two real conflicting UI PATCHes', patches.rows.length, 2);
      await screenshot('07-third-editor-409-preserves-draft');
      await ui.useServer.click();
      await ui.recovery.waitFor({ state: 'hidden' });
      await check('07 explicit latest-server choice updates form', await ui.input.inputValue(), third.result.intake.request);
      await check('07 server choice does not automatically PATCH', patches.rows.length, 2);
      const final = await getCase(request, check, '07 final');
      await check('07 no third-party overwrite', final, third.result);
      await check('07 source text preserved across conflicts', final.sourceText, baseline.sourceText);
      await record({ caseId: CASE, baselineRevision: baseline.revision, secondEditor: second,
        thirdEditor: third, firstConflict, secondConflict, uiPatches: patches.rows,
        finalRevision: final.revision, explicitFinalChoice: 'server',
        scope: 'Two real UI stale PATCH requests to the isolated API; no mocked 409 or direct product-state edits.' });
      return { actual409Responses: 2, thirdPartyRevisionPreserved: true, draftPreservedUntilChoice: true };
    } finally { patches.close(); }
  });
}
