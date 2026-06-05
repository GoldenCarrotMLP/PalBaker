# controllers/creator/palschema_exporter.py
import os
import json
import shutil
import subprocess
import re

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

    def generate_custom_actor_blueprint(self, p: dict) -> bool:
        """
        Dynamically extracts, clones, and compiles the parent actor blueprint
        to create a standalone child blueprint using UAssetGUI CLI.
        Allows variable-length string modifications without binary corruption.
        """
        pal_id = p["CharacterID"]
        template_id = p["TemplateID"]  # e.g., "WeaselDragon"
        
        # Clean standalone folder and asset names (no more padding!)
        custom_folder_name = pal_id
        custom_asset_name = f"BP_{pal_id}"
        
        # 1. Resolve UAssetGUI executable path (pointing directly to deps/UAssetGUI.exe)
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        uasset_gui_exe = os.path.normpath(os.path.join(repo_root, "deps", "UAssetGUI.exe"))
        
        if not os.path.exists(uasset_gui_exe):
            self.c.view.write_log(f"Error: UAssetGUI.exe not found at {uasset_gui_exe}. Place it there to compile blueprints.", "error")
            return False

        # 2. Extract the original parent uasset and uexp
        relative_uasset = f"Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/{template_id}/BP_{template_id}.uasset"
        relative_uexp = f"Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/{template_id}/BP_{template_id}.uexp"
        
        from utils.extractor.core import extract_game_files
        temp_dir = os.path.join(repo_root, "temp_bp_extract")
        shutil.rmtree(temp_dir, ignore_errors=True)
        os.makedirs(temp_dir, exist_ok=True)
        
        success, msg = extract_game_files(self.c.settings, [relative_uasset, relative_uexp], temp_dir, format_type="raw")
        if not success:
            self.c.view.write_log(f"Failed to extract parent blueprint for {template_id}: {msg}", "error")
            return False
            
        src_uasset = os.path.join(temp_dir, f"Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/{template_id}/BP_{template_id}.uasset")
        src_uexp = os.path.join(temp_dir, f"Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/{template_id}/BP_{template_id}.uexp")
        
        if not os.path.exists(src_uasset) or not os.path.exists(src_uexp):
            self.c.view.write_log(f"Extracted blueprint files not found for {template_id}.", "error")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False

        # 3. Export .uasset to temporary JSON using UAssetGUI CLI
        temp_json_path = os.path.join(temp_dir, "temp_blueprint.json")
        cmd_export = [uasset_gui_exe, "tojson", src_uasset, temp_json_path, "VER_UE5_1"]
        
        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            subprocess.run(cmd_export, check=True, creationflags=creation_flags)
        except Exception as e:
            self.c.view.write_log(f"UAssetGUI failed to export JSON: {e}", "error")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False

        # 4. Parse the JSON and perform variable-length string modifications
        try:
            with open(temp_json_path, "r", encoding="utf-8") as f:
                json_str = f.read()

            # Define replacements (no length matching required!)
            replacements = {
                # Package and class names
                f"/Game/Pal/Blueprint/Character/Monster/PalActorBP/{template_id}/BP_{template_id}": f"/Game/Pal/Blueprint/Character/Monster/PalActorBP/{custom_folder_name}/{custom_asset_name}",
                f"Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/{template_id}/BP_{template_id}": f"Pal/Content/Pal/Blueprint/Character/Monster/PalActorBP/{custom_folder_name}/{custom_asset_name}",
                f"Default__BP_{template_id}_C": f"Default__{custom_asset_name}_C",
                f"BP_{template_id}.BP_{template_id}_C": f"{custom_asset_name}.{custom_asset_name}_C",
                
                # Hardcoded Skeletal Mesh redirects
                f"/Game/Pal/Model/Character/Monster/WeaselDragon/SK_WeaselDragon": f"/Game/Pal/Model/Character/Monster/{custom_folder_name}/SK_{custom_folder_name}",
                f"Pal/Content/Pal/Model/Character/Monster/WeaselDragon/SK_WeaselDragon": f"Pal/Content/Pal/Model/Character/Monster/{custom_folder_name}/SK_{custom_folder_name}"
            }

            # Standard string replacements
            for old, new in replacements.items():
                json_str = json_str.replace(old, new)

            # Smart regex-based replacement to change BP_{template_id}_C -> BP_{custom_id}_C, 
            # while protecting any instances containing 'ABP_' from being modified
            class_pattern = re.compile(rf"(?<!A)BP_{template_id}_C")
            json_str = class_pattern.sub(f"{custom_asset_name}_C", json_str)

            with open(temp_json_path, "w", encoding="utf-8") as f:
                f.write(json_str)
        except Exception as e:
            self.c.view.write_log(f"Failed to patch blueprint JSON: {e}", "error")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False

        # 5. Import the modified JSON back into cooked assets using UAssetGUI CLI
        project_dir = os.path.dirname(self.c.settings.get("uproject", ""))
        project_name = os.path.splitext(os.path.basename(self.c.settings.get("uproject", "")))[0]
        if not project_dir or not os.path.exists(project_dir):
            self.c.view.write_log("Project directory not found in settings.", "error")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False
            
        # Self-healing: Delete uncooked folders
        old_uncooked_dir = os.path.join(project_dir, "Content", "Pal", "Blueprint", "Character", "Monster", "PalActorBP", custom_folder_name)
        if os.path.exists(old_uncooked_dir):
            try: shutil.rmtree(old_uncooked_dir)
            except Exception: pass

        cooked_dir = os.path.join(project_dir, "Saved", "Cooked", "Windows", project_name, "Content", "Pal", "Blueprint", "Character", "Monster", "PalActorBP", custom_folder_name)
        os.makedirs(cooked_dir, exist_ok=True)
        
        cooked_uasset = os.path.join(cooked_dir, f"{custom_asset_name}.uasset")
        
        cmd_import = [uasset_gui_exe, "fromjson", temp_json_path, cooked_uasset]
        try:
            subprocess.run(cmd_import, check=True, creationflags=creation_flags)
        except Exception as e:
            self.c.view.write_log(f"UAssetGUI failed to serialize assets: {e}", "error")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False

        shutil.rmtree(temp_dir, ignore_errors=True)
        self.c.view.write_log(f"Generated standalone pre-cooked blueprint class {custom_asset_name} in Cooked folder.", "success")
        return True

    def export_to_palschema(self, p: dict):
        mods_dir = self.get_palschema_mods_dir()
        if not mods_dir:
            self.c.view.write_log("PalSchema directory not found. Skipping auto-export. Install PalSchema first.", "warning")
            return

        pal_id = p["CharacterID"]
        template_id = p["TemplateID"]
        paldex_type = p.get("PaldexType", "Species")
        mod_name = f"PalBaker_Custom_{pal_id}"
        mod_root = os.path.join(mods_dir, mod_name)
        
        base_properties = self.c.templates_cache.get(template_id, {})
        
        # Clean paths (no padding required anymore!)
        custom_folder_name = pal_id
        custom_asset_name = f"BP_{pal_id}"
        
        # 1. Write Monster Parameter Table
        pals_dir = os.path.join(mod_root, "pals")
        os.makedirs(pals_dir, exist_ok=True)
        
        new_monster_props = dict(base_properties)
        new_monster_props["BPClass"] = f"MOD_{pal_id}"  # Map to custom key
        
        # Resolve Tribe and EPalTribeID Enum depending on PaldexType choice
        if paldex_type == "Species":
            new_monster_props["Tribe"] = f"EPalTribeID::MOD_{pal_id}"
            
            enums_dir = os.path.join(mod_root, "enums")
            os.makedirs(enums_dir, exist_ok=True)
            enums_payload = {
                "EPalTribeID": [f"MOD_{pal_id}"]
            }
            with open(os.path.join(enums_dir, f"{pal_id}_enums.json"), "w", encoding="utf-8") as f_enum:
                json.dump(enums_payload, f_enum, indent=4)
        else:
            parent_tribe = base_properties.get("Tribe", f"EPalTribeID::{template_id}")
            new_monster_props["Tribe"] = parent_tribe
            
            enums_file = os.path.join(mod_root, "enums", f"{pal_id}_enums.json")
            if os.path.exists(enums_file):
                try: os.remove(enums_file)
                except OSError: pass

        new_monster_props["ElementType1"] = p["ElementType1"]
        new_monster_props["ElementType2"] = p["ElementType2"]
        new_monster_props["Hp"] = p["BaseHP"]
        new_monster_props["MeleeAttack"] = p["BaseAtk"]
        new_monster_props["Defense"] = p["BaseDef"]
        new_monster_props["WorkSpeed"] = p["BaseWorkSpeed"]
        new_monster_props["BaseSkills"] = p["BaseSkills"]
        new_monster_props["PassiveSkills"] = p["PassiveSkills"]
        new_monster_props["PartnerSkill"] = p["PartnerSkill"]
        
        new_monster_props["ZukanIndex"] = int(p.get("ZukanIndex", -1))
        new_monster_props["ZukanIndexSuffix"] = str(p.get("ZukanIndexSuffix", ""))
        
        suitabilities = p.get("WorkSuitabilities", {})
        for k, v in suitabilities.items():
            new_monster_props[k] = v
            
        pals_payload = {
            f"MOD_{pal_id}": new_monster_props
        }
            
        with open(os.path.join(pals_dir, f"{pal_id}.json"), "w", encoding="utf-8") as f:
            json.dump(pals_payload, f, indent=4)

        # 2. Translations
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
        
        if p.get("EnablePaldeck", False) or p.get("ZukanIndex", -1) != -1:
            trans_payload["DT_PalLongDescriptionText"] = {
                f"PAL_LONG_DESC_MOD_{pal_id}": p.get("LongDescription", "")
            }
            
        with open(os.path.join(trans_dir, "names.json"), "w", encoding="utf-8") as f:
            json.dump(trans_payload, f, indent=4)

        # 3. Learnset
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

        # 4. Resolve DT_PalBPClass Mapping
        bp_virtual_path = f"/Game/Pal/Blueprint/Character/Monster/PalActorBP/{custom_folder_name}/{custom_asset_name}.{custom_asset_name}_C"
        
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

        self.c.view.write_log(f"Linked MOD_{pal_id} to standalone blueprint path: {bp_virtual_path}", "success")

        # 5. Blueprint Patch Co-Op Overrides
        saddle_item = p.get("SaddleItem", "None")
        coop_passives = p.get("CoopPassives", [])
        
        if (saddle_item and saddle_item != "None") or coop_passives:
            bp_dir = os.path.join(mod_root, "blueprints")
            os.makedirs(bp_dir, exist_ok=True)
            
            coop_passives_list = []
            for cp_id in coop_passives:
                if cp_id and cp_id != "None":
                    coop_passives_list.append({
                        "SkillAndParameters": [{"Key": {"Key": cp_id}, "Value": {"TriggerTypeFlags": 4}}]
                    })
            
            target_bp_key = f"{custom_asset_name}_C"
            bp_payload = { target_bp_key: { "PalPartnerSkillParameter": {} } }
            
            if saddle_item and saddle_item != "None":
                bp_payload[target_bp_key]["PalPartnerSkillParameter"]["RestrictionItems"] = [{"Key": saddle_item}]
            if coop_passives_list:
                bp_payload[target_bp_key]["PalPartnerSkillParameter"]["PassiveSkills"] = coop_passives_list
                
            with open(os.path.join(bp_dir, f"{pal_id}_blueprint.json"), "w", encoding="utf-8") as f:
                json.dump(bp_payload, f, indent=4)

        # 6. Custom Icon Row
        fmodel_base = self.c.settings.get("fmodel_output", "")
        if fmodel_base:
            custom_icon_name = f"T_{pal_id}_icon_normal.png"
            custom_icon_path = os.path.normpath(os.path.join(fmodel_base, "Exports", "Pal", "Content", "Pal", "Model", "Character", "Monster", pal_id, custom_icon_name))
            
            if os.path.exists(custom_icon_path):
                raw_dir = os.path.join(mod_root, "raw")
                os.makedirs(raw_dir, exist_ok=True)
                
                icon_key = f"MOD_{pal_id}" if paldex_type == "Species" else template_id
                icon_asset_path = f"/Game/Pal/Texture/PalIcon/Normal/T_{pal_id}_icon_normal.T_{pal_id}_icon_normal"
                icon_payload = {
                    "DT_PalCharacterIconDataTable": { icon_key: { "Icon": icon_asset_path } }
                }
                
                with open(os.path.join(raw_dir, "DT_PalCharacterIconDataTable.json"), "w", encoding="utf-8") as f_ic:
                    json.dump(icon_payload, f_ic, indent=4)

        # 7. UICaptureCameraOffsetData Row (Fixes Paldeck and Details preview loading)
        raw_dir = os.path.join(mod_root, "raw")
        os.makedirs(raw_dir, exist_ok=True)
        
        # We copy WeaselDragon's vanilla camera offsets so Furret displays perfectly aligned
        camera_payload = {
            "DT_PalUICaptureCameraOffsetData": {
                f"MOD_{pal_id}": {
                    "LocationOffset": { "X": 358.74005, "Y": 938.1497, "Z": 139.86491 },
                    "Rotator": { "Pitch": -0.51355, "Yaw": -110.36157, "Roll": 0.0 },
                    "PointLightOffset_1": { "X": -200.0, "Y": 100.0, "Z": 200.0 },
                    "PointLightIntensity_1": 10.0,
                    "PointLightSize_1": 1000.0,
                    "PointLightOffset_2": { "X": 200.0, "Y": 0.0, "Z": 100.0 },
                    "PointLightIntensity_2": 10.0,
                    "PointLightSize_2": 1000.0,
                    "RectLightOffset": { "X": 0.0, "Y": 300.0, "Z": 100.0 },
                    "RectLightRotator": { "Pitch": 0.0, "Yaw": -90.0, "Roll": 0.0 },
                    "RectLightIntensity": 450.0,
                    "RectLightSize": 1000.0
                }
            }
        }
        
        # We also generate it for the BOSS variant
        camera_payload["DT_PalUICaptureCameraOffsetData"][f"MOD_BOSS_{pal_id}"] = camera_payload["DT_PalUICaptureCameraOffsetData"][f"MOD_{pal_id}"]
        
        with open(os.path.join(raw_dir, "DT_PalUICaptureCameraOffsetData.json"), "w", encoding="utf-8") as f_cam:
            json.dump(camera_payload, f_cam, indent=4)
            
        self.c.view.write_log(f"Generated Paldeck UI Camera offsets for MOD_{pal_id}.", "success")