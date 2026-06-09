# utils/extractor/asset_cloner.py
import os
import json
from .core import extract_game_files

def extract_pal_assets(settings: dict, pal_name: str, category: str = "Monster") -> tuple[bool, str]:
    """Extracts and, if required, dynamically clones templates for standalone custom Pals."""
    fmodel_root = settings.get("fmodel_output", "")
    if not fmodel_root:
        return False, "FModel output folder is not configured."
        
    export_root = os.path.join(fmodel_root, "Exports")
    creator_json_path = os.path.normpath(os.path.join(export_root, "Pal", "Content", "Palbaker", "Creator", f"{pal_name}_creator.json"))
    
    source_pal_name = pal_name
    is_custom_pal = False
    
    if os.path.exists(creator_json_path):
        try:
            with open(creator_json_path, "r", encoding="utf-8") as f_creator:
                creator_data = json.load(f_creator)
                source_pal_name = creator_data.get("TemplateID", pal_name)
                is_custom_pal = (source_pal_name != pal_name)
        except Exception:
            pass

    pal_relative_dir = f"Pal/Content/Pal/Model/Character/{category}/{source_pal_name}"
    
    success_raw, msg_raw = extract_game_files(settings, [f"{pal_relative_dir}/*"], export_root, format_type="auto")
    if not success_raw:
        return False, f"Failed to extract and convert mesh/texture assets: {msg_raw}"
        
    success_json, msg_json = extract_game_files(settings, [f"{pal_relative_dir}/MI_*"], export_root, format_type="json")
    if not success_json:
        print(f"[Extractor] Warning: Material instance JSON extraction had issues: {msg_json}", flush=True)

    pal_dir = os.path.normpath(os.path.join(export_root, "Pal", "Content", "Pal", "Model", "Character", category, pal_name))
    source_dir = os.path.normpath(os.path.join(export_root, "Pal", "Content", "Pal", "Model", "Character", category, source_pal_name))

    if is_custom_pal and os.path.exists(source_dir) and not os.path.exists(pal_dir):
        try:
            os.rename(source_dir, pal_dir)
        except OSError as e:
            return False, f"Failed to instantiate custom Pal directory: {e}"

    if os.path.exists(pal_dir):
        redundant_extensions = (".uasset", ".uexp", ".ubulk")
        for root, _, files in os.walk(pal_dir):
            for file in files:
                file_lower = file.lower()
                
                if is_custom_pal and source_pal_name in file:
                    new_file_name = file.replace(source_pal_name, pal_name)
                    old_path = os.path.join(root, file)
                    new_path = os.path.join(root, new_file_name)
                    try:
                        os.rename(old_path, new_path)
                        file = new_file_name
                        file_lower = file.lower()
                    except OSError:
                        pass

                if is_custom_pal and file_lower.endswith(".json"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8-sig") as f_js:
                            content = f_js.read()
                        
                        updated_content = content.replace(source_pal_name, pal_name)
                        
                        with open(file_path, "w", encoding="utf-8") as f_js:
                            f_js.write(updated_content)
                    except Exception as e:
                        print(f"[Extractor Warning] Failed to update reference map for {file}: {e}", flush=True)

                if file_lower.endswith(redundant_extensions):
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                    except OSError as e:
                        print(f"[Extractor Cleanup] Warning: Failed to remove redundant asset {file}: {e}", flush=True)

    return True, f"Successfully extracted visual assets for {pal_name}."