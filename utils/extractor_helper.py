# utils/extractor_helper.py
import os
import sys
import json
import shutil
import subprocess
import glob

def get_paks_dir(palworld_exe: str) -> str | None:
    """
    Safely calculates the Palworld Paks folder directory path based on the executable path.
    Handles both root executable and Win64-Shipping executable paths.
    """
    if not palworld_exe or not os.path.exists(palworld_exe):
        return None
    
    exe_lower = palworld_exe.lower()
    if "binaries" in exe_lower:
        return os.path.normpath(os.path.join(os.path.dirname(palworld_exe), "..", "..", "Content", "Paks"))
    else:
        return os.path.normpath(os.path.join(os.path.dirname(palworld_exe), "Pal", "Content", "Paks"))

def extract_game_files(settings: dict, relative_paths: list[str], output_dir: str, format_type: str = "raw") -> tuple[bool, str]:
    """
    Runs cue4parse.exe to headlessly extract a list of game files from Palworld .pak archives.
    Allows specifying format_type (e.g. "json", "raw", "csv").
    Returns (success_boolean, status_message).
    """
    palworld_exe = settings.get("palworld_exe", "")
    paks_dir = get_paks_dir(palworld_exe)
    if not paks_dir or not os.path.exists(paks_dir):
        return False, f"Paks directory not found or Palworld.exe path is invalid: {paks_dir}"

    # --- HARD LINK ARCHIVE ISOLATION ---
    # Create an isolated temporary directory inside the game's Paks folder (guaranteeing same NTFS volume).
    # This isolates Pal-Windows* archives and ignores custom baked mods/~mods subdirectories,
    # preventing cue4parse parallel write-collision crashes on duplicate assets.
    isolated_dir = os.path.join(paks_dir, ".temp_palbaker_isolate")
    shutil.rmtree(isolated_dir, ignore_errors=True)
    os.makedirs(isolated_dir, exist_ok=True)
    
    files_linked = 0
    official_patterns = ["Pal-Windows*"]
    for pattern in official_patterns:
        for filepath in glob.glob(os.path.join(paks_dir, pattern)):
            if os.path.isfile(filepath):
                filename = os.path.basename(filepath)
                dest_link = os.path.join(isolated_dir, filename)
                try:
                    if hasattr(os, "link"):
                        os.link(filepath, dest_link)
                        files_linked += 1
                except Exception:
                    pass
                    
    # Fall back to standard paks directory if hard linking is not supported on the volume
    active_input_dir = isolated_dir if files_linked > 0 else paks_dir

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cue4parse_exe = os.path.normpath(os.path.join(repo_root, "deps", "cue4parse.exe"))
    usmap_path = os.path.normpath(os.path.join(repo_root, "deps", "Mappings.usmap"))

    if not os.path.exists(cue4parse_exe):
        shutil.rmtree(isolated_dir, ignore_errors=True)
        return False, f"Missing cue4parse.exe dependency at {cue4parse_exe}"
    if not os.path.exists(usmap_path):
        shutil.rmtree(isolated_dir, ignore_errors=True)
        return False, f"Missing Mappings.usmap dependency at {usmap_path}"

    os.makedirs(output_dir, exist_ok=True)

    # Compile the CLI commands targeting only the isolated directory
    cmd = [
        cue4parse_exe,
        "-i", active_input_dir,
        "-o", output_dir,
        "-m", usmap_path,
        "-g", "GAME_UE5_1",
        "-f", format_type,
        "-y"
    ]

    for rel_path in relative_paths:
        cmd.extend(["-p", rel_path])

    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=creation_flags)
        
        # Clean up isolated hard links immediately after execution
        shutil.rmtree(isolated_dir, ignore_errors=True)
        
        if result.returncode != 0:
            error_details = result.stderr or result.stdout
            return False, f"cue4parse exited with code {result.returncode}. Details: {error_details}"
            
        return True, "Extraction completed successfully."
    except Exception as e:
        shutil.rmtree(isolated_dir, ignore_errors=True)
        return False, f"Failed to execute cue4parse.exe process: {e}"

def extract_single_file(settings: dict, relative_path: str, output_dir: str) -> bool:
    """
    Helper wrapper to extract a single file directly from paks.
    Logs warnings internally to terminal console if the process fails.
    """
    success, msg = extract_game_files(settings, [relative_path], output_dir)
    if not success:
        print(f"[Extractor Helper] Extraction failed for {relative_path}: {msg}", flush=True)
    return success

def build_pal_names_map(settings: dict) -> tuple[bool, str]:
    """
    Extracts the latest English localization table from the game paks,
    translates the serialized structure, and builds the local pal_names_map.json.
    Also extracts all vanilla Pal icons from the archives to dynamically populate the UI,
    along with passive skills, active attacks, and base monster parameter templates.
    """
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_map_path = os.path.join(repo_root, "pal_names_map.json")
    os.makedirs(os.path.join(repo_root, "deps"), exist_ok=True)
    
    # 1. Primary Text Localization Extraction (CRITICAL PIPELINE START)
    temp_out = os.path.join(repo_root, "temp_db_extract")
    relative_asset_path = "Pal/Content/L10N/en/Pal/DataTable/Text/DT_PalNameText_Common.uasset"
    
    success, msg = extract_game_files(settings, [relative_asset_path], temp_out, format_type="json")
    if not success:
        return False, f"Failed to extract text data table: {msg}"
        
    extracted_file_path = os.path.normpath(os.path.join(
        temp_out, "Pal", "Content", "L10N", "en", "Pal", "DataTable", "Text", "DT_PalNameText_Common.json"
    ))
    
    if not os.path.exists(extracted_file_path):
        shutil.rmtree(temp_out, ignore_errors=True)
        return False, f"Extracted file not found at expected path: {extracted_file_path}"
        
    try:
        # FIXED: Explicitly use utf-8-sig to automatically discard the UTF-8 BOM signature generated by cue4parse
        with open(extracted_file_path, "r", encoding="utf-8-sig") as f:
            raw_data = json.load(f)
            
        # Parse standard array-wrapped DataTable object output by cue4parse
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
            # Clean row keys (e.g. PAL_NAME_Alpaca -> Alpaca)
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

    # --- SUB-TASK 2: VANILLA PAL ICONS (NON-BLOCKING) ---
    fmodel_base = settings.get("fmodel_output", "")
    if fmodel_base:
        try:
            icon_relative_dir = "Pal/Content/Pal/Texture/PalIcon/Normal"
            icon_export_root = os.path.join(fmodel_base, "Exports")
            
            success_icons, msg_icons = extract_game_files(
                settings,
                [f"{icon_relative_dir}/*"],
                icon_export_root,
                format_type="auto"
            )
            if success_icons:
                extracted_icon_dir = os.path.normpath(os.path.join(icon_export_root, icon_relative_dir))
                if os.path.exists(extracted_icon_dir):
                    redundant_extensions = (".uasset", ".uexp", ".ubulk")
                    for root, _, files in os.walk(extracted_icon_dir):
                        for file in files:
                            if file.lower().endswith(redundant_extensions):
                                try: os.remove(os.path.join(root, file))
                                except OSError: pass
        except Exception as e:
            print(f"[Extractor Warning] Failed to process vanilla icons: {e}", flush=True)

    # --- SUB-TASK 3: LOCALIZED SKILL NAMES LOOKUP (NON-BLOCKING) ---
    skill_names_lookup = {}
    try:
        temp_skill_names = os.path.join(repo_root, "temp_skill_names_extract")
        success_skill_names, msg_skill_names = extract_game_files(
            settings,
            ["Pal/Content/L10N/en/Pal/DataTable/Text/DT_SkillNameText_Common.uasset"],
            temp_skill_names,
            format_type="json"
        )
        if success_skill_names:
            raw_names_path = os.path.join(temp_skill_names, "Pal", "Content", "L10N", "en", "Pal", "DataTable", "Text", "DT_SkillNameText_Common.json")
            if os.path.exists(raw_names_path):
                with open(raw_names_path, "r", encoding="utf-8-sig") as f:
                    names_data = json.load(f)
                rows_obj = None
                for obj in (names_data if isinstance(names_data, list) else [names_data]):
                    if obj.get("Type") == "DataTable" and "Rows" in obj:
                        rows_obj = obj["Rows"]
                        break
                if rows_obj:
                    for k, v in rows_obj.items():
                        localized_val = v.get("TextData", {}).get("LocalizedString", k)
                        skill_names_lookup[k] = localized_val
        else:
            print(f"Warning: Skill Names extraction failed: {msg_skill_names}", flush=True)
        shutil.rmtree(temp_skill_names, ignore_errors=True)
    except Exception as e:
        print(f"[Extractor Warning] Failed to compile Skill Names lookup: {e}", flush=True)

    # --- SUB-TASK 4: MONSTER PARAMETERS TEMPLATE CACHE (MOVED UP FOR BRIDGING) ---
    partner_skill_to_pal_map = {}
    try:
        temp_params = os.path.join(repo_root, "temp_params_extract")
        success_params, msg_params = extract_game_files(
            settings, 
            ["Pal/Content/Pal/DataTable/Character/DT_PalMonsterParameter_Common.uasset"], 
            temp_params, 
            format_type="json"
        )
        if success_params:
            raw_params_path = os.path.join(temp_params, "Pal", "Content", "Pal", "DataTable", "Character", "DT_PalMonsterParameter_Common.json")
            if os.path.exists(raw_params_path):
                with open(raw_params_path, "r", encoding="utf-8-sig") as f:
                    params_raw_data = json.load(f)
                rows_obj = None
                for obj in (params_raw_data if isinstance(params_raw_data, list) else [params_raw_data]):
                    if obj.get("Type") == "DataTable" and "Rows" in obj:
                        rows_obj = obj["Rows"]
                        break
                if rows_obj:
                    # Build reverse-lookup bridge
                    for pal_id_key, pal_props in rows_obj.items():
                        pskill_id = pal_props.get("PartnerSkill")
                        if pskill_id and pskill_id != "None":
                            partner_skill_to_pal_map[pskill_id] = pal_id_key

                    with open(os.path.join(repo_root, "deps", "monster_parameter_cache.json"), "w", encoding="utf-8") as f_out:
                        json.dump(rows_obj, f_out, indent=4)
        else:
            print(f"Warning: Monster Parameters extraction failed: {msg_params}", flush=True)
        shutil.rmtree(temp_params, ignore_errors=True)
    except Exception as e:
        print(f"[Extractor Warning] Failed to compile Monster Parameters: {e}", flush=True)

    # --- SUB-TASK 5: ACTIVE ATTACKS CACHE (NON-BLOCKING) ---
    try:
        temp_skills = os.path.join(repo_root, "temp_skills_extract")
        success_active, msg_active = extract_game_files(
            settings, 
            ["Pal/Content/Pal/DataTable/Waza/DT_WazaDataTable_Common.uasset"], 
            temp_skills, 
            format_type="json"
        )
        if success_active:
            raw_skills_path = os.path.join(temp_skills, "Pal", "Content", "Pal", "DataTable", "Waza", "DT_WazaDataTable_Common.json")
            if os.path.exists(raw_skills_path):
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
                        skills_cache[friendly_name] = internal_id
                        
                    with open(os.path.join(repo_root, "deps", "active_skills_cache.json"), "w", encoding="utf-8") as f_out:
                        json.dump(skills_cache, f_out, indent=4)
        else:
            print(f"Warning: Active Attacks extraction failed: {msg_active}", flush=True)
        shutil.rmtree(temp_skills, ignore_errors=True)
    except Exception as e:
        print(f"[Extractor Warning] Failed to compile Active Skills: {e}", flush=True)

    # --- SUB-TASK 6: PASSIVE SKILLS CACHE (NON-BLOCKING) ---
    try:
        temp_passives = os.path.join(repo_root, "temp_passives_extract")
        success_passive, msg_passive = extract_game_files(
            settings, 
            ["Pal/Content/Pal/DataTable/PassiveSkill/DT_PassiveSkill_Main_Common.uasset"], 
            temp_passives, 
            format_type="json"
        )
        if success_passive:
            raw_passives_path = os.path.join(temp_passives, "Pal", "Content", "Pal", "DataTable", "PassiveSkill", "DT_PassiveSkill_Main_Common.json")
            if os.path.exists(raw_passives_path):
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
                            
                            # Resolve dynamic localized friendly name
                            lookup_key = f"PASSIVE_{internal_id}"
                            friendly_name = skill_names_lookup.get(lookup_key, internal_id)
                            
                            if friendly_name == "en Text":
                                friendly_name = internal_id
                                
                            # FIXED: Dynamically split riding/ability modifiers from standard breeding passives
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
                except Exception as e:
                    print(f"Warning: Failed to compile Passive Skills cache: {e}", flush=True)
        else:
            print(f"Warning: Passive Skills extraction failed: {msg_passive}", flush=True)
        shutil.rmtree(temp_passives, ignore_errors=True)
    except Exception as e:
        print(f"[Extractor Warning] Failed to compile Passive Skills: {e}", flush=True)

    # --- SUB-TASK 7: PARTNER ABILITIES CACHE (NON-BLOCKING) ---
    try:
        temp_partner = os.path.join(repo_root, "temp_partner_extract")
        success_partner, msg_partner = extract_game_files(
            settings, 
            ["Pal/Content/Pal/DataTable/PartnerSkill/DT_PartnerSkill.uasset"], 
            temp_partner, 
            format_type="json"
        )
        if success_partner:
            raw_partner_path = os.path.join(temp_partner, "Pal", "Content", "Pal", "DataTable", "PartnerSkill", "DT_PartnerSkill.json")
            if os.path.exists(raw_partner_path):
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
                            # Resolve matching Pal ID first to locate localized trigger keys
                            matching_pal_id = partner_skill_to_pal_map.get(internal_id, internal_id)
                            lookup_key = f"PARTNERSKILL_{matching_pal_id}"
                            
                            friendly_name = skill_names_lookup.get(lookup_key, internal_id)
                            partner_cache[friendly_name] = internal_id

                        with open(os.path.join(repo_root, "deps", "partner_skills_cache.json"), "w", encoding="utf-8") as f_out:
                            json.dump(partner_cache, f_out, indent=4)
                except Exception as e:
                    print(f"Warning: Failed to compile Partner Skills cache: {e}", flush=True)
        else:
            print(f"Warning: Partner Skills extraction failed: {msg_partner}", flush=True)
        shutil.rmtree(temp_partner, ignore_errors=True)
    except Exception as e:
        print(f"[Extractor Warning] Failed to compile Partner Skills: {e}", flush=True)
    # --- SUB-TASK 8: WAZA MASTER LEVEL (LEARNSET) CACHE (NON-BLOCKING) ---
    try:
        temp_learnset = os.path.join(repo_root, "temp_learnset_extract")
        success_learnset, msg_learnset = extract_game_files(
            settings, 
            ["Pal/Content/Pal/DataTable/Waza/DT_WazaMasterLevel_Common.uasset"], 
            temp_learnset, 
            format_type="json"
        )
        if success_learnset:
            raw_learnset_path = os.path.normpath(os.path.join(temp_learnset, "Pal", "Content", "Pal", "DataTable", "Waza", "DT_WazaMasterLevel_Common.json"))
            if os.path.exists(raw_learnset_path):
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
        else:
            print(f"[Extractor Warning] Failed to extract learnset: {msg_learnset}", flush=True)
        shutil.rmtree(temp_learnset, ignore_errors=True)
    except Exception as e:
        print(f"[Extractor Warning] Failed to compile Waza Master Level cache: {e}", flush=True)

    return True, "Pal database metrics built and pre-cached successfully."

def extract_pal_assets(settings: dict, pal_name: str, category: str = "Monster") -> tuple[bool, str]:
    """
    Extracts all visual assets (skeletal mesh, textures, material instances)
    for a given Pal directly from the game's Paks.
    If the target represents a custom standalone species, it dynamically clones 
    the mesh, textures, and properties from its parent template and re-maps their references.
    """
    fmodel_root = settings.get("fmodel_output", "")
    if not fmodel_root:
        return False, "FModel output folder is not configured."
        
    export_root = os.path.join(fmodel_root, "Exports")
    
    # --- DYNAMIC PARENT CLONING ENGINE ---
    # Intercept custom standalone species. If it is not native, we extract its parent 
    # skeleton and dynamically rename the physical assets and JSON references on the fly.
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
    
    # Pass 1: Auto conversion of Mesh and Textures (Mesh -> .psk, Texture2D -> .png)
    # Target strictly only the isolated game archives, ignoring duplicate cooked mod paks on the fly
    success_raw, msg_raw = extract_game_files(
        settings, 
        [f"{pal_relative_dir}/*"], 
        export_root, 
        format_type="auto"
    )
    if not success_raw:
        return False, f"Failed to extract and convert mesh/texture assets: {msg_raw}"
        
    # Pass 2: JSON serialization extraction of Material Instances
    success_json, msg_json = extract_game_files(
        settings, 
        [f"{pal_relative_dir}/MI_*"], 
        export_root, 
        format_type="json"
    )
    if not success_json:
        print(f"[Extractor] Warning: Material instance JSON extraction had issues: {msg_json}", flush=True)

    # Pass 3: Post-extraction sanitation and Dynamic Rename Mapping
    pal_dir = os.path.normpath(os.path.join(export_root, "Pal", "Content", "Pal", "Model", "Character", category, pal_name))
    source_dir = os.path.normpath(os.path.join(export_root, "Pal", "Content", "Pal", "Model", "Character", category, source_pal_name))

    # If it's a custom standalone species, rename the parent directory and all internal files/JSON keys
    if is_custom_pal and os.path.exists(source_dir) and not os.path.exists(pal_dir):
        try:
            os.rename(source_dir, pal_dir)
        except OSError as e:
            return False, f"Failed to instantiate custom Pal directory: {e}"

    if os.path.exists(pal_dir):
        # Clean raw engine binaries first
        redundant_extensions = (".uasset", ".uexp", ".ubulk")
        for root, _, files in os.walk(pal_dir):
            for file in files:
                file_lower = file.lower()
                
                # Dynamic re-mapping of physical file names
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

                # Dynamic reference mapping inside the JSON material instance files
                if is_custom_pal and file_lower.endswith(".json"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8-sig") as f_js:
                            content = f_js.read()
                        
                        # Swap all parent asset directory and texture prefix strings
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