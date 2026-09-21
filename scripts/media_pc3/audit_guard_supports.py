"""Read-only numeric guard audit: source AST cuboids and yaw OBB/AABB SAT.

No bpy import, Blender launch, scene generation, rendering, or product mutation.
The optional output JSON is an audit report, not Blender execution evidence.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from scene_contract import FRAME_COUNT, evaluate_motion, load_layout

ROOT = Path(__file__).resolve().parents[2]
EPSILON = 1e-9


def cube_label(node):
    value = node.value if isinstance(node, (ast.Expr, ast.Assign)) else None
    if (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
            and value.func.id == "cube" and value.args
            and isinstance(value.args[0], ast.Constant)):
        return value.args[0].value
    return None


def source_cuboids(source: str, layout: dict) -> list[dict]:
    """Execute only the observed primitive construction statements in a recorder.

    Import/attribute access/function definitions/arbitrary calls are forbidden.
    build_scene.build itself is never imported or invoked.
    """
    tree = ast.parse(source)
    build = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "build")
    start = next(i for i, node in enumerate(build.body) if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == "path" for target in node.targets))
    stop = next(i for i, node in enumerate(build.body) if isinstance(node, ast.FunctionDef) and node.name == "leg")
    guard_start = next(i for i, node in enumerate(build.body) if cube_label(node) == "North yellow safety rail")
    guard_stop = next(i for i, node in enumerate(build.body) if cube_label(node) == "Electrical cabinet")
    parcel_names = {"Selected synthetic parcel carton", "Parcel taped lid", "Blank synthetic parcel label"}
    parcel_nodes = [node for node in build.body if cube_label(node) in parcel_names]
    if len(parcel_nodes) != 3 or not start < stop < guard_start < guard_stop:
        raise ValueError("Source geometry boundaries changed; review extractor before auditing")
    subset = ast.Module(body=build.body[start:stop] + build.body[guard_start:guard_stop] + parcel_nodes, type_ignores=[])
    allowed = (ast.Module, ast.Assign, ast.AugAssign, ast.Expr, ast.For, ast.While, ast.If,
               ast.Name, ast.Load, ast.Store, ast.Constant, ast.List, ast.Tuple,
               ast.Subscript, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare,
               ast.Call, ast.keyword, ast.Add, ast.Sub, ast.Mult, ast.Div,
               ast.UAdd, ast.USub, ast.Not, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
               ast.And, ast.Or, ast.Eq, ast.NotEq, ast.In, ast.NotIn)
    for node in ast.walk(subset):
        if not isinstance(node, allowed):
            raise ValueError(f"Disallowed geometry AST node: {type(node).__name__}")
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name)
                or node.func.id not in {"cube", "cylinder", "range"}):
            raise ValueError("Geometry extractor permits only primitive recorder/range calls")
    shapes = []
    calls = 0

    def record_cube(name, location, dimensions, mat, bevel=0.0, parent=None):
        nonlocal calls
        calls += 1
        if calls > 1000:
            raise ValueError("Geometry recorder call limit exceeded")
        if len(location) != 3 or len(dimensions) != 3 or min(dimensions) <= 0:
            raise ValueError("Invalid source cuboid")
        item = {"name": name, "center": list(location), "dimensions": list(dimensions),
                "bevelMeters": bevel, "parented": parent is not None}
        shapes.append(item)
        return item

    def discard_cylinder(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls > 1000:
            raise ValueError("Geometry recorder call limit exceeded")

    scope = {"__builtins__": {}, "layout": layout,
             "mats": {key: key for key in ("belt", "steel", "yellow", "frame", "card", "tape", "white")},
             "cube": record_cube, "cylinder": discard_cylinder, "range": range, "root": "parcel-parent"}
    exec(compile(subset, "<numeric-source-cuboid-recorder>", "exec"), scope)
    return shapes


def aabb(box):
    return ([box["center"][i] - box["dimensions"][i] / 2 for i in range(3)],
            [box["center"][i] + box["dimensions"][i] / 2 for i in range(3)])


def overlap_lengths(first, second):
    a, b = aabb(first), aabb(second)
    return [min(a[1][i], b[1][i]) - max(a[0][i], b[0][i]) for i in range(3)]


def connection_check(supports, shapes):
    rows = []
    for index, post in enumerate(supports):
        if post["name"].startswith("North"):
            rail_name, frame_name = "North yellow safety rail", "Main conveyor side channel"
        elif post["name"].startswith("South"):
            rail_name, frame_name = "South interrupted safety rail", "Main conveyor side channel"
        elif post["name"].startswith("Outfeed"):
            rail_name, frame_name = "Outfeed side guard", "CH02 side frame"
        else:
            raise ValueError(f"Unknown guard family: {post['name']}")
        connected = {}
        for kind, name in (("rail", rail_name), ("frame", frame_name)):
            candidates = [item for item in shapes if item["name"] == name]
            matches = [{"center": item["center"], "overlapXYZMeters": overlap_lengths(post, item)}
                       for item in candidates if min(overlap_lengths(post, item)) > EPSILON]
            connected[kind] = matches
        rows.append({"index": index, **post, "railConnections": connected["rail"],
                     "frameConnections": connected["frame"],
                     "supported": bool(connected["rail"] and connected["frame"])})
    return rows


def parcel_intersects_post(part, position, yaw, post):
    """Exact separating axes for source yaw-only cuboid versus axis-aligned post.

    Mesh bevels remove material, so original cuboid collision is conservative.
    Touching within epsilon is not reported as positive-volume penetration.
    """
    c, s = math.cos(yaw), math.sin(yaw)
    local, half = part["center"], [v / 2 for v in part["dimensions"]]
    center = [position[0] + local[0] * c - local[1] * s,
              position[1] + local[0] * s + local[1] * c, position[2] + local[2]]
    delta = [post["center"][i] - center[i] for i in range(3)]
    other = [v / 2 for v in post["dimensions"]]
    if abs(delta[2]) >= half[2] + other[2] - EPSILON:
        return False
    ac, ass = abs(c), abs(s)
    # World X/Y and parcel local X/Y are the four distinct horizontal axes.
    return (abs(delta[0]) < other[0] + half[0] * ac + half[1] * ass - EPSILON
            and abs(delta[1]) < other[1] + half[0] * ass + half[1] * ac - EPSILON
            and abs(delta[0] * c + delta[1] * s) < half[0] + other[0] * ac + other[1] * ass - EPSILON
            and abs(-delta[0] * s + delta[1] * c) < half[1] + other[0] * ass + other[1] * ac - EPSILON)


def collision_check(times, layout, parcel, supports):
    hits, hit_count, samples = [], 0, 0
    for time_seconds in times:
        samples += 1
        motion = evaluate_motion(time_seconds, layout)
        for part in parcel:
            for index, post in enumerate(supports):
                if parcel_intersects_post(part, motion["position"], motion["yaw_radians"], post):
                    hit_count += 1
                    if len(hits) < 30:
                        hits.append({"elapsedSeconds": time_seconds, "part": part["name"], "postIndex": index})
    return {"poseCount": samples, "positiveVolumeIntersections": hit_count, "firstIntersections": hits}


def audit(source_path, layout_path, fixture_path):
    source_bytes = source_path.read_bytes()
    layout = load_layout(layout_path, fixture_path=fixture_path)
    shapes = source_cuboids(source_bytes.decode("utf-8-sig"), layout)
    supports = [item for item in shapes if item["name"].endswith("guard support")]
    expected = {"North guard support": 6, "South guard support": 6, "Outfeed guard support": 6}
    if dict(Counter(item["name"] for item in supports)) != expected:
        raise ValueError("Expected the reviewed six supports per guard family")
    parcel = [item for item in shapes if item["parented"]]
    connections = connection_check(supports, shapes)
    if not all(row["supported"] for row in connections):
        raise ValueError("A current support does not intersect both a source rail and source frame")
    rail_shapes = [item for item in shapes if item["name"] in {
        "North yellow safety rail", "South interrupted safety rail", "Outfeed side guard"}]
    if len(rail_shapes) != 5:
        raise ValueError("Expected five reviewed rail segments")
    rail_coverage = []
    for rail in rail_shapes:
        support_indices = [index for index, post in enumerate(supports)
                           if min(overlap_lengths(post, rail)) > EPSILON]
        rail_coverage.append({"name": rail["name"], "center": rail["center"],
                              "dimensions": rail["dimensions"],
                              "connectedSupportCount": len(support_indices), "supportIndices": support_indices})
    if not all(row["connectedSupportCount"] >= 1 for row in rail_coverage):
        raise ValueError("A source rail segment has no connected support")

    # Failure control from the reviewed pre-fix source, against current frame
    # geometry: vertical overlap alone must not hide the 10 mm horizontal gap.
    legacy = [{"name": "North guard support", "center": [x, 8.28, .94],
               "dimensions": [.04, .05, .24], "bevelMeters": .005, "parented": False}
              for x in [10, 12.5, 15, 17, 20, 22.5]]
    legacy_rows = connection_check(legacy, shapes)
    north_frame = next(item for item in shapes if item["name"] == "Main conveyor side channel" and item["center"][1] > 7.5)
    gaps = [-overlap_lengths(post, north_frame)[1] for post in legacy]
    if any(row["supported"] for row in legacy_rows) or not all(math.isclose(gap, .01, abs_tol=1e-9) for gap in gaps):
        raise ValueError("Legacy 10 mm disconnection was not rejected by the audit")

    body = next(item for item in parcel if item["name"] == "Selected synthetic parcel carton")
    positive = parcel_intersects_post(body, [supports[0]["center"][0], supports[0]["center"][1], .85], 0, supports[0])
    negative = parcel_intersects_post(body, [-100, -100, .85], math.pi / 4, supports[0])
    # A nearby post overlaps the rotated parcel's enclosing AABB but is outside
    # the actual OBB. This detects accidental replacement of SAT with AABB-only.
    rotated_post = {**supports[0], "center": [.34, .34, .935]}
    rotated_extent = (body["dimensions"][0] + body["dimensions"][1]) / math.sqrt(2)
    rotated_bounds = {"center": [0, 0, .85 + body["center"][2]],
                      "dimensions": [rotated_extent, rotated_extent, body["dimensions"][2]]}
    near_aabb_overlaps = min(overlap_lengths(rotated_bounds, rotated_post)) > EPSILON
    near_obb_separated = not parcel_intersects_post(body, [0, 0, .85], math.pi / 4, rotated_post)
    if not positive or negative or not near_aabb_overlaps or not near_obb_separated:
        raise ValueError("Collision detector positive/negative control failed")
    dense = collision_check((i / 1000 for i in range(12001)), layout, parcel, supports)
    frames = collision_check(((i - 1) / 24 for i in range(1, FRAME_COUNT + 1)), layout, parcel, supports)
    if dense["positiveVolumeIntersections"] or frames["positiveVolumeIntersections"]:
        raise ValueError(f"Parcel/support collision: {dense}; {frames}")
    if source_path.read_bytes() != source_bytes:
        raise ValueError("Generator changed during audit; rerun against a stable source")
    return {"schemaVersion": "pc3-guard-numeric-audit-v1", "checkedAt": datetime.now(timezone.utc).isoformat(),
            "method": "Source-AST primitive cuboid recorder and yaw OBB/AABB separating-axis mathematics",
            "blenderExecuted": False, "rendered": False, "status": "PASS-numeric-only",
            "source": {"path": str(source_path.relative_to(ROOT)), "sha256": hashlib.sha256(source_bytes).hexdigest()},
            "layoutSha256": hashlib.sha256(layout_path.read_bytes()).hexdigest(),
            "supportCount": len(supports), "connectedSupportCount": sum(row["supported"] for row in connections),
            "connections": connections, "railSegmentCoverage": rail_coverage,
            "legacyRedControl": {"tested": len(legacy), "rejectedDisconnectedSupports": sum(not row["supported"] for row in legacy_rows), "horizontalGapMeters": gaps},
            "collisionDetectorControls": {"intentionalCollisionDetected": positive, "farSeparatedRejected": not negative,
                "rotatedAabbFalsePositiveRejectedBySat": near_aabb_overlaps and near_obb_separated},
            "denseTimeSampling": dense, "renderFrameTimes": frames,
            "unchangedInputs": ["camera/path/event/tote keys are read only by this audit"],
            "limitations": ["No bpy API execution, scene build, render, or visual acceptance.",
                "Intersection uses source cuboids before bevel, not Blender-evaluated meshes.",
                "Positive volume overlap is a modeled attachment check, not structural engineering validation.",
                "Sampling includes 12001 1 ms poses and all 288 integer frame times; not a continuous-time proof.",
                "Ray occlusion, lighting, shadows, texture quality and representative image acceptance remain with pc1."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=ROOT / "scripts/media_pc3/build_scene.py")
    parser.add_argument("--fixture", type=Path, default=ROOT / "data/fixtures/cases.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.source.resolve(), args.layout.resolve(), args.fixture.resolve())
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "supportCount", "connectedSupportCount", "railSegmentCoverage",
        "legacyRedControl", "collisionDetectorControls", "denseTimeSampling", "renderFrameTimes", "blenderExecuted")}, indent=2))


if __name__ == "__main__":
    main()
