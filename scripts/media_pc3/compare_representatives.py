"""Compare received A/B metadata and three PNG headers, using only the stdlib.

No render/network/install or input mutation. Hashes check consistency with declared
metadata, not sender authenticity, release provenance, pixel decoding or quality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import stat
import struct
from pathlib import Path

from look_presets import settings_for

FRAMES = (1, 133, 288)
ANCHOR = {"caseId": "CASE-0002", "eventId": "W-W3", "occurredAt": "2026-09-18T02:33:00+09:00",
          "chuteId": "CH-02", "dockId": "D-02", "businessToteId": None, "visualObjectId": "SYN-VIS-PARCEL02"}
CLOCK = "illustrative-elapsed-separate-from-event-time"
NOTICE = "Header/hash/metadata comparison only; pixels and visual quality are unverified. Declared hashes do not authenticate the sender or replace Release verification."


class Invalid(Exception):
    def __init__(self, code, detail):
        self.code, self.detail = code, detail


def require(condition, detail, code="CONTRACT"):
    if not condition:
        raise Invalid(code, detail)


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def fingerprint(value, expected_name=None):
    require(isinstance(value, dict), "asset/source descriptor must be an object")
    name = value.get("name")
    require(isinstance(name, str) and bool(name) and name not in (".", "..")
            and not any(c in name for c in "/\\:\0"), "unsafe descriptor name")
    require(expected_name is None or name == expected_name, f"unexpected asset name: {name}")
    require(type(value.get("bytes")) is int and value["bytes"] > 0, f"invalid byte count: {name}")
    require(isinstance(value.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]), f"invalid SHA256: {name}")
    return {key: value[key] for key in ("name", "bytes", "sha256")}


def read_fixed(directory, name):
    path = directory / name  # name is selected by this program, never a report path.
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and not path.is_symlink()
            and not (getattr(info, "st_file_attributes", 0) & 0x400)
            and path.resolve().parent == directory, f"not a regular in-directory file: {name}", "READ")
    return path.read_bytes()


def parse_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"duplicate JSON key: {key}", "JSON")
            result[key] = value
        return result
    def constant(value):
        raise Invalid("JSON", f"non-finite JSON value: {value}")
    value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs, parse_constant=constant)
    json.dumps(value, allow_nan=False)  # Reject NaN, Infinity and exponent overflow.
    require(isinstance(value, dict), "JSON root must be an object", "JSON")
    return value


def match_bytes(data, descriptor, name):
    item = fingerprint(descriptor, name)
    require(len(data) == item["bytes"] and hashlib.sha256(data).hexdigest() == item["sha256"], f"bytes/SHA256 mismatch: {name}", "ASSET")


def check_run(directory, expected_look):
    directory = Path(directory).resolve(strict=True)
    report = parse_json(read_fixed(directory, "render-report.json"))
    require(report.get("schemaVersion") == "pc3-blender-candidate-v1", "report schema")
    for key, expected in {"synthetic": True, "visualGateAccepted": False, "mainRegistration": False, "videoEncoded": False}.items():
        require(report.get(key) is expected, f"report.{key}")
    for key, expected in {"renderedFrameCount": 3, "fps": 24, "candidateFrameCount": 288}.items():
        require(type(report.get(key)) is int and report[key] == expected, f"report.{key}")
    require(number(report.get("candidateDurationSeconds")) and report["candidateDurationSeconds"] == 12, "candidate duration")
    require(report.get("representativeFrames") == list(FRAMES)
            and all(type(item) is int for item in report["representativeFrames"]), "representative frame IDs")
    require(report.get("resolution") == [1280, 720] and all(type(v) is int for v in report["resolution"]), "report resolution")
    require(report.get("engine") == "BLENDER_EEVEE_NEXT", "expected EEVEE engine")
    require(isinstance(report.get("blenderVersion"), str) and bool(report["blenderVersion"].strip()), "missing Blender version")
    require(report.get("look") == {"name": expected_look, "settings": settings_for(expected_look)}, "look/settings drift")
    runtime = report.get("runtimeSamples", {})
    require(isinstance(runtime, dict) and runtime.get("property") == "scene.eevee.taa_render_samples", "sample readback property")
    requested = report.get("requestedSamples")
    require(type(requested) is int and requested > 0 and type(runtime.get("value")) is int
            and runtime["value"] == requested, "unverified or unequal runtime/requested samples")
    color = report.get("colorManagement", {})
    require(isinstance(color, dict) and color.get("viewTransform") == "AgX"
            and number(color.get("exposure")) and color["exposure"] == 0
            and number(color.get("gamma")) and color["gamma"] == 1, "color management drift")
    sources = {key: fingerprint(report.get(key)) for key in ("generator", "layout")}
    dependencies = report.get("sourceDependencies")
    require(isinstance(dependencies, list) and len(dependencies) == 2, "source dependency count")
    deps = [fingerprint(item) for item in dependencies]
    require({item["name"] for item in deps} == {"scene_contract.py", "look_presets.py"}, "dependency names/duplicates")
    sources["dependencies"] = sorted(deps, key=lambda item: item["name"])
    track_bytes = read_fixed(directory, "tracks.json")
    match_bytes(track_bytes, report.get("tracks"), "tracks.json")
    tracks = parse_json(track_bytes)
    for data, label in ((report, "report"), (tracks, "tracks")):
        require(data.get("eventAnchor") == ANCHOR, f"{label} event anchor")
        require(data.get("cameraId") == "SYN-CAM-02" and data.get("clockMode") == CLOCK, f"{label} camera/clock")
        require(data.get("clippedFrames") == [], f"{label} clipped frames")
    require(tracks.get("source") == "synthetic-scene-ground-truth" and tracks.get("synthetic") is True
            and tracks.get("occlusionTested") is False, "track provenance/occlusion")
    require(type(tracks.get("frameCount")) is int and tracks["frameCount"] == 288
            and type(tracks.get("fps")) is int and tracks["fps"] == 24
            and tracks.get("resolution") == [1280, 720]
            and all(type(v) is int for v in tracks["resolution"]), "track frame count/fps/resolution")
    rows = tracks.get("frames")
    require(isinstance(rows, list) and len(rows) == 288, "track row count")
    for frame, row in enumerate(rows, 1):
        require(isinstance(row, dict) and type(row.get("frame")) is int and row["frame"] == frame
                and number(row.get("elapsedSeconds")) and math.isclose(row["elapsedSeconds"], (frame - 1) / 24, rel_tol=0, abs_tol=1e-9), f"track frame/time {frame}")
        require(row.get("visualObjectId") == ANCHOR["visualObjectId"] and "businessToteId" in row
                and row["businessToteId"] is None and row.get("fullyInFrame") is True,
                f"track object identity/visibility {frame}")
    rendered = report.get("rendered")
    require(isinstance(rendered, list) and len(rendered) == 3, "rendered asset count")
    require(all(isinstance(item, dict) and type(item.get("frame")) is int for item in rendered), "rendered frame descriptors")
    indexed = {item["frame"]: item for item in rendered}
    require(set(indexed) == set(FRAMES), "rendered frame IDs/duplicates")
    for frame in FRAMES:
        name, item = f"frame-{frame:04d}.png", indexed[frame]
        fingerprint(item, name)  # Reject traversal before opening any frame file.
        require(number(item.get("elapsedSeconds")) and math.isclose(item["elapsedSeconds"], (frame - 1) / 24, rel_tol=0, abs_tol=1e-9), f"rendered frame/time {frame}")
        data = read_fixed(directory, name)
        match_bytes(data, item, name)
        require(len(data) >= 33 and data[:8] == b"\x89PNG\r\n\x1a\n"
                and data[8:16] == b"\0\0\0\rIHDR"
                and struct.unpack(">II", data[16:24]) == (1280, 720), f"PNG signature/IHDR dimensions: {name}", "ASSET")
    return {"report": report, "tracks": tracks, "sources": sources, "samples": requested}


def compare_runs(a_dir: Path, b_dir: Path) -> dict:
    result = {"schemaVersion": "pc3-representative-comparison-v1", "comparable": False,
              "failures": [], "visualAccepted": False, "pixelDecoded": False, "authenticityVerified": False, "notice": NOTICE}
    runs = []
    for label, directory, look in (("A", a_dir, "baseline"), ("B", b_dir, "contrast_material_v1")):
        try:
            runs.append(check_run(directory, look))
        except Exception as error:
            code = error.code if isinstance(error, Invalid) else "READ" if isinstance(error, OSError) else "JSON" if isinstance(error, (ValueError, UnicodeError)) else "INTERNAL"
            detail = error.detail if isinstance(error, Invalid) else str(error)
            result["failures"].append({"code": code, "detail": f"{label}: {detail}"})
    if len(runs) == 2:
        a, b = runs
        for field in ("blenderVersion", "engine", "colorManagement"):
            if a["report"][field] != b["report"][field]:
                result["failures"].append({"code": "CROSS_RUN", "detail": f"A/B {field} differs"})
        for field in ("samples", "sources", "tracks"):
            same = (json.dumps(a[field], sort_keys=True) == json.dumps(b[field], sort_keys=True)) if field == "tracks" else a[field] == b[field]
            if not same:
                result["failures"].append({"code": "CROSS_RUN", "detail": f"A/B {field} differs"})
        if not result["failures"]:
            result["comparable"] = True
            result["conditions"] = {"engine": a["report"]["engine"], "blenderVersion": a["report"]["blenderVersion"],
                "samples": a["samples"], "resolution": [1280, 720], "fps": 24, "looks": ["baseline", "contrast_material_v1"]}
            result["frames"] = [{"frame": frame, "name": f"frame-{frame:04d}.png", "elapsedSeconds": (frame - 1) / 24} for frame in FRAMES]
            result["imageDigests"] = {label: {item["name"]: fingerprint(item) for item in run["report"]["rendered"]}
                                      for label, run in (("A", a), ("B", b))}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a", required=True, type=Path)
    parser.add_argument("--b", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = compare_runs(args.a, args.b)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        try:
            if any(args.output.resolve().is_relative_to(path.resolve()) for path in (args.a, args.b)):
                parser.exit(2, "Output must be outside both input directories.\n")
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(text)
        except OSError as error:
            parser.exit(2, f"Output not written (existing outputs are never overwritten): {error}\n")
    print(text, end="")
    raise SystemExit(0 if result["comparable"] else 1)


if __name__ == "__main__":
    main()
