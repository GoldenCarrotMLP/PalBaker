# controllers/creator_controller.py
import os
import json
import re
import threading
import time

class CreatorController:
    def __init__(self, view, settings: dict):
        self.view = view
        self.settings = settings
        
        self.custom_pals = []
        self.active_skills_cache = {}
        self.passive_skills_cache = {}
        self.partner_skills_cache = {}
        self.coop_passives_cache = {}  
        self.templates_cache = {}
        self.learnsets_cache = {}  # Cache holding Pal level-up movesets

        self.load_index_caches()

    def get_creator_dir(self) -> str | None:
        fmodel_base = self.settings.get("fmodel_output", "")
        if not fmodel_base: return None
        return os.path.normpath(os.path.join(fmodel_base, "Exports", "Pal", "Content", "Palbaker", "Creator"))

    def get_palschema_mods_dir(self) -> str | None:
        """
        Safely calculates the Palworld PalSchema mods folder directory path based on the executable path.
        Resolves case-sensitive nested ue4ss/ folders under the non-flat directory layout.
        Includes verbose diagnostic console prints and a self-healing recursive backup search.
        """
        palworld_exe = self.settings.get("palworld_exe", "")
        if not palworld_exe or not os.path.exists(palworld_exe):
            print(f"[PalSchema Path Diagnostic] Palworld.exe path is empty or does not exist: '{palworld_exe}'", flush=True)
            return None
        
        exe_lower = palworld_exe.lower()
        dirname = os.path.dirname(palworld_exe)
        
        # 1. Resolve Win64 binaries directory
        if "win64" in exe_lower:
            bin_dir = dirname
        else:
            bin_dir = os.path.join(dirname, "Pal", "Binaries", "Win64")
            
        print(f"[PalSchema Path Diagnostic] Resolved Win64 Binaries Dir: '{bin_dir}' (Exists: {os.path.exists(bin_dir)})", flush=True)
        if not os.path.exists(bin_dir):
            return None
            
        # 2. Resolve case-sensitive nested ue4ss folder
        ue4ss_dir_lower = os.path.join(bin_dir, "ue4ss")
        ue4ss_dir_upper = os.path.join(bin_dir, "UE4SS")
        ue4ss_dir = ue4ss_dir_lower if os.path.exists(ue4ss_dir_lower) else ue4ss_dir_upper
        
        print(f"[PalSchema Path Diagnostic] Evaluated ue4ss Folder: '{ue4ss_dir}' (Exists: {os.path.exists(ue4ss_dir)})", flush=True)
        if not os.path.exists(ue4ss_dir):
            return None
            
        # 3. Append PalSchema mods path
        palschema_mods_dir = os.path.normpath(os.path.join(ue4ss_dir, "Mods", "PalSchema", "mods"))
        print(f"[PalSchema Path Diagnostic] Evaluated PalSchema mods path: '{palschema_mods_dir}' (Exists: {os.path.exists(palschema_mods_dir)})", flush=True)
        
        # --- SELF-HEALING RECURSIVE BACKUP SEARCH ---
        # If the standard calculated path is missing, search the Binaries folder directly
        if not os.path.exists(palschema_mods_dir):
            print("[PalSchema Path Diagnostic] Standard path missing. Triggering self-healing scan...", flush=True)
            for root, dirs, _ in os.walk(bin_dir):
                # Restrict recursive search depth to 3 levels to maintain fast startup
                depth = root[len(bin_dir):].count(os.sep)
                if depth > 3:
                    dirs[:] = []  # Stop traversing deeper
                    continue
                if "PalSchema" in dirs:
                    test_dir = os.path.normpath(os.path.join(root, "PalSchema", "mods"))
                    if os.path.exists(test_dir):
                        print(f"[PalSchema Path Diagnostic] Self-healing found active mods folder at: '{test_dir}'", flush=True)
                        palschema_mods_dir = test_dir
                        break

        return palschema_mods_dir if os.path.exists(palschema_mods_dir) else None

    def load_index_caches(self):
        """Loads all static deserialized indices directly from the local deps/ folder."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Load Active Skills (Attacks)
        active_path = os.path.join(repo_root, "deps", "active_skills_cache.json")
        if os.path.exists(active_path):
            try:
                with open(active_path, "r", encoding="utf-8") as f:
                    self.active_skills_cache = json.load(f)
            except Exception: pass
            
        # Load Passive Skills (Traits)
        passive_path = os.path.join(repo_root, "deps", "passive_skills_cache.json")
        if os.path.exists(passive_path):
            try:
                with open(passive_path, "r", encoding="utf-8") as f:
                    self.passive_skills_cache = json.load(f)
            except Exception: pass

        # Load Co-op Passives (Riding Buffs)
        coop_path = os.path.join(repo_root, "deps", "coop_passives_cache.json")
        if os.path.exists(coop_path):
            try:
                with open(coop_path, "r", encoding="utf-8") as f:
                    self.coop_passives_cache = json.load(f)
            except Exception: pass

        # Load Partner Skills (Abilities)
        partner_path = os.path.join(repo_root, "deps", "partner_skills_cache.json")
        if os.path.exists(partner_path):
            try:
                with open(partner_path, "r", encoding="utf-8") as f:
                    self.partner_skills_cache = json.load(f)
            except Exception: pass

        # Load Monster Templates
        templates_path = os.path.join(repo_root, "deps", "monster_parameter_cache.json")
        if os.path.exists(templates_path):
            try:
                with open(templates_path, "r", encoding="utf-8") as f:
                    self.templates_cache = json.load(f)
            except Exception: pass

        # Load Waza Master Level (Learnset) Cache
        learnset_path = os.path.join(repo_root, "deps", "waza_master_level_cache.json")
        if os.path.exists(learnset_path):
            try:
                with open(learnset_path, "r", encoding="utf-8") as f:
                    self.learnsets_cache = json.load(f)
            except Exception: pass

    def load_custom_pals(self):
        """Scans the local Palbaker Creator directory and parses existing custom Pal JSONs."""
        self.custom_pals.clear()
        creator_dir = self.get_creator_dir()
        if not creator_dir or not os.path.exists(creator_dir):
            return

        for f in os.listdir(creator_dir):
            if f.endswith("_creator.json"):
                f_path = os.path.join(creator_dir, f)
                try:
                    with open(f_path, "r", encoding="utf-8") as file:
                        data = json.load(file)
                        self.custom_pals.append(data)
                except Exception: pass

    def add_custom_pal(self, pal_id: str, template_id: str):
        """Clones a parent template from cache and instantiates a new Creator JSON on disk."""
        creator_dir = self.get_creator_dir()
        if not creator_dir:
            self.view.show_snackbar("Configure your Workspace Folder first.", "#E53935")
            return

        clean_id = re.sub(r'[^a-zA-Z0-9_]', '_', pal_id.strip())
        if not clean_id: return

        # Validate duplicate IDs (Synchronously verified in memory to notify instantly)
        if any(p.get("CharacterID") == clean_id for p in self.custom_pals):
            self.view.show_snackbar(f"Error: A Pal named '{clean_id}' already exists!", "#E53935")
            return

        # Safeguard duplicate checks against native base game Pal IDs
        from utils.names import load_names_map
        names_map = load_names_map()
        if clean_id in names_map:
            self.view.show_snackbar(f"Error: '{clean_id}' is a reserved vanilla Pal name.", "#E53935")
            return

        # FIRE AND FORGET: Spawn background thread for cloning and writing
        def background_adder():
            import time
            time.sleep(0.1) # Yield GIL so Flet UI can close dialog instantly
            
            os.makedirs(creator_dir, exist_ok=True)
            
            # Clone raw properties from our monster template cache
            base_properties = self.templates_cache.get(template_id, {})
            cloned_learnset = self.learnsets_cache.get(template_id, [])

            # Predict default Saddle Items & Coop passive buffers based on parent template choice
            predicted_saddle = f"SkillUnlock_{template_id}"
            predicted_coop_passives = []
            if "weaseldragon" in template_id.lower() or "amaterasuwolf" in template_id.lower():
                predicted_coop_passives.append("GiveADragon_Ride")

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
                "CoopPassives": predicted_coop_passives
            }

            target_file = os.path.join(creator_dir, f"{clean_id}_creator.json")
            try:
                with open(target_file, "w", encoding="utf-8") as f:
                    json.dump(new_pal_data, f, indent=4)
                self.view.write_log(f"Successfully created brand new Pal template: {clean_id}", "success")
                
                # Auto-compile and deploy to PalSchema mods directory immediately!
                self.export_to_palschema(new_pal_data)
            except Exception as e:
                self.view.write_log(f"Failed to save new Pal: {e}", "error")

            self.refresh_pals()

        threading.Thread(target=background_worker_wrapper(background_adder), daemon=True).start()

    def save_custom_pal(self, pal_id: str, updated_data: dict):
        """Asynchronously writes edited parameters back to the localized JSON file."""
        creator_dir = self.get_creator_dir()
        if not creator_dir: return

        target_file = os.path.join(creator_dir, f"{pal_id}_creator.json")
        
        def background_writer():
            import time
            time.sleep(0.1) # Yield to UI thread
            try:
                with open(target_file, "w", encoding="utf-8") as f:
                    json.dump(updated_data, f, indent=4)
                self.view.write_log(f"Successfully saved Pal Creator adjustments: {pal_id}", "success")
                
                # Auto-compile and deploy to PalSchema mods directory
                self.export_to_palschema(updated_data)
            except Exception as e:
                self.view.write_log(f"Failed to write Pal updates: {e}", "error")
            self.refresh_pals()

        threading.Thread(target=background_writer, daemon=True).start()

    def export_to_palschema(self, p: dict):
        """Compiles and auto-deploys custom Pal statistics and learnset modifications to PalSchema mods."""
        mods_dir = self.get_palschema_mods_dir()
        if not mods_dir:
            self.view.write_log("PalSchema directory not found. Skipping auto-export. Install PalSchema first.", "warning")
            return

        pal_id = p["CharacterID"]
        template_id = p["TemplateID"]
        mod_name = f"PalBaker_Custom_{pal_id}"
        mod_root = os.path.join(mods_dir, mod_name)
        
        # Pull standard template properties to clone unconfigured fields safely
        base_properties = self.templates_cache.get(template_id, {})
        
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
        
        # Flatten work suitabilities directly into the row struct to prevent PalSchema PropertyNotFound crashes
        suitabilities = p.get("WorkSuitabilities", {})
        for k, v in suitabilities.items():
            pals_payload[f"MOD_{pal_id}"][k] = v
            
        with open(os.path.join(pals_dir, f"{pal_id}.json"), "w", encoding="utf-8") as f:
            json.dump(pals_payload, f, indent=4)

        # 2. Write Name & Description Translations (Bypassing UE L10N tables)
        trans_dir = os.path.join(mod_root, "translations", "en")
        os.makedirs(trans_dir, exist_ok=True)
        
        trans_payload = {
            "DT_PalNameText": {
                f"PAL_NAME_MOD_{pal_id}": p["Name"]
            },
            # Corrected destination descriptor table to align with custom raw game logs
            "DT_PalFirstActivatedInfoText": {
                f"PAL_FIRST_SPAWN_DESC_MOD_{pal_id}": p["Description"]
            }
        }
        with open(os.path.join(trans_dir, "names.json"), "w", encoding="utf-8") as f:
            json.dump(trans_payload, f, indent=4)

        # 3. Write Waza Master Level (Learnset)
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

        # 4. Write Blueprint Patch (Co-Op Overrides)
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

        # 5. Write Custom Icon Row (Bypassing PalSchema Resource Reader)
        fmodel_base = self.settings.get("fmodel_output", "")
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

        self.view.write_log(f"Auto-deployed custom Pal to PalSchema: {mod_name}", "success")

    def delete_custom_pal(self, pal_id: str):
        """Removes the local creator JSON configuration file permanently from disk."""
        creator_dir = self.get_creator_dir()
        if not creator_dir: return

        target_file = os.path.join(creator_dir, f"{pal_id}_creator.json")
        
        def background_deleter():
            import time
            time.sleep(0.1) # Yield to UI thread
            if os.path.exists(target_file):
                try:
                    os.remove(target_file)
                    self.view.write_log(f"Deleted custom Pal: {pal_id}", "warning")
                except Exception as e:
                    self.view.write_log(f"Failed to delete Pal config: {e}", "error")
            self.refresh_pals()

        threading.Thread(target=background_worker_wrapper(background_deleter), daemon=True).start()

    def refresh_pals(self):
        """Instructs the main view to re-render using cached list entries."""
        self.load_custom_pals()
        self.view.refresh_creator_mods_ui()


def background_worker_wrapper(func):
    """Safeguards background exception contexts to prevent thread leaks."""
    def wrapper():
        try: func()
        except Exception as e: print(f"[Creator Controller] Worker crashed: {e}")
    return wrapper