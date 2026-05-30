# utils/scanner.py
import os
from .state import is_ue_modified, is_source_modified
from .names import get_localized_name

def get_mod_info(settings: dict):
    fmodel_base = settings.get("fmodel_output", "")
    uproject = settings.get("uproject", "")
    palworld_exe = settings.get("palworld_exe", "")

    ue_base = ""
    if uproject and os.path.exists(uproject):
        ue_base = os.path.join(os.path.dirname(uproject), "Content", "Pal", "Model", "Character")

    fmodel_monsters = os.path.join(fmodel_base, "Exports", "Pal", "Content", "Pal", "Model", "Character") if fmodel_base else ""

    monsters = {}

    def scan_directory(base_path, source_type):
        if not base_path or not os.path.exists(base_path):
            return
        for category in ["Monster", "Pending Monster"]:
            cat_path = os.path.join(base_path, category)
            if os.path.exists(cat_path):
                for item in os.listdir(cat_path):
                    item_path = os.path.join(cat_path, item)
                    if os.path.isdir(item_path):
                        if item not in monsters:
                            monsters[item] = {"name": item, "category": category, "fmodel_path": "", "ue_path": ""}
                        monsters[item][f"{source_type}_path"] = item_path

    scan_directory(fmodel_monsters, "fmodel")
    scan_directory(ue_base, "ue")

    results = []

    for name, data in monsters.items():
        badges = []
        fmodel_path = data["fmodel_path"]
        ue_path = data["ue_path"]
        
        has_fmodel = bool(fmodel_path)
        has_blend = has_fmodel and any(f.endswith(".blend") for f in os.listdir(fmodel_path))
        has_ue = bool(ue_path) and any(f.endswith(".uasset") for f in os.listdir(ue_path))
        icon_path = ""
        if fmodel_base:
            icon_path = os.path.join(fmodel_base, "Exports", "Pal", "Content", "Pal", "Texture", "PalIcon", "Normal", f"T_{name}_icon_normal.png")
            
        has_icon = os.path.exists(icon_path) if icon_path else False
        data["icon_path"] = icon_path
        data["has_icon"] = has_icon


        if has_fmodel and not has_blend:
            badges.append(("RAW", "#333333"))  # Return hex or simple representations
        if has_blend:
            badges.append(("SOURCE", "#2196F3"))
        if has_ue:
            badges.append(("UE ASSETS", "#FF9800"))

        source_modified = is_source_modified(fmodel_path) if (has_fmodel and has_blend) else False
        if source_modified:
            badges.append(("SRC CHANGED", "#0D47A1"))

        ue_modified_files = is_ue_modified(fmodel_path, ue_path) if (has_fmodel and has_ue) else []
        ue_modified = len(ue_modified_files) > 0
        if ue_modified:
            badges.append(("MODIFIED", "#D32F2F"))

        # --- PERSISTENT THREE-STATE CHECK ---
        pak_status = "Unpacked"
        pak_path = ""
        pak_err_path = ""
        
        if palworld_exe and os.path.exists(palworld_exe):
            pak_path = os.path.join(os.path.dirname(palworld_exe), "Pal", "Content", "Paks", "palBaker", f"{name}_P.pak")
            pak_err_path = os.path.join(os.path.dirname(palworld_exe), "Pal", "Content", "Paks", "palBaker", f"{name}_err_P.pak")
            
        has_pak = os.path.exists(pak_path)
        has_pak_err = os.path.exists(pak_err_path)
        active_pak_path = pak_path if has_pak else (pak_err_path if has_pak_err else "")
        
        if active_pak_path:
            pak_mtime = os.path.getmtime(active_pak_path)
            outdated = False
            
            if has_fmodel:
                for root, _, files in os.walk(fmodel_path):
                    for f in files:
                        if f.endswith(('.blend', '.fbx', '.png', '.json')) and os.path.getmtime(os.path.join(root, f)) > pak_mtime:
                            outdated = True
            if has_ue and not outdated:
                for root, _, files in os.walk(ue_path):
                    for f in files:
                        if f.endswith('.uasset') and os.path.getmtime(os.path.join(root, f)) > pak_mtime:
                            outdated = True
                            
            if outdated:
                pak_status = "Outdated"
            elif has_pak_err:
                pak_status = "Packed with Errors"
            else:
                pak_status = "Packed"

        data["badges"] = badges
        data["pak_status"] = pak_status
        data["pak_path"] = active_pak_path
        data["ue_modified"] = ue_modified
        data["ue_modified_files"] = ue_modified_files
        data["source_modified"] = source_modified
        data["has_fmodel"] = has_fmodel
        data["has_blend"] = has_blend
        data["has_ue"] = has_ue
        data["localized_name"] = get_localized_name(name)
        results.append(data)

    return sorted(results, key=lambda x: x["name"])