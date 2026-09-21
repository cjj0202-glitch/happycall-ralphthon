# N03-M6 media packaging handoff

This tool packages a **completed** synthetic full-animation output only after the existing M5 checker accepts its structure and its independently supplied expectations. It does not finish an incomplete render, issue a review receipt, approve visual quality, register a product asset or upload a Release.

## Operator inputs

Keep the original 291-file package unchanged: PNG frames 1 through 288, render-report.json, tracks.json and case-0002-ww3.blend. Freeze the expectation manifest separately from that output, from pc1's reviewed receipt and fixed source/input files, following full-output-handoff.md. Do not derive trusted expectations from the received report or run against the still-growing Blender directory.

Supply an existing FFmpeg executable explicitly. The tool does not download, install or discover a replacement executable. Where supported, an explicitly supplied ffprobe can provide structured metadata; the FFmpeg-only path compares input-stream metadata with separately decoded frame hashes. A success-like stderr message is insufficient. FFmpeg's rounded human-readable Duration field is not the exact timing authority.

The output must be a new directory outside the package and expectation inputs. Existing destinations and partial outputs are refused. Use a different new output path after a failed attempt; never treat the partial MP4 or tracks file as a complete result. The success candidate report is published only after all packaging checks. A failed or interrupted output is never accepted based on a single report file or on whether cleanup succeeded.

## Reproduction

From the repository root, use the completed pc1 package and its separately frozen manifest. These example data paths must be replaced with the actual independently reviewed inputs; the CLI never builds expectations from the report.

```powershell
python -B scripts/media_pc3/package_full_animation_media.py --package D:\hwana\Work\completed-full-render --expectations D:\hwana\Work\full-render-expectations.json --output D:\hwana\Work\new-full-media-candidate --ffmpeg D:\hwana\Work\happycall-ralphthon\.local\media-pc3-deps\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe --timeout 600
```

`--ffprobe` is optional and must identify an existing executable if supplied. `--timeout` applies to each media subprocess and must be an integer from 1 to 3600 seconds. CLI exit 0 means `valid: true` / `PASS_WITH_PENDING`; exit 1 means rejection. The Python entry point is `package_full_animation(package_dir, expectations_path, output_dir, ffmpeg_path, ffprobe_path=None, *, timeout=600)`.

A successful new directory contains exactly four candidate files:

- `sorter-demo.mp4`: validated final H.264 video.
- `sorter-demo.tracks.json`: the unchanged raw tracks bytes.
- `sorter-demo.tracks.descriptor.json`: exactly five binding fields.
- `candidate-report.json`: validation observations and provenance, written last.

Failure can retain `sorter-demo.partial.mp4` or diagnostic media plus a `failure.json`; those files are not a successful candidate. The correction does not delete markers on failure. Descriptor, staged-report and diagnostic files may remain; they are not evidence of success. A failure diagnostic is best effort and only written to the same owned directory identity. No permission changes or forced unlocking are attempted. It does not replace or clean an existing destination.

The independent suite uses artificial 291-file inputs and mocked media subprocess results:

```powershell
python -B -m unittest discover -s scripts/media_pc3 -p test_full_animation_media.py -v
```

Those unit tests do not invoke an actual encoder or authenticate Blender. Real installed-FFmpeg integration is reported separately in `full-media-checks.json`, with the exact command and output-log digests. Its flat artificial PNGs are functional test material, not the completed pc1 scene or visual acceptance.

## Media and provenance boundaries

The encoded video uses frames 1..288 at 24fps, H.264/yuv420p, 1920×1080 and faststart. No crop, pad, time offset or retiming is authorized. Full decoded-frame timing must cover 12 seconds, with the final frame beginning at 287/24 seconds. Raw tracks are copied without JSON reserialization or coordinate transformation.

The encoder explicitly sets display aspect 16:9 so input PNGs without aspect metadata become a square-pixel output. Both Input-stream metadata and decoded framehash still require SAR 1:1. The parser was exercised against the existing FFmpeg 7.1 build; other builds with different text metadata formatting can fail closed and require a separately tested parser update. ffprobe is optional but does not bypass the mandatory Input/framehash/container checks.

The track descriptor contains exactly five fields: schemaVersion, url, bytes, sha256 and videoSha256. Fixed values are oneflow-cctv-tracks-v1 and /demo/sorter-demo.tracks.json. The copy's actual bytes/SHA and final MP4's actual SHA fill the remaining fields. Independent expectation/source/receipt provenance is recorded separately; no fourth top-level product manifest asset is created.

The original M5 result's pending fields describe its structural-check boundary. Successful decoding here establishes only that this output video decoded with the observed format and timeline. It does not authenticate the renderer, re-open absent source/receipt files, perform a final Blender scene inspection or establish physical contact, visibility, lack of flicker or correspondence to a real incident. Business tote remains null and the scene remains explanatory synthetic material.

pc1 owns the actual finished-render intake, visual checks, final two WAV files plus MP4 plus tracks Release, product manifest, new build and UI playback/seek acceptance. No actual completed pc1 288-frame bundle has been provided to this M6 implementation yet. TEST roundtrip and whole-N03 acceptance remain separate.

## Review correction and required consumer check

The review of submission `3a223f160941212d4d8608a53806563ec2ef9318` found two independently reproducible gaps despite normal tests passing: rotation metadata did not affect acceptance, and a late validation failure plus injected deletion denial left contradictory success and failure markers. The original normal results and counterexamples are retained separately. pc1's reported 20/20 suite is an external observation, not pc3's new measurement.

The corrected publication contract uses `candidate-report.staged.json` while checks are still running. Input bytes, output identity/inventory and final hashes must pass before the final atomic publication of `candidate-report.json`. The publication operation is the final fallible step; there is no later validation that changes published success into a returned failure. Interrupted staged reports and leftover descriptors do not complete a bundle.

Consumers must call `validate_candidate(directory)` from `scripts/media_pc3/package_full_animation_media.py` when taking delivery. Require `valid is True` and `status == "PASS_WITH_PENDING"`; any other result rejects intake. This reads the complete four-file inventory, checks actual asset hashes and the exact five-field descriptor binding, and rejects failure/staged/partial/unknown files. Reading `candidate-report.json` alone is never the intake contract. The helper is a local integrity check and does not authenticate the issuer or independently replay the encoder. The same check is available without an encoder via CLI (exit 0 for a complete pending-review candidate, exit 1 for rejection):

```powershell
python -B scripts/media_pc3/package_full_animation_media.py --check-candidate D:\hwana\Work\new-full-media-candidate
```

Movie and track display matrices must be identity and displayed dimensions must remain 1920x1080. Explicit rotation/transform information must be understood and identity; unknown or non-identity transformations are rejected. Existing pixel-aspect, format, full-frame timeline and byte-identical tracks requirements remain. Metadata that is absent is not itself proof of identity; mandatory MP4 matrix inspection supplies that check.

The last checks and atomic publication have a finite observation boundary. External changes after the last observation cannot be permanently prevented by this script; consumers must validate again at intake and retain their own file-control policy. This does not promise protection against arbitrary simultaneous writers, forged reports or later changes. Failed outputs are diagnosed and abandoned, never reused.

This correction uses artificial completed 291-file fixtures with mock subprocesses for the full suite. New actual-tool execution is restricted to three artificial 64x64 PNGs. The preserved earlier real 1080p video, input metadata and decoded-frame logs are compared read-only against new guards; this is not another full-package encode or actual pc1 scene review. Detailed measured results are in `full-media-checks.json` under `reviewCorrection`.

### Measured review correction results

The frozen original source reproduced all nine expected observations in 14.511 seconds: three incorrectly accepted rotation examples, three normal controls, normal packaging, a late-failure/deletion-permitted control and the late-failure/deletion-denied contradiction. These are defect reproduction observations, not nine successful product checks. No real media process or Windows file lock was used.

The final packager is 40,523 bytes, SHA256 `cad81122ffb8225c35e58d7ca8b6327701e504e8ddbd8c6dd7d5b667d12b9396`; the final independent test file is 41,324 bytes, SHA256 `672ad99b52c06df95a53ee1b051a9d3e0c9c0e2c2c6b620fa031fcdb94b8f398`. One complete final-source suite passed 30/30 methods with 118 distinct negative cases, three killed guard mutants, no failures/errors/skips, in 272.266 seconds. The original decode guard, identity-matrix guard and consumer-inventory guard mutants were killed; the consumer mutant disables both initial and final inventory conditions and is counted as one mutant, not two. Source and test bytes were identical before and after execution. The raw unittest log says OK and the complete result JSON was observed. The tester did not retain the original command session handle, so its process exit code is uncollected, not inferred.

The compound fault reaches the staged report's final validation, returns FAIL, leaves no public candidate report and is rejected by the consumer. An unlink PermissionError injection remains configured, but the corrected code makes zero unlink attempts: failure safety no longer depends on deleting success markers. This is not a reproduction of an actual Windows file lock.

Independent pure parser/matrix checks passed 35/35. A read-only comparison of preserved genuine FFmpeg 1080p/288 outputs, saved Input/framehash logs and current consumer checks passed six observations; no new full-size encoding was performed. The fresh permitted tiny PNG sample used one actual encode and one EOF decode of three 64x64 frames at 24fps, 0.125 seconds. Consumer CLI checks separately accepted the preserved genuine bundle with exit 0 and rejected the original contradictory-marker directory with exit 1. These denominators overlap in purpose and are not added into a single test total.

All 25 preexisting media files remained byte-identical. Only the assigned two scripts and three full-media reports changed. No actual pc1 completed render was read or altered, and no renderer/server/browser, installation, Release, UI, manifest, deployment or permission change was performed. Whole N03 acceptance, TEST, visual review and actual-scene/media acceptance remain pending. Full commands, hashes, negative cases, raw-log references and the preserved original results are in `full-media-checks.json` under `reviewCorrection`.

## Original submission validation history

The first mocked-process suite passed 16 methods with 63 distinct negative cases and killed one removed-full-decode-guard mutant. Independent review then reproduced three additional publication-boundary failures: altered final video could still be accepted, replacement output-directory identity could still be accepted, and failure diagnostics could be written into that replacement directory. Rechecking identity/inventory/final hashes and restricting diagnostic writes fixed them. The expanded full suite passed 19/19 methods, 67 distinct negative cases and the same 1/1 guard mutant in 215.797 seconds, with no skips/errors. This full suite also separately altered the final tracks copy.

That full suite ran against the publication-fix version, SHA256 `86726979fb2b711a1abae4c097135ac466f66cf432d810c986f74b0033727c85`. The first real FFmpeg run then failed the strict SAR check despite successful encoder/decoder exits and 288 decoded frames: the PNGs lacked aspect metadata. Its 19.359-second failure and original logs remain preserved.

The final source differs only by the encoder's `-aspect 16:9` option, SHA256 `b4185ee1438ad4f98570750f35f8927aa67cf0eb1993846dd0ca3cc2f5eead45`. The affected normal/argv/SAR tests passed 3/3 in 24.203 seconds, including two new SAR rejection cases. These overlap the full-suite methods and are not reported as 22 independent tests. The full 19-method suite was not repeated after this single encoder option change.

The final real FFmpeg integration passed all 10 recorded checks in 16.406 seconds. One actual encoding and one actual EOF decode produced H.264/yuv420p, 1920×1080, square pixels, 24fps, 288 frames and exactly 12 seconds with faststart. The 291 artificial input files and external expectations were unchanged. The raw tracks copy was byte-identical and its exact five-field descriptor matched the final output hashes. The artificial MP4 was 26,181 bytes, SHA256 `6e9f3614dece4885498d6de1d1d06525f62a1794d6b3a0a41b2ff78efda24c47`.

`full-media-checks.json` contains commands, denominators, source/tool hashes, local raw-log references and the separate failed/corrected results. Source hashes describe the working bytes tested; Git line-ending normalization may change a checkout's byte hashes. All 25 preexisting media files remain byte-identical. No original PNG/Blend/video or raw session log is committed. This is a functional codec/packager check on flat artificial PNGs; actual pc1 scene/media acceptance is still pending.
