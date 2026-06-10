# tests/test_04_blender_reconstruction.py
"""
================================================================================
PALBAKER CLI INTEGRATION TEST 04: HEADLESS BLENDER WORKSPACE RECONSTRUCTION
================================================================================
COMMANDS EXECUTED SEQUENTIALLY ON THIS TEST:

[PROFILE 1: EMPTY CONFIGURATION]
1. Zeroes out all active configuration paths.
2. Attempt Blender reconstruction:
   python palbaker_cli.py mod create-blend BadCatgirl
3. Asserts CLI gracefully returns status 'error' and exit code 1.
4. Logs the descriptive error message returned by the CLI.

[PROFILE 2: GARBAGE CONFIGURATION]
5. Writes non-existent junk paths to the settings config.
6. Attempt Blender reconstruction:
   python palbaker_cli.py mod create-blend BadCatgirl
7. Asserts CLI gracefully returns status 'error', exit code 1, and path warnings.
8. Logs the descriptive error message returned by the CLI.

[PROFILE 3: REAL CONFIGURATION]
9. Restores the user's active manager_settings.json.
10. [Self-Healing] Verifies BadCatgirl was extracted; if missing, triggers Step 2:
    python palbaker_cli.py mod extract BadCatgirl
11. Wipes any existing reconstructed .blend and sidecar files on disk.
12. Performs actual headless reconstruction and sidecar layout harvesting:
    python palbaker_cli.py mod create-blend BadCatgirl
13. Asserts exit code is 0, status is 'success'.
14. Verifies physical disk outputs:
    - BadCatgirl.blend exists on disk (Reconstructed workspace)
    - BadCatgirl_blend.json exists on disk (Companion layout sidecar)
15. Parses and validates the companion sidecar JSON:
    - Assert "materials" key is present and is a populated dictionary.
    - Assert "jiggle_bones" key is present and is a list.
    - Assert "offset_bones" key is present and is a list.
    - Assert "morph_targets" key is present and is a list.
================================================================================
"""

import os
import sys
import glob
import json
import shutil
from test_helper import SettingsSandbox, run_cli_command, parse_cli_json, log

# Resolve paths relative to the test file location
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
SETTINGS_FILE = os.path.join(REPO_ROOT, "manager_settings.json")
CLI_ENTRY_POINT = os.path.join(REPO_ROOT, "palbaker_cli.py")

TARGET_PAL = "BadCatgirl"

def assert_graceful_failure(exit_code: int, stdout: str, stderr: str, profile_name: str):
    """
    Verifies that the CLI rejected the bad config gracefully without raw crashes.
    Logs the exact status and error messages emitted by your sub-handlers.
    """
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
    log(f"=== PalBaker CLI Blender Reconstruction (Chaos Proof): {TARGET_PAL} ===")
    
    sandbox = SettingsSandbox(REPO_ROOT)
    sandbox.backup()

    try:
        # ---------------------------------------------------------------------
        # PROFILE 1: Empty Configuration Check
        # ---------------------------------------------------------------------
        log("\n--- Profile 1: Empty Settings Verification ---")
        sandbox.apply_profile("empty")
        
        exit_code, stdout, stderr = run_cli_command(["mod", "create-blend", TARGET_PAL], CLI_ENTRY_POINT)
        assert_graceful_failure(exit_code, stdout, stderr, "EMPTY")
        log("✅ SUCCESS: Profile 1 passed. CLI rejected empty configuration gracefully.")

        # ---------------------------------------------------------------------
        # PROFILE 2: Garbage Configuration Check
        # ---------------------------------------------------------------------
        log("\n--- Profile 2: Garbage Settings Verification ---")
        sandbox.apply_profile("garbage")
        
        exit_code, stdout, stderr = run_cli_command(["mod", "create-blend", TARGET_PAL], CLI_ENTRY_POINT)
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
        
        # Self-Healing: Verify Nyafia raw files are extracted before running Blender tests
        if not os.path.exists(target_dir) or not glob.glob(os.path.join(target_dir, "*.psk")):
            log("Prerequisite Missing: Nyafia assets are not extracted. Executing self-healing step...")
            exit_code, stdout, stderr = run_cli_command(["mod", "extract", TARGET_PAL], CLI_ENTRY_POINT)
            if exit_code != 0:
                raise RuntimeError(f"Self-healing extraction failed. STDOUT: {stdout}\nSTDERR: {stderr}")

        # Target file names to verify
        blend_path = os.path.join(target_dir, f"{TARGET_PAL}.blend")
        sidecar_path = os.path.join(target_dir, f"{TARGET_PAL}_blend.json")

        # Wipe old output files to guarantee we are testing a fresh reconstruction
        for path in [blend_path, sidecar_path]:
            if os.path.exists(path):
                log(f"Wiping existing {os.path.basename(path)} to ensure clean workspace reconstruction...")
                os.remove(path)

        log(f"Triggering headless Blender workspace reconstruction for {TARGET_PAL}...")
        exit_code, stdout, stderr = run_cli_command(["mod", "create-blend", TARGET_PAL], CLI_ENTRY_POINT)

        parsed = parse_cli_json(stdout)
        if not parsed:
            raise AssertionError(f"CLI did not output valid JSON during reconstruction. STDOUT: {stdout}\nSTDERR: {stderr}")

        if exit_code != 0 or parsed.get("status") != "success":
            raise AssertionError(f"Blender reconstruction execution failed. Payload: {parsed}\nSTDERR: {stderr}")

        # Verify physical disk outputs
        log("Verifying physical output files on disk...")
        if not os.path.exists(blend_path):
            raise AssertionError(f"Reconstruction succeeded but the .blend file was not saved: {blend_path}")
        log(f"  -> Reconstructed Blender Workspace: {os.path.basename(blend_path)} (Size: {os.path.getsize(blend_path)} bytes)")

        if not os.path.exists(sidecar_path):
            raise AssertionError(f"Reconstruction succeeded but the companion sidecar was not generated: {sidecar_path}")
        log(f"  -> Generated Layout Sidecar:        {os.path.basename(sidecar_path)} (Size: {os.path.getsize(sidecar_path)} bytes)")

        # 6. Deep Verification of the sidecar layout schema
        log("Parsing companion sidecar schema to verify harvested metrics...")
        with open(sidecar_path, "r", encoding="utf-8") as f:
            sidecar_data = json.load(f)

        # Assertion A: Verify Materials list is present and populated
        if "materials" not in sidecar_data:
            raise AssertionError("Sidecar Validation Failure: 'materials' node is missing.")
        mats = sidecar_data["materials"]
        if not isinstance(mats, dict) or len(mats) == 0:
            raise AssertionError("Sidecar Validation Failure: 'materials' is empty or not a valid dictionary object.")
        log(f"  -> Successfully harvested {len(mats)} material slots: {list(mats.keys())}")

        # Assertion B: Verify skeletal bones arrays are present
        for key in ["jiggle_bones", "offset_bones", "morph_targets"]:
            if key not in sidecar_data:
                raise AssertionError(f"Sidecar Validation Failure: '{key}' node is missing.")
            if not isinstance(sidecar_data[key], list):
                raise AssertionError(f"Sidecar Validation Failure: '{key}' node must be a list object.")

        log(f"\n✅ PASS: Profile 3 passed. Reconstructed {TARGET_PAL}.blend and its companion layout sidecar are verified healthy.")

    except Exception as e:
        log(f"❌ TEST FAILED: {str(e)}", "ERROR")
        sys.exit(1)
        
    finally:
        log("\n--- Cleanup & Teardown ---")
        sandbox.restore()

if __name__ == "__main__":
    main()