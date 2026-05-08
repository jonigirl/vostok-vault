import json
import logging
import re
import shutil
import threading
from datetime import datetime
from pathlib import Path

from .mods import get_mod_names, parse_mod_config
from .paths import BACKUP_DIR, SAVE_DIR, TRACKED_DIRS, TRACKED_FILES
from .tres_parser import parse_character, parse_storage, parse_world

log = logging.getLogger(__name__)

_lock = threading.RLock()


def _sanitise_tag(tag: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_\s-]", "", tag).strip()
    return clean.replace(" ", "_")[:50] or "backup"


def list_backups() -> list[dict]:
    with _lock:
        if not BACKUP_DIR.exists():
            return []
        results = []
        for item in sorted(BACKUP_DIR.iterdir(), reverse=True):
            if not item.is_dir():
                continue
            manifest_path = item / "manifest.json"
            if not manifest_path.exists():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["_path"] = str(item)
                results.append(manifest)
            except Exception:
                continue
        return results


def create_backup(tag: str = "manual") -> dict | None:
    with _lock:
        return _create_backup_locked(tag)


def _create_backup_locked(tag: str = "manual") -> dict | None:
    if not SAVE_DIR.exists():
        return None
    _now = datetime.now()
    ts = _now.strftime("%Y%m%d_%H%M%S")
    created_iso = _now.isoformat(timespec="seconds")
    folder_name = f"{ts}_{_sanitise_tag(tag)}"
    dest = BACKUP_DIR / folder_name
    dest.mkdir(parents=True, exist_ok=True)

    for fname in TRACKED_FILES:
        src = SAVE_DIR / fname
        if src.exists():
            shutil.copy2(src, dest / fname)

    for dname in TRACKED_DIRS:
        src = SAVE_DIR / dname
        if src.exists() and src.is_dir():
            shutil.copytree(src, dest / dname, dirs_exist_ok=True)

    world = parse_world(SAVE_DIR / "World.tres")
    mods_raw = parse_mod_config(SAVE_DIR / "mod_config.cfg")
    name_map = get_mod_names(SAVE_DIR)
    mods = []
    for m in mods_raw:
        mods.append(
            {
                "id": m["id"],
                "name": name_map.get(m["id"], m["id"]),
                "version": m["version"],
                "enabled": m["enabled"],
            }
        )

    char_items = len(parse_character(dest / "Character.tres"))
    storage_items = sum(
        len(parse_storage(dest / f)) for f in ("Cabin.tres", "Tent.tres")
    )

    manifest = {
        "id": ts,
        "tag": tag,
        "created": created_iso,
        "game_day": world["day"],
        "game_time": world["time_str"],
        "season": world["season"],
        "weather": world["weather"],
        "difficulty": world["difficulty"],
        "char_items": char_items,
        "storage_items": storage_items,
        "mods": mods,
    }
    tmp = dest / "manifest.json.tmp"
    tmp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    tmp.replace(dest / "manifest.json")
    return manifest


def restore_backup(backup_path: Path) -> bool:
    with _lock:
        if not backup_path.exists():
            return False
        try:
            resolved = backup_path.resolve()
            backup_root = BACKUP_DIR.resolve()
        except OSError:
            return False
        if not resolved.is_relative_to(backup_root) or resolved == backup_root:
            return False
        _create_backup_locked("pre_restore")
        try:
            for fname in TRACKED_FILES:
                src = backup_path / fname
                if src.exists():
                    shutil.copy2(src, SAVE_DIR / fname)
            for dname in TRACKED_DIRS:
                src = backup_path / dname
                if src.exists() and src.is_dir():
                    dest_dir = SAVE_DIR / dname
                    if dest_dir.exists():
                        shutil.rmtree(dest_dir)
                    shutil.copytree(src, dest_dir)
        except OSError as e:
            log.error("restore_backup failed: %s", e)
            return False
        return True


def current_save_needs_backup() -> bool:
    """Return True if tracked save files are newer than the most recent non-restore backup."""
    if not SAVE_DIR.exists():
        return False
    latest_mtime: float | None = None
    for fname in TRACKED_FILES:
        fpath = SAVE_DIR / fname
        if fpath.exists():
            mt = fpath.stat().st_mtime
            if latest_mtime is None or mt > latest_mtime:
                latest_mtime = mt
    if latest_mtime is None:
        return False
    backups = list_backups()
    non_restore = [b for b in backups if not b.get("tag", "").startswith("pre_restore")]
    if not non_restore:
        return True
    most_recent = non_restore[0]
    try:
        backup_dt = datetime.fromisoformat(most_recent["created"])
        return latest_mtime > backup_dt.timestamp()
    except (ValueError, KeyError):
        return True


def delete_backup(backup_path: Path) -> bool:
    with _lock:
        if not backup_path.exists():
            return False
        try:
            resolved = backup_path.resolve()
            backup_root = BACKUP_DIR.resolve()
        except OSError:
            return False
        if not resolved.is_relative_to(backup_root) or resolved == backup_root:
            return False
        try:
            shutil.rmtree(backup_path)
        except OSError as e:
            log.error("delete_backup failed: %s", e)
            return False
        return True


def prune_auto_backups(max_count: int = 5) -> None:
    with _lock:
        if not BACKUP_DIR.exists():
            return
        # Folder names start with YYYYMMDD_HHMMSS_, so lexicographic order == chronological.
        auto_backups = sorted(
            [
                p
                for p in BACKUP_DIR.iterdir()
                if p.is_dir() and p.name.endswith("_auto")
            ],
            key=lambda p: p.name,
        )
        while len(auto_backups) > max_count:
            shutil.rmtree(auto_backups.pop(0), ignore_errors=True)
