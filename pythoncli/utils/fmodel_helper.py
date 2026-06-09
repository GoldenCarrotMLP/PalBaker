# utils/fmodel_helper.py
import os
import json
import shutil

def harvest_texture_references(json_data):
    """
    Yields tuples of (parameter_name, ue_path) from various FModel JSON formats.
    """
    if isinstance(json_data, dict):
        if "Textures" in json_data and isinstance(json_data["Textures"], dict):
            for param, path in json_data["Textures"].items():
                if isinstance(path, str):
                    yield param, path
        
        props = json_data.get("Properties", {})
        for tpv in props.get("TextureParameterValues", []):
            param_name = tpv.get("ParameterInfo", {}).get("Name")
            param_val = tpv.get("ParameterValue", {})
            if isinstance(param_val, dict):
                path = param_val.get("ObjectPath") or param_val.get("ObjectName")
                if param_name and path:
                    yield param_name, path
            elif isinstance(param_val, str):
                if param_name:
                    yield param_name, param_val

        params = json_data.get("Parameters", {})
        if isinstance(params, dict):
            if "Textures" in params and isinstance(params["Textures"], dict):
                for param, path in params["Textures"].items():
                    if isinstance(path, str):
                        yield param, path

    elif isinstance(json_data, list):
        for item in json_data:
            if isinstance(item, dict) and "Properties" in item:
                props = item["Properties"]
                for tpv in props.get("TextureParameterValues", []):
                    param_name = tpv.get("ParameterInfo", {}).get("Name")
                    param_val = tpv.get("ParameterValue", {})
                    if isinstance(param_val, dict):
                        path = param_val.get("ObjectPath") or param_val.get("ObjectName")
                        if param_name and path:
                            yield param_name, path
                    elif isinstance(param_val, str):
                        if param_name:
                            yield param_name, param_val


def clean_ue_path(ue_path: str) -> str:
    """
    Strips type-wrappers, quotes, package suffixes, and object index markers.
    """
    if "'" in ue_path:
        ue_path = ue_path.split("'")[1]
    
    if "." in ue_path:
        parts = ue_path.split(".")
        last_part = parts[-1]
        main_path = parts[0]
        if os.path.basename(main_path) == last_part or last_part.isdigit():
            ue_path = main_path
        else:
            ue_path = main_path
            
    ue_path = ue_path.replace("\\", "/").strip("/")
    return ue_path


def find_physical_texture(fmodel_root: str, ue_path: str) -> str | None:
    """
    Resolves virtual package paths to actual image files on disk.
    """
    cleaned = clean_ue_path(ue_path)
    rel_path = cleaned
    if rel_path.startswith("Pal/Content/"):
        rel_path = rel_path.replace("Pal/Content/", "Exports/Pal/Content/")
    elif rel_path.startswith("Game/"):
        rel_path = rel_path.replace("Game/", "Exports/Pal/Content/")
    elif rel_path.startswith("/Game/"):
        rel_path = rel_path.replace("/Game/", "Exports/Pal/Content/")
        
    candidates = []
    if "/" in rel_path or "\\" in rel_path:
        base_candidates = [rel_path]
        if "Monster" in rel_path and "Pending Monster" not in rel_path:
            base_candidates.append(rel_path.replace("/Monster/", "/Pending Monster/"))
        if "Pending Monster" in rel_path:
            base_candidates.append(rel_path.replace("/Pending Monster/", "/Monster/"))
            
        for bc in base_candidates:
            norm_bc = os.path.normpath(bc)
            candidates.append(os.path.join(fmodel_root, norm_bc))
            
    extensions = [".png", ".tga", ".jpg", ".jpeg"]
    for cand in candidates:
        for ext in extensions:
            full_path = cand + ext
            if os.path.exists(full_path):
                return full_path
                
    filename = os.path.basename(cleaned)
    if filename:
        search_dir = os.path.join(fmodel_root, "Exports", "Pal", "Content", "Pal", "Model", "Character")
        if os.path.exists(search_dir):
            for root, _, files in os.walk(search_dir):
                for f in files:
                    name_without_ext, ext = os.path.splitext(f)
                    if name_without_ext.lower() == filename.lower() and ext.lower() in extensions:
                        return os.path.join(root, f)
                        
    return None


def search_for_json(fmodel_root: str, filename: str) -> str | None:
    """
    Performs a recursive search starting from the Character base folder 
    for the specified filename.
    """
    search_dir = os.path.join(fmodel_root, "Exports", "Pal", "Content", "Pal", "Model", "Character")
    if not os.path.exists(search_dir):
        return None
        
    for root, _, files in os.walk(search_dir):
        for f in files:
            if f.lower() == filename.lower():
                return os.path.join(root, f)
    return None


def resolve_and_copy_material_json(material_name: str, fmodel_dir: str, fmodel_root: str) -> dict | None:
    """
    Finds a material JSON across fmodel output, extracts texture mappings, 
    copies missing files locally, and returns the constructed material mapping block.
    """
    target_file = f"{material_name}.json"
    local_path = os.path.join(fmodel_dir, target_file)
    
    # Check locally first, fallback to recursive search
    json_path = local_path if os.path.exists(local_path) else search_for_json(fmodel_root, target_file)
    
    if not json_path or not os.path.exists(json_path):
        print(f"  [Failure] Could not resolve JSON for material: {material_name}", flush=True)
        return None
        
    print(f"  [Resolved] Material JSON found at: {json_path}", flush=True)
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  Error reading resolved JSON: {e}", flush=True)
        return None

    parent_class = "CharacterBodyBase"
    if isinstance(data, dict):
        if "Properties" in data:
            props = data["Properties"]
            if "Parent" in props:
                parent_class = props["Parent"].get("ObjectName", "CharacterBodyBase")
        elif "Parameters" in data:
            props = data.get("Parameters", {}).get("Properties", {})
            if "Parent" in props:
                parent_class = props["Parent"].get("ObjectName", "CharacterBodyBase")
            elif "parent_class" in data:
                parent_class = data["parent_class"]
    elif isinstance(data, list) and len(data) > 0:
        props = data[0].get("Properties", {})
        if "Parent" in props:
            parent_class = props["Parent"].get("ObjectName", "CharacterBodyBase")

    if "Material'" in parent_class or "MaterialInstanceConstant'" in parent_class:
        parent_class = parent_class.split("'")[1]

    parameters = {}
    harvested = list(harvest_texture_references(data))
    
    for param_name, ue_path in harvested:
        cleaned = clean_ue_path(ue_path)
        tex_filename = os.path.basename(cleaned)
        parameters[param_name] = tex_filename

        # Perform the asset pulling and copy
        local_exists = any(os.path.exists(os.path.join(fmodel_dir, f"{tex_filename}{ext}")) for ext in [".png", ".tga", ".jpg", ".jpeg"])
        if not local_exists:
            physical_path = find_physical_texture(fmodel_root, ue_path)
            if physical_path and os.path.exists(physical_path):
                dest_path = os.path.join(fmodel_dir, f"{tex_filename}{os.path.splitext(physical_path)[1]}")
                print(f"  -> Copying missing dependency: {os.path.basename(physical_path)} -> {fmodel_dir}", flush=True)
                try:
                    shutil.copy2(physical_path, dest_path)
                except Exception as e:
                    print(f"  Failed copy: {e}", flush=True)
            else:
                print(f"  ⚠️ Shared asset path missing: {ue_path}", flush=True)

    return {
        "parent_class": parent_class,
        "parameters": parameters
    }


def preprocess_fmodel_textures(fmodel_dir: str, fmodel_root: str):
    """
    Preprocess existing local folder JSON configurations before running Blender.
    """
    if not os.path.exists(fmodel_dir):
        return

    print("Preprocessing existing local FModel materials...", flush=True)
    materials_metadata = {}

    for file in os.listdir(fmodel_dir):
        if not file.endswith(".json") or file in [".palbaker_state.json", "import_config.json", "materials_metadata.json", "bone_data.json"]:
            continue
            
        mat_name = os.path.splitext(file)[0]
        resolved = resolve_and_copy_material_json(mat_name, fmodel_dir, fmodel_root)
        if resolved:
            materials_metadata[mat_name] = resolved

    if materials_metadata:
        meta_path = os.path.join(fmodel_dir, "materials_metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(materials_metadata, f, indent=4)