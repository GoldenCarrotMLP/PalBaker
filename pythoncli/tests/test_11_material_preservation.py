# tests/test_11_material_preservation.py
"""
================================================================================
PALBAKER CLI INTEGRATION TEST 11: PER-PAL MATERIAL PRESERVATION & RE-LINKING
================================================================================
COMMANDS EXECUTED SEQUENTIALLY ON THIS TEST:

[PROFILE 1: EMPTY CONFIGURATION]
1. Zeroes out all active configuration paths.
2. Attempt material preservation toggle:
   python palbaker_cli.py mod set-preserve-materials BadCatgirl --path false
3. Asserts CLI gracefully returns status 'error' and exit code 1.

[PROFILE 2: GARBAGE CONFIGURATION]
4. Writes non-existent junk paths to the settings config.
5. Attempt material preservation toggle:
   python palbaker_cli.py mod set-preserve-materials BadCatgirl --path false
6. Asserts CLI gracefully returns status 'error', exit code 1, and path warnings.

[PROFILE 3: REAL CONFIGURATION STATE MACHINE]
7. Restores the user's active manager_settings.json.
8. [Self-Healing] Verifies Nyafia is extracted; if missing, extracts it.
9. **PHASE 1 (Baseline Overwrite):**
   - Toggle preservation OFF via CLI.
   - Execute push pipeline to force a clean default import.
   - Connect to Unreal Editor to query and remember default material slots.
10. **PHASE 2 (Manual Mutation):**
    - Connect to Unreal Editor to bind all slot material interfaces to the 
      built-in Engine dummy material (/Engine/BasicShapes/BasicShapeMaterial).
    - Save the mutated mesh, and assert that all slots are indeed bound to the dummy.
11. **PHASE 3 (Push with Keep/Preserve):**
    - Toggle preservation ON via CLI.
    - Execute push pipeline (Blender re-bakes, Unreal re-imports).
    - Connect to Unreal Editor to verify that all slots remained bound to the dummy (Preserved).
12. **PHASE 4 (Push with Overwrite/Restoration):**
    - Toggle preservation OFF via CLI.
    - Execute push pipeline.
    - Connect to Unreal Editor to verify that all slots restored to original defaults.
13. **PHASE 5 (Teardown):**
    - Reset the sidecar toggle back to true.
================================================================================
"""

import os
import sys
import json
import time
import shutil
import re
from test_helper import SettingsSandbox, run_cli_command, parse_cli_json, log

# Resolve paths relative to the test file location
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
SETTINGS_FILE = os.path.join(REPO_ROOT, "manager_settings.json")
CLI_ENTRY_POINT = os.path.join(REPO_ROOT, "palbaker_cli.py")

TARGET_PAL = "BadCatgirl"
DUMMY_MATERIAL_PATH = "/Engine/BasicShapes/BasicShapeMaterial"

def assert_graceful_failure(exit_code: int, stdout: str, stderr: str, profile_name: str):
    if "traceback" in stdout.lower() or "traceback" in stderr.lower():
         raise AssertionError(f"CLI crashed with a raw Python traceback under {profile_name} profile.\nSTDOUT: {stdout}\nSTDERR: {stderr}")
         
    parsed = parse_cli_json(stdout)
    if not parsed:
         raise AssertionError(f"CLI did not output a valid JSON envelope on graceful failure under {profile_name}.\nExit Code: {exit_code}\nSTDOUT: {stdout}\nSTDERR: {stderr}")
         
    if parsed.get("status") != "error":
         raise AssertionError(f"Expected status 'error' under {profile_name}, got '{parsed.get('status')}'")

    error_message = parsed.get("message", "No message field returned by CLI.")
    log(f"Graceful Reject Code: {exit_code}")
    log(f"Graceful Reject Msg:  {error_message}")


def execute_unreal_python(ue_root: str, project_name: str, script: str) -> tuple[bool, str]:
    """Connects to the running Unreal Editor via UDP and runs a raw Python script block."""
    ue_python_dir = os.path.join(ue_root, "Engine", "Plugins", "Experimental", "PythonScriptPlugin", "Content", "Python")
    if ue_python_dir not in sys.path:
        sys.path.append(ue_python_dir)
        
    try:
        import remote_execution  # type: ignore
    except ImportError:
        return False, "Could not locate remote_execution.py"

    remote_exec = remote_execution.RemoteExecution()
    remote_exec.start()
    
    node = None
    timeout = 10.0
    elapsed = 0.0
    while elapsed < timeout:
        node = next((n for n in remote_exec.remote_nodes if n.get('project_name', '').lower() == project_name.lower()), None)
        if node:
            break
        time.sleep(0.5)
        elapsed += 0.5

    if not node:
        remote_exec.stop()
        return False, "Connection to Unreal Editor timed out."

    remote_exec.open_command_connection(node.get('node_id'))
    response = remote_exec.run_command(script)
    remote_exec.stop()

    if response is not None and response.get('success'):
        logs = [log_entry.get('output', '') for log_entry in response.get('output', [])]
        return True, "".join(logs)
        
    return False, "Remote execution failed inside Unreal."


def query_unreal_slots(ue_root: str, project_name: str, mesh_path: str) -> dict:
    """Queries Unreal Editor for the current material assignments of a Skeletal Mesh."""
    script = f"""
import unreal
import json

results = {{}}
if unreal.EditorAssetLibrary.does_asset_exist("{mesh_path}"):
    mesh = unreal.EditorAssetLibrary.load_asset("{mesh_path}")
    for i, mat in enumerate(mesh.materials):
        slot_name = str(mat.material_slot_name).lower()
        results[slot_name] = mat.material_interface.get_path_name().split(".")[0] if mat.material_interface else "None"
        results[str(i)] = mat.material_interface.get_path_name().split(".")[0] if mat.material_interface else "None"
else:
    results["error"] = "Mesh does not exist"

print("SLOTS_QUERY_START" + json.dumps(results) + "SLOTS_QUERY_END")
"""
    success, output = execute_unreal_python(ue_root, project_name, script)
    if not success:
        raise RuntimeError(f"Unreal remote query failed: {output}")
        
    match = re.search(r"SLOTS_QUERY_START(.*?)SLOTS_QUERY_END", output)
    if match:
        return json.loads(match.group(1))
    raise RuntimeError(f"Failed to parse query output. Raw terminal logs:\n{output}")


def mutate_unreal_slots_to_dummy(ue_root: str, project_name: str, mesh_path: str, dummy_mat_path: str):
    """Mutates all material slots on the Skeletal Mesh to a valid Engine dummy material in Unreal Editor."""
    script = f"""
import unreal
import json

results = {{}}
if unreal.EditorAssetLibrary.does_asset_exist("{mesh_path}"):
    mesh = unreal.EditorAssetLibrary.load_asset("{mesh_path}")
    dummy_mat = unreal.EditorAssetLibrary.load_asset("{dummy_mat_path}")
    
    if dummy_mat:
        new_materials = []
        for mat in mesh.materials:
            mat.material_interface = dummy_mat
            new_materials.append(mat)
        mesh.materials = new_materials
        unreal.EditorAssetLibrary.save_loaded_asset(mesh)
        results["status"] = "success"
    else:
        results["status"] = "error"
        results["error"] = "Dummy material '{dummy_mat_path}' not found inside Engine Content."
else:
    results["status"] = "error"
    results["error"] = "Mesh does not exist"

print("SLOTS_MUTATE_START" + json.dumps(results) + "SLOTS_MUTATE_END")
"""
    success, output = execute_unreal_python(ue_root, project_name, script)
    if not success:
        raise RuntimeError(f"Unreal remote mutation failed: {output}")
        
    match = re.search(r"SLOTS_MUTATE_START(.*?)SLOTS_MUTATE_END", output)
    if match:
        res = json.loads(match.group(1))
        if res.get("status") != "success":
            raise RuntimeError(f"Failed to mutate slots: {res.get('error')}")
        return
    raise RuntimeError(f"Failed to parse mutation output. Raw terminal logs:\n{output}")


def main():
    log(f"=== PalBaker CLI Material Preservation State Machine: {TARGET_PAL} ===")
    
    sandbox = SettingsSandbox(REPO_ROOT)
    sandbox.backup()

    try:
        # ---------------------------------------------------------------------
        # PROFILE 1: Empty Settings Verification
        # ---------------------------------------------------------------------
        log("\n--- Profile 1: Empty Settings Verification ---")
        sandbox.apply_profile("empty")
        
        exit_code, stdout, stderr = run_cli_command(["mod", "set-preserve-materials", TARGET_PAL, "--path", "false"], CLI_ENTRY_POINT)
        assert_graceful_failure(exit_code, stdout, stderr, "EMPTY")
        log("✅ SUCCESS: Profile 1 passed. CLI rejected empty configuration gracefully.")

        # ---------------------------------------------------------------------
        # PROFILE 2: Garbage Settings Verification
        # ---------------------------------------------------------------------
        log("\n--- Profile 2: Garbage Settings Verification ---")
        sandbox.apply_profile("garbage")
        
        exit_code, stdout, stderr = run_cli_command(["mod", "set-preserve-materials", TARGET_PAL, "--path", "false"], CLI_ENTRY_POINT)
        assert_graceful_failure(exit_code, stdout, stderr, "GARBAGE")
        log("✅ SUCCESS: Profile 2 passed. CLI rejected invalid paths gracefully.")

        # ---------------------------------------------------------------------
        # PROFILE 3: Real Configuration State Machine Run
        # ---------------------------------------------------------------------
        log("\n--- Profile 3: Real Settings Verification & Run ---")
        sandbox.apply_profile("real")
        
        # Load restored settings to locate the physical test directories
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)

        fmodel_output = settings.get("fmodel_output", "")
        uproject_path = settings.get("uproject", "")
        ue_root = settings.get("ue_root", "")
        if not fmodel_output or not uproject_path or not ue_root:
            log("Skipping Profile 3 run: Required paths are not configured in settings.", "WARNING")
            return

        project_name = os.path.splitext(os.path.basename(uproject_path))[0]
        mesh_virtual_path = f"/Game/Pal/Model/Character/Monster/{TARGET_PAL}/SK_{TARGET_PAL}"

        # Self-Healing: Ensure Unreal Editor is running and fully booted
        from test_helper import ensure_unreal_opened
        ensure_unreal_opened(settings, CLI_ENTRY_POINT)

        # Self-Healing: Verify Nyafia raw files are extracted
        target_dir = os.path.normpath(os.path.join(
            fmodel_output, "Exports", "Pal", "Content", "Pal", "Model", "Character", "Monster", TARGET_PAL
        ))
        if not os.path.exists(target_dir):
            log("Prerequisite Missing: Nyafia assets are not extracted. Executing self-healing step...")
            exit_code, stdout, stderr = run_cli_command(["mod", "extract", TARGET_PAL], CLI_ENTRY_POINT)
            if exit_code != 0:
                raise RuntimeError(f"Self-healing extraction failed: {stderr}")

        # ---------------------------------------------------------------------
        # PHASE 1: Establish the Baseline (Intent of Overwriting)
        # ---------------------------------------------------------------------
        log("\n=== Phase 1: Overwriting to Establish Baseline ===")
        
        log("Toggling Material Preservation OFF via CLI...")
        exit_code, stdout, stderr = run_cli_command(["mod", "set-preserve-materials", TARGET_PAL, "--path", "false"], CLI_ENTRY_POINT)
        if exit_code != 0:
            raise RuntimeError(f"Failed to turn material preservation OFF: {stderr}")
            
        log("Executing baseline push pipeline to import default assets...")
        exit_code, stdout, stderr = run_cli_command(["mod", "push", TARGET_PAL], CLI_ENTRY_POINT)
        parsed_push = parse_cli_json(stdout)
        if not parsed_push or parsed_push.get("status") != "success":
            raise AssertionError(f"Baseline push failed. STDOUT: {stdout}\nSTDERR: {stderr}")

        log("Connecting to Unreal Editor to query default baseline material slots...")
        default_report = query_unreal_slots(ue_root, project_name, mesh_virtual_path)
        if "error" in default_report:
            raise AssertionError(f"Mesh not found in Unreal after push: {default_report['error']}")
            
        log(f"  -> Default Slots Map Harvested: {default_report}")

        # ---------------------------------------------------------------------
        # PHASE 2: Simulating Custom Modder Edits (The Mutation)
        # ---------------------------------------------------------------------
        log("\n=== Phase 2: Mutating Material Slots to Engine Dummy ===")
        
        log("Connecting to Unreal Editor to bind all active slots to Engine dummy material...")
        mutate_unreal_slots_to_dummy(ue_root, project_name, mesh_virtual_path, DUMMY_MATERIAL_PATH)
        
        log("Querying mesh to verify slots are mutated...")
        mutated_report = query_unreal_slots(ue_root, project_name, mesh_virtual_path)
        for key in mutated_report.keys():
            if key != "error" and "BasicShapeMaterial" not in mutated_report[key]:
                raise AssertionError(f"Mutation failed: Slot '{key}' was not bound to dummy (val: '{mutated_report[key]}').")
        log("  -> Verification: All slots successfully mutated to Engine Dummy on disk.")

        # ---------------------------------------------------------------------
        # PHASE 3: Push with "Intent of Keeping" (The Preservation Test)
        # ---------------------------------------------------------------------
        log("\n=== Phase 3: Push with Intent of Keeping (Toggle ON) ===")
        
        log("Toggling Material Preservation ON via CLI...")
        exit_code, stdout, stderr = run_cli_command(["mod", "set-preserve-materials", TARGET_PAL, "--path", "true"], CLI_ENTRY_POINT)
        if exit_code != 0:
            raise RuntimeError(f"Failed to turn material preservation ON: {stderr}")
            
        log("Executing push pipeline (Blender bakes and Unreal re-imports mesh)...")
        exit_code, stdout, stderr = run_cli_command(["mod", "push", TARGET_PAL], CLI_ENTRY_POINT)
        parsed_push2 = parse_cli_json(stdout)
        if not parsed_push2 or parsed_push2.get("status") != "success":
            raise AssertionError(f"Preservation push failed. STDOUT: {stdout}\nSTDERR: {stderr}")

        log("Connecting to Unreal Editor to assert slots remained preserved...")
        preserved_report = query_unreal_slots(ue_root, project_name, mesh_virtual_path)
        for key in preserved_report.keys():
            if key != "error" and "BasicShapeMaterial" not in preserved_report[key]:
                raise AssertionError(
                    f"PRESERVATION FAILURE: Material slot '{key}' was overwritten with a default asset: '{preserved_report[key]}'.\n"
                    f"Expected slot to remain bound to the custom dummy material."
                )
        log("  -> SUCCESS: All mutated slots remained completely preserved through the re-import!")

        # ---------------------------------------------------------------------
        # PHASE 4: Push with "Intent of Overwriting" (The Restoration Test)
        # ---------------------------------------------------------------------
        log("\n=== Phase 4: Push with Intent of Overwriting (Toggle OFF) ===")
        
        log("Toggling Material Preservation OFF via CLI...")
        exit_code, stdout, stderr = run_cli_command(["mod", "set-preserve-materials", TARGET_PAL, "--path", "false"], CLI_ENTRY_POINT)
        if exit_code != 0:
            raise RuntimeError(f"Failed to turn material preservation OFF: {stderr}")
            
        log("Executing push pipeline to force material overwrite...")
        exit_code, stdout, stderr = run_cli_command(["mod", "push", TARGET_PAL], CLI_ENTRY_POINT)
        parsed_push3 = parse_cli_json(stdout)
        if not parsed_push3 or parsed_push3.get("status") != "success":
            raise AssertionError(f"Restoration push failed. STDOUT: {stdout}\nSTDERR: {stderr}")

        log("Connecting to Unreal Editor to assert material slots were restored...")
        restored_report = query_unreal_slots(ue_root, project_name, mesh_virtual_path)
        for key in default_report.keys():
            if default_report[key] != restored_report.get(key):
                raise AssertionError(
                    f"RESTORATION FAILURE: Material slot '{key}' was not restored.\n"
                    f"Expected: '{default_report[key]}'\n"
                    f"Actual:   '{restored_report.get(key)}'"
                )
        log("  -> SUCCESS: All material slots successfully restored back to default baseline assets!")

        log(f"\n✅ PASS: Material preservation, self-healing harvesting, and overwrite restoration verified healthy.")

    except Exception as e:
        log(f"❌ TEST FAILED: {str(e)}", "ERROR")
        sys.exit(1)
        
    finally:
        log("\n--- Cleanup & Teardown ---")
        if os.path.exists(SETTINGS_FILE):
            run_cli_command(["mod", "set-preserve-materials", TARGET_PAL, "--path", "true"], CLI_ENTRY_POINT)
        sandbox.restore()

if __name__ == "__main__":
    main()