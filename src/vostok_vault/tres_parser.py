import json
import re
from pathlib import Path

from .paths import TRADERS_CATALOG_JSON


def _item_name_from_path(res_path: str) -> str:
    return Path(res_path).stem.replace("_", " ")


def _parse_ext_resources(lines: list[str]) -> dict[str, str]:
    ext_map: dict[str, str] = {}
    header_re = re.compile(r"\[ext_resource\b([^\]]*)\]")
    attr_re = re.compile(r'\b(\w+)="([^"]*)"')
    for line in lines:
        m = header_re.match(line.strip())
        if not m:
            continue
        attrs = dict(attr_re.findall(m.group(1)))
        rid = attrs.get("id", "")
        path = attrs.get("path", "")
        if rid and path:
            ext_map[rid] = path
    return ext_map


def _parse_props(block_lines: list[str]) -> dict[str, str]:
    props: dict[str, str] = {}
    for line in block_lines:
        if " = " in line:
            key, _, val = line.partition(" = ")
            props[key.strip()] = val.strip()
    return props


def _extract_extresource_refs(val: str) -> list[str]:
    return re.findall(r'ExtResource\("([^"]+)"\)', val)


def _parse_all_sub_resources(lines: list[str]) -> dict[str, dict[str, str]]:
    """Return {sub_resource_id: {prop: raw_value}} for all sub_resource blocks."""
    result: dict[str, dict[str, str]] = {}
    header_re = re.compile(r'\[sub_resource\b[^\]]*\bid="([^"]+)"')
    current_id: str | None = None
    current_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        m = header_re.match(stripped)
        if m:
            if current_id is not None:
                result[current_id] = _parse_props(current_lines)
            current_id = m.group(1)
            current_lines = []
        elif current_id is not None:
            if stripped.startswith("[") and stripped.endswith("]"):
                result[current_id] = _parse_props(current_lines)
                current_id = None
                current_lines = []
            else:
                current_lines.append(stripped)
    if current_id is not None:
        result[current_id] = _parse_props(current_lines)
    return result


def _extract_nested_item_refs(val: str) -> list[str]:
    # Format: Array[ExtResource("type_id")]([ExtResource("a"), ExtResource("b")])
    # Only extract from the array contents, not the type annotation.
    content_match = re.search(r"Array\[.*?\]\((\[.*?\])\)", val, re.DOTALL)
    if content_match:
        return re.findall(r'ExtResource\("([^"]+)"\)', content_match.group(1))
    return _extract_extresource_refs(val)


_ITEM_SUBTREES = (
    "res://Items/Weapons/",
    "res://Items/Ammo/",
    "res://Items/Attachments/",
    "res://Items/Backpacks/",
    "res://Items/Belts/",
    "res://Items/Books/",
    "res://Items/Clothing/",
    "res://Items/Consumables/",
    "res://Items/Electronics/",
    "res://Items/Equipment/",
    "res://Items/Food/",
    "res://Items/Knives/",
    "res://Items/Medical/",
    "res://Items/Misc/",
    "res://Items/Rigs/",
    "res://Items/Tools/",
    "res://Items/Containers/",
    "res://Items/Keys/",
)


def _is_item_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _ITEM_SUBTREES)


def _resolve_item(props: dict[str, str], ext_map: dict[str, str]) -> dict | None:
    refs = _extract_extresource_refs(props.get("itemData", ""))
    if not refs:
        return None
    item_path = ext_map.get(refs[0], "")
    if not item_path or not _is_item_path(item_path):
        return None
    item_name = _item_name_from_path(item_path)
    if not item_name:
        return None
    try:
        condition = int(float(props.get("condition", "")))
    except (ValueError, TypeError):
        condition = None
    try:
        amount = int(props.get("amount", "1"))
    except (ValueError, TypeError):
        amount = 1
    return {"item_name": item_name, "condition": condition, "amount": amount}


def parse_character(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    ext_map = _parse_ext_resources(lines)
    sub_map = _parse_all_sub_resources(lines)
    results = []
    for props in sub_map.values():
        base = _resolve_item(props, ext_map)
        if base is None:
            continue
        slot = props.get("slot", "").strip('"') or "Storage"
        attachments: list[str] = []
        nested_val = props.get("nested", "")
        if nested_val:
            for nref in _extract_nested_item_refs(nested_val):
                npath = ext_map.get(nref, "")
                if npath and _is_item_path(npath):
                    aname = _item_name_from_path(npath)
                    if aname:
                        attachments.append(aname)
        results.append(
            {
                "slot": slot,
                "item_name": base["item_name"],
                "condition": base["condition"],
                "amount": base["amount"],
                "attachments": attachments,
            }
        )
    return results


def parse_storage(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    ext_map = _parse_ext_resources(lines)
    storage_label = path.stem
    sub_map = _parse_all_sub_resources(lines)

    results = []
    seen_slot_ids: set[str] = set()

    # Phase 1: items stored inside named furniture containers
    for sub_id, props in sub_map.items():
        name_val = props.get("name", "")
        storage_val = props.get("storage", "")
        if not name_val or not storage_val:
            continue
        container_name = name_val.strip('"')
        for ref in re.findall(r'SubResource\("([^"]+)"\)', storage_val):
            if ref in seen_slot_ids:
                continue
            item = _resolve_item(sub_map.get(ref, {}), ext_map)
            if item is None:
                continue
            seen_slot_ids.add(ref)
            results.append(
                {**item, "container": container_name, "storage_label": storage_label}
            )

    # Phase 2: any remaining item slots not inside a container (floor items)
    for sub_id, props in sub_map.items():
        if sub_id in seen_slot_ids or "name" in props:
            continue
        item = _resolve_item(props, ext_map)
        if item is None:
            continue
        seen_slot_ids.add(sub_id)
        results.append({**item, "container": "", "storage_label": storage_label})

    return results


def parse_world(path: Path) -> dict:
    default = {
        "day": "?",
        "time_str": "??:??",
        "season": "?",
        "weather": "?",
        "difficulty": "?",
    }
    if not path.exists():
        return default

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    in_resource = False
    raw: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if stripped == "[resource]":
            in_resource = True
            continue
        if in_resource and stripped.startswith("[") and stripped.endswith("]"):
            break
        if in_resource and " = " in stripped:
            key, _, val = stripped.partition(" = ")
            raw[key.strip()] = val.strip()

    day: int | str = "?"
    try:
        day = int(raw.get("day", ""))
    except (ValueError, TypeError):
        pass

    season: int | str = "?"
    try:
        season = int(raw.get("season", ""))
    except (ValueError, TypeError):
        pass

    difficulty: int | str = "?"
    try:
        difficulty = int(raw.get("difficulty", ""))
    except (ValueError, TypeError):
        pass

    weather = raw.get("weather", "?").strip('"')

    time_str = "??:??"
    try:
        secs = float(raw.get("time", ""))
        hours = int(secs // 3600)
        mins = int((secs % 3600) // 60)
        time_str = f"{hours:02d}:{mins:02d}"
    except (ValueError, TypeError):
        pass

    try:
        shelters = int(raw.get("shelters", ""))
    except (ValueError, TypeError):
        shelters = None

    weather_time: float | None = None
    try:
        weather_time = float(raw.get("weatherTime", ""))
    except (ValueError, TypeError):
        pass

    return {
        "day": day,
        "time_str": time_str,
        "season": season,
        "weather": weather,
        "difficulty": difficulty,
        "shelters": shelters,
        "weather_time": weather_time,
    }


def parse_validator(path: Path) -> dict:
    if not path.exists():
        return {"player_id": None}
    in_resource = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped == "[resource]":
            in_resource = True
            continue
        if in_resource and stripped.startswith("[") and stripped.endswith("]"):
            break
        if in_resource and stripped.startswith("ID = "):
            return {"player_id": stripped[5:].strip().strip('"')}
    return {"player_id": None}


_STRING_ARRAY_RE = re.compile(r"^Array\[String\]\((\[.*\])\)$", re.DOTALL)


def parse_traders(path: Path) -> dict[str, list[str]]:
    """Return a dict mapping trader-type name → list of purchased item names.

    Fields are discovered dynamically from the resource block so new trader
    types added by future game updates appear automatically.  Only fields
    whose values are ``Array[String]`` are included; other fields (e.g.
    ``taskNotes``) are skipped.
    """
    if not path.exists():
        return {}
    in_resource = False
    result: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped == "[resource]":
            in_resource = True
            continue
        if in_resource and stripped.startswith("[") and stripped.endswith("]"):
            break
        if not in_resource or " = " not in stripped:
            continue
        key, _, val = stripped.partition(" = ")
        key = key.strip()
        val = val.strip()
        m = _STRING_ARRAY_RE.match(val)
        if not m:
            continue
        names = re.findall(r'"([^"]+)"', m.group(1))
        result[key] = names
    return result


def load_trader_task_catalog() -> dict[str, dict]:
    """Return {trader_key: {"tasks": [...], "base_tax": int}} from the bundled catalog.

    Returns an empty dict if the catalog file is not present.
    """
    if not TRADERS_CATALOG_JSON.exists():
        return {}
    with TRADERS_CATALOG_JSON.open(encoding="utf-8") as fh:
        return json.load(fh)


def _filter_extresource_array_refs(value: str, orphaned_ext_ids: set[str]) -> str:
    """Remove orphaned ExtResource refs from Array[...]([ ... ]) values."""
    m = re.search(r"(Array\[[^\]]+\]\(\[)(.*?)(\]\))", value, re.DOTALL)
    if not m:
        return value
    inner = m.group(2)
    refs = re.findall(r'ExtResource\("([^"]+)"\)', inner)
    kept = [f'ExtResource("{r}")' for r in refs if r not in orphaned_ext_ids]
    return value[: m.start(2)] + ", ".join(kept) + value[m.end(2) :]


def _rewrite_extresource_array_refs(line: str, orphaned_ext_ids: set[str]) -> str:
    """Rewrite a line that contains an ExtResource array, removing orphaned refs."""
    if " = " not in line or "Array[" not in line:
        return line
    if not any(f'ExtResource("{eid}")' in line for eid in orphaned_ext_ids):
        return line
    key, sep, value = line.partition(" = ")
    return f"{key}{sep}{_filter_extresource_array_refs(value, orphaned_ext_ids)}"


def _filter_subresource_refs(value: str, orphaned_sub_ids: set[str]) -> str:
    # Handle Array[...]([ inner ]) format
    m = re.search(r"(Array\[[^\]]+\]\(\[)(.*?)(\]\))", value, re.DOTALL)
    if m:
        inner = m.group(2)
        refs = re.findall(r'SubResource\("([^"]+)"\)', inner)
        kept = [f'SubResource("{r}")' for r in refs if r not in orphaned_sub_ids]
        return value[: m.start(2)] + ", ".join(kept) + value[m.end(2) :]

    # Handle plain [ inner ] format
    m = re.search(r"\[(.*?)\]", value, re.DOTALL)
    if m:
        inner = m.group(1)
        refs = re.findall(r'SubResource\("([^"]+)"\)', inner)
        if refs:
            kept = [f'SubResource("{r}")' for r in refs if r not in orphaned_sub_ids]
            return value[: m.start(1)] + ", ".join(kept) + value[m.end(1) :]

    return value


def _rewrite_subresource_refs(line: str, orphaned_sub_ids: set[str]) -> str:
    if " = " not in line:
        return line
    if not any(f'SubResource("{sid}")' in line for sid in orphaned_sub_ids):
        return line
    key, sep, value = line.partition(" = ")
    new_value = _filter_subresource_refs(value, orphaned_sub_ids)
    return f"{key}{sep}{new_value}"


def strip_orphaned_blocks(
    lines: list[str],
    orphaned_ext_ids: set[str],
    orphaned_sub_ids: set[str],
) -> list[str]:
    _id_re = re.compile(r'\bid="([^"]+)"')

    result: list[str] = []
    in_orphaned_sub = False
    in_rewrite_block = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("[") and stripped.endswith("]"):
            if stripped.startswith("[ext_resource"):
                in_orphaned_sub = False
                in_rewrite_block = False
                m = _id_re.search(stripped)
                if m and m.group(1) in orphaned_ext_ids:
                    continue
                result.append(line)
                continue

            if stripped.startswith("[sub_resource"):
                m = _id_re.search(stripped)
                sub_id = m.group(1) if m else ""
                if sub_id in orphaned_sub_ids:
                    in_orphaned_sub = True
                    in_rewrite_block = False
                    continue
                in_orphaned_sub = False
                in_rewrite_block = True
                result.append(line)
                continue

            in_orphaned_sub = False
            in_rewrite_block = stripped == "[resource]"
            result.append(line)
            continue

        if in_orphaned_sub:
            continue

        if in_rewrite_block and orphaned_sub_ids:
            line = _rewrite_subresource_refs(line, orphaned_sub_ids)

        if in_rewrite_block and orphaned_ext_ids:
            line = _rewrite_extresource_array_refs(line, orphaned_ext_ids)

        result.append(line)

    return result
