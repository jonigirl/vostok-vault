"""
Scan all backup .tres files and produce a report of:
- All unique item paths (res://Items/...)
- All unique item subtrees
- All unique slot names seen in Character.tres
- All save fields seen in World.tres, Traders.tres, Validator.tres
- Gaps: item subtrees in saves that are missing from _ITEM_SUBTREES allow-list
"""

import re
from pathlib import Path

BACKUP_DIR = Path(r"C:\Users\jonic\AppData\Roaming\Road to Vostok\vostok-vault-backups")

CURRENT_SUBTREES = {
    "res://Items/Weapons/",
    "res://Items/Ammo/",
    "res://Items/Clothing/",
    "res://Items/Equipment/",
    "res://Items/Food/",
    "res://Items/Medical/",
    "res://Items/Misc/",
    "res://Items/Tools/",
    "res://Items/Containers/",
    "res://Items/Keys/",
}

item_paths: set[str] = set()
slot_names: set[str] = set()
world_fields: set[str] = set()
trader_fields: set[str] = set()
validator_fields: set[str] = set()
all_subtrees: set[str] = set()
non_item_res_paths: set[str] = set()

path_re = re.compile(r'path="(res://[^"]+)"')
slot_re = re.compile(r'^slot\s*=\s*"([^"]+)"')
field_re = re.compile(r"^(\w+)\s*=")

for backup in sorted(BACKUP_DIR.iterdir()):
    if not backup.is_dir():
        continue
    for tres in backup.glob("*.tres"):
        text = tres.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()

        # Collect all res:// paths
        for m in path_re.finditer(text):
            p = m.group(1)
            if p.startswith("res://Items/"):
                item_paths.add(p)
                m2 = re.match(r"(res://Items/[^/]+/)", p)
                if m2:
                    all_subtrees.add(m2.group(1))
            elif not p.startswith("res://Scripts/"):
                non_item_res_paths.add(p)

        # Collect slot names from Character.tres
        if tres.name == "Character.tres":
            for line in lines:
                m3 = slot_re.match(line.strip())
                if m3:
                    slot_names.add(m3.group(1))

        # Collect World.tres resource fields
        if tres.name == "World.tres":
            in_resource = False
            for line in lines:
                s = line.strip()
                if s == "[resource]":
                    in_resource = True
                    continue
                if in_resource:
                    m4 = field_re.match(s)
                    if m4:
                        world_fields.add(m4.group(1))

        # Collect Traders.tres resource fields
        if tres.name == "Traders.tres":
            in_resource = False
            for line in lines:
                s = line.strip()
                if s == "[resource]":
                    in_resource = True
                    continue
                if in_resource:
                    m5 = field_re.match(s)
                    if m5:
                        trader_fields.add(m5.group(1))

        # Collect Validator.tres resource fields
        if tres.name == "Validator.tres":
            in_resource = False
            for line in lines:
                s = line.strip()
                if s == "[resource]":
                    in_resource = True
                    continue
                if in_resource:
                    m6 = field_re.match(s)
                    if m6:
                        validator_fields.add(m6.group(1))


print("=" * 60)
print("ITEM SUBTREES SEEN IN ALL BACKUPS")
print("=" * 60)
for s in sorted(all_subtrees):
    in_list = (
        "  [in allow-list]"
        if s in CURRENT_SUBTREES
        else "  *** MISSING FROM ALLOW-LIST ***"
    )
    print(f"  {s}{in_list}")

print()
print("=" * 60)
print(f"ALL UNIQUE ITEM PATHS ({len(item_paths)} total)")
print("=" * 60)
for p in sorted(item_paths):
    print(f"  {p}")

print()
print("=" * 60)
print("NON-ITEM, NON-SCRIPT res:// PATHS (clothing/backpacks/etc)")
print("=" * 60)
for p in sorted(non_item_res_paths):
    print(f"  {p}")

print()
print("=" * 60)
print("SLOT NAMES SEEN IN Character.tres")
print("=" * 60)
for s in sorted(slot_names):
    print(f"  {s}")

print()
print("=" * 60)
print("World.tres [resource] FIELDS")
print("=" * 60)
for f in sorted(world_fields):
    print(f"  {f}")

print()
print("=" * 60)
print("Traders.tres [resource] FIELDS")
print("=" * 60)
for f in sorted(trader_fields):
    print(f"  {f}")

print()
print("=" * 60)
print("Validator.tres [resource] FIELDS")
print("=" * 60)
for f in sorted(validator_fields):
    print(f"  {f}")
