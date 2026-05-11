import json
from pathlib import Path

import pytest

from vostok_vault.repair import create_repaired_backup, detect_orphaned_items
from vostok_vault.tres_parser import strip_orphaned_blocks

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_ITEMS_DB = [{"id": "MP5K"}, {"id": "Medkit"}, {"id": "Ammo_223"}]

CHAR_TRES_MIXED = """\
[gd_resource type="Resource" script_class="CharacterSave" format=3]
[ext_resource type="Script" path="res://Scripts/SlotData.gd" id="script_ext"]
[ext_resource type="Resource" path="res://Items/Weapons/MP5K/MP5K.tres" id="vanilla_ext"]
[ext_resource type="Resource" path="res://Items/Weapons/ModGun/ModGun.tres" id="mod_ext"]
[sub_resource type="Resource" id="slot_vanilla"]
script = ExtResource("script_ext")
itemData = ExtResource("vanilla_ext")
condition = 90
amount = 1
slot = "Primary"
[sub_resource type="Resource" id="slot_mod"]
script = ExtResource("script_ext")
itemData = ExtResource("mod_ext")
condition = 80
amount = 1
slot = "Secondary"
[resource]
script = ExtResource("script_ext")
slots = Array[SubResource("SlotData")]([SubResource("slot_vanilla"), SubResource("slot_mod")])
"""

CHAR_TRES_VANILLA_ONLY = """\
[gd_resource type="Resource" script_class="CharacterSave" format=3]
[ext_resource type="Script" path="res://Scripts/SlotData.gd" id="script_ext"]
[ext_resource type="Resource" path="res://Items/Weapons/MP5K/MP5K.tres" id="vanilla_ext"]
[sub_resource type="Resource" id="slot_vanilla"]
script = ExtResource("script_ext")
itemData = ExtResource("vanilla_ext")
condition = 90
amount = 1
slot = "Primary"
[resource]
script = ExtResource("script_ext")
slots = Array[SubResource("SlotData")]([SubResource("slot_vanilla")])
"""

CHAR_TRES_AMMO = """\
[gd_resource type="Resource" script_class="CharacterSave" format=3]
[ext_resource type="Script" path="res://Scripts/SlotData.gd" id="script_ext"]
[ext_resource type="Resource" path="res://Items/Ammo/Ammo_223/Ammo_223.tres" id="ammo_ext"]
[sub_resource type="Resource" id="slot_ammo"]
script = ExtResource("script_ext")
itemData = ExtResource("ammo_ext")
amount = 30
slot = "Pocket"
[resource]
script = ExtResource("script_ext")
slots = Array[SubResource("SlotData")]([SubResource("slot_ammo")])
"""

CHAR_TRES_TWO_SLOTS_SAME_EXT = """\
[gd_resource type="Resource" script_class="CharacterSave" format=3]
[ext_resource type="Script" path="res://Scripts/SlotData.gd" id="script_ext"]
[ext_resource type="Resource" path="res://Items/Weapons/ModGun/ModGun.tres" id="mod_ext"]
[sub_resource type="Resource" id="slot_mod_a"]
script = ExtResource("script_ext")
itemData = ExtResource("mod_ext")
condition = 90
amount = 1
slot = "Primary"
[sub_resource type="Resource" id="slot_mod_b"]
script = ExtResource("script_ext")
itemData = ExtResource("mod_ext")
condition = 60
amount = 1
slot = "Secondary"
[resource]
script = ExtResource("script_ext")
slots = Array[SubResource("SlotData")]([SubResource("slot_mod_a"), SubResource("slot_mod_b")])
"""

_MINIMAL_MANIFEST = {
    "id": "20240101_120000",
    "tag": "manual",
    "created": "2024-01-01T12:00:00",
    "active_mod_profile": None,
    "mods": [],
}


def _write_backup(path: Path, char_content: str, manifest: dict | None = None) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "Character.tres").write_text(char_content, encoding="utf-8")
    m = manifest if manifest is not None else _MINIMAL_MANIFEST
    (path / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Task 1 — detect_orphaned_items
# ---------------------------------------------------------------------------


def test_detect_finds_orphan(tmp_path: Path) -> None:
    _write_backup(tmp_path, CHAR_TRES_MIXED)
    result = detect_orphaned_items(tmp_path, FAKE_ITEMS_DB)
    assert result["total_slots"] == 1
    assert result["orphan_names"] == ["ModGun"]
    assert "Character.tres" in result["affected_files"]
    slot = result["affected_files"]["Character.tres"][0]
    assert slot["stem_name"] == "ModGun"
    assert slot["sub_id"] == "slot_mod"
    assert slot["ext_id"] == "mod_ext"


def test_detect_no_orphan(tmp_path: Path) -> None:
    _write_backup(tmp_path, CHAR_TRES_VANILLA_ONLY)
    result = detect_orphaned_items(tmp_path, FAKE_ITEMS_DB)
    assert result["total_slots"] == 0
    assert result["orphan_names"] == []


def test_detect_missing_file_skipped(tmp_path: Path) -> None:
    empty = tmp_path / "empty_backup"
    empty.mkdir()
    result = detect_orphaned_items(empty, FAKE_ITEMS_DB)
    assert result["total_slots"] == 0
    assert result["orphan_names"] == []
    assert result["affected_files"] == {}


def test_detect_vanilla_ammo_underscore(tmp_path: Path) -> None:
    _write_backup(tmp_path, CHAR_TRES_AMMO)
    result = detect_orphaned_items(tmp_path, FAKE_ITEMS_DB)
    assert result["total_slots"] == 0
    assert "Ammo 223" not in result["orphan_names"]


def test_detect_vanilla_survives(tmp_path: Path) -> None:
    _write_backup(tmp_path, CHAR_TRES_MIXED)
    result = detect_orphaned_items(tmp_path, FAKE_ITEMS_DB)
    assert "MP5K" not in result["orphan_names"]


# ---------------------------------------------------------------------------
# Task 2 — strip_orphaned_blocks
# ---------------------------------------------------------------------------

_EXT_LINE = '[ext_resource type="Resource" path="res://Items/Weapons/ModGun/ModGun.tres" id="mod_ext"]\n'
_SUB_HEADER = '[sub_resource type="Resource" id="orphan_sub"]\n'
_SUB_BODY_1 = 'itemData = ExtResource("mod_ext")\n'
_SUB_BODY_2 = "condition = 90\n"
_RESOURCE_HEADER = "[resource]\n"
_VANILLA_EXT = '[ext_resource type="Resource" path="res://Items/Weapons/MP5K/MP5K.tres" id="vanilla_ext"]\n'
_VANILLA_SUB_HEADER = '[sub_resource type="Resource" id="vanilla_sub"]\n'
_VANILLA_SUB_BODY = 'itemData = ExtResource("vanilla_ext")\n'
_GD_RESOURCE = '[gd_resource type="Resource" format=3]\n'


def test_strip_removes_ext_resource_line() -> None:
    lines = [_GD_RESOURCE, _EXT_LINE, _RESOURCE_HEADER, "something = 1\n"]
    result = strip_orphaned_blocks(
        lines, orphaned_ext_ids={"mod_ext"}, orphaned_sub_ids=set()
    )
    text = "".join(result)
    assert _EXT_LINE not in text
    assert "[gd_resource" in text
    assert "[resource]" in text


def test_strip_removes_sub_resource_block() -> None:
    lines = [
        _GD_RESOURCE,
        _SUB_HEADER,
        _SUB_BODY_1,
        _SUB_BODY_2,
        _RESOURCE_HEADER,
        "something = 1\n",
    ]
    result = strip_orphaned_blocks(
        lines, orphaned_ext_ids=set(), orphaned_sub_ids={"orphan_sub"}
    )
    text = "".join(result)
    assert "[sub_resource" not in text
    assert "itemData" not in text
    assert "[resource]" in text
    assert "something = 1" in text


def test_strip_partial_array_in_resource() -> None:
    lines = [
        _GD_RESOURCE,
        _RESOURCE_HEADER,
        'slots = Array[SubResource("SlotData")]([SubResource("vanilla"), SubResource("orphaned")])\n',
    ]
    result = strip_orphaned_blocks(
        lines, orphaned_ext_ids=set(), orphaned_sub_ids={"orphaned"}
    )
    text = "".join(result)
    assert 'SubResource("vanilla")' in text
    assert 'SubResource("orphaned")' not in text


def test_strip_partial_array_in_sub_resource_body() -> None:
    lines = [
        _GD_RESOURCE,
        '[sub_resource type="Resource" id="container_sub"]\n',
        'name = "Freezer"\n',
        'storage = Array[SubResource("SlotData")]([SubResource("vanilla"), SubResource("orphaned")])\n',
        _RESOURCE_HEADER,
    ]
    result = strip_orphaned_blocks(
        lines, orphaned_ext_ids=set(), orphaned_sub_ids={"orphaned"}
    )
    text = "".join(result)
    assert 'SubResource("vanilla")' in text
    assert 'SubResource("orphaned")' not in text
    assert "[sub_resource" in text


def test_strip_vanilla_survives() -> None:
    lines = [
        _GD_RESOURCE,
        _VANILLA_EXT,
        _VANILLA_SUB_HEADER,
        _VANILLA_SUB_BODY,
        "condition = 90\n",
        _RESOURCE_HEADER,
    ]
    result = strip_orphaned_blocks(
        lines, orphaned_ext_ids={"unrelated_ext"}, orphaned_sub_ids={"unrelated_sub"}
    )
    text = "".join(result)
    assert _VANILLA_EXT in text
    assert "[sub_resource" in text
    assert "vanilla_sub" in text
    assert _VANILLA_SUB_BODY in text


def test_strip_noop_empty_sets() -> None:
    lines = [
        _GD_RESOURCE,
        _VANILLA_EXT,
        _VANILLA_SUB_HEADER,
        _VANILLA_SUB_BODY,
        _RESOURCE_HEADER,
        "something = 1\n",
    ]
    result = strip_orphaned_blocks(
        lines, orphaned_ext_ids=set(), orphaned_sub_ids=set()
    )
    assert result == lines


# ---------------------------------------------------------------------------
# Task 3 — create_repaired_backup
# ---------------------------------------------------------------------------


def test_create_repaired_backup_nothing_to_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source_backup"
    _write_backup(source, CHAR_TRES_VANILLA_ONLY)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.repair.BACKUP_DIR", backup_dir)

    ok, reason = create_repaired_backup(source, FAKE_ITEMS_DB)
    assert ok is False
    assert reason == "nothing_to_repair"


def test_create_repaired_backup_cleans_nested_mod_attachment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Vanilla weapon with a modded scope in nested[] — scope ext_resource and
    its reference in nested must be removed even though it has no own sub_resource."""
    char_tres = """\
[gd_resource type="Resource" script_class="CharacterSave" format=3]
[ext_resource type="Script" path="res://Scripts/SlotData.gd" id="1"]
[ext_resource type="Resource" path="res://Items/Weapons/MP5K/MP5K.tres" id="vanilla_ext"]
[ext_resource type="Resource" path="res://Items/Attachments/Mod_Scope_FWE/Mod_Scope_FWE.tres" id="mod_scope"]
[ext_resource type="Script" path="res://Scripts/CharacterSave.gd" id="script"]
[sub_resource type="Resource" id="slot_vanilla"]
script = ExtResource("1")
itemData = ExtResource("vanilla_ext")
nested = Array[ExtResource("3")]([ExtResource("mod_scope")])
condition = 100
amount = 15
slot = "Primary"
[resource]
script = ExtResource("script")
inventory = Array[ExtResource("1")]([SubResource("slot_vanilla")])
"""
    source = tmp_path / "20240101_120000_manual"
    _write_backup(source, char_tres)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.repair.BACKUP_DIR", backup_dir)

    ok, reason = create_repaired_backup(source, FAKE_ITEMS_DB)
    assert ok is True

    repaired = list(backup_dir.iterdir())[0]
    repaired_text = (repaired / "Character.tres").read_text(encoding="utf-8")

    # mod scope ext_resource line removed
    assert "mod_scope" not in repaired_text
    # vanilla weapon sub_resource preserved
    assert "slot_vanilla" in repaired_text
    # vanilla weapon still has a nested line (empty array is fine)
    assert "nested = " in repaired_text


def test_create_repaired_backup_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "20240101_120000_manual"
    _write_backup(source, CHAR_TRES_MIXED)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.repair.BACKUP_DIR", backup_dir)

    ok, reason = create_repaired_backup(source, FAKE_ITEMS_DB)
    assert ok is True
    assert reason == "ok"

    repaired_dirs = list(backup_dir.iterdir())
    assert len(repaired_dirs) == 1
    repaired = repaired_dirs[0]
    assert "repaired" in repaired.name

    manifest = json.loads((repaired / "manifest.json").read_text(encoding="utf-8"))
    assert "repaired_from_id" in manifest
    assert manifest["repaired_from_id"] == _MINIMAL_MANIFEST["id"]
    assert manifest.get("original_tag") == _MINIMAL_MANIFEST["tag"]
    assert isinstance(manifest.get("removed_items"), list)
    assert len(manifest["removed_items"]) > 0

    source_char = (source / "Character.tres").read_text(encoding="utf-8")
    assert "mod_ext" in source_char

    repaired_char = (repaired / "Character.tres").read_text(encoding="utf-8")
    assert "mod_ext" not in repaired_char


def test_create_repaired_backup_source_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "20240101_120000_manual"
    _write_backup(source, CHAR_TRES_MIXED)
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("vostok_vault.repair.BACKUP_DIR", backup_dir)

    create_repaired_backup(source, FAKE_ITEMS_DB)

    source_char = (source / "Character.tres").read_text(encoding="utf-8")
    assert (
        '[ext_resource type="Resource" path="res://Items/Weapons/ModGun/ModGun.tres" id="mod_ext"]'
        in source_char
    )


# ---------------------------------------------------------------------------
# Task 8 — edge cases
# ---------------------------------------------------------------------------


def test_detect_same_ext_multiple_slots(tmp_path: Path) -> None:
    _write_backup(tmp_path, CHAR_TRES_TWO_SLOTS_SAME_EXT)
    result = detect_orphaned_items(tmp_path, FAKE_ITEMS_DB)
    assert result["total_slots"] == 2
    assert len(result["orphan_names"]) == 1
    assert result["orphan_names"] == ["ModGun"]


def test_strip_orphaned_nested_ext_refs_from_vanilla_weapon() -> None:
    """1c — vanilla weapon has a modded attachment in its nested array.
    The orphaned ExtResource should be removed from nested; vanilla weapon block kept."""
    lines = [
        _GD_RESOURCE,
        _VANILLA_EXT,
        '[ext_resource type="Resource" path="res://Items/Attachments/ModScope/ModScope.tres" id="mod_scope_ext"]\n',
        _VANILLA_SUB_HEADER,
        _VANILLA_SUB_BODY,
        'nested = Array[ExtResource("3")]([ExtResource("mod_scope_ext")])\n',
        "condition = 90\n",
        _RESOURCE_HEADER,
    ]
    result = strip_orphaned_blocks(
        lines,
        orphaned_ext_ids={"mod_scope_ext"},
        orphaned_sub_ids=set(),
    )
    text = "".join(result)
    # orphaned attachment removed from nested array
    assert 'ExtResource("mod_scope_ext")' not in text
    # nested line still present with empty array
    assert "nested = " in text
    # vanilla weapon block preserved
    assert _VANILLA_EXT in text
    assert "[sub_resource" in text
    assert _VANILLA_SUB_BODY in text


def test_strip_orphaned_nested_mixed_keeps_vanilla_attachment() -> None:
    """1b partial — vanilla weapon has one modded and one vanilla attachment in nested.
    Only the modded one should be removed; vanilla attachment ref stays."""
    lines = [
        _GD_RESOURCE,
        _VANILLA_EXT,
        '[ext_resource type="Resource" path="res://Items/Attachments/EXPS/EXPS.tres" id="vanilla_scope_ext"]\n',
        '[ext_resource type="Resource" path="res://Items/Attachments/ModScope/ModScope.tres" id="mod_scope_ext"]\n',
        _VANILLA_SUB_HEADER,
        _VANILLA_SUB_BODY,
        'nested = Array[ExtResource("3")]([ExtResource("vanilla_scope_ext"), ExtResource("mod_scope_ext")])\n',
        "condition = 90\n",
        _RESOURCE_HEADER,
    ]
    result = strip_orphaned_blocks(
        lines,
        orphaned_ext_ids={"mod_scope_ext"},
        orphaned_sub_ids=set(),
    )
    text = "".join(result)
    assert 'ExtResource("mod_scope_ext")' not in text
    assert 'ExtResource("vanilla_scope_ext")' in text
    assert "[sub_resource" in text


def test_strip_multiple_slots_same_ext() -> None:
    lines = [
        _GD_RESOURCE,
        '[ext_resource type="Resource" path="res://Items/Weapons/ModGun/ModGun.tres" id="mod_ext"]\n',
        '[sub_resource type="Resource" id="slot_mod_a"]\n',
        'itemData = ExtResource("mod_ext")\n',
        "condition = 90\n",
        '[sub_resource type="Resource" id="slot_mod_b"]\n',
        'itemData = ExtResource("mod_ext")\n',
        "condition = 60\n",
        _RESOURCE_HEADER,
        "something = 1\n",
    ]
    result = strip_orphaned_blocks(
        lines,
        orphaned_ext_ids={"mod_ext"},
        orphaned_sub_ids={"slot_mod_a", "slot_mod_b"},
    )
    text = "".join(result)
    assert "[ext_resource" not in text
    assert "slot_mod_a" not in text
    assert "slot_mod_b" not in text
    assert "[resource]" in text
    assert "something = 1" in text
