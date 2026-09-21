# N03-M2: guard supports, geometry-only follow-up

Assignment: pc1 comment [5759608980](https://github.com/cjj0202-glitch/happycall-ralphthon/issues/9#issuecomment-5759608980), 2026-09-21 20:17 KST. Baseline: `c208597a318a1934b7ee873299b326619ec23f33`. PC3: `LAPTOP-U2AL73UH` / `mcjun86-oss`; checkout `D:\hwana\Work\happycall-ralphthon`; branch `work/pc3-n03-wms-scenes`.

## Observed input, scope, expected result

PC1 rendered the three images in [the representative prerelease](https://github.com/cjj0202-glitch/happycall-ralphthon/releases/tag/demo-wms-blender-representatives-20260921). PC3 downloaded its five assets under `D:\hwana\Downloads\happycall-blender-representatives-20260921` and verified every byte count and GitHub SHA256 digest: 5/5, total 3,171,925 bytes. PC3 directly viewed frames 1, 133, 288. These are **PC1 renders**, not PC3 render execution. The report records Blender 4.5.14 LTS, EEVEE, 1280x720, 32 requested samples, three rendered frames, 17.565 seconds inside the generator. PC1 separately reported 18.625 seconds overall; these are different timing scopes.

The front and outfeed yellow rails lack visible supports. The bright floor and similar highlights on the steel and guards also need a later controlled material/lighting comparison; those settings are unchanged in this geometry-only revision. Contact-shadow speckles are visible, but the precise cause is not established from still PNGs.

Expected: all five guard segments attach through supports to their adjacent side frames; no support enters the parcel passage. Keep the layout, path, camera, event anchor, seed, materials, light setup, samples, and watermark unchanged. BMAD checks: the user must see supported machinery (UX), the geometry must connect (construction), parcel motion must remain clear (process), and synthetic visuals must not imply known business tote identity or blame (contract). No new user decision is required within this assigned scope.

## Implementation

The generator adds six south posts and six outfeed posts. It also corrects six existing north posts: their old Y bounds `[8.255,8.305]` missed the frame's `[8.155,8.245]` by 10 mm, despite adequate height. Simply copying those narrow posts south would leave another horizontal gap.

| Group | Count | Centers (m) | Dimensions (m) | Contact intent |
|---|---:|---|---|---|
| North | 6 | x=10,12.5,15,17,20,22.5; y=8.24; z=.935 | .06 × .16 × .25 | bridge rail y=8.28 and frame y=8.20 |
| South | 6 | same x; y=6.755; z=.935 | .06 × .16 × .25 | bridge rail y=6.71 and frame y=6.80; preserve opening x=17.6…19.4 |
| Outfeed | 6 | x=17.725 or19.275; y=4.1,5.5,6.25; z=.915 | .10 × .06 × .21 | connect rail and adjacent frame below the rounded turn |

All posts start at z=.81, overlapping the .84 m side-frame top by .03 m. Main posts reach1.06 m; outfeed posts reach1.02 m, beyond the respective rail bottoms1.01/.95 m. Bevel width remains .005 m, smaller than the tested contact overlaps. This is an illustrative synthetic construction, not a structural engineering certification.

## Verification and reproduction

Numerical audit: `python scripts/media_pc3/audit_guard_supports.py --layout planning/media/scene-layout-v1.json --output reports/pc3/blender-guard-geometry.json`. PC3 used its byte-identical `.local/pc3-blender/input/scene-layout-v1.json` copy because the task branch does not contain the main-owned planning path. The associated `blender-guard-geometry.json` records evaluated source boxes, support contacts, sampled collision checks, the old-gap negative case, and limitations. No Blender module is loaded by that audit.

Existing scene contract checks: `python -m unittest discover -s tests/remote/pc3 -p test_scene_contract.py -v` → 12/12 PASS after the geometry edit. `python -m py_compile scripts/media_pc3/build_scene.py scripts/media_pc3/scene_contract.py` and `git diff --check` → exit0. No UI code or shared fixture was changed.

Measured numeric results on PC3: 18/18 supports intersect both a rail and a frame; the six old north supports are rejected for their 10 mm horizontal disconnect. Yaw-aware cuboid separation checks find zero parcel/post intersections at 12,001 sampled times (1 ms grid, including endpoints) and at all 288 render-frame times. Deliberate collision, far-separated, and rotated AABB false-positive controls pass. These are source geometry measurements, not continuous collision proof or rendered pixel checks. The separate review agent ran on the same PC3 and is not another physical PC or a human reviewer.

PC1 reproduction with its verified Blender executable and the same shared input:

```powershell
& $blenderExe --background --factory-startup --python-exit-code 1 --python scripts/media_pc3/build_scene.py -- --layout planning/media/scene-layout-v1.json --fixture data/fixtures/cases.json --output .local/pc3-blender/guard-geometry-02 --mode representatives --resolution 1280 720 --samples 32
```

Use a new empty output directory. Compare frames1/133/288 to the prior release: yellow guards should have visible contact through posts with the gray side frames, while the same parcel poses remain clear. Check actual Blender output and pixels before accepting geometry. This numerical audit does not verify evaluated Blender modifiers, occlusion, shadows or production image quality. It must not be relabelled as rendered evidence.

## Remaining gate

PC3 has not rendered the revised scene. `visualGateAccepted=false` and `mainRegistration=false` remain. PC1 reviews the three new representative frames, then the material/lighting comparison. No 72-frame clip, 288-frame animation, final MP4, or shared registration is produced by this revision. TEST roundtrip remains separately incomplete.
