# Changelog

All notable changes to Vostok Vault will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `current_save_needs_backup()` in `backup.py` — compares tracked save file mtimes against the most recent non-restore backup to detect an unsaved session
- `src/vostok_vault/widgets/dialogs.py` — `_TagDialog` and `_SettingsDialog` extracted from `app.py`
- `_ITEM_SUBTREES` allow-list in `tres_parser.py` — storage tab now only shows items from known vanilla subtrees; mod-injected paths under `res://Items/` are filtered out

### Changed

- Mods section in the Overview tab and the Mods tab now clearly show the mods that were active **when the backup was created** — heading renamed to "Mods at Backup Time", column header renamed to "Was Active", subtitle added to the Mods tab
- Restore confirmation dialog now warns the user if their current game session has not been backed up
- Manifest writes are now atomic — written to a `.tmp` file then renamed with `os.replace()` to avoid corruption on crash
- Backup cards in the left panel are now keyboard-focusable (Tab order) with a visible blue focus border; Enter/Space activates the card
- Secondary label/description text contrast raised from `gray55` → `gray70` / `gray50` → `gray65` (WCAG 1.4.3)
- Mod chips in the Overview tab now wrap into rows of 3 instead of overflowing a single line
- Rename dialog now uses the same `_TagDialog` as the backup dialog, pre-filled with the current tag
- Settings dialog shows a note that the log path contains the Windows username

## [0.1.0] - 2026-05-07

### Added

- **Save backup / restore / delete** — one-click operations on Road to Vostok save files with confirmation dialogs
- **Rename backups** — tag any backup with a custom label; tag is sanitised and capped at 50 characters
- **Auto-suggest tag** — backup tag pre-filled with `Day{N}-{Season}-{HHhMM}` from the save file
- **Auto-backup watcher** — watchdog-based file watcher that triggers a backup 3 s after the save file is written; button shows "Auto-Backup: Off / On"
- **Backup pruning** — configurable limit keeps the newest N backups per save slot
- **Save file parsing** — reads `.tres` Godot save files: day/season/time, player stats, character slots, inventory items, active mods
- **Save detail panel** — Overview, Character, Storage, and Mods tabs; amount = 0 shown as `—`; slot order includes Torso, Light, Time
- **Font system** — Atkinson Hyperlegible loaded by default via Windows GDI; OpenDyslexic selectable in settings; Segoe UI fallback
- **Settings dialog** — font preference, debug logging toggle, open-log-folder button, log file path label
- **Debug logging** — rotating log file (512 KB, 1 backup) at `%APPDATA%\Road to Vostok\vostok-vault-backups\vostok-vault.log`; `sys.excepthook` captures uncaught exceptions
- **Error modals** — restore and delete failures surface a `messagebox.showerror` dialog, not just a status bar message
- **Window icon** — `.ico` file set via `iconbitmap` in both dev and frozen (PyInstaller) modes
- **Platform guard** — non-Windows launch shows an error dialog and exits cleanly
- **Thread safety** — `threading.RLock` protects all backup operations; symlink-safe path-traversal check on restore
- **Portable exe** — single-file `dist/VostokVault.exe` (~18 MB) built with PyInstaller; fonts bundled

[0.1.0]: https://github.com/jonigirl/vostok-vault/releases/tag/v0.1.0
