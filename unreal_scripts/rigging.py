import unreal
import os

def apply_rigging(working_dir, ue_path, folder_name, target_asset_path):
    json_path = os.path.join(working_dir, "bone_data.json")
    if not os.path.exists(json_path):
        return

    print("Checking for Animation Blueprint to apply advanced rigging...")
    anim_bp = None
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    
    skeleton_dir = f"/Game/Pal/Model/Character/Skeleton/{folder_name}"
    skeleton_assets = ar.get_assets_by_path(skeleton_dir, recursive=True)
    anim_bps = [a for a in skeleton_assets if str(a.asset_class_path.asset_name) == "AnimBlueprint"]
    
    if anim_bps:
        anim_bp = unreal.EditorAssetLibrary.load_asset(anim_bps[0].package_name)
    else:
        monster_assets = ar.get_assets_by_path(ue_path, recursive=True)
        anim_bps = [a for a in monster_assets if str(a.asset_class_path.asset_name) == "AnimBlueprint"]
        if anim_bps:
            anim_bp = unreal.EditorAssetLibrary.load_asset(anim_bps[0].package_name)
            
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
                
                if target_asset_path:
                    mesh_to_update = unreal.EditorAssetLibrary.load_asset(target_asset_path)
                    if mesh_to_update:
                        bp_name = anim_bp.get_name()
                        bp_path_name = anim_bp.get_path_name().split(".")[0]
                        class_path = f"{bp_path_name}.{bp_name}_C"
                        
                        gen_class = unreal.load_class(None, class_path)
                        if gen_class:
                            mesh_to_update.set_editor_property('post_process_anim_blueprint', gen_class)
                            unreal.EditorAssetLibrary.save_loaded_asset(mesh_to_update)
                            print(f"Successfully bound {gen_class.get_name()} to the Mesh!")
            else:
                print("C++ Rigging module returned false.")
        except Exception as e:
            print(f"Failed to execute rigging setup: {e}")