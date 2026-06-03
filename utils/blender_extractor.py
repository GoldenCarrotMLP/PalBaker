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


def extract_metadata(output_path: str, fbx_path: str = None):
    # Resolve working settings path
    working_dir = os.path.dirname(output_path)

    # 1. Gathers Pose Bones Transformations & Physics Properties safely (Returns serialized structures)
    bones_info = translator.get_pose_bones_info("Armature")
    
    jiggle_bones = []
    offset_bones = []

    for bone in bones_info:
        if bone["is_physics"]:
            # Setup spring config
            spring_config = {
                "bone_name": bone["bone_name"],
                **bone["physics_config"]
            }
            jiggle_bones.append(spring_config)
            
        if bone["transform_data"]:
            # Setup relative transformation adjustments
            transform_config = {
                "bone_name": bone["bone_name"],
                **bone["transform_data"]
            }
            offset_bones.append(transform_config)

    # 2. Harvest skeletal mesh materials strictly following their true slot indexes
    slots_in_order = translator.get_skeletal_mesh_material_slots()

    # Create dummy mapping configurations for the sidecar
    # (Actual properties and textures are processed/baked inside adapters_base on compilations)
    materials_compile = {}
    for mat_name in slots_in_order:
        # Ignore Dots Stroke or grease pencil filters
        k_lower = mat_name.lower()
        if "dots stroke" in k_lower or mat_name.startswith("."):
            continue
        materials_compile[mat_name] = {"parent_class": "MI_PalLit_CharacterBodyBase", "textures": {}}

    # Load existing sidecar config if present to delta-merge custom material mappings
    existing_data = {}
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception:
            pass

    # Safe delta-merge of historical variables
    merged_materials = {}
    for k, v in materials_compile.items():
        merged_materials[k] = v

    if "materials" in existing_data:
        for k, v in existing_data["materials"].items():
            k_lower = k.lower()
            if "dots stroke" in k_lower or k.startswith("."):
                continue
            if k not in merged_materials:
                merged_materials[k] = v

    # Write serialized non-Blender data structure cleanly
    layout_data = {
        "jiggle_bones": jiggle_bones,
        "offset_bones": offset_bones,
        "materials": merged_materials,
        "morph_targets": []  # Morph targets are dynamically updated on sync
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(layout_data, f, indent=4)

    # 3. Handle FBX export cleanly if requested by CLI
    if fbx_path:
        translator.export_fbx(fbx_path, "Armature")


if __name__ == "__main__":
    out_json, fbx_out = parse_args()
    extract_metadata(out_json, fbx_out)