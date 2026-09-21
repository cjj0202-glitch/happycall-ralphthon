"""Independent N03-M3 package tests: generated test files are NOT Blender renders.

Expected source/settings originate in root's separate frozen expectations file.
Flat-color PNGs, fake .blend bytes and fabricated runtime claims only exercise
the checker. Neither passing tests nor matching hashes authenticates a renderer.
"""
from __future__ import annotations

import ast
import contextlib
import copy
import hashlib
import importlib
import io
import itertools
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock
import zlib

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from scene_contract import SCENE_SEED, evaluate_motion, load_layout
from test_environment_detail import corners, project_point

EXPECTATIONS = ROOT / "reports/pc3/render-package-expectations.json"
CHECKER = HERE / "verify_render_package.py"
SCRATCH = ROOT / ".local/pc3-tests/render-package"
NEGATIVE_CASES = set()
MUTATION_RESULTS = []
MODES = {"prepare": [], "representatives": [1, 133, 288],
         "short": list(range(73, 145)), "animation": list(range(1, 289))}
PARCEL = [{"center": [0, 0, .175], "dimensions": [.62, .42, .35]},
          {"center": [0, 0, .352], "dimensions": [.075, .418, .004]},
          {"center": [.15, -.04, .352], "dimensions": [.16, .13, .004]}]


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    data = Path(path).read_bytes()
    return {"name": Path(path).name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def png(width=1280, height=720):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    raw = (b"\0" + bytes((40, 60, 80)) * width) * height
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def make_package(root, mode="representatives"):
    """Return (new root/package, independent expectations); refuse any overwrite."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    package = root / "package"
    package.mkdir()
    expected = json.loads(EXPECTATIONS.read_text(encoding="utf-8-sig"))
    expected["mode"] = mode
    selected = MODES[mode]
    layout_path = ROOT / "reports/pc3/render-package-test-layout.json"
    if digest(layout_path)["sha256"] != expected["layout"]["sha256"]:
        raise ValueError("Independent test layout bytes do not match the pinned external expectation")
    layout = load_layout(layout_path)
    rows = []
    for frame in range(1, 289):
        motion = evaluate_motion((frame - 1) / 24, layout)
        projected = [project_point(p, layout["camera"]) for part in PARCEL for p in corners(part, motion)]
        bounds = [min(p[0] for p in projected), min(p[1] for p in projected),
                  max(p[0] for p in projected), max(p[1] for p in projected)]
        rows.append({"frame": frame, "elapsedSeconds": (frame - 1) / 24,
                     "visualObjectId": "SYN-VIS-PARCEL02", "businessToteId": None,
                     "worldPosition": motion["position"], "yawRadians": motion["yaw_radians"],
                     "phase": motion["phase"], "bboxNormalizedXYXY": bounds,
                     "fullyInFrame": True, "contactPlaneGapMeters": 0})
    tracking = {"source": "synthetic-scene-ground-truth", "synthetic": True,
                "eventAnchor": copy.deepcopy(layout["eventAnchor"]), "coordinateSpace": "normalized-image-top-left",
                "fps": 24, "frameCount": 288, "resolution": [1280, 720],
                "clockMode": layout["animation"]["clockMode"], "cameraId": "SYN-CAM-02",
                "cameraPosition": [24, 1, 8], "cameraLensMm": 32, "sensorWidthMm": 36,
                "occlusionTested": False, "frames": rows, "clippedFrames": [],
                "notice": "TEST FIXTURE: independently calculated pinhole bounds; no Blender execution."}
    write_json(package / "tracks.json", tracking)
    (package / "case-0002-ww3.blend").write_bytes(b"SYNTHETIC TEST PLACEHOLDER, NOT A BLENDER FILE.\n")
    pixels, rendered = png(), []
    for frame in selected:
        asset = package / f"frame-{frame:04d}.png"
        asset.write_bytes(pixels)
        rendered.append({**digest(asset), "frame": frame, "elapsedSeconds": (frame - 1) / 24, "renderSeconds": .01})
    report = {"schemaVersion": "pc3-blender-candidate-v1", "synthetic": True,
              "status": "unreviewed-render-candidate" if selected else "scene-prepared-not-rendered",
              "visualGateAccepted": False, "mainRegistration": False, "seed": SCENE_SEED,
              "blenderVersion": "4.5.14", "engine": "BLENDER_EEVEE_NEXT", "engineDevice": "FAKE TEST DEVICE",
              "requestedSamples": expected["samples"], "resolution": [1280, 720], "fps": 24,
              "shadowRays": {"requested": 4, "actual": 4, "applied": True,
                             "property": "scene.eevee.shadow_ray_count", "range": {"cli": [1, 4], "runtime": {"min": 1, "max": 4}}},
              "runtimeSamples": {"property": "scene.eevee.taa_render_samples", "value": 96,
                                 "note": "Fabricated test metadata, not runtime observation."},
              "look": copy.deepcopy(expected["look"]), "environmentDetail": copy.deepcopy(expected["environmentDetail"]),
              "colorManagement": {"viewTransform": "AgX", "exposure": 0, "gamma": 1},
              "candidateDurationSeconds": 12, "candidateFrameCount": 288, "renderedFrameCount": len(selected),
              "wallSeconds": .1, "layout": copy.deepcopy(expected["layout"]),
              "generator": copy.deepcopy(expected["generator"]), "eventAnchor": copy.deepcopy(layout["eventAnchor"]),
              "sourceDependencies": copy.deepcopy(expected["sourceDependencies"]), "cameraId": "SYN-CAM-02",
              "clockMode": layout["animation"]["clockMode"], "representativeFrames": [1, 133, 288],
              "rendered": rendered, "blend": digest(package / "case-0002-ww3.blend"),
              "tracks": digest(package / "tracks.json"), "clippedFrames": [],
              "occlusionAndVisualContactReviewed": False, "videoEncoded": False,
              "note": "SYNTHETIC TEST FIXTURE ONLY: fake .blend, flat PNGs, no visual acceptance."}
    write_json(package / "render-report.json", report)
    return package, expected


def mutate_report(package, change):
    path = Path(package) / "render-report.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    change(value)
    write_json(path, value)


def mutate_tracks(package, change):
    path = Path(package) / "tracks.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    change(value)
    write_json(path, value)
    mutate_report(package, lambda report: report.__setitem__("tracks", digest(path)))


def update_asset_digest(package, name):
    def update(report):
        target = next(row for row in report["rendered"] if row["name"] == name)
        target.update(digest(Path(package) / name))
    mutate_report(package, update)


class RenderPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = importlib.import_module("verify_render_package")
        cls.checker_bytes = CHECKER.read_bytes()
        cls.checker_sha = hashlib.sha256(cls.checker_bytes).hexdigest()
        SCRATCH.mkdir(parents=True, exist_ok=True)
        cls.backup = SCRATCH / f"checker-original-{cls.checker_sha}.py"
        if not cls.backup.exists():
            cls.backup.write_bytes(cls.checker_bytes)
        if cls.backup.read_bytes() != cls.checker_bytes:
            raise RuntimeError("Original checker backup differs; refusing overwrite")

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="synthetic-", dir=SCRATCH)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.package, self.expected = make_package(self.root)
        self.report_original = (self.package / "render-report.json").read_bytes()
        self.tracks_original = (self.package / "tracks.json").read_bytes()

    def verify(self, package=None, expected=None):
        return self.validator.verify_package(package or self.package, self.expected if expected is None else expected)

    def rejected(self, name, package=None, expected=None):
        result = self.verify(package, expected)
        self.assertIs(result["valid"], False, (name, result))
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(result["failures"], name)
        for failure in result["failures"]:
            self.assertIsInstance(failure["code"], str)
            self.assertIsInstance(failure["detail"], str)
        for flag in ("visualAccepted", "pixelDecoded", "videoDecoded", "authenticityVerified"):
            self.assertIs(result[flag], False)
        NEGATIVE_CASES.add(name)

    def report_cases(self, variants):
        for name, change in variants:
            with self.subTest(name=name):
                (self.package / "render-report.json").write_bytes(self.report_original)
                mutate_report(self.package, change)
                self.rejected(name)

    def track_cases(self, variants):
        for name, change in variants:
            with self.subTest(name=name):
                (self.package / "tracks.json").write_bytes(self.tracks_original)
                (self.package / "render-report.json").write_bytes(self.report_original)
                mutate_tracks(self.package, change)
                self.rejected(name)

    def test_valid_modes_keep_pending_and_inputs_unchanged(self):
        for mode, frames in MODES.items():
            with self.subTest(mode=mode):
                package, expected = make_package(self.root / mode, mode)
                before = {p.name: digest(p) for p in package.iterdir()}
                expected_before = copy.deepcopy(expected)
                result = self.verify(package, expected)
                self.assertIs(result["valid"], True, result)
                self.assertEqual(result["status"], "PASS_WITH_PENDING")
                self.assertEqual(result["schemaVersion"], "pc3-render-package-verification-v1")
                self.assertEqual(result["failures"], [])
                self.assertEqual(result["mode"], mode)
                self.assertEqual(result["sourceCommit"], expected["sourceCommit"])
                self.assertEqual([row["frame"] for row in result["images"]], frames)
                self.assertEqual(len(result["images"]), len(frames))
                pending = {row["code"] if isinstance(row, dict) else row for row in result["pending"]}
                self.assertTrue({"FIXTURE_RUNTIME_UNVERIFIED", "THREADS_RUNTIME_UNVERIFIED"} <= pending)
                for flag in ("visualAccepted", "pixelDecoded", "videoDecoded", "authenticityVerified"):
                    self.assertIs(result[flag], False)
                self.assertEqual(before, {p.name: digest(p) for p in package.iterdir()})
                self.assertEqual(expected, expected_before)
                self.assertEqual({d["name"] for d in result["inputDigests"]}, set(before))

    def test_report_claims_cannot_promote_missing_fixture_threads_or_visual_checks(self):
        self.expected["fixture"] = {"name": "cases.json", "bytes": 10, "sha256": "a" * 64}
        mutate_report(self.package, lambda r: r.update(fixture=self.expected["fixture"], threads=2,
                       runtimeThreads={"value": 2, "mode": "FIXED"}, authenticityVerified=True))
        result = self.verify()
        self.assertIs(result["valid"], True, result)
        self.assertEqual(result["status"], "PASS_WITH_PENDING")
        self.assertIs(result["authenticityVerified"], False)
        codes = {row["code"] if isinstance(row, dict) else row for row in result["pending"]}
        self.assertTrue({"FIXTURE_RUNTIME_UNVERIFIED", "THREADS_RUNTIME_UNVERIFIED"} <= codes)

    def test_external_expectations_reject_invalid_shape_and_source_settings(self):
        variants = [("expectation-schema", lambda e: e.update(schemaVersion="unknown")),
                    ("expectation-source-sha", lambda e: e.update(sourceCommit="not-a-commit")),
                    ("expectation-mode", lambda e: e.update(mode="full")),
                    ("expectation-samples-unit", lambda e: e.update(samples="96")),
                    ("expectation-rays-bool", lambda e: e.update(shadowRays=True)),
                    ("expectation-thread-unit", lambda e: e.update(threads="2")),
                    ("expectation-generator", lambda e: e["generator"].update(sha256="0" * 64)),
                    ("expectation-layout", lambda e: e["layout"].update(sha256="0" * 64)),
                    ("expectation-module-missing", lambda e: e["sourceDependencies"].pop()),
                    ("expectation-module-duplicate", lambda e: e["sourceDependencies"].__setitem__(1, e["sourceDependencies"][0])),
                    ("expectation-environment", lambda e: e["environmentDetail"]["objects"][0]["location"].__setitem__(0, 99))]
        for name, change in variants:
            with self.subTest(name=name):
                expected = copy.deepcopy(self.expected)
                change(expected)
                self.rejected(name, expected=expected)

    def test_report_flags_units_events_settings_and_dependencies(self):
        variants = [(f"report-{key}", lambda r, k=key, v=value: r.__setitem__(k, v)) for key, value in
                    (("schemaVersion", "unknown"), ("synthetic", 1), ("mainRegistration", 0),
                     ("visualGateAccepted", True), ("videoEncoded", True), ("fps", "24"),
                     ("candidateFrameCount", 72), ("candidateDurationSeconds", "12seconds"),
                     ("renderedFrameCount", True), ("requestedSamples", 32), ("engine", "CYCLES"),
                     ("blenderVersion", ""), ("seed", 0), ("cameraId", "OTHER"), ("clockMode", "realtime"))]
        variants += [("report-other-event", lambda r: r["eventAnchor"].update(eventId="W-W2")),
                     ("report-other-date", lambda r: r["eventAnchor"].update(occurredAt="2026-09-19T02:33:00+09:00")),
                     ("report-false-tote", lambda r: r["eventAnchor"].update(businessToteId=False)),
                     ("report-sample-null", lambda r: r["runtimeSamples"].update(value=None)),
                     ("report-sample-false-unit", lambda r: r["runtimeSamples"].update(value="96")),
                     ("report-sample-property", lambda r: r["runtimeSamples"].update(property="scene.cycles.samples")),
                     ("report-rays-clamp", lambda r: r["shadowRays"].update(actual=2)),
                     ("report-rays-applied-int", lambda r: r["shadowRays"].update(applied=1)),
                     ("report-rays-range", lambda r: r["shadowRays"]["range"]["runtime"].update(max=8)),
                     ("report-look-drift", lambda r: r["look"]["settings"]["steel"].update(roughness=.99)),
                     ("report-environment-drift", lambda r: r["environmentDetail"]["objects"][0]["location"].__setitem__(0, 99)),
                     ("report-environment-tracked-int", lambda r: r["environmentDetail"]["objects"][0].update(tracked=0)),
                     ("report-environment-extra", lambda r: r["environmentDetail"]["objects"].append(copy.deepcopy(r["environmentDetail"]["objects"][0]))),
                     ("report-dependency-digest", lambda r: r["sourceDependencies"][0].update(sha256="0" * 64)),
                     ("report-dependency-duplicate", lambda r: r["sourceDependencies"].__setitem__(1, r["sourceDependencies"][0])),
                     ("report-frame-duplicate", lambda r: r["rendered"].__setitem__(1, r["rendered"][0])),
                     ("report-frame-boolean", lambda r: r["rendered"][0].update(frame=True)),
                     ("report-frame-time", lambda r: r["rendered"][1].update(elapsedSeconds=133)),
                     ("report-clipped", lambda r: r.update(clippedFrames=[133])),
                     ("report-traversal", lambda r: r["rendered"][0].update(name="../secret.png")),
                     ("report-absolute-path", lambda r: r["tracks"].update(name=str(self.root / "outside.json")))]
        self.report_cases(variants)

    def test_track_metadata_and_all_row_contracts(self):
        variants = [("tracks-case", lambda t: t["eventAnchor"].update(caseId="CASE-0001")),
                    ("tracks-occlusion-int", lambda t: t.update(occlusionTested=0)),
                    ("tracks-fps", lambda t: t.update(fps=30)),
                    ("tracks-camera-position", lambda t: t["cameraPosition"].__setitem__(0, 25)),
                    ("tracks-lens", lambda t: t.update(cameraLensMm=36)),
                    ("tracks-sensor", lambda t: t.update(sensorWidthMm=35)),
                    ("tracks-row-missing", lambda t: t["frames"].pop()),
                    ("tracks-row-duplicate", lambda t: t["frames"].__setitem__(132, t["frames"][131]))]
        variants += [(f"track-row-{field}", lambda t, f=field, v=value: t["frames"][132].__setitem__(f, v))
                     for field, value in (("frame", 134), ("elapsedSeconds", 5.6), ("visualObjectId", "OTHER"),
                                          ("businessToteId", "TOTE-A"), ("phase", "approach"),
                                          ("yawRadians", 0), ("worldPosition", [18.5, 4.5, .85]),
                                          ("contactPlaneGapMeters", .1), ("fullyInFrame", 1))]
        variants += [(f"track-bbox-{i}", lambda t, v=value: t["frames"][132].update(bboxNormalizedXYXY=v))
                     for i, value in enumerate(([.5, .5, .4, .6], [-.1, .2, .4, .6], [.1, .2, 1.1, .6],
                                               [True, .2, .4, .6], [.1, .2, .4], [.1, .2, .4, .6]))]
        variants += [("track-first-frame-bool", lambda t: t["frames"][0].update(frame=True)),
                     ("track-last-frame-world", lambda t: t["frames"][287]["worldPosition"].__setitem__(0, 19))]
        self.track_cases(variants)

    def test_rejects_asset_sha_mismatch(self):
        mutate_report(self.package, lambda r: r["rendered"][0].update(sha256="0" * 64))
        self.rejected("asset-sha-mismatch")

    def test_rejects_track_time_drift(self):
        mutate_tracks(self.package, lambda t: t["frames"][132].update(elapsedSeconds=6))
        self.rejected("track-time-drift")

    def test_rejects_environment_drift(self):
        mutate_report(self.package, lambda r: r["environmentDetail"]["objects"][0]["location"].__setitem__(0, 99))
        self.rejected("environment-drift")

    def test_rejects_unknown_file(self):
        (self.package / "unlisted.png").write_bytes(png())
        self.rejected("unlisted-file")

    def test_missing_and_corrupt_assets_even_when_declared_digest_matches(self):
        for name in ("render-report.json", "tracks.json", "case-0002-ww3.blend", "frame-0133.png"):
            path = self.package / name
            original = path.read_bytes()
            with self.subTest(missing=name):
                path.unlink()
                self.rejected("missing-" + name)
            path.write_bytes(original)
        original = png()
        broken = [("signature", b"not-png"), ("truncated-iend", original[:-12]),
                  ("trailing-data", original + b"hidden"), ("crc", original[:29] + bytes([original[29] ^ 1]) + original[30:]),
                  ("wrong-resolution", png(640, 360))]
        for name, data in broken:
            with self.subTest(corruption=name):
                path = self.package / "frame-0133.png"
                path.write_bytes(data)
                update_asset_digest(self.package, path.name)
                self.rejected("png-" + name)

    def test_all_asset_descriptors_and_external_video_allowlist_are_strict(self):
        variants = [(f"{kind}-{field}", lambda r, k=kind, f=field, v=value:
                     (r["rendered"][0] if k == "png" else r[k]).__setitem__(f, v))
                    for kind in ("png", "tracks", "blend")
                    for field, value in (("bytes", True), ("bytes", 1), ("sha256", "bad"))]
        self.report_cases(variants)
        (self.package / "render-report.json").write_bytes(self.report_original)
        for name in ("../outside.mp4", "nested/file.mp4", "C:/outside.mp4", "render-report.json"):
            expected = copy.deepcopy(self.expected)
            expected["additionalAssets"] = [{"name": name, "bytes": 1, "sha256": "a" * 64}]
            with self.subTest(name=name):
                self.rejected("video-allowlist-" + name, expected=expected)
        extra = self.package / "subdirectory"
        extra.mkdir()
        self.rejected("unexpected-subdirectory")

    def test_strict_json_duplicate_keys_nonfinite_malformed(self):
        for name, data in (("duplicate", b'{"schemaVersion":"pc3-blender-candidate-v1",' + self.report_original[1:]),
                           ("nan", self.report_original.replace(b'"wallSeconds": 0.1', b'"wallSeconds": NaN')),
                           ("infinity", self.report_original.replace(b'"wallSeconds": 0.1', b'"wallSeconds": Infinity')),
                           ("malformed", b'{broken')):
            with self.subTest(name=name):
                (self.package / "render-report.json").write_bytes(data)
                self.rejected("json-" + name)

    def test_only_explicit_external_additional_video_assets_are_hashed(self):
        path = self.package / "branch-preview.mp4"
        path.write_bytes(b"SYNTHETIC TEST VIDEO PLACEHOLDER, NOT DECODABLE MP4")
        self.rejected("video-undeclared")
        self.expected["additionalAssets"] = [digest(path)]
        result = self.verify()
        self.assertIs(result["valid"], True, result)
        self.assertIs(result["videoDecoded"], False)
        self.assertIn(path.name, {row["name"] for row in result["inputDigests"]})
        path.write_bytes(b"changed")
        self.rejected("video-bytes-mismatch")

    def test_cli_output_collision_input_mutation_and_exit_status(self):
        expectations = self.root / "expectations.json"
        write_json(expectations, self.expected)
        args = [sys.executable, "-B", str(CHECKER), "--package", str(self.package), "--expectations", str(expectations)]
        output = self.root / "result.json"
        completed = subprocess.run(args + ["--output", str(output)], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        data = output.read_bytes()
        self.assertTrue(json.loads(data)["valid"])
        duplicate = subprocess.run(args + ["--output", str(output)], capture_output=True, text=True)
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertEqual(output.read_bytes(), data)
        forbidden = self.package / "new-result.json"
        nested = subprocess.run(args + ["--output", str(forbidden)], capture_output=True, text=True)
        self.assertNotEqual(nested.returncode, 0)
        self.assertFalse(forbidden.exists())
        self.assertEqual((self.package / "render-report.json").read_bytes(), self.report_original)
        mutate_report(self.package, lambda r: r.update(synthetic=False))
        failed = subprocess.run(args, capture_output=True, text=True)
        self.assertNotEqual(failed.returncode, 0)

    def test_symlink_asset_cannot_read_outside_package(self):
        asset = self.package / "frame-0133.png"
        outside = self.root / "outside-original.png"
        original = asset.read_bytes()
        outside.write_bytes(original)
        asset.unlink()
        try:
            try:
                asset.symlink_to(outside)
            except OSError as error:
                self.skipTest(f"OS refused test symlink creation; no privilege changes: {error}")
            self.rejected("symlink-asset")
            self.assertEqual(outside.read_bytes(), original)
        finally:
            if asset.is_symlink():
                asset.unlink()

    def test_hardlink_asset_cannot_alias_an_outside_file(self):
        asset = self.package / "frame-0133.png"
        outside = self.root / "outside-hardlink-original.png"
        original = asset.read_bytes()
        outside.write_bytes(original)
        asset.unlink()
        try:
            try:
                os.link(outside, asset)
            except OSError as error:
                self.skipTest(f"OS refused isolated hardlink; no privilege changes: {error}")
            self.assertGreater(asset.stat().st_nlink, 1)
            self.rejected("hardlink-asset")
            self.assertEqual(outside.read_bytes(), original)
        finally:
            if asset.exists():
                asset.unlink()

    def test_mutated_critical_gates_are_killed_by_independent_negative_tests(self):
        cases = [
            ("sha", {"PNG bytes or SHA256 differ from report."}, "test_rejects_asset_sha_mismatch"),
            ("time", {"Track elapsed time differs from its frame."}, "test_rejects_track_time_drift"),
            ("environment", {"Look/environment metadata differs from expectations."}, "test_rejects_environment_drift"),
            ("inventory", {"Package contains missing or unexpected files.", "Package changed during verification."},
             "test_rejects_unknown_file"),
        ]
        original = CHECKER.read_bytes()
        for name, details, test_name in cases:
            with self.subTest(mutant=name):
                tree, changed = ast.parse(original.decode("utf-8-sig")), 0
                for node in ast.walk(tree):
                    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "require"
                            and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant)
                            and node.args[1].value in details):
                        node.args[0] = ast.Constant(value=True)
                        changed += 1
                self.assertEqual(changed, len(details), "Mutation selector must hit the actual intended gates")
                mutant = types.ModuleType("pc3_test_only_mutant_" + name)
                mutant.__file__ = str(CHECKER)
                exec(compile(ast.fix_missing_locations(tree), "<test-only-mutant-" + name + ">", "exec"), mutant.__dict__)
                with mock.patch.object(self.validator, "verify_package", mutant.verify_package):
                    result = unittest.TestResult()
                    RenderPackageTests(test_name).run(result)
                self.assertEqual(result.testsRun, 1)
                self.assertEqual(len(result.errors), 0, result.errors)
                self.assertEqual(len(result.failures), 1, f"Mutant {name} survived the independent test")
                MUTATION_RESULTS.append({"name": name, "disabledGates": changed,
                                         "negativeTest": test_name, "killed": True})
        self.assertEqual(CHECKER.read_bytes(), original)
        self.assertEqual(self.backup.read_bytes(), original)

    def test_junction_or_linked_package_directory_is_rejected(self):
        linked = self.root / "linked-package"
        if os.name == "nt":
            created = subprocess.run(["cmd", "/c", "mklink", "/J", str(linked), str(self.package)],
                                     capture_output=True, text=True)
            if created.returncode:
                self.skipTest(f"OS refused isolated test junction: {created.stderr}")
        else:
            linked.symlink_to(self.package, target_is_directory=True)
        try:
            self.rejected("linked-package-directory", package=linked)
            self.assertEqual((self.package / "render-report.json").read_bytes(), self.report_original)
        finally:
            # Remove only this verified test link, never recursively remove its target.
            self.assertEqual(linked.parent.resolve(), self.root.resolve())
            if linked.is_symlink():
                linked.unlink()
            elif os.name == "nt" and linked.is_junction():
                linked.rmdir()

    def test_original_checker_bytes_remain_unchanged(self):
        self.assertEqual(CHECKER.read_bytes(), self.checker_bytes)
        self.assertEqual(self.backup.read_bytes(), self.checker_bytes)


if __name__ == "__main__":
    unittest.main()
