import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

from .backup import sanitise_tag
from .paths import BACKUP_DIR, SHELTER_NAMES
from .tres_parser import (
    _extract_extresource_refs,
    _is_item_path,
    _item_name_from_path,
    _parse_all_sub_resources,
    _parse_ext_resources,
    parse_character,
    parse_storage,
    parse_world,
    strip_orphaned_blocks,
)

log = logging.getLogger(__name__)


def detect_orphaned_items(backup_path: Path, items_db: list[dict]) -> dict:
    known_names = frozenset(item["id"].replace("_", " ") for item in items_db)

    files_to_check = [backup_path / "Character.tres"] + [
        backup_path / f"{n}.tres" for n in SHELTER_NAMES
    ]

    affected_files: dict[str, list[dict]] = {}

    for file_path in files_to_check:
        if not file_path.exists():
            continue

        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        ext_map = _parse_ext_resources(lines)
        sub_map = _parse_all_sub_resources(lines)

        orphaned_ext_ids: set[str] = set()
        for ext_id, path in ext_map.items():
            if _is_item_path(path) and _item_name_from_path(path) not in known_names:
                orphaned_ext_ids.add(ext_id)

        if not orphaned_ext_ids:
            continue

        slots: list[dict] = []
        for sub_id, props in sub_map.items():
            refs = _extract_extresource_refs(props.get("itemData", ""))
            if not refs:
                continue
            ext_id = refs[0]
            if ext_id in orphaned_ext_ids:
                path = ext_map.get(ext_id, "")
                stem_name = _item_name_from_path(path)
                slots.append(
                    {"stem_name": stem_name, "sub_id": sub_id, "ext_id": ext_id}
                )

        # Include file if it has any orphaned ext_resources — even if they only
        # appear as nested attachment/ammo refs with no own sub_resource slot.
        affected_files[file_path.name] = slots

    all_orphan_names: set[str] = set()
    total_slots = 0
    for _filename, slots in affected_files.items():
        total_slots += len(slots)
        for slot in slots:
            all_orphan_names.add(slot["stem_name"])

    # Also collect names of orphaned ext_resources that only appear in nested
    # arrays (no own sub_resource slot) so the dialog can show them.
    for file_path in files_to_check:
        if not file_path.exists() or file_path.name not in affected_files:
            continue
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        ext_map = _parse_ext_resources(lines)
        slot_ext_ids = {s["ext_id"] for s in affected_files[file_path.name]}
        for ext_id, path in ext_map.items():
            if _is_item_path(path) and _item_name_from_path(path) not in known_names:
                if ext_id not in slot_ext_ids:
                    all_orphan_names.add(_item_name_from_path(path))

    orphan_names = sorted(all_orphan_names)

    return {
        "affected_files": affected_files,
        "orphan_names": orphan_names,
        "total_slots": total_slots,
    }


def create_repaired_backup(
    source_backup_path: Path, items_db: list[dict]
) -> tuple[bool, str]:
    detection = detect_orphaned_items(source_backup_path, items_db)
    if not detection["affected_files"]:
        return (False, "nothing_to_repair")

    manifest_path = source_backup_path / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        log.error("create_repaired_backup: failed to read manifest: %s", e)
        return (False, "write_error")

    original_id: str = manifest.get("id", "")
    original_tag: str = manifest.get("tag", "backup")

    folder_name = f"{original_id}_repaired_{sanitise_tag(original_tag)}"
    dest = BACKUP_DIR / folder_name

    if dest == source_backup_path:
        log.error("create_repaired_backup: dest equals source, aborting")
        return (False, "write_error")

    known_names = frozenset(item["id"].replace("_", " ") for item in items_db)

    try:
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_backup_path, dest, dirs_exist_ok=True)

        for filename, file_slots in detection["affected_files"].items():
            dest_file = dest / filename
            if not dest_file.exists():
                continue

            lines = dest_file.read_text(encoding="utf-8", errors="replace").splitlines(
                keepends=True
            )

            # Build orphaned_ext_ids from ALL orphaned item ext_resources in the
            # file — not just those referenced by itemData. This catches nested
            # attachment/ammo references inside vanilla weapon sub_resources.
            full_ext_map = _parse_ext_resources([ln.rstrip("\n") for ln in lines])
            orphaned_ext_ids = {
                ext_id
                for ext_id, path in full_ext_map.items()
                if _is_item_path(path) and _item_name_from_path(path) not in known_names
            }
            orphaned_sub_ids = {slot["sub_id"] for slot in file_slots}
            stripped_lines = strip_orphaned_blocks(
                lines, orphaned_ext_ids, orphaned_sub_ids
            )

            dest_file.write_text(
                "".join(stripped_lines), encoding="utf-8", newline="\n"
            )

            if filename == "Character.tres":
                source_count = len(parse_character(source_backup_path / filename))
                dest_count = len(parse_character(dest_file))
            else:
                source_count = len(parse_storage(source_backup_path / filename))
                dest_count = len(parse_storage(dest_file))

            if dest_count > source_count:
                log.error(
                    "create_repaired_backup: sanity check failed for %s "
                    "(dest=%d > source=%d); aborting",
                    filename,
                    dest_count,
                    source_count,
                )
                shutil.rmtree(dest)
                return (False, "write_error")

        world = parse_world(dest / "World.tres")
        char_items = len(parse_character(dest / "Character.tres"))
        storage_items = sum(
            len(parse_storage(dest / f"{name}.tres")) for name in SHELTER_NAMES
        )

        new_manifest = {
            "id": original_id,
            "tag": "repaired",
            "original_tag": original_tag,
            "removed_items": sorted(detection.get("orphan_names", [])),
            "created": datetime.now().isoformat(timespec="seconds"),
            "game_day": world["day"],
            "game_time": world["time_str"],
            "season": world["season"],
            "weather": world["weather"],
            "difficulty": world["difficulty"],
            "char_items": char_items,
            "storage_items": storage_items,
            "active_mod_profile": manifest.get("active_mod_profile"),
            "mods": manifest.get("mods", []),
            "repaired_from_id": original_id,
        }

        tmp = dest / "manifest.json.tmp"
        tmp.write_text(json.dumps(new_manifest, indent=2), encoding="utf-8")
        tmp.replace(dest / "manifest.json")

    except OSError as e:
        log.error("create_repaired_backup: OSError: %s", e)
        shutil.rmtree(dest, ignore_errors=True)
        return (False, "write_error")

    return (True, "ok")
