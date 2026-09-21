"""Standalone unittest/ASGITransport checks; no sockets, pytest, installs or live API.

Run from the repository with its existing Connexion/Starlette/httpx dependencies.
All written files are temporary synthetic exports. Stdout/stderr is the report.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import httpx
from starlette.responses import JSONResponse
from server import deployment_app as deployment
from server.media_contract import MEDIA_NAMES, TRACKS_NAME, TRACKS_URL

VIDEO = b"SYNTHETIC-M4-VIDEO-0123456789"
TRACKS = b'{"syntheticM4Fixture":"opaque-body-not-a-new-schema"}'
USER = "synthetic-m4-reviewer"
PASSWORD = "Synthetic-M4-Only_73!Fixture-Value"
AUTH = "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()


class Echo:
    async def __call__(self, scope, receive, send):
        await JSONResponse({"path": scope["path"]})(scope, receive, send)


def manifest():
    assets = [{"name": name, "bytes": len(VIDEO), "sha256": hashlib.sha256(VIDEO).hexdigest(),
               "synthetic": True} for name in MEDIA_NAMES]
    assets[-1]["tracks"] = {"schemaVersion": "oneflow-cctv-tracks-v1", "url": TRACKS_URL,
        "bytes": len(TRACKS), "sha256": hashlib.sha256(TRACKS).hexdigest(),
        "videoSha256": assets[-1]["sha256"]}
    return {"schemaVersion": 1, "repository": "cjj0202-glitch/happycall-ralphthon",
            "releaseTag": "demo-media-20260921-audio-v3", "assets": assets}


def request(app, path=TRACKS_URL, method="GET", headers=None):
    async def execute():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://synthetic.invalid") as client:
            return await client.request(method, path, headers=headers)
    return asyncio.run(execute())


class MediaM4(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="oneflow-m4-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "out"
        files = {name: b"synthetic" for name in deployment.REQUIRED_FILES}
        files.update({"_next/static/chunks/test.js": b"// synthetic", "_next/static/css/test.css": b"body{}",
                      "demo/" + TRACKS_NAME: TRACKS})
        files.update({"demo/" + name: VIDEO for name in MEDIA_NAMES})
        for name, content in files.items():
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        self.environment = {"ONEFLOW_STATIC_DIR": str(self.root), "ONEFLOW_ACCESS_USER": USER,
                            "ONEFLOW_ACCESS_PASSWORD": PASSWORD}
        self.package = self.base / "package"
        (self.package / "data").mkdir(parents=True)

    def router(self, value=None):
        return deployment.DeploymentRouter(Echo(), self.root, media_manifest=value)

    def factory(self, value):
        return deployment.create_deployment_app(environ=self.environment, api_app=Echo(), media_manifest=value)

    def test_01_legacy_router_denies_all_demo_json(self):
        app = self.router()
        (self.root / "demo/private.json").write_bytes(TRACKS)
        for path in (TRACKS_URL, "/demo/private.json"):
            with self.subTest(path=path):
                self.assertEqual(request(app, path).status_code, 404)
        self.assertEqual(request(app, "/demo/sorter-demo.mp4").content, VIDEO)

    def test_02_registered_get_head(self):
        app = self.router(manifest())
        got = request(app)
        self.assertEqual((got.status_code, got.content), (200, TRACKS))
        self.assertEqual(got.headers["content-type"], "application/json")
        head = request(app, method="HEAD")
        self.assertEqual((head.status_code, head.content), (200, b""))
        self.assertEqual(head.headers["content-length"], str(len(TRACKS)))
        self.assertEqual(request(app, headers={"Range": "bytes=2-7"}).content, TRACKS)

    def test_03_only_registered_exact_json_path(self):
        app = self.router(manifest())
        for name in ("private.json", "sorter-demo.json", "sorter-demo.tracks.json.backup"):
            (self.root / "demo" / name).write_bytes(TRACKS)
            with self.subTest(name=name):
                self.assertEqual(request(app, "/demo/" + name).status_code, 404)

    def test_04_media_get_head_range_unchanged(self):
        for registered in (None, manifest()):
            app = self.router(registered)
            for name in MEDIA_NAMES:
                with self.subTest(registered=registered is not None, name=name):
                    path = "/demo/" + name
                    self.assertEqual(request(app, path).content, VIDEO)
                    got = request(app, path, headers={"Range": "bytes=2-7"})
                    self.assertEqual((got.status_code, got.content), (206, VIDEO[2:8]))
                    head = request(app, path, "HEAD", {"Range": "bytes=2-7"})
                    self.assertEqual((head.status_code, head.content, head.headers["content-length"]), (206, b"", "6"))

    def test_05_ranges_and_if_range(self):
        app = self.router(manifest())
        path = "/demo/sorter-demo.mp4"
        for value, code, body in [("bytes=-4", 206, VIDEO[-4:]), ("bytes=999-", 416, b""),
                                  ("bytes=2-", 206, VIDEO[2:]),
                                  ("bytes=bad", 400, b""), ("bytes=-0", 416, b"")]:
            with self.subTest(value=value):
                got = request(app, path, headers={"Range": value})
                self.assertEqual((got.status_code, got.content), (code, body))
        full = request(app, path, headers={"Range": "bytes=2-7", "If-Range": '"stale"'})
        self.assertEqual((full.status_code, full.content), (200, VIDEO))
        dated = request(app, path, headers={"Range": "bytes=2-7", "If-Range": full.headers["last-modified"]})
        self.assertEqual((dated.status_code, dated.content), (206, VIDEO[2:8]))
        multiple = request(app, path, headers={"Range": "bytes=0-1,4-5"})
        self.assertEqual((multiple.status_code, multiple.content), (200, VIDEO))

    def test_06_absent_package_denies_sidecar(self):
        with patch.object(deployment, "PACKAGE_ROOT", self.package):
            app = deployment.create_deployment_app(environ=self.environment, api_app=Echo())
        self.assertEqual(request(app, headers={"Authorization": AUTH}).status_code, 404)

    def test_07_canonical_package_registers_and_cases_are_ignored(self):
        (self.package / "data/demo-media-manifest.json").write_text(json.dumps(manifest()), encoding="utf-8")
        (self.root / "cases.json").write_text('{"tracks":{"url":"/demo/private.json"}}', encoding="utf-8")
        with patch.object(deployment, "PACKAGE_ROOT", self.package):
            app = deployment.create_deployment_app(environ=self.environment, api_app=Echo())
        self.assertEqual(request(app, headers={"Authorization": AUTH}).content, TRACKS)
        self.assertEqual(request(app, "/demo/private.json", headers={"Authorization": AUTH}).status_code, 404)

    def test_08_package_and_injected_manifest_validate_identically(self):
        invalid = manifest()
        invalid["assets"][-1]["tracks"]["bytes"] = True
        (self.package / "data/demo-media-manifest.json").write_text(json.dumps(invalid), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.factory(invalid)
        with patch.object(deployment, "PACKAGE_ROOT", self.package), self.assertRaises(ValueError):
            deployment.create_deployment_app(environ=self.environment, api_app=Echo())

    def test_09_invalid_descriptor_fails_initialization(self):
        changes = {"url": "/demo/private.json", "schemaVersion": "wrong", "bytes": 10_000_001,
                   "sha256": "A" * 64, "videoSha256": "0" * 64, "unexpected": True}
        for key, value in changes.items():
            invalid = manifest()
            invalid["assets"][-1]["tracks"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.router(invalid)

    def test_10_missing_registered_files_fail_initialization(self):
        for name, body in ((TRACKS_NAME, TRACKS), ("sorter-demo.mp4", VIDEO)):
            target = self.root / "demo" / name
            target.unlink()
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.router(manifest())
            target.write_bytes(body)

    def test_11_mismatched_files_fail_initialization(self):
        for name, body in ((TRACKS_NAME, TRACKS), ("sorter-demo.mp4", VIDEO)):
            target = self.root / "demo" / name
            target.write_bytes(b"!" * len(body))
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.router(manifest())
            target.write_bytes(body)

    def test_12_mutation_after_start_denies_parent_and_sidecar(self):
        app = self.router(manifest())
        for name, body in ((TRACKS_NAME, TRACKS), ("sorter-demo.mp4", VIDEO)):
            target = self.root / "demo" / name
            target.write_bytes(b"!" * len(body))
            for path in (TRACKS_URL, "/demo/sorter-demo.mp4"):
                with self.subTest(name=name, path=path):
                    self.assertEqual(request(app, path).status_code, 404)
            target.write_bytes(body)

    def test_13_missing_after_start_denies(self):
        app = self.router(manifest())
        (self.root / "demo" / TRACKS_NAME).unlink()
        self.assertEqual(request(app).status_code, 404)

    def test_14_hardlink_fails_initialization(self):
        os.link(self.root / "demo" / TRACKS_NAME, self.base / "linked-tracks.json")
        with self.assertRaises(ValueError):
            self.router(manifest())

    def test_15_hardlink_after_start_denies(self):
        app = self.router(manifest())
        os.link(self.root / "demo/sorter-demo.mp4", self.base / "linked-video.mp4")
        self.assertEqual(request(app).status_code, 404)

    def test_16_link_components_block_init_and_request(self):
        app = self.router(manifest())
        original = deployment._is_link
        for marked in (self.root, self.root / "demo", self.root / "demo" / TRACKS_NAME):
            with self.subTest(marked=marked.name), patch.object(deployment, "_is_link", lambda p: p == marked or original(p)):
                self.assertEqual(request(app).status_code, 404)
                with self.assertRaises(ValueError):
                    self.router(manifest())

    def test_17_immutable_response_prevents_path_reopen_race(self):
        app = self.router(manifest())
        original = deployment._snapshot_response
        def replace_after_validation(content, scope, media_type, **kwargs):
            (self.root / "demo" / TRACKS_NAME).write_bytes(b"SYNTHETIC-UNAPPROVED-CONTENT")
            return original(content, scope, media_type, **kwargs)
        with patch.object(deployment, "_snapshot_response", replace_after_validation):
            got = request(app)
        self.assertEqual((got.status_code, got.content), (200, TRACKS))
        self.assertEqual(request(app).status_code, 404)

    def test_18_open_swap_rejects_unapproved_file(self):
        app = self.router(manifest())
        original = os.open
        target = self.root / "demo" / TRACKS_NAME
        outside = self.base / "private.json"
        outside.write_bytes(b"SYNTHETIC-PRIVATE-DO-NOT-SERVE")
        def replaced_open(path, flags, *args, **kwargs):
            return original(outside if Path(path) == target else path, flags, *args, **kwargs)
        with patch.object(os, "open", replaced_open):
            got = request(app)
        self.assertEqual((got.status_code, got.content), (404, b""))

    def test_19_injected_manifest_mutation_does_not_reauthorize(self):
        value = manifest()
        app = self.router(value)
        value["assets"][-1]["tracks"]["sha256"] = "0" * 64
        self.assertEqual(request(app).content, TRACKS)

    def test_20_package_manifest_hardlink_and_malformed_fail(self):
        target = self.package / "data/demo-media-manifest.json"
        for body in (b"not-json", b"null", b"[]"):
            target.write_bytes(body)
            with self.subTest(body=body), patch.object(deployment, "PACKAGE_ROOT", self.package), self.assertRaises(ValueError):
                deployment.create_deployment_app(environ=self.environment, api_app=Echo())
        target.write_text(json.dumps(manifest()), encoding="utf-8")
        os.link(target, self.base / "linked-manifest.json")
        with patch.object(deployment, "PACKAGE_ROOT", self.package), self.assertRaises(ValueError):
            deployment.create_deployment_app(environ=self.environment, api_app=Echo())

    def test_21_auth_security_headers_and_api_preserved(self):
        app = self.factory(manifest())
        self.assertEqual(request(app).status_code, 401)
        got = request(app, headers={"Authorization": AUTH})
        self.assertEqual(got.content, TRACKS)
        self.assertEqual(got.headers["cache-control"], "private, no-store")
        self.assertEqual(got.headers["x-content-type-options"], "nosniff")
        self.assertEqual(request(app, "/api/synthetic", headers={"Authorization": AUTH}).json()["path"], "/api/synthetic")
        self.assertEqual(request(app, "/healthz").json(), {"status": "ok"})

    def test_22_static_and_mutation_methods_preserved(self):
        app = self.router(manifest())
        self.assertEqual(request(app, "/").status_code, 200)
        self.assertEqual(request(app, method="POST").status_code, 405)
        for path in ("/demo//sorter-demo.tracks.json", "/demo/sorter-demo.tracks.json.",
                     "/demo/sorter-demo.tracks.json%00", "/demo/%252e%252e/index.html"):
            with self.subTest(path=path):
                self.assertEqual(request(app, path).status_code, 404)

    def test_23_legacy_tag_only_without_tracks_registration(self):
        legacy = manifest()
        legacy["releaseTag"] = "demo-media-20260921-audio-v2"
        with self.assertRaises(ValueError):
            self.router(legacy)
        legacy["assets"][-1].pop("tracks")
        app = self.router(legacy)
        self.assertEqual(request(app).status_code, 404)
        self.assertEqual(request(app, "/demo/sorter-demo.mp4").content, VIDEO)


if __name__ == "__main__":
    unittest.main(verbosity=2)
