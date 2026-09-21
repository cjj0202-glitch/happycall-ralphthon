"""Fail-closed shared access for the HTTPS hackathon demo, not user-role auth."""
from __future__ import annotations

import base64
import binascii
import asyncio
import hashlib
import hmac
import re
import secrets
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlsplit

from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send


ACCESS_ERROR = "ONEFLOW_ACCESS_USER/PASSWORD must contain valid non-placeholder demo credentials."
MAX_AUTHORIZATION_BYTES = 4096
MAX_LOGIN_BYTES = 2048
SESSION_TTL_SECONDS = 8 * 60 * 60
SESSION_COOKIE = "__Host-oneflow_session"
CHALLENGE = 'Basic realm="OneFlow demo", charset="UTF-8"'
RESPONSE_HEADERS = {"cache-control": "private, no-store", "x-content-type-options": "nosniff",
                    "referrer-policy": "no-referrer"}
_PLACEHOLDERS = ("changeme", "replaceme", "replacewith", "placeholder", "yourpassword",
                 "yourusername", "demopassword", "example", "notasecret", "insertsecret")

LOGIN_HTML = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>해피콜 로그인</title>
<style>body{margin:0;background:#f3f6fa;color:#17263c;font-family:system-ui,sans-serif;display:grid;min-height:100vh;place-items:center}main{width:min(360px,calc(100% - 64px));padding:32px;background:white;border:1px solid #dbe3ed;border-radius:20px;box-shadow:0 12px 36px #182f5010}h1{font-size:26px;margin:8px 0}p{line-height:1.6;color:#53647b;font-size:14px}label{display:block;font-size:14px;margin:18px 0 7px}input{box-sizing:border-box;width:100%;padding:12px;border:1px solid #a8b6c8;border-radius:8px;font:inherit}input:focus{outline:3px solid #dbeafe;border-color:#2563eb}button{width:100%;margin-top:24px;padding:13px;border:0;border-radius:9px;background:#245edb;color:white;font:inherit;font-weight:700;cursor:pointer}.brand{color:#245edb;font-weight:700;letter-spacing:.05em}.error{color:#a52232;background:#fff0f2;padding:10px;border-radius:8px}</style></head>
<body><main><div class="brand">HappyCall · OneFlow</div><h1>해피콜 접속</h1>
<p>안내받은 접속 계정으로 로그인해 주세요.</p>__MESSAGE__
<form method="post" action="/login"><label for="username">사용자 이름</label>
<input id="username" name="username" autocomplete="username" maxlength="64" required autofocus>
<label for="password">비밀번호</label><input id="password" name="password" type="password" autocomplete="current-password" maxlength="256" required>
<button type="submit">접속하기</button></form><p>합성 데이터로 구성한 시연 서비스입니다.<br>접속 계정은 안내받은 담당자에게 확인해 주세요.</p></main></body></html>"""


def _login_response(status=200, message=""):
    # Only fixed application messages are passed here, never submitted values.
    notice = f'<p class="error" role="alert">{message}</p>' if message else ""
    return HTMLResponse(LOGIN_HTML.replace("__MESSAGE__", notice), status_code=status,
                        headers={"content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
                                 "x-frame-options": "DENY"})


def _one_header(scope, name):
    values = [value for key, value in scope.get("headers", []) if key.lower() == name]
    return values[0] if len(values) == 1 else None


def _canonical_origin(value):
    try:
        if (not isinstance(value, str) or len(value) > 300
                or not re.fullmatch(r"https?://(?:[A-Za-z0-9.-]+|\[[A-Fa-f0-9:.]+\])(?::[0-9]{1,5})?", value)):
            return None
        parsed = urlsplit(value)
        port = parsed.port if parsed.port is not None else (443 if parsed.scheme == "https" else 80)
        if not parsed.hostname or not 1 <= port <= 65535:
            return None
        return (parsed.scheme, parsed.hostname.lower(), port)
    except ValueError:
        return None


def _request_origin(scope):
    host = _one_header(scope, b"host")
    if host is None:
        return None
    try:
        return _canonical_origin(scope.get("scheme", "") + "://" + host.decode("ascii"))
    except UnicodeError:
        return None


def _same_origin(scope):
    raw = _one_header(scope, b"origin")
    target = _request_origin(scope)
    if raw is None or target is None:
        return False
    try:
        return _canonical_origin(raw.decode("ascii")) == target
    except UnicodeError:
        return False


async def _login_fields(scope, receive):
    content_type = _one_header(scope, b"content-type")
    if content_type is None or not re.fullmatch(
            rb"application/x-www-form-urlencoded(?:\s*;\s*charset=utf-8)?", content_type.lower()):
        return None, 415
    lengths = [value for key, value in scope.get("headers", []) if key.lower() == b"content-length"]
    if len(lengths) > 1 or (lengths and not re.fullmatch(rb"[0-9]{1,8}", lengths[0])):
        return None, 400
    if lengths and int(lengths[0]) > MAX_LOGIN_BYTES:
        return None, 413
    body = bytearray()
    for _ in range(32):
        try:
            message = await asyncio.wait_for(receive(), timeout=5)
        except (TimeoutError, asyncio.TimeoutError):
            return None, 400
        if message.get("type") != "http.request":
            return None, 400
        body.extend(message.get("body", b""))
        if len(body) > MAX_LOGIN_BYTES:
            return None, 413
        if not message.get("more_body", False):
            break
    else:
        return None, 413
    if lengths and int(lengths[0]) != len(body):
        return None, 400
    try:
        raw = body.decode("ascii")
        if re.search(r"%(?![0-9A-Fa-f]{2})", raw):
            raise ValueError
        pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True,
                          encoding="utf-8", errors="strict", max_num_fields=2)
        if len(pairs) != 2 or {key for key, _ in pairs} != {"username", "password"}:
            raise ValueError
        fields = dict(pairs)
        if not (1 <= len(fields["username"]) <= 64 and 1 <= len(fields["password"]) <= 256):
            raise ValueError
        if ":" in fields["username"] or not all(_visible_ascii(value) for value in fields.values()):
            raise ValueError
        return fields, 200
    except (ValueError, UnicodeError):
        return None, 400


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
        self._session_key = hmac.new(credentials.password_digest,
                                     b"oneflow-browser-session-v1\0" + credentials.username_digest,
                                     hashlib.sha256).digest()

    def _signature(self, payload, origin):
        return hmac.new(self._session_key, (payload + "|" + repr(origin)).encode("ascii"),
                        hashlib.sha256).hexdigest()

    def _new_session(self, scope):
        issued = int(time.time())
        payload = f"v1.{issued}.{issued + SESSION_TTL_SECONDS}.{secrets.token_hex(16)}"
        return payload + "." + self._signature(payload, _request_origin(scope))

    def _session_valid(self, scope):
        raw = _one_header(scope, b"cookie")
        origin = _request_origin(scope)
        if raw is None or len(raw) > 8192 or origin is None:
            return False
        try:
            cookies = [part.strip().partition("=") for part in raw.decode("ascii").split(";")]
            selected = [(separator, value) for name, separator, value in cookies if name == SESSION_COOKIE]
            if len(selected) != 1 or selected[0][0] != "=":
                return False
            values = [selected[0][1]]
            match = re.fullmatch(r"v1\.([0-9]{10,12})\.([0-9]{10,12})\.([a-f0-9]{32})\.([a-f0-9]{64})", values[0])
            if not match:
                return False
            issued, expires = int(match[1]), int(match[2])
            now = int(time.time())
            if not issued <= now < expires or expires - issued != SESSION_TTL_SECONDS:
                return False
            payload, signature = values[0].rsplit(".", 1)
            return hmac.compare_digest(signature, self._signature(payload, origin))
        except (UnicodeError, ValueError):
            return False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def secure_send(message):
            if message["type"] == "http.response.start":
                policy = dict(RESPONSE_HEADERS)
                if scope["path"] == "/login":
                    # HTML form POST uses no-cors: no-referrer turns its Origin
                    # into null. Preserve same-origin login, never cross-site refs.
                    policy["referrer-policy"] = "same-origin"
                denied_names = {key.encode("ascii") for key in RESPONSE_HEADERS}
                headers = [(key, value) for key, value in message.get("headers", [])
                           if key.lower() not in denied_names]
                headers.extend((key.encode("ascii"), value.encode("ascii"))
                               for key, value in policy.items())
                message = {**message, "headers": headers}
            await send(message)

        if scope["path"] == "/healthz" and scope["method"] in {"GET", "HEAD"}:
            response = JSONResponse({"status": "ok"})
            if scope["method"] == "HEAD":
                response = Response(status_code=200, headers=dict(response.headers))
            await response(scope, receive, secure_send)
            return
        if scope["path"] == "/login":
            if scope["method"] == "GET":
                response = _login_response()
            elif scope["method"] != "POST":
                response = Response(status_code=405, headers={"allow": "GET, POST"})
            elif not _same_origin(scope):
                response = _login_response(403, "접속 주소를 확인한 뒤 같은 화면에서 다시 로그인해 주세요.")
            else:
                fields, status = await _login_fields(scope, receive)
                if fields is None:
                    response = _login_response(status, "로그인 입력 형식을 확인해 주세요.")
                else:
                    value = base64.b64encode((fields["username"] + ":" + fields["password"]).encode("ascii"))
                    if not self.credentials.accepts([(b"authorization", b"Basic " + value)]):
                        response = _login_response(401, "사용자 이름 또는 비밀번호가 올바르지 않습니다.")
                    else:
                        response = RedirectResponse("/", status_code=303)
                        response.set_cookie(SESSION_COOKIE, self._new_session(scope), max_age=SESSION_TTL_SECONDS,
                                            path="/", secure=True, httponly=True, samesite="strict")
            await response(scope, receive, secure_send)
            return
        basic = self.credentials.accepts(scope.get("headers", []))
        session = self._session_valid(scope) if not basic else False
        if session and scope["method"] not in {"GET", "HEAD", "OPTIONS"} and not _same_origin(scope):
            await JSONResponse({"error": {"code": "ORIGIN_REQUIRED", "message": "동일한 접속 주소에서 다시 시도해 주세요."}},
                               status_code=403)(scope, receive, secure_send)
            return
        if not basic and not session:
            has_authorization = any(key.lower() == b"authorization" for key, _ in scope.get("headers", []))
            accepts_html = any(key.lower() == b"accept" and b"text/html" in value.lower()
                               for key, value in scope.get("headers", []))
            if (scope["method"] == "GET" and not has_authorization
                    and (scope["path"] == "/" or (accepts_html and scope["path"] != "/api"
                         and not scope["path"].startswith("/api/")))):
                await RedirectResponse("/login", status_code=303)(scope, receive, secure_send)
                return
            response = Response(content=b"" if scope["method"] == "HEAD" else b"Unauthorized",
                                status_code=401, headers={"WWW-Authenticate": CHALLENGE},
                                media_type="text/plain")
            await response(scope, receive, secure_send)
            return
        # Downstream business handlers never need the shared access credential.
        authenticated_scope = {**scope, "headers": [(key, value) for key, value in scope.get("headers", [])
                                                     if key.lower() not in {b"authorization", b"cookie"}]}
        await self.app(authenticated_scope, receive, secure_send)
