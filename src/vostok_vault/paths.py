import os
from pathlib import Path

SAVE_DIR = Path(os.environ.get("APPDATA", "~")) / "Road to Vostok"
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
