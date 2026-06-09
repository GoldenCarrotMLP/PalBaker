# utils/scanner.py
import os
import json
from .state import is_ue_modified, is_source_modified
from .names import get_localized_name, load_names_map
from .audio_helper import get_pal_sound_metadata

def scan_character_folders(base_path: str, target_folder: str | None = None) -> dict:
    """Recursively finds all leaf directories containing .blend, .uasset, .psk, or .json files."""
    discovered = {}
    if not base_path or not os.path.exists(base_path):
        return discovered
        
    if target_folder:
        categories = ["Monster", "Pending Monster", "Player", "NPC", "Palmi", "Normal", "RaidMonster", "RaidBoss"]
        for cat in categories:
            test_path = os.path.join(base_path, cat, target_folder)
            if os.path.exists(test_path):
                has_assets = any(f.endswith(('.blend', '.uasset', '.json', '.fbx', '.psk', '.png')) for f in os.listdir(test_path))
                if has_assets:
                    discovered[target_folder] = os.path.abspath(test_path)
                    return discovered
        return discovered 
        
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ["Skeleton", "PalActorBP", "Animation"]]
        has_assets = any(f.endswith(('.blend', '.uasset', '.json', '.fbx', '.psk', '.png')) for f in files)
        if has_assets:
            folder_name = os.path.basename(root)
            if folder_name not in ["Character", "Monster", "NPC", "Player", "Palmi", "Normal", "WwiseAudio", "Media", "sources"]:
                if folder_name in discovered:
                    has_primary_new = any(f.endswith(('.psk', '.blend', '.png')) for f in files)
                    if has_primary_new:
                        discovered[folder_name] = os.path.abspath(root)
                else:
                    discovered[folder_name] = os.path.abspath(root)
                    
    return discovered

def get_mod_info(settings: dict, target_mod: str | None = None):
    fmodel_base = settings.get("fmodel_output", "")
    uproject = settings.get("uproject", "")
    palworld_exe = settings.get("palworld_exe", "")

    ue_base = ""
    if uproject and os.path.exists(uproject):
        ue_base = os.path.join(os.path.dirname(uproject), "Content", "Pal", "Model", "Character")

    fmodel_monsters = os.path.join(fmodel_base, "Exports", "Pal", "Content", "Pal", "Model", "Character", "Monster") if fmodel_base else ""
    fmodel_altermatic = os.path.join(fmodel_base, "Exports", "Pal", "Content", "Palbaker", "Model", "Character") if fmodel_base else ""

    # Physical scans
    f_root_scan = os.path.join(fmodel_base, "Exports", "Pal", "Content", "Pal", "Model", "Character") if fmodel_base else ""
    discovered_fmodel = scan_character_folders(f_root_scan, target_mod)
    discovered_altermatic = scan_character_folders(fmodel_altermatic, target_mod)
    discovered_ue = scan_character_folders(ue_base, target_mod)

    names_map = load_names_map()
    
    # Merge physical folders and master database names
    all_names = set(list(discovered_fmodel.keys()) + list(discovered_altermatic.keys()) + list(discovered_ue.keys()))
    
    # Scan for custom Pals created via the Creator tab
    creator_dir = os.path.normpath(os.path.join(fmodel_base, "Exports", "Pal", "Content", "Palbaker", "Creator")) if fmodel_base else ""
    custom_pals = []
    if creator_dir and os.path.exists(creator_dir):
        try:
            custom_pals = [f.split("_creator.json")[0] for f in os.listdir(creator_dir) if f.endswith("_creator.json")]
        except Exception:
            pass

    if target_mod:
        if target_mod in names_map:
            all_names.add(target_mod)
        if target_mod in custom_pals:
            all_names.add(target_mod)
    else:
        all_names.update(names_map.keys())
        all_names.update(custom_pals)

    monsters = {}
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
        fmodel_path = data["fmodel_path"]
        has_fmodel = bool(fmodel_path) and os.path.exists(fmodel_path)
        
        # If it is not extracted, but is neither a vanilla Pal nor a custom creator Pal, skip it
        is_vanilla_or_creator = (name in names_map) or (name in custom_pals)
        if not has_fmodel and not is_vanilla_or_creator:
            continue

        badges = []
        fmodel_altermatic_path = data["fmodel_altermatic_path"]
        ue_path = data["ue_path"]
        
        # Calculate predicted fmodel path if it does not exist on disk yet
        active_pak_path = ""
        ue_modified = False
        ue_modified_files = []
        source_modified = False
        if not has_fmodel:
            fmodel_path = os.path.normpath(os.path.join(fmodel_monsters, name))
            data["fmodel_path"] = fmodel_path
            
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
                            v["has_base_blend"] = has_blend
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
                    "base_type": "vanilla",
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

        # --- SEPARATED CUSTOM VS VANILLA ICON CHECK ---
        custom_icon_path = os.path.join(fmodel_path, f"T_{name}_icon_normal.png") if has_fmodel else ""
        has_custom_icon = os.path.exists(custom_icon_path) if custom_icon_path else False

        vanilla_icon_path = ""
        if fmodel_base:
            vanilla_icon_path = os.path.normpath(os.path.join(
                fmodel_base, "Exports", "Pal", "Content", "Pal", "Texture", "PalIcon", "Normal", f"T_{name}_icon_normal.png"
            ))
        has_vanilla_icon = os.path.exists(vanilla_icon_path) if vanilla_icon_path else False

        if has_custom_icon:
            data["icon_path"] = custom_icon_path
            data["has_icon"] = True
            data["is_custom_icon"] = True
        elif has_vanilla_icon:
            data["icon_path"] = vanilla_icon_path
            data["has_icon"] = True
            data["is_custom_icon"] = False
        else:
            data["icon_path"] = ""
            data["has_icon"] = False
            data["is_custom_icon"] = False

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
        active_pak_path = ""
        ue_modified = False
        ue_modified_files = []
        source_modified = False
        if not has_fmodel:
            badges.append(("UNEXTRACTED", "#E53935"))
        else:
            if not has_blend:
                badges.append(("RAW", "#333333"))
            if has_blend:
                badges.append(("SOURCE", "#2196F3"))
            if has_ue:
                badges.append(("UE ASSETS", "#FF9800"))
            if is_altermatic_active:
                badges.append(("ALTERMATIC", "#008080"))

            source_modified = is_source_modified(fmodel_path) if has_blend else False
            if source_modified:
                badges.append(("SRC CHANGED", "#0D47A1"))

            ue_modified_files = is_ue_modified(fmodel_path, ue_path) if has_ue else []
            ue_modified = len(ue_modified_files) > 0
            if ue_modified:
                badges.append(("MODIFIED", "#D32F2F"))

        # Persistent status checks
        pak_status = "Unpacked"
        active_pak_path = ""
        ue_modified = False
        ue_modified_files = []
        source_modified = False
        if not has_fmodel:
            pak_status = "Unextracted"
        else:
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
            else:
                active_pak_path = ""

        data["badges"] = badges
        data["pak_status"] = pak_status
        data["pak_path"] = active_pak_path if has_fmodel else ""
        data["ue_modified"] = ue_modified if has_fmodel else False
        data["ue_modified_files"] = ue_modified_files if has_fmodel else []
        data["source_modified"] = source_modified if has_fmodel else False
        data["has_fmodel"] = has_fmodel
        data["has_blend"] = has_blend
        data["has_ue"] = has_ue
        data["localized_name"] = get_localized_name(name)
        results.append(data)

    return sorted(results, key=lambda x: x["name"])