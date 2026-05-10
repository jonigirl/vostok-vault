import os
import sys
from pathlib import Path

SAVE_DIR = Path(os.environ.get("APPDATA", "~")) / "Road to Vostok"


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent.parent


ITEMS_JSON = _bundle_root() / "data" / "items.json"
ICONS_DIR = _bundle_root() / "data" / "icons"
BACKUP_DIR = SAVE_DIR / "vostok-vault-backups"

GAME_TRACKED_FILES = [
    "Character.tres",
    "World.tres",
    "Cabin.tres",
    "Tent.tres",
    "Attic.tres",
    "Classroom.tres",
    "Bunker.tres",
    "Traders.tres",
    "Validator.tres",
]

SHELTER_NAMES = ["Cabin", "Tent", "Attic", "Classroom", "Bunker"]

MOD_TRACKED_FILES = [
    "mod_config.cfg",
]

MOD_TRACKED_DIRS = ["MCM"]

# Combined — used by backup and watcher; prefer the typed lists above for logic
TRACKED_FILES = GAME_TRACKED_FILES + MOD_TRACKED_FILES
TRACKED_DIRS = MOD_TRACKED_DIRS

LOG_FILE = BACKUP_DIR / "vostok-vault.log"
