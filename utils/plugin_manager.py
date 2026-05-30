import os
import sys
import json  # ADDED: Fix NameError inside main execution block
from utils.plugins.detector import (
    get_max_source_mtime, 
    get_max_dll_mtime, 
    get_missing_assets, 
    check_remote_execution_settings,
    check_cooking_settings
)
from utils.plugins.installer import (
    sync_plugin_files, 
    inject_framework_assets, 
    copy_dlls_back, 
    enable_remote_execution_settings,
    enable_cooking_settings,
    restart_unreal_editor
)
from utils.plugins.compiler import run_ubt_compilation

def check_project_requirements(ue_root: str, uproject_path: str) -> dict:
    """Analyzes the ModKit status and returns exactly what files/plugins are missing."""
    result = {
        "error": None, 
        "needs_plugin_sync": False, 
        "needs_compile": False, 
        "needs_remote_exec_enable": False,
        "needs_cooking_setup": False,
        "missing_assets": []
    }
    
    if not ue_root or not uproject_path or not os.path.exists(uproject_path):
        result["error"] = "Unreal Engine Root or UProject path is missing or invalid."
        return result

    project_dir = os.path.dirname(uproject_path)
    dest_plugin_dir = os.path.join(project_dir, "Plugins", "PalBakerEditorUtils")
    dest_dll_dir = os.path.join(dest_plugin_dir, "Binaries", "Win64")

    src_plugin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugins", "PalBakerEditorUtils"))
    src_dll_dir = os.path.join(src_plugin_dir, "Binaries", "Win64")

    if not os.path.exists(src_plugin_dir):
        result["error"] = f"Source plugin directory not found at: {src_plugin_dir}. Verify git workspace files."
        return result

    src_source_mtime = get_max_source_mtime(src_plugin_dir)
    src_dll_mtime = get_max_dll_mtime(src_dll_dir)
    dest_dll_mtime = get_max_dll_mtime(dest_dll_dir)

    result["needs_compile"] = src_dll_mtime == 0.0 or src_source_mtime > src_dll_mtime
    result["needs_plugin_sync"] = not os.path.exists(dest_plugin_dir) or dest_dll_mtime != src_dll_mtime
    result["needs_remote_exec_enable"] = not check_remote_execution_settings(uproject_path)
    result["needs_cooking_setup"] = not check_cooking_settings(uproject_path)

    src_assets_dir = os.path.join(src_plugin_dir, "Assets", "Content")
    dest_content_dir = os.path.join(project_dir, "Content")

    result["missing_assets"] = get_missing_assets(src_assets_dir, dest_content_dir)
    return result

def install_and_compile_plugin(ue_root: str, uproject_path: str, verbose: bool = False, force_recompile: bool = False):
    """Executes the plugin installation and compilation phase."""
    project_dir = os.path.dirname(uproject_path)
    dest_plugin_dir = os.path.join(project_dir, "Plugins", "PalBakerEditorUtils")
    dest_dll_dir = os.path.join(dest_plugin_dir, "Binaries", "Win64")

    src_plugin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugins", "PalBakerEditorUtils"))
    src_dll_dir = os.path.join(src_plugin_dir, "Binaries", "Win64")

    src_source_mtime = get_max_source_mtime(src_plugin_dir)
    src_dll_mtime = get_max_dll_mtime(src_dll_dir)

    repo_needs_build = force_recompile or src_dll_mtime == 0.0 or src_source_mtime > src_dll_mtime

    if repo_needs_build:
        sync_plugin_files(src_plugin_dir, dest_plugin_dir, verbose)
        success, err_msg = run_ubt_compilation(ue_root, uproject_path, verbose)
        if not success:
            return False, err_msg
        
        copy_dlls_back(dest_dll_dir, src_dll_dir, verbose)
        src_dll_mtime = get_max_dll_mtime(src_dll_dir)

    dest_dll_mtime = get_max_dll_mtime(dest_dll_dir)
    user_needs_sync = not os.path.exists(dest_plugin_dir) or dest_dll_mtime != src_dll_mtime

    if user_needs_sync:
        sync_plugin_files(src_plugin_dir, dest_plugin_dir, verbose)

    return True, "C++ Plugin successfully synchronized and installed!"

def inject_missing_assets(uproject_path: str, verbose: bool = False):
    """Executes the exact asset copying phase."""
    project_dir = os.path.dirname(uproject_path)
    src_plugin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugins", "PalBakerEditorUtils"))
    
    src_assets_dir = os.path.join(src_plugin_dir, "Assets", "Content")
    dest_content_dir = os.path.join(project_dir, "Content")
    
    return inject_framework_assets(src_assets_dir, dest_content_dir, verbose)

# Backward compatibility aliases
setup_and_compile_plugin = install_and_compile_plugin

if __name__ == "__main__":
    print("=== PalBaker C++ Plugin Setup (Standalone) ===")
    
    settings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "manager_settings.json"))
    if not os.path.exists(settings_path):
        print(f"ERROR: Could not find settings file at {settings_path}")
        sys.exit(1)
        
    with open(settings_path, "r") as f:
        settings = json.load(f)
        
    ue_root = settings.get("ue_root", "")
    uproject = settings.get("uproject", "")
    
    is_success, final_msg = install_and_compile_plugin(ue_root, uproject, verbose=True, force_recompile=True)
    print(f"RESULT: {final_msg}")