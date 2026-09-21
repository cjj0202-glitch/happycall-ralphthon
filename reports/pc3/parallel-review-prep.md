# N03-M2: parallel preparation for A/B intake

The user explicitly requested splitting work into sessions and proceeding on 2026-09-21 at approximately 20:55 KST. This is preparation within the existing N03-M2 scope. PC1's three-frame geometry acceptance and its pending A/B render remain separate from this work. No duplicate implementation card, Blender install, extra render, paid call, public registration or deployment is created.

## File ownership and purpose

| PC3 session | Exclusive files | Result |
|---|---|---|
| n03_media | `scripts/media_pc3/compare_representatives.py` | Check an incoming A/B pair's manifests, hashes, representative frames and shared scene metadata |
| handoff_audit | `scripts/media_pc3/test_compare_representatives.py` | Exercise correct and deliberately broken pairs using temporary synthetic test fixtures |
| watcher_review | `scripts/media_pc3/build_review_page.py` | Build an offline side-by-side view of the six original representative images |
| root | this report and local dispatch state | Integrate the three outputs, inspect evidence, commit the named files, and reply once to #9 |

These sessions are on the same physical PC3. They are not additional PCs or human reviewers. The existing mailbox watcher remains a single process. No product source file overlaps the three preparation tasks.

## Intake contract

Inputs are two new output directories rendered by PC1 from the same A/B-enabled source: A=`baseline`, B=`contrast_material_v1`. Each contains `render-report.json`, `tracks.json`, and `frame-0001.png`, `frame-0133.png`, `frame-0288.png`. Old c208597 representative images use the previous geometry and cannot stand in for this pair.

The comparison checks the declared file sizes and SHA256 against local bytes; exact representative filenames; PNG signature/IHDR dimensions; scene/layout/dependency equality; requested and non-null actual sample counts; preset settings and color management; and matching synthetic trajectory/event/camera/time data. It refuses changed metadata, missing/corrupted assets, wrong look settings, unknown actual sample counts, and filenames outside the expected set. Input directories are read only.

`comparable=true` means this technical pairing can proceed to visual review. It does **not** mean that B looks better, the PNG pixels were fully decoded, the publisher was authenticated, or production quality was accepted. Release provenance and downloaded asset digests still require the normal authenticated intake check. `visualAccepted=false` remains explicit. Source projection samples remain different from actual rendered image frames.

## Reproduction after actual A/B assets arrive

Run from the repository root, using the actual newly received directories. The paths below are example locations; they do not claim that these outputs already exist on PC3.

```powershell
New-Item -ItemType Directory -Path .local/pc3-blender/look-intake-01
python scripts/media_pc3/compare_representatives.py --a .local/pc3-blender/look-ab-01/baseline --b .local/pc3-blender/look-ab-01/contrast_material_v1 --output .local/pc3-blender/look-intake-01/comparison.json
python scripts/media_pc3/build_review_page.py --a .local/pc3-blender/look-ab-01/baseline --b .local/pc3-blender/look-ab-01/contrast_material_v1 --output .local/pc3-blender/look-intake-01/review.html
```

Use a new output path and preserve previous results. The HTML embeds original PNG bytes and needs no CDN, server, upload, or network. Inspect it at original image size: floor/steel/belt/guard separation, support contact, parcel and branch visibility, and speckled shadows. The comparison page records no automatic visual acceptance and does not authorize the 72/288-frame extension. PC1 still decides the next N03-M2 unit after actual A/B observation.

## Verification record

Targeted test command: `python -m unittest discover -s scripts/media_pc3 -p test_compare_representatives.py -v`. Tests create their own temporary synthetic data and do not use or modify the received PC1 render assets. They are not evidence of newly rendered warehouse images.

Independent checker tests initially passed 10/10 with one correct synthetic pair and 47 deliberately broken variants. Viewer smoke checks passed 10 groups plus two output-path rejection cases. The fixtures are flat-color test images with fabricated renderer metadata, not actual warehouse renders. During root integration, identical invalid business identities in both inputs and image mutation between comparison and HTML generation were added as regression cases; the viewer now hashes the exact embedded bytes against the completed comparison. Final targeted results are recorded in the handoff below. Existing passed renderer/scene suites are not repeated merely because a preparation tool was added.

At 21:05 KST, PC3 received PC1's 21:00 follow-up (#9 comment 5760136604): PC1 has actually rendered six A/B frames and selected B for its improved material separation, with 42/42 reported geometry/camera/path/business-null checks. PC3 has not received or visually examined that pair. PC1 assigned an optional surrounding-environment candidate next; the three helper sessions are being reused for that bounded unit. These intake tools remain specific to the original two-dependency A/B report contract and do not automatically accept a later environment-detail report.

Final root integration run: the targeted command above passed **12/12 tests in 2.972 seconds**, including both added regression cases. `git diff --check` passed. The generator, existing scene and actual received render files were not modified by this preparation. Actual Blender rendering and visual A/B acceptance on PC3 remain **NOT_RUN**.
