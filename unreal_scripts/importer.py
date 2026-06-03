# unreal_scripts/importer.py
import unreal
import os

def clear_cache(ue_path, fbx_file, folder_name):
    """
    Cleans up old mesh assets from memory/disk before re-importing.
    We must NEVER delete the Skeleton asset because doing so breaks active bone containers 
    and causes the Unreal Editor to crash with InBoneContainer->IsValid() assertion failures.
    Instead, we leave the Skeleton intact and let the FBX importer update/upsert it with new bones.
    """
    if fbx_file and os.path.exists(fbx_file):
        fbx_base_name = os.path.splitext(os.path.basename(fbx_file))[0]
        paths_to_delete = [
            f"{ue_path}/SK_{fbx_base_name}",
            f"{ue_path}/SK_{folder_name}"  # Clean up canonical name cache as well
        ]
        
        # Deleting the SkeletalMesh is safe, but we avoid touching the USkeleton completely
        for path in paths_to_delete:
            if unreal.EditorAssetLibrary.does_asset_exist(path):
                print(f"[PalBaker] Clearing old mesh asset from cache: {path}")
                try:
                    unreal.EditorAssetLibrary.delete_asset(path)
                except Exception as e:
                    print(f"[PalBaker] Warning: Failed to delete mesh asset: {e}")

def import_assets(ue_path, textures, fbx_file, folder_name):
    """
    Imports textures and the skeletal FBX mesh into Unreal Engine.
    Leverages Unreal's native FbxImportUI to target the existing Skeleton if it exists,
    performing a seamless bone merge (upsert) to support new jigglebones without crashing the Editor.
    """
    # 1. Textures Import
    if textures:
        print("[PalBaker] Importing textures...")
        import_tasks = []
        for png in textures:
            if os.path.exists(png):
                tex_name = os.path.splitext(os.path.basename(png))[0]
                tex_path = f"{ue_path}/{tex_name}"
                
                task = unreal.AssetImportTask()
                task.set_editor_property('filename', png)
                task.set_editor_property('destination_path', ue_path)
                task.set_editor_property('automated', True)
                task.set_editor_property('save', True)
                
                # Use Texture Factory
                task.set_editor_property('factory', unreal.TextureFactory())
                import_tasks.append(task)
                
        if import_tasks:
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(import_tasks)

    # 2. Skeletal Mesh FBX Import
    target_asset_path = ""
    target_phys_path = ""
    
    if fbx_file and os.path.exists(fbx_file):
        fbx_filename = os.path.basename(fbx_file)
        fbx_base_name = os.path.splitext(fbx_filename)[0]
        
        print(f"[PalBaker] Importing Skeletal FBX: {fbx_filename}")
        
        # Determine import asset naming convention
        is_vanilla_replace = "Palbaker" not in ue_path
        if is_vanilla_replace:
            fbx_import_name = f"SK_{folder_name}"
        else:
            fbx_import_name = f"SK_{fbx_base_name}"
            
        target_asset_path = f"{ue_path}/{fbx_import_name}"
        target_phys_path = f"{ue_path}/PA_{folder_name}_PhysicsAsset"

        # Create asset import task
        task = unreal.AssetImportTask()
        task.set_editor_property('filename', fbx_file)
        task.set_editor_property('destination_path', ue_path)
        task.set_editor_property('destination_name', fbx_import_name)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', True)
        
        # Configure FBX Import options
        import_ui = unreal.FbxImportUI()
        import_ui.set_editor_property('import_mesh', True)
        import_ui.set_editor_property('import_as_skeletal', True)
        import_ui.set_editor_property('import_materials', False)
        import_ui.set_editor_property('import_textures', False)
        import_ui.set_editor_property('import_animations', False)
        import_ui.set_editor_property('create_physics_asset', True)
        
        # Configure Skeletal Mesh details
        skel_data = import_ui.skeletal_mesh_import_data
        skel_data.set_editor_property('import_mesh_lo_ds', False)
        skel_data.set_editor_property('import_morph_targets', True)
        skel_data.set_editor_property('use_t0_as_ref_pose', True)
        
        # --- SKELETON UPSERT / MERGING LOGIC ---
        # If the character's canonical Skeleton already exists on disk, target it during
        # import so Unreal merges any new jigglebones/joint adjustments directly into it
        # rather than creating a new skeleton or crashing on deleted asset references.
        skeleton_path = f"/Game/Pal/Model/Character/Skeleton/{folder_name}/SK_{folder_name}_Skeleton"
        existing_skeleton = unreal.EditorAssetLibrary.load_asset(skeleton_path)
        if existing_skeleton:
            print(f"[PalBaker] Existing skeleton found at {skeleton_path}. Merging and updating bone container...")
            import_ui.set_editor_property('skeleton', existing_skeleton)
            skel_data.set_editor_property('import_mesh_lo_ds', False)
        else:
            print(f"[PalBaker] No existing skeleton found at {skeleton_path}. Unreal will generate a new skeleton.")

        task.set_editor_property('options', import_ui)
        
        # Execute Import
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        print(f"[PalBaker] Successfully imported skeletal mesh to: {target_asset_path}")

    return target_asset_path, target_phys_path

def import_icon(icon_file, destination_path):
    """
    Imports the Pal's UI icon texture into Unreal Engine.
    """
    if icon_file and os.path.exists(icon_file):
        print(f"[PalBaker] Importing UI Icon: {os.path.basename(icon_file)} -> {destination_path}")
        task = unreal.AssetImportTask()
        task.set_editor_property('filename', icon_file)
        task.set_editor_property('destination_path', destination_path)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', True)
        task.set_editor_property('factory', unreal.TextureFactory())
        
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        print(f"[PalBaker] Successfully imported UI Icon to: {destination_path}")