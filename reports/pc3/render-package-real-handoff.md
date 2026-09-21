# N03-M3 actual 72-frame render intake

2026-09-21 KST. PC3: LAPTOP-U2AL73UH / mcjun86-oss.
Assignment: [pc1 issue 9 comment 5761144166](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/9#issuecomment-5761144166).
Generator source: `33fa0e4edeb88c0d4ad5e9cc0194ffc7e96cebcd`.
Checker: `9be72090021c550c6e27746469f926baf57fea2e`.
Branch: `work/pc3-n03-wms-scenes`. Result commit is the commit carrying this report.

The actual received package passes the existing checker with **PASS_WITH_PENDING**:
75 inputs, 72 rendered PNGs, all 288 coordinate rows and no checker failures.
The received MP4 also passed a separate full software decode on PC3. This is
technical intake evidence, not final image quality, product registration or
acceptance of the full N03 task.

## Release and original-byte inventory

[Candidate Release](https://github.com/cjj0202-glitch/happycall-ralphthon/releases/tag/wms-short-review-20260921-33fa0e4).
All three uploaded server digests and all three downloaded file sizes/SHA256
matched pc1's separately supplied values:

| File | Bytes | SHA256 |
|---|---:|---|
| wms-short-33fa0e4-review.zip | 82333801 | 10fa9981105eaecfe07a5c715d19c3e7bd932f8aa4b8bb375f93447f73f80891 |
| intake-expected.json | 2067 | c7066902302d770290bdb28a79cb4ebac2428c3963428ecb66c2236ddbd8e81f |
| case-0002-ww3-short-review.mp4 | 544733 | 21ac21351803125334deba303fd249909774aba98058bc787e38121058f70ccf |

The Release target is `181aa4070109b7024cd4aa3756502a55615c3844`; it is not
substituted for the independently pinned generator commit 33fa.

Before extraction, every ZIP path and case-folded name was checked. No absolute,
parent, backslash, drive/stream, Windows reserved-device, duplicate, encrypted,
link or nonregular entry was accepted. All 121 entry CRCs and bytes were checked.
The unversioned `package-files.json` contains 120 descriptors and excludes only
itself; the pinned ZIP digest covers that manifest too. **120/120** declared
bytes/SHA matched, and **121/121** extracted file bytes/SHA matched the archive.
Uncompressed size is 85,483,552 bytes. The independent audit found no defects.

File groups: 13 root files, 2 inputs, 30 review-video files and 76 short files.
`short/` contains 72 PNGs (frames 73 through 144), render-report, tracks, blend,
and the additional `independent-scene-readback.json`.

The strict checker copy contains only the first 75 required generator files.
All **75/75** copied files match their preserved raw counterparts byte for byte.
The readback remains at its original raw path and is reviewed separately; it is
not silently ignored or deleted. The other 46 raw files, including the manifest,
input files and supporting reports, were all byte verified and remain preserved.
No script received in the ZIP was executed.

## Independent expectations and actual checker result

`render-package-real-expectations.json` changes exactly two keys from the
Git-pinned 9be expectation: `mode=short` and the separately measured fixture
descriptor, **23,430 bytes / 79c3b01aed139352b5cc0a695f2829e76f78eabb61d7cfd6b8055db32f61a73b**.
The fixture bytes match the raw input, pc1's fixed SHA and source-intake evidence.
The previous local fixture has a different digest and was not substituted.

The generator and four source dependencies were compared against the actual
33fa Git blob bytes and the external source-intake descriptors: **5/5 match**.
The layout remains 1,772 bytes / c6aece6692c6b78beb85d4f1167868f2bd095b3ab8366e837466715b82bd6cb6.
The tracks were separately compared to pc1's fixed SHA
9fb424be0fd212bbf3faa057097bec56c63a89e4b8ae08c524e5fd76b80fd44b,
not just the received report's own declaration. No expected values were derived
from that render report.

The original 9be checker ran once on the real strict copy: exit 0,
`valid=true`, **PASS_WITH_PENDING**, failures 0, input digests 75, images 72.
The checker was not modified, and its SHA is still
36b4e2f3de8f0517da6cb26719e346e0fbfec221f5d1b673e494a73c31af30cc.

Checked identity remains CASE-0002 / W-W3 / SYN-CAM-02,
2026-09-18T02:33:00+09:00, CH-02 / D-02, businessToteId=null and
occlusionTested=false. Resolution is 1280 by 720, 24 fps. The 288 coordinate
rows cover the 12-second source. Rendered frames 73-144 cover source elapsed
**[3,6)**; the short MP4 covers **[0,3)**, requiring a +3-second source offset.
PC3 did not register 288 coordinates directly against that 3-second clip.

## Separate video and runtime evidence

An already installed FFmpeg 7.1 executable decoded the entire downloaded MP4
to a null output without a browser, server, installation or re-encoding.
**14/14** technical checks passed, exit 0, 1.241 seconds:
H.264 High, yuv420p, 1280x720, 24 fps, exactly 72 decoded frames, container
3.0 seconds, decoded first PTS 0 and last PTS 2.958333, no input audio stream.
The independent video audit preserves the command, executable SHA and every
frame timestamp. Input bytes remained unchanged.

The checker itself does not decode video; its `VIDEO_DECODE_NOT_RUN` field
remains true to its scope. The separate decoder result does not rewrite that
field or grant visual acceptance. The PNG inputs were structurally checked,
not independently decoded for image quality on this card.

The received pc1 process record reports exit 0 and 896.578 seconds for the
short render. Its independent Blender readback reports Blender 4.5.14 LTS,
EEVEE, FIXED 2 threads, effective samples 96, shadow rays 4, 316 evaluated
meshes (268 core plus 48 staging parts). PC3 checked the files and their
consistency; PC3 did not run Blender or regenerate that readback.
The fixture/thread gaps in the 33fa generator report remain PENDING while
these separate input/process/readback measurements are explicitly identified
as pc1 evidence. The **24/24** external-record comparisons matched. Prepared
scene artifacts were not supplied, so prepare/short equivalence remains a pc1
assertion supported by recorded hashes, not a local Blender replay. Earlier
`videoEncoded=false` reports describe the PNG stage; the later candidate and
independent decode cover the MP4. See `render-package-real-runtime.json`.

## Failure, recovery and preservation

The first local intake wrapper failed **after verified extraction and before
running the checker**, with `KeyError: 'dependencies'`. It incorrectly named
the existing expectation field `sourceDependencies`. This was a PC3 orchestration
error, not a defect in the received render or the original checker.

The first script was preserved. The wrapper field name was corrected, and a
resume path first revalidated the entire same ZIP and raw folder without
rewriting either. It then created the fresh strict copy and expected file.
The same pinned inputs subsequently passed the unchanged checker. No contract
was relaxed and no input was repaired or replaced to obtain a pass.
The publication byte check detected CRLF-to-LF conversion in six report copies.
Only the report copies were normalized to Git-required LF, and their original
local hashes remain recorded. JSON values and Python logic were unchanged;
no downloaded, extracted or checker input was normalized.

After inspection and decoding, **199/199** file byte comparisons passed:
3 downloaded assets, 121 raw files and 75 strict copies. Original downloads'
mtimes stayed unchanged. Independent archive inspection also confirmed raw
file identity, size and mtime stayed unchanged. No raw/strict files were missing
or added. Failure and successful-wrapper hashes are in the structured checks.

## Reproduction and evidence

Local preserved root: `D:\hwana\Work\happycall-ralphthon\.local\pc3-real-short-intake`.
Original assets are under `download/`; unmodified extraction is under `raw/`;
checker-only copies are under `strict-package/`. Nothing in these directories
is a Git binary asset.

For a fresh intake, download the three named assets into the above `download/`
directory before running `python -B reports/pc3/render-package-real-intake.py`.
The intake script refuses preexisting raw/strict outputs by default, verifies
all pinned bytes before extraction and does not execute archived source files.
Its `--reuse-verified-raw` recovery option only reads and revalidates an existing
raw extraction and still requires new expected/strict/evidence outputs. Do not
use it to overwrite this completed intake. For a separate clean reproduction,
use a fresh checkout's `.local/pc3-real-short-intake` directory.

To inspect the preserved strict copy with a new output filename:

```powershell
python -B scripts/media_pc3/verify_render_package.py --package .local/pc3-real-short-intake/strict-package --expectations reports/pc3/render-package-real-expectations.json --output .local/pc3-real-short-intake/checker-replay-new.json
```

Committed evidence:

- `render-package-real-checks.json`: pinned assets, expectations, source checks,
  exact counts, input preservation and failure/recovery.
- `render-package-real-checker.json`: first real checker output, with report-copy
  line endings normalized to LF for Git; the original local bytes are preserved.
- `render-package-real-archive.json`: independent 121-file path/CRC/hash audit.
- `render-package-real-video.json`: independent 72-frame decode and exact command.
- `render-package-real-runtime.json`: external evidence comparison, not a local render.
- `render-package-real-failure.json`, `render-package-real-intake.py`: explicit
  orchestration failure and successful intake procedure.

All three specialist lanes and root ran on this same PC. Their separate checks
are not four physical PCs, human review or TEST roundtrip completion. No product,
shared manifest, generator, existing checker, deployment or central task record
was changed. This evidence supports reproducible delegation and validation; it
makes no competition-score claim.

## Still pending

The six checker pending items remain: fixture runtime binding, thread runtime
readback, PNG pixel decode, checker video decode, visual review and authenticity.
Separate pc1 runtime evidence and PC3 video decoding are recorded above without
silently promoting those fields. Full 288-frame production, pixel/motion quality,
occlusion/contact/flicker acceptance, business attribution, product registration,
TEST roundtrip and final N03 acceptance remain incomplete. pc1 owns further
acceptance and instructions; this issue remains open.
