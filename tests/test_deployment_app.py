"""In-process deployment checks using synthetic exports/stores; no real secrets/API."""
from __future__ import annotations

import asyncio
import base64
import copy
import hashlib
import inspect
import json
import os
from pathlib import Path
import types
from unittest.mock import Mock

import httpx
import pytest
from starlette.responses import JSONResponse

from server import deployment_access as access
from server import deployment_app as deployment


USER = "reviewer-61"
PASSWORD = "T7!pK9@qV2#rM4$sN6%wZ8&cX0"
AUTH = "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()
MEDIA = b"SYNTHETIC-MEDIA-0123456789"


def run_request(app, method="GET", path="/", *, headers=None, **kwargs):
    async def execute():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                    base_url="https://demo.invalid") as client:
            return await client.request(method, path, headers=headers, **kwargs)
    return asyncio.run(execute())


def authenticated(app, method="GET", path="/", *, headers=None, **kwargs):
    return run_request(app, method, path, headers={"Authorization": AUTH, **(headers or {})}, **kwargs)


def physical_symlink(link, target, *, directory=False):
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError as error:
        if getattr(error, "winerror", None) == 1314:
            pytest.skip("Windows symlink privilege unavailable; physical link check not run")
        raise


class EchoAPI:
    def __init__(self):
        self.calls = []

    async def __call__(self, scope, receive, send):
        self.calls.append(dict(scope))
        await JSONResponse({"path": scope["path"], "root_path": scope.get("root_path", ""),
                            "query": scope["query_string"].decode()})(scope, receive, send)


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    from server import handlers, live, runtime_config
    for key in runtime_config.DEMO_ENV_KEYS | {runtime_config.CORS_ENV_KEY}:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(runtime_config, "ENV_FILE", tmp_path / "nonexistent-synthetic.env")
    forbidden = Mock(side_effect=AssertionError("Real live API and local runtime state are forbidden"))
    monkeypatch.setattr(live, "OpenAI", forbidden)
    monkeypatch.setattr(handlers, "get_runtime_storage", forbidden)
    monkeypatch.setattr(handlers, "service", forbidden)
    yield
    forbidden.assert_not_called()


@pytest.fixture
def export_dir(tmp_path):
    root = tmp_path / "out"
    files = {"index.html": b"<!doctype html><title>Synthetic OneFlow</title>",
             "404.html": b"<!doctype html><title>Missing</title>", "index.txt": b"synthetic-next-flight",
             "cases.json": b'{"cases":[]}', "icon.svg": b"<svg/>",
             "_next/static/chunks/app.js": b"console.log('synthetic');",
             "_next/static/css/app.css": b"body { color: black; }",
             "demo/CASE-0001.wav": MEDIA, "demo/CASE-0002.wav": MEDIA, "demo/sorter-demo.mp4": MEDIA}
    for name, content in files.items():
        file = root / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(content)
    return root


@pytest.fixture
def environment(export_dir):
    return {"ONEFLOW_STATIC_DIR": str(export_dir), "ONEFLOW_ACCESS_USER": USER,
            "ONEFLOW_ACCESS_PASSWORD": PASSWORD}


@pytest.fixture
def legacy_media_manifest(export_dir):
    """The three-file test export owns its descriptors; no repository media is read."""
    from server.media_contract import MEDIA_NAMES
    assets = []
    for name in MEDIA_NAMES:
        content = (export_dir / "demo" / name).read_bytes()
        assets.append({"name": name, "bytes": len(content),
                       "sha256": hashlib.sha256(content).hexdigest(), "synthetic": True})
    return {"schemaVersion": 1, "repository": "cjj0202-glitch/happycall-ralphthon",
            "releaseTag": "demo-media-20260921-audio-v3", "assets": assets}


@pytest.fixture
def app(environment, legacy_media_manifest):
    return deployment.create_deployment_app(environ=environment, api_app=EchoAPI(),
                                            media_manifest=legacy_media_manifest)


def test_explicit_legacy_export_does_not_load_packaged_registration(request, monkeypatch):
    forbidden = Mock(side_effect=AssertionError("Explicit test export must not load packaged media"))
    monkeypatch.setattr(deployment, "_packaged_manifest", forbidden)
    application = request.getfixturevalue("app")
    assert authenticated(application, path="/demo/sorter-demo.mp4").content == MEDIA
    assert authenticated(application, path="/demo/sorter-demo.tracks.json").status_code == 404
    forbidden.assert_not_called()


@pytest.mark.parametrize("method,path", [("GET", "/"), ("HEAD", "/"), ("GET", "/cases.json"),
    ("GET", "/_next/static/chunks/app.js"), ("GET", "/demo/CASE-0001.wav"),
    ("HEAD", "/demo/sorter-demo.mp4"), ("GET", "/api/health"), ("GET", "/api"),
    ("GET", "/api/"), ("PATCH", "/api/cases/SYN-TEST"), ("POST", "/api/intake"),
    ("OPTIONS", "/api/cases"), ("GET", "/missing"), ("GET", "/.env"), ("POST", "/healthz")])
def test_every_nonpublic_path_requires_authentication(app, method, path):
    response = run_request(app, method, path, headers={"Range": "bytes=0-3"})
    if method == "GET" and path == "/":
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
    else:
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == access.CHALLENGE
    assert "content-range" not in response.headers
    assert app.app.api.calls == []


@pytest.mark.parametrize("path", ["/healthz", "/healthz?ignored=synthetic-secret"])
def test_public_health_is_constant_and_does_not_call_api(app, path):
    response = run_request(app, path=path, headers={"Authorization": "not even valid"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert app.app.api.calls == []
    head = run_request(app, "HEAD", path)
    assert head.status_code == 200 and head.content == b""
    assert head.headers["content-length"] == str(len(response.content))


@pytest.mark.parametrize("value", ["", "Bearer x", "Basic", "Basic ", "Basic !!!", "Basic !!!===",
    "Basic abc", "Basic YQ==", "Basic dXNlcjpwYXNz trailing", "Basic\tdXNlcjpwYXNz",
    "Basic " + base64.b64encode(b"bad:credentials").decode(), "Basic " + "A" * 4097,
    "Basic " + base64.b64encode(b"\xff:\xff").decode(), AUTH + "=", AUTH + "\n"])
def test_invalid_authentication_is_identical_401(app, value, caplog):
    response = run_request(app, path="/api/cases", headers={"Authorization": value})
    assert response.status_code == 401
    assert response.text == "Unauthorized"
    assert response.headers["www-authenticate"] == access.CHALLENGE
    assert PASSWORD not in response.text + caplog.text
    assert app.app.api.calls == []


@pytest.mark.parametrize("headers", [[("Authorization", AUTH), ("Authorization", AUTH)],
    [("Authorization", AUTH), ("authorization", "Basic invalid")],
    [("Authorization", "Basic invalid"), ("Authorization", AUTH)],
    [("Authorization", AUTH + ", " + AUTH)]])
def test_duplicate_or_combined_authorization_is_rejected(app, headers):
    response = run_request(app, path="/api/cases", headers=headers)
    assert response.status_code == 401
    assert app.app.api.calls == []


def test_basic_scheme_is_case_insensitive_and_two_hashes_always_compared(app, monkeypatch):
    actual = access.hmac.compare_digest
    compare = Mock(wraps=actual)
    monkeypatch.setattr(access.hmac, "compare_digest", compare)
    response = run_request(app, headers={"Authorization": "bAsIc" + AUTH[5:]})
    assert response.status_code == 200
    assert compare.call_count == 2
    assert all(len(arg) == 32 for call in compare.call_args_list for arg in call.args)
    compare.reset_mock()
    bad = "Basic " + base64.b64encode(f"wrong-user:{PASSWORD}".encode()).decode()
    assert run_request(app, headers={"Authorization": bad}).status_code == 401
    assert compare.call_count == 2
    assert PASSWORD not in repr(app.credentials)


@pytest.mark.parametrize("path,mime", [("/", "text/html"), ("/index.html", "text/html"),
    ("/index.txt", "text/plain"), ("/cases.json", "application/json"),
    ("/icon.svg", "image/svg+xml"), ("/_next/static/chunks/app.js", "text/javascript"),
    ("/_next/static/css/app.css", "text/css"), ("/demo/CASE-0001.wav", "audio/wav"),
    ("/demo/sorter-demo.mp4", "video/mp4")])
def test_authenticated_export_has_expected_mime_and_security_headers(app, path, mime):
    response = authenticated(app, path=path)
    assert response.status_code == 200
    assert response.headers["content-type"].split(";")[0] == mime
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.content


@pytest.mark.parametrize("path", ["/demo/CASE-0001.wav", "/demo/sorter-demo.mp4"])
def test_media_get_head_and_range(app, path):
    full = authenticated(app, path=path)
    assert full.content == MEDIA
    assert full.headers["accept-ranges"] == "bytes"
    head = authenticated(app, "HEAD", path)
    assert head.status_code == 200 and head.content == b""
    assert head.headers["content-length"] == str(len(MEDIA))
    partial = authenticated(app, path=path, headers={"Range": "bytes=2-7"})
    assert partial.status_code == 206
    assert partial.content == MEDIA[2:8]
    assert partial.headers["content-range"] == f"bytes 2-7/{len(MEDIA)}"
    suffix = authenticated(app, path=path, headers={"Range": "bytes=-4"})
    assert suffix.status_code == 206 and suffix.content == MEDIA[-4:]
    head_range = authenticated(app, "HEAD", path, headers={"Range": "bytes=2-7"})
    assert head_range.status_code == 206 and head_range.content == b""
    assert head_range.headers["content-length"] == "6"
    outside = authenticated(app, path=path, headers={"Range": "bytes=999-"})
    assert outside.status_code == 416
    assert outside.headers["content-range"] == f"bytes */{len(MEDIA)}"
    if_range = authenticated(app, path=path, headers={"Range": "bytes=2-7", "If-Range": '"stale"'})
    assert if_range.status_code == 200 and if_range.content == MEDIA


@pytest.mark.parametrize("path", ["/api", "/api/", "/api/cases?selected=SYN-TEST", "/api/unknown"])
def test_api_receives_original_path_query_and_origin(app, path):
    response = authenticated(app, path=path)
    assert response.status_code == 200
    assert response.json()["path"] == path.split("?")[0]
    assert response.json()["root_path"] == ""
    assert response.json()["query"] == (path.split("?", 1)[1] if "?" in path else "")
    assert app.app.api.calls[-1]["scheme"] == "https"
    assert not any(key.lower() == b"authorization" for key, value in app.app.api.calls[-1]["headers"])
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize("path", ["/missing", "/missing.js", "/demo/missing.wav", "/apiary",
    "/healthz/", "/.env", "/server/deployment_app.py", "/secret.json", "/README.md",
    "/_next/static/chunks/secret.js.map", "/demo/private.json"])
def test_unknown_static_and_secret_files_are_404_not_html(app, export_dir, path):
    if path not in {"/missing", "/healthz/"}:
        candidate = export_dir / path.lstrip("/")
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text("synthetic-private-value", encoding="utf-8")
    response = authenticated(app, path=path)
    # Missing allowed assets deliberately remain missing, all other planted files are denied.
    if path in {"/missing.js", "/demo/missing.wav"}:
        (export_dir / path.lstrip("/")).unlink()
        response = authenticated(app, path=path)
    assert response.status_code == 404
    assert b"synthetic-private-value" not in response.content
    assert b"<!doctype" not in response.content


@pytest.mark.parametrize("path", ["/%2e%2e/secret.json", "/demo/%2e%2e/index.html",
    "/demo/%252e%252e/index.html", "/demo%5c..%5cindex.html", "/demo//CASE-0001.wav",
    "/demo/CASE-0001.wav%00", "/demo/CASE-0001.wav:secret", "/demo/CASE-0001.wav.",
    "/demo/CASE-0001.wav%20", "/_next/static/.private.js", "/%00"])
def test_traversal_and_ambiguous_paths_are_denied(app, path):
    response = authenticated(app, path=path)
    assert response.status_code == 404
    assert response.content == b""


def test_symlink_files_and_directories_are_not_served(app, export_dir, tmp_path):
    outside = tmp_path / "private.wav"
    outside.write_text("synthetic-private-value", encoding="utf-8")
    physical_symlink(export_dir / "demo/linked.wav", outside)
    physical_symlink(export_dir / "demo/linked-dir", tmp_path, directory=True)
    for path in ("/demo/linked.wav", "/demo/linked-dir/private.wav"):
        response = authenticated(app, path=path)
        assert response.status_code == 404
        assert b"synthetic-private-value" not in response.content


def test_replaced_required_file_symlink_is_blocked_after_start(app, export_dir, tmp_path):
    secret = tmp_path / "private.html"
    secret.write_text("synthetic-private-value", encoding="utf-8")
    target = export_dir / "index.html"
    target.unlink()
    physical_symlink(target, secret)
    assert authenticated(app).status_code == 404


@pytest.mark.parametrize("key,value", [("ONEFLOW_ACCESS_USER", ""), ("ONEFLOW_ACCESS_USER", "abc"),
    ("ONEFLOW_ACCESS_USER", "admin"), ("ONEFLOW_ACCESS_USER", "demo"),
    ("ONEFLOW_ACCESS_USER", "person:name"), ("ONEFLOW_ACCESS_USER", "x" * 65),
    ("ONEFLOW_ACCESS_USER", "user with spaces"), ("ONEFLOW_ACCESS_USER", "사용자이름"),
    ("ONEFLOW_ACCESS_PASSWORD", ""), ("ONEFLOW_ACCESS_PASSWORD", "short-synthetic-value"),
    ("ONEFLOW_ACCESS_PASSWORD", "x" * 32), ("ONEFLOW_ACCESS_PASSWORD", "x" * 257),
    ("ONEFLOW_ACCESS_PASSWORD", "replace-with-a-secure-password-123456789!"),
    ("ONEFLOW_ACCESS_PASSWORD", "ChangeMe-1234567890-Secret!"),
    ("ONEFLOW_ACCESS_PASSWORD", PASSWORD + "\n")])
def test_invalid_access_configuration_fails_without_echo(environment, legacy_media_manifest, key, value):
    with pytest.raises(ValueError) as caught:
        deployment.create_deployment_app(environ={**environment, key: value}, api_app=EchoAPI(),
                                         media_manifest=legacy_media_manifest)
    assert str(caught.value) == access.ACCESS_ERROR
    assert PASSWORD not in str(caught.value)


@pytest.mark.parametrize("key", ["ONEFLOW_STATIC_DIR", "ONEFLOW_ACCESS_USER", "ONEFLOW_ACCESS_PASSWORD"])
def test_missing_environment_is_not_recovered_from_local_file(environment, legacy_media_manifest, key):
    environment.pop(key)
    with pytest.raises(ValueError):
        deployment.create_deployment_app(environ=environment, api_app=EchoAPI(),
                                         media_manifest=legacy_media_manifest)


@pytest.mark.parametrize("value", ["", "apps/web/out", "../out", "missing-synthetic-export", "\x00"])
def test_invalid_static_configuration_fails_without_echo(environment, legacy_media_manifest, value):
    with pytest.raises(ValueError) as caught:
        deployment.create_deployment_app(environ={**environment, "ONEFLOW_STATIC_DIR": value}, api_app=EchoAPI(),
                                         media_manifest=legacy_media_manifest)
    assert str(caught.value) == deployment.STATIC_ERROR


@pytest.mark.parametrize("relative", [*deployment.REQUIRED_FILES, "_next/static/chunks/app.js",
                                    "_next/static/css/app.css"])
def test_missing_export_component_prevents_startup(environment, export_dir, legacy_media_manifest, relative):
    (export_dir / relative).unlink()
    with pytest.raises(ValueError, match="ONEFLOW_STATIC_DIR"):
        deployment.create_deployment_app(environ=environment, api_app=EchoAPI(),
                                         media_manifest=legacy_media_manifest)


def test_empty_export_component_and_symlink_root_prevent_startup(environment, export_dir, legacy_media_manifest, tmp_path):
    (export_dir / "index.html").write_bytes(b"")
    with pytest.raises(ValueError, match="ONEFLOW_STATIC_DIR"):
        deployment.create_deployment_app(environ=environment, api_app=EchoAPI(),
                                         media_manifest=legacy_media_manifest)
    (export_dir / "index.html").write_bytes(b"<html/>")
    root_link = tmp_path / "linked-export"
    physical_symlink(root_link, export_dir, directory=True)
    with pytest.raises(ValueError, match="ONEFLOW_STATIC_DIR"):
        deployment.create_deployment_app(environ={**environment, "ONEFLOW_STATIC_DIR": str(root_link)}, api_app=EchoAPI(),
                                         media_manifest=legacy_media_manifest)


def test_static_mutation_methods_are_not_allowed(app):
    response = authenticated(app, "POST", "/index.html", content="do not change")
    assert response.status_code == 405
    assert response.headers["allow"] == "GET, HEAD"
    assert authenticated(app, "POST", "/healthz").status_code == 405


@pytest.mark.parametrize("kind", ["is_symlink", "is_junction"])
@pytest.mark.parametrize("relative", ["index.html", "demo", ""])
def test_synthetic_link_detection_denies_file_directory_and_root(app, export_dir, monkeypatch, kind, relative):
    """Exercise both link detectors without requiring OS link creation privilege."""
    original = getattr(Path, kind)
    marked_link = export_dir / relative
    monkeypatch.setattr(Path, kind, lambda path: path == marked_link or original(path))
    path = "/demo/CASE-0001.wav" if relative == "demo" else "/"
    assert authenticated(app, path=path).status_code == 404


@pytest.mark.parametrize("kind", ["is_symlink", "is_junction"])
def test_synthetic_link_export_fails_startup(environment, export_dir, legacy_media_manifest, monkeypatch, kind):
    original = getattr(Path, kind)
    monkeypatch.setattr(Path, kind, lambda path: path == export_dir or original(path))
    with pytest.raises(ValueError, match="ONEFLOW_STATIC_DIR"):
        deployment.create_deployment_app(environ=environment, api_app=EchoAPI(),
                                         media_manifest=legacy_media_manifest)


def test_websockets_are_always_closed(app):
    sent = []
    async def send(message):
        sent.append(message)
    asyncio.run(app({"type": "websocket", "path": "/api", "headers": []}, None, send))
    assert sent == [{"type": "websocket.close", "code": 1008}]
    assert app.app.api.calls == []


@pytest.fixture
def real_api_app(environment, legacy_media_manifest, tmp_path, monkeypatch):
    from server import handlers
    from server.repository import JsonCaseRepository
    from server.service import CaseService
    root = Path(__file__).resolve().parents[1]
    fixture = tmp_path / "synthetic-fixtures.json"
    fixture.write_bytes((root / "data/fixtures/cases.json").read_bytes())
    analyzer = Mock()
    analyzer.analyze.side_effect = AssertionError("No model calls")
    service = CaseService(JsonCaseRepository(tmp_path / "synthetic-store.json", fixture), analyzer=analyzer)
    monkeypatch.setattr(handlers, "service", lambda: service)
    async def health():
        return {"status": "synthetic", "budget": {"marker": "private-synthetic-budget"}}
    monkeypatch.setattr(handlers, "health", health)
    yield deployment.create_deployment_app(environ=environment, media_manifest=legacy_media_manifest), service
    analyzer.analyze.assert_not_called()


def test_real_connexion_api_and_health_are_protected_and_keep_contract(real_api_app):
    app, service = real_api_app
    denied = run_request(app, path="/api/health")
    assert denied.status_code == 401 and "private-synthetic-budget" not in denied.text
    health = authenticated(app, path="/api/health")
    assert health.status_code == 200 and health.json()["budget"]["marker"] == "private-synthetic-budget"
    listed = authenticated(app, path="/api/cases")
    assert listed.status_code == 200 and len(listed.json()["cases"]) == 2
    for path in ("/api", "/api/", "/api/unknown", "/api/cases/UNKNOWN"):
        missing = authenticated(app, path=path)
        assert missing.status_code == 404
        assert "html" not in missing.headers.get("content-type", "")
    wrong_method = authenticated(app, "DELETE", "/api/cases")
    assert wrong_method.status_code == 405


def test_real_api_role_and_revision_denials_survive_outer_basic_auth(real_api_app):
    app, service = real_api_app
    case = service.list()["cases"][0]
    path = "/api/cases/" + case["id"]
    missing_revision = authenticated(app, "PATCH", path, json={"departmentId": "delivery"})
    assert missing_revision.status_code == 428
    denied = authenticated(app, "PATCH", path, headers={"X-Demo-Role": "owner"},
                           json={"expectedRevision": 0, "reviewConfirmed": True})
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "READ_ONLY_ROLE"
    blocked = authenticated(app, "PATCH", path, headers={"X-Demo-Role": "counselor"},
                            json={"expectedRevision": 0, "status": "closed"})
    assert blocked.status_code == 409
    assert service.get(case["id"])["revision"] == 0
    allowed = authenticated(app, "PATCH", path, headers={"X-Demo-Role": "counselor"},
                            json={"expectedRevision": 0, "departmentId": "delivery"})
    assert allowed.status_code == 200 and allowed.json()["revision"] == 1
    handoff = authenticated(app, "PATCH", path, headers={"X-Demo-Role": "counselor"},
                            json={"expectedRevision": 1, "reviewConfirmed": True, "status": "handed_off"})
    assert handoff.status_code == 200
    close = authenticated(app, "PATCH", path, headers={"X-Demo-Role": "counselor"},
                          json={"expectedRevision": 2, "status": "closed"})
    assert close.status_code == 403 and close.json()["error"]["code"] == "CENTER_ROLE_REQUIRED"


def test_guard_mutations_are_killed_with_unchanged_control(environment, export_dir, legacy_media_manifest):
    """Execute memory-only mutants; never rewrite repository source during verification."""
    access_source = Path(access.__file__).read_text(encoding="utf-8")
    app_source = Path(deployment.__file__).read_text(encoding="utf-8")

    def load_copy(module, source):
        # Keep the original name for dataclass type introspection; this object is not installed.
        copied = types.ModuleType(module.__name__)
        copied.__file__ = module.__file__
        exec(compile(source, "<synthetic-deployment-mutant>", "exec"), copied.__dict__)
        return copied

    def protected(module):
        app = module.DeploymentAccess(EchoAPI(), access.AccessCredentials.from_environment(environment))
        assert run_request(app, path="/api/cases").status_code == 401

    def allowed(module):
        app = module.DeploymentAccess(EchoAPI(), access.AccessCredentials.from_environment(environment))
        assert authenticated(app, path="/api/cases").status_code == 200

    def original_path(module):
        app = module.create_deployment_app(environ=environment, api_app=EchoAPI(),
                                           media_manifest=legacy_media_manifest)
        assert authenticated(app, path="/api/cases").json()["path"] == "/api/cases"

    def secret_denied(module):
        (export_dir / "private.json").write_text('{"syntheticSecret":"never-serve"}', encoding="utf-8")
        app = module.create_deployment_app(environ=environment, api_app=EchoAPI(),
                                           media_manifest=legacy_media_manifest)
        assert authenticated(app, path="/private.json").status_code == 404

    mutations = [
        (access, access_source, "if not basic and not session:", "if False:", protected),
        (access, access_source, "if not basic and not session:", "if True:", allowed),
        (deployment, app_source, "await self.api(scope, receive, send)\n            return\n        if path",
         "await self.api({**scope, 'path': path.removeprefix('/api')}, receive, send)\n            return\n        if path", original_path),
        (deployment, app_source, "if relative in ROOT_FILES:", "if relative in ROOT_FILES or relative.endswith('.json'):", secret_denied),
    ]
    killed = 0
    for module, source, before, after, check in mutations:
        check(load_copy(module, source))
        assert source.count(before) == 1
        with pytest.raises(AssertionError):
            check(load_copy(module, source.replace(before, after)))
        killed += 1
    assert killed == 4


@pytest.fixture
def tracks_registration(export_dir, legacy_media_manifest):
    """Registered sidecar coverage stays separate from the legacy three-file fixture."""
    from server.media_contract import TRACKS_NAME, TRACKS_URL
    tracks = b'{"syntheticM4Fixture":"opaque-sidecar"}'
    (export_dir / "demo" / TRACKS_NAME).write_bytes(tracks)
    digest = hashlib.sha256(MEDIA).hexdigest()
    manifest = copy.deepcopy(legacy_media_manifest)
    manifest["assets"][-1]["tracks"] = {"schemaVersion": "oneflow-cctv-tracks-v1", "url": TRACKS_URL,
        "bytes": len(tracks), "sha256": hashlib.sha256(tracks).hexdigest(), "videoSha256": digest}
    return manifest, tracks


def test_tracks_absent_registration_denies_even_if_cases_advertise_it(export_dir):
    (export_dir / "demo/sorter-demo.tracks.json").write_bytes(b'{"synthetic":true}')
    (export_dir / "cases.json").write_bytes(b'{"tracks":{"url":"/demo/sorter-demo.tracks.json"}}')
    router = deployment.DeploymentRouter(EchoAPI(), export_dir)
    assert run_request(router, path="/demo/sorter-demo.tracks.json").status_code == 404


def test_registered_tracks_get_head_auth_and_exact_allowlist(environment, export_dir, tracks_registration):
    manifest, tracks = tracks_registration
    app = deployment.create_deployment_app(environ=environment, api_app=EchoAPI(), media_manifest=manifest)
    assert run_request(app, path="/demo/sorter-demo.tracks.json").status_code == 401
    got = authenticated(app, path="/demo/sorter-demo.tracks.json")
    assert got.status_code == 200 and got.content == tracks
    assert got.headers["content-type"] == "application/json"
    assert got.headers["cache-control"] == "private, no-store"
    head = authenticated(app, "HEAD", "/demo/sorter-demo.tracks.json")
    assert head.status_code == 200 and head.content == b""
    assert head.headers["content-length"] == str(len(tracks))
    (export_dir / "demo/private.json").write_bytes(tracks)
    assert authenticated(app, path="/demo/private.json").status_code == 404


@pytest.mark.parametrize("name", ["sorter-demo.mp4", "sorter-demo.tracks.json"])
@pytest.mark.parametrize("change", ["missing", "same-size-mismatch"])
def test_registered_pair_is_verified_at_start_and_each_request(export_dir, tracks_registration, name, change):
    manifest, _ = tracks_registration
    app = deployment.DeploymentRouter(EchoAPI(), export_dir, media_manifest=manifest)
    target = export_dir / "demo" / name
    if change == "missing":
        target.unlink()
    else:
        target.write_bytes(b"!" * target.stat().st_size)
    with pytest.raises(ValueError, match="integrity"):
        deployment.DeploymentRouter(EchoAPI(), export_dir, media_manifest=manifest)
    for path in ("/demo/sorter-demo.mp4", "/demo/sorter-demo.tracks.json"):
        result = run_request(app, path=path)
        assert result.status_code == 404 and result.content == b""


@pytest.mark.parametrize("key,value", [("url", "/demo/private.json"), ("bytes", True),
    ("bytes", 0), ("bytes", 10_000_001), ("sha256", "A" * 64),
    ("videoSha256", "0" * 64), ("schemaVersion", "other"), ("unexpected", True)])
def test_injected_tracks_descriptor_is_never_exempt(export_dir, tracks_registration, key, value):
    manifest, _ = tracks_registration
    invalid = copy.deepcopy(manifest)
    invalid["assets"][-1]["tracks"][key] = value
    with pytest.raises(ValueError, match="integrity"):
        deployment.DeploymentRouter(EchoAPI(), export_dir, media_manifest=invalid)


@pytest.mark.parametrize("tag", ["demo-media-20260921-audio-v3", "demo-media-20260922-v4"])
def test_packaged_manifest_is_known_path_and_uses_same_validator(environment, export_dir, tmp_path, monkeypatch, tracks_registration, tag):
    manifest, tracks = tracks_registration
    manifest["releaseTag"] = tag
    package = tmp_path / "synthetic-package"
    (package / "data").mkdir(parents=True)
    monkeypatch.setattr(deployment, "PACKAGE_ROOT", package)
    absent = deployment.create_deployment_app(environ=environment, api_app=EchoAPI())
    assert authenticated(absent, path="/demo/sorter-demo.tracks.json").status_code == 404
    path = package / "data/demo-media-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    registered = deployment.create_deployment_app(environ=environment, api_app=EchoAPI())
    assert authenticated(registered, path="/demo/sorter-demo.tracks.json").content == tracks
    video = export_dir / "demo/sorter-demo.mp4"
    video.write_bytes(b"!" * len(MEDIA))
    with pytest.raises(ValueError, match="integrity"):
        deployment.create_deployment_app(environ=environment, api_app=EchoAPI())
    video.write_bytes(MEDIA)
    manifest["assets"][-1]["tracks"]["bytes"] = True
    path.write_text(json.dumps(manifest), encoding="utf-8")
    for args in ({}, {"media_manifest": manifest}):
        with pytest.raises(ValueError, match="integrity"):
            deployment.create_deployment_app(environ=environment, api_app=EchoAPI(), **args)


@pytest.mark.parametrize("name", ["sorter-demo.mp4", "sorter-demo.tracks.json"])
def test_registered_hardlinks_are_denied(export_dir, tmp_path, tracks_registration, name):
    manifest, _ = tracks_registration
    app = deployment.DeploymentRouter(EchoAPI(), export_dir, media_manifest=manifest)
    os.link(export_dir / "demo" / name, tmp_path / ("linked-" + name))
    assert run_request(app, path="/demo/sorter-demo.tracks.json").status_code == 404
    with pytest.raises(ValueError, match="integrity"):
        deployment.DeploymentRouter(EchoAPI(), export_dir, media_manifest=manifest)


def test_verified_tracks_response_does_not_reopen_changed_path(export_dir, tracks_registration, monkeypatch):
    manifest, tracks = tracks_registration
    app = deployment.DeploymentRouter(EchoAPI(), export_dir, media_manifest=manifest)
    original = deployment._snapshot_response
    def change_after_validation(content, scope, media_type, **kwargs):
        (export_dir / "demo/sorter-demo.tracks.json").write_bytes(b"UNAPPROVED-SYNTHETIC-BYTES")
        return original(content, scope, media_type, **kwargs)
    monkeypatch.setattr(deployment, "_snapshot_response", change_after_validation)
    assert run_request(app, path="/demo/sorter-demo.tracks.json").content == tracks
    assert run_request(app, path="/demo/sorter-demo.tracks.json").status_code == 404


@pytest.mark.parametrize("tag", ["demo-media-20260921-audio-v2", "unregistered-release"])
def test_tracks_release_is_not_exempt_from_offline_validation(export_dir, tracks_registration, tag):
    manifest, _ = tracks_registration
    manifest["releaseTag"] = tag
    with pytest.raises(ValueError, match="integrity"):
        deployment.DeploymentRouter(EchoAPI(), export_dir, media_manifest=manifest)


@pytest.fixture
def snapshot_observations(tmp_path):
    """Stable file identity; Windows path/handle ctime providers may differ."""
    target = tmp_path / "synthetic-snapshot.bin"
    target.write_bytes(MEDIA)
    common = dict(st_mode=target.stat().st_mode, st_dev=11, st_ino=17,
                  st_size=len(MEDIA), st_mtime_ns=300, st_nlink=1, st_birthtime_ns=100)
    observations = {name: types.SimpleNamespace(**common, st_ctime_ns=ctime)
                    for name, ctime in zip(("before", "opened", "after", "now"),
                                           (100, 200, 200, 100))}
    return target, observations


def read_observed_snapshot(monkeypatch, target, observations, reader=None):
    """Patch metadata only; the real file is opened/read within the snapshot helper."""
    with monkeypatch.context() as patched:
        path_stat = Mock(side_effect=[observations["before"], observations["now"]])
        handle_stat = Mock(side_effect=[observations["opened"], observations["after"]])
        patched.setattr(deployment, "_regular_file", Mock(return_value=target))
        patched.setattr(type(target), "stat", path_stat)
        patched.setattr(deployment.os, "fstat", handle_stat)
        result = (reader or deployment._read_regular_snapshot)(target.parent, target.name, len(MEDIA))
        assert path_stat.call_count == handle_stat.call_count == 2
        return result


@pytest.mark.parametrize("profile", ["windows", "same-provider", "unix-no-birthtime"])
def test_snapshot_accepts_stable_metadata_from_each_provider(snapshot_observations, monkeypatch, profile):
    target, observations = snapshot_observations
    if profile != "windows":
        for value in observations.values():
            value.st_ctime_ns = 100
            if profile == "unix-no-birthtime":
                del value.st_birthtime_ns
    result = read_observed_snapshot(monkeypatch, target, observations)
    assert result is not None and result[0] == MEDIA
    assert result[1] is observations["after"]


@pytest.mark.parametrize("profile", ["windows", "unix-no-birthtime"])
@pytest.mark.parametrize("changed", ["now", "after"])
def test_snapshot_rejects_ctime_change_within_each_provider(snapshot_observations, monkeypatch, profile, changed):
    target, observations = snapshot_observations
    if profile == "unix-no-birthtime":
        for value in observations.values():
            value.st_ctime_ns = 100
            del value.st_birthtime_ns
    observations[changed].st_ctime_ns += 1
    assert read_observed_snapshot(monkeypatch, target, observations) is None


@pytest.mark.parametrize("field", ["st_dev", "st_ino", "st_size", "st_mtime_ns", "st_nlink", "st_birthtime_ns"])
def test_snapshot_rejects_changed_common_signature(snapshot_observations, monkeypatch, field):
    target, observations = snapshot_observations
    setattr(observations["after"], field, getattr(observations["after"], field) + 1)
    assert read_observed_snapshot(monkeypatch, target, observations) is None


def test_snapshot_rejects_birthtime_availability_change(snapshot_observations, monkeypatch):
    target, observations = snapshot_observations
    del observations["after"].st_birthtime_ns
    assert read_observed_snapshot(monkeypatch, target, observations) is None


@pytest.mark.parametrize("changed,guard", [
    ("now", "before.st_ctime_ns != now.st_ctime_ns"),
    ("after", "opened.st_ctime_ns != after.st_ctime_ns"),
])
def test_snapshot_ctime_guard_mutations_are_killed(snapshot_observations, monkeypatch, changed, guard):
    target, observations = snapshot_observations
    # A normal snapshot must reach the actual byte read before testing rejection.
    assert read_observed_snapshot(monkeypatch, target, observations)[0] == MEDIA
    observations[changed].st_ctime_ns += 1
    assert read_observed_snapshot(monkeypatch, target, observations) is None

    source = inspect.getsource(deployment._read_regular_snapshot)
    assert source.count(guard) == 1
    namespace = {**deployment.__dict__, "_regular_file": lambda root, relative: target}
    exec(compile(source.replace(guard, "False"), "<synthetic-ctime-mutant>", "exec"), namespace)
    reader = namespace["_read_regular_snapshot"]
    with pytest.raises(AssertionError):
        assert read_observed_snapshot(monkeypatch, target, observations, reader) is None
