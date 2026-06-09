# ue_export.py
import unreal  # type: ignore
import os
import json

def run_export():
    working_dir = globals().get('TARGET_FOLDER', os.getcwd())
    ue_path = globals().get('UE_PATH', '')
    overwrite = globals().get('OVERWRITE_ALL', False)
    
    if not ue_path:
        print("ERROR: UE_PATH not provided.")
        return

    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    assets = ar.get_assets_by_path(ue_path, recursive=True)

    working_dir = os.path.abspath(working_dir).replace("\\", "/")
    os.makedirs(working_dir, exist_ok=True)

    materials_metadata = {}

    # FIXED: Explicit type guard to narrow 'Array | None' to 'Array' to resolve Pylance's OptionalIterable warning
    if assets is not None:
        for asset in assets:
            asset_class = str(asset.asset_class_path.asset_name)
            
            if asset_class not in ["SkeletalMesh", "Texture2D", "MaterialInstanceConstant"]:
                continue

            try:
                loaded_asset = unreal.EditorAssetLibrary.load_asset(asset.package_name)
            except Exception as e:
                print(f"Warning: Skipping corrupted/unloadable asset {asset.package_name}: {e}")
                continue

            if not loaded_asset:
                continue

            if asset_class == "SkeletalMesh":
                base_name = loaded_asset.get_name().replace("SK_", "")
                fbx_path = f"{working_dir}/{base_name}.fbx"
                
                if not overwrite and os.path.exists(fbx_path):
                    print(f"Skipping existing FBX: {os.path.basename(fbx_path)}")
                else:
                    print(f"Exporting SkeletalMesh to: {fbx_path}")
                    task = unreal.AssetExportTask()
                    task.set_editor_property('object', loaded_asset)
                    task.set_editor_property('filename', fbx_path)
                    task.set_editor_property('automated', True)
                    task.set_editor_property('prompt', False)
                    task.set_editor_property('replace_identical', True)
                    
                    options = unreal.FbxExportOption()
                    task.set_editor_property('options', options)
                    unreal.Exporter.run_asset_export_task(task)

            elif asset_class == "Texture2D":
                png_path = f"{working_dir}/{loaded_asset.get_name()}.png"
                
                if not overwrite and os.path.exists(png_path):
                    print(f"Skipping existing Texture: {os.path.basename(png_path)}")
                else:
                    print(f"Exporting Texture2D to: {png_path}")
                    task = unreal.AssetExportTask()
                    task.set_editor_property('object', loaded_asset)
                    task.set_editor_property('filename', png_path)
                    task.set_editor_property('automated', True)
                    task.set_editor_property('prompt', False)
                    task.set_editor_property('replace_identical', True)
                    
                    unreal.Exporter.run_asset_export_task(task)

            elif asset_class == "MaterialInstanceConstant":
                # --- EXTRACT MATERIAL PROPERTIES DIRECTLY FROM UNREAL ENGINE ---
                mat_name = loaded_asset.get_name()
                
                # Extract Parent Class
                parent_name = "MI_PalLit_CharacterBodyBase"
                parent_mat = loaded_asset.get_editor_property('parent')
                if parent_mat:
                    parent_name = parent_mat.get_name()
                
                # Extract Texture Parameters
                params = {}
                tex_params = loaded_asset.get_editor_property('texture_parameter_values')
                for tex_param in tex_params:
                    param_name = str(tex_param.parameter_info.name)
                    if tex_param.parameter_value:
                        params[param_name] = tex_param.parameter_value.get_name()
                        
                materials_metadata[mat_name] = {
                    "parent_class": parent_name,
                    "parameters": params
                }

    if materials_metadata:
        meta_path = os.path.join(working_dir, "materials_metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(materials_metadata, f, indent=4)
        print(f"Exported True Material Topology Metadata to: {meta_path}")

run_export()