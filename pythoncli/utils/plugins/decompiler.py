import os
import sys
import time
import glob
import subprocess

def run_decompile_pipeline(ue_root: str, uproject_path: str, monster_name: str, fmodel_dir: str, ue_virtual_path: str, blender_path: str, verbose: bool = False, overwrite: bool = False):
    """Orchestrates the decompile process: remote UE export -> headless blender .blend generation."""
    project_name = os.path.splitext(os.path.basename(uproject_path))[0]
    
    sys.path.append(os.path.join(ue_root, "Engine", "Plugins", "Experimental", "PythonScriptPlugin", "Content", "Python"))
    try:
        import remote_execution  # type: ignore
    except ImportError:
        return False, "Could not locate remote_execution.py."

    remote_exec = remote_execution.RemoteExecution()
    remote_exec.start()
    
    node = None
    timeout = 10.0
    elapsed = 0.0
    while elapsed < timeout:
        node = next((n for n in remote_exec.remote_nodes if n.get('project_name', '').lower() == project_name.lower()), None)
        if node:
            break
        time.sleep(0.5)
        elapsed += 0.5
        
    if not node:
        remote_exec.stop()
        return False, "Unreal Editor is not running. Please open your project first."
        
    remote_exec.open_command_connection(node.get('node_id'))
    
    ue_export_script = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ue_export.py")).replace("\\", "/")
    
    cmd = (
        f'TARGET_FOLDER = r"{fmodel_dir}"; '
        f'UE_PATH = r"{ue_virtual_path}"; '
        f'OVERWRITE_ALL = {overwrite}; '
        f'exec(open(r"{ue_export_script}").read())'
    )
    
    print("Injecting decompiler command into Unreal Editor...")
    response = remote_exec.run_command(cmd)
    remote_exec.stop()

    if response is not None and not response.get('success'):
        return False, f"Export failed inside Unreal: {response.get('result')}"

    fbx_files = glob.glob(os.path.join(fmodel_dir, "*.fbx"))
    if not fbx_files:
        return False, "No FBX assets were exported by Unreal. Decompile aborted."

    fbx_file = fbx_files[0]
    blend_file = os.path.join(fmodel_dir, f"{monster_name}.blend")

    if not overwrite and os.path.exists(blend_file):
        print("Blend file already exists. Skipping reconstruction.")
        return True, "Decompile completed cleanly (skipped existing files)."

    reconstructor_script = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "utils", "blender_reconstruct.py"))
    
    print("Launching headless Blender to reconstruct .blend workspace...")
    cmd_args = [
        blender_path,
        "-b",
        "--python", reconstructor_script,
        "--",
        "--fbx", fbx_file,
        "--output", blend_file
    ]
    
    try:
        result = subprocess.run(
            cmd_args, 
            capture_output=True, 
            text=True, 
            encoding='utf-8', 
            errors='replace'
        )
        
        if os.path.exists(blend_file):
            return True, "Sources successfully reconstructed from compiled project assets!"
        else:
            error_details = result.stdout + "\n" + result.stderr
            return False, f"Blender executed but failed to save .blend file. Internal traceback:\n{error_details}"
    except Exception as e:
        return False, f"Failed to execute Blender process: {e}"