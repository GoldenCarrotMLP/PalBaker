# pythoncli/utils/config.py
import os
import json

# Force settings file to always save in the root PalBaker directory
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "manager_settings.json")

def clean_path_prefix(path_val):
    if isinstance(path_val, str):
        # Strip Windows extended path prefix (UNC canonical prefix) safely
        return path_val.replace("\\\\?\\", "").replace("//?/", "")
    return path_val

def load_settings():
    settings = {
        "fmodel_output": "", 
        "ue_root": "", 
        "uproject": "", 
        "blender": "",
        "palworld_exe": "",
        "show_mapped": False,
        "console_height": 200
    }
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    settings.update(loaded)
        except:
            pass
            
    # Centralized Path Cleaning: Automatically strip any Windows extended UNC paths
    for key in ["fmodel_output", "ue_root", "uproject", "blender", "palworld_exe", "workspace"]:
        if key in settings:
            settings[key] = clean_path_prefix(settings[key])
            
    return settings

def save_settings(settings):
    # Ensure saved paths are also fully cleaned
    for key in ["fmodel_output", "ue_root", "uproject", "blender", "palworld_exe", "workspace"]:
        if key in settings:
            settings[key] = clean_path_prefix(settings[key])
            
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)

def validate_settings(settings: dict, required_keys: list[str]) -> tuple[bool, str]:
    """
    Validates that the required settings keys are configured and point
    to directories or files that physically exist on the system.
    Returns: (is_valid: bool, error_message: str)
    """
    friendly_names = {
        "fmodel_output": "Workspace Folder",
        "ue_root": "Unreal Engine Root",
        "uproject": "Palworld ModKit .uproject Path",
        "blender": "Blender Executable Path",
        "palworld_exe": "Palworld.exe Path"
    }
    
    for key in required_keys:
        val = settings.get(key, "")
        if not val or not isinstance(val, str) or val.strip() == "":
            return False, f"Missing required setting: '{friendly_names.get(key, key)}'. Please configure it in your Settings."
        
        val_clean = clean_path_prefix(val.strip())
        if not os.path.exists(val_clean):
            return False, f"The configured path for '{friendly_names.get(key, key)}' does not exist on disk: '{val_clean}'"
            
    return True, ""