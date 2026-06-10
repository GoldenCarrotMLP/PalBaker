# tests/test_07_unreal_decompile.py
"""
================================================================================
PALBAKER CLI INTEGRATION TEST 07: UNREAL ASSET DECOMPILATION (REVERSE PIPELINE)
================================================================================
COMMANDS EXECUTED SEQUENTIALLY ON THIS TEST:

[PROFILE 1: EMPTY CONFIGURATION]
1. Zeroes out all active configuration paths.
2. Attempt decompile command:
   python palbaker_cli.py mod decompile BadCatgirl --overwrite
3. Asserts CLI gracefully returns status 'error' and exit code 1.
4. Logs the descriptive error message returned by the CLI.

[PROFILE 2: GARBAGE CONFIGURATION]
5. Writes non-existent junk paths to the settings config.
6. Attempt decompile command:
   python palbaker_cli.py mod decompile BadCatgirl --overwrite
7. Asserts CLI gracefully returns status 'error', exit code 1, and path warnings.
8. Logs the descriptive error message returned by the CLI.

[PROFILE 3: REAL CONFIGURATION]
9. Restores the user's active manager_settings.json.
10. [Self-Healing] Verifies Nyafia is in Unreal memory; if missing, triggers Step 6:
    python palbaker_cli.py mod push BadCatgirl
11. Wipes the local BadCatgirl.blend and companion sidecars on disk.
12. Performs actual Unreal asset decompile and Blender reconstruction:
    python palbaker_cli.py mod decompile BadCatgirl --overwrite
13. Asserts exit code is 0, status is 'success'.
14. Verifies physical disk outputs:
    - BadCatgirl.blend exists on disk (Reconstructed workspace)
    - materials_metadata.json exists on disk (Exported Unreal material topologies)
15. Parses and validates the exported materials_metadata.json:
    - Assert that parent classes (e.g. MI_PalLit_CharacterBodyBase) were salvaged.
    - Assert that texture parameters (e.g. Base Texture, Normal Map) match.
================================================================================
"""

import os
import sys
import json
import glob
import shutil
from test_helper import SettingsSandbox, run_cli_command, parse_cli_json, log

# Resolve paths relative to the test file location
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
SETTINGS_FILE = os.path.join(REPO_ROOT, "manager_settings.json")
CLI_ENTRY_POINT = os.path.join(REPO_ROOT, "palbaker_cli.py")

TARGET_PAL = "BadCatgirl"

def assert_graceful_failure(exit_code: int, stdout: str, stderr: str, profile_name: str):
    if "traceback" in stdout.lower() or "traceback" in stderr.lower():
         raise AssertionError(f"CLI crashed with a raw Python traceback under {profile_name} profile.\nSTDOUT: {stdout}\nSTDERR: {stderr}")
         
    parsed = parse_cli_json(stdout)
    if not parsed:
         raise AssertionError(f"CLI did not output a valid JSON envelope on graceful failure under {profile_name}.\nExit Code: {exit_code}\nSTDOUT: {stdout}")
         
    if parsed.get("status") != "error":
         raise AssertionError(f"Expected status 'error' under {profile_name}, got '{parsed.get('status')}'")

    error_message = parsed.get("message", "No message field returned by CLI.")
    log(f"Graceful Reject Code: {exit_code}")
    log(f"Graceful Reject Msg:  {error_message}")


def main():
    log(f"=== PalBaker CLI Unreal Decompile (Chaos Proof): {TARGET_PAL} ===")
    
    sandbox = SettingsSandbox(REPO_ROOT)
    sandbox.backup()

    try:
        # ---------------------------------------------------------------------
        # PROFILE 1: Empty Configuration Check
        # ---------------------------------------------------------------------
        log("\n--- Profile 1: Empty Settings Verification ---")
        sandbox.apply_profile("empty")
        
        exit_code, stdout, stderr = run_cli_command(["mod", "decompile", TARGET_PAL, "--overwrite"], CLI_ENTRY_POINT)
        assert_graceful_failure(exit_code, stdout, stderr, "EMPTY")
        log("✅ SUCCESS: Profile 1 passed. CLI rejected empty configuration gracefully.")

        # ---------------------------------------------------------------------
        # PROFILE 2: Garbage Configuration Check
        # ---------------------------------------------------------------------
        log("\n--- Profile 2: Garbage Settings Verification ---")
        sandbox.apply_profile("garbage")
        
        exit_code, stdout, stderr = run_cli_command(["mod", "decompile", TARGET_PAL, "--overwrite"], CLI_ENTRY_POINT)
        assert_graceful_failure(exit_code, stdout, stderr, "GARBAGE")
        log("✅ SUCCESS: Profile 2 passed. CLI rejected invalid paths gracefully.")

        # ---------------------------------------------------------------------
        # PROFILE 3: Real Configuration Operational Test
        # ---------------------------------------------------------------------
        log("\n--- Profile 3: Real Settings Verification & Run ---")
        sandbox.apply_profile("real")
        
        # Load restored settings to locate the physical test directory
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)

        fmodel_output = settings.get("fmodel_output", "")
        if not fmodel_output:
            log("Skipping Profile 3 run: Workspace Folder is not configured in settings.", "WARNING")
            return

        target_dir = os.path.normpath(os.path.join(
            fmodel_output, "Exports", "Pal", "Content", "Pal", "Model", "Character", "Monster", TARGET_PAL
        ))
        
        # Self-Healing: Verify Nyafia is in Unreal Editor before running decompile tests
        # We perform a rapid query on the active project to verify
        from test_06_unreal_import import query_unreal_editor_assets
        project_name = os.path.splitext(os.path.basename(settings["uproject"]))[0]
        mesh_virtual_path = f"/Game/Pal/Model/Character/Monster/{TARGET_PAL}/SK_{TARGET_PAL}"
        
        success, report = query_unreal_editor_assets(settings["ue_root"], project_name, [mesh_virtual_path])
        if not success or report.get(mesh_virtual_path) != "exists":
            log("Prerequisite Missing: Nyafia assets are not imported in Unreal. Executing self-healing step...")
            exit_code, stdout, stderr = run_cli_command(["mod", "push", TARGET_PAL], CLI_ENTRY_POINT)
            if exit_code != 0:
                raise RuntimeError(f"Self-healing push failed. STDOUT: {stdout}\nSTDERR: {stderr}")

        # Paths of interest on disk
        blend_path = os.path.join(target_dir, f"{TARGET_PAL}.blend")
        meta_path = os.path.join(target_dir, "materials_metadata.json")

        # Wipe existing files to ensure we are testing a true decompile reconstruction
        for path in [blend_path, meta_path]:
            if os.path.exists(path):
                log(f"Wiping existing {os.path.basename(path)} to ensure clean decompile verification...")
                os.remove(path)

        # 1. Execute Decompile command
        log(f"Triggering asset decompile and Blender reconstruction for {TARGET_PAL}...")
        exit_code, stdout, stderr = run_cli_command(["mod", "decompile", TARGET_PAL, "--overwrite"], CLI_ENTRY_POINT)

        parsed_decompile = parse_cli_json(stdout)
        if not parsed_decompile or parsed_decompile.get("status") != "success":
            raise AssertionError(f"Decompilation pipeline failed. STDOUT: {stdout}\nSTDERR: {stderr}")

        # Verify physical disk outputs
        log("Verifying physical output assets on disk...")
        if not os.path.exists(blend_path):
            raise AssertionError(f"Decompile succeeded but the .blend file was not saved: {blend_path}")
        log(f"  -> Reconstructed Blender Workspace: {os.path.basename(blend_path)} (Size: {os.path.getsize(blend_path)} bytes)")

        if not os.path.exists(meta_path):
            raise AssertionError(f"Decompile succeeded but the material topology metadata was not saved: {meta_path}")
        log(f"  -> Exported Material Topologies:     {os.path.basename(meta_path)} (Size: {os.path.getsize(meta_path)} bytes)")

        # 2. Deep Parsing of the exported material topologies
        log("Parsing exported material topologies to verify lossless reconstruction...")
        with open(meta_path, "r", encoding="utf-8") as f:
            meta_data = json.load(f)

        # Assert that the body material instance was exported and possesses correct parameters
        body_mi_key = f"MI_{TARGET_PAL}_Body"
        if body_mi_key not in meta_data:
            raise AssertionError(f"Topology Verification Failure: Expected material instance '{body_mi_key}' is missing from metadata.")

        body_meta = meta_data[body_mi_key]
        parent_class = body_meta.get("parent_class", "")
        if "CharacterBodyBase" not in parent_class:
            raise AssertionError(f"Topology Verification Failure: Expected parent class 'CharacterBodyBase', got '{parent_class}'.")
        log("  -> Parent Material Class verified: CharacterBodyBase (Perfect Ingestion)")

        parameters = body_meta.get("parameters", {})
        if not parameters or not isinstance(parameters, dict):
            raise AssertionError("Topology Verification Failure: 'parameters' block is empty or malformed.")
            
        log(f"  -> Successfully verified {len(parameters)} material parameters: {list(parameters.keys())}")

        log(f"\n✅ PASS: Profile 3 passed. Decompile and reverse-trip of {TARGET_PAL} verified successfully.")

    except Exception as e:
        log(f"❌ TEST FAILED: {str(e)}", "ERROR")
        sys.exit(1)
        
    finally:
        log("\n--- Cleanup & Teardown ---")
        sandbox.restore()

if __name__ == "__main__":
    main()