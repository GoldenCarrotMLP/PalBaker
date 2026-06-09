# utils/ue4ss_helper.py
import os
import shutil
import urllib.request
import zipfile
import tempfile
import hashlib
import ssl
import json

PALWORLD_BRANCH_URL = "https://github.com/Okaetsu/RE-UE4SS/releases/download/experimental-palworld/UE4SS-Palworld.zip"
LATEST_BRANCH_URL = "https://github.com/UE4SS-RE/RE-UE4SS/releases/download/experimental-latest/UE4SS_v3.0.1-953-gb872ad11.zip"

# Pre-registered signatures for automatic branch detection on manual installations
KNOWN_HASHES = {
    "1e697df5b8f54f5eee2c9d3291169b516876aec6b6096130fd4185a88d9b71bc": "Palworld-Experimental",
    "12592a086dbe5bcf2724c5c3ec7d4d16772f07bebaa0d5184801ccc12a6c43af": "Latest-Experimental"
}

def get_binaries_dir(palworld_exe: str | None) -> str :
    """Resolves the Win64 binary directory from the game executable path."""
    if not palworld_exe or not os.path.exists(palworld_exe):
        return ""
    dirname = os.path.dirname(palworld_exe)
    basename = os.path.basename(palworld_exe).lower()
    
    # User selected Palworld.exe in root
    if basename == "palworld.exe":
        b_dir = os.path.join(dirname, "Pal", "Binaries", "Win64")
        if os.path.exists(b_dir):
            return b_dir
    # User selected Palworld-Win64-Shipping.exe inside the Win64 folder
    elif "win64" in dirname.lower():
        return dirname
    return ""

def hash_file(filepath: str) -> str:
    """Computes a SHA-256 checksum for a file."""
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except Exception:
        return ""

def get_ue4ss_status(palworld_exe: str | None) -> dict:
    """Evaluates whether UE4SS is installed, which branch, and if the DLL matches its expected hash."""
    bin_dir = get_binaries_dir(palworld_exe)
    if not bin_dir:
        return {"status": "Exe not found", "branch": "Unknown", "corrupted": False}
        
    dwmapi = os.path.join(bin_dir, "dwmapi.dll")
    
    # FIXED: Strictly look inside the nested ue4ss / UE4SS subfolder for core dll loader
    ue4ss_dll_sub_lower = os.path.join(bin_dir, "ue4ss", "UE4SS.dll")
    ue4ss_dll_sub_upper = os.path.join(bin_dir, "UE4SS", "UE4SS.dll")
    ue4ss_dll = ue4ss_dll_sub_lower if os.path.exists(ue4ss_dll_sub_lower) else ue4ss_dll_sub_upper
    
    installed = os.path.exists(dwmapi) and os.path.exists(ue4ss_dll)
    if not installed:
        return {"status": "Not Installed", "branch": "None", "corrupted": False}
        
    current_hash = hash_file(ue4ss_dll).lower()
    info_file = os.path.join(bin_dir, ".palbaker_ue4ss.json")
    
    branch = "Unknown"
    expected_hash = ""
    corrupted = False
    
    if os.path.exists(info_file):
        try:
            with open(info_file, "r") as f:
                data = json.load(f)
                branch = data.get("branch", "Unknown")
                expected_hash = data.get("dll_hash", "").lower()
        except Exception:
            pass

    # Identify unmanaged manual installations matching pre-registered hashes
    if not expected_hash:
        if current_hash in KNOWN_HASHES:
            branch = KNOWN_HASHES[current_hash]
            expected_hash = current_hash
            try:
                with open(info_file, "w") as f:
                    json.dump({"branch": branch, "dll_hash": current_hash}, f)
            except Exception:
                pass
        else:
            branch = "Unknown"
            
    if expected_hash:
        if current_hash != expected_hash:
            corrupted = True
            
    return {"status": "Installed", "branch": branch, "corrupted": corrupted}

def download_and_extract_ue4ss(palworld_exe: str, branch: str, log_callback) -> bool:
    """Downloads the zip, extracts it natively to Win64/ue4ss/ preserving structures, and registers hashes."""
    bin_dir = get_binaries_dir(palworld_exe)
    if not bin_dir:
        log_callback("Error: Invalid Palworld executable path.", True)
        return False
        
    url = PALWORLD_BRANCH_URL if branch == "Palworld-Experimental" else LATEST_BRANCH_URL
    
    temp_dir = tempfile.gettempdir()
    zip_path = os.path.join(temp_dir, f"ue4ss_{branch}.zip")
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        log_callback(f"Downloading UE4SS ({branch})...", False)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx) as response, open(zip_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
            
        log_callback("Extracting UE4SS natively...", False)
        extract_tmp = os.path.join(temp_dir, f"ue4ss_{branch}_extracted")
        if os.path.exists(extract_tmp):
            shutil.rmtree(extract_tmp)
        os.makedirs(extract_tmp, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_tmp)
            
        # Target folder inside the Binaries directory
        target_ue4ss_dir = os.path.join(bin_dir, "ue4ss")
        os.makedirs(target_ue4ss_dir, exist_ok=True)

        # FIXED: Robust, non-flattened extraction.
        # Cases:
        # A) Zip already has 'ue4ss' subfolder (Okaetsu's package style)
        # B) Zip has flat root files (Standard experimental package style)
        has_subfolder = os.path.exists(os.path.join(extract_tmp, "ue4ss"))
        
        if has_subfolder:
            # Case A: Deploy dwmapi.dll to Win64 root, and copy the ue4ss folder as-is
            dwmapi_src = os.path.join(extract_tmp, "dwmapi.dll")
            if os.path.exists(dwmapi_src):
                shutil.copy2(dwmapi_src, os.path.join(bin_dir, "dwmapi.dll"))
                
            shutil.copytree(os.path.join(extract_tmp, "ue4ss"), target_ue4ss_dir, dirs_exist_ok=True)
        else:
            # Case B: Standard flat zip. We copy dwmapi.dll to root, and route all other assets into ue4ss/
            for item in os.listdir(extract_tmp):
                src_item = os.path.join(extract_tmp, item)
                if item.lower() == "dwmapi.dll":
                    shutil.copy2(src_item, os.path.join(bin_dir, "dwmapi.dll"))
                else:
                    dest_item = os.path.join(target_ue4ss_dir, item)
                    if os.path.isdir(src_item):
                        shutil.copytree(src_item, dest_item, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src_item, dest_item)

        # Hash UE4SS.dll to track and register branch status
        ue4ss_dll = os.path.join(target_ue4ss_dir, "UE4SS.dll")
        dll_hash = hash_file(ue4ss_dll)
        
        info_file = os.path.join(bin_dir, ".palbaker_ue4ss.json")
        with open(info_file, "w") as f:
            json.dump({"branch": branch, "dll_hash": dll_hash}, f)
            
        log_callback("UE4SS installation completed successfully!", False)
        
        # Cleanup
        shutil.rmtree(extract_tmp, ignore_errors=True)
        try: os.remove(zip_path)
        except OSError: pass
        return True
        
    except Exception as e:
        log_callback(f"Error during installation: {e}", True)
        return False

def uninstall_ue4ss(palworld_exe: str, log_callback) -> bool:
    """Removes dwmapi.dll and core UE4SS assets strictly without deleting the user's Mods directory."""
    bin_dir = get_binaries_dir(palworld_exe)
    if not bin_dir:
        log_callback("Error: Invalid Palworld executable path.", True)
        return False
        
    try:
        # Delete root proxy loader
        dwmapi_path = os.path.join(bin_dir, "dwmapi.dll")
        if os.path.exists(dwmapi_path):
            os.remove(dwmapi_path)

        # Delete local state tracker
        info_file = os.path.join(bin_dir, ".palbaker_ue4ss.json")
        if os.path.exists(info_file):
            os.remove(info_file)
            
        # FIXED: Clean up only core loader binaries, keeping the Mods directory safe
        ue4ss_dir = os.path.join(bin_dir, "ue4ss")
        if os.path.exists(ue4ss_dir):
            core_files_to_remove = [
                "UE4SS.dll",
                "UE4SS-settings.ini",
                "MemberVariableLayout.ini",
                "VTableLayout.ini",
                "UE4SS.log",
                "README.md"
            ]
            for f in core_files_to_remove:
                f_path = os.path.join(ue4ss_dir, f)
                if os.path.exists(f_path):
                    os.remove(f_path)
            
            # Clean up signatures folder if present
            sigs_dir = os.path.join(ue4ss_dir, "UE4SS_Signatures")
            if os.path.exists(sigs_dir):
                shutil.rmtree(sigs_dir, ignore_errors=True)
                
            # If the ue4ss folder is completely empty except for Mods, we leave it.
            # Otherwise, if Mods is empty, we cleanly remove it.
            mods_dir = os.path.join(ue4ss_dir, "Mods")
            if os.path.exists(mods_dir) and not os.listdir(mods_dir):
                shutil.rmtree(ue4ss_dir, ignore_errors=True)
            elif not os.path.exists(mods_dir) and not os.listdir(ue4ss_dir):
                shutil.rmtree(ue4ss_dir, ignore_errors=True)
            
        log_callback("UE4SS successfully uninstalled (Mods folder preserved).", False)
        return True
    except Exception as e:
        log_callback(f"Error during uninstallation: {e}", True)
        return False