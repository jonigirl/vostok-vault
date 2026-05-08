"""
Build local item database directly from decompiled game files.

Requires: data/game_full/ produced by GDRETools full recovery of RTV.pck
Output:   data/items.json  (gitignored — local dev use only)
          data/icons/      (item PNG icons copied from game_full)

Usage:
    uv run python scripts/build_item_db.py
"""

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
GAME_DIR = REPO_ROOT / "data" / "game_full"
GAME_ITEMS_DIR = GAME_DIR / "Items"
ICONS_OUT = REPO_ROOT / "data" / "icons"
OUT_FILE = REPO_ROOT / "data" / "items.json"

RTV_GAME_SUBPATH = Path("steamapps") / "common" / "Road to Vostok" / "RTV.pck"


def _steam_library_roots() -> list[Path]:
    """Return all Steam library root folders found on this machine."""
    candidates = [
        Path("C:/Program Files (x86)/Steam"),
        Path("C:/Program Files/Steam"),
    ]
    roots: list[Path] = []
    for steam_root in candidates:
        if steam_root.exists():
            roots.append(steam_root)
            vdf = steam_root / "steamapps" / "libraryfolders.vdf"
            if vdf.exists():
                for m in re.finditer(
                    r'"path"\s+"([^"]+)"',
                    vdf.read_text(encoding="utf-8", errors="replace"),
                ):
                    lib = Path(m.group(1).replace("\\\\", "\\"))
                    if lib.exists() and lib not in roots:
                        roots.append(lib)
    return roots


def _find_pck() -> Path | None:
    """Locate RTV.pck across all known Steam library folders."""
    for root in _steam_library_roots():
        candidate = root / RTV_GAME_SUBPATH
        if candidate.exists():
            return candidate
    return None


def _check_extraction_staleness() -> None:
    """Warn if RTV.pck is newer than data/game_full/, meaning re-extraction is needed."""
    pck = _find_pck()
    if pck is None:
        return

    pck_mtime = pck.stat().st_mtime
    sentinel = GAME_ITEMS_DIR if GAME_ITEMS_DIR.exists() else GAME_DIR
    if not sentinel.exists():
        return

    extracted_mtime = sentinel.stat().st_mtime
    if pck_mtime > extracted_mtime:
        pck_dt = datetime.fromtimestamp(pck_mtime).strftime("%Y-%m-%d %H:%M:%S")
        ext_dt = datetime.fromtimestamp(extracted_mtime).strftime("%Y-%m-%d %H:%M:%S")
        print("\n" + "=" * 60)
        print("  ⚠  STALE EXTRACTION DETECTED")
        print(f"  RTV.pck modified:  {pck_dt}")
        print(f"  game_full/ date:   {ext_dt}")
        print("  Re-run GDRETools before building the item DB:")
        print(f'    gdre_tools.exe --headless --recover="{pck}"')
        print("    --output=data/game_full")
        print("=" * 60 + "\n")


ITEM_CLASSES = {
    "ItemData",
    "WeaponData",
    "AttachmentData",
    "CasetteData",
    "CatData",
    "FishingData",
    "GrenadeData",
    "InstrumentData",
    "KnifeData",
}

RARITY_MAP = {0: "common", 1: "rare", 2: "legendary", 3: None}

TYPE_TO_CATEGORY: dict[str, str] = {
    "Ammo": "Ammo",
    "Armor": "Armor",
    "Attachment": "Attachments",
    "Backpack": "Backpacks",
    "Belt Pouch": "Belts",
    "Clothing": "Clothing",
    "Consumable": "Consumables",
    "Consumables": "Consumables",
    "Electronics": "Electronics",
    "Fish": "Fishing",
    "Fishing": "Fishing",
    "Grenade": "Grenades",
    "Helmet": "Helmets",
    "Instrument": "Instruments",
    "Key": "Keys",
    "Knife": "Knives",
    "Literature": "Books",
    "Lore": "Lore",
    "Medical": "Medical",
    "Misc": "Misc",
    "Rig": "Rigs",
    "Weapon": "Weapons",
}


def _parse_ext_resources(lines: list[str]) -> dict[str, str]:
    """Map ext_resource id → res:// path."""
    ext_map: dict[str, str] = {}
    header_re = re.compile(r"^\[ext_resource\b")
    id_re = re.compile(r'\bid="([^"]+)"')
    path_re = re.compile(r'\bpath="([^"]+)"')
    for line in lines:
        if not header_re.match(line):
            continue
        id_m = id_re.search(line)
        path_m = path_re.search(line)
        if id_m and path_m:
            ext_map[id_m.group(1)] = path_m.group(1)
    return ext_map


def _parse_resource_block(lines: list[str]) -> dict[str, str]:
    """Extract key=value pairs from the [resource] block."""
    fields: dict[str, str] = {}
    in_resource = False
    for line in lines:
        stripped = line.strip()
        if stripped == "[resource]":
            in_resource = True
            continue
        if in_resource:
            if stripped.startswith("["):
                break
            m = re.match(r"^(\w+)\s*=\s*(.+)", stripped)
            if m:
                fields[m.group(1)] = m.group(2).strip()
    return fields


def _parse_string(raw: str | None) -> str:
    if not raw:
        return ""
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    return raw


def _parse_float(raw: str | None) -> float:
    try:
        return float(raw) if raw else 0.0
    except ValueError:
        return 0.0


def _parse_int(raw: str | None) -> int:
    try:
        return int(raw) if raw else 0
    except ValueError:
        return 0


def _parse_bool(raw: str | None) -> bool:
    return raw == "true"


def _parse_vector2(raw: str | None) -> tuple[int, int]:
    if not raw:
        return (1, 1)
    m = re.match(r"Vector2\(\s*([\d.]+)\s*,\s*([\d.]+)\s*\)", raw)
    if m:
        return (int(float(m.group(1))), int(float(m.group(2))))
    return (1, 1)


def _parse_string_array(raw: str | None) -> list[str]:
    if not raw:
        return []
    return re.findall(r'"([^"]+)"', raw)


def _parse_extresource_array(raw: str | None, ext_map: dict[str, str]) -> list[str]:
    """Parse Array[ExtResource] like [ExtResource("1"), ExtResource("3")] → list of res:// paths."""
    if not raw:
        return []
    ids = re.findall(r'ExtResource\("([^"]+)"\)', raw)
    return [ext_map[i] for i in ids if i in ext_map]


def _resolve_icon(
    fields: dict[str, str],
    ext_map: dict[str, str],
) -> tuple[str | None, Path | None]:
    """
    Resolve icon ExtResource ref → (icon_filename, local_disk_path).
    Returns (None, None) if the icon can't be resolved.
    """
    icon_raw = fields.get("icon")
    if not icon_raw:
        return None, None

    m = re.match(r'ExtResource\("([^"]+)"\)', icon_raw)
    if not m:
        return None, None

    res_path = ext_map.get(m.group(1))
    if not res_path:
        return None, None

    rel = res_path.removeprefix("res://")
    local = GAME_DIR / rel
    if local.exists():
        return local.name, local
    return local.name, None


def build_db() -> None:
    _check_extraction_staleness()

    if not GAME_ITEMS_DIR.exists():
        raise SystemExit(
            f"Game items directory not found: {GAME_ITEMS_DIR}\n"
            "Run GDRETools full recovery first:\n"
            "  gdre_tools.exe --headless --recover=RTV.pck --output=data/game_full"
        )

    if ICONS_OUT.exists():
        shutil.rmtree(ICONS_OUT)
    ICONS_OUT.mkdir(parents=True, exist_ok=True)

    tres_files = [
        f
        for f in GAME_ITEMS_DIR.rglob("*.tres")
        if not f.name.startswith(("MT_", "TX_", "MS_"))
    ]
    print(f"Found {len(tres_files)} candidate .tres files")

    items: list[dict] = []
    skipped_class = 0
    skipped_type = 0
    icons_copied = 0
    icons_missing = 0
    unknown_types: set[str] = set()
    unknown_classes: set[str] = set()
    read_errors: list[str] = []

    for tres_path in sorted(tres_files):
        try:
            lines = tres_path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError) as e:
            print(f"  WARNING: could not read {tres_path.name}: {e}")
            read_errors.append(str(tres_path))
            continue
        if not lines:
            continue

        # Filter by script class
        m = re.search(r'script_class="(\w+)"', lines[0])
        if not m or m.group(1) not in ITEM_CLASSES:
            if m:
                unknown_classes.add(m.group(1))
            skipped_class += 1
            continue

        ext_map = _parse_ext_resources(lines)
        fields = _parse_resource_block(lines)

        raw_type = _parse_string(fields.get("type")).strip()
        if not raw_type:
            skipped_type += 1
            continue

        category = TYPE_TO_CATEGORY.get(raw_type)
        if not category:
            unknown_types.add(raw_type)
            skipped_type += 1
            continue

        item_id = tres_path.stem
        rel_path = tres_path.relative_to(GAME_DIR).as_posix()
        res_path = "res://" + rel_path

        size_w, size_h = _parse_vector2(fields.get("size"))
        rarity_int = _parse_int(fields.get("rarity"))
        rarity = RARITY_MAP.get(rarity_int, "common")

        icon_file, icon_disk = _resolve_icon(fields, ext_map)
        if icon_disk and icon_disk.exists():
            dest = ICONS_OUT / icon_disk.name
            shutil.copy2(icon_disk, dest)
            icons_copied += 1
        elif icon_file:
            icons_missing += 1

        compatible = _parse_extresource_array(fields.get("compatible"), ext_map)

        items.append(
            {
                "res_path": res_path,
                "id": item_id,
                "category": category,
                "display_name": _parse_string(fields.get("name")) or item_id,
                "name_inventory": _parse_string(fields.get("inventory")),
                "name_rotated": _parse_string(fields.get("rotated")),
                "name_equipment": _parse_string(fields.get("equipment")),
                "size_w": size_w,
                "size_h": size_h,
                "weight": _parse_float(fields.get("weight")),
                "value": _parse_int(fields.get("value")),
                "rarity": rarity,
                "icon_file": icon_file,
                "slots": _parse_string_array(fields.get("slots")),
                "stackable": _parse_bool(fields.get("stackable")),
                "show_condition": _parse_bool(fields.get("showCondition")),
                "show_amount": _parse_bool(fields.get("showAmount")),
                "default_amount": _parse_int(fields.get("defaultAmount")),
                "max_amount": _parse_int(fields.get("maxAmount")),
                "repairs": _parse_bool(fields.get("repairs")),
                "compatible": compatible,
            }
        )

    items.sort(key=lambda i: (i["category"], i["display_name"]))

    output = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "source": "game files (RTV.pck v4.6.2, GDRETools v2.5.0-beta.5 full recovery)",
        "total": len(items),
        "items": items,
    }

    OUT_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\nResults:")
    print(f"  Items written:       {len(items)}")
    print(f"  Icons copied:        {icons_copied}")
    print(f"  Icons missing:       {icons_missing}")
    print(f"  Skipped (non-item):  {skipped_class}")
    print(f"  Skipped (no type):   {skipped_type}")
    if read_errors:
        print(f"  Read errors:         {len(read_errors)}")
    if unknown_types:
        print(f"  Unknown types:       {sorted(unknown_types)}")
    if unknown_classes:
        print(f"  Unknown classes:     {sorted(unknown_classes)}")

    cats: dict[str, int] = {}
    for item in items:
        cats[item["category"]] = cats.get(item["category"], 0) + 1
    print("\nBy category:")
    for cat, count in sorted(cats.items()):
        print(f"  {cat}: {count}")

    warnings = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "unknown_types": sorted(unknown_types),
        "unknown_classes": sorted(unknown_classes),
        "read_errors": read_errors,
    }
    warnings_file = REPO_ROOT / "data" / "build_warnings.json"
    warnings_file.write_text(
        json.dumps(warnings, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\nWrote {OUT_FILE}")
    print(f"Wrote icons to {ICONS_OUT}")
    print(f"Wrote warnings to {warnings_file}")


if __name__ == "__main__":
    build_db()
