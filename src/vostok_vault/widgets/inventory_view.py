import json
import logging

import customtkinter as ctk

from ..fonts import get_font
from ..paths import ICONS_DIR, ITEMS_JSON

log = logging.getLogger(__name__)

_RARITY_COLOURS: dict[str, tuple[str, str]] = {
    "rare": ("#2471A3", "#5DADE2"),
    "legendary": ("#B7770D", "#F0B027"),
}

_ITEM_RARITY: dict[str, str] = {}
_ITEM_DISPLAY_NAME: dict[str, str] = {}
_ITEM_WEIGHT: dict[str, float] = {}
_ITEM_CATEGORY: dict[str, str] = {}
_ITEM_ICON_FILE: dict[str, str] = {}
_ITEM_ICON_CACHE: dict[str, ctk.CTkImage] = {}
_RARITY_LOADED = False


def _ensure_rarity_loaded() -> None:
    global _RARITY_LOADED
    if _RARITY_LOADED:
        return
    _RARITY_LOADED = True
    if not ITEMS_JSON.exists():
        return
    try:
        data = json.loads(ITEMS_JSON.read_text(encoding="utf-8"))
        for item in data.get("items", []):
            key = item.get("id", "").replace("_", " ")
            _ITEM_RARITY[key] = item.get("rarity") or "common"
            _ITEM_DISPLAY_NAME[key] = item.get("display_name") or key
            _ITEM_WEIGHT[key] = float(item.get("weight") or 0.0)
            _ITEM_CATEGORY[key] = item.get("category") or ""
            if item.get("icon_file"):
                _ITEM_ICON_FILE[key] = item["icon_file"]
    except Exception:
        pass


def available_categories() -> list[str]:
    """Return sorted list of category names present in items.json."""
    _ensure_rarity_loaded()
    return sorted(set(v for v in _ITEM_CATEGORY.values() if v))


def _rarity_color(name: str) -> tuple[str, str] | None:
    _ensure_rarity_loaded()
    return _RARITY_COLOURS.get(_ITEM_RARITY.get(name, "common"))


def display_name(stem: str) -> str:
    """Return the human-readable display name for a stem-key, falling back to the stem."""
    _ensure_rarity_loaded()
    name = _ITEM_DISPLAY_NAME.get(stem)
    if name is None:
        log.debug("Unknown item stem: %s", stem)
        return stem
    return name


def item_weight(stem: str) -> float:
    _ensure_rarity_loaded()
    return _ITEM_WEIGHT.get(stem, 0.0)


def rarity_counts(stems: list[str]) -> dict[str, int]:
    """Return counts of legendary/rare/common for a list of item stem keys."""
    _ensure_rarity_loaded()
    counts: dict[str, int] = {"legendary": 0, "rare": 0, "common": 0}
    for stem in stems:
        r = _ITEM_RARITY.get(stem, "common")
        if r in counts:
            counts[r] += 1
        else:
            counts["common"] += 1
    return counts


def _get_icon(stem: str) -> ctk.CTkImage | None:
    if stem in _ITEM_ICON_CACHE:
        return _ITEM_ICON_CACHE[stem]
    _ensure_rarity_loaded()
    icon_file = _ITEM_ICON_FILE.get(stem)
    if not icon_file:
        return None
    icon_path = ICONS_DIR / icon_file
    if not icon_path.exists():
        return None
    try:
        from PIL import Image

        img = Image.open(icon_path).resize((44, 44), Image.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(44, 44))
        _ITEM_ICON_CACHE[stem] = ctk_img
        return ctk_img
    except Exception:
        return None


class InventoryTable(ctk.CTkFrame):
    """Reusable grid table for inventory items."""

    HEADERS = ["Slot", "Item", "Condition", "Amount"]
    COL_WIDTHS = [130, 250, 90, 65]

    def __init__(self, parent, **kwargs) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)

    def populate(self, items: list[dict]) -> None:
        for w in self.winfo_children():
            w.destroy()

        font = get_font()

        if not items:
            ctk.CTkLabel(
                self,
                text="No items found.",
                text_color=("gray65", "gray65"),
                font=ctk.CTkFont(family=font, size=13),
            ).pack(pady=10)
            return

        header_row = ctk.CTkFrame(self, fg_color=("gray80", "#1A1A2E"), corner_radius=4)
        header_row.pack(fill="x", padx=2, pady=(2, 0))
        for col, (h, w) in enumerate(zip(self.HEADERS, self.COL_WIDTHS)):
            ctk.CTkLabel(
                header_row,
                text=h,
                font=ctk.CTkFont(family=font, size=13, weight="bold"),
                width=w,
                anchor="w",
            ).grid(row=0, column=col, padx=6, pady=5, sticky="w")

        _ensure_rarity_loaded()

        for item in items:
            cond = f"{item['condition']}%" if item.get("condition") is not None else "—"
            item_stem = item.get("item_name", "")
            rarity = _ITEM_RARITY.get(item_stem, "common")
            name_color = _RARITY_COLOURS.get(rarity)
            icon = _get_icon(item_stem)
            shown_name = display_name(item_stem)
            row_frame = ctk.CTkFrame(self, fg_color="transparent")
            row_frame.pack(fill="x", padx=2, pady=3)

            slot_val = item.get("slot", "")
            amt_val = (
                "—" if item.get("amount", 1) in (0, 1) else str(item.get("amount", 1))
            )

            for col, (val, w) in enumerate(
                zip([slot_val, shown_name, cond, amt_val], self.COL_WIDTHS)
            ):
                if col == 1:
                    cell = ctk.CTkFrame(row_frame, fg_color="transparent")
                    cell.grid(row=0, column=col, padx=6, pady=3, sticky="w")
                    if rarity in _RARITY_COLOURS:
                        ctk.CTkLabel(
                            cell,
                            text="●",
                            font=ctk.CTkFont(family=font, size=9),
                            text_color=_RARITY_COLOURS[rarity],
                        ).pack(side="left", padx=(0, 4))
                    if icon:
                        ctk.CTkLabel(cell, image=icon, text="").pack(
                            side="left", padx=(0, 4)
                        )
                    name_kw: dict = {
                        "font": ctk.CTkFont(family=font, size=14),
                        "anchor": "w",
                    }
                    if name_color:
                        name_kw["text_color"] = name_color
                    ctk.CTkLabel(cell, text=val, **name_kw).pack(side="left")
                else:
                    ctk.CTkLabel(
                        row_frame,
                        text=val,
                        font=ctk.CTkFont(family=font, size=14),
                        width=w,
                        anchor="w",
                    ).grid(row=0, column=col, padx=6, pady=4, sticky="w")

            for att in item.get("attachments", []):
                att_row = ctk.CTkFrame(self, fg_color="transparent")
                att_row.pack(fill="x", padx=2, pady=0)
                ctk.CTkLabel(
                    att_row,
                    text="",
                    width=self.COL_WIDTHS[0],
                ).grid(row=0, column=0, padx=6)
                ctk.CTkLabel(
                    att_row,
                    text=f"  ↳ {display_name(att)}",
                    font=ctk.CTkFont(family=font, size=13),
                    text_color=("gray65", "gray65"),
                    anchor="w",
                ).grid(row=0, column=1, padx=6, sticky="w")
