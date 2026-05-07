from pathlib import Path

import customtkinter as ctk

from ..config import DIFFICULTY_NAMES, SEASON_NAMES, get_font
from ..tres_parser import parse_character, parse_storage
from .inventory_view import InventoryTable


class SaveDetailPanel(ctk.CTkFrame):
    def __init__(self, parent, **kwargs) -> None:
        super().__init__(parent, corner_radius=8, **kwargs)
        self._current: dict | None = None
        self._build()

    def _build(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._tabs = ctk.CTkTabview(self, anchor="nw")
        self._tabs.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        for name in ("Overview", "Character", "Storage", "Mods"):
            tab = self._tabs.add(name)
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_columnconfigure(0, weight=1)

        self._overview_scroll = ctk.CTkScrollableFrame(self._tabs.tab("Overview"))
        self._overview_scroll.grid(row=0, column=0, sticky="nsew")
        self._overview_scroll.grid_columnconfigure(1, weight=1)

        self._char_scroll = ctk.CTkScrollableFrame(self._tabs.tab("Character"))
        self._char_scroll.grid(row=0, column=0, sticky="nsew")

        self._storage_scroll = ctk.CTkScrollableFrame(self._tabs.tab("Storage"))
        self._storage_scroll.grid(row=0, column=0, sticky="nsew")

        self._mods_scroll = ctk.CTkScrollableFrame(self._tabs.tab("Mods"))
        self._mods_scroll.grid(row=0, column=0, sticky="nsew")

        self._show_placeholder()

    def _clear(self, frame: ctk.CTkScrollableFrame) -> None:
        for w in frame.winfo_children():
            w.destroy()

    def _show_placeholder(self) -> None:
        font = get_font()
        for frame in (
            self._overview_scroll,
            self._char_scroll,
            self._storage_scroll,
            self._mods_scroll,
        ):
            self._clear(frame)
        ctk.CTkLabel(
            self._overview_scroll,
            text="Select a backup from the list to view details.",
            font=ctk.CTkFont(family=font, size=14),
            text_color=("gray55", "gray55"),
        ).pack(pady=60)

    def show_backup(self, data: dict | None) -> None:
        self._current = data
        if not data:
            self._show_placeholder()
            return
        self._populate_overview(data)
        self._populate_character(data)
        self._populate_storage(data)
        self._populate_mods(data)

    def _populate_overview(self, data: dict) -> None:
        self._clear(self._overview_scroll)
        font = get_font()
        f = self._overview_scroll

        def info_row(label: str, value: str, row: int) -> None:
            ctk.CTkLabel(
                f,
                text=label,
                font=ctk.CTkFont(family=font, size=13, weight="bold"),
                anchor="e",
                width=110,
            ).grid(row=row, column=0, sticky="e", padx=(12, 6), pady=5)
            ctk.CTkLabel(
                f,
                text=value,
                font=ctk.CTkFont(family=font, size=14),
                anchor="w",
            ).grid(row=row, column=1, sticky="w", padx=(0, 12), pady=5)

        info_row("Tag", data.get("tag", "—"), 0)
        info_row("Created", data.get("created", "—")[:16].replace("T", " "), 1)
        info_row("Day", str(data.get("game_day", "?")), 2)
        info_row("Time", data.get("game_time", "??:??"), 3)

        season_raw = data.get("season", "?")
        info_row("Season", SEASON_NAMES.get(season_raw, str(season_raw)), 4)
        info_row("Weather", str(data.get("weather", "?")), 5)

        diff_raw = data.get("difficulty", "?")
        info_row("Difficulty", DIFFICULTY_NAMES.get(diff_raw, str(diff_raw)), 6)

        ctk.CTkLabel(
            f,
            text="Active Mods",
            font=ctk.CTkFont(family=font, size=14, weight="bold"),
            anchor="w",
        ).grid(row=7, column=0, columnspan=2, sticky="w", padx=12, pady=(16, 4))

        mods = [m for m in data.get("mods", []) if m.get("enabled")]
        if mods:
            chips_frame = ctk.CTkFrame(f, fg_color="transparent")
            chips_frame.grid(
                row=8, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 12)
            )
            for mod in mods:
                chip_text = (
                    f"{mod.get('name', mod.get('id', '?'))}  {mod.get('version', '')}"
                )
                ctk.CTkLabel(
                    chips_frame,
                    text=chip_text,
                    font=ctk.CTkFont(family=font, size=13),
                    fg_color=("gray80", "#2E3A50"),
                    corner_radius=10,
                    padx=10,
                    pady=3,
                ).pack(side="left", padx=4, pady=2)
        else:
            ctk.CTkLabel(
                f,
                text="No active mods",
                font=ctk.CTkFont(family=font, size=13),
                text_color=("gray55", "gray55"),
                anchor="w",
            ).grid(row=8, column=0, columnspan=2, sticky="w", padx=12)

    def _populate_character(self, data: dict) -> None:
        self._clear(self._char_scroll)
        font = get_font()
        f = self._char_scroll

        backup_path = Path(data.get("_path", ""))
        char_file = backup_path / "Character.tres"
        items = parse_character(char_file)

        if not char_file.exists():
            ctk.CTkLabel(
                f,
                text="[missing] — Character.tres not found in this backup.",
                font=ctk.CTkFont(family=font, size=13),
                text_color=("gray55", "gray55"),
            ).pack(pady=20)
            return

        if not items:
            ctk.CTkLabel(
                f,
                text="No equipped items found.",
                font=ctk.CTkFont(family=font, size=13),
                text_color=("gray55", "gray55"),
            ).pack(pady=20)
            return

        slot_order = [
            "Head",
            "Chest",
            "Legs",
            "Hands",
            "Feet",
            "Primary",
            "Secondary",
            "Knife",
            "Backpack",
            "Rig",
            "Belt",
            "Pocket1",
            "Pocket2",
            "Storage",
        ]
        order_map = {s: i for i, s in enumerate(slot_order)}
        items_sorted = sorted(items, key=lambda x: order_map.get(x["slot"], 99))

        table = InventoryTable(f)
        table.pack(fill="x", padx=4, pady=4)
        table.populate(items_sorted)

    def _populate_storage(self, data: dict) -> None:
        self._clear(self._storage_scroll)
        font = get_font()
        f = self._storage_scroll
        backup_path = Path(data.get("_path", ""))

        for filename in ("Cabin.tres", "Tent.tres"):
            storage_path = backup_path / filename
            label = filename.replace(".tres", "")

            ctk.CTkLabel(
                f,
                text=label,
                font=ctk.CTkFont(family=font, size=14, weight="bold"),
                anchor="w",
            ).pack(fill="x", padx=10, pady=(12, 4))

            if not storage_path.exists():
                ctk.CTkLabel(
                    f,
                    text="[missing]",
                    font=ctk.CTkFont(family=font, size=13),
                    text_color=("gray55", "gray55"),
                    anchor="w",
                ).pack(fill="x", padx=20, pady=(0, 4))
                continue

            items = parse_storage(storage_path)
            if not items:
                ctk.CTkLabel(
                    f,
                    text="Empty",
                    font=ctk.CTkFont(family=font, size=13),
                    text_color=("gray55", "gray55"),
                    anchor="w",
                ).pack(fill="x", padx=20, pady=(0, 4))
                continue

            for item in items:
                cond = (
                    f"{item['condition']}%"
                    if item.get("condition") is not None
                    else "—"
                )
                line = f"{item['item_name']}  ×{item['amount']}  {cond}"
                ctk.CTkLabel(
                    f,
                    text=line,
                    font=ctk.CTkFont(family=font, size=13),
                    anchor="w",
                ).pack(fill="x", padx=20, pady=2)

    def _populate_mods(self, data: dict) -> None:
        self._clear(self._mods_scroll)
        font = get_font()
        f = self._mods_scroll
        mods = data.get("mods", [])

        if not mods:
            ctk.CTkLabel(
                f,
                text="No mod data recorded in this backup.",
                font=ctk.CTkFont(family=font, size=13),
                text_color=("gray55", "gray55"),
            ).pack(pady=20)
            return

        headers = ["Name", "Version", "Enabled"]
        col_widths = [220, 110, 80]

        header_row = ctk.CTkFrame(f, fg_color=("gray80", "#1A1A2E"), corner_radius=4)
        header_row.pack(fill="x", padx=4, pady=(4, 0))
        for col, (h, w) in enumerate(zip(headers, col_widths)):
            ctk.CTkLabel(
                header_row,
                text=h,
                font=ctk.CTkFont(family=font, size=13, weight="bold"),
                width=w,
                anchor="w",
            ).grid(row=0, column=col, padx=6, pady=5, sticky="w")

        for mod in mods:
            row_frame = ctk.CTkFrame(f, fg_color="transparent")
            row_frame.pack(fill="x", padx=4, pady=1)
            enabled = mod.get("enabled", False)
            enabled_str = "Yes" if enabled else "No"
            enabled_color = ("#2ECC71", "#27AE60") if enabled else ("gray55", "gray55")
            name = mod.get("name", mod.get("id", "?"))
            version = mod.get("version", "?")
            for col, (val, w) in enumerate(
                zip([name, version, enabled_str], col_widths)
            ):
                kwargs: dict = {}
                if col == 2:
                    kwargs["text_color"] = enabled_color
                ctk.CTkLabel(
                    row_frame,
                    text=val,
                    font=ctk.CTkFont(family=font, size=13),
                    width=w,
                    anchor="w",
                    **kwargs,
                ).grid(row=0, column=col, padx=6, pady=3, sticky="w")
