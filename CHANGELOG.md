# Changelog

All notable changes to Vostok Vault will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.1] - 2026-05-11

### Added

- **Save Repair** — initial implementation; detects items in character and shelter saves that belong to mods no longer present in the backup, then creates a cleaned copy of the backup with those items removed; covers items held directly in inventory slots, items stored in vanilla shelter containers, and mod items nested as attachments on vanilla weapons; repaired backups are labelled `(repaired)` in the backup list; note: custom shelter `.tres` files added by a mod (not part of the base game's tracked file list) are not included in backups and therefore cannot be repaired
- **Status bar** — persistent bar below the toolbar shows current app status and version; notifications (save changed, repair detected) display here rather than inline with the buttons
- Traders tab: completed tasks now shown with a green dot indicator

### Changed

- Version shown in title bar and startup status message
- Status messages shortened to fit without truncation

### Fixed

- Backup tabs now prefilled in the background after parsing; GDI font handles released on close (prevents handle leak when app is open for extended periods)
- Repair correctly strips orphaned mod attachment refs nested inside vanilla weapon blocks
- Orphan detection now flags saves where a modded item appears only as an attachment (not in a direct inventory slot)

## [0.5.0] - 2026-05-11

### Added

- **Traders tab** — shows all traders present in the save with their full task list; each task marked ✓ (complete) or ○ (incomplete); live tax rate displayed per trader; traders ordered by in-game encounter sequence (generalist → doctor → gunsmith); bundled static catalog (`data/traders_catalog.json`) so task names are always available without parsing game files
- **MCM settings tab** — displays Mod Configuration Menu settings for each backup, grouped by mod
- **Auto-update checker** — checks GitHub releases for a newer version; toggle in Settings; toolbar button appears when an update is available
- **Storage: container grouping** — shelter items now grouped under the named furniture container they are stored in (e.g. Freezer, Shelf); floor items listed separately
- **Storage: category filter** — filter storage items by category (Weapons, Ammo, Medical, etc.)
- **Rarity sort and weight column** — inventory table supports sorting by rarity; weight column added
- **File watcher recovery** — watcher now recovers gracefully if `SAVE_DIR` disappears (e.g. game uninstalled or drive ejected) and resumes when it returns
- `TRACKED_FILES` split into `GAME_TRACKED_FILES` and `MOD_TRACKED_FILES` for finer change detection

### Changed

- Backup selection performance: `.tres` files parsed off the UI thread; each tab renders lazily on first open; all tabs show a loading indicator while parsing
- Storage tab: shelters with no items are hidden entirely (previously showed an "Empty" label)
- Traders tab: only traders present in the current save are shown (previously showed all catalog traders regardless of save state)
- Grid column widths aligned consistently across Character and Storage tabs
- UI polish: collapse-all button defaults, icon sizes, layout spacing throughout

### Fixed

- Backup manifest `storage_items` count now covers all 5 shelter types (Cabin, Tent, Attic, Classroom, Bunker); previously only Cabin and Tent were counted

## [0.4.0] - 2026-05-08

### Changed

- Overview tab: removed redundant Tag row; date now shown in friendly format ("Today HH:MM", "Yesterday HH:MM", "8 May HH:MM")
- Character tab: items grouped by collapsible category sections (Armour, Weapons, Gear, Pockets); expand state persists across selections
- Storage tab: filter input added; section header shows dynamic item count; section expand state persists across filter redraws; filter matches both item ID and display name; sort bar added (Name / Weight / Condition / Amount, with ascending/descending toggle)
- Mods tab: Was Active column replaced with a status dot indicator (green/red)
- Toolbar: Delete button separated with a 1 px divider and prefixed with a trash icon
- Backup cards: equipped and stored item counts shown in card subtitle
- Backup cards: friendly date format, colored border (red for Ironman, gray otherwise), visual polish throughout
- Inventory table: display names, item icons (28px), rarity colour dots, weight lookup loaded from `data/items.json`; row font 14px with increased padding
- `_on_rename()` in `app.py`: manifest write now uses `.tmp` + `.replace()` atomic pattern
- `_create_backup_locked()` in `backup.py`: single `datetime.now()` capture ensures folder name and `created` field are always identical
- Secondary text (`gray55`) raised to `gray65` throughout for WCAG AA contrast compliance

### Fixed

- Storage tab crash (`KeyError`) caused by mutating the CTkTabview internal segmented button label while tab dict keys remained unchanged

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

[0.5.0]: https://github.com/jonigirl/vostok-vault/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/jonigirl/vostok-vault/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/jonigirl/vostok-vault/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/jonigirl/vostok-vault/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/jonigirl/vostok-vault/releases/tag/v0.1.0
