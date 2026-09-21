"""Candidate-only metadata for explicitly procedural WMS demonstration clips.

No fixture, public directory, manifest or existing media registration is changed.
This module is standard-library only, including contract validation.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "data/fixtures/cases.json"
OVERLAY = ROOT / "data/overlays/pc3-wms.json"
STAGES = (("picking", "피킹", 1), ("sorting", "분기", 3), ("shipping", "출고", 4))
CASE_PREFIXES = {"CASE-0001": "W-M", "CASE-0002": "W-W"}
NOTICE = "코드로 그린 합성 공정 설명입니다. 실제 CCTV·연속 위치추적·AI 영상 모델 결과가 아니며 원인·휴먼에러·귀책을 입증하지 않습니다."
SECONDS, FPS, WIDTH, HEIGHT = 6, 18, 960, 540


def aware_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Missing timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timezone is required; do not infer UTC/KST")
    return result


def build_candidates(fixture: dict) -> tuple[list[dict], list[dict]]:
    if fixture.get("synthetic") is not True:
        raise ValueError("Only the explicit synthetic fixture may be used")
    by_case = {case["id"]: case for case in fixture.get("cases", [])}
    if len(by_case) != len(fixture.get("cases", [])):
        raise ValueError("Duplicate case ID")
    candidates, missing = [], []
    for case_id, prefix in CASE_PREFIXES.items():
        case = by_case.get(case_id)
        if case is None:
            missing.append({"caseId": case_id, "reason": "case-not-registered"})
            continue
        wms = case.get("wms", {})
        events = {event["id"]: event for event in wms.get("events", [])}
        if len(events) != len(wms.get("events", [])):
            raise ValueError(f"Duplicate event ID: {case_id}")
        picking, shipping = wms.get("picking", {}), wms.get("shipping", {})
        for stage, stage_label, event_number in STAGES:
            event_id = prefix + str(event_number)
            event = events.get(event_id)
            if event is None:
                missing.append({"caseId": case_id, "stage": stage, "eventId": event_id,
                                "reason": "event-not-registered"})
                continue
            occurred = aware_timestamp(event.get("time"))
            if occurred > aware_timestamp(case.get("asOf")):
                raise ValueError(f"Event is after case asOf: {case_id}/{event_id}")
            record = picking if stage == "picking" else shipping if stage == "shipping" else wms.get("sorting", {})
            source_time_key = {"picking": "pickedAt", "sorting": "sortedAt", "shipping": "time"}[stage]
            if record.get(source_time_key) != event.get("time"):
                raise ValueError(f"Stage/event time mismatch: {case_id}/{event_id}")
            # A tote on another process row is not the selected event's tote.
            tote = record.get("toteId")
            case_suffix = case_id[-4:]
            name = f"{case_id.lower()}-{stage}.mp4"
            candidates.append({
                "id": f"SYN-PC3-{case_suffix}-{stage.upper()}", "caseId": case_id,
                "system": "WMS", "cameraId": f"SYN-PC3-CAM-{case_suffix}-{stage.upper()}",
                "cameraProvenance": "new-fictional-camera-for-procedural-clip",
                "eventIds": [event_id], "occurredAt": event["time"],
                "stage": stage, "label": f"{stage_label} 공정 코드 애니메이션 후보",
                "url": f"/demo/pc3/{name}", "localRelativePath": f".local/pc3-media/{name}",
                "synthetic": True, "generationMethod": "procedural Pillow drawing + FFmpeg H.264; no AI media model",
                "registrationStatus": "candidate-not-registered", "publicationStatus": "local-only",
                "startSeconds": 0, "endSeconds": SECONDS, "durationSeconds": SECONDS,
                "notice": NOTICE, "eventRelationStatus": "exact",
                "relationStatus": "exact" if tote is not None else "needs_review",
                "relations": {
                    "storeId": case["store"]["id"], "orderId": picking.get("orderId"),
                    "businessDate": (case.get("tms") or {}).get("bizDate"),
                    "toteId": tote, "toteRelationStatus": "recorded" if tote is not None else "unknown",
                    "pickingToteId": picking.get("toteId"), "shippingToteId": shipping.get("toteId"),
                    "asOf": case["asOf"],
                },
                "sourceRecordKey": f"{case_id}/wms/events/{event_id}",
                "source": {"fixturePath": "data/fixtures/cases.json", "event": event, "processRecord": record},
            })
    return candidates, missing


def validate_overlay(overlay: dict, fixture: dict, asset_root: Path | None = None) -> None:
    if overlay.get("schemaVersion") != "pc3-wms-media-candidates-v1":
        raise ValueError("Wrong overlay schema")
    if overlay.get("synthetic") is not True or overlay.get("integrationStatus") != "candidate-not-registered":
        raise ValueError("Candidate status must remain explicit")
    expected, missing = build_candidates(fixture)
    original_registration = [{"caseId": case["id"], "media": case.get("media", [])} for case in fixture["cases"]]
    if overlay.get("existingRegistrationUnchanged") != original_registration:
        raise ValueError("Existing registered media snapshot was modified")
    actual = overlay.get("mediaCandidates", [])
    if overlay.get("unregistered") != missing or len(actual) != len(expected):
        raise ValueError("Candidate count or missing-event report differs from fixture")
    by_id = {item.get("id"): item for item in actual}
    if len(by_id) != len(actual):
        raise ValueError("Duplicate media ID")
    seen_urls, seen_cameras = set(), set()
    for item in expected:
        measured = by_id.get(item["id"], {})
        for key, value in item.items():
            if measured.get(key) != value:
                raise ValueError(f"Metadata drift: {item['id']}.{key}")
        if measured["url"] in seen_urls or measured["cameraId"] in seen_cameras:
            raise ValueError("Each procedural clip must have a distinct URL and synthetic camera")
        seen_urls.add(measured["url"])
        seen_cameras.add(measured["cameraId"])
        if type(measured.get("bytes")) is not int or measured["bytes"] <= 0:
            raise ValueError("Missing measured byte count")
        if not re.fullmatch(r"[0-9a-f]{64}", str(measured.get("sha256", ""))):
            raise ValueError("Missing measured SHA256")
        validation = measured.get("validation", {})
        if (validation.get("decodedFrames") != SECONDS * FPS
                or validation.get("distinctSampleFrames") != 4
                or validation.get("width") != WIDTH or validation.get("height") != HEIGHT
                or validation.get("fps") != FPS or validation.get("codec") != "h264"
                or validation.get("durationSeconds") != SECONDS):
            raise ValueError("Incomplete decoder validation")
        if asset_root is not None:
            path = asset_root / Path(measured["url"]).name
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"Missing regular asset: {path}")
            if path.stat().st_size != measured["bytes"] or hashlib.sha256(path.read_bytes()).hexdigest() != measured["sha256"]:
                raise ValueError(f"Asset hash mismatch: {path}")


def read_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
