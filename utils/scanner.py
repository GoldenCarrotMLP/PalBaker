# utils/scanner.py
import os
import json
from .state import is_ue_modified, is_source_modified
from .names import get_localized_name
from .audio_helper import get_pal_sound_metadata

def scan_character_folders(base_path: str) -> dict:
    """Recursively finds all leaf directories containing .blend, .uasset, or .json files."""
    discovered = {}
    if not base_path or not os.path.exists(base_path):
        return discovered
        
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        has_assets = any(f.endswith(('.blend', '.uasset', '.json', '.fbx')) for f in files)
        if has_assets:
            folder_name = os.path.basename(root)
            if folder_name not in ["Character", "Skeleton", "PalActorBP", "Normal", "WwiseAudio", "Media", "sources"]:
                discovered[folder_name] = os.path.abspath(root)
    return discovered

def get_mod_info(settings: dict):
    fmodel_base = settings.get("fmodel_output", "")
    uproject = settings.get("uproject", "")
    palworld_exe = settings.get("palworld_exe", "")

    ue_base = ""
    if uproject and os.path.exists(uproject):
        ue_base = os.path.join(os.path.dirname(uproject), "Content", "Pal", "Model", "Character")

    fmodel_monsters = os.path.join(fmodel_base, "Exports", "Pal", "Content", "Pal", "Model", "Character") if fmodel_base else ""
    fmodel_altermatic = os.path.join(fmodel_base, "Exports", "Pal", "Content", "Palbaker", "Model", "Character") if fmodel_base else ""

    discovered_fmodel = scan_character_folders(fmodel_monsters)
    discovered_altermatic = scan_character_folders(fmodel_altermatic)
    discovered_ue = scan_character_folders(ue_base)

    monsters = {}
    all_names = set(list(discovered_fmodel.keys()) + list(discovered_altermatic.keys()) + list(discovered_ue.keys()))

    for name in all_names:
        monsters[name] = {
            "name": name,
            "fmodel_path": discovered_fmodel.get(name, ""),
            "fmodel_altermatic_path": discovered_altermatic.get(name, ""),
            "ue_path": discovered_ue.get(name, "")
        }

    results = []

    swap_json_dir = ""
    if palworld_exe and os.path.exists(palworld_exe):
        swap_json_dir = os.path.join(os.path.dirname(palworld_exe), "Pal", "Content", "Paks", "~Mods", "SwapJSON")

    for name, data in monsters.items():
        badges = []
        fmodel_path = data["fmodel_path"]
        fmodel_altermatic_path = data["fmodel_altermatic_path"]
        ue_path = data["ue_path"]
        
        has_fmodel = bool(fmodel_path)
        has_blend = has_fmodel and any(f.endswith(".blend") for f in os.listdir(fmodel_path))
        has_ue = bool(ue_path) and any(f.endswith(".uasset") for f in os.listdir(ue_path))
        
        # --- Altermatic Detection ---
        is_altermatic_active = False
        altermatic_config_path = ""
        if swap_json_dir and os.path.exists(swap_json_dir):
            target_json = os.path.join(swap_json_dir, f"palbaker-{name}.json")
            if os.path.exists(target_json):
                is_altermatic_active = True
                altermatic_config_path = target_json

        if fmodel_altermatic_path and os.path.exists(fmodel_altermatic_path):
            is_altermatic_active = True

        altermatic_variants = []
        
        # Read the active state strictly from your manifest JSON
        manifest_name = f"{name}_altermatic.json"
        manifest_path = os.path.join(fmodel_altermatic_path if fmodel_altermatic_path else fmodel_path, manifest_name)
        
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f_man:
                    loaded_structure = json.load(f_man)
                    is_altermatic_active = bool(loaded_structure.get("is_altermatic_active", False))
                    
                    variants_data = loaded_structure.get("variants", {})
                    if isinstance(variants_data, dict):
                        for k, v in variants_data.items():
                            v["label"] = k
                            v["CharacterID"] = name
                            v["is_base"] = (k == "base")
                            v["has_base_blend"] = has_blend  # Pass blend existence flag safely
                            altermatic_variants.append(v)
                    elif isinstance(variants_data, list):
                        for v in variants_data:
                            v["CharacterID"] = name
                            v["is_base"] = (v.get("label") == "base")
                            v["has_base_blend"] = has_blend
                            altermatic_variants.append(v)
            except Exception:
                pass

        if is_altermatic_active:
            # Setup canonical base entry if the active list is empty
            if not altermatic_variants:
                base_variant = {
                    "label": "base",
                    "CharacterID": name,
                    "SkeletonSource": "base",
                    "Gender": "None",
                    "IsRarePal": False,
                    "SkinName": "",
                    "ReqTrait": [],
                    "PrefTrait": [],
                    "MatReplace": [],
                    "MorphTarget": [],
                    "is_base": True,
                    "base_type": "vanilla",  # Defaults to non-destructive vanilla base fallback
                    "has_base_blend": has_blend
                }
                altermatic_variants.append(base_variant)
                
            has_base_variant = any(v.get("is_base") for v in altermatic_variants)
            if not has_base_variant:
                base_variant = {
                    "label": "base",
                    "CharacterID": name,
                    "SkeletonSource": "base",
                    "Gender": "None",
                    "IsRarePal": False,
                    "SkinName": "",
                    "ReqTrait": [],
                    "PrefTrait": [],
                    "MatReplace": [],
                    "MorphTarget": [],
                    "is_base": True,
                    "base_type": "vanilla",
                    "has_base_blend": has_blend
                }
                altermatic_variants.insert(0, base_variant)

        icon_path = ""
        if fmodel_base:
            icon_path = os.path.join(fmodel_base, "Exports", "Pal", "Content", "Pal", "Texture", "PalIcon", "Normal", f"T_{name}_icon_normal.png")
            
        has_icon = os.path.exists(icon_path) if icon_path else False
        data["icon_path"] = icon_path
        data["has_icon"] = has_icon
        data["is_altermatic_active"] = is_altermatic_active
        data["altermatic_config_path"] = altermatic_config_path
        data["altermatic_variants"] = altermatic_variants

        # --- AUDIO STATE DETECTION ---
        sound_meta = get_pal_sound_metadata(name)
        audio_overrides = {}
        
        if has_fmodel:
            audio_dir = os.path.join(fmodel_path, ".palbaker_audio", "sources")
            for cry_name in ["Normal", "Joy", "Anger", "Sorrow", "Pain", "Death"]:
                if cry_name in sound_meta:
                    audio_overrides[cry_name] = None
                    for ext in [".wav", ".mp3", ".ogg"]:
                        test_path = os.path.join(audio_dir, f"{cry_name}{ext}")
                        if os.path.exists(test_path):
                            audio_overrides[cry_name] = test_path
                            break
                        
        data["audio_overrides"] = audio_overrides
        data["sound_metadata"] = sound_meta

        # Badges state indicators
        if has_fmodel and not has_blend:
            badges.append(("RAW", "#333333"))
        if has_blend:
            badges.append(("SOURCE", "#2196F3"))
        if has_ue:
            badges.append(("UE ASSETS", "#FF9800"))
        if is_altermatic_active:
            badges.append(("ALTERMATIC", "#008080"))

        source_modified = is_source_modified(fmodel_path) if (has_fmodel and has_blend) else False
        if source_modified:
            badges.append(("SRC CHANGED", "#0D47A1"))

        ue_modified_files = is_ue_modified(fmodel_path, ue_path) if (has_fmodel and has_ue) else []
        ue_modified = len(ue_modified_files) > 0
        if ue_modified:
            badges.append(("MODIFIED", "#D32F2F"))

        # Persistent status checks
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
                for root, dirs, files in os.walk(fmodel_path):
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
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