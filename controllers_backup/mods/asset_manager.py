# controllers/mods/asset_manager.py
import os
import shutil
import asyncio

class AssetManager:
    def __init__(self, controller):
        self.c = controller

    def get_category_from_path(self, path: str) -> str:
        if not path:
            return "Monster"
        parts = path.replace("\\", "/").split("/")
        if "Character" in parts:
            idx = parts.index("Character")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        return "Monster"

    def apply_custom_icon(self, mod_data: dict, src_path: str):
        """Copies the custom uploaded PNG icon file strictly inside the mod's local workspace folder."""
        fmodel_path = mod_data.get("fmodel_path")
        if fmodel_path:
            target_path = os.path.normpath(os.path.join(fmodel_path, f"T_{mod_data['name']}_icon_normal.png"))
            try:
                os.makedirs(fmodel_path, exist_ok=True)
                shutil.copy2(src_path, target_path)
                self.c.view.write_log(f"SUCCESS: Set custom icon for {mod_data['name']}.", "success")
                self.c.refresh_mods(scan_disk=True, target_mod=mod_data["name"])
            except Exception as e:
                self.c.view.write_log(f"ERROR: Failed to apply custom icon: {e}", "error")

    def build_pal_database(self):
        """Asynchronously extracts, transforms, and rebuilds the local pal_names_map.json."""
        self.c.is_building = True
        self.c.view.set_refresh_state(loading=True)
        self.c.view.write_log("\n>>> EXTRACTING AND BUILDING PAL NAMES DATABASE FROM GAME PAKS", "stage")

        async def build_task():
            from utils.extractor import build_pal_names_map
            success, msg = await asyncio.to_thread(build_pal_names_map, self.c.settings)
            
            if success:
                self.c.view.write_log(f"SUCCESS: {msg}", "success")
                import utils.names
                utils.names._names_cache.clear()
            else:
                self.c.view.write_log(f"FAILED to build database: {msg}", "error")

            self.c.is_building = False
            self.c.view.set_refresh_state(loading=False)
            self.c.refresh_mods(scan_disk=True)

        self.c.view.run_async_task(build_task)

    def execute_extraction_pipeline(self, mod_data: dict):
        """Dispatches an asynchronous, non-blocking pipeline task to extract raw game visual assets."""
        self.c.is_building = True
        self.c.active_mod_name = mod_data["name"]
        self.c.refresh_mods(scan_disk=False)
        self.c.view.write_log(f"\n>>> EXTRACTING MODEL & TEXTURES FOR: {mod_data['name']}", "stage")

        async def extract_task():
            import time
            time.sleep(0.1)
            from utils.extractor import extract_pal_assets
            
            success, msg = await asyncio.to_thread(
                extract_pal_assets,
                self.c.settings,
                mod_data["name"],
                "Monster"
            )

            if success:
                self.c.view.write_log(f"SUCCESS: {msg}", "success")
            else:
                self.c.view.write_log(f"FAILED: {msg}", "error")

            self.c.is_building = False
            self.c.active_mod_name = ""
            self.c.view.reset_card_state(mod_data["name"], success)
            self.c.refresh_mods(scan_disk=False)
            self.c.refresh_mods(scan_disk=True, target_mod=mod_data["name"])

        self.c.view.run_async_task(extract_task)