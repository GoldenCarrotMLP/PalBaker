# views/mods_view.py
import flet as ft
from controllers.mods_controller import ModsController
from components.mods.mod_card import ModItem
from components.mods.dialogs import (
    create_overwrite_warning_dialog,
    create_decompile_options_dialog,
    create_troubleshooting_advisor_dialog
)

class ModsView:
    def __init__(self, page: ft.Page, settings: dict):
        self.main_page = page
        self.settings = settings
        
        self.controller = ModsController(self, settings)

        self.mods_list = ft.ListView(expand=True, spacing=10)
        self.log_view = ft.ListView(expand=True, spacing=2, auto_scroll=True)
        self.cached_components = {}  # Store UI components by mod name

        # File Picker for Icons
        self.icon_picker = ft.FilePicker()
        self.main_page.services.append(self.icon_picker)
        

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
        self.refresh_spinner = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False)

        self.console_container = ft.Container(
            content=self.log_view, expand=True, bgcolor=ft.Colors.BLACK, 
            border_radius=10, padding=15, border=ft.Border.all(1, ft.Colors.WHITE10)
        )

        self.view = ft.Column(
            expand=True,
            controls=[
                ft.Row([self.search_bar, self.refresh_spinner, self.refresh_button]),
                self.badge_chips,
                self.status_chips,
                ft.Container(self.mods_list, height=300, border=ft.Border.all(1, ft.Colors.WHITE10), border_radius=10, padding=10),
                ft.Row([
                    ft.Text("Build Console", size=16, weight=ft.FontWeight.BOLD),
                    ft.IconButton(icon=ft.Icons.COPY_ALL, tooltip="Copy console", on_click=self.copy_console_to_clipboard)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.console_container
            ]
        )

    # --- Task Runners ---
    def run_in_thread(self, func):
        self.main_page.run_thread(func)

    def run_async_task(self, func):
        self.main_page.run_task(func)

    # --- Render Methods ---
    def render_mods(self, mods_data: list[dict], global_building: bool, active_mod_name: str):
        """Takes pure data from the Controller, instantiates the UI ModItems, and displays them."""
        self.mods_list.controls.clear()
        self.cached_components.clear()
        
        for mod_data in mods_data:
            item = ModItem(
                mod_data=mod_data,
                on_action_click=self.controller.handle_action,
                on_cancel_click=self.controller.handle_cancel,
                on_pick_icon=self.trigger_icon_picker,
                is_building=global_building,
                show_mapped=self.controller.show_mapped
            )
            item.set_state(global_building, is_active_target=(mod_data["name"] == active_mod_name))
            self.cached_components[mod_data["name"]] = item
            self.mods_list.controls.append(item.view)
            
        self.force_update()

    # --- Icon Picker Logic ---
    async def trigger_icon_picker(self, mod_data):
        """Asynchronously triggers the file picker and applies the selected icon on success."""
        result = await self.icon_picker.pick_files(allow_multiple=False, allowed_extensions=["png", "jpg", "jpeg"])
        # FIX: result is a raw list in Flet 0.84.0+
        if result and len(result) > 0:
            self.controller.apply_custom_icon(mod_data, result[0].path)

    def _on_icon_picked(self, e):
        """Event handler for icon file picker results, safe across all Flet versions."""
        if e.files and len(e.files) > 0 and self.active_icon_mod_data:
            self.controller.apply_custom_icon(self.active_icon_mod_data, e.files[0].path)
        self.active_icon_mod_data = None

    # --- ModCard Visual Setters ---
    def update_card_progress(self, mod_name: str, line: str, flush: bool):
        if mod_name in self.cached_components:
            self.cached_components[mod_name].update_progress(line, flush)

    def reset_card_state(self, mod_name: str, success: bool):
        if mod_name in self.cached_components:
            self.cached_components[mod_name].set_state(global_building=False, is_active_target=False, success=success)

    # --- Dialog Factories ---
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

    # --- Core UI Updaters ---
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

    def show_dialog(self, dlg: ft.AlertDialog):
        self.main_page.show_dialog(dlg)

    def pop_dialog(self):
        self.main_page.pop_dialog()

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