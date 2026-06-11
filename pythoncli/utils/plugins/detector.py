import os
import glob
import hashlib

def get_source_dir_hash(plugin_dir: str) -> str:
    """Computes a combined SHA-256 hash of all C++ source files, normalizing newlines to prevent Git CRLF issues."""
    source_dir = os.path.join(plugin_dir, "Source")
    if not os.path.exists(source_dir):
        return ""
    
    hasher = hashlib.sha256()
    extensions = (".h", ".cpp", ".cs", ".uplugin")
    
    filepaths = []
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith(extensions):
                filepaths.append(os.path.join(root, file))
                
    uplugin_path = os.path.join(plugin_dir, "PalBakerEditorUtils.uplugin")
    if os.path.exists(uplugin_path):
        filepaths.append(uplugin_path)
                
    # Sort files to ensure deterministic hashing order across all OSs
    filepaths.sort()
    
    for path in filepaths:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().replace("\r\n", "\n")
                hasher.update(content.encode("utf-8"))
        except Exception:
            pass
            
    return hasher.hexdigest().lower()

def get_missing_assets(src_assets_dir: str, dest_content_dir: str) -> list[str]:
    """Diffs the repository assets against the ModKit and returns a list of missing relative paths."""
    missing = []
    if not os.path.exists(src_assets_dir):
        return missing
    for root, _, files in os.walk(src_assets_dir):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), src_assets_dir)
            dest_path = os.path.join(dest_content_dir, rel_path)
            if not os.path.exists(dest_path):
                missing.append(rel_path.replace("\\", "/"))
    return missing

def check_remote_execution_settings(uproject_path: str) -> bool:
    """Returns True if bRemoteExecution=True is configured in DefaultEngine.ini (fully case-insensitive)."""
    project_dir = os.path.dirname(uproject_path)
    ini_path = os.path.join(project_dir, "Config", "DefaultEngine.ini")
    
    if not os.path.exists(ini_path):
        return False
        
    try:
        with open(ini_path, "r", encoding="utf-8-sig", errors="replace") as f:
            lines = f.readlines()
            
        in_section = False
        target_section = "[/script/pythonscriptplugin.pythonscriptpluginsettings]"
        
        for line in lines:
            stripped = line.strip().replace(" ", "").lower()
            if stripped.startswith("[") and stripped.endswith("]"):
                if stripped == target_section:
                    in_section = True
                else:
                    in_section = False
            elif in_section:
                if stripped == "bremoteexecution=true":
                    return True
        return False
    except Exception:
        return False

def check_cooking_settings(uproject_path: str) -> bool:
    """Returns True if bUseIoStore=False and bShareMaterialShaderCode=False are configured in DefaultGame.ini."""
    project_dir = os.path.dirname(uproject_path)
    ini_path = os.path.join(project_dir, "Config", "DefaultGame.ini")
    
    if not os.path.exists(ini_path):
        return False
        
    try:
        with open(ini_path, "r", encoding="utf-8-sig", errors="replace") as f:
            content = f.read()
            
        section_header = "[/Script/UnrealEd.ProjectPackagingSettings]"
        if section_header.lower() not in content.lower():
            return False
            
        lines = content.splitlines()
        in_section = False
        io_store_ok = False
        shader_code_ok = False
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                if stripped.lower() == section_header.lower():
                    in_section = True
                else:
                    in_section = False
            elif in_section:
                clean_line = stripped.replace(" ", "").lower()
                if clean_line == "buseiostore=false":
                    io_store_ok = True
                elif clean_line == "bsharematerialshadercode=false":
                    shader_code_ok = True
                    
        return io_store_ok and shader_code_ok
    except Exception:
        return False