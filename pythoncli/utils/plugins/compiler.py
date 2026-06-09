# utils/plugins/compiler.py
import os
import subprocess
import shutil

def run_ubt_compilation(ue_root: str, uproject_path: str, verbose: bool = False) -> tuple[bool, str]:
    """
    Regenerates project files and compiles the C++ plugin.
    Supports both C++ and pure Blueprint-only projects automatically.
    """
    out_stream = None if verbose else subprocess.PIPE
    err_stream = None if verbose else subprocess.STDOUT

    project_dir = os.path.dirname(uproject_path)
    has_source_folder = os.path.exists(os.path.join(project_dir, "Source"))

    # --- Case A: Pure Blueprint-only Project (Use RunUAT BuildPlugin) ---
    if not has_source_folder:
        if verbose:
            print(">>> Blueprint-only project detected. Compiling C++ plugin via RunUAT BuildPlugin...", flush=True)
            
        run_uat = os.path.join(ue_root, "Engine", "Build", "BatchFiles", "RunUAT.bat")
        if not os.path.exists(run_uat):
            return False, f"Could not find RunUAT.bat at: {run_uat}"

        plugin_path = os.path.join(project_dir, "Plugins", "PalBakerEditorUtils", "PalBakerEditorUtils.uplugin")
        temp_build_dir = os.path.join(project_dir, "Intermediate", "PalBakerPluginBuild")

        # Clean old temporary build directory
        shutil.rmtree(temp_build_dir, ignore_errors=True)

        cmd = [
            run_uat, 
            "BuildPlugin", 
            f"-Plugin={plugin_path}", 
            f"-Package={temp_build_dir}", 
            "-Rocket", 
            "-TargetPlatforms=Win64"
        ]

        if verbose:
            print(f">>> Compiling Plugin using Command:\n{' '.join(cmd)}\n", flush=True)

        try:
            subprocess.run(cmd, check=True, stdout=out_stream, stderr=err_stream)
            
            # Copy compiled binaries back to the project's actual plugin folder
            compiled_binaries_src = os.path.join(temp_build_dir, "Binaries")
            compiled_binaries_dest = os.path.join(project_dir, "Plugins", "PalBakerEditorUtils", "Binaries")
            
            if os.path.exists(compiled_binaries_src):
                shutil.copytree(compiled_binaries_src, compiled_binaries_dest, dirs_exist_ok=True)
                
            # Clean up the temporary build directory
            shutil.rmtree(temp_build_dir, ignore_errors=True)
            return True, "Success"
        except subprocess.CalledProcessError as e:
            error_msg = "" if verbose else e.output.decode('utf-8', errors='replace')
            return False, f"RunUAT compilation failed with exit code {e.returncode}. {error_msg}"

    # --- Case B: C++ Project (Standard UBT / Build.bat compilation) ---
    ubt_exe = os.path.join(ue_root, "Engine", "Binaries", "DotNET", "UnrealBuildTool", "UnrealBuildTool.exe")
    if not os.path.exists(ubt_exe):
        return False, f"Could not find UnrealBuildTool.exe at: {ubt_exe}"

    # 1. Regenerate Project Files
    gen_cmd = [ubt_exe, "-projectfiles", f"-project={uproject_path}", "-game"]
    if verbose:
        print(">>> Regenerating project files...", flush=True)
    try:
        subprocess.run(gen_cmd, check=True, stdout=out_stream, stderr=err_stream)
    except subprocess.CalledProcessError as e:
        if not verbose:
            print(f"Project generation warning (Exit code: {e.returncode}).", flush=True)

    # 2. Compile the Project
    build_bat = os.path.join(ue_root, "Engine", "Build", "BatchFiles", "Build.bat")
    project_name = os.path.splitext(os.path.basename(uproject_path))[0]
    cmd = [build_bat, f"{project_name}Editor", "Win64", "Development", f"-Project={uproject_path}", "-WaitMutex"]

    if verbose:
        print(f">>> Compiling Plugin using Command:\n{' '.join(cmd)}\n", flush=True)
    try:
        subprocess.run(cmd, check=True, stdout=out_stream, stderr=err_stream)
        return True, "Success"
    except subprocess.CalledProcessError as e:
        error_msg = "" if verbose else e.output.decode('utf-8', errors='replace')
        return False, f"Compilation failed with exit code {e.returncode}. {error_msg}"