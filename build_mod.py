# build_mod.py
import os
import sys
import glob
import json
import subprocess
from utils.builder.workspace import ModWorkspace
from utils.builder.config_helper import restore_palbaker_backup, GameIniCookContext
from utils.builder.blender_helper import run_headless_blender
from utils.builder.unreal_helper import run_remote_import
from utils.builder.cooker_helper import clean_cook_environment, resolve_packaging_manifest, run_and_stream, pack_cooked_assets
from utils.state import save_push_state

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
        import_targets = []
        if os.path.exists(workspace.fmodel_dir):
            import_targets.append((workspace.fmodel_dir, workspace.ue_virtual_path))
            
        # Strictly append Altermatic assets only if the Switch is toggled ON
        if workspace.is_altermatic_active and os.path.exists(workspace.fmodel_altermatic_dir) and any(f.endswith(".blend") for f in os.listdir(workspace.fmodel_altermatic_dir)):
            import_targets.append((workspace.fmodel_altermatic_dir, workspace.ue_altermatic_virtual_path))

        if not import_targets:
            print("ERROR: No raw model sources found in workspaces to push.", flush=True)
            sys.exit(1)

        # Pre-Push layout sync using master sync routine
        from utils.altermatic_helper import sync_sidecar_metadata
        for target_dir, _ in import_targets:
            for blend_file in glob.glob(os.path.join(target_dir, "*.blend")):
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

            # Now build the import_config.json for this specific directory
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
                "bone_data_file": f"{base_mesh_name}_blend.json"
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

        ue_abs_path = os.path.join(workspace.project_dir, "Content", "Pal", "Model", "Character", "Monster", MONSTER_NAME)
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
            
            cmd = [
                workspace.blender_path,
                "-b",
                blend_file,
                "--addons", "bl_ext.blender_org.io_scene_psk_psa,bl_ext.user_default.io_scene_psk_psa,io_scene_psk_psa,io_import_scene_unreal_psa_psk",
                "--python", extractor_script,
                "--",
                "--output", output_json
            ]
            subprocess.run(cmd)
            
        print("SUCCESS! Staged layout sync completed.", flush=True)

    # -------------------------------------------------------------
    # PHASE 2: COOK & PACK
    # -------------------------------------------------------------
    if ACTION in ["cook", "full"]:
        restore_palbaker_backup(workspace.uproject_path)
        clean_cook_environment(workspace)

        extra_cook_paths = []
        if workspace.has_custom_shader:
            extra_cook_paths.append("/Game/CartoonCelShader/Materials/CelShader")
        if workspace.has_icon:
            extra_cook_paths.append(workspace.icon_virtual_path)
        extra_cook_paths.append(workspace.blueprint_virtual_path)

        # Dynamic multi-path cook inclusion
        altermatic_project_source_dir = os.path.join(workspace.project_dir, "Content", "Palbaker", "Model", "Character", "Monster", workspace.monster_name)
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

            final_pak_path = workspace.output_pak_err if had_cook_issues else workspace.output_pak_clean
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
                
            if not had_cook_issues:
                print(f"SUCCESS! Pak created at: {final_pak_path} ({files_found} files)", flush=True)
                for suffix in ["_err_P.pak", "_err_p.pak"]:
                    err_pak = os.path.join(workspace.output_dir, f"{MONSTER_NAME}{suffix}")
                    if os.path.exists(err_pak):
                        try:
                            os.remove(err_pak)
                        except OSError:
                            pass

                # Compile and deploy Altermatic JSON config to SwapJSON folder
                swap_json_dir = ""
                if workspace.palworld_exe and os.path.exists(workspace.palworld_exe):
                    swap_json_dir = os.path.join(os.path.dirname(workspace.palworld_exe), "Pal", "Content", "Paks", "~Mods", "SwapJSON")
                
                if workspace.is_altermatic_active and swap_json_dir and os.path.exists(workspace.fmodel_altermatic_dir):
                    from utils.altermatic_helper import compile_unified_altermatic_json
                    success, msg = compile_unified_altermatic_json(workspace.monster_name, workspace.fmodel_altermatic_dir, swap_json_dir)
                    print(msg, flush=True)

if __name__ == "__main__":
    main()