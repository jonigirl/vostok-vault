"""
Build a local item reference database from backup save files.

Output: data/items.json  (gitignored — local dev use only)

Structure per item entry:
  res_path   : full Godot resource path from save files
  name       : human-readable name derived from filename
  category   : subtree label (Weapons, Ammo, Medical, ...)
  subtree    : full res://Items/<Category>/ prefix
  rarity     : null — not stored in save files (in encrypted PCK)
               fill manually if you discover values via other means
  seen_in_slots : list of Character slot names this item was found equipped in
  seen_count : how many times this item appeared across all scanned saves

Usage:
    uv run python scripts/build_item_db.py

Re-run any time after new backups are made to pick up newly seen items.
Existing entries are preserved; new ones are appended; counts/slots updated.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
BACKUP_DIR = Path(r"C:\Users\jonic\AppData\Roaming\Road to Vostok\vostok-vault-backups")
OUT_FILE = REPO_ROOT / "data" / "items.json"


def _item_name(res_path: str) -> str:
    return Path(res_path).stem.replace("_", " ")


def _category(res_path: str) -> str:
    m = re.match(r"res://Items/([^/]+)/", res_path)
    return m.group(1) if m else "Unknown"


def _subtree(res_path: str) -> str:
    m = re.match(r"(res://Items/[^/]+/)", res_path)
    return m.group(1) if m else ""


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


def scan_backups() -> dict[str, dict]:
    """Return dict keyed by res_path with merged data from all backups."""
    if not BACKUP_DIR.exists():
        print(f"ERROR: Backup directory not found: {BACKUP_DIR}", file=sys.stderr)
        sys.exit(1)

    item_re = re.compile(r'ExtResource\("([^"]+)"\)')
    slot_re = re.compile(r'^slot\s*=\s*"([^"]+)"')
    item_data_re = re.compile(r'^itemData\s*=\s*ExtResource\("([^"]+)"\)')

    results: dict[str, dict] = {}

    for backup in sorted(BACKUP_DIR.iterdir()):
        if not backup.is_dir():
            continue
        for tres in backup.glob("*.tres"):
            lines = tres.read_text(encoding="utf-8", errors="replace").splitlines()
            ext_map = _parse_ext_resources(lines)

            in_block = False
            current_item_ref: str | None = None
            current_slot: str | None = None

            for line in lines:
                s = line.strip()
                if s.startswith("[sub_resource"):
                    in_block = True
                    current_item_ref = None
                    current_slot = None
                    continue
                if in_block and s.startswith("[") and s.endswith("]"):
                    in_block = False
                    current_item_ref = None
                    current_slot = None
                    continue
                if not in_block:
                    continue

                m_item = item_data_re.match(s)
                if m_item:
                    ref = m_item.group(1)
                    path = ext_map.get(ref, "")
                    if path.startswith("res://Items/"):
                        current_item_ref = path

                m_slot = slot_re.match(s)
                if m_slot:
                    current_slot = m_slot.group(1)

                # End of logical block (empty line or new section)
                if s == "" and current_item_ref:
                    _record(results, current_item_ref, current_slot)
                    current_item_ref = None
                    current_slot = None

    return results


def _record(results: dict, res_path: str, slot: str | None) -> None:
    if res_path not in results:
        results[res_path] = {
            "res_path": res_path,
            "name": _item_name(res_path),
            "category": _category(res_path),
            "subtree": _subtree(res_path),
            "rarity": None,
            "seen_in_slots": [],
            "seen_count": 0,
        }
    entry = results[res_path]
    entry["seen_count"] += 1
    if slot and slot not in entry["seen_in_slots"]:
        entry["seen_in_slots"].append(slot)


def load_existing() -> dict[str, dict]:
    if not OUT_FILE.exists():
        return {}
    try:
        data = json.loads(OUT_FILE.read_text(encoding="utf-8"))
        return {item["res_path"]: item for item in data.get("items", [])}
    except Exception as e:
        print(f"Warning: could not load existing {OUT_FILE}: {e}", file=sys.stderr)
        return {}


def main() -> None:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    print("Scanning backup saves...")
    scanned = scan_backups()

    existing = load_existing()

    # Merge: update seen_count and seen_in_slots; preserve manually set rarity
    for res_path, entry in scanned.items():
        if res_path in existing:
            old = existing[res_path]
            old["seen_count"] = entry["seen_count"]
            # merge slots without losing manually added ones
            for slot in entry["seen_in_slots"]:
                if slot not in old["seen_in_slots"]:
                    old["seen_in_slots"].append(slot)
        else:
            existing[res_path] = entry

    items = sorted(existing.values(), key=lambda x: (x["category"], x["name"]))

    output = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "backup save scan — rarity=null (in encrypted PCK, not accessible)",
        "total": len(items),
        "items": items,
    }

    OUT_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Written {len(items)} items to {OUT_FILE}")

    by_cat: dict[str, int] = {}
    for item in items:
        by_cat[item["category"]] = by_cat.get(item["category"], 0) + 1
    print("\nBy category:")
    for cat, count in sorted(by_cat.items()):
        print(f"  {cat:20s}  {count}")


if __name__ == "__main__":
    main()
