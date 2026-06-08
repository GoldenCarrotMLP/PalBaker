# manager.py
import flet as ft  # type: ignore
from utils.config import load_settings, save_settings
from views.settings_view import SettingsView  
from views.mods_view import ModsView          
from views.creator_view import CreatorView 
from utils.builder.config_helper import restore_palbaker_backup
import os

def main(page: ft.Page):
    page.title = "Palworld Baker Mod Manager"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 900
    page.window.height = 800
    page.padding = 20

    # Load state
    settings = load_settings()

    uproject_path = settings.get("uproject")
    if isinstance(uproject_path, str):
        restore_palbaker_backup(uproject_path)

    # Mount decoupled UI views
    mods_view = ModsView(page, settings)
    creator_view = CreatorView(page, settings) 
    settings_view = SettingsView(
        page, 
        settings, 
        on_save_callback=mods_view.refresh_mods,
        on_rebuild_db_callback=mods_view.prompt_build_database
    )

    page.mods_view = mods_view  # type: ignore
    page.creator_view = creator_view  # type: ignore

    tab_bar = ft.TabBar(
        tabs=[
            ft.Tab(label="Manager", icon=ft.Icons.WIDGETS),
            ft.Tab(label="Pal Creator", icon=ft.Icons.CREATE),
            ft.Tab(label="Settings", icon=ft.Icons.SETTINGS),
        ]
    )

    tab_view = ft.TabBarView(
        expand=True,
        controls=[
            mods_view.view,       
            creator_view.view, 
            settings_view.view,   
        ]
    )

    tabs_controller = ft.Tabs(
        length=3, 
        selected_index=0,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                tab_bar,
                tab_view
            ]
        )
    )

    page.add(tabs_controller)

    mods_view.refresh_mods()
    creator_view.refresh_pals() 

    # --- UPGRADED CONSOLIDATED STARTUP VERIFICATION HOOK ---
    async def run_startup_checks():
        try:
            nonlocal settings
            changed = False
            
            # Asynchronously autodetect if settings are empty, bypassing blocking synchronous I/O scans on startup!
            if not settings.get("ue_root") or not settings.get("palworld_exe") or not settings.get("blender") or settings.get("blender") == "blender":
                detect_res = await mods_view.cli.env_autodetect()
                if detect_res.get("status") == "success":
                    if not settings.get("ue_root") and detect_res.get("ue_root"):
                        settings["ue_root"] = detect_res["ue_root"]
                        changed = True
                    if not settings.get("palworld_exe") and detect_res.get("palworld_exe"):
                        settings["palworld_exe"] = detect_res["palworld_exe"]
                        changed = True
                    
                    blender_vers = detect_res.get("blender_versions", [])
                    blender_path = settings.get("blender")
                    
                    # Handle multiple Blender versions asynchronously
                    if len(blender_vers) > 1 and (not blender_path or blender_path == "blender"):
                        def on_blender_selected(e):
                            selected = e.control.data
                            settings["blender"] = selected
                            save_settings(settings)
                            settings_view.update_settings(settings) 
                            dlg.open = False
                            page.update()
                            page.overlay.append(ft.SnackBar(ft.Text(f"Blender set to: {selected}")))
                            page.update()

                        controls_list: list[ft.Control] = [ft.Text("Please select the Blender version to use:")]
                        for v in blender_vers:
                            controls_list.append(ft.ElevatedButton(content=ft.Text(v), data=v, on_click=on_blender_selected))

                        dlg = ft.AlertDialog(
                            title=ft.Text("Multiple Blender Versions Detected"),
                            content=ft.Column(controls=controls_list)
                        )
                        page.show_dialog(dlg)
                    elif (not blender_path or blender_path == "blender") and len(blender_vers) == 1:
                        settings["blender"] = blender_vers[0]
                        changed = True
            
            if changed:
                save_settings(settings)
                settings_view.update_settings(settings)
                
            status = await mods_view.cli.env_verify()
            map_path = os.path.join(os.path.dirname(__file__), "pal_names_map.json")
            skills_cache = os.path.join(os.path.dirname(__file__), "deps", "active_skills_cache.json")
            if not os.path.exists(map_path) or not os.path.exists(skills_cache) or status.get("needs_db_build"):
                mods_view.prompt_build_database()
        except Exception:
            pass

    page.run_task(run_startup_checks)

if __name__ == "__main__":
    ft.run(main)
