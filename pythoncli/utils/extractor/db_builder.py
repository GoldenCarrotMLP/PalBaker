# utils/extractor/db_builder.py
import os
import json
import shutil
from .core import extract_game_files

def build_pal_names_map(settings: dict) -> tuple[bool, str]:
    """Extracts, parses, and compiles all dynamic database caches and wild overworld spawner directories."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    target_map_path = os.path.join(repo_root, "pal_names_map.json")
    os.makedirs(os.path.join(repo_root, "deps"), exist_ok=True)
    
    # 1. Text Localization Table
    temp_out = os.path.join(repo_root, "temp_db_extract")
    relative_asset_path = "Pal/Content/L10N/en/Pal/DataTable/Text/DT_PalNameText_Common.uasset"
    
    success, msg = extract_game_files(settings, [relative_asset_path], temp_out, format_type="json")
    if not success:
        return False, f"Failed to extract text data table: {msg}"
        
    extracted_file_path = None
    for root, _, files in os.walk(temp_out):
        for file in files:
            if file.lower() == "dt_palnametext_common.json":
                extracted_file_path = os.path.join(root, file)
                break
        if extracted_file_path:
            break
            
    if not extracted_file_path or not os.path.exists(extracted_file_path):
        shutil.rmtree(temp_out, ignore_errors=True)
        return False, f"Extracted file not found at expected path: DT_PalNameText_Common.json"
        
    try:
        with open(extracted_file_path, "r", encoding="utf-8-sig") as f:
            raw_data = json.load(f)
            
        data_table_obj = None
        if isinstance(raw_data, list):
            for obj in raw_data:
                if obj.get("Type") == "DataTable" and "Rows" in obj:
                    data_table_obj = obj
                    break
        elif isinstance(raw_data, dict):
            if raw_data.get("Type") == "DataTable" and "Rows" in raw_data:
                data_table_obj = raw_data
                
        if not data_table_obj:
            shutil.rmtree(temp_out, ignore_errors=True)
            return False, "Extracted JSON does not contain valid DataTable Rows."
            
        raw_rows = data_table_obj["Rows"]
        transformed_rows = {}
        
        for k, v in raw_rows.items():
            clean_key = k
            if k.startswith("PAL_NAME_"):
                clean_key = k[len("PAL_NAME_"):]
                
            text_data = v.get("TextData", {})
            transformed_text_data = {
                "Namespace": text_data.get("Namespace", "DT_PalNameText_Common"),
                "Key": clean_key,
                "SourceString": text_data.get("SourceString", ""),
                "LocalizedString": text_data.get("LocalizedString", "")
            }
            
            transformed_rows[clean_key] = {
                "TextData": transformed_text_data
            }
            
        output_payload = {
            "Rows": transformed_rows
        }
        
        with open(target_map_path, "w", encoding="utf-8") as f_out:
            json.dump(output_payload, f_out, indent=4)
            
    except Exception as e:
        shutil.rmtree(temp_out, ignore_errors=True)
        return False, f"Fatal error parsing text localization: {e}"
        
    shutil.rmtree(temp_out, ignore_errors=True)

    # Dispatch modular sub-task compilers
    skill_names_lookup = _build_skills_lookup(settings, repo_root)
    partner_skill_to_pal_map = _build_monster_parameters(settings, repo_root)
    _build_vanilla_icons(settings)
    _build_active_skills_cache(settings, repo_root, skill_names_lookup)
    _build_passive_skills_cache(settings, repo_root, skill_names_lookup)
    _build_partner_skills_cache(settings, repo_root, skill_names_lookup, partner_skill_to_pal_map)
    _build_waza_learnsets_cache(settings, repo_root)
    _build_wild_spawners_cache(settings, repo_root)
    _build_camera_offsets_cache(settings, repo_root)

    return True, "Pal database metrics built and pre-cached successfully."

# --- MODULAR SUB-TASK INTERNALS ---

def _build_skills_lookup(settings: dict, repo_root: str) -> dict:
    skill_names_lookup = {}
    try:
        temp_skill_names = os.path.join(repo_root, "temp_skill_names_extract")
        success, _ = extract_game_files(
            settings,
            ["Pal/Content/L10N/en/Pal/DataTable/Text/DT_SkillNameText_Common.uasset"],
            temp_skill_names,
            format_type="json"
        )
        if success:
            raw_names_path = None
            for root, _, files in os.walk(temp_skill_names):
                for file in files:
                    if file.lower() == "dt_skillnametext_common.json":
                        raw_names_path = os.path.join(root, file)
                        break
                if raw_names_path: break
                
            if raw_names_path and os.path.exists(raw_names_path):
                with open(raw_names_path, "r", encoding="utf-8-sig") as f:
                    names_data = json.load(f)
                rows_obj = None
                for obj in (names_data if isinstance(names_data, list) else [names_data]):
                    if obj.get("Type") == "DataTable" and "Rows" in obj:
                        rows_obj = obj["Rows"]
                        break
                if rows_obj:
                    for k, v in rows_obj.items():
                        skill_names_lookup[k] = v.get("TextData", {}).get("LocalizedString", k)
        shutil.rmtree(temp_skill_names, ignore_errors=True)
    except Exception:
        pass
    return skill_names_lookup

def _build_monster_parameters(settings: dict, repo_root: str) -> dict:
    partner_skill_to_pal_map = {}
    try:
        temp_params = os.path.join(repo_root, "temp_params_extract")
        success, _ = extract_game_files(
            settings, 
            ["Pal/Content/Pal/DataTable/Character/DT_PalMonsterParameter_Common.uasset"], 
            temp_params, 
            format_type="json"
        )
        if success:
            raw_params_path = None
            for root, _, files in os.walk(temp_params):
                for file in files:
                    if file.lower() == "dt_palmonsterparameter_common.json":
                        raw_params_path = os.path.join(root, file)
                        break
                if raw_params_path: break
                
            if raw_params_path and os.path.exists(raw_params_path):
                with open(raw_params_path, "r", encoding="utf-8-sig") as f:
                    params_raw_data = json.load(f)
                rows_obj = None
                for obj in (params_raw_data if isinstance(params_raw_data, list) else [params_raw_data]):
                    if obj.get("Type") == "DataTable" and "Rows" in obj:
                        rows_obj = obj["Rows"]
                        break
                if rows_obj:
                    for pal_id_key, pal_props in rows_obj.items():
                        pskill_id = pal_props.get("PartnerSkill")
                        if pskill_id and pskill_id != "None":
                            partner_skill_to_pal_map[pskill_id] = pal_id_key

                    with open(os.path.join(repo_root, "deps", "monster_parameter_cache.json"), "w", encoding="utf-8") as f_out:
                        json.dump(rows_obj, f_out, indent=4)
        shutil.rmtree(temp_params, ignore_errors=True)
    except Exception:
        pass
    return partner_skill_to_pal_map

def _build_vanilla_icons(settings: dict):
    fmodel_base = settings.get("fmodel_output", "")
    if fmodel_base:
        try:
            icon_relative_dir = "Pal/Content/Pal/Texture/PalIcon/Normal"
            icon_export_root = os.path.join(fmodel_base, "Exports")
            success, _ = extract_game_files(
                settings,
                [f"{icon_relative_dir}/*"],
                icon_export_root,
                format_type="auto"
            )
            if success:
                extracted_icon_dir = os.path.normpath(os.path.join(icon_export_root, icon_relative_dir))
                if os.path.exists(extracted_icon_dir):
                    redundant_extensions = (".uasset", ".uexp", ".ubulk")
                    for root, _, files in os.walk(extracted_icon_dir):
                        for file in files:
                            if file.lower().endswith(redundant_extensions):
                                try: os.remove(os.path.join(root, file))
                                except OSError: pass
        except Exception:
            pass

def _build_active_skills_cache(settings: dict, repo_root: str, skill_names_lookup: dict):
    try:
        temp_skills = os.path.join(repo_root, "temp_skills_extract")
        success, _ = extract_game_files(
            settings, 
            ["Pal/Content/Pal/DataTable/Waza/DT_WazaDataTable_Common.uasset"], 
            temp_skills, 
            format_type="json"
        )
        if success:
            raw_skills_path = None
            for root, _, files in os.walk(temp_skills):
                for file in files:
                    if file.lower() == "dt_wazadatatable_common.json":
                        raw_skills_path = os.path.join(root, file)
                        break
                if raw_skills_path: break
                
            if raw_skills_path and os.path.exists(raw_skills_path):
                with open(raw_skills_path, "r", encoding="utf-8-sig") as f:
                    skills_raw_data = json.load(f)
                rows_obj = None
                for obj in (skills_raw_data if isinstance(skills_raw_data, list) else [skills_raw_data]):
                    if obj.get("Type") == "DataTable" and "Rows" in obj:
                        rows_obj = obj["Rows"]
                        break
                if rows_obj:
                    skills_cache = {}
                    for r_k, r_v in rows_obj.items():
                        waza_type = r_v.get("WazaType", "")
                        internal_id = waza_type.split("::")[1] if "::" in waza_type else waza_type
                        if not internal_id: continue
                        
                        lookup_key = f"WAZA_{internal_id}"
                        friendly_name = skill_names_lookup.get(lookup_key, internal_id)
                        
                        raw_element = r_v.get("Element", "EPalElementType::None")
                        element = raw_element.split("::")[1] if "::" in raw_element else raw_element
                        
                        raw_category = r_v.get("Category", "EPalWazaCategory::None")
                        category = raw_category.split("::")[1] if "::" in raw_category else raw_category
                        
                        skills_cache[friendly_name] = {
                            "id": internal_id,
                            "element": element,
                            "category": category,
                            "power": int(r_v.get("Power", 0)) # <-- EXTRACT THE NATIVE POWER VALUE!
                        }
                        
                    with open(os.path.join(repo_root, "deps", "active_skills_cache.json"), "w", encoding="utf-8") as f_out:
                        json.dump(skills_cache, f_out, indent=4)
        shutil.rmtree(temp_skills, ignore_errors=True)
    except Exception as e:
        print(f"Warning: Failed to compile Active Skills cache: {e}", flush=True)

def _build_passive_skills_cache(settings: dict, repo_root: str, skill_names_lookup: dict):
    try:
        temp_passives = os.path.join(repo_root, "temp_passives_extract")
        success, _ = extract_game_files(
            settings, 
            ["Pal/Content/Pal/DataTable/PassiveSkill/DT_PassiveSkill_Main_Common.uasset"], 
            temp_passives, 
            format_type="json"
        )
        if success:
            raw_passives_path = None
            for root, _, files in os.walk(temp_passives):
                for file in files:
                    if file.lower() == "dt_passiveskill_main_common.json":
                        raw_passives_path = os.path.join(root, file)
                        break
                if raw_passives_path: break
                
            if raw_passives_path and os.path.exists(raw_passives_path):
                try:
                    with open(raw_passives_path, "r", encoding="utf-8-sig") as f:
                        passives_raw_data = json.load(f)
                    rows_obj = None
                    for obj in (passives_raw_data if isinstance(passives_raw_data, list) else [passives_raw_data]):
                        if obj.get("Type") == "DataTable" and "Rows" in obj:
                            rows_obj = obj["Rows"]
                            break
                    if rows_obj:
                        passives_cache = {}
                        coop_passives_cache = {}
                        for internal_id in rows_obj.keys():
                            if internal_id.startswith("TestSkill"):
                                continue
                            lookup_key = f"PASSIVE_{internal_id}"
                            friendly_name = skill_names_lookup.get(lookup_key, internal_id)
                            
                            if friendly_name == "en Text":
                                friendly_name = internal_id
                                
                            internal_id_lower = internal_id.lower()
                            is_coop = (
                                "_ride" in internal_id_lower or
                                "partnerskill" in internal_id_lower or
                                "coop" in internal_id_lower or
                                "giveelement_" in internal_id_lower
                            )
                            if is_coop:
                                coop_passives_cache[friendly_name] = internal_id
                            else:
                                passives_cache[friendly_name] = internal_id

                        with open(os.path.join(repo_root, "deps", "passive_skills_cache.json"), "w", encoding="utf-8") as f_out:
                            json.dump(passives_cache, f_out, indent=4)
                        with open(os.path.join(repo_root, "deps", "coop_passives_cache.json"), "w", encoding="utf-8") as f_out:
                            json.dump(coop_passives_cache, f_out, indent=4)
                except Exception:
                    pass
        shutil.rmtree(temp_passives, ignore_errors=True)
    except Exception:
        pass

def _build_partner_skills_cache(settings: dict, repo_root: str, skill_names_lookup: dict, partner_skill_to_pal_map: dict):
    try:
        temp_partner = os.path.join(repo_root, "temp_partner_extract")
        success, _ = extract_game_files(
            settings, 
            ["Pal/Content/Pal/DataTable/PartnerSkill/DT_PartnerSkill.uasset"], 
            temp_partner, 
            format_type="json"
        )
        if success:
            raw_partner_path = None
            for root, _, files in os.walk(temp_partner):
                for file in files:
                    if file.lower() == "dt_partnerskill.json":
                        raw_partner_path = os.path.join(root, file)
                        break
                if raw_partner_path: break
                
            if raw_partner_path and os.path.exists(raw_partner_path):
                try:
                    with open(raw_partner_path, "r", encoding="utf-8-sig") as f:
                        partner_raw_data = json.load(f)
                    rows_obj = None
                    for obj in (partner_raw_data if isinstance(partner_raw_data, list) else [partner_raw_data]):
                        if obj.get("Type") == "DataTable" and "Rows" in obj:
                            rows_obj = obj["Rows"]
                            break
                    if rows_obj:
                        partner_cache = {}
                        for internal_id in rows_obj.keys():
                            matching_pal_id = partner_skill_to_pal_map.get(internal_id, internal_id)
                            lookup_key = f"PARTNERSKILL_{matching_pal_id}"
                            friendly_name = skill_names_lookup.get(lookup_key, internal_id)
                            partner_cache[friendly_name] = internal_id

                        with open(os.path.join(repo_root, "deps", "partner_skills_cache.json"), "w", encoding="utf-8") as f_out:
                            json.dump(partner_cache, f_out, indent=4)
                except Exception:
                    pass
        shutil.rmtree(temp_partner, ignore_errors=True)
    except Exception:
        pass

def _build_waza_learnsets_cache(settings: dict, repo_root: str):
    try:
        temp_learnset = os.path.join(repo_root, "temp_learnset_extract")
        success, _ = extract_game_files(
            settings, 
            ["Pal/Content/Pal/DataTable/Waza/DT_WazaMasterLevel_Common.uasset"], 
            temp_learnset, 
            format_type="json"
        )
        if success:
            raw_learnset_path = None
            for root, _, files in os.walk(temp_learnset):
                for file in files:
                    if file.lower() == "dt_wazamasterlevel_common.json":
                        raw_learnset_path = os.path.join(root, file)
                        break
                if raw_learnset_path: break
                
            if raw_learnset_path and os.path.exists(raw_learnset_path):
                try:
                    with open(raw_learnset_path, "r", encoding="utf-8-sig") as f:
                        learnset_raw_data = json.load(f)
                    rows_obj = None
                    for obj in (learnset_raw_data if isinstance(learnset_raw_data, list) else [learnset_raw_data]):
                        if obj.get("Type") == "DataTable" and "Rows" in obj:
                            rows_obj = obj["Rows"]
                            break
                    if rows_obj:
                        learnset_map = {}
                        for r_k, r_v in rows_obj.items():
                            pal_id_val = r_v.get("PalId", "")
                            waza_id_val = r_v.get("WazaID", "")
                            level_val = r_v.get("Level", 1)
                            clean_waza_id = waza_id_val.split("::")[1] if "::" in waza_id_val else waza_id_val
                            if pal_id_val and clean_waza_id:
                                if pal_id_val not in learnset_map:
                                    learnset_map[pal_id_val] = []
                                learnset_map[pal_id_val].append({
                                    "Level": level_val,
                                    "WazaID": clean_waza_id
                                })
                        for pid in learnset_map:
                            learnset_map[pid] = sorted(learnset_map[pid], key=lambda x: x["Level"])
                        with open(os.path.join(repo_root, "deps", "waza_master_level_cache.json"), "w", encoding="utf-8") as f_out:
                            json.dump(learnset_map, f_out, indent=4)
                except Exception as e:
                    print(f"Warning: Failed to compile Waza Master Level cache: {e}", flush=True)
        shutil.rmtree(temp_learnset, ignore_errors=True)
    except Exception:
        pass

def _build_wild_spawners_cache(settings: dict, repo_root: str):
    try:
        temp_spawners = os.path.join(repo_root, "temp_spawners_extract")
        success, _ = extract_game_files(
            settings, 
            ["Pal/Content/Pal/DataTable/Spawner/DT_PalWildSpawner.uasset"], 
            temp_spawners, 
            format_type="json"
        )
        if success:
            raw_spawners_path = None
            for root, _, files in os.walk(temp_spawners):
                for file in files:
                    if file.lower() == "dt_palwildspawner.json":
                        raw_spawners_path = os.path.join(root, file)
                        break
                if raw_spawners_path: break
                
            if raw_spawners_path and os.path.exists(raw_spawners_path):
                with open(raw_spawners_path, "r", encoding="utf-8-sig") as f:
                    spawners_raw_data = json.load(f)
                rows_obj = None
                for obj in (spawners_raw_data if isinstance(spawners_raw_data, list) else [spawners_raw_data]):
                    if obj.get("Type") == "DataTable" and "Rows" in obj:
                        rows_obj = obj["Rows"]
                        break
                if rows_obj:
                    spawner_groups = {}
                    default_spawners_map = {}
                    
                    for row_key, row_val in rows_obj.items():
                        spawner_name = row_val.get("SpawnerName")
                        if not spawner_name or spawner_name == "None":
                            continue
                        
                        if spawner_name not in spawner_groups:
                            spawner_groups[spawner_name] = set()
                            
                        spawner_type = row_val.get("SpawnerType", "")
                        is_boss = "boss" in spawner_type.lower() or "predator" in spawner_type.lower()
                        
                        for idx in range(1, 4):
                            pal_col = row_val.get(f"Pal_{idx}")
                            if pal_col and pal_col != "None":
                                from utils.names import get_localized_name
                                loc_name = get_localized_name(pal_col)
                                spawner_groups[spawner_name].add(loc_name)
                                
                                if pal_col not in default_spawners_map or (not is_boss and "dungeon" not in spawner_name.lower()):
                                    default_spawners_map[pal_col] = spawner_name
                                
                    spawners_cache = {}
                    for s_name, pals_set in spawner_groups.items():
                        prominent_list = sorted(list(pals_set))[:4]
                        if prominent_list:
                            friendly_label = f"{s_name} ({', '.join(prominent_list)})"
                        else:
                            friendly_label = s_name
                        spawners_cache[friendly_label] = s_name
                        
                    sorted_spawners_cache = dict(sorted(spawners_cache.items(), key=lambda x: x[1].lower()))
                    
                    with open(os.path.join(repo_root, "deps", "monster_spawners_cache.json"), "w", encoding="utf-8") as f_out:
                        json.dump(sorted_spawners_cache, f_out, indent=4)
                        
                    with open(os.path.join(repo_root, "deps", "monster_spawners_default_map.json"), "w", encoding="utf-8") as f_def:
                        json.dump(default_spawners_map, f_def, indent=4)
        shutil.rmtree(temp_spawners, ignore_errors=True)
    except Exception:
        pass

def _build_camera_offsets_cache(settings: dict, repo_root: str):
    """Extracts and parses UI capture camera offsets from the correct UI directory."""
    try:
        temp_camera = os.path.join(repo_root, "temp_camera_extract")
        success, _ = extract_game_files(
            settings, 
            ["Pal/Content/Pal/DataTable/UI/DT_PalUICaptureCameraOffsetData.uasset"], 
            temp_camera, 
            format_type="json"
        )
        if success:
            raw_camera_path = None
            for root, dirs, files in os.walk(temp_camera):
                for file in files:
                    if file.lower() == "dt_paluicapturecameraoffsetdata.json":
                        raw_camera_path = os.path.join(root, file)
                        break
                if raw_camera_path: break
                
            if raw_camera_path and os.path.exists(raw_camera_path):
                with open(raw_camera_path, "r", encoding="utf-8-sig") as f:
                    camera_raw_data = json.load(f)
                rows_obj = None
                for obj in (camera_raw_data if isinstance(camera_raw_data, list) else [camera_raw_data]):
                    if obj.get("Type") == "DataTable" and "Rows" in obj:
                        rows_obj = obj["Rows"]
                        break
                if rows_obj:
                    with open(os.path.join(repo_root, "deps", "camera_offsets_cache.json"), "w", encoding="utf-8") as f_out:
                        json.dump(rows_obj, f_out, indent=4)
        shutil.rmtree(temp_camera, ignore_errors=True)
    except Exception as e:
        print(f"Warning: Failed to compile UICaptureCameraOffsetData cache: {e}", flush=True)