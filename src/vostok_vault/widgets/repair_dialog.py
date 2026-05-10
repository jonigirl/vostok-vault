import customtkinter as ctk

from ..backup import format_backup_date
from ..fonts import get_font


class RepairConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, detection: dict, backup_data: dict) -> None:
        super().__init__(parent)
        self.title("Repair Save")
        self.resizable(False, False)
        self.result: bool = False
        font = get_font()

        tag = backup_data.get("tag", "")
        created = backup_data.get("created", "")
        formatted_date = format_backup_date(created)

        ctk.CTkLabel(
            self,
            text=f"Backup: {tag}  ·  {formatted_date}",
            font=ctk.CTkFont(family=font, size=13),
            anchor="w",
        ).pack(padx=20, pady=(16, 4), fill="x")

        total_slots = detection.get("total_slots", 0)
        affected_count = len(detection.get("affected_files", {}))
        ctk.CTkLabel(
            self,
            text=f"Found {total_slots} orphaned item slot(s) across {affected_count} file(s).",
            font=ctk.CTkFont(family=font, size=13),
            anchor="w",
        ).pack(padx=20, pady=(0, 8), fill="x")

        ctk.CTkLabel(
            self,
            text="Unknown items:",
            font=ctk.CTkFont(family=font, size=13, weight="bold"),
            anchor="w",
        ).pack(padx=20, pady=(0, 4), fill="x")

        orphan_names = detection.get("orphan_names", [])
        names_box = ctk.CTkTextbox(
            self,
            width=380,
            height=min(120, max(40, len(orphan_names) * 22)),
            font=ctk.CTkFont(family=font, size=13),
            wrap="word",
        )
        names_box.pack(padx=20, pady=(0, 8), fill="x")
        for name in orphan_names:
            names_box.insert("end", f"  •  {name}\n")
        names_box.configure(state="disabled")

        warning_text = (
            "⚠ A new backup will be created alongside the original. "
            "The original is not changed.\n"
            "If the repaired save causes issues in-game, restore the original "
            "backup from your list."
        )
        ctk.CTkLabel(
            self,
            text=warning_text,
            font=ctk.CTkFont(family=font, size=12),
            text_color=("#C0392B", "#E74C3C"),
            anchor="w",
            wraplength=380,
            justify="left",
        ).pack(padx=20, pady=(0, 12), fill="x")

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(padx=20, pady=(0, 16), fill="x")

        ctk.CTkButton(
            btn_row,
            text="Create Repaired Backup",
            font=ctk.CTkFont(family=font, size=13),
            command=self._confirm,
        ).pack(side="left")

        ctk.CTkButton(
            btn_row,
            text="Cancel",
            font=ctk.CTkFont(family=font, size=13),
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray25"),
            command=self._cancel,
        ).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.transient(parent)
        self.grab_set()

    def _confirm(self) -> None:
        self.result = True
        self.destroy()

    def _cancel(self) -> None:
        self.result = False
        self.destroy()
