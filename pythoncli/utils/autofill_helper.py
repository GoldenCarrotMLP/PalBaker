import os
import glob
import string

def get_active_drives():
    """Returns a list of all active drive root paths on the system."""
    if os.name == 'nt':
        return [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
    return ["/"] # Fallback for POSIX-compliant environments

def detect_unreal_engine():
    """Scans all active drives for Unreal Engine 5.1 installations."""
    drives = get_active_drives()
    
    # Common UE 5.1 installation subpaths
    subpaths = [
        r"Program Files\Epic Games\UE_5.1",
        r"UE_5.1"
    ]
    
    for drive in drives:
        for subpath in subpaths:
            full_path = os.path.join(drive, subpath)
            if os.path.exists(full_path):
                return os.path.normpath(full_path)
    return ""

def detect_palworld_exe():
    """Scans all active drives for the root Palworld.exe launcher."""
    drives = get_active_drives()
    
    # Exclusively search for root launcher paths (ignoring shipping/binary paths)
    subpaths = [
        r"Program Files (x86)\Steam\steamapps\common\Palworld\Palworld.exe",
        r"SteamLibrary\steamapps\common\Palworld\Palworld.exe"
    ]
    
    for drive in drives:
        for subpath in subpaths:
            full_path = os.path.join(drive, subpath)
            if os.path.exists(full_path):
                return os.path.normpath(full_path)
    return ""

def find_blender_versions():
    """Scans all active drives for standard and Steam-bound Blender installations."""
    drives = get_active_drives()
    found_versions = []
    
    for drive in drives:

        # 1. Check Steam installations (both default and custom library drives)
        steam_subpaths = [
            r"Program Files (x86)\Steam\steamapps\common\Blender\blender.exe",
            r"SteamLibrary\steamapps\common\Blender\blender.exe"
        ]
        for subpath in steam_subpaths:
            full_path = os.path.join(drive, subpath)
            if os.path.exists(full_path):
                found_versions.append(os.path.normpath(full_path))

        # 2. Check standard Program Files installations using wildcards
        standard_pattern = os.path.join(drive, "Program Files", "Blender Foundation", "Blender *", "blender.exe")
        for match in glob.glob(standard_pattern):
            if os.path.exists(match):
                found_versions.append(os.path.normpath(match))
                
        
                
    # Deduplicate entries while preserving path priority
    seen = set()
    return [x for x in found_versions if not (x in seen or seen.add(x))]