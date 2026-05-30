import os
import sys
import glob
import json
import shutil
from utils.builder.config_helper import inject_packaging_settings
from utils.builder.blender_helper import run_headless_blender
from utils.builder.unreal_helper import run_remote_import
from utils.builder.cooker_helper import run_and_stream, pack_cooked_assets
from utils.state import save_push_state  # ADDED: Fix save_push_state NameError

# Force standard output stream to use UTF-8. 
# This completely prevents "UnicodeEncodeError: 'charmap' codec can't encode characters" crashes in Windows terminals.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

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

    FMODEL_ROOT = settings.get("fmodel_output", "")
    UE_ROOT = settings.get("ue_root", "")
    UPROJECT_PATH = settings.get("uproject", "")
    BLENDER_PATH = settings.get("blender", "blender")
    PW_EXE = settings.get("palworld_exe", "")

    # Path Computations
    UE_CMD_PATH = os.path.join(UE_ROOT, "Engine", "Binaries", "Win64", "UnrealEditor-Cmd.exe")
    UNREALPAK_PATH = os.path.join(UE_ROOT, "Engine", "Binaries", "Win64", "UnrealPak.exe")

    # Absolute paths
    FMODEL_DIR = os.path.join(FMODEL_ROOT, "Exports", "Pal", "Content", "Pal", "Model", "Character", CATEGORY, MONSTER_NAME)
    UE_VIRTUAL_PATH = f"/Game/Pal/Model/Character/{CATEGORY}/{MONSTER_NAME}"
    SKELETON_VIRTUAL_PATH = f"/Game/Pal/Model/Character/Skeleton/{MONSTER_NAME}"
    ANIMS_VIRTUAL_PATH = f"/Game/Pal/Animation/Character/Monster/{MONSTER_NAME}"
    ICON_VIRTUAL_PATH = "/Game/Pal/Texture/PalIcon/Normal"
    ICON_FMODEL_PATH = os.path.join(FMODEL_ROOT, "Exports", "Pal", "Content", "Pal", "Texture", "PalIcon", "Normal", f"T_{MONSTER_NAME}_icon_normal.png")
    HAS_ICON = os.path.exists(ICON_FMODEL_PATH)


    project_dir = os.path.dirname(UPROJECT_PATH)
    target_project_name = os.path.splitext(os.path.basename(UPROJECT_PATH))[0]
    
    # Ensure project config directory is initialized
    config_dir = os.path.join(project_dir, "Config")
    os.makedirs(config_dir, exist_ok=True)
    ini_path = os.path.join(config_dir, "DefaultGame.ini")
    
    # FIX: Use unique PalBaker backup extension
    ini_backup = os.path.join(config_dir, "DefaultGame.ini.palbaker.bak")

    # Detect animations in project
    anims_source_dir = os.path.join(project_dir, "Content", "Pal", "Animation", "Character", "Monster", MONSTER_NAME)
    has_anims = os.path.exists(anims_source_dir)

    # Output directory resolution
    output_dir = FMODEL_DIR if os.path.exists(FMODEL_DIR) else project_dir
    if PW_EXE and os.path.exists(PW_EXE):
        output_dir = os.path.join(os.path.dirname(PW_EXE), "Pal", "Content", "Paks", "palBaker")
        os.makedirs(output_dir, exist_ok=True)
        
    # Configure both clean and error-flagged pak targets
    output_pak_clean = os.path.join(output_dir, f"{MONSTER_NAME}_P.pak")
    output_pak_err = os.path.join(output_dir, f"{MONSTER_NAME}_err_P.pak")


    # -------------------------------------------------------------
    # PHASE 0: RAW FMODEL DECOMPILE (Create .blend file)
    # -------------------------------------------------------------
    if ACTION == "create_blend":
        psk_files = glob.glob(os.path.join(FMODEL_DIR, "*.psk"))
        if not psk_files:
            print("ERROR: No .psk skeletal mesh found in FModel directory.", flush=True)
            sys.exit(1)
            
        psk_file = psk_files[0]
        blend_file = os.path.join(FMODEL_DIR, f"{MONSTER_NAME}.blend")
        reconstructor_script = os.path.join(os.path.dirname(__file__), "utils", "blender_reconstruct.py")
        
        psk_file_clean = psk_file.replace("\\", "/")
        blend_file_clean = blend_file.replace("\\", "/")
        
        # NEW: Intercept raw files, resolve/copy shared texture files, and produce the metadata mapping
        from utils.fmodel_helper import preprocess_fmodel_textures
        preprocess_fmodel_textures(FMODEL_DIR, FMODEL_ROOT)
        
        print("Launching headless Blender to reconstruct .blend workspace from .psk...", flush=True)
        result = run_headless_blender(
            BLENDER_PATH, 
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
        if not os.path.exists(FMODEL_DIR):
            print(f"ERROR: Cannot push. FModel directory not found at {FMODEL_DIR}")
            sys.exit(1)

        blend_files = glob.glob(os.path.join(FMODEL_DIR, "*.blend"))
        fbx_file = ""
        if blend_files:
            blend_file = blend_files[0]
            fbx_file = os.path.join(FMODEL_DIR, f"{MONSTER_NAME}.fbx")
            
            extractor_script = os.path.join(os.path.dirname(__file__), "utils", "blender_extractor.py")
            output_json = os.path.join(FMODEL_DIR, "bone_data.json")
            
            print("Running headless Blender (Extracting Rigging & Exporting FBX)...", flush=True)
            run_headless_blender(BLENDER_PATH, blend_file, extractor_script, ["--output", output_json, "--fbx", fbx_file])

        pngs = glob.glob(os.path.join(FMODEL_DIR, "*.png"))
        jsons = glob.glob(os.path.join(FMODEL_DIR, "MI_*.json"))
        
        config = {
            "ue_target_path": UE_VIRTUAL_PATH,
            "textures": pngs,
            "fbx_file": fbx_file if os.path.exists(fbx_file) else None,
            "mi_jsons": jsons,
            "icon_file": ICON_FMODEL_PATH if HAS_ICON else None  # Pass icon specifically
        }
        config_path = os.path.join(FMODEL_DIR, "import_config.json")
        with open(config_path, "w") as f:
            json.dump(config, f)

        # FIXED: Call the modularized remote execution import library
        print("Connecting to Open Unreal Engine...", flush=True)
        ue_import_script = os.path.join(os.path.dirname(__file__), "ue_import.py")
        success, log_msg = run_remote_import(UE_ROOT, target_project_name, FMODEL_DIR, ue_import_script)
        
        if log_msg.strip():
            print(log_msg, flush=True)
            
        if not success:
            print("!!! ERROR INSIDE UNREAL ENGINE !!!", flush=True)
            sys.exit(1)

        ue_abs_path = os.path.join(project_dir, "Content", "Pal", "Model", "Character", CATEGORY, MONSTER_NAME)
        save_push_state(FMODEL_DIR, ue_abs_path)

    # -------------------------------------------------------------
    # PHASE 2: COOK & PACK
    # -------------------------------------------------------------
    if ACTION in ["cook", "full"]:
        if ACTION == "cook":
            # Wipe both possible paks before cooking
            for p in [output_pak_clean, output_pak_err]:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        print(f"CRITICAL ERROR: Cannot overwrite '{os.path.basename(p)}'. Close the game!")
                        sys.exit(1)


        # FIX: Check and restore any stranded backup before backing up again
        from utils.builder.config_helper import restore_palbaker_backup
        restore_palbaker_backup(UPROJECT_PATH)

        rel_ue_path = UE_VIRTUAL_PATH.replace("/Game/", "").replace("/", os.sep)
        cooked_dir = os.path.join(project_dir, "Saved", "Cooked", "Windows", target_project_name, "Content", rel_ue_path)
        
        rel_skel_path = SKELETON_VIRTUAL_PATH.replace("/Game/", "").replace("/", os.sep)
        cooked_skel_dir = os.path.join(project_dir, "Saved", "Cooked", "Windows", target_project_name, "Content", rel_skel_path)

        rel_anims_path = ANIMS_VIRTUAL_PATH.replace("/Game/", "").replace("/", os.sep)
        cooked_anims_dir = os.path.join(project_dir, "Saved", "Cooked", "Windows", target_project_name, "Content", rel_anims_path)
        
        if os.path.exists(cooked_dir): shutil.rmtree(cooked_dir, ignore_errors=True)
        if os.path.exists(cooked_skel_dir): shutil.rmtree(cooked_skel_dir, ignore_errors=True)
        if os.path.exists(cooked_anims_dir): shutil.rmtree(cooked_anims_dir, ignore_errors=True)

        # Check for custom cartoon cel shader dependency inside Content directory
        custom_shader_raw = os.path.join(project_dir, "Content", "CartoonCelShader", "Materials", "CelShader")
        has_custom_shader = os.path.exists(custom_shader_raw)
        extra_cook_paths = []
        if has_custom_shader:
            extra_cook_paths.append("/Game/CartoonCelShader/Materials/CelShader")

        if HAS_ICON:
            extra_cook_paths.append(ICON_VIRTUAL_PATH)


        if os.path.exists(ini_path): 
            shutil.copy2(ini_path, ini_backup)
            inject_packaging_settings(
                ini_path, 
                UE_VIRTUAL_PATH, 
                SKELETON_VIRTUAL_PATH, 
                ANIMS_VIRTUAL_PATH, 
                has_anims,
                extra_paths=extra_cook_paths
            )

        try:
            print("Cooking Target Folders...", flush=True)
            # Run cooker and capture warning/error flags from stdout
            had_cook_issues = run_and_stream([UE_CMD_PATH, UPROJECT_PATH, "-run=cook", "-targetplatform=Windows", "-unversioned", "-NoUI", "-Map=/Engine/Maps/Entry"])

            # Dynamically map the target file name
            final_pak_path = output_pak_err if had_cook_issues else output_pak_clean
            print(f"Preparing Pak (Target: {os.path.basename(final_pak_path)})...", flush=True)
            response_file = os.path.join(output_dir, "response.txt")

            
            folders_to_pack = [
                (cooked_dir, UE_VIRTUAL_PATH.replace("/Game/", "")),
                (cooked_skel_dir, SKELETON_VIRTUAL_PATH.replace("/Game/", ""))
            ]
            
            if has_anims:
                folders_to_pack.append((cooked_anims_dir, ANIMS_VIRTUAL_PATH.replace("/Game/", "")))
                print("  -> Custom animations detected: Shipping complete Skeleton, Animation, and BP assets.", flush=True)
            else:
                print("  -> No custom animations: Shipping BP assets, but stripping Skeleton asset to prevent ragdoll glitches.", flush=True)

            if has_custom_shader:
                custom_shader_cooked = os.path.join(project_dir, "Saved", "Cooked", "Windows", target_project_name, "Content", "CartoonCelShader", "Materials", "CelShader")
                folders_to_pack.append((custom_shader_cooked, "CartoonCelShader/Materials/CelShader"))
                print("  -> Custom Cartoon Cel Shader detected: Packing shader dependencies.", flush=True)

            if HAS_ICON:
                # Find all cooked parts of the specific icon file (uasset, uexp, etc.)
                icon_cooked_base = os.path.join(project_dir, "Saved", "Cooked", "Windows", target_project_name, "Content", "Pal", "Texture", "PalIcon", "Normal", f"T_{MONSTER_NAME}_icon_normal")
                
                icon_parts_found = False
                for ext in [".uasset", ".uexp", ".ubulk"]:
                    cooked_file = icon_cooked_base + ext
                    if os.path.exists(cooked_file):
                        # Construct its precise virtual destination path
                        virtual_file = f"Pal/Texture/PalIcon/Normal/T_{MONSTER_NAME}_icon_normal{ext}"
                        folders_to_pack.append((cooked_file, virtual_file))
                        icon_parts_found = True
                
                if icon_parts_found:
                    print(f"  -> Custom Icon detected: Packing only {MONSTER_NAME} icon files.", flush=True)


            print(f"Building final PAK...", flush=True)
            files_found = pack_cooked_assets(UNREALPAK_PATH, response_file, final_pak_path, folders_to_pack, has_anims)
            
            if files_found == 0:
                print("ERROR: No files found to pack. Cook process might have failed.", flush=True)
                sys.exit(1)
                
            print(f"SUCCESS! Pak created at: {final_pak_path} ({files_found} files)", flush=True)
            for suffix in ["_err_P.pak", "_err_p.pak"]:
                err_pak = os.path.join(output_dir, f"{MONSTER_NAME}{suffix}")
                if os.path.exists(err_pak):
                    try:
                        os.remove(err_pak)
                        print(f"Cleaned up legacy error pak: {os.path.basename(err_pak)}", flush=True)
                    except OSError as e:
                        print(f"Warning: Failed to delete legacy error pak {err_pak}: {e}", flush=True)



        finally:
            if os.path.exists(ini_backup):
                shutil.move(ini_backup, ini_path)

if __name__ == "__main__":
    main()