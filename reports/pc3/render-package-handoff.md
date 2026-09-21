# N03-M3 intake checker and local review document

2026-09-21, PC3: LAPTOP-U2AL73UH / mcjun86-oss. Assignment:
[issue 9, pc1 comment 5760629024](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/9#issuecomment-5760629024).
Generator baseline: `33fa0e4edeb88c0d4ad5e9cc0194ffc7e96cebcd`.
Branch: `work/pc3-n03-wms-scenes`. Result commit is the commit carrying this report.

The new checker compares a received package against separately pinned source,
input and settings expectations. It rejects mixed, missing or altered files and
coordinates, identifies the failed check, and leaves the package unchanged.
The local HTML document embeds original PNG bytes and shows metadata with
unverified items visible. Existing d67 A/B behavior is preserved.

The implementation is ready for pc1 review. **No actual M3 render package has
been received on PC3, and this is not final media or product acceptance.**

## Changes and fixed inputs

- `scripts/media_pc3/verify_render_package.py`: independent standard-library
  checker, strict external expectations and JSON, source/input descriptors,
  frame inventory, event/camera/clock/null rules, motion and projected bbox,
  settings readback, byte/SHA and PNG chunk/CRC checks. Explicit optional MP4s
  are hashed only. Links, reparse points, hardlinks, directory escapes and
  changed inputs are refused.
- `scripts/media_pc3/test_render_package.py`: independent artificial fixtures,
  wrong inputs, actual Windows link cases and isolated checker mutations.
- `scripts/media_pc3/build_review_page.py`, `test_review_package.py`: package
  mode, whole-input rehash before display, escaped metadata, no scripts/network,
  native keyboard expansion, new output outside inputs. A/B mode remains.
- `reports/pc3/render-package-*`: contract, pinned expectations, test layout,
  execution results, browser replay script and this handoff.

The production generator, its four source dependencies, layout, fixture, shared
manifest/API and React UI have not changed. Expectations use committed generator
source bytes at 33fa and the layout at e5469aa, not a candidate report's own
declarations. Full mode definitions and trust limits are in
`render-package-contract.md`.

## Executed checks and denominators

| Check | Expected | Actual |
|---|---|---|
| Checker unittest | Four positive modes and explicit failures | 19 methods: **18 PASS, 1 SKIP**, no failure/error; 13.697 seconds |
| Mode inventory | prepare 0, reps 3, short 72, animation 288 PNGs | All four artificial modes return `PASS_WITH_PENDING`; all have 288 coordinate rows |
| Invalid fixtures | Reject tampering, wrong event/time/units/bbox/settings, missing/extra files | **104 named cases rejected**; counts are test cases, not rendered images |
| Checker mutation | Disabling a real guard must break a corresponding negative test | **4/4 mutants detected**, covering five hash/time/environment/inventory conditions |
| Link boundary | No reads through package links | Actual hardlink and Windows directory junction refused; file symlink creation was **SKIP: WinError 1314** |
| Review document | Correct mode denominator, byte binding, input/output and metadata handling | **19/19 PASS**, 13.628 seconds |
| Existing A/B | Preserve comparison and old viewer behavior | **12/12 PASS**, 4.197 seconds |
| Browser | 390/768/1365 width, pending label, three artificial PNG decodes, Enter expansion, no external activity | **14/14 PASS**, Chrome 153.0.8010.48; errors 0, external requests 0 |
| Isolated copy | Tests must not need preexisting private `.local`, planning inputs or `.git` | One targeted test covering all **four positive modes PASS**, 3.452 seconds |

The browser checks used a flat-color PNG fixture, not pc1 imagery. Root inspected
the mobile and desktop screenshots: no page overflow, readable labels and
metadata, and native expansion/collapse worked. No person usability test is
claimed. The source checker still correctly reports pixel/video decoding as
NOT_RUN; the browser's artificial PNG decode test is a separate test result.

## Defects, changes and same-input recheck

1. The first checker incorrectly used a filename pattern for synthetic object
   IDs containing `+`, rejecting the valid pinned environment. Object IDs now
   have their own bounded pattern; file/path rules were not weakened. Root ran
   the **same positive artificial package** against the preserved first checker
   and the final checker: `PATH` failure before, `PASS_WITH_PENDING` after.
   Evidence: `render-package-fix-recheck.json`.
2. Review found that the initial read path did not explicitly refuse hardlinks
   or compare the opened handle identity with the pre-open file. The checker
   now checks link count, device/inode/size/time and bytes read. Actual hardlink
   and junction negative tests pass. File symlink privileges were not changed.
3. Initial artificial timing fields were zero and conflicted with positive
   source timing checks. The fixtures now explicitly use fabricated positive
   timing values. The checker was not loosened to conceal the test-input error.
4. The test layout initially depended on PC3 local scratch input. A pinned,
   byte-identical test snapshot and isolated-copy execution removed that
   dependency without changing production layout.

Original checker versions are preserved under `.local/pc3-tests/render-package/`.
The final checker SHA256 is
`36b4e2f3de8f0517da6cb26719e346e0fbfec221f5d1b673e494a73c31af30cc`.
Structured evidence is in `render-package-checks.json`,
`render-package-unit-checks.json`, `render-package-browser-checks.json`, and
`render-package-clean-replay.json`. The source snapshots were unchanged during
final tests. No input or preexisting output was overwritten.

## Reproduction

On PC3, start in `D:\hwana\Work\happycall-ralphthon` and use the existing Python
3.12 environment. These tests install nothing, contact no service and render
no Blender frames:

```powershell
python -B -m unittest discover -s scripts/media_pc3 -p test_render_package.py -v
python -B -m unittest discover -s scripts/media_pc3 -p test_review_package.py -v
python -B -m unittest discover -s scripts/media_pc3 -p test_compare_representatives.py -v
```

To create a clearly artificial representative package in a new scratch directory:

```powershell
@'
from pathlib import Path
import json, sys, time
sys.path.insert(0, str(Path('scripts/media_pc3').resolve()))
from test_render_package import make_package
from verify_render_package import verify_package
from build_review_page import build_package_html
root = Path('.local') / ('m3-replay-' + str(time.time_ns()))
package, expected = make_package(root)
(root / 'expectations.json').write_text(json.dumps(expected), encoding='utf-8')
result = verify_package(package, expected)
assert result['valid'] is True
(root / 'synthetic-review.html').write_text(build_package_html(package, result), encoding='utf-8')
print(root / 'synthetic-review.html')
'@ | python -B -
```

With an already installed Chromium and the existing pc3 Playwright dependency,
run `node reports/pc3/render-package-browser-check.mjs <printed-html-path>`.
No browser/runtime download is part of this command. The script writes its own
test evidence under `.local/pc3-m3-browser/` and does not modify the input HTML.
For an actual package, use the CLI examples in the contract with a separate
expectation file whose **mode and asset digests were supplied by pc1**.

## Pending and next main action

Fixture digest and actual threads are absent from the 33fa report and remain
PENDING even if unversioned extra fields claim values. The environment's 48
declarations are not Blender evaluated-mesh readback. Source hashes do not
authenticate a sender or establish which commit actually executed.

The checker does not decode `.blend`, PNG compressed pixels or MP4 frames;
occlusion, physical contact, flicker and final quality require separate review.
prepare is not rendered completion; 72 frames are not a 12-second finished
video. The viewer displays 0/0, 3/3, 3/72 or 3/288 PNGs as applicable, not all
frames of short/full modes. Supporting 288-frame intake does not authorize a
288-frame render. TEST roundtrip, final media, product registration and human
acceptance remain incomplete.

pc1 can now review this checker and supply the actual candidate Release,
source/input evidence and explicit mode for a subsequent **real intake**. Keep
Release manifests outside the strict generator package directory unless a
future explicit inventory contract includes them. Do not relabel the artificial
test packages as received renders. The implementation/source code and quantified
failure/recheck evidence support the delegation and validation records; no
competition score or final acceptance is claimed.
