# controllers/creator/__init__.py
from .cache_loader import CacheLoader
from .pal_manager import PalManager
from .palschema_exporter import PalSchemaExporter

class CreatorController:
    def __init__(self, view, settings: dict):
        self.view = view
        self.settings = settings
        self.custom_pals = []
        
        self.cache = CacheLoader()
        self.manager = PalManager(self)
        self.exporter = PalSchemaExporter(self)
        
        # Facade routing maps
        self.active_skills_cache = {}
        self.passive_skills_cache = {}
        self.partner_skills_cache = {}
        self.coop_passives_cache = {}  
        self.monster_spawners_cache = {}
        self.monster_spawners_default_map = {}
        self.templates_cache = {}
        self.learnsets_cache = {}
        self.camera_offsets_cache = {}
        self.pal_drop_item_cache = {} # Added
        
        # Load index caches on startup and dynamically update facade pointers
        self.load_index_caches()
        
    def load_index_caches(self):
        self.cache.load_index_caches()
        
        # In-place pointer updates to preserve Flet UI view references
        self.active_skills_cache.clear()
        self.active_skills_cache.update(self.cache.active_skills_cache)
        
        self.passive_skills_cache.clear()
        self.passive_skills_cache.update(self.cache.passive_skills_cache)
        
        self.partner_skills_cache.clear()
        self.partner_skills_cache.update(self.cache.partner_skills_cache)
        
        self.coop_passives_cache.clear()
        self.coop_passives_cache.update(self.cache.coop_passives_cache)
        
        self.monster_spawners_cache.clear()
        self.monster_spawners_cache.update(self.cache.monster_spawners_cache)
        
        self.monster_spawners_default_map.clear()
        self.monster_spawners_default_map.update(self.cache.monster_spawners_default_map)
        
        self.templates_cache.clear()
        self.templates_cache.update(self.cache.templates_cache)
        
        self.learnsets_cache.clear()
        self.learnsets_cache.update(self.cache.learnsets_cache)

        self.camera_offsets_cache.clear()
        self.camera_offsets_cache.update(self.cache.camera_offsets_cache)
        
        self.pal_drop_item_cache.clear()
        self.pal_drop_item_cache.update(self.cache.pal_drop_item_cache)
        
    def get_creator_dir(self) -> str | None:
        return self.manager.get_creator_dir()
        
    def get_palschema_mods_dir(self) -> str | None:
        return self.exporter.get_palschema_mods_dir()
        
    def load_custom_pals(self):
        self.manager.load_custom_pals()
        
    def add_custom_pal(self, pal_id: str, template_id: str):
        self.manager.add_custom_pal(pal_id, template_id)
        
    def save_custom_pal(self, pal_id: str, updated_data: dict):
        self.manager.save_custom_pal(pal_id, updated_data)
        
    def delete_custom_pal(self, pal_id: str):
        self.manager.delete_custom_pal(pal_id)
        
    def export_to_palschema(self, p: dict):
        self.exporter.export_to_palschema(p)
        
    def refresh_pals(self):
        self.manager.refresh_pals()

    def delete_palschema_export(self, pal_id: str):
        self.exporter.delete_palschema_export(pal_id)

    def refresh_actor_blueprint(self, pal_id: str):
        """Asynchronously extracts and patches the target Pal's parent blueprint."""
        pal_data = next((p for p in self.custom_pals if p["CharacterID"] == pal_id), None)
        if not pal_data:
            self.view.write_log(f"Error: Custom Pal configuration {pal_id} not found.", "error")
            self.refresh_pals()
            return
            
        self.view.write_log(f"Refreshing standalone Actor Blueprint for {pal_id}...", "standard")
        
        def worker():
            success = self.exporter.generate_custom_actor_blueprint(pal_data)
            if success:
                self.view.write_log(f"Successfully refreshed standalone Actor Blueprint for {pal_id}!", "success")
            else:
                self.view.write_log(f"Failed to generate Actor Blueprint for {pal_id}.", "error")
            self.refresh_pals()
            
        self.view.run_in_thread(worker)