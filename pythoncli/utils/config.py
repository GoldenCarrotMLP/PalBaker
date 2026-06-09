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