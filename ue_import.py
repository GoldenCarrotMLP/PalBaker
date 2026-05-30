import sys
import os
import json
import unreal

# Inject the local module path into the Unreal Python environment
palbaker_root = globals().get('PALBAKER_ROOT', '')
if palbaker_root and palbaker_root not in sys.path:
    sys.path.append(palbaker_root)

# FIXED: Force-delete from sys.modules to completely bypass the python "from-import" caching bug.
# This guarantees that the new 4-argument function signature is bound correctly.
for k in list(sys.modules.keys()):
    if k.startswith("unreal_scripts"):
        del sys.modules[k]

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
    
    icon_file = config.get("icon_file")
    if icon_file:
        from unreal_scripts.importer import import_icon
        import_icon(icon_file, "/Game/Pal/Texture/PalIcon/Normal")

    # 2. Build material instances dynamically (Passes the correct json_path parameters)
    json_path = os.path.join(working_dir, "bone_data.json")
    mi_assets = build_materials(ue_path, json_path, config["textures"], target_asset_path)
    
    # 3. Bind everything together
    bind_materials_to_mesh(target_asset_path, target_phys_path, mi_assets)
    
    # 4. Generate & apply rigging
    apply_rigging(working_dir, ue_path, folder_name, target_asset_path)

    print("Flushing all generated assets to disk...")
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(save_map_packages=False, save_content_packages=True)
    print("--- IMPORT COMPLETE ---")

run_pipeline()