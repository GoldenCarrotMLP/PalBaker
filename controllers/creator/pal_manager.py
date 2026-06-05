# controllers/creator/pal_manager.py
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

        for f in os.listdir(creator_dir):
            if f.endswith("_creator.json"):
                f_path = os.path.join(creator_dir, f)
                try:
                    with open(f_path, "r", encoding="utf-8") as file:
                        data = json.load(file)
                        self.c.custom_pals.append(data)
                except Exception: pass

    def add_custom_pal(self, pal_id: str, template_id: str):
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
            time.sleep(0.1)
            
            os.makedirs(creator_dir, exist_ok=True)
            
            base_properties = self.c.templates_cache.get(template_id, {})
            cloned_learnset = self.c.learnsets_cache.get(template_id, [])

            predicted_saddle = f"SkillUnlock_{template_id}"
            predicted_coop_passives = []
            if "weaseldragon" in template_id.lower() or "amaterasuwolf" in template_id.lower():
                predicted_coop_passives.append("GiveADragon_Ride")

            # Predict overworld spawner location based on parent template ID [4]
            predicted_spawner = self.c.monster_spawners_default_map.get(template_id, "1_1_plain_begginer")

            new_pal_data = {
                "CharacterID": clean_id,
                "TemplateID": template_id,
                "Name": clean_id,
                "Description": f"A custom standalone Pal cloned from {template_id}.",
                "ElementType1": base_properties.get("ElementType1", "EPalElementType::None"),
                "ElementType2": base_properties.get("ElementType2", "EPalElementType::None"),
                "BaseHP": base_properties.get("HP", 100),
                "BaseAtk": base_properties.get("MeleeAttack", 100),
                "BaseDef": base_properties.get("Defense", 100),
                "BaseWorkSpeed": base_properties.get("WorkSpeed", 70),
                "WorkSuitabilities": {k: v for k, v in base_properties.items() if k.startswith("WorkSuitability_")},
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
                "ZukanIndex": -1,
                "ZukanIndexSuffix": "",
                "LongDescription": f"A custom standalone Pal cloned from {template_id}.",
                "PaldexType": "Species"  # Baseline classification default
            }


            target_file = os.path.join(creator_dir, f"{clean_id}_creator.json")
            try:
                with open(target_file, "w", encoding="utf-8") as f:
                    json.dump(new_pal_data, f, indent=4)
                self.c.view.write_log(f"Successfully created brand new Pal template: {clean_id}", "success")
                
                # Auto-extract, clone, and binary-patch standalone blueprint assets on creation!
                self.c.exporter.generate_custom_actor_blueprint(new_pal_data)
                
                self.c.export_to_palschema(new_pal_data)
            except Exception as e:
                self.c.view.write_log(f"Failed to save new Pal: {e}", "error")


            self.refresh_pals()

        threading.Thread(target=background_adder, daemon=True).start()

    def save_custom_pal(self, pal_id: str, updated_data: dict):
        """Asynchronously writes edited parameters back to the localized JSON file."""
        creator_dir = self.get_creator_dir()
        if not creator_dir: return

        target_file = os.path.join(creator_dir, f"{pal_id}_creator.json")
        
        def background_writer():
            import time
            time.sleep(0.1)
            try:
                with open(target_file, "w", encoding="utf-8") as f:
                    json.dump(updated_data, f, indent=4)
                self.c.view.write_log(f"Successfully saved Pal Creator adjustments: {pal_id}", "success")
                
                self.c.export_to_palschema(updated_data)
            except Exception as e:
                self.c.view.write_log(f"Failed to write Pal updates: {e}", "error")
            self.refresh_pals()

        threading.Thread(target=background_writer, daemon=True).start()

    def delete_custom_pal(self, pal_id: str):
        """Removes the local creator JSON configuration file permanently from disk."""
        creator_dir = self.get_creator_dir()
        if not creator_dir: return

        target_file = os.path.join(creator_dir, f"{pal_id}_creator.json")
        
        def background_deleter():
            import time
            time.sleep(0.1)
            if os.path.exists(target_file):
                try:
                    os.remove(target_file)
                    self.c.view.write_log(f"Deleted custom Pal: {pal_id}", "warning")
                except Exception as e:
                    self.c.view.write_log(f"Failed to delete Pal config: {e}", "error")
            self.refresh_pals()

        threading.Thread(target=background_deleter, daemon=True).start()

    def refresh_pals(self):
        """Instructs the main view to re-render using cached list entries."""
        self.load_custom_pals()
        self.c.view.refresh_creator_mods_ui()