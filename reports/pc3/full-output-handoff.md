# N03-M5: full output checker handoff

This checker prepares technical intake of a completed 1080p, 24fps, 288-frame synthetic animation. PC3 tests artificial fixtures only. The real full render remains pc1's single existing process; no completed real bundle, pixel decode, MP4 or product acceptance is claimed here.

## Input contract and execution

Use the completed, unchanged animation output directory, containing exactly:

```text
render-report.json
tracks.json
case-0002-ww3.blend
frame-0001.png ... frame-0288.png
```

Keep logs, independent runtime sidecars, receipt/source bundles, MP4s and the expectation manifest outside this strict 291-file directory. Preserve originals; if pc1 needs a separate intake directory, make verified byte-identical copies rather than editing files or changing the running render directory. Do not run this check on the still-growing output and interpret a missing-file failure as a completed render defect.

```powershell
python -B scripts/media_pc3/verify_full_animation.py --package '<PC1 completed animation directory>' --expectations '<PC1 independently frozen expected manifest outside the package>'
python -B -m unittest discover -s scripts/media_pc3 -p test_full_animation_package.py -v
```

The checker only reads and prints JSON to stdout. Exit 0 means its structural/hash checks passed with explicit remaining checks; exit 1 means validation failed. It does not write a report back into the inputs, render, encode, contact a service, or approve a product asset. The Python API is `verify_full_animation(package_path, expected_dict)`; API callers are responsible for supplying independent trusted expectations, while the CLI enforces a separate expectation file outside the package.

## Independent expectation manifest

pc1 freezes this file from the previously reviewed receipt and the actual pinned source/input files, before trusting the output report. **Do not copy expected hashes or settings from the output under test.** A descriptor is `{ "name": "filename", "bytes": <measured positive integer>, "sha256": "<measured lower-case 64 hex SHA>" }`. Current source includes build_scene.py plus scene_contract.py, look_presets.py, shadow_settings.py, environment_detail.py and full_render_gate.py.

Schema example below deliberately contains invalid placeholders; PC3 has not issued a real manifest or fabricated actual output hashes:

```json
{
  "schemaVersion": "pc3-full-animation-expectations-v1",
  "sourceCommit": "PC1-PINNED-40-HEX-SOURCE-COMMIT",
  "mode": "animation",
  "generator": "MEASURED build_scene.py DESCRIPTOR",
  "sourceDependencies": ["MEASURED DESCRIPTORS FOR ALL FIVE DEPENDENCIES"],
  "layout": "MEASURED scene-layout-v1.json DESCRIPTOR",
  "fixture": "MEASURED cases.json DESCRIPTOR",
  "receipt": "MEASURED ORIGINAL PC1 RECEIPT DESCRIPTOR",
  "settings": {
    "camera": "cctv", "resolution": [1920, 1080], "engine": "eevee",
    "samples": 96, "shadowRays": 4, "look": "contrast_material_v1",
    "environmentDetail": "staging_v1", "threads": 2, "fps": 24, "frames": 288
  },
  "look": "PINNED FULL contrast_material_v1 LOOK OBJECT",
  "environmentDetail": "PINNED FULL staging_v1 48-OBJECT DESCRIPTION",
  "reviewId": "ID-FROM-PC1-PINNED-RECEIPT",
  "verifiedFiles": ["ALL 12 EXPECTED RECEIPT FILE RECORDS, FROM REVIEWED INPUTS"]
}
```

`look` contains both `name` and `settings`, not just the preset name. It can be taken from `settings_for('contrast_material_v1')` in the independently fixed look_presets.py, wrapped with that name. `environmentDetail` is the complete `environment_specs('staging_v1')` object from the fixed environment_detail.py. Verify those code files' bytes first. These objects must not be obtained from the output report being tested.

Each `verifiedFiles` entry is `{ "role": "...", "path": "receipt-relative/POSIX/path", "bytes": <measured integer>, "sha256": "<measured SHA>" }`. The required roles are generator (1), layout (1), fixture (1), dependency (5), reviewed-representative (3: frames 1/133/288) and reviewed-short-report (1). These are the pre-render review inputs, not the new 288 output PNG descriptors. Reconstruct the records from pc1's independently pinned original receipt/source bundle; the M4 verification return format is documented in full_render_gate.py. Paths, file identities and roles must agree with the pinned receipt and cannot escape its relative namespace.

The manifest's sourceCommit records pc1's supplied provenance. Hash agreement checks consistency with independently supplied expectations; it does not authenticate the sender or prove that the stated commit actually rendered the files.

## Remaining checks

The checker hashes all received PNGs, tracks and blend bytes and verifies their report references. Source/layout/fixture/receipt files are absent from the output directory, so their embedded descriptors are compared with expectations rather than rehashed as if they were present. The embedded receipt result is not rerun or treated as a signature.

The generator collects sceneReadback and threads before the first frame; runtimeSamples is read again when writing the report. Matching these fields checks consistency, not a fresh final Blender inspection. pc1 still performs post-completion scene inspection, pixel decoding, visual/motion/contact/occlusion/flicker checks, MP4 encoding/decoding/seek and matching 12-second tracks, and final product registration. The older 3-second video cannot inherit this 12-second coordinate timeline.

The old 720p checker and all generator/scene/source files remain unchanged. Passing artificial tests does not mean the real 288-frame render has finished or that N03/TEST/product acceptance is complete.

## Measured verification on pc3

At 2026-09-21 23:30 KST, the first complete independent suite ran 18 test methods: **17 passed, 1 skipped, 0 failures, 0 errors**, in 87.593 seconds. Its live counter recorded **129 distinct rejected negative cases**; that is a separate denominator from the 18 test methods. The skipped file-symlink test was blocked by Windows WinError 1314, not counted as a pass. Actual hard-link and junction tests reached and confirmed their respective file safety guards.

The normal artificial package contained 288 flat-colour 1920×1080 PNGs, 288 coordinate rows and 291 total files. API and CLI checks passed with pending review flags; package bytes and the external expectations were preserved. Cases included a missing/duplicate/tampered frame, 720p image, previous 72-frame report, foreign input/dependency hashes, receipt mismatch, missing/out-of-range coordinates, requested-versus-readback conflicts, unsafe paths, strict JSON and a package changing during verification.

An in-memory mutant disabled exactly the PNG byte/SHA guard. Running the independent hash-mismatch test against it produced the expected real assertion failure (`True is not False`): **1 of 1 mutants detected**. The original source was never replaced. During code review, receipt self-path collision was found and corrected before the full suite; its dedicated regression passed. No earlier failing suite is claimed for that review finding.

All 23 preexisting files under scripts/media_pc3 were compared to their pre-M5 byte counts and SHA256 values and remained identical. Only this card's two new Python files and full-output reports change. `full-output-checks.json` records exact source and raw local evidence digests; the raw result/log were captured from the same unittest process. Git may normalize line endings, so recorded working-file hashes are not promised to equal Git blob hashes.

pc1's next step is to supply independently frozen expectations and apply the checker to the completed real bundle. PC3 has not received or tested that completed bundle. The existing pc1 full render was not restarted or duplicated.
