# Changelog

All notable changes to Vostok Vault will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Mods section in the Overview tab and the Mods tab now clearly show the mods that were active **when the backup was created**, not the current game state — heading renamed to "Mods at Backup Time", column header renamed to "Was Active", and a subtitle added to the Mods tab
- Restore confirmation dialog now warns the user if their current game session has not been backed up, advising them to use "+ Backup Now" first if they want to keep a named copy

### Added

- `current_save_needs_backup()` in `backup.py` — compares tracked save file mtimes against the most recent non-restore backup to detect an unsaved session

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
