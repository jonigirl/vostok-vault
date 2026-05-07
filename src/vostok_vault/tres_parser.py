import re
from pathlib import Path


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


def _split_sub_resource_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[sub_resource"):
            if current is not None:
                blocks.append(current)
            current = []
        elif current is not None:
            if stripped.startswith("[") and stripped.endswith("]"):
                blocks.append(current)
                current = None
            else:
                current.append(stripped)
    if current is not None:
        blocks.append(current)
    return blocks


def _parse_props(block_lines: list[str]) -> dict[str, str]:
    props: dict[str, str] = {}
    for line in block_lines:
        if " = " in line:
            key, _, val = line.partition(" = ")
            props[key.strip()] = val.strip()
    return props


def _extract_extresource_refs(val: str) -> list[str]:
    return re.findall(r'ExtResource\("([^"]+)"\)', val)


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


def parse_character(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    ext_map = _parse_ext_resources(lines)
    blocks = _split_sub_resource_blocks(lines)
    results = []
    for block in blocks:
        props = _parse_props(block)
        if "itemData" not in props:
            continue
        refs = _extract_extresource_refs(props["itemData"])
        if not refs:
            continue
        item_ref = refs[0]
        item_path = ext_map.get(item_ref, "")
        if not item_path or not _is_item_path(item_path):
            continue
        item_name = _item_name_from_path(item_path)
        if not item_name:
            continue

        slot = props.get("slot", "").strip('"') or "Storage"

        try:
            condition = int(float(props.get("condition", "")))
        except (ValueError, TypeError):
            condition = None

        try:
            amount = int(props.get("amount", "1"))
        except (ValueError, TypeError):
            amount = 1

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
                "item_name": item_name,
                "condition": condition,
                "amount": amount,
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
    blocks = _split_sub_resource_blocks(lines)
    results = []
    for block in blocks:
        props = _parse_props(block)
        if "itemData" not in props:
            continue
        refs = _extract_extresource_refs(props["itemData"])
        if not refs:
            continue
        item_path = ext_map.get(refs[0], "")
        if not item_path or not _is_item_path(item_path):
            continue
        item_name = _item_name_from_path(item_path)
        if not item_name:
            continue

        try:
            condition = int(float(props.get("condition", "")))
        except (ValueError, TypeError):
            condition = None

        try:
            amount = int(props.get("amount", "1"))
        except (ValueError, TypeError):
            amount = 1

        results.append(
            {
                "item_name": item_name,
                "condition": condition,
                "amount": amount,
                "storage_label": storage_label,
            }
        )
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
