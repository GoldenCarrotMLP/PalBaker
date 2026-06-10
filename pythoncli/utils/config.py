# utils/config.py
import os
import json

# Force settings file to always save in the root PalBaker directory
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "manager_settings.json")

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {
        "fmodel_output": "", 
        "ue_root": "", 
        "uproject": "", 
        "blender": "",
        "palworld_exe": "",
        "show_mapped": False,
        "console_height": 200
    }

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
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
        
        val_clean = val.strip()
        if not os.path.exists(val_clean):
            return False, f"The configured path for '{friendly_names.get(key, key)}' does not exist on disk: '{val_clean}'"
            
    return True, ""