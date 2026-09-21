# N03-M5: full animation output intake

2026-09-21 / pc3, LAPTOP-U2AL73UH, mcjun86-oss. Assignment: issue #9 comment 5761966922; contract read at main c768d9231e73e6806fe8320cc4826e05c9b24c53. Baseline generator a39cd664758575a81e1fcce437db245f60fc2c1b.

## Outcome and operator flow

Before connecting a synthetic 12-second CCTV candidate to the product, pc1 can detect missing/changed/wrong-version files and a mismatched coordinate timeline. pc1 supplies the completed animation directory and a separately frozen expectation manifest. The checker reads them and prints JSON; it does not render, write inputs, encode video, generate approval receipts, or register media.

The flat output contract contains exactly 291 files: frame-0001.png through frame-0288.png, render-report.json, tracks.json and case-0002-ww3.blend. Expectations originate outside that directory and must be fixed independently of its report. They bind the generator, five source dependencies, layout, fixture, receipt and reviewed settings. The report cannot provide its own trusted expectations.

## Contract and proof boundary

Validate actual PNG names, bytes/SHA, chunk structure/CRC and 1920×1080 dimensions; report frame order and elapsed time `(frame-1)/24`; 288 coordinate rows, event/identity, 24fps, resolution and normalized boxes; actual tracks/blend digests; report source/input/receipt metadata and EEVEE96/shadow4/FIXED2/fixed-camera readback. Reuse safe read-only primitives without changing the old 720p checker or generator.

Source, layout, fixture and receipt files are not copied into the generator output. Comparing their report descriptors with independent expectations is not rehashing those absent files or proving execution identity. The embedded sceneReadback/threads values were collected before the first render; runtimeSamples is read again when the report is written. Consistency is checkable, but a new post-completion Blender inspection remains pc1's separate responsibility. PNG structure is not pixel decoding, visual quality, MP4 validity or physical/causal evidence.

## Independent work and counterexamples

Root owns design, handoff and evidence integration. n03_media owns new verify_full_animation.py; handoff_audit owns new test_full_animation_package.py; watcher_review independently audits existing schemas and new checks without changing product code. These are local parallel tasks, not four PCs or human reviewers.

Artificial positive input must pass; missing/duplicate/tampered frame, wrong resolution, old 72-frame report, wrong expected source/input digest, missing/out-of-range tracks, path/link and inconsistent runtime values must fail. An actual disabled-guard mutant must fail an independent test. Preserve all 23 preexisting media scripts byte-for-byte; only the two new scripts and full-output reports are in scope. No actual full output or real approval expectation manifest is fabricated.
