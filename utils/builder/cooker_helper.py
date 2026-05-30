import os
import shutil
import subprocess

def run_and_stream(cmd_args) -> bool:
    """
    Executes a command, streams output in real-time, and returns True 
    if 'Warning:' or 'Error:' was printed in stdout, False otherwise.
    """
    process = subprocess.Popen(
        cmd_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1  # Line-buffered
    )
    
    had_issues = False
    if process.stdout:
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            stripped = line.strip()
            print(stripped, flush=True) 
            
            # Scan for issues
            line_lower = stripped.lower()
            if "error:" in line_lower or "warning:" in line_lower:
                had_issues = True
            
    process.wait()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd_args)
        
    return had_issues


def pack_cooked_assets(unrealpak_path: str, response_file: str, output_pak: str, folders_to_pack: list, has_anims: bool) -> int:
    """
    Creates the response file for UnrealPak and executes the packaging.
    Supports both Directory-level and File-level packaging paths.
    """
    files_found = 0
    with open(response_file, "w") as f:
        for path_on_disk, relative_virtual_path in folders_to_pack:
            if os.path.exists(path_on_disk):
                # Case A: Directory-level packaging (Standard recursive walk)
                if os.path.isdir(path_on_disk):
                    for root, _, files in os.walk(path_on_disk):
                        for file in files:
                            if file.endswith((".uasset", ".uexp", ".ubulk")):
                                # Exclude PhysicsAsset always
                                if "PhysicsAsset" in file:
                                    continue
                                # Exclude Skeleton if no custom animations are shipped
                                if "Skeleton" in file and not has_anims:
                                    continue
                                    
                                abs_path = os.path.join(root, file)
                                rel_to_cooked = os.path.relpath(abs_path, path_on_disk)
                                rel_virtual = "../../../Pal/Content/" + relative_virtual_path + "/" + rel_to_cooked.replace("\\", "/")
                                f.write(f'"{abs_path}" "{rel_virtual}"\n')
                                files_found += 1
                # Case B: File-level packaging (Single explicit asset)
                else:
                    rel_virtual = "../../../Pal/Content/" + relative_virtual_path.replace("\\", "/")
                    f.write(f'"{path_on_disk}" "{rel_virtual}"\n')
                    files_found += 1
                            
    if files_found > 0:
        run_and_stream([unrealpak_path, output_pak, f"-Create={response_file}"])
        
    return files_found
