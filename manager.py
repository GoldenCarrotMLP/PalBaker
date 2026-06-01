# manager.py (Top Imports)
import flet as ft
from utils.config import load_settings, save_settings
from utils.autofill_helper import detect_unreal_engine, detect_palworld_exe, find_blender_versions
from views.settings_view import SettingsView  # UPDATED: Import from views
from views.mods_view import ModsView          # UPDATED: Import from views
from utils.builder.config_helper import restore_palbaker_backup
import flet as ft

def main(page: ft.Page):
    page.title = "Palworld Baker Mod Manager"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 900
    page.window.height = 800
    page.padding = 20

    # Load state
    settings = load_settings()

    # FIX: Automatically restore any stranded backups immediately on UI launch
    uproject_path = settings.get("uproject")
    if isinstance(uproject_path, str):
        restore_palbaker_backup(uproject_path)

    # Mount decoupled UI controllers
    mods_view = ModsView(page, settings)
    settings_view = SettingsView(page, settings, on_save_callback=mods_view.refresh_mods)

    # Autofill settings if empty
    changed = False
    
    # Unreal Engine
    if not settings.get("ue_root"):
        detected_ue = detect_unreal_engine()
        if detected_ue:
            print(f"Auto-detected Unreal Engine location as: '{detected_ue}'")
            settings["ue_root"] = detected_ue
            changed = True
        else:
            print("Could not auto-detect Unreal Engine location.")
    else:
        print(f"Unreal Engine location already defined as: '{settings.get('ue_root')}' - skipping autofill.")
    
    # Palworld
    if not settings.get("palworld_exe"):
        detected_pal = detect_palworld_exe()
        if detected_pal:
            print(f"Auto-detected Palworld.exe location as: '{detected_pal}'")
            settings["palworld_exe"] = detected_pal
            changed = True
        else:
            print("Could not auto-detect Palworld.exe location.")
    else:
        print(f"Palworld.exe location already defined as: '{settings.get('palworld_exe')}' - skipping autofill.")
            
    # Blender Autofill
    blender_versions = find_blender_versions()
    blender_path = settings.get("blender")
    if blender_path and blender_path != "blender":
        print(f"Blender location already defined as: '{blender_path}' - skipping autofill.")
    elif len(blender_versions) == 1:
        print(f"Auto-detected single Blender installation: '{blender_versions[0]}'")
        settings["blender"] = blender_versions[0]
        changed = True
    elif len(blender_versions) > 1:
        print(f"Auto-detected multiple Blender paths: {blender_versions}")
    else:
        print("Could not auto-detect any Blender installations.")
    
    if changed:
        save_settings(settings)
        settings_view.update_settings(settings)

    # FIX: Automatically restore any stranded backups immediately on UI launch

    # Flet 0.85+ Tabs Architecture
    tab_bar = ft.TabBar(
        tabs=[
            ft.Tab(label="Manager", icon=ft.Icons.WIDGETS),
            ft.Tab(label="Settings", icon=ft.Icons.SETTINGS),
        ]
    )

    tab_view = ft.TabBarView(
        expand=True,
        controls=[
            mods_view.view,       # Mount the layout columns here
            settings_view.view,   # Mount the layout columns here
        ]
    )

    tabs_controller = ft.Tabs(
        length=2,
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
            print(f"User picked Blender path: '{selected}'")
            settings["blender"] = selected
            save_settings(settings)
            settings_view.update_settings(settings) # Added this
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

if __name__ == "__main__":
    ft.run(main)
