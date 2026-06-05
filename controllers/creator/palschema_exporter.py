# controllers/creator/palschema_exporter.py
import os
import json

class PalSchemaExporter:
    def __init__(self, controller):
        self.c = controller

    def get_palschema_mods_dir(self) -> str | None:
        palworld_exe = self.c.settings.get("palworld_exe", "")
        if not palworld_exe or not os.path.exists(palworld_exe):
            return None
        
        exe_lower = palworld_exe.lower()
        dirname = os.path.dirname(palworld_exe)
        
        if "win64" in exe_lower:
            bin_dir = dirname
        else:
            bin_dir = os.path.join(dirname, "Pal", "Binaries", "Win64")
            
        if not os.path.exists(bin_dir):
            return None
            
        ue4ss_dir_lower = os.path.join(bin_dir, "ue4ss")
        ue4ss_dir_upper = os.path.join(bin_dir, "UE4SS")
        ue4ss_dir = ue4ss_dir_lower if os.path.exists(ue4ss_dir_lower) else ue4ss_dir_upper
        
        if not os.path.exists(ue4ss_dir):
            return None
            
        palschema_mods_dir = os.path.normpath(os.path.join(ue4ss_dir, "Mods", "PalSchema", "mods"))
        
        # Self-healing recursive search fallback
        if not os.path.exists(palschema_mods_dir):
            for root, dirs, _ in os.walk(bin_dir):
                depth = root[len(bin_dir):].count(os.sep)
                if depth > 3:
                    dirs[:] = []
                    continue
                if "PalSchema" in dirs:
                    test_dir = os.path.normpath(os.path.join(root, "PalSchema", "mods"))
                    if os.path.exists(test_dir):
                        palschema_mods_dir = test_dir
                        break

        return palschema_mods_dir if os.path.exists(palschema_mods_dir) else None

    def export_to_palschema(self, p: dict):
        """Compiles and auto-deploys custom Pal statistics and learnset modifications to PalSchema mods."""
        mods_dir = self.get_palschema_mods_dir()
        if not mods_dir:
            self.c.view.write_log("PalSchema directory not found. Skipping auto-export. Install PalSchema first.", "warning")
            return

        pal_id = p["CharacterID"]
        template_id = p["TemplateID"]
        mod_name = f"PalBaker_Custom_{pal_id}"
        mod_root = os.path.join(mods_dir, mod_name)
        
        base_properties = self.c.templates_cache.get(template_id, {})
        
        # 1. Write Monster Parameter Table
        pals_dir = os.path.join(mod_root, "pals")
        os.makedirs(pals_dir, exist_ok=True)
        
        pals_payload = {
            f"MOD_{pal_id}": {
                "Tribe": base_properties.get("Tribe", f"EPalTribeID::{pal_id}"),
                "ElementType1": p["ElementType1"],
                "ElementType2": p["ElementType2"],
                "Hp": p["BaseHP"],
                "MeleeAttack": p["BaseAtk"],
                "Defense": p["BaseDef"],
                "WorkSpeed": p["BaseWorkSpeed"],
                "BaseSkills": p["BaseSkills"],
                "PassiveSkills": p["PassiveSkills"],
                "PartnerSkill": p["PartnerSkill"]
            }
        }
        
        suitabilities = p.get("WorkSuitabilities", {})
        for k, v in suitabilities.items():
            pals_payload[f"MOD_{pal_id}"][k] = v
            
        with open(os.path.join(pals_dir, f"{pal_id}.json"), "w", encoding="utf-8") as f:
            json.dump(pals_payload, f, indent=4)

        # 2. Name & Description Translations
        trans_dir = os.path.join(mod_root, "translations", "en")
        os.makedirs(trans_dir, exist_ok=True)
        
        trans_payload = {
            "DT_PalNameText": {
                f"PAL_NAME_MOD_{pal_id}": p["Name"]
            },
            "DT_PalFirstActivatedInfoText": {
                f"PAL_FIRST_SPAWN_DESC_MOD_{pal_id}": p["Description"]
            }
        }
        with open(os.path.join(trans_dir, "names.json"), "w", encoding="utf-8") as f:
            json.dump(trans_payload, f, indent=4)

        # 3. Waza Master Level Learnset
        learnset_list = p.get("Learnset", [])
        if learnset_list:
            raw_dir = os.path.join(mod_root, "raw")
            os.makedirs(raw_dir, exist_ok=True)
            
            learnset_rows = {}
            for idx, entry in enumerate(learnset_list):
                row_key = f"{pal_id}_Learn_{idx+1}"
                learnset_rows[row_key] = {
                    "PalId": f"MOD_{pal_id}",
                    "WazaID": f"EPalWazaID::{entry['WazaID']}",
                    "Level": entry["Level"]
                }
                
            learnset_payload = {
                "DT_WazaMasterLevel_Common": learnset_rows
            }
            with open(os.path.join(raw_dir, "DT_WazaMasterLevel_Common.json"), "w", encoding="utf-8") as f:
                json.dump(learnset_payload, f, indent=4)

        # 4. Blueprint Patch Co-Op Overrides
        saddle_item = p.get("SaddleItem", "None")
        coop_passives = p.get("CoopPassives", [])
        
        if (saddle_item and saddle_item != "None") or coop_passives:
            bp_dir = os.path.join(mod_root, "blueprints")
            os.makedirs(bp_dir, exist_ok=True)
            
            bp_key = f"BP_{pal_id}_C"
            
            coop_passives_list = []
            for cp_id in coop_passives:
                if cp_id and cp_id != "None":
                    coop_passives_list.append({
                        "SkillAndParameters": [
                            {
                                "Key": {
                                    "Key": cp_id
                                },
                                "Value": {
                                    "TriggerTypeFlags": 4  
                                }
                            }
                        ]
                    })
            
            bp_payload = {
                bp_key: {
                    "PalPartnerSkillParameter": {}
                }
            }
            
            if saddle_item and saddle_item != "None":
                bp_payload[bp_key]["PalPartnerSkillParameter"]["RestrictionItems"] = [
                    { "Key": saddle_item }
                ]
            if coop_passives_list:
                bp_payload[bp_key]["PalPartnerSkillParameter"]["PassiveSkills"] = coop_passives_list
                
            with open(os.path.join(bp_dir, f"{pal_id}_blueprint.json"), "w", encoding="utf-8") as f:
                json.dump(bp_payload, f, indent=4)

        # 5. Custom Icon Row
        fmodel_base = self.c.settings.get("fmodel_output", "")
        if fmodel_base:
            custom_icon_name = f"T_{pal_id}_icon_normal.png"
            custom_icon_path = os.path.normpath(os.path.join(fmodel_base, "Exports", "Pal", "Content", "Pal", "Model", "Character", "Monster", pal_id, custom_icon_name))
            
            if os.path.exists(custom_icon_path):
                raw_dir = os.path.join(mod_root, "raw")
                os.makedirs(raw_dir, exist_ok=True)
                
                icon_asset_path = f"/Game/Pal/Texture/PalIcon/Normal/T_{pal_id}_icon_normal.T_{pal_id}_icon_normal"
                
                icon_payload = {
                    "DT_PalCharacterIconDataTable": {
                        f"MOD_{pal_id}": {
                            "Icon": icon_asset_path
                        }
                    }
                }
                with open(os.path.join(raw_dir, "DT_PalCharacterIconDataTable.json"), "w", encoding="utf-8") as f_ic:
                    json.dump(icon_payload, f_ic, indent=4)

        # 6. DT_PalBPClass Mapping
        bp_virtual_path = None
        project_dir = os.path.dirname(self.c.settings.get("uproject", ""))
        if project_dir and os.path.exists(project_dir):
            search_pattern = os.path.join(project_dir, "Content", "Pal", "Blueprint", "Character", "Monster", "PalActorBP", "**", f"BP_{pal_id}.uasset")
            import glob
            matching_files = glob.glob(search_pattern, recursive=True)
            if matching_files:
                physical_bp_path = os.path.abspath(matching_files[0]).replace("\\", "/")
                marker = "Content/"
                if marker in physical_bp_path:
                    relative_part = physical_bp_path.split(marker, 1)[1]
                    clean_rel = os.path.splitext(relative_part)[0]
                    bp_virtual_path = f"/Game/{clean_rel}.BP_{pal_id}_C"
        
        if not bp_virtual_path:
            bp_virtual_path = f"/Game/Pal/Blueprint/Character/Monster/PalActorBP/{pal_id}/BP_{pal_id}.BP_{pal_id}_C"

        raw_dir = os.path.join(mod_root, "raw")
        os.makedirs(raw_dir, exist_ok=True)
        
        bp_class_payload = {
            "DT_PalBPClass": {
                f"MOD_{pal_id}": {
                    "BPClass": bp_virtual_path
                }
            }
        }
        with open(os.path.join(raw_dir, "DT_PalBPClass.json"), "w", encoding="utf-8") as f_bp:
            json.dump(bp_class_payload, f_bp, indent=4)

        self.c.view.write_log(f"Linked MOD_{pal_id} to actor class path: {bp_virtual_path}", "success")

        # 7. Inject Spawns directly into the native DT_PalWildSpawner table! [4]
        if p.get("EnableSpawns", True):
            selected_spawner = p.get("SpawnLocationID", "1_1_plain_begginer")
            row_key = f"MOD_{pal_id}_Spawn_{selected_spawner}"
            
            wild_spawner_payload = {
                row_key: {
                    "SpawnerName": selected_spawner,
                    "SpawnerType": "EPalSpawnedCharacterType::Common",
                    "Weight": 40.0,
                    "OnlyTime": "EPalOneDayTimeType::Undefined",
                    "OnlyWeather": "EPalWeatherConditionType::Undefined",
                    "Pal_1": f"MOD_{pal_id}",
                    "NPC_1": "None",
                    "LvMin_1": int(p.get("SpawnMinLevel", 2)),
                    "LvMax_1": int(p.get("SpawnMaxLevel", 5)),
                    "NumMin_1": int(p.get("SpawnMinGroup", 1)),
                    "NumMax_1": int(p.get("SpawnMaxGroup", 3)),
                    "Pal_2": "None",
                    "NPC_2": "None",
                    "LvMin_2": 0,
                    "LvMax_2": 0,
                    "NumMin_2": 0,
                    "NumMax_2": 0,
                    "Pal_3": "None",
                    "NPC_3": "None",
                    "LvMin_3": 0,
                    "LvMax_3": 0,
                    "NumMin_3": 0,
                    "NumMax_3": 0,
                    "bIsAllowRandomizer": True
                }
            }
            
            spawner_json_path = os.path.join(raw_dir, "DT_PalWildSpawner.json")
            existing_spawner_table = {}
            if os.path.exists(spawner_json_path):
                try:
                    with open(spawner_json_path, "r", encoding="utf-8") as f_sp:
                        outer_data = json.load(f_sp)
                        existing_spawner_table = outer_data.get("DT_PalWildSpawner", {})
                except Exception:
                    pass
            
            for k, v in wild_spawner_payload.items():
                existing_spawner_table[k] = v
                
            final_payload = {
                "DT_PalWildSpawner": existing_spawner_table
            }
            
            with open(spawner_json_path, "w", encoding="utf-8") as f_sp:
                json.dump(final_payload, f_sp, indent=4)
                
            self.c.view.write_log("Successfully injected custom spawning lottery pools directly into the game's native DT_PalWildSpawner table!", "success")

        self.c.view.write_log(f"Auto-deployed custom Pal to PalSchema: {mod_name}", "success")