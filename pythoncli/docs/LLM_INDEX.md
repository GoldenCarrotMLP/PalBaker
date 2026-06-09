# PalBaker Modding Suite: LLM Context & Repository Index

## 📌 Purpose of this Document
This file serves as the definitive structural map and architectural index of the PalBaker repository. It is designed to be ingested by future LLM generations upon session startup to immediately understand the layout, dependencies, and intended workflows of the project without needing to grep through files or read stale documentation.

---

## 🏗️ Architecture Overview
PalBaker is an automated modding environment for Palworld (Unreal Engine 5.1). It features a **Flet** frontend (Python) orchestrating a robust subprocess backend. It bridges **FModel**, **Blender**, **Unreal Engine**, and **UnrealPak** to fully automate the asset extraction, skeleton rigging, model baking, and packaging pipeline.

The repository follows a decoupled architecture separating the GUI layout from the headless automation scripts.

---

## 📂 Project Structure & Key Directories

### 1. Root Orchestrators
* **`manager.py`**: The application entry point. Initializes the Flet UI, loads settings, and mounts the decoupled views (`ModsView`, `CreatorView`, `SettingsView`).
* **`build_mod.py`**: The backend headless orchestrator. Executed via subprocess to prevent blocking the Flet UI. It manages the full compilation pipeline by calling helper modules.

### 2. `views/` (Flet UI Layouts)
Follows a specific "View Wrapper Pattern" to bypass Flet's C++ inheritance issues. Components are instantiated as standard Python classes that store their built Flet control tree in a `self.view` attribute.
* `mods_view.py`: Displays active mods. Uses in-memory component caching to support lag-free, real-time search filtering.
* `creator_view.py`: The UI for creating and setting up new mods (Altermatic/PalSchema inputs).
* `settings_view.py`: Handles executable path configurations (Blender, Unreal Editor, FModel directory).

### 3. `controllers/` (UI State & Business Logic)
Handles the asynchronous backend logic and state mutations for the views.
* `mods/`, `creator/`, `altermatic/`: Separated logic domains.
* `audio_controller.py`: Manages the on-the-fly audio compilation using Wwise and `vgmstream-cli` completely decoupled from Unreal Engine.
* `settings_controller.py`: Detects system configurations and verifies compiler toolchains.

### 4. `utils/` (Core Pipeline Logic)
The heavy lifting of the mod manager. Broken into specific domains:
* **`builder/`**: Submodules imported by `build_mod.py` (`workspace.py`, `config_helper.py`, `blender_helper.py`, `unreal_helper.py`, `cooker_helper.py`).
* **`blender_extractor.py` & `blender_reconstruct.py`**: Scripts meant to run headlessly inside Blender to handle `.psk` parsing and `.fbx` exporting with Unreal-friendly bone properties.
* **`fmodel_helper.py` & `ue4ss_helper.py`**: Handles parsing dumped raw data.
* **`blueprint_patcher.py` & `palschema_helper.py` & `altermatic_helper.py`**: Generates and injects JSON schema configuration for runtime modding.
* **`plugin_manager.py` & `check_compiler_requirements.py`**: MSVC diagnostics and automated C++ plugin injection for the target UE 5.1 project.

### 5. `unreal_scripts/` (Engine Execution)
Python scripts sent to the active Unreal Editor instance via Remote Execution.
* `importer.py`: Headless asset ingestion.
* `materials.py`: Compiles and links Material Instances based on dumped JSON data.
* `rigging.py`: Programmatically generates complex AnimGraph node trees for jiggle bones and physics proxies using the injected `PalBakerEditorUtils` C++ plugin.

### 6. `plugins/PalBakerEditorUtils/`
A custom C++ Unreal module that is automatically compiled into the user's project to expose advanced Blueprint Node instantiation (which the Python API lacks natively).

### 7. `components/`
Modular Flet UI widgets used inside the views (e.g., custom buttons, input fields, mod cards).

---

## 🚀 The Build Pipeline (`build_mod.py`)
When a mod is triggered for execution, the pipeline runs as follows:
1. **Workspace Context:** Resolves local FModel, output, and Unreal paths.
2. **Push (Blender → Unreal):**
   * Headless Blender extracts `.blend` -> `.fbx` (forcing UE scale limits).
   * Unreal Engine Remote Execution evaluates `ue_import.py` (via `unreal_scripts/`).
   * Assets, textures, and generated materials are linked inside the editor.
   * `rigging.py` wires physics and anim blueprints via C++.
3. **Cook (`DefaultGame.ini` injection):**
   * A Python Context Manager safely hijacks `DefaultGame.ini` to restrict the cook directory exclusively to the target mod, massively reducing cook time.
4. **Pack (`UnrealPak`):**
   * Combines cooked assets and staged Wwise `.wem` audio overrides.
   * Filters out skeletons and physics assets automatically to prevent ragdoll glitches.

---

## 🛠️ Modding Paradigm (PalSchema vs. Compiled)
The suite supports dual-tier modding:
1. **Compiled Modding:** Replacing existing character meshes via traditional `_P.pak` file overrides.
2. **Runtime Modding (Altermatic/PalSchema):** Generating `.json` configurations (`DT_PalBPClass`, `Furret.json`, `SpawnGroupList` array overrides) that dynamically inject new, standalone species IDs into spawner blueprints and map them to custom models at runtime.

---

*This index should be referenced whenever a file needs modifying to ensure architectural consistency with Flet constraints and pipeline decoupling.*