import json
import logging
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from . import backup as bk
from . import repair as rp
from . import tres_parser, updater
from .constants import (
    APP_TITLE,
    LEFT_PANEL_WIDTH,
    SEASON_NAMES,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from .fonts import get_font, init_font, unload_bundled_fonts
from .logging_setup import setup_logging
from .paths import ITEMS_JSON, SAVE_DIR
from .settings import load_settings, save_settings
from .watcher import SaveWatcher
from .widgets.backup_list import BackupListPanel
from .widgets.dialogs import SettingsDialog, TagDialog, UpdateDialog
from .widgets.repair_dialog import RepairConfirmDialog
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
        self._version = updater.get_current_version()
        self.root.title(f"{APP_TITLE} v{self._version}")
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
        self._update_info: dict | None = None
        self._watcher = SaveWatcher(
            self._on_auto_backup, on_dir_lost=self._on_save_dir_lost
        )

        self._build_ui()
        self._load_backups()
        self.root.after(200, self._check_startup)
        self.root.after(
            2000,
            lambda: self._schedule_update_check(
                settings.get("check_for_updates", False)
            ),
        )

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
        toolbar = ctk.CTkFrame(self.root, height=80, corner_radius=0)
        toolbar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        toolbar.grid_propagate(False)
        toolbar.pack_propagate(False)

        # ── row 0: buttons ───────────────────────────────────────────────────
        self._btn_row = ctk.CTkFrame(toolbar, fg_color="transparent")
        self._btn_row.pack(side="top", fill="x", padx=0, pady=(6, 0))

        btn_opts = {
            "height": 34,
            "corner_radius": 4,
            "font": ctk.CTkFont(family=font, size=13),
        }

        ctk.CTkButton(
            self._btn_row,
            text="Restore",
            width=90,
            command=self._on_restore,
            **btn_opts,
        ).pack(side="left", padx=(10, 4))
        ctk.CTkButton(
            self._btn_row,
            text="Rename Tag",
            width=100,
            command=self._on_rename,
            **btn_opts,
        ).pack(side="left", padx=4)
        self._open_folder_btn = ctk.CTkButton(
            self._btn_row,
            text="Open Backups Folder",
            width=140,
            command=self._on_open_folder,
            state="disabled",
            **btn_opts,
        )
        self._open_folder_btn.pack(side="left", padx=4)

        self._repair_btn = ctk.CTkButton(
            self._btn_row,
            text="Repair",
            width=80,
            command=self._on_repair,
            state="disabled",
            **btn_opts,
        )
        self._repair_btn.pack(side="left", padx=4)

        ctk.CTkFrame(self._btn_row, width=1, fg_color=("gray70", "gray40")).pack(
            side="left", fill="y", padx=(8, 8), pady=4
        )

        ctk.CTkButton(
            self._btn_row,
            text="🗑  Delete",
            width=92,
            fg_color="#7A1C1C",
            hover_color="#5C1010",
            command=self._on_delete,
            **btn_opts,
        ).pack(side="left", padx=(0, 4))

        self._watch_btn = ctk.CTkButton(
            self._btn_row,
            text="Auto-Backup: Off",
            width=140,
            command=self._on_toggle_watch,
            **btn_opts,
        )
        self._watch_btn.pack(side="left", padx=4)

        ctk.CTkButton(
            self._btn_row,
            text="⚙ Settings",
            width=100,
            command=self._on_open_settings,
            **btn_opts,
        ).pack(side="right", padx=(4, 10))

        self._update_btn = ctk.CTkButton(
            self._btn_row,
            text="⬆ Update available",
            width=140,
            fg_color=("#1A5276", "#1A5276"),
            hover_color=("#154360", "#154360"),
            text_color=("white", "white"),
            command=self._on_show_update,
            **btn_opts,
        )
        # _update_btn is intentionally not packed here — shown only when an update is found

        # ── row 1: status / notifications ────────────────────────────────────
        status_row = ctk.CTkFrame(toolbar, fg_color="transparent")
        status_row.pack(side="top", fill="x", padx=0, pady=(2, 0))

        self._status = ctk.CTkLabel(
            status_row,
            text=f"Ready  ·  v{self._version}",
            font=ctk.CTkFont(family=font, size=13),
            anchor="w",
            text_color=("gray75", "gray75"),
        )
        self._status.pack(side="left", padx=14, fill="x", expand=True)

    def _schedule_update_check(self, check_for_updates: bool) -> None:
        if not check_for_updates:
            return

        def _check() -> None:
            info = updater.check_for_update()
            if info:
                self.root.after(0, lambda: self._on_update_available(info))

        threading.Thread(target=_check, daemon=True).start()

    def _on_update_available(self, info: dict) -> None:
        self._update_info = info
        self._update_btn.pack(side="right", padx=(4, 4))

    def _on_show_update(self) -> None:
        if self._update_info is not None:
            UpdateDialog(self.root, self._update_info)

    def _check_startup(self) -> None:
        settings = load_settings()
        backups = bk.list_backups()

        if not settings.get("first_run_done") and not backups and SAVE_DIR.exists():
            updated = {**settings, "first_run_done": True}
            save_settings(updated)
            if messagebox.askyesno(
                "Welcome to Vostok Vault",
                "No backups found.\n\n"
                "Create an initial 'OG Save' now to protect your run from the start?\n\n"
                "You can always back up manually using '+ Backup Now'.",
                parent=self.root,
            ):
                manifest = bk.create_backup("OG_Save")
                if manifest:
                    self._set_status("OG Save created — your run is protected.")
                    self._load_backups()
                else:
                    self._set_status(
                        "Could not create OG Save — save folder not found."
                    )
            return

        if backups and bk.current_save_needs_backup():
            self._set_status("Your current save has changed since your last backup.")

    def _load_backups(self) -> None:
        self._left.set_backups(bk.list_backups())

    def _on_select(self, data: dict | None) -> None:
        self._selected = data
        self._right.show_backup(data)
        self._open_folder_btn.configure(state="normal" if data else "disabled")
        self._repair_btn.configure(state="normal" if data else "disabled")

    def _on_open_folder(self) -> None:
        if not self._selected:
            return
        os.startfile(Path(self._selected["_path"]).parent)

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

        dialog = TagDialog(self.root, suggestion)
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
            bk.prune_pre_restore_backups(3)
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
        dialog = TagDialog(self.root, current_tag)
        new_tag = dialog.get_result()
        if not new_tag or not new_tag.strip():
            return
        sanitised = bk.sanitise_tag(new_tag.strip()) or current_tag
        manifest_path = Path(self._selected["_path"]) / "manifest.json"
        try:
            with bk._lock:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["tag"] = sanitised
                tmp = manifest_path.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                tmp.replace(manifest_path)
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
            else:
                self._set_status("Could not start watcher — save folder not found")

    def _on_save_dir_lost(self) -> None:
        self.root.after(
            0,
            lambda: (
                self._watch_btn.configure(text="Auto-Backup: Off"),
                self._set_status("Auto-Backup stopped — save folder not found"),
            ),
        )

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

    def _on_repair(self) -> None:
        if not self._selected:
            return
        self._repair_btn.configure(state="disabled")
        self._set_status("Scanning for orphaned items…")

        try:
            items_db = json.loads(ITEMS_JSON.read_text(encoding="utf-8"))
            if isinstance(items_db, dict):
                items_db = items_db.get("items", [])
        except Exception:
            items_db = []

        source_path = Path(self._selected["_path"])

        def _detect() -> dict:
            return rp.detect_orphaned_items(source_path, items_db)

        def _on_done(detection: dict) -> None:
            self.root.after(0, lambda: self._on_repair_detected(detection, items_db))

        def _thread() -> None:
            detection = _detect()
            _on_done(detection)

        threading.Thread(target=_thread, daemon=True).start()

    def _on_repair_detected(self, detection: dict, items_db: list[dict]) -> None:
        if not detection["affected_files"]:
            self._set_status("No orphaned items found.")
            self._repair_btn.configure(state="normal")
            return

        dialog = RepairConfirmDialog(self.root, detection, self._selected)
        dialog.wait_window()

        if not dialog.result:
            self._set_status("Repair cancelled.")
            self._repair_btn.configure(state="normal")
            return

        self._set_status("Repairing…")
        self._repair_btn.configure(state="disabled")

        source_path = Path(self._selected["_path"])

        def _do_repair() -> tuple[bool, str]:
            return rp.create_repaired_backup(source_path, items_db)

        def _thread() -> None:
            ok, reason = _do_repair()
            self.root.after(0, lambda: self._on_repair_complete(ok, reason))

        threading.Thread(target=_thread, daemon=True).start()

    def _on_repair_complete(self, ok: bool, reason: str) -> None:
        self._repair_btn.configure(state="normal")
        if ok:
            self._set_status("Repaired backup created.")
            self._load_backups()
        else:
            self._set_status("Repair failed — original unchanged. See log.")

    def _on_open_settings(self) -> None:
        SettingsDialog(self.root)

    def _set_status(self, msg: str) -> None:
        self._status.configure(text=msg)

    def _on_close(self) -> None:
        self._watcher.stop()
        unload_bundled_fonts()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
