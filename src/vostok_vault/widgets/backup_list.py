from typing import Callable

import customtkinter as ctk

from ..config import get_font


class BackupCard(ctk.CTkFrame):
    def __init__(self, parent, data: dict, on_click: Callable, **kwargs) -> None:
        super().__init__(parent, corner_radius=6, **kwargs)
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
        created = self._data.get("created", "")[:16].replace("T", " ")
        day = self._data.get("game_day", "?")
        time_str = self._data.get("game_time", "??:??")
        mod_count = len(self._data.get("mods", []))
        mod_label = f"{mod_count} mod{'s' if mod_count != 1 else ''}"

        ctk.CTkLabel(
            self,
            text=tag,
            font=ctk.CTkFont(family=font, size=14, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 2))

        ctk.CTkLabel(
            self,
            text=created,
            font=ctk.CTkFont(family=font, size=13),
            anchor="w",
            text_color=("gray55", "gray55"),
        ).pack(fill="x", padx=10)

        ctk.CTkLabel(
            self,
            text=f"Day {day}  ·  {time_str}  ·  {mod_label}",
            font=ctk.CTkFont(family=font, size=13),
            anchor="w",
            text_color=("gray55", "gray55"),
        ).pack(fill="x", padx=10, pady=(0, 8))

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
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)

        self._scroll = ctk.CTkScrollableFrame(
            self, label_text="Backups", corner_radius=6
        )
        self._scroll.grid(row=0, column=0, sticky="nsew", padx=6, pady=(6, 4))

        self._empty_label = ctk.CTkLabel(
            self._scroll,
            text="No backups yet.\nUse '+ Backup Now' to create one.",
            wraplength=220,
            justify="center",
            text_color=("gray55", "gray55"),
            font=ctk.CTkFont(family=font, size=13),
        )

        ctk.CTkButton(
            self,
            text="+ Backup Now",
            height=44,
            corner_radius=4,
            font=ctk.CTkFont(family=font, size=15, weight="bold"),
            command=self._on_backup_now,
        ).grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))

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
            card.pack(fill="x", padx=4, pady=4)
            self._cards.append(card)

    def _card_clicked(self, data: dict) -> None:
        for card in self._cards:
            card.set_selected(card._data is data)
        self._on_select(data)
