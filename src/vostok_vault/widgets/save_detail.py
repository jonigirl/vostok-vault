import logging
import threading
import time
from pathlib import Path

import customtkinter as ctk

from ..backup import format_backup_date
from ..constants import DIFFICULTY_NAMES, SEASON_NAMES
from ..fonts import get_font
from ..mcm_parser import parse_mcm_configs
from ..paths import SHELTER_NAMES
from ..tres_parser import (
    load_trader_task_catalog,
    parse_character,
    parse_storage,
    parse_traders,
    parse_validator,
    parse_world,
)
from .inventory_view import (
    _ITEM_CATEGORY,
    _ITEM_RARITY,
    InventoryTable,
    available_categories,
    display_name,
    item_weight,
    rarity_counts,
)

log = logging.getLogger(__name__)

_SLOT_GROUP: dict[str, str] = {
    "Head": "Armour",
    "Chest": "Armour",
    "Torso": "Armour",
    "Legs": "Armour",
    "Hands": "Armour",
    "Feet": "Armour",
    "Primary": "Weapons",
    "Secondary": "Weapons",
    "Knife": "Weapons",
    "Backpack": "Gear",
    "Rig": "Gear",
    "Belt": "Gear",
    "Light": "Gear",
    "Time": "Gear",
    "Pocket1": "Pockets",
    "Pocket2": "Pockets",
    "Storage": "Storage",
}

_MOD_DISPLAY_NAMES: dict[str, str] = {
    "CT-map": "Collapsed Tunnels",
    "elegant-hud": "Elegant HUD",
    "road-to-vostok-enemy-ai": "Faction Warfare + More Enemies",
    "feel": "FEEL",
    "xp-skills-system": "XP & Skills System",
    "doinkoink-mcm": "Mod Configuration Menu",
}


def _format_weather_time(secs: float) -> str:
    mins = int(secs / 60)
    if mins < 60:
        return f"{mins} min"
    return f"{mins // 60}h {mins % 60}m"


class SaveDetailPanel(ctk.CTkFrame):
    def __init__(self, parent, **kwargs) -> None:
        super().__init__(parent, corner_radius=8, **kwargs)
        self._current: dict | None = None
        self._storage_expanded: dict[str, bool] = {}
        self._char_expanded: dict[str, bool] = {}
        self._mcm_expanded: dict[str, bool] = {}
        self._traders_expanded: dict[str, bool] = {}
        self._storage_sort_key: str = "Name"
        self._storage_sort_reverse: bool = False
        self._storage_category_var: ctk.StringVar | None = None
        self._storage_category_menu: ctk.CTkOptionMenu | None = None
        self._cached_path: str = ""
        self._cached_validator: dict = {}
        self._cached_world: dict = {}
        self._cached_char: list = []
        self._cached_shelters: dict[str, list] = {}
        self._cached_traders: dict = {}
        self._cached_mcm: dict = {}
        self._tabs_populated: set[str] = set()
        self._build()

    def _build(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        font = get_font()

        self._tabs = ctk.CTkTabview(self, anchor="nw")
        self._tabs.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        for name in ("Overview", "Character", "Storage", "Traders", "Mods"):
            tab = self._tabs.add(name)
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_columnconfigure(0, weight=1)

        self._overview_scroll = ctk.CTkScrollableFrame(self._tabs.tab("Overview"))
        self._overview_scroll.grid(row=0, column=0, sticky="nsew")
        self._overview_scroll.grid_columnconfigure(1, weight=1)

        char_tab = self._tabs.tab("Character")
        char_tab.grid_rowconfigure(0, weight=0)
        char_tab.grid_rowconfigure(1, weight=1)
        _collapse_btn_opts = dict(
            width=110,
            height=26,
            font=ctk.CTkFont(family=font, size=12),
            fg_color=("gray80", "gray25"),
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray35"),
        )
        char_header = ctk.CTkFrame(char_tab, fg_color="transparent", height=32)
        char_header.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
        self._char_collapse_btn = ctk.CTkButton(
            char_header,
            text="\u229f Collapse All",
            command=self._on_char_collapse_all,
            **_collapse_btn_opts,
        )
        self._char_collapse_btn.pack(side="right", padx=4)
        self._char_scroll = ctk.CTkScrollableFrame(char_tab)
        self._char_scroll.grid(row=1, column=0, sticky="nsew")

        storage_tab = self._tabs.tab("Storage")
        storage_tab.grid_rowconfigure(0, weight=0)
        storage_tab.grid_rowconfigure(1, weight=0)
        storage_tab.grid_rowconfigure(2, weight=0)
        storage_tab.grid_rowconfigure(3, weight=1)
        storage_tab.grid_columnconfigure(0, weight=1)

        self._storage_filter_var = ctk.StringVar()
        self._storage_filter_entry = ctk.CTkEntry(
            storage_tab,
            placeholder_text="Filter items…",
            textvariable=self._storage_filter_var,
            font=ctk.CTkFont(family=font, size=13),
            height=32,
            corner_radius=4,
        )
        self._storage_filter_entry.grid(
            row=0, column=0, sticky="ew", padx=8, pady=(8, 4)
        )
        self._storage_filter_var.trace_add("write", self._on_storage_filter_change)

        cat_frame = ctk.CTkFrame(storage_tab, fg_color="transparent")
        cat_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))
        ctk.CTkLabel(
            cat_frame,
            text="Category:",
            font=ctk.CTkFont(family=font, size=13),
            text_color=("gray50", "gray60"),
        ).pack(side="left", padx=(0, 6))
        self._storage_category_var = ctk.StringVar(value="All")
        self._storage_category_menu = ctk.CTkOptionMenu(
            cat_frame,
            values=["All"],
            variable=self._storage_category_var,
            font=ctk.CTkFont(family=font, size=13),
            width=160,
            command=self._on_storage_category_change,
        )
        self._storage_category_menu.pack(side="left")

        sort_frame = ctk.CTkFrame(storage_tab, fg_color="transparent")
        sort_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 4))
        ctk.CTkLabel(
            sort_frame,
            text="Sort:",
            font=ctk.CTkFont(family=font, size=13),
            text_color=("gray50", "gray60"),
        ).pack(side="left", padx=(0, 6))
        self._storage_sort_seg = ctk.CTkSegmentedButton(
            sort_frame,
            values=["Name", "Weight", "Condition", "Amount", "Rarity"],
            command=self._on_storage_sort_key_change,
            font=ctk.CTkFont(family=font, size=12),
            height=28,
        )
        self._storage_sort_seg.set("Name")
        self._storage_sort_seg.pack(side="left")
        self._storage_sort_dir_btn = ctk.CTkButton(
            sort_frame,
            text="\u2191 Asc",
            width=68,
            height=28,
            font=ctk.CTkFont(family=font, size=12),
            fg_color=("gray80", "gray25"),
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray35"),
            command=self._on_storage_sort_toggle,
        )
        self._storage_sort_dir_btn.pack(side="left", padx=(6, 0))
        self._storage_collapse_btn = ctk.CTkButton(
            sort_frame,
            text="\u229f Collapse All",
            command=self._on_storage_collapse_all,
            **_collapse_btn_opts,
        )
        self._storage_collapse_btn.pack(side="right", padx=(6, 0))

        self._storage_scroll = ctk.CTkScrollableFrame(storage_tab)
        self._storage_scroll.grid(row=3, column=0, sticky="nsew")

        traders_tab = self._tabs.tab("Traders")
        traders_tab.grid_rowconfigure(0, weight=0)
        traders_tab.grid_rowconfigure(1, weight=1)
        traders_header = ctk.CTkFrame(traders_tab, fg_color="transparent", height=32)
        traders_header.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
        self._traders_collapse_btn = ctk.CTkButton(
            traders_header,
            text="\u229f Collapse All",
            command=self._on_traders_collapse_all,
            **_collapse_btn_opts,
        )
        self._traders_collapse_btn.pack(side="right", padx=4)
        self._traders_scroll = ctk.CTkScrollableFrame(traders_tab)
        self._traders_scroll.grid(row=1, column=0, sticky="nsew")

        mods_tab = self._tabs.tab("Mods")
        mods_tab.grid_rowconfigure(0, weight=0)
        mods_tab.grid_rowconfigure(1, weight=1)
        mods_header = ctk.CTkFrame(mods_tab, fg_color="transparent", height=32)
        mods_header.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
        self._mods_collapse_btn = ctk.CTkButton(
            mods_header,
            text="\u229f Collapse All",
            command=self._on_mods_collapse_all,
            **_collapse_btn_opts,
        )
        self._mods_collapse_btn.pack(side="right", padx=4)
        self._mods_scroll = ctk.CTkScrollableFrame(mods_tab)
        self._mods_scroll.grid(row=1, column=0, sticky="nsew")

        self._tabs.configure(command=self._on_tab_changed)

        self._show_placeholder()

    def _clear(self, frame: ctk.CTkScrollableFrame) -> None:
        for w in frame.winfo_children():
            w.destroy()

    def _show_placeholder(self) -> None:
        self._tabs_populated.clear()
        font = get_font()
        for frame in (
            self._overview_scroll,
            self._char_scroll,
            self._storage_scroll,
            self._traders_scroll,
            self._mods_scroll,
        ):
            self._clear(frame)
        ctk.CTkLabel(
            self._overview_scroll,
            text="Select a backup from the list to view details.",
            font=ctk.CTkFont(family=font, size=14),
            text_color=("gray70", "gray70"),
        ).pack(pady=60)

    def _on_storage_filter_change(self, *_args) -> None:
        if self._current and self._cached_path:
            self._populate_storage(self._current)

    def _on_storage_category_change(self, _value: str) -> None:
        if self._current and self._cached_path:
            self._populate_storage(self._current)

    def _on_storage_sort_key_change(self, value: str) -> None:
        self._storage_sort_key = value
        if self._current:
            self._populate_storage(self._current)

    def _on_storage_sort_toggle(self) -> None:
        self._storage_sort_reverse = not self._storage_sort_reverse
        self._storage_sort_dir_btn.configure(
            text="\u2193 Desc" if self._storage_sort_reverse else "\u2191 Asc"
        )
        if self._current:
            self._populate_storage(self._current)

    def _on_char_collapse_all(self) -> None:
        collapsing = self._char_collapse_btn.cget("text") == "\u229f Collapse All"
        for k in self._char_expanded:
            self._char_expanded[k] = not collapsing
        self._char_collapse_btn.configure(
            text="\u229e Expand All" if collapsing else "\u229f Collapse All"
        )
        if self._current:
            self._tabs_populated.discard("Character")
            self._populate_tab("Character", self._current)

    def _on_storage_collapse_all(self) -> None:
        collapsing = self._storage_collapse_btn.cget("text") == "\u229f Collapse All"
        for k in self._storage_expanded:
            self._storage_expanded[k] = not collapsing
        self._storage_collapse_btn.configure(
            text="\u229e Expand All" if collapsing else "\u229f Collapse All"
        )
        if self._current:
            self._populate_storage(self._current)

    def _on_traders_collapse_all(self) -> None:
        collapsing = self._traders_collapse_btn.cget("text") == "\u229f Collapse All"
        for k in self._traders_expanded:
            self._traders_expanded[k] = not collapsing
        self._traders_collapse_btn.configure(
            text="\u229e Expand All" if collapsing else "\u229f Collapse All"
        )
        if self._current:
            self._tabs_populated.discard("Traders")
            self._populate_tab("Traders", self._current)

    def _on_mods_collapse_all(self) -> None:
        collapsing = self._mods_collapse_btn.cget("text") == "\u229f Collapse All"
        for k in self._mcm_expanded:
            self._mcm_expanded[k] = not collapsing
        self._mods_collapse_btn.configure(
            text="\u229e Expand All" if collapsing else "\u229f Collapse All"
        )
        if self._current:
            self._tabs_populated.discard("Mods")
            self._populate_tab("Mods", self._current)

    def _on_tab_changed(self) -> None:
        if not self._current or not self._cached_path:
            return
        tab = self._tabs.get()
        if tab not in self._tabs_populated:
            self._populate_tab(tab, self._current)

    def show_backup(self, data: dict | None) -> None:
        self._current = data
        if not data:
            self._show_placeholder()
            return
        cats = available_categories()
        if self._storage_category_menu is not None:
            self._storage_category_menu.configure(values=["All"] + cats)
            if self._storage_category_var.get() not in (["All"] + cats):
                self._storage_category_var.set("All")
        self._show_loading()
        threading.Thread(target=self._parse_backup, args=(data,), daemon=True).start()

    def _show_loading(self) -> None:
        font = get_font()
        self._tabs_populated.clear()
        for frame in (
            self._overview_scroll,
            self._char_scroll,
            self._storage_scroll,
            self._traders_scroll,
            self._mods_scroll,
        ):
            self._clear(frame)
            ctk.CTkLabel(
                frame,
                text="Loading\u2026",
                font=ctk.CTkFont(family=font, size=14),
                text_color=("gray70", "gray70"),
            ).pack(pady=60)

    def _parse_backup(self, data: dict) -> None:
        backup_path = Path(data.get("_path", ""))
        t0 = time.perf_counter()
        validator = parse_validator(backup_path / "Validator.tres")
        world = parse_world(backup_path / "World.tres")
        char_items = parse_character(backup_path / "Character.tres")
        shelters = {
            name: parse_storage(backup_path / f"{name}.tres") for name in SHELTER_NAMES
        }
        traders = parse_traders(backup_path / "Traders.tres")
        mcm = parse_mcm_configs(backup_path / "MCM")
        t1 = time.perf_counter()
        log.debug("_parse_backup: %.3fs", t1 - t0)
        self._cached_path = str(backup_path)
        self._cached_validator = validator
        self._cached_world = world
        self._cached_char = char_items
        self._cached_shelters = shelters
        self._cached_traders = traders
        self._cached_mcm = mcm
        self.after(0, lambda: self._render_parsed(data))

    def _render_parsed(self, data: dict) -> None:
        if self._current is not data:
            return
        active_tab = self._tabs.get()
        self._populate_tab(active_tab, data)

    def _populate_tab(self, tab: str, data: dict) -> None:
        t0 = time.perf_counter()
        if tab == "Overview":
            self._populate_overview(data)
        elif tab == "Character":
            self._populate_character(data)
        elif tab == "Storage":
            self._populate_storage(data)
        elif tab == "Traders":
            self._populate_traders(data)
        elif tab == "Mods":
            self._populate_mods(data)
        else:
            return
        self._tabs_populated.add(tab)
        log.debug("_populate_tab %s: %.3fs", tab, time.perf_counter() - t0)

    def _populate_overview(self, data: dict) -> None:
        self._clear(self._overview_scroll)
        font = get_font()
        f = self._overview_scroll
        f.grid_columnconfigure(0, weight=0, minsize=110)

        def info_row(label: str, value: str, row: int) -> None:
            ctk.CTkLabel(
                f,
                text=label,
                font=ctk.CTkFont(family=font, size=13),
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=(12, 8), pady=(4, 2))
            ctk.CTkLabel(
                f,
                text=value,
                font=ctk.CTkFont(family=font, size=14, weight="bold"),
                anchor="w",
            ).grid(row=row, column=1, sticky="w", padx=(0, 12), pady=(4, 2))

        def section_heading(title: str, row: int) -> None:
            ctk.CTkLabel(
                f,
                text=title,
                font=ctk.CTkFont(family=font, size=11),
                text_color=("gray65", "gray65"),
                anchor="w",
            ).grid(row=row, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 2))

        row = 0
        info_row("Created", format_backup_date(data.get("created", "—")), row)
        row += 1

        section_heading("WORLD", row)
        row += 1
        info_row("Day", str(data.get("game_day", "?")), row)
        row += 1
        season_raw = data.get("season", "?")
        info_row("Season", SEASON_NAMES.get(season_raw, str(season_raw)), row)
        row += 1
        info_row("Time", data.get("game_time", "??:??"), row)
        row += 1
        info_row("Weather", str(data.get("weather", "?")), row)
        row += 1

        section_heading("PLAYER", row)
        row += 1
        diff_raw = data.get("difficulty", "?")
        info_row("Difficulty", DIFFICULTY_NAMES.get(diff_raw, str(diff_raw)), row)
        row += 1
        if diff_raw == 3:
            ctk.CTkLabel(
                f,
                text="⚠ Ironman — character is deleted on death",
                font=ctk.CTkFont(family=font, size=13),
                text_color=("#C0392B", "#E74C3C"),
                anchor="w",
            ).grid(row=row, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 4))
            row += 1

        validator = self._cached_validator
        if validator["player_id"]:
            info_row("Player ID", validator["player_id"], row)
            row += 1

        world = self._cached_world
        if world["shelters"] is not None:
            info_row("Shelters", str(world["shelters"]), row)
            row += 1
        if world["weather_time"] is not None:
            info_row("Weather in", _format_weather_time(world["weather_time"]), row)
            row += 1

        char_items_parsed = self._cached_char
        storage_items_parsed = [
            i for items in self._cached_shelters.values() for i in items
        ]

        char_weight = sum(
            item_weight(i["item_name"]) for i in char_items_parsed if i.get("item_name")
        )
        storage_weight = sum(
            item_weight(i["item_name"])
            for i in storage_items_parsed
            if i.get("item_name")
        )
        if char_weight > 0 or storage_weight > 0:
            info_row(
                "Carried / Stored",
                f"{char_weight:.1f} kg / {storage_weight:.1f} kg",
                row,
            )
            row += 1

        all_stems = [
            i["item_name"].replace("_", " ")
            for i in char_items_parsed + storage_items_parsed
            if i.get("item_name")
        ]
        if all_stems:
            counts = rarity_counts(all_stems)
            section_heading("INVENTORY RARITY", row)
            row += 1
            parts = []
            if counts["legendary"]:
                parts.append(f"{counts['legendary']} legendary")
            if counts["rare"]:
                parts.append(f"{counts['rare']} rare")
            if counts["common"]:
                parts.append(f"{counts['common']} common")
            if parts:
                info_row("Items", "  ·  ".join(parts), row)
                row += 1

        section_heading("ACTIVE MODS", row)
        row += 1

        mods = [m for m in data.get("mods", []) if m.get("enabled")]
        if mods:
            chips_frame = ctk.CTkFrame(f, fg_color="transparent")
            chips_frame.grid(
                row=row, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 12)
            )
            for i, mod in enumerate(mods):
                if i % 3 == 0:
                    row_frame = ctk.CTkFrame(chips_frame, fg_color="transparent")
                    row_frame.pack(fill="x", pady=0)
                chip_text = (
                    f"{mod.get('name', mod.get('id', '?'))}  {mod.get('version', '')}"
                )
                ctk.CTkLabel(
                    row_frame,
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
                text_color=("gray70", "gray70"),
                anchor="w",
            ).grid(row=row, column=0, columnspan=2, sticky="w", padx=12)

    def _populate_character(self, data: dict) -> None:
        self._clear(self._char_scroll)
        font = get_font()
        f = self._char_scroll

        items = self._cached_char
        if not (Path(data.get("_path", "")) / "Character.tres").exists():
            ctk.CTkLabel(
                f,
                text="[missing] — Character.tres not found in this backup.",
                font=ctk.CTkFont(family=font, size=13),
                text_color=("gray70", "gray70"),
            ).pack(pady=20)
            return

        if not items:
            ctk.CTkLabel(
                f,
                text="No equipped items found.",
                font=ctk.CTkFont(family=font, size=13),
                text_color=("gray70", "gray70"),
            ).pack(pady=20)
            return

        slot_order = [
            "Head",
            "Chest",
            "Torso",
            "Legs",
            "Hands",
            "Feet",
            "Primary",
            "Secondary",
            "Knife",
            "Backpack",
            "Rig",
            "Belt",
            "Light",
            "Time",
            "Pocket1",
            "Pocket2",
            "Storage",
        ]

        order_map = {s: i for i, s in enumerate(slot_order)}
        items_sorted = sorted(items, key=lambda x: order_map.get(x["slot"], 99))

        last_group = None
        group_items: list[dict] = []

        def flush_group(group: str, rows: list[dict]) -> None:
            if not rows:
                return
            group_key = group.lower()
            is_expanded = [self._char_expanded.get(group_key, True)]
            self._char_expanded[group_key] = is_expanded[0]
            header_text = group.upper()

            def make_char_toggle(btn, frame, flag, key, text):
                def _toggle():
                    if flag[0]:
                        frame.pack_forget()
                        btn.configure(text=f"\u25b6  {text}")
                        flag[0] = False
                    else:
                        frame.pack(fill="x", padx=4, pady=(0, 4))
                        btn.configure(text=f"\u25bc  {text}")
                        flag[0] = True
                    self._char_expanded[key] = flag[0]

                return _toggle

            section = ctk.CTkFrame(f, fg_color="transparent")
            section.pack(fill="x", padx=0, pady=0)
            expand_char = "\u25bc" if is_expanded[0] else "\u25b6"
            header_btn = ctk.CTkButton(
                section,
                text=f"{expand_char}  {header_text}",
                fg_color=("gray85", "#2A2A40"),
                hover_color=("gray78", "#32324E"),
                text_color=("gray10", "gray90"),
                anchor="w",
                corner_radius=4,
                font=ctk.CTkFont(family=font, size=11),
            )
            header_btn.pack(fill="x", padx=4, pady=(8, 0))
            content_frame = ctk.CTkFrame(section, fg_color="transparent")
            t = InventoryTable(content_frame)
            t.pack(fill="x", padx=4, pady=(0, 4))
            t.populate(rows)
            if is_expanded[0]:
                content_frame.pack(fill="x", padx=4, pady=(0, 4))
            header_btn.configure(
                command=make_char_toggle(
                    header_btn, content_frame, is_expanded, group_key, header_text
                )
            )

        for item in items_sorted:
            group = _SLOT_GROUP.get(item["slot"], "Other")
            if group != last_group:
                flush_group(last_group or "", group_items)
                group_items = []
                last_group = group
            group_items.append(item)
        flush_group(last_group or "", group_items)

        total = sum(item_weight(i["item_name"]) for i in items_sorted)
        if total > 0:
            ctk.CTkLabel(
                f,
                text=f"Total weight: {total:.1f} kg",
                font=ctk.CTkFont(family=font, size=13),
                text_color=("gray65", "gray65"),
                anchor="e",
            ).pack(fill="x", padx=16, pady=(4, 8))

    def _populate_storage(self, data: dict) -> None:
        self._clear(self._storage_scroll)
        font = get_font()
        f = self._storage_scroll
        backup_path = Path(data.get("_path", ""))
        if self._cached_path != str(backup_path):
            return
        filter_text = self._storage_filter_var.get().lower().strip()
        selected_cat = (
            self._storage_category_var.get() if self._storage_category_var else "All"
        )

        def make_toggle(btn, frame, flag, key, header_text):
            def _toggle():
                if flag[0]:
                    frame.pack_forget()
                    btn.configure(text=f"\u25b6  {header_text}")
                    flag[0] = False
                else:
                    frame.pack(fill="x", padx=4, pady=(0, 8))
                    btn.configure(text=f"\u25bc  {header_text}")
                    flag[0] = True
                self._storage_expanded[key] = flag[0]

            return _toggle

        def _sort_key(i: dict):
            name = display_name(i["item_name"]).lower()
            if self._storage_sort_key == "Weight":
                return (item_weight(i["item_name"]), name)
            if self._storage_sort_key == "Condition":
                cond = i.get("condition")
                return (float(cond) if cond is not None else 0.0, name)
            if self._storage_sort_key == "Amount":
                return (float(i.get("amount", 1) or 1), name)
            if self._storage_sort_key == "Rarity":
                _rarity_order = {"legendary": 0, "rare": 1, "common": 2}
                rarity = _ITEM_RARITY.get(i["item_name"])
                priority = _rarity_order.get(rarity, 3) if rarity is not None else 3
                return (priority, name)
            return (name, "")

        def _matches(i: dict) -> bool:
            if (
                filter_text
                and filter_text not in i["item_name"].lower()
                and filter_text not in display_name(i["item_name"]).lower()
            ):
                return False
            if (
                selected_cat != "All"
                and _ITEM_CATEGORY.get(i["item_name"]) != selected_cat
            ):
                return False
            return True

        active_filter = bool(filter_text or selected_cat != "All")

        for shelter_name in SHELTER_NAMES:
            all_items: list[dict] = self._cached_shelters.get(shelter_name, [])

            if not all_items:
                continue

            shelter_section = ctk.CTkFrame(f, fg_color="transparent")
            shelter_section.pack(fill="x", padx=0, pady=(4, 0))
            ctk.CTkLabel(
                shelter_section,
                text=shelter_name.upper(),
                font=ctk.CTkFont(family=font, size=11, weight="bold"),
                text_color=("gray55", "gray55"),
                anchor="w",
            ).pack(fill="x", padx=8, pady=(6, 2))

            # Group by container name; "" = floor/uncategorised
            containers: dict[str, list[dict]] = {}
            for item in all_items:
                key = item.get("container", "")
                containers.setdefault(key, []).append(item)

            shelter_total_weight: float = 0.0
            for container_label, raw_items in sorted(
                containers.items(), key=lambda kv: kv[0].lower() if kv[0] else "\xff"
            ):
                items = (
                    [i for i in raw_items if _matches(i)]
                    if active_filter
                    else raw_items
                )
                items = sorted(items, key=_sort_key, reverse=self._storage_sort_reverse)
                display_label = container_label if container_label else "Uncategorised"
                section_key = f"{shelter_name}:{display_label}"
                shown_count = (
                    f"  ({len(items)})" if items else ("  (0)" if active_filter else "")
                )
                header_text = f"{display_label}{shown_count}"

                section = ctk.CTkFrame(shelter_section, fg_color="transparent")
                section.pack(fill="x", padx=0, pady=0)

                header_btn = ctk.CTkButton(
                    section,
                    text=f"\u25b6  {header_text}",
                    fg_color=("gray85", "#2A2A40"),
                    hover_color=("gray78", "#32324E"),
                    text_color=("gray10", "gray90"),
                    anchor="w",
                    corner_radius=4,
                    font=ctk.CTkFont(family=font, size=13, weight="bold"),
                )
                header_btn.pack(fill="x", padx=4, pady=(4, 0))

                content_frame = ctk.CTkFrame(section, fg_color="transparent")

                if not items:
                    ctk.CTkLabel(
                        content_frame,
                        text="Empty" if not active_filter else "No matches",
                        font=ctk.CTkFont(family=font, size=13),
                        text_color=("gray70", "gray70"),
                        anchor="w",
                    ).pack(fill="x", padx=20, pady=(4, 4))
                else:
                    table_items = [
                        {
                            "slot": "",
                            "item_name": i["item_name"],
                            "condition": i["condition"],
                            "amount": i["amount"],
                            "attachments": [],
                        }
                        for i in items
                    ]
                    storage_table = InventoryTable(content_frame, show_slot=False)
                    storage_table.pack(fill="x", padx=8, pady=(4, 4))
                    storage_table.populate(table_items)
                    shelter_total_weight += sum(
                        item_weight(i["item_name"]) for i in items
                    )

                is_expanded = [
                    self._storage_expanded.get(section_key, bool(active_filter))
                ]
                self._storage_expanded[section_key] = is_expanded[0]
                if is_expanded[0]:
                    content_frame.pack(fill="x", padx=4, pady=(0, 4))
                    header_btn.configure(text=f"\u25bc  {header_text}")
                header_btn.configure(
                    command=make_toggle(
                        header_btn, content_frame, is_expanded, section_key, header_text
                    )
                )

            if shelter_total_weight > 0:
                ctk.CTkLabel(
                    shelter_section,
                    text=f"Total weight: {shelter_total_weight:.1f} kg",
                    font=ctk.CTkFont(family=font, size=13),
                    text_color=("gray65", "gray65"),
                    anchor="e",
                ).pack(fill="x", padx=16, pady=(0, 8))

    def _populate_traders(self, data: dict) -> None:
        self._clear(self._traders_scroll)
        font = get_font()
        f = self._traders_scroll
        backup_path = Path(data.get("_path", ""))
        traders_path = backup_path / "Traders.tres"

        if not traders_path.exists():
            ctk.CTkLabel(
                f,
                text="No Traders.tres in this backup.",
                font=ctk.CTkFont(family=font, size=13),
                text_color=("gray70", "gray70"),
            ).pack(pady=20)
            return

        completed: dict[str, list[str]] = self._cached_traders
        catalog: dict[str, dict] = load_trader_task_catalog()

        # Only show traders the player has encountered in this save
        if catalog:
            all_trader_keys = [k for k in catalog.keys() if k in completed]
        else:
            all_trader_keys = list(completed.keys())
        if not all_trader_keys:
            ctk.CTkLabel(
                f,
                text="No trader data found.",
                font=ctk.CTkFont(family=font, size=13),
                text_color=("gray70", "gray70"),
            ).pack(pady=20)
            return

        ctk.CTkLabel(
            f,
            text="Completed tasks per trader. Completing tasks reduces their trade tax.",
            font=ctk.CTkFont(family=font, size=12),
            text_color=("gray70", "gray70"),
            anchor="w",
            wraplength=400,
            justify="left",
        ).pack(fill="x", padx=8, pady=(8, 4))

        def make_traders_toggle(btn, frame, flag, key, header, count):
            def _toggle():
                if flag[0]:
                    frame.pack_forget()
                    btn.configure(text=f"\u25b6  {header}{count}")
                    flag[0] = False
                else:
                    frame.pack(fill="x", padx=4, pady=(0, 4))
                    btn.configure(text=f"\u25bc  {header}{count}")
                    flag[0] = True
                self._traders_expanded[key] = flag[0]

            return _toggle

        for trader_key in all_trader_keys:
            done_set = set(completed.get(trader_key, []))
            entry = catalog.get(trader_key, {})
            all_tasks = (
                entry.get("tasks", sorted(done_set)) if entry else sorted(done_set)
            )
            base_tax = entry.get("base_tax", 100) if entry else 100
            done_count = sum(1 for t in all_tasks if t in done_set)
            total_count = len(all_tasks)
            if total_count > 0:
                current_tax = (
                    round(base_tax * (1.0 - done_count / total_count) / 10) * 10
                )
            else:
                current_tax = base_tax
            header_text = trader_key.replace("_", " ").title()
            tax_text = f"Tax: {current_tax}%"
            count_text = f"  —  {tax_text}  ({done_count} / {total_count})"
            is_expanded = [self._traders_expanded.get(trader_key, False)]
            self._traders_expanded[trader_key] = is_expanded[0]
            expand_char = "\u25bc" if is_expanded[0] else "\u25b6"
            section = ctk.CTkFrame(f, fg_color="transparent")
            section.pack(fill="x", padx=0, pady=0)
            header_btn = ctk.CTkButton(
                section,
                text=f"{expand_char}  {header_text}{count_text}",
                fg_color=("gray85", "#2A2A40"),
                hover_color=("gray78", "#32324E"),
                text_color=("gray10", "gray90"),
                anchor="w",
                corner_radius=4,
                font=ctk.CTkFont(family=font, size=13, weight="bold"),
            )
            header_btn.pack(fill="x", padx=4, pady=(8, 0))
            content_frame = ctk.CTkFrame(section, fg_color="transparent")
            if not all_tasks:
                ctk.CTkLabel(
                    content_frame,
                    text="No tasks available",
                    font=ctk.CTkFont(family=font, size=13),
                    text_color=("gray70", "gray70"),
                    anchor="w",
                ).pack(fill="x", padx=20, pady=(4, 4))
            else:
                for task_name in all_tasks:
                    is_done = task_name in done_set
                    symbol = "\u2713" if is_done else "\u25cb"
                    color = ("gray30", "gray80") if is_done else ("gray60", "gray50")
                    ctk.CTkLabel(
                        content_frame,
                        text=f"{symbol}  {task_name}",
                        font=ctk.CTkFont(family=font, size=13),
                        text_color=color,
                        anchor="w",
                    ).pack(fill="x", padx=20, pady=(2, 2))
            if is_expanded[0]:
                content_frame.pack(fill="x", padx=4, pady=(0, 4))
            header_btn.configure(
                command=make_traders_toggle(
                    header_btn,
                    content_frame,
                    is_expanded,
                    trader_key,
                    header_text,
                    count_text,
                )
            )

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
                text_color=("gray70", "gray70"),
            ).pack(pady=20)
            return

        active_profile = data.get("active_mod_profile", "")
        profile_heading = (
            f"Metro Mod Loader Profile: {active_profile}"
            if active_profile
            else "Metro Mod Loader Profile"
        )
        ctk.CTkLabel(
            f,
            text=profile_heading,
            font=ctk.CTkFont(family=font, size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=8, pady=(8, 0))

        ctk.CTkLabel(
            f,
            text="Mods that were active when this backup was created.",
            font=ctk.CTkFont(family=font, size=12),
            text_color=("gray70", "gray70"),
            anchor="w",
        ).pack(fill="x", padx=8, pady=(2, 4))

        headers = ["", "Name", "Version"]
        col_widths = [24, 260, 110]

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
            dot_color = ("#27AE60", "#2ECC71") if enabled else ("gray55", "gray55")
            mod_id = mod.get("id", "?")
            name = mod.get("name") or _MOD_DISPLAY_NAMES.get(mod_id) or mod_id
            version = mod.get("version", "?")
            for col, (val, w) in enumerate(zip(["●", name, version], col_widths)):
                kwargs: dict = {}
                if col == 0:
                    kwargs["text_color"] = dot_color
                ctk.CTkLabel(
                    row_frame,
                    text=val,
                    font=ctk.CTkFont(family=font, size=13),
                    width=w,
                    anchor="w",
                    **kwargs,
                ).grid(row=0, column=col, padx=6, pady=3, sticky="w")

        backup_path = data.get("_path", "")
        if not backup_path:
            return
        mcm_data = self._cached_mcm
        if not mcm_data:
            return

        ctk.CTkLabel(
            f,
            text="MCM Mod Settings",
            font=ctk.CTkFont(family=font, size=14, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=8, pady=(16, 4))

        mcm_col_widths = [220, 140]

        def make_mcm_toggle(btn, frame, flag, key, text):
            def _toggle():
                if flag[0]:
                    frame.pack_forget()
                    btn.configure(text=f"\u25b6  {text}")
                    flag[0] = False
                else:
                    frame.pack(fill="x", padx=4, pady=(0, 4))
                    btn.configure(text=f"\u25bc  {text}")
                    flag[0] = True
                self._mcm_expanded[key] = flag[0]

            return _toggle

        for mod_folder, settings in mcm_data.items():
            display_mod_name = _MOD_DISPLAY_NAMES.get(mod_folder, mod_folder)
            is_expanded = [self._mcm_expanded.get(mod_folder, False)]
            self._mcm_expanded[mod_folder] = is_expanded[0]
            expand_char = "\u25bc" if is_expanded[0] else "\u25b6"

            section = ctk.CTkFrame(f, fg_color="transparent")
            section.pack(fill="x", padx=0, pady=0)

            header_btn = ctk.CTkButton(
                section,
                text=f"{expand_char}  {display_mod_name}",
                fg_color=("gray85", "#2A2A40"),
                hover_color=("gray78", "#32324E"),
                text_color=("gray10", "gray90"),
                anchor="w",
                corner_radius=4,
                font=ctk.CTkFont(family=font, size=11),
            )
            header_btn.pack(fill="x", padx=4, pady=(8, 0))

            content_frame = ctk.CTkFrame(section, fg_color="transparent")

            mcm_header = ctk.CTkFrame(
                content_frame, fg_color=("gray80", "#1A1A2E"), corner_radius=4
            )
            mcm_header.pack(fill="x", padx=4, pady=(2, 0))
            for col, (h, w) in enumerate(zip(["Setting", "Value"], mcm_col_widths)):
                ctk.CTkLabel(
                    mcm_header,
                    text=h,
                    font=ctk.CTkFont(family=font, size=13, weight="bold"),
                    width=w,
                    anchor="w",
                ).grid(row=0, column=col, padx=6, pady=4, sticky="w")

            current_category = ""
            for setting in settings:
                cat = setting.get("category", "")
                if cat and cat != current_category:
                    current_category = cat
                    ctk.CTkLabel(
                        content_frame,
                        text=cat,
                        font=ctk.CTkFont(family=font, size=11),
                        text_color=("gray65", "gray65"),
                        anchor="w",
                    ).pack(fill="x", padx=12, pady=(4, 0))

                row_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
                row_frame.pack(fill="x", padx=4, pady=1)
                for col, (val, w) in enumerate(
                    zip([setting["name"], setting["display_value"]], mcm_col_widths)
                ):
                    ctk.CTkLabel(
                        row_frame,
                        text=val,
                        font=ctk.CTkFont(family=font, size=13),
                        width=w,
                        anchor="w",
                    ).grid(row=0, column=col, padx=6, pady=2, sticky="w")

            if is_expanded[0]:
                content_frame.pack(fill="x", padx=4, pady=(0, 4))
            header_btn.configure(
                command=make_mcm_toggle(
                    header_btn, content_frame, is_expanded, mod_folder, display_mod_name
                )
            )
