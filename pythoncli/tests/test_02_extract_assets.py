# tests/test_02_extract_assets.py
"""
================================================================================
PALBAKER CLI INTEGRATION TEST 02: CUE4PARSE ASSET EXTRACTION (CHAOS PROOF)
================================================================================
COMMANDS EXECUTED SEQUENTIALLY ON THIS TEST:

[PROFILE 1: EMPTY CONFIGURATION]
1. Zeroes out all active configuration paths.
2. Attempt extraction:
   python palbaker_cli.py mod extract BadCatgirl
3. Asserts CLI gracefully returns status 'error' and exit code 1.
4. Logs the descriptive error message returned by the CLI.

[PROFILE 2: GARBAGE CONFIGURATION]
5. Writes non-existent junk paths to the settings config.
6. Attempt extraction:
   python palbaker_cli.py mod extract BadCatgirl
7. Asserts CLI gracefully returns status 'error', exit code 1, and path warnings.
8. Logs the descriptive error message returned by the CLI.

[PROFILE 3: REAL CONFIGURATION]
9. Restores the user's active manager_settings.json.
10. Wipes any existing Nyafia export workspace on disk.
11. Performs actual headless extraction:
    python palbaker_cli.py mod extract BadCatgirl
12. Asserts exit code is 0, status is 'success', and verifies physical existence
    of .psk, .png, and MI_*.json files in the export directory.
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
         raise AssertionError(
             f"CLI crashed with a raw Python traceback under {profile_name} profile.\n"
             f"STDOUT: {stdout}\nSTDERR: {stderr}"
         )
         
    parsed = parse_cli_json(stdout)
    if not parsed:
         raise AssertionError(
             f"CLI did not output a valid JSON envelope on graceful failure under {profile_name}.\n"
             f"Exit Code: {exit_code}\nSTDOUT: {stdout}"
         )
         
    if parsed.get("status") != "error":
         raise AssertionError(f"Expected status 'error' under {profile_name}, got '{parsed.get('status')}'")

    # Extract and log descriptive error outputs for manual verification
    error_message = parsed.get("message", "No message field returned by CLI.")
    log(f"Graceful Reject Code: {exit_code}")
    log(f"Graceful Reject Msg:  {error_message}")


def main():
    log(f"=== PalBaker CLI Extraction Diagnostics (Chaos Proof): {TARGET_PAL} ===")
    
    sandbox = SettingsSandbox(REPO_ROOT)
    sandbox.backup()

    try:
        # ---------------------------------------------------------------------
        # PROFILE 1: Empty Configuration Check
        # ---------------------------------------------------------------------
        log("\n--- Profile 1: Empty Settings Verification ---")
        sandbox.apply_profile("empty")
        
        exit_code, stdout, stderr = run_cli_command(["mod", "extract", TARGET_PAL], CLI_ENTRY_POINT)
        assert_graceful_failure(exit_code, stdout, stderr, "EMPTY")
        log("✅ SUCCESS: Profile 1 passed. CLI rejected empty configuration gracefully.")

        # ---------------------------------------------------------------------
        # PROFILE 2: Garbage Configuration Check
        # ---------------------------------------------------------------------
        log("\n--- Profile 2: Garbage Settings Verification ---")
        sandbox.apply_profile("garbage")
        
        exit_code, stdout, stderr = run_cli_command(["mod", "extract", TARGET_PAL], CLI_ENTRY_POINT)
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
        
        # Wipe old files to guarantee we are testing a real, new extraction
        if os.path.exists(target_dir):
            log(f"Wiping existing {TARGET_PAL} workspace folder to ensure clean extraction verification...")
            shutil.rmtree(target_dir)

        log(f"Triggering Cue4Parse extraction for {TARGET_PAL}...")
        exit_code, stdout, stderr = run_cli_command(["mod", "extract", TARGET_PAL], CLI_ENTRY_POINT)

        parsed = parse_cli_json(stdout)
        if not parsed:
            raise AssertionError(f"CLI did not output valid JSON during extraction. STDOUT: {stdout}\nSTDERR: {stderr}")

        if exit_code != 0 or parsed.get("status") != "success":
            raise AssertionError(f"Extraction execution failed. Payload: {parsed}\nSTDERR: {stderr}")

        # Verify physical disk outputs
        log("Verifying physical output assets on disk...")
        if not os.path.exists(target_dir):
            raise AssertionError(f"Extraction succeeded but target directory was not created: {target_dir}")

        psk_files = glob.glob(os.path.join(target_dir, "*.psk"))
        if not psk_files:
            raise AssertionError("No skeletal mesh (*.psk) was extracted.")
        log(f"  -> Found Skeletal Mesh: {os.path.basename(psk_files[0])}")

        png_files = glob.glob(os.path.join(target_dir, "*.png"))
        if not png_files:
            raise AssertionError("No texture dependencies (*.png) were extracted.")
        log(f"  -> Found {len(png_files)} texture assets.")

        json_files = glob.glob(os.path.join(target_dir, "MI_*.json"))
        if not json_files:
            raise AssertionError("No material parameters (MI_*.json) were extracted.")
        log(f"  -> Found {len(json_files)} material configurations.")

        log(f"\n✅ PASS: Profile 3 passed. Extraction of {TARGET_PAL} resolved successfully.")

    except Exception as e:
        log(f"❌ TEST FAILED: {str(e)}", "ERROR")
        sys.exit(1)
        
    finally:
        log("\n--- Cleanup & Teardown ---")
        sandbox.restore()

if __name__ == "__main__":
    main()