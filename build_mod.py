# build_mod.py
import os
import sys
import glob
import json
import shutil
import subprocess
import re
from utils.builder.workspace import ModWorkspace
from utils.builder.config_helper import restore_palbaker_backup, GameIniCookContext
from utils.builder.blender_helper import run_headless_blender
from utils.builder.unreal_helper import run_remote_import
from utils.builder.cooker_helper import clean_cook_environment, resolve_packaging_manifest, run_and_stream, pack_cooked_assets
from utils.state import save_push_state

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding='utf-8')

def generate_cooked_actor_blueprint(settings: dict, pal_id: str, template_id: str, project_dir: str, project_name: str) -> bool:
    """
    Dynamically extracts, clones, and compiles the parent actor blueprint
    directly into your project's Saved/Cooked directory before packaging.
    Allows variable-length string modifications without binary corruption.
    """
    custom_folder_name = pal_id
    custom_asset_name = f"BP_{pal_id}"
    
    # 1. Resolve UAssetGUI executable path
    repo_root = os.path.dirname(os.path.abspath(__file__))
    uasset_gui_exe = os.path.normpath(os.path.join(repo_root, "deps", "UAssetGUI.exe"))
    
    if not os.path.exists(uasset_gui_exe):
        print(f"[Blueprint Patch] Error: UAssetGUI.exe not found at {uasset_gui_exe}", flush=True)
        return False

    # 2. Extract the original parent uasset and uexp
    relative_uasset = f"Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/{template_id}/BP_{template_id}.uasset"
    relative_uexp = f"Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/{template_id}/BP_{template_id}.uexp"
    
    from utils.extractor.core import extract_game_files
    temp_dir = os.path.join(repo_root, "temp_bp_extract")
    shutil.rmtree(temp_dir, ignore_errors=True)
    os.makedirs(temp_dir, exist_ok=True)
    
    success, msg = extract_game_files(settings, [relative_uasset, relative_uexp], temp_dir, format_type="raw")
    if not success:
        print(f"[Blueprint Patch] Failed to extract parent blueprint for {template_id}: {msg}", flush=True)
        return False
        
    src_uasset = os.path.join(temp_dir, f"Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/{template_id}/BP_{template_id}.uasset")
    src_uexp = os.path.join(temp_dir, f"Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/{template_id}/BP_{template_id}.uexp")
    
    if not os.path.exists(src_uasset) or not os.path.exists(src_uexp):
        print(f"[Blueprint Patch] Extracted blueprint files not found for {template_id}.", flush=True)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    # 3. Export .uasset to temporary JSON using UAssetGUI CLI
    temp_json_path = os.path.join(temp_dir, "temp_blueprint.json")
    cmd_export = [uasset_gui_exe, "tojson", src_uasset, temp_json_path, "VER_UE5_1"]
    
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        subprocess.run(cmd_export, check=True, creationflags=creation_flags)
    except Exception as e:
        print(f"[Blueprint Patch] UAssetGUI failed to export JSON: {e}", flush=True)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    # 4. Parse the JSON and perform variable-length string modifications
    try:
        with open(temp_json_path, "r", encoding="utf-8") as f:
            json_str = f.read()

        # Define replacements (no length matching required!)
        replacements = {
            # Package and class names
            f"/Game/Pal/Blueprint/Character/Monster/PalActorBP/{template_id}/BP_{template_id}": f"/Game/Pal/Blueprint/Character/Monster/PalActorBP/{custom_folder_name}/{custom_asset_name}",
            f"Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/{template_id}/BP_{template_id}": f"Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/{custom_folder_name}/{custom_asset_name}",
            f"Default__BP_{template_id}_C": f"Default__{custom_asset_name}_C",
            f"BP_{template_id}.BP_{template_id}_C": f"{custom_asset_name}.{custom_asset_name}_C",
            
            # Hardcoded Skeletal Mesh redirects (replaces WeaselDragon with your custom mesh path)
            f"/Game/Pal/Model/Character/Monster/WeaselDragon/SK_WeaselDragon": f"/Game/Pal/Model/Character/Monster/{custom_folder_name}/SK_{custom_folder_name}",
            f"Pal/Content/Pal/Model/Character/Monster/WeaselDragon/SK_WeaselDragon": f"Pal/Content/Pal/Model/Character/Monster/{custom_folder_name}/SK_{custom_folder_name}"
        }

        # Standard string replacements
        for old, new in replacements.items():
            json_str = json_str.replace(old, new)

        # Smart regex-based replacement to change BP_{template_id}_C -> BP_{custom_id}_C, 
        # while protecting any instances containing 'ABP_' from being modified
        class_pattern = re.compile(rf"(?<!A)BP_{template_id}_C")
        json_str = class_pattern.sub(f"{custom_asset_name}_C", json_str)

        with open(temp_json_path, "w", encoding="utf-8") as f:
            f.write(json_str)
    except Exception as e:
        print(f"[Blueprint Patch] Failed to patch blueprint JSON: {e}", flush=True)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    # 5. Import the modified JSON back into cooked assets using UAssetGUI CLI
    cooked_dir = os.path.join(project_dir, "Saved", "Cooked", "Windows", project_name, "Content", "Pal", "Blueprint", "Character", "Monster", "PalActorBP", custom_folder_name)
    os.makedirs(cooked_dir, exist_ok=True)
    
    cooked_uasset = os.path.join(cooked_dir, f"{custom_asset_name}.uasset")
    
    cmd_import = [uasset_gui_exe, "fromjson", temp_json_path, cooked_uasset]
    try:
        subprocess.run(cmd_import, check=True, creationflags=creation_flags)
    except Exception as e:
        print(f"[Blueprint Patch] UAssetGUI failed to serialize assets: {e}", flush=True)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    shutil.rmtree(temp_dir, ignore_errors=True)
    print(f"[Blueprint Patch] Dynamically generated standalone cooked blueprint at: {cooked_uasset}", flush=True)
    return True

def main():
    if len(sys.argv) < 4:
        print("ERROR: Missing arguments. Usage: build_mod.py <name> <category> <action>")
        sys.exit(1)

    MONSTER_NAME = sys.argv[1]
    CATEGORY = sys.argv[2] 
    ACTION = sys.argv[3]   

    SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "manager_settings.json")
    with open(SETTINGS_FILE, "r") as f:
        settings = json.load(f)

    workspace = ModWorkspace(MONSTER_NAME, CATEGORY, settings)

    # -------------------------------------------------------------
    # PHASE 0: RAW FMODEL DECOMPILE (Create .blend file)
    # -------------------------------------------------------------
    if ACTION == "create_blend":
        psk_files = glob.glob(os.path.join(workspace.fmodel_dir, "*.psk"))
        if not psk_files:
            print("ERROR: No .psk skeletal mesh found in FModel directory.", flush=True)
            sys.exit(1)
            
        psk_file = psk_files[0]
        blend_file = os.path.join(workspace.fmodel_dir, f"{MONSTER_NAME}.blend")
        reconstructor_script = os.path.join(os.path.dirname(__file__), "utils", "blender_reconstruct.py")
        
        psk_file_clean = psk_file.replace("\\", "/")
        blend_file_clean = blend_file.replace("\\", "/")
        
        from utils.fmodel_helper import preprocess_fmodel_textures
        preprocess_fmodel_textures(workspace.fmodel_dir, workspace.fmodel_root)
        
        print("Launching headless Blender to reconstruct .blend workspace from .psk...", flush=True)
        result = run_headless_blender(
            workspace.blender_path, 
            None, 
            reconstructor_script, 
            ["--fbx", psk_file_clean, "--output", blend_file_clean]
        )
        
        if os.path.exists(blend_file):
            print(f"SUCCESS! .blend file generated at: {blend_file}", flush=True)
            
            extractor_script = os.path.normpath(os.path.join(os.path.dirname(__file__), "utils", "blender_extractor.py"))
            output_json = os.path.join(workspace.fmodel_dir, f"{MONSTER_NAME}_blend.json")
            
            print("Generating companion sidecar layout on the fly...", flush=True)
            run_headless_blender(
                workspace.blender_path,
                blend_file,
                extractor_script,
                ["--output", output_json]
            )
            
            if result.stdout.strip():
                print("\n=== BLENDER PIPELINE LOGS ===", flush=True)
                print(result.stdout, flush=True)
                print("=============================\n", flush=True)
        else:
            print("ERROR: Blender executed but failed to save .blend file. Internal traceback:", flush=True)
            print(result.stdout, flush=True)
            print(result.stderr, flush=True)
            sys.exit(1)

    # -------------------------------------------------------------
    # PHASE 1: IMPORT (Push to Unreal)
    # -------------------------------------------------------------
    if ACTION in ["push", "full"]:
        import_targets = []
        
        should_push_vanilla = not workspace.is_altermatic_active or workspace.base_type == "custom"

        if should_push_vanilla:
            if os.path.exists(workspace.fmodel_dir):
                import_targets.append((workspace.fmodel_dir, workspace.ue_virtual_path))
        else:
            if os.path.exists(workspace.fmodel_dir) and os.path.exists(workspace.fmodel_altermatic_dir):
                print("Standalone Altermatic Fallback active. Mirroring modified base assets to Palbaker directory...", flush=True)
                for item in os.listdir(workspace.fmodel_dir):
                    if item == f"{MONSTER_NAME}_altermatic.json" or item == ".palbaker_state.json":
                        continue
                    src_file = os.path.join(workspace.fmodel_dir, item)
                    if os.path.isfile(src_file):
                        dest_file = os.path.join(workspace.fmodel_altermatic_dir, item)
                        if not os.path.exists(dest_file) or os.path.getmtime(src_file) > os.path.getmtime(dest_file):
                            shutil.copy2(src_file, dest_file)
                            print(f"  Mirrored: {item}", flush=True)

        if workspace.is_altermatic_active and os.path.exists(workspace.fmodel_altermatic_dir) and any(f.endswith(".blend") for f in os.listdir(workspace.fmodel_altermatic_dir)):
            import_targets.append((workspace.fmodel_altermatic_dir, workspace.ue_altermatic_virtual_path))

        if not import_targets:
            print("ERROR: No raw model sources found in workspaces to push.", flush=True)
            sys.exit(1)

        from utils.altermatic_helper import sync_sidecar_metadata
        for target_dir, _ in import_targets:
            for blend_file in glob.glob(os.path.join(target_dir, "*.blend")):
                if target_dir == workspace.fmodel_altermatic_dir:
                    base_sidecar = os.path.join(workspace.fmodel_dir, f"{MONSTER_NAME}_blend.json")
                    var_base_name = os.path.splitext(os.path.basename(blend_file))[0]
                    var_sidecar = os.path.join(workspace.fmodel_altermatic_dir, f"{var_base_name}_blend.json")
                    if os.path.exists(base_sidecar) and not os.path.exists(var_sidecar):
                        print(f"  [Self-Healing] Restoring base sidecar {os.path.basename(base_sidecar)} to {os.path.basename(var_sidecar)}", flush=True)
                        shutil.copy2(base_sidecar, var_sidecar)

                print(f"Pre-import synchronizing layout metadata for {os.path.basename(blend_file)}...", flush=True)
                sync_sidecar_metadata(workspace.blender_path, blend_file)

        for target_dir, virtual_path in import_targets:
            blend_files = glob.glob(os.path.join(target_dir, "*.blend"))
            for blend_file in blend_files:
                base_name = os.path.splitext(os.path.basename(blend_file))[0]
                fbx_file = os.path.join(target_dir, f"{base_name}.fbx")
                output_json = os.path.join(target_dir, f"{base_name}_blend.json")
                
                extractor_script = os.path.join(os.path.dirname(__file__), "utils", "blender_extractor.py")
                print(f"Running headless Blender (Exporting FBX for {base_name})...", flush=True)
                run_headless_blender(workspace.blender_path, blend_file, extractor_script, ["--output", output_json, "--fbx", fbx_file])

            pngs = glob.glob(os.path.join(target_dir, "*.png"))
            jsons = glob.glob(os.path.join(target_dir, "MI_*.json"))
            fbx_files = glob.glob(os.path.join(target_dir, "*.fbx"))
            
            fbx_file = fbx_files[0] if fbx_files else ""
            base_mesh_name = os.path.splitext(os.path.basename(fbx_file))[0] if fbx_file else MONSTER_NAME

            config = {
                "ue_target_path": virtual_path,
                "textures": pngs,
                "fbx_file": fbx_file if os.path.exists(fbx_file) else None,
                "mi_jsons": jsons,
                "icon_file": workspace.icon_fmodel_path if (workspace.has_icon and target_dir == workspace.fmodel_dir) else None,
                "bone_data_file": f"{base_mesh_name}_blend.json",
                "template_id": workspace.template_id,
                "is_custom_pal": workspace.is_custom_pal
            }
            config_path = os.path.join(target_dir, "import_config.json")
            with open(config_path, "w") as f:
                json.dump(config, f)

            print(f"Connecting to Open Unreal Engine (Target: {os.path.basename(target_dir)})...", flush=True)
            ue_import_script = os.path.join(os.path.dirname(__file__), "ue_import.py")
            success, log_msg = run_remote_import(workspace.ue_root, workspace.target_project_name, target_dir, ue_import_script)
            
            if log_msg.strip():
                print(log_msg, flush=True)
                
            if not success:
                print(f"!!! ERROR INSIDE UNREAL ENGINE DURING {os.path.basename(target_dir)} IMPORT !!!", flush=True)
                sys.exit(1)

        ue_abs_path = os.path.join(workspace.project_dir, "Content", "Pal", "Model", "Character", CATEGORY, MONSTER_NAME)
        save_push_state(workspace.fmodel_dir, ue_abs_path)

    # -------------------------------------------------------------
    # PHASE 1.5: REFRESH BLEND (Sync layouts on the spot)
    # -------------------------------------------------------------
    if ACTION == "refresh_blend":
        blend_files = []
        if os.path.exists(workspace.fmodel_dir):
            blend_files.extend(glob.glob(os.path.join(workspace.fmodel_dir, "*.blend")))
        if workspace.is_altermatic_active and os.path.exists(workspace.fmodel_altermatic_dir):
            blend_files.extend(glob.glob(os.path.join(workspace.fmodel_altermatic_dir, "*.blend")))

        if not blend_files:
            print("ERROR: No .blend files found in workspace to refresh.", flush=True)
            sys.exit(1)

        extractor_script = os.path.normpath(os.path.join(os.path.dirname(__file__), "utils", "blender_extractor.py"))
        for blend_file in blend_files:
            parent_dir = os.path.dirname(blend_file)
            base_name = os.path.splitext(os.path.basename(blend_file))[0]
            output_json = os.path.normpath(os.path.join(parent_dir, f"{base_name}_blend.json"))
            
            print(f"Synchronizing sidecar layout metadata for {os.path.basename(blend_file)}...", flush=True)
            
            result = run_headless_blender(
                workspace.blender_path,
                blend_file,
                extractor_script,
                ["--output", output_json]
            )
            
            if result.stdout.strip():
                print(result.stdout, flush=True)
            if result.stderr.strip():
                print(result.stderr, flush=True)
            
        print("SUCCESS! Staged layout sync completed.", flush=True)

    # -------------------------------------------------------------
    # PHASE 2: COOK (Compile only)
    # -------------------------------------------------------------
    if ACTION in ["cook", "full", "cook_only"]:
        restore_palbaker_backup(workspace.uproject_path)
        clean_cook_environment(workspace)

        extra_cook_paths = []
        if workspace.has_custom_shader:
            extra_cook_paths.append("/Game/CartoonCelShader/Materials/CelShader")
        if workspace.has_icon:
            extra_cook_paths.append(workspace.icon_virtual_path)
            
        altermatic_rel_path = workspace.ue_altermatic_virtual_path.replace("/Game/", "")
        altermatic_project_source_dir = os.path.join(workspace.project_dir, "Content", os.path.normpath(altermatic_rel_path))
        
        if workspace.is_altermatic_active and os.path.exists(altermatic_project_source_dir):
            extra_cook_paths.append(workspace.ue_altermatic_virtual_path)

        with GameIniCookContext(workspace, extra_paths=extra_cook_paths):
            print("Cooking Target Folders...", flush=True)
            had_cook_issues = run_and_stream([
                workspace.ue_cmd_path, 
                workspace.uproject_path, 
                "-run=cook", 
                "-targetplatform=Windows", 
                "-unversioned", 
                "-NoUI", 
                "-Map=/Engine/Maps/Entry"
            ])
            if had_cook_issues:
                print("COOK FAILED: Errors encountered during compile.", flush=True)
                sys.exit(1)
            else:
                print("COOK SUCCESS: Compilation completed successfully.", flush=True)

    # -------------------------------------------------------------
    # PHASE 3: PACK (Package only)
    # -------------------------------------------------------------
    if ACTION in ["cook", "full", "pack_only"]:
        # Auto-generate standalone custom Pal blueprints on the fly right before packaging! [6]
        if workspace.is_custom_pal:
            print(f"Custom Pal detected. Auto-generating patched standalone cooked blueprint...", flush=True)
            generate_cooked_actor_blueprint(
                settings, 
                workspace.monster_name, 
                workspace.template_id, 
                workspace.project_dir, 
                workspace.target_project_name
            )

        final_pak_path = workspace.output_pak_clean
        print(f"Preparing Pak (Target: {os.path.basename(final_pak_path)})...", flush=True)
        response_file = os.path.join(workspace.output_dir, "response.txt")

        folders_to_pack = resolve_packaging_manifest(workspace, workspace.has_anims)

        print("Building final PAK...", flush=True)
        files_found = pack_cooked_assets(
            workspace.unrealpak_path, 
            response_file, 
            final_pak_path, 
            folders_to_pack, 
            workspace.has_anims
        )
        
        if files_found == 0:
            print("ERROR: No files found to pack. Cook process might have failed.", flush=True)
            sys.exit(1)
            
        print(f"SUCCESS! Pak created at: {final_pak_path} ({files_found} files)", flush=True)
        for suffix in ["_err_P.pak", "_err_p.pak"]:
            err_pak = os.path.join(workspace.output_dir, f"{MONSTER_NAME}{suffix}")
            if os.path.exists(err_pak):
                try:
                    os.remove(err_pak)
                except OSError:
                    pass

        swap_json_dir = ""
        if workspace.palworld_exe and os.path.exists(workspace.palworld_exe):
            swap_json_dir = os.path.join(os.path.dirname(workspace.palworld_exe), "Pal", "Content", "Paks", "~Mods", "SwapJSON")
        
        if workspace.is_altermatic_active and swap_json_dir and os.path.exists(workspace.fmodel_altermatic_dir):
            from utils.altermatic_helper import compile_unified_altermatic_json
            success, msg = compile_unified_altermatic_json(workspace.monster_name, workspace.fmodel_altermatic_dir, swap_json_dir)
            print(msg, flush=True)

if __name__ == "__main__":
    main()