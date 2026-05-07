import ctypes
import logging
import logging.handlers
import os
import sys
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

FONT_ATKINSON = "Atkinson Hyperlegible"
FONT_OPENDYSLEXIC = "OpenDyslexic"
FONT_FALLBACK = "Segoe UI"

_app_font: str = FONT_FALLBACK


def _fonts_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "assets" / "fonts"
    return Path(__file__).resolve().parent.parent.parent / "assets" / "fonts"


def _load_font_windows(ttf_path: Path) -> bool:
    if sys.platform != "win32":
        return False
    try:
        added = ctypes.windll.gdi32.AddFontResourceW(str(ttf_path))
        if added > 0:
            ctypes.windll.user32.SendMessageTimeoutW(
                0xFFFF, 0x001D, 0, 0, 0, 1000, None
            )
            return True
    except Exception:
        return False
    return False


def _load_bundled_fonts() -> None:
    fonts_dir = _fonts_dir()
    for name in ("AtkinsonHyperlegible-Regular.ttf", "AtkinsonHyperlegible-Bold.ttf"):
        f = fonts_dir / name
        if f.exists():
            _load_font_windows(f)


def init_font(preferred: str | None = None) -> str:
    global _app_font
    _load_bundled_fonts()
    try:
        import tkinter as tk
        import tkinter.font as tkfont

        _tmp = tk.Tk()
        _tmp.withdraw()
        families = tkfont.families()
        _tmp.destroy()
    except Exception:
        families = ()

    if preferred == FONT_OPENDYSLEXIC and FONT_OPENDYSLEXIC in families:
        _app_font = FONT_OPENDYSLEXIC
    elif FONT_ATKINSON in families:
        _app_font = FONT_ATKINSON
    else:
        _app_font = FONT_FALLBACK
    return _app_font


def get_font() -> str:
    return _app_font


_SETTINGS_FILE = BACKUP_DIR / "settings.json"
LOG_FILE = BACKUP_DIR / "vostok-vault.log"


_log = logging.getLogger(__name__)


def load_settings() -> dict:
    try:
        if _SETTINGS_FILE.exists():
            import json

            return json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _log.warning("Could not load settings: %s", e)
    return {}


def save_settings(data: dict) -> None:
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        import json

        _SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError as e:
        _log.error("Could not save settings: %s", e)


def setup_logging(debug: bool = False) -> None:
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        level = logging.DEBUG if debug else logging.WARNING
        handler = logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=512_000, backupCount=1, encoding="utf-8"
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.addHandler(handler)
        root_logger.setLevel(level)
    except OSError:
        logging.basicConfig(level=logging.WARNING)
