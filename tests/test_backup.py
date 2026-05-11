import json
from pathlib import Path

import pytest

from vostok_vault.backup import (
    create_backup,
    current_save_needs_backup,
    delete_backup,
    format_backup_date,
    list_backups,
    prune_auto_backups,
    prune_pre_restore_backups,
    rename_backup,
    restore_backup,
    sanitise_tag,
)

# ---------------------------------------------------------------------------
# rename_backup
# ---------------------------------------------------------------------------


def test_rename_backup_updates_tag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    d = backup_dir / "20240101_120000_manual"
    d.mkdir()
    (d / "manifest.json").write_text(
        json.dumps({"id": "x", "tag": "manual"}), encoding="utf-8"
    )

    assert rename_backup(d, "checkpoint") is True
    manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["tag"] == "checkpoint"


def test_rename_backup_missing_manifest(tmp_path: Path) -> None:
    d = tmp_path / "no_manifest"
    d.mkdir()
    assert rename_backup(d, "anything") is False


def test_rename_backup_corrupt_manifest(tmp_path: Path) -> None:
    d = tmp_path / "bad_manifest"
    d.mkdir()
    (d / "manifest.json").write_text("{ not json }", encoding="utf-8")
    assert rename_backup(d, "anything") is False


# ---------------------------------------------------------------------------
# format_backup_date
# ---------------------------------------------------------------------------


def test_format_backup_date_empty() -> None:
    assert format_backup_date("") == ""


def test_format_backup_date_today(monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import date

    import vostok_vault.backup as bk_mod

    today = date(2024, 6, 15)
    monkeypatch.setattr(
        bk_mod, "date", type("_FakeDate", (), {"today": staticmethod(lambda: today)})()
    )  # type: ignore[attr-defined]
    result = format_backup_date("2024-06-15T09:30:00")
    assert result.startswith("Today")
    assert "09:30" in result


def test_format_backup_date_yesterday(monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import date

    import vostok_vault.backup as bk_mod

    today = date(2024, 6, 15)
    monkeypatch.setattr(
        bk_mod, "date", type("_FakeDate", (), {"today": staticmethod(lambda: today)})()
    )  # type: ignore[attr-defined]
    result = format_backup_date("2024-06-14T22:00:00")
    assert result.startswith("Yesterday")
    assert "22:00" in result


def test_format_backup_date_older_date() -> None:
    result = format_backup_date("2023-01-05T14:30:00")
    assert "5" in result
    assert "Jan" in result
    assert "14:30" in result


def test_format_backup_date_invalid_falls_back() -> None:
    result = format_backup_date("not-a-date")
    assert result == "not-a-date"


def test_format_backup_date_utc_aware_converts_to_local() -> None:
    result = format_backup_date("2023-01-05T14:30:00+00:00")
    assert result != ""


# ---------------------------------------------------------------------------
# prune_auto_backups
# ---------------------------------------------------------------------------


def _make_backup_dir_with_tag(backup_dir: Path, name: str, tag: str) -> None:
    d = backup_dir / name
    d.mkdir()
    (d / "manifest.json").write_text(
        json.dumps({"id": name, "tag": tag}), encoding="utf-8"
    )


def test_prune_auto_backups_removes_oldest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    for i in range(7):
        _make_backup_dir_with_tag(backup_dir, f"2024010{i}_120000_auto", "auto")

    prune_auto_backups(max_count=5)

    remaining = sorted(d.name for d in backup_dir.iterdir() if d.is_dir())
    assert len(remaining) == 5
    assert remaining[0] == "20240102_120000_auto"


def test_prune_auto_backups_ignores_non_auto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    for i in range(6):
        _make_backup_dir_with_tag(backup_dir, f"2024010{i}_120000_auto", "auto")
    _make_backup_dir_with_tag(backup_dir, "20240107_120000_my_auto", "manual")

    prune_auto_backups(max_count=5)

    assert (backup_dir / "20240107_120000_my_auto").exists()


def test_prune_auto_backups_no_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", tmp_path / "missing")
    prune_auto_backups()


# ---------------------------------------------------------------------------
# prune_pre_restore_backups
# ---------------------------------------------------------------------------


def test_prune_pre_restore_backups_removes_oldest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    for i in range(5):
        _make_backup_dir_with_tag(
            backup_dir, f"2024010{i}_120000_pre_restore", "pre_restore"
        )

    prune_pre_restore_backups(max_count=3)

    remaining = [d for d in backup_dir.iterdir() if d.is_dir()]
    assert len(remaining) == 3


def test_prune_pre_restore_backups_ignores_suffix_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    for i in range(4):
        _make_backup_dir_with_tag(
            backup_dir, f"2024010{i}_120000_pre_restore", "pre_restore"
        )
    _make_backup_dir_with_tag(backup_dir, "20240105_120000_my_pre_restore", "manual")

    prune_pre_restore_backups(max_count=3)

    assert (backup_dir / "20240105_120000_my_pre_restore").exists()


# ---------------------------------------------------------------------------
# _sanitise_tag
# ---------------------------------------------------------------------------


def test_sanitise_tag_simple() -> None:
    assert sanitise_tag("manual") == "manual"


def test_sanitise_tag_spaces_become_underscores() -> None:
    assert sanitise_tag("my tag") == "my_tag"


def test_sanitise_tag_special_chars_removed() -> None:
    assert sanitise_tag("tag!@#$%") == "tag"


def test_sanitise_tag_empty_returns_fallback() -> None:
    assert sanitise_tag("") == "backup"


def test_sanitise_tag_only_special_chars_returns_fallback() -> None:
    assert sanitise_tag("!!!") == "backup"


def test_sanitise_tag_truncates_at_50() -> None:
    assert len(sanitise_tag("a" * 60)) == 50


def test_sanitise_tag_strips_leading_trailing_whitespace() -> None:
    assert sanitise_tag("  tag  ") == "tag"


def test_sanitise_tag_preserves_hyphens() -> None:
    assert sanitise_tag("pre-restore") == "pre-restore"


# ---------------------------------------------------------------------------
# list_backups
# ---------------------------------------------------------------------------


def test_list_backups_no_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", tmp_path / "nonexistent")
    assert list_backups() == []


def test_list_backups_empty_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)
    assert list_backups() == []


def test_list_backups_returns_manifests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    for name in ["20240101_120000_first", "20240102_120000_second"]:
        d = backup_dir / name
        d.mkdir()
        (d / "manifest.json").write_text(
            json.dumps({"id": name, "tag": "test", "game_day": 1}),
            encoding="utf-8",
        )

    results = list_backups()
    assert len(results) == 2


def test_list_backups_sorted_newest_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    for name in ["20240101_120000_alpha", "20240102_120000_beta"]:
        d = backup_dir / name
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps({"id": name}), encoding="utf-8")

    results = list_backups()
    assert results[0]["id"] == "20240102_120000_beta"


def test_list_backups_injects_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    d = backup_dir / "20240101_120000_solo"
    d.mkdir()
    (d / "manifest.json").write_text(json.dumps({"id": "solo"}), encoding="utf-8")

    result = list_backups()[0]
    assert "_path" in result
    assert result["_path"] == str(d)


def test_list_backups_ignores_dirs_without_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    (backup_dir / "orphan").mkdir()

    assert list_backups() == []


def test_list_backups_ignores_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    (backup_dir / "not_a_dir.json").write_text("{}", encoding="utf-8")

    assert list_backups() == []


# ---------------------------------------------------------------------------
# create_backup
# ---------------------------------------------------------------------------


def test_create_backup_no_save_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("vostok_vault.backup.SAVE_DIR", tmp_path / "missing_save")
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", tmp_path / "backups")
    assert create_backup("test") is None


def test_create_backup_returns_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_dir = tmp_path / "save"
    save_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.SAVE_DIR", save_dir)
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", tmp_path / "backups")

    result = create_backup("my_tag")
    assert result is not None
    assert result["tag"] == "my_tag"


def test_create_backup_writes_manifest_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_dir = tmp_path / "save"
    save_dir.mkdir()
    backup_dir = tmp_path / "backups"
    monkeypatch.setattr("vostok_vault.backup.SAVE_DIR", save_dir)
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    create_backup("check_manifest")

    folders = list(backup_dir.iterdir())
    assert len(folders) == 1
    assert (folders[0] / "manifest.json").exists()


def test_create_backup_copies_tracked_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_dir = tmp_path / "save"
    save_dir.mkdir()
    backup_dir = tmp_path / "backups"
    monkeypatch.setattr("vostok_vault.backup.SAVE_DIR", save_dir)
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    (save_dir / "World.tres").write_text("world_data", encoding="utf-8")

    create_backup("with_world")

    folders = list(backup_dir.iterdir())
    assert (folders[0] / "World.tres").read_text(encoding="utf-8") == "world_data"


def test_create_backup_manifest_has_required_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_dir = tmp_path / "save"
    save_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.SAVE_DIR", save_dir)
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", tmp_path / "backups")

    result = create_backup("keys_check")
    assert result is not None
    for key in (
        "id",
        "tag",
        "created",
        "game_day",
        "game_time",
        "season",
        "weather",
        "difficulty",
        "mods",
    ):
        assert key in result


# ---------------------------------------------------------------------------
# restore_backup
# ---------------------------------------------------------------------------


def test_restore_backup_missing_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_dir = tmp_path / "save"
    save_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.SAVE_DIR", save_dir)
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", tmp_path / "backups")

    assert restore_backup(tmp_path / "does_not_exist") is False


def test_restore_backup_copies_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_dir = tmp_path / "save"
    save_dir.mkdir()
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.SAVE_DIR", save_dir)
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    backup_path = backup_dir / "old_backup"
    backup_path.mkdir()
    (backup_path / "World.tres").write_text("restored_world", encoding="utf-8")

    result = restore_backup(backup_path)
    assert result is True
    assert (save_dir / "World.tres").read_text(encoding="utf-8") == "restored_world"


def test_restore_backup_rejects_path_outside_backup_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_dir = tmp_path / "save"
    save_dir.mkdir()
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.SAVE_DIR", save_dir)
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    outside = tmp_path / "outside_backup"
    outside.mkdir()

    assert restore_backup(outside) is False


def test_restore_backup_rejects_backup_dir_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_dir = tmp_path / "save"
    save_dir.mkdir()
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.SAVE_DIR", save_dir)
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    assert restore_backup(backup_dir) is False


# ---------------------------------------------------------------------------
# delete_backup
# ---------------------------------------------------------------------------


def test_delete_backup_missing_returns_false(tmp_path: Path) -> None:
    assert delete_backup(tmp_path / "nonexistent") is False


def test_delete_backup_removes_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    d = backup_dir / "20240101_120000_manual"
    d.mkdir()
    (d / "manifest.json").write_text("{}", encoding="utf-8")

    assert delete_backup(d) is True
    assert not d.exists()


def test_delete_backup_rejects_path_outside_backup_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    outside = tmp_path / "outside"
    outside.mkdir()

    assert delete_backup(outside) is False
    assert outside.exists()


def test_delete_backup_rejects_backup_dir_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    assert delete_backup(backup_dir) is False


# ---------------------------------------------------------------------------
# current_save_needs_backup
# ---------------------------------------------------------------------------


def test_current_save_needs_backup_no_save_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("vostok_vault.backup.SAVE_DIR", tmp_path / "missing")
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", tmp_path / "backups")
    assert current_save_needs_backup() is False


def test_current_save_needs_backup_no_tracked_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_dir = tmp_path / "save"
    save_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.SAVE_DIR", save_dir)
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", tmp_path / "backups")
    assert current_save_needs_backup() is False


def test_current_save_needs_backup_no_backups_yet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_dir = tmp_path / "save"
    save_dir.mkdir()
    (save_dir / "World.tres").write_text("data", encoding="utf-8")
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.SAVE_DIR", save_dir)
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)
    assert current_save_needs_backup() is True


def test_current_save_needs_backup_save_newer_than_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json
    import time

    save_dir = tmp_path / "save"
    save_dir.mkdir()
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.SAVE_DIR", save_dir)
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    d = backup_dir / "20240101_120000_manual"
    d.mkdir()
    (d / "manifest.json").write_text(
        json.dumps({"id": "old", "tag": "manual", "created": "2024-01-01T12:00:00"}),
        encoding="utf-8",
    )

    time.sleep(0.01)
    (save_dir / "World.tres").write_text("newer", encoding="utf-8")

    assert current_save_needs_backup() is True


def test_current_save_needs_backup_backup_is_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    save_dir = tmp_path / "save"
    save_dir.mkdir()
    (save_dir / "World.tres").write_text("data", encoding="utf-8")

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.SAVE_DIR", save_dir)
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    d = backup_dir / "20990101_120000_manual"
    d.mkdir()
    (d / "manifest.json").write_text(
        json.dumps({"id": "future", "tag": "manual", "created": "2099-01-01T12:00:00"}),
        encoding="utf-8",
    )

    assert current_save_needs_backup() is False


def test_current_save_needs_backup_ignores_pre_restore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    save_dir = tmp_path / "save"
    save_dir.mkdir()
    (save_dir / "World.tres").write_text("data", encoding="utf-8")

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.backup.SAVE_DIR", save_dir)
    monkeypatch.setattr("vostok_vault.backup.BACKUP_DIR", backup_dir)

    d = backup_dir / "20990101_120000_pre_restore"
    d.mkdir()
    (d / "manifest.json").write_text(
        json.dumps(
            {"id": "pr", "tag": "pre_restore", "created": "2099-01-01T12:00:00"}
        ),
        encoding="utf-8",
    )

    assert current_save_needs_backup() is True
