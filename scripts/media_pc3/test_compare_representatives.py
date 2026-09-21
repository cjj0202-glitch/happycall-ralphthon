"""Synthetic comparison-validator fixtures, not Blender renders or visual proof.

Only isolated temporary inputs are created. The PNGs are valid flat-color test
images; reported sample counts/version strings are deliberately fabricated test
data. Passing this suite does not authenticate a renderer or approve a look.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from compare_representatives import compare_runs
from look_presets import settings_for
from scene_contract import SCENE_SEED, evaluate_motion, load_layout


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def digest(path):
    data = path.read_bytes()
    return {"name": path.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def png(width=1280, height=720, color=(40, 60, 80)):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    rows = (b"\0" + bytes(color) * width) * height
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def make_run(directory: Path, look: str) -> dict:
    """Create a new synthetic test run; refuse to overwrite an existing folder."""
    directory = Path(directory)
    directory.mkdir()
    planning = ROOT / "planning/media/scene-layout-v1.json"
    layout_path = planning if planning.exists() else ROOT / ".local/pc3-blender/input/scene-layout-v1.json"
    layout = load_layout(layout_path, ROOT / "data/fixtures/cases.json")
    frames = []
    for frame in range(1, 289):
        motion = evaluate_motion((frame - 1) / 24, layout)
        frames.append({"frame": frame, "elapsedSeconds": (frame - 1) / 24,
                       "visualObjectId": "SYN-VIS-PARCEL02", "businessToteId": None,
                       "worldPosition": motion["position"], "yawRadians": motion["yaw_radians"],
                       "phase": motion["phase"], "bboxNormalizedXYXY": [0.4, 0.3, 0.55, 0.6],
                       "fullyInFrame": True, "contactPlaneGapMeters": 0})
    anchor, clock = layout["eventAnchor"], layout["animation"]["clockMode"]
    tracking = {"source": "synthetic-scene-ground-truth", "synthetic": True, "eventAnchor": anchor,
                "coordinateSpace": "normalized-image-top-left", "fps": 24, "frameCount": 288,
                "resolution": [1280, 720], "clockMode": clock, "cameraId": "SYN-CAM-02",
                "cameraPosition": [24, 1, 8], "cameraLensMm": 32, "sensorWidthMm": 36,
                "occlusionTested": False, "frames": frames, "clippedFrames": [],
                "notice": "SYNTHETIC TEST FIXTURE: bbox values are not Blender projections."}
    write_json(directory / "tracks.json", tracking)
    image = png(color=(40, 60, 80) if look == "baseline" else (25, 35, 50))
    rendered = []
    for frame in (1, 133, 288):
        path = directory / f"frame-{frame:04d}.png"
        path.write_bytes(image)
        rendered.append({**digest(path), "frame": frame, "elapsedSeconds": (frame - 1) / 24, "renderSeconds": 0})
    blend = directory / "case-0002-ww3.blend"
    blend.write_bytes(b"SYNTHETIC TEST PLACEHOLDER: not a Blender file.\n")
    report = {"schemaVersion": "pc3-blender-candidate-v1", "synthetic": True,
              "status": "unreviewed-render-candidate", "visualGateAccepted": False, "mainRegistration": False,
              "seed": SCENE_SEED, "blenderVersion": "4.5.0", "engine": "BLENDER_EEVEE_NEXT",
              "engineDevice": "Synthetic test report; no runtime device", "requestedSamples": 32,
              "resolution": [1280, 720], "fps": 24,
              "runtimeSamples": {"property": "scene.eevee.taa_render_samples", "value": 32, "note": "Fabricated fixture value"},
              "look": {"name": look, "settings": settings_for(look)},
              "colorManagement": {"viewTransform": "AgX", "exposure": 0, "gamma": 1},
              "candidateDurationSeconds": 12, "candidateFrameCount": 288, "renderedFrameCount": 3,
              "wallSeconds": 0, "layout": digest(layout_path), "generator": digest(ROOT / "scripts/media_pc3/build_scene.py"),
              "eventAnchor": anchor, "sourceDependencies": [digest(ROOT / "scripts/media_pc3" / name)
                                                          for name in ("scene_contract.py", "look_presets.py")],
              "cameraId": "SYN-CAM-02", "clockMode": clock, "representativeFrames": [1, 133, 288],
              "rendered": rendered, "blend": digest(blend), "tracks": digest(directory / "tracks.json"),
              "clippedFrames": [], "occlusionAndVisualContactReviewed": False, "videoEncoded": False,
              "note": "SYNTHETIC TEST FIXTURE ONLY. No Blender execution or visual acceptance."}
    write_json(directory / "render-report.json", report)
    return report


class RepresentativeComparisonTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="pc3-comparison-test-")
        self.addCleanup(temporary.cleanup)
        self.a, self.b = Path(temporary.name) / "a", Path(temporary.name) / "b"
        self.a_report = make_run(self.a, "baseline")
        self.b_report = make_run(self.b, "contrast_material_v1")

    def rejected(self):
        result = compare_runs(self.a, self.b)
        self.assertIs(result["comparable"], False)
        self.assertIs(result["visualAccepted"], False)
        self.assertTrue(result["failures"])
        self.assertTrue(all(isinstance(item.get("code"), str) and isinstance(item.get("detail"), str)
                            for item in result["failures"]))

    def report_variants(self, variants):
        for name, mutate in variants:
            with self.subTest(name=name):
                report = copy.deepcopy(self.b_report)
                mutate(report)
                write_json(self.b / "render-report.json", report)
                self.rejected()

    def test_happy_pair_is_comparable_not_visually_accepted_and_inputs_unchanged(self):
        before = {str(path): path.read_bytes() for folder in (self.a, self.b) for path in folder.iterdir()}
        result = compare_runs(self.a, self.b)
        self.assertIs(result["comparable"], True, result["failures"])
        self.assertEqual(result["schemaVersion"], "pc3-representative-comparison-v1")
        self.assertEqual(result["failures"], [])
        self.assertIs(result["visualAccepted"], False)
        self.assertEqual(before, {str(path): path.read_bytes() for folder in (self.a, self.b) for path in folder.iterdir()})

    def test_corrupt_png_signature_and_wrong_ihdr_dimensions_with_matching_digest(self):
        for data in (b"not a PNG", png(width=640)):
            with self.subTest(size=len(data)):
                path = self.b / "frame-0133.png"
                path.write_bytes(data)
                report = copy.deepcopy(self.b_report)
                report["rendered"][1].update(digest(path))
                write_json(self.b / "render-report.json", report)
                self.rejected()

    def test_missing_fixed_assets(self):
        for name in ("render-report.json", "tracks.json", "frame-0001.png"):
            path = self.b / name
            original = path.read_bytes()
            with self.subTest(name=name):
                path.unlink()
                self.rejected()
            path.write_bytes(original)

    def test_asset_hash_and_byte_mismatches(self):
        self.report_variants([(f"{asset}-{field}", lambda r, a=asset, f=field: (r["rendered"][0] if a == "png" else r["tracks"]).__setitem__(f, "0" * 64 if f == "sha256" else 1))
                              for asset in ("png", "tracks") for field in ("sha256", "bytes")])

    def test_cross_run_generator_layout_and_dependency_changes(self):
        self.report_variants([(name, lambda r, n=name: (r["sourceDependencies"][0] if n == "dependency" else r[n]).__setitem__("sha256", "1" * 64))
                              for name in ("generator", "layout", "dependency")])

    def test_unverified_or_mismatched_runtime_samples(self):
        self.report_variants([(str(value), lambda r, v=value: r["runtimeSamples"].__setitem__("value", v)) for value in (None, 16, True, "32", float("nan"), float("inf"), -float("inf"))]
                             + [("wrong property", lambda r: r["runtimeSamples"].__setitem__("property", "requestedSamples"))])

    def test_look_and_report_contract_mismatches(self):
        self.report_variants([
            ("wrong look", lambda r: r["look"].__setitem__("name", "baseline")),
            ("wrong settings", lambda r: r["look"]["settings"]["concrete"].__setitem__("roughness", 0.9)),
            ("camera", lambda r: r.__setitem__("cameraId", "OTHER")),
            ("event", lambda r: r["eventAnchor"].__setitem__("eventId", "W-W4")),
            ("time", lambda r: r["eventAnchor"].__setitem__("occurredAt", "2026-09-19T02:33:00+09:00")),
            ("tote", lambda r: r["eventAnchor"].__setitem__("businessToteId", "SYN-TOTE02-A")),
            ("render count", lambda r: r.__setitem__("renderedFrameCount", 4)),
            ("extra render", lambda r: r["rendered"].append(copy.deepcopy(r["rendered"][0]))),
            ("boolean render frame", lambda r: r["rendered"][0].__setitem__("frame", True)),
            ("main accepted", lambda r: r.__setitem__("mainRegistration", True)),
        ])

    def test_tracks_metadata_clock_identity_and_content_mismatches(self):
        original = json.loads((self.b / "tracks.json").read_text(encoding="utf-8"))
        variants = [("camera", lambda t: t.__setitem__("cameraId", "OTHER")),
                    ("case", lambda t: t["eventAnchor"].__setitem__("caseId", "CASE-0001")),
                    ("clock", lambda t: t.__setitem__("clockMode", "real-time")),
                    ("tote", lambda t: t["frames"][0].__setitem__("businessToteId", "TOTE")),
                    ("elapsed", lambda t: t["frames"][132].__setitem__("elapsedSeconds", 6)),
                    ("boolean track frame", lambda t: t["frames"][0].__setitem__("frame", True)),
                    ("pose diff", lambda t: t["frames"][100]["worldPosition"].__setitem__(0, 15.9)),
                    ("missing frame", lambda t: t["frames"].pop())]
        for name, mutate in variants:
            with self.subTest(name=name):
                tracking = copy.deepcopy(original)
                mutate(tracking)
                write_json(self.b / "tracks.json", tracking)
                report = copy.deepcopy(self.b_report)
                report["tracks"] = digest(self.b / "tracks.json")
                write_json(self.b / "render-report.json", report)
                self.rejected()

    def test_asset_path_traversal_and_absolute_names(self):
        self.report_variants([(name, lambda r, n=name: r["rendered"][0].__setitem__("name", n))
                              for name in ("../outside.png", "..\\outside.png", "/tmp/outside.png", "C:\\outside.png")]
                             + [("tracks traversal", lambda r: r["tracks"].__setitem__("name", "../tracks.json"))])

    def test_identically_wrong_business_identity_in_both_runs_is_rejected(self):
        for directory, report in ((self.a, self.a_report), (self.b, self.b_report)):
            tracking = json.loads((directory / "tracks.json").read_text(encoding="utf-8"))
            tracking["frames"][0]["businessToteId"] = "UNVERIFIED-TOTE"
            write_json(directory / "tracks.json", tracking)
            report["tracks"] = digest(directory / "tracks.json")
            write_json(directory / "render-report.json", report)
        self.rejected()

    def test_viewer_embeds_verified_originals_and_rejects_changed_image(self):
        from build_review_page import build_html
        result = compare_runs(self.a, self.b)
        page = build_html(self.a, self.b, result)
        self.assertEqual(page.count("data:image/png;base64,"), 6)
        self.assertIn("visualAccepted=false", page)
        image = self.b / "frame-0133.png"
        image.write_bytes(png(color=(100, 100, 100)))
        with self.assertRaises(ValueError):
            build_html(self.a, self.b, result)

    def test_malformed_and_nonobject_report_or_tracks_json(self):
        for name in ("render-report.json", "tracks.json"):
            for data in ("{bad json", "[]"):
                with self.subTest(name=name, data=data):
                    write_json(self.b / "render-report.json", self.b_report)
                    path = self.b / name
                    path.write_text(data, encoding="utf-8")
                    if name == "tracks.json":
                        report = copy.deepcopy(self.b_report)
                        report["tracks"] = digest(path)
                        write_json(self.b / "render-report.json", report)
                    self.rejected()


if __name__ == "__main__":
    unittest.main()
