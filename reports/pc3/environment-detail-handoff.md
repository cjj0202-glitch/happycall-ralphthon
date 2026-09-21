# N03-M2 optional warehouse surroundings candidate

## Assignment and boundaries

PC1 assigned this unit in #9 comment 5760136604 at 21:00 KST on 2026-09-21; PC3 read it at 21:05. PC1 reported six actual A/B renders from `d67b2c7c60c9bf08ec7d29555366e0e33a9790f6`, selected B for material separation, and requested static surrounding equipment because the remaining empty floor still reads as explanatory CG. This report does not claim PC3 rendered or personally inspected those A/B images.

Implementation uses the existing `work/pc3-n03-wms-scenes` branch after the independent intake helper commit `81f61be6a797f2164770dc85439ad47107a2ae0b`. Shared planning was read from `origin/main` at `b03246a` without merging the work branch. The synthetic reference was inspected locally; no original company drawings, employee likenesses, operational identifiers or paid services are used.

The same physical PC3 runs three helper sessions with exclusive files: surrounding-placement design and renderer instructions; optional environment module and generator integration; independent contract, clearance and visibility tests. Root reviews their integration and submits one result. These are not three additional computers or independent human acceptances.

## Intended result and acceptance

The default must preserve the existing scene. `--environment-detail staging_v1` adds only the designed static context, with separate synthetic environment metadata and no business-object identity. Existing conveyor, guard supports, parcel meshes, camera, motion, event anchor, unknown business tote, materials, lighting and sample defaults remain fixed. B's `short` option is available for PC1's explicit later 72-frame review; the environment candidate and B remain blocked from the 288-frame animation mode.

The placement design and exact inventory are recorded in `environment-detail-design.md`. Computer checks must cover default invariance, deterministic optional additions, invalid options, fixed event and motion contracts, open corridors, conservative new-object bounds, and camera rays to the moving parcel. These checks do not replace actual Blender geometry, surface-contact, shadow, occlusion and three-frame image review.

## Verification and remaining work

Final targeted verification at 21:14:58 KST passed **34/34 tests in 2.634 seconds**: 11 environment tests, the requested 12 existing scene-contract tests, and 11 look/CLI regression tests. No unrelated passed UI suites were repeated.

| Expected | Measured |
|---|---|
| Default adds no objects; candidate is static and untracked | Actual generator insertion recorded with fake primitive helpers: `none`=0, `staging_v1`=48, original tracked list unchanged |
| Existing scene and rendering rules remain fixed | Original build AST is identical after removing the one added environment loop. Camera/tracks/mesh helpers, materials, lights and motion contract are unchanged; main render logic differs only by new metadata/dependency recording |
| No new prop intersects the sampled moving parcel | 288 poses × 3 original parcel parts × 48 props = 41,472 pairs; 0 intersections |
| New props do not block sampled camera rays | 6,912 camera-to-corner segments × 48 AABBs = 331,776 pairs; 0 intersections |
| Context remains in the fixed camera frame | 384 declared prop corners in frame; independent root/group projection agrees |
| Open aisle and supported components | 0 new solid aisle intersections, 8 wheels and 4 rack legs at floor, 4 cartons supported by shelf planes, all 48 conservative AABBs connected to ground |
| Failure detectors really reject defects | Injected route/ray blockers, tall object mislabeled as paint, wrong option/type and forbidden animation modes rejected |

Root found a real design failure before handoff: the original rack centered at x=19.5 projected to x=1351.95px outside the 1280px frame. Moving only the rack and its four cartons by -1.2m changed the maximum to 1238.51px. The rejected original placement is retained as a regression case. The camera, lights and parcel route did not move.

Detailed evidence: `environment-detail-checks.json` records measured checks, test-source digests and limitations; `environment-projection-estimate.json` records the initial failure and final group projections. `environment-detail-spec.json` is a pure-Python declaration of the 48 optional parts, explicitly `declaration-only-not-rendered`, `renderedFrames=0`, `visualGateAccepted=false`. It is **not** a Blender `prepare` output or runtime readback.

Reproduce from the repository root with the shared layout available at `planning/media/scene-layout-v1.json` (this older PC3 checkout uses its identical `.local/pc3-blender/input/scene-layout-v1.json`):

```powershell
python -m unittest discover -s scripts/media_pc3 -p test_environment_detail.py -v
python -m unittest discover -s tests/remote/pc3 -p test_scene_contract.py -v
python -m unittest discover -s scripts/media_pc3 -p test_look_presets.py -v
```

PC1's initial render input is the shared layout plus `data/fixtures/cases.json`, the four generator modules from this result commit, and explicit `--look contrast_material_v1 --environment-detail staging_v1`. Exact new-output `prepare` and representative commands are in `scripts/media_pc3/BLENDER.md`. Material/sample changes are not bundled with this geometry candidate.

No Blender process or actual PNG generation has run on PC3 for this candidate (**NOT_RUN**). Conservative AABB contact and sampled rays do not prove evaluated mesh contact, between-frame visibility, shadow behavior or final visual quality. PC1 must render the same three representative frames, compare the fixed source/trajectory/camera, and accept visual clearance before extending to the short motion review. Final video acceptance, common media registration and TEST roundtrip remain separate and incomplete.
