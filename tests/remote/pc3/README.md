# pc3 WMS scene component checks

This suite bundles the actual `apps/web/components/WmsScene.tsx` and its CSS with the shared design tokens. It uses `data/fixtures/cases.json`; it does not substitute a test implementation of the component. React resolves from `apps/web/node_modules`.

Install the web dependencies with the repository's normal workflow first, then run from this directory:

```text
npm ci
npm test
```

The suite starts one temporary HTTP server bound to `127.0.0.1` on an automatically selected port. It never starts, restarts, or modifies the application's UI/API servers. Requests outside the local harness are blocked, and no paid AI API is used. Media requests are served only from `apps/web/public/demo`.

An existing Chromium, Chrome, or Edge installation is required. Browser download is not part of the test. Set `PC3_CHROMIUM` to an installed executable if automatic discovery does not find one. The authenticated user browser profile is never used.

The registered legacy clip requires the original `apps/web/public/demo/sorter-demo.mp4`. Supply the independently verified release asset before running playback checks. Missing media is a failed prerequisite; it is not silently replaced with another video.

Results, request observations, and screenshots are written under `.local/pc3-tests/<UTC timestamp>/`. These outputs are ignored by Git. Each result records actual source hashes, browser version, fixture IDs, and failed checks. A passing component harness is not full-application integration, remote PC mailbox TEST, actual CCTV verification, or human usability validation.

The browser-only `window.pc3Harness` exposes `render(caseOrId, {rejectLink})`, `state()`, `fixture()`, `inspect(caseData)`, and `validate(caseData, event, media)` to reproducibly inject inputs and observe callback outcomes. It is not included in the production component.

`linked-intake-cases.mjs` additionally creates offline input shaped after `CaseService.intake` without invoking an API: explicit `linkedFixtureId`, copied source WMS/evidence/asOf, newly entered text, and no `media` field. Linked-intake checks cover both source cases, the reviewer's `INT-MAINREVIEW` reproduction, object-key order independence, invalid identity/source/record mutations, callback outcomes, source-change state reset, and refusal to inherit manually attached videos. A targeted pre-fix reproduction is `node run.mjs --only=linked-intake-positive-CASE-0002`; the complete suite remains `npm test`.
