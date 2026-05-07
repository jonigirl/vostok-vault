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

SEASON_NAMES = {1: "Spring", 2: "Summer", 3: "Autumn", 4: "Winter"}
DIFFICULTY_NAMES = {0: "Rookie", 1: "Stalker", 2: "Hardcore"}

APP_TITLE = "Vostok Vault"
WINDOW_MIN_WIDTH = 1100
WINDOW_MIN_HEIGHT = 700
LEFT_PANEL_WIDTH = 280

_app_font: str = "Segoe UI"


def init_font() -> str:
    global _app_font
    try:
        import tkinter.font as tkfont

        if "OpenDyslexic" in tkfont.families():
            _app_font = "OpenDyslexic"
        else:
            _app_font = "Segoe UI"
    except Exception:
        _app_font = "Segoe UI"
    return _app_font


def get_font() -> str:
    return _app_font
