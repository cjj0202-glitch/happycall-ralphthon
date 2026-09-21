# N03-M4 full animation gate handoff

The reviewed full-animation execution gate is implemented. Four unit suites passed 52 tests with one OS-dependent symlink skip; the disabled SHA guard mutant was detected. This document is not a real receipt or visual acceptance. PC3 did not run Blender, render 1080p/288 frames, install tools, publish assets, or register product media.

## Measured verification

Evidence: `reports/pc3/full-render-checks.json`. Run from the repository root:

```powershell
python -B -m unittest discover -s scripts/media_pc3 -p test_full_render_gate.py -v
python -B -m unittest discover -s scripts/media_pc3 -p test_look_presets.py -v
python -B -m unittest discover -s scripts/media_pc3 -p test_environment_detail.py -v
python -B -m unittest discover -s scripts/media_pc3 -p test_shadow_settings.py -v
```

| Check | Expected | Observed |
|---|---|---|
| New receipt/main tests | Complete artificial receipt reaches first stub render; invalid input/runtime stops | 16 PASS, 1 SKIP; 6 actual-main boundary methods; 17.601s |
| Negative branches | Reject malformed/missing/changed sources, inputs, evidence, settings and readback | 83 declared branches in passing methods, excluding skipped symlink and mutation |
| Disabled receipt SHA guard | Wrong-SHA main test must fail | 1/1 mutant detected: `Wrong expected receipt SHA reached the renderer`; original source bytes unchanged |
| Look / environment / shadow regression | Preserve original defaults, geometry/material/light/camera/motion/tracks and old main statements | 14/14 + 11/11 + 11/11 PASS |
| Separate collector audit | Actual scene properties and matrix math, without requested-value substitution | 17/17 stub checks PASS; prior PC1 matrix matches fixed camera direction/roll within 1e-5 |
| Real earlier 720p report compatibility | Read existing report without changing it or claiming a new render | PASS, 47,567 bytes, SHA `5679d20271eadab4addb4ce7043077b8fb68d5c701d50845196cd7100daf6c91` |

The new suite exercises the actual `arguments`, `scene_readback`, `main` and receipt/readback validators with explicit build/tracks/save/render stubs. It stops at the first render stub and does not validate completion of 288 images. Actual hardlink and junction rejection were measured at their specific link guards. Creating a symlink was denied by Windows error 1314, so that one check was skipped without changing privileges.

The old shadow suite initially failed two strict CLI/AST expectations after the authorized additions. pc1 expanded ownership in issue comment 5761626092; only those integration expectations were updated, preserving old runtime/ordering/geometry assertions. The same 11-test suite then passed. A junction test initially used the wrong PNG basename; it was corrected to a valid basename and now asserts the actual reparse-point rejection message rather than accepting an unrelated rejection.

pc1 supplied the corrected 1080p review reference `ed2b188de31091a71f1596f50961239d02813107`, which PC3 read. pc1 also accepted prior M3 intake at `c7fd1c0` within its independently reported 538/538 scope; that is separate from this M4 code result and full288 acceptance.

## Main operator contract

pc1 must review this new code and the existing three 1080p PNGs plus 720p 72-frame report before creating a receipt. Use the **current checkout bytes**, including the new gate dependency; the previous 33fa0e4 generator digest cannot authorize the changed generator. Preserve the exact bytes when copying reviewed evidence into a receipt bundle. The receipt parent contains all referenced files; source/input descriptors are compared with the actual generator directory and actual `--layout`/`--fixture` paths as well.

Example layout (illustrative names, no issued receipt):

```text
review-bundle/
  pc1-review.json
  source/build_scene.py
  source/scene_contract.py
  source/look_presets.py
  source/shadow_settings.py
  source/environment_detail.py
  source/full_render_gate.py
  input/scene-layout-v1.json
  input/cases.json
  evidence/1080p/frame-0001.png
  evidence/1080p/frame-0133.png
  evidence/1080p/frame-0288.png
  evidence/720p/render-report.json
```

Every descriptor is `{ "path": "relative/POSIX/name", "bytes": <actual positive integer>, "sha256": "<actual lower-case 64 hex SHA>" }`. Compute bytes and digest from the file itself (for example `len(path.read_bytes())` and `hashlib.sha256(path.read_bytes()).hexdigest()`); placeholders below are not executable receipt values. No links, junctions, hard links, parent traversal, absolute paths, duplicate paths, BOM-sensitive manual hash changes or unreviewed substitutions.

Receipt schema, to be populated **only by pc1 after review**:

```json
{
  "schemaVersion": "pc3-animation-review-v1",
  "reviewId": "PC1-CHOOSES-ACTUAL-REVIEW-ID",
  "scope": "synthetic-full-animation-candidate",
  "settings": {
    "camera": "cctv", "resolution": [1920, 1080], "engine": "eevee",
    "samples": 96, "shadowRays": 4, "look": "contrast_material_v1",
    "environmentDetail": "staging_v1", "threads": 2, "fps": 24, "frames": 288
  },
  "sources": {
    "generator": "REPLACE WITH build_scene.py DESCRIPTOR",
    "dependencies": ["REPLACE WITH ALL FIVE DEPENDENCY DESCRIPTORS"],
    "layout": "REPLACE WITH scene-layout-v1.json DESCRIPTOR",
    "fixture": "REPLACE WITH cases.json DESCRIPTOR"
  },
  "evidence": {
    "representatives": [
      {"role": "reviewed-representative", "frame": 1, "resolution": [1920, 1080], "path": "evidence/1080p/frame-0001.png", "bytes": "ACTUAL INTEGER", "sha256": "ACTUAL SHA"},
      {"role": "reviewed-representative", "frame": 133, "resolution": [1920, 1080], "path": "evidence/1080p/frame-0133.png", "bytes": "ACTUAL INTEGER", "sha256": "ACTUAL SHA"},
      {"role": "reviewed-representative", "frame": 288, "resolution": [1920, 1080], "path": "evidence/1080p/frame-0288.png", "bytes": "ACTUAL INTEGER", "sha256": "ACTUAL SHA"}
    ],
    "shortReport": {"role": "reviewed-short-report", "resolution": [1280, 720], "frameStart": 73, "frameEnd": 144, "renderedFrameCount": 72, "path": "evidence/720p/render-report.json", "bytes": "ACTUAL INTEGER", "sha256": "ACTUAL SHA"}
  }
}
```

The short report remains the reviewed earlier 33fa0e4 output, not a claim that the new gate produced those images. It must retain the registered synthetic event, 72 entries (73..144), original 288-frame denominator, EEVEE96/shadow4 runtime evidence and staging48 metadata. PNG signatures, dimensions, chunk structure and CRCs are checked; compressed image pixels are not decoded or judged by this gate.

After independently recording the exact final receipt SHA, pc1 runs its verified Blender executable from the repository root. All paths below are operator placeholders. Choose a fresh output directory; no overwrite or automatic retry is provided.

```powershell
& '<PC1 verified Blender executable>' --background --factory-startup --python-exit-code 1 --python scripts/media_pc3/build_scene.py -- --layout '<PC1 layout>/scene-layout-v1.json' --fixture '<PC1 fixture>/cases.json' --output '<PC1 fresh output>' --mode animation --camera cctv --resolution 1920 1080 --engine eevee --samples 96 --shadow-rays 4 --look contrast_material_v1 --environment-detail staging_v1 --threads 2 --animation-review '<PC1 review-bundle>/pc1-review.json' --animation-review-sha256 '<PC1 independently recorded exact SHA>'
```

## Runtime and report changes

- Receipt preflight finishes before output mkdir. Missing/invalid receipt flags fail in the actual CLI; wrong bytes/settings/evidence fail in the file gate.
- Threads are optional for existing modes (default `None`, no change to preexisting thread behavior). Reviewed animation requires explicit `--threads 2` and actual FIXED/2 readback. Baseline animation without a receipt keeps its prior behavior; overview animation remains forbidden.
- Actual scene values are read after build and again immediately before the first render, along with a second complete file check. Resolution percentage/pixel aspect/fps, engine/sample/shadow settings, fixed threads, camera position/direction/roll/type/shift/lens/sensor must match. A later file edit after the final check is not an immutable execution sandbox; keep the checkout and evidence unchanged during rendering.
- `fixture` adds actual bytes/SHA. `threads` separates requested value, observed `scene.render.threads` property and mode (AUTO is not a measurement of effective worker count). `sceneReadback` contains observed properties. `animationReview` separates requested SHA from verified receipt digest and evidence metadata. Final visual/product flags remain false.
- `full_render_gate.py` is added to report source dependencies. The earlier M3 checker pins the old four-dependency 720p contract and is **not** a validator for this new 1080p full run; pc1 must provide the appropriate next intake contract before using it on the new output.

The expected digest is supplied by the trusted operator; the gate does not cryptographically authenticate pc1 or establish image quality. Actual full288 render, final motion/occlusion/flicker review, product registration and TEST roundtrip remain separate.
