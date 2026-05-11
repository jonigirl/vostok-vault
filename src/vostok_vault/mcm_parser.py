import ast
import re
from pathlib import Path

_VALUE_SECTIONS = {"String", "Int", "Float", "Bool", "Keycode", "Color", "Dropdown"}


def parse_mcm_configs(mcm_dir: Path) -> dict[str, list[dict]]:
    """Parse MCM config.ini files from a backup's MCM directory.

    Returns a dict of mod_folder_name -> list of setting dicts,
    sorted by category then menu_pos within each mod.
    """
    result: dict[str, list[dict]] = {}
    if not mcm_dir.exists():
        return result
    for mod_dir in sorted(mcm_dir.iterdir()):
        if not mod_dir.is_dir():
            continue
        cfg = mod_dir / "config.ini"
        if not cfg.exists():
            continue
        settings = _parse_mcm_config(cfg)
        if settings:
            result[mod_dir.name] = settings
    return result


def _parse_mcm_config(cfg_path: Path) -> list[dict]:
    try:
        lines = cfg_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    # Parse line-by-line. Godot ConfigFile uses & as a line-continuation prefix.
    # Each setting block looks like:
    #   key_name={
    #   &"field": value,
    #   }
    # We track brace depth so nested dicts (Dropdown options) work correctly.
    settings: list[dict] = []
    current_section: str | None = None
    current_key: str | None = None
    block_lines: list[str] = []
    brace_depth = 0

    for line in lines:
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1]
            current_key = None
            block_lines = []
            brace_depth = 0
            continue

        if current_key is None:
            if current_section not in _VALUE_SECTIONS:
                continue
            m = re.match(r"^(\w+)=(\{.*)$", line)
            if m:
                current_key = m.group(1)
                first = m.group(2)
                brace_depth = first.count("{") - first.count("}")
                block_lines = [first]
        else:
            clean = line.lstrip("&")
            brace_depth += clean.count("{") - clean.count("}")
            block_lines.append(clean)
            if brace_depth <= 0:
                raw_block = "\n".join(block_lines)
                setting = _parse_setting(current_key, current_section or "", raw_block)
                if setting is not None:
                    settings.append(setting)
                current_key = None
                block_lines = []
                brace_depth = 0

    settings.sort(key=lambda s: (s.get("category", ""), s.get("menu_pos", 999)))
    return settings


def _parse_setting(key: str, section: str, raw: str) -> dict | None:
    raw = raw.strip()
    if not raw.startswith("{"):
        return None

    # Normalise Godot variant literals to Python-safe equivalents before
    # passing to ast.literal_eval.
    normalized = raw
    # Boolean literals
    normalized = re.sub(r"\btrue\b", "True", normalized)
    normalized = re.sub(r"\bfalse\b", "False", normalized)
    # null literal
    normalized = re.sub(r"\bnull\b", "None", normalized)
    # Color(...) — keep as a readable string rather than trying to evaluate
    normalized = re.sub(r"Color\([^)]*\)", lambda m: f'"{m.group(0)}"', normalized)

    try:
        data = ast.literal_eval(normalized)
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    value = data.get("value")
    # Format value for display
    display_value = _format_value(value, section)

    return {
        "key": key,
        "type": section,
        "name": str(data.get("name", key)),
        "display_value": display_value,
        "category": str(data.get("category", "")),
        "menu_pos": int(data.get("menu_pos") or 999),
        "tooltip": str(data.get("tooltip", "")),
    }


def _format_value(value: object, section: str) -> str:
    if value is None:
        return "—"
    if section == "Bool":
        return "On" if value else "Off"
    if section == "Color":
        return str(value)
    if section == "Keycode":
        return f"Key {value}"
    if section == "Float":
        if isinstance(value, float):
            return f"{value:.2f}".rstrip("0").rstrip(".")
        return str(value)
    return str(value)
