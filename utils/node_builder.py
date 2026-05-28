import bpy
import os

# --- DYNAMIC PARAMETER MAPPING ---
PARAMETER_MAPPING = {
    "base_color": [
        "Base Color Texture (RGB)",
        "Base Texture",
        "BaseColor",
        "Diffuse",
        "Albedo"
    ],
    "normal": [
        "Normal Map",
        "NormalTexture",
        "Normal",
        "PM_Normals"
    ],
    "mrao": [
        "MetallicRoughnessOcclusionSpecularTexture",
        "ParameterMap",
        "MaskMap",
        "MRAO",
        "PM_SpecularMasks"
    ],
    "subsurface": [
        "Subsurface Texture",
        "Subsurface"
    ],
    "emissive": [
        "Emissive Texture",
        "PM_Emissive",
        "EmissiveTexture",
        "Emissive",
        "Fresnel Emissive Color"
    ]
}

def get_mapped_texture(params, role):
    keywords = [k.lower() for k in PARAMETER_MAPPING.get(role, [])]
    for param_name, tex_name in params.items():
        if param_name.lower() in keywords:
            return tex_name
    for param_name, tex_name in params.items():
        if any(kw in param_name.lower() for kw in keywords):
            return tex_name
    return None

def find_best_texture_match(slot_name, textures, suffix):
    """Calculates the highest token intersection between slot and file to map textures dynamically."""
    clean_slot = slot_name.lower().replace("mi_", "").replace("sk_", "")
    slot_tokens = set(clean_slot.split("_"))
    
    best_match = None
    best_score = 0.0
    
    # Conflict check mapping to prevent Eye slots from grabbing Body textures
    exclusive_keywords = {"body", "eye", "mouth", "hair", "tail", "head"}
    slot_exclusives = slot_tokens.intersection(exclusive_keywords)
    non_base_suffixes = ["_n", "_normal", "_m", "_s", "_specular", "_param", "_mrao", "_ao", "_em", "_emissive", "_rgn"]
    
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
        elif suffix == "EM":
            if any(tex_name.endswith(s) for s in ["_em", "_emissive"]):
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
            
    if best_match:
        return os.path.splitext(os.path.basename(best_match))[0]
    return None

def create_texture_node(nodes, working_dir, texture_name, loc_x, loc_y, non_color=False):
    """Unconditionally spawns an Image node. Leaves it blank if the texture file is missing."""
    tex_node = nodes.new("ShaderNodeTexImage")
    tex_node.location = (loc_x, loc_y)
    
    if texture_name:
        img_path = os.path.join(working_dir, f"{texture_name}.png")
        if os.path.exists(img_path):
            img = bpy.data.images.get(f"{texture_name}.png")
            if not img:
                img = bpy.data.images.load(img_path)
            if non_color:
                img.colorspace_settings.name = 'Non-Color'
            tex_node.image = img
            
    return tex_node

def build_eye_template(mat, params, working_dir):
    """Builds the simplified transparent eye/mouth PBR template."""
    print(f"Building simplified Eye/Mouth shader for: {mat.name}")
    mat.use_nodes = True
    mat.blend_method = 'HASHED'  # Enables alpha transparency in viewport
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output_node = nodes.new("ShaderNodeOutputMaterial")
    output_node.location = (300, 100)
    
    bsdf_node = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf_node.location = (-100, 100)
    links.new(bsdf_node.outputs["BSDF"], output_node.inputs["Surface"])

    tex_base_name = get_mapped_texture(params, "base_color")
    print(f"  -> Resolved Base Texture: {tex_base_name}")
    
    tex_node = create_texture_node(nodes, working_dir, tex_base_name, -500, 100)
    
    links.new(tex_node.outputs["Color"], bsdf_node.inputs["Base Color"])
    links.new(tex_node.outputs["Alpha"], bsdf_node.inputs["Alpha"])

def build_body_template(mat, params, working_dir):
    """Builds the complex Palworld Character Body PBR template with all nodes."""
    print(f"Building complex Body/Skeletal shader for: {mat.name}")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # --- Core Mathematical Nodes ---
    output_node = nodes.new("ShaderNodeOutputMaterial")
    output_node.location = (300, 100)
    
    bsdf_node = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf_node.location = (-100, 100)
    links.new(bsdf_node.outputs["BSDF"], output_node.inputs["Surface"])

    mix_node = nodes.new("ShaderNodeMix")
    mix_node.data_type = 'RGBA'
    mix_node.blend_type = 'MULTIPLY'
    mix_node.inputs["Factor"].default_value = 1.0
    mix_node.location = (-400, 200)
    links.new(mix_node.outputs["Result"], bsdf_node.inputs["Base Color"])

    sep_color = nodes.new("ShaderNodeSeparateColor")
    sep_color.mode = 'RGB'
    sep_color.location = (-800, 0)
    links.new(sep_color.outputs["Red"], bsdf_node.inputs["Metallic"])
    links.new(sep_color.outputs["Green"], bsdf_node.inputs["Roughness"])
    links.new(sep_color.outputs["Blue"], mix_node.inputs["B"])

    norm_map = nodes.new("ShaderNodeNormalMap")
    norm_map.location = (-400, -300)
    if hasattr(norm_map, "convention"):
        norm_map.convention = 'DIRECTX'
    links.new(norm_map.outputs["Normal"], bsdf_node.inputs["Normal"])

    # Resolve textures using the dynamic mapping
    tex_base_name = get_mapped_texture(params, "base_color")
    tex_mrao_name = get_mapped_texture(params, "mrao")
    tex_norm_name = get_mapped_texture(params, "normal")
    tex_sss_name = get_mapped_texture(params, "subsurface")
    tex_em_name = get_mapped_texture(params, "emissive")

    print(f"  -> Resolved Base Texture:  {tex_base_name}")
    print(f"  -> Resolved Normal Map:    {tex_norm_name}")
    print(f"  -> Resolved MRAO/Mask Map: {tex_mrao_name}")
    print(f"  -> Resolved Subsurface:    {tex_sss_name}")
    print(f"  -> Resolved Emissive:      {tex_em_name}")

    # Texture Nodes (created unconditionally)
    base_tex = create_texture_node(nodes, working_dir, tex_base_name, -800, 300)
    links.new(base_tex.outputs["Color"], mix_node.inputs["A"])

    if tex_mrao_name:
        mrao_tex = create_texture_node(nodes, working_dir, tex_mrao_name, -1200, 0, non_color=True)
        links.new(mrao_tex.outputs["Color"], sep_color.inputs["Color"])
    else:
        # Fallback to Color Pickers
        combine_node = nodes.new("ShaderNodeCombineColor")
        combine_node.mode = 'RGB'
        combine_node.location = (-1200, 0)
        
        color_r = nodes.new("ShaderNodeRGB")
        color_r.location = (-1500, 100)
        color_r.outputs[0].default_value = (0.0, 0.0, 0.0, 1.0)
        
        color_g = nodes.new("ShaderNodeRGB")
        color_g.location = (-1500, -100)
        color_g.outputs[0].default_value = (0.5, 0.5, 0.5, 1.0)
        
        color_b = nodes.new("ShaderNodeRGB")
        color_b.location = (-1500, -300)
        color_b.outputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
        
        links.new(color_r.outputs[0], combine_node.inputs["Red"])
        links.new(color_g.outputs[0], combine_node.inputs["Green"])
        links.new(color_b.outputs[0], combine_node.inputs["Blue"])
        links.new(combine_node.outputs["Color"], sep_color.inputs["Color"])

    norm_tex = create_texture_node(nodes, working_dir, tex_norm_name, -800, -300, non_color=True)
    links.new(norm_tex.outputs["Color"], norm_map.inputs["Color"])

    sss_tex = create_texture_node(nodes, working_dir, tex_sss_name, -400, -600)
    links.new(sss_tex.outputs["Color"], bsdf_node.inputs["Subsurface Radius"])

    # --- Dynamic Emission Connection ---
    em_tex = create_texture_node(nodes, working_dir, tex_em_name, -800, -600)
    em_socket = bsdf_node.inputs.get("Emission Color") or bsdf_node.inputs.get("Emission")
    if em_socket:
        links.new(em_tex.outputs["Color"], em_socket)
        
    # Set Emission Strength to 1.0 so that connected emissive textures are active
    em_strength = bsdf_node.inputs.get("Emission Strength")
    if em_strength:
        em_strength.default_value = 1.0

def build_materials_heuristically(working_dir):
    """Builds all materials currently loaded in Blender using naming heuristics when no JSON exists."""
    print("No JSON metadata resolved. Running Blender-side suffix matching heuristics...")
    
    # Gather all .png files inside the directory
    textures = [os.path.join(working_dir, f).replace("\\", "/") for f in os.listdir(working_dir) if f.endswith(".png")]
    print(f"Discovered disk textures: {[os.path.basename(t) for t in textures]}")
    print(f"Scene active materials: {[m.name for m in bpy.data.materials]}")
    
    for mat in bpy.data.materials:
        slot_name = mat.name
        
        # Extract matches
        tex_base = find_best_texture_match(slot_name, textures, "B")
        tex_norm = find_best_texture_match(slot_name, textures, "N")
        tex_mrao = find_best_texture_match(slot_name, textures, "M")
        tex_em = find_best_texture_match(slot_name, textures, "EM")
        
        # Combine into parameters dictionary
        params = {}
        if tex_base: params["Base Texture"] = tex_base
        if tex_norm: params["Normal Map"] = tex_norm
        if tex_mrao: params["MetallicRoughnessOcclusionSpecularTexture"] = tex_mrao
        if tex_em: params["Emissive Texture"] = tex_em
        
        build_material(mat, slot_name, params, working_dir)

def build_material(mat, parent_class, params, working_dir):
    """
    Router function to evaluate the target template.
    Checks both parent class and material slot name for 'eye' or 'mouth' indicators.
    """
    parent_lower = parent_class.lower() if parent_class else ""
    mat_name_lower = mat.name.lower() if mat and hasattr(mat, "name") else ""
    
    if "eye" in parent_lower or "mouth" in parent_lower or "eye" in mat_name_lower or "mouth" in mat_name_lower:
        build_eye_template(mat, params, working_dir)
    else:
        build_body_template(mat, params, working_dir)
