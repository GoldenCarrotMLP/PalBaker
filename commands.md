# PalBaker v1.0 Headless CLI Complete Specification

This document serves as the definitive reference for the PalBaker Command Line Interface. All commands output strictly parsed, single-line JSON envelopes to STDOUT on completion (or newline-delimited JSONL lines during active compilation streams) [todo.md].

---

### 1. Global & State Management (`manager`)
Scans workspaces, compiles index datastores, and manages the in-memory UI cache.

*   **List Discovered Mods**
    *   **Description:** Scans both vanilla FModel exports and active Altermatic working directories to return a structural JSON array of discovered mod configurations [utils/scanner.py].
    *   **Command:** `python palbaker_cli.py manager list [--show-unextracted]` [UI_detachment_plan.md]
    *   **Flags:**
        *   `--show-unextracted`: Includes vanilla game-archive characters that have not been physically extracted yet [manager.py].
    *   **STDOUT Contract:** `{"status": "success", "data": [ { "name": "WeaselDragon", "pak_status": "Unpacked", ... } ]}` [cli_queries_dump.json]

*   **Build Localization & Reference Databases**
    *   **Description:** Invokes Cue4Parse to extract English localization DataTables, active skills, partner actions, overworld spawners, and camera offset matrices, compiling them into clean reference JSON caches [deps/active_skills_cache.json, deps/partner_skills_cache.json].
    *   **Command:** `python palbaker_cli.py manager build-db` [UI_detachment_plan.md]
    *   **STDOUT Contract:** `{"status": "success", "message": "Pal database metrics built and pre-cached successfully."}` [utils/extractor/db_builder.py]

*   **Retrieve Consolidated Cached Data**
    *   **Description:** Returns all parsed active skills, passive traits, partner abilities, learnset tables, wild spawners, and localized text files over stdout in a single round-trip, preventing repetitive file I/O operations [ui_client/dispatcher.py].
    *   **Command:** `python palbaker_cli.py manager get-caches` [utils/cli/manager_handlers.py]
    *   **STDOUT Contract:** `{"status": "success", "data": { "active_skills": {...}, "templates": {...}, "pal_names": {...} }}` [cli_queries_dump.json]

---

### 2. Configuration Settings (`config`)
Read and write settings inside `manager_settings.json` [utils/config.py].

*   **Get Active Settings**
    *   **Description:** Returns a dictionary containing all configured executable paths, workspace directories, and rendering parameters [utils/config.py].
    *   **Command:** `python palbaker_cli.py config get` [palbaker_cli.py]
    *   **STDOUT Contract:** `{"status": "success", "data": { "fmodel_output": "...", "ue_root": "...", "blender": "..." }}` [cli_queries_dump.json]

*   **Set Configuration Key**
    *   **Description:** Overwrites or registers a settings parameter in `manager_settings.json` [palbaker_cli.py].
    *   **Command:** `python palbaker_cli.py config set <key> <value>` [UI_detachment_plan.md]
    *   **Arguments:**
        *   `<key>`: Mapped settings keys (`fmodel_output` [palbaker_cli.py], `ue_root` [palbaker_cli.py], `uproject` [palbaker_cli.py], `blender` [palbaker_cli.py], `palworld_exe` [palbaker_cli.py], `show_mapped` [palbaker_cli.py]).
        *   `<value>`: String directory paths, filenames, or Boolean toggles.
    *   **STDOUT Contract:** `{"status": "success", "message": "Updated <key>."}` [palbaker_cli.py]

---

### 3. Audio Customization (`audio`)
Modifies and previews Pal cries and voice overrides [UI_detachment_plan.md].

*   **Apply Custom Voice Override**
    *   **Description:** Headlessly decodes an MP3/OGG source to WAV using `vgmstream-cli` and compiles it into a `.wem` package via Wwise Console, naming the output after the target Wwise `media_id` [utils/audio_helper.py].
    *   **Command:** `python palbaker_cli.py audio set <mod_name> <cry_name> <audio_path>` [utils/cli/mod_handlers.py]
    *   **Arguments:**
        *   `<mod_name>`: Internal Pal folder name (e.g. `PinkCat` [test_audio_cli.py]).
        *   `<cry_name>`: Mapped cry states (`Normal`, `Joy`, `Anger`, `Sorrow`, `Pain`, `Death`) [utils/audio_helper.py].
        *   `<audio_path>`: Absolute file path of the source audio.
    *   **STDOUT Contract:** `{"status": "success", "message": "Converted and staged Joy -> <media_id>.wem"}` [utils/audio_helper.py]

*   **Revert Override to Vanilla**
    *   **Description:** Deletes the custom override and its compiled `.wem` from your active staging workspace [utils/audio_helper.py].
    *   **Command:** `python palbaker_cli.py audio clear <mod_name> <cry_name>` [utils/cli/mod_handlers.py]
    *   **STDOUT Contract:** `{"status": "success", "message": "Successfully cleared custom override for <cry_name>."}` [utils/cli/mod_handlers.py]

*   **Preview Voice Asset**
    *   **Description:** Decodes and plays a custom audio override or extracts the original `.wem` file from your game archives to play it on your system speakers [utils/cli/mod_handlers.py].
    *   **Command:** `python palbaker_cli.py audio play <mod_name> <cry_name>` [utils/cli/mod_handlers.py]
    *   **STDOUT Contract:** `{"status": "success", "message": "Playing transcoded MP3/OGG preview."}` [utils/cli/mod_handlers.py]

---

### 4. Standard Compilation Pipeline (`mod`)
Executes asset extractions, mesh import bakes, targeted cooks, and pak assemblies [UI_detachment_plan.md, build_mod.py].

*   **Execute Pipeline Phase**
    *   **Description:** Runs the requested action for the target Pal. Long-running actions run through `build_mod.py` and output real-time progress percentages over JSONL [todo.md].
    *   **Command:** `python palbaker_cli.py mod <action> <mod_name> [options]` [utils/cli/mod_handlers.py]
    *   **Arguments:**
        *   `<mod_name>`: Internal Pal folder name (e.g. `BadCatgirl` [tests/test_01_preflight.py]).
        *   `<action>`: Mapped compiler actions:
            *   `extract`        : Extracts raw PSK/PNG/JSON meshes via Cue4Parse [utils/extractor/asset_cloner.py].
            *   `create-blend`   : Converts the PSK to `.blend` and generates a sidecar file [build_mod.py].
            *   `push`           : Exports FBX from Blender and imports it into Unreal Engine [build_mod.py].
            *   `refresh-blend`  : Scans Blender to sync material slots and shape keys [build_mod.py].
            *   `cook`           : Configures `DefaultGame.ini` and cooks the mod folder [build_mod.py].
            *   `pack`           : Packages cooked assets into `_P.pak` (excluding skeletons) [build_mod.py].
            *   `full`           : Runs `push` $\rightarrow$ `cook` $\rightarrow$ `pack` in sequence [build_mod.py].
            *   `decompile`      : Reverse-engineers cooked `.uassets` back to `.blend` [utils/plugins/decompiler.py].
            *   `set-icon`       : Copies and stages a custom icon PNG into the workspace [utils/cli/mod_handlers.py].
            *   `browse-ue`      : Highlights the folder inside Unreal Editor [palbaker_cli.py].
            *   `ping`           : Handshakes Unreal Editor to verify remote execution [palbaker_cli.py].
            *   `cancel-pipeline`: Forces any running `UnrealEditor-Cmd.exe` or `UnrealPak.exe` processes to close [utils/cli/mod_handlers.py].
    *   **Options:**
        *   `--overwrite`: Forces overriding of existing `.blend` workspaces during decompilation [utils/plugins/decompiler.py].
        *   `--path <path>`: Local file path of your custom PNG (specifically for `set-icon` [utils/cli/mod_handlers.py]).
    *   **JSONL Stream Contract:** 
        `{"type": "progress", "percent": 0.55, "message": "Importing skeletal mesh..."}` [utils/cli/mod_handlers.py]  
        `{"type": "log", "level": "standard", "message": "Import completed successfully."}` [utils/cli/mod_handlers.py]

---

### 5. Altermatic Multi-Model Variants (`altermatic`)
Creates dynamic gender meshes, material reskins, and spawn configs [UI_detachment_plan.md].

*   **Toggle Altermatic Engine**
    *   **Description:** Enables or disables Altermatic variant swaps for the target Pal inside its local `_altermatic.json` manifest [utils/altermatic/manifest_manager.py].
    *   **Command:** `python palbaker_cli.py altermatic toggle <mod_name> <on|off>` [ui_client/dispatcher.py]
    *   **STDOUT Contract:** `{"status": "success", "message": "Altermatic Mod Mode enabled for <mod_name>."}` [utils/altermatic/__init__.py]

*   **List Variants**
    *   **Description:** Returns all variants configured inside the Pal's local `_altermatic.json` manifest [utils/altermatic/manifest_manager.py].
    *   **Command:** `python palbaker_cli.py altermatic list <mod_name>` [ui_client/dispatcher.py]
    *   **STDOUT Contract:** `{"status": "success", "data": [ { "SkeletonSource": "base", "is_base": true, ... } ]}` [cli_queries_dump.json]

*   **Add Variant**
    *   **Description:** Stages a new variant, optionally cloning the target `.blend` skeleton to a new file [utils/altermatic/cloner.py].
    *   **Command:** `python palbaker_cli.py altermatic add <mod_name> <label_name> [--custom] [--source <source_choice>]` [utils/altermatic/cloner.py]
    *   **Flags:**
        *   `--custom`: Clones and provisions a separate `.blend` workspace on disk [utils/altermatic/cloner.py].
        *   `--source <choice>`: Source blend model template name (e.g. `base` or another variant) [utils/altermatic/cloner.py].
    *   **STDOUT Contract:** `{"status": "success", "message": "Successfully generated variant: <label_name>"}` [utils/altermatic/cloner.py]

*   **Delete Variant**
    *   **Description:** Removes a variant configuration from the manifest and deletes its custom `.blend` model [utils/altermatic/__init__.py].
    *   **Command:** `python palbaker_cli.py altermatic delete <mod_name> <index_number>` [utils/altermatic/__init__.py]
    *   **STDOUT Contract:** `{"status": "success", "message": "Successfully deleted Altermatic variant at index <index_number>"}` [ui_client/dispatcher.py]

*   **Save Variant Properties**
    *   **Description:** Updates material overrides, gender constraints, lucky/rare attributes, passive traits, and shape keys for a variant [utils/altermatic/__init__.py].
    *   **Command:** `python palbaker_cli.py altermatic save <index_number> --data "<json_string>"` [utils/altermatic/__init__.py]
    *   **STDOUT Contract:** `{"status": "success", "message": "Successfully saved Altermatic variant structure."}` [ui_client/dispatcher.py]

*   **Sync Sidecar Metadata**
    *   **Description:** Scans the active Blender file to update material slots and blendshapes in your `_blend.json` sidecar on the spot [utils/altermatic_helper.py].
    *   **Command:** `python palbaker_cli.py altermatic sidecar <mod_name> <blend_name>` [ui_client/dispatcher.py]
    *   **STDOUT Contract:** `{"status": "success", "data": { "materials": {...}, "MorphTarget": [...] }}` [utils/altermatic_helper.py]

*   **Get Mod Metadata**
    *   **Description:** Returns all available materials, `.blend` files, and classification data for your Altermatic workspace [ui_client/dispatcher.py].
    *   **Command:** `python palbaker_cli.py altermatic metadata <mod_name>` [ui_client/dispatcher.py]
    *   **STDOUT Contract:** `{"status": "success", "blend_files": ["<mod_name>.blend"], "category": "Monster"}` [cli_queries_dump.json]

*   **Open Blend File**
    *   **Description:** Launches your configured Blender executable directly to edit the selected variant [utils/altermatic/__init__.py].
    *   **Command:** `python palbaker_cli.py altermatic open-blend <mod_name> <blend_name|base> [--category <category>]` [utils/altermatic/__init__.py]
    *   **STDOUT Contract:** `{"status": "success", "message": "Blender launched successfully."}` [ui_client/dispatcher.py]

---

### 6. Standalone Pal Creator (`creator`)
Generates standalone custom species IDs, learnsets, and custom stats [UI_detachment_plan.md].

*   **List Custom Standalone Pals**
    *   **Description:** Scans `Palbaker/Creator` and parses all custom standalone Pal configurations [utils/creator/pal_manager.py].
    *   **Command:** `python palbaker_cli.py creator list` [ui_client/dispatcher.py]
    *   **STDOUT Contract:** `{"status": "success", "data": [ { "CharacterID": "Furret", "Learnset": [...], ... } ]}` [cli_queries_dump.json]

*   **Instantiate Standalone Pal**
    *   **Description:** Clones a parent template's attributes, learnset, and spawns, and headlessly compiles a stand-alone, binary-patched Actor Blueprint via UAssetGUI [utils/creator/pal_manager.py, utils/creator/palschema_exporter.py].
    *   **Command:** `python palbaker_cli.py creator add <pal_id> --template <parent_pal_id>` [utils/creator/pal_manager.py]
    *   **STDOUT Contract:** `{"status": "success", "message": "Successfully created brand new Pal template: <pal_id>"}` [utils/creator/pal_manager.py]

*   **Delete Standalone Pal**
    *   **Description:** Permanently deletes the custom Pal's configuration JSON and its exported PalSchema mod folders [utils/creator/pal_manager.py].
    *   **Command:** `python palbaker_cli.py creator delete <pal_id>` [utils/creator/pal_manager.py]
    *   **STDOUT Contract:** `{"status": "success", "message": "Deleted custom Pal config: <pal_id>"}` [utils/creator/pal_manager.py]

*   **Update Standalone Pal Properties**
    *   **Description:** Saves edited parameters (stats, spawns, learnset, element, abilities) and exports the updated JSON schemas to PalSchema [utils/creator/pal_manager.py].
    *   **Command:** `python palbaker_cli.py creator update <pal_id> --data "<json_string>"` [utils/creator/pal_manager.py]
    *   **STDOUT Contract:** `{"status": "success", "message": "Successfully saved Pal Creator adjustments: <pal_id>"}` [utils/creator/pal_manager.py]

*   **Patch Actor Blueprint**
    *   **Description:** Extracts and patches the parent template blueprint, renaming core references while preserving animation blueprint bindings [utils/creator/palschema_exporter.py, utils/blueprint_patcher.py].
    *   **Command:** `python palbaker_cli.py creator refresh-bp <pal_id>` [utils/creator/__init__.py]
    *   **STDOUT Contract:** `{"status": "success", "message": "Successfully refreshed standalone Actor Blueprint for <pal_id>!"}` [utils/creator/__init__.py]

---

### 7. Environment Health & Diagnostics (`env`)
Handles compiler diagnostics, auto-fixes, and UE4SS/PalSchema integrations [UI_detachment_plan.md].

*   **Verify Environment Health**
    *   **Description:** Scans for compliant MSVC 14.3x compiler toolsets, verifies `BuildConfiguration.xml`, check C++ plugin compilation, and reviews INI configurations [utils/plugin_manager.py].
    *   **Command:** `python palbaker_cli.py env verify` [ui_client/dispatcher.py]
    *   **STDOUT Contract:** `{"status": "success", "data": { "error": null, "needs_remote_exec_enable": false, "missing_assets": [] }, "message": "Verification completed."}` [cli_queries_dump.json]

*   **Install/Uninstall UE4SS**
    *   **Description:** Downloads, unzips, and registers UE4SS binaries in the game's Win64 folder without deleting your local mods [utils/ue4ss_helper.py].
    *   **Command:** `python palbaker_cli.py env ue4ss-install --action <action_key>` [utils/cli/env_handlers.py]
    *   **Arguments:**
        *   `--action`: Mapped installation actions:
            *   `install-palworld`: Installs Okaetsu's Palworld-Experimental branch [utils/ue4ss_helper.py].
            *   `install-latest`  : Installs the main Latest-Experimental branch [utils/ue4ss_helper.py].
            *   `repair`          : Re-copies and registers missing or corrupted DLL loader files [utils/ue4ss_helper.py].
            *   `uninstall`       : Cleans all UE4SS files from the game folder [utils/ue4ss_helper.py].
    *   **STDOUT Contract:** `{"status": "success", "message": "UE4SS management completed!"}` [views/settings_view.py]

*   **Install/Uninstall PalSchema Mod**
    *   **Description:** Installs the PalSchema mod, updates `mods.txt` to enable dependencies, and configures UE4SS loading parameters [utils/palschema_helper.py].
    *   **Command:** `python palbaker_cli.py env install-plugin --action <install|uninstall>` [utils/cli/env_handlers.py]
    *   **STDOUT Contract:** `{"status": "success", "message": "PalSchema installation completed successfully!"}` [utils/palschema_helper.py]

*   **Fetch Integration Status**
    *   **Description:** Queries the system to check if UE4SS is active, which branch is installed, whether PalSchema is hooked, and if Unreal is running [utils/ue4ss_helper.py, utils/palschema_helper.py].
    *   **Command:** `python palbaker_cli.py env status` [ui_client/dispatcher.py]
    *   **STDOUT Contract:** `{"status": "success", "palschema": { "status": "Installed" }, "remote_exec_enabled": true}` [cli_queries_dump.json]

*   **Launch Unreal Editor**
    *   **Description:** Instantly opens your configured `.uproject` file inside Unreal Editor headlessly [utils/plugins/installer.py].
    *   **Command:** `python palbaker_cli.py env launch-unreal` [ui_client/dispatcher.py]
    *   **STDOUT Contract:** `{"status": "success", "message": "Unreal Editor successfully launched!"}` [utils/plugins/installer.py]

*   **Enable Remote Execution Settings**
    *   **Description:** Safely injects `bRemoteExecution=True` and `bDeveloperMode=True` into your project's `DefaultEngine.ini` [utils/plugins/installer.py].
    *   **Command:** `python palbaker_cli.py env enable-remote-exec` [ui_client/dispatcher.py]
    *   **STDOUT Contract:** `{"status": "success", "message": "Python Remote Execution successfully enabled!"}` [utils/plugins/installer.py]

*   **Autodetect System Paths**
    *   **Description:** Runs background autodetectors to scan standard system folders for active Unreal Engine 5.1, Blender, and Palworld installations [utils/autofill_helper.py].
    *   **Command:** `python palbaker_cli.py env autodetect` [ui_client/dispatcher.py]
    *   **STDOUT Contract:** `{"status": "success", "palworld_exe": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Palworld\\Palworld.exe", "blender_versions": [...]}` [cli_queries_dump.json]