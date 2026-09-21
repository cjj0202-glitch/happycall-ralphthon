"""Fetch only the three approved synthetic demo assets from the team GitHub Release.

Requires authenticated GitHub CLI for downloads. Verification and self-test use
only the Python standard library, never an API key or paid media generation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "cjj0202-glitch/happycall-ralphthon"
RELEASE_TAG = "demo-media-20260921"
NAMES = ("CASE-0001.wav", "CASE-0002.wav", "sorter-demo.mp4")
MANIFEST = ROOT / "data/demo-media-manifest.json"
DESTINATION = ROOT / "apps/web/public/demo"


def validate_manifest(manifest: dict) -> list[dict]:
    if (manifest.get("schemaVersion") != 1
            or manifest.get("repository") != REPOSITORY
            or manifest.get("releaseTag") != RELEASE_TAG):
        raise ValueError("Unexpected manifest schema, repository, or release tag")
    assets = manifest.get("assets", [])
    if len(assets) != len(NAMES) or {a.get("name") for a in assets} != set(NAMES):
        raise ValueError("Manifest must contain exactly the three approved asset names")
    for asset in assets:
        if type(asset.get("bytes")) is not int or asset["bytes"] <= 0:
            raise ValueError(f"Invalid byte count: {asset['name']}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(asset.get("sha256", ""))):
            raise ValueError(f"Invalid SHA256: {asset['name']}")
    return assets


def verify(path: Path, asset: dict) -> bool:
    if not path.is_file() or path.is_symlink() or path.stat().st_size != asset["bytes"]:
        return False
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return digest == asset["sha256"]


def download(name: str, target: Path) -> None:
    # No shell interpolation. Repo, tag, and all possible names are fixed above.
    subprocess.run(
        ["gh", "release", "download", RELEASE_TAG, "--repo", REPOSITORY,
         "--pattern", name, "--dir", str(target)],
        check=True, timeout=120,
    )


def fetch(assets: list[dict], destination: Path, *, verify_only: bool = False,
          downloader: Callable[[str, Path], None] = download) -> dict:
    missing: list[dict] = []
    skipped: list[str] = []
    for asset in assets:
        path = destination / asset["name"]
        if path.exists() or path.is_symlink():
            if not verify(path, asset):
                raise ValueError(f"Existing asset differs; preserved without overwrite: {path}")
            skipped.append(asset["name"])
        else:
            missing.append(asset)
    if verify_only:
        return {"verified": skipped, "missing": [a["name"] for a in missing], "downloaded": []}
    if not missing:
        return {"verified": skipped, "missing": [], "downloaded": []}
    destination.mkdir(parents=True, exist_ok=True)
    installed: list[str] = []
    # Same volume as destination so the final os.replace is atomic per file.
    with tempfile.TemporaryDirectory(prefix=".demo-media-", dir=destination.parent) as temp:
        staging = Path(temp)
        for asset in missing:
            downloader(asset["name"], staging)
            if not verify(staging / asset["name"], asset):
                raise ValueError(f"Downloaded asset failed bytes/SHA256 verification: {asset['name']}")
        # Validate every downloaded file before installing any file.
        for asset in missing:
            final = destination / asset["name"]
            if final.exists() or final.is_symlink():
                if not verify(final, asset):
                    raise ValueError(f"Asset appeared during download; preserved without overwrite: {final}")
                skipped.append(asset["name"])
                continue
            os.replace(staging / asset["name"], final)
            installed.append(asset["name"])
    return {"verified": skipped + installed, "missing": [], "downloaded": installed}


def self_test() -> dict:
    """Positive, negative, boundary and mutation checks without network access."""
    payloads = {name: f"synthetic mock content {name}".encode() for name in NAMES}
    manifest = {"schemaVersion": 1, "repository": REPOSITORY, "releaseTag": RELEASE_TAG,
                "assets": [{"name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                           for name, data in payloads.items()]}
    assets = validate_manifest(manifest)
    passed: list[str] = []
    calls: list[str] = []

    def fake_download(name: str, target: Path) -> None:
        calls.append(name)
        (target / name).write_bytes(payloads[name])

    def forbidden_download(name: str, target: Path) -> None:
        raise AssertionError("An existing valid asset must not trigger a download")

    with tempfile.TemporaryDirectory(prefix="demo-media-selftest-") as temp:
        destination = Path(temp) / "demo"
        result = fetch(assets, destination, verify_only=True, downloader=forbidden_download)
        assert result["missing"] == list(NAMES) and not destination.exists()
        passed.append("verify-only reports all three missing without writes or downloads")
        result = fetch(assets, destination, downloader=fake_download)
        assert result["downloaded"] == list(NAMES) and calls == list(NAMES)
        assert all(verify(destination / a["name"], a) for a in assets)
        passed.append("three mock downloads install only after size and hash verification")
        timestamps = {name: (destination / name).stat().st_mtime_ns for name in NAMES}
        result = fetch(assets, destination, downloader=forbidden_download)
        assert result["downloaded"] == [] and result["verified"] == list(NAMES)
        assert timestamps == {name: (destination / name).stat().st_mtime_ns for name in NAMES}
        passed.append("three matching existing assets skip network and preserve timestamps")
        damaged = destination / NAMES[0]
        original = damaged.read_bytes()
        mutation = bytes([original[0] ^ 1]) + original[1:]
        damaged.write_bytes(mutation)
        assert damaged.stat().st_size == assets[0]["bytes"] and not verify(damaged, assets[0])
        try:
            fetch(assets, destination, downloader=forbidden_download)
        except ValueError:
            assert damaged.read_bytes() == mutation
        else:
            raise AssertionError("Same-size hash corruption was accepted")
        passed.append("same-size SHA256 mutation fails and existing content is preserved")
        assert not verify(destination / NAMES[1], {**assets[1], "bytes": assets[1]["bytes"] + 1})
        passed.append("wrong byte-count boundary fails")
        corrupt_target = Path(temp) / "corrupt-download"

        def corrupt_download(name: str, target: Path) -> None:
            data = payloads[name]
            (target / name).write_bytes(data if name != NAMES[-1] else bytes([data[0] ^ 1]) + data[1:])

        try:
            fetch(assets, corrupt_target, downloader=corrupt_download)
        except ValueError:
            assert not any(corrupt_target.iterdir())
        else:
            raise AssertionError("Corrupted download was installed")
        passed.append("corrupt third download prevents all three installations")
        for field, value in (("repository", "other/repository"), ("releaseTag", "other-tag")):
            try:
                validate_manifest({**manifest, field: value})
            except ValueError:
                pass
            else:
                raise AssertionError(f"Unexpected {field} accepted")
        passed.append("alternate repository and tag rejected")
        bad_assets = [{**assets[0], "name": "../unexpected.wav"}, *assets[1:]]
        try:
            validate_manifest({**manifest, "assets": bad_assets})
        except ValueError:
            pass
        else:
            raise AssertionError("Unexpected asset path accepted")
        passed.append("asset path outside fixed three-name allowlist rejected")
    return {"selfTest": "PASS", "checks": len(passed), "networkCalls": 0, "evidence": passed}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify-only", action="store_true", help="Check local files without network or writes")
    mode.add_argument("--self-test", action="store_true", help="Run isolated mock checks without network")
    args = parser.parse_args()
    try:
        if args.self_test:
            result = self_test()
        else:
            assets = validate_manifest(json.loads(MANIFEST.read_text(encoding="utf-8")))
            result = fetch(assets, DESTINATION, verify_only=args.verify_only)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("missing") else 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "FAILED", "message": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
