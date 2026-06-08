Here is a clear, technically precise description of your program suite designed for another LLM to parse and understand immediately. It outlines your tech stack, system architecture, file dependencies, and execution pipelines.

***

### 📋 Palworld Modding Suite: Technical Overview for LLM Context

This workspace contains two distinct, integrated tools designed to modify, customize, and extend **Palworld (Unreal Engine 5.1)** character parameters, assets, and overworld spawning systems. The suite operates at both the compiled binary level (`.uasset`/`_P.pak`) and the runtime modding level (**PalSchema** and **Altermatic**).

---

### 1. Palworld Randomizer & Spawn Editor (C# / .NET 8 / WPF)
A desktop GUI application that reads, parses, mutates, and writes game databases and spawner blueprints.

* **Tech Stack:** C#, WPF, .NET 8, `UAssetAPI` (VER_UE5_1 target), `CUE4Parse` (Unreal archive parsing).
* **Core Mechanisms:**
  * **Ingestion:** Uses `CUE4Parse` to read game `.pak` archives, locate, and extract `DT_PalMonsterParameter`, `DT_PalNameText_Common`, caged Pal tables, and compiled spawner sheets (`BP_PalSpawner_Sheets_*.uasset`).
  * **Binary Deserialization:** Leverages `UAssetAPI` to unpack the raw byte data of serialized Blueprints and DataTables, parsing active `SpawnGroupList` array structures.
  * **Mutation & Serialization:** Allows the user to randomize or manually edit spawn tables, group weights, and level parameters. Writes the mutated data back to standard UE 5.1 `.uasset`/`.uexp` binary structures.
  * **Compilation/Export Pipelines:** 
    1. **PAK Compiler:** Generates a file-mapping response manifest and headlessly executes `UnrealPak.exe` to compile a compressed `_P.pak` patch.
    2. **PalSchema Exporter:** Serializes the modified spawner and caged Pal arrays directly into zipped PalSchema JSON configuration structures (`blueprints/PalSpawns.json`, `raw/Cages.json`) [4].

---

### 2. PalBaker Mod Builder (Python / Flet / C++)
An asynchronous pipeline orchestrator that automates the reverse-engineering and cooking workflow from raw FModel dumps to custom 3D in-game models.

* **Tech Stack:** Python 3.10+, Flet (UI), C++ (Unreal Editor Plugin), MSVC Toolchain.
* **Architecture:** Decoupled, single-responsibility modular structure.
* **Pipelines:**
  * **Headless Blender Pipeline (`utils/extractor/`):** Runs Blender headlessly to reconstruct `.blend` projects from `.psk` skeletal meshes, extract skeletal transformations, walk material shader trees, and export FBX targets with forced bone scaling, rotation, and hierarchy parameters.
  * **Unreal Engine Remote Execution (`unreal_scripts/`):** Establishes a remote socket connection to the active Unreal Editor. It headlessly imports meshes/textures, compiles child material instances, and links them to the skeletal mesh.
  * **Dynamic C++ AnimGraph Compilation:** Inject and headlessly compiles `PalBakerEditorUtils` (a custom C++ module) to programmatically build complex `AnimGraph` node trees (spring physics, bone offsets) inside newly generated Animation Blueprints.
  * **Micro-Cooking & Packaging:** Restricts `DefaultGame.ini` cooking directories to the target mod on the fly. Packs loose cooked assets into `_P.pak` files using `UnrealPak`, stripping redundant skeleton assets to prevent ragdoll glitches.
  * **Altermatic Compilation:** Deploys runtime mesh-swap configurations (`palbaker-{monster}.json` inside `Paks/~Mods/SwapJSON/`) mapping standalone IDs to skeletal meshes.

---

### 3. PalSchema & Altermatic Runtime Integration
The runtime modding layer used by the mod manager to inject standalone custom species (e.g., `MOD_Furret`) without binary compilation.

* **DataTable Injection (`raw/`):**
  * `DT_PalBPClass.json`: Maps the custom species ID (`MOD_Furret`) to a valid logic class (e.g., `BP_WeaselDragon_C`).
  * `DT_PalCharacterIconDataTable.json` & `DT_PalDropItem.json`: Generates required frontend UI icons and drop tables to prevent spawner-logic culling.
* **Character Parameters (`pals/`):**
  * `Furret.json`: Clones the parent's base properties (movement speed, scale, viewing distance) into `DT_PalMonsterParameter` to ensure the Pal has physical form. Overrides `"BPClass"` to `MOD_Furret` to enforce correct class lookup [4].
* **Blueprint Spawner Patching (`blueprints/`):**
  * Overwrites the compiled `SpawnGroupList` array property inside the spawner blueprint sheets directly (e.g., `BP_PalSpawner_Sheets_1_1_plain_begginer_C`) [6] to inject the custom Pal ID at runtime.
* **Altermatic Mesh-Swapping:**
  * Intercepts the spawned entity's Character ID at runtime and swaps the parent's mesh with the custom skeletal mesh (`SK_furret`).