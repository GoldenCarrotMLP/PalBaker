# utils/extractor/paths.py
import os

def get_paks_dir(palworld_exe: str) -> str | None:
    """Safely calculates the Palworld Paks folder directory path based on the executable path."""
    if not palworld_exe or not os.path.exists(palworld_exe):
        return None
    
    exe_lower = palworld_exe.lower()
    if "binaries" in exe_lower:
        return os.path.normpath(os.path.join(os.path.dirname(palworld_exe), "..", "..", "Content", "Paks"))
    else:
        return os.path.normpath(os.path.join(os.path.dirname(palworld_exe), "Pal", "Content", "Paks"))