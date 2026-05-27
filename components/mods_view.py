import flet as ft
import os
import sys
import asyncio
import subprocess
import time
from utils import get_mod_info
from components.mod_item import ModItem
from utils.plugins.decompiler import run_decompile_pipeline

class ModsView:
    def __init__(self, page: ft.Page, settings: dict):
        self.main_page = page
        self.settings = settings
        self.is_building = False
        self.active_mod_name = ""
        self.active_process = None
        
        # State Engine
        self.raw_mods: list[dict] = []
        self.cached_items: list[ModItem] = [] 
        self.search_query = ""
        self.show_mapped = False
        self.selected_badges: set[str] = set()
        self.selected_statuses: set[str] = set()

        # UI Lists
        self.mods_list = ft.ListView(expand=True, spacing=10)
        self.log_view = ft.ListView(expand=True, spacing=2, auto_scroll=True)

        self.search_bar = ft.TextField(
            label="Search by internal or actual name...",
            expand=True,
            on_change=self.on_search_change,
            prefix_icon=ft.Icons.SEARCH
        )
        
        self.badge_chips = ft.Row([
            ft.Text("Tags:", weight=ft.FontWeight.BOLD),
            ft.Chip(label=ft.Text("RAW"), on_select=lambda e: self.on_badge_select("RAW", e)),
            ft.Chip(label=ft.Text("SOURCE"), on_select=lambda e: self.on_badge_select("SOURCE", e)),
            ft.Chip(label=ft.Text("UE ASSETS"), on_select=lambda e: self.on_badge_select("UE ASSETS", e)),
            ft.Chip(label=ft.Text("MODIFIED"), on_select=lambda e: self.on_badge_select("MODIFIED", e)),
        ], spacing=10)

        self.status_chips = ft.Row([
            ft.Text("Status:", weight=ft.FontWeight.BOLD),
            ft.Chip(label=ft.Text("Packed"), on_select=lambda e: self.on_status_select("Packed", e)),
            ft.Chip(label=ft.Text("Unpacked"), on_select=lambda e: self.on_status_select("Unpacked", e)),
            ft.Chip(label=ft.Text("Outdated"), on_select=lambda e: self.on_status_select("Outdated", e)),
        ], spacing=10)

        row_controls: list[ft.Control] = [
            self.search_bar,
            ft.IconButton(ft.Icons.REFRESH, on_click=lambda e: self.refresh_mods(scan_disk=True))
        ]

        self.console_container = ft.Container(
            content=self.log_view, 
            expand=True, 
            bgcolor=ft.Colors.BLACK, 
            border_radius=10, 
            padding=15, 
            border=ft.Border.all(1, ft.Colors.WHITE10)
        )

        self.view = ft.Column(
            expand=True,
            controls=[
                ft.Row(controls=row_controls),
                self.badge_chips,
                self.status_chips,
                ft.Container(self.mods_list, height=300, border=ft.Border.all(1, ft.Colors.WHITE10), border_radius=10, padding=10),
                ft.Row([
                    ft.Text("Build Console", size=16, weight=ft.FontWeight.BOLD),
                    ft.IconButton(
                        icon=ft.Icons.COPY_ALL, 
                        tooltip="Copy console content to clipboard", 
                        on_click=self.copy_console_to_clipboard
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.console_container
            ]
        )

    async def copy_console_to_clipboard(self, e):
        """Asynchronously gathers all printed lines in log_view and copies them to the system clipboard."""
        log_lines = []
        for ctrl in self.log_view.controls:
            if isinstance(ctrl, ft.Text) and ctrl.value:
                log_lines.append(ctrl.value)
        
        full_log = "\n".join(log_lines)
        
        if full_log.strip():
            await ft.Clipboard().set(full_log)
            self.main_page.overlay.append(ft.SnackBar(ft.Text("Console content copied to clipboard!"), open=True))
        else:
            self.main_page.overlay.append(ft.SnackBar(ft.Text("Console is currently empty."), open=True))
            
        self.main_page.update()

    def on_search_change(self, e):
        self.search_query = str(self.search_bar.value)
        self.apply_filters()

    def on_badge_select(self, badge: str, e):
        if e.control.selected:
            self.selected_badges.add(badge)
        else:
            self.selected_badges.discard(badge)
        self.apply_filters()

    def on_status_select(self, status: str, e):
        if e.control.selected:
            self.selected_statuses.add(status)
        else:
            self.selected_statuses.discard(status)
        self.apply_filters()

    def refresh_mods(self, scan_disk: bool = True):
        self.show_mapped = bool(self.settings.get("show_mapped", False))

        if scan_disk:
            self.raw_mods = get_mod_info(self.settings)
            self.cached_items.clear()
            for mod_data in self.raw_mods:
                self.cached_items.append(
                    ModItem(
                        mod_data, 
                        on_action_click=self.handle_action, 
                        on_cancel_click=self.handle_cancel,
                        is_building=self.is_building,
                        show_mapped=self.show_mapped
                    )
                )
        else:
            for item in self.cached_items:
                item.set_show_mapped(self.show_mapped)
                is_active = (getattr(item, "mod_data")["name"] == self.active_mod_name)
                item.set_state(global_building=self.is_building, is_active_target=is_active)

        self.apply_filters()

    def force_update(self):
        """Forces the update of the main view component."""
        try:
            self.view.update()
        except Exception:
            pass

    def apply_filters(self):
        self.mods_list.controls.clear()
        
        fmodel_dir = str(self.settings.get("fmodel_output", ""))
        if not fmodel_dir or not os.path.exists(fmodel_dir):
            self.mods_list.controls.append(ft.Text("Set a valid FModel Output Folder in Settings.", color=ft.Colors.RED_400))
            self.force_update()
            return

        filtered_items = []
        for item in self.cached_items:
            mod = getattr(item, "mod_data", None)
            if not mod: continue
            
            search_lower = self.search_query.lower()
            name_match = (search_lower in mod["name"].lower()) or (search_lower in mod["localized_name"].lower())
            if not name_match:
                continue

            if self.selected_badges:
                mod_badges = {b[0] for b in mod["badges"]}
                if not self.selected_badges.issubset(mod_badges):
                    continue

            if self.selected_statuses:
                if mod["pak_status"] not in self.selected_statuses:
                    continue

            filtered_items.append(item)

        filtered_items.sort(key=lambda x: str(getattr(x, "mod_data")["localized_name"] if self.show_mapped else getattr(x, "mod_data")["name"]).lower())

        if not filtered_items:
             self.mods_list.controls.append(ft.Text("No mods match active filters.", color=ft.Colors.YELLOW_400))
        else:
            self.mods_list.controls.extend([item.view for item in filtered_items])
            
        self.force_update()

    def handle_action(self, mod_data, action):
        if self.is_building: return

        # WARNING: MANUALLY MODIFIED FILES DIALOG
        if action in ["push", "full"] and mod_data.get("ue_modified"):
            def confirm(e):
                self.main_page.pop_dialog()
                self.execute_pipeline(mod_data, action)
            
            def cancel(e):
                self.main_page.pop_dialog()

            mod_files = mod_data.get("ue_modified_files", [])
            files_str = "\n".join([f" • {f}" for f in mod_files])

            dlg = ft.AlertDialog(
                open=True,
                modal=True,
                title=ft.Text("Warning: Overwrite Unreal Assets?"),
                content=ft.Column([
                    ft.Text(f"You have manually modified files inside Unreal Engine since your last Push for {mod_data['name']}.\nContinuing will OVERWRITE and delete those changes.\n\nModified files:"),
                    ft.Text(files_str, color=ft.Colors.RED_400, size=12, selectable=True),
                    ft.Text("Are you sure you want to proceed?", weight=ft.FontWeight.BOLD)
                ], tight=True),
                actions=[
                    ft.TextButton("Cancel", on_click=cancel),
                    ft.TextButton("Overwrite & Proceed", on_click=confirm, style=ft.ButtonStyle(color=ft.Colors.RED)),
                ]
            )
            self.main_page.show_dialog(dlg)

        # NEW: GENERATE SOURCES MODAL CHOICE
        elif action == "decompile":
            def on_missing_only(e):
                self.main_page.pop_dialog()
                self.execute_decompile_pipeline(mod_data, overwrite=False)
                
            def on_overwrite_all(e):
                self.main_page.pop_dialog()
                self.execute_decompile_pipeline(mod_data, overwrite=True)
                
            def on_cancel(e):
                self.main_page.pop_dialog()

            dlg = ft.AlertDialog(
                open=True,
                modal=True,
                title=ft.Text("Generate Source Assets"),
                content=ft.Column([
                    ft.Text("This process will reverse-engineer your ModKit's compiled .uassets back into editable Blender and PNG source files.\n\nChoose an extraction mode:"),
                    ft.Text(" • Generate Missing Only (Safest — leaves existing files alone)", size=12, color=ft.Colors.WHITE70),
                    ft.Text(" • Overwrite & Regenerate (Wipes local source folder)", size=12, color=ft.Colors.WHITE70),
                ], tight=True),
                actions=[
                    ft.TextButton("Cancel", on_click=on_cancel),
                    ft.TextButton("Missing Only", on_click=on_missing_only),
                    ft.TextButton("Overwrite All", on_click=on_overwrite_all, style=ft.ButtonStyle(color=ft.Colors.RED)),
                ]
            )
            self.main_page.show_dialog(dlg)
        else:
            self.execute_pipeline(mod_data, action)

    def handle_cancel(self):
        """Forces the termination of the active build process and its children."""
        if self.active_process:
            self.write_log("\n[!] Force terminating the build process...", ft.Colors.RED_400)
            try:
                if os.name == 'nt':
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.active_process.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    self.active_process.kill()
            except Exception as e:
                self.write_log(f"Error terminating process: {e}", ft.Colors.RED_400)

    def write_log(self, text, color=ft.Colors.WHITE70, flush: bool = True):
        # 1. Append the log entry
        self.log_view.controls.append(ft.Text(text, color=color, size=12, font_family="Consolas"))
        
        # 2. Slice the controls list to retain only the last 100 entries (prevents UI lag)
        MAX_LINES = 100
        if len(self.log_view.controls) > MAX_LINES:
            self.log_view.controls = self.log_view.controls[-MAX_LINES:]
            
        if flush:
            self.force_update()

    def execute_decompile_pipeline(self, mod_data, overwrite: bool = False):
        """Asynchronously triggers the decompiler routine."""
        self.is_building = True
        self.active_mod_name = mod_data["name"]
        self.refresh_mods(scan_disk=False)
        self.write_log(f"\n>>> EXECUTING DECOMPILER: {mod_data['name']}", ft.Colors.CYAN_400)
        
        async def decompile_task():
            # Source & target directories
            fmodel_dir = mod_data["fmodel_path"]
            # Target path under /Game/
            ue_virtual_path = f"/Game/Pal/Model/Character/{mod_data['category']}/{mod_data['name']}"
            
            # Run the decompile pipeline asynchronously
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
            
            if success:
                self.write_log(f"SUCCESS: {msg}", ft.Colors.GREEN_400)
            else:
                self.write_log(f"FAILED: {msg}", ft.Colors.RED_400)
                
            self.is_building = False
            self.active_mod_name = ""
            self.refresh_mods(scan_disk=True)
            
        self.main_page.run_task(decompile_task)

    def execute_pipeline(self, mod_data, action):
        self.is_building = True
        self.active_mod_name = mod_data["name"]
        self.refresh_mods(scan_disk=False)
        self.write_log(f"\n>>> EXECUTING [{action.upper()}]: {mod_data['name']}", ft.Colors.CYAN_400)
        
        async def run_task():
            script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "build_mod.py")
            
            # Start process asynchronously using asyncio's subprocess implementation
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-u", script_path, mod_data["name"], mod_data["category"], action,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            self.active_process = process

            last_update_time = time.time()
            update_pending = False

            if process.stdout:
                while True:
                    line_bytes = await process.stdout.readline()
                    if not line_bytes:
                        break
                    
                    line = line_bytes.decode('utf-8', errors='replace')
                    
                    # Append log line silently (truncation triggers automatically inside write_log)
                    self.write_log(line.strip(), flush=False)
                    
                    # Update progress bar properties silently
                    for item in self.cached_items:
                        if getattr(item, "mod_data")["name"] == self.active_mod_name:
                            item.update_progress(line, flush=False)
                            break
                    
                    update_pending = True
                    
                    # Yield execution briefly back to Flet's asyncio loop to flush socket queues
                    await asyncio.sleep(0.001)
                    
                    # Throttle updates to at most once every 100ms
                    current_time = time.time()
                    if current_time - last_update_time >= 0.10:
                        self.force_update()
                        last_update_time = current_time
                        update_pending = False

            # Wait for the async process exit
            returncode = await process.wait()
            success = (returncode == 0)
            
            if success:
                self.write_log("SUCCESS: Operation completed.", ft.Colors.GREEN_400, flush=False)
            else:
                self.write_log(f"Process terminated with exit code {returncode}", ft.Colors.RED_400, flush=False)
            
            self.is_building = False
            self.active_process = None
            
            for item in self.cached_items:
                if getattr(item, "mod_data")["name"] == self.active_mod_name:
                    item.set_state(global_building=False, is_active_target=False, success=success)
                    break
                    
            self.active_mod_name = ""
            self.refresh_mods(scan_disk=True)

        # Execute as a native asyncio task managed by Flet's underlying event loop
        self.main_page.run_task(run_task)