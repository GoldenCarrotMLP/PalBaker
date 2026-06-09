# utils/blender_reconstruct.py
import sys
import os
import json

# Inject paths into Blender context to allow importing from utils package
current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Ensure the parent directory is in path so we can import 'fmodel_helper' and 'node_builder'
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import strictly from the dynamic translation facade (NO direct 'bpy' imports allowed!)
from blender_utils import translator
import node_builder
from fmodel_helper import resolve_and_copy_material_json

def parse_args():
    args = []
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
    
    fbx_path = None
    blend_path = None
    for i, arg in enumerate(args):
        if arg == "--fbx" and i + 1 < len(args):
            fbx_path = args[i + 1]
        elif arg == "--output" and i + 1 < len(args):
            blend_path = args[i + 1]
    return fbx_path, blend_path

def reconstruct_materials(working_dir):
    """
    Constructs materials loaded into Blender. If materials are missing configurations 
    locally, it performs a search across FModel folders to resolve dependencies dynamically.
    """
    fmodel_root = working_dir
    parts = os.path.normpath(working_dir).replace("\\", "/").split("/")
    
    # Find index of "Exports"
    if "Exports" in parts:
        exp_idx = parts.index("Exports")
        fmodel_root = "/".join(parts[:exp_idx])
    
    meta_path = os.path.join(working_dir, "materials_metadata.json")
    
    metadata = {}
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load local materials_metadata: {e}")

    # Gathers slots list in the exact skeletal mesh index order
    active_materials = translator.get_skeletal_mesh_material_slots()
    print(f"Discovered active mesh materials in Blender: {active_materials}")

    updated_meta = False

    for mat_name in active_materials:
        # Ignore dummy Blender default material
        if mat_name.lower() == "material":
            continue
            
        # Clean naming variant formatting (e.g. MI_Body.001 -> MI_Body)
        clean_name = mat_name.split(".")[0]
        
        # If this material doesn't have local metadata, perform parent-wide pull
        if clean_name not in metadata:
            print(f"Missing local configuration for '{clean_name}'. Executing dynamic search...", flush=True)
            resolved = resolve_and_copy_material_json(clean_name, working_dir, fmodel_root)
            if resolved:
                metadata[clean_name] = resolved
                updated_meta = True

    # Save resolved metadata locally to optimize subsequent pipeline runs
    if updated_meta:
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4)
        except Exception as e:
            print(f"Warning: Failed to write updated materials_metadata: {e}")

    print(f"Resolved Metadata Keys: {list(metadata.keys()) if metadata else 'None'}")

    if metadata:
        for mat_name in active_materials:
            if mat_name.lower() == "material":
                continue
                
            clean_name = mat_name.split(".")[0]
            data = metadata.get(clean_name)
            if data:
                parent_class = data.get("parent_class", "")
                params = data.get("parameters", {})
                node_builder.build_material(mat_name, parent_class, params, working_dir)
            else:
                print(f"Warning: No mapping resolved for '{mat_name}', running suffix fallback...")
                textures = [os.path.join(working_dir, f).replace("\\", "/") for f in os.listdir(working_dir) if f.endswith(".png")]
                tex_base = node_builder.find_best_texture_match(mat_name, textures, "B")
                tex_norm = node_builder.find_best_texture_match(mat_name, textures, "N")
                tex_mrao = node_builder.find_best_texture_match(mat_name, textures, "M")
                tex_em = node_builder.find_best_texture_match(mat_name, textures, "EM")
                
                params = {}
                if tex_base: params["Base Texture"] = tex_base
                if tex_norm: params["Normal Map"] = tex_norm
                if tex_mrao: params["MetallicRoughnessOcclusionSpecularTexture"] = tex_mrao
                if tex_em: params["Emissive Texture"] = tex_em
                
                node_builder.build_material(mat_name, mat_name, params, working_dir)
    else:
        node_builder.build_materials_heuristically(working_dir)

def reconstruct_blend(input_path, blend_path):
    if not input_path or not os.path.exists(input_path):
        print(f"ERROR: Input mesh file not found at {input_path}")
        sys.exit(1)

    input_path = os.path.abspath(input_path).replace("\\", "/")
    blend_path = os.path.abspath(blend_path).replace("\\", "/")

    if os.name == 'nt':
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            ext_path = os.path.join(appdata, "Blender Foundation", "Blender", "5.1", "extensions")
            if os.path.exists(ext_path) and ext_path not in sys.path:
                sys.path.append(ext_path)
                print(f"Injected AppData extensions path: {ext_path}")

    print("Clearing default scene objects...")
    translator.clean_scene()

    print(f"Importing mesh file: {input_path}")
    translator.import_mesh(input_path)
    
    translator.fix_hierarchy("Armature")
    
    working_dir = os.path.dirname(blend_path).replace("\\", "/")
    reconstruct_materials(working_dir)

    print(f"Saving .blend file to: {blend_path}")
    translator.save_blend(blend_path)
    print("BLEND Reconstruction Complete.")

if __name__ == "__main__":
    # FIXED: Replaced the redundant 'from blender_reconstruct import parse_args' 
    # module loader to prevent circular ImportError failures inside headless Python.
    fbx, blend = parse_args()
    reconstruct_blend(fbx, blend)