# N03-M4: reviewed full animation gate

2026-09-21 / pc3, LAPTOP-U2AL73UH, mcjun86-oss. Assignment: issue #9 comment 5761425934. Intake HEAD c7fd1c0; scene baseline 33fa0e4.

## Outcome and operator flow

pc1 can render the reviewed synthetic 12-second scene with an explicit receipt and its independently supplied SHA-256. This grants a candidate render path, not final visual or product acceptance. pc1 reviews the new code and creates the actual receipt; PC3 creates only clearly artificial test fixtures. Existing baseline, representatives and short defaults remain unchanged.

Run the generator with the reviewed animation settings, `--threads 2`, `--animation-review <receipt.json>` and `--animation-review-sha256 <expected digest>`. Validation reads the receipt, current generator/dependencies, layout, fixture, three reviewed PNGs and reviewed 72-frame report before creating output. After build, actual runtime settings and fixed camera are checked before rendering. Input hashes and readback are checked again immediately before the first render.

## Contract

The receipt is strict `pc3-animation-review-v1` JSON. Settings pin CCTV, 1920×1080, EEVEE, 96 samples, 4 shadow rays, contrast_material_v1, staging_v1, 2 threads, 24 fps and 288 frames. All file descriptors pin bytes and SHA-256 under receipt-relative paths. Links, escapes, duplicate paths/files and missing or changed files fail closed. A caller-supplied digest is an operator trust boundary; it does not cryptographically prove issuer identity or pixel quality.

The geometry, materials, lights, camera construction, movement and projection formulas remain unchanged. A new readback collector observes Blender state; reports distinguish requested threads/digest from actual threads/digest and add fixture bytes/SHA. No Blender, server, browser, install, paid call or real final receipt is run/issued on PC3.

## Counterexamples and ownership

Independent pure-Python tests cover complete artificial receipt; missing/one-sided receipt; hash/file/input/settings changes; missing evidence; traversal/link/duplicate; wrong camera; readback mismatches; output/render boundary ordering; and a disabled-guard mutant. Existing look/environment regression tests retain geometry and motion AST checks.

Root: generator integration and full-render reports. n03_media: gate module. handoff_audit: independent gate tests and mutation. watcher_review: existing CLI and preservation regressions. These are four local execution lanes, not independent physical PCs or human acceptance.
