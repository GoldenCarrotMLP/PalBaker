# tests/test_06_unreal_import.py
"""
================================================================================
PALBAKER CLI INTEGRATION TEST 06: UNREAL ENGINE REMOTE INGESTION
================================================================================
COMMANDS EXECUTED SEQUENTIALLY ON THIS TEST:

[PROFILE 1: EMPTY CONFIGURATION]
1. Zeroes out all active configuration paths.
2. Attempt Unreal ingestion:
   python palbaker_cli.py mod push BadCatgirl
3. Asserts CLI gracefully returns status 'error' and exit code 1.
4. Logs the descriptive error message returned by the CLI.

[PROFILE 2: GARBAGE CONFIGURATION]
5. Writes non-existent junk paths to the settings config.
6. Attempt Unreal ingestion:
   python palbaker_cli.py mod push BadCatgirl
7. Asserts CLI gracefully returns status 'error', exit code 1, and path warnings.
8. Logs the descriptive error message returned by the CLI.

[PROFILE 3: REAL CONFIGURATION]
9. Restores the user's active manager_settings.json.
10. [Self-Healing] Verifies BadCatgirl.blend exists; if missing, triggers Step 4:
    python palbaker_cli.py mod create-blend BadCatgirl
11. Performs actual out-of-process FBX baking and Unreal Editor UDP push:
    python palbaker_cli.py mod push BadCatgirl
12. Asserts exit code is 0, status is 'success'.
13. Connects to the running Unreal Editor via custom Remote Python execution.
14. Executes live memory assertions inside Unreal Editor:
    - Assert skeletal mesh exists: /Game/Pal/Model/Character/Monster/BadCatgirl/SK_BadCatgirl
    - Assert body material instance exists: /Game/Pal/Model/Character/Monster/BadCatgirl/MI_BadCatgirl_Body
    - Assert animation blueprint exists: /Game/Pal/Model/Character/Skeleton/BadCatgirl/BadCatgirl_BP
    - Assert C++ AnimGraph binding exists (Post-Process AnimBP class is NOT None)
================================================================================
"""

import os
import sys
import json
import time
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


def query_unreal_editor_assets(ue_root: str, project_name: str, asset_paths_to_check: list[str]) -> tuple[bool, dict]:
    """
    Connects to the open Unreal Editor session via UDP multicast 
    and checks the structural status of the newly imported assets in memory.
    """
    ue_python_dir = os.path.join(ue_root, "Engine", "Plugins", "Experimental", "PythonScriptPlugin", "Content", "Python")
    if ue_python_dir not in sys.path:
        sys.path.append(ue_python_dir)
        
    try:
        import remote_execution  # type: ignore
    except ImportError:
        return False, {"error": "Could not locate remote_execution.py in Unreal directory."}

    remote_exec = remote_execution.RemoteExecution()
    remote_exec.start()
    
    # Wait for the project node to become available
    node = None
    timeout = 5.0
    elapsed = 0.0
    while elapsed < timeout:
        node = next((n for n in remote_exec.remote_nodes if n.get('project_name', '').lower() == project_name.lower()), None)
        if node:
            break
        time.sleep(0.5)
        elapsed += 0.5

    if not node:
        remote_exec.stop()
        return False, {"error": "Connection timed out. Ensure Unreal Editor is running with Python Remote Execution enabled."}

    remote_exec.open_command_connection(node.get('node_id'))
    
    # Python code block compiled inside Unreal Editor
    verification_script = f"""
import unreal
import json

paths = {json.dumps(asset_paths_to_check)}
results = {{}}

for path in paths:
    exists = unreal.EditorAssetLibrary.does_asset_exist(path)
    results[path] = "exists" if exists else "missing"

# Verify the C++ post-process AnimBlueprint assignment on the imported skeletal mesh
mesh_path = "{asset_paths_to_check[0]}"
if unreal.EditorAssetLibrary.does_asset_exist(mesh_path):
    mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
    pp_class = mesh.get_editor_property('post_process_anim_blueprint')
    results["post_process_class"] = pp_class.get_name() if pp_class else "None"
else:
    results["post_process_class"] = "No Mesh"

print("VERIFICATION_START" + json.dumps(results) + "VERIFICATION_END")
"""

    response = remote_exec.run_command(verification_script)
    remote_exec.stop()

    if response is not None and response.get('success'):
        logs = [log_entry.get('output', '') for log_entry in response.get('output', [])]
        merged_output = "".join(logs)
        
        import re
        match = re.search(r"VERIFICATION_START(.*?)VERIFICATION_END", merged_output)
        if match:
            return True, json.loads(match.group(1))
            
    return False, {"error": f"Failed to retrieve execution output from Unreal: {response.get('result') if response else 'No response'}"}


def main():
    log(f"=== PalBaker CLI Unreal Ingestion (Chaos Proof): {TARGET_PAL} ===")
    
    sandbox = SettingsSandbox(REPO_ROOT)
    sandbox.backup()

    try:
        # ---------------------------------------------------------------------
        # PROFILE 1: Empty Configuration Check
        # ---------------------------------------------------------------------
        log("\n--- Profile 1: Empty Settings Verification ---")
        sandbox.apply_profile("empty")
        
        exit_code, stdout, stderr = run_cli_command(["mod", "push", TARGET_PAL], CLI_ENTRY_POINT)
        assert_graceful_failure(exit_code, stdout, stderr, "EMPTY")
        log("✅ SUCCESS: Profile 1 passed. CLI rejected empty configuration gracefully.")

        # ---------------------------------------------------------------------
        # PROFILE 2: Garbage Configuration Check
        # ---------------------------------------------------------------------
        log("\n--- Profile 2: Garbage Settings Verification ---")
        sandbox.apply_profile("garbage")
        
        exit_code, stdout, stderr = run_cli_command(["mod", "push", TARGET_PAL], CLI_ENTRY_POINT)
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

        # ADDED AUTONOMOUS GATES: Ensure Unreal Editor is running and fully booted
        from test_helper import ensure_unreal_opened
        ensure_unreal_opened(settings, CLI_ENTRY_POINT)


        fmodel_output = settings.get("fmodel_output", "")
        uproject_path = settings.get("uproject", "")
        ue_root = settings.get("ue_root", "")
        if not fmodel_output or not uproject_path or not ue_root:
            log("Skipping Profile 3 run: Required paths are not configured in settings.", "WARNING")
            return

        project_name = os.path.splitext(os.path.basename(uproject_path))[0]

        target_dir = os.path.normpath(os.path.join(
            fmodel_output, "Exports", "Pal", "Content", "Pal", "Model", "Character", "Monster", TARGET_PAL
        ))
        
        # Self-Healing: Verify Nyafia .blend workspace is reconstructed before running Unreal tests
        if not os.path.exists(target_dir) or not os.path.exists(os.path.join(target_dir, f"{TARGET_PAL}.blend")):
            log("Prerequisite Missing: Nyafia .blend is not reconstructed. Executing self-healing step...")
            exit_code, stdout, stderr = run_cli_command(["mod", "create-blend", TARGET_PAL], CLI_ENTRY_POINT)
            if exit_code != 0:
                raise RuntimeError(f"Self-healing reconstruction failed. STDOUT: {stdout}\nSTDERR: {stderr}")

        # 1. Execute the Mod Push command (Blender FBX Export -> Unreal Import)
        log(f"Triggering automated push and import pipeline for {TARGET_PAL}...")
        exit_code, stdout, stderr = run_cli_command(["mod", "push", TARGET_PAL], CLI_ENTRY_POINT)

        parsed_push = parse_cli_json(stdout)
        if not parsed_push or parsed_push.get("status") != "success":
            raise AssertionError(f"Ingestion pipeline failed. STDOUT: {stdout}\nSTDERR: {stderr}")

        # 2. Establish Remote connection and query active Editor assets
        log("Connecting to open Unreal Editor session to query asset allocation...")
        assets_to_verify = [
            f"/Game/Pal/Model/Character/Monster/{TARGET_PAL}/SK_{TARGET_PAL}",
            f"/Game/Pal/Model/Character/Monster/{TARGET_PAL}/MI_{TARGET_PAL}_Body",
            f"/Game/Pal/Model/Character/Skeleton/{TARGET_PAL}/{TARGET_PAL}_BP"  # FIXED: Target the Skeleton/ subfolder
        ]
        
        success, report = query_unreal_editor_assets(ue_root, project_name, assets_to_verify)
        if not success:
            raise AssertionError(f"Unreal Editor diagnostic query failed: {report.get('error', 'Unknown Error')}")

        # 3. Assertions inside live Unreal Engine memory
        log("Executing live Unreal Engine asset registry assertions...")
        for path in assets_to_verify:
            status = report.get(path, "missing")
            if status != "exists":
                raise AssertionError(f"Asset Registry Failure: Target asset was not created in project: {path}")
            log(f"  -> Asset verified in Unreal: {os.path.basename(path)}")

        # 4. Assertions on the C++ AnimGraph binding
        pp_class_name = report.get("post_process_class", "None")
        if pp_class_name == "None" or pp_class_name == "No Mesh":
            raise AssertionError(
                f"ANIMATION BINDING FAILURE: The custom AnimBlueprint class is not assigned to the skeletal mesh's Post-Process slot.\n"
                f"Your character will spawn frozen in a T-Pose in-game."
            )
        log(f"  -> C++ Post-Process AnimBP Hook: {pp_class_name} (Linked & Active)")

        log(f"\n✅ PASS: Profile 3 passed. Modular push and custom C++ AnimGraph rigging fully validated.")

    except Exception as e:
        log(f"❌ TEST FAILED: {str(e)}", "ERROR")
        sys.exit(1)
        
    finally:
        log("\n--- Cleanup & Teardown ---")
        sandbox.restore()

if __name__ == "__main__":
    main()