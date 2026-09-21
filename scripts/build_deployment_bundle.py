"""Validate a completed Next export and assemble a new, secret-free deployment.

--build runs npm build and records completion only. Without --build, assemble a
bundle from that completion record. Neither mode logs in, deploys or loads .env.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]
# Keep direct ``python scripts/build_deployment_bundle.py`` compatible.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from server.media_contract import validate_media_manifest
BUILD_STAMP_NAME = ".oneflow-build.json"
STAMP_SCHEMA = "oneflow-next-build-v1"
BUNDLE_SCHEMA = "oneflow-deployment-bundle-v1"
MEDIA_MANIFEST = "data/demo-media-manifest.json"
MEDIA_NAMES = ("CASE-0001.wav", "CASE-0002.wav", "sorter-demo.mp4")
# These JSON files are imported into the WMS/TMS client bundle from outside web/.
# A build is stale if any of them changes, even when public asset bytes do not.
FRONTEND_DATA_FILES = ("data/fixtures/cases.json", MEDIA_MANIFEST, "data/overlays/pc4-tms.json")
SOURCE_FILES = (
    "server/__init__.py", "server/analysis_schema.py", "server/budget.py",
    "server/cas_budget.py", "server/cas_repository.py", "server/cas_store.py",
    "server/deployment_access.py", "server/deployment_app.py", "server/errors.py",
    "server/media_contract.py", "server/notifications.py",
    "server/handlers.py", "server/live.py", "server/repository.py",
    "server/intake_idempotency.py", "server/claim_grounding.py", "server/request_grounding.py",
    "server/runtime_config.py", "server/runtime_storage.py", "server/service.py",
    "server/vercel_blob_store.py", "server/openapi.yaml", "scripts/demo_openai_env.py",
    "data/fixtures/cases.json", MEDIA_MANIFEST, "pyproject.toml", "uv.lock",
)
TEMPLATES = {"deploy/vercel/index.py": "api/index.py", "deploy/vercel/vercel.json": "vercel.json"}
ROOT_STATIC = {"index.html", "404.html", "index.txt", "cases.json", "icon.svg", "favicon.ico"}
NEXT_SUFFIXES = {".js", ".css", ".woff", ".woff2", ".ttf", ".otf", ".png", ".jpg",
                 ".jpeg", ".webp", ".avif", ".gif", ".svg", ".ico"}
REQUIRED_STATIC = {"index.html", "404.html", "index.txt", "cases.json",
                   *("demo/" + name for name in MEDIA_NAMES)}
MAX_BUNDLE_BYTES = 500_000_000  # Input payload only; installed dependencies are additional.
_HEX = re.compile(r"[a-f0-9]{64}\Z")
_TIMESTAMP = re.compile(r"\d{8}T\d{12}Z\Z")
_REVISION = re.compile(r"[a-f0-9]{40}\Z")
_SECRET_NAME = re.compile(r"(?:^\.env(?:\.|$)|credential|secret|private[._-]?key|id_rsa)", re.I)
_SECRET_PATTERNS = (
    re.compile(rb"\bsk-[A-Za-z0-9_-]{32,}"),
    re.compile(rb"\b(?:ghp_|github_pat_|vercel_blob_rw_)[A-Za-z0-9_-]{16,}"),
    re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(rb"-----BEGIN (?:[A-Z ]*PRIVATE KEY|OPENSSH PRIVATE KEY)-----"),
    re.compile(rb"(?i)(?:api[_-]?key|access[_-]?password|client[_-]?secret|password|token)\s*['\"]?\s*[:=]\s*['\"][A-Za-z0-9_!@#$%^&*+=./:-]{16,}['\"]"),
)
_TEXT_SUFFIXES = {".py", ".json", ".toml", ".lock", ".yaml", ".html", ".txt", ".js",
                  ".css", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".svg"}


class BundleError(ValueError):
    """Static diagnostics deliberately omit file contents and secret values."""


def _error(code: str) -> BundleError:
    return BundleError(code)


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _no_links(path: Path) -> None:
    for component in (path, *path.parents):
        if component.is_symlink() or component.is_junction():
            raise _error("LINK_PATH_REJECTED")
        if component.exists():
            info = component.stat()
            if stat.S_ISREG(info.st_mode) and info.st_nlink > 1:
                raise _error("LINK_PATH_REJECTED")


def _root(path: Path) -> Path:
    try:
        absolute = Path(os.path.abspath(path))
        _no_links(absolute)
        if not absolute.is_dir():
            raise _error("SOURCE_ROOT_REQUIRED")
        return absolute.resolve(strict=True)
    except OSError:
        raise _error("SOURCE_ROOT_UNAVAILABLE") from None


def _relative_name(name: str) -> bool:
    parts = name.split("/")
    return bool(name and not any(not part or part in {".", ".."} or part.endswith((".", " "))
                                for part in parts)
                and not any(char in name for char in ("\\", ":", "%", "\0"))
                and not any(ord(char) < 32 for char in name))


def _secure_path(root: Path, relative: str, *, exists: bool = True) -> Path:
    if not _relative_name(relative):
        raise _error("INVALID_RELATIVE_PATH")
    path = root / relative
    _no_links(path)
    try:
        if not path.resolve(strict=exists).is_relative_to(root):
            raise _error("PATH_OUTSIDE_SOURCE")
    except OSError:
        raise _error("REQUIRED_INPUT_MISSING") from None
    return path


def _read(root: Path, relative: str) -> bytes:
    try:
        path = _secure_path(root, relative)
        before = path.stat()
        if not stat.S_ISREG(before.st_mode):
            raise _error("REGULAR_FILE_REQUIRED")
        content = path.read_bytes()
        _no_links(path)
        after = path.stat()
        if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                or len(content) != before.st_size):
            raise _error("INPUT_CHANGED_DURING_READ")
        return content
    except OSError:
        raise _error("REQUIRED_INPUT_UNAVAILABLE") from None


def _check_name(relative: str) -> None:
    if (not _relative_name(relative) or any(part.startswith(".") or _SECRET_NAME.search(part)
                                          for part in relative.split("/"))
            or Path(relative).suffix.lower() in {".pem", ".key", ".pfx", ".p12", ".sqlite", ".db", ".jsonl"}):
        raise _error("PRIVATE_OR_AMBIGUOUS_FILENAME")


def _check_content(relative: str, content: bytes) -> None:
    if Path(relative).suffix.lower() in _TEXT_SUFFIXES:
        if any(pattern.search(content) for pattern in _SECRET_PATTERNS):
            raise _error("CREDENTIAL_CONTENT_REJECTED")


def _walk(root: Path, relative: str) -> list[str]:
    directory = _secure_path(root, relative)
    if not directory.is_dir():
        raise _error("REQUIRED_DIRECTORY_MISSING")
    found = []
    for child in sorted(directory.iterdir()):
        name = child.relative_to(root).as_posix()
        _no_links(child)
        if child.is_dir():
            found.extend(_walk(root, name))
        elif child.is_file():
            found.append(name)
        else:
            raise _error("REGULAR_FILE_REQUIRED")
    return found


def _inventory_fingerprint(files: dict[str, bytes]) -> str:
    entries = [{"path": name, "size": len(content), "sha256": _digest(content)}
               for name, content in sorted(files.items())]
    return _digest(_json_bytes(entries))


def source_fingerprint(root: Path) -> str:
    root = _root(root)
    web = _secure_path(root, "apps/web")
    selected = list(FRONTEND_DATA_FILES)
    for child in web.iterdir():
        if child.name.startswith(".env"):
            raise _error("FRONTEND_ENV_FILE_REJECTED")
        if child.is_file() and child.name != "next-env.d.ts" and child.suffix in {
                ".ts", ".js", ".mjs", ".cjs", ".json", ".css"}:
            selected.append(child.relative_to(root).as_posix())
    for directory in ("app", "components", "lib", "public", "scripts"):
        target = web / directory
        _no_links(target)
        if target.exists():
            selected.extend(_walk(root, "apps/web/" + directory))
        elif directory in {"app", "lib", "public"}:
            raise _error("FRONTEND_SOURCE_MISSING")
    required = {"apps/web/package.json", "apps/web/package-lock.json", "apps/web/tsconfig.json",
                "apps/web/next.config.ts", "apps/web/app/page.tsx", "apps/web/app/layout.tsx"}
    if not required <= set(selected):
        raise _error("FRONTEND_SOURCE_MISSING")
    files = {}
    for name in sorted(selected):
        _check_name(name)
        content = _read(root, name)
        _check_content(name, content)
        files[name] = content
    return _inventory_fingerprint(files)


def _output_files(root: Path) -> dict[str, bytes]:
    files = {}
    prefix = "apps/web/out/"
    approved_media = {"demo/" + asset["name"] for asset in _registered_media(root)}
    for name in _walk(root, prefix.rstrip("/")):
        relative = name.removeprefix(prefix)
        if relative == BUILD_STAMP_NAME:
            continue
        _check_name(relative)
        allowed = (relative in ROOT_STATIC
                   or (relative.startswith("_next/static/") and Path(relative).suffix.lower() in NEXT_SUFFIXES)
                   or relative in approved_media)
        if not allowed:
            raise _error("UNAPPROVED_EXPORT_FILE")
        content = _read(root, name)
        _check_content(name, content)
        files[relative] = content
    required = REQUIRED_STATIC | approved_media
    if not required <= files.keys() or any(not files[name] for name in required):
        raise _error("INCOMPLETE_NEXT_EXPORT")
    for directory, suffix in (("_next/static/chunks/", ".js"), ("_next/static/css/", ".css")):
        if not any(name.startswith(directory) and name.endswith(suffix) and content for name, content in files.items()):
            raise _error("INCOMPLETE_NEXT_EXPORT")
    return files


def _parse_json(content: bytes) -> object:
    try:
        return json.loads(content.decode("utf-8-sig"))
    except (ValueError, UnicodeError):
        raise _error("INVALID_JSON_INPUT") from None


def _registered_media(root: Path) -> list[dict]:
    manifest = _parse_json(_read(root, MEDIA_MANIFEST))
    try:
        # This offline path never chooses a Release. Download tag restrictions
        # are enforced by fetch; preserve legacy packaging callers here.
        return validate_media_manifest(manifest, require_synthetic=True, check_release=False)
    except ValueError:
        raise _error("INVALID_MEDIA_MANIFEST") from None


def _media(root: Path, manifest_path: Path) -> dict[str, bytes]:
    expected = _secure_path(root, MEDIA_MANIFEST)
    _no_links(manifest_path)
    # Windows TEMP can use an 8.3 spelling while _root() resolves the long name.
    # Both paths must still identify the one canonical, non-linked file.
    if Path(os.path.abspath(manifest_path)).resolve(strict=True) != expected:
        raise _error("CANONICAL_MEDIA_MANIFEST_REQUIRED")
    assets = _registered_media(root)
    verified = {}
    for asset in assets:
        for directory in ("apps/web/public/demo/", "apps/web/out/demo/"):
            path = _secure_path(root, directory + asset["name"])
            if path.stat().st_size != asset["bytes"]:
                raise _error("MEDIA_BYTES_OR_HASH_MISMATCH")
        content = _read(root, "apps/web/public/demo/" + asset["name"])
        exported = _read(root, "apps/web/out/demo/" + asset["name"])
        if (len(content) != asset["bytes"] or _digest(content) != asset["sha256"]
                or exported != content):
            raise _error("MEDIA_BYTES_OR_HASH_MISMATCH")
        verified[asset["name"]] = content
    return verified


def _stamp_path(root: Path) -> Path:
    return _secure_path(root, "apps/web/out/" + BUILD_STAMP_NAME, exists=False)


def _invalidate_stamp(root: Path) -> None:
    path = _stamp_path(root)
    if path.exists():
        if not path.is_file():
            raise _error("INVALID_BUILD_STAMP")
        path.unlink()


def write_build_stamp(root: Path, source_before: str) -> Path:
    """Record a successful caller-controlled build; not exposed as a CLI signing shortcut."""
    root = _root(root)
    _invalidate_stamp(root)
    source_after = source_fingerprint(root)
    if not isinstance(source_before, str) or not _HEX.fullmatch(source_before) or source_after != source_before:
        raise _error("SOURCE_CHANGED_DURING_BUILD")
    files = _output_files(root)
    _media(root, root / MEDIA_MANIFEST)
    payload = {"schemaVersion": STAMP_SCHEMA, "status": "complete", "command": ["npm", "run", "build"],
               "sourceBefore": source_before, "sourceAfter": source_after,
               "outputFingerprint": _inventory_fingerprint(files), "outputFileCount": len(files),
               "nextPublicApiBase": "", "completedAt": datetime.now(timezone.utc).isoformat()}
    payload["recordDigest"] = _digest(_json_bytes(payload))
    path = _stamp_path(root)
    with path.open("xb") as stream:
        stream.write(_json_bytes(payload))
    return path


def _verified_stamp(root: Path, files: dict[str, bytes]) -> dict:
    payload = _parse_json(_read(root, "apps/web/out/" + BUILD_STAMP_NAME))
    required = {"schemaVersion", "status", "command", "sourceBefore", "sourceAfter", "outputFingerprint",
                "outputFileCount", "nextPublicApiBase", "completedAt", "recordDigest"}
    if not isinstance(payload, dict) or set(payload) != required:
        raise _error("INVALID_BUILD_STAMP")
    digest = payload["recordDigest"]
    body = {key: value for key, value in payload.items() if key != "recordDigest"}
    if (digest != _digest(_json_bytes(body)) or payload["schemaVersion"] != STAMP_SCHEMA
            or payload["status"] != "complete" or payload["command"] != ["npm", "run", "build"]
            or payload["nextPublicApiBase"] != "" or payload["sourceBefore"] != payload["sourceAfter"]
            or payload["sourceAfter"] != source_fingerprint(root)
            or payload["outputFingerprint"] != _inventory_fingerprint(files)
            or payload["outputFileCount"] != len(files)):
        raise _error("STALE_OR_CHANGED_BUILD_STAMP")
    return payload


def _check_runtime(files: dict[str, bytes]) -> None:
    try:
        project = tomllib.loads(files["pyproject.toml"].decode("utf-8-sig"))
        lock = tomllib.loads(files["uv.lock"].decode("utf-8-sig"))
        if (project["project"]["requires-python"] != ">=3.12,<3.13"
                or lock.get("requires-python") not in {">=3.12,<3.13", "==3.12.*"}):
            raise _error("PYTHON_312_RUNTIME_REQUIRED")
        for name, content in files.items():
            if not name.endswith(".py"):
                continue
            tree = ast.parse(content, filename=name)
            for node in ast.walk(tree):
                modules = ([node.module] if isinstance(node, ast.ImportFrom) and node.module
                           else [item.name for item in node.names] if isinstance(node, ast.Import) else [])
                for module in modules:
                    if module.startswith(("server.", "scripts.")) and module.replace(".", "/") + ".py" not in files:
                        raise _error("RUNTIME_MODULE_OUTSIDE_BUNDLE")
        fixture = _parse_json(files["data/fixtures/cases.json"])
        if isinstance(fixture, dict):
            approved = fixture.get("synthetic") is True and isinstance(fixture.get("cases"), list) and bool(fixture["cases"])
        else:
            approved = isinstance(fixture, list) and bool(fixture) and all(isinstance(row, dict) and row.get("synthetic") is True for row in fixture)
        if not approved:
            raise _error("SYNTHETIC_FIXTURE_REQUIRED")
        routing = _parse_json(files["vercel.json"])
        if (routing.get("routes") != [{"src": "/(.*)", "dest": "/api/index.py"}]
                or routing.get("framework", "unexpected") is not None
                or routing.get("version") != 2 or routing.get("buildCommand") != ""
                or routing.get("installCommand") != "uv sync --frozen --no-dev"
                or routing.get("functions") != {"api/index.py": {"maxDuration": 240}}
                or set(routing) != {"$schema", "version", "framework", "buildCommand", "installCommand", "functions", "routes"}):
            raise _error("UNPROTECTED_ROUTING_REJECTED")
    except (KeyError, ValueError, TypeError, SyntaxError, AttributeError):
        raise _error("INVALID_RUNTIME_INPUT") from None


def _payload(root: Path, manifest: Path) -> tuple[dict[str, bytes], dict]:
    output = _output_files(root)
    stamp = _verified_stamp(root, output)
    media = _media(root, manifest)
    files = {}
    for source in (*SOURCE_FILES, *TEMPLATES):
        content = _read(root, source)
        _check_name(source)
        _check_content(source, content)
        files[TEMPLATES.get(source, source)] = content
    _check_runtime(files)
    if (files["data/fixtures/cases.json"] != _read(root, "apps/web/public/cases.json")
            or files["data/fixtures/cases.json"] != output["cases.json"]):
        raise _error("SYNTHETIC_FIXTURE_COPIES_DIFFER")
    files.update({"apps/web/out/" + name: content for name, content in output.items()})
    files.update({"apps/web/public/demo/" + name: content for name, content in media.items()})
    return files, stamp


def build_bundle(root: Path, manifest_path: Path, *, timestamp: str | None = None,
                 revision: str | None = None, max_bytes: int = MAX_BUNDLE_BYTES) -> Path:
    root = _root(root)
    timestamp = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    if revision is None:
        try:
            revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root,
                                               stderr=subprocess.DEVNULL, text=True).strip()
        except (OSError, subprocess.SubprocessError):
            raise _error("GIT_REVISION_UNAVAILABLE") from None
    if not _TIMESTAMP.fullmatch(timestamp) or not _REVISION.fullmatch(revision):
        raise _error("INVALID_OUTPUT_IDENTITY")
    if type(max_bytes) is not int or max_bytes <= 0:
        raise _error("INVALID_SIZE_LIMIT")
    destination = _secure_path(root, "dist/deployment/" + timestamp + "-" + revision[:12], exists=False)
    if destination.exists():
        raise _error("OUTPUT_ALREADY_EXISTS")
    files, stamp = _payload(root, Path(manifest_path))
    total = sum(len(content) for content in files.values())
    if total > max_bytes:
        raise _error("BUNDLE_INPUT_SIZE_LIMIT_EXCEEDED")
    manifest = {"schemaVersion": BUNDLE_SCHEMA, "status": "complete", "sourceRevision": revision,
                "createdAt": timestamp, "frontendSourceFingerprint": stamp["sourceAfter"],
                "frontendOutputFingerprint": stamp["outputFingerprint"], "buildRecordDigest": stamp["recordDigest"],
                "totalBytes": total, "files": [{"path": name, "size": len(content), "sha256": _digest(content)}
                                               for name, content in sorted(files.items())],
                "notVerified": ["Vercel account permissions", "provider build and final dependency size",
                                "HTTPS routing and browser access", "remote storage and live model requests"]}
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        _no_links(destination)
        destination.mkdir(exist_ok=False)
        for name, content in sorted(files.items()):
            target = _secure_path(destination, name, exists=False)
            target.parent.mkdir(parents=True, exist_ok=True)
            _no_links(target)
            with target.open("xb") as stream:
                stream.write(content)
            if _read(destination, name) != content:
                raise _error("COPIED_BYTES_CHANGED")
        fresh_files, fresh_stamp = _payload(root, Path(manifest_path))
        if fresh_files != files or fresh_stamp != stamp:
            raise _error("SOURCE_CHANGED_DURING_PACKAGE")
        marker = _secure_path(destination, ".bundle-manifest.json", exists=False)
        with marker.open("xb") as stream:
            stream.write(_json_bytes(manifest))
    except OSError:
        # Do not remove a partially written tree or overwrite someone else's output.
        raise _error("BUNDLE_WRITE_FAILED_INCOMPLETE_OUTPUT_PRESERVED") from None
    return destination


def run_build(root: Path) -> Path:
    root = _root(root)
    _invalidate_stamp(root)
    before = source_fingerprint(root)
    command = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if command is None:
        raise _error("NPM_UNAVAILABLE")
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP",
               "USERPROFILE", "APPDATA", "LOCALAPPDATA", "HOME"}
    environment = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    environment.update({"CI": "1", "NEXT_TELEMETRY_DISABLED": "1", "NODE_ENV": "production",
                        "NEXT_PUBLIC_API_BASE": "", "NPM_CONFIG_UPDATE_NOTIFIER": "false"})
    try:
        result = subprocess.run([command, "run", "build"], cwd=root / "apps/web", env=environment,
                                capture_output=True, timeout=600, check=False)
    except (OSError, subprocess.SubprocessError):
        raise _error("FRONTEND_BUILD_FAILED_NO_COMPLETION_RECORD") from None
    if result.returncode != 0:
        raise _error("FRONTEND_BUILD_FAILED_NO_COMPLETION_RECORD")
    return write_build_stamp(root, before)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--media-manifest", type=Path)
    parser.add_argument("--build", action="store_true", help="Run npm build and record completion only; no package")
    args = parser.parse_args(argv)
    try:
        root = _root(args.root)
        if args.build:
            output = run_build(root)
            print(json.dumps({"status": "build-recorded", "path": str(output)}, ensure_ascii=False))
        else:
            output = build_bundle(root, args.media_manifest or root / MEDIA_MANIFEST)
            print(json.dumps({"status": "packaged-not-deployed", "path": str(output)}, ensure_ascii=False))
        return 0
    except BundleError as error:
        print("Deployment preparation refused: " + str(error), file=sys.stderr)
        return 1
    except OSError:
        print("Deployment preparation refused: FILESYSTEM_UNAVAILABLE", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
