import configparser
import re
import zipfile
from pathlib import Path


def parse_mod_config(cfg_path: Path) -> tuple[list[dict], str]:
    if not cfg_path.exists():
        return [], ""
    parser = configparser.RawConfigParser()
    try:
        parser.read(cfg_path, encoding="utf-8")
    except Exception:
        return [], ""
    active_profile = ""
    if parser.has_section("settings"):
        active_profile = parser.get("settings", "active_profile", fallback="").strip(
            '"'
        )
    results = []
    for section in parser.sections():
        if "enabled" not in section.lower():
            continue
        for key, val in parser.items(section):
            if "@" not in key:
                continue
            mod_id, _, version = key.partition("@")
            enabled = val.strip().lower() == "true"
            results.append(
                {
                    "id": mod_id.strip(),
                    "version": version.strip(),
                    "enabled": enabled,
                }
            )
    return results, active_profile


def _read_vmz_mod_info(vmz_path: Path) -> dict:
    try:
        with zipfile.ZipFile(vmz_path, "r") as z:
            if "mod.txt" not in z.namelist():
                return {}
            content = z.read("mod.txt").decode("utf-8", errors="replace")
            parser = configparser.RawConfigParser()
            parser.read_string(content)
            if not parser.has_section("mod"):
                return {}
            return {
                "name": parser.get("mod", "name", fallback="").strip('"'),
                "id": parser.get("mod", "id", fallback="").strip('"'),
                "version": parser.get("mod", "version", fallback="").strip('"'),
                "author": parser.get("mod", "author", fallback="").strip('"'),
            }
    except Exception:
        return {}


def _parse_archive_paths(cfg_path: Path) -> list[Path]:
    if not cfg_path.exists():
        return []
    content = cfg_path.read_text(encoding="utf-8", errors="replace")
    # Handle quoted paths first (most common in Godot config files)
    raw_paths = re.findall(r'"([^"]+\.vmz)"', content)
    if not raw_paths:
        # Fall back to unquoted Windows absolute paths
        raw_paths = re.findall(r'([A-Za-z]:\\[^\s",\]\)\n]+\.vmz)', content)
    seen: set[str] = set()
    paths: list[Path] = []
    for raw in raw_paths:
        normalized = raw.replace("\\\\", "\\")
        if normalized not in seen:
            seen.add(normalized)
            paths.append(Path(normalized))
    return paths


def get_mod_names(save_dir: Path) -> dict[str, str]:
    pass_state = save_dir / "mod_pass_state.cfg"
    vmz_paths = _parse_archive_paths(pass_state)
    name_map: dict[str, str] = {}
    for vmz in vmz_paths:
        info = _read_vmz_mod_info(vmz)
        mod_id = info.get("id", "")
        mod_name = info.get("name", "")
        if mod_id and mod_name:
            name_map[mod_id] = mod_name
    return name_map
