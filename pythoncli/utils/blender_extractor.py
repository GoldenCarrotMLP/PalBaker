# pythoncli/utils/blender_extractor.py
import sys
import os
import json

current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from blender_utils import translator
    from sidecar_helper import load_sidecar, save_sidecar
except Exception as e:
    import traceback
    print("\n❌ CRITICAL: ImportError inside Blender's python runtime!", flush=True)
    traceback.print_exc()
    sys.exit(1)

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
            
        print(f"[PalBaker Extractor] Node-walking shader tree for material: '{mat_name}'...", flush=True)
        extracted_textures = translator.get_material_textures(mat_name)
        
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

    # Centralized Loader takes care of safe parsing
    existing_data = load_sidecar(output_path)

    # If the sidecar was empty, attempt to heal/initialize from preprocessed materials_metadata.json
    if not existing_data:
        meta_path = os.path.join(working_dir, "materials_metadata.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta_mats = json.load(f)
                    existing_data["materials"] = meta_mats
            except Exception:
                pass

    # Merge materials topologically
    old_materials = existing_data.get("materials", {})
    merged_materials = {}
    STANDARD_BASES = {"MI_PalLit_CharacterBodyBase", "MI_PalLit_CharacterEyeBase", "MI_PalLit_CharacterHairBase"}

    for k, v in materials_compile.items():
        if k in old_materials:
            old_val = old_materials[k]
            # Use Blender textures, fallback to old ones if empty
            textures = v.get("textures", {})
            if not textures and old_val.get("textures"):
                textures = old_val["textures"]
            # Keep custom parent class overrides
            parent_class = old_val.get("parent_class", v.get("parent_class"))
            if parent_class not in STANDARD_BASES:
                parent_class = old_val.get("parent_class")
                
            merged_materials[k] = {
                "parent_class": parent_class,
                "textures": textures
            }
        else:
            merged_materials[k] = v

    # Preserve old keys not present in merged materials
    for k, v in old_materials.items():
        if k not in merged_materials:
            merged_materials[k] = v

    layout_data = {
        "jiggle_bones": jiggle_bones,
        "offset_bones": offset_bones,
        "materials": merged_materials,
        "morph_targets": []
    }
    
    # Preserve existing other sidecar root parameters safely
    for k in ["Gender", "IsRarePal", "SkinName", "ReqTrait", "PrefTrait", "MaterialOverrides", "MorphTarget", "preserve_materials"]:
        if k in existing_data:
            layout_data[k] = existing_data[k]

    print(f"[PalBaker Extractor] Writing updated sidecar to: {os.path.basename(output_path)}", flush=True)
    save_sidecar(output_path, layout_data)

    if fbx_path:
        print(f"[PalBaker Extractor] Exporting FBX payload to: {os.path.basename(fbx_path)}", flush=True)
        translator.export_fbx(fbx_path, "Armature")
        
    print("[PalBaker Extractor] Extraction routine complete!\n", flush=True)

if __name__ == "__main__":
    try:
        out_json, fbx_out = parse_args()
        extract_metadata(out_json, fbx_out)
    except Exception as e:
        import traceback
        print("\n❌ CRITICAL: Execution error inside Blender's python runtime!", flush=True)
        traceback.print_exc()
        sys.exit(1)