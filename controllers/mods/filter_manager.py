# controllers/mods/filter_manager.py
import os
from utils import get_mod_info
from utils.altermatic_helper import load_traits_database

class FilterManager:
    def __init__(self, controller):
        self.c = controller
        
        self.search_query = ""
        self.show_unextracted = False  
        self.selected_badges = set()
        self.selected_statuses = set()
        self.traits_db = load_traits_database()

    def update_search(self, query: str):
        self.search_query = query
        self.apply_filters()

    def toggle_unextracted(self, value: bool):
        self.show_unextracted = value
        self.apply_filters()

    def update_badge_filter(self, badge: str, selected: bool):
        if selected:
            self.selected_badges.add(badge)
        else:
            self.selected_badges.discard(badge)
        self.apply_filters()

    def update_status_filter(self, status: str, selected: bool):
        if selected:
            self.selected_statuses.add(status)
        else:
            self.selected_statuses.discard(status)
        self.apply_filters()

    def refresh_mods(self, scan_disk: bool = True, target_mod: str = None):
        self.c.show_mapped = bool(self.c.settings.get("show_mapped", False))

        if scan_disk:
            if not target_mod:
                self.c.view.set_refresh_state(loading=True)
                
            def worker():
                try:
                    if target_mod and len(self.c.raw_mods) > 0:
                        updated_mods = get_mod_info(self.c.settings, target_mod)
                        if updated_mods:
                            updated_mod = updated_mods[0]
                            for i, m in enumerate(self.c.raw_mods):
                                if m["name"] == target_mod:
                                    self.c.raw_mods[i] = updated_mod
                                    break
                            else:
                                self.c.raw_mods.append(updated_mod)
                                
                            self.c.view.evict_cache(target_mod)
                    else:
                        self.c.raw_mods = get_mod_info(self.c.settings)
                        self.c.view.clear_ui_cache()
                except Exception as e:
                    print(f"[PalBaker] Disk scan encountered an error: {e}", flush=True)
                finally:
                    if not target_mod:
                        self.c.view.set_refresh_state(loading=False)
                    self.apply_filters()
                    
            self.c.view.run_in_thread(worker)
        else:
            self.apply_filters()

    def apply_filters(self):
        fmodel_dir = str(self.c.settings.get("fmodel_output", ""))
        if not fmodel_dir or not os.path.exists(fmodel_dir):
            self.c.view.render_error("Set a valid Workspace Folder in Settings.")
            return

        filtered_mods = []
        for mod in self.c.raw_mods:
            if not self.show_unextracted and mod["pak_status"] == "Unextracted":
                continue

            search_lower = self.search_query.lower()
            name_match = (search_lower in mod["name"].lower()) or (search_lower in mod["localized_name"].lower())
            if not name_match: continue

            if self.selected_badges:
                mod_badges = {b[0] for b in mod["badges"]}
                if not self.selected_badges.issubset(mod_badges): continue

            if self.selected_statuses:
                if mod["pak_status"] not in self.selected_statuses: continue

            filtered_mods.append(mod)

        filtered_mods.sort(key=lambda x: str(x["localized_name"] if self.c.show_mapped else x["name"]).lower())

        if not filtered_mods:
            self.c.view.render_empty()
        else:
            self.c.view.render_mods(filtered_mods, self.c.is_building, self.c.active_mod_name)