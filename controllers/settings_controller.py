# controllers/settings_controller.py
import flet as ft  # type: ignore
import threading
import asyncio
from utils.config import save_settings
from utils.builder.config_helper import restore_palbaker_backup
from utils.plugin_manager import (
    check_project_requirements, 
    install_and_compile_plugin, 
    inject_missing_assets
)
from utils.plugins.installer import (
    enable_remote_execution_settings,
    enable_cooking_settings,
    is_unreal_running,
    close_unreal_editor,
    launch_unreal_editor
)

class SettingsController:
    def __init__(self, view, settings: dict, on_save_callback):
        self.view = view
        self.settings = settings
        self.on_save_callback = on_save_callback

    async def pick_directory(self, target_picker_component, picker):
        """Asynchronously triggers directory selection."""
        result = await picker.get_directory_path()
        if result:
            target_picker_component.set_value(str(result))

    async def pick_file(self, target_picker_component, picker, allowed_extensions=None):
        """Asynchronously triggers file selection."""
        file_type = ft.FilePickerFileType.ANY
        if allowed_extensions:
            file_type = ft.FilePickerFileType.CUSTOM

        result = await picker.pick_files(
            allow_multiple=False, 
            allowed_extensions=allowed_extensions,
            file_type=file_type
        )
        if result and len(result) > 0 and result[0].path:
            target_picker_component.set_value(str(result[0].path))
            
            if target_picker_component == self.view.palworld_exe_picker:
                self.refresh_ue4ss_status(str(result[0].path))

    def refresh_ue4ss_status(self, exe_path: str | None = None):
        if exe_path is None:
            exe_path = self.view.palworld_exe_picker.get_value()
            
        from utils.ue4ss_helper import get_ue4ss_status
        status_ue4ss = get_ue4ss_status(exe_path)
        self.view.update_ue4ss_ui(status_ue4ss)
        
        from utils.palschema_helper import get_palschema_status
        status_palschema = get_palschema_status(exe_path)
        self.view.update_palschema_ui(status_palschema)
        
    def manage_ue4ss(self, action: str):
        self.view.main_page.run_task(self._manage_ue4ss_async, action)
        
    async def _manage_ue4ss_async(self, action: str):
        exe_path = self.view.palworld_exe_picker.get_value()
        from utils.ue4ss_helper import download_and_extract_ue4ss, uninstall_ue4ss, get_ue4ss_status
        
        def log_callback(msg, is_error):
            self.view.show_snackbar(msg, ft.Colors.RED_400 if is_error else ft.Colors.GREEN_400)
            
        status = get_ue4ss_status(exe_path)
        branch = status.get("branch", "Palworld-Experimental")
        if branch == "Unknown" or branch == "None":
            branch = "Palworld-Experimental"
            
        if action == "Install Palworld":
            await asyncio.to_thread(download_and_extract_ue4ss, exe_path, "Palworld-Experimental", log_callback)
        elif action == "Install Latest":
            await asyncio.to_thread(download_and_extract_ue4ss, exe_path, "Latest-Experimental", log_callback)
        elif action == "Repair":
            await asyncio.to_thread(download_and_extract_ue4ss, exe_path, branch, log_callback)
        elif action == "Uninstall":
            from utils.palschema_helper import uninstall_palschema
            await asyncio.to_thread(uninstall_palschema, exe_path, lambda m, e: None)
            await asyncio.to_thread(uninstall_ue4ss, exe_path, log_callback)
            
        self.refresh_ue4ss_status(exe_path)

    def manage_palschema(self, action: str):
        self.view.main_page.run_task(self._manage_palschema_async, action)

    async def _manage_palschema_async(self, action: str):
        exe_path = self.view.palworld_exe_picker.get_value()
        from utils.palschema_helper import download_and_extract_palschema, uninstall_palschema

        def log_callback(msg, is_error):
            self.view.show_snackbar(msg, ft.Colors.RED_400 if is_error else ft.Colors.GREEN_400)

        if action == "Install":
            await asyncio.to_thread(download_and_extract_palschema, exe_path, log_callback)
        elif action == "Uninstall":
            await asyncio.to_thread(uninstall_palschema, exe_path, log_callback)

        self.refresh_ue4ss_status(exe_path)

    def quiet_save(self, current_paths: dict, show_mapped: bool):
        """Saves settings quietly to disk without triggering the heavy verification/build pipeline."""
        self.settings.update(current_paths)
        self.settings["show_mapped"] = show_mapped
        save_settings(self.settings)

    def save_clicked(self, current_paths: dict, show_mapped: bool):
        self.settings.update(current_paths)
        self.settings["show_mapped"] = show_mapped
        save_settings(self.settings)

        restore_palbaker_backup(self.settings.get("uproject"))

        def verify_and_build():
            def ask_user_modal(title, content_control):
                result = [False]
                event = threading.Event()

                def on_yes(e):
                    result[0] = True
                    self.view.pop_dialog()
                    event.set()

                def on_no(e):
                    result[0] = False
                    self.view.pop_dialog()
                    event.set()

                dlg = ft.AlertDialog(
                    modal=True,
                    title=ft.Text(title),
                    content=content_control,
                    actions=[
                        ft.TextButton("Skip / No", on_click=on_no),
                        ft.TextButton("Yes, Fix It", on_click=on_yes, style=ft.ButtonStyle(color=ft.Colors.BLUE)),
                    ]
                )
                self.view.show_dialog(dlg)
                event.wait()
                return result[0]

            reqs = check_project_requirements(self.settings.get("ue_root", ""), self.settings.get("uproject", ""))

            if reqs.get("error"):
                self.view.show_snackbar(reqs["error"], ft.Colors.RED_400)
                self.on_save_callback()
                return

            unreal_was_running = is_unreal_running()
            needs_relaunch = False

            # STEP 1: Plugin Sync & Compile
            if reqs["needs_plugin_sync"] or reqs["needs_compile"]:
                content = ft.Column([
                    ft.Text("PalBaker requires a C++ Editor Utility Plugin to automatically generate Animation Blueprints via Python:"),
                    ft.Text(" \u2022 PalBaker Editor Utilities", color=ft.Colors.CYAN_200, weight=ft.FontWeight.BOLD),
                    ft.Text("The plugin is missing or outdated in your active Unreal Engine project.", color=ft.Colors.ORANGE_400),
                    ft.Text("Unreal Editor MUST be closed to install it safely to avoid permission errors.", color=ft.Colors.RED_300, weight=ft.FontWeight.BOLD) if unreal_was_running else ft.Text(""),
                    ft.Text("Would you like to install and compile it now?", weight=ft.FontWeight.BOLD)
                ], tight=True)

                if ask_user_modal("Step 1: Install Required Plugin", content):
                    if is_unreal_running():
                        self.view.show_snackbar("Closing Unreal Editor to unlock files...", ft.Colors.ORANGE_400)
                        close_unreal_editor()
                        unreal_was_running = True
                        needs_relaunch = True
                    
                    self.view.show_snackbar("Installing and verifying C++ plugin... (This may take a minute)", ft.Colors.WHITE)
                    success, msg = install_and_compile_plugin(self.settings["ue_root"], self.settings["uproject"])
                    self.view.show_snackbar(msg, ft.Colors.GREEN_400 if success else ft.Colors.RED_400)
                    if not success:
                        self.on_save_callback()
                        return

            # STEP 2: Core Assets
            missing_assets = reqs.get("missing_assets", [])
            if missing_assets:
                files_controls = [ft.Text(f" \u2022 {f}", size=12, color=ft.Colors.WHITE70) for f in missing_assets]
                files_list = ft.ListView(controls=files_controls, height=150, spacing=2, padding=10)  # type: ignore
                
                content = ft.Column([
                    ft.Text("The following core framework assets are missing from your ModKit's Content directory:"),
                    ft.Container(content=files_list, border=ft.Border.all(1, ft.Colors.WHITE24), border_radius=5),
                    ft.Text("PalBaker requires these to cleanly bind Material Instances.\nWould you like to inject them into your project automatically?", weight=ft.FontWeight.BOLD)
                ], tight=True)

                if ask_user_modal("Step 2: Inject Core Assets", content):
                    success, msg = inject_missing_assets(self.settings["uproject"])
                    self.view.show_snackbar(msg, ft.Colors.GREEN_400 if success else ft.Colors.RED_400)

            # STEP 3: Remote Execution
            if reqs.get("needs_remote_exec_enable"):
                content = ft.Column([
                    ft.Text("PalBaker orchestrates Unreal Engine via the Python Remote Execution API, but it is currently disabled."),
                    ft.Text("Would you like to enable 'Python Remote Execution' in DefaultEngine.ini now?", weight=ft.FontWeight.BOLD)
                ], tight=True)

                if ask_user_modal("Step 3: Enable Python Remote Execution", content):
                    enable_remote_execution_settings(self.settings["uproject"])
                    self.view.show_snackbar("Python Remote Execution enabled.", ft.Colors.GREEN_400)
                    needs_relaunch = True

            # STEP 4: Cooking Settings
            if reqs.get("needs_cooking_setup"):
                content = ft.Column([
                    ft.Text("Unreal Engine must be configured to compile loose .uasset files to generate valid Palworld mods."),
                    ft.Text("Would you like to disable 'I/O Store' & 'Material Shader Sharing' in DefaultGame.ini now?", weight=ft.FontWeight.BOLD)
                ], tight=True)

                if ask_user_modal("Step 4: Configure Cooking Settings", content):
                    enable_cooking_settings(self.settings["uproject"])
                    self.view.show_snackbar("Cooking settings configured.", ft.Colors.GREEN_400)
                    needs_relaunch = True

            self.view.show_snackbar("Project settings verification complete!", ft.Colors.GREEN_400)
            
            if needs_relaunch or not is_unreal_running():
                self.view.show_snackbar("Launching Unreal Editor...", ft.Colors.CYAN_400)
                launch_unreal_editor(self.settings["ue_root"], self.settings["uproject"])

            self.on_save_callback()

        threading.Thread(target=verify_and_build, daemon=True).start()