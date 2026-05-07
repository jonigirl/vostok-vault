import json
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from . import backup as bk
from .config import (
    APP_TITLE,
    LEFT_PANEL_WIDTH,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    get_font,
    init_font,
)
from .watcher import SaveWatcher
from .widgets.backup_list import BackupListPanel
from .widgets.save_detail import SaveDetailPanel


class VostokVaultApp:
    def __init__(self) -> None:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.root = ctk.CTk()
        self.root.title(APP_TITLE)
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.root.geometry(f"{WINDOW_MIN_WIDTH}x{WINDOW_MIN_HEIGHT}")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        init_font()

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
            text="Start Watch",
            width=110,
            command=self._on_toggle_watch,
            **btn_opts,
        )
        self._watch_btn.pack(side="left", padx=4, pady=9)

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
        dialog = ctk.CTkInputDialog(
            text="Enter a tag for this backup:", title="Backup Now"
        )
        tag = dialog.get_input()
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
        if not messagebox.askyesno(
            "Restore Backup",
            f"Restore '{self._selected['tag']}'?\n\nYour current save will be backed up first as 'pre_restore'.",
            parent=self.root,
        ):
            return
        ok = bk.restore_backup(Path(self._selected["_path"]))
        if ok:
            self._set_status(f"Restored: {self._selected['tag']}")
            self._load_backups()
        else:
            self._set_status("Restore failed — backup folder not found")

    def _on_rename(self) -> None:
        if not self._selected:
            return
        current_tag = self._selected.get("tag", "")
        dialog = ctk.CTkInputDialog(
            text=f"New tag (current: {current_tag}):",
            title="Rename Tag",
        )
        new_tag = dialog.get_input()
        if not new_tag or not new_tag.strip():
            return
        manifest_path = Path(self._selected["_path"]) / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["tag"] = new_tag.strip()
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        except Exception:
            self._set_status("Rename failed")
            return
        self._set_status(f"Renamed to: {new_tag.strip()}")
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
            self._set_status("Delete failed")

    def _on_toggle_watch(self) -> None:
        if self._watcher.is_running:
            self._watcher.stop()
            self._watch_btn.configure(text="Start Watch")
            self._set_status("Watcher stopped")
        else:
            self._watcher.start()
            if self._watcher.is_running:
                self._watch_btn.configure(text="Stop Watch")
                self._set_status("Watcher active — monitoring save files")
            else:
                self._set_status("Could not start watcher — save folder not found")

    def _on_auto_backup(self) -> None:
        bk.create_backup("auto")
        bk.prune_auto_backups(5)
        self.root.after(0, self._load_backups)
        self.root.after(0, lambda: self._set_status("Auto-backup created"))

    def _set_status(self, msg: str) -> None:
        self._status.configure(text=msg)

    def _on_close(self) -> None:
        self._watcher.stop()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
