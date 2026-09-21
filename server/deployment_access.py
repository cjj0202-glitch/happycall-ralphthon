"""Fail-closed shared access for the HTTPS hackathon demo, not user-role auth."""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send


ACCESS_ERROR = "ONEFLOW_ACCESS_USER/PASSWORD must contain valid non-placeholder demo credentials."
MAX_AUTHORIZATION_BYTES = 4096
CHALLENGE = 'Basic realm="OneFlow demo", charset="UTF-8"'
RESPONSE_HEADERS = {"cache-control": "private, no-store", "x-content-type-options": "nosniff",
                    "referrer-policy": "no-referrer"}
_PLACEHOLDERS = ("changeme", "replaceme", "replacewith", "placeholder", "yourpassword",
                 "yourusername", "demopassword", "example", "notasecret", "insertsecret")


def _visible_ascii(value: str) -> bool:
    return all(33 <= ord(char) <= 126 for char in value)


def _placeholder(value: str) -> bool:
    compact = re.sub(r"[^a-z0-9]", "", value.lower())
    return any(marker in compact for marker in _PLACEHOLDERS)


@dataclass(frozen=True)
class AccessCredentials:
    username_digest: bytes = field(repr=False)
    password_digest: bytes = field(repr=False)

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> "AccessCredentials":
        username = environment.get("ONEFLOW_ACCESS_USER", "")
        password = environment.get("ONEFLOW_ACCESS_PASSWORD", "")
        valid = (isinstance(username, str) and isinstance(password, str)
                 and 4 <= len(username) <= 64 and 24 <= len(password) <= 256
                 and _visible_ascii(username) and _visible_ascii(password)
                 and ":" not in username and len(set(password)) >= 12
                 and username.lower() not in {"admin", "user", "demo", "test", "username", "password"}
                 and not _placeholder(username) and not _placeholder(password)
                 and username != password)
        if not valid:
            raise ValueError(ACCESS_ERROR)
        return cls(hashlib.sha256(username.encode("ascii")).digest(),
                   hashlib.sha256(password.encode("ascii")).digest())

    def accepts(self, headers: list[tuple[bytes, bytes]]) -> bool:
        authorization = [value for name, value in headers if name.lower() == b"authorization"]
        if len(authorization) != 1:
            return False
        value = authorization[0]
        if len(value) > MAX_AUTHORIZATION_BYTES:
            return False
        scheme, separator, token = value.partition(b" ")
        if scheme.lower() != b"basic" or separator != b" " or not token:
            return False
        try:
            decoded = base64.b64decode(token, validate=True)
        except (binascii.Error, ValueError):
            return False
        if base64.b64encode(decoded) != token:
            return False
        username, separator, password = decoded.partition(b":")
        if not separator:
            return False
        # Fixed-size digests and two unconditional comparisons avoid a username shortcut.
        username_matches = hmac.compare_digest(hashlib.sha256(username).digest(), self.username_digest)
        password_matches = hmac.compare_digest(hashlib.sha256(password).digest(), self.password_digest)
        return bool(username_matches & password_matches)


class DeploymentAccess:
    def __init__(self, app: ASGIApp, credentials: AccessCredentials):
        self.app = app
        self.credentials = credentials

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def secure_send(message):
            if message["type"] == "http.response.start":
                denied_names = {key.encode("ascii") for key in RESPONSE_HEADERS}
                headers = [(key, value) for key, value in message.get("headers", [])
                           if key.lower() not in denied_names]
                headers.extend((key.encode("ascii"), value.encode("ascii"))
                               for key, value in RESPONSE_HEADERS.items())
                message = {**message, "headers": headers}
            await send(message)

        if scope["path"] == "/healthz" and scope["method"] in {"GET", "HEAD"}:
            response = JSONResponse({"status": "ok"})
            if scope["method"] == "HEAD":
                response = Response(status_code=200, headers=dict(response.headers))
            await response(scope, receive, secure_send)
            return
        if not self.credentials.accepts(scope.get("headers", [])):
            response = Response(content=b"" if scope["method"] == "HEAD" else b"Unauthorized",
                                status_code=401, headers={"WWW-Authenticate": CHALLENGE},
                                media_type="text/plain")
            await response(scope, receive, secure_send)
            return
        # Downstream business handlers never need the shared access credential.
        authenticated_scope = {**scope, "headers": [(key, value) for key, value in scope.get("headers", [])
                                                     if key.lower() != b"authorization"]}
        await self.app(authenticated_scope, receive, secure_send)
