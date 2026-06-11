# utils/cli/manager_handlers.py
import os
import sys
import json
from utils.config import validate_settings
from utils.cli.shared import json_print, error_print
from utils.scanner import get_mod_info
from utils.extractor.db_builder import build_pal_names_map

def handle_manager_command(args, settings):
    """Router for all manager-level subcommands."""
    
    # 1. manager list [--show-unextracted]
    if args.subcommand == "list":
        is_valid, err_msg = validate_settings(settings, ["fmodel_output"])
        if not is_valid:
            error_print(err_msg)
            sys.exit(1)
            
        show_unextracted = getattr(args, "show_unextracted", False)
        try:
            mods = get_mod_info(settings)
            if not show_unextracted:
                # Exclude unextracted game archive references
                mods = [m for m in mods if m["pak_status"] != "Unextracted"]
            json_print({"status": "success", "data": mods})
        except Exception as e:
            error_print(f"Failed to scan mod directory: {str(e)}")
            sys.exit(1)

    # 2. manager build-db
    elif args.subcommand == "build-db":
        is_valid, err_msg = validate_settings(settings, ["fmodel_output", "palworld_exe"])
        if not is_valid:
            error_print(err_msg)
            sys.exit(1)
            
        try:
            success, msg = build_pal_names_map(settings)
            if success:
                json_print({"status": "success", "message": msg})
            else:
                json_print({"status": "error", "message": msg})
                sys.exit(1)
        except Exception as e:
            error_print(f"Database build crashed: {str(e)}")
            sys.exit(1)

    # 3. manager get-caches
    elif args.subcommand == "get-caches":
        # Returns all pre-cached static lists over stdout in a single round-trip
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        deps_dir = os.path.join(repo_root, "deps")
        
        caches = {
            "active_skills": {},
            "passive_skills": {},
            "partner_skills": {},
            "coop_passives": {},
            "monster_spawners": {},
            "monster_spawners_default_map": {},
            "templates": {},
            "learnsets": {},
            "camera_offsets": {},
            "traits_db": {},
            "pal_names": {}
        }
        
        file_mappings = {
            "active_skills": "active_skills_cache.json",
            "passive_skills": "passive_skills_cache.json",
            "coop_passives": "coop_passives_cache.json",
            "partner_skills": "partner_skills_cache.json",
            "monster_spawners": "monster_spawners_cache.json",
            "monster_spawners_default_map": "monster_spawners_default_map.json",
            "templates": "monster_parameter_cache.json",
            "learnsets": "waza_master_level_cache.json",
            "camera_offsets": "camera_offsets_cache.json"
        }
        
        for key, filename in file_mappings.items():
            path = os.path.join(deps_dir, filename)
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        caches[key] = json.load(f)
                except Exception:
                    pass
                    
        # traits_db points directly to passive_skills
        caches["traits_db"] = caches["passive_skills"]
        
        # Parse flat localization map from pal_names_map.json located inside deps/
        names_path = os.path.join(deps_dir, "pal_names_map.json")
        if os.path.exists(names_path):
            try:
                with open(names_path, "r") as f:
                    data = json.load(f)
                    rows = data.get("Rows", {})
                    flat_names = {}
                    for k, v in rows.items():
                        localized = v.get("TextData", {}).get("LocalizedString", k)
                        flat_names[k] = str(localized).strip()
                    caches["pal_names"] = flat_names
            except Exception:
                pass
                
        json_print({"status": "success", "data": caches})

    else:
        error_print(f"Unknown manager subcommand: {args.subcommand}")
        sys.exit(1)