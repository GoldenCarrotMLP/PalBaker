import os
import flet as ft
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
        
        # Determine Badges
        if has_fmodel and not has_blend:
            badges.append(("RAW", ft.Colors.GREY_700))
        if has_blend:
            badges.append(("SOURCE", ft.Colors.BLUE_700))
        if has_ue:
            badges.append(("UE ASSETS", ft.Colors.ORANGE_700))

        # Check Source Modifications
        source_modified = is_source_modified(fmodel_path) if (has_fmodel and has_blend) else False
        if source_modified:
            badges.append(("SRC CHANGED", ft.Colors.BLUE_900))

        # Check UE Modifications
        ue_modified_files = is_ue_modified(fmodel_path, ue_path) if (has_fmodel and has_ue) else []
        ue_modified = len(ue_modified_files) > 0
        
        if ue_modified:
            badges.append(("MODIFIED", ft.Colors.RED_700))

        # Determine Pack Status
        pak_status = "Unpacked"
        pak_color = ft.Colors.RED_400
        
        pak_path = ""
        if palworld_exe and os.path.exists(palworld_exe):
            pak_path = os.path.join(os.path.dirname(palworld_exe), "Pal", "Content", "Paks", "palBaker", f"{name}_P.pak")
            
        if pak_path and os.path.exists(pak_path):
            pak_mtime = os.path.getmtime(pak_path)
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
                pak_color = ft.Colors.ORANGE_400
            else:
                pak_status = "Packed"
                pak_color = ft.Colors.GREEN_400

        data["badges"] = badges
        data["pak_status"] = pak_status
        data["pak_color"] = pak_color
        data["ue_modified"] = ue_modified
        data["ue_modified_files"] = ue_modified_files
        data["source_modified"] = source_modified
        data["has_fmodel"] = has_fmodel
        data["has_blend"] = has_blend
        data["has_ue"] = has_ue
        data["localized_name"] = get_localized_name(name)
        results.append(data)

    return sorted(results, key=lambda x: x["name"])