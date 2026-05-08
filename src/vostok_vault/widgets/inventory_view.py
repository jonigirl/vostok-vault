import json

import customtkinter as ctk

from ..fonts import get_font
from ..paths import ITEMS_JSON

# Rarity colouring: (light_mode_colour, dark_mode_colour).
# "common" items use the default text colour — no entry needed.
_RARITY_COLOURS: dict[str, tuple[str, str]] = {
    "rare": ("#2471A3", "#5DADE2"),
    "legendary": ("#B7770D", "#F0B027"),
}

# Lazily-populated rarity lookup keyed by item stem-name (id with _ → space).
_ITEM_RARITY: dict[str, str] = {}
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
            rarity = item.get("rarity") or "common"
            _ITEM_RARITY[key] = rarity
    except Exception:
        pass


def _rarity_color(name: str) -> tuple[str, str] | None:
    _ensure_rarity_loaded()
    return _RARITY_COLOURS.get(_ITEM_RARITY.get(name, "common"))


class InventoryTable(ctk.CTkFrame):
    """Reusable grid table for inventory items."""

    HEADERS = ["Slot", "Item", "Condition", "Amount"]
    COL_WIDTHS = [130, 230, 90, 65]

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
                text_color=("gray55", "gray55"),
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

        for item in items:
            cond = f"{item['condition']}%" if item.get("condition") is not None else "—"
            item_name = item.get("item_name", "")
            name_color = _rarity_color(item_name)
            row_frame = ctk.CTkFrame(self, fg_color="transparent")
            row_frame.pack(fill="x", padx=2, pady=1)
            for col, (val, w) in enumerate(
                zip(
                    [
                        item.get("slot", ""),
                        item_name,
                        cond,
                        "—"
                        if item.get("amount", 1) in (0, 1)
                        else str(item.get("amount", 1)),
                    ],
                    self.COL_WIDTHS,
                )
            ):
                label_kwargs: dict = {}
                if col == 1 and name_color:
                    label_kwargs["text_color"] = name_color
                ctk.CTkLabel(
                    row_frame,
                    text=val,
                    font=ctk.CTkFont(family=font, size=13),
                    width=w,
                    anchor="w",
                    **label_kwargs,
                ).grid(row=0, column=col, padx=6, pady=3, sticky="w")

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
                    text=f"  ↳ {att}",
                    font=ctk.CTkFont(family=font, size=13),
                    text_color=("gray55", "gray55"),
                    anchor="w",
                ).grid(row=0, column=1, padx=6, sticky="w")
