# utils/builder/config_helper.py
import os
import shutil

def restore_palbaker_backup(uproject_path: str | None) -> bool:
    """
    Checks if a stranded DefaultGame.ini.palbaker.bak exists in the project Config directory.
    If found, restores it to DefaultGame.ini and removes the backup file.
    Returns True if restoration was performed, False otherwise.
    """
    if not uproject_path or not os.path.exists(uproject_path):
        return False
        
    project_dir = os.path.dirname(uproject_path)
    ini_dir = os.path.join(project_dir, "Config")
    ini_path = os.path.join(ini_dir, "DefaultGame.ini")
    ini_backup = os.path.join(ini_dir, "DefaultGame.ini.palbaker.bak")
    
    if os.path.exists(ini_backup):
        print(f"\n[Self-Healing] Stranded PalBaker backup detected! Restoring {ini_backup} -> {ini_path}...", flush=True)
        try:
            shutil.copy2(ini_backup, ini_path)
            os.remove(ini_backup)
            print("[Self-Healing] Project DefaultGame.ini successfully restored and healed.", flush=True)
            return True
        except Exception as e:
            print(f"[Self-Healing] ERROR: Failed to restore backup: {e}", flush=True)
            
    return False

def inject_packaging_settings(ini_path: str, ue_virtual_path: str, skeleton_virtual_path: str, anims_virtual_path: str, has_anims: bool, should_cook_vanilla: bool, extra_paths: list | None = None):
    """Safely updates DefaultGame.ini packaging settings without modifying existing user entries."""
    if not os.path.exists(ini_path):
        return
        
    with open(ini_path, "r", encoding="utf-8-sig", errors="replace") as f:
        lines = f.readlines()
        
    new_lines = []
    in_section = False
    section_found = False
    section_header = "[/Script/UnrealEd.ProjectPackagingSettings]"
    
    keys_to_override = [
        "DirectoriesToAlwaysCook", "+DirectoriesToAlwaysCook", "-DirectoriesToAlwaysCook",
        "bCookAll", "bUseIoStore", "bShareMaterialShaderCode", "MapsToCook", "+MapsToCook", "-MapsToCook"
    ]
    
    append_lines = [
        "bCookAll=False\n",
        "bUseIoStore=False\n",
        "bShareMaterialShaderCode=False\n",
    ]
    
    # FIXED: Only cook the vanilla directory if should_cook_vanilla evaluates to True
    if should_cook_vanilla:
        append_lines.append(f'+DirectoriesToAlwaysCook=(Path="{ue_virtual_path}")\n')
        
    append_lines.append(f'+DirectoriesToAlwaysCook=(Path="{skeleton_virtual_path}")\n')
        
    if has_anims:
        append_lines.append(f'+DirectoriesToAlwaysCook=(Path="{anims_virtual_path}")\n')
        
    if extra_paths:
        for path in extra_paths:
            append_lines.append(f'+DirectoriesToAlwaysCook=(Path="{path}")\n')
            
    append_lines.append("MapsToCook=\n")
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if stripped.lower() == section_header.lower():
                in_section = True
                section_found = True
                new_lines.append(line)
                new_lines.extend(append_lines)
                continue
            else:
                in_section = False
                
        if in_section:
            if any(stripped.startswith(k) for k in keys_to_override):
                continue
        new_lines.append(line)
        
    if not section_found:
        new_lines.append("\n" + section_header + "\n")
        new_lines.extend(append_lines)
        
    with open(ini_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


class GameIniCookContext:
    """Context Manager to safely backup, modify, and restore DefaultGame.ini during a cook run."""
    def __init__(self, workspace, extra_paths: list | None = None):
        self.workspace = workspace
        self.extra_paths = extra_paths

    def __enter__(self):
        if self.workspace.config_dir:
            os.makedirs(self.workspace.config_dir, exist_ok=True)

        if os.path.exists(self.workspace.ini_path):
            shutil.copy2(self.workspace.ini_path, self.workspace.ini_backup)
            
            # FIXED: Dynamically toggle cooking of the original vanilla model directory
            should_cook_vanilla = not self.workspace.is_altermatic_active or self.workspace.base_type == "custom"
            
            inject_packaging_settings(
                self.workspace.ini_path,
                self.workspace.ue_virtual_path,
                self.workspace.skeleton_virtual_path,
                self.workspace.anims_virtual_path,
                self.workspace.has_anims,
                should_cook_vanilla,
                extra_paths=self.extra_paths
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if os.path.exists(self.workspace.ini_backup):
            shutil.move(self.workspace.ini_backup, self.workspace.ini_path)