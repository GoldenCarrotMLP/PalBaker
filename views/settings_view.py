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

        self.show_mapped_switch = ft.Switch(
            label="Show Mapped Names (e.g. Chillet instead of WeaselDragon)", 
            value=bool(settings.get("show_mapped", False))
        )

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
                ft.Text("Preferences", size=20, weight=ft.FontWeight.BOLD),
                self.show_mapped_switch,
                ft.Divider(),
                ft.ElevatedButton("Save and Reload Mod List", icon=ft.Icons.SAVE, on_click=self._on_save, height=50)
            ]
        )

    def update_settings(self, new_settings: dict):
        self.settings = new_settings
        self.fmodel_picker.set_value(str(new_settings.get("fmodel_output", "")))
        self.ue_root_picker.set_value(str(new_settings.get("ue_root", "")))
        self.uproject_picker.set_value(str(new_settings.get("uproject", "")))
        self.blender_picker.set_value(str(new_settings.get("blender", "")))
        self.palworld_exe_picker.set_value(str(new_settings.get("palworld_exe", "")))
        self.show_mapped_switch.value = bool(new_settings.get("show_mapped", False))
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