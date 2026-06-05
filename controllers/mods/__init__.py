# controllers/mods/__init__.py
from .filter_manager import FilterManager
from .pipeline_executor import PipelineExecutor
from .asset_manager import AssetManager
from controllers.audio_controller import AudioController
from controllers.altermatic import AltermaticController

class ModsController:
    def __init__(self, view, settings: dict):
        self.view = view
        self.settings = settings
        
        self.filter = FilterManager(self)
        self.executor = PipelineExecutor(self)
        self.asset = AssetManager(self)
        self.audio = AudioController(self)
        self.altermatic = AltermaticController(self)
        
        # Facade routing maps
        self.raw_mods = []
        self.traits_db = self.filter.traits_db
        
    @property
    def is_building(self):
        return self.executor.is_building
    @is_building.setter
    def is_building(self, value):
        self.executor.is_building = value
        
    @property
    def active_mod_name(self):
        return self.executor.active_mod_name
    @active_mod_name.setter
    def active_mod_name(self, value):
        self.executor.active_mod_name = value
        
    @property
    def active_token(self):
        return self.executor.active_token
    @active_token.setter
    def active_token(self, value):
        self.executor.active_token = value
        
    @property
    def search_query(self):
        return self.filter.search_query
    @search_query.setter
    def search_query(self, value):
        self.filter.search_query = value
        
    @property
    def show_unextracted(self):
        return self.filter.show_unextracted
    @show_unextracted.setter
    def show_unextracted(self, value):
        self.filter.show_unextracted = value
        
    @property
    def selected_badges(self):
        return self.filter.selected_badges
    @selected_badges.setter
    def selected_badges(self, value):
        self.filter.selected_badges = value
        
    @property
    def selected_statuses(self):
        return self.filter.selected_statuses
    @selected_statuses.setter
    def selected_statuses(self, value):
        self.filter.selected_statuses = value
        
    def get_category_from_path(self, path: str) -> str:
        return self.asset.get_category_from_path(path)
        
    def update_search(self, query: str):
        self.filter.update_search(query)
        
    def toggle_unextracted(self, value: bool):
        self.filter.toggle_unextracted(value)
        
    def update_badge_filter(self, badge: str, selected: bool):
        self.filter.update_badge_filter(badge, selected)
        
    def update_status_filter(self, status: str, selected: bool):
        self.filter.update_status_filter(status, selected)
        
    def refresh_mods(self, scan_disk: bool = True, target_mod: str = None):
        self.filter.refresh_mods(scan_disk, target_mod)
        
    def apply_filters(self):
        self.filter.apply_filters()
        
    def apply_custom_icon(self, mod_data: dict, src_path: str):
        self.asset.apply_custom_icon(mod_data, src_path)
        
    async def run_async_task_threadsafe(self, func, *args):
        import asyncio
        return await asyncio.to_thread(func, *args)
        
    def toggle_altermatic(self, mod_data: dict, is_active: bool):
        self.altermatic.toggle_altermatic(mod_data, is_active)
        
    def add_altermatic_variant(self, mod_data: dict):
        self.altermatic.add_altermatic_variant(mod_data)
        
    def edit_altermatic_variant(self, mod_data: dict, index: int):
        self.altermatic.edit_altermatic_variant(mod_data, index)
        
    def delete_altermatic_variant(self, mod_data: dict, index: int):
        self.altermatic.delete_altermatic_variant(mod_data, index)
        
    def delete_altermatic_variant_by_index(self, monster_name: str, index: int):
        self.altermatic.delete_altermatic_variant_by_index(monster_name, index)
        
    def save_altermatic_variant_callback(self, index: int, variant_data: dict):
        self.altermatic.save_altermatic_variant_callback(index, variant_data)
        
    def run_refresh_pipeline_callback(self, monster_name: str):
        mod_data = next((m for m in self.raw_mods if m["name"] == monster_name), None)
        if mod_data:
            self.execute_pipeline(mod_data, "refresh_blend")
            
    async def apply_custom_audio(self, mod_data: dict, cry_name: str, src_path: str):
        await self.audio.apply_custom_audio(mod_data, cry_name, src_path)
        
    async def clear_audio(self, mod_data: dict, cry_name: str):
        await self.audio.clear_audio(mod_data, cry_name)
        
    async def play_audio(self, mod_data: dict, cry_name: str):
        await self.audio.play_audio(mod_data, cry_name)
        
    def build_pal_database(self):
        self.asset.build_pal_database()
        
    def execute_extraction_pipeline(self, mod_data: dict):
        self.asset.execute_extraction_pipeline(mod_data)
        
    def handle_action(self, mod_data, action):
        self.executor.handle_action(mod_data, action)
        
    def execute_decompile_pipeline(self, mod_data, overwrite: bool = False):
        self.executor.execute_decompile_pipeline(mod_data, overwrite)
        
    def execute_pipeline(self, mod_data, action):
        self.executor.execute_pipeline(mod_data, action)
        
    def execute_browse_unreal(self, mod_data):
        self.executor.execute_browse_unreal(mod_data)
        
    def handle_cancel(self):
        self.executor.handle_cancel()