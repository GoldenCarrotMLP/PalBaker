# unreal_scripts/importer.py
import unreal
import os

def import_icon(icon_file, ue_icon_path):
    if not icon_file or not os.path.exists(icon_file):
        return
        
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    print(f"Importing UI Icon: {os.path.basename(icon_file)}")
    
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', icon_file)
    task.set_editor_property('destination_path', ue_icon_path)
    task.set_editor_property('automated', True)
    task.set_editor_property('save', True)
    task.set_editor_property('replace_existing', True)
    
    tasks = unreal.Array(unreal.AssetImportTask)
    tasks.append(task)
    asset_tools.import_asset_tasks(tasks)
    
    imported_asset = unreal.EditorAssetLibrary.load_asset(f"{ue_icon_path}/{os.path.splitext(os.path.basename(icon_file))[0]}")
    if imported_asset:
        imported_asset.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON)
        imported_asset.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
        unreal.EditorAssetLibrary.save_loaded_asset(imported_asset)


def clear_cache(ue_path, fbx_file, folder_name):
    if fbx_file and os.path.exists(fbx_file):
        fbx_base_name = os.path.splitext(os.path.basename(fbx_file))[0]
        paths_to_delete = [
            f"{ue_path}/SK_{fbx_base_name}",
            f"{ue_path}/SK_{folder_name}",  # Clean up canonical name cache as well
            f"{ue_path}/SK_{fbx_base_name}_Skeleton",
            f"{ue_path}/PA_{folder_name}_PhysicsAsset",
            f"/Game/Pal/Model/Character/Skeleton/{folder_name}/SK_{folder_name}_Skeleton",
            f"/Game/Pal/Model/Character/Skeleton/{folder_name}/{folder_name}_BP"
        ]
        for path in paths_to_delete:
            if unreal.EditorAssetLibrary.does_asset_exist(path):
                unreal.EditorAssetLibrary.delete_asset(path)


def import_assets(ue_path, textures, fbx_file, folder_name):
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    # 1. Textures
    for png in textures:
        print(f"Importing texture: {os.path.basename(png)}")
        task = unreal.AssetImportTask()
        task.set_editor_property('filename', png)
        task.set_editor_property('destination_path', ue_path)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', True)
        task.set_editor_property('replace_existing', True)
        
        tasks = unreal.Array(unreal.AssetImportTask)
        tasks.append(task)
        asset_tools.import_asset_tasks(tasks)

    # 2. FBX
    target_asset_path = ""
    target_phys_path = ""
    if fbx_file and os.path.exists(fbx_file):
        fbx_filename = os.path.basename(fbx_file)
        
        # --- Canonical Overwrite Renamer ---
        # If we are importing into the game's native directory, force rename to SK_{PalName}
        is_vanilla_replace = "Palbaker" not in ue_path
        if is_vanilla_replace:
            fbx_import_name = f"SK_{folder_name}"
        else:
            fbx_import_name = f"SK_{os.path.splitext(fbx_filename)[0]}"
            
        target_asset_path = f"{ue_path}/{fbx_import_name}"
        
        print(f"Importing skeletal mesh: {fbx_filename} as {fbx_import_name}")
        fbx_task = unreal.AssetImportTask()
        fbx_task.set_editor_property('filename', fbx_file)
        fbx_task.set_editor_property('destination_path', ue_path)
        fbx_task.set_editor_property('destination_name', fbx_import_name)
        fbx_task.set_editor_property('automated', True)
        fbx_task.set_editor_property('save', True)
        fbx_task.set_editor_property('replace_existing', True)
        
        options = unreal.FbxImportUI()
        options.set_editor_property('import_mesh', True)
        options.set_editor_property('import_as_skeletal', True)
        options.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_SKELETAL_MESH)
        options.set_editor_property('import_materials', False)
        options.set_editor_property('import_textures', False)
        options.set_editor_property('create_physics_asset', True)
        
        options.set_editor_property('automated_import_should_detect_type', False)
        
        skel_data = unreal.FbxSkeletalMeshImportData()
        skel_data.set_editor_property('import_content_type', unreal.FBXImportContentType.FBXICT_ALL)
        skel_data.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        skel_data.set_editor_property('update_skeleton_reference_pose', False)
        skel_data.set_editor_property('use_t0_as_ref_pose', True)
        
        options.set_editor_property('skeletal_mesh_import_data', skel_data)
        fbx_task.set_editor_property('options', options)
        
        fbx_tasks = unreal.Array(unreal.AssetImportTask)
        fbx_tasks.append(fbx_task)
        asset_tools.import_asset_tasks(fbx_tasks)

        target_skeleton_dir = f"/Game/Pal/Model/Character/Skeleton/{folder_name}"
        target_skeleton_path = f"{target_skeleton_dir}/SK_{folder_name}_Skeleton"
        
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        ar.scan_paths_synchronous([ue_path])
        assets = ar.get_assets_by_path(ue_path)
        
        auto_skeleton_path = ""
        for asset in assets:
            if str(asset.asset_class_path.asset_name) == "Skeleton":
                auto_skeleton_path = str(asset.package_name)
                break
                
        if not auto_skeleton_path:
            auto_skeleton_path = f"{ue_path}/{fbx_import_name}_Skeleton"

        if unreal.EditorAssetLibrary.does_asset_exist(auto_skeleton_path):
            unreal.EditorAssetLibrary.make_directory(target_skeleton_dir)
            if unreal.EditorAssetLibrary.does_asset_exist(target_skeleton_path):
                unreal.EditorAssetLibrary.delete_asset(target_skeleton_path)
            unreal.EditorAssetLibrary.rename_asset(auto_skeleton_path, target_skeleton_path)

        auto_phys_path = f"{ue_path}/{fbx_import_name}_PhysicsAsset"
        target_phys_path = f"{ue_path}/PA_{folder_name}_PhysicsAsset"
        if unreal.EditorAssetLibrary.does_asset_exist(auto_phys_path):
            if unreal.EditorAssetLibrary.does_asset_exist(target_phys_path):
                unreal.EditorAssetLibrary.delete_asset(target_phys_path)
            unreal.EditorAssetLibrary.rename_asset(auto_phys_path, target_phys_path)

    return target_asset_path, target_phys_path