"""Build a verified Lambda zip locally; never deploy or load credentials.

Python 3.12 / x86_64 only. Downloads pinned, hash-checked public Linux wheels.
Uses the completed Next export and runtime whitelist of build_deployment_bundle.
Run: python scripts/build_aws_bundle.py
Verify an existing artifact: python scripts/build_aws_bundle.py --verify PATH
AWS limits: https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess
import sys
import zipfile

import build_deployment_bundle as deployment

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = "deploy/aws/requirements-lambda.txt"
PLATFORMS = ("manylinux_2_34_x86_64", "manylinux_2_28_x86_64",
             "manylinux_2_17_x86_64", "manylinux2014_x86_64")
MAX_ZIP = 50 * 1024 * 1024
MAX_EXPANDED = 250 * 1024 * 1024


def digest(content):
    return hashlib.sha256(content).hexdigest()


def inventory(files):
    return [{"path": name, "size": len(content), "sha256": digest(content)}
            for name, content in sorted(files.items())]


def safe_dependency_name(name):
    if not deployment._relative_name(name):
        raise ValueError("INVALID_WHEEL_PATH")
    if any(part in {".local", ".aws", ".ssh", "__pycache__"}
           or part.startswith(".env") for part in name.split("/")):
        raise ValueError("PRIVATE_WHEEL_PATH")
    if Path(name).suffix.lower() in {".pyd", ".dll", ".exe", ".key", ".pfx", ".p12", ".pyc"}:
        raise ValueError("UNSUPPORTED_WHEEL_FILE")


def unpack_wheels(directory):
    files, wheels = {}, []
    for wheel in sorted(directory.glob("*.whl")):
        content = wheel.read_bytes()
        wheels.append({"path": wheel.name, "size": len(content), "sha256": digest(content)})
        with zipfile.ZipFile(wheel) as archive:
            if archive.testzip() is not None:
                raise ValueError("INVALID_WHEEL_CRC")
            for entry in archive.infolist():
                if entry.is_dir():
                    continue
                name = entry.filename
                # SDK documentation examples are never loaded by clients and
                # contain illustrative IAM private keys. Do not ship them.
                if name.startswith("botocore/data/") and name.endswith("/examples-1.json"):
                    continue
                if stat.S_ISLNK(entry.external_attr >> 16):
                    raise ValueError("WHEEL_LINK_REJECTED")
                parts = name.split("/")
                if parts[0].endswith(".data"):
                    if len(parts) >= 3 and parts[1] == "scripts":
                        continue  # Lambda imports libraries; console entry points are unused.
                    if len(parts) < 3 or parts[1] not in {"purelib", "platlib"}:
                        raise ValueError("UNSUPPORTED_WHEEL_INSTALL_SCHEME")
                    name = "/".join(parts[2:])
                safe_dependency_name(name)
                data = archive.read(entry)
                if name.endswith(".so") and (data[:6] != b"\x7fELF\x02\x01"
                                               or int.from_bytes(data[18:20], "little") != 62):
                    raise ValueError("NATIVE_LIBRARY_NOT_LINUX_X86_64")
                if re.search(rb"-----BEGIN (?:[A-Z ]*PRIVATE KEY|OPENSSH PRIVATE KEY)-----", data):
                    raise ValueError("PRIVATE_KEY_IN_WHEEL")
                if name in files:
                    raise ValueError("DUPLICATE_WHEEL_FILE")
                files[name] = data
    if not wheels:
        raise ValueError("DEPENDENCY_WHEELS_MISSING")
    return files, wheels


def runtime_payload():
    files, stamp = deployment._payload(ROOT, ROOT / deployment.MEDIA_MANIFEST)
    # The common validator checks the existing deployment contract before these
    # provider-specific files are removed. AWS invokes the root handler directly.
    del files["api/index.py"]
    del files["vercel.json"]
    files["handler.py"] = deployment._read(ROOT, "deploy/aws/handler.py")
    files["requirements-lambda.txt"] = deployment._read(ROOT, REQUIREMENTS)
    deployment._check_content("handler.py", files["handler.py"])
    return files, stamp


def verify(directory):
    directory = Path(directory).resolve(strict=True)
    manifest = json.loads((directory / "manifest.json").read_text("utf-8"))
    archive_path = directory / "oneflow-lambda.zip"
    if archive_path.stat().st_size > MAX_ZIP or digest(archive_path.read_bytes()) != manifest["zipSha256"]:
        raise ValueError("ZIP_SIZE_OR_HASH_MISMATCH")
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or archive.testzip() is not None:
            raise ValueError("ZIP_DUPLICATE_OR_CRC_ERROR")
        actual = {}
        for entry in archive.infolist():
            safe_dependency_name(entry.filename)
            if stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError("ZIP_LINK_REJECTED")
            actual[entry.filename] = archive.read(entry)
    if inventory(actual) != manifest["files"] or sum(map(len, actual.values())) > MAX_EXPANDED:
        raise ValueError("ZIP_CONTENT_MISMATCH")
    if sum(map(len, actual.values())) != manifest["expandedBytes"]:
        raise ValueError("ZIP_EXPANDED_SIZE_MISMATCH")
    return {"directory": str(directory), "zipBytes": archive_path.stat().st_size,
            "expandedBytes": manifest["expandedBytes"], "fileCount": len(actual),
            "zipSha256": manifest["zipSha256"], "status": "verified-local-only"}


def build():
    if sys.version_info[:2] != (3, 12):
        raise ValueError("PYTHON_312_REQUIRED")
    sources, stamp = runtime_payload()
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = ROOT / "dist/aws" / (timestamp + "-" + revision[:12])
    deployment._no_links(output)
    output.mkdir(parents=True, exist_ok=False)
    wheels_dir = output / "wheels"
    wheels_dir.mkdir()
    # Copy the exact validated requirements bytes; source changes cannot alter
    # the dependency download half way through a build.
    requirements = output / "requirements-lambda.txt"
    requirements.write_bytes(sources["requirements-lambda.txt"])
    command = [sys.executable, "-m", "pip", "--isolated", "--disable-pip-version-check",
               "download", "--index-url", "https://pypi.org/simple", "--only-binary=:all:",
               "--no-deps", "--require-hashes", "--implementation", "cp", "--abi", "cp312",
               "--python-version", "3.12", "--dest", str(wheels_dir), "-r", str(requirements)]
    for platform in PLATFORMS:
        command.extend(["--platform", platform])
    downloaded = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if downloaded.returncode:
        # The command only addresses public PyPI, but avoid echoing arbitrary
        # local pip configuration, proxy values or inherited environment data.
        raise ValueError("PUBLIC_LINUX_WHEEL_DOWNLOAD_FAILED")
    dependencies, wheels = unpack_wheels(wheels_dir)
    if sources.keys() & dependencies.keys():
        raise ValueError("APPLICATION_DEPENDENCY_PATH_COLLISION")
    files = dependencies | sources
    expanded = sum(map(len, files.values()))
    if expanded > MAX_EXPANDED:
        raise ValueError("LAMBDA_EXPANDED_SIZE_LIMIT")
    for name, content in files.items():
        if name.startswith("apps/web/out/") and ((len(content) + 2) // 3 * 4 + 16384) > 6 * 1024 * 1024:
            raise ValueError("STATIC_FILE_EXCEEDS_BUFFERED_RESPONSE_LIMIT")
    archive_path = output / "oneflow-lambda.zip"
    with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(files.items()):
            entry = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, content)
    if archive_path.stat().st_size > MAX_ZIP:
        raise ValueError("LAMBDA_DIRECT_UPLOAD_SIZE_LIMIT")
    fresh_sources, fresh_stamp = runtime_payload()
    if fresh_sources != sources or fresh_stamp != stamp:
        raise ValueError("SOURCE_CHANGED_DURING_PACKAGE")
    manifest = {"schemaVersion": "oneflow-aws-lambda-v1", "status": "complete",
                "runtime": "python3.12", "architecture": "x86_64", "handler": "handler.handler",
                "sourceRevision": revision, "sourceBytesFingerprint": deployment._inventory_fingerprint(sources),
                "frontendSourceFingerprint": stamp["sourceAfter"],
                "frontendOutputFingerprint": stamp["outputFingerprint"],
                "createdAt": timestamp, "expandedBytes": expanded,
                "zipBytes": archive_path.stat().st_size, "zipSha256": digest(archive_path.read_bytes()),
                "wheels": wheels, "files": inventory(files),
                "notVerified": ["AWS deployment and IAM", "Linux runtime invocation",
                                "remote DynamoDB and live model requests"]}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return verify(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path)
    arguments = parser.parse_args()
    try:
        result = verify(arguments.verify) if arguments.verify else build()
    except (ValueError, OSError, subprocess.SubprocessError, zipfile.BadZipFile) as error:
        print(json.dumps({"status": "failed", "code": str(error) if isinstance(error, ValueError)
                          else type(error).__name__}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
