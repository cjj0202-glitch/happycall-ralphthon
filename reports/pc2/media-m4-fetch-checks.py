"""Offline M4 fetch evidence: standard library, synthetic bytes, no downloads.

Run: python reports/pc2/media-m4-fetch-checks.py
This is independently executed unittest coverage, not a pytest run.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import fetch_demo_media as media


def sha(data):
    return hashlib.sha256(data).hexdigest()


class FetchChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pc2-m4-fetch-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.dest = self.base / "public" / "demo"
        self.backup = self.base / "private" / "backups"
        self.old = {n: ("old synthetic " + n).encode() for n in media.NAMES}
        self.new = {n: ("new synthetic " + n).encode() for n in media.NAMES}
        # Descriptor contract deliberately makes no payload-schema assumption.
        self.new[media.TRACKS_NAME] = b"opaque synthetic tracks payload"
        self.manifest = {"schemaVersion": 1, "repository": media.REPOSITORY,
                         "releaseTag": "demo-media-20260922-v4", "assets": []}
        for name in media.NAMES:
            self.manifest["assets"].append({
                "name": name, "bytes": len(self.new[name]), "sha256": sha(self.new[name]),
                "synthetic": True, "sourceBytes": len(self.old[name]),
                "sourceSha256": sha(self.old[name]),
            })
        self.manifest["assets"][2]["tracks"] = {
            "schemaVersion": "oneflow-cctv-tracks-v1", "url": "/demo/sorter-demo.tracks.json",
            "bytes": len(self.new[media.TRACKS_NAME]), "sha256": sha(self.new[media.TRACKS_NAME]),
            "videoSha256": sha(self.new[media.NAMES[2]]),
        }
        self.calls = []

    def download(self, name, target):
        self.calls.append(name)
        (target / name).write_bytes(self.new[name])

    def fetch(self, **kwargs):
        return media.fetch(media.validate_manifest(self.manifest), self.dest,
                           release_tag=self.manifest["releaseTag"], backup_root=self.backup,
                           downloader=kwargs.pop("downloader", self.download), **kwargs)

    def install_old(self):
        self.dest.mkdir(parents=True)
        for name, payload in self.old.items():
            (self.dest / name).write_bytes(payload)

    def assert_old(self):
        self.assertEqual({n: (self.dest / n).read_bytes() for n in self.old}, self.old)

    def test_01_legacy_three_manifest_and_self_test(self):
        self.manifest["assets"][2].pop("tracks")
        self.manifest["releaseTag"] = media.RELEASE_TAG
        self.assertEqual(len(media.validate_manifest(self.manifest)), 3)
        self.assertEqual(media.self_test()["checks"], 8)

    def test_02_four_assets_fresh_install_and_idempotence(self):
        result = self.fetch()
        self.assertEqual(result["downloaded"], [*media.NAMES, media.TRACKS_NAME])
        self.assertEqual({n: (self.dest / n).read_bytes() for n in self.new}, self.new)
        times = {n: (self.dest / n).stat().st_mtime_ns for n in self.new}
        self.calls.clear()
        self.assertEqual(self.fetch()["downloaded"], [])
        self.assertEqual(self.calls, [])
        self.assertEqual(times, {n: (self.dest / n).stat().st_mtime_ns for n in self.new})

    def test_03_verify_only_never_creates_or_downloads(self):
        result = self.fetch(verify_only=True)
        self.assertEqual(result["missing"], [*media.NAMES, media.TRACKS_NAME])
        self.assertFalse(self.dest.exists())
        self.assertEqual(self.calls, [])

    def test_04_three_media_upgrade_and_new_sidecar_backup(self):
        self.install_old()
        result = self.fetch(upgrade_approved=True)
        saved = Path(result["backupDirectory"])
        self.assertEqual(result["upgraded"], list(media.NAMES))
        self.assertEqual({n: (saved / n).read_bytes() for n in self.old}, self.old)
        self.assertEqual({n: (self.dest / n).read_bytes() for n in self.new}, self.new)
        record = json.loads((saved / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(record["releaseTag"], "demo-media-20260922-v4")
        self.assertEqual(record["status"], "complete")
        self.assertFalse(saved.is_relative_to(self.dest))

    def test_05_changed_sidecar_refused_before_writes(self):
        self.install_old()
        sidecar = self.dest / media.TRACKS_NAME
        sidecar.write_bytes(b"earlier sidecar")
        with self.assertRaisesRegex(ValueError, "No approved source"):
            self.fetch(upgrade_approved=True)
        self.assert_old()
        self.assertEqual(sidecar.read_bytes(), b"earlier sidecar")
        self.assertFalse(self.backup.exists())
        self.assertEqual(self.calls, [])

    def test_06_mp4_unknown_source_is_preserved(self):
        self.install_old()
        video = self.dest / media.NAMES[2]
        video.write_bytes(b"unknown synthetic video")
        with self.assertRaises(ValueError):
            self.fetch(upgrade_approved=True)
        self.assertEqual(video.read_bytes(), b"unknown synthetic video")
        self.assertEqual(self.calls, [])
        self.assertFalse(self.backup.exists())

    def test_07_mp4_requires_source_and_synthetic_proof(self):
        self.install_old()
        for field, value in (("sourceBytes", True), ("sourceBytes", 0),
                             ("sourceSha256", ""), ("sourceSha256", "f" * 64),
                             ("synthetic", False)):
            with self.subTest(field=field, value=value):
                original = copy.deepcopy(self.manifest)
                self.manifest["assets"][2][field] = value
                with self.assertRaises(ValueError):
                    self.fetch(upgrade_approved=True)
                self.assert_old()
                self.assertEqual(self.calls, [])
                self.manifest = original

    def test_08_corrupt_fourth_prevents_every_replacement(self):
        self.install_old()
        def corrupt(name, target):
            self.download(name, target)
            if name == media.TRACKS_NAME:
                (target / name).write_bytes(b"x" * len(self.new[name]))
        with self.assertRaisesRegex(ValueError, "verification"):
            self.fetch(upgrade_approved=True, downloader=corrupt)
        self.assert_old()
        self.assertFalse((self.dest / media.TRACKS_NAME).exists())
        self.assertFalse((self.backup / ".upgrade.lock").exists())

    def test_09_offline_partial_download_keeps_originals(self):
        self.install_old()
        def offline(name, target):
            if name == media.NAMES[2]:
                raise OSError("simulated offline")
            self.download(name, target)
        with self.assertRaisesRegex(ValueError, "simulated offline"):
            self.fetch(upgrade_approved=True, downloader=offline)
        self.assert_old()
        self.assertFalse((self.dest / media.TRACKS_NAME).exists())
        self.assertEqual(self.fetch(upgrade_approved=True)["upgraded"], list(media.NAMES))

    def test_10_sidecar_publish_failure_keeps_all_original_backups(self):
        self.install_old()
        real_move = media.move_no_replace
        def fail(source, target):
            if source.parent.name == "downloads" and target.name == media.TRACKS_NAME:
                raise OSError("simulated sidecar publish failure")
            return real_move(source, target)
        with patch.object(media, "move_no_replace", fail):
            with self.assertRaisesRegex(ValueError, "publish failure"):
                self.fetch(upgrade_approved=True)
        journal = next(self.backup.glob("*/result.json"))
        record = json.loads(journal.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["installed"], list(media.NAMES))
        self.assertEqual({n: (journal.parent / n).read_bytes() for n in self.old}, self.old)
        self.assertFalse((self.dest / media.TRACKS_NAME).exists())
        self.assertEqual(self.fetch(upgrade_approved=True)["downloaded"], [media.TRACKS_NAME])

    def test_11_direct_list_escape_and_unregistered_sidecar_rejected(self):
        flat = media.validate_manifest(self.manifest)
        variants = []
        escaped = copy.deepcopy(flat)
        escaped[0]["name"] = "../escape.wav"
        variants.append(escaped)
        unbound = copy.deepcopy(flat)
        unbound[2].pop("tracks")
        variants.append(unbound)
        mismatched = copy.deepcopy(flat)
        mismatched[-1]["sha256"] = "f" * 64
        variants.append(mismatched)
        variants.append([*copy.deepcopy(flat), copy.deepcopy(flat[-1])])
        for assets in variants:
            with self.subTest(names=[a["name"] for a in assets]):
                with self.assertRaises(ValueError):
                    media.fetch(assets, self.dest, downloader=self.download)
        self.assertFalse(self.dest.exists())
        self.assertEqual(self.calls, [])

    def test_12_descriptor_contract_rejects_invalid_boundaries(self):
        invalid = [("schemaVersion", "other"), ("url", "https://example.invalid/evil"),
                   ("url", "/demo/../sidecar.json"), ("bytes", 0), ("bytes", True),
                   ("bytes", 10000001), ("sha256", "A" * 64), ("videoSha256", "f" * 64)]
        for field, value in invalid:
            with self.subTest(field=field, value=value):
                changed = copy.deepcopy(self.manifest)
                changed["assets"][2]["tracks"][field] = value
                with self.assertRaises(ValueError):
                    media.validate_manifest(changed)

    def test_13_raw_three_with_nested_tracks_expands(self):
        result = media.fetch(self.manifest["assets"], self.dest, downloader=self.download,
                             release_tag="demo-media-20260922-v4")
        self.assertEqual(result["downloaded"], [*media.NAMES, media.TRACKS_NAME])

    def test_14_cli_uses_selected_manifest_release_tag(self):
        manifest_path = self.base / "manifest.json"
        manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")
        observed = []
        def fake_run(argv, **kwargs):
            observed.append(argv)
            name = argv[argv.index("--pattern") + 1]
            target = Path(argv[argv.index("--dir") + 1])
            (target / name).write_bytes(self.new[name])
        with patch.object(media, "MANIFEST", manifest_path), patch.object(media, "DESTINATION", self.dest), \
             patch.object(sys, "argv", ["fetch_demo_media.py"]), \
             patch.object(media.subprocess, "run", fake_run), patch("sys.stdout", io.StringIO()):
            self.assertEqual(media.main(), 0)
        self.assertEqual(len(observed), 4)
        self.assertTrue(all(a[:4] == ["gh", "release", "download", "demo-media-20260922-v4"] for a in observed))

    def test_15_unapproved_tag_or_name_never_calls_subprocess(self):
        with patch.object(media.subprocess, "run") as run:
            for name, tag in (("../bad", media.RELEASE_TAG), (media.NAMES[0], "arbitrary-tag")):
                with self.assertRaises(ValueError):
                    media.download(name, self.dest, release_tag=tag)
            run.assert_not_called()

    def test_16_default_upgrade_refused_no_backups(self):
        self.install_old()
        with self.assertRaisesRegex(ValueError, "Existing asset differs"):
            self.fetch()
        self.assert_old()
        self.assertFalse(self.backup.exists())
        self.assertEqual(self.calls, [])

    def test_17_current_media_missing_sidecar_only_downloads_sidecar(self):
        self.dest.mkdir(parents=True)
        for name in media.NAMES:
            (self.dest / name).write_bytes(self.new[name])
        result = self.fetch(upgrade_approved=True)
        self.assertEqual(result["downloaded"], [media.TRACKS_NAME])
        self.assertEqual(result["upgraded"], [])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FetchChecks)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"suite": "M4 synthetic fetch unittest", "executed": result.testsRun,
                      "failed": len(result.failures), "errors": len(result.errors),
                      "skipped": len(result.skipped), "networkCalls": 0,
                      "pytestExecuted": False}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
