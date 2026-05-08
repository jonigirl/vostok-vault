import json
import logging

from .paths import BACKUP_DIR

_SETTINGS_FILE = BACKUP_DIR / "settings.json"

_log = logging.getLogger(__name__)


def load_settings() -> dict:
    try:
        if _SETTINGS_FILE.exists():
            return json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _log.warning("Could not load settings: %s", e)
    return {}


def save_settings(data: dict) -> None:
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _SETTINGS_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(_SETTINGS_FILE)
    except OSError as e:
        _log.error("Could not save settings: %s", e)
