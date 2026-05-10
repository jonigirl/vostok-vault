from datetime import date, datetime
from typing import Callable

import customtkinter as ctk

from ..constants import SEASON_NAMES
from ..fonts import get_font


def _format_card_date(iso: str) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso)
        today = date.today()
        if dt.date() == today:
            return f"Today  {dt.strftime('%H:%M')}"
        if dt.date().toordinal() == today.toordinal() - 1:
            return f"Yesterday  {dt.strftime('%H:%M')}"
        return f"{dt.day} {dt.strftime('%b')}  {dt.strftime('%H:%M')}"
    except (ValueError, TypeError):
        return iso[:16].replace("T", " ")


class BackupCard(ctk.CTkFrame):
    def __init__(self, parent, data: dict, on_click: Callable, **kwargs) -> None:
        super().__init__(parent, corner_radius=6, border_width=1, **kwargs)
        self._data = data
        self._on_click = on_click
        self._build()
        self._bind_clicks(self)

    def _bind_clicks(self, widget) -> None:
        widget.bind("<Button-1>", self._clicked)
        for child in widget.winfo_children():
            self._bind_clicks(child)

    def _build(self) -> None:
        font = get_font()
        tag = self._data.get("tag", "untitled")
        created = self._data.get("created", "")
        day = self._data.get("game_day", "?")
        time_str = self._data.get("game_time", "??:??")
        season_num = self._data.get("season")
        season_name = SEASON_NAMES.get(season_num, "") if season_num is not None else ""
        mod_count = len(self._data.get("mods", []))
        mod_label = f"{mod_count} mod{'s' if mod_count != 1 else ''}"

        is_auto = tag == "auto"
        is_pre_restore = tag == "pre_restore"

        display_tag = tag
        type_label: str | None = None
        if is_auto:
            display_tag = "auto backup"
            type_label = "(automatic)"
        elif is_pre_restore:
            display_tag = "pre-restore backup"
            type_label = "(pre-restore)"

        auto_color = ("gray55", "gray55")

        title_row = ctk.CTkFrame(self, fg_color="transparent")
        title_row.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(
            title_row,
            text=display_tag,
            font=ctk.CTkFont(family=font, size=14, weight="bold"),
            anchor="w",
        ).pack(side="left")
        if type_label:
            ctk.CTkLabel(
                title_row,
                text=f"  {type_label}",
                font=ctk.CTkFont(family=font, size=12),
                text_color=auto_color,
                anchor="w",
            ).pack(side="left")

        ctk.CTkLabel(
            self,
            text=_format_card_date(created),
            font=ctk.CTkFont(family=font, size=13),
            anchor="w",
            text_color=("gray65", "gray65"),
        ).pack(fill="x", padx=10)

        ironman = self._data.get("difficulty") == 3
        char_items = self._data.get("char_items")
        storage_items = self._data.get("storage_items")
        item_parts = []
        if char_items is not None:
            item_parts.append(f"{char_items} equipped")
        if storage_items is not None:
            item_parts.append(f"{storage_items} stored")

        subtitle = f"Day {day}  ·  {season_name + '  ·  ' if season_name else ''}{time_str}  ·  {mod_label}"
        if item_parts:
            subtitle += "  ·  " + "  ·  ".join(item_parts)
        if ironman:
            subtitle += "  ·  ☠ Ironman"
        ctk.CTkLabel(
            self,
            text=subtitle,
            font=ctk.CTkFont(family=font, size=13),
            anchor="w",
            text_color=("#C0392B", "#E74C3C") if ironman else ("gray65", "gray65"),
        ).pack(fill="x", padx=10, pady=(0, 8))

        self.configure(
            border_color=("#C0392B", "#E74C3C") if ironman else ("gray70", "gray35")
        )

    def _clicked(self, _event=None) -> None:
        self._on_click(self._data)

    def set_selected(self, selected: bool) -> None:
        color = ("#DDEEFF", "#1C3A58") if selected else ("gray90", "#2A2A2A")
        self.configure(fg_color=color)


class BackupListPanel(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        width: int,
        on_select: Callable,
        on_backup_now: Callable,
        **kwargs,
    ) -> None:
        super().__init__(parent, width=width, corner_radius=8, **kwargs)
        self._on_select = on_select
        self._on_backup_now = on_backup_now
        self._cards: list[BackupCard] = []
        self.grid_propagate(False)
        self._build()

    def _build(self) -> None:
        font = get_font()
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)

        filter_row = ctk.CTkFrame(self, fg_color="transparent")
        filter_row.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 2))
        filter_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            filter_row,
            text="Filter:",
            font=ctk.CTkFont(family=font, size=13),
            text_color=("gray60", "gray60"),
        ).grid(row=0, column=0, padx=(0, 4))
        self._filter_var = ctk.StringVar()
        ctk.CTkEntry(
            filter_row,
            textvariable=self._filter_var,
            placeholder_text="tag or date…",
            font=ctk.CTkFont(family=font, size=13),
            height=28,
            corner_radius=4,
        ).grid(row=0, column=1, sticky="ew")
        self._filter_var.trace_add("write", self._apply_filter)

        self._scroll = ctk.CTkScrollableFrame(
            self, label_text="Backups", corner_radius=6
        )
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=(2, 4))

        self._empty_label = ctk.CTkLabel(
            self._scroll,
            text="No backups yet.\nUse '+ Backup Now' to create one.",
            wraplength=220,
            justify="center",
            text_color=("gray65", "gray65"),
            font=ctk.CTkFont(family=font, size=13),
        )

        ctk.CTkButton(
            self,
            text="+ Backup Now",
            height=44,
            corner_radius=4,
            font=ctk.CTkFont(family=font, size=15, weight="bold"),
            command=self._on_backup_now,
        ).grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 6))

    def set_backups(self, backups: list[dict]) -> None:
        for card in self._cards:
            card.destroy()
        self._cards.clear()
        self._empty_label.pack_forget()

        if not backups:
            self._empty_label.pack(expand=True, pady=40)
            return

        for data in backups:
            card = BackupCard(
                self._scroll,
                data=data,
                on_click=self._card_clicked,
                fg_color=("gray88", "#2A2A2A"),
            )
            self._cards.append(card)
        self._apply_filter()

    def _apply_filter(self, *_args) -> None:
        text = self._filter_var.get().lower().strip()
        for card in self._cards:
            card.pack_forget()
        for card in self._cards:
            d = card._data
            visible = (
                not text
                or text in (d.get("tag") or "").lower()
                or text in _format_card_date(d.get("created") or "").lower()
            )
            if visible:
                card.pack(fill="x", padx=4, pady=4)

    def _card_clicked(self, data: dict) -> None:
        for card in self._cards:
            card.set_selected(card._data is data)
        self._on_select(data)
