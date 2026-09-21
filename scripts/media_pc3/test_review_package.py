"""Offline viewer tests using fabricated package fixtures, never real renders."""
from __future__ import annotations

import base64
import contextlib
import copy
from html.parser import HTMLParser
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import build_review_page as viewer
from compare_representatives import Invalid, compare_runs
from test_compare_representatives import make_run
from test_render_package import digest, make_package, mutate_report, write_json

SCRATCH = ROOT / ".local/pc3-tests/review-package"


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def attrs(self, name):
        return [attrs for tag, attrs in self.tags if tag == name]


class ReviewPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verifier = importlib.import_module("verify_render_package")
        SCRATCH.mkdir(parents=True, exist_ok=True)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="synthetic-", dir=SCRATCH)
        self.root = Path(temporary.name).resolve()
        self.assertEqual(self.root.parent, SCRATCH.resolve())
        self.addCleanup(temporary.cleanup)
        self.package, self.expected = make_package(self.root)
        self.expectation_file = self.root / "expectations.json"
        write_json(self.expectation_file, self.expected)

    def verified(self, package=None, expected=None):
        result = self.verifier.verify_package(package or self.package, expected or self.expected)
        self.assertIs(result["valid"], True, result["failures"])
        return result

    def command(self, *args):
        return subprocess.run([sys.executable, "-B", str(HERE / "build_review_page.py"), *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8")

    def package_args(self, output):
        return ["--package", self.package, "--expectations", self.expectation_file, "--output", output]

    def assert_refused(self, verification):
        with self.assertRaises((ValueError, TypeError, Invalid, OSError)):
            viewer.build_package_html(self.package, verification)

    def test_all_four_mode_denominators_and_exact_selected_original_bytes(self):
        for mode, total in (("prepare", 0), ("representatives", 3), ("short", 72), ("animation", 288)):
            with self.subTest(mode=mode):
                package, expected = make_package(self.root / mode, mode)
                result = self.verified(package, expected)
                page = viewer.build_package_html(package, result)
                images = Document(page).attrs("img")
                selected = viewer.PACKAGE_SELECTION[mode]
                self.assertEqual(len(images), len(selected))
                self.assertIn(f"표시 PNG {len(selected)} / 검증 목록 PNG {total}", page)
                self.assertIn("좌표 288행", page)
                for attributes, frame in zip(images, selected):
                    header, raw = attributes["src"].split(",", 1)
                    self.assertEqual(header, "data:image/png;base64")
                    self.assertEqual(base64.b64decode(raw, validate=True), (package / f"frame-{frame:04d}.png").read_bytes())
                    self.assertIn(f"시연 +{(frame - 1) / 24:.6f}초", page)
                if mode == "prepare":
                    self.assertIn("prepare: PNG 0장", page)

    def test_page_has_pending_provenance_fixed_clock_and_no_external_execution(self):
        page = viewer.build_package_html(self.package, self.verified())
        document = Document(page)
        self.assertFalse(document.attrs("script"))
        self.assertFalse(document.attrs("video"))
        policy = next(item["content"] for item in document.attrs("meta") if item.get("http-equiv") == "Content-Security-Policy")
        for fragment in ("default-src 'none'", "img-src data:", "style-src 'unsafe-inline'"):
            self.assertIn(fragment, policy)
        for _, attributes in document.tags:
            self.assertFalse(any(key.lower().startswith("on") for key in attributes))
            self.assertFalse(any(attributes.get(key, "").startswith(("http:", "https:", "//")) for key in ("href", "src")))
        for text in ("visualAccepted=false", "VISUAL REVIEW PENDING", "synthetic-scene-ground-truth",
                     "occlusionTested=false", "2026-09-18T02:33:00+09:00", "sourceCommit", "NOT_RUN", "@media", ":focus-visible"):
            self.assertIn(text, page)
        self.assertEqual(len(document.attrs("input")), 4)
        self.assertTrue(all("checked" not in attributes for attributes in document.attrs("input")))

    def test_report_text_is_escaped_without_altering_image_bytes(self):
        mutate_report(self.package, lambda report: report.__setitem__("note", '<script>alert("x")</script>&<img src="https://invalid">'))
        page = viewer.build_package_html(self.package, self.verified())
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<script>", page)
        self.assertEqual(len(Document(page).attrs("img")), 3)

    def test_invalid_verifier_status_schema_flags_and_source_rejected(self):
        result = self.verified()
        changes = [{"valid": False}, {"status": "FAIL"}, {"schemaVersion": "old"}, {"failures": [{"code": "bad"}]},
                   {"sourceCommit": "fake"}, {"mode": "other"}, {"mode": []}]
        changes += [{flag: True} for flag in ("visualAccepted", "pixelDecoded", "videoDecoded", "authenticityVerified")]
        for change in changes:
            with self.subTest(change=change):
                self.assert_refused({**result, **change})

    def test_image_denominator_frame_time_descriptor_and_binding_rejected(self):
        result = self.verified()
        variants = [lambda r: r["images"].pop(), lambda r: r["images"][0].__setitem__("frame", True),
                    lambda r: r["images"][0].__setitem__("elapsedSeconds", float("nan")),
                    lambda r: r["images"][0].__setitem__("elapsedSeconds", 0.5),
                    lambda r: r["images"][0].__setitem__("name", "../outside.png"),
                    lambda r: r["images"][0].__setitem__("bytes", True),
                    lambda r: r["images"][0].__setitem__("sha256", "0" * 64),
                    lambda r: r["inputDigests"].append(copy.deepcopy(r["inputDigests"][0])),
                    lambda r: r["inputDigests"].pop()]
        for index, mutate in enumerate(variants):
            with self.subTest(index=index):
                invalid = copy.deepcopy(result)
                mutate(invalid)
                self.assert_refused(invalid)

    def test_selected_same_size_png_changed_after_verification_rejected(self):
        result = self.verified()
        path = self.package / "frame-0133.png"
        raw = bytearray(path.read_bytes())
        raw[-1] ^= 1
        path.write_bytes(raw)
        self.assert_refused(result)

    def test_unselected_short_png_is_rehashed(self):
        package, expected = make_package(self.root / "short", "short")
        result = self.verified(package, expected)
        path = package / "frame-0080.png"
        path.write_bytes(path.read_bytes() + b"changed")
        with self.assertRaises(ValueError):
            viewer.build_package_html(package, result)

    def test_report_tracks_and_blend_rehashed_not_only_images(self):
        for name in ("render-report.json", "tracks.json", "case-0002-ww3.blend"):
            with self.subTest(name=name):
                result = self.verified()
                path = self.package / name
                raw = path.read_bytes()
                path.write_bytes(raw + b" ")
                self.assert_refused(result)
                path.write_bytes(raw)

    def test_added_file_or_directory_after_verification_rejected(self):
        result = self.verified()
        for name, folder in (("unknown.txt", False), ("extra", True)):
            path = self.package / name
            with self.subTest(name=name):
                path.mkdir() if folder else path.write_bytes(b"extra")
                self.assert_refused(result)
                path.rmdir() if folder else path.unlink()

    def test_hardlinked_asset_even_with_matching_bytes_rejected(self):
        result = self.verified()
        path = self.package / "frame-0001.png"
        outside = self.root / "outside.png"
        outside.write_bytes(path.read_bytes())
        path.unlink()
        os.link(outside, path)
        self.assert_refused(result)

    def test_embedding_and_metadata_memory_limits(self):
        result = self.verified()
        for setting in ("MAX_EMBED_BYTES", "MAX_METADATA_BYTES"):
            with self.subTest(setting=setting), mock.patch.object(viewer, setting, 1):
                self.assert_refused(result)

    def test_explicit_video_is_hashed_but_never_embedded_or_decoded(self):
        path = self.package / "explicit-short.mp4"
        path.write_bytes(b"FAKE VIDEO TEST BYTES; NOT A DECODABLE VIDEO")
        self.expected["additionalAssets"] = [digest(path)]
        result = self.verified()
        page = viewer.build_package_html(self.package, result)
        self.assertFalse(Document(page).attrs("video"))
        self.assertIn("동영상 1개는 파일 해시 대조만", page)
        path.write_bytes(b"changed")
        self.assert_refused(result)

    def test_package_helper_preserves_all_input_bytes(self):
        before = {path.name: path.read_bytes() for path in self.package.iterdir()}
        viewer.build_package_html(self.package, self.verified())
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.package.iterdir()})

    def test_package_cli_success_existing_file_and_inside_input_output(self):
        output = self.root / "review.html"
        result = self.command(*self.package_args(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["visualAccepted"])
        original = output.read_bytes()
        self.assertEqual(self.command(*self.package_args(output)).returncode, 2)
        self.assertEqual(output.read_bytes(), original)
        for path in (self.package / "new.html", self.package / "nested/new.html", self.root / "wrong.txt"):
            with self.subTest(path=path):
                self.assertEqual(self.command(*self.package_args(path)).returncode, 2)
                self.assertFalse(path.exists())

    def test_invalid_package_cli_creates_no_output(self):
        (self.package / "frame-0133.png").write_bytes(b"bad")
        output = self.root / "failed.html"
        result = self.command(*self.package_args(output))
        self.assertEqual(result.returncode, 2)
        self.assertFalse(output.exists())

    def test_cli_modes_are_complete_and_mutually_exclusive(self):
        output = self.root / "never.html"
        variants = [["--a", self.package], ["--package", self.package], ["--expectations", self.expectation_file],
                    ["--a", self.package, "--b", self.package, "--expectations", self.expectation_file],
                    ["--package", self.package, "--expectations", self.expectation_file, "--b", self.package],
                    ["--a", self.package, "--package", self.package]]
        for variant in variants:
            with self.subTest(variant=variant):
                self.assertEqual(self.command(*variant, "--output", output).returncode, 2)
                self.assertFalse(output.exists())

    def test_expectations_duplicate_keys_rejected_without_output(self):
        raw = self.expectation_file.read_text(encoding="utf-8")
        self.expectation_file.write_text('{"mode":"prepare",' + raw.lstrip()[1:], encoding="utf-8")
        output = self.root / "never.html"
        self.assertEqual(self.command(*self.package_args(output)).returncode, 2)
        self.assertFalse(output.exists())

    def test_expectation_file_change_after_verification_refuses_output(self):
        original = viewer.build_package_html
        def changed(package, result):
            page = original(package, result)
            self.expectation_file.write_bytes(self.expectation_file.read_bytes() + b" ")
            return page
        output = self.root / "never.html"
        with mock.patch.object(sys, "argv", ["viewer", *map(str, self.package_args(output))]), \
             mock.patch.object(viewer, "build_package_html", side_effect=changed), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(viewer.main(), 2)
        self.assertFalse(output.exists())

    def test_existing_ab_helper_cli_and_toctou_guard_are_preserved(self):
        a, b = self.root / "old-a", self.root / "old-b"
        make_run(a, "baseline")
        make_run(b, "contrast_material_v1")
        comparison = compare_runs(a, b)
        self.assertIs(comparison["comparable"], True, comparison["failures"])
        page = viewer.build_html(a, b, comparison)
        self.assertEqual(len(Document(page).attrs("img")), 6)
        output = self.root / "ab.html"
        command = self.command("--a", a, "--b", b, "--output", output)
        self.assertEqual(command.returncode, 0, command.stderr)
        self.assertIs(json.loads(command.stdout)["comparable"], True)
        self.assertEqual(output.read_text(encoding="utf-8"), page)
        asset = b / "frame-0133.png"
        asset.write_bytes(asset.read_bytes() + b"changed")
        with self.assertRaises((ValueError, Invalid)):
            viewer.build_html(a, b, comparison)


if __name__ == "__main__":
    unittest.main()
