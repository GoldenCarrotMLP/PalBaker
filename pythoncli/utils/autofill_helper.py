import os
import glob
import string

def detect_unreal_engine():
    # Common locations for Unreal Engine 5.1.1
    common_paths = [
        r"C:\Program Files\Epic Games\UE_5.1",
        r"C:\EpicGames\UE_5.1"
    ]
    for path in common_paths:
        if os.path.exists(path):
            return path
    return ""

def detect_palworld_exe():
    # Check all available drives
    drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
    
    # Common relative paths from a drive root
    common_subpaths = [
        r"Program Files (x86)\Steam\steamapps\common\Palworld\Palworld.exe", # Added this
        r"Program Files (x86)\Steam\steamapps\common\Palworld\Pal\Binaries\Win64\Pal-Win64-Shipping.exe",
        r"Program Files (x86)\Steam\steamapps\common\PalServer\Pal\Binaries\Win64\PalServer-Win64-Shipping.exe",
        r"SteamLibrary\steamapps\common\Palworld\Pal\Binaries\Win64\Pal-Win64-Shipping.exe",
        r"SteamLibrary\steamapps\common\PalServer\Pal\Binaries\Win64\PalServer-Win64-Shipping.exe"
    ]
    
    for drive in drives:
        for subpath in common_subpaths:
            full_path = os.path.join(drive, subpath)
            if os.path.exists(full_path):
                return full_path
    return ""

def find_blender_versions():
    # Search for Blender installations in Program Files
    # Typical path: C:\Program Files\Blender Foundation\Blender 4.3\blender.exe
    search_pattern = r"C:\Program Files\Blender Foundation\Blender *\blender.exe"
    found_files = glob.glob(search_pattern)
    return found_files

