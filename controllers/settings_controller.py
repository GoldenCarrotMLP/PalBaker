# controllers/settings_controller.py
import flet as ft
import threading
import asyncio
from utils.config import save_settings
from utils.builder.config_helper import restore_palbaker_backup
from utils.plugin_manager import (
    check_project_requirements, 
    install_and_compile_plugin, 
    inject_missing_assets, 
    enable_remote_execution_settings,
    enable_cooking_settings,
    restart_unreal_editor
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
        # Cleanly resolve the correct file type enum based on the custom extensions provided
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

    def refresh_ue4ss_status(self, exe_path: str = None):
        """Fetches the loader and PalSchema states from disk and forwards them to the UI view."""
        if exe_path is None:
            exe_path = self.view.palworld_exe_picker.get_value()
            
        from utils.ue4ss_helper import get_ue4ss_status
        status_ue4ss = get_ue4ss_status(exe_path)
        self.view.update_ue4ss_ui(status_ue4ss)
        
        # Verify PalSchema status dynamically
        from utils.palschema_helper import get_palschema_status
        status_palschema = get_palschema_status(exe_path)
        self.view.update_palschema_ui(status_palschema)
        
    def manage_ue4ss(self, action: str):
        """Offloads task to the async engine runner."""
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
            # Also uninstall PalSchema to prevent unreferenced mod directory locks
            from utils.palschema_helper import uninstall_palschema
            await asyncio.to_thread(uninstall_palschema, exe_path, lambda m, e: None)
            await asyncio.to_thread(uninstall_ue4ss, exe_path, log_callback)
            
        self.refresh_ue4ss_status(exe_path)

    def manage_palschema(self, action: str):
        """Offloads PalSchema operations asynchronously to prevent UI thread lock."""
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

    def save_clicked(self, current_paths: dict, show_mapped: bool):
        self.settings.update(current_paths)
        self.settings["show_mapped"] = show_mapped
        save_settings(self.settings)

        # Restore stranded backups if the uproject path changed
        restore_palbaker_backup(self.settings.get("uproject"))

        # Run verification asynchronously
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
                        ft.TextButton("Cancel", on_click=on_no),
                        ft.TextButton("Yes, Install", on_click=on_yes, style=ft.ButtonStyle(color=ft.Colors.BLUE)),
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

            # Plugin Sync
            if reqs["needs_plugin_sync"] or reqs["needs_compile"]:
                plugin_names = ["PalBaker Editor Utilities"]
                plugins_text = "\n".join([f" • {name}" for name in plugin_names])
                content = ft.Column([
                    ft.Text("PalBaker requires the following custom C++ Editor Utility Plugin(s) to automatically generate Animation Blueprints via Python:"),
                    ft.Text(plugins_text, color=ft.Colors.CYAN_200, weight=ft.FontWeight.BOLD),
                    ft.Text("The plugin(s) are missing or outdated in your active Unreal Engine project.", color=ft.Colors.ORANGE_400),
                    ft.Text("Would you like to install and bind them to your ModKit now?", weight=ft.FontWeight.BOLD)
                ], tight=True)

                if ask_user_modal("Required Plugin Missing", content):
                    self.view.show_snackbar("Installing and verifying C++ plugin... (This may take a moment)", ft.Colors.WHITE)
                    success, msg = install_and_compile_plugin(self.settings["ue_root"], self.settings["uproject"])
                    color = ft.Colors.GREEN_400 if success else ft.Colors.RED_400
                    self.view.show_snackbar(msg, color)

            # Assets Sync
            missing_assets = reqs.get("missing_assets", [])
            if missing_assets:
                files_controls = [ft.Text(f" • {f}", size=12, color=ft.Colors.WHITE70) for f in missing_assets]
                files_list = ft.ListView(controls=files_controls, height=150, spacing=2, padding=10)
                
                content = ft.Column([
                    ft.Text("The following core framework assets are missing from your ModKit's Content directory:"),
                    ft.Container(content=files_list, border=ft.Border.all(1, ft.Colors.WHITE24), border_radius=5),
                    ft.Text("PalBaker requires these to cleanly bind Material Instances.\nWould you like to inject them into your project automatically?", weight=ft.FontWeight.BOLD)
                ], tight=True)

                if ask_user_modal("Missing Core Assets", content):
                    success, msg = inject_missing_assets(self.settings["uproject"])
                    color = ft.Colors.GREEN_400 if success else ft.Colors.RED_400
                    self.view.show_snackbar(msg, color)

            # Engine Configurations
            needs_remote_exec = reqs.get("needs_remote_exec_enable")
            needs_cooking_setup = reqs.get("needs_cooking_setup")

            if needs_remote_exec or needs_cooking_setup:
                reasons = []
                if needs_remote_exec:
                    reasons.append(" • Enable 'Python Remote Execution' (allows Python script orchestration)")
                if needs_cooking_setup:
                    reasons.append(" • Disable 'I/O Store' & 'Material Shader Sharing' (forces compilation to loose .uasset files)")

                content = ft.Column([
                    ft.Text("PalBaker needs to apply the following required configuration changes to your project's .ini files:"),
                    ft.Text("\n".join(reasons), color=ft.Colors.ORANGE_400),
                    ft.Text("Please ensure your work inside Unreal is saved before proceeding! Clicking 'Yes, Install' will write these settings and AUTOMATICALLY restart your Unreal Editor project.", weight=ft.FontWeight.BOLD)
                ], tight=True)

                if ask_user_modal("Project Configurations Required", content):
                    if needs_remote_exec:
                        enable_remote_execution_settings(self.settings["uproject"])
                    if needs_cooking_setup:
                        enable_cooking_settings(self.settings["uproject"])
                        
                    self.view.show_snackbar("Configurations successfully written. Restarting Unreal Editor...", ft.Colors.WHITE)
                    restart_success, restart_msg = restart_unreal_editor(self.settings["ue_root"], self.settings["uproject"])
                    color = ft.Colors.GREEN_400 if restart_success else ft.Colors.RED_400
                    self.view.show_snackbar(restart_msg, color)

            self.view.show_snackbar("Settings saved and verified!", ft.Colors.GREEN_400)
            self.on_save_callback()

        threading.Thread(target=verify_and_build, daemon=True).start()