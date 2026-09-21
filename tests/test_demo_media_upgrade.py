"""Temporary files and injected downloads only: never network/public media."""
import hashlib
import json
import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts import fetch_demo_media as media


@pytest.fixture
def setup(tmp_path):
    old = {name: ("old " + name).encode() for name in media.NAMES[:2]}
    new = {name: ("new " + name).encode() for name in media.NAMES}
    assets = []
    for name, payload in new.items():
        item = {"name": name, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(), "synthetic": True}
        if name in old:
            item.update(sourceBytes=len(old[name]), sourceSha256=hashlib.sha256(old[name]).hexdigest())
        assets.append(item)
    dest, backups = tmp_path / "public" / "demo", tmp_path / "private" / "backups"
    dest.mkdir(parents=True)
    for name in media.NAMES:
        (dest / name).write_bytes(old.get(name, new[name]))
    calls = []

    def download(name, target):
        calls.append(name)
        (target / name).write_bytes(new[name])

    def run(**kwargs):
        return media.fetch(assets, dest, upgrade_approved=True, backup_root=backups,
                           downloader=kwargs.pop("downloader", download), **kwargs)
    return assets, old, new, dest, backups, calls, download, run


def test_approved_upgrade_preserves_exact_bytes_and_is_idempotent(setup):
    assets, old, new, dest, backups, calls, download, run = setup
    result = run()
    assert result["upgraded"] == list(old) and calls == list(old)
    saved = Path(result["backupDirectory"])
    assert saved.is_relative_to(backups) and not saved.is_relative_to(dest)
    assert {name: (saved / name).read_bytes() for name in old} == old
    assert {name: (dest / name).read_bytes() for name in new} == new
    assert json.loads((saved / "result.json").read_text())["status"] == "complete"
    times = {name: (dest / name).stat().st_mtime_ns for name in new}
    result = run(downloader=Mock(side_effect=AssertionError("unexpected download")))
    assert result["upgraded"] == []
    assert times == {name: (dest / name).stat().st_mtime_ns for name in new}


def test_default_still_refuses_known_old_file_without_writes(setup):
    assets, old, new, dest, backups, calls, download, run = setup
    with pytest.raises(ValueError, match="Existing asset differs"):
        media.fetch(assets, dest, downloader=download)
    assert not calls and not backups.exists()
    assert (dest / media.NAMES[0]).read_bytes() == old[media.NAMES[0]]


@pytest.mark.parametrize("field,value", [("sourceBytes", None), ("sourceBytes", True),
    ("sourceBytes", 0), ("sourceBytes", 999), ("sourceSha256", ""),
    ("sourceSha256", "0" * 64), ("synthetic", False)])
def test_source_metadata_must_match_exactly(setup, field, value):
    assets, old, new, dest, backups, calls, download, run = setup
    assets[0][field] = value
    with pytest.raises(ValueError):
        run()
    assert not calls and not backups.exists()
    assert (dest / media.NAMES[0]).read_bytes() == old[media.NAMES[0]]


@pytest.mark.parametrize("name", media.NAMES)
def test_unknown_existing_file_is_preserved_before_any_download(setup, name):
    assets, old, new, dest, backups, calls, download, run = setup
    payload = b"unknown content"
    (dest / name).write_bytes(payload)
    with pytest.raises(ValueError):
        run()
    assert (dest / name).read_bytes() == payload and not calls


def test_download_corruption_prevents_every_replacement(setup):
    assets, old, new, dest, backups, calls, download, run = setup
    def damaged(name, target):
        download(name, target)
        if name == media.NAMES[1]:
            (target / name).write_bytes(b"x" * len(new[name]))
    with pytest.raises(ValueError, match="verification"):
        run(downloader=damaged)
    assert all((dest / name).read_bytes() == value for name, value in old.items())
    assert not list(backups.glob("*/CASE-*.wav"))
    assert not (backups / ".upgrade.lock").exists()


def test_network_failure_preserves_originals_and_retry_works(setup):
    assets, old, new, dest, backups, calls, download, run = setup
    with pytest.raises(ValueError, match="offline"):
        run(downloader=Mock(side_effect=OSError("offline")))
    assert all((dest / name).read_bytes() == value for name, value in old.items())
    assert run()["upgraded"] == list(old)


def test_changed_original_during_download_is_never_overwritten(setup):
    assets, old, new, dest, backups, calls, download, run = setup
    def competing(name, target):
        download(name, target)
        (dest / media.NAMES[0]).write_bytes(b"other worker")
    with pytest.raises(ValueError, match="changed during download"):
        run(downloader=competing)
    assert (dest / media.NAMES[0]).read_bytes() == b"other worker"
    assert (dest / media.NAMES[1]).read_bytes() == old[media.NAMES[1]]


def test_second_publish_failure_keeps_first_new_and_restores_second(setup, monkeypatch):
    assets, old, new, dest, backups, calls, download, run = setup
    real_move = media.move_no_replace
    def fail(source, target):
        if source.parent.name == "downloads" and target.name == media.NAMES[1]:
            raise OSError("injected publish failure")
        return real_move(source, target)
    monkeypatch.setattr(media, "move_no_replace", fail)
    with pytest.raises(ValueError, match="publish failure"):
        run()
    assert (dest / media.NAMES[0]).read_bytes() == new[media.NAMES[0]]
    assert (dest / media.NAMES[1]).read_bytes() == old[media.NAMES[1]]
    saved = next(backups.glob("*/result.json"))
    assert json.loads(saved.read_text())["installed"] == [media.NAMES[0]]
    assert all((saved.parent / name).read_bytes() == value for name, value in old.items())
    monkeypatch.setattr(media, "move_no_replace", real_move)
    assert run()["upgraded"] == [media.NAMES[1]]


def test_competing_file_after_capture_is_preserved_with_backups(setup, monkeypatch):
    assets, old, new, dest, backups, calls, download, run = setup
    real_move = media.move_no_replace
    def race(source, target):
        if source.parent.name == "downloads" and target.name == media.NAMES[0]:
            target.write_bytes(b"raced writer")
        return real_move(source, target)
    monkeypatch.setattr(media, "move_no_replace", race)
    with pytest.raises(ValueError):
        run()
    assert (dest / media.NAMES[0]).read_bytes() == b"raced writer"
    saved = next(backups.glob("*/result.json")).parent
    assert (saved / media.NAMES[0]).read_bytes() == old[media.NAMES[0]]
    assert (saved / (media.NAMES[0] + ".captured")).read_bytes() == old[media.NAMES[0]]


def test_competing_original_at_capture_is_restored_not_lost(setup, monkeypatch):
    assets, old, new, dest, backups, calls, download, run = setup
    real_move = media.move_no_replace
    def race(source, target):
        if source.parent == dest and source.name == media.NAMES[0]:
            source.write_bytes(b"last second change")
        return real_move(source, target)
    monkeypatch.setattr(media, "move_no_replace", race)
    with pytest.raises(ValueError, match="changed at capture"):
        run()
    assert (dest / media.NAMES[0]).read_bytes() == b"last second change"
    saved = next(backups.glob("*/result.json")).parent
    assert (saved / media.NAMES[0]).read_bytes() == old[media.NAMES[0]]


def test_missing_asset_and_partial_previous_upgrade(setup):
    assets, old, new, dest, backups, calls, download, run = setup
    (dest / media.NAMES[0]).write_bytes(new[media.NAMES[0]])
    (dest / media.NAMES[2]).unlink()
    result = run()
    assert result["upgraded"] == [media.NAMES[1]]
    assert result["downloaded"] == list(media.NAMES[1:])


def test_staging_change_before_publish_restores_original(setup, monkeypatch):
    assets, old, new, dest, backups, calls, download, run = setup
    original = media.move_no_replace
    def modify_staged(source, target):
        result = original(source, target)
        if target.name == media.NAMES[0] + ".captured":
            (target.parent / "downloads" / media.NAMES[0]).write_bytes(b"changed staged bytes")
        return result
    monkeypatch.setattr(media, "move_no_replace", modify_staged)
    with pytest.raises(ValueError, match="Staged asset changed"):
        run()
    assert (dest / media.NAMES[0]).read_bytes() == old[media.NAMES[0]]


def test_missing_path_appearing_during_download_is_not_overwritten(setup):
    assets, old, new, dest, backups, calls, download, run = setup
    missing_name = media.NAMES[2]
    (dest / missing_name).unlink()
    def competing(name, target):
        download(name, target)
        if name == missing_name:
            (dest / missing_name).write_bytes(b"new external file")
    with pytest.raises(ValueError):
        run(downloader=competing)
    assert (dest / missing_name).read_bytes() == b"new external file"


def test_invalid_asset_name_cannot_escape_destination(setup):
    assets, old, new, dest, backups, calls, download, run = setup
    assets[0]["name"] = "../escape.wav"
    with pytest.raises(ValueError, match="exactly"):
        run()
    assert not calls and not backups.exists()


def test_active_or_crash_lock_is_not_removed(setup):
    assets, old, new, dest, backups, calls, download, run = setup
    lock = backups / ".upgrade.lock"
    lock.mkdir(parents=True)
    (lock / "owner.json").write_text("external owner")
    with pytest.raises(ValueError, match="inspect before retry"):
        run()
    assert (lock / "owner.json").read_text() == "external owner"
    assert not calls


@pytest.mark.parametrize("relative", [".", "backups", "../demo/backups"])
def test_backup_under_destination_is_rejected(setup, relative):
    assets, old, new, dest, backups, calls, download, run = setup
    with pytest.raises(ValueError, match="outside"):
        media.fetch(assets, dest, upgrade_approved=True, backup_root=dest / relative, downloader=download)
    assert not calls


def test_hardlinked_asset_rejected_and_preserved(setup, tmp_path):
    assets, old, new, dest, backups, calls, download, run = setup
    linked = tmp_path / "linked.wav"
    os.link(dest / media.NAMES[0], linked)
    with pytest.raises(ValueError, match="Linked"):
        run()
    assert linked.read_bytes() == old[media.NAMES[0]] and not calls


def test_reparse_ancestor_is_rejected_without_writes(setup, monkeypatch):
    assets, old, new, dest, backups, calls, download, run = setup
    original = media.is_link
    monkeypatch.setattr(media, "is_link", lambda p: p == dest.parent or original(p))
    with pytest.raises(ValueError, match="Linked"):
        run()
    assert not calls and not backups.exists()


def test_symbolic_asset_rejected_when_supported(setup, tmp_path):
    assets, old, new, dest, backups, calls, download, run = setup
    original = tmp_path / "outside.wav"
    original.write_bytes(old[media.NAMES[0]])
    asset = dest / media.NAMES[0]
    asset.unlink()
    try:
        asset.symlink_to(original)
    except OSError as exc:
        pytest.skip(f"Physical symlink unavailable on this host: {exc}")
    with pytest.raises(ValueError, match="Linked"):
        run()
    assert asset.is_symlink() and original.read_bytes() == old[media.NAMES[0]]
    assert not calls


def test_junction_attribute_detector_without_platform_privileges(tmp_path, monkeypatch):
    from types import SimpleNamespace
    info = SimpleNamespace(st_mode=0o040755, st_nlink=1, st_file_attributes=0x400)
    monkeypatch.setattr(Path, "lstat", lambda self: info)
    assert media.is_link(tmp_path / "junction") is True


def test_verify_mode_cannot_upgrade(setup):
    with pytest.raises(ValueError, match="cannot be combined"):
        setup[-1](verify_only=True)


def test_original_self_test_still_passes():
    assert media.self_test()["checks"] == 8


def load_mutant(old, new):
    text = Path(media.__file__).read_text(encoding="utf-8")
    assert text.count(old) == 1
    namespace = {"__name__": "media_mutant", "__file__": media.__file__}
    exec(compile(text.replace(old, new), "<isolated media mutant>", "exec"), namespace)
    return namespace


def test_mutation_source_gate_removal_is_detected_before_network(setup):
    assets, old, new, dest, backups, calls, download, run = setup
    mutant = load_mutant("if not verify(path, source):", "if False:")
    (dest / media.NAMES[0]).write_bytes(b"unknown")
    try:
        mutant["fetch"](assets, dest, upgrade_approved=True, backup_root=backups, downloader=download)
    except ValueError:
        pass
    # The unchanged baseline oracle requires zero downloads for unknown files.
    assert calls, "Mutant survived: test did not distinguish the removed source gate"


def test_mutation_initial_download_verification_removal_is_detected(setup):
    assets, old, new, dest, backups, calls, download, run = setup
    anchor = 'for asset in needed:\n            downloader(asset["name"], staging)\n            if not verify(staging / asset["name"], asset):'
    mutant = load_mutant(anchor, anchor.replace('if not verify(staging / asset["name"], asset):', 'if False:'))
    def damaged(name, target):
        (target / name).write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        mutant["fetch"](assets, dest, upgrade_approved=True, backup_root=backups, downloader=damaged)
    # Baseline corruption test requires no source backups before all candidates pass.
    assert list(backups.glob("*/CASE-*.wav")), "Mutant survived download-before-backup oracle"


def test_mutation_overwrite_publish_is_detected(setup):
    assets, old, new, dest, backups, calls, download, run = setup
    mutant = load_mutant('os.rename(source, target)  # Windows rename fails if target exists.',
                         'os.replace(source, target)  # deliberately unsafe mutant')
    if os.name != "nt":
        pytest.skip("This mutant specifically targets Windows rename semantics")
    original = mutant["move_no_replace"]
    def competing(source, target):
        if source.parent.name == "downloads" and target.name == media.NAMES[0]:
            target.write_bytes(b"raced writer")
        return original(source, target)
    mutant["move_no_replace"] = competing
    mutant["fetch"](assets, dest, upgrade_approved=True, backup_root=backups, downloader=download)
    assert (dest / media.NAMES[0]).read_bytes() != b"raced writer", "Mutant survived preservation oracle"


def test_mutation_overstrict_source_gate_rejects_positive_control(setup):
    assets, old, new, dest, backups, calls, download, run = setup
    mutant = load_mutant('asset["name"] not in NAMES[:2]', 'asset["name"] in NAMES[:2]')
    with pytest.raises(ValueError, match="No approved source"):
        mutant["fetch"](assets, dest, upgrade_approved=True, backup_root=backups, downloader=download)
    assert not calls  # Baseline positive-control oracle requires successful two-WAV upgrade.
