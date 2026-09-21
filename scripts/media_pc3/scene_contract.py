"""Validate the independent W-W3 scene and evaluate deterministic ground truth.

Coordinates are illustrative metres, never reconstructed BCR/CCTV measurements.
The returned z is the parcel's support surface, not its centre. A renderer must
add half the parcel height. No fixture, media registration or file is modified.
"""
from __future__ import annotations

import copy
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

SCENE_SEED = 20260921
FRAME_COUNT = 288
CORNER_RADIUS_METERS = 1.0
SCHEMA_VERSION = "synthetic-center-layout-v1"
EVENT_TIME = "2026-09-18T02:33:00+09:00"
EXPECTED_PATH = [[10, 7.5, 0.85], [16, 7.5, 0.85],
                 [18.5, 7.5, 0.85], [18.5, 4.5, 0.85]]
PHASES = {"approach": [0, 3], "branch": [3, 6],
          "chute": [6, 10], "settle": [10, 12]}
ZONE_BOUNDS = {"SYN-Z-PICK": [1, 9, 8, 7], "SYN-Z-IN": [9, 6, 3, 3],
               "SYN-Z-SORT": [12, 6, 11, 3], "SYN-Z-CH02": [17, 3, 3, 3],
               "SYN-Z-STAGE": [11, 0.5, 13, 2], "SYN-Z-D02": [26, 0.5, 3, 4]}
ZONE_IDS = set(ZONE_BOUNDS)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _number(value: Any, name: str) -> float:
    _require(type(value) in (int, float), f"{name} must be a finite number (not a boolean)")
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError(f"{name} is outside finite floating-point range") from error
    _require(math.isfinite(number), f"{name} must be finite")
    return number


def _object(value: Any, name: str) -> dict:
    _require(isinstance(value, dict), f"{name} must be an object")
    return value


def _vector(value: Any, size: int, name: str) -> list[float]:
    _require(isinstance(value, list) and len(value) == size,
             f"{name} must contain exactly {size} numbers")
    return [_number(item, f"{name}[{index}]") for index, item in enumerate(value)]


def _timestamp(value: Any, name: str) -> datetime:
    _require(isinstance(value, str), f"{name} must be an explicit timezone timestamp")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"Invalid {name}") from error
    _require(result.tzinfo is not None and result.utcoffset() is not None,
             f"{name} must include a timezone")
    return result


def _read_json(path: str | Path) -> dict:
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError(f"Non-finite JSON value: {value}")

    with Path(path).open(encoding="utf-8-sig") as handle:
        return _object(json.load(handle, object_pairs_hook=unique_object,
                                 parse_constant=invalid_constant), "JSON root")


def validate_layout(layout: dict, fixture: dict | None = None) -> None:
    """Reject layout v1 drift and optionally cross-check immutable event records.

    The phase/path contract is deliberately versioned and fixed. A different
    route, business object or real-geometry source requires a reviewed contract,
    rather than being silently accepted by this first-Bolt implementation.
    """
    layout = _object(layout, "layout")
    _require(layout.get("schemaVersion") == SCHEMA_VERSION, "Unsupported layout schema")
    _require(layout.get("synthetic") is True, "The scene must be explicitly synthetic")
    _require(layout.get("geometrySource") == "independent-demo-design",
             "Only independent demonstration geometry is permitted")
    _require(layout.get("units") == "m", "Scene units must be metres")
    _require(layout.get("axes") == {"x": "right", "y": "away-from-docks", "z": "up"},
             "Scene axes differ from the shared contract")
    _require(isinstance(layout.get("notice"), str) and bool(layout["notice"].strip()),
             "The scene requires a synthetic-geometry notice")
    floor = _object(layout.get("floor"), "floor")
    width, depth = _number(floor.get("width"), "floor.width"), _number(floor.get("depth"), "floor.depth")
    _require((width, depth) == (30, 18), "Layout v1 floor must be 30 by 18 metres")
    zones = layout.get("zones")
    _require(isinstance(zones, list) and len(zones) == len(ZONE_IDS), "Expected six independent scene zones")
    zone_ids = []
    for index, item in enumerate(zones):
        item = _object(item, f"zones[{index}]")
        zone_ids.append(item.get("id"))
        x, y, w, d = _vector(item.get("bounds"), 4, f"zones[{index}].bounds")
        _require(w > 0 and d > 0 and x >= 0 and y >= 0 and x + w <= width and y + d <= depth,
                 "Zone bounds must remain inside the declared independent floor")
        zone_id = item.get("id")
        _require(isinstance(zone_id, str) and zone_id in ZONE_BOUNDS,
                 "Zone ID is not registered in layout v1")
        _require([x, y, w, d] == ZONE_BOUNDS[zone_id],
                 f"The bounds of {zone_id} differ from the fixed layout v1 geometry")
    _require(all(isinstance(item, str) for item in zone_ids) and set(zone_ids) == ZONE_IDS,
             "Zone IDs must be unique and match the shared layout")
    visual_path = _object(layout.get("visualPath"), "visualPath")
    _require(visual_path.get("id") == "SYN-PATH-BRANCH02", "Wrong visual path ID")
    _require(visual_path.get("mode") == "illustrative" and visual_path.get("sourceBcrTrace") is False
             and visual_path.get("speedMeasured") is False, "Do not claim observed BCR paths or measured speed")
    points = visual_path.get("points")
    _require(isinstance(points, list) and len(points) == 4, "The first Bolt requires four path points")
    converted = [_vector(point, 3, f"visualPath.points[{index}]") for index, point in enumerate(points)]
    _require(converted == EXPECTED_PATH, "The route differs from the shared layout v1 path")
    camera = _object(layout.get("camera"), "camera")
    _require(camera.get("id") == "SYN-CAM-02" and camera.get("fixed") is True,
             "The event uses fixed synthetic camera SYN-CAM-02")
    position = _vector(camera.get("position"), 3, "camera.position")
    look_at = _vector(camera.get("lookAt"), 3, "camera.lookAt")
    _require(0 <= position[0] <= width and 0 <= position[1] <= depth and position[2] > 0,
             "Camera position must be above the independent scene")
    _require(position != look_at, "Camera cannot look at its own position")
    lens = _number(camera.get("lensMm"), "camera.lensMm")
    _require(lens > 0, "Camera focal length must be positive")
    _require(position == [24, 1, 8] and look_at == [17, 7, 0.85] and lens == 32,
             "Camera position, target and focal length must match fixed layout v1")
    anchor = _object(layout.get("eventAnchor"), "eventAnchor")
    expected_anchor = {"caseId": "CASE-0002", "eventId": "W-W3", "occurredAt": EVENT_TIME,
                       "chuteId": "CH-02", "dockId": "D-02", "visualObjectId": "SYN-VIS-PARCEL02"}
    for key, value in expected_anchor.items():
        _require(anchor.get(key) == value, f"Wrong eventAnchor.{key}")
    _require("businessToteId" in anchor and anchor["businessToteId"] is None,
             "W-W3 business tote is unknown; do not assign a picking/shipping tote")
    _timestamp(anchor["occurredAt"], "eventAnchor.occurredAt")
    animation = _object(layout.get("animation"), "animation")
    duration = _number(animation.get("durationSeconds"), "animation.durationSeconds")
    fps = _number(animation.get("fps"), "animation.fps")
    _require(duration == 12 and fps == 24 and duration * fps == FRAME_COUNT,
             "The scene must contain 288 frames at 24 fps over 12 seconds")
    _require(_vector(animation.get("targetResolution"), 2, "animation.targetResolution") == [1920, 1080],
             "The declared final resolution must be 1920 by 1080")
    phases = _object(animation.get("phaseSeconds"), "animation.phaseSeconds")
    _require(set(phases) == set(PHASES), "The scene must preserve all four phases")
    for key, value in PHASES.items():
        _require(_vector(phases[key], 2, f"phaseSeconds.{key}") == value,
                 f"Wrong timing for phase {key}")
    _require(animation.get("clockMode") == "illustrative-elapsed-separate-from-event-time",
             "Playback time must remain separate from the fixed event timestamp")
    _require(animation.get("trackSource") == "synthetic-scene-ground-truth"
             and animation.get("actualIncidentReconstruction") is False,
             "Ground truth is synthetic scene geometry, not reconstructed incident tracking")
    if "seed" in animation:
        _require(type(animation["seed"]) is int and animation["seed"] == SCENE_SEED,
                 "The deterministic scene seed differs")
    if fixture is not None:
        _validate_fixture_anchor(layout, fixture)


def _validate_fixture_anchor(layout: dict, fixture: dict) -> None:
    fixture = _object(fixture, "fixture")
    _require(fixture.get("synthetic") is True, "Source fixture must be explicitly synthetic")
    cases = fixture.get("cases")
    _require(isinstance(cases, list), "Fixture cases must be a list")
    matches = [item for item in cases if isinstance(item, dict) and item.get("id") == "CASE-0002"]
    _require(len(matches) == 1, "Fixture must have one CASE-0002")
    case = matches[0]
    wms = _object(case.get("wms"), "fixture.wms")
    events = wms.get("events")
    _require(isinstance(events, list), "WMS events must be a list")
    matches = [item for item in events if isinstance(item, dict) and item.get("id") == "W-W3"]
    _require(len(matches) == 1, "Fixture must have one W-W3 event")
    event = matches[0]
    _require(event.get("time") == EVENT_TIME, "Fixture event timestamp differs from the scene anchor")
    _require(_timestamp(event["time"], "event.time") <= _timestamp(case.get("asOf"), "case.asOf"),
             "The selected event is after the source case's asOf")
    sorting = _object(wms.get("sorting"), "fixture.wms.sorting")
    _require(sorting.get("sortedAt") == EVENT_TIME and sorting.get("schdChuteNo") == "CH-02"
             and sorting.get("rsltChuteNo") == "CH-02", "Fixture sorting/chute records differ")
    _require(_object(wms.get("shipping"), "fixture.wms.shipping").get("dock") == "D-02",
             "Fixture dock differs from the scene anchor")
    _require(event.get("toteId") is None and sorting.get("toteId") is None,
             "The first-Bolt source must preserve the unknown branch tote")
    media = case.get("media")
    _require(isinstance(media, list), "Fixture media must be a list")
    matching_media = [item for item in media if isinstance(item, dict)
                      and item.get("caseId") == "CASE-0002" and item.get("system") == "WMS"
                      and item.get("cameraId") == layout["camera"]["id"]
                      and isinstance(item.get("eventIds"), list) and "W-W3" in item["eventIds"]]
    _require(len(matching_media) == 1 and matching_media[0].get("synthetic") is True
             and matching_media[0].get("occurredAt") == EVENT_TIME,
             "Fixture must have one matching synthetic event/camera registration")


def load_layout(path: str | Path, fixture_path: str | Path | None = None) -> dict:
    """Read and validate layout JSON, optionally checking a source fixture JSON."""
    layout = _read_json(path)
    validate_layout(layout, _read_json(fixture_path) if fixture_path is not None else None)
    return copy.deepcopy(layout)


def _hermite_distance(t: float, start_t: float, end_t: float,
                      start_s: float, end_s: float, start_speed: float, end_speed: float) -> float:
    span = end_t - start_t
    u = (t - start_t) / span
    u2, u3 = u * u, u * u * u
    value = ((2 * u3 - 3 * u2 + 1) * start_s + (u3 - 2 * u2 + u) * span * start_speed
             + (-2 * u3 + 3 * u2) * end_s + (u3 - u2) * span * end_speed)
    # Suppress floating-point endpoint overshoot, never wrap time or a path.
    return min(end_s, max(start_s, value))


def evaluate_motion(t_seconds: float, layout: dict) -> dict:
    """Return the non-random parcel support position and continuous tangent yaw.

    Times are finite and bounded to [0, 12]. Render indices 0..287 use i/24;
    t=12 is also defined as the held endpoint for verification. A radius-1m
    quarter-circle rounds the declared right-angle corner. Hermite distance
    curves share velocities at phase boundaries; settle has exactly zero speed.
    """
    t = _number(t_seconds, "t_seconds")
    _require(0 <= t <= 12, "t_seconds must lie within the closed interval [0, 12]")
    validate_layout(layout)
    p0, p1, p2, p3 = layout["visualPath"]["points"]
    radius = CORNER_RADIUS_METERS
    approach_length = p1[0] - p0[0]
    straight_length = p2[0] - p0[0] - radius
    arc_end = straight_length + math.pi * radius / 2
    total = arc_end + p2[1] - radius - p3[1]
    if t < 3:
        phase = "approach"
        distance = _hermite_distance(t, 0, 3, 0, approach_length, 0, 1)
    elif t < 6:
        phase = "branch"
        distance = _hermite_distance(t, 3, 6, approach_length, arc_end, 1, 0.75)
    elif t < 10:
        phase = "chute"
        distance = _hermite_distance(t, 6, 10, arc_end, total, 0.75, 0)
    else:
        phase, distance = "settle", total
    if distance <= straight_length:
        x, y, yaw = p0[0] + distance, p0[1], 0.0
    elif distance < arc_end:
        angle = (distance - straight_length) / radius
        x = p2[0] - radius + radius * math.sin(angle)
        y = p2[1] - radius + radius * math.cos(angle)
        yaw = -angle
    else:
        # Preserve the exact declared endpoint instead of arc-length subtraction
        # leaving a tiny floating-point excursion outside the path bounds.
        x, y, yaw = p2[0], max(p3[1], p2[1] - radius - (distance - arc_end)), -math.pi / 2
    return {"position": [x, y, float(p0[2])], "yaw_radians": yaw, "phase": phase,
            "time_seconds": t, "visualObjectId": "SYN-VIS-PARCEL02", "businessToteId": None,
            "trackSource": "synthetic-scene-ground-truth", "seed": SCENE_SEED}
