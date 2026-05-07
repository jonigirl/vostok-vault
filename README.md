# Vostok Vault

A save manager for [Road to Vostok](https://roadtovostok.com/) — a hardcore survival game with no in-game save system.

Road to Vostok only saves progress when you enter a shelter. If you die outside, you lose everything on you. If you die in the permadeath zone (Vostok itself), you lose everything everywhere. Vostok Vault lets you snapshot your save state before dangerous runs and restore it if things go wrong.

## Features

- **Backup** — snapshot your current save with a custom tag
- **Restore** — roll back to any previous snapshot (your current state is auto-backed up first as a safety net)
- **Browse** — view in-game day, time, season, weather, and difficulty for each backup
- **Inventory view** — see what's equipped on your character and what's in your shelters
- **Mod tracking** — each backup records which mods were active and their versions
- **Auto-backup** — watches your save folder and creates a backup automatically when the game saves
- **Tag and delete** — rename or remove old backups

## Requirements

- Windows
- Python 3.12+
- [UV](https://docs.astral.sh/uv/) (package manager)
- Road to Vostok installed via Steam

## Installation

```powershell
git clone https://github.com/your-username/vostok-vault.git
cd vostok-vault
uv sync
```

## Usage

```powershell
uv run vault
```

The GUI will open. Your Road to Vostok save folder is detected automatically from `%APPDATA%\Road to Vostok\`.

Backups are stored in `%APPDATA%\Road to Vostok\vostok-vault-backups\` — separate from the game's own backup folder.

## Building the exe

```powershell
pwsh build.ps1         # build only
pwsh build.ps1 -Clean  # clean previous build first
```

Output: `dist/VostokVault.exe` (~18 MB, standalone, no installer needed).

## Running tests

```powershell
uv run pytest -v
```

## Settings and log file

Settings are stored in:

```
%APPDATA%\Road to Vostok\vostok-vault-backups\settings.json
```

This file persists your font preference and debug logging toggle across sessions.

The log file is at:

```
%APPDATA%\Road to Vostok\vostok-vault-backups\vostok-vault.log
```

Debug logging is **off by default**. Enable it in **⚙ Settings** to record detailed activity. If you're reporting a bug, enable debug logging, reproduce the issue, then attach the log file to your report.

## Font

Vostok Vault ships with [Atkinson Hyperlegible](https://brailleinstitute.org/freefont) as the default font — an open-source typeface designed for readability and low-vision users. An OpenDyslexic option is available in **⚙ Settings**.

Font files are licensed under the [SIL Open Font License 1.1](assets/fonts/OFL.txt).

## Known limitations

- **Windows only** — the save folder path is Windows-specific (`%APPDATA%\Road to Vostok\`)
- **Storage tab** — may show non-inventory entries from some mods or game updates; scheduled for a future fix
- **Backup list** — mouse-only; keyboard navigation not yet supported

## Troubleshooting

**Save folder not detected**
Vostok Vault looks for `%APPDATA%\Road to Vostok\`. If Road to Vostok has never been launched on this machine, the folder won't exist yet. Launch the game once to create it, then restart Vostok Vault.

**Restore fails**
Close Road to Vostok before restoring. The game locks save files while running.

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

Vostok Vault is an unofficial fan project and is not affiliated with, endorsed by, or connected to Road to Vostok Ltd. in any way.

Item data shown in the app is sourced from player save files and [roadtovostok.wiki](https://roadtovostok.wiki/) — an independent, community-run wiki that is itself not affiliated with Road to Vostok Ltd.

All game content, assets, and trademarks are the property of Road to Vostok Ltd.
