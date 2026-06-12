# unreal_scripts/importer.py
import unreal  # type: ignore
import os

def clear_cache(ue_path, fbx_file, import_name, folder_name, is_custom_pal=False):
    """
    Cleans up old mesh assets from memory/disk before re-importing.
    If this is a Custom Pal, we ensure any rogue generated skeletons matching its name are wiped out.
    """
    if fbx_file and os.path.exists(fbx_file):
        paths_to_delete = [
            f"{ue_path}/SK_{import_name}",
            f"{ue_path}/PA_{import_name}_PhysicsAsset"
        ]
        if import_name != folder_name:
            # Clean up canonical name cache as well just in case they renamed it
            paths_to_delete.append(f"{ue_path}/SK_{folder_name}")
            paths_to_delete.append(f"{ue_path}/PA_{folder_name}_PhysicsAsset")
        
        for path in paths_to_delete:
            if unreal.EditorAssetLibrary.does_asset_exist(path):
                print(f"[PalBaker] Clearing old mesh asset from cache: {path}")
                try:
                    unreal.EditorAssetLibrary.delete_asset(path)
                except Exception as e:
                    print(f"[PalBaker] Warning: Failed to delete mesh asset: {e}")

        # Wipe any rogue custom skeletons to ensure it binds to the parent
        if is_custom_pal:
            rogue_skeleton = f"/Game/Pal/Model/Character/Skeleton/{folder_name}/SK_{folder_name}_Skeleton"
            if unreal.EditorAssetLibrary.does_asset_exist(rogue_skeleton):
                print(f"[PalBaker] Clearing rogue custom skeleton: {rogue_skeleton}")
                try:
                    unreal.EditorAssetLibrary.delete_asset(rogue_skeleton)
                except Exception:
                    pass

def import_assets(ue_path, textures, fbx_file, import_name, folder_name, template_id=None, is_custom_pal=False, import_tex=True):
    """
    Imports textures and the skeletal FBX mesh into Unreal Engine.
    Forces binding to the parent's skeleton if configured as a custom Pal.
    """
    # 1. Textures Import
    if import_tex and textures:
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
                task.set_editor_property('factory', unreal.TextureFactory())
                import_tasks.append(task)
                
        if import_tasks:
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(import_tasks)

    # 2. Skeletal Mesh FBX Import
    target_asset_path = ""
    target_phys_path = ""
    
    if fbx_file and os.path.exists(fbx_file):
        fbx_filename = os.path.basename(fbx_file)
        
        print(f"[PalBaker] Importing Skeletal FBX: {fbx_filename}")
        
        fbx_import_name = f"SK_{import_name}"
        target_asset_path = f"{ue_path}/{fbx_import_name}"
        target_phys_path = f"{ue_path}/PA_{import_name}_PhysicsAsset"

        task = unreal.AssetImportTask()
        task.set_editor_property('filename', fbx_file)
        task.set_editor_property('destination_path', ue_path)
        task.set_editor_property('destination_name', fbx_import_name)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', True)
        
        import_ui = unreal.FbxImportUI()
        import_ui.set_editor_property('import_mesh', True)
        import_ui.set_editor_property('import_as_skeletal', True)
        import_ui.set_editor_property('import_materials', False)
        import_ui.set_editor_property('import_textures', False)
        import_ui.set_editor_property('import_animations', False)
        import_ui.set_editor_property('create_physics_asset', True)
        
        skel_data = import_ui.skeletal_mesh_import_data
        skel_data.set_editor_property('import_mesh_lo_ds', False)
        skel_data.set_editor_property('import_morph_targets', True)
        skel_data.set_editor_property('use_t0_as_ref_pose', True)
        
        # --- SMART SKELETON BINDING LOGIC ---
        # Target the parent template's skeleton natively using the folder_name parameter
        target_skeleton_name = template_id if (is_custom_pal and template_id) else folder_name
        skeleton_path = f"/Game/Pal/Model/Character/Skeleton/{target_skeleton_name}/SK_{target_skeleton_name}_Skeleton"
        
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
        
        # --- VALIDATE IMPORT TYPE ---
        imported_asset = unreal.EditorAssetLibrary.load_asset(target_asset_path)
        if imported_asset:
            asset_class = imported_asset.get_class().get_name()
            if asset_class == "StaticMesh":
                raise Exception(
                    f"\n[!] FATAL ERROR: Unreal Engine imported '{fbx_filename}' as a StaticMesh instead of a SkeletalMesh!\n"
                    f"This means the FBX exporter could not find a valid Armature or vertex weights for your mesh.\n"
                    f"Please open your .blend file, ensure your mesh is parented to the 'Armature' object with bone weights, and try again."
                )

        print(f"[PalBaker] Successfully imported skeletal mesh to: {target_asset_path}")

        # Relocate the generated PhysicsAsset cleanly to its expected path
        expected_skeleton_path = skeleton_path
        expected_phys_path = target_phys_path
        
        skeleton_relocated = False
        phys_relocated = False

        imported_paths = list(task.get_editor_property('imported_object_paths'))
        for imported_path in imported_paths:
            asset = unreal.EditorAssetLibrary.load_asset(imported_path)
            if not asset: continue
            
            asset_class = asset.get_class().get_name()
            
            if asset_class == "Skeleton":
                if imported_path != expected_skeleton_path:
                    print(f"[PalBaker] Relocating generated skeleton: {imported_path} -> {expected_skeleton_path}")
                    unreal.EditorAssetLibrary.make_directory(f"/Game/Pal/Model/Character/Skeleton/{target_skeleton_name}")
                    if unreal.EditorAssetLibrary.rename_asset(imported_path, expected_skeleton_path):
                        print(f"[PalBaker] Successfully relocated skeleton to {expected_skeleton_path}!")
                skeleton_relocated = True
            
            elif asset_class == "PhysicsAsset":
                if imported_path != expected_phys_path:
                    print(f"[PalBaker] Relocating generated physics asset: {imported_path} -> {expected_phys_path}")
                    unreal.EditorAssetLibrary.rename_asset(imported_path, expected_phys_path)
                phys_relocated = True

        if not skeleton_relocated:
            generated_skeleton_path = f"{ue_path}/{fbx_import_name}_Skeleton"
            if unreal.EditorAssetLibrary.does_asset_exist(generated_skeleton_path) and generated_skeleton_path != expected_skeleton_path:
                print(f"[PalBaker] Hard Lookup: Relocating generated skeleton: {generated_skeleton_path} -> {expected_skeleton_path}")
                unreal.EditorAssetLibrary.make_directory(f"/Game/Pal/Model/Character/Skeleton/{target_skeleton_name}")
                if unreal.EditorAssetLibrary.rename_asset(generated_skeleton_path, expected_skeleton_path):
                    print(f"[PalBaker] Successfully relocated skeleton to {expected_skeleton_path}!")

        if not phys_relocated:
            generated_phys_path = f"{ue_path}/{fbx_import_name}_PhysicsAsset"
            if unreal.EditorAssetLibrary.does_asset_exist(generated_phys_path) and generated_phys_path != expected_phys_path:
                print(f"[PalBaker] Hard Lookup: Relocating generated physics asset: {generated_phys_path} -> {expected_phys_path}")
                unreal.EditorAssetLibrary.rename_asset(generated_phys_path, expected_phys_path)

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