# views/mods_view.py
import flet as ft  # type: ignore
import os

from ui_client.dispatcher import PalBakerCLI
from components.mods.mod_card import ModItem
from components.mods.dialogs import (
    create_overwrite_warning_dialog,
    create_decompile_options_dialog,
    create_troubleshooting_advisor_dialog,
    create_build_database_dialog,
    create_unreal_closed_dialog,            
    create_remote_exec_disabled_dialog      
)
from components.altermatic.dialogs import AltermaticEditDialog, AltermaticAddDialog, AltermaticDeleteDialog

class ModsView:
    def __init__(self, page: ft.Page, settings: dict):
        self.main_page = page
        self.settings = settings
        
        self.cli = PalBakerCLI()

        # Localized UI states & filters to replace ModsController entirely!
        self.raw_mods = []
        self.show_mapped = bool(settings.get("show_mapped", False))
        self.search_query = ""
        self.show_unextracted = False
        self.selected_badges = set()
        self.selected_statuses = set()

        self.traits_db = {}
        self.run_async_task(self.load_traits_db)

        self.mods_list = ft.ListView(expand=True, spacing=10)
        self.log_view = ft.ListView(expand=True, spacing=2, auto_scroll=True)
        
        self.cached_components = {}
        self.expanded_states = {}  

        self.icon_picker = ft.FilePicker()
        self.main_page.services.append(self.icon_picker)
        
        self.audio_picker = ft.FilePicker()
        self.main_page.services.append(self.audio_picker)

        self.search_bar = ft.TextField(
            label="Search by internal or actual name...",
            expand=True,
            on_change=lambda e: self.update_search(self.search_bar.value),
            prefix_icon=ft.Icons.SEARCH
        )
        
        self.show_unextracted_switch = ft.Switch(
            label="Show Unextracted Pals",
            value=False,
            on_change=lambda e: self.toggle_unextracted(self.show_unextracted_switch.value)
        )
        
        self.badge_chips = ft.Row([
            ft.Text("Tags:", weight=ft.FontWeight.BOLD),
            ft.Chip(label=ft.Text("RAW"), on_select=lambda e: self.update_badge_filter("RAW", e.control.selected)),
            ft.Chip(label=ft.Text("SOURCE"), on_select=lambda e: self.update_badge_filter("SOURCE", e.control.selected)),
            ft.Chip(label=ft.Text("UE ASSETS"), on_select=lambda e: self.update_badge_filter("UE ASSETS", e.control.selected)),
            ft.Chip(label=ft.Text("MODIFIED"), on_select=lambda e: self.update_badge_filter("MODIFIED", e.control.selected)),
            ft.Chip(label=ft.Text("ALTERMATIC"), on_select=lambda e: self.update_badge_filter("ALTERMATIC", e.control.selected)),
        ], spacing=10)

        self.status_chips = ft.Row([
            ft.Text("Status:", weight=ft.FontWeight.BOLD),
            ft.Chip(label=ft.Text("Packed"), on_select=lambda e: self.update_status_filter("Packed", e.control.selected)),
            ft.Chip(label=ft.Text("Packed with Errors"), on_select=lambda e: self.update_status_filter("Packed with Errors", e.control.selected)),
            ft.Chip(label=ft.Text("Unpacked"), on_select=lambda e: self.update_status_filter("Unpacked", e.control.selected)),
            ft.Chip(label=ft.Text("Outdated"), on_select=lambda e: self.update_status_filter("Outdated", e.control.selected)),
        ], spacing=10)

        self.refresh_button = ft.IconButton(
            icon=ft.Icons.REFRESH, 
            tooltip="Rescan disk for mods",
            on_click=lambda e: self.refresh_mods(scan_disk=True)
        )
        self.refresh_spinner = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False)

        self.console_height = int(settings.get("console_height", 200))
        
        self.mods_list_container = ft.Container(
            self.mods_list, 
            expand=True,
            border=ft.Border.all(1, ft.Colors.WHITE10), 
            border_radius=10, 
            padding=10
        )
        
        self.console_container = ft.Container(
            content=self.log_view, 
            height=self.console_height,
            bgcolor=ft.Colors.BLACK, 
            border_radius=10, 
            padding=15, 
            border=ft.Border.all(1, ft.Colors.WHITE10)
        )

        self.divider_handle = ft.GestureDetector(
            content=ft.Container(height=10, content=ft.Icon(ft.Icons.DRAG_HANDLE, size=16), bgcolor=ft.Colors.WHITE10, border_radius=5),
            on_pan_update=self.on_divider_drag
        )

        self.view = ft.Column(
            expand=True,
            controls=[
                ft.Row([self.search_bar, self.show_unextracted_switch, self.refresh_spinner, self.refresh_button]),
                self.badge_chips,
                self.status_chips,
                self.mods_list_container,
                self.divider_handle,
                ft.Row([
                    ft.Text("Build Console", size=16, weight=ft.FontWeight.BOLD),
                    ft.IconButton(icon=ft.Icons.COPY_ALL, tooltip="Copy console", on_click=self.copy_console_to_clipboard)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.console_container
            ]
        )

        self.altermatic_edit_dialog = AltermaticEditDialog(
            self.main_page, 
            self.settings, 
            self.traits_db, 
            on_save_callback=lambda idx, data: self.run_async_task(self._async_save_altermatic_variant, idx, data),
            on_refresh_callback=self.run_refresh_pipeline_callback,
            on_delete_callback=lambda name, idx: self.run_async_task(self._async_delete_altermatic_variant, name, idx)
        )
        self.altermatic_add_dialog = AltermaticAddDialog(self.main_page)
        self.altermatic_delete_dialog = AltermaticDeleteDialog(self.main_page)

    def on_divider_drag(self, e: ft.DragUpdateEvent):
        delta = 0.0
        if hasattr(e, "local_delta") and e.local_delta is not None:
            delta = e.local_delta.y
        elif hasattr(e, "delta_y"):
            delta = e.delta_y  # type: ignore

        new_console_height = max(50, (self.console_container.height or 0) - delta)  # type: ignore
        self.console_container.height = new_console_height
        self.console_height = new_console_height
        
        self.settings["console_height"] = new_console_height
        self.run_async_task(self.cli.set_config, "console_height", str(new_console_height))
        
        self.force_update()

    def run_in_thread(self, func):
        self.main_page.run_thread(func)

    def run_async_task(self, func, *args):
        self.main_page.run_task(func, *args)

    def clear_ui_cache(self):
        for name, item in self.cached_components.items():
            if item.details_visible:
                self.expanded_states[name] = True
            else:
                self.expanded_states.pop(name, None)
        self.cached_components.clear()

    def evict_cache(self, mod_name: str):
        if mod_name in self.cached_components:
            item = self.cached_components.pop(mod_name)
            if item.details_visible:
                self.expanded_states[mod_name] = True
            else:
                self.expanded_states.pop(mod_name, None)

    def render_mods(self, mods_data: list[dict], global_building: bool, active_mod_name: str):
        self.mods_list.controls.clear()
        
        for mod_data in mods_data:
            name = mod_data["name"]
            if name in self.cached_components:
                item = self.cached_components[name]
                item.mod_data = mod_data
                item.set_show_mapped(self.show_mapped)  # type: ignore
                item.set_state(global_building, is_active_target=(name == active_mod_name))
            else:
                item = ModItem(
                    mod_data=mod_data,
                    on_action_click=lambda md, action: self.run_async_task(self._async_handle_action, md, action),
                    on_cancel_click=self.handle_cancel,
                    on_pick_icon=self.trigger_icon_picker,
                    on_pick_audio=self.trigger_audio_picker,
                    on_play_audio=lambda mod_data, cry: self.run_async_task(self._async_play_audio, mod_data, cry),
                    on_clear_audio=lambda mod_data, cry: self.run_async_task(self._async_clear_audio, mod_data, cry),
                    on_toggle_altermatic=lambda mod_data, status: self.run_async_task(self._async_toggle_altermatic, mod_data, status),
                    on_add_variant=lambda mod_data: self.run_async_task(self._async_add_variant, mod_data),
                    on_edit_variant=lambda mod_data, idx: self.run_async_task(self._async_edit_variant, mod_data, idx),
                    on_delete_variant=lambda mod_data, idx: self.run_async_task(self._async_delete_variant, mod_data, idx),
                    is_building=global_building,
                    show_mapped=self.show_mapped  # type: ignore
                )
                
                if self.expanded_states.get(name, False):
                    item.details_visible = True
                    item.details_container.visible = True
                    item.chevron.icon = ft.Icons.KEYBOARD_ARROW_UP

                item.set_state(global_building, is_active_target=(name == active_mod_name))
                self.cached_components[name] = item
                
            self.mods_list.controls.append(item.view)
            
        try:
            self.mods_list.update()
        except Exception:
            pass
        self.force_update()

    async def trigger_icon_picker(self, mod_data):
        result = await self.icon_picker.pick_files(allow_multiple=False, allowed_extensions=["png", "jpg", "jpeg"])
        if result and len(result) > 0:
            path = result[0].path
            if isinstance(path, str):
                try:
                    response = await self.cli.set_icon(mod_data["name"], path)
                    if response.get("status") == "success":
                        self.write_log(f"Icon set for {mod_data['name']}", "success")
                    else:
                        self.write_log(f"Error setting icon: {response.get('message', 'Unknown error')}", "error")
                except Exception as e:
                    self.write_log(f"Error setting icon: {str(e)}", "error")

    async def trigger_audio_picker(self, mod_data, cry_name):
        result = await self.audio_picker.pick_files(allow_multiple=False, allowed_extensions=["wav", "mp3", "ogg"])
        if result and len(result) > 0:
            path = result[0].path
            if isinstance(path, str):
                try:
                    response = await self.cli._execute(["audio", "set", mod_data["name"], cry_name, path])
                    if response.get("status") == "success":
                        self.write_log(f"Audio set for {mod_data['name']} ({cry_name})", "success")
                    else:
                        self.write_log(f"Error setting audio: {response.get('message', 'Unknown error')}", "error")
                except Exception as e:
                    self.write_log(f"Error setting audio: {str(e)}", "error")

    async def _async_handle_action(self, mod_data, action):
        """Dispatches and streams operational pipelines safely through the CLI Dispatcher."""
        if action in ["push", "full", "decompile", "browse_unreal"]:
            env_res = await self.cli.env_status()
            if env_res.get("status") == "success":
                remote_exec_enabled = env_res.get("remote_exec_enabled", False)
                unreal_running = env_res.get("unreal_running", False)
                
                if not remote_exec_enabled:
                    def on_fix_clicked():
                        async def fix_task():
                            await self.cli.env_enable_remote_exec()
                            await self.cli.env_launch_unreal()
                            self.show_snackbar("Python Remote Execution enabled! Launching Unreal Editor... Please wait for it to fully load, then retry.", ft.Colors.GREEN_400)
                        self.run_async_task(fix_task)
                    
                    self.prompt_remote_exec_disabled_warning(on_fix_clicked)
                    return
                
                if not unreal_running:
                    def on_launch_clicked():
                        async def launch_task():
                            await self.cli.env_launch_unreal()
                            self.show_snackbar("Launching Unreal Editor... Please wait for it to fully load, then retry.", ft.Colors.CYAN_400)
                        self.run_async_task(launch_task)
                    
                    self.prompt_unreal_closed_warning(on_launch_clicked)
                    return

        if action == "extract_pal":
            try:
                self.write_log(f"\n>>> EXECUTING [EXTRACT_PAL]: {mod_data['name']}", "stage")
                if mod_data["name"] in self.cached_components:
                    card = self.cached_components[mod_data["name"]]
                    card.set_state(global_building=True, is_active_target=True)
                    card.progress_bar.value = None # Indeterminate spinner!
                    card.status_text.value = "Extracting game files..."
                    self.force_update()
                
                response = await self.cli._execute(["mod", "extract", mod_data["name"]])
                if response.get("status") == "success":
                    self.write_log(f"Extraction completed successfully: {response.get('message')}", "success")
                    if mod_data["name"] in self.cached_components:
                        self.cached_components[mod_data["name"]].set_state(global_building=False, is_active_target=False, success=True)
                    self.refresh_mods(scan_disk=True)
                else:
                    self.write_log(f"Extraction failed: {response.get('message')}", "error")
                    if mod_data["name"] in self.cached_components:
                        self.cached_components[mod_data["name"]].set_state(global_building=False, is_active_target=False, success=False)
            except Exception as e:
                self.write_log(f"Extraction error: {str(e)}", "error")
                if mod_data["name"] in self.cached_components:
                    self.cached_components[mod_data["name"]].set_state(global_building=False, is_active_target=False, success=False)
        elif action in ["push", "full"] and mod_data.get("ue_modified"):
            self.prompt_overwrite_warning(mod_data, lambda: self.run_async_task(self._async_execute_pipeline, mod_data, action))
        elif action == "decompile":
            self.prompt_decompile_options(mod_data)
        elif action == "browse_unreal":
            try:
                response = await self.cli._execute(["mod", "browse-ue", mod_data["name"]])
                if response.get("status") != "success":
                    self.write_log(f"Error focusing Unreal content browser: {response.get('message', 'Unknown error')}", "error")
            except Exception as e:
                self.write_log(f"Error: {str(e)}", "error")
        else:
            await self._async_execute_pipeline(mod_data, action)

    async def _async_execute_pipeline(self, mod_data, action):
        """Spawns out-of-process builds and live-streams logs straight through dispatcher.run_pipeline_stream."""
        self.set_log_autoscroll(True)
        
        # Determine sequential steps for multi-stage pipelines to completely decouple and modularize processes
        if action == "cook":
            steps = ["cook", "pack"]
        elif action == "full":
            steps = ["push", "cook", "pack"]
        else:
            steps = [action]

        import asyncio
        success = True
        
        for step in steps:
            # Put the card in an active building state specifically for the current sequential step
            if mod_data["name"] in self.cached_components:
                self.cached_components[mod_data["name"]].set_state(global_building=True, is_active_target=True)
                self.force_update()
            
            def log_callback(msg, level="standard"):
                self.write_log(msg, level, flush=False)
                
            def progress_callback(percent, msg):
                self.update_card_progress(mod_data["name"], f"[{percent}%] {msg}", flush=True)
                
            # Create a future to await completion of this individual sub-process
            loop = asyncio.get_running_loop()
            step_fut = loop.create_future()
            
            def done_callback(step_success):
                try:
                    step_fut.set_result(step_success)
                except Exception:
                    pass
            
            await self.cli.run_pipeline_stream(mod_data["name"], step, log_callback, progress_callback, done_callback)
            
            step_success = await step_fut
            if not step_success:
                success = False
                break
                
        self.set_log_autoscroll(False)
        self.reset_card_state(mod_data["name"], success)
        if success:
            self.write_log("SUCCESS: Operation completed cleanly.", "success")
        else:
            self.write_log("FAILED: Pipeline execution encountered issues.", "error")
        self.refresh_mods(scan_disk=True)

    def update_card_progress(self, mod_name: str, line: str, flush: bool):
        if mod_name in self.cached_components:
            self.cached_components[mod_name].update_progress(line, flush)

    def reset_card_state(self, mod_name: str, success: bool):
        if mod_name in self.cached_components:
            self.cached_components[mod_name].set_state(global_building=False, is_active_target=False, success=success)

    def prompt_overwrite_warning(self, mod_data, confirm_callback):
        dlg = create_overwrite_warning_dialog(mod_data.get("ue_modified_files", []), lambda e: (self.pop_dialog(), confirm_callback()), lambda e: self.pop_dialog())
        self.show_dialog(dlg)

    def prompt_decompile_options(self, mod_data):
        dlg = create_decompile_options_dialog(
            lambda e: (self.pop_dialog(), self.run_async_task(self._async_decompile, mod_data, False)),
            lambda e: (self.pop_dialog(), self.run_async_task(self._async_decompile, mod_data, True)),
            lambda e: self.pop_dialog()
        )
        self.show_dialog(dlg)

    async def _async_decompile(self, mod_data, overwrite: bool):
        """Execute decompile pipeline via CLI."""
        try:
            self.write_log(f"\n>>> EXECUTING [DECOMPILE]: {mod_data['name']}", "stage")
            if mod_data["name"] in self.cached_components:
                card = self.cached_components[mod_data["name"]]
                card.set_state(global_building=True, is_active_target=True)
                card.progress_bar.value = None # Indeterminate spinner!
                card.status_text.value = "Decompiling project assets..."
                self.force_update()

            args = ["mod", "decompile", mod_data["name"]]
            if overwrite:
                args.append("--overwrite")
            response = await self.cli._execute(args)
            if response.get("status") == "success":
                self.write_log(f"Decompile completed for {mod_data['name']}", "success")
                if response.get("summary"):
                    self.write_log(f"Summary: {response.get('summary')}", "standard")
                if mod_data["name"] in self.cached_components:
                    self.cached_components[mod_data["name"]].set_state(global_building=False, is_active_target=False, success=True)
            else:
                self.write_log(f"Decompile failed: {response.get('message', 'Unknown error')}", "error")
                if mod_data["name"] in self.cached_components:
                    self.cached_components[mod_data["name"]].set_state(global_building=False, is_active_target=False, success=False)
        except Exception as e:
            self.write_log(f"Error during decompile: {str(e)}", "error")
            if mod_data["name"] in self.cached_components:
                self.cached_components[mod_data["name"]].set_state(global_building=False, is_active_target=False, success=False)

    def prompt_build_database(self):
        dlg = create_build_database_dialog(
            lambda e: (self.pop_dialog(), self.run_async_task(self._async_build_database)),
            lambda e: self.pop_dialog()
        )
        self.show_dialog(dlg)

    async def _async_build_database(self):
        """Build Pal database via CLI."""
        try:
            response = await self.cli.build_database()
            if response.get("status") == "success":
                self.write_log("Database built successfully!", "success")
            else:
                self.write_log(f"Database build failed: {response.get('message', 'Unknown error')}", "error")
        except Exception as e:
            self.write_log(f"Error building database: {str(e)}", "error")

    async def _async_play_audio(self, mod_data, cry_name):
        """Play audio via CLI."""
        try:
            response = await self.cli._execute(["audio", "play", mod_data["name"], cry_name])
            if response.get("status") != "success":
                self.write_log(f"Error playing audio: {response.get('message', 'Unknown error')}", "error")
        except Exception as e:
            self.write_log(f"Error playing audio: {str(e)}", "error")

    async def _async_clear_audio(self, mod_data, cry_name):
        """Clear audio via CLI."""
        try:
            response = await self.cli._execute(["audio", "clear", mod_data["name"], cry_name])
            if response.get("status") == "success":
                self.write_log(f"Audio cleared for {cry_name}", "success")
            else:
                self.write_log(f"Error clearing audio: {response.get('message', 'Unknown error')}", "error")
        except Exception as e:
            self.write_log(f"Error clearing audio: {str(e)}", "error")

    async def _async_toggle_altermatic(self, mod_data, status: str):
        """Toggle Altermatic via CLI (status: 'on' or 'off')."""
        try:
            status_str = "on" if (status is True or status == "on" or status == "True") else "off"
            response = await self.cli.altermatic_toggle(mod_data["name"], status_str)
            if response.get("status") == "success":
                self.write_log(f"Altermatic toggled to {status_str} for {mod_data['name']}", "success")
            else:
                self.write_log(f"Error toggling Altermatic: {response.get('message', 'Unknown error')}", "error")
        except Exception as e:
            self.write_log(f"Error toggling Altermatic: {str(e)}", "error")

    async def _async_add_variant(self, mod_data):
        """Add Altermatic variant via CLI."""
        current_char_id = mod_data["name"]
        
        meta_res = await self.cli.altermatic_metadata(current_char_id)
        if meta_res.get("status") != "success":
            self.write_log(f"ERROR: Could not fetch Altermatic metadata: {meta_res.get('message', 'Unknown error')}", "error")
            return
            
        has_base_blend = meta_res.get("has_base_blend", False)
        if not has_base_blend:
            self.write_log(f"ERROR: Cannot add variant. Base model {current_char_id}.blend is missing.", "error")
            self.show_snackbar("Generate the base .blend file first.", "#EF5350")
            return
            
        blend_files = meta_res.get("blend_files", [])

        async def confirm_clone(label, custom, src):
            res = await self.cli.altermatic_add(mod_data["name"], label, custom, src)
            if res.get("status") == "success":
                self.write_log(f"Added Altermatic variant: {label}", "success")
                self.refresh_mods(scan_disk=True)
            else:
                self.write_log(f"Failed to add variant: {res.get('message', 'Unknown error')}", "error")

        self.altermatic_add_dialog.show(current_char_id, blend_files, lambda label, custom, src: self.run_async_task(confirm_clone, label, custom, src))

    async def _async_edit_variant(self, mod_data, index: int):
        """Edit Altermatic variant via CLI."""
        variants = mod_data.get("altermatic_variants", [])
        if index < 0 or index >= len(variants): return
        
        v = variants[index]
        current_char_id = mod_data["name"]

        meta_res = await self.cli.altermatic_metadata(current_char_id)
        if meta_res.get("status") != "success":
            self.write_log(f"ERROR: Could not fetch Altermatic metadata: {meta_res.get('message', 'Unknown error')}", "error")
            return
            
        blend_files = meta_res.get("blend_files", [])
        available_mats = meta_res.get("available_materials", [])
        category = meta_res.get("category", "Monster")

        self.altermatic_edit_dialog.show(current_char_id, index, v, blend_files, available_mats, category)

    async def _async_save_altermatic_variant(self, index: int, variant_data: dict):
        res = await self.cli.altermatic_save(index, variant_data)
        if res.get("status") == "success":
            self.write_log("Successfully saved Altermatic variant structure.", "success")
            self.refresh_mods(scan_disk=True)
        else:
            self.write_log(f"Failed to save Altermatic variant: {res.get('message', 'Unknown error')}", "error")

    async def _async_delete_altermatic_variant(self, mod_name: str, index: int):
        res = await self.cli.altermatic_delete(mod_name, index)
        if res.get("status") == "success":
            self.write_log(f"Successfully deleted Altermatic variant at index {index}", "success")
            self.refresh_mods(scan_disk=True)
        else:
            self.write_log(f"Failed to delete Altermatic variant: {res.get('message', 'Unknown error')}", "error")

    async def _async_delete_variant(self, mod_data, index: int):
        """Delete Altermatic variant Confirmation Prompt."""
        variants = mod_data.get("altermatic_variants", [])
        if index < 0 or index >= len(variants): return
        
        v = variants[index]
        current_char_id = mod_data["name"]

        is_material_only_reskin = (v.get("SkeletonSource", "base") == "base")
        if is_material_only_reskin:
            confirm_message = f"Are you sure you want to permanently delete the variant '{v['label']}'? Your base Blender model ({current_char_id}.blend) will remain untouched."
        else:
            confirm_message = f"Are you sure you want to permanently delete the variant '{v['label']}'? This will erase its custom Blender model ({v['SkeletonSource']}) from your hard drive."

        self.altermatic_delete_dialog.show(confirm_message, lambda: self.run_async_task(self._async_delete_altermatic_variant, current_char_id, index))

    def prompt_unreal_closed_warning(self, on_launch):
        dlg = create_unreal_closed_dialog(
            lambda e: (self.pop_dialog(), on_launch()),
            lambda e: self.pop_dialog()
        )
        self.show_dialog(dlg)

    def prompt_remote_exec_disabled_warning(self, on_fix):
        dlg = create_remote_exec_disabled_dialog(
            lambda e: (self.pop_dialog(), on_fix()),
            lambda e: self.pop_dialog()
        )
        self.show_dialog(dlg)

    def set_refresh_state(self, loading: bool):
        self.refresh_button.disabled = loading
        self.refresh_spinner.visible = loading
        self.force_update()

    def set_log_autoscroll(self, enabled: bool):
        self.log_view.auto_scroll = enabled
        self.force_update()

    def write_log(self, text: str, category: str = "standard", flush: bool = True):
        color_map = {
            "error": ft.Colors.RED_400, "warning": ft.Colors.ORANGE_400, 
            "success": ft.Colors.GREEN_400, "stage": ft.Colors.CYAN_400, "standard": ft.Colors.WHITE70
        }
        self.log_view.controls.append(ft.Text(text, color=color_map.get(category, ft.Colors.WHITE70), size=12, font_family="Consolas"))
        if len(self.log_view.controls) > 100:
            self.log_view.controls = self.log_view.controls[-100:]
        if flush: self.force_update()

    def render_empty(self):
        self.mods_list.controls.clear()
        self.mods_list.controls.append(ft.Text("No mods match active filters.", color=ft.Colors.YELLOW_400))
        try:
            self.mods_list.update()
        except Exception:
            pass
        self.force_update()

    def render_error(self, message: str):
        self.mods_list.controls.clear()
        self.mods_list.controls.append(ft.Text(message, color=ft.Colors.RED_400))
        self.force_update()

    def show_dialog(self, dlg: ft.AlertDialog):
        self.current_dialog = dlg
        if hasattr(self.main_page, "show_dialog"):
            getattr(self.main_page, "show_dialog")(dlg)
        elif hasattr(self.main_page, "open"):
            getattr(self.main_page, "open")(dlg)
        else:
            setattr(self.main_page, "dialog", dlg)
            setattr(dlg, "open", True)
            self.main_page.update()

    def pop_dialog(self):
        if hasattr(self.main_page, "pop_dialog"):
            try: getattr(self.main_page, "pop_dialog")(); return
            except Exception: pass
            
        dlg = getattr(self, "current_dialog", getattr(self.main_page, "dialog", None))
        if dlg:
            if hasattr(self.main_page, "close"):
                try: getattr(self.main_page, "close")(dlg); return
                except Exception: pass
            
            setattr(dlg, "open", False)
            self.main_page.update()

    def show_snackbar(self, message: str, color):
        self.main_page.overlay.append(ft.SnackBar(ft.Text(message, color=color), open=True))
        self.main_page.update()

    def force_update(self):
        try: self.view.update()
        except Exception: pass

    async def copy_console_to_clipboard(self, e):
        log_lines = [ctrl.value for ctrl in self.log_view.controls if isinstance(ctrl, ft.Text) and ctrl.value]
        full_log = "\n".join(log_lines)
        if full_log.strip():
            await ft.Clipboard().set(full_log)
            self.main_page.overlay.append(ft.SnackBar(ft.Text("Console content copied!"), open=True))
        self.main_page.update()

    def refresh_mods(self, scan_disk: bool = True):
        self.show_mapped = bool(self.settings.get("show_mapped", False))
        if scan_disk:
            self.set_refresh_state(loading=True)
            async def worker():
                try:
                    response = await self.cli.list_mods(show_unextracted=True) # Always fetch all, filter locally
                    if response.get("status") == "success":
                        self.raw_mods = response.get("data", [])
                        self.clear_ui_cache()
                    else:
                        self.write_log(f"CLI Error: {response.get('message')}", "error")
                except Exception as e:
                    self.write_log(f"Disk scan encountered an error: {e}", "error")
                finally:
                    self.set_refresh_state(loading=False)
                    self.apply_filters()
            self.run_async_task(worker)
        else:
            self.apply_filters()

    def get_category_from_path(self, path: str) -> str:
        if not path:
            return "Monster"
        parts = path.replace("\\", "/").split("/")
        if "Character" in parts:
            idx = parts.index("Character")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        return "Monster"

    def handle_cancel(self, e=None):
        """Dispatches cancellation task asynchronously via the CLI."""
        async def cancel_task():
            await self.cli._execute(["mod", "cancel-pipeline"])
            self.write_log("Cancellation command issued.", "warning")
        self.run_async_task(cancel_task)

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

    def apply_filters(self):
        fmodel_dir = str(self.settings.get("fmodel_output", ""))
        if not fmodel_dir or not os.path.exists(fmodel_dir):
            self.render_error("Set a valid Workspace Folder in Settings.")
            return

        filtered_mods = []
        for mod in self.raw_mods:
            if not self.show_unextracted and mod["pak_status"] == "Unextracted":
                continue

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

            filtered_mods.append(mod)

        filtered_mods.sort(key=lambda x: str(x["localized_name"] if self.show_mapped else x["name"]).lower())

        if not filtered_mods:
            self.render_empty()
        else:
            self.render_mods(filtered_mods, global_building=False, active_mod_name="")

    def run_refresh_pipeline_callback(self, monster_name: str):
        mod_data = next((m for m in self.raw_mods if m["name"] == monster_name), None)
        if mod_data:
            self.run_async_task(self._async_execute_pipeline, mod_data, "refresh_blend")

    async def load_traits_db(self):
        try:
            caches = await self.cli.get_skills_cache()
            self.traits_db = caches.get("traits_db", {})
            self.altermatic_edit_dialog.traits_db = self.traits_db
        except Exception:
            pass