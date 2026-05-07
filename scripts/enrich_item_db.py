"""
Enrich data/items.json with wiki data and cross-reference fields.

Sources (all May 2026):
  roadtovostok.wiki/items         — prices, rarity, wiki names/slugs
  roadtovostok.wiki/crafting      — crafting recipe ingredients
  roadtovostok.wiki/traders/*     — trader task deliver requirements

Fields added / updated per item:
  rarity       : "common" | "rare" | "legendary" | null
  wiki_name    : canonical display name from roadtovostok.wiki
  wiki_slug    : URL slug (roadtovostok.wiki/items/<slug>); null if no page
  price_euros  : base sell price at 100% condition; null if unknown
  fits         : weapon wiki_names this attachment mounts on; null otherwise
  crafted_into : recipe names where this item is a consumed ingredient; null
  trader_tasks : "Trader/Task" strings where this item is a deliver requirement
  data_source  : "save+wiki" if wiki-matched; "save" if found in saves only

Unmatched items are reported to stdout; wiki fields default to null.
Save-derived fields (res_path, name, category, seen_count, …) are never
ovewritten — saves are the authoritative source for structural identity.

Usage:
    uv run python scripts/enrich_item_db.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
OUT_FILE = REPO_ROOT / "data" / "items.json"

# Each entry: {wiki_name, rarity, wiki_slug, price_euros, fits}
# Keyed by the `name` field as it appears in items.json (stem with _ → space).
#
# fits: list of weapon wiki_names (roadtovostok.wiki display names) this
#       attachment mounts on. null for non-attachment items.
# price_euros: base sell price at 100% condition per roadtovostok.wiki.
_W = dict  # alias to keep line lengths down

_WIKI: dict[str, dict] = {
    # ── Ammo ──────────────────────────────────────────────────────────────────
    "Ammo 12x70": _W(
        wiki_name="12/70",
        rarity="common",
        wiki_slug="ammo-ammo-12x70",
        price_euros=200,
        fits=None,
    ),
    "Ammo 223": _W(
        wiki_name=".223",
        rarity="common",
        wiki_slug="ammo-ammo-223",
        price_euros=300,
        fits=None,
    ),
    "Ammo 45ACP": _W(
        wiki_name=".45 ACP",
        rarity="common",
        wiki_slug="ammo-ammo-45acp",
        price_euros=250,
        fits=None,
    ),
    "Ammo 545x39": _W(
        wiki_name="5.45x39",
        rarity="common",
        wiki_slug="ammo-ammo-545x39",
        price_euros=325,
        fits=None,
    ),
    "Ammo 762x39": _W(
        wiki_name="7.62x39",
        rarity="common",
        wiki_slug="ammo-ammo-762x39",
        price_euros=350,
        fits=None,
    ),
    "Ammo 9x18": _W(
        wiki_name="9x18",
        rarity="common",
        wiki_slug="ammo-ammo-9x18",
        price_euros=200,
        fits=None,
    ),
    "Ammo 9x19": _W(
        wiki_name="9x19",
        rarity="common",
        wiki_slug="ammo-ammo-9x19",
        price_euros=250,
        fits=None,
    ),
    # ── Attachments ───────────────────────────────────────────────────────────
    # fits lists use wiki display names from roadtovostok.wiki
    "Kobra": _W(
        wiki_name="Kobra",
        rarity="rare",
        wiki_slug="attachment-kobra",
        price_euros=350,
        fits=[
            "KA-12",
            "KA-M",
            "KAS-74U",
            "KAR-21 (.223)",
            "KAR-21 (.308)",
            "KM18",
            "PM5",
            "PM5-K",
            "PM5-SD",
            "PM7",
            "RK-95",
            "VSD",
            "SSV",
        ],
    ),
    "Micro": _W(
        wiki_name="Micro",
        rarity="rare",
        wiki_slug="attachment-micro",
        price_euros=450,
        fits=[
            "KA-12",
            "KA-M",
            "KAS-74U",
            "KAR-21 (.223)",
            "KAR-21 (.308)",
            "KM18",
            "PM5",
            "PM5-K",
            "PM5-SD",
            "PM7",
            "RK-95",
            "VSD",
            "SSV",
        ],
    ),
    # Monster: suppressor for KAR-21/KM18/RK-95 — not yet on roadtovostok.wiki;
    # confirmed by namu.wiki equipment page. All other suppressors are Rare.
    "Monster": _W(
        wiki_name="Monster",
        rarity="rare",
        wiki_slug=None,
        price_euros=820,
        fits=["KAR-21 (.223)", "KAR-21 (.308)", "KM18", "RK-95"],
    ),
    "PU": _W(
        wiki_name="PU Scope",
        rarity="rare",
        wiki_slug="attachment-pu",
        price_euros=400,
        fits=["Mosin"],
    ),
    # ── Backpacks ─────────────────────────────────────────────────────────────
    "Duffel Retro": _W(
        wiki_name="Duffel (Retro)",
        rarity="common",
        wiki_slug="backpack-duffel-retro",
        price_euros=75,
        fits=None,
    ),
    # ── Belts ─────────────────────────────────────────────────────────────────
    "Kukkaro Black": _W(
        wiki_name="Kukkaro (Black)",
        rarity="common",
        wiki_slug="belt-pouch-kukkaro-black",
        price_euros=70,
        fits=None,
    ),
    # ── Books ─────────────────────────────────────────────────────────────────
    "Book Children": _W(
        wiki_name="Book (Children)",
        rarity="common",
        wiki_slug="book-book-children",
        price_euros=50,
        fits=None,
    ),
    "Book Cooking": _W(
        wiki_name="Book (Cooking)",
        rarity="common",
        wiki_slug="book-book-cooking",
        price_euros=50,
        fits=None,
    ),
    "Book Fishing": _W(
        wiki_name="Book (Fishing)",
        rarity="common",
        wiki_slug="book-book-fishing",
        price_euros=50,
        fits=None,
    ),
    "Book Religion": _W(
        wiki_name="Book (Religion)",
        rarity="common",
        wiki_slug="book-book-religion",
        price_euros=50,
        fits=None,
    ),
    # ── Clothing ──────────────────────────────────────────────────────────────
    "Boots Combat": _W(
        wiki_name="Combat Boots",
        rarity="common",
        wiki_slug="clothing-boots-combat",
        price_euros=160,
        fits=None,
    ),
    "Cap M62": _W(
        wiki_name="M62 Cap",
        rarity="common",
        wiki_slug="clothing-cap-m62",
        price_euros=75,
        fits=None,
    ),
    "Fleece Tactical Green": _W(
        wiki_name="Tactical Fleece (Green)",
        rarity="common",
        wiki_slug="clothing-fleece-tactical-green",
        price_euros=80,
        fits=None,
    ),
    "Gloves Leather": _W(
        wiki_name="Leather Gloves",
        rarity="common",
        wiki_slug="clothing-gloves-leather",
        price_euros=25,
        fits=None,
    ),
    "Gloves Work": _W(
        wiki_name="Work Gloves",
        rarity="common",
        wiki_slug="clothing-gloves-work",
        price_euros=15,
        fits=None,
    ),
    "Jacket M62": _W(
        wiki_name="M62 Jacket",
        rarity="common",
        wiki_slug="clothing-jacket-m62",
        price_euros=125,
        fits=None,
    ),
    "Pants Hiking": _W(
        wiki_name="Hiking Pants",
        rarity="common",
        wiki_slug="clothing-pants-hiking",
        price_euros=40,
        fits=None,
    ),
    # ── Consumables ───────────────────────────────────────────────────────────
    "Beer": _W(
        wiki_name="Beer",
        rarity="rare",
        wiki_slug="consumable-beer",
        price_euros=250,
        fits=None,
    ),
    "Can Empty": _W(
        wiki_name="Empty Can",
        rarity="common",
        wiki_slug="consumable-can-empty",
        price_euros=5,
        fits=None,
    ),
    "Canned Pea Soup": _W(
        wiki_name="Canned Pea Soup",
        rarity="common",
        wiki_slug="consumable-canned-pea-soup",
        price_euros=100,
        fits=None,
    ),
    "Canned Pear": _W(
        wiki_name="Canned Pear",
        rarity="common",
        wiki_slug="consumable-canned-pear",
        price_euros=120,
        fits=None,
    ),
    "Canned Peas": _W(
        wiki_name="Canned Peas",
        rarity="common",
        wiki_slug="consumable-canned-peas",
        price_euros=80,
        fits=None,
    ),
    "Canned Tuna": _W(
        wiki_name="Canned Tuna",
        rarity="common",
        wiki_slug="consumable-canned-tuna",
        price_euros=60,
        fits=None,
    ),
    "Cigarettes": _W(
        wiki_name="Cigarettes",
        rarity="rare",
        wiki_slug="consumable-cigarettes",
        price_euros=125,
        fits=None,
    ),
    "Juice Orange": _W(
        wiki_name="Juice (Orange)",
        rarity="common",
        wiki_slug="consumable-juice-orange",
        price_euros=50,
        fits=None,
    ),
    "Juice Raspberry": _W(
        wiki_name="Juice (Raspberry)",
        rarity="common",
        wiki_slug="consumable-juice-raspberry",
        price_euros=50,
        fits=None,
    ),
    "Potato": _W(
        wiki_name="Potato",
        rarity="common",
        wiki_slug="consumable-potato",
        price_euros=10,
        fits=None,
    ),
    "Soda Lemon": _W(
        wiki_name="Soda (Lemon)",
        rarity="rare",
        wiki_slug="consumable-soda-lemon",
        price_euros=100,
        fits=None,
    ),
    "Sugar": _W(
        wiki_name="Sugar",
        rarity="common",
        wiki_slug="consumable-sugar",
        price_euros=120,
        fits=None,
    ),
    "Yeast": _W(
        wiki_name="Yeast",
        rarity="common",
        wiki_slug="consumable-yeast",
        price_euros=25,
        fits=None,
    ),
    # ── Electronics ───────────────────────────────────────────────────────────
    "Alarm Clock": _W(
        wiki_name="Alarm Clock",
        rarity="common",
        wiki_slug="electronics-alarm-clock",
        price_euros=150,
        fits=None,
    ),
    "Batteries": _W(
        wiki_name="Batteries",
        rarity="rare",
        wiki_slug="electronics-batteries",
        price_euros=100,
        fits=None,
    ),
    "Battery Cables": _W(
        wiki_name="Battery Cables",
        rarity="common",
        wiki_slug="electronics-battery-cables",
        price_euros=50,
        fits=None,
    ),
    "Casette Symphony": _W(
        wiki_name="Casette (Symphony)",
        rarity="rare",
        wiki_slug="electronics-casette-symphony",
        price_euros=150,
        fits=None,
    ),
    "Coffeemaster": _W(
        wiki_name="Coffeemaster",
        rarity="legendary",
        wiki_slug="electronics-coffeemaster",
        price_euros=2250,
        fits=None,
    ),
    "Hotplate": _W(
        wiki_name="Hotplate",
        rarity="common",
        wiki_slug="electronics-hotplate",
        price_euros=250,
        fits=None,
    ),
    "Narva": _W(
        wiki_name="Narva",
        rarity="common",
        wiki_slug="electronics-narva",
        price_euros=180,
        fits=None,
    ),
    # ── Knives ────────────────────────────────────────────────────────────────
    "Jaeger 140": _W(
        wiki_name="Jaeger 140",
        rarity="common",
        wiki_slug="knife-jaeger-140",
        price_euros=150,
        fits=None,
    ),
    # ── Medical ───────────────────────────────────────────────────────────────
    "Antibiotics": _W(
        wiki_name="Antibiotics",
        rarity="rare",
        wiki_slug="medical-antibiotics",
        price_euros=250,
        fits=None,
    ),
    "Antiseptic": _W(
        wiki_name="Antiseptic",
        rarity="rare",
        wiki_slug="medical-antiseptic",
        price_euros=250,
        fits=None,
    ),
    "Balm": _W(
        wiki_name="Balm",
        rarity="common",
        wiki_slug="medical-balm",
        price_euros=85,
        fits=None,
    ),
    "Bandage": _W(
        wiki_name="Bandage",
        rarity="common",
        wiki_slug="medical-bandage",
        price_euros=150,
        fits=None,
    ),
    "Gum": _W(
        wiki_name="Gum",
        rarity="common",
        wiki_slug="medical-gum",
        price_euros=40,
        fits=None,
    ),
    "Lotion": _W(
        wiki_name="Lotion",
        rarity="common",
        wiki_slug="medical-lotion",
        price_euros=75,
        fits=None,
    ),
    "Melatonin": _W(
        wiki_name="Melatonin",
        rarity="common",
        wiki_slug="medical-melatonin",
        price_euros=75,
        fits=None,
    ),
    "Painkillers": _W(
        wiki_name="Painkillers",
        rarity="common",
        wiki_slug="medical-painkillers",
        price_euros=150,
        fits=None,
    ),
    "Tissues": _W(
        wiki_name="Tissues",
        rarity="common",
        wiki_slug="medical-tissues",
        price_euros=50,
        fits=None,
    ),
    "Tourniquet": _W(
        wiki_name="Tourniquet",
        rarity="common",
        wiki_slug="medical-tourniquet",
        price_euros=150,
        fits=None,
    ),
    # ── Misc ──────────────────────────────────────────────────────────────────
    "Board Game": _W(
        wiki_name="Board Game",
        rarity="rare",
        wiki_slug="misc-board-game",
        price_euros=140,
        fits=None,
    ),
    "Bucket": _W(
        wiki_name="Bucket",
        rarity="common",
        wiki_slug="misc-bucket",
        price_euros=25,
        fits=None,
    ),
    "Jerry Can": _W(
        wiki_name="Jerry Can",
        rarity="rare",
        wiki_slug="misc-jerry-can",
        price_euros=120,
        fits=None,
    ),
    "Map": _W(
        wiki_name="Map", rarity="rare", wiki_slug="misc-map", price_euros=250, fits=None
    ),
    "Matches": _W(
        wiki_name="Matches",
        rarity="common",
        wiki_slug="misc-matches",
        price_euros=20,
        fits=None,
    ),
    "Nails": _W(
        wiki_name="Nails",
        rarity="common",
        wiki_slug="misc-nails",
        price_euros=50,
        fits=None,
    ),
    "Rags": _W(
        wiki_name="Rags",
        rarity="common",
        wiki_slug="misc-rags",
        price_euros=20,
        fits=None,
    ),
    "Sticks": _W(
        wiki_name="Sticks",
        rarity="common",
        wiki_slug="misc-sticks",
        price_euros=25,
        fits=None,
    ),
    # ── Rigs ──────────────────────────────────────────────────────────────────
    "Vest Fishing": _W(
        wiki_name="Fishing Vest",
        rarity="common",
        wiki_slug="rig-vest-fishing",
        price_euros=140,
        fits=None,
    ),
    # ── Weapons (includes magazines stored under Weapons/ in saves) ───────────
    "AKM": _W(
        wiki_name="KA-M",
        rarity="common",
        wiki_slug="weapon-akm",
        price_euros=1200,
        fits=None,
    ),
    "MP5 Magazine": _W(
        wiki_name="PM5 Magazine",
        rarity="common",
        wiki_slug="attachment-mp5-magazine",
        price_euros=60,
        fits=["PM5", "PM5-K", "PM5-SD"],
    ),
    "MP5K": _W(
        wiki_name="PM5-K",
        rarity="common",
        wiki_slug="weapon-mp5k",
        price_euros=1850,
        fits=None,
    ),
    "Mosin": _W(
        wiki_name="Mosin",
        rarity="common",
        wiki_slug="weapon-mosin",
        price_euros=450,
        fits=None,
    ),
    "RK Magazine": _W(
        wiki_name="RK Magazine",
        rarity="common",
        wiki_slug="attachment-rk-magazine",
        price_euros=120,
        fits=["RK-62", "RK-95", "RK-62M"],
    ),
}

# Items that are consumed ingredients in crafting recipes.
# Source: roadtovostok.wiki/crafting (May 2026, consumables tab).
_CRAFTED_INTO: dict[str, list[str]] = {
    "Bucket": ["Kilju"],
    "Canned Pea Soup": ["Pea Soup (Cooked)"],
    "Canned Pear": ["Kompot"],
    "Potato": ["Fish Soup (Cooked)"],
    "Sugar": ["Kilju", "Kompot"],
    "Yeast": ["Kilju"],
}

# Items required as DELIVER items in trader tasks.
# Format: "Trader/Task name" — source: roadtovostok.wiki/traders/* (May 2026).
_TRADER_TASKS: dict[str, list[str]] = {
    "AKM": ["Gunsmith/Weapon Delivery"],
    "Antibiotics": ["Doctor/Infections"],
    "Antiseptic": ["Doctor/Infections"],
    "Batteries": ["Doctor/Night Surgery"],
    "Battery Cables": ["Generalist/Road Trip"],
    "Beer": ["Generalist/Six Pack"],
    "Board Game": ["Doctor/Dice Master"],
    "Book Children": ["Doctor/Bookworm"],
    "Book Cooking": ["Doctor/Bookworm"],
    "Book Fishing": ["Doctor/Bookworm"],
    "Book Religion": ["Doctor/Bookworm"],
    "Bucket": ["Generalist/Handyman"],
    "Cigarettes": ["Generalist/Bad Habits"],
    "Jerry Can": ["Generalist/Road Trip"],
    "Lotion": ["Generalist/Backpains"],
    "Matches": ["Generalist/Bad Habits"],
    "Nails": ["Generalist/Handyman"],
    "Painkillers": ["Generalist/Backpains"],
}


def main() -> None:
    if not OUT_FILE.exists():
        print(f"ERROR: {OUT_FILE} not found — run build_item_db.py first")
        return

    db = json.loads(OUT_FILE.read_text(encoding="utf-8"))
    items: list[dict] = db["items"]

    matched = 0
    unmatched: list[str] = []

    for item in items:
        name: str = item["name"]
        entry = _WIKI.get(name)
        if entry is None:
            unmatched.append(f"  {name!r}  [{item['category']}]  {item['res_path']}")
            # Save data is authoritative for structural fields; add wiki defaults.
            item.setdefault("wiki_name", None)
            item.setdefault("wiki_slug", None)
            item.setdefault("price_euros", None)
            item.setdefault("fits", None)
            item.setdefault("crafted_into", _CRAFTED_INTO.get(name))
            item.setdefault("trader_tasks", _TRADER_TASKS.get(name))
            item["data_source"] = "save"
            continue

        # Only overwrite rarity if it was null (don't clobber manual edits).
        # Save-observed rarity (future) would already be set and is kept.
        if item.get("rarity") is None:
            item["rarity"] = entry["rarity"]
        item["wiki_name"] = entry["wiki_name"]
        item["wiki_slug"] = entry["wiki_slug"]
        item["price_euros"] = entry["price_euros"]
        item["fits"] = entry["fits"]
        item["crafted_into"] = _CRAFTED_INTO.get(name)
        item["trader_tasks"] = _TRADER_TASKS.get(name)
        item["data_source"] = "save+wiki"
        matched += 1

    db["source"] = "backup save scan + roadtovostok.wiki enrichment (May 2026)"
    db["generated"] = datetime.now(timezone.utc).isoformat()

    OUT_FILE.write_text(json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Enriched {matched}/{len(items)} items.")
    if unmatched:
        print(f"\nNo wiki match for {len(unmatched)} item(s) — rarity left null:")
        for line in unmatched:
            print(line)


if __name__ == "__main__":
    main()
