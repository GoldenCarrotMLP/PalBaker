# utils/builder/blender_helper.py
import os
import re
import urllib.request
import zipfile
import tempfile
import shutil
import ssl
import subprocess
import sys

# Inject paths into context to allow importing from the utils package dynamically
utils_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if utils_dir not in sys.path:
    sys.path.append(utils_dir)

from blender_utils import translator

def get_blender_version(blender_path: str) -> str:
    """Queries the Blender executable headlessly to parse its version string."""
    if not blender_path or not os.path.exists(blender_path):
        return "4.2"
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        result = subprocess.run(
            [blender_path, "-v"], 
            capture_output=True, 
            text=True, 
            encoding='utf-8', 
            errors='replace', 
            creationflags=creation_flags, 
            timeout=3
        )
        match = re.search(r"Blender\s+(\d+\.\d+)", result.stdout)
        if match:
            return match.group(1)
    except Exception:
        pass
    return "4.2"

def get_blender_version_tuple(version_str: str) -> tuple:
    """Parses a "X.Y" version string into a (major, minor) tuple."""
    try:
        parts = version_str.split('.')
        return (int(parts[0]), int(parts[1]))
    except Exception:
        return (4, 2)

def patch_extracted_addon_files(target_addon_dir: str):
    """
    Scans the extracted addon files and automatically patches known 3rd-party API breaks
    (like 'use_auto_smooth' in 4.1+). This function is strictly idempotent and self-healing.
    It will strip out corrupted stacked 'try:' blocks from previous errors before re-applying.
    """
    print("[PalBaker] Running automated compatibility patcher on extracted addon files...", flush=True)
    for root, _, files in os.walk(target_addon_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    
                    modified = False
                    patched_lines = []
                    for line in lines:
                        # Idempotent & Self-Healing: Target lines with assignments to 'use_auto_smooth'
                        if "use_auto_smooth" in line and "=" in line:
                            # Strip out any existing 'try:' prefixes to cure stacked corruption
                            clean_code = re.sub(r'(try:\s*)+', '', line.strip())
                            indent = line[:len(line) - len(line.lstrip())]
                            
                            patched_lines.append(f"{indent}try: {clean_code}\n")
                            patched_lines.append(f"{indent}except AttributeError: pass\n")
                            modified = True
                        elif "except AttributeError: pass" in line:
                            # Skip floating except blocks left over from previous runs
                            continue
                        else:
                            patched_lines.append(line)
                    
                    if modified:
                        print(f"  Patching compat rules inside: {os.path.basename(file_path)}", flush=True)
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.writelines(patched_lines)
                except Exception as e:
                    print(f"  Warning: Failed to patch {file}: {e}", flush=True)

def pre_install_psk_addon(blender_path: str):
    """
    Dynamically downloads and unzips the correct version of the PSK addon 
    directly into the Blender installation directory's scripts folder.
    """
    blender_dir = os.path.dirname(blender_path)
    version_str = get_blender_version(blender_path)
    try:
        version_val = float(version_str)
    except ValueError:
        version_val = 4.2

    version_tuple = get_blender_version_tuple(version_str)

    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        return

    # Resolve extraction path natively based on Blender version via adapter
    target_addon_dir = translator.execute_with_version("get_target_addon_directory", version_tuple, blender_dir, version_str, appdata)

    if os.path.exists(target_addon_dir) and any(f.endswith(".py") for f in os.listdir(target_addon_dir)):
        print(f"[PalBaker] PSK Importer addon is already installed inside Blender's system folder ({version_str}).", flush=True)
        # Execute patcher anyway to heal corrupted files from previous errors
        patch_extracted_addon_files(target_addon_dir)
        return

    if os.path.exists(target_addon_dir):
        try:
            shutil.rmtree(target_addon_dir, ignore_errors=True)
        except PermissionError:
            print(f"[PalBaker] Warning: System folder is write-protected. Falling back to AppData directory...", flush=True)
            target_addon_dir = os.path.join(appdata, "Blender Foundation", "Blender", version_str, "extensions" if version_val >= 4.2 else "scripts", "user_default" if version_val >= 4.2 else "addons", "io_scene_psk_psa")

    print(f"[PalBaker] PSK Importer addon is missing. Pre-installing version-compliant release for Blender {version_str}...", flush=True)
    
    url = translator.execute_with_version("get_download_url", version_tuple, version_str)

    try:
        temp_dir = tempfile.gettempdir()
        zip_path = os.path.join(temp_dir, f"io_scene_psk_psa_{version_str}.zip")
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        
        print(f"  Downloading: {url} -> {zip_path}", flush=True)
        with urllib.request.urlopen(req, context=ctx) as response, open(zip_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
            
        print(f"  Extracting package directly to: {target_addon_dir}", flush=True)
        os.makedirs(target_addon_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            namelist = zip_ref.namelist()
            
            if "__init__.py" in namelist:
                addon_source_subfolder = ""
            else:
                init_paths = [f for f in namelist if f.endswith("/__init__.py")]
                if init_paths:
                    init_paths.sort(key=lambda f: f.count("/"))
                    addon_source_subfolder = os.path.dirname(init_paths[0])
                else:
                    addon_source_subfolder = ""

            if addon_source_subfolder:
                print(f"  Extracting nested package '{addon_source_subfolder}' to: {target_addon_dir}", flush=True)
                for member in zip_ref.infolist():
                    if member.filename.startswith(addon_source_subfolder + "/"):
                        rel_path = os.path.relpath(member.filename, addon_source_subfolder)
                        dest_file = os.path.join(target_addon_dir, rel_path)
                        if member.is_dir():
                            os.makedirs(dest_file, exist_ok=True)
                        else:
                            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                            with zip_ref.open(member) as source, open(dest_file, "wb") as target:
                                shutil.copyfileobj(source, target)
            else:
                print(f"  Extracting flat package directly to: {target_addon_dir}", flush=True)
                zip_ref.extractall(target_addon_dir)
                
        print(f"[PalBaker] Successfully pre-installed PSK addon for Blender {version_str}!", flush=True)
        
        patch_extracted_addon_files(target_addon_dir)
        
        try: os.remove(zip_path)
        except OSError: pass
        
    except Exception as e:
        print(f"ERROR: Failed to pre-install PSK addon: {e}", flush=True)

def run_headless_blender(blender_path: str, blend_file: str | None, script_path: str, args: list) -> subprocess.CompletedProcess:
    """Executes a script inside headless Blender, loading startup files, enabling addons via CLI, and capturing output."""
    version_str = get_blender_version(blender_path)
    v_tuple = get_blender_version_tuple(version_str)

    # RULE CHECK: Only run pre-install and load addons if we are actually importing/reconstructing a PSK!
    # This prevents loading or downloading any classes during simple "Refresh Layout" operations.
    is_psk_task = "blender_reconstruct.py" in script_path or any(".psk" in str(arg).lower() for arg in args)

    cmd = [blender_path, "-b"]
    
    # Bypasses double-registration/AppData collisions entirely by running an isolated clean environment
    cmd.append("--factory-startup")

    if blend_file and blend_file.lower().endswith(".blend"):
        cmd.append(blend_file)
        
    if is_psk_task:
        pre_install_psk_addon(blender_path)
        addons_list = translator.execute_with_version("get_addons_list", v_tuple)
        cmd.extend(["--addons", addons_list])
    
    cmd.extend(["--python", script_path, "--"])
    cmd.extend(args)
    
    return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')