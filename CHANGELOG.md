# Changelog

All notable changes to Vostok Vault will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-05-08

### Added

- `scripts/build_item_db.py` (rewritten) — extracts item data directly from decompiled game files via GDRETools full recovery of `RTV.pck`; produces `data/items.json` (249 items) and `data/icons/` (246 PNGs) without any wiki dependency
- `data/icons/` — item icon PNGs extracted from game files, bundled with the exe
- `paths.py` — `ITEMS_JSON` and `ICONS_DIR` constants with `sys._MEIPASS` support for packaged builds
- Ironman difficulty (`difficulty = 3`) — backup cards show `· Ironman` in red; save detail panel shows a red `⚠ Ironman — character is deleted on death` warning below the Difficulty row
- `test_difficulty_names_ironman` added to test suite; traversal-guard tests for `restore_backup` and `delete_backup`; Ironman `parse_world` test

### Changed

- Item rarity colouring in the inventory table now loaded from `data/items.json` (game-authoritative) instead of a hardcoded wiki-sourced lookup table
- `DIFFICULTY_NAMES` in `constants.py` extended with `3: "Ironman"`
- `vostok-vault.spec` bundles `data/items.json` and `data/icons/` with the exe
- README placeholder clone URL and outdated keyboard-nav limitation fixed
- `delete_backup` — path-traversal guard added (was missing); rejects any path outside `BACKUP_DIR` or equal to it
- `restore_backup` — traversal check now uses `is_relative_to()` and rejects `BACKUP_DIR` root itself
- `save_settings` — now uses atomic `.tmp` + `replace()` write to avoid corruption on crash
- `settings.py` — `import json` moved to module level
- Both `_TagDialog` and `_SettingsDialog` now call `transient(parent)` so they stay above the main window
- `_TagDialog` entry limited to 60 characters via Tk validation

### Removed

- `scripts/enrich_item_db.py` — wiki enrichment pipeline removed; game files are now the authoritative source
- `scripts/check_wiki_updates.py` — wiki change detection no longer needed

## [0.2.0] - 2026-05-08

### Added

- `src/vostok_vault/widgets/dialogs.py` — `_TagDialog` and `_SettingsDialog` extracted from `app.py`
- `_ITEM_SUBTREES` allow-list in `tres_parser.py` — storage tab now only shows items from known vanilla subtrees; mod-injected paths under `res://Items/` are filtered out
- `current_save_needs_backup()` in `backup.py` — compares tracked save file mtimes against the most recent non-restore backup to detect an unsaved session
- `config.py` split into focused modules: `paths.py`, `constants.py`, `fonts.py`, `settings.py`, `logging_setup.py`; `config.py` kept as a backward-compatible re-export shim
- `scripts/build_item_db.py` — scans local backups to build a local item reference database (`data/items.json`)
- `scripts/enrich_item_db.py` — enriches the item DB with wiki-sourced data: rarity, price, wiki name/slug, crafting uses, trader task requirements
- `scripts/check_wiki_updates.py` — manually triggered script to check roadtovostok.wiki for item data changes after game patches
- Inventory items coloured by rarity — rare items shown in blue, legendary in gold
- `parse_validator` and extended `parse_world` (shelters count, weather time) added to `tres_parser.py`
- Disclaimer added to README: not affiliated with Road to Vostok Ltd.; item data sourced from saves and the community wiki

### Changed

- Mods section in the Overview tab and the Mods tab now clearly show the mods that were active **when the backup was created** — heading renamed to "Mods at Backup Time", column header renamed to "Was Active", subtitle added to the Mods tab
- Restore confirmation dialog now warns the user if their current game session has not been backed up
- Manifest writes are now atomic — written to a `.tmp` file then renamed with `os.replace()` to avoid corruption on crash
- Backup cards in the left panel are now keyboard-focusable (Tab order) with a visible blue focus border; Enter/Space activates the card
- Secondary label/description text contrast raised from `gray55` → `gray70` / `gray50` → `gray65` (WCAG 1.4.3)
- Mod chips in the Overview tab now wrap into rows of 3 instead of overflowing a single line
- Rename dialog now uses the same `_TagDialog` as the backup dialog, pre-filled with the current tag
- Settings dialog shows a note that the log path contains the Windows username
- Mod display names corrected — all 6 supported mods now shown with accurate names

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

[0.3.0]: https://github.com/jonigirl/vostok-vault/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/jonigirl/vostok-vault/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/jonigirl/vostok-vault/releases/tag/v0.1.0
