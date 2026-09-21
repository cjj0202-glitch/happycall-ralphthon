"""Single-origin Next export + existing Connexion API for an HTTPS host.

Run using ``uvicorn --factory server.deployment_app:create_deployment_app``.
Importing this module performs no filesystem writes, env-file reads or network I/O.
"""
from __future__ import annotations

import os
import stat
from collections.abc import Mapping
from pathlib import Path

from connexion import AsyncApp
from starlette.responses import FileResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from server.deployment_access import AccessCredentials, DeploymentAccess


STATIC_ERROR = "ONEFLOW_STATIC_DIR must be an absolute, complete, regular Next export directory."
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
    return path.is_symlink() or path.is_junction()


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
        if not stat.S_ISREG(resolved.stat().st_mode):
            return None
        return resolved
    except (OSError, ValueError, RuntimeError):
        return None


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
    def __init__(self, api: ASGIApp, root: Path):
        self.api = api
        self.root = root

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
        candidate = _regular_file(self.root, relative) if relative and _allowed(relative) else None
        if candidate is None:
            await Response(status_code=404)(scope, receive, send)
            return
        await FileResponse(candidate, media_type=MEDIA_TYPES[candidate.suffix.lower()])(scope, receive, send)


def create_deployment_app(*, environ: Mapping[str, str] | None = None,
                          api_app: ASGIApp | None = None) -> ASGIApp:
    """Uvicorn factory; explicit arguments permit isolated synthetic tests."""
    environment = os.environ if environ is None else environ
    credentials = AccessCredentials.from_environment(environment)
    root = static_directory(environment)
    if api_app is None:
        # Single-origin deployment needs no cross-origin browser permission.
        api_app = AsyncApp(__name__, specification_dir=str(Path(__file__).parent))
        api_app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)
    return DeploymentAccess(DeploymentRouter(api_app, root), credentials)
