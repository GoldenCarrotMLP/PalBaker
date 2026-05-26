import os
import sys
import glob
import json
import subprocess
import time
import shutil

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
UE_PYTHON_DIR = os.path.join(UE_ROOT, "Engine", "Plugins", "Experimental", "PythonScriptPlugin", "Content", "Python")

# Absolute paths
FMODEL_DIR = os.path.join(FMODEL_ROOT, "Exports", "Pal", "Content", "Pal", "Model", "Character", CATEGORY, MONSTER_NAME)
UE_VIRTUAL_PATH = f"/Game/Pal/Model/Character/{CATEGORY}/{MONSTER_NAME}"
SKELETON_VIRTUAL_PATH = f"/Game/Pal/Model/Character/Skeleton/{MONSTER_NAME}"

sys.path.append(UE_PYTHON_DIR)
try:
    import remote_execution
except ImportError:
    print(f"ERROR: Could not find remote_execution.py in {UE_PYTHON_DIR}")
    sys.exit(1)

try:
    from utils.state import save_push_state
except ImportError:
    sys.path.append(os.path.dirname(__file__))
    from utils.state import save_push_state

def run_and_stream(cmd_args):
    """Executes a command and streams its output in absolute real-time to stdout."""
    process = subprocess.Popen(
        cmd_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1 # Line-buffered
    )
    if process.stdout:
        for line in iter(process.stdout.readline, ''):
            if not line: break
            # Force immediate console flush so the Flet UI captures it
            print(line.strip(), flush=True) 
            
    process.wait()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd_args)

def inject_packaging_settings(ini_path):
    if not os.path.exists(ini_path):
        return
    with open(ini_path, "r", encoding="utf-8-sig", errors="replace") as f:
        lines = f.readlines()
        
    new_lines = []
    in_section = False
    section_found = False
    section_header = "[/Script/UnrealEd.ProjectPackagingSettings]"
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if stripped.lower() == section_header.lower():
                in_section = True
                section_found = True
                new_lines.append(line)
                new_lines.append("bCookAll=False\n")
                new_lines.append(f'+DirectoriesToAlwaysCook=(Path="{UE_VIRTUAL_PATH}")\n')
                new_lines.append(f'+DirectoriesToAlwaysCook=(Path="{SKELETON_VIRTUAL_PATH}")\n')
                new_lines.append("MapsToCook=\n")
                continue
            else:
                in_section = False
                
        if in_section:
            if any(stripped.startswith(k) for k in ["DirectoriesToAlwaysCook", "+DirectoriesToAlwaysCook", "-DirectoriesToAlwaysCook", "bCookAll", "MapsToCook", "+MapsToCook", "-MapsToCook"]):
                continue
        new_lines.append(line)
        
    if not section_found:
        new_lines.append("\n" + section_header + "\n")
        new_lines.append("bCookAll=False\n")
        new_lines.append(f'+DirectoriesToAlwaysCook=(Path="{UE_VIRTUAL_PATH}")\n')
        new_lines.append(f'+DirectoriesToAlwaysCook=(Path="{SKELETON_VIRTUAL_PATH}")\n')
        
    with open(ini_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

def main():
    project_dir = os.path.dirname(UPROJECT_PATH)
    target_project_name = os.path.splitext(os.path.basename(UPROJECT_PATH))[0]
    ini_path = os.path.join(project_dir, "Config", "DefaultGame.ini")
    ini_backup = os.path.join(project_dir, "Config", "DefaultGame.ini.bak")

    # Determine Output directory
    output_dir = FMODEL_DIR if os.path.exists(FMODEL_DIR) else project_dir
    if PW_EXE and os.path.exists(PW_EXE):
        output_dir = os.path.join(os.path.dirname(PW_EXE), "Pal", "Content", "Paks", "palBaker")
        os.makedirs(output_dir, exist_ok=True)
        
    output_pak = os.path.join(output_dir, f"{MONSTER_NAME}_P.pak")

    if ACTION in ["cook", "full"]:
        if os.path.exists(output_pak):
            try:
                os.remove(output_pak)
            except OSError:
                print(f"CRITICAL ERROR: Cannot overwrite '{output_pak}'. Close the game!")
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
            print("Running headless Blender...", flush=True)
            
            blender_export_script = (
                f"import bpy; "
                f"bpy.ops.export_scene.fbx("
                f"filepath=r'{fbx_file}', "
                f"use_selection=False, "
                f"add_leaf_bones=False, "
                f"mesh_smooth_type='FACE', "
                f"armature_nodetype='ROOT', "
                f"global_scale=0.01, "
                f"apply_scale_options='FBX_SCALE_ALL')"
            )
            subprocess.run([BLENDER_PATH, "-b", blend_file, "--python-expr", blender_export_script], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        pngs = glob.glob(os.path.join(FMODEL_DIR, "*.png"))
        jsons = glob.glob(os.path.join(FMODEL_DIR, "MI_*.json"))
        
        config = {
            "ue_target_path": UE_VIRTUAL_PATH,
            "textures": pngs,
            "fbx_file": fbx_file if os.path.exists(fbx_file) else None,
            "mi_jsons": jsons
        }
        config_path = os.path.join(FMODEL_DIR, "import_config.json")
        with open(config_path, "w") as f:
            json.dump(config, f)

        print("Connecting to Open Unreal Engine...", flush=True)
        remote_exec = remote_execution.RemoteExecution()
        remote_exec.start()
        time.sleep(2.0)
        
        node = next((n for n in remote_exec.remote_nodes if n.get('project_name', '').lower() == target_project_name.lower()), None)
        if not node:
            print("ERROR: Unreal Editor is not running. Please open it first!")
            sys.exit(1)
            
        remote_exec.open_command_connection(node.get('node_id'))
        
        ue_script_path = os.path.join(os.path.dirname(__file__), "ue_import.py").replace("\\", "/")
        print("Injecting import commands...", flush=True)
        
        cmd = f'TARGET_FOLDER = r"{FMODEL_DIR}"; exec(open(r"{ue_script_path}").read())'
        response = remote_exec.run_command(cmd)
        remote_exec.stop()

        if response is not None:
            if response.get('output'):
                for log_entry in response['output']:
                    log_text = log_entry.get('output', '') if isinstance(log_entry, dict) else str(log_entry)
                    if log_text.strip():
                        print(log_text.rstrip(), flush=True)

            if not response.get('success'):
                print("!!! ERROR INSIDE UNREAL ENGINE !!!", flush=True)
                print(response.get('result'), flush=True)
                sys.exit(1)
        else:
            print("ERROR: No response received from Unreal Engine remote execution. Check if the editor is frozen.", flush=True)
            sys.exit(1)

        ue_abs_path = os.path.join(project_dir, "Content", "Pal", "Model", "Character", CATEGORY, MONSTER_NAME)
        save_push_state(FMODEL_DIR, ue_abs_path)

    # -------------------------------------------------------------
    # PHASE 2: COOK & PACK
    # -------------------------------------------------------------
    if ACTION in ["cook", "full"]:
        rel_ue_path = UE_VIRTUAL_PATH.replace("/Game/", "").replace("/", os.sep)
        cooked_dir = os.path.join(project_dir, "Saved", "Cooked", "Windows", "Pal", "Content", rel_ue_path)
        
        rel_skel_path = SKELETON_VIRTUAL_PATH.replace("/Game/", "").replace("/", os.sep)
        cooked_skel_dir = os.path.join(project_dir, "Saved", "Cooked", "Windows", "Pal", "Content", rel_skel_path)
        
        if os.path.exists(cooked_dir): shutil.rmtree(cooked_dir, ignore_errors=True)
        if os.path.exists(cooked_skel_dir): shutil.rmtree(cooked_skel_dir, ignore_errors=True)

        if os.path.exists(ini_path): 
            shutil.copy2(ini_path, ini_backup)
            inject_packaging_settings(ini_path)

        try:
            print("Cooking Target Folders...", flush=True)
            # FIXED: Streams the Unreal Cook logs in absolute real-time without buffering
            run_and_stream([UE_CMD_PATH, UPROJECT_PATH, "-run=cook", "-targetplatform=Windows", "-unversioned", "-NoUI", "-Map=/Engine/Maps/Entry"])

            print("Preparing Pak (Filtering out Skeleton and Physics)...", flush=True)
            response_file = os.path.join(output_dir, "response.txt")
            folders_to_pack = [(cooked_dir, UE_VIRTUAL_PATH.replace("/Game/", "")), (cooked_skel_dir, SKELETON_VIRTUAL_PATH.replace("/Game/", ""))]
            files_found = 0
            
            with open(response_file, "w") as f:
                for c_dir, v_path in folders_to_pack:
                    if os.path.exists(c_dir):
                        for root, dirs, files in os.walk(c_dir):
                            for file in files:
                                if file.endswith((".uasset", ".uexp", ".ubulk")):
                                    if "PhysicsAsset" in file or "Skeleton" in file:
                                        continue
                                    abs_path = os.path.join(root, file)
                                    rel_to_cooked = os.path.relpath(abs_path, c_dir)
                                    rel_virtual = "../../../Pal/Content/" + v_path + "/" + rel_to_cooked.replace("\\", "/")
                                    f.write(f'"{abs_path}" "{rel_virtual}"\n')
                                    files_found += 1
                                    
            if files_found == 0:
                print("ERROR: No files found to pack. Cook process might have failed.", flush=True)
                sys.exit(1)

            print(f"Building final PAK ({files_found} files)...", flush=True)
            # FIXED: Streams the UnrealPak log in absolute real-time
            run_and_stream([UNREALPAK_PATH, output_pak, f"-Create={response_file}"])
            print(f"SUCCESS! Pak created at: {output_pak}", flush=True)

        finally:
            if os.path.exists(ini_backup):
                shutil.move(ini_backup, ini_path)

if __name__ == "__main__":
    main()