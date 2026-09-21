"""Isolated packaging contracts; synthetic bytes only, no npm/network/deployment.

These tests establish local artifact boundaries, not Vercel build/runtime support.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest

from scripts import build_deployment_bundle as bundle


REAL_ROOT = Path(__file__).resolve().parents[1]
TIMESTAMP = "20260921T090000000000Z"
REVISION = "a" * 40
MEDIA_NAMES = ("CASE-0001.wav", "CASE-0002.wav", "sorter-demo.mp4")


def put(root: Path, name: str, content: str | bytes) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
    return path


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file()}


@pytest.fixture
def source_repo(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    for relative in bundle.SOURCE_FILES:
        name = str(relative).replace("\\", "/")
        content = "# synthetic source\n" if name.endswith(".py") else "{}\n"
        put(root, name, content)
    for name in ("index.py", "vercel.json"):
        target = root / "deploy/vercel" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REAL_ROOT / "deploy/vercel" / name, target)
    put(root, "pyproject.toml", '[project]\nname = "synthetic-bundle"\n'
        'version = "0.0.0"\nrequires-python = ">=3.12,<3.13"\n'
        'dependencies = []\n[tool.uv]\npackage = false\n')
    put(root, "uv.lock", 'version = 1\nrevision = 1\nrequires-python = ">=3.12,<3.13"\n')
    put(root, "data/fixtures/cases.json", '[{"id":"SYN-TEST-1","synthetic":true}]\n')
    put(root, "data/overlays/pc4-tms.json", '{"synthetic":true,"visits":[]}\n')
    for name, content in {
        "app/page.tsx": "export default function Page(){return 'synthetic';}\n",
        "app/layout.tsx": "export default function Layout(){return 'synthetic';}\n",
        "app/globals.css": "body{color:#111}\n",
        "components/Card.tsx": "export const Card = 'synthetic';\n",
        "lib/api.ts": "export const API_BASE = '';\n",
        "package.json": '{"name":"synthetic-web","scripts":{"build":"next build"}}\n',
        "package-lock.json": '{"name":"synthetic-web","lockfileVersion":3}\n',
        "tsconfig.json": '{}\n',
        "next.config.ts": "export default {output:'export'};\n",
        "next-env.d.ts": "// synthetic Next type reference\n",
        "public/cases.json": '[{"id":"SYN-TEST-1","synthetic":true}]\n',
        "out/index.html": "<!doctype html><main>synthetic</main>\n",
        "out/404.html": "<!doctype html><main>not found</main>\n",
        "out/index.txt": 'synthetic RSC payload\n',
        "out/cases.json": '[{"id":"SYN-TEST-1","synthetic":true}]\n',
        "out/_next/static/chunks/a.js": "self.synthetic = true;\n",
        "out/_next/static/css/a.css": "body{color:#111}\n",
    }.items():
        put(root, "apps/web/" + name, content)
    assets = []
    for name in MEDIA_NAMES:
        content = ("synthetic-media-for-tests-only:" + name).encode()
        for relative in ("apps/web/public/demo/", "apps/web/out/demo/"):
            put(root, relative + name, content)
        assets.append({"name": name, "bytes": len(content),
                       "sha256": digest(content), "synthetic": True})
    manifest = {"schemaVersion": 1,
                "repository": "cjj0202-glitch/happycall-ralphthon",
                "releaseTag": "demo-media-20260921", "assets": assets}
    put(root, "data/demo-media-manifest.json", json.dumps(manifest))
    stamp(root)
    return root


def stamp(root: Path):
    return bundle.write_build_stamp(root, bundle.source_fingerprint(root))


def build(root: Path, *, timestamp=TIMESTAMP, **kwargs) -> Path:
    return bundle.build_bundle(root, root / "data/demo-media-manifest.json",
                               timestamp=timestamp, revision=REVISION, **kwargs)


def assert_no_complete_bundle(root: Path):
    destination = root / "dist/deployment"
    assert not destination.exists() or not list(destination.glob("*/.bundle-manifest.json"))


def test_complete_bundle_has_exact_inventory_and_two_verified_media_copies(source_repo):
    root = source_repo
    before = {p: content for p, content in tree_bytes(root).items()
              if not p.startswith("dist/")}
    output = build(root)
    assert output.is_relative_to(root / "dist/deployment")
    actual = tree_bytes(output)
    manifest = json.loads(actual[".bundle-manifest.json"])
    assert manifest["schemaVersion"] == "oneflow-deployment-bundle-v1"
    assert manifest["status"] == "complete"
    entries = {entry["path"]: entry for entry in manifest["files"]}
    assert len(entries) == len(manifest["files"])
    assert set(entries) == set(actual) - {".bundle-manifest.json"}
    assert manifest["totalBytes"] == sum(len(actual[name]) for name in entries)
    for name, entry in entries.items():
        assert entry["size"] == len(actual[name])
        assert entry["sha256"] == digest(actual[name])
    for name in MEDIA_NAMES:
        expected = (root / "apps/web/public/demo" / name).read_bytes()
        assert actual["apps/web/out/demo/" + name] == expected
        assert actual["apps/web/public/demo/" + name] == expected
    assert {"api/index.py", "vercel.json", "pyproject.toml", "uv.lock",
            "server/deployment_app.py", "data/fixtures/cases.json",
            "scripts/demo_openai_env.py", "apps/web/out/index.html"} <= set(entries)
    assert not any(Path(name).name == bundle.BUILD_STAMP_NAME for name in entries)
    assert before == {p: content for p, content in tree_bytes(root).items()
                      if not p.startswith("dist/")}


def register_tracks(root):
    from server.media_contract import CURRENT_RELEASE_TAG, TRACKS_NAME, TRACKS_SCHEMA, TRACKS_URL
    manifest_path = root / bundle.MEDIA_MANIFEST
    manifest = json.loads(manifest_path.read_bytes())
    manifest["releaseTag"] = CURRENT_RELEASE_TAG
    content = b'{"synthetic":true,"frames":[]}'
    video = next(a for a in manifest["assets"] if a["name"] == "sorter-demo.mp4")
    video["tracks"] = {"schemaVersion": TRACKS_SCHEMA, "url": TRACKS_URL,
                       "bytes": len(content), "sha256": digest(content), "videoSha256": video["sha256"]}
    put(root, bundle.MEDIA_MANIFEST, json.dumps(manifest))
    for folder in ("apps/web/public/demo/", "apps/web/out/demo/"):
        put(root, folder + TRACKS_NAME, content)
    return content


def test_registered_tracks_copied_exactly_and_contract_module_bundled(source_repo):
    content = register_tracks(source_repo)
    stamp(source_repo)
    output = build(source_repo)
    assert (output / "apps/web/public/demo/sorter-demo.tracks.json").read_bytes() == content
    assert (output / "apps/web/out/demo/sorter-demo.tracks.json").read_bytes() == content
    assert (output / "server/media_contract.py").is_file()


@pytest.mark.parametrize("field,value", [("bytes", True), ("bytes", 10000001),
    ("schemaVersion", "other"), ("url", "/demo/../other.json"),
    ("sha256", "A" * 64), ("videoSha256", "f" * 64)])
def test_invalid_registered_tracks_blocks_stamp(source_repo, field, value):
    register_tracks(source_repo)
    path = source_repo / bundle.MEDIA_MANIFEST
    manifest = json.loads(path.read_bytes())
    next(a for a in manifest["assets"] if a["name"] == "sorter-demo.mp4")["tracks"][field] = value
    put(source_repo, bundle.MEDIA_MANIFEST, json.dumps(manifest))
    with pytest.raises(bundle.BundleError, match="INVALID_MEDIA_MANIFEST"):
        stamp(source_repo)
    assert_no_complete_bundle(source_repo)


def test_unregistered_tracks_cannot_be_packaged(source_repo):
    put(source_repo, "apps/web/out/demo/sorter-demo.tracks.json", "{}")
    with pytest.raises(bundle.BundleError, match="UNAPPROVED_EXPORT_FILE"):
        stamp(source_repo)


def test_registered_tracks_missing_public_cannot_be_packaged(source_repo):
    register_tracks(source_repo)
    (source_repo / "apps/web/public/demo/sorter-demo.tracks.json").unlink()
    with pytest.raises((bundle.BundleError, OSError)):
        stamp(source_repo)


def test_forbidden_root_files_are_neither_read_nor_copied(source_repo, monkeypatch):
    excluded = set()
    for name in (".env", ".env.demo.local", ".local/live-api.log", ".git/config",
                 "raw/customer.json", "node_modules/private.js", "keys/private.pem"):
        excluded.add(put(source_repo, name, "unread-synthetic-private-sentinel").resolve())
    original_open = Path.open

    def guarded_open(path, *args, **kwargs):
        if path.resolve() in excluded:
            raise AssertionError("Packaging opened a non-allowlisted root file")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    output = build(source_repo)
    copied = tree_bytes(output)
    assert not any("unread-synthetic-private-sentinel".encode() in data
                   for data in copied.values())
    assert all(not any(part in {".local", ".git", "raw", "keys", "node_modules"}
                       for part in Path(name).parts) for name in copied)


@pytest.mark.parametrize("location", ["apps/web/public/demo/CASE-0001.wav",
                                    "apps/web/out/demo/CASE-0001.wav"])
def test_same_size_media_mutation_is_rejected_after_fresh_stamp(source_repo, location):
    path = source_repo / location
    original = path.read_bytes()
    mutated = bytes([original[0] ^ 1]) + original[1:]
    path.write_bytes(mutated)
    # A newly signed output cannot bless bytes that differ from approval hashes.
    with pytest.raises(bundle.BundleError):
        stamp(source_repo)
        build(source_repo)
    assert path.read_bytes() == mutated
    assert_no_complete_bundle(source_repo)


@pytest.mark.parametrize("change", ["synthetic", "sha256", "bytes", "name", "repository"])
def test_unapproved_or_invalid_media_manifest_is_rejected(source_repo, change):
    path = source_repo / "data/demo-media-manifest.json"
    manifest = json.loads(path.read_text())
    if change == "repository":
        manifest["repository"] = "unapproved/synthetic"
    else:
        manifest["assets"][0][change] = {"synthetic": False, "sha256": "0" * 64,
                                         "bytes": 0, "name": "../escape.wav"}[change]
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(bundle.BundleError):
        stamp(source_repo)
        build(source_repo)
    assert_no_complete_bundle(source_repo)


@pytest.mark.parametrize("name", [".env", "credentials.json", "_next/static/chunks/a.js.map",
                                  "_next/static/chunks/readme.txt", "demo/unapproved.wav"])
def test_unknown_or_secret_named_export_file_is_rejected(source_repo, name):
    put(source_repo, "apps/web/out/" + name, "synthetic unexpected content")
    with pytest.raises(bundle.BundleError):
        stamp(source_repo)
        build(source_repo)
    assert_no_complete_bundle(source_repo)


@pytest.mark.parametrize("name", ["apps/web/out/index.html", "server/live.py"])
def test_credential_content_in_allowed_file_is_rejected_without_echo(source_repo, name):
    fake_key = "sk-" + "testOnlyNeverRealCredentials" * 3
    put(source_repo, name, 'synthetic_key = "' + fake_key + '"\n')
    with pytest.raises(bundle.BundleError) as error:
        stamp(source_repo)
        build(source_repo)
    assert fake_key not in str(error.value)
    assert_no_complete_bundle(source_repo)


@pytest.mark.parametrize("name", ["server/deployment_app.py", "server/openapi.yaml", "uv.lock",
                                  "apps/web/out/index.html", "apps/web/out/404.html",
                                  "apps/web/out/index.txt", "apps/web/out/cases.json",
                                  "apps/web/out/demo/CASE-0002.wav"])
def test_missing_required_input_is_rejected(source_repo, name):
    (source_repo / name).unlink()
    with pytest.raises(bundle.BundleError):
        stamp(source_repo)
        build(source_repo)
    assert_no_complete_bundle(source_repo)


def test_unsigned_output_is_rejected(source_repo):
    stamps = list(source_repo.rglob(bundle.BUILD_STAMP_NAME))
    assert len(stamps) == 1
    stamps[0].unlink()
    with pytest.raises(bundle.BundleError):
        build(source_repo)
    assert_no_complete_bundle(source_repo)


@pytest.mark.parametrize("name", ["apps/web/app/page.tsx", "apps/web/components/Card.tsx",
                                  "apps/web/lib/api.ts", "apps/web/public/cases.json",
                                  "apps/web/package-lock.json", "apps/web/next.config.ts"])
def test_source_change_after_build_stamp_is_rejected(source_repo, name):
    with (source_repo / name).open("a", encoding="utf-8") as stream:
        stream.write("\n// synthetic source change after build\n")
    with pytest.raises(bundle.BundleError):
        build(source_repo)
    assert_no_complete_bundle(source_repo)


def test_source_change_during_build_cannot_receive_completion_stamp(source_repo):
    before = bundle.source_fingerprint(source_repo)
    put(source_repo, "apps/web/app/page.tsx", "export default 'changed-during-build';\n")
    with pytest.raises(bundle.BundleError):
        bundle.write_build_stamp(source_repo, before)
    with pytest.raises(bundle.BundleError):
        build(source_repo)


@pytest.mark.parametrize('name', bundle.FRONTEND_DATA_FILES)
def test_external_client_json_change_invalidates_build(source_repo, name):
    before = bundle.source_fingerprint(source_repo)
    # Valid JSON whitespace change suffices: the export must bind the exact input.
    with (source_repo / name).open('a', encoding='utf-8') as stream:
        stream.write('\n ')
    assert bundle.source_fingerprint(source_repo) != before
    with pytest.raises(bundle.BundleError, match='STALE_OR_CHANGED_BUILD_STAMP'):
        build(source_repo)
    assert_no_complete_bundle(source_repo)


@pytest.mark.parametrize('name', bundle.FRONTEND_DATA_FILES)
def test_missing_external_client_json_cannot_receive_stamp(source_repo, name):
    (source_repo / name).unlink()
    with pytest.raises(bundle.BundleError):
        bundle.source_fingerprint(source_repo)


def test_output_change_after_build_stamp_is_rejected(source_repo):
    put(source_repo, "apps/web/out/_next/static/chunks/a.js", "self.tampered = true;\n")
    with pytest.raises(bundle.BundleError):
        build(source_repo)
    assert_no_complete_bundle(source_repo)


def test_existing_bundle_is_preserved_byte_for_byte(source_repo):
    output = build(source_repo)
    sentinel = put(output, "existing-owner-file.txt", "preserve existing output")
    before = tree_bytes(output)
    with pytest.raises(bundle.BundleError):
        build(source_repo)
    assert sentinel.exists()
    assert tree_bytes(output) == before


def test_size_limit_accepts_exact_payload_and_rejects_one_byte_less(source_repo):
    baseline = build(source_repo)
    total = json.loads((baseline / ".bundle-manifest.json").read_text())["totalBytes"]
    exact = build(source_repo, timestamp="20260921T090001000000Z", max_bytes=total)
    assert exact.is_dir()
    with pytest.raises(bundle.BundleError):
        build(source_repo, timestamp="20260921T090002000000Z", max_bytes=total - 1)


@pytest.mark.parametrize("name", ["server/live.py", "apps/web/out/_next/static/chunks/a.js"])
def test_same_bytes_symlink_input_is_rejected(source_repo, tmp_path, monkeypatch, name):
    path = source_repo / name
    original = path.read_bytes()
    target = put(tmp_path, "outside/synthetic-target", original)
    path.unlink()
    try:
        path.symlink_to(target)
    except OSError as error:
        if getattr(error, "winerror", None) != 1314:
            raise
        # Windows may lack the symlink privilege. Exercise the link-detection
        # boundary deterministically rather than silently skip the contract.
        path.write_bytes(original)
        original_is_symlink = Path.is_symlink
        monkeypatch.setattr(Path, "is_symlink", lambda item:
                            item == path or original_is_symlink(item))
    with pytest.raises(bundle.BundleError):
        build(source_repo)
    assert target.read_bytes() == original
    assert_no_complete_bundle(source_repo)


@pytest.mark.parametrize("relative", ["server", "apps/web/out/_next", "dist"])
def test_junction_in_input_or_output_ancestor_is_rejected(source_repo, monkeypatch, relative):
    junction = source_repo / relative
    junction.mkdir(parents=True, exist_ok=True)
    original_is_junction = Path.is_junction
    monkeypatch.setattr(Path, "is_junction", lambda path:
                        path == junction or original_is_junction(path))
    with pytest.raises(bundle.BundleError):
        build(source_repo)
    assert_no_complete_bundle(source_repo)


def test_external_manifest_is_rejected_even_if_content_is_valid(source_repo, tmp_path):
    external = put(tmp_path, "outside-manifest.json",
                   (source_repo / "data/demo-media-manifest.json").read_bytes())
    with pytest.raises(bundle.BundleError):
        bundle.build_bundle(source_repo, external, timestamp=TIMESTAMP, revision=REVISION)
    assert_no_complete_bundle(source_repo)


@pytest.mark.parametrize("timestamp,revision", [("../escape", REVISION),
                                               (TIMESTAMP, "../escape")])
def test_output_path_components_cannot_escape_destination(source_repo, timestamp, revision):
    with pytest.raises(bundle.BundleError):
        bundle.build_bundle(source_repo, source_repo / "data/demo-media-manifest.json",
                            timestamp=timestamp, revision=revision)
    assert_no_complete_bundle(source_repo)


def test_build_mode_records_completion_only_with_sanitized_environment(source_repo, monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-secret-not-for-build")
    monkeypatch.setenv("BLOB_READ_WRITE_TOKEN", "synthetic-storage-secret")
    monkeypatch.setenv("ONEFLOW_ACCESS_PASSWORD", "synthetic-access-secret")
    monkeypatch.setenv("NEXT_PUBLIC_API_BASE", "https://unexpected.invalid")
    monkeypatch.setattr(bundle.shutil, "which", lambda name: "synthetic-npm")
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        assert not list(source_repo.rglob(bundle.BUILD_STAMP_NAME))
        assert kwargs["env"]["NEXT_PUBLIC_API_BASE"] == ""
        assert not {"OPENAI_API_KEY", "BLOB_READ_WRITE_TOKEN", "ONEFLOW_ACCESS_PASSWORD"} & kwargs["env"].keys()
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(bundle.subprocess, "run", run)
    assert bundle.main(["--root", str(source_repo), "--build"]) == 0
    assert len(calls) == 1 and calls[0][0] == ["synthetic-npm", "run", "build"]
    assert calls[0][1]["cwd"] == source_repo / "apps/web"
    assert len(list(source_repo.rglob(bundle.BUILD_STAMP_NAME))) == 1
    assert not (source_repo / "dist").exists()
    assert "build-recorded" in capsys.readouterr().out


def test_failed_npm_removes_old_completion_and_never_echoes_build_output(source_repo, monkeypatch, capsys):
    monkeypatch.setattr(bundle.shutil, "which", lambda name: "synthetic-npm")
    marker = "synthetic-private-error-value"
    monkeypatch.setattr(bundle.subprocess, "run", lambda *args, **kwargs:
                        SimpleNamespace(returncode=1, stdout=marker, stderr=marker))
    assert bundle.main(["--root", str(source_repo), "--build"]) == 1
    assert not list(source_repo.rglob(bundle.BUILD_STAMP_NAME))
    output = capsys.readouterr()
    assert marker not in output.out + output.err
    with pytest.raises(bundle.BundleError):
        build(source_repo)


def test_source_changed_by_mock_npm_cannot_receive_stamp(source_repo, monkeypatch):
    monkeypatch.setattr(bundle.shutil, "which", lambda name: "synthetic-npm")
    def run(*args, **kwargs):
        put(source_repo, "apps/web/app/page.tsx", "export default 'changed-by-mock-build';")
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(bundle.subprocess, "run", run)
    with pytest.raises(bundle.BundleError):
        bundle.run_build(source_repo)
    assert not list(source_repo.rglob(bundle.BUILD_STAMP_NAME))
    assert_no_complete_bundle(source_repo)


def test_build_record_checksum_catches_metadata_tamper(source_repo):
    path = next(source_repo.rglob(bundle.BUILD_STAMP_NAME))
    record = json.loads(path.read_text())
    record["completedAt"] = "tampered-local-record"
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(bundle.BundleError):
        build(source_repo)
    assert_no_complete_bundle(source_repo)


def test_missing_local_runtime_dependency_is_rejected(source_repo):
    put(source_repo, "server/live.py", "from server.not_in_bundle import dependency\n")
    with pytest.raises(bundle.BundleError):
        build(source_repo)
    assert_no_complete_bundle(source_repo)


def test_frontend_dotenv_is_rejected_before_reading_it(source_repo, monkeypatch):
    private = put(source_repo, "apps/web/.env.local", "do-not-open-synthetic-private-data")
    original_open = Path.open
    def forbidden_open(path, *args, **kwargs):
        assert path != private, "Next dotenv contents must not be read"
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", forbidden_open)
    with pytest.raises(bundle.BundleError, match="FRONTEND_ENV_FILE_REJECTED"):
        build(source_repo)
    assert_no_complete_bundle(source_repo)


@pytest.mark.parametrize("change", ["filesystem", "second-function", "output-directory", "rewrite"])
def test_vercel_configuration_cannot_create_static_authentication_bypass(source_repo, change):
    path = source_repo / "deploy/vercel/vercel.json"
    value = json.loads(path.read_text())
    if change == "filesystem":
        value["routes"].insert(0, {"handle": "filesystem"})
    elif change == "second-function":
        value["functions"]["api/other.py"] = {}
    elif change == "output-directory":
        value["outputDirectory"] = "apps/web/out"
    else:
        value["rewrites"] = [{"source": "/:path*", "destination": "/:path*"}]
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(bundle.BundleError):
        build(source_repo)
    assert_no_complete_bundle(source_repo)


def test_real_runtime_imports_and_asgi_work_without_original_repository(source_repo):
    # Only approved Python source is taken from the real repository. Fixture,
    # media, environment and Next export remain temporary synthetic inputs.
    for relative in bundle.SOURCE_FILES:
        if relative.endswith(".py") or relative == "server/openapi.yaml":
            put(source_repo, relative, (REAL_ROOT / relative).read_bytes())
    output = build(source_repo)
    environment = {key: value for key, value in os.environ.items()
                   if key.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "COMSPEC", "PATHEXT"}}
    environment.update({"ONEFLOW_ACCESS_USER": "bundle-reviewer",
                        "ONEFLOW_ACCESS_PASSWORD": "R8!vB4@qC2#nM9$sL1%wZ6&kJ0",
                        "ONEFLOW_STATIC_DIR": "deliberately-ignored-external-path"})
    code = r'''
import asyncio, base64, json, os, sys
from pathlib import Path
root = Path.cwd()
sys.path.insert(0, str(root))
from api.index import app
from server import deployment_app, handlers, live, runtime_config, runtime_storage
import scripts.demo_openai_env
for module in (deployment_app, handlers, live, runtime_config, runtime_storage, scripts.demo_openai_env):
    assert Path(module.__file__).resolve().is_relative_to(root)
assert app.app.root == root / "apps/web/out"
def forbidden(*args, **kwargs):
    raise AssertionError("Live, secret-file and real-state access forbidden")
handlers.get_runtime_storage = handlers.service = live.OpenAI = runtime_config.read_demo_env = forbidden
import httpx
authorization = "Basic " + base64.b64encode((os.environ["ONEFLOW_ACCESS_USER"] + ":" + os.environ["ONEFLOW_ACCESS_PASSWORD"]).encode()).decode()
async def check():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://bundle.invalid") as client:
        assert (await client.get("/healthz")).json() == {"status": "ok"}
        for path in ("/", "/demo/CASE-0001.wav", "/api/cases"):
            assert (await client.get(path)).status_code == 401
        assert (await client.get("/", headers={"Authorization": authorization})).status_code == 200
        media = await client.get("/demo/sorter-demo.mp4", headers={"Authorization": authorization, "Range": "bytes=0-3"})
        assert media.status_code == 206 and len(media.content) == 4
        assert (await client.get("/api/unknown", headers={"Authorization": authorization})).status_code == 404
asyncio.run(check())
print(json.dumps({"selfContained": True, "health": 200, "protected": 401, "range": 206, "unknownApi": 404}))
'''
    # -I ignores PYTHONUTF8, so bind child and reader encodings explicitly.
    result = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", "-c", code], cwd=output,
                            env=environment, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"selfContained": True, "health": 200, "protected": 401,
                                        "range": 206, "unknownApi": 404}
    assert not (output / ".local").exists()


def test_packaging_guard_mutants_are_killed_with_same_location_controls(source_repo, tmp_path):
    source = Path(bundle.__file__).read_text(encoding="utf-8")
    def module_copy(text):
        copied = ModuleType("synthetic_bundle_mutant")
        copied.__file__ = bundle.__file__
        exec(compile(text, "<memory-only-bundle-mutant>", "exec"), copied.__dict__)
        return copied
    def reject_secret(candidate, root):
        put(root, "server/live.py", 'key = "sk-' + "syntheticKeyOnly" * 4 + '"\n')
        with pytest.raises(candidate.BundleError):
            candidate.build_bundle(root, root / bundle.MEDIA_MANIFEST, timestamp=TIMESTAMP, revision=REVISION)
    def reject_stale_source(candidate, root):
        put(root, "apps/web/app/page.tsx", "export default 'stale-source';")
        with pytest.raises(candidate.BundleError):
            candidate.build_bundle(root, root / bundle.MEDIA_MANIFEST, timestamp=TIMESTAMP, revision=REVISION)
    def reject_media(candidate, root):
        # Reach the hash comparison even with the preceding byte-size guard.
        original = (root / "apps/web/public/demo" / MEDIA_NAMES[0]).read_bytes()
        changed = bytes([original[0] ^ 1]) + original[1:]
        for prefix in ("apps/web/public/demo/", "apps/web/out/demo/"):
            put(root, prefix + MEDIA_NAMES[0], changed)
        with pytest.raises(candidate.BundleError):
            candidate.write_build_stamp(root, candidate.source_fingerprint(root))
            candidate.build_bundle(root, root / bundle.MEDIA_MANIFEST, timestamp=TIMESTAMP, revision=REVISION)
    def reject_static_route(candidate, root):
        path = root / "deploy/vercel/vercel.json"
        config = json.loads(path.read_text())
        config["routes"].insert(0, {"handle": "filesystem"})
        path.write_text(json.dumps(config), encoding="utf-8")
        with pytest.raises(candidate.BundleError):
            candidate.build_bundle(root, root / bundle.MEDIA_MANIFEST, timestamp=TIMESTAMP, revision=REVISION)
    mutations = [
        ("credential-scan", "if any(pattern.search(content) for pattern in _SECRET_PATTERNS):", "if False:", reject_secret),
        ("source-binding", 'payload["sourceAfter"] != source_fingerprint(root)', "False", reject_stale_source),
        ("media-hash", 'if (len(content) != asset["bytes"] or _digest(content) != asset["sha256"]\n                or exported != content):', "if False:", reject_media),
        ("static-routing", 'routing.get("routes") != [{"src": "/(.*)", "dest": "/api/index.py"}]', "False", reject_static_route),
    ]
    killed = 0
    for name, before, after, check in mutations:
        assert source.count(before) == 1, name
        control_root = tmp_path / (name + "-control")
        mutant_root = tmp_path / (name + "-mutant")
        shutil.copytree(source_repo, control_root)
        shutil.copytree(source_repo, mutant_root)
        check(module_copy(source), control_root)
        with pytest.raises(pytest.fail.Exception):
            check(module_copy(source.replace(before, after)), mutant_root)
        killed += 1
    assert killed == 4
