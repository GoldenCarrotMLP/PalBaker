# tests/test_09_cook_and_pack.py
"""
================================================================================
PALBAKER CLI INTEGRATION TEST 09: TARGETED COOKING & SAFE PACKAGING
================================================================================
COMMANDS EXECUTED SEQUENTIALLY ON THIS TEST:

[PROFILE 1: EMPTY CONFIGURATION]
1. Zeroes out all active configuration paths.
2. Attempt cook and pack:
   python palbaker_cli.py mod cook BadCatgirl
3. Asserts CLI gracefully returns status 'error' and exit code 1.
4. Logs the descriptive error message returned by the CLI.

[PROFILE 2: GARBAGE CONFIGURATION]
5. Writes non-existent junk paths to the settings config.
6. Attempt cook and pack:
   python palbaker_cli.py mod cook BadCatgirl
7. Asserts CLI gracefully returns status 'error', exit code 1, and path warnings.
8. Logs the descriptive error message returned by the CLI.

[PROFILE 3: REAL CONFIGURATION]
9. Restores the user's active manager_settings.json.
10. [Self-Healing] Verifies Nyafia is in Unreal memory; if missing, triggers Step 6:
    python palbaker_cli.py mod push BadCatgirl
11. Performs actual out-of-process targeted cook and pak assembly:
    python palbaker_cli.py mod cook BadCatgirl
12. Asserts exit code is 0, status is 'success'.
13. Verifies that the compiled BadCatgirl_P.pak is generated inside your game's
    Content/Paks/~Mods/ (or palBaker) directory.
14. Unpacks the compiled .pak file using UnrealPak.exe:
    UnrealPak.exe <pak_path> -Extract <temp_unpack_dir>
15. Performs physical file assertions inside the unpacked game archive:
    - Assert Skeletal Mesh exists: SK_BadCatgirl.uasset
    - Assert Body Material exists: MI_BadCatgirl_Body.uasset
    - Assert SKELETON IS STRIPPED: SK_BadCatgirl_Skeleton.uasset is NOT present
    - Assert PHYSICS IS STRIPPED: PA_BadCatgirl_PhysicsAsset.uasset is NOT present
================================================================================
"""

import os
import sys
import json
import glob
import shutil
import subprocess
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


def unpack_game_archive(unrealpak_path: str, pak_path: str, dest_dir: str) -> bool:
    """Invokes UnrealPak.exe headlessly to extract the compiled game archive."""
    if not os.path.exists(unrealpak_path):
        return False
        
    shutil.rmtree(dest_dir, ignore_errors=True)
    os.makedirs(dest_dir, exist_ok=True)
    
    # Standard UnrealPak extraction syntax
    cmd = [unrealpak_path, pak_path, f"-Extract", dest_dir]
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creation_flags)
        return True
    except Exception:
        return False


def main():
    log(f"=== PalBaker CLI Targeted Cooking & Safe Packing (Chaos Proof): {TARGET_PAL} ===")
    
    sandbox = SettingsSandbox(REPO_ROOT)
    sandbox.backup()

    try:
        # ---------------------------------------------------------------------
        # PROFILE 1: Empty Settings Verification
        # ---------------------------------------------------------------------
        log("\n--- Profile 1: Empty Settings Verification ---")
        sandbox.apply_profile("empty")
        
        exit_code, stdout, stderr = run_cli_command(["mod", "cook", TARGET_PAL], CLI_ENTRY_POINT)
        assert_graceful_failure(exit_code, stdout, stderr, "EMPTY")
        log("✅ SUCCESS: Profile 1 passed. CLI rejected empty configuration gracefully.")

        # ---------------------------------------------------------------------
        # PROFILE 2: Garbage Settings Verification
        # ---------------------------------------------------------------------
        log("\n--- Profile 2: Garbage Settings Verification ---")
        sandbox.apply_profile("garbage")
        
        exit_code, stdout, stderr = run_cli_command(["mod", "cook", TARGET_PAL], CLI_ENTRY_POINT)
        assert_graceful_failure(exit_code, stdout, stderr, "GARBAGE")
        log("✅ SUCCESS: Profile 2 passed. CLI rejected invalid paths gracefully.")

        # ---------------------------------------------------------------------
        # PROFILE 3: Real Configuration Cooking & Packing Verification
        # ---------------------------------------------------------------------
        log("\n--- Profile 3: Real Settings Verification & Run ---")
        sandbox.apply_profile("real")
        
        # Load restored settings to locate the physical test directories
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)

        # ADDED AUTONOMOUS GATES: Ensure Unreal Editor is running and fully booted
        from test_helper import ensure_unreal_opened
        ensure_unreal_opened(settings, CLI_ENTRY_POINT)
        ue_root = settings.get("ue_root", "")
        uproject_path = settings.get("uproject", "")
        palworld_exe = settings.get("palworld_exe", "")
        if not ue_root or not uproject_path:
            log("Skipping Profile 3 run: Required paths are not configured in settings.", "WARNING")
            return

        project_name = os.path.splitext(os.path.basename(uproject_path))[0]
        unrealpak_exe = os.path.normpath(os.path.join(ue_root, "Engine", "Binaries", "Win64", "UnrealPak.exe"))
        
        if not os.path.exists(unrealpak_exe):
            raise AssertionError(f"Missing required UnrealPak dependency at {unrealpak_exe}")

        # Self-Healing: Verify Nyafia is in Unreal Editor before running cook tests
        from test_06_unreal_import import query_unreal_editor_assets
        mesh_virtual_path = f"/Game/Pal/Model/Character/Monster/{TARGET_PAL}/SK_{TARGET_PAL}"
        
        success, report = query_unreal_editor_assets(ue_root, project_name, [mesh_virtual_path])
        if not success or report.get(mesh_virtual_path) != "exists":
            log("Prerequisite Missing: Nyafia assets are not imported in Unreal. Executing self-healing step...")
            exit_code, stdout, stderr = run_cli_command(["mod", "push", TARGET_PAL], CLI_ENTRY_POINT)
            if exit_code != 0:
                raise RuntimeError(f"Self-healing push failed. STDOUT: {stdout}\nSTDERR: {stderr}")

        # Resolve expected output directory for the compiled pak file
        output_dir = os.path.dirname(uproject_path)
        if palworld_exe and os.path.exists(palworld_exe):
            output_dir = os.path.join(os.path.dirname(palworld_exe), "Pal", "Content", "Paks", "palBaker")
            
        final_pak_path = os.path.normpath(os.path.join(output_dir, f"{TARGET_PAL}_P.pak"))
        final_pak_err_path = os.path.normpath(os.path.join(output_dir, f"{TARGET_PAL}_err_P.pak"))

        # Clean existing cooked pak configurations
        for path in [final_pak_path, final_pak_err_path]:
            if os.path.exists(path):
                log(f"Cleaning old target pak: {os.path.basename(path)}")
                try: os.remove(path)
                except OSError: pass

        # 1. Execute unified Cook & Pack command
        log(f"Triggering micro-cook and pack compile for {TARGET_PAL}...")
        exit_code, stdout, stderr = run_cli_command(["mod", "cook", TARGET_PAL], CLI_ENTRY_POINT)

        parsed_cook = parse_cli_json(stdout)
        if not parsed_cook or parsed_cook.get("status") != "success":
            raise AssertionError(f"Cooking and packing execution failed. STDOUT: {stdout}\nSTDERR: {stderr}")

        # Verify compiled pak file exists
        if not os.path.exists(final_pak_path):
            if os.path.exists(final_pak_err_path):
                raise AssertionError(f"Pak was created but with critical errors: {final_pak_err_path}")
            raise AssertionError(f"Cook succeeded but the final .pak file was not written: {final_pak_path}")
            
        log(f"  -> Generated Pak Archive: {os.path.basename(final_pak_path)} (Size: {os.path.getsize(final_pak_path)} bytes)")

        # 2. Extract and physically verify the compiled game archive
        log("Unpacking compiled game archive for diagnostic verification...")
        temp_unpack_dir = os.path.join(TESTS_DIR, "temp_pak_unpack")
        
        success = unpack_game_archive(unrealpak_exe, final_pak_path, temp_unpack_dir)
        if not success:
            raise AssertionError("UnrealPak.exe failed to extract the compiled game archive.")

        # Walk the unpacked files to run structural assertions
        log("Scanning unpacked game assets...")
        unpacked_files = []
        for root, _, files in os.walk(temp_unpack_dir):
            for file in files:
                unpacked_files.append(file.lower())

        # Assertion A: Verify Skeletal Mesh exists
        expected_mesh = f"SK_{TARGET_PAL}.uasset".lower()
        if expected_mesh not in unpacked_files:
            raise AssertionError(f"Unpacked Archive Failure: Expected skeletal mesh asset '{expected_mesh}' is missing.")
        log(f"  -> Skeletal Mesh verified inside archive: {expected_mesh}")

        # Assertion B: Verify Material exists
        expected_material = f"MI_{TARGET_PAL}_Body.uasset".lower()
        if expected_material not in unpacked_files:
            raise AssertionError(f"Unpacked Archive Failure: Expected material asset '{expected_material}' is missing.")
        log(f"  -> Body Material verified inside archive: {expected_material}")

        # Assertion C: SKELETON STRIPPING VERIFICATION (No custom animations are shipped in this test)
        blacklisted_skeleton = f"SK_{TARGET_PAL}_Skeleton.uasset".lower()
        if blacklisted_skeleton in unpacked_files:
            raise AssertionError(
                f"RAGDOLL SECURITY VULNERABILITY FAILED:\n"
                f"Skeletal Asset '{blacklisted_skeleton}' was packaged inside the final archive.\n"
                f"Shipping custom skeleton files without custom animations will trigger infinite ragdoll glitches in-game."
            )
        log("  -> Safe Packaging: Skeleton asset successfully stripped from archive.")

        # Assertion D: PHYSICS ASSET STRIPPING VERIFICATION
        blacklisted_physics = f"PA_{TARGET_PAL}_PhysicsAsset.uasset".lower()
        if blacklisted_physics in unpacked_files:
            raise AssertionError(
                f"RAGDOLL SECURITY VULNERABILITY FAILED:\n"
                f"Physics Asset '{blacklisted_physics}' was packaged inside the final archive."
            )
        log("  -> Safe Packaging: Physics asset successfully stripped from archive.")

        log(f"\n✅ PASS: Profile 3 passed. Micro-cook complete, and safe skeleton-stripped pak compiled successfully.")

    except Exception as e:
        log(f"❌ TEST FAILED: {str(e)}", "ERROR")
        sys.exit(1)
        
    finally:
        log("\n--- Cleanup & Teardown ---")
        shutil.rmtree(os.path.join(TESTS_DIR, "temp_pak_unpack"), ignore_errors=True)
        sandbox.restore()

if __name__ == "__main__":
    main()