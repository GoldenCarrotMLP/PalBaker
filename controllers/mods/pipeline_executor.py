# controllers/mods/pipeline_executor.py
import os
import sys
import subprocess
import asyncio
import flet as ft  # <-- ADDED THIS IMPORT TO FIX THE NameError  # type: ignore
from utils.builder.pipeline_runner import run_pipeline_async

class PipelineExecutor:
    def __init__(self, controller):
        self.c = controller
        
        self.is_building = False
        self.active_mod_name = ""
        self.active_token = {"process": None}

    def handle_action(self, mod_data, action):
        if self.is_building: return

        # Unreal Engine environment validation for specific pipelines
        if action in ["push", "full", "decompile", "browse_unreal"]:
            from utils.plugins.detector import check_remote_execution_settings
            from utils.plugins.installer import is_unreal_running, launch_unreal_editor, enable_remote_execution_settings
            
            uproject = self.c.settings.get("uproject", "")
            ue_root = self.c.settings.get("ue_root", "")
            
            # Check 1: Check if Remote Execution is statically disabled in INI
            if not check_remote_execution_settings(uproject):
                def on_fix_clicked():
                    enable_remote_execution_settings(uproject)
                    launch_unreal_editor(ue_root, uproject)
                    self.c.view.show_snackbar("Python Remote Execution enabled! Launching Unreal Editor... Please wait for it to fully load, then retry.", ft.Colors.GREEN_400)
                
                self.c.view.prompt_remote_exec_disabled_warning(on_fix_clicked)
                return
            
            # Check 2: Check if Unreal Editor is physically closed
            if not is_unreal_running():
                def on_launch_clicked():
                    launch_unreal_editor(ue_root, uproject)
                    self.c.view.show_snackbar("Launching Unreal Editor... Please wait for it to fully load, then retry.", ft.Colors.CYAN_400)
                
                self.c.view.prompt_unreal_closed_warning(on_launch_clicked)
                return

        if action == "extract_pal":
            self.c.execute_extraction_pipeline(mod_data)
        elif action in ["push", "full"] and mod_data.get("ue_modified"):
            self.c.view.prompt_overwrite_warning(mod_data, lambda: self.execute_pipeline(mod_data, action))
        elif action == "decompile":
            self.c.view.prompt_decompile_options(mod_data)
        elif action == "browse_unreal":
            self.c.execute_browse_unreal(mod_data)
        else:
            self.c.execute_pipeline(mod_data, action)

    def handle_cancel(self):
        """Cross-platform safe termination mechanism preventing zombie processes."""
        if self.active_token and self.active_token.get("process"):
            self.c.view.write_log("\n[!] Force terminating the active pipeline...", "error")
            try:
                proc = self.active_token["process"]
                if os.name == 'nt':
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # type: ignore
                else:
                    import signal
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)  # type: ignore
                    except Exception as pg_err:
                        print(f"Failed to kill process group: {pg_err}", flush=True)
                        if proc is not None:
                            proc.kill()  # type: ignore
            except Exception as e:
                self.c.view.write_log(f"Error terminating process: {e}", "error")

    def execute_decompile_pipeline(self, mod_data, overwrite: bool = False):
        self.is_building = True
        self.active_mod_name = mod_data["name"]
        self.c.refresh_mods(scan_disk=False)
        self.c.view.write_log(f"\n>>> EXECUTING DECOMPILER: {mod_data['name']}", "stage")
        
        async def decompile_task():
            fmodel_dir = mod_data["fmodel_path"]
            category = self.c.get_category_from_path(fmodel_dir)
            category_sanitized = category.replace(" ", "_")
            ue_virtual_path = f"/Game/Pal/Model/Character/{category_sanitized}/{mod_data['name']}"
            
            from utils.plugins.decompiler import run_decompile_pipeline
            success, msg = await asyncio.to_thread(
                run_decompile_pipeline,
                self.c.settings["ue_root"],
                self.c.settings["uproject"],
                mod_data["name"],
                fmodel_dir,
                ue_virtual_path,
                self.c.settings["blender"],
                verbose=True,
                overwrite=overwrite
            )
            
            from utils.builder.log_analyzer import LogAnalyzer
            analyzer = LogAnalyzer()
            for line in msg.splitlines():
                analyzed_text, category_log, _ = analyzer.analyze_line(line)
                self.c.view.write_log(analyzed_text, category_log, flush=False)
                
            summary = analyzer.generate_summary(success)
            status = summary.get("status", "failed") if summary else "pure_success"
            
            if success and status == "pure_success":
                self.c.view.write_log("SUCCESS: Decompile completed cleanly.", "success")
            elif status == "success_with_warnings":
                self.c.view.write_log("WARNING: Decompile completed with warnings.", "warning")
            elif status == "success_with_errors":
                self.c.view.write_log("ERROR: Decompile completed but found compiler errors.", "error")
            else:
                self.c.view.write_log("FAILED: Decompile failed. Check logs.", "error")
                
            self.is_building = False
            self.active_mod_name = ""
            
            if summary:
                self.c.view.prompt_troubleshooting_advisor(summary)
                
            self.c.refresh_mods(scan_disk=False)
            self.c.refresh_mods(scan_disk=True, target_mod=mod_data["name"])
            
        self.c.view.run_async_task(decompile_task)

    def execute_pipeline(self, mod_data, action):
        self.is_building = True
        self.c.view.set_log_autoscroll(True)
        self.active_mod_name = mod_data["name"]
        self.c.refresh_mods(scan_disk=False)
        self.c.view.write_log(f"\n>>> EXECUTING [{action.upper()}]: {mod_data['name']}", "stage")
        
        self.active_token = {"process": None}
        
        async def run_task():
            def log_callback(text, category, flush=True):
                if text is not None:
                    self.c.view.write_log(text, category, flush=False)
                if flush:
                    self.c.view.force_update()
                    
            def progress_callback(line, flush=True):
                self.c.view.update_card_progress(self.active_mod_name, line, flush)
                        
            def complete_callback(success, returncode, summary):
                status = "pure_success"
                if summary:
                    status = summary.get("status", "failed")

                if status == "pure_success" and success:
                    self.c.view.write_log("SUCCESS: Operation completed cleanly.", "success")
                elif status == "success_with_warnings":
                    self.c.view.write_log(f"WARNING: Operation completed with {summary['total_warnings']} warnings.", "warning")
                elif status == "success_with_errors":
                    self.c.view.write_log(f"ERROR: Operation completed but found {summary['total_errors']} compilation errors.", "error")
                else:
                    self.c.view.write_log(f"FAILED: Process terminated with exit code {returncode}", "error")
                
                self.is_building = False
                self.c.view.set_log_autoscroll(False)
                self.active_token = {"process": None}
                
                card_success = success and (status != "success_with_errors")
                self.c.view.reset_card_state(self.active_mod_name, card_success)
                self.active_mod_name = ""
                
                if summary:
                    self.c.view.prompt_troubleshooting_advisor(summary)
                    
                self.c.refresh_mods(scan_disk=False)
                self.c.refresh_mods(scan_disk=True, target_mod=mod_data["name"])

            f_path = mod_data.get("fmodel_path") or mod_data.get("fmodel_altermatic_path") or mod_data.get("ue_path")
            category = self.c.get_category_from_path(f_path)

            script_args = [mod_data["name"], category, action]
            await run_pipeline_async(script_args, log_callback, progress_callback, complete_callback, self.active_token)

        self.c.view.run_async_task(run_task)

    def execute_browse_unreal(self, mod_data):
        self.is_building = True
        self.active_mod_name = mod_data["name"]
        self.c.refresh_mods(scan_disk=False)
        self.c.view.write_log(f"\n>>> FOCUSING UNREAL CONTENT BROWSER: {mod_data['name']}", "stage")
        
        async def browse_task():
            f_path = mod_data.get("fmodel_path") or mod_data.get("fmodel_altermatic_path") or mod_data.get("ue_path")
            category = self.c.get_category_from_path(f_path)
            category_sanitized = category.replace(" ", "_")
            ue_virtual_path = f"/Game/Pal/Model/Character/{category_sanitized}/{mod_data['name']}"
            python_cmd = f'import unreal; unreal.EditorUtilityLibrary.sync_browser_to_folders(["{ue_virtual_path}"])'
            
            from utils.builder.unreal_helper import run_remote_command, focus_unreal_window
            target_project_name = os.path.splitext(os.path.basename(self.c.settings["uproject"]))[0]
            
            success, msg = await asyncio.to_thread(
                run_remote_command,
                self.c.settings["ue_root"],
                target_project_name,
                python_cmd
            )
            
            if success:
                self.c.view.write_log(f"SUCCESS: Focused Content Browser to: {ue_virtual_path}", "success")
                focus_unreal_window(target_project_name)
            else:
                self.c.view.write_log(f"FAILED to focus Unreal: {msg}", "error")
                
            self.is_building = False
            self.active_mod_name = ""
            self.c.refresh_mods(scan_disk=False)
            
        self.c.view.run_async_task(browse_task)