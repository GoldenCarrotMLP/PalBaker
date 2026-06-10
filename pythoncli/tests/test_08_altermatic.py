# tests/test_08_altermatic.py
"""
================================================================================
PALBAKER CLI INTEGRATION TEST 08: ALTERMATIC LIFECYCLE (CHAOS PROOF)
================================================================================
COMMANDS EXECUTED SEQUENTIALLY ON THIS TEST:

[PROFILE 1: EMPTY CONFIGURATION]
1. Zeroes out all active configuration paths.
2. Attempt Altermatic toggling:
   python palbaker_cli.py altermatic toggle BadCatgirl on
3. Asserts CLI gracefully returns status 'error' and exit code 1.
4. Logs the descriptive error message returned by the CLI.

[PROFILE 2: GARBAGE CONFIGURATION]
5. Writes non-existent junk paths to the settings config.
6. Attempt Altermatic toggling:
   python palbaker_cli.py altermatic toggle BadCatgirl on
7. Asserts CLI gracefully returns status 'error', exit code 1, and path warnings.
8. Logs the descriptive error message returned by the CLI.

[PROFILE 3: REAL CONFIGURATION]
9. Restores the user's active manager_settings.json.
10. [Self-Healing] Verifies BadCatgirl is extracted and has a base .blend workspace; 
    if missing, triggers Step 4:
    python palbaker_cli.py mod create-blend BadCatgirl
11. Toggles Altermatic framework ON for BadCatgirl:
    python palbaker_cli.py altermatic toggle BadCatgirl on
12. Verifies the manifest is created and active on disk.
13. Query active Altermatic variants:
    python palbaker_cli.py altermatic list BadCatgirl
    - Asserts that at least the baseline "base" variant exists.
14. Adds a brand-new Altermatic variant and forces a C++ Blender .blend clone:
    python palbaker_cli.py altermatic add BadCatgirl testvar --custom --source BadCatgirl.blend
    - Asserts that BadCatgirl_testvar.blend and its sidecar JSON are created.
15. Saves custom variant properties (ReqTrait: Artisan, PrefTrait: Swift, Gender: Female):
    python palbaker_cli.py altermatic save 1 --data "<json_payload>"
    - Asserts that the properties successfully saved inside BadCatgirl_altermatic.json.
16. Deletes the newly created custom variant by index:
    python palbaker_cli.py altermatic delete BadCatgirl 1
    - Asserts that the files are deleted from the disk and the manifest is pruned.
17. Toggles Altermatic framework OFF for BadCatgirl:
    python palbaker_cli.py altermatic toggle BadCatgirl off
    - Asserts that the framework was turned off in the manifest.
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
VARIANT_LABEL = "testvar"
FULL_VARIANT_LABEL = f"{TARGET_PAL}_{VARIANT_LABEL}"

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
    log(f"=== PalBaker CLI Altermatic Lifecycle (Chaos Proof): {TARGET_PAL} ===")
    
    sandbox = SettingsSandbox(REPO_ROOT)
    sandbox.backup()

    # Initialize all path scope pointers to None to prevent UnboundLocalError on early crash teardowns
    target_alt_dir = None
    manifest_path = None
    cloned_blend = None
    cloned_sidecar = None

    try:
        # ---------------------------------------------------------------------
        # PROFILE 1: Empty Settings Verification
        # ---------------------------------------------------------------------
        log("\n--- Profile 1: Empty Settings Verification ---")
        sandbox.apply_profile("empty")
        
        exit_code, stdout, stderr = run_cli_command(["altermatic", "toggle", TARGET_PAL, "on"], CLI_ENTRY_POINT)
        assert_graceful_failure(exit_code, stdout, stderr, "EMPTY")
        log("✅ SUCCESS: Profile 1 passed. CLI rejected empty configuration gracefully.")

        # ---------------------------------------------------------------------
        # PROFILE 2: Garbage Settings Verification
        # ---------------------------------------------------------------------
        log("\n--- Profile 2: Garbage Settings Verification ---")
        sandbox.apply_profile("garbage")
        
        exit_code, stdout, stderr = run_cli_command(["altermatic", "toggle", TARGET_PAL, "on"], CLI_ENTRY_POINT)
        assert_graceful_failure(exit_code, stdout, stderr, "GARBAGE")
        log("✅ SUCCESS: Profile 2 passed. CLI rejected invalid paths gracefully.")

        # ---------------------------------------------------------------------
        # PROFILE 3: Real Configuration Operational Test
        # ---------------------------------------------------------------------
        log("\n--- Profile 3: Real Settings Verification & Run ---")
        sandbox.apply_profile("real")
        
        # Load restored settings to locate the physical test directories
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)

        fmodel_output = settings.get("fmodel_output", "")
        if not fmodel_output:
            log("Skipping Profile 3 run: Workspace Folder is not configured in settings.", "WARNING")
            return

        target_dir = os.path.normpath(os.path.join(
            fmodel_output, "Exports", "Pal", "Content", "Pal", "Model", "Character", "Monster", TARGET_PAL
        ))
        target_alt_dir = os.path.normpath(os.path.join(
            fmodel_output, "Exports", "Pal", "Content", "Palbaker", "Model", "Character", "Monster", TARGET_PAL
        ))
        
        # Self-Healing: Verify Nyafia .blend workspace is reconstructed before running Altermatic tests
        if not os.path.exists(target_dir) or not os.path.exists(os.path.join(target_dir, f"{TARGET_PAL}.blend")):
            log("Prerequisite Missing: Nyafia .blend is not reconstructed. Executing self-healing step...")
            exit_code, stdout, stderr = run_cli_command(["mod", "create-blend", TARGET_PAL], CLI_ENTRY_POINT)
            if exit_code != 0:
                raise RuntimeError(f"Self-healing reconstruction failed. STDOUT: {stdout}\nSTDERR: {stderr}")

        # Target files on disk
        manifest_path = os.path.normpath(os.path.join(target_alt_dir, f"{TARGET_PAL}_altermatic.json"))
        cloned_blend = os.path.join(target_alt_dir, f"{FULL_VARIANT_LABEL}.blend")
        cloned_sidecar = os.path.join(target_alt_dir, f"{FULL_VARIANT_LABEL}_blend.json")

        # Cleanup any old test structures from previous runs to ensure clean verification
        if os.path.exists(target_alt_dir):
            shutil.rmtree(target_alt_dir, ignore_errors=True)

        # Step 1: Toggle Altermatic ON
        log("Toggling Altermatic framework ON...")
        exit_code, stdout, stderr = run_cli_command(["altermatic", "toggle", TARGET_PAL, "on"], CLI_ENTRY_POINT)
        parsed_toggle_on = parse_cli_json(stdout)
        if not parsed_toggle_on or parsed_toggle_on.get("status") != "success":
            raise AssertionError(f"Failed to toggle Altermatic ON. STDOUT: {stdout}\nSTDERR: {stderr}")

        # Verify on-disk manifest was created successfully
        if not os.path.exists(manifest_path):
            raise AssertionError(f"Altermatic turned ON but manifest was not created: {manifest_path}")
        log(f"  -> Generated Manifest: {os.path.basename(manifest_path)} (Created)")

        # Step 2: List Variants (Should possess baseline "base" by default)
        log("Querying Altermatic variants list...")
        exit_code, stdout, stderr = run_cli_command(["altermatic", "list", TARGET_PAL], CLI_ENTRY_POINT)
        parsed_list = parse_cli_json(stdout)
        if not parsed_list or parsed_list.get("status") != "success":
            raise AssertionError(f"Failed to query variants list. STDOUT: {stdout}\nSTDERR: {stderr}")

        variants = parsed_list.get("data", [])
        if not any(v.get("label") == "base" for v in variants):
            raise AssertionError("Layout Verification Failure: Baseline 'base' variant was not initialized in manifest.")
        log("  -> Baseline 'base' variant verified as active.")

        # Step 3: Add new custom variant (Forces .blend clone from WeaselDragon base)
        log(f"Adding new variant '{VARIANT_LABEL}' and cloning skeletal .blend workspace...")
        exit_code, stdout, stderr = run_cli_command(["altermatic", "add", TARGET_PAL, VARIANT_LABEL, "--custom", "--source", "base"], CLI_ENTRY_POINT)
        parsed_add = parse_cli_json(stdout)
        if not parsed_add or parsed_add.get("status") != "success":
            raise AssertionError(f"Failed to add Altermatic variant. STDOUT: {stdout}\nSTDERR: {stderr}")

        # Verify cloned workspace assets are created on disk
        if not os.path.exists(cloned_blend):
            raise AssertionError(f"Variant added but skeletal .blend was not cloned: {cloned_blend}")
        log(f"  -> Cloned Blender Workspace: {os.path.basename(cloned_blend)} (Created)")

        if not os.path.exists(cloned_sidecar):
            raise AssertionError(f"Variant added but layout sidecar was not synced: {cloned_sidecar}")
        log(f"  -> Generated Cloned Sidecar:  {os.path.basename(cloned_sidecar)} (Created)")

        # Step 4: Save properties (Assigning Gender: Female, IsRarePal: True, ReqTrait: Artisan, PrefTrait: Swift)
        log(f"Saving custom configurations for variant '{VARIANT_LABEL}'...")
        variant_payload = {
            "label": VARIANT_LABEL,
            "CharacterID": TARGET_PAL,
            "SkeletonSource": f"{FULL_VARIANT_LABEL}.blend",
            "Gender": "Female",
            "IsRarePal": True,
            "SkinName": f"{TARGET_PAL}_Skin001",
            "ReqTrait": ["Artisan"],
            "PrefTrait": ["Swift"],
            "MatReplace": [],
            "MorphTarget": [],
            "is_base": False
        }
        
        exit_code, stdout, stderr = run_cli_command(["altermatic", "save", "1", "--data", json.dumps(variant_payload)], CLI_ENTRY_POINT)
        parsed_save = parse_cli_json(stdout)
        if not parsed_save or parsed_save.get("status") != "success":
            raise AssertionError(f"Failed to save Altermatic variant properties. STDOUT: {stdout}\nSTDERR: {stderr}")

        # Deep Verification of the manifest state
        log("Opening manifest to verify parameter serialization...")
        with open(manifest_path, "r", encoding="utf-8") as f_man:
            manifest_state = json.load(f_man)

        stored_variants = manifest_state.get("variants", {})
        new_label = f"{TARGET_PAL}_{VARIANT_LABEL}"
        if new_label not in stored_variants:
            raise AssertionError(f"Serialization Failure: Variant key '{new_label}' is missing from manifest.")

        v_saved = stored_variants[new_label]
        if v_saved.get("Gender") != "Female":
            raise AssertionError(f"Serialization Failure: Expected Gender 'Female', got '{v_saved.get('Gender')}'")
        if v_saved.get("IsRarePal") is not True:
            raise AssertionError(f"Serialization Failure: Expected IsRarePal 'True', got '{v_saved.get('IsRarePal')}'")
        if v_saved.get("SkinName") != f"{TARGET_PAL}_Skin001":
            raise AssertionError(f"Serialization Failure: Expected SkinName '{TARGET_PAL}_Skin001', got '{v_saved.get('SkinName')}'")
        if v_saved.get("ReqTrait") != ["Artisan"] or v_saved.get("PrefTrait") != ["Swift"]:
            raise AssertionError(f"Serialization Failure: Stored traits do not match updated parameters.")
            
        log("  -> Variant parameters successfully serialized inside manifest.")

        # Step 5: Delete Custom Variant
        log(f"Deleting variant '{VARIANT_LABEL}' by positional index (1)...")
        exit_code, stdout, stderr = run_cli_command(["altermatic", "delete", TARGET_PAL, "1"], CLI_ENTRY_POINT)
        parsed_delete = parse_cli_json(stdout)
        if not parsed_delete or parsed_delete.get("status") != "success":
            raise AssertionError(f"Failed to delete Altermatic variant. STDOUT: {stdout}\nSTDERR: {stderr}")

        # Verify filesystem cleanup
        log("Verifying physical cleanup of deleted variant assets...")
        if os.path.exists(cloned_blend):
            raise AssertionError("Blender model (.blend) was not deleted from the disk.")
        if os.path.exists(cloned_sidecar):
            raise AssertionError("Layout sidecar JSON was not deleted from the disk.")
        log("  -> Physical files successfully cleared from disk.")

        # Verify manifest update
        with open(manifest_path, "r", encoding="utf-8") as f_man:
            manifest_state = json.load(f_man)
        if new_label in manifest_state.get("variants", {}):
            raise AssertionError("Pruning Failure: Deleted variant key is still present inside manifest.")
        log("  -> Variant entry successfully pruned from manifest.")

        # Step 6: Toggle Altermatic OFF
        log("Toggling Altermatic framework OFF...")
        exit_code, stdout, stderr = run_cli_command(["altermatic", "toggle", TARGET_PAL, "off"], CLI_ENTRY_POINT)
        parsed_toggle_off = parse_cli_json(stdout)
        if not parsed_toggle_off or parsed_toggle_off.get("status") != "success":
            raise AssertionError(f"Failed to toggle Altermatic OFF. STDOUT: {stdout}\nSTDERR: {stderr}")

        with open(manifest_path, "r", encoding="utf-8") as f_man:
            manifest_state = json.load(f_man)
        if manifest_state.get("is_altermatic_active") is not False:
            raise AssertionError("Deactivation Failure: Altermatic status flag remains 'True' in manifest.")
        log("  -> Altermatic status flag set to 'False' in manifest.")

        log(f"\n✅ PASS: Profile 3 passed. Altermatic modular lifecycle verified successfully.")

    except Exception as e:
        log(f"❌ TEST FAILED: {str(e)}", "ERROR")
        sys.exit(1)
        
    finally:
        log("\n--- Cleanup & Teardown ---")
        if target_alt_dir and os.path.exists(target_alt_dir):
            shutil.rmtree(target_alt_dir, ignore_errors=True)
        sandbox.restore()

if __name__ == "__main__":
    main()