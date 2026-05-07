import customtkinter as ctk

from ..fonts import get_font

# Rarity colouring: (light_mode_colour, dark_mode_colour).
# "common" items use the default text colour — no entry needed.
_RARITY_COLOURS: dict[str, tuple[str, str]] = {
    "rare": ("#2471A3", "#5DADE2"),
    "legendary": ("#B7770D", "#F0B027"),
}

# Rarity lookup keyed by item_name as it appears in save files.
# Source: roadtovostok.wiki/items + namu.wiki (May 2026).
_ITEM_RARITY: dict[str, str] = {
    "Alarm Clock": "common",
    "AKM": "common",
    "Ammo 12x70": "common",
    "Ammo 223": "common",
    "Ammo 45ACP": "common",
    "Ammo 545x39": "common",
    "Ammo 762x39": "common",
    "Ammo 9x18": "common",
    "Ammo 9x19": "common",
    "Antibiotics": "rare",
    "Antiseptic": "rare",
    "Balm": "common",
    "Bandage": "common",
    "Batteries": "rare",
    "Battery Cables": "common",
    "Beer": "rare",
    "Board Game": "rare",
    "Book Children": "common",
    "Book Cooking": "common",
    "Book Fishing": "common",
    "Book Religion": "common",
    "Boots Combat": "common",
    "Bucket": "common",
    "Can Empty": "common",
    "Canned Pea Soup": "common",
    "Canned Pear": "common",
    "Canned Peas": "common",
    "Canned Tuna": "common",
    "Cap M62": "common",
    "Casette Symphony": "rare",
    "Cigarettes": "rare",
    "Coffeemaster": "legendary",
    "Duffel Retro": "common",
    "Fleece Tactical Green": "common",
    "Gloves Leather": "common",
    "Gloves Work": "common",
    "Gum": "common",
    "Hotplate": "common",
    "Jacket M62": "common",
    "Jaeger 140": "common",
    "Jerry Can": "rare",
    "Juice Orange": "common",
    "Juice Raspberry": "common",
    "Kobra": "rare",
    "Kukkaro Black": "common",
    "Lotion": "common",
    "Map": "rare",
    "Matches": "common",
    "Melatonin": "common",
    "Micro": "rare",
    "Monster": "rare",
    "Mosin": "common",
    "MP5 Magazine": "common",
    "MP5K": "common",
    "Nails": "common",
    "Narva": "common",
    "Painkillers": "common",
    "Pants Hiking": "common",
    "Potato": "common",
    "PU": "rare",
    "Rags": "common",
    "RK Magazine": "common",
    "Soda Lemon": "rare",
    "Sticks": "common",
    "Sugar": "common",
    "Tissues": "common",
    "Tourniquet": "common",
    "Vest Fishing": "common",
    "Yeast": "common",
}


def _rarity_color(name: str) -> tuple[str, str] | None:
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
