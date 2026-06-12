# utils/extractor/asset_cloner.py
import os
import json
import shutil
from .core import extract_game_files

def extract_pal_assets(settings: dict, pal_name: str, category: str = "Monster") -> tuple[bool, str]:
    """
    Extracts and, if required, dynamically clones templates for standalone custom Pals.
    Uses a temporary directory to strictly avoid accidentally overwriting parent assets.
    """
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

    pal_dir = os.path.normpath(os.path.join(export_root, "Pal", "Content", "Pal", "Model", "Character", category, pal_name))
    
    if is_custom_pal:
        # Use an isolated temporary directory for safe manipulation
        temp_dir = os.path.join(fmodel_root, ".temp_palbaker_extract")
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        parent_dir = os.path.normpath(os.path.join(export_root, "Pal", "Content", "Pal", "Model", "Character", category, source_pal_name))
        has_local_parent = os.path.exists(parent_dir) and any(f.endswith((".psk", ".blend", ".png", ".fbx")) for f in os.listdir(parent_dir))
        
        if has_local_parent:
            print(f"[Asset Cloner] Local workspace found for parent '{source_pal_name}'. Cloning to temporary folder...")
            working_temp_dir = os.path.join(temp_dir, source_pal_name)
            shutil.copytree(parent_dir, working_temp_dir)
        else:
            print(f"[Asset Cloner] Extracting parent '{source_pal_name}' from game paks to temporary folder...")
            pal_relative_dir = f"Pal/Content/Pal/Model/Character/{category}/{source_pal_name}"
            
            success_raw, msg_raw = extract_game_files(settings, [f"{pal_relative_dir}/*"], temp_dir, format_type="auto")
            if not success_raw:
                shutil.rmtree(temp_dir, ignore_errors=True)
                return False, f"Failed to extract raw assets: {msg_raw}"
                
            extract_game_files(settings, [f"{pal_relative_dir}/MI_*"], temp_dir, format_type="json")
            working_temp_dir = os.path.normpath(os.path.join(temp_dir, "Pal", "Content", "Pal", "Model", "Character", category, source_pal_name))

        print(f"[Asset Cloner] Recursively renaming assets from '{source_pal_name}' to '{pal_name}'...")
        redundant_extensions = (".uasset", ".uexp", ".ubulk")
        
        if os.path.exists(working_temp_dir):
            for root, _, files in os.walk(working_temp_dir, topdown=False):
                for file in files:
                    file_lower = file.lower()
                    
                    # 1. Clean compiled uassets from the clone workspace
                    if file_lower.endswith(redundant_extensions):
                        try: os.remove(os.path.join(root, file))
                        except OSError: pass
                        continue
                    
                    # 2. Patch file contents (remapping materials inside JSONs)
                    if file_lower.endswith(".json"):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, "r", encoding="utf-8-sig") as f_js:
                                content = f_js.read()
                            # Deep search/replace references from Parent -> Child
                            updated_content = content.replace(source_pal_name, pal_name)
                            with open(file_path, "w", encoding="utf-8") as f_js:
                                f_js.write(updated_content)
                        except Exception:
                            pass
                    
                    # 3. Rename physical files (Textures, Blend files, JSONs)
                    if source_pal_name in file:
                        new_file_name = file.replace(source_pal_name, pal_name)
                        old_path = os.path.join(root, file)
                        new_path = os.path.join(root, new_file_name)
                        try: os.rename(old_path, new_path)
                        except OSError: pass

            print(f"[Asset Cloner] Moving prepared workspace to: {pal_dir}")
            if os.path.exists(pal_dir):
                shutil.rmtree(pal_dir, ignore_errors=True)
            os.makedirs(os.path.dirname(pal_dir), exist_ok=True)
            shutil.move(working_temp_dir, pal_dir)
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return True, f"Successfully cloned and configured workspace for {pal_name}."
        else:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False, f"Extracted assets missing for {source_pal_name}."

    else:
        # Standard vanilla Pal extraction
        print(f"[Asset Cloner] Extracting {pal_name} from game paks...")
        pal_relative_dir = f"Pal/Content/Pal/Model/Character/{category}/{pal_name}"
        
        success_raw, msg_raw = extract_game_files(settings, [f"{pal_relative_dir}/*"], export_root, format_type="auto")
        if not success_raw:
            return False, f"Failed to extract raw assets: {msg_raw}"
            
        extract_game_files(settings, [f"{pal_relative_dir}/MI_*"], export_root, format_type="json")
        
        # Clean redundant assets
        if os.path.exists(pal_dir):
            redundant_extensions = (".uasset", ".uexp", ".ubulk")
            for root, _, files in os.walk(pal_dir):
                for file in files:
                    if file.lower().endswith(redundant_extensions):
                        try: os.remove(os.path.join(root, file))
                        except OSError: pass
                        
        return True, f"Successfully extracted visual assets for {pal_name}."