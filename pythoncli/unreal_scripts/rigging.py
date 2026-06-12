# unreal_scripts/rigging.py
import unreal  # type: ignore
import os

def apply_rigging(working_dir, ue_path, import_name, folder_name, target_asset_path, bone_data_file="bone_data.json", template_id=None, is_custom_pal=False):
    json_path = os.path.join(working_dir, bone_data_file)
    if not os.path.exists(json_path):
        return

    print(f"Checking for Animation Blueprint to apply advanced rigging to: {target_asset_path}")
    anim_bp = None
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    
    # Derive name and directory from the target mesh asset path directly
    mesh_name = target_asset_path.split("/")[-1]
    base_mesh_name = mesh_name.replace("SK_", "")
    bp_name = f"{base_mesh_name}_BP"
    
    if "Palbaker" in target_asset_path:
        target_bp_dir = "/".join(target_asset_path.split("/")[:-1])
    else:
        target_bp_dir = f"/Game/Pal/Model/Character/Skeleton/{folder_name}"
        
    target_bp_path = f"{target_bp_dir}/{bp_name}"
    
    # Target parent skeleton for correct animation compilation using folder_name
    target_skeleton_name = template_id if (is_custom_pal and template_id) else folder_name
    skeleton_path = f"/Game/Pal/Model/Character/Skeleton/{target_skeleton_name}/SK_{target_skeleton_name}_Skeleton"

    if unreal.EditorAssetLibrary.does_asset_exist(target_bp_path):
        print(f"Cleaning old Animation Blueprint for fresh rebuild: {target_bp_path}")
        unreal.EditorAssetLibrary.delete_asset(target_bp_path)
        
    print(f"Generating new custom Animation Blueprint: {target_bp_path} against {skeleton_path}")
    skel = unreal.EditorAssetLibrary.load_asset(skeleton_path)
    if skel:
        factory = unreal.AnimBlueprintFactory()
        factory.set_editor_property('target_skeleton', skel)
        unreal.EditorAssetLibrary.make_directory(target_bp_dir)
        anim_bp = asset_tools.create_asset(bp_name, target_bp_dir, unreal.AnimBlueprint.static_class(), factory)
        if anim_bp:
            print(f"Successfully generated new Animation Blueprint: {bp_name}")
    else:
        print(f"ERROR: Cannot create Animation Blueprint because skeleton {skeleton_path} is missing.")
            
    if anim_bp:
        print(f"Applying PalBaker rigging setup to: {anim_bp.get_name()}")
        try:
            success = unreal.AnimScriptingLibrary.apply_pal_baker_rigging(anim_bp, json_path)
            if success:
                print("Rigging applied and compiled successfully.")
                
                # Bind this newly generated AnimBlueprint to the Skeletal Mesh's Post-Process slot
                loaded_mesh = unreal.EditorAssetLibrary.load_asset(target_asset_path)
                
                bp_name = anim_bp.get_name()
                bp_path_name = anim_bp.get_path_name().split(".")[0]
                class_path = f"{bp_path_name}.{bp_name}_C"
                
                gen_class = unreal.load_class(None, class_path)
                if gen_class and loaded_mesh:
                    loaded_mesh.set_editor_property('post_process_anim_blueprint', gen_class)
                    unreal.EditorAssetLibrary.save_loaded_asset(loaded_mesh)
                    print(f"Successfully bound {gen_class.get_name()} to Mesh: {loaded_mesh.get_name()}!")
                else:
                    print("Failed to load generated blueprint class or skeletal mesh target.")
        except Exception as e:
            print(f"Failed to execute rigging setup: {e}")