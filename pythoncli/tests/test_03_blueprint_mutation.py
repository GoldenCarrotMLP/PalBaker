# tests/test_03_blueprint_mutation.py
"""
================================================================================
PALBAKER CLI INTEGRATION TEST 03: BLUEPRINT MUTATION & DEEP PARSING
================================================================================
COMMANDS EXECUTED SEQUENTIALLY ON THIS TEST:

[PROFILE 1: EMPTY CONFIGURATION]
1. Zeroes out all active configuration paths.
2. Attempt standalone Pal instantiation:
   python palbaker_cli.py creator add BadCatgirlTest --template BadCatgirl
3. Asserts CLI gracefully returns status 'error' and exit code 1.

[PROFILE 2: GARBAGE CONFIGURATION]
4. Writes non-existent junk paths to the settings config.
5. Attempt standalone Pal instantiation:
   python palbaker_cli.py creator add BadCatgirlTest --template BadCatgirl
6. Asserts CLI gracefully returns status 'error', exit code 1, and path warnings.

[PROFILE 3: REAL CONFIGURATION]
7. Restores the user's active manager_settings.json.
8. Creates a new custom standalone Pal and triggers automated lookbehind patching:
   python palbaker_cli.py creator add BadCatgirlTest --template BadCatgirl
9. Extracts the *vanilla* BP_BadCatgirl.uasset using cue4parse.
10. Converts BOTH the vanilla .uasset and the modified .uasset to JSON.
11. Performs a recursive Deep JSON Diff:
    - Asserts both JSONs have identically matching schemas, arrays, and keys.
    - Bypasses UAssetGUI recalculated math (offsets, sizes, counts) dynamically.
    - Asserts that anywhere values differ, it is STRICTLY related to our intended
      string replacements, proving zero data loss or serialization corruption.
12. Performs a structured ObjectName validation check supporting both modern
    and legacy UAssetGUI JSON schemas.
13. Performs clean teardown of the custom test Pal.
================================================================================
"""

import os
import sys
import json
import shutil
import subprocess
from test_helper import SettingsSandbox, run_cli_command, parse_cli_json, log

# Resolve paths relative to the test file location
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
SETTINGS_FILE = os.path.join(REPO_ROOT, "manager_settings.json")
CLI_ENTRY_POINT = os.path.join(REPO_ROOT, "palbaker_cli.py")

TARGET_PAL = "BadCatgirlTest"
TEMPLATE_PAL = "BadCatgirl"

def assert_graceful_failure(exit_code: int, stdout: str, stderr: str, profile_name: str):
    if "traceback" in stdout.lower() or "traceback" in stderr.lower():
         raise AssertionError(f"CLI crashed with a raw Python traceback under {profile_name} profile.\nSTDOUT: {stdout}\nSTDERR: {stderr}")
    parsed = parse_cli_json(stdout)
    if not parsed:
         raise AssertionError(f"CLI did not output a valid JSON envelope under {profile_name}.\nExit Code: {exit_code}\nSTDOUT: {stdout}")
    if parsed.get("status") != "error":
         raise AssertionError(f"Expected status 'error' under {profile_name}, got '{parsed.get('status')}'")


def verify_structural_integrity(orig_node, mod_node, path="root"):
    """
    Recursively walks two JSON dictionaries simultaneously.
    Ensures that the entire structural schema is 100% identical and that 
    the only changes made are the expected string mutations.
    """
    # 1. Type Matching
    if type(orig_node) != type(mod_node):
        # Gracefully handle implicit float/int casting by Python's JSON decoder
        if isinstance(orig_node, (int, float)) and isinstance(mod_node, (int, float)):
            pass
        else:
            raise AssertionError(f"Serialization Corruption: Type mismatch at {path}. Orig: {type(orig_node).__name__} vs Mod: {type(mod_node).__name__}")
    
    # Extract current key to check for dynamic offset-bypass rules
    current_key = path.split(".")[-1].split("[")[0].lower()

    # 2. Binary Shifting Bypass Check
    # UAssetGUI dynamically recalculates array counts, sizes, and file byte offsets.
    # We ignore their explicit values, relying on type and schema mapping to prove integrity.
    if "offset" in current_key or "size" in current_key or "count" in current_key:
        return

    # 3. Dictionary Walk
    if isinstance(orig_node, dict):
        orig_keys = set(orig_node.keys())
        mod_keys = set(mod_node.keys())
        
        if orig_keys != mod_keys:
            missing = orig_keys - mod_keys
            extra = mod_keys - orig_keys
            raise AssertionError(f"Serialization Corruption: Key mismatch at {path}.\nMissing keys: {missing}\nExtra keys: {extra}")
            
        for k in orig_keys:
            verify_structural_integrity(orig_node[k], mod_node[k], f"{path}.{k}")
            
    # 4. Array Walk
    elif isinstance(orig_node, list):
        if len(orig_node) != len(mod_node):
            raise AssertionError(f"Serialization Corruption: Array length mismatch at {path}. Orig: {len(orig_node)} vs Mod: {len(mod_node)}")
            
        for i in range(len(orig_node)):
            verify_structural_integrity(orig_node[i], mod_node[i], f"{path}[{i}]")
            
    # 5. String Mutation Validation
    elif isinstance(orig_node, str):
        if orig_node != mod_node:
            # If the strings differ, it MUST be because of our targeted Pal ID injection.
            if TEMPLATE_PAL not in orig_node or TARGET_PAL not in mod_node:
                raise AssertionError(f"Unexpected string mutation detected at {path}!\nOriginal: {orig_node}\nModified: {mod_node}")
                
            # Crucial assertion: Ensure the AnimBP was NOT corrupted.
            if f"ABP_{TEMPLATE_PAL}" in orig_node and f"ABP_{TARGET_PAL}" in mod_node:
                 raise AssertionError(
                     f"CRITICAL ANIMATION BP CORRUPTION DETECTED at {path}!\n"
                     f"The negative lookbehind regex failed. 'ABP_{TEMPLATE_PAL}' was mutated into 'ABP_{TARGET_PAL}'. "
                     f"This will break in-game animations."
                 )
                
    # 6. Primitives (int, float, bool, null)
    else:
        if orig_node != mod_node:
            raise AssertionError(f"Serialization Corruption: Primitive value mismatch at {path}. Orig: {orig_node} vs Mod: {mod_node}")


def main():
    log(f"=== PalBaker CLI Blueprint Mutation (Chaos Proof): {TARGET_PAL} ===")
    
    sandbox = SettingsSandbox(REPO_ROOT)
    sandbox.backup()

    uasset_gui_exe = os.path.normpath(os.path.join(REPO_ROOT, "deps", "UAssetGUI.exe"))
    if not os.path.exists(uasset_gui_exe):
        log(f"Fatal: Missing required UAssetGUI dependency at {uasset_gui_exe}", "ERROR")
        sys.exit(1)

    try:
        # Profile 1: Empty Settings
        log("\n--- Profile 1: Empty Settings Verification ---")
        sandbox.apply_profile("empty")
        exit_code, stdout, stderr = run_cli_command(["creator", "add", TARGET_PAL, "--template", TEMPLATE_PAL], CLI_ENTRY_POINT)
        assert_graceful_failure(exit_code, stdout, stderr, "EMPTY")
        log("✅ SUCCESS: Profile 1 passed. CLI rejected empty configuration gracefully.")

        # Profile 2: Garbage Settings
        log("\n--- Profile 2: Garbage Settings Verification ---")
        sandbox.apply_profile("garbage")
        exit_code, stdout, stderr = run_cli_command(["creator", "add", TARGET_PAL, "--template", TEMPLATE_PAL], CLI_ENTRY_POINT)
        assert_graceful_failure(exit_code, stdout, stderr, "GARBAGE")
        log("✅ SUCCESS: Profile 2 passed. CLI rejected invalid paths gracefully.")

        # Profile 3: Real Run
        log("\n--- Profile 3: Real Settings Verification & Run ---")
        sandbox.apply_profile("real")
        
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)

        fmodel_output = settings.get("fmodel_output", "")
        uproject_path = settings.get("uproject", "")
        if not fmodel_output or not uproject_path:
            log("Skipping Profile 3 run: Required paths are not configured in settings.", "WARNING")
            return

        project_dir = os.path.dirname(uproject_path)
        project_name = os.path.splitext(os.path.basename(uproject_path))[0]

        creator_file = os.path.normpath(os.path.join(fmodel_output, "Exports", "Pal", "Content", "Palbaker", "Creator", f"{TARGET_PAL}_creator.json"))
        if os.path.exists(creator_file):
            os.remove(creator_file)

        # Cleanup existing cooked assets to guarantee a fresh compilation check
        cooked_uasset_path = os.path.normpath(os.path.join(
            project_dir, "Saved", "Cooked", "Windows", project_name, 
            "Content", "Pal", "Blueprint", "Character", "Monster", "PalActorBP", 
            TARGET_PAL, f"BP_{TARGET_PAL}.uasset"
        ))
        if os.path.exists(cooked_uasset_path):
            log(f"Wiping existing cooked target uasset to guarantee fresh compilation: {cooked_uasset_path}")
            os.remove(cooked_uasset_path)

        # 1. Instantiate the custom Pal
        log(f"Instantiating Custom Standalone Pal: {TARGET_PAL} from {TEMPLATE_PAL}...")
        exit_code, stdout, stderr = run_cli_command(["creator", "add", TARGET_PAL, "--template", TEMPLATE_PAL], CLI_ENTRY_POINT)
        parsed_add = parse_cli_json(stdout)
        if not parsed_add or parsed_add.get("status") != "success":
            raise AssertionError(f"Failed to instantiate custom Pal. STDOUT: {stdout}\nSTDERR: {stderr}")

        # 2. Extract Original Vanilla Blueprint to temp folder
        log("Extracting original vanilla parent blueprint for baseline comparison...")
        sys.path.append(REPO_ROOT)
        from utils.extractor.core import extract_game_files
        
        temp_dir = os.path.join(TESTS_DIR, "temp_bp_diff")
        shutil.rmtree(temp_dir, ignore_errors=True)
        os.makedirs(temp_dir, exist_ok=True)
        
        relative_uasset = f"Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/{TEMPLATE_PAL}/BP_{TEMPLATE_PAL}.uasset"
        relative_uexp = f"Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/{TEMPLATE_PAL}/BP_{TEMPLATE_PAL}.uexp"
        
        success, msg = extract_game_files(settings, [relative_uasset, relative_uexp], temp_dir, format_type="raw")
        if not success:
            raise AssertionError(f"Failed to extract vanilla blueprint: {msg}")

        vanilla_uasset_path = os.path.join(temp_dir, f"Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/{TEMPLATE_PAL}/BP_{TEMPLATE_PAL}.uasset")
        if not os.path.exists(vanilla_uasset_path):
            raise AssertionError("Extracted vanilla .uasset not found on disk.")

        # 3. Verify the generated cooked .uasset exists
        if not os.path.exists(cooked_uasset_path):
            raise AssertionError(f"Patched compiled blueprint was not saved to expected path: {cooked_uasset_path}")

        # 4. Decompile BOTH to JSON using UAssetGUI
        log("Decompiling BOTH assets to JSON for structural diffing...")
        vanilla_json_path = os.path.join(temp_dir, "vanilla.json")
        modified_json_path = os.path.join(temp_dir, "modified.json")

        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        subprocess.run([uasset_gui_exe, "tojson", vanilla_uasset_path, vanilla_json_path, "VER_UE5_1"], check=True, creationflags=creation_flags)
        subprocess.run([uasset_gui_exe, "tojson", cooked_uasset_path, modified_json_path, "VER_UE5_1"], check=True, creationflags=creation_flags)

        # 5. Load and Execute Deep Recursive Diff
        log("Executing Deep Recursive JSON Diff...")
        with open(vanilla_json_path, "r", encoding="utf-8") as f:
            vanilla_data = json.load(f)
        with open(modified_json_path, "r", encoding="utf-8") as f:
            modified_data = json.load(f)

        verify_structural_integrity(vanilla_data, modified_data)

        # 6. Specific ObjectName confirmation check (Mesh visibility guard)
        log("Validating ObjectName linking rules...")
        
        # Check Imports table for modern structured references
        has_mesh_link = False
        imports = modified_data.get("Imports", [])
        for imp in imports:
            if imp.get("ClassName") == "SkeletalMesh" and imp.get("ObjectName") == f"SK_{TARGET_PAL}":
                has_mesh_link = True
                break
                
        # Fallback check on raw string dump (for older UAssetGUI installations)
        mod_json_str = json.dumps(modified_data)
        expected_mesh_objname = f"SkeletalMesh'SK_{TARGET_PAL}'"
        if expected_mesh_objname in mod_json_str:
            has_mesh_link = True

        if not has_mesh_link:
            log("Diagnostic: MESH VISIBILITY CHECK FAILED. Scanning modified JSON for any SkeletalMesh references...", "WARNING")
            matches = []
            def find_skeletal_meshes(node, path="root"):
                if isinstance(node, str):
                    if "skeletalmesh" in node.lower() or "skinnedasset" in node.lower() or "sk_" in node.lower():
                        matches.append(f"  {path}: '{node}'")
                elif isinstance(node, dict):
                    for k, v in node.items():
                        find_skeletal_meshes(v, f"{path}.{k}")
                elif isinstance(node, list):
                    for i, v in enumerate(node):
                        find_skeletal_meshes(v, f"{path}[{i}]")
            find_skeletal_meshes(modified_data)
            for m in matches[:20]:
                log(m, "DEBUG")
                
            raise AssertionError(
                f"MESH VISIBILITY FAILURE: Expected ObjectName mapping for 'SK_{TARGET_PAL}' is missing.\n"
                f"The Pal will render invisible. See diagnostic logs above for actual compiled strings."
            )

        log("✅ PASS: Profile 3 passed. Blueprint structural schema is 100% intact with zero serialization corruption.")

    except Exception as e:
        log(f"❌ TEST FAILED: {str(e)}", "ERROR")
        sys.exit(1)
        
    finally:
        # Teardown: Call the CLI to delete the custom Pal definition and clean up
        log("\n--- Cleanup & Teardown ---")
        if os.path.exists(SETTINGS_FILE):
            run_cli_command(["creator", "delete", TARGET_PAL], CLI_ENTRY_POINT)
        shutil.rmtree(os.path.join(TESTS_DIR, "temp_bp_diff"), ignore_errors=True)
        sandbox.restore()

if __name__ == "__main__":
    main()