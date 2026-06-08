# controllers/creator/cache_loader.py
import os
import json

class CacheLoader:
    def __init__(self):
        self.active_skills_cache = {}
        self.passive_skills_cache = {}
        self.partner_skills_cache = {}
        self.coop_passives_cache = {}  
        self.monster_spawners_cache = {}
        self.monster_spawners_default_map = {}
        self.templates_cache = {}
        self.learnsets_cache = {}
        self.camera_offsets_cache = {}

    def load_index_caches(self):
        """Loads static caches from the local deps directory."""
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
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

        # Load Learnset Cache
        learnset_path = os.path.join(repo_root, "deps", "waza_master_level_cache.json")
        if os.path.exists(learnset_path):
            try:
                with open(learnset_path, "r", encoding="utf-8") as f:
                    self.learnsets_cache = json.load(f)
            except Exception: pass

        # Load Wild Spawner Locations directory
        spawners_path = os.path.join(repo_root, "deps", "monster_spawners_cache.json")
        if os.path.exists(spawners_path):
            try:
                with open(spawners_path, "r", encoding="utf-8") as f:
                    self.monster_spawners_cache = json.load(f)
            except Exception: pass

        # Load default spawner map
        default_map_path = os.path.join(repo_root, "deps", "monster_spawners_default_map.json")
        if os.path.exists(default_map_path):
            try:
                with open(default_map_path, "r", encoding="utf-8") as f:
                    self.monster_spawners_default_map = json.load(f)
            except Exception: pass

        # Load Camera Offsets Cache
        camera_offsets_path = os.path.join(repo_root, "deps", "camera_offsets_cache.json")
        if os.path.exists(camera_offsets_path):
            try:
                with open(camera_offsets_path, "r", encoding="utf-8") as f:
                    self.camera_offsets_cache = json.load(f)
            except Exception: pass