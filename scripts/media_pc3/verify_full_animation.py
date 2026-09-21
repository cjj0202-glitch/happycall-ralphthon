"""Read-only M5 verification of a completed 1080p, 288-PNG candidate.

The manifest is an independent pc1 input, never inferred from the report. This
checks stored bytes and declarations; it does not render, decode pixels/video,
authenticate pc1, re-open receipt sources, or grant visual/product acceptance.
The existing 720p verifier is imported read-only for safe I/O and route math.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re

try:
    from . import verify_render_package as common
    from . import full_render_gate as gate
    from .environment_detail import environment_specs
except ImportError:
    import verify_render_package as common
    import full_render_gate as gate
    from environment_detail import environment_specs


Invalid = common.Invalid
require = common.require
same = common.same
number = common.number
parse_json = common.parse_json
load_expectations = common.load_expectations
FRAME_COUNT = 288
NAMES = {"render-report.json", "tracks.json", "case-0002-ww3.blend"} | {
    f"frame-{frame:04d}.png" for frame in range(1, FRAME_COUNT + 1)}
CAMERA_LAYOUT = {"camera": {"id": "SYN-CAM-02", "fixed": True,
                          "position": [24, 1, 8], "lookAt": [17, 7, .85], "lensMm": 32}}
NOTICE = ("Machine checks of 291 stored files against an independently supplied manifest. "
          "Source/layout/fixture/receipt bytes and review evidence are not present in this package: "
          "their embedded declarations are compared, not re-executed or re-hashed here. "
          "sceneReadback/threads describe the pre-render snapshot; runtimeSamples was recorded at report creation. "
          "PNG structure/CRC does not decode pixels. No Blend inspection, final Blender readback, "
          "MP4 encoding, visual acceptance or issuer authentication is performed.")


def _descriptor(value, name=None):
    require(type(value) is dict and set(value) == {"name", "bytes", "sha256"},
            "Expected an exact name/bytes/sha256 descriptor.", "DESCRIPTOR")
    return common.descriptor(value, name)


def _dependencies(values):
    require(type(values) is list and len(values) == 5,
            "Exactly five generator dependency descriptors are required.", "SOURCE")
    parsed = [_descriptor(item) for item in values]
    require({item["name"] for item in parsed} == gate.DEPENDENCIES,
            "Missing, duplicate or unexpected generator dependency.", "SOURCE")
    return {item["name"]: item for item in parsed}


def _settings(value):
    require(same(value, gate.SETTINGS), "Settings differ from the fixed full-animation contract.", "SETTINGS")
    require(all(type(value[key]) is int for key in ("samples", "shadowRays", "threads", "fps", "frames"))
            and all(type(item) is int for item in value["resolution"]),
            "Frame, resolution and render counts must be strict integers.", "SETTINGS")


def _verified_files(values, expected):
    require(type(values) is list and len(values) == 12,
            "Review verification must declare exactly twelve referenced files.", "RECEIPT")
    paths, roles, representatives = {expected["receipt"]["name"].casefold()}, {}, set()
    dependencies = _dependencies(expected["sourceDependencies"])
    for item in values:
        require(type(item) is dict and set(item) == {"role", "path", "bytes", "sha256"},
                "Malformed reviewed file reference.", "RECEIPT")
        relative = item["path"]
        require(type(relative) is str and relative and "\\" not in relative and ":" not in relative,
                "Reviewed references must be relative POSIX paths.", "PATH")
        parts = relative.split("/")
        for part in parts:
            common._safe_name(part)
        require(relative.casefold() not in paths, "Duplicate reviewed file path.", "RECEIPT")
        paths.add(relative.casefold())
        name = parts[-1]
        parsed = _descriptor({"name": name, "bytes": item["bytes"], "sha256": item["sha256"]})
        role = item["role"]
        require(type(role) is str, "Invalid reviewed file role.", "RECEIPT")
        roles[role] = roles.get(role, 0) + 1
        if role in ("generator", "layout", "fixture"):
            require(same(parsed, expected[role]), "Reviewed source/input differs from independent expectations.", "RECEIPT")
        elif role == "dependency":
            require(name in dependencies and same(parsed, dependencies[name]),
                    "Reviewed dependency differs from independent expectations.", "RECEIPT")
            dependencies.pop(name)
        elif role == "reviewed-representative":
            require(name in {"frame-0001.png", "frame-0133.png", "frame-0288.png"}
                    and name not in representatives, "Reviewed representative identity differs.", "RECEIPT")
            representatives.add(name)
        elif role == "reviewed-short-report":
            require(name == "render-report.json", "Reviewed short evidence has the wrong filename.", "RECEIPT")
        else:
            raise Invalid("RECEIPT", "Unknown reviewed file role.")
    require(roles == {"generator": 1, "layout": 1, "fixture": 1, "dependency": 5,
                      "reviewed-representative": 3, "reviewed-short-report": 1} and not dependencies,
            "Review references do not contain the complete source/evidence roles.", "RECEIPT")
    return sorted(values, key=lambda item: (item["role"], item["path"]))


def _expectations(value):
    common._json_tree(value)
    fields = {"schemaVersion", "sourceCommit", "mode", "generator", "sourceDependencies", "layout", "fixture",
              "receipt", "settings", "look", "environmentDetail", "reviewId", "verifiedFiles"}
    require(type(value) is dict and set(value) == fields, "Missing or unexpected manifest fields.", "EXPECTATIONS")
    require(value["schemaVersion"] == "pc3-full-animation-expectations-v1" and value["mode"] == "animation",
            "Manifest must describe the full-animation v1 contract.", "EXPECTATIONS")
    require(type(value["sourceCommit"]) is str and re.fullmatch(r"[0-9a-f]{40}", value["sourceCommit"]),
            "Manifest sourceCommit must be a 40-character lowercase SHA declaration.", "EXPECTATIONS")
    for key, name in (("generator", "build_scene.py"), ("layout", "scene-layout-v1.json"), ("fixture", "cases.json")):
        _descriptor(value[key], name)
    _descriptor(value["receipt"])
    require(value["receipt"]["name"].endswith(".json"), "Receipt descriptor must name a JSON file.", "EXPECTATIONS")
    _dependencies(value["sourceDependencies"])
    _settings(value["settings"])
    require(same(value["look"], common.B_LOOK), "Manifest look differs from the fixed B preset.", "EXPECTATIONS")
    require(same(value["environmentDetail"], environment_specs("staging_v1")),
            "Manifest environment differs from the fixed 48-object staging specification.", "EXPECTATIONS")
    common._safe_name(value["reviewId"])
    _verified_files(value["verifiedFiles"], value)


def _animation_review(value, expected):
    require(type(value) is dict and set(value) == {"requestedSha256", "verified"}
            and value["requestedSha256"] == expected["receipt"]["sha256"],
            "Requested receipt hash differs from the independent manifest.", "RECEIPT")
    verified = value["verified"]
    keys = {"schemaVersion", "receipt", "reviewId", "scope", "settings", "verifiedFiles",
            "issuerAuthenticated", "visualAccepted", "notice"}
    require(type(verified) is dict and set(verified) == keys,
            "Review verification metadata is incomplete or unexpected.", "RECEIPT")
    fixed = {"schemaVersion": "pc3-animation-review-verification-v1", "receipt": expected["receipt"],
             "reviewId": expected["reviewId"], "scope": gate.SCOPE, "settings": expected["settings"],
             "issuerAuthenticated": False, "visualAccepted": False}
    require(all(same(verified[key], item) for key, item in fixed.items()),
            "Review verification differs from independent expectations or overclaims acceptance.", "RECEIPT")
    _descriptor(verified["receipt"])
    _settings(verified["settings"])
    require(type(verified["notice"]) is str and 0 < len(verified["notice"]) <= 4096,
            "Review metadata must retain a bounded explanatory notice.", "RECEIPT")
    require(same(_verified_files(verified["verifiedFiles"], expected),
                 _verified_files(expected["verifiedFiles"], expected)),
            "Embedded review evidence differs from the independently fixed receipt records.", "RECEIPT")


def _report(report, expected):
    fixed = {"schemaVersion": "pc3-blender-candidate-v1", "synthetic": True,
             "status": "unreviewed-render-candidate", "visualGateAccepted": False, "mainRegistration": False,
             "videoEncoded": False, "engine": "BLENDER_EEVEE_NEXT", "resolution": [1920, 1080],
             "eventAnchor": common.ANCHOR, "cameraId": "SYN-CAM-02", "clockMode": common.CLOCK,
             "clippedFrames": [], "occlusionAndVisualContactReviewed": False, "representativeFrames": [1, 133, 288],
             "look": expected["look"], "environmentDetail": expected["environmentDetail"],
             "colorManagement": {"viewTransform": "AgX", "exposure": 0, "gamma": 1}}
    for key, value in fixed.items():
        require(key in report and same(report[key], value), "Report setting/event/provenance differs: " + key, "REPORT")
    for key, value in (("seed", 20260921), ("fps", 24), ("candidateFrameCount", 288),
                       ("renderedFrameCount", 288), ("requestedSamples", 96)):
        require(type(report.get(key)) is int and report[key] == value, "Report integer count differs: " + key, "REPORT")
    require(all(type(item) is int for item in report["resolution"] + report["representativeFrames"]),
            "Report frame IDs and resolution must be integers.", "REPORT")
    require(common._close(report.get("candidateDurationSeconds"), 12)
            and number(report.get("wallSeconds")) and report["wallSeconds"] > 0,
            "Report duration or measured elapsed time is invalid.", "REPORT")
    require(type(report.get("blenderVersion")) is str and re.fullmatch(r"4\.5\.\d+(?: LTS)?", report["blenderVersion"]),
            "Report lacks Blender 4.5 version evidence.", "REPORT")
    for key in ("generator", "layout", "fixture"):
        require(same(_descriptor(report.get(key)), expected[key]), "Source/input differs from independent manifest: " + key, "SOURCE")
    require(same(_dependencies(report.get("sourceDependencies")), _dependencies(expected["sourceDependencies"])),
            "Generator dependency bytes or hashes differ from independent manifest.", "SOURCE")
    runtime = report.get("runtimeSamples")
    require(type(runtime) is dict and runtime.get("property") == "scene.eevee.taa_render_samples"
            and type(runtime.get("value")) is int and runtime["value"] == 96,
            "Report-creation sample readback must be 96.", "READBACK")
    shadow = report.get("shadowRays")
    require(type(shadow) is dict and type(shadow.get("requested")) is int and shadow["requested"] == 4
            and type(shadow.get("actual")) is int and shadow["actual"] == 4 and shadow.get("applied") is True
            and shadow.get("property") == "scene.eevee.shadow_ray_count"
            and same(shadow.get("range"), {"cli": [1, 4], "runtime": {"min": 1, "max": 4}}),
            "Shadow metadata must record actual four-ray EEVEE readback.", "READBACK")
    require(all(type(item) is int for item in shadow["range"]["cli"] + list(shadow["range"]["runtime"].values())),
            "Shadow range must use integers.", "READBACK")
    threads = report.get("threads")
    require(same(threads, {"requested": 2, "actual": 2, "mode": "FIXED"})
            and type(threads["requested"]) is int and type(threads["actual"]) is int,
            "Pre-render thread readback must be FIXED two threads.", "READBACK")
    try:
        gate.validate_scene_readback(report.get("sceneReadback"), CAMERA_LAYOUT)
    except gate.GateError as error:
        raise Invalid("READBACK", "Pre-render scene readback differs from the fixed full-animation contract.") from error
    _animation_review(report.get("animationReview"), expected)
    for key in ("sourceCommit", "mode"):
        require(key not in report or same(report[key], expected[key]),
                "Supplemental source/mode assertion conflicts with the independent manifest.", "REPORT")


def _tracks(value):
    fixed = {"source": "synthetic-scene-ground-truth", "synthetic": True, "eventAnchor": common.ANCHOR,
             "coordinateSpace": "normalized-image-top-left", "resolution": [1920, 1080], "clockMode": common.CLOCK,
             "cameraId": "SYN-CAM-02", "cameraPosition": [24, 1, 8], "cameraLensMm": 32,
             "sensorWidthMm": 36, "occlusionTested": False, "clippedFrames": []}
    require(all(key in value and same(value[key], expected) for key, expected in fixed.items()),
            "Tracks camera/event/resolution/provenance differs.", "TRACKS")
    require(type(value.get("frameCount")) is int and value["frameCount"] == 288
            and type(value.get("fps")) is int and value["fps"] == 24
            and all(type(item) is int for item in value["resolution"]), "Tracks frame count/fps/resolution differs.", "TRACKS")
    rows = value.get("frames")
    require(type(rows) is list and len(rows) == 288, "Tracks must contain all 288 rows.", "TRACKS")
    for frame, row in enumerate(rows, 1):
        require(type(row) is dict and type(row.get("frame")) is int and row["frame"] == frame
                and common._close(row.get("elapsedSeconds"), (frame - 1) / 24),
                "Track frame order or elapsed time differs.", "TRACKS")
        require(row.get("visualObjectId") == common.ANCHOR["visualObjectId"]
                and "businessToteId" in row and row["businessToteId"] is None and row.get("fullyInFrame") is True,
                "Track object/tote identity or visibility declaration differs.", "TRACKS")
        position, yaw, phase = common._motion(frame)
        require(row.get("phase") == phase and common._vector(row.get("worldPosition"), 3)
                and all(common._close(a, b, 1e-6) for a, b in zip(row["worldPosition"], position))
                and common._close(row.get("yawRadians"), yaw, 1e-6)
                and common._close(row.get("contactPlaneGapMeters"), 0, 1e-5),
                "Track route/phase/yaw/contact-plane data differs.", "TRACKS")
        box = row.get("bboxNormalizedXYXY")
        require(common._vector(box, 4) and all(0 <= item <= 1 for item in box)
                and box[0] < box[2] and box[1] < box[3], "Track bounding box is not ordered and normalized.", "TRACKS")
        # Normalized projection depends on aspect, and 1920/1080 == 1280/720.
        require(all(common._close(a, b, 2e-5) for a, b in zip(box, common._projected_bbox(position, yaw))),
                "Track bounding box differs from the fixed camera/parcel projection.", "TRACKS")


def _result():
    return {"schemaVersion": "pc3-full-animation-verification-v1", "valid": False, "status": "FAIL",
            "failures": [], "pending": [
                {"code": "SOURCE_RECEIPT_BYTES_NOT_RECHECKED", "detail": "The package contains no source/layout/fixture/receipt or reviewed evidence files; their declarations are compared to external expectations."},
                {"code": "FINAL_SCENE_READBACK_NOT_RUN", "detail": "sceneReadback/threads are pre-render snapshots, not a new post-completion Blender inspection."},
                {"code": "PIXEL_DECODE_NOT_RUN", "detail": "PNG structure, CRC and dimensions only; compressed pixels are not decoded."},
                {"code": "MP4_ENCODING_NOT_CHECKED", "detail": "288 PNG files are not an encoded video; no MP4 is inspected or accepted."},
                {"code": "VISUAL_REVIEW_PENDING", "detail": "Blend geometry, visibility, physical contact, motion and visual quality require separate review."},
                {"code": "AUTHENTICITY_UNVERIFIED", "detail": "Manifest and report declarations do not authenticate pc1 or prove the executing commit."}],
            "visualAccepted": False, "pixelDecoded": False, "videoDecoded": False, "authenticityVerified": False,
            "inputDigests": [], "images": [], "mode": "animation", "sourceCommit": None, "notice": NOTICE}


def _stamp(path):
    info = common._safe_path(path).stat()
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def verify_full_animation(package: Path, expected: dict) -> dict:
    """Return sanitized machine-check results without writing any file.

    expected must originate independently from pc1's fixed inputs and receipt.
    A valid result is still PASS_WITH_PENDING, never visual/product acceptance.
    """
    result = _result()
    try:
        _expectations(expected)
        expected = copy.deepcopy(expected)
        result["sourceCommit"] = expected["sourceCommit"]
        result["expectationsCanonicalSha256"] = hashlib.sha256(json.dumps(
            expected, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()
        directory = common._safe_path(package, directory=True)
        entries = list(directory.iterdir())
        require(len(entries) == 291 and {path.name for path in entries} == NAMES
                and len({path.name.casefold() for path in entries}) == 291,
                "Completed animation must contain exactly the fixed 291 files.", "INVENTORY")
        stamps = {path.name: _stamp(path) for path in entries}
        raw, actual = common._file(directory, "render-report.json", read=True, limit=4*1024*1024)
        result["inputDigests"].append(actual)
        report = parse_json(raw)
        _report(report, expected)
        for name, key in (("tracks.json", "tracks"), ("case-0002-ww3.blend", "blend")):
            declared = _descriptor(report.get(key), name)
            raw, actual = common._file(directory, name, read=key == "tracks")
            result["inputDigests"].append(actual)
            require(same(actual, declared), "Tracks/Blend bytes or SHA256 differ from the report.", "ASSET")
            if key == "tracks":
                _tracks(parse_json(raw))
        rendered = report.get("rendered")
        require(type(rendered) is list and len(rendered) == 288,
                "Report must declare exactly 288 rendered PNG files.", "FRAMES")
        for frame, item in enumerate(rendered, 1):
            name = f"frame-{frame:04d}.png"
            declared = common.descriptor(item, name)
            require(type(item.get("frame")) is int and item["frame"] == frame
                    and common._close(item.get("elapsedSeconds"), (frame-1)/24)
                    and number(item.get("renderSeconds")) and item["renderSeconds"] > 0,
                    "Rendered PNG frame/time/order/timing differs.", "FRAMES")
            raw, actual = common._file(directory, name, read=True, limit=64*1024*1024)
            result["inputDigests"].append(actual)
            require(same(actual, declared), "PNG bytes or SHA256 differ from the report.", "ASSET")
            try:
                gate._png(raw)
            except gate.GateError as error:
                raise Invalid("PNG", "PNG structure, CRC or 1920x1080 RGB/RGBA format is invalid.") from error
            result["images"].append({**actual, "frame": frame, "elapsedSeconds": (frame-1)/24})
        require({path.name for path in directory.iterdir()} == NAMES
                and all(_stamp(directory / name) == stamp for name, stamp in stamps.items()),
                "Package changed during verification.", "INPUT_CHANGED")
        result.update({"valid": True, "status": "PASS_WITH_PENDING"})
    except Exception as error:
        common._failure(result, error)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--expectations", required=True, type=Path)
    args = parser.parse_args()
    try:
        package = common._safe_path(args.package, directory=True)
        manifest = common._safe_path(args.expectations)
        require(not manifest.is_relative_to(package), "Manifest must be outside the received output package.", "PATH")
        raw, digest = common._file(manifest.parent, manifest.name, read=True, limit=2*1024*1024)
        expected = parse_json(raw)
        result = verify_full_animation(package, expected)
        _, after = common._file(manifest.parent, manifest.name)
        require(same(digest, after), "Independent manifest changed during verification.", "INPUT_CHANGED")
        result["expectationsFileDigest"] = digest
    except Exception as error:
        result = common._failure(_result(), error)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
