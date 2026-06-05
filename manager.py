# manager.py
import flet as ft
from utils.config import load_settings, save_settings
from utils.autofill_helper import detect_unreal_engine, detect_palworld_exe, find_blender_versions
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

    page.mods_view = mods_view
    page.creator_view = creator_view

    # Autofill settings if empty
    changed = False
    
    # Unreal Engine
    if not settings.get("ue_root"):
        detected_ue = detect_unreal_engine()
        if detected_ue:
            print(f"Auto-detected Unreal Engine location as: '{detected_ue}'")
            settings["ue_root"] = detected_ue
            changed = True
    
    # Palworld
    if not settings.get("palworld_exe"):
        detected_pal = detect_palworld_exe()
        if detected_pal:
            print(f"Auto-detected Palworld.exe location as: '{detected_pal}'")
            settings["palworld_exe"] = detected_pal
            changed = True
            
    # Blender Autofill
    blender_versions = find_blender_versions()
    blender_path = settings.get("blender")
    if blender_path and blender_path != "blender":
        pass
    elif len(blender_versions) == 1:
        settings["blender"] = blender_versions[0]
        changed = True
    
    if changed:
        save_settings(settings)
        settings_view.update_settings(settings)

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
    
    # Prompt for Blender version if multiple found
    blender_path = settings.get("blender")
    if len(blender_versions) > 1 and (not blender_path or blender_path == "blender"):
        def on_blender_selected(e):
            selected = e.control.data
            settings["blender"] = selected
            save_settings(settings)
            settings_view.update_settings(settings) 
            dlg.open = False
            page.update()
            page.overlay.append(ft.SnackBar(ft.Text(f"Blender set to: {selected}")))
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Multiple Blender Versions Detected"),
            content=ft.Column(
                [ft.Text("Please select the Blender version to use:")] + 
                [ft.ElevatedButton(content=ft.Text(v), data=v, on_click=on_blender_selected) for v in blender_versions]
            )
        )
        page.show_dialog(dlg)

    mods_view.refresh_mods()
    creator_view.refresh_pals() 

    # --- UPGRADED CONSOLIDATED STARTUP VERIFICATION HOOK ---
    # Tracks both wild spawner lookup caches on launch to trigger dynamic rebuilds.
    map_path = os.path.join(os.path.dirname(__file__), "pal_names_map.json")
    skills_cache = os.path.join(os.path.dirname(__file__), "deps", "active_skills_cache.json")
    passives_cache = os.path.join(os.path.dirname(__file__), "deps", "passive_skills_cache.json")
    partner_cache = os.path.join(os.path.dirname(__file__), "deps", "partner_skills_cache.json")
    params_cache = os.path.join(os.path.dirname(__file__), "deps", "monster_parameter_cache.json")
    learnset_cache = os.path.join(os.path.dirname(__file__), "deps", "waza_master_level_cache.json")
    spawners_cache = os.path.join(os.path.dirname(__file__), "deps", "monster_spawners_cache.json")
    default_map_cache = os.path.join(os.path.dirname(__file__), "deps", "monster_spawners_default_map.json")

    if not all(os.path.exists(p) for p in [map_path, skills_cache, passives_cache, partner_cache, params_cache, learnset_cache, spawners_cache, default_map_cache]):
        mods_view.prompt_build_database()

if __name__ == "__main__":
    ft.run(main)