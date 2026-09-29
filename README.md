# Chunk Reset CLI

A command-line tool that deletes chunks within a rectangular area in **Minecraft Bedrock Edition** and Java Edition worlds, so they regenerate the next time you visit them in-game.

The primary target environment is **Windows + PowerShell with Bedrock Edition**. This tool uses [Amulet Core](https://github.com/Amulet-Team/Amulet-Core) as a library dependency and does **not** require the Amulet Map Editor application.

> Japanese: [README.ja.md](README.ja.md)

---

## Table of Contents

1. [Dependency Notice](#dependency-notice)
2. [License](#license)
3. [Setup (PowerShell)](#setup-powershell)
4. [Basic Usage](#basic-usage)
5. [World Folder Location (Windows Bedrock)](#world-folder-location-windows-bedrock)
6. [Coordinate Specification](#coordinate-specification)
7. [Pinned Chunks and `reset-all`](#pinned-chunks-and-reset-all)
8. [Options](#options)

---

## Dependency Notice

This project depends on **Amulet-Core**.

**This project does not redistribute any Amulet-Core source code.** Amulet-Core is used only as an external dependency installed via pip at runtime.

**Users of this software must hold a valid license to use Amulet-Core.** Amulet-Core is proprietary software; a license must be purchased to use it. For details, see:

https://www.amuletmc.com/legal

### MIT License Publication

The source code of **this project** is released under the [MIT License](LICENSE). Before publishing, the author confirmed on Discord with **gentlegiantJGC** (Amulet developer) that this would be acceptable, subject to the following conditions:

- No Amulet-Core code is redistributed.
- Users are clearly informed that a valid Amulet license is required.

Permission was granted accordingly.

---

## License

This project's source code is licensed under the MIT License. See [LICENSE](LICENSE) for the full text.

Amulet-Core remains subject to its own license terms. Using this CLI does not grant any rights to Amulet-Core beyond what your Amulet license provides.

---

## Setup (PowerShell)

Requires Python **3.11 or later** ([python.org](https://www.python.org/downloads/)).

After cloning the repository, run the following from the project root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

If `chunk-reset --help` displays the help text, installation succeeded.

> **Note:** `pip install` will download Amulet-Core as a dependency. You must have a valid Amulet license to use Amulet-Core legally.

---

## Basic Usage

### Before You Run (Required)

1. **Back up your world**
2. **Fully close Minecraft** (the tool will fail if LevelDB is locked)

### Workflow

```
① Identify the world folder path
        ↓
② Run with --dry-run to verify the target chunks (and confirm the path)
        ↓
③ Run for real if everything looks correct
```

#### ① Find the World Path

See [World Folder Location](#world-folder-location-windows-bedrock). You need the path to an **individual world folder** that contains `level.dat` and a `db` folder.

Replace the placeholders below with your environment's values:

| Placeholder | Meaning | Typical format |
|-------------|---------|----------------|
| `<USER_ID>` | Per–Microsoft-account folder name | Long numeric string |
| `<WORLD_ID>` | World folder name under `minecraftWorlds` | Alphanumeric (may end with `=`) |

```powershell
$userId = "<USER_ID>"
$worldId = "<WORLD_ID>"
$worldPath = "$env:APPDATA\Minecraft Bedrock\Users\$userId\games\com.mojang\minecraftWorlds\$worldId"
```

#### ② Dry Run

```powershell
chunk-reset $worldPath --from 0,0 --to 100,100 --dry-run
```

- If `World: ...` is printed, the **path is correct**
- `Chunks to delete (exist): N` shows how many chunks would be deleted
- Each chunk coordinate `(cx, cz)` is listed

#### ③ Execute

```powershell
chunk-reset $worldPath --from 0,0 --to 100,100
```

A confirmation prompt appears. Use `-y` to skip it:

```powershell
chunk-reset $worldPath --from 100,300 --to 200,400 -y
```

### Other Examples

```powershell
# Chunk coordinates
chunk-reset $worldPath --from 6,18 --to 12,25 --chunk-coords --dry-run

# Nether / End
chunk-reset $worldPath --from 0,0 --to 100,100 --dimension nether --dry-run
```

> **Path tips:** Because `Minecraft Bedrock` contains a space, quote paths when needed. `<WORLD_ID>` may end with **`=`**. In PowerShell use **`$env:APPDATA`** (not `%APPDATA%`, which is for cmd).

---

## World Folder Location (Windows Bedrock)

### Path to Pass

The first argument `world` must be an **individual world folder**:

```powershell
$userId = "<USER_ID>"
$worldId = "<WORLD_ID>"
"$env:APPDATA\Minecraft Bedrock\Users\$userId\games\com.mojang\minecraftWorlds\$worldId"
```

**Do not pass:**

| Path | Reason |
|------|--------|
| `...\Minecraft Bedrock\Users` | User list, not a world |
| `...\minecraftWorlds` | Parent folder of multiple worlds |
| In-game world display name only | Folder name is the internal `<WORLD_ID>` |

### Troubleshooting

- Fully close Minecraft and retry
- Confirm `level.dat` exists at the path
- If `--dry-run` shows `World: ...`, the path is correct
- Export the world as `.mcworld` in-game, extract it, and point the tool at that folder (good for backup/testing)

---

## Coordinate Specification

`--from` and `--to` take **two X,Z values** (comma-separated). Y is not used; the **full world height** is affected.

### Common Rules

- Order of `--from` / `--to` does not matter (min/max are computed automatically)
- Both ends are **inclusive**
- Deletion is in **chunk (16×16 block) units**; any touched chunk is removed **entirely**
- **Negative coordinates** are supported

### Negative Coordinates in PowerShell

Space-separated arguments can make values like `-352,736` look like options. Prefer `=` syntax:

```powershell
# Bad: space-separated (negative values may be parsed as options)
chunk-reset $worldPath --from -352,736 --to -100,800 --dry-run

# Good: = syntax (recommended)
chunk-reset $worldPath --from=-352,736 --to=-100,800 --dry-run

# Good: quoted
chunk-reset $worldPath --from "-352,736" --to "-100,800" --dry-run
```

Positive coordinates (e.g. `--from 100,200`) work fine with spaces.

### Block Coordinates (Default)

In-game coordinates are treated as **block coordinates**. The range is **snapped to 16-block chunk boundaries** (same behavior as Amulet Map Editor's Chunk tool).

```
Chunk (0,0) = blocks x: 0–15,  z: 0–15
Chunk (1,0) = blocks x: 16–31, z: 0–15
Chunk (0,1) = blocks x: 0–15,  z: 16–31
```

#### Example: Small Range (`--from 1,5 --to 2,10`)

| Item | Value |
|------|-------|
| Specified range (blocks) | x: 1–2, z: 5–10 |
| After snap | x: 0–15, z: 0–15 |
| Chunks deleted | **`(0, 0)` only — one chunk** |

Even a few blocks triggers deletion of the entire chunk `(0,0)` (**16×16 blocks**).

#### Example: Multiple Chunks (`--from 0,0 --to 31,31`)

| Item | Value |
|------|-------|
| Specified range (blocks) | x: 0–31, z: 0–31 |
| Chunks deleted | `(0,0)`, `(1,0)`, `(0,1)`, `(1,1)` — **4 chunks** |

#### Example: Larger Range (`--from 100,300 --to 200,400`)

All chunks covering blocks x: 100–200, z: 300–400 (after snap, roughly x: 96–207, z: 288–415).

### Chunk Coordinates (`--chunk-coords`)

Specify chunk indices directly:

```powershell
# Single chunk (0,0)
chunk-reset $worldPath --from 0,0 --to 0,0 --chunk-coords --dry-run

# Chunks x: 6–12, z: 18–25 (up to 7×8 = 56 chunks)
chunk-reset $worldPath --from 6,18 --to 12,25 --chunk-coords --dry-run
```

### Which Mode to Use

| Goal | Recommendation |
|------|----------------|
| Reset near in-game coordinates | Block coordinates (default) |
| You know chunk numbers | `--chunk-coords` |
| Verify targets accurately | Always run `--dry-run` first |

---

## Pinned Chunks and `reset-all`

Pinned chunks are chunks that `reset-all` will **never** delete. They are stored in a **directory**, one JSON file per dimension, and managed with `chunk-reset pin`. The pin commands only edit those files; they never open or modify a world.

`reset-all` deletes **every existing chunk in one dimension except the pinned ones**, so it is much more destructive than the rectangular reset. Back up the world first and always run `--dry-run` before a real run.

### Pin Directory and File Names

Pass the directory to `--pins` / `pin`. The file for the target dimension is chosen automatically by name:

| Dimension (`--dimension`) | File in the pin directory |
|---------------------------|---------------------------|
| `overworld` (default) | `pin_overworld.json` |
| `nether` | `pin_nether.json` |
| `end` | `pin_end.json` |

```
pins/
  pin_overworld.json
  pin_nether.json
  pin_end.json
```

Only the file for the dimension you are resetting is read. If it does not exist, the command fails.

### Safety Rules

`reset-all` refuses to run (and changes nothing) unless:

- the pin file for the target dimension exists, is valid, and defines **at least one pin**
- **at least one pinned chunk actually exists** in the world (protects against a wrong dimension or mistyped coordinates)

These checks also apply with `-y`. Only the dimension given by `--dimension` is affected; other dimensions are left untouched. Each pin file records its own `dimension`, and a file whose `dimension` does not match its use (for example `pin_overworld.json` copied and renamed to `pin_end.json`) is rejected.

### Managing Pins

Pins are stored as rectangles in **chunk coordinates**. `--from` / `--to` follow the same rules as the rectangular reset (block coordinates by default, `--chunk-coords` for chunk indices; see [Coordinate Specification](#coordinate-specification)). `--dimension` defaults to `overworld`.

```powershell
# Add a pin (creates the directory and file if missing)
chunk-reset pin add pins --from 0,0 --to 100,100 --label base
chunk-reset pin add pins --from=-352,736 --to=-100,800 --label farm
chunk-reset pin add pins --from 0,0 --to 3,3 --chunk-coords --dimension nether

# Show pins (chunk coordinates); all pin files, or one dimension
chunk-reset pin list pins
chunk-reset pin list pins --dimension nether

# Remove a pin by label, or by exactly the same area
chunk-reset pin remove pins --label farm
chunk-reset pin remove pins --from 0,0 --to 100,100
```

Labels are optional but must be unique within a dimension. Removing by area only matches a pin with exactly the same area (after snapping to chunks); use `pin list` to check.

File format (`pin_overworld.json`):

```json
{
  "version": 1,
  "dimension": "minecraft:overworld",
  "pins": [
    {"from": [0, 0], "to": [6, 6], "label": "base"}
  ]
}
```

### Running `reset-all`

```powershell
# 1. Check what would be kept and deleted
chunk-reset reset-all $worldPath --pins pins --dry-run

# 2. Run for real (prompts for confirmation; -y skips the prompt)
chunk-reset reset-all $worldPath --pins pins

# Other dimensions use their own file (pin_nether.json)
chunk-reset reset-all $worldPath --pins pins --dimension nether --dry-run
```

The summary shows the number of existing chunks, pinned chunks kept, and chunks to delete. Chunks next to a pinned area are regenerated by the game, so terrain seams can appear along the border of a pinned area.

### Protecting Pins in a Rectangular Reset

The normal rectangular reset can also honor the pins. Pass `--pins` with the directory and pinned chunks of the target dimension inside the area are skipped:

```powershell
chunk-reset $worldPath --from 0,0 --to 300,300 --pins pins --dry-run
```

The output shows `Chunks skipped (pinned, exist): N`. Without `--pins`, the rectangular reset deletes everything in the area as before. The pin file for the dimension must exist, but it may contain zero pins (a rectangle is a bounded operation).

---

## Options

| Option | Description |
|--------|-------------|
| `world` | Path to world folder (directory containing `level.dat`) |
| `--from X,Z` | One corner (required). For negatives, prefer `--from=-352,736` |
| `--to X,Z` | Opposite corner (required). For negatives, prefer `--to=-100,800` |
| `--dimension`, `-d` | `overworld` (default), `nether`, `end`, or `minecraft:overworld` form |
| `--chunk-coords` | Interpret coordinates as chunk indices |
| `--pins DIR` | Skip pinned chunks (reads `pin_<dimension>.json` in DIR) |
| `--dry-run` | List chunks without modifying the world |
| `-y`, `--yes` | Skip confirmation prompt |
