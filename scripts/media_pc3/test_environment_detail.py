"""Independent static geometry checks; no bpy, render, pixel or shadow claims.

Cylinder/bevel geometry uses conservative AABBs. Ray tests cover all 24 original
parcel-part corners at each of 288 poses, against new props only. They do not
certify full rendered visibility, shadows, contacts or between-frame behavior.
"""
from __future__ import annotations

import ast
from collections import Counter
import copy
import itertools
import math
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_guard_supports import aabb, overlap_lengths, parcel_intersects_post, source_cuboids
from environment_detail import environment_specs
from scene_contract import FRAME_COUNT, evaluate_motion, load_layout
from test_look_presets import actual_arguments, function, record_look

ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "scripts/media_pc3/build_scene.py"
EPS = 1e-9
AISLE = {"center": [15.25, 9.4, 1.1], "dimensions": [10.5, 1.6, 2.2]}


def prop_box(prop):
    if prop["primitive"] == "cube":
        dimensions = prop["dimensions"]
    else:
        dimensions = [2 * prop["radius"]] * 3
        dimensions["XYZ".index(prop["axis"])] = prop["depth"]
    return {"name": prop["name"], "center": prop["location"], "dimensions": dimensions}


def corners(part, motion):
    c, s = math.cos(motion["yaw_radians"]), math.sin(motion["yaw_radians"])
    for signs in itertools.product((-1, 1), repeat=3):
        x, y, z = [part["center"][i] + signs[i] * part["dimensions"][i] / 2 for i in range(3)]
        p = motion["position"]
        yield [p[0] + x * c - y * s, p[1] + x * s + y * c, p[2] + z]


def segment_hits_box(start, end, box):
    """Closed segment/slab test; tangency is conservatively a possible occluder."""
    low, high = aabb(box)
    enter, leave = 0.0, 1.0
    for axis in range(3):
        direction = end[axis] - start[axis]
        if abs(direction) < EPS:
            if start[axis] < low[axis] - EPS or start[axis] > high[axis] + EPS:
                return False
        else:
            first, last = sorted(((low[axis] - start[axis]) / direction,
                                  (high[axis] - start[axis]) / direction))
            enter, leave = max(enter, first), min(leave, last)
            if enter > leave + EPS:
                return False
    return leave >= 0 and enter <= 1


def project_point(point, camera):
    """Independent pinhole approximation: horizontal 36 mm sensor, 1280x720."""
    def unit(v):
        length = math.sqrt(sum(n * n for n in v))
        return [n / length for n in v]
    def cross(a, b):
        return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
    forward = unit([b - a for a, b in zip(camera["position"], camera["lookAt"])])
    right = unit(cross(forward, [0, 0, 1]))
    up = cross(right, forward)
    delta = [b - a for a, b in zip(camera["position"], point)]
    depth = sum(a * b for a, b in zip(delta, forward))
    scale = camera["lensMm"] / 36 / depth
    return [.5 + scale * sum(a * b for a, b in zip(delta, right)),
            .5 - scale * (1280 / 720) * sum(a * b for a, b in zip(delta, up)), depth]


def aisle_hits(props):
    # Only actual ground paint at <=2 cm is excluded; a tall mislabelled cue is not.
    return [p["name"] for p in props if not
            (p["group"] == "floor-cue" and aabb(prop_box(p))[0][2] >= -EPS
             and aabb(prop_box(p))[1][2] <= .02 + EPS)
            and min(overlap_lengths(prop_box(p), AISLE)) > EPS]


def sample_checks(props, layout, parcel):
    boxes = [prop_box(p) for p in props]
    hits, occlusions, max_y = 0, 0, -math.inf
    for index in range(FRAME_COUNT):
        motion = evaluate_motion(index / 24, layout)
        for part in parcel:
            hits += sum(parcel_intersects_post(part, motion["position"], motion["yaw_radians"], b)
                        for b in boxes)
            for point in corners(part, motion):
                max_y = max(max_y, point[1])
                occlusions += sum(segment_hits_box(layout["camera"]["position"], point, b) for b in boxes)
    return {"poses": FRAME_COUNT, "parcelParts": len(parcel), "props": len(boxes),
            "routePairs": FRAME_COUNT * len(parcel) * len(boxes),
            "cameraSegments": FRAME_COUNT * len(parcel) * 8,
            "segmentBoxPairs": FRAME_COUNT * len(parcel) * 8 * len(boxes),
            "routeIntersections": hits, "rayIntersections": occlusions, "maxParcelCornerY": max_y}


def environment_loop(source):
    build = function(ast.parse(source), "build")
    matches = [node for node in build.body if isinstance(node, ast.For)
               and any(isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                       and call.func.id == "environment_specs" for call in ast.walk(node.iter))]
    if len(matches) != 1:
        raise ValueError("Expected one explicit environment-only insertion")
    return build, matches[0]


class EnvironmentDetailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = GENERATOR.read_text(encoding="utf-8-sig")
        cls.previous = subprocess.check_output(["git", "show", "d67b2c7:scripts/media_pc3/build_scene.py"],
                                               cwd=ROOT, text=True, encoding="utf-8")
        planning = ROOT / "planning/media/scene-layout-v1.json"
        cls.layout = load_layout(planning if planning.exists() else ROOT / ".local/pc3-blender/input/scene-layout-v1.json",
                                 ROOT / "data/fixtures/cases.json")
        cls.props = environment_specs("staging_v1")["objects"]
        cls.parcel = [p for p in source_cuboids(cls.source, cls.layout) if p["parented"]]
        cls.samples = sample_checks(cls.props, cls.layout, cls.parcel)

    def test_none_is_empty_and_snapshots_are_independent(self):
        self.assertEqual(environment_specs("none")["objects"], [])
        first = environment_specs("staging_v1")
        self.assertEqual(first, environment_specs("staging_v1"))
        first["objects"][0]["location"][0] = -999
        first["objects"][0]["tracked"] = True
        self.assertEqual(environment_specs("staging_v1")["objects"], self.props)
        for bad in (None, False, 0, [], {}, "", "STAGING_V1", "../staging_v1"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                environment_specs(bad)

    def test_exact_static_nonbusiness_inventory_and_finite_geometry(self):
        self.assertEqual(Counter(p["group"] for p in self.props),
                         {"rollcage-1": 17, "rollcage-2": 17, "staging-rack": 6,
                          "staging-cartons": 4, "floor-cue": 4})
        self.assertEqual(len({p["name"] for p in self.props}), 48)
        for p in [environment_specs("staging_v1"), *self.props]:
            self.assertIs(p["synthetic"], True)
            self.assertIs(p["tracked"], False)
            self.assertIsNone(p["businessToteId"])
            self.assertEqual((p["motion"], p["role"]), ("static", "synthetic-environment"))
        for p in self.props:
            box = prop_box(p)
            self.assertTrue(all(math.isfinite(v) for v in box["center"] + box["dimensions"]))
            self.assertGreater(min(box["dimensions"]), 0)
            self.assertIn(p["material"], {"steel", "frame", "card", "yellow"})
            low, high = aabb(box)
            self.assertGreaterEqual(min(low), -EPS)
            self.assertLessEqual(high[0], 30)
            self.assertLessEqual(high[1], 18)

    def test_actual_adapter_emits_each_prop_once_static_and_untracked(self):
        _, loop = environment_loop(self.source)
        module = ast.Module(body=[loop], type_ignores=[])
        for call in (n for n in ast.walk(loop) if isinstance(n, ast.Call)):
            self.assertIsInstance(call.func, ast.Name)
            self.assertIn(call.func.id, {"environment_specs", "cube", "cylinder"})
        for name in ("none", "staging_v1"):
            emitted = []
            def cube(n, location, dimensions, material, bevel=0, parent=None):
                row = {"name": n, "location": location, "dimensions": dimensions,
                       "material": material, "bevel": bevel, "parent": parent, "primitive": "cube"}
                emitted.append(row)
                return row
            def cylinder(n, location, radius, depth, material, axis="Z"):
                row = {"name": n, "location": location, "radius": radius, "depth": depth,
                       "material": material, "axis": axis, "primitive": "cylinder"}
                emitted.append(row)
                return row
            tracked = [object(), object(), object()]
            scope = {"__builtins__": {}, "args": SimpleNamespace(environment_detail=name),
                     "environment_specs": environment_specs, "cube": cube, "cylinder": cylinder,
                     "mats": {v: v for v in ("steel", "frame", "card", "yellow")}, "tracked": tracked}
            exec(compile(module, "<actual-environment-adapter>", "exec"), scope)
            self.assertIs(scope["tracked"], tracked)
            self.assertEqual(len(tracked), 3)
            self.assertEqual(len(emitted), len(environment_specs(name)["objects"]))
            for expected, row in zip(environment_specs(name)["objects"], emitted):
                for key in ("name", "location", "primitive", "material"):
                    self.assertEqual(row[key], expected[key])
                for key in ("dimensions", "bevel", "radius", "depth", "axis"):
                    if key in expected:
                        self.assertEqual(row[key], expected[key])
                self.assertIs(row.get("parent"), None)
                self.assertEqual((row["role"], row["synthetic"], row["tracked"], row["motion"]),
                                 ("synthetic-environment", True, False, "static"))
                self.assertEqual(row["businessToteId"], "null (unassigned environment prop)")

    def test_original_build_and_core_helpers_ast_unchanged(self):
        current, loop = environment_loop(self.source)
        current.body.remove(loop)
        old_tree = ast.parse(self.previous)
        self.assertEqual(ast.dump(current), ast.dump(function(old_tree, "build")))
        for name in ("tracks", "camera", "cube", "cylinder", "area", "material", "aim"):
            self.assertEqual(ast.dump(function(ast.parse(self.source), name)), ast.dump(function(old_tree, name)), name)
        self.assertEqual(source_cuboids(self.source, self.layout), source_cuboids(self.previous, self.layout))
        for look in ("baseline", "contrast_material_v1"):
            self.assertEqual(record_look(self.source, look), record_look(self.previous, look))
        for name in ("scene_contract.py", "look_presets.py"):
            old = subprocess.check_output(["git", "show", f"d67b2c7:scripts/media_pc3/{name}"], cwd=ROOT,
                                          text=True, encoding="utf-8")
            self.assertEqual(ast.dump(ast.parse((GENERATOR.parent / name).read_text(encoding="utf-8-sig"))),
                             ast.dump(ast.parse(old)), name)

    def test_cli_default_and_review_only_modes(self):
        flags = ["--layout", "layout.json", "--output", "output"]
        current, previous = actual_arguments(self.source, flags), actual_arguments(self.previous, flags)
        self.assertEqual(current.environment_detail, "none")
        self.assertEqual({k: v for k, v in vars(current).items() if k != "environment_detail"}, vars(previous))
        for look, env, mode in itertools.product(("baseline", "contrast_material_v1"),
                                                ("none", "staging_v1"),
                                                ("prepare", "representatives", "short", "animation")):
            options = flags + ["--look", look, "--environment-detail", env, "--mode", mode]
            with self.subTest(look=look, env=env, mode=mode):
                if mode == "animation" and (look != "baseline" or env != "none"):
                    with self.assertRaises(SystemExit) as err:
                        actual_arguments(self.source, options)
                    self.assertEqual(err.exception.code, 2)
                else:
                    self.assertEqual(actual_arguments(self.source, options).environment_detail, env)
        for env in ("STAGING_V1", "../staging_v1", "unknown"):
            with self.subTest(env=env), self.assertRaises(SystemExit):
                actual_arguments(self.source, flags + ["--environment-detail", env])

    def test_actual_report_metadata_and_optional_dependency_only(self):
        main = function(ast.parse(self.source), "main")
        report = next(n.value for n in main.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "report" for t in n.targets))
        index = next(i for i, key in enumerate(report.keys) if key.value == "environmentDetail")
        expression = ast.Expression(body=report.values.pop(index))
        report.keys.pop(index)
        dependency_if = next(n for n in main.body if isinstance(n, ast.If)
                             and "args.environment_detail" in ast.unparse(n.test))
        main.body.remove(dependency_if)
        self.assertEqual(ast.dump(main), ast.dump(function(ast.parse(self.previous), "main")))
        for name in ("none", "staging_v1"):
            scope = {"args": SimpleNamespace(environment_detail=name), "environment_specs": environment_specs,
                     "report": {"sourceDependencies": ["scene_contract.py", "look_presets.py"]},
                     "digest": lambda path: Path(path).name, "Path": Path, "__file__": str(GENERATOR)}
            detail = eval(compile(expression, "<actual-environment-report>", "eval"), scope)
            self.assertEqual(detail, environment_specs(name))
            exec(compile(ast.Module(body=[dependency_if], type_ignores=[]), "<actual-dependency-gate>", "exec"), scope)
            self.assertEqual(scope["report"]["sourceDependencies"],
                             ["scene_contract.py", "look_presets.py"] +
                             (["environment_detail.py"] if name == "staging_v1" else []))

    def test_aisle_and_floor_contact_cartons_supported(self):
        self.assertEqual(aisle_hits(self.props), [])
        boxes = [prop_box(p) for p in self.props]
        for prop, box in zip(self.props, boxes):
            low, high = aabb(box)
            if prop["group"] != "floor-cue":
                self.assertGreaterEqual(low[1], 10.5 - EPS)
            else:
                for i, limits in enumerate(((12.4, 16), (10.2, 11.6), (0, .008))):
                    self.assertGreaterEqual(low[i], limits[0] - EPS)
                    self.assertLessEqual(high[i], limits[1] + EPS)
            if "WHEEL" in prop["name"] or "RACK-POST" in prop["name"]:
                self.assertAlmostEqual(low[2], 0)
            if prop["group"] == "staging-cartons":
                supports = [b for p, b in zip(self.props, boxes) if "RACK-SHELF" in p["name"]
                            and abs(aabb(b)[1][2] - low[2]) < EPS
                            and min(overlap_lengths(b, box)[:2]) > EPS]
                self.assertEqual(len(supports), 1)
        # Conservative contact graph must connect every part to floor-supported props.
        grounded = {i for i, box in enumerate(boxes) if abs(aabb(box)[0][2]) < EPS}
        while True:
            grown = grounded | {i for i, b in enumerate(boxes) if any(
                min(overlap_lengths(b, boxes[j])) >= -EPS for j in grounded)}
            if grown == grounded:
                break
            grounded = grown
        self.assertEqual(len(grounded), len(boxes))

    def test_all_288_poses_and_6912_camera_segments_clear_new_props(self):
        self.assertEqual(self.samples["poses"], 288)
        self.assertEqual(self.samples["cameraSegments"], 6912)
        self.assertEqual(self.samples["routePairs"], 41472)
        self.assertEqual(self.samples["segmentBoxPairs"], 331776)
        self.assertEqual(self.samples["routeIntersections"], 0)
        self.assertEqual(self.samples["rayIntersections"], 0)
        self.assertLess(self.samples["maxParcelCornerY"], 8)

    def test_all_384_new_prop_corners_within_fixed_camera_pinhole_frame(self):
        points = [point for p in self.props for point in itertools.product(*zip(*aabb(prop_box(p))))]
        self.assertEqual(len(points), 384)
        for point in points:
            x, y, depth = project_point(point, self.layout["camera"])
            self.assertGreater(depth, 0)
            self.assertTrue(0 <= x <= 1 and 0 <= y <= 1, (point, x, y))
        # The original x=19.5 rack was clipped: this check must detect it.
        old_rack = {"center": [19.5, 12.4, .825], "dimensions": [3.6, 1, 1.65]}
        old_points = itertools.product(*zip(*aabb(old_rack)))
        self.assertTrue(any(project_point(p, self.layout["camera"])[0] > 1 for p in old_points))

    def test_detectors_reject_injected_route_ray_and_mislabelled_aisle_blockers(self):
        motion = evaluate_motion(5.5, self.layout)
        route = {"center": [*motion["position"][:2], 1.025], "dimensions": [.5, .5, .5]}
        self.assertTrue(parcel_intersects_post(self.parcel[0], motion["position"], motion["yaw_radians"], route))
        point = next(corners(self.parcel[0], motion))
        cam = self.layout["camera"]["position"]
        blocker = {"center": [(a + b) / 2 for a, b in zip(cam, point)], "dimensions": [.1] * 3}
        self.assertTrue(segment_hits_box(cam, point, blocker))
        blocker["center"][1] += 3
        self.assertFalse(segment_hits_box(cam, point, blocker))
        for group, height in (("staging-rack", .5), ("floor-cue", .5)):
            fake = copy.deepcopy(self.props[0])
            fake.update(group=group, location=[15, 9.4, height / 2], dimensions=[.5, .5, height])
            self.assertEqual(aisle_hits([fake]), [fake["name"]])
        fake.update(group="floor-cue", location=[15, 9.4, .004], dimensions=[.5, .5, .008])
        self.assertEqual(aisle_hits([fake]), [])

    def test_source_not_changed_during_checks(self):
        self.assertEqual(GENERATOR.read_text(encoding="utf-8-sig"), self.source)


if __name__ == "__main__":
    unittest.main()
