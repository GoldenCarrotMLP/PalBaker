# utils/node_builder.py
import os

# Import strictly from the dynamic translation facade (NO direct 'bpy' imports allowed!)
from blender_utils import translator

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

def build_materials_heuristically(working_dir):
    """Builds all materials currently loaded in Blender using naming heuristics when no JSON exists."""
    print("No JSON metadata resolved. Running Blender-side suffix matching heuristics...")
    
    # Gather all .png files inside the directory
    textures = [os.path.join(working_dir, f).replace("\\", "/") for f in os.listdir(working_dir) if f.endswith(".png")]
    slots_in_order = translator.get_skeletal_mesh_material_slots()
    
    for slot_name in slots_in_order:
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
        
        build_material(slot_name, slot_name, params, working_dir)

def build_material(mat_name, parent_class, params, working_dir):
    """Router function to execute the version-safe material compiler."""
    translator.compile_material_instance(mat_name, parent_class, params, working_dir)