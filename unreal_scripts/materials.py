import unreal
import json
import os

def find_best_texture_match(slot_name, textures, suffix):
    """Calculates the highest token intersection between slot and file to map textures dynamically."""
    clean_slot = slot_name.lower().replace("mi_", "").replace("sk_", "")
    slot_tokens = set(clean_slot.split("_"))
    
    best_match = None
    best_score = 0.0
    
    # Conflict check mapping to prevent Eye slots from grabbing Body textures
    exclusive_keywords = {"body", "eye", "mouth", "hair", "tail", "head"}
    slot_exclusives = slot_tokens.intersection(exclusive_keywords)
    non_base_suffixes = ["_n", "_normal", "_m", "_s", "_specular", "_param", "_mrao", "_ao", "_em", "_rgn"]
    
    for tex in textures:
        tex_name = os.path.splitext(os.path.basename(tex))[0].lower()
        is_suffix_match = False
        
        if suffix == "B":
            if any(tex_name.endswith(s) for s in ["_b", "_d", "_albedo", "_basecolor"]):
                is_suffix_match = True
            elif not any(tex_name.endswith(s) for s in non_base_suffixes):
                is_suffix_match = True
        elif suffix == "N":
            if any(tex_name.endswith(s) for s in ["_n", "_normal"]):
                is_suffix_match = True
        elif suffix == "M":
            if any(tex_name.endswith(s) for s in ["_m", "_s", "_specular", "_param", "_mrao"]):
                is_suffix_match = True
                
        if not is_suffix_match:
            continue
            
        clean_tex_name = tex_name
        for s in non_base_suffixes + ["_b", "_d", "_albedo", "_basecolor"]:
            if clean_tex_name.endswith(s):
                clean_tex_name = clean_tex_name[:-len(s)]
                break
                
        if clean_tex_name.startswith("t_"):
            clean_tex_name = clean_tex_name[2:]
            
        tex_tokens = set(clean_tex_name.split("_"))
        
        # Conflict Enforcement: If texture has an exclusive keyword that the slot DOES NOT have, skip it.
        tex_exclusives = tex_tokens.intersection(exclusive_keywords)
        if tex_exclusives and not tex_exclusives.issubset(slot_exclusives):
            continue
        
        # Jaccard Similarity Score
        intersection = len(slot_tokens.intersection(tex_tokens))
        union = len(slot_tokens.union(tex_tokens))
        score = intersection / union if union > 0 else 0
        
        if score > best_score:
            best_score = score
            best_match = tex
            
    return best_match if best_score > 0 else None

def build_materials(ue_path, textures, target_asset_path):
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    mi_assets = []
    material_slots = []
    
    if target_asset_path:
        mesh = unreal.EditorAssetLibrary.load_asset(target_asset_path)
        if mesh:
            for mat in mesh.materials:
                material_slots.append(str(mat.material_slot_name))

    print("Running dynamic slot-and-suffix material binder...")
    for slot_name in material_slots:
        mi_path = f"{ue_path}/{slot_name}"
        
        # FIXED: If the asset already exists, load it. Otherwise, create it cleanly [33].
        if unreal.EditorAssetLibrary.does_asset_exist(mi_path):
            print(f"Loading existing material instance: {slot_name}")
            mi_asset = unreal.EditorAssetLibrary.load_asset(mi_path)
        else:
            print(f"Creating new material instance: {slot_name}")
            factory = unreal.MaterialInstanceConstantFactoryNew()
            mi_asset = asset_tools.create_asset(slot_name, ue_path, unreal.MaterialInstanceConstant.static_class(), factory)
            
        if not mi_asset:
            print(f"ERROR: Could not load or create material instance for slot: {slot_name}")
            continue
            
        lower_name = slot_name.lower()
        if "eye" in lower_name or "mouth" in lower_name:
            parent_path = "/Game/Pal/Material/Character/Common/MI_PalLit_CharacterEyeBase"
        elif "hair" in lower_name:
            parent_path = "/Game/Pal/Material/Character/Common/MI_PalLit_CharacterHairBase"
        else:
            parent_path = "/Game/Pal/Material/Character/Common/MI_PalLit_CharacterBodyBase"
            
        parent_mat = unreal.EditorAssetLibrary.load_asset(parent_path)
        if parent_mat:
            unreal.MaterialEditingLibrary.set_material_instance_parent(mi_asset, parent_mat)
            
        # Set accurate Palworld parameter names
        tex_b = find_best_texture_match(slot_name, textures, "B")
        if tex_b:
            loaded_tex = unreal.EditorAssetLibrary.load_asset(f"{ue_path}/{os.path.splitext(os.path.basename(tex_b))[0]}")
            if loaded_tex:
                unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(mi_asset, "Base Texture", loaded_tex)
                print(f"  Bound BaseColor: {os.path.basename(tex_b)}")
                
        tex_n = find_best_texture_match(slot_name, textures, "N")
        if tex_n:
            loaded_tex = unreal.EditorAssetLibrary.load_asset(f"{ue_path}/{os.path.splitext(os.path.basename(tex_n))[0]}")
            if loaded_tex:
                unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(mi_asset, "Normal Map", loaded_tex)
                print(f"  Bound Normal: {os.path.basename(tex_n)}")
                
        tex_m = find_best_texture_match(slot_name, textures, "M")
        if tex_m:
            loaded_tex = unreal.EditorAssetLibrary.load_asset(f"{ue_path}/{os.path.splitext(os.path.basename(tex_m))[0]}")
            if loaded_tex:
                unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(mi_asset, "MetallicRoughnessOcclusionSpecularTexture", loaded_tex)
                print(f"  Bound ParameterMap: {os.path.basename(tex_m)}")
                
        unreal.EditorAssetLibrary.save_loaded_asset(mi_asset)
        mi_assets.append((slot_name.lower(), mi_asset))

    return mi_assets

def bind_materials_to_mesh(target_asset_path, target_phys_path, mi_assets):
    if not target_asset_path:
        return
        
    mesh = unreal.EditorAssetLibrary.load_asset(target_asset_path)
    if not mesh:
        return

    print("Linking Materials and Physics Asset...")
    saved_phys = unreal.EditorAssetLibrary.load_asset(target_phys_path)
    if saved_phys:
        try:
            mesh.set_editor_property('physics_asset', saved_phys)
        except Exception:
            pass
    
    # Access the SkeletalMaterial structs array directly as properties
    skel_materials = mesh.materials
    print(f"Skeletal mesh has {len(skel_materials)} material slots.")
    
    new_materials = []
    for skel_mat in skel_materials:
        # Read struct attributes directly
        slot_name = str(skel_mat.material_slot_name).lower()
        print(f"Processing slot: {slot_name}")
        
        matched_mi = None
        for mi_name, mi_asset in mi_assets:
            if mi_name == slot_name:
                matched_mi = mi_asset
                break
                
        if not matched_mi:
            for mi_name, mi_asset in mi_assets:
                if ("body" in mi_name and "body" in slot_name) or \
                   ("eye" in mi_name and "eye" in slot_name) or \
                   ("mouth" in mi_name and "mouth" in slot_name) or \
                   ("hair" in mi_name and "hair" in slot_name):
                    matched_mi = mi_asset
                    break
                    
        if matched_mi:
            # Assign struct attributes directly
            skel_mat.material_interface = matched_mi
            print(f"  Linked slot {slot_name} -> {matched_mi.get_name()}")
        else:
            # Safeguard: Bind the master parent directly to prevent unassigned
            # "DefaultMaterial" checkerboard glitches from showing in-game.
            if "eye" in slot_name or "mouth" in slot_name:
                fallback_path = "/Game/Pal/Material/Character/Common/MI_PalLit_CharacterEyeBase"
            elif "hair" in slot_name:
                fallback_path = "/Game/Pal/Material/Character/Common/MI_PalLit_CharacterHairBase"
            else:
                fallback_path = "/Game/Pal/Material/Character/Common/MI_PalLit_CharacterBodyBase"
                
            fallback_mat = unreal.EditorAssetLibrary.load_asset(fallback_path)
            if fallback_mat:
                skel_mat.material_interface = fallback_mat
                print(f"  [Safeguard] Linked empty slot {slot_name} to Master: {fallback_mat.get_name()}")
                
        new_materials.append(skel_mat)
    
    # Write struct array directly
    mesh.materials = new_materials
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)