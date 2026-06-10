# PalBaker Test Suite & Automation Grounds

This directory contains the automated testing environment for the **PalBaker CLI**. Rather than utilizing heavy testing frameworks which can obscure execution outputs and stdout logs, this suite is built as a series of **atomic, standalone, and sequential Python scripts**. 

Each script is designed to be fully runnable in isolation for targeted debugging and tweaking, while a master orchestrator (`run_all_tests.py`) runs the entire suite from end to end.

---

## 🏗️ Test Suite Architecture

```text
tests/
├── README.md                      # This file
├── fixtures/                      # Statically staged test resources
│   ├── test_audio.mp3             # Minimal silent audio for Wwise testing
│   ├── test_icon.png              # Test PNG for icon replacement tests
│   └── mock_schemas/
│       └── custom_pal_payload.json# Raw JSON used for standalone Pal Creator tests
│
├── test_01_preflight.py             # Checks environment, paths, and binary states
├── test_02_extract_assets.py        # Extracts BadCatgirl (Nyafia) raw files
├── test_03_blueprint_mutation.py    # Tests UAssetGUI blueprint serialization & regex rules
├── test_04_blender_reconstruction.py # Tests headless Blender reconstruction
├── test_05_audio_compilation.py     # Tests vgmstream decoding & Wwise encoding
├── test_06_unreal_import.py         # Tests remote execution and asset loading
├── test_07_unreal_decompile.py      # Verifies the lossless "round-trip" decompiler
├── test_08_cook_and_pack.py         # Tests targeted cooking and skeleton-stripped packaging
└── run_all_tests.py                 # The Master End-to-End Orchestrator
```

---

## 📋 Implementation Progress Checklist

Use this checklist to monitor the construction of your modular test suite.

### Core Automation & Environment
- [ ] Staged audio, icon, and JSON schemas in `tests/fixtures/`
- [ ] Implemented the Master Orchestrator (`run_all_tests.py`) with stdout capturing and exit code monitoring

### Subsystem Standalone Tests
- [ ] **`test_01_preflight.py`** — Environment Path & Connection Verification
- [ ] **`test_02_extract_assets.py`** — Game Archive Asset Dumping via Cue4Parse
- [ ] **`test_03_blueprint_mutation.py`** — UAssetGUI Serialization & Lookbehind Regex Patches
- [ ] **`test_04_blender_reconstruction.py`** — Headless Blender FBX to `.blend` Conversion
- [ ] **`test_05_audio_compilation.py`** — `vgmstream-cli` & `WwiseConsole` Compilation
- [ ] **`test_06_unreal_import.py`** — Unreal Engine Remote Execution Ingestion
- [ ] **`test_07_unreal_decompile.py`** — Round-trip Lossless Re-export & Overwrite
- [ ] **`test_08_cook_and_pack.py`** — Micro-cooking and Safe Skeleton-stripped Packing

---

## 🛠️ Standalone Test Breakdown & Design Specs

### `test_01_preflight.py` (The Environment Gatekeeper)
* **Goal:** Verify that all paths, dependencies, and connections are valid before running long pipelines.
* **Execution:**
  1. Load `manager_settings.json` from the root directory [build_mod.py].
  2. Verify that all target paths (`fmodel_output`, `ue_root`, `uproject`, `blender`, `palworld_exe`) exist on disk [views/settings_view.py].
  3. Execute `python palbaker_cli.py mod ping BadCatgirl` to assert connection to a running Unreal Editor instance with Python Remote Execution enabled [palbaker_cli.py].
  4. Verify that `cue4parse.exe` and `Mappings.usmap` exist in the `deps/` directory [utils/extractor/core.py].
* **Asserts:** All filesystem paths are reachable, and the active Unreal connection returns `"FULLY_CONNECTED"`.

### `test_02_extract_assets.py` (Cue4Parse Ingestion)
* **Goal:** Verify that the extractor correctly dumps raw game files.
* **Execution:**
  1. Invoke the CLI: `python palbaker_cli.py mod extract BadCatgirl` [palbaker_cli.py].
  2. Check the FModel output path for newly created Nyafia folders [utils/scanner.py].
* **Asserts:**
  * Exit code is `0`.
  * The PSK skeletal mesh exists in the destination folder [build_mod.py].
  * Texture `.png` dependencies (body, eye, etc.) exist on disk [build_mod.py].

### `test_03_blueprint_mutation.py` (Blueprint Patching)
* **Goal:** Verify UAssetGUI serialization and protect against animation blueprint corruption.
* **The "BP_BadCatgirlTest" Mutation Rule:**
  * Extract the parent `BP_BadCatgirl.uasset` and convert it to JSON [blueprint_patcher.py].
  * Programmatically search and mutate the JSON strings, changing `BP_BadCatgirl` to `BP_BadCatgirlTest` [blueprint_patcher.py].
  * **Strict AnimBP Preservation constraint:** Assert that `ABP_BadCatgirl` (the Animation Blueprint) [blueprint_patcher.py] was **not** altered to `ABP_BadCatgirlTest` [blueprint_patcher.py].
  * Recompile the JSON to `.uasset` using UAssetGUI [blueprint_patcher.py].
* **Asserts:**
  * UAssetGUI compiled successfully [blueprint_patcher.py].
  * The modified `.uasset` maintains structural binary integrity.
  * Animation class references remain bound to the vanilla parent skeleton.

### `test_04_blender_reconstruction.py` (Headless Blender Workspace)
* **Goal:** Verify headless reconstruction of `.blend` and companion sidecar JSON layouts.
* **Execution:**
  1. Invoke the CLI: `python palbaker_cli.py mod create-blend BadCatgirl` [palbaker_cli.py].
  2. Assert that `BadCatgirl.blend` and `BadCatgirl_blend.json` have been written to the FModel directory [build_mod.py].
* **Asserts:**
  * Sidecar JSON file is created [build_mod.py].
  * JSON parses correctly and contains the `materials` dictionary [manager-test.py, ue_import.py].
  * Verified bone transform layouts are populated under the `offset_bones` block [utils/blender_extractor.py].

### `test_05_audio_compilation.py` (Wwise Pipeline)
* **Goal:** Verify custom MP3/OGG decoding and on-the-fly Wwise `.wem` compilation.
* **Execution:**
  1. Copy the mock `test_audio.mp3` file to a temporary location.
  2. Invoke the CLI: `python palbaker_cli.py audio set BadCatgirl Joy <temp_path>` [palbaker_cli.py].
  3. Verify `vgmstream-cli` successfully outputs a clean `.wav` [utils/audio_helper.py].
  4. Verify `WwiseConsole.exe` successfully compiles the `.wav` into a `.wem` file [utils/audio_helper.py].
  5. Delete the custom override via the CLI and verify files are removed [palbaker_cli.py].
* **Asserts:**
  * Staged `.wem` file matches Nyafia's exact Wwise `media_id` (e.g., `191233074.wem`) [utils/audio_helper.py].
  * Override clean-up deletes both the source audio and the compiled `.wem` [utils/audio_helper.py].

### `test_06_unreal_import.py` (Unreal Engine Import)
* **Goal:** Verify Remote Execution mesh and material instantiation in Unreal Editor.
* **Execution:**
  1. Invoke the CLI: `python palbaker_cli.py mod push BadCatgirl` [palbaker_cli.py].
  2. Run a custom Remote Python script to scan active editor assets [utils/builder/unreal_helper.py].
* **Asserts:**
  * `/Game/Pal/Model/Character/Monster/BadCatgirl/SK_BadCatgirl` exists in editor memory [unreal_scripts/materials.py].
  * Generated material instances (MIs) are created and assigned to the correct skeletal slots [unreal_scripts/materials.py].
  * Post-process animation slot is bound to Nyafia's new AnimBP [unreal_scripts/rigging.py].

### `test_07_unreal_decompile.py` (Lossless Round-Trip Verification)
* **Goal:** Verify that decompiling compiled Unreal assets back to source `.blend` files is 100% lossless.
* **Execution:**
  1. Forcefully delete `BadCatgirl.blend` from the local workspace folder [build_mod.py].
  2. Invoke the CLI: `python palbaker_cli.py mod decompile BadCatgirl --overwrite` [palbaker_cli.py].
  3. Check that `BadCatgirl.blend` has been reconstructed on disk [build_mod.py].
* **Asserts:**
  * New `.blend` file exists [build_mod.py].
  * Reconstructed `materials_metadata.json` matches original topological data harvested in Step 4 [ue_export.py].
  * Structural bone scales and local parent transforms are unchanged.

### `test_08_cook_and_pack.py` (Cook & Pack Strip Filter)
* **Goal:** Verify targeted cooking and the safe skeleton-stripping rules of the packer.
* **Execution:**
  1. Modify `DefaultGame.ini` via context managers to target only the `BadCatgirl` folder [utils/builder/config_helper.py].
  2. Invoke the CLI: `python palbaker_cli.py mod cook BadCatgirl` and `python palbaker_cli.py mod pack BadCatgirl` [palbaker_cli.py].
  3. Unpack the compiled `BadCatgirl_P.pak` into a temporary directory [utils/builder/cooker_helper.py].
* **Asserts:**
  * The `.pak` contains only the cooked Nyafia files [utils/builder/cooker_helper.py].
  * **The Ragdoll Check:** Verify that `SK_BadCatgirl_Skeleton.uasset` is **not** present in the pak, ensuring the safe packaging filter successfully stripped it out to prevent ragdoll glitches [docs/architecture.md].

---

## 🏎️ Orchestrator Design (`run_all_tests.py`)

`run_all_tests.py` acts as the master automation supervisor. It runs each test script sequentially in a clean subprocess session.

### Execution Rules
1. **Self-Healing Chain:** Each step requires the success of the previous step. If `test_03_blueprint_mutation.py` fails, the orchestrator immediately halts execution, aborts downstream steps, and preserves the workspace state for manual inspection.
2. **Standard Output Capturing:** The orchestrator intercepts all log stdout streams from child tests. It formats output logs and prints detailed troubleshooting information only in the event of an active failure.
3. **Pristine State Restoration:** If all tests complete successfully, the orchestrator executes a cleanup routing to wipe out generated `BadCatgirlTest` and temporary build files [build_mod.py], restoring your workspace to its exact original state.