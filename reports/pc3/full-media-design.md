# N03-M6: verified full-frame media packaging

2026-09-22 / pc3, LAPTOP-U2AL73UH, mcjun86-oss. Baseline de2c790a5e739a4aa9cdb2fc481fb10db3e43e29; contract reports/channel/N03-M6-full-media-packaging.md at main faf52a688d0713143d4677b31503746cbb5987cc, issue #9 comment 5762563996.

## User outcome and flow

pc1 can convert a completed, structurally verified synthetic CCTV candidate into an MP4 and byte-identical coordinates on the same 1920×1080, 24fps, 12-second timeline. The operator supplies the completed 291-file package, independently frozen expectations, an existing FFmpeg executable and a new output directory outside the inputs. A valid M5 result precedes any encoding. Generated-in-progress inputs and previous partial outputs are not valid handoffs.

Encoding uses all frames 1 through 288, H.264/yuv420p and faststart, with no crop, padding, timing offset or retiming. Completion requires actual metadata and full-frame decoding checks, followed by an unchanged raw tracks copy and a separate provenance report. Structural and media checks do not grant visual, physical-contact, occlusion or product acceptance.

The 1920×1080 output explicitly declares display aspect 16:9, yielding square pixels without scaling or changing coordinates. The first real-tool run found that PNGs without pixel-aspect metadata otherwise produced an unspecified SAR and were correctly refused by the strict decoder check. The decoder still requires actual SAR 1:1; the implementation does not relax that guard to pass unknown metadata.

## Output and failure boundaries

The tracks descriptor has exactly schemaVersion, url, bytes, sha256 and videoSha256. Its fixed schemaVersion is oneflow-cctv-tracks-v1 and URL is /demo/sorter-demo.tracks.json. Track bytes/hash describe the copy; videoSha256 describes the actual final MP4. Source/receipt/expected information belongs in the separate candidate report, never extra descriptor fields or a fourth manifest asset.

Inputs remain read-only. Refuse overlapping paths, existing output, links and unsafe paths. Invoke explicit argv with shell=False, a timeout and hidden Windows subprocesses. Refuse encoder errors, incomplete output, metadata/decode disagreement and input changes. Do not create a success report after failure or reuse partial files as a completed package.

## Tools and independent validation

Only existing tools may run. PC3 has an imageio-ffmpeg 0.6.0 bundled FFmpeg 7.1 Gyan build; it is a third-party build, not claimed as authenticated by upstream FFmpeg. No ffprobe executable was found in the checked PATH/project/Apps locations. The FFmpeg-only route must therefore combine actual input-stream metadata with independent complete framehash decoding; a success-like stderr phrase alone cannot pass. An explicitly supplied ffprobe may provide structured metadata where available. No downloads or installations are part of this card.

Implementation, independent tests, read-only tool/security audit and integration run as four local roles on pc3, not four PCs. Test expectations include valid artificial inputs, M5 rejection, encoder/decode failure and partial files, wrong frame count/duration/size/codec/pixel format, input changes, output overlap/no-overwrite, and an actually killed guard mutant. Real installed-tool checks on artificial material are distinguished from mocked process tests and from pc1's still-running full render.

## Ownership and remaining work

Only the two new package_full_animation_media.py/test_full_animation_media.py files and full-media reports are changed. Preserve all 25 preexisting media scripts. Do not alter the generator, existing validators, fixture, product manifest, frontend or Release. pc1 retains its single Blender render, actual finished-bundle intake, visual review, final media registration, UI seek verification and deployment. TEST roundtrip remains separate and pending.

## Review correction design — 2026-09-22 01:19 KST

Review assignment: issue #9 comment 5763744576, pc1 main reference 4b18b27e00ffab3106d1d88920e4f18b3de64356; preserve submitted commit 3a223f160941212d4d8608a53806563ec2ef9318. pc1 reports its isolated final-source suite 20/20 PASS in 267.557 seconds. That is external reported evidence, separate from pc3 measurements below and from the additional counterexamples.

The user outcome is unchanged raw tracks aligned with the displayed video, with a consumer able to distinguish a completed candidate from a failed or interrupted output. Two original-version claims are being independently reproduced against a frozen local source copy before repair: accepted rotation/matrix metadata and a late-check failure that leaves a success report when marker deletion is denied. Normal and deletion-permitted controls remain in the evidence.

Coordinate validation will require identity movie/track display matrices and native displayed dimensions in the MP4, reject nonzero/unknown rotation or unsupported transformations in text/structured metadata, and retain existing dimensions/aspect/frame/timeline checks. Missing optional rotation metadata is acceptable only with the mandatory container identity check; malformed or non-identity information is not treated as zero. No tracks are transformed. Existing genuine FFmpeg outputs and saved logs provide a positive regression comparison; any new actual tool use is restricted to the approved tiny artificial PNG sample, not another full render or 288-frame encode.

Publication will stage a non-public report, finish input/output identity and hash checks, and make the success report visible as the final commit point. There must be no validation that can subsequently change a published success into a returned failure. Marker deletion is not part of the corrected failure path. A best-effort failure diagnostic never establishes success. A consumer must verify the complete bundle, absence of failure/staging markers and all asset/descriptor bindings instead of trusting candidate-report.json alone. A failed or interrupted directory is never reused. These checks do not prevent arbitrary modifications after the final observation; consumers revalidate at intake and final pc1 acceptance remains mandatory.

Only package_full_animation_media.py, test_full_animation_media.py and full-media-* reports are editable. Tests use artificial complete 291-file fixtures and mock processes; final full-suite results, relevant guard mutants, compound failure injection and actual-tool observations are recorded separately. No renderer, server, browser, installation, permission change, forced unlocking or actual pc1 input modification is permitted.

Measured review outcome: the frozen original reproduced all nine expected control/counterexample observations. The final source passed one full 30-method suite with 118 negative cases and three killed mutants; independent pure guards passed 35/35. Existing real-output comparisons passed six observations, the permitted new actual sample was only three 64x64 PNGs, and two consumer CLI exit checks matched expectations. Detailed evidence and the uncollected full-suite process exit-code limitation are preserved in full-media-checks.json/reviewCorrection. No whole-N03 or actual-scene acceptance is claimed.
