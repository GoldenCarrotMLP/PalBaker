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

# Import our dedicated concerns
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
        self.show_mapped = False
        self.selected_badges: set[str] = set()
        self.selected_statuses: set[str] = set()

        # Delegate custom sub-systems cleanly to children
        self.audio = AudioController(self)
        self.altermatic = AltermaticController(self)

        # Load traits database
        from utils.altermatic_helper import load_traits_database
        self.traits_db = load_traits_database()

    def get_category_from_path(self, path: str) -> str:
        """Parses a physical file path to resolve the true character category (e.g. Monster, Pending Monster)."""
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
        """Rescans the directory for mods. If target_mod is supplied, performs an instant micro-update."""
        self.show_mapped = bool(self.settings.get("show_mapped", False))

        if scan_disk:
            # Skip global loading spinners during targeted micro-updates
            if not target_mod:
                self.view.set_refresh_state(loading=True)
                
            def worker():
                try:
                    if target_mod and len(self.raw_mods) > 0:
                        # Fetch the targeted file directly inside O(1) bypassing os.walk
                        updated_mods = get_mod_info(self.settings, target_mod)
                        if updated_mods:
                            updated_mod = updated_mods[0]
                            for i, m in enumerate(self.raw_mods):
                                if m["name"] == target_mod:
                                    self.raw_mods[i] = updated_mod
                                    break
                            else:
                                self.raw_mods.append(updated_mod)
                                
                            # Evict just this one card from the visual cache so it rebuilds its nested objects natively
                            self.view.evict_cache(target_mod)
                    else:
                        # Full clean global initialization
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
            self.view.render_error("Set a valid FModel Output Folder in Settings.")
            return

        filtered_mods = []
        for mod in self.raw_mods:
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
        self.audio.mc.apply_custom_icon(mod_data, src_path)

    async def run_async_task_threadsafe(self, func, *args):
        """Helper used to safely await asynchronous background threads."""
        return await asyncio.to_thread(func, *args)

    # --- Dispatcher mappings to keep View/Card interfaces stable ---
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
        """Dispatches a background compile pipeline to headlessly refresh all active .blend layouts."""
        mod_data = next((m for m in self.raw_mods if m["name"] == monster_name), None)
        if mod_data:
            self.execute_pipeline(mod_data, "refresh_blend")

    async def apply_custom_audio(self, mod_data: dict, cry_name: str, src_path: str):
        await self.audio.apply_custom_audio(mod_data, cry_name, src_path)

    async def clear_audio(self, mod_data: dict, cry_name: str):
        await self.audio.clear_audio(mod_data, cry_name)

    async def play_audio(self, mod_data: dict, cry_name: str):
        await self.audio.play_audio(mod_data, cry_name)

    # --- PIPELINE ORCHESTRATORS ---
    def handle_action(self, mod_data, action):
        if self.is_building: return

        if action in ["push", "full"] and mod_data.get("ue_modified"):
            self.view.prompt_overwrite_warning(mod_data, lambda: self.execute_pipeline(mod_data, action))
        elif action == "decompile":
            self.view.prompt_decompile_options(mod_data)
        elif action == "browse_unreal":
            self.execute_browse_unreal(mod_data)
        else:
            self.execute_pipeline(mod_data, action)

    def handle_cancel(self):
        if self.active_token and self.active_token.get("process"):
            self.view.write_log("\n[!] Force terminating the active pipeline...", "error")
            try:
                proc = self.active_token["process"]
                if os.name == 'nt':
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
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
            
            # FIXED: Sanitized spaces for UE remote execution path handling
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

            # FIXED: Sanitized spaces for UE remote execution path handling
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


def get_blend_files_for_context(category: str, character_id: str) -> list[str]:
    """Scans the local staging workspace directory for .blend files dynamically."""
    from utils.config import load_settings
    settings = load_settings()
    fmodel_root = settings.get("fmodel_output", "")
    if not fmodel_root:
        return []
    
    target_dir = os.path.join(fmodel_root, "Exports", "Pal", "Content", "Palbaker", "Model", "Character", category, character_id)
    blend_files = []
    if os.path.exists(target_dir):
        for f in os.listdir(target_dir):
            if f.endswith(".blend") and not f.startswith(f"{character_id}_Default"):
                blend_files.append(f)
    return blend_files