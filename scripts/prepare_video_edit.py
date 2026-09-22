"""Verify an extracted video handoff and create a separate, portable edit workspace.

No downloads, dependency installation, rendering, API calls, or existing-file overwrites.
Renderer dependencies (install separately if needed): imageio-ffmpeg, numpy.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat

ROOT = Path(__file__).resolve().parents[1]
OLD_ROOT = "C:/00.프로젝트/happycall-workflow-ux"
RECORDING = ".local/demo-video/audience-2026-09-22T01-47-27-459Z"
PREFIXES = (".local/demo-video/", ".local/video-handoff/blender/", "apps/web/public/demo/")


def no_links(path: Path) -> None:
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            raise ValueError(f"Link/reparse point rejected: {item}")


def relative(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value or "\0" in value:
        raise ValueError("Manifest paths must be repository-relative POSIX paths")
    p = PurePosixPath(value)
    parts = value.split("/")
    if p.is_absolute() or any(x in ("", ".", "..") or x.endswith((".", " ")) for x in parts):
        raise ValueError(f"Unsafe path: {value}")
    if any(re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", x) for x in parts):
        raise ValueError(f"Reserved path: {value}")
    if not value.startswith(PREFIXES):
        raise ValueError(f"Unapproved payload path: {value}")
    return value


def digest(path: Path) -> tuple[int, str]:
    h = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            count += len(block)
            h.update(block)
    return count, h.hexdigest()


def remap(value, root: Path):
    if isinstance(value, dict):
        return {key: remap(item, root) for key, item in value.items()}
    if isinstance(value, list):
        return [remap(item, root) for item in value]
    if isinstance(value, str):
        normalized = value.replace("\\", "/")
        if normalized.casefold().startswith(OLD_ROOT.casefold() + "/"):
            return str(root / relative(normalized[len(OLD_ROOT) + 1:]))
        if normalized.casefold() == OLD_ROOT.casefold():
            return str(root)
    return value


def copy_new(source: Path, target: Path) -> None:
    no_links(source)
    no_links(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    no_links(target.parent)
    # Exclusive creation also prevents overwrites if a concurrent writer appears.
    with source.open("rb") as incoming, target.open("xb") as outgoing:
        shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)


def prepare(package: Path, root: Path = ROOT) -> dict:
    package = package.absolute()
    root = root.absolute()
    no_links(package)
    no_links(root)
    if not package.is_dir() or not root.is_dir():
        raise ValueError("Package and repository root must be existing directories")
    manifest_file = package / "handoff-manifest.json"
    no_links(manifest_file)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("handoff-manifest.json requires a nonempty files array")
    entries, folded = {}, set()
    for entry in files:
        name = relative(entry["path"])
        if name.casefold() in folded:
            raise ValueError(f"Duplicate/case-colliding manifest path: {name}")
        folded.add(name.casefold())
        if type(entry.get("size")) is not int or entry["size"] < 0 or not isinstance(entry.get("sha256"), str) or not re.fullmatch(r"[a-fA-F0-9]{64}", entry["sha256"]):
            raise ValueError(f"Invalid size/hash: {name}")
        entries[name] = (entry["size"], entry["sha256"].lower())
    actual = set()
    for folder, directories, filenames in os.walk(package, followlinks=False):
        for name in directories + filenames:
            candidate = Path(folder) / name
            no_links(candidate)
            if candidate.is_file():
                actual.add(candidate.relative_to(package).as_posix())
            elif not candidate.is_dir():
                raise ValueError(f"Nonregular package entry: {candidate}")
    if actual != set(entries) | {"handoff-manifest.json"}:
        raise ValueError("Package file inventory differs from manifest (unlisted or missing files)")
    copy_plan, skipped = [], []
    for name, expected in entries.items():
        source, target = package / name, root / name
        no_links(source)
        no_links(target)
        if not source.is_file() or digest(source) != expected:
            raise ValueError(f"Package size/SHA256 mismatch: {name}")
        if target.exists():
            if not target.is_file() or digest(target) != expected:
                raise ValueError(f"Existing file differs; preserved without overwrite: {name}")
            skipped.append(name)
        else:
            copy_plan.append((name, source, target))
    timeline_name, verifier_name = f"{RECORDING}/timeline.json", f"{RECORDING}/verify_audience.py"
    if not {timeline_name, verifier_name}.issubset(entries):
        raise ValueError("Latest recording timeline and original verifier must be in the package")
    original = json.loads((package / timeline_name).read_text(encoding="utf-8"))
    edited = remap(original, root)
    raw = Path(edited.get("rawVideo", ""))
    try:
        raw_name = raw.relative_to(root).as_posix()
    except ValueError:
        raise ValueError("rawVideo must map into this repository") from None
    if raw_name not in entries or not raw_name.startswith(RECORDING + "/") or raw.suffix.lower() != ".webm":
        raise ValueError("Latest raw WebM is not registered in this package")
    for group in ("audio", "narration"):
        for clip in edited.get(group, []):
            try:
                name = Path(clip["file"]).relative_to(root).as_posix()
            except (KeyError, ValueError):
                raise ValueError(f"Unmapped {group} file") from None
            if name not in entries:
                raise ValueError(f"Missing {group} payload: {name}")
    # All package bytes, destination conflicts, and timeline dependencies passed before any copy.
    for name, source, target in copy_plan:
        copy_new(source, target)
        if digest(target) != entries[name]:
            raise ValueError(f"Copied bytes changed during transfer: {name}")
    edit = root / ".local/demo-video" / datetime.now(timezone.utc).strftime("audience-edit-%Y%m%dT%H%M%S%fZ")
    no_links(edit)
    edit.mkdir(parents=True, exist_ok=False)
    copied_raw = edit / raw.name
    copy_new(root / raw_name, copied_raw)
    copy_new(root / verifier_name, edit / "verify_audience.py")
    edited["rawVideo"] = str(copied_raw)
    with (edit / "timeline.json").open("x", encoding="utf-8") as stream:
        json.dump(edited, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return {"status": "PREPARED_NOT_RENDERED", "verifiedFiles": len(entries), "copiedFiles": len(copy_plan), "identicalFilesSkipped": len(skipped), "editDirectory": str(edit), "timeline": str(edit / "timeline.json"), "rawVideo": str(copied_raw), "originalMetadataModified": False, "dependencies": "Renderer requires imageio-ffmpeg and numpy; this helper installs nothing", "next": "Render into editDirectory using scripts/render_dynamic_demo.py, then run its copied verify_audience.py. The verifier expects ai-go-demo-audience-ko.mp4 and the newly generated dynamic-render-plan.json."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True, help="Extracted handoff directory containing handoff-manifest.json")
    args = parser.parse_args()
    try:
        result = prepare(args.package)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Preparation stopped: {error}\n")
    # ASCII JSON keeps Korean paths intact across Windows console code pages.
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
