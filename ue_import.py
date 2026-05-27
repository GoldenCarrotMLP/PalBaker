import sys
import os
import json
import unreal
import importlib

# Inject the local module path into the Unreal Python environment
palbaker_root = globals().get('PALBAKER_ROOT', '')
if palbaker_root and palbaker_root not in sys.path:
    sys.path.append(palbaker_root)

# FIXED: Force python to reload cached submodules so changes on disk are updated instantly
for module_name in ["unreal_scripts.importer", "unreal_scripts.materials", "unreal_scripts.rigging", "unreal_scripts"]:
    if module_name in sys.modules:
        try:
            importlib.reload(sys.modules[module_name])
        except Exception:
            pass

from unreal_scripts.importer import clear_cache, import_assets
from unreal_scripts.materials import build_materials, bind_materials_to_mesh
from unreal_scripts.rigging import apply_rigging

def run_pipeline():
    working_dir = globals().get('TARGET_FOLDER', os.getcwd())
    config_path = os.path.join(working_dir, "import_config.json")
    
    with open(config_path, "r") as f:
        config = json.load(f)

    ue_path = config["ue_target_path"]
    folder_name = ue_path.split("/")[-1]
    
    clear_cache(ue_path, config.get("fbx_file"), folder_name)
    
    # 1. Import meshes and textures
    target_asset_path, target_phys_path = import_assets(ue_path, config["textures"], config.get("fbx_file"), folder_name)
    
    # 2. Build material instances dynamically
    mi_assets = build_materials(ue_path, config["textures"], target_asset_path)
    
    # 3. Bind everything together
    bind_materials_to_mesh(target_asset_path, target_phys_path, mi_assets)
    
    # 4. Generate & apply rigging
    apply_rigging(working_dir, ue_path, folder_name, target_asset_path)

    print("Flushing all generated assets to disk...")
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(save_map_packages=False, save_content_packages=True)
    print("--- IMPORT COMPLETE ---")

run_pipeline()