# unreal_scripts/rigging.py
import unreal
import os

def apply_rigging(working_dir, ue_path, folder_name, target_asset_path, bone_data_file="bone_data.json"):
    json_path = os.path.join(working_dir, bone_data_file)
    if not os.path.exists(json_path):
        return

    print(f"Checking for Animation Blueprint to apply advanced rigging to: {target_asset_path}")
    anim_bp = None
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    
    # Derive name and directory from the target mesh asset path directly
    mesh_name = target_asset_path.split("/")[-1] # e.g. "SK_WeaselDragon_Ferret_Shiny"
    base_mesh_name = mesh_name.replace("SK_", "") # e.g. "WeaselDragon_Ferret_Shiny"
    bp_name = f"{base_mesh_name}_BP" # e.g. "WeaselDragon_Ferret_Shiny_BP"
    
    # If the mesh is in Palbaker (Altermatic variant), place the AnimBlueprint right next to it!
    # If it is vanilla, save it in the default skeleton folder.
    if "Palbaker" in target_asset_path:
        target_bp_dir = "/".join(target_asset_path.split("/")[:-1])
    else:
        target_bp_dir = f"/Game/Pal/Model/Character/Skeleton/{folder_name}"
        
    target_bp_path = f"{target_bp_dir}/{bp_name}"
    skeleton_path = f"/Game/Pal/Model/Character/Skeleton/{folder_name}/SK_{folder_name}_Skeleton"

    # FIXED: Always delete any stale or old variant AnimBlueprint first to prevent node piling
    if unreal.EditorAssetLibrary.does_asset_exist(target_bp_path):
        print(f"Cleaning old Animation Blueprint for fresh rebuild: {target_bp_path}")
        unreal.EditorAssetLibrary.delete_asset(target_bp_path)
        
    print(f"Generating new custom Animation Blueprint: {target_bp_path}")
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