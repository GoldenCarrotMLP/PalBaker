# views/settings_view.py
import flet as ft  # type: ignore
from components.common.path_picker import PathPicker
from controllers.settings_controller import SettingsController
from ui_client.dispatcher import PalBakerCLI

class SettingsView:
    def __init__(self, page: ft.Page, settings: dict, on_save_callback, on_rebuild_db_callback):
        self.main_page = page
        self.settings = settings
        self.on_rebuild_db_callback = on_rebuild_db_callback
        self.on_save_callback = on_save_callback # Bind callback to class instance
        
        self.dir_picker = ft.FilePicker()
        self.file_picker = ft.FilePicker()
        self.main_page.services.append(self.dir_picker)
        self.main_page.services.append(self.file_picker)

        self.controller = SettingsController(self, settings, on_save_callback)
        self.cli = PalBakerCLI()

        self.fmodel_picker = PathPicker(
            label="Workspace Folder", 
            value=str(settings.get("fmodel_output", "")), 
            icon=ft.Icons.FOLDER_OPEN,
            on_browse_click=lambda e: self.main_page.run_task(self.controller.pick_directory, self.fmodel_picker, self.dir_picker),
            on_change=self._auto_save
        )
        
        self.ue_root_picker = PathPicker(
            label="Unreal Engine Root (e.g. UE_5.1)", 
            value=str(settings.get("ue_root", "")), 
            icon=ft.Icons.FOLDER_OPEN,
            on_browse_click=lambda e: self.main_page.run_task(self.controller.pick_directory, self.ue_root_picker, self.dir_picker),
            on_change=self._auto_save
        )
        
        self.uproject_picker = PathPicker(
            label="Palworld ModKit .uproject Path", 
            value=str(settings.get("uproject", "")), 
            icon=ft.Icons.FILE_OPEN,
            on_browse_click=lambda e: self.main_page.run_task(self.controller.pick_file, self.uproject_picker, self.file_picker, ["uproject"]),
            on_change=self._auto_save
        )
        
        self.blender_picker = PathPicker(
            label="Blender Executable Path", 
            value=str(settings.get("blender", "")), 
            icon=ft.Icons.FILE_OPEN,
            on_browse_click=lambda e: self.main_page.run_task(self.controller.pick_file, self.blender_picker, self.file_picker),
            on_change=self._auto_save
        )
        
        self.palworld_exe_picker = PathPicker(
            label="Palworld.exe Path", 
            value=str(settings.get("palworld_exe", "")), 
            icon=ft.Icons.FILE_OPEN,
            on_browse_click=lambda e: self.main_page.run_task(self.controller.pick_file, self.palworld_exe_picker, self.file_picker, ["exe"]),
            on_change=self._on_palworld_exe_change
        )

        self.show_mapped_switch = ft.Switch(
            label="Show Mapped Names (e.g. Chillet instead of WeaselDragon)", 
            value=bool(settings.get("show_mapped", False)),
            on_change=self._on_show_mapped_change
        )
        
        # --- UE4SS Integration UI ---
        self.ue4ss_status_text = ft.Text("Checking UE4SS status...", size=14)
        
        self.install_palworld_btn = ft.ElevatedButton("Install Palworld-Experimental", on_click=lambda e: self.run_async_task(self._async_manage_ue4ss))
        self.install_latest_btn = ft.ElevatedButton("Install Latest-Experimental", on_click=lambda e: self.run_async_task(self._async_manage_ue4ss))
        self.repair_btn = ft.ElevatedButton("Repair Corrupted Files", on_click=lambda e: self.run_async_task(self._async_manage_ue4ss))
        self.uninstall_btn = ft.ElevatedButton("Uninstall UE4SS", on_click=lambda e: self.run_async_task(self._async_manage_ue4ss), style=ft.ButtonStyle(color=ft.Colors.RED))
        
        self.ue4ss_buttons_row = ft.Row([
            self.install_palworld_btn,
            self.install_latest_btn,
            self.repair_btn,
            self.uninstall_btn
        ], wrap=True)

        # --- PALSCHEMA INTEGRATION UI ---
        self.palschema_status_text = ft.Text("Checking PalSchema status...", size=14)
        
        self.install_palschema_btn = ft.ElevatedButton("Install PalSchema", on_click=lambda e: self.run_async_task(self._async_manage_palschema))
        self.uninstall_palschema_btn = ft.ElevatedButton("Uninstall PalSchema", on_click=lambda e: self.run_async_task(self._async_manage_palschema), style=ft.ButtonStyle(color=ft.Colors.RED))
        
        self.palschema_buttons_row = ft.Row([
            self.install_palschema_btn,
            self.uninstall_palschema_btn
        ], wrap=True)

        self.view = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=20,
            controls=[
                ft.Text("Application Paths", size=20, weight=ft.FontWeight.BOLD),
                self.fmodel_picker.view,
                self.ue_root_picker.view,
                self.uproject_picker.view,
                self.blender_picker.view,
                self.palworld_exe_picker.view,
                ft.Divider(),
                ft.Text("UE4SS Integration", size=20, weight=ft.FontWeight.BOLD),
                self.ue4ss_status_text,
                self.ue4ss_buttons_row,
                ft.Divider(),
                ft.Text("PalSchema Integration", size=20, weight=ft.FontWeight.BOLD),
                self.palschema_status_text,
                self.palschema_buttons_row,
                ft.Divider(),
                ft.Text("Preferences", size=20, weight=ft.FontWeight.BOLD),
                self.show_mapped_switch,
                ft.Divider(),
                ft.Row([
                    ft.ElevatedButton("Save & Verify Project Requirements", icon=ft.Icons.VERIFIED, on_click=self._on_save, height=50, expand=True),
                    ft.ElevatedButton("Rebuild Game Database", icon=ft.Icons.STORAGE_ROUNDED, on_click=self._on_rebuild_db, height=50, style=ft.ButtonStyle(color=ft.Colors.CYAN_400))
                ], spacing=10)
            ]
        )
        
        # Run standard startup scan
        self.controller.refresh_ue4ss_status()

    def _auto_save(self, e=None):
        current_paths = {
            "fmodel_output": self.fmodel_picker.get_value(),
            "ue_root": self.ue_root_picker.get_value(),
            "uproject": self.uproject_picker.get_value(),
            "blender": self.blender_picker.get_value(),
            "palworld_exe": self.palworld_exe_picker.get_value(),
        }
        self.controller.quiet_save(current_paths, bool(self.show_mapped_switch.value))

    def _on_palworld_exe_change(self, e=None):
        self._auto_save()
        self.controller.refresh_ue4ss_status(self.palworld_exe_picker.get_value())

    def _on_show_mapped_change(self, e=None):
        self._auto_save()
        if self.on_save_callback:
            # Setting scan_disk=False instantly updates mod names without freezing the UI!
            self.on_save_callback(scan_disk=False)

    def _on_rebuild_db(self, e):
        """Dispatches the linked database rebuild warning trigger."""
        if self.on_rebuild_db_callback:
            self.on_rebuild_db_callback()

    def _on_save(self, e):
        """Save and verify project requirements."""
        self.main_page.run_task(self._async_verify)

    async def _async_verify(self):
        """Async wrapper for env verify."""
        try:
            result = await self.cli.env_verify()
            if result.get("status") == "success":
                self.show_snackbar("Verification completed successfully!", ft.Colors.GREEN)
            else:
                self.show_snackbar(f"Verification failed: {result.get('message', 'Unknown error')}", ft.Colors.RED)
        except Exception as e:
            self.show_snackbar(f"Error during verification: {str(e)}", ft.Colors.RED)

    async def _async_manage_ue4ss(self):
        """Async wrapper for UE4SS management."""
        try:
            result = await self.cli.env_ue4ss_install()
            if result.get("status") == "success":
                self.show_snackbar("UE4SS management completed!", ft.Colors.GREEN)
            else:
                self.show_snackbar(f"Error: {result.get('message', 'Unknown error')}", ft.Colors.RED)
        except Exception as e:
            self.show_snackbar(f"Error: {str(e)}", ft.Colors.RED)

    async def _async_manage_palschema(self):
        """Async wrapper for PalSchema management."""
        try:
            result = await self.cli.env_install_plugin()
            if result.get("status") == "success":
                self.show_snackbar("PalSchema management completed!", ft.Colors.GREEN)
            else:
                self.show_snackbar(f"Error: {result.get('message', 'Unknown error')}", ft.Colors.RED)
        except Exception as e:
            self.show_snackbar(f"Error: {str(e)}", ft.Colors.RED)

    def run_async_task(self, func, *args):
        self.main_page.run_task(func, *args)

    def update_ue4ss_ui(self, status: dict):
        """Map contextual actions correctly and shift font colors based on hash validation."""
        s = status["status"]
        b = status["branch"]
        c = status["corrupted"]
        
        color = ft.Colors.WHITE
        
        # Reset buttons to default baseline
        self.install_palworld_btn.disabled = False
        self.install_latest_btn.disabled = False
        
        if s == "Installed":
            if c:
                text = f"Status: Installed ({b}) - CORRUPTED!"
                color = ft.Colors.RED_400
                self.repair_btn.visible = True
            else:
                text = f"Status: Installed ({b})"
                color = ft.Colors.GREEN_400
                self.repair_btn.visible = False
                
            self.uninstall_btn.visible = True
            
            # Lock out the button for the branch they are already on
            if b == "Palworld-Experimental":
                self.install_palworld_btn.disabled = True
            elif b == "Latest-Experimental":
                self.install_latest_btn.disabled = True
                
        elif s == "Not Installed":
            text = "Status: Not Installed"
            color = ft.Colors.ORANGE_400
            self.uninstall_btn.visible = False
            self.repair_btn.visible = False
        else:
            text = f"Status: {s}"
            self.uninstall_btn.visible = False
            self.repair_btn.visible = False
            self.install_palworld_btn.disabled = True
            self.install_latest_btn.disabled = True
            
        self.ue4ss_status_text.value = text
        self.ue4ss_status_text.color = color
        
        try:
            self.main_page.update()
        except Exception:
            pass

    def update_palschema_ui(self, status: dict):
        """Renders the visual state of PalSchema dynamically in real-time."""
        s = status["status"]
        color = ft.Colors.WHITE
        
        self.install_palschema_btn.disabled = False
        self.uninstall_palschema_btn.disabled = False
        
        if s == "Installed":
            text = "Status: Installed"
            color = ft.Colors.GREEN_400
            self.install_palschema_btn.disabled = True
            self.uninstall_palschema_btn.visible = True
        elif s == "Not Installed":
            text = "Status: Not Installed"
            color = ft.Colors.ORANGE_400
            self.uninstall_palschema_btn.visible = False
        else:
            text = f"Status: {s}"
            self.install_palschema_btn.disabled = True
            self.uninstall_palschema_btn.disabled = True
            
        self.palschema_status_text.value = text
        self.palschema_status_text.color = color
        
        try:
            self.main_page.update()
        except Exception:
            pass

    def update_settings(self, new_settings: dict):
        self.settings = new_settings
        self.fmodel_picker.set_value(str(new_settings.get("fmodel_output", "")))
        self.ue_root_picker.set_value(str(new_settings.get("ue_root", "")))
        self.uproject_picker.set_value(str(new_settings.get("uproject", "")))
        self.blender_picker.set_value(str(new_settings.get("blender", "")))
        self.palworld_exe_picker.set_value(str(new_settings.get("palworld_exe", "")))
        self.show_mapped_switch.value = bool(new_settings.get("show_mapped", False))
        
        self.controller.refresh_ue4ss_status()
        self.main_page.update()

    def _on_save(self, e):
        self.main_page.run_task(self._async_verify)

    async def _async_verify(self):
        """Async wrapper for env verify."""
        try:
            result = await self.cli.env_verify()
            if result.get("status") == "success":
                self.show_snackbar("Verification completed successfully!", ft.Colors.GREEN)
            else:
                self.show_snackbar(f"Verification failed: {result.get('message', 'Unknown error')}", ft.Colors.RED)
        except Exception as e:
            self.show_snackbar(f"Error during verification: {str(e)}", ft.Colors.RED)

    async def _async_manage_ue4ss(self):
        """Async wrapper for UE4SS management."""
        try:
            result = await self.cli.env_ue4ss_install()
            if result.get("status") == "success":
                self.show_snackbar("UE4SS management completed!", ft.Colors.GREEN)
            else:
                self.show_snackbar(f"Error: {result.get('message', 'Unknown error')}", ft.Colors.RED)
        except Exception as e:
            self.show_snackbar(f"Error: {str(e)}", ft.Colors.RED)

    async def _async_manage_palschema(self):
        """Async wrapper for PalSchema management."""
        try:
            result = await self.cli.env_install_plugin()
            if result.get("status") == "success":
                self.show_snackbar("PalSchema management completed!", ft.Colors.GREEN)
            else:
                self.show_snackbar(f"Error: {result.get('message', 'Unknown error')}", ft.Colors.RED)
        except Exception as e:
            self.show_snackbar(f"Error: {str(e)}", ft.Colors.RED)

    def run_async_task(self, func, *args):
        self.main_page.run_task(func, *args)

    def show_dialog(self, dlg: ft.AlertDialog):
        self.main_page.show_dialog(dlg)

    def pop_dialog(self):
        self.main_page.pop_dialog()

    def show_snackbar(self, message: str, color):
        self.main_page.overlay.append(ft.SnackBar(ft.Text(message, color=color), open=True))
        self.main_page.update()