# views/settings_view.py
import flet as ft
from components.common.path_picker import PathPicker
from controllers.settings_controller import SettingsController

class SettingsView:
    def __init__(self, page: ft.Page, settings: dict, on_save_callback):
        self.main_page = page
        self.settings = settings
        
        # FIXED: Initialize shared pickers once to prevent dynamic TimeoutExceptions
        self.dir_picker = ft.FilePicker()
        self.file_picker = ft.FilePicker()
        self.main_page.services.append(self.dir_picker)
        self.main_page.services.append(self.file_picker)

        # Link the Controller
        self.controller = SettingsController(self, settings, on_save_callback)

        self.fmodel_picker = PathPicker(
            label="FModel Output Folder", 
            value=str(settings.get("fmodel_output", "")), 
            icon=ft.Icons.FOLDER_OPEN,
            on_browse_click=lambda e: self.main_page.run_task(self.controller.pick_directory, self.fmodel_picker, self.dir_picker)
        )
        
        self.ue_root_picker = PathPicker(
            label="Unreal Engine Root (e.g. UE_5.1)", 
            value=str(settings.get("ue_root", "")), 
            icon=ft.Icons.FOLDER_OPEN,
            on_browse_click=lambda e: self.main_page.run_task(self.controller.pick_directory, self.ue_root_picker, self.dir_picker)
        )
        
        self.uproject_picker = PathPicker(
            label="Palworld ModKit .uproject Path", 
            value=str(settings.get("uproject", "")), 
            icon=ft.Icons.FILE_OPEN,
            on_browse_click=lambda e: self.main_page.run_task(self.controller.pick_file, self.uproject_picker, self.file_picker, ["uproject"])
        )
        
        self.blender_picker = PathPicker(
            label="Blender Executable Path", 
            value=str(settings.get("blender", "")), 
            icon=ft.Icons.FILE_OPEN,
            on_browse_click=lambda e: self.main_page.run_task(self.controller.pick_file, self.blender_picker, self.file_picker)
        )
        
        self.palworld_exe_picker = PathPicker(
            label="Palworld.exe Path", 
            value=str(settings.get("palworld_exe", "")), 
            icon=ft.Icons.FILE_OPEN,
            on_browse_click=lambda e: self.main_page.run_task(self.controller.pick_file, self.palworld_exe_picker, self.file_picker, ["exe"])
        )

        # Intercept manual typings on the exe picker so UE4SS detects the executable dynamically on-the-fly
        original_on_change = self.palworld_exe_picker.text_field.on_change
        def new_on_change(e):
            original_on_change(e)
            self.controller.refresh_ue4ss_status(self.palworld_exe_picker.get_value())
        self.palworld_exe_picker.text_field.on_change = new_on_change

        self.show_mapped_switch = ft.Switch(
            label="Show Mapped Names (e.g. Chillet instead of WeaselDragon)", 
            value=bool(settings.get("show_mapped", False))
        )
        
        # --- UE4SS Integration UI ---
        self.ue4ss_status_text = ft.Text("Checking UE4SS status...", size=14)
        
        self.install_palworld_btn = ft.ElevatedButton("Install Palworld-Experimental", on_click=lambda e: self.controller.manage_ue4ss("Install Palworld"))
        self.install_latest_btn = ft.ElevatedButton("Install Latest-Experimental", on_click=lambda e: self.controller.manage_ue4ss("Install Latest"))
        self.repair_btn = ft.ElevatedButton("Repair Corrupted Files", on_click=lambda e: self.controller.manage_ue4ss("Repair"))
        self.uninstall_btn = ft.ElevatedButton("Uninstall UE4SS", on_click=lambda e: self.controller.manage_ue4ss("Uninstall"), style=ft.ButtonStyle(color=ft.Colors.RED))
        
        self.ue4ss_buttons_row = ft.Row([
            self.install_palworld_btn,
            self.install_latest_btn,
            self.repair_btn,
            self.uninstall_btn
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
                ft.Text("Preferences", size=20, weight=ft.FontWeight.BOLD),
                self.show_mapped_switch,
                ft.Divider(),
                ft.ElevatedButton("Save and Reload Mod List", icon=ft.Icons.SAVE, on_click=self._on_save, height=50)
            ]
        )
        
        # Run standard startup scan
        self.controller.refresh_ue4ss_status()

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
        current_paths = {
            "fmodel_output": self.fmodel_picker.get_value(),
            "ue_root": self.ue_root_picker.get_value(),
            "uproject": self.uproject_picker.get_value(),
            "blender": self.blender_picker.get_value(),
            "palworld_exe": self.palworld_exe_picker.get_value(),
        }
        self.controller.save_clicked(current_paths, bool(self.show_mapped_switch.value))

    def show_dialog(self, dlg: ft.AlertDialog):
        self.main_page.show_dialog(dlg)

    def pop_dialog(self):
        self.main_page.pop_dialog()

    def show_snackbar(self, message: str, color):
        self.main_page.overlay.append(ft.SnackBar(ft.Text(message, color=color), open=True))
        self.main_page.update()