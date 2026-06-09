Detaching the UI from the execution logic to create a CLI-first architecture is an excellent architectural move. It will solve the Flet WebSocket clogging issues mentioned in your tech debt docs, allow for easy CI/CD integrations, and let you swap out Flet for a different frontend (like PyQt or a web dashboard) in the future.

Based on an analysis of your entire repository—including the `build_mod.py` orchestrator, `CreatorController`, `AltermaticController`, `SettingsController`, and the UAsset/Wwise compilation helpers—here is a comprehensive list of all the CLI commands your backend should support to fully power the current and future UI.

### 1. Global & State Management (`manager`)
These commands deal with the overarching state of the mod manager, settings, and database rebuilding.

*   `manager list [--filter-status <status>] [--show-unextracted]` 
    *   Returns JSON/list of all Pals, their badges, modified states, and paths.
*   `manager info <monsterName>` 
    *   Returns detailed JSON for a specific Pal (paths, active variants, audio overrides).
*   `manager build-db` 
    *   Executes `build_pal_names_map()` to extract game files via `cue4parse` and compile `pal_names_map.json` and local skill/spawner caches.
*   `manager config set <key> <value>` / `manager config get` 
    *   Get/set paths for FModel, UE 5.1, Blender, and Palworld.exe.

### 2. Standard Modding Pipeline (`mod`)
These commands replace the monolithic `build_mod.py` arguments and standard UI buttons.

*   `mod extract <monsterName>` 
    *   Runs `cue4parse` to dump `.psk`, `.png`, and `.json` assets for the specific Pal.
*   `mod create-blend <monsterName>` 
    *   Executes `blender_reconstruct.py` headlessly to convert the `.psk` into a ready-to-use `.blend` workspace.
*   `mod push <monsterName>` 
    *   Exports the `.fbx` via Blender and pushes it into Unreal Engine via Remote Execution (`ue_import.py`).
*   `mod refresh-layout <monsterName>` 
    *   Executes `blender_extractor.py` to sync bone/material slot layouts from the `.blend` file into the `_blend.json` sidecar.
*   `mod cook <monsterName> [--only]` 
    *   Modifies `DefaultGame.ini` and micro-cooks the target directory using `UnrealEditor-Cmd.exe`.
*   `mod pack <monsterName> [--only]` 
    *   Calls `UnrealPak.exe` to package the cooked assets (filtering out skeletons if no anims exist).
*   `mod full-pipeline <monsterName>` 
    *   Sequentially runs `push`, `cook`, and `pack`.
*   `mod decompile <monsterName> [--overwrite]` 
    *   Reverses UE modifications back into Blender via `ue_export.py`.
*   `mod browse-ue <monsterName>` 
    *   Focuses the Unreal Editor Content Browser on the target mod.
*   `mod set-icon <monsterName> <imagePath>` 
    *   Copies and formats a custom PNG into the workspace for packing.

### 3. Altermatic Variants (`altermatic`)
Commands that interact with `controllers/altermatic/`.

*   `altermatic list <monsterName>` 
    *   Lists all branching variants configured in the manifest.
*   `altermatic toggle <monsterName> <on|off>` 
    *   Enables/disables the Altermatic framework in the JSON manifest.
*   `altermatic add <monsterName> <variantLabel> [--clone-source <source.blend>] [--custom-mesh]` 
    *   Stages a new variant, optionally copying the base `.blend` file into a new file.
*   `altermatic update <monsterName> <variantLabel> --data '<json_payload>'` 
    *   Updates material slot overrides, shape key/morph targets, and conditional spawn logic (traits, gender, lucky).
*   `altermatic delete <monsterName> <variantLabel>` 
    *   Removes the variant and its associated `.blend` file.
*   `altermatic deploy <monsterName>` 
    *   Compiles `palbaker-<monsterName>.json` and moves it to the game's `~Mods/SwapJSON/` directory.

### 4. Custom Pal Creator (`creator`)
Commands that interact with `controllers/creator/` and `blueprint_patcher.py`.

*   `creator list` 
    *   Lists all standalone custom Pals mapped in the `Palbaker/Creator/` folder.
*   `creator add <customPalId> --template <templateId>` 
    *   Clones a parent (e.g., WeaselDragon) to initialize a new standalone ID.
*   `creator update <customPalId> --data '<json_payload>'` 
    *   Mutates the JSON schema (HP, Atk, Def, typing, wild spawn rules, learnsets).
*   `creator refresh-bp <customPalId>` 
    *   Executes `UAssetGUI.exe` to decompile the parent actor blueprint, regex-patch the class paths, and recompile it.
*   `creator delete <customPalId>` 
    *   Wipes the creator JSON and the exported PalSchema mod folder.
*   `creator deploy <customPalId>` 
    *   Translates the creator JSON into PalSchema structure (`pals/`, `spawns/`, `raw/DT_PalBPClass.json`) and copies it to `UE4SS/Mods/PalSchema/mods/`.

### 5. Audio Replacer (`audio`)
Commands that interact with `AudioController`.

*   `audio list <monsterName>` 
    *   Lists valid cries (Normal, Joy, Anger, Sorrow, Pain, Death) and checks for active overrides.
*   `audio set <monsterName> <cryName> <audioFilePath>` 
    *   Decodes `.mp3/.ogg` using `vgmstream-cli` and recompiles to `.wem` using `WwiseConsole.exe`.
*   `audio clear <monsterName> <cryName>` 
    *   Deletes the source override and compiled `.wem` from the `.palbaker_audio` staging folder.
*   `audio play <monsterName> <cryName>` 
    *   Plays the custom override, or dynamically extracts and decodes the vanilla `.wem` file for preview using `vgmstream-cli`.

### 6. Environment & Setup (`env`)
Commands that deal with `plugin_manager.py`, `ue4ss_helper.py`, and general prerequisites.

*   `env verify` 
    *   Checks for MSVC 14.3x compilers, `BuildConfiguration.xml`, C++ plugin status, and INI configuration.
*   `env fix-compiler` 
    *   Auto-fixes `BuildConfiguration.xml` to point to a valid MSVC 2022 toolchain.
*   `env install-plugin [--force]` 
    *   Compiles `PalBakerEditorUtils` using `RunUAT.bat` or `UnrealBuildTool.exe` and injects it into the project.
*   `env inject-assets` 
    *   Copies required master materials (e.g., `MI_PalLit_CharacterBodyBase`) into the UE Content folder.
*   `env configure-ue` 
    *   Injects `bUseIoStore=False` and `bRemoteExecution=True` into project INI files.
*   `env ue4ss {install-palworld|install-latest|repair|uninstall}` 
    *   Downloads, unzips, and registers UE4SS binaries in the game's Win64 folder.
*   `env palschema {install|uninstall}` 
    *   Downloads PalSchema, updates `mods.txt` to enable dependencies (`BPModLoaderMod`, etc.), and installs the DLL.

---

### Potential Future Commands (Based on Architecture & Tech Debt Docs)

As you detach the UI, you will likely need commands to manage background processes that Flet currently handles implicitly:

*   `env ue start` / `env ue stop` 
    *   To address the "Unreal Engine Process Locking" tech debt, allowing the CLI to cleanly kill zombied `UnrealEditor.exe` or `UnrealEditor-Cmd.exe` processes without prompting the user.
*   `mod cancel-pipeline` 
    *   Sends the SIGKILL / Taskkill commands securely to kill an active pipeline job.
*   `env clean-ddc` 
    *   To clear the Derived Data Cache (DDC) in Unreal if compilation becomes corrupted.
*   `manager watch <monsterName>` 
    *   A filesystem watcher (like `nodemon`) that listens for saves in Blender or Photoshop and automatically triggers `mod push` -> `mod cook`.