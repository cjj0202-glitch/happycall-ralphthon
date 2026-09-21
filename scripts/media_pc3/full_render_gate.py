"""Fail-closed, read-only receipt gate for a reviewed full-animation candidate.

The separately supplied exact receipt SHA is the trust boundary. This module
does not authenticate an issuer, issue receipts, judge image quality or render.
All dependencies are from the Python standard library.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import zlib


SETTINGS = {"camera": "cctv", "resolution": [1920, 1080], "engine": "eevee", "samples": 96,
            "shadowRays": 4, "look": "contrast_material_v1", "environmentDetail": "staging_v1",
            "threads": 2, "fps": 24, "frames": 288}
DEPENDENCIES = {"scene_contract.py", "look_presets.py", "shadow_settings.py",
                "environment_detail.py", "full_render_gate.py"}
ANCHOR = {"caseId": "CASE-0002", "eventId": "W-W3", "occurredAt": "2026-09-18T02:33:00+09:00",
          "chuteId": "CH-02", "dockId": "D-02", "businessToteId": None, "visualObjectId": "SYN-VIS-PARCEL02"}
CLOCK = "illustrative-elapsed-separate-from-event-time"
SCOPE = "synthetic-full-animation-candidate"
B_LOOK = {"name": "contrast_material_v1", "settings": {
    "worldStrength": .12,
    "lightEnergies": {"Large soft loading-side light": 1800, "Ceiling key": 3300, "Warehouse fill": 650, "Chute rim": 900},
    "concrete": {"color": [.20, .215, .225], "roughness": .43, "bumpStrength": .06, "bumpDistance": .002},
    "steel": {"color": [.32, .35, .38], "metallic": .88, "roughness": .24}}}


class GateError(ValueError):
    """Receipt/input/readback mismatch: caller must stop before rendering."""


def require(condition, message):
    if not condition:
        raise GateError(message)


def number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def same(actual, expected):
    if number(expected):
        return number(actual) and actual == expected
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(same(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(same(a, b) for a, b in zip(actual, expected))
    return actual == expected


def _finite_tree(value, depth=0):
    require(depth <= 50, "Receipt JSON nesting is too deep.")
    if value is None or type(value) in (str, bool):
        return
    if type(value) in (int, float):
        require(number(value), "Non-finite JSON number is forbidden.")
    elif type(value) is list:
        for item in value:
            _finite_tree(item, depth + 1)
    elif type(value) is dict:
        require(all(type(key) is str for key in value), "JSON keys must be strings.")
        for item in value.values():
            _finite_tree(item, depth + 1)
    else:
        raise GateError("Unsupported JSON value type.")


def _json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key is forbidden.")
            result[key] = value
        return result
    def constant(_):
        raise GateError("Non-finite JSON constant is forbidden.")
    try:
        value = json.loads(data.decode("utf-8-sig"), object_pairs_hook=pairs, parse_constant=constant)
        _finite_tree(value)
        require(type(value) is dict, "Receipt/report must be a JSON object.")
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError, OverflowError) as error:
        raise GateError("Invalid receipt/report JSON.") from error


def _safe_file(path):
    path = Path(path)
    require(".." not in path.parts, "Parent path traversal is forbidden.")
    path = path if path.is_absolute() else Path.cwd() / path
    for entry in (*reversed(path.parents), path):
        info = entry.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not (getattr(info, "st_file_attributes", 0) & 0x400),
                "Links and reparse points in input paths are forbidden.")
        if entry == path:
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                    "Inputs must be regular files without hard links.")
        else:
            require(stat.S_ISDIR(info.st_mode), "Input ancestor is not a directory.")
    return path.resolve(strict=True)


def _stamp(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def _read(path, maximum=64 * 1024 * 1024):
    path = _safe_file(path)
    before = path.stat()
    require(0 < before.st_size <= maximum, "Input size is empty or exceeds the gate limit.")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        require(stat.S_ISREG(opened.st_mode) and opened.st_nlink == 1 and _stamp(opened) == _stamp(before),
                "Input changed before its file handle was opened.")
        data = stream.read(maximum + 1)
    after = _safe_file(path).stat()
    require(_stamp(before) == _stamp(after) and len(data) == after.st_size and len(data) <= maximum,
            "Input changed while being read.")
    return data, {"name": path.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _sha(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _descriptor(value, basename=None, fields=()):
    require(type(value) is dict and set(value) == {"path", "bytes", "sha256", *fields},
            "Receipt descriptor fields are incomplete or unexpected.")
    relative = value["path"]
    require(type(relative) is str and relative and "\\" not in relative and ":" not in relative,
            "Receipt paths must be relative POSIX paths.")
    parts = relative.split("/")
    require(all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", part) and part not in (".", "..") for part in parts),
            "Unsafe or escaping receipt path.")
    require(basename is None or parts[-1] == basename, "Receipt descriptor has the wrong file role/name.")
    require(type(value["bytes"]) is int and value["bytes"] > 0 and _sha(value["sha256"]),
            "Receipt bytes/SHA must be explicit and valid.")
    return {"name": parts[-1], "bytes": value["bytes"], "sha256": value["sha256"]}


def _verify_ref(base, item, role, seen, verified, basename=None, fields=()):
    expected = _descriptor(item, basename, fields)
    key = item["path"].casefold()
    require(key not in seen, "Receipt contains a duplicate file path.")
    seen.add(key)
    path = _safe_file(base / item["path"])
    require(path.is_relative_to(base), "Receipt file escapes its parent directory.")
    data, actual = _read(path)
    require(same(actual, expected), "Receipt-referenced file bytes/SHA do not match.")
    verified.append({"role": role, "path": item["path"], "bytes": actual["bytes"], "sha256": actual["sha256"]})
    return data, expected


def _png(data):
    require(data[:8] == b"\x89PNG\r\n\x1a\n", "Representative evidence is not PNG.")
    offset, seen, image_bytes, after_idat = 8, set(), 0, False
    while offset < len(data):
        require(offset + 12 <= len(data), "Truncated representative PNG chunk.")
        size = struct.unpack_from(">I", data, offset)[0]
        kind = data[offset+4:offset+8]
        end = offset + size + 12
        require(size <= 0x7fffffff and end <= len(data) and re.fullmatch(b"[A-Za-z]{4}", kind)
                and not (kind[2] & 32), "Invalid representative PNG chunk.")
        payload = data[offset+8:offset+8+size]
        require(zlib.crc32(kind+payload) & 0xffffffff == struct.unpack_from(">I", data, offset+8+size)[0],
                "Representative PNG CRC mismatch.")
        require(seen or kind == b"IHDR", "Representative PNG must start with IHDR.")
        if kind == b"IHDR":
            require(not seen and size == 13, "Invalid or duplicate representative PNG IHDR.")
            width, height, bits, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            require((width, height) == (1920, 1080) and bits in (8, 16) and color in (2, 6)
                    and compression == filtering == 0 and interlace in (0, 1), "Representative evidence must be 1080p RGB/RGBA PNG.")
        elif kind == b"IDAT":
            require(not after_idat, "Representative PNG IDAT chunks are not consecutive.")
            image_bytes += size
        elif kind == b"IEND":
            require(size == 0 and image_bytes > 0 and end == len(data), "Invalid representative PNG IEND/image data.")
            return
        elif kind == b"PLTE":
            require(kind not in seen and b"IDAT" not in seen and 0 < size <= 768 and size % 3 == 0,
                    "Invalid representative PNG palette.")
        else:
            require(kind[0] & 32 and kind not in (b"acTL", b"fcTL", b"fdAT"), "Unsupported representative PNG chunk.")
        if b"IDAT" in seen and kind != b"IDAT":
            after_idat = True
        seen.add(kind)
        offset = end
    raise GateError("Representative PNG has no final IEND.")


def _short_report(report):
    fixed = {"schemaVersion": "pc3-blender-candidate-v1", "synthetic": True, "visualGateAccepted": False,
             "mainRegistration": False, "videoEncoded": False, "engine": "BLENDER_EEVEE_NEXT",
             "status": "unreviewed-render-candidate",
             "resolution": [1280, 720], "eventAnchor": ANCHOR, "cameraId": "SYN-CAM-02", "clockMode": CLOCK,
             "clippedFrames": [], "occlusionAndVisualContactReviewed": False, "representativeFrames": [1, 133, 288]}
    for key, value in fixed.items():
        require(key in report and same(report[key], value), "Reviewed short report has a different event/settings/provenance contract.")
    for key, value in (("seed", 20260921), ("renderedFrameCount", 72), ("candidateFrameCount", 288), ("fps", 24), ("requestedSamples", 96)):
        require(type(report.get(key)) is int and report[key] == value, "Reviewed short report has a different frame/sample count.")
    require(number(report.get("candidateDurationSeconds")) and report["candidateDurationSeconds"] == 12,
            "Reviewed short report must retain the 12-second source denominator.")
    runtime, shadow = report.get("runtimeSamples"), report.get("shadowRays")
    require(type(runtime) is dict and runtime.get("property") == "scene.eevee.taa_render_samples"
            and type(runtime.get("value")) is int and runtime["value"] == 96, "Reviewed short samples lack actual readback.")
    require(type(shadow) is dict and type(shadow.get("requested")) is int and shadow["requested"] == 4
            and type(shadow.get("actual")) is int and shadow["actual"] == 4 and shadow.get("applied") is True
            and shadow.get("property") == "scene.eevee.shadow_ray_count"
            and same(shadow.get("range"), {"cli": [1, 4], "runtime": {"min": 1, "max": 4}}),
            "Reviewed short shadows lack actual four-ray readback.")
    require(same(report.get("look"), B_LOOK)
            and same(report.get("colorManagement"), {"viewTransform": "AgX", "exposure": 0, "gamma": 1}),
            "Reviewed short look/color settings differ.")
    environment = report.get("environmentDetail")
    require(type(environment) is dict and environment.get("name") == SETTINGS["environmentDetail"]
            and environment.get("synthetic") is True and environment.get("tracked") is False
            and "businessToteId" in environment and environment["businessToteId"] is None
            and type(environment.get("objects")) is list and len(environment["objects"]) == 48,
            "Reviewed short environment differs.")
    names = []
    for item in environment["objects"]:
        require(type(item) is dict and type(item.get("name")) is str and item["name"].startswith("SYN-ENV-")
                and item.get("synthetic") is True and item.get("tracked") is False
                and item.get("role") == "synthetic-environment" and item.get("motion") == "static"
                and "businessToteId" in item and item["businessToteId"] is None,
                "Reviewed short environment object roles/identities differ.")
        names.append(item["name"])
    require(len(set(names)) == 48, "Reviewed short environment object names are duplicated.")
    rendered = report.get("rendered")
    require(type(rendered) is list and len(rendered) == 72, "Reviewed short report must list exactly 72 PNGs.")
    for frame, item in zip(range(73, 145), rendered):
        require(type(item) is dict and type(item.get("frame")) is int and item["frame"] == frame
                and item.get("name") == f"frame-{frame:04d}.png" and type(item.get("bytes")) is int and item["bytes"] > 0
                and _sha(item.get("sha256")) and number(item.get("elapsedSeconds"))
                and abs(item["elapsedSeconds"] - (frame-1)/24) <= 1e-9,
                "Reviewed short frame identities/digests/times are incomplete or inconsistent.")


def verify_animation_review(args, generator_path: Path) -> dict:
    """Verify explicit animation receipt and current files before mkdir/render.

    Call again immediately before first render to re-read the same pinned receipt
    and all source/input/evidence bytes. Neither invocation changes any file.
    """
    try:
        review_path = getattr(args, "animation_review", None)
        expected_sha = getattr(args, "animation_review_sha256", None)
        require(review_path is not None and _sha(expected_sha), "Animation requires both a receipt path and its exact SHA256.")
        require(args.mode == "animation", "Review receipt is only valid for explicit animation mode.")
        for key, name in (("camera", "camera"), ("resolution", "resolution"), ("engine", "engine"),
                          ("samples", "samples"), ("shadowRays", "shadow_rays"), ("look", "look"),
                          ("environmentDetail", "environment_detail"), ("threads", "threads")):
            require(same(getattr(args, name), SETTINGS[key]), "Animation request differs from the reviewed fixed configuration.")
        require(type(args.samples) is int and type(args.shadow_rays) is int and type(args.threads) is int
                and type(args.resolution) is list and all(type(v) is int for v in args.resolution),
                "Animation samples/shadows/resolution must be strict integers.")
        receipt_path = _safe_file(review_path)
        raw, receipt_digest = _read(receipt_path, 2 * 1024 * 1024)
        require(receipt_digest["sha256"] == expected_sha, "Animation review receipt SHA256 differs from the supplied expectation.")
        receipt = _json(raw)
        require(set(receipt) == {"schemaVersion", "reviewId", "scope", "settings", "sources", "evidence"},
                "Animation review receipt is incomplete or has unexpected fields.")
        require(receipt["schemaVersion"] == "pc3-animation-review-v1" and receipt["scope"] == SCOPE,
                "Wrong animation receipt schema/scope.")
        require(type(receipt["reviewId"]) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", receipt["reviewId"]),
                "Review ID must be an explicit bounded identifier.")
        require(same(receipt["settings"], SETTINGS), "Receipt settings differ from the fixed reviewed candidate.")
        for key in ("samples", "shadowRays", "threads", "fps", "frames"):
            require(type(receipt["settings"][key]) is int, "Receipt integer settings must not use bool/float values.")
        require(all(type(v) is int for v in receipt["settings"]["resolution"]), "Receipt resolution must use integers.")
        sources, evidence = receipt["sources"], receipt["evidence"]
        require(type(sources) is dict and set(sources) == {"generator", "dependencies", "layout", "fixture"},
                "Receipt source/input roles are incomplete or unexpected.")
        require(type(evidence) is dict and set(evidence) == {"representatives", "shortReport"}, "Receipt evidence roles are incomplete or unexpected.")
        base, seen, verified = receipt_path.parent, {receipt_path.name.casefold()}, []
        generator = _safe_file(generator_path)
        for key, current, filename in (("generator", generator, "build_scene.py"),
                                       ("layout", Path(args.layout), "scene-layout-v1.json"),
                                       ("fixture", Path(args.fixture), "cases.json")):
            _, expected = _verify_ref(base, sources[key], key, seen, verified, filename)
            _, actual = _read(current)
            require(same(actual, expected), "Actual generator/input bytes differ from the reviewed source.")
        dependencies = sources["dependencies"]
        require(type(dependencies) is list and len(dependencies) == 5, "Receipt must bind all five current generator dependencies.")
        names = []
        for item in dependencies:
            expected = _descriptor(item)
            name = expected["name"]
            require(name in DEPENDENCIES and name not in names, "Unexpected/duplicate dependency in receipt.")
            names.append(name)
            _verify_ref(base, item, "dependency", seen, verified, name)
            _, actual = _read(generator.parent / name)
            require(same(actual, expected), "Current dependency bytes differ from the reviewed source.")
            if name == "full_render_gate.py":
                _, executing = _read(Path(__file__))
                require(same(executing, expected), "Executing gate module differs from the reviewed gate source.")
        representatives = evidence["representatives"]
        require(type(representatives) is list and len(representatives) == 3, "Three reviewed representative PNGs are required.")
        for frame, item in zip((1, 133, 288), representatives):
            data, _ = _verify_ref(base, item, "reviewed-representative", seen, verified, f"frame-{frame:04d}.png",
                                  ("role", "frame", "resolution"))
            require(item["role"] == "reviewed-representative" and type(item["frame"]) is int and item["frame"] == frame
                    and same(item["resolution"], [1920, 1080]) and all(type(v) is int for v in item["resolution"]),
                    "Reviewed representative frame/resolution/role differs.")
            _png(data)
        short = evidence["shortReport"]
        raw, _ = _verify_ref(base, short, "reviewed-short-report", seen, verified, "render-report.json",
                             ("role", "resolution", "frameStart", "frameEnd", "renderedFrameCount"))
        require(short["role"] == "reviewed-short-report" and same(short["resolution"], [1280, 720])
                and all(type(v) is int for v in short["resolution"]), "Reviewed short role/resolution differs.")
        for key, value in (("frameStart", 73), ("frameEnd", 144), ("renderedFrameCount", 72)):
            require(type(short[key]) is int and short[key] == value, "Reviewed short evidence denominator differs.")
        _short_report(_json(raw))
        return {"schemaVersion": "pc3-animation-review-verification-v1", "receipt": receipt_digest,
                "reviewId": receipt["reviewId"], "scope": SCOPE, "settings": copy.deepcopy(SETTINGS),
                "verifiedFiles": verified, "issuerAuthenticated": False, "visualAccepted": False,
                "notice": "Exact caller-supplied receipt SHA is the authorization boundary, not cryptographic issuer proof. "
                          "Evidence bytes/roles and runtime inputs are checked; pixels, visual quality and full288 output are not accepted."}
    except GateError:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError) as error:
        raise GateError("Animation review verification could not read or validate the required inputs.") from error


def _vector(value, size):
    return type(value) is list and len(value) == size and all(number(v) for v in value)


def validate_scene_readback(readback: dict, layout: dict) -> dict:
    """Validate actual Blender values collected by the caller, before rendering."""
    try:
        require(type(readback) is dict and type(layout) is dict, "Scene readback/layout must be objects.")
        _finite_tree(readback)
        for key, expected in (("samples", 96), ("shadowRays", 4), ("threads", 2), ("resolutionPercentage", 100),
                              ("fps", 24), ("frameStart", 1), ("frameEnd", 288)):
            require(type(readback.get(key)) is int and readback[key] == expected, "Actual scene integer setting differs from the reviewed candidate.")
        require(readback.get("engine") == "BLENDER_EEVEE_NEXT" and readback.get("threadsMode") == "FIXED",
                "Actual scene engine/thread mode differs.")
        require(same(readback.get("resolution"), [1920, 1080]) and all(type(v) is int for v in readback["resolution"])
                and same(readback.get("pixelAspect"), [1, 1]) and number(readback.get("fpsBase")) and readback["fpsBase"] == 1,
                "Actual scene resolution, pixel aspect or frame rate differs.")
        reference, camera = layout.get("camera"), readback.get("camera")
        require(type(reference) is dict and reference.get("id") == "SYN-CAM-02" and reference.get("fixed") is True
                and same(reference.get("position"), [24, 1, 8]) and same(reference.get("lookAt"), [17, 7, .85])
                and number(reference.get("lensMm")) and reference["lensMm"] == 32, "Layout camera differs from the fixed scene contract.")
        require(type(camera) is dict and camera.get("name") == "SYN-CAM-02" and camera.get("sensorFit") == "HORIZONTAL"
                and camera.get("type") == "PERSP" and _vector(camera.get("shift"), 2)
                and all(abs(v) <= 1e-5 for v in camera["shift"])
                and number(camera.get("lens")) and abs(camera["lens"]-32) <= 1e-5
                and number(camera.get("sensorWidth")) and abs(camera["sensorWidth"]-36) <= 1e-5,
                "Actual camera identity/lens/sensor differs.")
        direction = [b-a for a, b in zip(reference["position"], reference["lookAt"])]
        length = math.sqrt(sum(v*v for v in direction))
        expected_forward = [v/length for v in direction]
        up_projection = [-expected_forward[2]*v for v in expected_forward]
        up_projection[2] += 1
        up_length = math.sqrt(sum(v*v for v in up_projection))
        expected_up = [v/up_length for v in up_projection]
        require(_vector(camera.get("position"), 3) and all(abs(a-b) <= 1e-5 for a, b in zip(camera["position"], reference["position"]))
                and _vector(camera.get("forward"), 3) and all(abs(a-b) <= 1e-5 for a, b in zip(camera["forward"], expected_forward))
                and _vector(camera.get("up"), 3) and all(abs(a-b) <= 1e-5 for a, b in zip(camera["up"], expected_up)),
                "Actual camera world position/direction/roll differs.")
        return copy.deepcopy(readback)
    except GateError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError) as error:
        raise GateError("Actual scene readback is incomplete or malformed.") from error
