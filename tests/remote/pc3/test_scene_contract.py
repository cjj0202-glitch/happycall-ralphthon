"""Independent scene-contract checks; standard library only, no Blender/API.

When the main-owned planning file is not yet in a worker checkout, the exact
already-fetched e5469aa Git object provides the source. No fetch/pull is run.
Temporary JSON inputs are isolated; the fixture and shared layout are unchanged.
"""
from __future__ import annotations

import copy
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/media_pc3"))
from scene_contract import (FRAME_COUNT, SCENE_SEED, evaluate_motion, load_layout,
                            validate_layout)


class SceneContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = ROOT / "planning/media/scene-layout-v1.json"
        cls.raw = source.read_text(encoding="utf-8-sig") if source.exists() else subprocess.check_output(
            ["git", "show", "e5469aa:planning/media/scene-layout-v1.json"], cwd=ROOT, text=True, encoding="utf-8")
        cls.layout = json.loads(cls.raw)
        cls.fixture_path = ROOT / "data/fixtures/cases.json"
        cls.fixture = json.loads(cls.fixture_path.read_text(encoding="utf-8-sig"))

    def test_shared_layout_load_and_fixture_anchor(self):
        original = copy.deepcopy(self.layout)
        with tempfile.TemporaryDirectory(prefix="pc3-scene-contract-") as temporary:
            path = Path(temporary) / "layout.json"
            path.write_text(self.raw, encoding="utf-8")
            self.assertEqual(load_layout(path, self.fixture_path), original)
        self.assertEqual(self.layout, original)

    def test_schema_synthetic_geometry_camera_and_semantic_mutations_rejected(self):
        mutations = [
            ("schemaVersion", "real-layout"), ("synthetic", False),
            ("geometrySource", "source-pdf-coordinates"), ("units", "cm"),
            ("camera.fixed", False), ("camera.id", "SYN-CAM-OTHER"),
            ("eventAnchor.caseId", "CASE-0001"), ("eventAnchor.eventId", "W-W4"),
            ("eventAnchor.occurredAt", "2026-09-18T03:02:00+09:00"),
            ("eventAnchor.chuteId", "CH-01"), ("eventAnchor.dockId", "D-01"),
            ("eventAnchor.businessToteId", "SYN-TOTE02-A"),
            ("eventAnchor.visualObjectId", "SYN-TOTE02-B"),
            ("animation.durationSeconds", 10), ("animation.fps", 30),
            ("animation.actualIncidentReconstruction", True),
            ("animation.trackSource", "video-ai-detector"),
            ("animation.clockMode", "real-cctv-clock"),
            ("animation.seed", SCENE_SEED + 1),
            ("visualPath.sourceBcrTrace", True), ("visualPath.speedMeasured", True),
        ]
        for field, value in mutations:
            with self.subTest(field=field):
                layout = copy.deepcopy(self.layout)
                target = layout
                pieces = field.split(".")
                for key in pieces[:-1]:
                    target = target[key]
                target[pieces[-1]] = value
                with self.assertRaises(ValueError):
                    validate_layout(layout)

    def test_nonfinite_boolean_bad_vector_and_route_drift_rejected(self):
        for value in (float("nan"), float("inf"), -float("inf"), 10 ** 400, True, None, "0.85"):
            with self.subTest(value=value):
                layout = copy.deepcopy(self.layout)
                layout["visualPath"]["points"][0][2] = value
                with self.assertRaises(ValueError):
                    validate_layout(layout)
        for change in (lambda c: c["visualPath"]["points"].pop(),
                       lambda c: c["visualPath"]["points"][2].__setitem__(0, 20),
                       lambda c: c["zones"][0].__setitem__("bounds", [-1, 9, 8, 7]),
                       lambda c: c["zones"][1].__setitem__("id", c["zones"][0]["id"]),
                       lambda c: c["animation"]["phaseSeconds"].__setitem__("branch", [3, 5])):
            layout = copy.deepcopy(self.layout)
            change(layout)
            with self.assertRaises(ValueError):
                validate_layout(layout)

    def test_camera_and_all_zone_coordinates_are_pinned_to_layout_v1(self):
        validate_layout(self.layout, self.fixture)
        for field in ("position", "lookAt"):
            for index in range(3):
                with self.subTest(camera_field=field, coordinate=index):
                    layout = copy.deepcopy(self.layout)
                    layout["camera"][field][index] += 0.25
                    with self.assertRaises(ValueError):
                        validate_layout(layout)
        layout = copy.deepcopy(self.layout)
        layout["camera"]["lensMm"] = 33
        with self.assertRaises(ValueError):
            validate_layout(layout)
        # Each mutation stays finite, positive and inside the floor. Rejection
        # therefore checks exact scene geometry, not merely generic bounds.
        for zone_index in range(6):
            for coordinate in range(4):
                with self.subTest(zone=zone_index, coordinate=coordinate):
                    layout = copy.deepcopy(self.layout)
                    layout["zones"][zone_index]["bounds"][coordinate] += 0.05
                    with self.assertRaises(ValueError):
                        validate_layout(layout)

    def test_duplicate_json_key_and_nonfinite_json_rejected(self):
        with tempfile.TemporaryDirectory(prefix="pc3-scene-contract-") as temporary:
            path = Path(temporary) / "bad.json"
            for raw in ('{"synthetic": true, "synthetic": false}', '{"camera": NaN}'):
                path.write_text(raw, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_layout(path)

    def test_fixture_anchor_mismatches_and_duplicate_event_rejected(self):
        mutations = [
            lambda c: c["wms"]["events"][2].__setitem__("time", "2026-09-19T02:33:00+09:00"),
            lambda c: c.__setitem__("asOf", "2026-09-18T02:32:00+09:00"),
            lambda c: c["wms"]["sorting"].__setitem__("rsltChuteNo", "CH-01"),
            lambda c: c["wms"]["shipping"].__setitem__("dock", "D-01"),
            lambda c: c["wms"]["events"][2].__setitem__("toteId", "SYN-TOTE02-A"),
            lambda c: c["media"][0].__setitem__("cameraId", "OTHER"),
            lambda c: c["wms"]["events"].append(copy.deepcopy(c["wms"]["events"][2])),
        ]
        for index, change in enumerate(mutations):
            with self.subTest(index=index):
                fixture = copy.deepcopy(self.fixture)
                case = next(item for item in fixture["cases"] if item["id"] == "CASE-0002")
                change(case)
                with self.assertRaises(ValueError):
                    validate_layout(self.layout, fixture)

    def test_unknown_branch_tote_is_not_filled_from_known_other_processes(self):
        case = next(item for item in self.fixture["cases"] if item["id"] == "CASE-0002")
        self.assertNotEqual(case["wms"]["picking"]["toteId"], case["wms"]["shipping"]["toteId"])
        for t in (0, 3, 4.5, 6, 10, 12):
            state = evaluate_motion(t, self.layout)
            self.assertIsNone(state["businessToteId"])
            self.assertEqual(state["visualObjectId"], "SYN-VIS-PARCEL02")
            self.assertEqual(state["trackSource"], "synthetic-scene-ground-truth")

    def test_time_validation_and_phase_boundaries(self):
        for value in (-0.001, 12.001, float("nan"), float("inf"), True, None, "3"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                evaluate_motion(value, self.layout)
        expected = [(0, "approach"), (2.999, "approach"), (3, "branch"),
                    (5.999, "branch"), (6, "chute"), (9.999, "chute"),
                    (10, "settle"), (12, "settle")]
        for t, phase in expected:
            self.assertEqual(evaluate_motion(t, self.layout)["phase"], phase)

    def test_endpoint_and_support_surface_semantics(self):
        self.assertEqual(evaluate_motion(0, self.layout)["position"], [10, 7.5, 0.85])
        self.assertEqual(evaluate_motion(3, self.layout)["position"], [16, 7.5, 0.85])
        for t in (10, 11, 12):
            result = evaluate_motion(t, self.layout)
            self.assertEqual(result["position"], [18.5, 4.5, 0.85])
            self.assertEqual(result["yaw_radians"], -math.pi / 2)

    def test_all_288_frames_deterministic_finite_monotonic_and_in_path_bounds(self):
        before = copy.deepcopy(self.layout)
        frames = [evaluate_motion(index / 24, self.layout) for index in range(FRAME_COUNT)]
        self.assertEqual(len(frames), 288)
        self.assertEqual(frames, [evaluate_motion(index / 24, self.layout) for index in range(FRAME_COUNT)])
        self.assertEqual(self.layout, before)
        for index, frame in enumerate(frames):
            x, y, z = frame["position"]
            self.assertTrue(all(math.isfinite(n) for n in (x, y, z, frame["yaw_radians"])))
            self.assertTrue(10 <= x <= 18.5 and 4.5 <= y <= 7.5)
            self.assertEqual(z, 0.85)
            self.assertEqual(frame["seed"], SCENE_SEED)
            self.assertTrue(-math.pi / 2 <= frame["yaw_radians"] <= 0)
            if index:
                previous = frames[index - 1]
                self.assertGreater(frame["time_seconds"], previous["time_seconds"])
                self.assertGreaterEqual(x + 1e-12, previous["position"][0])
                self.assertLessEqual(y - 1e-12, previous["position"][1])
                self.assertLessEqual(frame["yaw_radians"], previous["yaw_radians"] + 1e-12)
                self.assertLess(math.dist(frame["position"], previous["position"]), 0.15)

    def test_phase_boundary_position_and_velocity_continuity(self):
        epsilon = 1e-5
        for t in (3, 6, 10):
            a = evaluate_motion(t - epsilon, self.layout)["position"]
            b = evaluate_motion(t, self.layout)["position"]
            c = evaluate_motion(t + epsilon, self.layout)["position"]
            left = [(y - x) / epsilon for x, y in zip(a, b)]
            right = [(y - x) / epsilon for x, y in zip(b, c)]
            self.assertLess(math.dist(left, right), 1e-4, (t, left, right))
            self.assertLess(math.dist(a, c), 0.00003)
        self.assertEqual(evaluate_motion(10, self.layout)["position"],
                         evaluate_motion(12, self.layout)["position"])

    def test_rounded_corner_tangent_matches_yaw_without_an_orientation_jump(self):
        epsilon = 1e-5
        samples = [3 + index / 100 for index in range(1, 300)]
        turned = []
        for t in samples:
            state = evaluate_motion(t, self.layout)
            before = evaluate_motion(t - epsilon, self.layout)["position"]
            after = evaluate_motion(t + epsilon, self.layout)["position"]
            tangent = math.atan2(after[1] - before[1], after[0] - before[0])
            self.assertAlmostEqual(tangent, state["yaw_radians"], delta=2e-5)
            if state["yaw_radians"] < 0:
                turned.append(state)
        self.assertGreater(len(turned), 50)
        self.assertTrue(all(17.5 <= item["position"][0] <= 18.5 and 6.5 <= item["position"][1] <= 7.5
                            for item in turned))


if __name__ == "__main__":
    unittest.main()
