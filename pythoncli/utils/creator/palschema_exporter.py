import os
import json
import shutil
import subprocess
import re
from utils.blueprint_patcher import patch_actor_blueprint

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

    def delete_palschema_export(self, pal_id: str):
        """Permanently deletes the exported PalSchema mod folder to prevent orphan directory clutter."""
        mod_name = f"PalBaker_Custom_{pal_id}"
        
        creator_dir = self.c.get_creator_dir()
        if creator_dir:
            local_mod_root = os.path.join(creator_dir, "PalSchema", mod_name)
            if os.path.exists(local_mod_root):
                try:
                    shutil.rmtree(local_mod_root)
                    self.c.view.write_log(f"Successfully deleted local PalSchema export directory: {mod_name}", "warning")
                except Exception as e:
                    self.c.view.write_log(f"Failed to delete local PalSchema export: {e}", "error")

        mods_dir = self.get_palschema_mods_dir()
        if mods_dir:
            mod_root = os.path.join(mods_dir, mod_name)
            if os.path.exists(mod_root):
                try:
                    shutil.rmtree(mod_root)
                    self.c.view.write_log(f"Successfully deleted deployed PalSchema export directory: {mod_name}", "warning")
                except Exception as e:
                    self.c.view.write_log(f"Failed to delete deployed PalSchema export: {e}", "error")

    def generate_custom_actor_blueprint(self, p: dict) -> bool:
        """
        Proxies standalone blueprint compilation cleanly to the centralized
        shared patching engine and binds console logging to the Flet output window.
        """
        pal_id = p["CharacterID"]
        template_id = p["TemplateID"]
        
        def log_bridge(msg, category):
            self.c.view.write_log(msg, category)

        return patch_actor_blueprint(self.c.settings, pal_id, template_id, log_callback=log_bridge)

    def export_to_palschema(self, p: dict):
        creator_dir = self.c.get_creator_dir()
        if not creator_dir:
            self.c.view.write_log("Creator directory not found. Cannot export PalSchema data.", "error")
            return

        pal_id = p["CharacterID"]
        template_id = p["TemplateID"]
        paldex_type = p.get("PaldexType", "Species")
        mod_name = f"PalBaker_Custom_{pal_id}"
        
        # Build the files in the local workspace directory as the single source of truth
        mod_root = os.path.join(creator_dir, "PalSchema", mod_name)
        os.makedirs(mod_root, exist_ok=True)
        
        base_properties = self.c.templates_cache.get(template_id, {})
        
        custom_folder_name = pal_id
        custom_asset_name = f"BP_{pal_id}"
        
        # 1. Write Monster Parameter Table
        pals_dir = os.path.join(mod_root, "pals")
        os.makedirs(pals_dir, exist_ok=True)
        
        new_monster_props = dict(base_properties)
        
        new_monster_props["BPClass"] = f"MOD_{pal_id}"
        new_monster_props["IsPal"] = True
        
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

        # Serialize exact original game parameters mapped from the frontend state
        new_monster_props["ElementType1"] = p.get("ElementType1", "EPalElementType::Normal")
        new_monster_props["ElementType2"] = p.get("ElementType2", "EPalElementType::None")
        new_monster_props["Hp"] = int(p.get("Hp", p.get("BaseHP", 100)))
        new_monster_props["MeleeAttack"] = int(p.get("MeleeAttack", p.get("BaseAtk", 100)))
        new_monster_props["ShotAttack"] = int(p.get("ShotAttack", p.get("BaseShot", 100)))
        new_monster_props["Defense"] = int(p.get("Defense", p.get("BaseDef", 100)))
        new_monster_props["Support"] = int(p.get("Support", 100))
        new_monster_props["CraftSpeed"] = int(p.get("CraftSpeed", p.get("BaseWorkSpeed", 100)))
        new_monster_props["Size"] = p.get("Size", "EPalSizeType::M")
        new_monster_props["Rarity"] = int(p.get("Rarity", 1))
        new_monster_props["Price"] = float(p.get("Price", 1000.0))
        new_monster_props["WalkSpeed"] = int(p.get("WalkSpeed", 100))
        new_monster_props["RunSpeed"] = int(p.get("RunSpeed", 500))
        new_monster_props["RideSprintSpeed"] = int(p.get("RideSprintSpeed", 700))
        new_monster_props["TransportSpeed"] = int(p.get("TransportSpeed", 200))
        new_monster_props["FoodAmount"] = int(p.get("FoodAmount", 1))
        new_monster_props["Stamina"] = int(p.get("Stamina", 100))
        new_monster_props["MaleProbability"] = int(p.get("MaleProbability", 50))
        new_monster_props["CombiRank"] = int(p.get("CombiRank", 100))
        new_monster_props["CaptureRateCorrect"] = float(p.get("CaptureRateCorrect", 1.0))

        # Collision Capsule Heights & Relative Mesh Translation Slices
        new_monster_props["MeshCapsuleHalfHeight"] = float(p.get("MeshCapsuleHalfHeight", 110.0))
        new_monster_props["MeshCapsuleRadius"] = float(p.get("MeshCapsuleRadius", 50.0))
        
        mesh_loc = p.get("MeshRelativeLocation", {"X": 0.0, "Y": 0.0, "Z": -110.0})
        new_monster_props["MeshRelativeLocation"] = {
            "X": float(mesh_loc.get("X", 0.0)),
            "Y": float(mesh_loc.get("Y", 0.0)),
            "Z": float(mesh_loc.get("Z", -110.0))
        }

        new_monster_props["BaseSkills"] = p.get("BaseSkills", [])
        new_monster_props["PassiveSkills"] = p.get("PassiveSkills", [])
        new_monster_props["PartnerSkill"] = p.get("PartnerSkill", "None")
        
        # Flattened Work Suitabilities directly into the object
        for k in p.keys():
            if k.startswith("WorkSuitability_"):
                new_monster_props[k] = int(p[k])
                
        # Self-healing legacy fallback for any old creator JSONs
        if "WorkSuitabilities" in p:
            for k, v in p["WorkSuitabilities"].items():
                if k not in new_monster_props:
                    new_monster_props[k] = int(v)
            
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

        # 5. Blueprint Patch Overrides (Co-op Integrations)
        saddle_item = p.get("SaddleItem", "None")
        coop_passives = p.get("CoopPassives", [])
        
        bp_payload = {}

        target_bp_key = f"{custom_asset_name}_C"
        pal_bp_data = {}
        if saddle_item and saddle_item != "None":
            pal_bp_data.setdefault("PalPartnerSkillParameter", {})["RestrictionItems"] = [{"Key": saddle_item}]
        
        coop_passives_list = []
        for cp_id in coop_passives:
            if cp_id and cp_id != "None":
                coop_passives_list.append({
                    "SkillAndParameters": [{"Key": {"Key": cp_id}, "Value": {"TriggerTypeFlags": 4}}]
                })
        if coop_passives_list:
            pal_bp_data.setdefault("PalPartnerSkillParameter", {})["PassiveSkills"] = coop_passives_list

        if pal_bp_data:
            bp_payload[target_bp_key] = pal_bp_data

        if bp_payload:
            bp_dir = os.path.join(mod_root, "blueprints")
            os.makedirs(bp_dir, exist_ok=True)
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

        # 7. UICaptureCameraOffsetData Row
        raw_dir = os.path.join(mod_root, "raw")
        os.makedirs(raw_dir, exist_ok=True)
        
        parent_offset = self.c.camera_offsets_cache.get(template_id)
        if parent_offset:
            self.c.view.write_log(f"Dynamic Camera Offset resolved for {template_id} and cloned for {pal_id}.", "success")
        else:
            self.c.view.write_log(f"Warning: Camera offset for {template_id} not cached. Using standard fallback.", "warning")
            parent_offset = {
                "LocationOffset": { "X": 358.74005, "Y": 938.1497, "Z": 139.86491 },
                "Rotator": { "Pitch": -0.51355, "Yaw": -110.36157, "Roll": 0.0 },
                "PointLightOffset_1": { "X": -200.0, "Y": 100.0, "Z": 200.0 },
                "PointLightOffset_2": { "X": 200.0, "Y": 0.0, "Z": 100.0 },
                "RectLightOffset": { "X": 0.0, "Y": 300.0, "Z": 100.0 },
                "RectLightRotator": { "Pitch": 0.0, "Yaw": -90.0, "Roll": 0.0 },
                "RectLightIntensity": 450.0,
                "RectLightSize": 1000.0
            }

        camera_payload = {
            "DT_PalUICaptureCameraOffsetData": {
                f"MOD_{pal_id}": parent_offset
            }
        }
        camera_payload["DT_PalUICaptureCameraOffsetData"][f"MOD_BOSS_{pal_id}"] = parent_offset
        
        with open(os.path.join(raw_dir, "DT_PalUICaptureCameraOffsetData.json"), "w", encoding="utf-8") as f_cam:
            json.dump(camera_payload, f_cam, indent=4)

        # 8. Overworld Spawning Export
        if p.get("EnableSpawns", True):
            spawns_dir = os.path.join(mod_root, "spawns")
            os.makedirs(spawns_dir, exist_ok=True)
            
            spawn_location = p.get("SpawnLocationID", "1_1_plain_begginer")
            
            spawns_payload = [
                {
                    "Type": "Sheet",
                    "SpawnerName": spawn_location,
                    "SpawnerType": "Common",
                    "Location": { "X": 23300.0, "Y": -48800.0, "Z": 3000.0 },
                    "Rotation": { "Pitch": 0.0, "Yaw": 0.0, "Roll": 0.0 },
                    "SpawnGroupList": [
                        {
                            "Weight": 100,
                            "PalList": [
                                {
                                    "PalId": f"MOD_{pal_id}",
                                    "Level": int(p.get("SpawnMinLevel", 2)),
                                    "Level_Max": int(p.get("SpawnMaxLevel", 5)),
                                    "Num": int(p.get("SpawnMinGroup", 1)),
                                    "Num_Max": int(p.get("SpawnMaxGroup", 3))
                                }
                            ]
                        }
                    ]
                }
            ]
            
            with open(os.path.join(spawns_dir, f"{pal_id}_spawns.json"), "w", encoding="utf-8") as f_spawn:
                json.dump(spawns_payload, f_spawn, indent=4)
        else:
            spawns_file = os.path.join(mod_root, "spawns", f"{pal_id}_spawns.json")
            if os.path.exists(spawns_file):
                try: os.remove(spawns_file)
                except OSError: pass

        # Deploy local workspace configuration natively to the Palworld game directory
        game_mods_dir = self.get_palschema_mods_dir()
        if game_mods_dir:
            game_mod_root = os.path.join(game_mods_dir, mod_name)
            if os.path.exists(game_mod_root):
                try:
                    shutil.rmtree(game_mod_root)
                except OSError: pass
            try:
                shutil.copytree(mod_root, game_mod_root)
                self.c.view.write_log(f"Deployed PalSchema config to game directory: {mod_name}", "success")
            except Exception as e:
                self.c.view.write_log(f"Failed to deploy PalSchema config to game: {e}", "error")
        else:
            self.c.view.write_log("Game PalSchema directory not found. Saved locally but did not deploy to game.", "warning")