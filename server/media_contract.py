"""Canonical synthetic media descriptors shared by delivery and serving.

This validates trusted-manifest structure, not case data or video semantics.
Importing the module has no file, network, environment or process side effects.
"""
from __future__ import annotations

import re

REPOSITORY = "cjj0202-glitch/happycall-ralphthon"
MEDIA_NAMES = ("CASE-0001.wav", "CASE-0002.wav", "sorter-demo.mp4")
TRACKS_NAME = "sorter-demo.tracks.json"
TRACKS_URL = "/demo/" + TRACKS_NAME
TRACKS_SCHEMA = "oneflow-cctv-tracks-v1"
CURRENT_RELEASE_TAG = "demo-media-20260921-audio-v3"
ALLOWED_RELEASE_TAGS = frozenset({CURRENT_RELEASE_TAG, "demo-media-20260922-v4"})
MAX_TRACKS_BYTES = 10_000_000
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_TRACKS_FIELDS = {"schemaVersion", "url", "bytes", "sha256", "videoSha256"}


def _digest(value: object) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def validate_media_manifest(manifest: object, *, require_synthetic: bool = False,
                            check_release: bool = True) -> list[dict]:
    """Return three assets and at most one derived fixed-name tracks descriptor.

    The nested MP4 descriptor alone authorizes the sidecar. A top-level fourth
    asset, tracks on a WAV, an extra descriptor key, or an alternate URL fails.
    ``check_release=False`` preserves legacy three-file offline validators.
    A registered sidecar always requires an explicitly approved Release tag.
    All download entry points must use the default True.
    """
    if (not isinstance(manifest, dict)
            or type(manifest.get("schemaVersion")) is not int
            or manifest["schemaVersion"] != 1
            or manifest.get("repository") != REPOSITORY
            or (check_release and (not isinstance(manifest.get("releaseTag"), str)
                                   or manifest["releaseTag"] not in ALLOWED_RELEASE_TAGS))):
        raise ValueError("INVALID_MEDIA_MANIFEST")
    assets = manifest.get("assets")
    if not isinstance(assets, list) or len(assets) != 3:
        raise ValueError("INVALID_MEDIA_ASSETS")
    validated = []
    seen = set()
    tracks = None
    for asset in assets:
        if (not isinstance(asset, dict) or not isinstance(asset.get("name"), str)
                or asset["name"] not in MEDIA_NAMES or asset["name"] in seen
                or type(asset.get("bytes")) is not int or asset["bytes"] <= 0
                or not _digest(asset.get("sha256"))
                or (require_synthetic and asset.get("synthetic") is not True)):
            raise ValueError("INVALID_MEDIA_ASSET")
        seen.add(asset["name"])
        copy = dict(asset)
        if "tracks" in asset:
            descriptor = asset["tracks"]
            if (asset["name"] != "sorter-demo.mp4" or not isinstance(descriptor, dict)
                    or set(descriptor) != _TRACKS_FIELDS
                    or descriptor.get("schemaVersion") != TRACKS_SCHEMA
                    or descriptor.get("url") != TRACKS_URL
                    or type(descriptor.get("bytes")) is not int
                    or not 0 < descriptor["bytes"] <= MAX_TRACKS_BYTES
                    or not _digest(descriptor.get("sha256"))
                    or not _digest(descriptor.get("videoSha256"))
                    or descriptor["videoSha256"] != asset["sha256"]):
                raise ValueError("INVALID_TRACKS_DESCRIPTOR")
            copy["tracks"] = dict(descriptor)
            tracks = {**descriptor, "name": TRACKS_NAME}
        validated.append(copy)
    if seen != set(MEDIA_NAMES):
        raise ValueError("INVALID_MEDIA_ASSETS")
    if tracks is not None and (not isinstance(manifest.get("releaseTag"), str)
                               or manifest["releaseTag"] not in ALLOWED_RELEASE_TAGS):
        raise ValueError("UNAPPROVED_TRACKS_RELEASE")
    return validated + ([tracks] if tracks is not None else [])
