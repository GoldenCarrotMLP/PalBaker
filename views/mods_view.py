# views/mods_view.py
import flet as ft
import os

from controllers.mods_controller import ModsController
from components.mods.mod_card import ModItem
from components.mods.dialogs import (
    create_overwrite_warning_dialog,
    create_decompile_options_dialog,
    create_troubleshooting_advisor_dialog
)
from components.mods.altermatic_dialog import AltermaticDialog

class ModsView:
    def __init__(self, page: ft.Page, settings: dict):
        self.main_page = page
        self.settings = settings
        
        self.controller = ModsController(self, settings)

        self.mods_list = ft.ListView(expand=True, spacing=10)
        self.log_view = ft.ListView(expand=True, spacing=2, auto_scroll=True)
        
        self.cached_components = {}
        self.expanded_states = {}  # Tracks the open/closed state of dropdowns across rescans

        # Non-visual file picker services
        self.icon_picker = ft.FilePicker()
        self.main_page.services.append(self.icon_picker)
        
        self.audio_picker = ft.FilePicker()
        self.main_page.services.append(self.audio_picker)

        self.active_icon_mod_data = None
        self.search_bar = ft.TextField(
            label="Search by internal or actual name...",
            expand=True,
            on_change=lambda e: self.controller.update_search(self.search_bar.value),
            prefix_icon=ft.Icons.SEARCH
        )
        
        self.badge_chips = ft.Row([
            ft.Text("Tags:", weight=ft.FontWeight.BOLD),
            ft.Chip(label=ft.Text("RAW"), on_select=lambda e: self.controller.update_badge_filter("RAW", e.control.selected)),
            ft.Chip(label=ft.Text("SOURCE"), on_select=lambda e: self.controller.update_badge_filter("SOURCE", e.control.selected)),
            ft.Chip(label=ft.Text("UE ASSETS"), on_select=lambda e: self.controller.update_badge_filter("UE ASSETS", e.control.selected)),
            ft.Chip(label=ft.Text("MODIFIED"), on_select=lambda e: self.controller.update_badge_filter("MODIFIED", e.control.selected)),
            ft.Chip(label=ft.Text("ALTERMATIC"), on_select=lambda e: self.controller.update_badge_filter("ALTERMATIC", e.control.selected)),
        ], spacing=10)

        self.status_chips = ft.Row([
            ft.Text("Status:", weight=ft.FontWeight.BOLD),
            ft.Chip(label=ft.Text("Packed"), on_select=lambda e: self.controller.update_status_filter("Packed", e.control.selected)),
            ft.Chip(label=ft.Text("Packed with Errors"), on_select=lambda e: self.controller.update_status_filter("Packed with Errors", e.control.selected)),
            ft.Chip(label=ft.Text("Unpacked"), on_select=lambda e: self.controller.update_status_filter("Unpacked", e.control.selected)),
            ft.Chip(label=ft.Text("Outdated"), on_select=lambda e: self.controller.update_status_filter("Outdated", e.control.selected)),
        ], spacing=10)

        self.refresh_button = ft.IconButton(
            icon=ft.Icons.REFRESH, 
            tooltip="Rescan disk for mods",
            on_click=lambda e: self.controller.refresh_mods(scan_disk=True)
        )
        self.refresh_button.disabled = False
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
                ft.Row([self.search_bar, self.refresh_spinner, self.refresh_button]),
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

        # Instantiate Altermatic visual modal dialog cleanly using the traits database and dispatcher
        self.altermatic_dialog = AltermaticDialog(
            self.main_page, 
            self.settings, 
            self.controller.traits_db, 
            self.controller.save_altermatic_variant_callback,
            on_refresh_callback=self.controller.run_refresh_pipeline_callback,
            on_delete_callback=self.controller.delete_altermatic_variant_by_index
        )

    def on_divider_drag(self, e: ft.DragUpdateEvent):
        delta = 0.0
        if hasattr(e, "local_delta") and e.local_delta is not None:
            delta = e.local_delta.y
        elif hasattr(e, "delta_y"):
            delta = e.delta_y

        new_console_height = max(50, self.console_container.height - delta)
        self.console_container.height = new_console_height
        self.console_height = new_console_height
        
        self.settings["console_height"] = new_console_height
        from utils.config import save_settings
        save_settings(self.settings)
        
        self.force_update()

    def run_in_thread(self, func):
        self.main_page.run_thread(func)

    def run_async_task(self, func, *args):
        self.main_page.run_task(func, *args)

    def clear_ui_cache(self):
        """Saves the current expanded states and clears the UI components cache."""
        for name, item in self.cached_components.items():
            if item.details_visible:
                self.expanded_states[name] = True
            else:
                self.expanded_states.pop(name, None)
        self.cached_components.clear()

    def render_mods(self, mods_data: list[dict], global_building: bool, active_mod_name: str):
        self.mods_list.controls.clear()
        
        for mod_data in mods_data:
            name = mod_data["name"]
            if name in self.cached_components:
                item = self.cached_components[name]
                item.mod_data = mod_data
                item.set_show_mapped(self.controller.show_mapped)
                item.set_state(global_building, is_active_target=(name == active_mod_name))
            else:
                item = ModItem(
                    mod_data=mod_data,
                    on_action_click=self.controller.handle_action,
                    on_cancel_click=self.controller.handle_cancel,
                    on_pick_icon=self.trigger_icon_picker,
                    on_pick_audio=self.trigger_audio_picker,
                    on_play_audio=self.controller.play_audio,
                    on_clear_audio=self.controller.clear_audio,
                    # Altermatic UI forward bindings
                    on_toggle_altermatic=self.controller.toggle_altermatic,
                    on_add_variant=self.controller.add_altermatic_variant,
                    on_edit_variant=self.controller.edit_altermatic_variant,
                    on_delete_variant=self.controller.delete_altermatic_variant,
                    is_building=global_building,
                    show_mapped=self.controller.show_mapped
                )
                
                # Restore the expanded state if it was open before the cache was cleared
                if self.expanded_states.get(name, False):
                    item.details_visible = True
                    item.details_container.visible = True
                    item.chevron.icon = ft.Icons.KEYBOARD_ARROW_UP

                item.set_state(global_building, is_active_target=(name == active_mod_name))
                self.cached_components[name] = item
                
            self.mods_list.controls.append(item.view)
        self.force_update()

    async def trigger_icon_picker(self, mod_data):
        result = await self.icon_picker.pick_files(allow_multiple=False, allowed_extensions=["png", "jpg", "jpeg"])
        if result and len(result) > 0:
            path = result[0].path
            if isinstance(path, str):
                self.controller.apply_custom_icon(mod_data, path)

    async def trigger_audio_picker(self, mod_data, cry_name):
        result = await self.audio_picker.pick_files(allow_multiple=False, allowed_extensions=["wav", "mp3", "ogg"])
        if result and len(result) > 0:
            path = result[0].path
            if isinstance(path, str):
                await self.controller.apply_custom_audio(mod_data, cry_name, path)

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
            lambda e: (self.pop_dialog(), self.controller.execute_decompile_pipeline(mod_data, False)),
            lambda e: (self.pop_dialog(), self.controller.execute_decompile_pipeline(mod_data, True)),
            lambda e: self.pop_dialog()
        )
        self.show_dialog(dlg)

    def prompt_troubleshooting_advisor(self, summary):
        dlg = create_troubleshooting_advisor_dialog(summary, lambda e: self.pop_dialog())
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
        self.force_update()

    def render_error(self, message: str):
        self.mods_list.controls.clear()
        self.mods_list.controls.append(ft.Text(message, color=ft.Colors.RED_400))
        self.force_update()

    # FIXED: Reconstructed to provide version-safe dialog operations across Flet versions
    # preventing UI locks and permanently disabled buttons.
    def show_dialog(self, dlg: ft.AlertDialog):
        if hasattr(self.main_page, "show_dialog"):
            self.main_page.show_dialog(dlg)
        elif hasattr(self.main_page, "open"):
            self.main_page.open(dlg)
        else:
            self.main_page.dialog = dlg
            dlg.open = True
            self.main_page.update()

    def pop_dialog(self):
        if hasattr(self.main_page, "pop_dialog"):
            try:
                self.main_page.pop_dialog()
                return
            except Exception:
                pass
                
        if hasattr(self.main_page, "close") and hasattr(self.main_page, "dialog") and self.main_page.dialog:
            try:
                self.main_page.close(self.main_page.dialog)
                return
            except Exception:
                pass
                
        if hasattr(self.main_page, "dialog") and self.main_page.dialog:
            self.main_page.dialog.open = False
            self.main_page.update()

    def show_snackbar(self, message: str, color):
        """Displays a temporary colored popup alert at the bottom of the screen."""
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
        self.controller.refresh_mods(scan_disk)