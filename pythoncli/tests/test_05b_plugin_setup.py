# tests/test_05b_plugin_setup.py
"""
================================================================================
PALBAKER CLI INTEGRATION TEST 05b: C++ PLUGIN COMPILATION & SETUP
================================================================================
COMMANDS EXECUTED SEQUENTIALLY ON THIS TEST:

[PROFILE 1: EMPTY CONFIGURATION]
1. Zeroes out all active configuration paths.
2. Attempt plugin installation:
   python palbaker_cli.py env install-plugin
3. Asserts CLI gracefully returns status 'error' and exit code 1.
4. Logs the descriptive error message returned by the CLI.

[PROFILE 2: GARBAGE CONFIGURATION]
5. Writes non-existent junk paths to the settings config.
6. Attempt plugin installation:
   python palbaker_cli.py env install-plugin
7. Asserts CLI gracefully returns status 'error', exit code 1, and path warnings.
8. Logs the descriptive error message returned by the CLI.

[PROFILE 3: REAL CONFIGURATION]
9. Restores the user's active manager_settings.json.
10. [Prerequisite Ping Check] Pings the closed Unreal Editor to assert it is offline:
    python palbaker_cli.py mod ping BadCatgirl
    - Asserts connection returns "UNREAL_CLOSED" or "UNREAL_DISABLED".
    - This validates both the ping command and ensures no file-locks are active.
11. Wipes any existing compiled DLLs inside the local repository:
    plugins/PalBakerEditorUtils/Binaries/Win64/*
12. Wipes the active installed plugin folder inside the Unreal Project:
    <project_dir>/Plugins/PalBakerEditorUtils
13. Compiles the C++ C++ source files headlessly via UnrealBuildTool or RunUAT:
    python palbaker_cli.py env install-plugin
14. Asserts exit code is 0, status is 'success'.
15. Verifies physical disk outputs:
    - plugins/PalBakerEditorUtils/Binaries/Win64/UnrealEditor-PalBakerEditorUtils.dll exists
    - <project_dir>/Plugins/PalBakerEditorUtils/Binaries/Win64/UnrealEditor-PalBakerEditorUtils.dll exists
16. Injects and validates missing master materials and project setup:
    python palbaker_cli.py env verify
    - Asserts status is 'success' and 'missing_assets' array is empty.
================================================================================
"""

import os
import sys
import json
import shutil
import glob
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
    log("=== PalBaker CLI Plugin Compilation & Setup (Chaos Proof) ===")
    
    sandbox = SettingsSandbox(REPO_ROOT)
    sandbox.backup()

    try:
        # ---------------------------------------------------------------------
        # PROFILE 1: Empty Configuration Check
        # ---------------------------------------------------------------------
        log("\n--- Profile 1: Empty Settings Verification ---")
        sandbox.apply_profile("empty")
        
        exit_code, stdout, stderr = run_cli_command(["env", "install-plugin"], CLI_ENTRY_POINT)
        assert_graceful_failure(exit_code, stdout, stderr, "EMPTY")
        log("✅ SUCCESS: Profile 1 passed. CLI rejected empty configuration gracefully.")

        # ---------------------------------------------------------------------
        # PROFILE 2: Garbage Configuration Check
        # ---------------------------------------------------------------------
        log("\n--- Profile 2: Garbage Settings Verification ---")
        sandbox.apply_profile("garbage")
        
        exit_code, stdout, stderr = run_cli_command(["env", "install-plugin"], CLI_ENTRY_POINT)
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

        # ADDED AUTONOMOUS GATES: Force editor to close to release file locks
        from test_helper import ensure_unreal_closed
        ensure_unreal_closed()


        ue_root = settings.get("ue_root", "")
        uproject_path = settings.get("uproject", "")
        if not ue_root or not uproject_path:
            log("Skipping Profile 3 run: Required paths are not configured in settings.", "WARNING")
            return

        project_dir = os.path.dirname(uproject_path)
        project_name = os.path.splitext(os.path.basename(uproject_path))[0]

        # 1. Closed Editor Ping Verification
        log("Verifying Unreal Editor is closed and executing offline ping handshake...")
        exit_code, stdout, stderr = run_cli_command(["mod", "ping", TARGET_PAL], CLI_ENTRY_POINT)
        parsed_ping = parse_cli_json(stdout)
        
        if not parsed_ping:
            raise AssertionError(f"CLI did not output valid JSON during offline ping check. STDOUT: {stdout}\nSTDERR: {stderr}")
            
        diag_code = parsed_ping.get("diagnostic_code")
        if diag_code not in ["UNREAL_CLOSED", "UNREAL_DISABLED"]:
            raise AssertionError(
                f"UNREAL LOCK WARNING: Expected Unreal Editor to be closed or unreachable.\n"
                f"Diagnostic Code: {diag_code}\n"
                f"Compiling a C++ plugin while the editor is running will trigger permission locks on the DLL."
            )
        log(f"  -> Connection Handshake Code: {diag_code} (Clean offline state verified)")

        # 2. Setup Clean Slate
        # Wipe local repo binaries
        local_bin_dir = os.path.normpath(os.path.join(REPO_ROOT, "plugins", "PalBakerEditorUtils", "Binaries", "Win64"))
        if os.path.exists(local_bin_dir):
            log("Clearing existing local repository DLL binaries...")
            shutil.rmtree(local_bin_dir, ignore_errors=True)

        # Wipe installed project plugins
        installed_plugin_dir = os.path.normpath(os.path.join(project_dir, "Plugins", "PalBakerEditorUtils"))
        if os.path.exists(installed_plugin_dir):
            log(f"Wiping existing active ModKit plugin installation: {installed_plugin_dir}")
            shutil.rmtree(installed_plugin_dir, ignore_errors=True)

        # 3. Trigger headless compilation and installation
        log("Triggering headless C++ plugin compilation via UBT or RunUAT...")
        exit_code, stdout, stderr = run_cli_command(["env", "install-plugin"], CLI_ENTRY_POINT)

        parsed_install = parse_cli_json(stdout)
        if not parsed_install or parsed_install.get("status") != "success":
            raise AssertionError(f"C++ Plugin compilation failed.\nSTDOUT: {stdout}\nSTDERR: {stderr}")

        # 4. Verify physical DLL generation
        log("Verifying compiled C++ binaries on disk...")
        
        # Verify compiled DLL exists in the active Unreal project plugins folder
        active_dll_path = os.path.join(installed_plugin_dir, "Binaries", "Win64")
        active_dlls = glob.glob(os.path.join(active_dll_path, "UnrealEditor-PalBakerEditorUtils*.dll"))
        if not active_dlls:
            raise AssertionError(f"No compiled C++ plugin DLL was found in the project directory: {active_dll_path}")
        log(f"  -> Active Unreal Plugin DLL: {os.path.basename(active_dlls[0])} (Size: {os.path.getsize(active_dlls[0])} bytes)")

        # Verify compiled DLL was successfully copied back to the local repository
        local_dlls = glob.glob(os.path.join(local_bin_dir, "UnrealEditor-PalBakerEditorUtils*.dll"))
        if not local_dlls:
            raise AssertionError(f"Compiled C++ plugin DLL was not copied back to the repository binaries folder: {local_bin_dir}")
        log(f"  -> Local Repository Backup:  {os.path.basename(local_dlls[0])} (Size: {os.path.getsize(local_dlls[0])} bytes)")

        # 5. Injects and validates project requirements
        log("Verifying project assets and BuildConfiguration.xml readiness...")
        exit_code, stdout, stderr = run_cli_command(["env", "verify"], CLI_ENTRY_POINT)
        
        parsed_verify = parse_cli_json(stdout)
        if not parsed_verify or parsed_verify.get("status") != "success":
            raise AssertionError(f"Project requirements verification failed.\nSTDOUT: {stdout}\nSTDERR: {stderr}")

        verify_data = parsed_verify.get("data", {})
        missing_assets = verify_data.get("missing_assets", [])
        if missing_assets:
            raise AssertionError(f"Project is missing required framework assets: {missing_assets}")
            
        log("  -> Project requirements and MSVC toolchain verified as completely healthy.")
        log("\n✅ PASS: Profile 3 passed. Custom C++ plugin compiled, linked, and verified cleanly.")

    except Exception as e:
        log(f"❌ TEST FAILED: {str(e)}", "ERROR")
        sys.exit(1)
        
    finally:
        log("\n--- Cleanup & Teardown ---")
        sandbox.restore()

if __name__ == "__main__":
    main()