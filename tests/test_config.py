from vostok_vault.config import (
    APP_TITLE,
    BACKUP_DIR,
    DIFFICULTY_NAMES,
    SAVE_DIR,
    SEASON_NAMES,
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


def test_app_title() -> None:
    assert APP_TITLE == "Vostok Vault"


def test_tracked_files_is_list() -> None:
    assert isinstance(TRACKED_FILES, list)
    assert len(TRACKED_FILES) > 0


def test_tracked_dirs_is_list() -> None:
    assert isinstance(TRACKED_DIRS, list)
    assert len(TRACKED_DIRS) > 0
