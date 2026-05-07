import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from . import backup as bk
from . import tres_parser
from .constants import (
    APP_TITLE,
    LEFT_PANEL_WIDTH,
    SEASON_NAMES,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from .fonts import get_font, init_font
from .logging_setup import setup_logging
from .paths import SAVE_DIR
from .settings import load_settings
from .watcher import SaveWatcher
from .widgets.backup_list import BackupListPanel
from .widgets.dialogs import _SettingsDialog, _TagDialog
from .widgets.save_detail import SaveDetailPanel

log = logging.getLogger(__name__)


class VostokVaultApp:
    def __init__(self) -> None:
        if sys.platform != "win32":
            import tkinter as _tk

            _r = _tk.Tk()
            _r.withdraw()
            messagebox.showerror(
                "Unsupported platform",
                "Vostok Vault is Windows-only.",
            )
            _r.destroy()
            sys.exit(1)

        settings = load_settings()
        setup_logging(debug=settings.get("debug_logging", False))
        log.debug("VostokVaultApp starting")

        def _excepthook(exc_type, exc_value, exc_tb):
            log.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
            sys.__excepthook__(exc_type, exc_value, exc_tb)

        sys.excepthook = _excepthook

        init_font(preferred=settings.get("font_preference"))

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.root = ctk.CTk()
        self.root.title(APP_TITLE)
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.root.geometry(f"{WINDOW_MIN_WIDTH}x{WINDOW_MIN_HEIGHT}")

        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            icon_path = Path(sys._MEIPASS) / "assets" / "vostok-vault.ico"
        else:
            icon_path = (
                Path(__file__).resolve().parent.parent.parent
                / "assets"
                / "vostok-vault.ico"
            )
        if icon_path.exists():
            self.root.iconbitmap(str(icon_path))

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._selected: dict | None = None
        self._watcher = SaveWatcher(self._on_auto_backup)

        self._build_ui()
        self._load_backups()

    def _build_ui(self) -> None:
        self.root.grid_columnconfigure(0, weight=0, minsize=LEFT_PANEL_WIDTH)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)

        self._left = BackupListPanel(
            self.root,
            width=LEFT_PANEL_WIDTH,
            on_select=self._on_select,
            on_backup_now=self._on_backup_now,
        )
        self._left.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(8, 4))

        self._right = SaveDetailPanel(self.root)
        self._right.grid(row=0, column=1, sticky="nsew", padx=8, pady=(8, 4))

        self._build_toolbar()

    def _build_toolbar(self) -> None:
        font = get_font()
        toolbar = ctk.CTkFrame(self.root, height=52, corner_radius=0)
        toolbar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        toolbar.grid_propagate(False)

        btn_opts = {
            "height": 34,
            "corner_radius": 4,
            "font": ctk.CTkFont(family=font, size=13),
        }

        ctk.CTkButton(
            toolbar, text="Restore", width=90, command=self._on_restore, **btn_opts
        ).pack(side="left", padx=(10, 4), pady=9)
        ctk.CTkButton(
            toolbar, text="Rename Tag", width=100, command=self._on_rename, **btn_opts
        ).pack(side="left", padx=4, pady=9)
        ctk.CTkButton(
            toolbar,
            text="Delete",
            width=80,
            fg_color="#7A1C1C",
            hover_color="#5C1010",
            command=self._on_delete,
            **btn_opts,
        ).pack(side="left", padx=4, pady=9)

        self._watch_btn = ctk.CTkButton(
            toolbar,
            text="Auto-Backup: Off",
            width=140,
            command=self._on_toggle_watch,
            **btn_opts,
        )
        self._watch_btn.pack(side="left", padx=4, pady=9)

        ctk.CTkLabel(
            toolbar,
            text="Auto-Backup watches for game saves and backs up automatically.",
            font=ctk.CTkFont(family=font, size=10),
            text_color=("gray55", "gray55"),
            anchor="w",
        ).pack(side="left", padx=(2, 8), pady=9)

        ctk.CTkButton(
            toolbar,
            text="⚙ Settings",
            width=100,
            command=self._on_open_settings,
            **btn_opts,
        ).pack(side="right", padx=(4, 10), pady=9)

        self._status = ctk.CTkLabel(
            toolbar,
            text="Ready",
            font=ctk.CTkFont(family=font, size=13),
            anchor="w",
            text_color=("gray60", "gray60"),
        )
        self._status.pack(side="left", padx=12, fill="x", expand=True)

    def _load_backups(self) -> None:
        self._left.set_backups(bk.list_backups())

    def _on_select(self, data: dict | None) -> None:
        self._selected = data
        self._right.show_backup(data)

    def _on_backup_now(self) -> None:
        world = tres_parser.parse_world(SAVE_DIR / "World.tres")
        if (
            world["day"] != "?"
            and world["season"] != "?"
            and world["time_str"] != "??:??"
        ):
            time_part = world["time_str"].replace(":", "h")
            season_name = SEASON_NAMES.get(world["season"], str(world["season"]))
            suggestion = f"Day{world['day']}-{season_name}-{time_part}"
        else:
            suggestion = datetime.now().strftime("backup-%Y%m%d-%H%M")

        dialog = _TagDialog(self.root, suggestion)
        tag = dialog.get_result()
        if tag is None:
            return
        tag = tag.strip() or "manual"
        manifest = bk.create_backup(tag)
        if manifest:
            self._set_status(f"Backup created: {manifest['tag']}")
        else:
            self._set_status("Backup failed — save folder not found")
        self._load_backups()

    def _on_restore(self) -> None:
        if not self._selected:
            return
        if bk.current_save_needs_backup():
            msg = (
                f"Restore '{self._selected['tag']}'?\n\n"
                "Warning: Your current game session has not been backed up.\n\n"
                "An automatic 'pre_restore' snapshot will be saved before restoring, "
                "but it won't have a custom name.\n\n"
                "Click 'No' to create a named backup first using '+ Backup Now', "
                "or 'Yes' to restore now."
            )
        else:
            msg = (
                f"Restore '{self._selected['tag']}'?\n\n"
                "Your current save will be backed up first as 'pre_restore'."
            )
        if not messagebox.askyesno("Restore Backup", msg, parent=self.root):
            return
        ok = bk.restore_backup(Path(self._selected["_path"]))
        if ok:
            self._set_status(f"Restored: {self._selected['tag']}")
            self._load_backups()
        else:
            messagebox.showerror(
                "Restore failed",
                "Could not restore the backup.\n\nThe save folder may be locked by the game or another process.",
                parent=self.root,
            )
            self._set_status("Restore failed")

    def _on_rename(self) -> None:
        if not self._selected:
            return
        current_tag = self._selected.get("tag", "")
        dialog = _TagDialog(self.root, current_tag)
        new_tag = dialog.get_result()
        if not new_tag or not new_tag.strip():
            return
        import re

        sanitised = re.sub(r"[^a-zA-Z0-9_\s-]", "", new_tag.strip())[:50] or current_tag
        manifest_path = Path(self._selected["_path"]) / "manifest.json"
        try:
            with bk._lock:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["tag"] = sanitised
                manifest_path.write_text(
                    json.dumps(manifest, indent=2), encoding="utf-8"
                )
        except (OSError, json.JSONDecodeError):
            self._set_status("Rename failed")
            return
        self._set_status(f"Renamed to: {sanitised}")
        self._load_backups()

    def _on_delete(self) -> None:
        if not self._selected:
            return
        if not messagebox.askyesno(
            "Delete Backup",
            f"Permanently delete '{self._selected['tag']}'?\n\nThis cannot be undone.",
            parent=self.root,
        ):
            return
        ok = bk.delete_backup(Path(self._selected["_path"]))
        if ok:
            self._selected = None
            self._right.show_backup(None)
            self._set_status("Backup deleted")
            self._load_backups()
        else:
            messagebox.showerror(
                "Delete failed",
                "Could not delete the backup.\n\nThe folder may be open in another program.",
                parent=self.root,
            )
            self._set_status("Delete failed")

    def _on_toggle_watch(self) -> None:
        if self._watcher.is_running:
            self._watcher.stop()
            self._watch_btn.configure(text="Auto-Backup: Off")
            self._set_status("Watcher stopped")
        else:
            self._watcher.start()
            if self._watcher.is_running:
                self._watch_btn.configure(text="Auto-Backup: On")
                self._set_status("Watcher active — monitoring save files")
            else:
                self._set_status("Could not start watcher — save folder not found")

    def _on_auto_backup(self) -> None:
        try:
            bk.create_backup("auto")
            bk.prune_auto_backups(5)
            self.root.after(0, self._load_backups)
            self.root.after(0, lambda: self._set_status("Auto-backup created"))
        except Exception as exc:
            log.exception("Auto-backup failed")
            self.root.after(
                0, lambda msg=str(exc): self._set_status(f"Auto-backup failed: {msg}")
            )

    def _on_open_settings(self) -> None:
        _SettingsDialog(self.root)

    def _set_status(self, msg: str) -> None:
        self._status.configure(text=msg)

    def _on_close(self) -> None:
        self._watcher.stop()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
