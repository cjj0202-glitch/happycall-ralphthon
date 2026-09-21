# N03-M6 media packaging handoff

This tool packages a **completed** synthetic full-animation output only after the existing M5 checker accepts its structure and its independently supplied expectations. It does not finish an incomplete render, issue a review receipt, approve visual quality, register a product asset or upload a Release.

## Operator inputs

Keep the original 291-file package unchanged: PNG frames 1 through 288, render-report.json, tracks.json and case-0002-ww3.blend. Freeze the expectation manifest separately from that output, from pc1's reviewed receipt and fixed source/input files, following full-output-handoff.md. Do not derive trusted expectations from the received report or run against the still-growing Blender directory.

Supply an existing FFmpeg executable explicitly. The tool does not download, install or discover a replacement executable. Where supported, an explicitly supplied ffprobe can provide structured metadata; the FFmpeg-only path compares input-stream metadata with separately decoded frame hashes. A success-like stderr message is insufficient. FFmpeg's rounded human-readable Duration field is not the exact timing authority.

The output must be a new directory outside the package and expectation inputs. Existing destinations and partial outputs are refused. Use a different new output path after a failed attempt; never treat the partial MP4 or tracks file as a complete result. Encoding, decoding and metadata failures must leave no success candidate report.

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

Failure can retain `sorter-demo.partial.mp4` or diagnostic media plus a `failure.json`; those files are not a successful candidate. The tool removes only success markers created by its own invocation where their filesystem identities remain unchanged. It does not replace or clean an existing destination.

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

## Observed validation and corrections

The first mocked-process suite passed 16 methods with 63 distinct negative cases and killed one removed-full-decode-guard mutant. Independent review then reproduced three additional publication-boundary failures: altered final video could still be accepted, replacement output-directory identity could still be accepted, and failure diagnostics could be written into that replacement directory. Rechecking identity/inventory/final hashes and restricting diagnostic writes fixed them. The expanded full suite passed 19/19 methods, 67 distinct negative cases and the same 1/1 guard mutant in 215.797 seconds, with no skips/errors. This full suite also separately altered the final tracks copy.

That full suite ran against the publication-fix version, SHA256 `86726979fb2b711a1abae4c097135ac466f66cf432d810c986f74b0033727c85`. The first real FFmpeg run then failed the strict SAR check despite successful encoder/decoder exits and 288 decoded frames: the PNGs lacked aspect metadata. Its 19.359-second failure and original logs remain preserved.

The final source differs only by the encoder's `-aspect 16:9` option, SHA256 `b4185ee1438ad4f98570750f35f8927aa67cf0eb1993846dd0ca3cc2f5eead45`. The affected normal/argv/SAR tests passed 3/3 in 24.203 seconds, including two new SAR rejection cases. These overlap the full-suite methods and are not reported as 22 independent tests. The full 19-method suite was not repeated after this single encoder option change.

The final real FFmpeg integration passed all 10 recorded checks in 16.406 seconds. One actual encoding and one actual EOF decode produced H.264/yuv420p, 1920×1080, square pixels, 24fps, 288 frames and exactly 12 seconds with faststart. The 291 artificial input files and external expectations were unchanged. The raw tracks copy was byte-identical and its exact five-field descriptor matched the final output hashes. The artificial MP4 was 26,181 bytes, SHA256 `6e9f3614dece4885498d6de1d1d06525f62a1794d6b3a0a41b2ff78efda24c47`.

`full-media-checks.json` contains commands, denominators, source/tool hashes, local raw-log references and the separate failed/corrected results. Source hashes describe the working bytes tested; Git line-ending normalization may change a checkout's byte hashes. All 25 preexisting media files remain byte-identical. No original PNG/Blend/video or raw session log is committed. This is a functional codec/packager check on flat artificial PNGs; actual pc1 scene/media acceptance is still pending.
