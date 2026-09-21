"""Offline browser login and session boundaries; synthetic credentials only."""
import asyncio
import base64
from urllib.parse import urlencode

import httpx
import pytest
from starlette.responses import JSONResponse

from server import deployment_access as access

USER = "reviewer-61"
PASSWORD = "T7!pK9@qV2#rM4$sN6%wZ8&cX0"
ORIGIN = "https://demo.invalid"
AUTH = "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()


class Echo:
    def __init__(self):
        self.calls = []

    async def __call__(self, scope, receive, send):
        self.calls.append(scope)
        await JSONResponse({"ok": True})(scope, receive, send)


def app(password=PASSWORD):
    return access.DeploymentAccess(Echo(), access.AccessCredentials.from_environment(
        {"ONEFLOW_ACCESS_USER": USER, "ONEFLOW_ACCESS_PASSWORD": password}))


def request(application, method="GET", path="/", **kwargs):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url=ORIGIN) as client:
            return await client.request(method, path, **kwargs)
    return asyncio.run(run())


def login(application, **changes):
    return request(application, "POST", "/login", headers={"Origin": ORIGIN},
                   data={"username": USER, "password": PASSWORD, **changes})


def cookie(application):
    response = login(application)
    assert response.status_code == 303
    return response.headers["set-cookie"].split(";", 1)[0]


def test_public_login_redirect_form_and_existing_basic_contract():
    application = app()
    response = request(application)
    assert response.status_code == 303 and response.headers["location"] == "/login"
    form = request(application, path="/login?next=https://evil.invalid")
    assert form.status_code == 200 and 'action="/login"' in form.text
    assert "접속하기" in form.text and 'type="password"' in form.text
    assert USER not in form.text and PASSWORD not in form.text and "evil.invalid" not in form.text
    assert "frame-ancestors 'none'" in form.headers["content-security-policy"]
    assert form.headers["cache-control"] == "private, no-store"
    for path in ("/api/cases", "/demo/CASE-0001.wav", "/_next/static/app.js"):
        assert request(application, path=path).status_code == 401
    assert request(application, "HEAD").status_code == 401
    assert request(application, headers={"Authorization": "Basic invalid"}).status_code == 401
    assert request(application, "POST", "/api/intake", headers={"Authorization": AUTH}).status_code == 200
    assert request(application, path="/healthz").json() == {"status": "ok"}
    assert request(application, path="/page.html", headers={"Accept": "text/html"}).headers["location"] == "/login"


def test_login_cookie_attributes_authenticated_get_and_sanitized_failure():
    application = app()
    response = login(application)
    header = response.headers["set-cookie"]
    for attribute in ("HttpOnly", "Secure", "SameSite=strict", "Path=/", "Max-Age=28800"):
        assert attribute in header
    assert "Domain=" not in header and response.headers["location"] == "/"
    assert USER not in header and PASSWORD not in header
    response = request(application, path="/api/cases", headers={"Cookie": header.split(";", 1)[0]})
    assert response.status_code == 200
    assert not any(k.lower() in {b"cookie", b"authorization"} for k, _ in application.app.calls[-1]["headers"])
    failed = login(application, password="wrong-value-private")
    assert failed.status_code == 401 and "올바르지 않습니다" in failed.text
    assert "set-cookie" not in failed.headers and "wrong-value-private" not in failed.text


@pytest.mark.parametrize("origin", [None, "null", "http://demo.invalid", "https://evil.invalid",
                                    "https://demo.invalid.evil.invalid", "https://demo.invalid:444",
                                    "https://demo.invalid:0", "https://demo.invalid/", "https://demo.invalid@evil.invalid"])
def test_login_rejects_foreign_missing_or_malformed_origin(origin):
    application = app()
    response = request(application, "POST", "/login", headers={} if origin is None else {"Origin": origin},
                       data={"username": USER, "password": PASSWORD})
    assert response.status_code == 403 and "set-cookie" not in response.headers
    assert application.app.calls == []


def test_duplicate_origins_or_hosts_and_forwarded_origin_spoof_are_rejected():
    application = app()
    for headers in ([('Origin', ORIGIN), ('Origin', ORIGIN)],
                    [('Origin', ORIGIN), ('Host', 'demo.invalid'), ('Host', 'demo.invalid')],
                    [('Origin', 'https://evil.invalid'), ('X-Forwarded-Host', 'evil.invalid')]):
        assert request(application, "POST", "/login", headers=headers,
                       data={"username": USER, "password": PASSWORD}).status_code == 403


@pytest.mark.parametrize("method", ["POST", "PATCH", "PUT", "DELETE"])
def test_cookie_mutations_require_same_origin_but_basic_is_unchanged(method):
    application = app()
    session = cookie(application)
    for origin in (None, "null", "https://evil.invalid"):
        headers = {"Cookie": session, **({"Origin": origin} if origin else {})}
        assert request(application, method, "/api/cases/synthetic", headers=headers).status_code == 403
    assert request(application, method, "/api/cases/synthetic",
                   headers={"Cookie": session, "Origin": ORIGIN}).status_code == 200
    assert request(application, method, "/api/cases/synthetic", headers={"Authorization": AUTH}).status_code == 200


def test_tampered_duplicate_expired_future_and_rotated_sessions_fail(monkeypatch):
    application = app()
    now = 1800000000
    monkeypatch.setattr(access.time, "time", lambda: now)
    session = cookie(application)
    token = session.partition("=")[2]
    for value in (session + "x", session + "; " + session,
                  session + "; " + access.SESSION_COOKIE, access.SESSION_COOKIE + '="' + token + '"'):
        assert request(application, path="/api/cases", headers={"Cookie": value}).status_code == 401
    assert request(application, path="/api/cases", headers=[("Cookie", session), ("Cookie", session)]).status_code == 401
    monkeypatch.setattr(access.time, "time", lambda: now + access.SESSION_TTL_SECONDS)
    assert request(application, path="/api/cases", headers={"Cookie": session}).status_code == 401
    monkeypatch.setattr(access.time, "time", lambda: now - 1)
    assert request(application, path="/api/cases", headers={"Cookie": session}).status_code == 401
    monkeypatch.setattr(access.time, "time", lambda: now)
    assert request(app(PASSWORD + "R"), path="/api/cases", headers={"Cookie": session}).status_code == 401
    assert request(application, path="/api/cases", headers={"Cookie": session, "Host": "other.invalid"}).status_code == 401


@pytest.mark.parametrize("content,content_type,status", [
    ("{}", "application/json", 415), ("x" * 2049, "application/x-www-form-urlencoded", 413),
    ("username=a&username=b", "application/x-www-form-urlencoded", 400),
    ("username=a&password=%ZZ", "application/x-www-form-urlencoded", 400),
    ("username=a&password=b&next=https://evil.invalid", "application/x-www-form-urlencoded", 400),
])
def test_body_type_size_and_duplicate_fields_rejected(content, content_type, status):
    response = request(app(), "POST", "/login", headers={"Origin": ORIGIN, "Content-Type": content_type}, content=content)
    assert response.status_code == status and "set-cookie" not in response.headers
    assert "evil.invalid" not in response.text


def test_chunked_over_limit_and_inconsistent_length_rejected():
    async def run(messages, headers):
        async def receive():
            return messages.pop(0)
        return await access._login_fields({"headers": headers}, receive)

    content_type = [(b"content-type", b"application/x-www-form-urlencoded")]
    result = asyncio.run(run([{"type": "http.request", "body": b"a" * 1500, "more_body": True},
                              {"type": "http.request", "body": b"b" * 800}], content_type))
    assert result == (None, 413)
    result = asyncio.run(run([{"type": "http.request", "body": b"abc"}], content_type + [(b"content-length", b"2")]))
    assert result == (None, 400)
