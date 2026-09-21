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
import stat
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "cjj0202-glitch/happycall-ralphthon"
RELEASE_TAG = "demo-media-20260921-audio-v2"
NAMES = ("CASE-0001.wav", "CASE-0002.wav", "sorter-demo.mp4")
MANIFEST = ROOT / "data/demo-media-manifest.json"
DESTINATION = ROOT / "apps/web/public/demo"
BACKUP_ROOT = ROOT / ".local/demo-media-backups"


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
    if not path.is_file() or is_link(path) or path.stat().st_size != asset["bytes"]:
        return False
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return digest == asset["sha256"]


def is_link(path: Path) -> bool:
    """Include Windows junctions/reparse points, even dangling ones."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return (stat.S_ISLNK(info.st_mode)
            or bool(getattr(info, "st_file_attributes", 0) & 0x400)
            or (stat.S_ISREG(info.st_mode) and info.st_nlink > 1))


def safe_path(path: Path) -> None:
    for part in (path, *path.parents):
        if is_link(part):
            raise ValueError(f"Linked/reparse path is preserved and rejected: {part}")


def snapshot(path: Path) -> tuple:
    safe_path(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"Expected a regular asset file: {path}")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    after = path.stat()
    key = lambda item: (item.st_dev, item.st_ino, item.st_size,
                        item.st_mtime_ns, item.st_ctime_ns)
    if key(before) != key(after):
        raise ValueError(f"Asset changed while reading; preserved: {path}")
    return (*key(after), digest)


def move_no_replace(source: Path, target: Path) -> None:
    """Publish without replacing a concurrent writer's destination."""
    safe_path(source)
    safe_path(target)
    if os.name == "nt":
        os.rename(source, target)  # Windows rename fails if target exists.
    else:
        os.link(source, target)  # POSIX rename would silently overwrite.
        source.unlink()


def approved_source(asset: dict) -> dict:
    if (asset["name"] not in NAMES[:2] or asset.get("synthetic") is not True
            or type(asset.get("sourceBytes")) is not int or asset["sourceBytes"] <= 0
            or not re.fullmatch(r"[0-9a-f]{64}", str(asset.get("sourceSha256", "")))):
        raise ValueError(f"No approved source bytes/SHA256 for upgrade: {asset['name']}")
    return {"bytes": asset["sourceBytes"], "sha256": asset["sourceSha256"]}


def upgrade(assets: list[dict], destination: Path, *, backup_root: Path,
            downloader: Callable[[str, Path], None]) -> dict:
    """Validated, opt-in replacement; completed files remain on partial failure."""
    # The API is used by isolated tests as well as main; do not trust caller names.
    validate_manifest({"schemaVersion": 1, "repository": REPOSITORY,
                       "releaseTag": RELEASE_TAG, "assets": assets})
    destination, backup_root = destination.absolute(), backup_root.absolute()
    safe_path(destination)
    safe_path(backup_root)
    if (backup_root == destination or destination in backup_root.parents
            or backup_root == (ROOT / "apps/web/public").absolute()
            or (ROOT / "apps/web/public").absolute() in backup_root.parents):
        raise ValueError("Backup root must be outside the public media tree")
    needed, skipped, originals = [], [], {}
    for asset in assets:
        path = destination / asset["name"]
        safe_path(path)
        if path.exists():
            if verify(path, asset):
                skipped.append(asset["name"])
                continue
            source = approved_source(asset)
            if not verify(path, source):
                raise ValueError(f"Unrecognized existing asset; preserved: {path}")
            originals[asset["name"]] = snapshot(path)
        needed.append(asset)
    if not needed:
        return {"verified": skipped, "missing": [], "downloaded": [], "upgraded": []}
    backup_root.mkdir(parents=True, exist_ok=True)
    safe_path(backup_root)
    lock = backup_root / ".upgrade.lock"
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise ValueError(f"Another upgrade or interrupted run owns {lock}; inspect before retry") from exc
    run = None
    record = {"status": "preparing", "releaseTag": RELEASE_TAG,
              "destination": str(destination), "installed": [], "backups": []}
    try:
        run = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-"),
                                    dir=backup_root))
        (lock / "owner.json").write_text(json.dumps({"pid": os.getpid(), "run": str(run)}), encoding="utf-8")
        staging = run / "downloads"
        staging.mkdir()
        journal = run / "result.json"

        def save() -> None:
            journal.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

        save()
        for asset in needed:
            downloader(asset["name"], staging)
            if not verify(staging / asset["name"], asset):
                raise ValueError(f"Downloaded asset failed bytes/SHA256 verification: {asset['name']}")
        # Every candidate passes before any existing asset is moved or replaced.
        for name, expected in originals.items():
            if snapshot(destination / name) != expected:
                raise ValueError(f"Asset changed during download; preserved: {name}")
        for name, expected in originals.items():
            data = (destination / name).read_bytes()
            if len(data) != expected[2] or hashlib.sha256(data).hexdigest() != expected[-1]:
                raise ValueError(f"Asset changed during backup; preserved: {name}")
            with (run / name).open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            if not verify(run / name, approved_source(next(a for a in needed if a["name"] == name))):
                raise ValueError(f"Backup verification failed; original preserved: {name}")
            record["backups"].append(name)
        record["status"] = "installing"
        save()
        destination.mkdir(parents=True, exist_ok=True)
        for asset in needed:
            name, final = asset["name"], destination / asset["name"]
            safe_path(final)
            captured = run / (name + ".captured")
            if name in originals:
                if snapshot(final) != originals[name]:
                    raise ValueError(f"Asset changed before replacement; preserved: {name}")
                move_no_replace(final, captured)
            try:
                if name in originals:
                    captured_state = snapshot(captured)
                    # A rename can change POSIX ctime; identity, size, mtime and
                    # bytes must still be the checked original.
                    if (captured_state[:4], captured_state[-1]) != (originals[name][:4], originals[name][-1]):
                        raise ValueError(f"Asset changed at capture; original and captured bytes preserved: {name}")
                # Candidates may also have changed since the initial verification.
                if not verify(staging / name, asset):
                    raise ValueError(f"Staged asset changed; preserved: {name}")
                move_no_replace(staging / name, final)
                record["installed"].append(name)
                save()
            except BaseException:
                if captured.exists() and not final.exists() and not is_link(final):
                    try:
                        move_no_replace(captured, final)
                    except (OSError, ValueError):
                        pass  # Captured bytes and original backup remain for recovery.
                raise
        if not all(verify(destination / a["name"], a) for a in assets):
            raise ValueError("Asset changed before final verification; inspect preserved backups")
        record["status"] = "complete"
        save()
        return {"verified": skipped + record["installed"], "missing": [],
                "downloaded": record["installed"],
                "upgraded": list(originals), "backupDirectory": str(run)}
    except BaseException as exc:
        if run is not None:
            record.update(status="failed", error=str(exc))
            try:
                (run / "result.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            except OSError:
                pass
        raise ValueError(f"Upgrade incomplete; preserve and inspect backup {run}: {exc}") from exc
    finally:
        # Only remove this run's small lock, never recursively delete backups.
        owner = lock / "owner.json"
        if owner.exists():
            owner.unlink()
        lock.rmdir()


def download(name: str, target: Path) -> None:
    # No shell interpolation. Repo, tag, and all possible names are fixed above.
    subprocess.run(
        ["gh", "release", "download", RELEASE_TAG, "--repo", REPOSITORY,
         "--pattern", name, "--dir", str(target)],
        check=True, timeout=120,
    )


def fetch(assets: list[dict], destination: Path, *, verify_only: bool = False,
          upgrade_approved: bool = False, backup_root: Path = BACKUP_ROOT,
          downloader: Callable[[str, Path], None] = download) -> dict:
    if upgrade_approved:
        if verify_only:
            raise ValueError("--upgrade-approved cannot be combined with --verify-only")
        return upgrade(assets, destination, backup_root=backup_root, downloader=downloader)
    safe_path(destination)
    missing: list[dict] = []
    skipped: list[str] = []
    for asset in assets:
        path = destination / asset["name"]
        safe_path(path)
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
    # Same volume as destination for atomic, non-overwriting publication.
    with tempfile.TemporaryDirectory(prefix=".demo-media-", dir=destination.parent) as temp:
        staging = Path(temp)
        for asset in missing:
            downloader(asset["name"], staging)
            if not verify(staging / asset["name"], asset):
                raise ValueError(f"Downloaded asset failed bytes/SHA256 verification: {asset['name']}")
        # Validate every downloaded file before installing any file.
        for asset in missing:
            final = destination / asset["name"]
            safe_path(final)
            if final.exists() or final.is_symlink():
                if not verify(final, asset):
                    raise ValueError(f"Asset appeared during download; preserved without overwrite: {final}")
                skipped.append(asset["name"])
                continue
            move_no_replace(staging / asset["name"], final)
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
    mode.add_argument("--upgrade-approved", action="store_true", help="Replace only exact approved v1 WAVs, preserving private backups")
    args = parser.parse_args()
    try:
        if args.self_test:
            result = self_test()
        else:
            assets = validate_manifest(json.loads(MANIFEST.read_text(encoding="utf-8")))
            result = fetch(assets, DESTINATION, verify_only=args.verify_only,
                           upgrade_approved=args.upgrade_approved)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("missing") else 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "FAILED", "message": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
