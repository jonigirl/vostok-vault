"""
Check roadtovostok.wiki for updates to the item data stored in data/items.json.

Fetches each item page and compares wiki_name, rarity, and price_euros against
the current database. Reports any differences to stdout. Optionally writes
changes back with --update.

roadtovostok.wiki is an independent community resource and is not affiliated
with Road to Vostok Ltd. This script is for personal, non-commercial use only.
Scrapes politely with delays — do not modify to bypass rate limiting.

Usage:
    uv run python scripts/check_wiki_updates.py
    uv run python scripts/check_wiki_updates.py --update
"""

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).parent.parent
DB_FILE = REPO_ROOT / "data" / "items.json"
WIKI_BASE = "https://roadtovostok.wiki/items"

# Realistic Chrome 124 on Windows 11.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
}


def _make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(_HEADERS)
    # Warm up the session with the items index — sets any cookies Cloudflare
    # might plant before we start hitting individual pages.
    try:
        s.get(WIKI_BASE, timeout=15)
    except requests.RequestException:
        pass
    return s


def _pause() -> None:
    """Random human-paced delay between requests."""
    time.sleep(random.uniform(2.0, 4.5))


def _fetch(session: requests.Session, slug: str) -> str | None:
    url = f"{WIKI_BASE}/{slug}"
    try:
        resp = session.get(
            url,
            timeout=15,
            headers={"Referer": WIKI_BASE},
        )
        if resp.status_code == 200:
            return resp.text
        print(f"  [SKIP] {slug} — HTTP {resp.status_code}")
        return None
    except requests.RequestException as exc:
        print(f"  [ERROR] {slug} — {exc}")
        return None


def _parse_wiki_name(html: str) -> str | None:
    m = re.search(r"<h1[^>]*>\s*([^<]+?)\s*</h1>", html, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _parse_rarity(html: str) -> str | None:
    # CSS class pattern: text-rarity-common / text-rarity-rare / text-rarity-legendary
    m = re.search(r"text-rarity-(common|rare|legendary)", html)
    return m.group(1) if m else None


def _parse_price(html: str) -> int | None:
    # Appears in the meta description: "Stats: value 250€, ..."
    m = re.search(r"[Vv]alue[:\s]+(\d+)\s*€", html)
    return int(m.group(1)) if m else None


def _diff(name: str, field: str, old, new) -> str:
    return f"  {name!r}  {field}: {old!r} → {new!r}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--update",
        action="store_true",
        help="Write changes back to items.json",
    )
    args = parser.parse_args()

    if not DB_FILE.exists():
        print(f"ERROR: {DB_FILE} not found — run build_item_db.py first")
        sys.exit(1)

    db = json.loads(DB_FILE.read_text(encoding="utf-8"))
    items: list[dict] = db["items"]
    to_check = [i for i in items if i.get("wiki_slug")]
    print(f"Checking {len(to_check)} items with wiki slugs …\n")

    session = _make_session()
    diffs: list[str] = []
    changed_items: list[dict] = []

    for idx, item in enumerate(to_check, 1):
        slug: str = item["wiki_slug"]
        name: str = item["name"]
        print(f"[{idx}/{len(to_check)}] {name} ({slug})", end=" … ", flush=True)

        html = _fetch(session, slug)
        if html is None:
            print()
            _pause()
            continue

        wiki_name = _parse_wiki_name(html)
        rarity = _parse_rarity(html)
        price = _parse_price(html)

        item_diffs: list[str] = []
        if wiki_name and wiki_name != item.get("wiki_name"):
            item_diffs.append(
                _diff(name, "wiki_name", item.get("wiki_name"), wiki_name)
            )
        if rarity and rarity != item.get("rarity"):
            item_diffs.append(_diff(name, "rarity", item.get("rarity"), rarity))
        if price is not None and price != item.get("price_euros"):
            item_diffs.append(
                _diff(name, "price_euros", item.get("price_euros"), price)
            )

        if item_diffs:
            print("CHANGED")
            diffs.extend(item_diffs)
            if args.update:
                if wiki_name:
                    item["wiki_name"] = wiki_name
                if rarity:
                    item["rarity"] = rarity
                if price is not None:
                    item["price_euros"] = price
                changed_items.append(item)
        else:
            print("ok")

        if idx < len(to_check):
            _pause()

    print()
    if diffs:
        print(f"{'─' * 60}")
        print(f"Found {len(diffs)} change(s):")
        for line in diffs:
            print(line)
        print(f"{'─' * 60}")
        if args.update and changed_items:
            DB_FILE.write_text(
                json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(f"\nUpdated {len(changed_items)} item(s) in {DB_FILE.name}")
        else:
            print("\nRun with --update to apply changes.")
    else:
        print("No changes found — items.json is up to date.")


if __name__ == "__main__":
    main()
