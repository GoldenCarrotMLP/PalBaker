# pythoncli/utils/creator/pal_manager.py
import os
import json
import re
import threading

class PalManager:
    def __init__(self, controller):
        self.c = controller

    def get_creator_dir(self) -> str | None:
        fmodel_base = self.c.settings.get("fmodel_output", "")
        if not fmodel_base: return None
        return os.path.normpath(os.path.join(fmodel_base, "Exports", "Pal", "Content", "Palbaker", "Creator"))

    def load_custom_pals(self):
        """Scans the local Palbaker Creator directory and parses existing custom Pal JSONs."""
        self.c.custom_pals.clear()
        creator_dir = self.get_creator_dir()
        if not creator_dir or not os.path.exists(creator_dir):
            return

        fmodel_base = self.c.settings.get("fmodel_output", "")

        for f in os.listdir(creator_dir):
            if f.endswith("_creator.json"):
                f_path = os.path.join(creator_dir, f)
                try:
                    with open(f_path, "r", encoding="utf-8") as file:
                        data = json.load(file)
                        
                        # Resolve icon path on backend to prevent front-end blocking I/O!
                        pal_id = data.get("CharacterID", "")
                        resolved_icon_path = ""
                        if fmodel_base and pal_id:
                            custom_icon_path = os.path.normpath(os.path.join(
                                fmodel_base, "Exports", "Pal", "Content", "Pal", "Model", "Character", "Monster", pal_id, f"T_{pal_id}_icon_normal.png"
                            ))
                            shared_icon_path = os.path.normpath(os.path.join(
                                fmodel_base, "Exports", "Pal", "Content", "Pal", "Texture", "PalIcon", "Normal", f"T_{pal_id}_icon_normal.png"
                            ))
                            if os.path.exists(custom_icon_path):
                                resolved_icon_path = custom_icon_path
                            elif os.path.exists(shared_icon_path):
                                resolved_icon_path = shared_icon_path
                        
                        data["resolved_icon_path"] = resolved_icon_path
                        
                        self.c.custom_pals.append(data)
                except Exception: pass

    def add_custom_pal(self, pal_id: str, template_id: str, sync: bool = False):
        """Clones a parent template from cache and instantiates a new Creator JSON on disk."""
        creator_dir = self.get_creator_dir()
        if not creator_dir:
            self.c.view.show_snackbar("Configure your Workspace Folder first.", "#E53935")
            return

        clean_id = re.sub(r'[^a-zA-Z0-9_]', '_', pal_id.strip())
        if not clean_id: return

        if any(p.get("CharacterID") == clean_id for p in self.c.custom_pals):
            self.c.view.show_snackbar(f"Error: A Pal named '{clean_id}' already exists!", "#E53935")
            return

        from utils.names import load_names_map
        names_map = load_names_map()
        if clean_id in names_map:
            self.c.view.show_snackbar(f"Error: '{clean_id}' is a reserved vanilla Pal name.", "#E53935")
            return

        def background_adder():
            import time
            if not sync:
                time.sleep(0.1)
            
            os.makedirs(creator_dir, exist_ok=True)
            
            base_properties = self.c.templates_cache.get(template_id, {})
            cloned_learnset = self.c.learnsets_cache.get(template_id, [])

            predicted_saddle = f"SkillUnlock_{template_id}"
            predicted_coop_passives = []
            if "weaseldragon" in template_id.lower() or "amaterasuwolf" in template_id.lower():
                predicted_coop_passives.append("GiveADragon_Ride")

            predicted_spawner = self.c.monster_spawners_default_map.get(template_id, "1_1_plain_begginer")

            new_pal_data = {
                "CharacterID": clean_id,
                "TemplateID": template_id,
                "Name": clean_id,
                "Description": f"A custom standalone Pal cloned from {template_id}.",
                
                "ElementType1": base_properties.get("ElementType1", "EPalElementType::Normal"),
                "ElementType2": base_properties.get("ElementType2", "EPalElementType::None"),
                "Hp": base_properties.get("Hp", 100),
                "MeleeAttack": base_properties.get("MeleeAttack", 100),
                "ShotAttack": base_properties.get("ShotAttack", 100),
                "Defense": base_properties.get("Defense", 100),
                "Support": base_properties.get("Support", 100),
                "CraftSpeed": base_properties.get("CraftSpeed", 100),
                
                "Size": base_properties.get("Size", "EPalSizeType::M"),
                "Rarity": base_properties.get("Rarity", 1),
                "Price": base_properties.get("Price", 1000.0),
                "WalkSpeed": base_properties.get("WalkSpeed", 100),
                "RunSpeed": base_properties.get("RunSpeed", 500),
                "RideSprintSpeed": base_properties.get("RideSprintSpeed", 700),
                "TransportSpeed": base_properties.get("TransportSpeed", 200),
                "FoodAmount": base_properties.get("FoodAmount", 1),
                "Stamina": base_properties.get("Stamina", 100),
                "MaleProbability": base_properties.get("MaleProbability", 50),
                "CombiRank": base_properties.get("CombiRank", 100),
                "CaptureRateCorrect": base_properties.get("CaptureRateCorrect", 1.0),

                "MeshCapsuleHalfHeight": base_properties.get("MeshCapsuleHalfHeight", 110.0),
                "MeshCapsuleRadius": base_properties.get("MeshCapsuleRadius", 50.0),
                "MeshRelativeLocation": base_properties.get("MeshRelativeLocation", {"X": 0.0, "Y": 0.0, "Z": -110.0}),

                "BaseSkills": ["AirCanon", "IgnisBlast"],
                "PassiveSkills": [],
                "PartnerSkill": base_properties.get("PartnerSkill", "None"),
                "Learnset": cloned_learnset,
                "SaddleItem": predicted_saddle,
                "CoopPassives": predicted_coop_passives,
                "EnableSpawns": True,
                "SpawnLocationID": predicted_spawner,
                "SpawnMinLevel": 2,
                "SpawnMaxLevel": 5,
                "SpawnMinGroup": 1,
                "SpawnMaxGroup": 3,
                "EnablePaldeck": True,
                "ZukanIndex": -1,
                "ZukanIndexSuffix": "",
                "LongDescription": f"A custom standalone Pal cloned from {template_id}.",
                "PaldexType": "Species"
            }
            
            # FIXED: Safely loop over base_properties keys instead of undefined 'p'
            for k in base_properties.keys():
                if k.startswith("WorkSuitability_"):
                    new_pal_data[k] = base_properties[k]

            target_file = os.path.join(creator_dir, f"{clean_id}_creator.json")
            try:
                with open(target_file, "w", encoding="utf-8") as f:
                    json.dump(new_pal_data, f, indent=4)
                self.c.view.write_log(f"Successfully created brand new Pal template: {clean_id}", "success")
                
                from utils.extractor.asset_cloner import extract_pal_assets
                self.c.view.write_log(f"Cloning parent assets and setting up workspace for {clean_id}...", "standard")
                success, msg = extract_pal_assets(self.c.settings, clean_id, "Monster")
                if success:
                    self.c.view.write_log(msg, "success")
                else:
                    self.c.view.write_log(f"Workspace cloning failed: {msg}", "warning")

                self.c.exporter.generate_custom_actor_blueprint(new_pal_data)
                self.c.export_to_palschema(new_pal_data)
            except Exception as e:
                self.c.view.write_log(f"Failed to save new Pal: {e}", "error")
                if sync:
                    raise e

            self.refresh_pals()

        if sync:
            background_adder()
        else:
            threading.Thread(target=background_adder, daemon=True).start()

    def save_custom_pal(self, pal_id: str, updated_data: dict, sync: bool = False):
        """Asynchronously writes edited parameters back to the localized JSON file."""
        creator_dir = self.get_creator_dir()
        if not creator_dir: return

        target_file = os.path.join(creator_dir, f"{pal_id}_creator.json")
        
        def background_writer():
            import time
            if not sync:
                time.sleep(0.1)
            try:
                with open(target_file, "w", encoding="utf-8") as f:
                    json.dump(updated_data, f, indent=4)
                self.c.view.write_log(f"Successfully saved Pal Creator adjustments: {pal_id}", "success")
                
                self.c.export_to_palschema(updated_data)
            except Exception as e:
                self.c.view.write_log(f"Failed to write Pal updates: {e}", "error")
                if sync:
                    raise e
            self.refresh_pals()

        if sync:
            background_writer()
        else:
            threading.Thread(target=background_writer, daemon=True).start()


    def delete_custom_pal(self, pal_id: str, sync: bool = False):
        """Removes the local creator JSON configuration file permanently from disk."""
        creator_dir = self.get_creator_dir()
        if not creator_dir: return

        target_file = os.path.join(creator_dir, f"{pal_id}_creator.json")
        
        def background_deleter():
            import time
            if not sync:
                time.sleep(0.1)
            if os.path.exists(target_file):
                try:
                    os.remove(target_file)
                    self.c.view.write_log(f"Deleted custom Pal config: {pal_id}", "warning")
                    self.c.delete_palschema_export(pal_id)
                except Exception as e:
                    self.c.view.write_log(f"Failed to delete Pal config: {e}", "error")
            self.refresh_pals()

        if sync:
            background_deleter()
        else:
            threading.Thread(target=background_deleter, daemon=True).start()

    def refresh_pals(self):
        """Instructs the main view to re-render using cached list entries."""
        self.load_custom_pals()
        self.c.view.refresh_creator_mods_ui()