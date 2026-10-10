---
name: palworld-assets
description: Find, extract and decompile vanilla Palworld assets (montages, anim sequences, action/module blueprints, datatables) from Pal-Windows.pak, and decompile PalBaker's cooked output, to compare a mod against its donor. Use when debugging PalBaker output, checking what a vanilla asset contains, or when the user references a game asset path.
---

# Palworld asset lookup

The helper script: `python .claude/skills/palworld-assets/pal_asset.py <cmd>` (from the repo root).

| Command | What it does |
|---|---|
| `find <regex>` | Searches `palbaker-cli/palworld_files_dir.txt` (every package in Pal-Windows.pak, no extensions). Do this first; it's instant. |
| `extract <pak path> [--fmt json\|raw]` | Uses cue4parse to extract the asset. `json` gives CUE4Parse's readable JSON, which is the best format for understanding an asset. Prints the output path. |
| `uagui <pak path>` | Extracts raw (`.uasset` and `.uexp`), then runs UAssetGUI `tojson`. This is the AST PalBaker actually patches and recompiles, so it is the source of truth for patching. |
| `tojson <file.uasset> [out]` | Runs UAssetGUI on a local file, such as a cooked mod asset under `<uproject>/Saved/Cooked/Windows/<Project>/Content/...`. |

Outputs go to `%TEMP%/claude/pal_assets/`.

## Which format to use
- **CUE4Parse JSON** (`extract`): resolved object names, `Properties` dicts and readable notifies. Use it to understand what an asset does.
- **UAssetGUI JSON** (`uagui`/`tojson`): `Imports`/`Exports`/`NameMap`, plus `Data` arrays of typed properties with negative import indices. This is what `utils/uasset_helper.py` and `utils/blueprint_patcher` mutate, so check it before writing patch code.

## Gotchas
- cue4parse patterns: an exact path needs an extension (`.uasset`). A path without an extension matches nothing. `raw` needs `.*` to get the `.uexp` too (the script handles this).
- The FModel exports under `H:\SteamLibrary\steamapps\common\Palworld\Output\Exports` and `<fmodel_output>\Exports` can be **stale or from mod paks**. When it matters, re-extract vanilla data, or `tojson` the freshly cooked file.
- Native class layouts (e.g. `UPalSkillModule_HorseTackle`, `EPalTackleState`) are in the UE4SS dump: `H:\SteamLibrary\steamapps\common\Palworld\Pal\Binaries\Win64\ue4ss\CXXHeaderDump\Pal.hpp`.
- Paths come from `palbaker-cli/manager_settings.json` (`palworld_exe`, `uproject`, `fmodel_output`).
- In the pipeline itself, use `utils/extractor/core.py::extract_game_files` and `utils/uasset_helper.py::{decompile_uasset, compile_uasset}`. Don't shell out separately.
