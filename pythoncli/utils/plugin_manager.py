# utils/plugin_manager.py
import os
import sys
import json
import glob
import hashlib
from utils.plugins.detector import (
    get_source_dir_hash, 
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
    restart_unreal_editor,
    is_unreal_running,
    close_unreal_editor
)
from utils.plugins.compiler import run_ubt_compilation

def get_file_hash(filepath: str) -> str:
    """Computes a SHA-256 checksum for a file to prevent false-positive mtime desyncs."""
    if not os.path.exists(filepath):
        return ""
    hasher = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest().lower()
    except Exception:
        return ""

def get_dll_hashes(directory: str) -> dict:
    """Finds all compiled plugin DLLs and returns a map of their filenames to SHA-256 hashes."""
    hashes = {}
    if not os.path.exists(directory):
        return hashes
    dlls = glob.glob(os.path.join(directory, "UnrealEditor-PalBakerEditorUtils*.dll"))
    for d in dlls:
        name = os.path.basename(d)
        hashes[name] = get_file_hash(d)
    return hashes

def check_project_requirements(ue_root: str, uproject_path: str) -> dict:
    """Analyzes the ModKit status and returns exactly what files/plugins are missing."""
    result = {
        "error": None, 
        "needs_plugin_sync": False, 
        "plugin_outdated": False,
        "needs_compile": False, 
        "needs_remote_exec_enable": False,
        "needs_cooking_setup": False,
        "needs_icon_extraction": False,
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

    src_dll_hashes = get_dll_hashes(src_dll_dir)
    dest_dll_hashes = get_dll_hashes(dest_dll_dir)

    # If running inside a compiled release (frozen), skip local compilation checks
    is_frozen = getattr(sys, "frozen", False)
    if is_frozen:
        result["needs_compile"] = not bool(src_dll_hashes)
    else:
        # Check source hash against stored hash state
        source_hash = get_source_dir_hash(src_plugin_dir)
        hash_file = os.path.join(src_dll_dir, ".source_hash.txt")
        stored_hash = ""
        if os.path.exists(hash_file):
            try:
                with open(hash_file, "r") as f:
                    stored_hash = f.read().strip()
            except Exception: pass
            
        result["needs_compile"] = not bool(src_dll_hashes) or source_hash != stored_hash

    # Determine if the plugin files actually need a synchronization pass
    if not os.path.exists(dest_plugin_dir) or not dest_dll_hashes:
        result["needs_plugin_sync"] = True
        result["plugin_outdated"] = False
    else:
        # Check if any pre-compiled DLL is missing or has a different hash in the destination
        needs_sync = False
        for name, src_hash in src_dll_hashes.items():
            if name not in dest_dll_hashes or dest_dll_hashes[name] != src_hash:
                needs_sync = True
                break
        result["needs_plugin_sync"] = needs_sync
        result["plugin_outdated"] = needs_sync

    result["needs_remote_exec_enable"] = not check_remote_execution_settings(uproject_path)
    result["needs_cooking_setup"] = not check_cooking_settings(uproject_path)

    # Check if vanilla icons are extracted in the workspace (>10 png files is considered healthy)
    # This keeps standard database builds lightning-fast and makes icon extraction fully optional!
    from utils.config import load_settings
    settings = load_settings()
    fmodel_base = settings.get("fmodel_output", "")
    icon_dir = os.path.normpath(os.path.join(fmodel_base, "Exports", "Pal", "Content", "Pal", "Texture", "PalIcon", "Normal"))
    has_icons = os.path.exists(icon_dir) and len(glob.glob(os.path.join(icon_dir, "*.png"))) > 10
    result["needs_icon_extraction"] = not has_icons

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

    # Safeguard: Force-close Unreal Editor before file operations to prevent DLL permission locks
    if is_unreal_running():
        print(">>> Unreal Editor is running. Closing it to prevent it from overwriting DefaultEngine.ini...", flush=True)
        close_unreal_editor(verbose)

    is_frozen = getattr(sys, "frozen", False)
    
    # If we are in production (packaged/frozen app), we NEVER want to trigger compilation.
    # We simply copy the pre-compiled plugin and binaries straight from the program resources directory!
    if is_frozen:
        if verbose:
            print(">>> Production environment detected. Copying pre-compiled binaries directly...", flush=True)
        sync_plugin_files(src_plugin_dir, dest_plugin_dir, verbose)
        return True, "C++ Plugin successfully synchronized and installed!"

    # Dev-only compilation steps below
    source_hash = get_source_dir_hash(src_plugin_dir)
    hash_file = os.path.join(src_dll_dir, ".source_hash.txt")
    
    stored_hash = ""
    if os.path.exists(hash_file):
        try:
            with open(hash_file, "r") as f:
                stored_hash = f.read().strip()
        except Exception: pass

    src_dll_hashes = get_dll_hashes(src_dll_dir)
    repo_needs_build = force_recompile or not bool(src_dll_hashes) or source_hash != stored_hash

    if repo_needs_build:
        if verbose:
            print(">>> Source code changes detected or DLLs missing. Compiling C++ plugin...", flush=True)
            
        sync_plugin_files(src_plugin_dir, dest_plugin_dir, verbose)
        success, err_msg = run_ubt_compilation(ue_root, uproject_path, verbose)
        if not success:
            return False, err_msg
        
        copy_dlls_back(dest_dll_dir, src_dll_dir, verbose)
        
        # Save the new state hash after successful compilation
        os.makedirs(src_dll_dir, exist_ok=True)
        try:
            with open(hash_file, "w") as f:
                f.write(source_hash)
        except Exception: pass

    # Always sync the (now up-to-date) binaries to the destination
    sync_plugin_files(src_plugin_dir, dest_plugin_dir, verbose)
    return True, "C++ Plugin successfully synchronized and installed!"

def inject_missing_assets(uproject_path: str, verbose: bool = False):
    """Executes the exact asset copying phase."""
    project_dir = os.path.dirname(uproject_path)
    src_plugin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugins", "PalBakerEditorUtils"))
    
    src_assets_dir = os.path.join(src_plugin_dir, "Assets", "Content")
    dest_content_dir = os.path.join(project_dir, "Content")
    
    return inject_framework_assets(src_assets_dir, dest_content_dir, verbose)