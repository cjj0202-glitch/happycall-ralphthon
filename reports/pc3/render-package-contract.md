# N03-M3: rendered package intake contract

2026-09-21. Assigned by pc1 in issue 9, comment 5760629024. PC3 is
LAPTOP-U2AL73UH / mcjun86-oss. The generator baseline is
`33fa0e4edeb88c0d4ad5e9cc0194ffc7e96cebcd`.

## Outcome and ownership

Check whether a received candidate's files, coordinates, declared inputs and
settings agree with a separately supplied expectation. Explain a refusal without
editing the package. This does not accept image quality, prove real CCTV,
authenticate the sender, or register media in the product.

| Lane | Owned changes | Result |
|---|---|---|
| Generator-independent checker | `scripts/media_pc3/verify_render_package.py` | Read-only verification JSON and CLI |
| Independent adversarial testing | `scripts/media_pc3/test_render_package.py` | Positive fixtures, corruptions, boundaries and checker mutations |
| Local review document | `scripts/media_pc3/build_review_page.py`, `test_review_package.py` | New package mode; existing A/B mode preserved |
| Root integration | `reports/pc3/render-package-*` | Pinned expectations, execution evidence, review and handoff |

The generator, scene contract, environment/shadow modules, layout, fixtures,
shared media manifest, API and React inspector are read-only for this card.
All lanes run on the same PC; they are not independent physical PCs or people.

## Independent expectations

`render-package-expectations.json` uses schema
`pc3-render-expectations-v1`. It was built from committed Git blob bytes, not
from a received report:

- Generator and four dependencies: the source commit above, exact names, sizes
  and SHA256. Dependency names are `scene_contract.py`, `look_presets.py`,
  `shadow_settings.py`, `environment_detail.py`.
- Layout: `planning/media/scene-layout-v1.json` at
  `e5469aa99bb266c5a977b80c097223275ac6fc9b`, SHA256
  `c6aece6692c6b78beb85d4f1167868f2bd095b3ab8366e837466715b82bd6cb6`.
- B look: the committed literal `contrast_material_v1` settings. Environment:
  the committed `staging_v1` declaration containing 48 static parts.
- Expected effective EEVEE samples 96 and shadow rays 4; expected threads 2.
  The checked-in example selects `representatives`; select another explicit
  mode in a separate expectation file only when pc1 supplies that package.
- Fixture digest is null because pc1 has not supplied that input digest for
  this package. `additionalAssets` is empty until pc1 explicitly identifies
  encoded MP4 assets and their expected digests.

The expectation file is a trusted caller input. Hash agreement with it does not
authenticate that file or independently prove a Git origin. Do not populate its
expected source/settings fields from the candidate being tested. Actual Release
provenance and byte verification remain a separate root intake step.

## Fixed scene and mode denominators

Both report and tracks bind CASE-0002 / W-W3 / SYN-CAM-02 to
`2026-09-18T02:33:00+09:00`, CH-02 / D-02. Business tote is explicitly null;
visual object is SYN-VIS-PARCEL02. Clock mode is
`illustrative-elapsed-separate-from-event-time`; synthetic elapsed time is never
the incident's clock. The camera is at [24, 1, 8], with 32 mm lens and 36 mm
sensor; coordinate space is normalized image top-left.

| Mode | Rendered PNG frame IDs | PNG count | Selected playback coverage |
|---|---|---:|---|
| prepare | none | 0 | No rendered image or video |
| representatives | 1, 133, 288 | 3 | Three samples, not a continuous clip |
| short | 73 through 144 | 72 | [3, 6) seconds of the scene; 3-second clip at 24 fps |
| animation | 1 through 288 | 288 | [0, 12) seconds at 24 fps |

All four modes still contain 288 coordinate rows for the full 12-second scene,
at 1280 by 720. A row's elapsed time is `(frame - 1) / 24`. Phase intervals are
approach [0,3), branch [3,6), chute [6,10), settle [10,12). World position/yaw,
bbox ordering and bounds, frame continuity, identity, units and contact-plane
gap must satisfy the source contract. `occlusionTested=false` remains mandatory.
Supporting animation intake does not authorize rendering or accepting 288 frames.

## Failures, pending evidence and safe reads

Reject wrong/missing/duplicate frames, files, input digests, identities or
settings. Reject non-finite or wrong-type numbers, invalid bbox/phase/time,
ambiguous JSON, unsafe names, links/reparse points and directory escapes.
Read only a fixed package inventory. Reports cannot nominate arbitrary paths.
Check byte count and SHA for report-referenced tracks, blend and selected PNGs;
check explicit optional MP4 digests without claiming video decoding.

PNG structural checks and original-byte display do not establish pixel quality.
Input data and existing output files must remain unchanged; outputs go to a new
file outside inputs. The viewer verifies original PNG bytes again before embedding
them, escapes metadata, loads no scripts or network resources, and preserves A/B
behavior.

Missing evidence is not a successful measurement:

- The 33fa report does not contain actual fixture digest or thread readback:
  `PENDING`, requiring separate pc1 execution evidence. Requested 2 is not actual 2.
- Environment data is a declaration, not evaluated Blender mesh readback.
- Blender execution, image pixel decoding and video decoding are `NOT_RUN` in
  this checker. Visual acceptance and product registration stay false.
- `valid=true` / `PASS_WITH_PENDING` means only that the implemented consistency
  checks passed. It never means the pending items or final product passed.

## Validation and reproduction

Tests use explicitly artificial checker fixtures with small synthetic files,
including prepare, representatives, short and animation inventories. They are
not received Blender output. Invalid variants rehash modified fixtures when
needed to test semantic gates separately from byte-integrity gates. Selected
checker gates are deliberately disabled in isolated mutation trials; the tests
must detect each disabled gate. Preserve the original checker bytes first.

The byte-identical `render-package-test-layout.json` snapshot makes the tests
reproducible without PC3's private `.local` layout or a Git object database. It
is a test input copied from the pinned layout above, not a modified production
layout. The fixture helper verifies its SHA before constructing artificial data.

```powershell
python -B -m unittest discover -s scripts/media_pc3 -p test_render_package.py -v
python -B -m unittest discover -s scripts/media_pc3 -p test_review_package.py -v
python -B scripts/media_pc3/verify_render_package.py --package <received-directory> --expectations reports/pc3/render-package-expectations.json --output <new-outside-input.json>
python -B scripts/media_pc3/build_review_page.py --package <received-directory> --expectations reports/pc3/render-package-expectations.json --output <new-outside-input.html>
```

The angle-bracket paths are caller-supplied placeholders. Actual 72-frame assets
have not been received on PC3 at contract creation. Execution results, failures,
fixes and actual vs synthetic denominators belong in the subsequent handoff.
