# utils/blueprint_patcher.py

"""
================================================================================
          PALBAKER BLUEPRINT PATCHER ENGINE - STRICT PRESERVATION GUIDE
================================================================================
CRITICAL CONSTRAINTS:

1. ANIMATION BLUEPRINT INHERITANCE (THE "ABP_WEASELDRAGON" CONSTRAINT):
   Custom standalone Pals must inherit and utilize their parent template's 
   animations and skeletons (e.g., ABP_WeaselDragon_C). Naively replacing 
   "BP_WeaselDragon" inside class paths will corrupt "ABP_WeaselDragon_C" into 
   "ABP_Furret_C". Since "ABP_Furret_C" does not exist, the Pal will spawn in 
   a static T-Pose/A-Pose or freeze.
   
   - DO NOT perform blind global string replacements of the template name.
   - ALWAYS use a negative lookbehind (?<!A) when targeting class strings:
     e.g., re.sub(rf"(?<!A)BP_{template_id}", ...)
     This guarantees that "ABP_WeaselDragon" remains completely untouched.

2. OBJECTNAME & OBJECTPATH PAIRING RULE:
   Unreal Engine's serialization framework mandates that both the ObjectPath 
   and the ObjectName reference structures are updated in tandem:
   - ObjectPath: "/Game/Pal/Model/Character/Monster/Furret/SK_Furret"
   - ObjectName: "SkeletalMesh'SK_Furret'" (NOT "SkeletalMesh'SK_WeaselDragon'")
   Failing to replace the ObjectName alongside the ObjectPath results in 
   a null-mesh binding, making the Pal completely invisible in-world.

3. DOUBLE-QUOTED RAW REFERENCE BINDINGS:
   UAssetGUI imports include raw double-quoted strings in the Imports table 
   (e.g., '"SK_WeaselDragon"'). These must be explicitly searched and replaced 
   with double-quoted targets ('"SK_Furret"') to allow the serializer to 
   bind the newly cooked uassets at runtime.
================================================================================
"""

import os
import re
import shutil
import subprocess
from utils.extractor.core import extract_game_files

def patch_actor_blueprint(settings: dict, pal_id: str, template_id: str, log_callback=None) -> bool:
    """
    Unified processing engine to extract, JSON-patch, and compile standalone 
    custom Pal blueprints using UAssetGUI CLI.
    """
    def log(msg, category="standard"):
        if log_callback:
            log_callback(msg, category)
        else:
            print(f"[Blueprint Patch] {msg}", flush=True)

    custom_folder_name = pal_id
    custom_asset_name = f"BP_{pal_id}"
    
    # 1. Resolve UAssetGUI executable path
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    uasset_gui_exe = os.path.normpath(os.path.join(repo_root, "deps", "UAssetGUI.exe"))
    
    if not os.path.exists(uasset_gui_exe):
        log(f"Error: UAssetGUI.exe not found at {uasset_gui_exe}", "error")
        return False

    # 2. Extract the original parent uasset and uexp
    relative_uasset = f"Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/{template_id}/BP_{template_id}.uasset"
    relative_uexp = f"Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/{template_id}/BP_{template_id}.uexp"
    
    temp_dir = os.path.join(repo_root, "temp_bp_extract")
    shutil.rmtree(temp_dir, ignore_errors=True)
    os.makedirs(temp_dir, exist_ok=True)
    
    success, msg = extract_game_files(settings, [relative_uasset, relative_uexp], temp_dir, format_type="raw")
    if not success:
        log(f"Failed to extract parent blueprint for {template_id}: {msg}", "error")
        return False
        
    src_uasset = os.path.join(temp_dir, f"Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/{template_id}/BP_{template_id}.uasset")
    src_uexp = os.path.join(temp_dir, f"Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/{template_id}/BP_{template_id}.uexp")
    
    if not os.path.exists(src_uasset) or not os.path.exists(src_uexp):
        log(f"Extracted blueprint files not found for {template_id}.", "error")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    # 3. Export .uasset to temporary JSON using UAssetGUI CLI
    temp_json_path = os.path.join(temp_dir, "temp_blueprint.json")
    cmd_export = [uasset_gui_exe, "tojson", src_uasset, temp_json_path, "VER_UE5_1"]
    
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        subprocess.run(cmd_export, check=True, creationflags=creation_flags)
    except Exception as e:
        log(f"UAssetGUI failed to export JSON: {e}", "error")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    # 4. Parse the JSON and perform highly-targeted string modifications
    try:
        with open(temp_json_path, "r", encoding="utf-8") as f:
            json_str = f.read()

        # Phase 1: EXACT string replacements that target the Package Paths & Object Names perfectly
        replacements = {
            # Package Paths
            f"/PalActorBP/{template_id}/BP_{template_id}": f"/PalActorBP/{pal_id}/BP_{pal_id}",
            f"/Monster/{template_id}/SK_{template_id}": f"/Monster/{pal_id}/SK_{pal_id}",
            f"/Monster/{template_id}/PA_{template_id}": f"/Monster/{pal_id}/PA_{pal_id}",
            
            # UAssetGUI ObjectName Exact Matches (Fixes invisible meshes and broken collisions)
            f"SkeletalMesh'SK_{template_id}'": f"SkeletalMesh'SK_{pal_id}'",
            f'"SK_{template_id}"': f'"SK_{pal_id}"',
            f"PhysicsAsset'PA_{template_id}_PhysicsAsset'": f"PhysicsAsset'PA_{pal_id}_PhysicsAsset'",
            f'"PA_{template_id}_PhysicsAsset"': f'"PA_{pal_id}_PhysicsAsset"',
            
            # Specific default blueprint object instantiations
            f"Default__BP_{template_id}": f"Default__BP_{pal_id}",
            f'"BP_{template_id}"': f'"BP_{pal_id}"'
        }

        for old, new in replacements.items():
            json_str = json_str.replace(old, new)

        # Phase 2: Regex replacements to safely target the Actor Blueprint Class Names
        # The (?<!A) ensures we DO NOT match "ABP_WeaselDragon_C", preserving the animation blueprint!
        json_str = re.sub(rf"(?<!A)BP_{template_id}_C", f"BP_{pal_id}_C", json_str)
        json_str = re.sub(rf"(?<!A)BP_{template_id}(?!_C)", f"BP_{pal_id}", json_str)

        with open(temp_json_path, "w", encoding="utf-8") as f:
            f.write(json_str)
    except Exception as e:
        log(f"Failed to patch blueprint JSON: {e}", "error")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    # 5. Import the modified JSON back into cooked assets using UAssetGUI CLI
    uproject = settings.get("uproject", "")
    project_dir = os.path.dirname(uproject)
    project_name = os.path.splitext(os.path.basename(uproject))[0]
    
    if not project_dir or not os.path.exists(project_dir):
        log("Project directory not found in settings.", "error")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False
        
    old_uncooked_dir = os.path.join(project_dir, "Content", "Pal", "Blueprint", "Character", "Monster", "PalActorBP", custom_folder_name)
    if os.path.exists(old_uncooked_dir):
        try:
            shutil.rmtree(old_uncooked_dir)
        except Exception:
            pass

    cooked_dir = os.path.join(project_dir, "Saved", "Cooked", "Windows", project_name, "Content", "Pal", "Blueprint", "Character", "Monster", "PalActorBP", custom_folder_name)
    os.makedirs(cooked_dir, exist_ok=True)
    
    cooked_uasset = os.path.join(cooked_dir, f"{custom_asset_name}.uasset")
    
    cmd_import = [uasset_gui_exe, "fromjson", temp_json_path, cooked_uasset]
    try:
        subprocess.run(cmd_import, check=True, creationflags=creation_flags)
    except Exception as e:
        log(f"UAssetGUI failed to serialize assets: {e}", "error")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    shutil.rmtree(temp_dir, ignore_errors=True)
    log(f"Generated standalone pre-cooked blueprint class {custom_asset_name} at: {cooked_uasset}", "success")
    return True