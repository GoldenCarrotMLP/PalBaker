# utils/altermatic_helper.py
import os
import json
import re
import subprocess

# Optimized Python command injected into headless Blender to extract material slots and shape keys
BLENDER_EXTRACTOR_SCRIPT = (
    "import bpy, json; "
    "mesh_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH']; "
    "slots = list(set(slot.name for obj in mesh_objs for slot in obj.material_slots if slot.name)); "
    "morphs = list(set(kb.name for obj in mesh_objs if obj.data.shape_keys for kb in obj.data.shape_keys.key_blocks if kb.name != 'Basis')); "
    "print('ALTERMATIC_METADATA_START' + json.dumps({'slots': slots, 'morphs': morphs}) + 'ALTERMATIC_METADATA_END')"
)

def get_virtual_path_for_file(absolute_path: str) -> str:
    clean_path = absolute_path.replace("\\", "/")
    marker = "Pal/Content/"
    if marker in clean_path:
        relative_part = clean_path.split(marker, 1)[1]
        folder_part = "/".join(relative_part.split("/")[:-1]).replace(" ", "_")
        return f"/Game/{folder_part}"
    return ""

def get_blend_files_for_context(fmodel_altermatic_dir: str | None, fmodel_dir: str | None = "") -> list[str]:
    blend_files = []
    if fmodel_dir and os.path.exists(fmodel_dir):
        for f in os.listdir(fmodel_dir):
            if f.endswith(".blend"):
                blend_files.append(f)
                
    if fmodel_altermatic_dir and os.path.exists(fmodel_altermatic_dir):
        for f in os.listdir(fmodel_altermatic_dir):
            if f.endswith(".blend") and f not in blend_files:
                blend_files.append(f)
                
    return blend_files

def get_available_materials_for_context(fmodel_root: str, fmodel_altermatic_dir: str | None, character_id: str, category: str = "Monster") -> list[str]:
    materials = []
    paths_to_check = []

    if fmodel_root:
        base_dir = os.path.join(fmodel_root, "Exports", "Pal", "Content", "Pal", "Model", "Character", category, character_id)
        if os.path.exists(base_dir):
            paths_to_check.append(base_dir)

    if fmodel_altermatic_dir and os.path.exists(fmodel_altermatic_dir):
        paths_to_check.append(fmodel_altermatic_dir)

    for directory in paths_to_check:
        for f in os.listdir(directory):
            if f.endswith("_blend.json"):
                sidecar_path = os.path.join(directory, f)
                try:
                    with open(sidecar_path, "r", encoding="utf-8") as f_var:
                        data = json.load(f_var)
                        mats = data.get("materials", {})
                        for mat_name in mats.keys():
                            if mat_name and mat_name not in materials:
                                materials.append(mat_name)
                except json.JSONDecodeError as e:
                    print(f"Warning: Corrupted sidecar JSON {sidecar_path}: {e}")
                except Exception as e:
                    print(f"Warning: Failed to read sidecar {sidecar_path}: {e}")

    if not materials:
        materials = [
            f"MI_{character_id}_Body_Latex",
            f"MI_{character_id}_Body_Shiny",
            f"MI_{character_id}_Body_Gold"
        ]

    return sorted(materials)

def extract_blend_metadata(blender_path: str, blend_file_path: str) -> dict:
    if not blender_path or not os.path.exists(blender_path):
        return {"slots": [], "morphs": []}
    if not blend_file_path or not os.path.exists(blend_file_path):
        return {"slots": [], "morphs": []}

    cmd = [
        blender_path,
        "-b",
        blend_file_path,
        "--python-expr",
        BLENDER_EXTRACTOR_SCRIPT
    ]

    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=creation_flags
        )
        
        match = re.search(r"ALTERMATIC_METADATA_START(.*?)ALTERMATIC_METADATA_END", result.stdout)
        if match:
            return json.loads(match.group(1))
    except Exception as e:
        print(f"Error extracting metadata from Blender: {e}")

    return {"slots": [], "morphs": []}

def delta_merge_sidecar(existing_data: dict, fresh_slots: list[str], fresh_morphs: list[str]) -> dict:
    synced = {
        "Gender": existing_data.get("Gender", "None"),
        "IsRarePal": bool(existing_data.get("IsRarePal", False)),
        "SkinName": existing_data.get("SkinName", ""),
        "ReqTrait": list(existing_data.get("ReqTrait", [])),
        "PrefTrait": list(existing_data.get("PrefTrait", [])),
        "MaterialOverrides": {}, 
        "MorphTarget": []
    }

    if "jiggle_bones" in existing_data:
        synced["jiggle_bones"] = existing_data["jiggle_bones"]
    if "offset_bones" in existing_data:
        synced["offset_bones"] = existing_data["offset_bones"]
    if "materials" in existing_data:
        synced["materials"] = existing_data["materials"]

    old_overrides = existing_data.get("MaterialOverrides", {})
    for slot_name in fresh_slots:
        if slot_name in old_overrides:
            synced["MaterialOverrides"][slot_name] = old_overrides[slot_name]

    old_morphs = {m["Target"]: m for m in existing_data.get("MorphTarget", []) if "Target" in m}
    for morph_name in fresh_morphs:
        if morph_name in old_morphs:
            synced["MorphTarget"].append(old_morphs[morph_name])
        else:
            synced["MorphTarget"].append({
                "Target": morph_name,
                "Type": "None"
            })

    return synced

def sync_sidecar_metadata(blender_path: str, blend_file_path: str) -> dict:
    root_dir = os.path.dirname(blend_file_path)
    base_name = os.path.splitext(os.path.basename(blend_file_path))[0]
    sidecar_path = os.path.join(root_dir, f"{base_name}_blend.json")

    existing_data = {}
    if os.path.exists(sidecar_path):
        try:
            with open(sidecar_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"ERROR: Sidecar JSON corrupted at {sidecar_path}: {e}")
        except Exception as e:
            print(f"Warning: Could not read {sidecar_path}: {e}")

    fresh_metadata = extract_blend_metadata(blender_path, blend_file_path)
    synced_data = delta_merge_sidecar(
        existing_data, 
        fresh_metadata.get("slots", []), 
        fresh_metadata.get("morphs", [])
    )

    try:
        with open(sidecar_path, "w", encoding="utf-8") as f:
            json.dump(synced_data, f, indent=4)
    except PermissionError as e:
        print(f"ERROR: Permission denied writing sidecar. {e}")
    except Exception as e:
        print(f"ERROR: Failed to save sidecar {sidecar_path}: {e}")

    return synced_data

def compile_unified_altermatic_json(monster_name: str, altermatic_staging_dir: str, swap_json_dir: str) -> tuple[bool, str]:
    manifest_name = f"{monster_name}_altermatic.json"
    manifest_path = os.path.join(altermatic_staging_dir, manifest_name)

    if not os.path.exists(manifest_path):
        return True, "No Altermatic variants manifest detected to compile."

    try:
        with open(manifest_path, "r", encoding="utf-8") as f_man:
            manifest_data = json.load(f_man)
        variants_data = manifest_data.get("variants", {})
        
        variants_list = []
        if isinstance(variants_data, dict):
            for k, v in variants_data.items():
                v["label"] = k
                variants_list.append(v)
        elif isinstance(variants_data, list):
            variants_list = variants_data
            
    except Exception as e:
        return False, f"Failed to read Altermatic manifest: {e}"

    category = "Monster"
    parts = altermatic_staging_dir.replace("\\", "/").split("/")
    if "Character" in parts:
        idx = parts.index("Character")
        if idx + 1 < len(parts):
            category = parts[idx + 1]

    swaps_array = []

    # Detect if this is a custom standalone pal to prefix MOD_
    fmodel_root = ""
    if "Exports" in parts:
        exp_idx = parts.index("Exports")
        fmodel_root = "/".join(parts[:exp_idx+1])
    else:
        fmodel_root = os.path.normpath(os.path.join(altermatic_staging_dir, "..", "..", "..", "..", "..", ".."))

    creator_json = os.path.join(fmodel_root, "Pal", "Content", "Palbaker", "Creator", f"{monster_name}_creator.json")
    is_custom_pal = os.path.exists(creator_json)
    
    final_character_id = f"MOD_{monster_name}" if is_custom_pal else monster_name

    for v in variants_list:
        # We skip 'base' if it's vanilla, because the game's blueprint naturally holds it.
        # But if it's custom, the game's blueprint holds the template parent (e.g. Chillet),
        # so Altermatic MUST mesh-swap the base to Furret!
        if v.get("is_base") and not is_custom_pal:
            continue

        try:
            mat_replace_list = []
            slots_order = []
            
            if v.get("is_base") and is_custom_pal:
                # Custom standalone Pal - Base Mesh Resolution
                cat_sanitized = category.replace(" ", "_")
                mesh_resolved_path = f"/Game/Pal/Model/Character/{cat_sanitized}/{monster_name}/SK_{monster_name}"
                sidecar_path = os.path.join(fmodel_root, "Pal", "Content", "Pal", "Model", "Character", category, monster_name, f"{monster_name}_blend.json")
            else:
                # Standard Altermatic custom variant resolution
                blend_base_name = os.path.splitext(v["SkeletonSource"])[0]
                blend_file_path = os.path.join(altermatic_staging_dir, f"{blend_base_name}.blend")
                sidecar_path = os.path.join(altermatic_staging_dir, f"{blend_base_name}_blend.json")

                clean_path = blend_file_path.replace("\\", "/")
                marker = "Pal/Content/"
                if marker in clean_path:
                    relative_part = clean_path.split(marker, 1)[1]
                    sk_name = blend_base_name if blend_base_name.startswith("SK_") else f"SK_{blend_base_name}"
                    relative_virtual_dir = "/".join(relative_part.split("/")[:-1]).replace(" ", "_")
                    mesh_resolved_path = f"/Game/{relative_virtual_dir}/{sk_name}"
                else:
                    cat_sanitized = category.replace(" ", "_")
                    mesh_resolved_path = f"/Game/Palbaker/Model/Character/{cat_sanitized}/{monster_name}/SK_{blend_base_name}"

            if os.path.exists(sidecar_path):
                try:
                    with open(sidecar_path, "r", encoding="utf-8") as f_side:
                        sidecar_data = json.load(f_side)
                        slots_order = list(sidecar_data.get("materials", {}).keys())
                except Exception:
                    pass

            if not slots_order:
                slots_order = ["mi_body", "mi_eye", "mi_mouth"]

            slots_order_lower = [s.lower() for s in slots_order]

            material_overrides = v.get("MaterialOverrides", {})
            for slot_name, mat_override_name in material_overrides.items():
                slot_name_lower = slot_name.lower()
                if slot_name_lower in slots_order_lower and mat_override_name:
                    idx = slots_order_lower.index(slot_name_lower)
                    mat_resolved_dir = get_virtual_path_for_file(sidecar_path)
                    resolved_mat_path = f"{mat_resolved_dir}/{mat_override_name}"
                    mat_replace_list.append({
                        "Index": str(idx),
                        "MatPath": resolved_mat_path
                    })

            compiled_swap = {
                "CharacterID": final_character_id,
                "SkelMeshPath": mesh_resolved_path,
                "Gender": v.get("Gender", "None")
            }

            if v.get("IsRarePal"):
                compiled_swap["IsRarePal"] = "True"
            if v.get("SkinName"):
                compiled_swap["SkinName"] = v["SkinName"]
            if v.get("ReqTrait"):
                compiled_swap["ReqTrait"] = v["ReqTrait"]
            if v.get("PrefTrait"):
                compiled_swap["PrefTrait"] = v["PrefTrait"]
            if mat_replace_list:
                compiled_swap["MatReplace"] = mat_replace_list

            compiled_morphs = []
            for m in v.get("MorphTarget", []):
                if m.get("Type") == "Static" and "Set" in m:
                    compiled_morphs.append({
                        "Target": m["Target"],
                        "Set": m["Set"]
                    })
                elif m.get("Type") == "Random":
                    compiled_morphs.append({
                        "Target": m["Target"],
                        "Min": m.get("Min", 0.0),
                        "Max": m.get("Max", 1.0),
                        "Type": m.get("Type", "Free")
                    })
            if compiled_morphs:
                compiled_swap["MorphTarget"] = compiled_morphs

            swaps_array.append(compiled_swap)
        except Exception as e:
            print(f"Altermatic Mod Builder Warning: Skipping corrupted variant compilation: {e}", flush=True)

    output_structure = {
        "PackName": f"PalBaker-{monster_name} Replacer Pack",
        "SkelMeshSwap": swaps_array
    }

    os.makedirs(swap_json_dir, exist_ok=True)
    target_path = os.path.join(swap_json_dir, f"palbaker-{monster_name}.json")

    try:
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(output_structure, f, indent=4)
        return True, f"SUCCESS: Compiled and deployed Altermatic config to {target_path}"
    except Exception as e:
        return False, f"Failed to write deployment JSON: {e}"

def load_traits_database() -> dict:
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_path = os.path.normpath(os.path.join(root_dir, "deps", "passive_skills_cache.json"))
    
    if not os.path.exists(target_path):
        fallback_path = os.path.normpath(os.path.join(root_dir, "traits_db.json"))
        if os.path.exists(fallback_path):
            target_path = fallback_path
            
    if not os.path.exists(target_path):
        return {}
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load traits database: {e}")
        return {}