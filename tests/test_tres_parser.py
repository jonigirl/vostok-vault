from pathlib import Path

import pytest

from vostok_vault.tres_parser import (
    _is_item_path,
    parse_character,
    parse_storage,
    parse_traders,
    parse_validator,
    parse_world,
)

VALIDATOR_TRES = """\
[gd_resource type="Resource" script_class="ValidatorSave" format=3]
[ext_resource type="Script" path="res://Scripts/ValidatorSave.gd" id="1"]
[resource]
script = ExtResource("1")
ID = "Taikuri"
warning = "WARNING: Do not touch this file."
"""

WORLD_TRES = """\
[gd_resource type="Resource" script_class="WorldSave" format=3]
[ext_resource type="Script" path="res://Scripts/WorldSave.gd" id="1"]
[resource]
script = ExtResource("1")
difficulty = 1
season = 1
day = 3
time = 1956.337329382232
weather = "Neutral"
weatherTime = 380.3
shelters = 0
"""

CHARACTER_TRES = """\
[gd_resource type="Resource" script_class="CharacterSave" format=3]
[ext_resource type="Script" path="res://Scripts/SlotData.gd" id="1"]
[ext_resource type="Resource" path="res://Items/Weapons/MP5K/MP5K.tres" id="2"]
[ext_resource type="Script" path="res://Scripts/ItemData.gd" id="3"]
[ext_resource type="Script" path="res://Scripts/CharacterSave.gd" id="4"]
[sub_resource type="Resource" id="Resource_abc"]
script = ExtResource("1")
itemData = ExtResource("2")
nested = Array[ExtResource("3")]([])
storage = Array[ExtResource("1")]([])
condition = 91
amount = 30
position = 0.0
mode = 1
zoom = 1
chamber = true
casing = false
state = ""
gridPosition = Vector2(0, 0)
gridRotated = false
slot = "Secondary"
[resource]
script = ExtResource("4")
"""

STORAGE_TRES = """\
[gd_resource type="Resource" script_class="StorageSave" format=3]
[ext_resource type="Script" path="res://Scripts/SlotData.gd" id="1"]
[ext_resource type="Resource" path="res://Items/Medical/Medkit/Medkit.tres" id="2"]
[sub_resource type="Resource" id="Resource_xyz"]
script = ExtResource("1")
itemData = ExtResource("2")
condition = 75
amount = 5
[resource]
"""


def test_parse_world_missing_file(tmp_path: Path) -> None:
    result = parse_world(tmp_path / "missing.tres")
    assert result["day"] == "?"
    assert result["time_str"] == "??:??"
    assert result["season"] == "?"
    assert result["weather"] == "?"
    assert result["difficulty"] == "?"


def test_parse_world_returns_all_keys(tmp_path: Path) -> None:
    p = tmp_path / "World.tres"
    p.write_text(WORLD_TRES, encoding="utf-8")
    result = parse_world(p)
    assert set(result.keys()) == {
        "day",
        "time_str",
        "season",
        "weather",
        "difficulty",
        "shelters",
        "weather_time",
    }


def test_parse_world_day(tmp_path: Path) -> None:
    p = tmp_path / "World.tres"
    p.write_text(WORLD_TRES, encoding="utf-8")
    assert parse_world(p)["day"] == 3


def test_parse_world_weather(tmp_path: Path) -> None:
    p = tmp_path / "World.tres"
    p.write_text(WORLD_TRES, encoding="utf-8")
    assert parse_world(p)["weather"] == "Neutral"


def test_parse_world_season_and_difficulty(tmp_path: Path) -> None:
    p = tmp_path / "World.tres"
    p.write_text(WORLD_TRES, encoding="utf-8")
    result = parse_world(p)
    assert result["season"] == 1
    assert result["difficulty"] == 1


def test_parse_world_difficulty_ironman(tmp_path: Path) -> None:
    content = '[resource]\nday = 5\ntime = 3600.0\nseason = 2\ndifficulty = 3\nweather = "Clear"\n'
    p = tmp_path / "World.tres"
    p.write_text(content, encoding="utf-8")
    assert parse_world(p)["difficulty"] == 3


def test_parse_world_shelters(tmp_path: Path) -> None:
    p = tmp_path / "World.tres"
    p.write_text(WORLD_TRES, encoding="utf-8")
    assert parse_world(p)["shelters"] == 0


def test_parse_world_weather_time(tmp_path: Path) -> None:
    p = tmp_path / "World.tres"
    p.write_text(WORLD_TRES, encoding="utf-8")
    result = parse_world(p)
    assert result["weather_time"] == pytest.approx(380.3)


def test_parse_world_missing_shelters_and_weather_time(tmp_path: Path) -> None:
    content = '[resource]\nday = 1\ntime = 3600.0\nseason = 0\ndifficulty = 0\nweather = "Clear"\n'
    p = tmp_path / "World.tres"
    p.write_text(content, encoding="utf-8")
    result = parse_world(p)
    assert result["shelters"] is None
    assert result["weather_time"] is None


def test_parse_world_time_conversion(tmp_path: Path) -> None:
    # 1956 s = 0 h 32 m
    p = tmp_path / "World.tres"
    p.write_text(WORLD_TRES, encoding="utf-8")
    assert parse_world(p)["time_str"] == "00:32"


def test_parse_world_time_exact_hour(tmp_path: Path) -> None:
    # 7200 s = 02:00
    content = '[resource]\nday = 1\ntime = 7200.0\nseason = 2\ndifficulty = 0\nweather = "Clear"\n'
    p = tmp_path / "World.tres"
    p.write_text(content, encoding="utf-8")
    result = parse_world(p)
    assert result["time_str"] == "02:00"
    assert result["season"] == 2
    assert result["difficulty"] == 0
    assert result["weather"] == "Clear"


def test_parse_character_missing_file(tmp_path: Path) -> None:
    assert parse_character(tmp_path / "missing.tres") == []


def test_parse_character_returns_one_item(tmp_path: Path) -> None:
    p = tmp_path / "Character.tres"
    p.write_text(CHARACTER_TRES, encoding="utf-8")
    items = parse_character(p)
    assert len(items) == 1


def test_parse_character_item_name(tmp_path: Path) -> None:
    p = tmp_path / "Character.tres"
    p.write_text(CHARACTER_TRES, encoding="utf-8")
    assert parse_character(p)[0]["item_name"] == "MP5K"


def test_parse_character_slot(tmp_path: Path) -> None:
    p = tmp_path / "Character.tres"
    p.write_text(CHARACTER_TRES, encoding="utf-8")
    assert parse_character(p)[0]["slot"] == "Secondary"


def test_parse_character_condition_and_amount(tmp_path: Path) -> None:
    p = tmp_path / "Character.tres"
    p.write_text(CHARACTER_TRES, encoding="utf-8")
    item = parse_character(p)[0]
    assert item["condition"] == 91
    assert item["amount"] == 30


def test_parse_character_no_attachments_for_empty_nested(tmp_path: Path) -> None:
    p = tmp_path / "Character.tres"
    p.write_text(CHARACTER_TRES, encoding="utf-8")
    assert parse_character(p)[0]["attachments"] == []


def test_parse_character_skips_script_resources(tmp_path: Path) -> None:
    # Blocks whose itemData points to a Script path should be excluded.
    content = """\
[ext_resource type="Script" path="res://Scripts/SlotData.gd" id="1"]
[sub_resource type="Resource" id="Resource_script"]
itemData = ExtResource("1")
condition = 50
amount = 1
slot = "Primary"
[resource]
"""
    p = tmp_path / "Character.tres"
    p.write_text(content, encoding="utf-8")
    assert parse_character(p) == []


def test_parse_storage_missing_file(tmp_path: Path) -> None:
    assert parse_storage(tmp_path / "missing.tres") == []


def test_parse_storage_returns_one_item(tmp_path: Path) -> None:
    p = tmp_path / "Cabin.tres"
    p.write_text(STORAGE_TRES, encoding="utf-8")
    assert len(parse_storage(p)) == 1


def test_parse_storage_item_name(tmp_path: Path) -> None:
    p = tmp_path / "Cabin.tres"
    p.write_text(STORAGE_TRES, encoding="utf-8")
    assert parse_storage(p)[0]["item_name"] == "Medkit"


def test_parse_storage_condition_and_amount(tmp_path: Path) -> None:
    p = tmp_path / "Cabin.tres"
    p.write_text(STORAGE_TRES, encoding="utf-8")
    item = parse_storage(p)[0]
    assert item["condition"] == 75
    assert item["amount"] == 5


def test_parse_storage_label_from_filename(tmp_path: Path) -> None:
    p = tmp_path / "Cabin.tres"
    p.write_text(STORAGE_TRES, encoding="utf-8")
    assert parse_storage(p)[0]["storage_label"] == "Cabin"


# ---------------------------------------------------------------------------
# parse_traders
# ---------------------------------------------------------------------------

TRADERS_TRES = """\
[gd_resource type="Resource" script_class="TraderSave" format=3]
[ext_resource type="Script" path="res://Scripts/TraderSave.gd" id="1"]
[ext_resource type="Script" path="res://Scripts/TaskData.gd" id="2"]
[ext_resource type="Resource" path="res://Traders/Generalist/Tasks/01_Task.tres" id="3"]

[resource]
script = ExtResource("1")
generalist = Array[String](["Backpains", "Prime Time"])
doctor = Array[String]([])
gunsmith = Array[String](["AK-74"])
grandma = Array[String]([])
taskNotes = Array[ExtResource("2")]([ExtResource("3")])
"""


def test_parse_traders_missing_file(tmp_path: Path) -> None:
    assert parse_traders(tmp_path / "missing.tres") == {}


def test_parse_traders_returns_all_string_array_fields(tmp_path: Path) -> None:
    p = tmp_path / "Traders.tres"
    p.write_text(TRADERS_TRES, encoding="utf-8")
    result = parse_traders(p)
    assert set(result.keys()) == {"generalist", "doctor", "gunsmith", "grandma"}


def test_parse_traders_populated_trader(tmp_path: Path) -> None:
    p = tmp_path / "Traders.tres"
    p.write_text(TRADERS_TRES, encoding="utf-8")
    assert parse_traders(p)["generalist"] == ["Backpains", "Prime Time"]


def test_parse_traders_empty_trader(tmp_path: Path) -> None:
    p = tmp_path / "Traders.tres"
    p.write_text(TRADERS_TRES, encoding="utf-8")
    assert parse_traders(p)["doctor"] == []


def test_parse_traders_skips_ext_resource_arrays(tmp_path: Path) -> None:
    p = tmp_path / "Traders.tres"
    p.write_text(TRADERS_TRES, encoding="utf-8")
    result = parse_traders(p)
    assert "taskNotes" not in result


def test_parse_traders_empty_resource_block(tmp_path: Path) -> None:
    content = '[gd_resource type="Resource" format=3]\n[resource]\n'
    p = tmp_path / "Traders.tres"
    p.write_text(content, encoding="utf-8")
    assert parse_traders(p) == {}


def test_parse_storage_label_tent(tmp_path: Path) -> None:
    p = tmp_path / "Tent.tres"
    p.write_text(STORAGE_TRES, encoding="utf-8")
    assert parse_storage(p)[0]["storage_label"] == "Tent"


def test_parse_validator_returns_player_id(tmp_path: Path) -> None:
    p = tmp_path / "Validator.tres"
    p.write_text(VALIDATOR_TRES, encoding="utf-8")
    assert parse_validator(p)["player_id"] == "Taikuri"


def test_parse_validator_missing_file(tmp_path: Path) -> None:
    assert parse_validator(tmp_path / "missing.tres")["player_id"] is None


def test_parse_validator_no_id_field(tmp_path: Path) -> None:
    content = '[resource]\nwarning = "WARNING: Do not touch this."\n'
    p = tmp_path / "Validator.tres"
    p.write_text(content, encoding="utf-8")
    assert parse_validator(p)["player_id"] is None


@pytest.mark.parametrize(
    "prefix",
    [
        "res://Items/Weapons/",
        "res://Items/Ammo/",
        "res://Items/Attachments/",
        "res://Items/Backpacks/",
        "res://Items/Belts/",
        "res://Items/Books/",
        "res://Items/Clothing/",
        "res://Items/Consumables/",
        "res://Items/Electronics/",
        "res://Items/Equipment/",
        "res://Items/Food/",
        "res://Items/Knives/",
        "res://Items/Medical/",
        "res://Items/Misc/",
        "res://Items/Rigs/",
        "res://Items/Tools/",
        "res://Items/Containers/",
        "res://Items/Keys/",
    ],
)
def test_is_item_path_allows_known_subtrees(prefix: str) -> None:
    assert _is_item_path(prefix + "SomeItem/SomeItem.tres") is True


def test_is_item_path_rejects_mod_subtree() -> None:
    assert _is_item_path("res://Items/SomeMod/ModWeapon/ModWeapon.tres") is False


def test_is_item_path_rejects_unrelated_path() -> None:
    assert _is_item_path("res://Scripts/CharacterSave.gd") is False
