import os
import sys
import json
import subprocess
import glob
import shutil

def setup_and_compile_plugin(ue_root: str, uproject_path: str, verbose: bool = False, force_recompile: bool = False):
    """Copies the C++ plugin files from the repo, generates project files, and compiles the DLL."""
    if not ue_root or not uproject_path:
        return False, "Unreal Engine Root or UProject path is missing."

    project_dir = os.path.dirname(uproject_path)
    dest_plugin_dir = os.path.join(project_dir, "Plugins", "PalBakerEditorUtils")
    dll_dir = os.path.join(dest_plugin_dir, "Binaries", "Win64")
    dlls_found = glob.glob(os.path.join(dll_dir, "UnrealEditor-PalBakerEditorUtils*.dll"))

    if not force_recompile and os.path.exists(dest_plugin_dir) and len(dlls_found) > 0:
        return True, "Plugin already installed and compiled."

    # Locate the source plugin in the PalBaker repository
    src_plugin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugins", "PalBakerEditorUtils"))
    
    if not os.path.exists(src_plugin_dir):
        return False, f"Source plugin directory not found at: {src_plugin_dir}"

    # Copy the plugin files over
    if verbose:
        print(f">>> Copying plugin from repository to: {dest_plugin_dir}")
    shutil.copytree(src_plugin_dir, dest_plugin_dir, dirs_exist_ok=True)

    out_stream = None if verbose else subprocess.PIPE
    err_stream = None if verbose else subprocess.STDOUT

    ubt_exe = os.path.join(ue_root, "Engine", "Binaries", "DotNET", "UnrealBuildTool", "UnrealBuildTool.exe")
    
    if not os.path.exists(ubt_exe):
        return False, f"Could not find UnrealBuildTool.exe at: {ubt_exe}"

    gen_cmd = [
        ubt_exe,
        "-projectfiles",
        f"-project={uproject_path}",
        "-game"
    ]
    
    if verbose:
        print(">>> Regenerating project files to register the new plugin...")
        
    try:
        subprocess.run(gen_cmd, check=True, stdout=out_stream, stderr=err_stream)
    except subprocess.CalledProcessError as e:
        if not verbose:
            print(f"Project generation output: {e.output.decode('utf-8', errors='replace')}")

    build_bat = os.path.join(ue_root, "Engine", "Build", "BatchFiles", "Build.bat")
    project_name = os.path.splitext(os.path.basename(uproject_path))[0]

    cmd = [
        build_bat,
        f"{project_name}Editor",
        "Win64",
        "Development",
        f"-Project={uproject_path}",
        "-WaitMutex"
    ]

    if verbose:
        print(f">>> Compiling Plugin using Command:\n{' '.join(cmd)}\n")

    try:
        subprocess.run(cmd, check=True, stdout=out_stream, stderr=err_stream)
        
        updated_dlls = glob.glob(os.path.join(dll_dir, "UnrealEditor-PalBakerEditorUtils*.dll"))
        if len(updated_dlls) > 0:
            return True, "C++ Plugin successfully compiled and installed!"
        else:
            return False, "UBT completed successfully, but the compiled DLL was not found."
    except subprocess.CalledProcessError as e:
        if not verbose:
            error_msg = e.output.decode('utf-8', errors='replace')
        else:
            error_msg = f"Compilation process exited with code {e.returncode}."
        return False, f"Compilation Failed: {error_msg}"

if __name__ == "__main__":
    settings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "manager_settings.json"))
    
    if not os.path.exists(settings_path):
        print(f"ERROR: Could not find settings file at {settings_path}")
        print("Please open the PalBaker UI, configure your paths, and click Save first.")
        input("Press Enter to exit...")
        sys.exit(1)
        
    with open(settings_path, "r") as f:
        settings = json.load(f)
        
    ue_root_path = settings.get("ue_root", "")
    uproject_file = settings.get("uproject", "")
    
    print("=== PalBaker C++ Plugin Setup (Standalone) ===")
    print(f"Loaded UE Root: {ue_root_path}")
    print(f"Loaded UProject:  {uproject_file}")
    print("-" * 60)
    
    is_success, final_msg = setup_and_compile_plugin(ue_root_path, uproject_file, verbose=True, force_recompile=True)
    
    print("-" * 60)
    print("RESULT:")
    print(final_msg)
    print("-" * 60)
    input("Press Enter to exit...")