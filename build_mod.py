# build_mod.py
import os
import sys
import glob
import json
from utils.builder.workspace import ModWorkspace
from utils.builder.config_helper import restore_palbaker_backup, GameIniCookContext
from utils.builder.blender_helper import run_headless_blender
from utils.builder.unreal_helper import run_remote_import
from utils.builder.cooker_helper import clean_cook_environment, resolve_packaging_manifest, run_and_stream, pack_cooked_assets
from utils.state import save_push_state

# Dynamic stream check to prevent static type stub AttributeAccess errors in Pylance
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding='utf-8')

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

    # 1. Resolve all path context via the workspace resolver
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
        if not os.path.exists(workspace.fmodel_dir):
            print(f"ERROR: Cannot push. FModel directory not found at {workspace.fmodel_dir}")
            sys.exit(1)

        blend_files = glob.glob(os.path.join(workspace.fmodel_dir, "*.blend"))
        fbx_file = ""
        if blend_files:
            blend_file = blend_files[0]
            fbx_file = os.path.join(workspace.fmodel_dir, f"{MONSTER_NAME}.fbx")
            
            extractor_script = os.path.join(os.path.dirname(__file__), "utils", "blender_extractor.py")
            output_json = os.path.join(workspace.fmodel_dir, "bone_data.json")
            
            print("Running headless Blender (Extracting Rigging & Exporting FBX)...", flush=True)
            run_headless_blender(workspace.blender_path, blend_file, extractor_script, ["--output", output_json, "--fbx", fbx_file])

        pngs = glob.glob(os.path.join(workspace.fmodel_dir, "*.png"))
        jsons = glob.glob(os.path.join(workspace.fmodel_dir, "MI_*.json"))
        
        config = {
            "ue_target_path": workspace.ue_virtual_path,
            "textures": pngs,
            "fbx_file": fbx_file if os.path.exists(fbx_file) else None,
            "mi_jsons": jsons,
            "icon_file": workspace.icon_fmodel_path if workspace.has_icon else None
        }
        config_path = os.path.join(workspace.fmodel_dir, "import_config.json")
        with open(config_path, "w") as f:
            json.dump(config, f)

        print("Connecting to Open Unreal Engine...", flush=True)
        ue_import_script = os.path.join(os.path.dirname(__file__), "ue_import.py")
        success, log_msg = run_remote_import(workspace.ue_root, workspace.target_project_name, workspace.fmodel_dir, ue_import_script)
        
        if log_msg.strip():
            print(log_msg, flush=True)
            
        if not success:
            print("!!! ERROR INSIDE UNREAL ENGINE !!!", flush=True)
            sys.exit(1)

        ue_abs_path = os.path.join(workspace.project_dir, "Content", "Pal", "Model", "Character", CATEGORY, MONSTER_NAME)
        save_push_state(workspace.fmodel_dir, ue_abs_path)

    # -------------------------------------------------------------
    # PHASE 2: COOK & PACK
    # -------------------------------------------------------------
    if ACTION in ["cook", "full"]:
        # Resolve automatic self-healing before compiling
        restore_palbaker_backup(workspace.uproject_path)

        # 2. Cleanup the old build caches
        clean_cook_environment(workspace)

        extra_cook_paths = []
        if workspace.has_custom_shader:
            extra_cook_paths.append("/Game/CartoonCelShader/Materials/CelShader")
        if workspace.has_icon:
            extra_cook_paths.append(workspace.icon_virtual_path)
        extra_cook_paths.append(workspace.blueprint_virtual_path)

        # 3. Use the Context Manager to handle DefaultGame.ini backup & safety automatically
        with GameIniCookContext(workspace, extra_paths=extra_cook_paths):
            print("Cooking Target Folders...", flush=True)
            had_cook_issues = run_and_stream([
                workspace.ue_cmd_path, 
                workspace.uproject_path, 
                "-run=cook", 
                "-targetplatform=Windows", 
                #"-unversioned", 
                "-NoUI", 
                "-Map=/Engine/Maps/Entry"
            ])

            final_pak_path = workspace.output_pak_err if had_cook_issues else workspace.output_pak_clean
            print(f"Preparing Pak (Target: {os.path.basename(final_pak_path)})...", flush=True)
            response_file = os.path.join(workspace.output_dir, "response.txt")

            # 4. Resolve the complete packaging list (including custom audio overrides)
            folders_to_pack = resolve_packaging_manifest(workspace, workspace.has_anims)

            # 5. Pack the archive
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
            if not had_cook_issues:
                print(f"SUCCESS! Pak created at: {final_pak_path} ({files_found} files)", flush=True)
                for suffix in ["_err_P.pak", "_err_p.pak"]:
                    err_pak = os.path.join(workspace.output_dir, f"{MONSTER_NAME}{suffix}")
                    if os.path.exists(err_pak):
                        try:
                            os.remove(err_pak)
                            print(f"Cleaned up legacy error pak: {os.path.basename(err_pak)}", flush=True)
                        except OSError as e:
                            print(f"Warning: Failed to delete legacy error pak {err_pak}: {e}", flush=True)

if __name__ == "__main__":
    main()