import json
from pathlib import Path

import pytest

import vostok_vault.widgets.inventory_view as iv

MOCK_ITEMS = {
    "items": [
        {
            "id": "Coffee_Brewed",
            "display_name": "Coffee (Brewed)",
            "rarity": None,
            "weight": 0.2,
            "icon_file": None,
            "category": "Consumables",
        },
        {
            "id": "AK_74",
            "display_name": "AK-74",
            "rarity": "rare",
            "weight": 3.5,
            "icon_file": None,
            "category": "Weapon",
        },
        {
            "id": "Gold_Bar",
            "display_name": "Gold Bar",
            "rarity": "legendary",
            "weight": 1.0,
            "icon_file": None,
            "category": "Valuable",
        },
    ]
}


@pytest.fixture(autouse=True)
def reset_item_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    items_json = tmp_path / "items.json"
    items_json.write_text(json.dumps(MOCK_ITEMS), encoding="utf-8")
    monkeypatch.setattr(iv, "ITEMS_JSON", items_json)
    monkeypatch.setattr(iv, "_RARITY_LOADED", False)
    monkeypatch.setattr(iv, "_ITEM_RARITY", {})
    monkeypatch.setattr(iv, "_ITEM_DISPLAY_NAME", {})
    monkeypatch.setattr(iv, "_ITEM_WEIGHT", {})
    monkeypatch.setattr(iv, "_ITEM_CATEGORY", {})
    monkeypatch.setattr(iv, "_ITEM_ICON_FILE", {})
    monkeypatch.setattr(iv, "_ITEM_ICON_CACHE", {})


# ---------------------------------------------------------------------------
# display_name
# ---------------------------------------------------------------------------


def test_display_name_known_rare() -> None:
    assert iv.display_name("AK 74") == "AK-74"


def test_display_name_known_legendary() -> None:
    assert iv.display_name("Gold Bar") == "Gold Bar"


def test_display_name_null_rarity_item() -> None:
    assert iv.display_name("Coffee Brewed") == "Coffee (Brewed)"


def test_display_name_unknown_returns_stem() -> None:
    assert iv.display_name("Mystery Item") == "Mystery Item"


def test_display_name_unknown_empty_stem() -> None:
    assert iv.display_name("") == ""


# ---------------------------------------------------------------------------
# item_weight
# ---------------------------------------------------------------------------


def test_item_weight_known_rare() -> None:
    assert iv.item_weight("AK 74") == pytest.approx(3.5)


def test_item_weight_known_legendary() -> None:
    assert iv.item_weight("Gold Bar") == pytest.approx(1.0)


def test_item_weight_null_rarity_item() -> None:
    assert iv.item_weight("Coffee Brewed") == pytest.approx(0.2)


def test_item_weight_missing_returns_zero() -> None:
    assert iv.item_weight("Does Not Exist") == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# rarity_counts
# ---------------------------------------------------------------------------


def test_rarity_counts_empty() -> None:
    assert iv.rarity_counts([]) == {"legendary": 0, "rare": 0, "common": 0}


def test_rarity_counts_single_legendary() -> None:
    counts = iv.rarity_counts(["Gold Bar"])
    assert counts["legendary"] == 1
    assert counts["rare"] == 0
    assert counts["common"] == 0


def test_rarity_counts_single_rare() -> None:
    counts = iv.rarity_counts(["AK 74"])
    assert counts["rare"] == 1


def test_rarity_counts_null_rarity_counted_as_common() -> None:
    counts = iv.rarity_counts(["Coffee Brewed"])
    assert counts["common"] == 1


def test_rarity_counts_unknown_stem_counted_as_common() -> None:
    counts = iv.rarity_counts(["No Such Item"])
    assert counts["common"] == 1


def test_rarity_counts_mixed() -> None:
    stems = ["AK 74", "Gold Bar", "Coffee Brewed", "Unknown Item"]
    counts = iv.rarity_counts(stems)
    assert counts["legendary"] == 1
    assert counts["rare"] == 1
    assert counts["common"] == 2


# ---------------------------------------------------------------------------
# _rarity_color
# ---------------------------------------------------------------------------


def test_rarity_color_rare() -> None:
    color = iv._rarity_color("AK 74")
    assert color == ("#2471A3", "#5DADE2")


def test_rarity_color_legendary() -> None:
    color = iv._rarity_color("Gold Bar")
    assert color == ("#B7770D", "#F0B027")


def test_rarity_color_common_returns_none() -> None:
    assert iv._rarity_color("Coffee Brewed") is None


def test_rarity_color_unknown_returns_none() -> None:
    assert iv._rarity_color("Mystery Item") is None


# ---------------------------------------------------------------------------
# available_categories
# ---------------------------------------------------------------------------


def test_available_categories_returns_sorted_list() -> None:
    cats = iv.available_categories()
    assert cats == sorted(cats)


def test_available_categories_contains_mock_values() -> None:
    cats = iv.available_categories()
    assert "Consumables" in cats
    assert "Weapon" in cats
    assert "Valuable" in cats


def test_available_categories_no_duplicates() -> None:
    cats = iv.available_categories()
    assert len(cats) == len(set(cats))
