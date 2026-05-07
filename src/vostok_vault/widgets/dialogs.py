import os

import customtkinter as ctk

from ..config import (
    FONT_ATKINSON,
    FONT_OPENDYSLEXIC,
    LOG_FILE,
    get_font,
    load_settings,
    save_settings,
    setup_logging,
)


class _TagDialog(ctk.CTkToplevel):
    def __init__(self, parent, suggestion: str) -> None:
        super().__init__(parent)
        self.title("Backup Tag")
        self.resizable(False, False)
        self._result: str | None = None
        font = get_font()

        ctk.CTkLabel(
            self,
            text="Backup tag:",
            font=ctk.CTkFont(family=font, size=13),
        ).pack(padx=20, pady=(16, 4))

        self._entry = ctk.CTkEntry(
            self, width=280, font=ctk.CTkFont(family=font, size=13)
        )
        self._entry.pack(padx=20, pady=(0, 12))
        self._entry.insert(0, suggestion)
        self._entry.select_range(0, "end")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(0, 16))
        ctk.CTkButton(
            btn_frame,
            text="OK",
            width=100,
            font=ctk.CTkFont(family=font, size=13),
            command=self._ok,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=100,
            font=ctk.CTkFont(family=font, size=13),
            command=self._cancel,
        ).pack(side="left")

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.grab_set()
        self._entry.bind("<Return>", lambda e: self._ok())
        self._entry.bind("<Escape>", lambda e: self._cancel())
        self.after(50, self._entry.focus_set)

    def _ok(self) -> None:
        self._result = self._entry.get()
        self.destroy()

    def _cancel(self) -> None:
        self._result = None
        self.destroy()

    def get_result(self) -> str | None:
        self.wait_window()
        return self._result


class _SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.title("Settings")
        self.resizable(False, False)
        font = get_font()
        self._settings = load_settings()

        ctk.CTkLabel(
            self,
            text="Font preference",
            font=ctk.CTkFont(family=font, size=13, weight="bold"),
        ).pack(padx=20, pady=(16, 4))

        options = [
            "Standard (Atkinson Hyperlegible)",
            "Dyslexia-friendly (OpenDyslexic)",
        ]
        current_font = get_font()
        current_val = options[1] if FONT_OPENDYSLEXIC in current_font else options[0]

        self._font_menu = ctk.CTkOptionMenu(
            self,
            values=options,
            font=ctk.CTkFont(family=font, size=13),
            width=280,
        )
        self._font_menu.set(current_val)
        self._font_menu.pack(padx=20, pady=(0, 12))

        ctk.CTkLabel(
            self,
            text="Debug logging",
            font=ctk.CTkFont(family=font, size=13, weight="bold"),
        ).pack(padx=20, pady=(4, 4))

        debug_row = ctk.CTkFrame(self, fg_color="transparent")
        debug_row.pack(padx=20, pady=(0, 4), fill="x")

        self._debug_var = ctk.BooleanVar(
            value=self._settings.get("debug_logging", False)
        )
        self._debug_switch = ctk.CTkSwitch(
            debug_row,
            text="Write debug log",
            font=ctk.CTkFont(family=font, size=13),
            variable=self._debug_var,
            command=self._on_debug_toggle,
        )
        self._debug_switch.pack(side="left")

        ctk.CTkButton(
            debug_row,
            text="Open log folder",
            font=ctk.CTkFont(family=font, size=12),
            width=120,
            command=lambda: os.startfile(str(LOG_FILE.parent)),
        ).pack(side="right")

        ctk.CTkLabel(
            self,
            text=f"Log: {LOG_FILE}",
            font=ctk.CTkFont(family=font, size=10),
            text_color=("gray55", "gray55"),
            wraplength=320,
            justify="left",
        ).pack(padx=20, pady=(0, 8), anchor="w")

        ctk.CTkLabel(
            self,
            text="Log path contains your Windows username.",
            font=ctk.CTkFont(family=font, size=11),
            text_color=("gray65", "gray65"),
            anchor="w",
        ).pack(padx=20, pady=(0, 8), fill="x")

        self._msg_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family=font, size=12),
            text_color=("gray55", "gray55"),
        )
        self._msg_label.pack(padx=20)

        ctk.CTkButton(
            self,
            text="Save & Restart",
            font=ctk.CTkFont(family=font, size=13),
            command=self._save,
        ).pack(padx=20, pady=(8, 16))

        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _on_debug_toggle(self) -> None:
        enabled = self._debug_var.get()
        setup_logging(debug=enabled)
        self._settings["debug_logging"] = enabled
        save_settings(self._settings)

    def _save(self) -> None:
        val = self._font_menu.get()
        pref = FONT_OPENDYSLEXIC if "OpenDyslexic" in val else FONT_ATKINSON
        self._settings["font_preference"] = pref
        save_settings(self._settings)
        self._msg_label.configure(text="Restart the app to apply font changes.")
        self.after(1500, self.destroy)
