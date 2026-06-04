# controllers/mods_controller.py
import asyncio
import os
import sys
import shutil
import subprocess
from utils import get_mod_info
from utils.builder.pipeline_runner import run_pipeline_async
from utils.builder.log_analyzer import LogAnalyzer
from utils.plugins.decompiler import run_decompile_pipeline

from controllers.audio_controller import AudioController
from controllers.altermatic import AltermaticController

class ModsController:
    def __init__(self, view, settings: dict):
        self.view = view
        self.settings = settings
        
        self.is_building = False
        self.active_mod_name = ""
        self.active_token = {"process": None}
        
        self.raw_mods: list[dict] = []
        self.search_query = ""
        self.show_unextracted = False  # Proposal C Toggle State
        self.selected_badges: set[str] = set()
        self.selected_statuses: set[str] = set()

        self.audio = AudioController(self)
        self.altermatic = AltermaticController(self)

        from utils.altermatic_helper import load_traits_database
        self.traits_db = load_traits_database()

    def get_category_from_path(self, path: str) -> str:
        if not path:
            return "Monster"
        parts = path.replace("\\", "/").split("/")
        if "Character" in parts:
            idx = parts.index("Character")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        return "Monster"

    def update_search(self, query: str):
        self.search_query = query
        self.apply_filters()

    def toggle_unextracted(self, value: bool):
        """Toggles the dynamic filter representing Proposal C."""
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
        self.show_mapped = bool(self.settings.get("show_mapped", False))

        if scan_disk:
            if not target_mod:
                self.view.set_refresh_state(loading=True)
                
            def worker():
                try:
                    if target_mod and len(self.raw_mods) > 0:
                        updated_mods = get_mod_info(self.settings, target_mod)
                        if updated_mods:
                            updated_mod = updated_mods[0]
                            for i, m in enumerate(self.raw_mods):
                                if m["name"] == target_mod:
                                    self.raw_mods[i] = updated_mod
                                    break
                            else:
                                self.raw_mods.append(updated_mod)
                                
                            self.view.evict_cache(target_mod)
                    else:
                        self.raw_mods = get_mod_info(self.settings)
                        self.view.clear_ui_cache()
                except Exception as e:
                    print(f"[PalBaker] Disk scan encountered an error: {e}", flush=True)
                finally:
                    if not target_mod:
                        self.view.set_refresh_state(loading=False)
                    self.apply_filters()
                    
            self.view.run_in_thread(worker)
        else:
            self.apply_filters()

    def apply_filters(self):
        fmodel_dir = str(self.settings.get("fmodel_output", ""))
        if not fmodel_dir or not os.path.exists(fmodel_dir):
            self.view.render_error("Set a valid Workspace Folder in Settings.")
            return

        filtered_mods = []
        for mod in self.raw_mods:
            # PROPOSAL C: Filter out unextracted Pals unless explicitly toggled ON
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

        filtered_mods.sort(key=lambda x: str(x["localized_name"] if self.show_mapped else x["name"]).lower())

        if not filtered_mods:
            self.view.render_empty()
        else:
            self.view.render_mods(filtered_mods, self.is_building, self.active_mod_name)

    def apply_custom_icon(self, mod_data: dict, src_path: str):
        """Copies the custom uploaded PNG icon file strictly inside the mod's local workspace folder."""
        fmodel_path = mod_data.get("fmodel_path")
        if fmodel_path:
            target_path = os.path.normpath(os.path.join(fmodel_path, f"T_{mod_data['name']}_icon_normal.png"))
            try:
                os.makedirs(fmodel_path, exist_ok=True)
                shutil.copy2(src_path, target_path)
                self.view.write_log(f"SUCCESS: Set custom icon for {mod_data['name']}.", "success")
                self.refresh_mods(scan_disk=True, target_mod=mod_data["name"])
            except Exception as e:
                self.view.write_log(f"ERROR: Failed to apply custom icon: {e}", "error")

    async def run_async_task_threadsafe(self, func, *args):
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
        """Asynchronously extracts, transforms, and rebuilds the local pal_names_map.json."""
        self.is_building = True
        self.view.set_refresh_state(loading=True)
        self.view.write_log("\n>>> EXTRACTING AND BUILDING PAL NAMES DATABASE FROM GAME PAKS", "stage")

        async def build_task():
            from utils.extractor_helper import build_pal_names_map
            success, msg = await asyncio.to_thread(build_pal_names_map, self.settings)
            
            if success:
                self.view.write_log(f"SUCCESS: {msg}", "success")
                import utils.names
                utils.names._names_cache.clear()
            else:
                self.view.write_log(f"FAILED to build database: {msg}", "error")

            self.is_building = False
            self.view.set_refresh_state(loading=False)
            self.refresh_mods(scan_disk=True)

        self.view.run_async_task(build_task)

    def execute_extraction_pipeline(self, mod_data: dict):
        """Dispatches an asynchronous, non-blocking pipeline task to extract raw game visual assets."""
        self.is_building = True
        self.active_mod_name = mod_data["name"]
        self.refresh_mods(scan_disk=False)
        self.view.write_log(f"\n>>> EXTRACTING MODEL & TEXTURES FOR: {mod_data['name']}", "stage")

        async def extract_task():
            import time
            time.sleep(0.1) # Yield GIL so WebSocket UI can flush
            from utils.extractor_helper import extract_pal_assets
            
            success, msg = await asyncio.to_thread(
                extract_pal_assets,
                self.settings,
                mod_data["name"],
                "Monster"  # Assumes standard monster class categories
            )

            if success:
                self.view.write_log(f"SUCCESS: {msg}", "success")
            else:
                self.view.write_log(f"FAILED: {msg}", "error")

            self.is_building = False
            self.active_mod_name = ""
            self.view.reset_card_state(mod_data["name"], success)
            self.refresh_mods(scan_disk=False)
            self.refresh_mods(scan_disk=True, target_mod=mod_data["name"])

        self.view.run_async_task(extract_task)

    def handle_action(self, mod_data, action):
        if self.is_building: return

        if action == "extract_pal":
            self.execute_extraction_pipeline(mod_data)
        elif action in ["push", "full"] and mod_data.get("ue_modified"):
            self.view.prompt_overwrite_warning(mod_data, lambda: self.execute_pipeline(mod_data, action))
        elif action == "decompile":
            self.view.prompt_decompile_options(mod_data)
        elif action == "browse_unreal":
            self.execute_browse_unreal(mod_data)
        else:
            self.execute_pipeline(mod_data, action)

    def handle_cancel(self):
        """Cross-platform safe termination mechanism preventing zombie processes."""
        if self.active_token and self.active_token.get("process"):
            self.view.write_log("\n[!] Force terminating the active pipeline...", "error")
            try:
                proc = self.active_token["process"]
                if os.name == 'nt':
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    import signal
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except Exception as pg_err:
                        print(f"Failed to kill process group: {pg_err}", flush=True)
                        proc.kill()
            except Exception as e:
                self.view.write_log(f"Error terminating process: {e}", "error")

    def execute_decompile_pipeline(self, mod_data, overwrite: bool = False):
        self.is_building = True
        self.active_mod_name = mod_data["name"]
        self.refresh_mods(scan_disk=False)
        self.view.write_log(f"\n>>> EXECUTING DECOMPILER: {mod_data['name']}", "stage")
        
        async def decompile_task():
            fmodel_dir = mod_data["fmodel_path"]
            
            category = self.get_category_from_path(fmodel_dir)
            category_sanitized = category.replace(" ", "_")
            ue_virtual_path = f"/Game/Pal/Model/Character/{category_sanitized}/{mod_data['name']}"
            
            success, msg = await asyncio.to_thread(
                run_decompile_pipeline,
                self.settings["ue_root"],
                self.settings["uproject"],
                mod_data["name"],
                fmodel_dir,
                ue_virtual_path,
                self.settings["blender"],
                verbose=True,
                overwrite=overwrite
            )
            
            from utils.builder.log_analyzer import LogAnalyzer
            analyzer = LogAnalyzer()
            for line in msg.splitlines():
                analyzed_text, category_log, is_error = analyzer.analyze_line(line)
                self.view.write_log(analyzed_text, category_log, flush=False)
                
            summary = analyzer.generate_summary(success)
            status = summary.get("status", "failed") if summary else "pure_success"
            
            if success and status == "pure_success":
                self.view.write_log("SUCCESS: Decompile completed cleanly.", "success")
            elif status == "success_with_warnings":
                self.view.write_log("WARNING: Decompile completed with warnings.", "warning")
            elif status == "success_with_errors":
                self.view.write_log("ERROR: Decompile completed but found compiler errors.", "error")
            else:
                self.view.write_log("FAILED: Decompile failed. Check logs.", "error")
                
            self.is_building = False
            self.active_mod_name = ""
            
            if summary:
                self.view.prompt_troubleshooting_advisor(summary)
                
            self.refresh_mods(scan_disk=False)
            self.refresh_mods(scan_disk=True, target_mod=mod_data["name"])
            
        self.view.run_async_task(decompile_task)

    def execute_pipeline(self, mod_data, action):
        self.is_building = True
        self.view.set_log_autoscroll(True)
        self.active_mod_name = mod_data["name"]
        self.refresh_mods(scan_disk=False)
        self.view.write_log(f"\n>>> EXECUTING [{action.upper()}]: {mod_data['name']}", "stage")
        
        self.active_token = {"process": None}
        
        async def run_task():
            def log_callback(text, category, flush=True):
                if text is not None:
                    self.view.write_log(text, category, flush=False)
                if flush:
                    self.view.force_update()
                    
            def progress_callback(line, flush=True):
                self.view.update_card_progress(self.active_mod_name, line, flush)
                        
            def complete_callback(success, returncode, summary):
                status = "pure_success"
                if summary:
                    status = summary.get("status", "failed")

                if status == "pure_success" and success:
                    self.view.write_log("SUCCESS: Operation completed cleanly.", "success")
                elif status == "success_with_warnings":
                    self.view.write_log(f"WARNING: Operation completed with {summary['total_warnings']} warnings.", "warning")
                elif status == "success_with_errors":
                    self.view.write_log(f"ERROR: Operation completed but found {summary['total_errors']} compilation errors.", "error")
                else:
                    self.view.write_log(f"FAILED: Process terminated with exit code {returncode}", "error")
                
                self.is_building = False
                self.view.set_log_autoscroll(False)
                self.active_token = {"process": None}
                
                card_success = success and (status != "success_with_errors")
                self.view.reset_card_state(self.active_mod_name, card_success)
                self.active_mod_name = ""
                
                if summary:
                    self.view.prompt_troubleshooting_advisor(summary)
                    
                self.refresh_mods(scan_disk=False)
                self.refresh_mods(scan_disk=True, target_mod=mod_data["name"])

            f_path = mod_data.get("fmodel_path") or mod_data.get("fmodel_altermatic_path") or mod_data.get("ue_path")
            category = self.get_category_from_path(f_path)

            script_args = [mod_data["name"], category, action]
            await run_pipeline_async(script_args, log_callback, progress_callback, complete_callback, self.active_token)

        self.view.run_async_task(run_task)

    def execute_browse_unreal(self, mod_data):
        self.is_building = True
        self.active_mod_name = mod_data["name"]
        self.refresh_mods(scan_disk=False)
        self.view.write_log(f"\n>>> FOCUSING UNREAL CONTENT BROWSER: {mod_data['name']}", "stage")
        
        async def browse_task():
            f_path = mod_data.get("fmodel_path") or mod_data.get("fmodel_altermatic_path") or mod_data.get("ue_path")
            category = self.get_category_from_path(f_path)

            category_sanitized = category.replace(" ", "_")
            ue_virtual_path = f"/Game/Pal/Model/Character/{category_sanitized}/{mod_data['name']}"
            python_cmd = f'import unreal; unreal.EditorUtilityLibrary.sync_browser_to_folders(["{ue_virtual_path}"])'
            
            from utils.builder.unreal_helper import run_remote_command, focus_unreal_window
            target_project_name = os.path.splitext(os.path.basename(self.settings["uproject"]))[0]
            
            success, msg = await asyncio.to_thread(
                run_remote_command,
                self.settings["ue_root"],
                target_project_name,
                python_cmd
            )
            
            if success:
                self.view.write_log(f"SUCCESS: Focused Content Browser to: {ue_virtual_path}", "success")
                focus_unreal_window(target_project_name)
            else:
                self.view.write_log(f"FAILED to focus Unreal: {msg}", "error")
                
            self.is_building = False
            self.active_mod_name = ""
            self.refresh_mods(scan_disk=False)
            
        self.view.run_async_task(browse_task)