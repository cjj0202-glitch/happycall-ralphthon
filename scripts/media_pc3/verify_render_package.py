"""Read-only N03-M3 package checks against separately trusted expectations.

Only the standard library is used. Hash agreement is not sender authentication;
PNG structure is not pixel decoding, and projected boxes do not test occlusion.
The 33fa generator has no fixture/thread readback: these remain pending even if
unversioned extra fields appear in a received report. No input file is modified.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import zlib


ANCHOR = {"caseId": "CASE-0002", "eventId": "W-W3", "occurredAt": "2026-09-18T02:33:00+09:00",
          "chuteId": "CH-02", "dockId": "D-02", "businessToteId": None, "visualObjectId": "SYN-VIS-PARCEL02"}
CLOCK = "illustrative-elapsed-separate-from-event-time"
MODES = {"prepare": [], "representatives": [1, 133, 288],
         "short": list(range(73, 145)), "animation": list(range(1, 289))}
DEPENDENCIES = {"scene_contract.py", "look_presets.py", "shadow_settings.py", "environment_detail.py"}
B_LOOK = {"name": "contrast_material_v1", "settings": {
    "worldStrength": .12,
    "lightEnergies": {"Large soft loading-side light": 1800, "Ceiling key": 3300, "Warehouse fill": 650, "Chute rim": 900},
    "concrete": {"color": [.20, .215, .225], "roughness": .43, "bumpStrength": .06, "bumpDistance": .002},
    "steel": {"color": [.32, .35, .38], "metallic": .88, "roughness": .24}}}
ENV_COMMON = {"synthetic": True, "role": "synthetic-environment", "businessToteId": None,
              "tracked": False, "motion": "static"}
NOTICE = ("Machine checks only, using externally supplied expectations. Declared source hashes do not authenticate "
          "the sender or establish the executing commit. PNG chunks/CRC are checked without decompressing pixels; "
          "Blend meshes, video decoding, physical contact, occlusion and visual quality are not inspected.")


class Invalid(Exception):
    def __init__(self, code, detail):
        self.code, self.detail = code, detail
        super().__init__(detail)


def require(condition, detail, code="CONTRACT"):
    if not condition:
        raise Invalid(code, detail)


def number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def same(actual, expected):
    """JSON equality with bool/number/null separation, including nested values."""
    if number(expected):
        return number(actual) and actual == expected
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(same(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(same(a, b) for a, b in zip(actual, expected))
    return actual == expected


def _json_tree(value, depth=0):
    require(depth <= 50, "JSON nesting exceeds the supported limit.", "JSON")
    if value is None or type(value) in (str, bool):
        return
    if type(value) in (int, float):
        require(number(value), "JSON contains a non-finite number.", "JSON")
    elif type(value) is list:
        for item in value:
            _json_tree(item, depth + 1)
    elif type(value) is dict:
        require(all(type(key) is str for key in value), "JSON object keys must be strings.", "JSON")
        for item in value.values():
            _json_tree(item, depth + 1)
    else:
        raise Invalid("JSON", "Unsupported JSON value type.")


def parse_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON object key.", "JSON")
            result[key] = value
        return result
    def constant(_):
        raise Invalid("JSON", "JSON contains a non-finite constant.")
    try:
        value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise Invalid("JSON", "Invalid JSON encoding or syntax.") from exc
    _json_tree(value)
    require(type(value) is dict, "JSON root must be an object.", "JSON")
    return value


def _safe_path(path, directory=False):
    path = Path(path)
    require(".." not in path.parts, "Parent traversal is not allowed.", "PATH")
    path = path if path.is_absolute() else Path.cwd() / path
    for item in (*reversed(path.parents), path):
        info = item.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not (getattr(info, "st_file_attributes", 0) & 0x400),
                "Input path or ancestor is a link/reparse point.", "PATH")
        expected_type = stat.S_ISDIR if item != path or directory else stat.S_ISREG
        require(expected_type(info.st_mode), "Input is not a regular file/directory.", "PATH")
        if stat.S_ISREG(info.st_mode):
            require(info.st_nlink == 1, "Hard-linked input files are not allowed.", "PATH")
    return path.resolve(strict=True)


def _safe_name(name):
    require(type(name) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", name)
            and name not in (".", ".."), "Unsafe file descriptor name.", "PATH")
    return name


def descriptor(value, expected_name=None):
    require(type(value) is dict, "File/source descriptor must be an object.", "DESCRIPTOR")
    name = _safe_name(value.get("name"))
    require(expected_name is None or name == expected_name, "Descriptor names differ from the fixed contract.", "DESCRIPTOR")
    require(type(value.get("bytes")) is int and value["bytes"] > 0, "Descriptor bytes must be a positive integer.", "DESCRIPTOR")
    require(type(value.get("sha256")) is str and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]),
            "Descriptor SHA256 must be 64 lowercase hexadecimal characters.", "DESCRIPTOR")
    return {key: value[key] for key in ("name", "bytes", "sha256")}


def _file(directory, name, read=False, limit=32 * 1024 * 1024):
    path = _safe_path(directory / _safe_name(name))
    require(path.parent == directory, "File escapes the package directory.", "PATH")
    before = path.stat()
    require(not read or before.st_size <= limit, "Metadata/PNG exceeds the supported size limit.", "FILE_SIZE")
    hasher, chunks, byte_count = hashlib.sha256(), [], 0
    with path.open("rb") as stream:
        # fstat confirms the actual opened handle is regular, not merely its name.
        opened = os.fstat(stream.fileno())
        require(stat.S_ISREG(opened.st_mode) and opened.st_nlink == 1,
                "Opened input is not an unlinked regular file.", "PATH")
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                == (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns),
                "Input changed before its handle was opened.", "INPUT_CHANGED")
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
            byte_count += len(block)
            if read:
                chunks.append(block)
                require(byte_count <= limit, "Input grew beyond the supported size limit.", "FILE_SIZE")
    after = _safe_path(path).stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), "Input changed during verification.", "INPUT_CHANGED")
    require(byte_count == after.st_size, "Read byte count differs from the file size.", "INPUT_CHANGED")
    return b"".join(chunks) if read else None, {"name": name, "bytes": after.st_size, "sha256": hasher.hexdigest()}


def load_expectations(path: Path) -> dict:
    """Strictly read an external expectation file; does not derive any values."""
    path = _safe_path(path)
    raw, _ = _file(path.parent, path.name, read=True, limit=2 * 1024 * 1024)
    return parse_json(raw)


def _dependencies(value):
    require(type(value) is list and len(value) == 4, "Exactly four source dependencies are required.", "SOURCE")
    items = [descriptor(item) for item in value]
    require({item["name"] for item in items} == DEPENDENCIES, "Dependency names are missing, duplicated or unexpected.", "SOURCE")
    return sorted(items, key=lambda item: item["name"])


def _environment(value):
    require(type(value) is dict and value.get("name") == "staging_v1"
            and value.get("geometrySource") == "independent-demo-design", "Expected staging_v1 environment.", "EXPECTATIONS")
    for key, expected in ENV_COMMON.items():
        require(key in value and same(value[key], expected), "Invalid environment classification.", "EXPECTATIONS")
    require(type(value.get("notice")) is str and bool(value["notice"].strip()), "Environment notice is required.", "EXPECTATIONS")
    objects = value.get("objects")
    require(type(objects) is list and len(objects) == 48, "Environment requires exactly 48 static props.", "EXPECTATIONS")
    names, groups = [], []
    for obj in objects:
        require(type(obj) is dict, "Environment object must be an object.", "EXPECTATIONS")
        for key, expected in ENV_COMMON.items():
            require(key in obj and same(obj[key], expected), "Invalid environment object classification.", "EXPECTATIONS")
        name = obj.get("name")
        require(type(name) is str and re.fullmatch(r"SYN-ENV-[A-Za-z0-9+_-]{1,100}", name),
                "Environment object names must be synthetic.", "EXPECTATIONS")
        names.append(name)
        groups.append(obj.get("group"))
        require(_vector(obj.get("location"), 3), "Environment location must contain finite numbers.", "EXPECTATIONS")
        require(obj.get("material") in {"steel", "frame", "card", "yellow"}, "Unknown environment material.", "EXPECTATIONS")
        if obj.get("primitive") == "cube":
            require(_vector(obj.get("dimensions"), 3) and all(v > 0 for v in obj["dimensions"])
                    and number(obj.get("bevel")) and obj["bevel"] >= 0, "Invalid environment cube.", "EXPECTATIONS")
        else:
            require(obj.get("primitive") == "cylinder" and obj.get("axis") == "X"
                    and number(obj.get("radius")) and obj["radius"] == .07
                    and number(obj.get("depth")) and obj["depth"] == .06, "Invalid environment cylinder.", "EXPECTATIONS")
    require(len(set(names)) == 48 and Counter(groups) == {"rollcage-1": 17, "rollcage-2": 17,
            "staging-rack": 6, "staging-cartons": 4, "floor-cue": 4}, "Environment names/groups are inconsistent.", "EXPECTATIONS")


def _expectations(value):
    _json_tree(value)
    required = {"schemaVersion", "sourceCommit", "mode", "generator", "layout", "sourceDependencies",
                "fixture", "samples", "shadowRays", "threads", "look", "environmentDetail"}
    require(type(value) is dict and required <= value.keys()
            and value.keys() <= required | {"additionalAssets"}, "Missing or unknown expectation fields.", "EXPECTATIONS")
    require(value["schemaVersion"] == "pc3-render-expectations-v1", "Unsupported expectation schema.", "EXPECTATIONS")
    require(type(value["sourceCommit"]) is str and re.fullmatch(r"[0-9a-f]{40}", value["sourceCommit"]),
            "Expected source commit must be 40 lowercase hexadecimal characters.", "EXPECTATIONS")
    require(type(value["mode"]) is str and value["mode"] in MODES, "Unsupported expected mode.", "EXPECTATIONS")
    descriptor(value["generator"], "build_scene.py")
    descriptor(value["layout"], "scene-layout-v1.json")
    _dependencies(value["sourceDependencies"])
    if value["fixture"] is not None:
        descriptor(value["fixture"], "cases.json")
    for field, expected in (("samples", 96), ("shadowRays", 4), ("threads", 2)):
        require(type(value[field]) is int and value[field] == expected, "Expected sample/shadow/thread configuration differs.", "EXPECTATIONS")
    require(same(value["look"], B_LOOK), "Expected look differs from the fixed B preset.", "EXPECTATIONS")
    _environment(value["environmentDetail"])
    extras = value.get("additionalAssets", [])
    require(type(extras) is list and len(extras) <= 8, "Additional assets must be a bounded descriptor list.", "EXPECTATIONS")
    assets = [descriptor(item) for item in extras]
    require(all(item["name"].endswith(".mp4") for item in assets)
            and len({item["name"] for item in assets}) == len(assets), "Additional assets must be unique explicit MP4 files.", "EXPECTATIONS")
    return assets


def _vector(value, length):
    return type(value) is list and len(value) == length and all(number(item) for item in value)


def _close(actual, expected, tolerance=1e-9):
    return number(actual) and abs(actual - expected) <= tolerance


def _motion(frame):
    t = (frame - 1) / 24
    arc_end = 7.5 + math.pi / 2
    total = arc_end + 2
    if t < 3:
        phase, a, b, start, end, va, vb = "approach", 0, 3, 0, 6, 0, 1
    elif t < 6:
        phase, a, b, start, end, va, vb = "branch", 3, 6, 6, arc_end, 1, .75
    elif t < 10:
        phase, a, b, start, end, va, vb = "chute", 6, 10, arc_end, total, .75, 0
    else:
        return [18.5, 4.5, .85], -math.pi / 2, "settle"
    u = (t - a) / (b - a)
    distance = ((2*u**3 - 3*u**2 + 1)*start + (u**3 - 2*u**2 + u)*(b-a)*va
                + (-2*u**3 + 3*u**2)*end + (u**3-u**2)*(b-a)*vb)
    distance = min(end, max(start, distance))
    if distance <= 7.5:
        return [10 + distance, 7.5, .85], 0.0, phase
    if distance < arc_end:
        angle = distance - 7.5
        return [17.5 + math.sin(angle), 6.5 + math.cos(angle), .85], -angle, phase
    return [18.5, max(4.5, 6.5 - (distance - arc_end)), .85], -math.pi / 2, phase


def _projected_bbox(position, yaw):
    def unit(v):
        length = math.sqrt(sum(n*n for n in v))
        return [n/length for n in v]
    def cross(a, b):
        return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
    forward = unit([-7, 6, -7.15])
    right = unit(cross(forward, [0, 0, 1]))
    up = cross(right, forward)
    parts = [([0, 0, .175], [.62, .42, .35]), ([0, 0, .352], [.075, .418, .004]),
             ([.15, -.04, .352], [.16, .13, .004])]
    points, c, s = [], math.cos(yaw), math.sin(yaw)
    for center, size in parts:
        for signs in itertools.product((-1, 1), repeat=3):
            x, y, z = [center[i] + signs[i]*size[i]/2 for i in range(3)]
            delta = [position[0]+x*c-y*s-24, position[1]+x*s+y*c-1, position[2]+z-8]
            depth = sum(a*b for a, b in zip(delta, forward))
            points.append([.5+32/36*sum(a*b for a, b in zip(delta, right))/depth,
                           .5-32/36*(1280/720)*sum(a*b for a, b in zip(delta, up))/depth])
    return [min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points)]


def _tracks(tracks):
    fixed = {"source": "synthetic-scene-ground-truth", "synthetic": True, "eventAnchor": ANCHOR,
             "coordinateSpace": "normalized-image-top-left", "resolution": [1280, 720], "clockMode": CLOCK,
             "cameraId": "SYN-CAM-02", "cameraPosition": [24, 1, 8], "cameraLensMm": 32,
             "sensorWidthMm": 36, "occlusionTested": False, "clippedFrames": []}
    for key, expected in fixed.items():
        require(key in tracks and same(tracks[key], expected), "Track camera/event/provenance contract differs.", "TRACKS")
    for key, expected in (("frameCount", 288), ("fps", 24)):
        require(type(tracks.get(key)) is int and tracks[key] == expected, "Track frame count/fps differs.", "TRACKS")
    require(all(type(x) is int for x in tracks["resolution"]), "Track resolution must use integers.", "TRACKS")
    rows = tracks.get("frames")
    require(type(rows) is list and len(rows) == 288, "Tracks must contain exactly 288 rows.", "TRACKS")
    for frame, row in enumerate(rows, 1):
        require(type(row) is dict and type(row.get("frame")) is int and row["frame"] == frame,
                "Track rows must be consecutive unique frame numbers 1..288.", "TRACKS")
        require(_close(row.get("elapsedSeconds"), (frame-1)/24), "Track elapsed time differs from its frame.", "TRACKS")
        require(row.get("visualObjectId") == ANCHOR["visualObjectId"] and "businessToteId" in row
                and row["businessToteId"] is None and row.get("fullyInFrame") is True, "Track identity/visibility differs.", "TRACKS")
        position, yaw, phase = _motion(frame)
        require(row.get("phase") == phase and _vector(row.get("worldPosition"), 3)
                and all(_close(a, b, 1e-6) for a, b in zip(row["worldPosition"], position))
                and _close(row.get("yawRadians"), yaw, 1e-6), "Track phase/world position/yaw differs from the fixed route.", "TRACKS")
        require(_close(row.get("contactPlaneGapMeters"), 0, 1e-5), "Track contact-plane gap exceeds tolerance.", "TRACKS")
        bbox = row.get("bboxNormalizedXYXY")
        require(_vector(bbox, 4) and all(0 <= v <= 1 for v in bbox) and bbox[0] < bbox[2] and bbox[1] < bbox[3],
                "Track bbox is not a finite ordered normalized box.", "TRACKS")
        require(all(_close(a, b, 2e-5) for a, b in zip(bbox, _projected_bbox(position, yaw))),
                "Track bbox differs from the fixed camera/parcel projection.", "TRACKS")


def _png(data):
    require(data[:8] == b"\x89PNG\r\n\x1a\n", "Invalid PNG signature.", "PNG")
    offset, count, idat_bytes, ended_idat = 8, 0, 0, False
    seen, color = set(), None
    while offset < len(data):
        require(offset + 12 <= len(data), "Truncated PNG chunk header.", "PNG")
        length = struct.unpack_from(">I", data, offset)[0]
        kind = data[offset+4:offset+8]
        end = offset + 12 + length
        require(length <= 0x7fffffff and end <= len(data) and re.fullmatch(b"[A-Za-z]{4}", kind)
                and not (kind[2] & 32), "Invalid PNG chunk length/type.", "PNG")
        payload = data[offset+8:offset+8+length]
        crc = struct.unpack_from(">I", data, offset+8+length)[0]
        require((zlib.crc32(kind+payload) & 0xffffffff) == crc, "PNG chunk CRC mismatch.", "PNG")
        if count == 0:
            require(kind == b"IHDR" and length == 13, "PNG must start with one 13-byte IHDR.", "PNG")
        if kind == b"IHDR":
            require(kind not in seen and length == 13, "Duplicate or malformed PNG IHDR.", "PNG")
            width, height, bits, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            depths = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
            require((width, height) == (1280, 720) and bits in depths.get(color, ())
                    and compression == filtering == 0 and interlace in (0, 1), "PNG IHDR dimensions/format differ.", "PNG")
        elif kind == b"PLTE":
            require(kind not in seen and b"IDAT" not in seen and color not in (0, 4)
                    and 0 < length <= 768 and length % 3 == 0, "Invalid PNG palette.", "PNG")
        elif kind == b"IDAT":
            require(not ended_idat and (color != 3 or b"PLTE" in seen), "Invalid PNG IDAT ordering/palette.", "PNG")
            idat_bytes += length
        elif kind == b"IEND":
            require(length == 0 and idat_bytes > 0 and end == len(data), "Invalid/missing PNG image data or final IEND.", "PNG")
            return
        else:
            require(bool(kind[0] & 32) and kind not in (b"acTL", b"fcTL", b"fdAT"),
                    "Unsupported PNG critical/animated chunk.", "PNG")
        if b"IDAT" in seen and kind != b"IDAT":
            ended_idat = True
        seen.add(kind)
        offset, count = end, count + 1
    raise Invalid("PNG", "PNG has no complete final IEND.")


def _report(report, expectations):
    mode = expectations["mode"]
    fixed = {"schemaVersion": "pc3-blender-candidate-v1", "synthetic": True, "visualGateAccepted": False,
             "mainRegistration": False, "videoEncoded": False, "engine": "BLENDER_EEVEE_NEXT", "resolution": [1280, 720],
             "eventAnchor": ANCHOR, "cameraId": "SYN-CAM-02", "clockMode": CLOCK, "clippedFrames": [],
             "occlusionAndVisualContactReviewed": False, "representativeFrames": [1, 133, 288],
             "status": "scene-prepared-not-rendered" if mode == "prepare" else "unreviewed-render-candidate"}
    for key, expected in fixed.items():
        require(key in report and same(report[key], expected), "Report event/camera/status/provenance contract differs.", "REPORT")
    for key, expected in (("seed", 20260921), ("fps", 24), ("candidateFrameCount", 288),
                          ("renderedFrameCount", len(MODES[mode])), ("requestedSamples", 96)):
        require(type(report.get(key)) is int and report[key] == expected, "Report count/sample/seed differs.", "REPORT")
    require(all(type(v) is int for v in report["resolution"] + report["representativeFrames"]),
            "Report frame IDs/resolution must use integers.", "REPORT")
    require(_close(report.get("candidateDurationSeconds"), 12) and number(report.get("wallSeconds"))
            and report["wallSeconds"] > 0, "Invalid report duration/timing.", "REPORT")
    require(type(report.get("blenderVersion")) is str and re.fullmatch(r"4\.5\.\d+(?: LTS)?", report["blenderVersion"]),
            "Expected Blender 4.5 version evidence.", "REPORT")
    require(same(report.get("look"), expectations["look"])
            and same(report.get("environmentDetail"), expectations["environmentDetail"]), "Look/environment metadata differs from expectations.", "SETTINGS")
    require(same(report.get("colorManagement"), {"viewTransform": "AgX", "exposure": 0, "gamma": 1}),
            "Color management differs.", "SETTINGS")
    samples = report.get("runtimeSamples")
    require(type(samples) is dict and samples.get("property") == "scene.eevee.taa_render_samples"
            and type(samples.get("value")) is int and samples["value"] == 96, "Actual sample readback must be 96.", "READBACK")
    shadow = report.get("shadowRays")
    require(type(shadow) is dict and type(shadow.get("requested")) is int and shadow["requested"] == 4
            and type(shadow.get("actual")) is int and shadow["actual"] == 4 and shadow.get("applied") is True
            and shadow.get("property") == "scene.eevee.shadow_ray_count"
            and same(shadow.get("range"), {"cli": [1, 4], "runtime": {"min": 1, "max": 4}}),
            "Actual shadow readback/range must support the requested four rays.", "READBACK")
    for key in ("generator", "layout"):
        require(same(descriptor(report.get(key)), descriptor(expectations[key])), "Source/input descriptor differs from expectations.", "SOURCE")
    require(same(_dependencies(report.get("sourceDependencies")), _dependencies(expectations["sourceDependencies"])),
            "Source dependency hashes differ from expectations.", "SOURCE")
    for field in ("mode", "sourceCommit"):
        require(field not in report or same(report[field], expectations[field]), "Supplemental mode/source assertion conflicts with expectations.", "REPORT")


def _result():
    return {"schemaVersion": "pc3-render-package-verification-v1", "valid": False, "status": "FAIL",
            "failures": [], "pending": [
                {"code": "FIXTURE_RUNTIME_UNVERIFIED", "detail": "33fa has no fixture digest readback; separate execution evidence is required."},
                {"code": "THREADS_RUNTIME_UNVERIFIED", "detail": "33fa has no actual thread readback; requested two threads remain unverified."},
                {"code": "PIXEL_DECODE_NOT_RUN", "detail": "PNG chunks and CRC only; compressed pixels are not decoded."},
                {"code": "VIDEO_DECODE_NOT_RUN", "detail": "Video hashes only; codec, frame count, FPS and duration are not decoded."},
                {"code": "VISUAL_REVIEW_PENDING", "detail": "Meshes, physical contact, occlusion, motion and visual quality need separate review."},
                {"code": "AUTHENTICITY_UNVERIFIED", "detail": "Source commit and source hashes are external expectations/declarations, not sender authentication."}],
            "visualAccepted": False, "pixelDecoded": False, "videoDecoded": False, "authenticityVerified": False,
            "inputDigests": [], "images": [], "videos": [], "mode": None, "sourceCommit": None, "notice": NOTICE}


def _failure(result, error):
    if isinstance(error, Invalid):
        code, detail = error.code, error.detail
    elif isinstance(error, OSError):
        code, detail = "READ", "Required input could not be read as a regular local file."
    elif isinstance(error, (ValueError, TypeError, KeyError, OverflowError, RecursionError)):
        code, detail = "MALFORMED", "Malformed input structure or unsupported value."
    else:
        code, detail = "INTERNAL", "Verification could not complete."
    result["valid"], result["status"] = False, "FAIL"
    result["failures"].append({"code": code, "detail": detail[:300]})
    return result


def verify_package(package_dir: Path, expectations: dict) -> dict:
    result = _result()
    try:
        extras = _expectations(expectations)
        mode = expectations["mode"]
        result.update({"mode": mode, "sourceCommit": expectations["sourceCommit"]})
        directory = _safe_path(package_dir, directory=True)
        allowed = {"render-report.json", "tracks.json", "case-0002-ww3.blend"}
        allowed.update(f"frame-{frame:04d}.png" for frame in MODES[mode])
        allowed.update(item["name"] for item in extras)
        entries = list(directory.iterdir())
        require({p.name for p in entries} == allowed, "Package contains missing or unexpected files.", "INVENTORY")
        for path in entries:
            _safe_path(path)
        report_raw, report_digest = _file(directory, "render-report.json", read=True, limit=4*1024*1024)
        result["inputDigests"].append(report_digest)
        report = parse_json(report_raw)
        _report(report, expectations)
        for name, key in (("tracks.json", "tracks"), ("case-0002-ww3.blend", "blend")):
            declared = descriptor(report.get(key), name)
            raw, actual = _file(directory, name, read=key == "tracks")
            result["inputDigests"].append(actual)
            require(same(actual, declared), "Track/Blend bytes or SHA256 differ from report.", "ASSET")
            if key == "tracks":
                _tracks(parse_json(raw))
        rendered = report.get("rendered")
        require(type(rendered) is list and len(rendered) == len(MODES[mode]), "Rendered asset list does not match expected mode.", "FRAMES")
        for frame, item in zip(MODES[mode], rendered):
            name = f"frame-{frame:04d}.png"
            declared = descriptor(item, name)
            require(type(item.get("frame")) is int and item["frame"] == frame
                    and _close(item.get("elapsedSeconds"), (frame-1)/24)
                    and number(item.get("renderSeconds")) and item["renderSeconds"] > 0,
                    "Rendered frame ID/time/order differs from expected mode.", "FRAMES")
            raw, actual = _file(directory, name, read=True)
            result["inputDigests"].append(actual)
            require(same(actual, declared), "PNG bytes or SHA256 differ from report.", "ASSET")
            _png(raw)
            result["images"].append({**actual, "frame": frame, "elapsedSeconds": (frame-1)/24})
        for declared in extras:
            _, actual = _file(directory, declared["name"])
            result["inputDigests"].append(actual)
            require(same(actual, declared), "Explicit video bytes or SHA256 differ from expectations.", "ASSET")
            result["videos"].append(actual)
        require({p.name for p in directory.iterdir()} == allowed, "Package changed during verification.", "INPUT_CHANGED")
        result.update({"valid": True, "status": "PASS_WITH_PENDING"})
    except Exception as error:
        _failure(result, error)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--expectations", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        package = _safe_path(args.package, directory=True)
        expected_path = _safe_path(args.expectations)
        require(not expected_path.is_relative_to(package), "Expectations must be supplied outside the received package.", "PATH")
        result = verify_package(package, load_expectations(expected_path))
        if args.output:
            require(".." not in args.output.parts, "Output parent traversal is not allowed.", "OUTPUT")
            parent = _safe_path(args.output.parent, directory=True)
            output = parent / _safe_name(args.output.name)
            require(not output.is_relative_to(package) and output != expected_path
                    and not output.exists() and not output.is_symlink(), "Output must be a new file outside all inputs.", "OUTPUT")
            with output.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    except Exception as error:
        result = _failure(_result(), error)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
