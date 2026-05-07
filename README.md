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

## Running tests

```powershell
uv run pytest -v
```

## License

MIT — see [LICENSE](LICENSE).
