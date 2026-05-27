import unreal
import json
import os

def run_import():
    working_dir = globals().get('TARGET_FOLDER', os.getcwd())
    config_path = os.path.join(working_dir, "import_config.json")
    
    with open(config_path, "r") as f:
        config = json.load(f)

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    ue_path = config["ue_target_path"]
    folder_name = ue_path.split("/")[-1]

    # PRE-WIPE CACHE
    if config.get("fbx_file") and os.path.exists(config["fbx_file"]):
        fbx_base_name = os.path.splitext(os.path.basename(config['fbx_file']))[0]
        
        sk_path = f"{ue_path}/SK_{fbx_base_name}"
        if unreal.EditorAssetLibrary.does_asset_exist(sk_path):
            unreal.EditorAssetLibrary.delete_asset(sk_path)
            
        pa_path = f"{ue_path}/PA_{folder_name}_PhysicsAsset"
        if unreal.EditorAssetLibrary.does_asset_exist(pa_path):
            unreal.EditorAssetLibrary.delete_asset(pa_path)
            
        skel_path = f"/Game/Pal/Model/Character/Skeleton/{folder_name}/SK_{folder_name}_Skeleton"
        if unreal.EditorAssetLibrary.does_asset_exist(skel_path):
            unreal.EditorAssetLibrary.delete_asset(skel_path)
            
        # FIXED: Delete the stale Animation Blueprint so that it is forced 
        # to regenerate and link directly to the newly imported skeleton's GUID.
        anim_bp_path = f"/Game/Pal/Model/Character/Skeleton/{folder_name}/{folder_name}_BP"
        if unreal.EditorAssetLibrary.does_asset_exist(anim_bp_path):
            unreal.EditorAssetLibrary.delete_asset(anim_bp_path)
            
    for json_file in config["mi_jsons"]:
        mi_name = os.path.basename(json_file).replace('.json', '')
        mi_path = f"{ue_path}/{mi_name}"
        if unreal.EditorAssetLibrary.does_asset_exist(mi_path):
            unreal.EditorAssetLibrary.delete_asset(mi_path)

    # 1. IMPORT TEXTURES
    for png in config["textures"]:
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

    # 2. IMPORT FBX & GENERATE ASSETS natively at 1.0 Scale
    target_asset_path = ""
    target_phys_path = ""
    
    if config.get("fbx_file") and os.path.exists(config["fbx_file"]):
        fbx_filename = os.path.basename(config['fbx_file'])
        fbx_base_name = os.path.splitext(fbx_filename)[0]
        fbx_import_name = f"SK_{fbx_base_name}"
        target_asset_path = f"{ue_path}/{fbx_import_name}"
        
        print(f"Importing skeletal mesh: {fbx_filename} as {fbx_import_name}")
        fbx_task = unreal.AssetImportTask()
        fbx_task.set_editor_property('filename', config["fbx_file"])
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

        # RELOCATE SKELETON
        auto_skeleton_path = f"{ue_path}/{fbx_import_name}_Skeleton"
        target_skeleton_path = f"/Game/Pal/Model/Character/Skeleton/{folder_name}/SK_{folder_name}_Skeleton"
        
        if unreal.EditorAssetLibrary.does_asset_exist(auto_skeleton_path):
            unreal.EditorAssetLibrary.make_directory(f"/Game/Pal/Model/Character/Skeleton/{folder_name}")
            if unreal.EditorAssetLibrary.does_asset_exist(target_skeleton_path):
                unreal.EditorAssetLibrary.delete_asset(target_skeleton_path)
            unreal.EditorAssetLibrary.rename_asset(auto_skeleton_path, target_skeleton_path)

        # RENAME PHYSICS ASSET
        auto_phys_path = f"{ue_path}/{fbx_import_name}_PhysicsAsset"
        target_phys_path = f"{ue_path}/PA_{folder_name}_PhysicsAsset"
        
        if unreal.EditorAssetLibrary.does_asset_exist(auto_phys_path):
            if unreal.EditorAssetLibrary.does_asset_exist(target_phys_path):
                unreal.EditorAssetLibrary.delete_asset(target_phys_path)
            unreal.EditorAssetLibrary.rename_asset(auto_phys_path, target_phys_path)

    # 3. CREATE MATERIAL INSTANCES
    mi_assets = []
    for json_file in config["mi_jsons"]:
        print(f"Creating material instance: {os.path.basename(json_file)}")
        with open(json_file, 'r') as f:
            mi_data = json.load(f)
            
        asset_name = os.path.basename(json_file).replace('.json', '')
        factory = unreal.MaterialInstanceConstantFactoryNew()
        mi_asset = asset_tools.create_asset(asset_name, ue_path, unreal.MaterialInstanceConstant.static_class(), factory)
        
        is_raw_fmodel = isinstance(mi_data, list) and len(mi_data) > 0 and "Properties" in mi_data[0]
        parent_path = ""

        if is_raw_fmodel and "Parent" in mi_data[0]["Properties"]:
            raw_path = mi_data[0]["Properties"]["Parent"]["ObjectPath"]
            if "Pal/Content/" in raw_path:
                parent_path = "/Game/" + raw_path.split("Pal/Content/")[1].split(".")[0]
        
        if not parent_path:
            lower_name = asset_name.lower()
            if "eye" in lower_name or "mouth" in lower_name:
                parent_path = "/Game/Pal/Material/Character/Common/MI_PalLit_CharacterEyeBase"
            elif "hair" in lower_name:
                parent_path = "/Game/Pal/Material/Character/Common/MI_PalLit_CharacterHairBase"
            else:
                parent_path = "/Game/Pal/Material/Character/Common/MI_PalLit_CharacterBodyBase"

        parent_mat = unreal.EditorAssetLibrary.load_asset(parent_path)
        if parent_mat:
            unreal.MaterialEditingLibrary.set_material_instance_parent(mi_asset, parent_mat)

        if is_raw_fmodel:
            props = mi_data[0]["Properties"]
            for vp in props.get("VectorParameterValues", []):
                name = vp["ParameterInfo"]["Name"]
                val = vp["ParameterValue"]
                color_val = unreal.LinearColor(val.get("R", 0), val.get("G", 0), val.get("B", 0), val.get("A", 1))
                unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi_asset, name, color_val)
                
            for sp in props.get("ScalarParameterValues", []):
                name = sp["ParameterInfo"]["Name"]
                val = sp["ParameterValue"]
                unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi_asset, name, val)
                
            for tp in props.get("TextureParameterValues", []):
                name = tp["ParameterInfo"]["Name"]
                obj_name = tp["ParameterValue"]["ObjectName"]
                tex_asset_name = obj_name.split("'")[1]
                loaded_tex = unreal.EditorAssetLibrary.load_asset(f"{ue_path}/{tex_asset_name}")
                if loaded_tex:
                    unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(mi_asset, name, loaded_tex)
        else:
            colors = mi_data.get("Parameters", {}).get("Colors", {})
            for c_name, rgba in colors.items():
                color_val = unreal.LinearColor(rgba["R"], rgba["G"], rgba["B"], rgba["A"])
                unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi_asset, c_name, color_val)
            scalars = mi_data.get("Parameters", {}).get("Scalars", {})
            for s_name, val in scalars.items():
                unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi_asset, s_name, val)
            textures = mi_data.get("Textures", {})
            for t_name, t_path in textures.items():
                tex_asset_name = t_path.split('.')[-1]
                loaded_tex = unreal.EditorAssetLibrary.load_asset(f"{ue_path}/{tex_asset_name}")
                if loaded_tex:
                    unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(mi_asset, t_name, loaded_tex)

        unreal.EditorAssetLibrary.save_loaded_asset(mi_asset)
        mi_assets.append((asset_name.lower(), mi_asset))

    # 4. ATTACH MATERIALS & PHYSICS TO THE MESH
    if target_asset_path:
        mesh = unreal.EditorAssetLibrary.load_asset(target_asset_path)
        if mesh:
            print("Linking Materials and Physics Asset...")
            
            saved_phys = unreal.EditorAssetLibrary.load_asset(target_phys_path)
            if saved_phys:
                try:
                    mesh.set_editor_property('physics_asset', saved_phys)
                except Exception:
                    pass
            
            new_materials = []
            skel_materials = mesh.get_editor_property('materials')
            
            for skel_mat in skel_materials:
                slot_name = str(skel_mat.get_editor_property('material_slot_name')).lower()
                
                for mi_name, mi_asset in mi_assets:
                    if ("body" in mi_name and "body" in slot_name) or \
                       ("eye" in mi_name and "eye" in slot_name) or \
                       ("mouth" in mi_name and "mouth" in slot_name) or \
                       ("hair" in mi_name and "hair" in slot_name):
                        skel_mat.set_editor_property('material_interface', mi_asset)
                        break
                        
                new_materials.append(skel_mat)
            
            mesh.set_editor_property('materials', new_materials)
            unreal.EditorAssetLibrary.save_loaded_asset(mesh)

    # 5. AUTOMATED RIGGING (SPRING BONES AND OFFSETS)
    json_path = os.path.join(working_dir, "bone_data.json")
    if os.path.exists(json_path):
        print("Checking for Animation Blueprint to apply advanced rigging...")
        anim_bp = None
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        
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
                
        # GENERATE NEW BLUEPRINT IF NOT FOUND
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
                else:
                    print("C++ Rigging module returned false.")
            except Exception as e:
                print(f"Failed to execute rigging setup: {e}")

    print("Flushing all generated assets to disk...")
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(save_map_packages=False, save_content_packages=True)
    print(f"--- IMPORT COMPLETE ---")

run_import()