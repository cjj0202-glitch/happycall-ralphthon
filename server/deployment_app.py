"""Single-origin Next export + existing Connexion API for an HTTPS host.

Run using ``uvicorn --factory server.deployment_app:create_deployment_app``.
Importing this module performs no filesystem writes, env-file reads or network I/O.
"""
from __future__ import annotations

import os
import stat
import hashlib
import json
import re
from collections.abc import Mapping
from email.utils import formatdate
from pathlib import Path

from starlette.responses import FileResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from server.deployment_access import AccessCredentials, DeploymentAccess
from server.media_contract import TRACKS_NAME, TRACKS_URL, validate_media_manifest


STATIC_ERROR = "ONEFLOW_STATIC_DIR must be an absolute, complete, regular Next export directory."
MEDIA_ERROR = "Registered demo media manifest or files failed integrity validation."
PACKAGE_ROOT = Path(__file__).absolute().parents[1]
_PACKAGED_MANIFEST = object()
ROOT_FILES = {"index.html", "404.html", "index.txt", "cases.json", "icon.svg", "favicon.ico"}
NEXT_SUFFIXES = {".js", ".css", ".woff", ".woff2", ".ttf", ".otf", ".png", ".jpg",
                 ".jpeg", ".webp", ".avif", ".gif", ".svg", ".ico"}
REQUIRED_FILES = ("index.html", "404.html", "index.txt", "cases.json", "demo/CASE-0001.wav",
                  "demo/CASE-0002.wav", "demo/sorter-demo.mp4")
MEDIA_TYPES = {".html": "text/html", ".txt": "text/plain", ".json": "application/json",
               ".js": "text/javascript", ".css": "text/css", ".wav": "audio/wav",
               ".mp4": "video/mp4", ".svg": "image/svg+xml", ".ico": "image/x-icon",
               ".woff": "font/woff", ".woff2": "font/woff2", ".ttf": "font/ttf",
               ".otf": "font/otf", ".png": "image/png", ".jpg": "image/jpeg",
               ".jpeg": "image/jpeg", ".webp": "image/webp", ".avif": "image/avif",
               ".gif": "image/gif"}


def _is_link(path: Path) -> bool:
    # Windows directory junctions do not satisfy is_symlink().
    if path.is_symlink() or path.is_junction():
        return True
    return bool(getattr(path.lstat(), "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _regular_file(root: Path, relative: str) -> Path | None:
    """Check every component on each request, including a replaced export root."""
    try:
        candidate = root
        for component in (root, *root.parents):
            if _is_link(component):
                return None
        for part in relative.split("/"):
            candidate = candidate / part
            if _is_link(candidate):
                return None
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(root):
            return None
        information = resolved.stat()
        if not stat.S_ISREG(information.st_mode) or information.st_nlink != 1:
            return None
        return resolved
    except (OSError, ValueError, RuntimeError):
        return None


def _read_regular_snapshot(root: Path, relative: str, maximum: int) -> tuple[bytes, os.stat_result] | None:
    """Snapshot one regular file; never send a path that could change after validation."""
    try:
        candidate = _regular_file(root, relative)
        if candidate is None:
            return None
        before = candidate.stat()
        if before.st_size > maximum:
            return None
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(candidate, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                    or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)):
                return None
            content = stream.read(maximum + 1)
            after = os.fstat(stream.fileno())
        current = _regular_file(root, relative)
        if current is None or len(content) > maximum:
            return None
        now = current.stat()
        signature = lambda item: (item.st_dev, item.st_ino, item.st_size,
                                  item.st_mtime_ns, item.st_nlink,
                                  getattr(item, "st_birthtime_ns", None))
        if signature(before) != signature(opened) or signature(opened) != signature(after) or signature(after) != signature(now):
            return None
        # Windows stat/fstat can expose different ctime meanings. Each provider
        # must still report an unchanged ctime across the complete read.
        if before.st_ctime_ns != now.st_ctime_ns or opened.st_ctime_ns != after.st_ctime_ns:
            return None
        return content, after
    except (OSError, ValueError, RuntimeError):
        return None


def _packaged_manifest() -> Mapping | None:
    relative = "data/demo-media-manifest.json"
    candidate = PACKAGE_ROOT / relative
    # Only genuinely absent manifests mean no registration. Broken links fail closed.
    if not os.path.lexists(candidate):
        return None
    snapshot = _read_regular_snapshot(PACKAGE_ROOT, relative, 10_000_000)
    if snapshot is None:
        raise ValueError(MEDIA_ERROR)
    try:
        manifest = json.loads(snapshot[0])
        if not isinstance(manifest, dict):
            raise ValueError(MEDIA_ERROR)
        return manifest
    except (ValueError, UnicodeError):
        raise ValueError(MEDIA_ERROR) from None


def _snapshot_response(content: bytes, scope: Scope, media_type: str, *, last_modified: str | None = None) -> Response:
    """Serve immutable bytes; registered MP4 supports a single byte range."""
    size = len(content)
    etag = '"' + hashlib.sha256(content).hexdigest() + '"'
    headers = {"accept-ranges": "bytes" if media_type == "video/mp4" else "none",
               "etag": etag, "content-length": str(size)}
    if last_modified is not None:
        headers["last-modified"] = last_modified
    request = {key.lower(): value.decode("latin-1") for key, value in scope.get("headers", [])}
    range_value = request.get(b"range")
    if media_type == "video/mp4" and range_value and request.get(b"if-range", etag) in {etag, last_modified}:
        # Multiple ranges may be ignored by the server. Keep one immutable body
        # instead of allocating an amplified multipart response for large video.
        if "," in range_value:
            return Response(b"" if scope["method"] == "HEAD" else content, media_type=media_type, headers=headers)
        if len(range_value) > 4096:
            return Response(status_code=400)
        if not re.fullmatch(r"bytes=\s*\d*-\d*\s*", range_value):
            return Response(status_code=400)
        first, last = range_value[6:].strip().split("-")
        if not first and not last:
            return Response(status_code=400)
        start = int(first) if first else max(0, size - int(last))
        end = min(size - 1, int(last)) if first and last else size - 1
        if start >= size or end < start or (not first and int(last) == 0):
            return Response(status_code=416, headers={"content-range": f"bytes */{size}"})
        body = content[start:end + 1]
        headers.update({"content-range": f"bytes {start}-{end}/{size}", "content-length": str(len(body))})
        return Response(b"" if scope["method"] == "HEAD" else body, status_code=206,
                        media_type=media_type, headers=headers)
    return Response(b"" if scope["method"] == "HEAD" else content, media_type=media_type, headers=headers)


def _safe_relative(path: str) -> str | None:
    if not path.startswith("/") or any(ord(char) < 32 or ord(char) == 127 for char in path):
        return None
    if any(char in path for char in ("\\", "%", ":", "\x00")):
        return None
    if path == "/":
        return "index.html"
    parts = path[1:].split("/")
    if any(not part or part in {".", ".."} or part.startswith(".")
           or part.endswith((".", " ")) for part in parts):
        return None
    return "/".join(parts)


def _allowed(relative: str) -> bool:
    if relative in ROOT_FILES:
        return True
    suffix = Path(relative).suffix.lower()
    if relative.startswith("_next/static/") and suffix in NEXT_SUFFIXES:
        return True
    return relative.startswith("demo/") and suffix in {".wav", ".mp4"}


def static_directory(environment: Mapping[str, str]) -> Path:
    value = environment.get("ONEFLOW_STATIC_DIR", "")
    if not isinstance(value, str) or not value:
        raise ValueError(STATIC_ERROR)
    try:
        root = Path(value)
        if not root.is_absolute() or any(part in {".", ".."} for part in root.parts):
            raise ValueError(STATIC_ERROR)
        if any(_is_link(component) for component in (root, *root.parents)) or not root.is_dir():
            raise ValueError(STATIC_ERROR)
        root = root.resolve(strict=True)
        for relative in REQUIRED_FILES:
            path = _regular_file(root, relative)
            if path is None or path.stat().st_size == 0:
                raise ValueError(STATIC_ERROR)
        # A manifest-only directory must not pass for a complete Next build.
        for directory, suffix in (("_next/static/chunks", ".js"), ("_next/static/css", ".css")):
            if not any(_regular_file(root, candidate.relative_to(root).as_posix()) is not None
                       and candidate.stat().st_size > 0
                       for candidate in (root / directory).rglob("*" + suffix)):
                raise ValueError(STATIC_ERROR)
        return root
    except (OSError, ValueError, RuntimeError):
        raise ValueError(STATIC_ERROR) from None


class DeploymentRouter:
    def __init__(self, api: ASGIApp, root: Path, *, media_manifest: Mapping | None = None):
        self.api = api
        self.root = root
        self._registered: dict[str, dict] = {}
        if media_manifest is not None:
            try:
                # Legacy three-file exports keep their offline release behavior.
                # The shared validator still enforces the v3/v4 tag for tracks;
                # packaged and injected manifests take the same validation path.
                assets = validate_media_manifest(media_manifest, check_release=False)
                indexed = {asset["name"]: dict(asset) for asset in assets}
                if TRACKS_NAME in indexed:
                    self._registered = {name: indexed[name] for name in ("sorter-demo.mp4", TRACKS_NAME)}
                    if self._media_snapshot() is None:
                        raise ValueError(MEDIA_ERROR)
            except (ValueError, TypeError, KeyError):
                raise ValueError(MEDIA_ERROR) from None

    def _media_snapshot(self) -> dict[str, tuple[bytes, os.stat_result]] | None:
        snapshot = {}
        for name, descriptor in self._registered.items():
            verified = _read_regular_snapshot(self.root, "demo/" + name, descriptor["bytes"])
            if (verified is None or len(verified[0]) != descriptor["bytes"]
                    or hashlib.sha256(verified[0]).hexdigest() != descriptor["sha256"]):
                return None
            snapshot[name] = verified
        return snapshot

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.api(scope, receive, send)
            return
        path = scope["path"]
        if path == "/api" or path.startswith("/api/"):
            # Connexion's OpenAPI paths already contain /api; do not strip it.
            await self.api(scope, receive, send)
            return
        if path == "/healthz" or scope["method"] not in {"GET", "HEAD"}:
            await Response(status_code=405, headers={"Allow": "GET, HEAD"})(scope, receive, send)
            return
        relative = _safe_relative(path)
        if relative in {TRACKS_URL.lstrip("/"), "demo/sorter-demo.mp4"} and self._registered:
            snapshot = self._media_snapshot()
            if snapshot is None:
                await Response(status_code=404)(scope, receive, send)
                return
            name = relative.removeprefix("demo/")
            content, information = snapshot[name]
            response = _snapshot_response(content, scope, MEDIA_TYPES[Path(name).suffix],
                                          last_modified=formatdate(information.st_mtime, usegmt=True))
            await response(scope, receive, send)
            return
        candidate = _regular_file(self.root, relative) if relative and _allowed(relative) else None
        if candidate is None:
            await Response(status_code=404)(scope, receive, send)
            return
        await FileResponse(candidate, media_type=MEDIA_TYPES[candidate.suffix.lower()])(scope, receive, send)


def create_deployment_app(*, environ: Mapping[str, str] | None = None,
                          api_app: ASGIApp | None = None,
                          media_manifest: Mapping | None | object = _PACKAGED_MANIFEST) -> ASGIApp:
    """Uvicorn factory; explicit arguments permit isolated synthetic tests."""
    environment = os.environ if environ is None else environ
    access_mode = environment.get("ONEFLOW_REQUIRE_LOGIN", "0")
    if access_mode not in {"0", "1"}:
        raise ValueError("ONEFLOW_REQUIRE_LOGIN must be 0 or 1.")
    credentials = AccessCredentials.from_environment(environment) if access_mode == "1" else None
    root = static_directory(environment)
    manifest = _packaged_manifest() if media_manifest is _PACKAGED_MANIFEST else media_manifest
    if api_app is None:
        from connexion import AsyncApp

        # Single-origin deployment needs no cross-origin browser permission.
        api_app = AsyncApp(__name__, specification_dir=str(Path(__file__).parent))
        api_app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)
    return DeploymentAccess(DeploymentRouter(api_app, root, media_manifest=manifest), credentials)
