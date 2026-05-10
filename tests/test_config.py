from vostok_vault.constants import APP_TITLE, DIFFICULTY_NAMES, SEASON_NAMES
from vostok_vault.paths import (
    BACKUP_DIR,
    GAME_TRACKED_FILES,
    MOD_TRACKED_DIRS,
    MOD_TRACKED_FILES,
    SAVE_DIR,
    TRACKED_DIRS,
    TRACKED_FILES,
)


def test_backup_dir_is_child_of_save_dir() -> None:
    assert BACKUP_DIR.parent == SAVE_DIR


def test_tracked_files_contains_character() -> None:
    assert "Character.tres" in TRACKED_FILES


def test_tracked_files_contains_world() -> None:
    assert "World.tres" in TRACKED_FILES


def test_tracked_dirs_contains_mcm() -> None:
    assert "MCM" in TRACKED_DIRS


def test_game_tracked_files_vanilla_only() -> None:
    for fname in GAME_TRACKED_FILES:
        assert fname.endswith(".tres"), f"{fname} is not a .tres file"


def test_game_tracked_files_no_mod_config() -> None:
    assert "mod_config.cfg" not in GAME_TRACKED_FILES


def test_mod_tracked_files_contains_mod_config() -> None:
    assert "mod_config.cfg" in MOD_TRACKED_FILES


def test_mod_tracked_dirs_contains_mcm() -> None:
    assert "MCM" in MOD_TRACKED_DIRS


def test_tracked_files_is_union_of_typed_lists() -> None:
    assert set(TRACKED_FILES) == set(GAME_TRACKED_FILES) | set(MOD_TRACKED_FILES)


def test_tracked_dirs_equals_mod_tracked_dirs() -> None:
    assert TRACKED_DIRS == MOD_TRACKED_DIRS


def test_season_names_spring() -> None:
    assert SEASON_NAMES[1] == "Spring"


def test_season_names_summer() -> None:
    assert SEASON_NAMES[2] == "Summer"


def test_season_names_autumn() -> None:
    assert SEASON_NAMES[3] == "Autumn"


def test_season_names_winter() -> None:
    assert SEASON_NAMES[4] == "Winter"


def test_difficulty_names_rookie() -> None:
    assert DIFFICULTY_NAMES[0] == "Rookie"


def test_difficulty_names_stalker() -> None:
    assert DIFFICULTY_NAMES[1] == "Stalker"


def test_difficulty_names_hardcore() -> None:
    assert DIFFICULTY_NAMES[2] == "Hardcore"


def test_difficulty_names_ironman() -> None:
    assert DIFFICULTY_NAMES[3] == "Ironman"


def test_app_title() -> None:
    assert APP_TITLE == "Vostok Vault"


def test_tracked_files_is_list() -> None:
    assert isinstance(TRACKED_FILES, list)
    assert len(TRACKED_FILES) > 0


def test_tracked_dirs_is_list() -> None:
    assert isinstance(TRACKED_DIRS, list)
    assert len(TRACKED_DIRS) > 0
