# unreal_scripts/rigging.py
import unreal
import os

def apply_rigging(working_dir, ue_path, folder_name, target_asset_path, bone_data_file="bone_data.json"):
    json_path = os.path.join(working_dir, bone_data_file)
    if not os.path.exists(json_path):
        return

    print("Checking for Animation Blueprint to apply advanced rigging...")
    anim_bp = None
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    
    skeleton_dir = f"/Game/Pal/Model/Character/Skeleton/{folder_name}"
    
    skeleton_assets = ar.get_assets_by_path(unreal.Name(skeleton_dir), recursive=True)
    anim_bps = []
    if skeleton_assets is not None:
        anim_bps = [a for a in skeleton_assets if str(a.asset_class_path.asset_name) == "AnimBlueprint"]
    
    if anim_bps:
        anim_bp = unreal.EditorAssetLibrary.load_asset(anim_bps[0].package_name)
    else:
        search_paths = [
            f"/Game/Pal/Model/Character/Monster/{folder_name}",
            f"/Game/Palbaker/Model/Character/Monster/{folder_name}"
        ]
        for path in search_paths:
            if unreal.EditorAssetLibrary.does_directory_exist(path):
                monster_assets = ar.get_assets_by_path(unreal.Name(path), recursive=True)
                if monster_assets is not None:
                    anim_bps = [a for a in monster_assets if str(a.asset_class_path.asset_name) == "AnimBlueprint"]
                if anim_bps:
                    anim_bp = unreal.EditorAssetLibrary.load_asset(anim_bps[0].package_name)
                    break
                
    if not anim_bp:
        print(f"No Animation Blueprint found. Generating a new one for {folder_name}...")
        skeleton_path = f"/Game/Pal/Model/Character/Skeleton/{folder_name}/SK_{folder_name}_Skeleton"
        skel = unreal.EditorAssetLibrary.load_asset(skeleton_path)
        
        if skel:
            factory = unreal.AnimBlueprintFactory()
            factory.set_editor_property('target_skeleton', skel)
            bp_name = f"{folder_name}_BP"
            anim_bp = asset_tools.create_asset(bp_name, skeleton_dir, unreal.AnimBlueprint.static_class(), factory)
            if anim_bp:
                print(f"Created new Animation Blueprint: {bp_name}")
        else:
            print(f"ERROR: Cannot create Animation Blueprint because skeleton {skeleton_path} is missing.")
            
    if anim_bp:
        print(f"Applying PalBaker rigging setup to: {anim_bp.get_name()}")
        try:
            success = unreal.AnimScriptingLibrary.apply_pal_baker_rigging(anim_bp, json_path)
            if success:
                print("Rigging applied and compiled successfully.")
                
                paths_to_scan = [
                    f"/Game/Pal/Model/Character/Monster/{folder_name}",
                    f"/Game/Palbaker/Model/Character/Monster/{folder_name}"
                ]
                
                skeletal_meshes_to_bind = []
                for scan_path in paths_to_scan:
                    if unreal.EditorAssetLibrary.does_directory_exist(scan_path):
                        assets = ar.get_assets_by_path(unreal.Name(scan_path), recursive=True)
                        if assets is not None:
                            for asset in assets:
                                if str(asset.asset_class_path.asset_name) == "SkeletalMesh":
                                    loaded_mesh = unreal.EditorAssetLibrary.load_asset(asset.package_name)
                                    if loaded_mesh and loaded_mesh not in skeletal_meshes_to_bind:
                                        skeletal_meshes_to_bind.append(loaded_mesh)

                bp_name = anim_bp.get_name()
                bp_path_name = anim_bp.get_path_name().split(".")[0]
                class_path = f"{bp_path_name}.{bp_name}_C"
                
                gen_class = unreal.load_class(None, class_path)
                if gen_class and skeletal_meshes_to_bind:
                    for mesh_to_update in skeletal_meshes_to_bind:
                        mesh_to_update.set_editor_property('post_process_anim_blueprint', gen_class)
                        unreal.EditorAssetLibrary.save_loaded_asset(mesh_to_update)
                        print(f"Successfully bound {gen_class.get_name()} to Mesh: {mesh_to_update.get_name()}!")
                else:
                    print("No skeletal mesh variants found to bind.")
        except Exception as e:
            print(f"Failed to execute rigging setup: {e}")