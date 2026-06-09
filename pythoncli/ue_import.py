# ue_import.py
import sys
import os
import json
import unreal  # type: ignore

palbaker_root = globals().get('PALBAKER_ROOT', '')
if palbaker_root and palbaker_root not in sys.path:
    sys.path.append(palbaker_root)

for k in list(sys.modules.keys()):
    if k.startswith("unreal_scripts"):
        del sys.modules[k]

from unreal_scripts.importer import clear_cache, import_assets
from unreal_scripts.materials import build_materials, bind_materials_to_mesh
from unreal_scripts.rigging import apply_rigging

def run_pipeline():
    working_dir = globals().get('TARGET_FOLDER', os.getcwd())
    config_path = os.path.join(working_dir, "import_config.json")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    ue_path = config["ue_target_path"]
    folder_name = ue_path.split("/")[-1]
    
    template_id = config.get("template_id")
    is_custom_pal = config.get("is_custom_pal", False)
    
    clear_cache(ue_path, config.get("fbx_file"), folder_name, is_custom_pal)
    
    # 1. Import meshes and textures (Using parent skeleton if custom pal)
    target_asset_path, target_phys_path = import_assets(ue_path, config["textures"], config.get("fbx_file"), folder_name, template_id, is_custom_pal)
    
    icon_file = config.get("icon_file")
    if icon_file:
        from unreal_scripts.importer import import_icon
        import_icon(icon_file, "/Game/Pal/Texture/PalIcon/Normal")

    # 2. Build material instances dynamically
    bone_data_file = config.get("bone_data_file", "bone_data.json")
    sidecar_json_path = os.path.join(working_dir, bone_data_file)
    
    mi_assets = build_materials(ue_path, sidecar_json_path, config["textures"], target_asset_path)
    
    # 3. Bind everything together
    bind_materials_to_mesh(target_asset_path, target_phys_path, mi_assets)
    
    # 4. Generate & apply rigging (Compiling the AnimBP against the parent's skeleton)
    apply_rigging(working_dir, ue_path, folder_name, target_asset_path, bone_data_file, template_id, is_custom_pal)

    print("Flushing all generated assets to disk...")
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(save_map_packages=False, save_content_packages=True)
    print("--- IMPORT COMPLETE ---")

run_pipeline()