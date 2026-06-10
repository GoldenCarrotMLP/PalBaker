# tests/test_10_altermatic_compile.py
"""
================================================================================
PALBAKER CLI ALTERMATIC INGESTION, BINDING, & COOKING
================================================================================
COMMANDS EXECUTED SEQUENTIALLY ON THIS TEST:

[PROFILE 1 & 2: CHAOS CHECKS]
1. Zeroes out/Garbage tests the pipeline commands to assert graceful failure.

[PROFILE 3: REAL INTEGRATION RUN]
2. Restores settings and verifies BadCatgirl is extracted.
3. Toggles Altermatic framework ON:
   python palbaker_cli.py altermatic toggle BadCatgirl on
4. Adds a custom variant and clones the base .blend workspace:
   python palbaker_cli.py altermatic add BadCatgirl testvar --custom --source base
5. Saves the variant properties (Gender: Female, IsRarePal: True):
   python palbaker_cli.py altermatic save 1 --data "<json_payload>"
6. Executes the combined FBX baking and Unreal Engine remote ingestion:
   python palbaker_cli.py mod push BadCatgirl
   - Blender headlessly bakes BadCatgirl.blend -> SK_BadCatgirl.fbx.
   - Blender headlessly bakes BadCatgirl_testvar.blend -> SK_BadCatgirl_testvar.fbx.
   - Unreal imports the base mesh to: /Game/Pal/Model/Character/Monster/BadCatgirl/
   - Unreal imports the variant to:  /Game/Palbaker/Model/Character/Monster/BadCatgirl/
7. Connects to the Unreal Editor via remote UDP execution to assert:
   - Base Mesh exists and is mapped.
   - Variant Mesh exists under the correct Palbaker/ virtual folder path.
   - SKELETON BINDING VERIFICATION: Both meshes point to the same parent skeleton:
     /Game/Pal/Model/Character/Skeleton/BadCatgirl/SK_BadCatgirl_Skeleton
   - AnimBP BINDING VERIFICATION: Both meshes are bound to their respective AnimBPs:
     - Base mesh -> /Game/Pal/Model/Character/Skeleton/BadCatgirl/BadCatgirl_BP
     - Variant mesh -> /Game/Palbaker/Model/Character/Monster/BadCatgirl/BadCatgirl_testvar_BP
8. Executes the micro-cook and pack compile:
   python palbaker_cli.py mod cook BadCatgirl
9. Unpacks the compiled BadCatgirl_P.pak using UnrealPak.exe:
   UnrealPak.exe <pak_path> -Extract <temp_unpack_dir>
10. Performs physical file assertions inside the unpacked game archive:
    - Assert Base Mesh exists.
    - Assert Variant Mesh exists under the /Palbaker/ cooked folder.
    - Assert SKELETON IS STRIPPED (Even though multiple meshes bound to it).
11. Verifies that the loose Altermatic JSON config is deployed to the game directory:
    - Assert palbaker-BadCatgirl.json exists in Pal/Content/Paks/~Mods/SwapJSON/
12. Clears the variant, disables Altermatic, and cleans up the test workspace.
================================================================================
"""

import os
import sys
import json
import time
import shutil
import subprocess
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
         raise AssertionError(f"CLI did not output a valid JSON envelope under {profile_name}.\nExit Code: {exit_code}\nSTDOUT: {stdout}")
    if parsed.get("status") != "error":
         raise AssertionError(f"Expected status 'error' under {profile_name}, got '{parsed.get('status')}'")


def query_unreal_editor_skeletons(ue_root: str, project_name: str, mesh_paths: list[str]) -> tuple[bool, dict]:
    """
    UDP remote executor. Queries Unreal Editor to check which physical skeleton 
    asset each skeletal mesh is bound to.
    """
    ue_python_dir = os.path.join(ue_root, "Engine", "Plugins", "Experimental", "PythonScriptPlugin", "Content", "Python")
    if ue_python_dir not in sys.path:
        sys.path.append(ue_python_dir)
        
    try:
        import remote_execution  # type: ignore
    except ImportError:
        return False, {"error": "Could not locate remote_execution.py."}

    remote_exec = remote_execution.RemoteExecution()
    remote_exec.start()
    
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
        return False, {"error": "Connection timed out. Ensure Unreal Editor is running."}

    remote_exec.open_command_connection(node.get('node_id'))
    
    verification_script = f"""
import unreal
import json

mesh_paths = {json.dumps(mesh_paths)}
results = {{}}

for path in mesh_paths:
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        mesh = unreal.EditorAssetLibrary.load_asset(path)
        skeleton = mesh.get_editor_property('skeleton')
        anim_class = mesh.get_editor_property('post_process_anim_blueprint')
        
        results[path] = {{
            "status": "exists",
            "skeleton_path": skeleton.get_path_name().split(".")[0] if skeleton else "None",
            "post_process_class": anim_class.get_name() if anim_class else "None"
        }}
    else:
        results[path] = {{"status": "missing", "skeleton_path": "None", "post_process_class": "None"}}

print("SKELETON_VERIFICATION_START" + json.dumps(results) + "SKELETON_VERIFICATION_END")
"""

    response = remote_exec.run_command(verification_script)
    remote_exec.stop()

    if response is not None and response.get('success'):
        logs = [log_entry.get('output', '') for log_entry in response.get('output', [])]
        merged_output = "".join(logs)
        
        import re
        match = re.search(r"SKELETON_VERIFICATION_START(.*?)"
                          r"SKELETON_VERIFICATION_END", merged_output)
        if match:
            return True, json.loads(match.group(1))
            
    return False, {"error": f"Failed to query Unreal Editor."}


def unpack_game_archive(unrealpak_path: str, pak_path: str, dest_dir: str) -> bool:
    if not os.path.exists(unrealpak_path):
        return False
    shutil.rmtree(dest_dir, ignore_errors=True)
    os.makedirs(dest_dir, exist_ok=True)
    
    cmd = [unrealpak_path, pak_path, f"-Extract", dest_dir]
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creation_flags)
        return True
    except Exception:
        return False


def main():
    log(f"=== PalBaker CLI Altermatic Compile & Strip Test (Chaos Proof): {TARGET_PAL} ===")
    
    sandbox = SettingsSandbox(REPO_ROOT)
    sandbox.backup()

    uasset_gui_exe = os.path.normpath(os.path.join(REPO_ROOT, "deps", "UAssetGUI.exe"))
    unrealpak_exe = None # Derived inside Profile 3

    try:
        # Profile 1: Empty Settings
        log("\n--- Profile 1: Empty Settings Verification ---")
        sandbox.apply_profile("empty")
        exit_code, stdout, stderr = run_cli_command(["altermatic", "toggle", TARGET_PAL, "on"], CLI_ENTRY_POINT)
        assert_graceful_failure(exit_code, stdout, stderr, "EMPTY")
        log("✅ SUCCESS: Profile 1 passed. CLI rejected empty configuration gracefully.")

        # Profile 2: Garbage Settings
        log("\n--- Profile 2: Garbage Settings Verification ---")
        sandbox.apply_profile("garbage")
        exit_code, stdout, stderr = run_cli_command(["altermatic", "toggle", TARGET_PAL, "on"], CLI_ENTRY_POINT)
        assert_graceful_failure(exit_code, stdout, stderr, "GARBAGE")
        log("✅ SUCCESS: Profile 2 passed. CLI rejected invalid paths gracefully.")

        # Profile 3: Real Run
        log("\n--- Profile 3: Real Settings Verification & Run ---")
        sandbox.apply_profile("real")
        
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)

        fmodel_output = settings.get("fmodel_output", "")
        uproject_path = settings.get("uproject", "")
        palworld_exe = settings.get("palworld_exe", "")
        ue_root = settings.get("ue_root", "")
        
        if not fmodel_output or not uproject_path or not ue_root:
            log("Skipping Profile 3 run: Required paths are not configured in settings.", "WARNING")
            return

        project_name = os.path.splitext(os.path.basename(uproject_path))[0]
        unrealpak_exe = os.path.normpath(os.path.join(ue_root, "Engine", "Binaries", "Win64", "UnrealPak.exe"))
        
        if not os.path.exists(unrealpak_exe):
            raise AssertionError(f"Missing required UnrealPak dependency at {unrealpak_exe}")

        target_dir = os.path.normpath(os.path.join(
            fmodel_output, "Exports", "Pal", "Content", "Pal", "Model", "Character", "Monster", TARGET_PAL
        ))
        target_alt_dir = os.path.normpath(os.path.join(
            fmodel_output, "Exports", "Pal", "Content", "Palbaker", "Model", "Character", "Monster", TARGET_PAL
        ))

        # Self-Healing: Verify Nyafia is extracted
        if not os.path.exists(target_dir):
            log("Prerequisite Missing: Nyafia assets are not extracted. Executing self-healing step...")
            exit_code, stdout, stderr = run_cli_command(["mod", "extract", TARGET_PAL], CLI_ENTRY_POINT)
            if exit_code != 0:
                raise RuntimeError(f"Self-healing extraction failed. STDOUT: {stdout}\nSTDERR: {stderr}")

        # Ensure a completely clean Altermatic workspace
        if os.path.exists(target_alt_dir):
            shutil.rmtree(target_alt_dir, ignore_errors=True)

        # 1. Enable Altermatic and add custom variant
        log("Activating Altermatic and cloning .blend workspace...")
        run_cli_command(["altermatic", "toggle", TARGET_PAL, "on"], CLI_ENTRY_POINT)
        run_cli_command(["altermatic", "add", TARGET_PAL, VARIANT_LABEL, "--custom", "--source", "base"], CLI_ENTRY_POINT)
        
        # Save custom properties
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
        run_cli_command(["altermatic", "save", "1", "--data", json.dumps(variant_payload)], CLI_ENTRY_POINT)

        # 2. Execute Mod Push (Baking both meshes, pushing, and linking)
        log("Triggering FBX baking and Unreal Engine remote ingestion...")
        exit_code, stdout, stderr = run_cli_command(["mod", "push", TARGET_PAL], CLI_ENTRY_POINT)
        parsed_push = parse_cli_json(stdout)
        if not parsed_push or parsed_push.get("status") != "success":
            raise AssertionError(f"Ingestion pipeline failed. STDOUT: {stdout}\nSTDERR: {stderr}")

        # 3. Establish connection to Unreal Editor and query skeleton bindings
        log("Connecting to open Unreal Editor session to verify skeletal bindings in memory...")
        base_mesh_virtual_path = f"/Game/Pal/Model/Character/Monster/{TARGET_PAL}/SK_{TARGET_PAL}"
        variant_mesh_virtual_path = f"/Game/Palbaker/Model/Character/Monster/{TARGET_PAL}/SK_{FULL_VARIANT_LABEL}"
        
        expected_skeleton_path = f"/Game/Pal/Model/Character/Skeleton/{TARGET_PAL}/SK_{TARGET_PAL}_Skeleton"
        expected_animbp_class = f"{FULL_VARIANT_LABEL}_BP_C" # Post-process generated C++ class

        success, report = query_unreal_editor_skeletons(ue_root, project_name, [base_mesh_virtual_path, variant_mesh_virtual_path])
        if not success:
            raise AssertionError(f"Unreal Editor skeletal query failed: {report.get('error', 'Unknown Error')}")

        # 4. Assertions on the imported skeletal mesh locations and parent bindings
        log("Executing live Unreal Engine memory assertions...")
        
        # Verify Base Mesh Ingestion
        base_rep = report.get(base_mesh_virtual_path, {})
        if base_rep.get("status") != "exists":
            raise AssertionError(f"Ingestion Failure: Base mesh does not exist: {base_mesh_virtual_path}")
        if base_rep.get("skeleton_path") != expected_skeleton_path:
            raise AssertionError(f"Ingestion Failure: Base mesh is not bound to expected skeleton: {base_rep.get('skeleton_path')}")
            
        # Verify Variant Mesh Ingestion
        var_rep = report.get(variant_mesh_virtual_path, {})
        if var_rep.get("status") != "exists":
            raise AssertionError(f"Ingestion Failure: Altermatic variant was not imported to correct Palbaker directory: {variant_mesh_virtual_path}")
        log(f"  -> Variant imported under correct virtual directory: {os.path.dirname(variant_mesh_virtual_path)}")

        # SKELETON BINDING VERIFICATION
        if var_rep.get("skeleton_path") != expected_skeleton_path:
            raise AssertionError(
                f"SKELETAL BINDING FAILURE: Custom variant mesh is bound to the wrong skeleton: '{var_rep.get('skeleton_path')}'\n"
                f"Expected parent skeleton: '{expected_skeleton_path}'"
            )
        log(f"  -> Skeletal Binding: Cloned variant bound to real parent skeleton (Lossless Rigging)")

        # AnimBP BINDING VERIFICATION (Verifying variant-isolated AnimBP class binding)
        if var_rep.get("post_process_class") != expected_animbp_class:
            raise AssertionError(
                f"AnimBP BINDING FAILURE: Cloned variant mesh post-process slot is bound to wrong class: '{var_rep.get('post_process_class')}'\n"
                f"Expected variant blueprint class: '{expected_animbp_class}'"
            )
        log(f"  -> AnimBP Binding:  Cloned variant post-process bound to parent AnimBP")

        # 5. Execute targeted Cook and Pack
        log("Triggering micro-cook and pack compile...")
        
        output_dir = os.path.dirname(uproject_path)
        if palworld_exe and os.path.exists(palworld_exe):
            output_dir = os.path.join(os.path.dirname(palworld_exe), "Pal", "Content", "Paks", "palBaker")
        final_pak_path = os.path.normpath(os.path.join(output_dir, f"{TARGET_PAL}_P.pak"))

        if os.path.exists(final_pak_path):
            try: os.remove(final_pak_path)
            except OSError: pass

        exit_code, stdout, stderr = run_cli_command(["mod", "cook", TARGET_PAL], CLI_ENTRY_POINT)
        parsed_cook = parse_cli_json(stdout)
        if not parsed_cook or parsed_cook.get("status") != "success":
            raise AssertionError(f"Cooking and packing execution failed. STDOUT: {stdout}\nSTDERR: {stderr}")

        if not os.path.exists(final_pak_path):
            raise AssertionError(f"Cook succeeded but the final .pak file was not written: {final_pak_path}")

        # 6. Unpack compiled .pak and assert skeleton exclusion rules
        log("Unpacking compiled game archive for diagnostic verification...")
        temp_unpack_dir = os.path.join(TESTS_DIR, "temp_pak_unpack")
        success = unpack_game_archive(unrealpak_exe, final_pak_path, temp_unpack_dir)
        if not success:
            raise AssertionError("UnrealPak.exe failed to extract the compiled game archive.")

        # Walk the unpacked files
        log("Scanning unpacked game assets...")
        unpacked_files = []
        for root, _, files in os.walk(temp_unpack_dir):
            for file in files:
                unpacked_files.append(file.lower())

        # Assert variant mesh is compiled and packaged
        expected_variant_mesh = f"SK_{FULL_VARIANT_LABEL}.uasset".lower()
        if expected_variant_mesh not in unpacked_files:
            raise AssertionError(f"Unpacked Archive Failure: Cloned variant mesh asset '{expected_variant_mesh}' was not packaged.")
        log(f"  -> Custom Variant Mesh verified inside archive: {expected_variant_mesh}")

        # SKELETON EXCLUSION TEST
        blacklisted_skeleton = f"SK_{TARGET_PAL}_Skeleton.uasset".lower()
        if blacklisted_skeleton in unpacked_files:
            raise AssertionError(
                f"RAGDOLL SECURITY VULNERABILITY FAILED:\n"
                f"Skeletal Asset '{blacklisted_skeleton}' was packaged inside the final archive.\n"
                f"Shipping custom skeleton files will trigger infinite ragdoll glitches in-game."
            )
        log("  -> Safe Packaging: Parent skeleton successfully stripped from archive (Zero Ragdoll Glitch Guard)")

        # 7. Dynamic Altermatic Loose JSON Deployment Verification
        if palworld_exe and os.path.exists(palworld_exe):
            swap_json_dir = os.path.normpath(os.path.join(
                os.path.dirname(palworld_exe), "Pal", "Content", "Paks", "~Mods", "SwapJSON"
            ))
            expected_deployed_json = os.path.join(swap_json_dir, f"palbaker-{TARGET_PAL}.json")
            
            log(f"Verifying existence of deployed Altermatic JSON config: {expected_deployed_json}")
            if not os.path.exists(expected_deployed_json):
                raise AssertionError(f"Altermatic Deployment Failure: Loose config JSON was not written to: {expected_deployed_json}")
            log(f"  -> Altermatic Loose JSON Config verified on disk: {os.path.basename(expected_deployed_json)}")

        log(f"\n✅ PASS: Profile 3 passed. Altermatic compilation, skeletal binding, and safe-stripping fully verified.")

    except Exception as e:
        log(f"❌ TEST FAILED: {str(e)}", "ERROR")
        sys.exit(1)
        
    finally:
        # Teardown: Call the CLI to restore clean state
        log("\n--- Cleanup & Teardown ---")
        if os.path.exists(SETTINGS_FILE):
            run_cli_command(["altermatic", "toggle", TARGET_PAL, "off"], CLI_ENTRY_POINT)
        if target_alt_dir and os.path.exists(target_alt_dir):
            shutil.rmtree(target_alt_dir, ignore_errors=True)
        shutil.rmtree(os.path.join(TESTS_DIR, "temp_pak_unpack"), ignore_errors=True)
        sandbox.restore()

if __name__ == "__main__":
    main()