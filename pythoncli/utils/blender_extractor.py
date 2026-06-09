# utils/blender_extractor.py
import sys
import os
import json

current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Import strictly from the dynamic translation facade (NO direct 'bpy' imports allowed!)
from blender_utils import translator

def parse_args():
    args = []
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
    
    output_json = "sidecar_blend.json"
    output_fbx = None
    for i, arg in enumerate(args):
        if arg == "--output" and i + 1 < len(args):
            output_json = args[i + 1]
            if not output_json.endswith(".json"):
                for next_arg in args[i+1:]:
                    if next_arg.endswith(".json"):
                        output_json = next_arg
                        break
        elif arg == "--fbx" and i + 1 < len(args):
            output_fbx = args[i + 1]
    return output_json, output_fbx

def extract_metadata(output_path: str, fbx_path: str | None = None):
    print(f"\n[PalBaker Extractor] Starting metadata extraction for {os.path.basename(output_path)}...", flush=True)
    working_dir = os.path.dirname(output_path)
    
    print("[PalBaker Extractor] Harvesting pose bones and physics info...", flush=True)
    bones_info = translator.get_pose_bones_info("Armature")
    
    jiggle_bones = []
    offset_bones = []

    for bone in bones_info:
        if bone["is_physics"]:
            spring_config = {
                "bone_name": bone["bone_name"],
                **bone["physics_config"]
            }
            jiggle_bones.append(spring_config)
            
        if bone["transform_data"]:
            transform_config = {
                "bone_name": bone["bone_name"],
                **bone["transform_data"]
            }
            offset_bones.append(transform_config)

    print(f"[PalBaker Extractor] Found {len(jiggle_bones)} jiggle bones and {len(offset_bones)} offset bones.", flush=True)

    slots_in_order = translator.get_skeletal_mesh_material_slots()
    materials_compile = {}

    for mat_name in slots_in_order:
        k_lower = mat_name.lower()
        if "dots stroke" in k_lower or mat_name.startswith("."):
            continue
            
        # DYNAMIC NODE-WALKING EXTRACTION
        print(f"[PalBaker Extractor] Node-walking shader tree for material: '{mat_name}'...", flush=True)
        extracted_textures = translator.get_material_textures(mat_name)
        
        # --- COMPLEXITY-BASED PARENT RESOLUTION ---
        parent_class = "MI_PalLit_CharacterEyeBase"
        
        has_complex_nodes = (
            "Normal Map" in extracted_textures or 
            "MetallicRoughnessOcclusionSpecularTexture" in extracted_textures or 
            "Emissive Texture" in extracted_textures
        )
        
        if has_complex_nodes or "body" in k_lower:
            parent_class = "MI_PalLit_CharacterBodyBase"
        elif "hair" in k_lower:
            parent_class = "MI_PalLit_CharacterHairBase"
            
        materials_compile[mat_name] = {
            "parent_class": parent_class,
            "textures": extracted_textures
        }

    # Load existing sidecar config locally and safely
    existing_data = {}
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            print("[PalBaker Extractor] Existing sidecar data successfully loaded.", flush=True)
        except Exception as e:
            print(f"[PalBaker Extractor] Warning: Failed to parse existing sidecar: {e}", flush=True)

    # If the sidecar is empty, attempt to heal/initialize from preprocessed materials_metadata.json
    if not existing_data:
        meta_path = os.path.join(working_dir, "materials_metadata.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta_mats = json.load(f)
                    existing_data = {"materials": meta_mats}
                    print(f"[PalBaker Extractor] Bridged {len(meta_mats)} preprocessed materials into sidecar.", flush=True)
            except Exception as e:
                pass

    merged_materials = {}
    for k, v in materials_compile.items():
        merged_materials[k] = v

    # Our program standard bases. If detected, we allow them to be recalculated 
    # dynamically based on the shader complexity, protecting against stale sidecar locks.
    STANDARD_BASES = {"MI_PalLit_CharacterBodyBase", "MI_PalLit_CharacterEyeBase", "MI_PalLit_CharacterHairBase"}

    if "materials" in existing_data:
        for k, v in existing_data["materials"].items():
            k_lower = k.lower()
            if "dots stroke" in k_lower or k.startswith("."):
                continue
            
            if k in merged_materials:
                # If Blender extracted no textures, fall back to preserving the sidecar's existing textures
                if not merged_materials[k]["textures"] and "textures" in v and v["textures"]:
                    merged_materials[k]["textures"] = v["textures"]
                    
                # Only preserve parent_class from sidecar if the user typed a custom override
                if "parent_class" in v and v["parent_class"] not in STANDARD_BASES:
                    merged_materials[k]["parent_class"] = v["parent_class"]
            else:
                merged_materials[k] = v

    layout_data = {
        "jiggle_bones": jiggle_bones,
        "offset_bones": offset_bones,
        "materials": merged_materials,
        "morph_targets": []
    }
    
    # Preserve existing other sidecar root parameters
    for k in ["Gender", "IsRarePal", "SkinName", "ReqTrait", "PrefTrait", "MaterialOverrides", "MorphTarget"]:
        if k in existing_data:
            layout_data[k] = existing_data[k]

    print(f"[PalBaker Extractor] Writing updated sidecar to: {os.path.basename(output_path)}", flush=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(layout_data, f, indent=4)

    if fbx_path:
        print(f"[PalBaker Extractor] Exporting FBX payload to: {os.path.basename(fbx_path)}", flush=True)
        translator.export_fbx(fbx_path, "Armature")
        
    print("[PalBaker Extractor] Extraction routine complete!\n", flush=True)

if __name__ == "__main__":
    out_json, fbx_out = parse_args()
    extract_metadata(out_json, fbx_out)