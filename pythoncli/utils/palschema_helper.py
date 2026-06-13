# utils/palschema_helper.py
import os
import urllib.request
import zipfile
import tempfile
import ssl
import json
import shutil
from utils.ue4ss_helper import get_binaries_dir

PALSCHEMA_URL = "https://github.com/Okaetsu/PalSchema/releases/download/0.5.2/PalSchema_0.5.2.zip"

def get_ue4ss_dir(bin_dir: str) -> str:
    """Resolves the case-sensitive active UE4SS directory inside Win64."""
    ue4ss_dir_lower = os.path.join(bin_dir, "ue4ss")
    ue4ss_dir_upper = os.path.join(bin_dir, "UE4SS")
    return ue4ss_dir_lower if os.path.exists(ue4ss_dir_lower) else ue4ss_dir_upper

def get_palschema_status(palworld_exe: str | None) -> dict:
    """Checks if the PalSchema mod is currently installed by verifying its main.dll loader."""
    bin_dir = get_binaries_dir(palworld_exe)
    if not bin_dir:
        return {"status": "Exe not found"}
        
    ue4ss_dir = get_ue4ss_dir(bin_dir)
    
    # FIXED: Verify installation by the physical existence of the main.dll library
    palschema_dll = os.path.normpath(os.path.join(ue4ss_dir, "Mods", "PalSchema", "dlls", "main.dll"))
    installed = os.path.exists(palschema_dll) and os.path.isfile(palschema_dll)
    
    return {"status": "Installed" if installed else "Not Installed"}

def configure_ue4ss_mods(ue4ss_dir: str):
    """
    Safely parses and updates mods.txt and mods.json inside the UE4SS Mods folder.
    Forces mandatory core mods required for PalSchema to be enabled.
    """
    mods_folder = os.path.join(ue4ss_dir, "Mods")
    if not os.path.exists(mods_folder):
        return

    mods_txt_path = os.path.join(mods_folder, "mods.txt")
    mods_json_path = os.path.join(mods_folder, "mods.json")

    mandatory_mods_map = {
        "cheatmanagerenablermod": "CheatManagerEnablerMod",
        "consolecommandsmod": "ConsoleCommandsMod",
        "consoleenablermod": "ConsoleEnablerMod",
        "bpml_genericfunctions": "BPML_GenericFunctions",
        "bpmodloadermod": "BPModLoaderMod"
    }

    # 1. Configure mods.txt
    if os.path.exists(mods_txt_path):
        try:
            with open(mods_txt_path, "r", encoding="utf-8-sig", errors="replace") as f:
                lines = f.readlines()

            new_lines = []
            modified_keys = set()

            for line in lines:
                stripped = line.strip()
                if stripped.startswith(";") or not stripped:
                    new_lines.append(line)
                    continue

                if ":" in stripped:
                    parts = stripped.split(":")
                    key = parts[0].strip()
                    key_lower = key.lower()
                    if key_lower in mandatory_mods_map:
                        new_lines.append(f"{mandatory_mods_map[key_lower]} : 1\n")
                        modified_keys.add(key_lower)
                        continue
                new_lines.append(line)

            for k_lower, clean_name in mandatory_mods_map.items():
                if k_lower not in modified_keys:
                    new_lines.insert(0, f"{clean_name} : 1\n")

            with open(mods_txt_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception as e:
            print(f"Warning: Failed to update mods.txt: {e}")

    # 2. Configure mods.json
    if os.path.exists(mods_json_path):
        try:
            with open(mods_json_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)

            if isinstance(data, list):
                modified_targets = set()
                for item in data:
                    if isinstance(item, dict) and "mod_name" in item:
                        name_lower = item["mod_name"].lower()
                        if name_lower in mandatory_mods_map:
                            item["mod_enabled"] = True
                            modified_targets.add(name_lower)

                for k_lower, clean_name in mandatory_mods_map.items():
                    if k_lower not in modified_targets:
                        data.insert(0, {
                            "mod_name": clean_name,
                            "mod_enabled": True
                        })

                with open(mods_json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Warning: Failed to update mods.json: {e}")


def download_and_extract_palschema(palworld_exe: str, log_callback) -> bool:
    """Downloads the PalSchema zip and extracts it natively into the active UE4SS/Mods/ directory."""
    bin_dir = get_binaries_dir(palworld_exe)
    if not bin_dir:
        log_callback("Error: Invalid Palworld executable path.", True)
        return False

    ue4ss_dir = get_ue4ss_dir(bin_dir)
    mods_dir = os.path.join(ue4ss_dir, "Mods")
    if not os.path.exists(mods_dir):
        log_callback("Error: UE4SS Mods folder not found. Install UE4SS first.", True)
        return False

    temp_dir = tempfile.gettempdir()
    zip_path = os.path.join(temp_dir, "palschema_temp.zip")

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        log_callback("Downloading PalSchema...", False)
        req = urllib.request.Request(PALSCHEMA_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx) as response, open(zip_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)

        log_callback("Extracting PalSchema to Mods...", False)
        extract_tmp = os.path.join(temp_dir, "palschema_extracted")
        if os.path.exists(extract_tmp):
            shutil.rmtree(extract_tmp)
        os.makedirs(extract_tmp, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_tmp)

        actual_root = extract_tmp
        for root, dirs, files in os.walk(extract_tmp):
            if "PalSchema" in dirs:
                actual_root = os.path.join(root, "PalSchema")
                break

        dest_palschema_dir = os.path.join(mods_dir, "PalSchema")
        
        # Safely clean out the old installation while preserving the 'mods' folder
        if os.path.exists(dest_palschema_dir):
            for item in os.listdir(dest_palschema_dir):
                if item.lower() == "mods":
                    continue
                
                item_path = os.path.join(dest_palschema_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path, ignore_errors=True)
                else:
                    try:
                        os.remove(item_path)
                    except OSError:
                        pass

        # Copy the newly downloaded files over, merging safely with the preserved 'mods' folder
        shutil.copytree(actual_root, dest_palschema_dir, dirs_exist_ok=True)


        # Programmatically configure UE4SS mod initialization parameters
        log_callback("Configuring UE4SS mods database variables...", False)
        configure_ue4ss_mods(ue4ss_dir)

        log_callback("PalSchema installation completed successfully!", False)

        # Cleanup
        shutil.rmtree(extract_tmp, ignore_errors=True)
        try: os.remove(zip_path)
        except OSError: pass
        return True

    except Exception as e:
        log_callback(f"Error during PalSchema installation: {e}", True)
        return False

def uninstall_palschema(palworld_exe: str, log_callback) -> bool:
    """Permanently deletes the PalSchema mod but preserves the user's custom 'mods' directory."""
    bin_dir = get_binaries_dir(palworld_exe)
    if not bin_dir:
        log_callback("Error: Invalid Palworld executable path.", True)
        return False

    ue4ss_dir = get_ue4ss_dir(bin_dir)
    palschema_dir = os.path.join(ue4ss_dir, "Mods", "PalSchema")

    try:
        if os.path.exists(palschema_dir):
            # Iterate through the PalSchema directory and delete everything except 'mods'
            for item in os.listdir(palschema_dir):
                if item.lower() == "mods":
                    continue  # Skip and preserve the mods folder!
                
                item_path = os.path.join(palschema_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path, ignore_errors=True)
                else:
                    try:
                        os.remove(item_path)
                    except OSError:
                        pass

            log_callback("PalSchema successfully uninstalled (custom 'mods' folder preserved).", False)
            return True
        else:
            log_callback("PalSchema folder not found. Nothing to uninstall.", False)
            return True
    except Exception as e:
        log_callback(f"Error during uninstallation: {e}", True)
        return False