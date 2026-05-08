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

TRACKED_FILES = [
    "Character.tres",
    "World.tres",
    "Cabin.tres",
    "Tent.tres",
    "Traders.tres",
    "LifelineBPMMarker.tres",
    "Validator.tres",
    "mod_config.cfg",
]
TRACKED_DIRS = ["MCM"]

LOG_FILE = BACKUP_DIR / "vostok-vault.log"
