# Architecture

The application is divided into a frontend UI (Flet) and a backend orchestration layer (subprocess and Unreal Python API).

## Directory Structure
* `manager.py`: The entry point for the UI.
* `build_mod.py`: The backend orchestrator, streamlined as an unbuffered, lightweight subprocess.
* `ue_import.py`: The script executed internally by Unreal Engine via remote execution.
* `components/`: Flet UI definitions.
* `controllers/`: Decoupled asynchronous controllers coordinating state changes.
* `views/`: Layout presentations for mod management and system settings.
* `utils/`: File I/O, state tracking, custom audio compilers, and parsing logic.

## Decoupled Pipeline Components
To preserve maintainability, the compilation and packaging pipeline is split into five distinct sub-modules:

1. **The Workspace Resolver (`ModWorkspace`):** Consolidates all FModel local directory trees, Unreal Engine virtual paths, cooked directories, and output target names into a single immutable context object. This keeps `build_mod.py` completely free of path-resolution arithmetic.
2. **The INI Overrides Context Manager (`GameIniCookContext`):** Implements a Python context manager (`with` statement) to handle `DefaultGame.ini` modification. It automatically backs up the active configuration, injects temporary micro-cooking parameters, and guarantees the restoration of the original `.ini` on exit (even in the event of compiler failures or process cancellations).
3. **The Staged Audio Resolver (`get_staged_audio_overrides`):** Scans the Pal's local `.palbaker_audio` subdirectory for pre-compiled WEM files and maps them directly to their target package paths, completely decoupling the audio pipeline from the Unreal Editor.
4. **The Pack Manifest Coordinator (`resolve_packaging_manifest`):** Automatically cleans up the compile environment, evaluates custom animations, custom shaders, UI icons, and staged audio overrides to assemble the final list of active resources for packaging.

## Pipeline Flow
1. **Blender Export:** `build_mod.py` calls `blender.exe` in background mode. It executes a Python expression to export the `.blend` file to `.fbx`. `global_scale=0.01` and `apply_scale_options='FBX_SCALE_ALL'` are enforced to fix standard Unreal Engine bone scaling issues. `add_leaf_bones=False` prevents hierarchy corruption.
2. **Unreal Engine Injection:** `build_mod.py` establishes a remote connection to the open Unreal Editor. It passes the target directory as a variable and executes the text content of `ue_import.py`.
3. **Asset Serialization (`ue_import.py`):**
    * Existing assets are wiped from the cache.
    * Textures are imported.
    * The `.fbx` is imported without generating standard materials, but forcing physics asset generation.
    * Material Instances are constructed from parsed JSON files and assigned specific parent materials based on naming conventions.
    * Skeletons and Physics Assets are relocated and renamed to match Palworld's expected path structures.
    * Materials are linked to the skeletal mesh slots.
4. **Staged Audio Compilation (On-The-Fly):** Custom audio overrides (WAV, MP3, OGG) are processed directly inside the controller during file selection. Non-WAV inputs are headlessly decoded to temporary WAV files via `vgmstream-cli` and compiled to `.wem` files using Wwise Console. The resulting files are named after their target numeric `media_id` and staged in `.palbaker_audio/WwiseAudio/Media/`.
5. **Cooking:** `build_mod.py` uses the `GameIniCookContext` to temporarily configure `DefaultGame.ini` to point `DirectoriesToAlwaysCook` strictly to the target folder and its associated skeleton folder. `UnrealEditor-Cmd.exe` is called with `-run=cook` and `-Map=/Engine/Maps/Entry` to perform a targeted cook.
6. **Packaging:** `UnrealPak.exe` is called. The script iterates through the cooked directory and appends any staged `.wem` audio overrides directly to the response file. It excludes `.uasset`, `.uexp`, and `.ubulk` files matching `Skeleton` or `PhysicsAsset` (unless custom animations are shipped). The output is deposited into the designated target folder or the game's `Paks/palBaker` directory.