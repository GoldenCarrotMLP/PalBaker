# components/mods/mod_card.py
import flet as ft
import os
import sys
import subprocess
import glob
import re
import threading
import time
from components.mods.mod_details import ModDetails

def open_folder(path: str):
    """Opens a directory path in the operating system's native file explorer."""
    if path and os.path.exists(path):
        if os.name == 'nt':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(['xdg-open', path])

def open_file_in_explorer(file_path: str):
    """Opens the directory containing the file and highlights/selects the file if supported."""
    if not file_path:
        return
    if os.path.exists(file_path):
        if os.name == 'nt':
            subprocess.run(['explorer.exe', f'/select,{os.path.normpath(file_path)}'])
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', '-R', file_path])
        else:
            parent_dir = os.path.dirname(file_path)
            if os.path.exists(parent_dir):
                subprocess.Popen(['xdg-open', parent_dir])

def safe_update(control):
    """Safely updates a Flet control, bypassing the RuntimeError if it is not mounted yet."""
    try:
        control.update()
    except Exception:
        pass

class ModItem:
    def __init__(self, mod_data: dict, on_action_click, on_cancel_click, on_pick_icon, on_pick_audio, on_play_audio, on_clear_audio,
                 on_toggle_altermatic, on_add_variant, on_edit_variant, on_delete_variant,
                 is_building: bool, show_mapped: bool):
        self.mod_data = mod_data
        self.on_action_click = on_action_click
        self.on_cancel_click = on_cancel_click
        self.on_pick_icon = on_pick_icon
        self.on_pick_audio = on_pick_audio
        self.on_play_audio = on_play_audio
        self.on_clear_audio = on_clear_audio
        
        # Altermatic custom callbacks
        self.on_toggle_altermatic = on_toggle_altermatic
        self.on_add_variant = on_add_variant
        self.on_edit_variant = on_edit_variant
        self.on_delete_variant = on_delete_variant
        
        self.is_building = is_building
        self.show_mapped = show_mapped

        # Progress tracking variables
        self.import_total_steps = 1
        self.import_current_step = 0

        # Reusable Text node
        self.name_text = ft.Text(
            value=self.get_display_name(),
            weight=ft.FontWeight.BOLD,
            size=16
        )

        # Dropdown Toggle
        self.details_visible = False
        self.chevron = ft.IconButton(
            icon=ft.Icons.KEYBOARD_ARROW_DOWN,
            on_click=self.toggle_details,
            icon_size=20,
            disabled=not mod_data["has_fmodel"]  # Block details on unextracted Pals
        )

        badge_controls = []
        for text, color_hex in mod_data["badges"]:
            if text == "UNEXTRACTED":
                tooltip_msg = "This Pal mesh and texture database resides purely inside your game archives. Click Extract to build its workspace folders."
            elif text == "RAW":
                tooltip_msg = "FModel files extracted, but no Blender (.blend) file has been created yet."
            elif text == "SOURCE":
                tooltip_msg = "Blender (.blend) source file detected. Mod is actively being worked on."
            elif text == "UE ASSETS":
                tooltip_msg = "Warning: Files have been manually modified inside Unreal Engine since your last Push!"
            elif text == "MODIFIED":
                tooltip_msg = "Warning: Files have been manually modified inside Unreal Engine since your last Push!"
            elif text == "SRC CHANGED":
                tooltip_msg = "Source files (Blender/textures) have been edited since your last Push! It is recommended to run 'Push & Cook & Pack'."
            elif text == "ALTERMATIC":
                tooltip_msg = "Altermatic dynamic variants are active for this Pal."
            else:
                tooltip_msg = ""

            badge_controls.append(
                ft.Container(
                    content=ft.Text(text, size=10, weight=ft.FontWeight.BOLD),
                    bgcolor=color_hex, 
                    padding=ft.Padding(left=6, right=6, top=2, bottom=2), 
                    border_radius=4,
                    tooltip=tooltip_msg
                )
            )

        status_colors = {
            "Packed": ft.Colors.GREEN_400,
            "Packed with Errors": ft.Colors.YELLOW_400,
            "Outdated": ft.Colors.ORANGE_400,
            "Unpacked": ft.Colors.RED_400,
            "Unextracted": ft.Colors.RED_400
        }
        status_color = status_colors.get(mod_data["pak_status"], ft.Colors.RED_400)

        self.update_primary_button_config()

        self.primary_button = ft.ElevatedButton(
            self.primary_text, 
            icon=self.primary_icon, 
            on_click=self.handle_button_click, 
            disabled=self.is_building or self.primary_action == "none"
        )

        overflow_menu = ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT,
            items=[
                ft.PopupMenuItem(content=ft.Text("Push to Unreal"), on_click=lambda e: on_action_click(self.mod_data, "push"), disabled=not self.mod_data["has_fmodel"] or not self.mod_data.get("has_blend", False)),
                ft.PopupMenuItem(content=ft.Text("Cook & Pack (Skip Import)"), on_click=lambda e: on_action_click(self.mod_data, "cook"), disabled=not self.mod_data["has_ue"]),
                ft.PopupMenuItem(content=ft.Text("Push & Cook & Pack"), on_click=lambda e: on_action_click(self.mod_data, "full"), disabled=not self.mod_data["has_fmodel"] or not self.mod_data.get("has_blend", False)),
                ft.PopupMenuItem(content=ft.Text("Generate Sources"), on_click=lambda e: on_action_click(self.mod_data, "decompile"), disabled=not self.mod_data["has_ue"])
            ]
        )

        # --- DYNAMIC AVATAR RESOLUTION ---
        # Display the custom/extracted Pal icon directly on the main card list-view row.
        # If none exist, gracefully fall back to a proportional folder container.
        if mod_data.get("has_icon") and mod_data.get("icon_path"):
            self.avatar = ft.Container(
                content=ft.Image(src=mod_data["icon_path"], width=32, height=32, fit=ft.BoxFit.CONTAIN),
                width=32,
                height=32,
                border_radius=6,
                border=ft.Border.all(1, ft.Colors.WHITE10),
                bgcolor=ft.Colors.WHITE10
            )
        else:
            self.avatar = ft.Container(
                content=ft.Icon(ft.Icons.FOLDER, color=ft.Colors.BLUE_200, size=20),
                width=32,
                height=32,
                alignment=ft.Alignment.CENTER  # FIXED: Replaced lowercase alias with class-constant
            )

        row_controls: list[ft.Control] = [
            self.chevron,
            self.avatar,  
            self.name_text,
            ft.Row(badge_controls, spacing=5),
            ft.Container(expand=True),
            ft.Text(mod_data["pak_status"], color=status_color, size=12, width=120, text_align=ft.TextAlign.RIGHT),
            self.primary_button,
            overflow_menu
        ]
        self.main_row = ft.Row(controls=row_controls)

        # --- Progress Bar UI ---
        self.progress_bar = ft.ProgressBar(value=0.0, color=ft.Colors.CYAN_400, bgcolor=ft.Colors.WHITE10)
        self.status_text = ft.Text("Waiting...", size=12, color=ft.Colors.WHITE54, italic=True)
        self.progress_container = ft.Column(
            controls=[
                ft.Divider(height=1, color=ft.Colors.WHITE24),
                self.progress_bar,
                self.status_text
            ],
            visible=False,
            spacing=5
        )

        # Initialize Dropdown Details with forward mappings
        self.details = ModDetails(
            mod_data=mod_data, 
            on_pick_icon=self.on_pick_icon,
            on_pick_audio=self.on_pick_audio,
            on_play_audio=self.on_play_audio,
            on_clear_audio=self.on_clear_audio,
            on_toggle_altermatic=self.on_toggle_altermatic,
            on_add_variant=self.on_add_variant,
            on_edit_variant=self.on_edit_variant,
            on_delete_variant=self.on_delete_variant
        )
        self.details_container = ft.Container(content=self.details.view, visible=False)

        self.container = ft.Container(
            content=ft.Column([self.main_row, self.progress_container, self.details_container], spacing=0),
            padding=10,
            border=ft.Border.all(1, ft.Colors.WHITE24),
            border_radius=8,
            animate=ft.Animation(500, ft.AnimationCurve.EASE_OUT) 
        )

        self.view = ft.ContextMenu(
            content=self.container,
            secondary_items=[
                ft.PopupMenuItem(content=ft.Text("Open source in file explorer"), on_click=lambda e: open_folder(self.mod_data["fmodel_path"]), disabled=not self.mod_data["has_fmodel"]),
                ft.PopupMenuItem(content=ft.Text("Open unreal assets in file explorer"), on_click=lambda e: open_folder(self.mod_data["ue_path"]), disabled=not self.mod_data["has_ue"]),
                ft.PopupMenuItem(
                    content=ft.Text("Open PAK in file explorer"), 
                    on_click=lambda e: open_file_in_explorer(self.mod_data.get("pak_path", "")), 
                    disabled=self.mod_data.get("pak_status") != "Packed"
                ),
                ft.PopupMenuItem(
                    content=ft.Text("Show in Unreal Content Browser"),
                    on_click=lambda e: on_action_click(self.mod_data, "browse_unreal"),
                    disabled=not self.mod_data["has_ue"]
                )
            ]
        ) # type: ignore

    def toggle_details(self, e):
        if not self.mod_data["has_fmodel"]:
            return
            
        self.details_visible = not self.details_visible
        self.details_container.visible = self.details_visible
        self.chevron.icon = ft.Icons.KEYBOARD_ARROW_UP if self.details_visible else ft.Icons.KEYBOARD_ARROW_DOWN
        safe_update(self.view)

    def handle_button_click(self, e):
        if self.is_building:
            if self.on_cancel_click:
                self.on_cancel_click()
        elif self.primary_action == "extract_pal":
            self.on_action_click(self.mod_data, "extract_pal")
        elif self.primary_action == "create_blend":
            self.on_action_click(self.mod_data, "create_blend")
        elif self.primary_action == "open_folder":
            open_folder(self.mod_data["fmodel_path"])
        else:
            self.on_action_click(self.mod_data, self.primary_action)

    def update_primary_button_config(self):
        """Determines the standard text and action for the button based on badges."""
        if self.mod_data["pak_status"] == "Unextracted":
            self.primary_text = "Extract Pal"
            self.primary_action = "extract_pal"
            self.primary_icon = ft.Icons.DOWNLOAD_ROUNDED
        elif self.mod_data["has_ue"]:
            if self.mod_data.get("source_modified", False):
                self.primary_text = "Push & Cook & Pack"
                self.primary_action = "full"
                self.primary_icon = ft.Icons.PUBLISH
            else:
                self.primary_text = "Cook & Pack"
                self.primary_action = "cook"
                self.primary_icon = ft.Icons.FAST_FORWARD
        elif self.mod_data["has_fmodel"]:
            if not self.mod_data.get("has_blend", False):
                self.primary_text = "Create .blend file"
                self.primary_action = "create_blend"
                self.primary_icon = ft.Icons.CREATE_NEW_FOLDER
            else:
                self.primary_text = "Push to Unreal"
                self.primary_action = "push"
                self.primary_icon = ft.Icons.CLOUD_UPLOAD
        else:
            self.primary_text = "Unavailable"
            self.primary_action = "none"
            self.primary_icon = ft.Icons.BLOCK

    def get_display_name(self) -> str:
        return str(self.mod_data["localized_name"]) if self.show_mapped else str(self.mod_data["name"])

    def set_show_mapped(self, show_mapped: bool):
        self.show_mapped = show_mapped
        self.name_text.value = self.get_display_name()
        safe_update(self.name_text)

    def set_state(self, global_building: bool, is_active_target: bool = False, success: bool | None = None):
        """Changes the visual state of the item based on what is building."""
        self.is_building = global_building
        self.update_primary_button_config()

        if is_active_target:
            fmodel_path = self.mod_data["fmodel_path"]
            if os.path.exists(fmodel_path):
                pngs = len(glob.glob(os.path.join(fmodel_path, "*.png")))
                jsons = len(glob.glob(os.path.join(fmodel_path, "MI_*.json")))
                fbx = 1 if glob.glob(os.path.join(fmodel_path, "*.fbx")) else 0
                self.import_total_steps = pngs + jsons + fbx + 1
            else:
                self.import_total_steps = 1
            
            self.import_current_step = 0
            self.progress_container.visible = True
            self.progress_bar.value = 0.0
            self.status_text.value = "Starting pipeline..."
            self.container.border = ft.Border.all(1, ft.Colors.CYAN_700)
            
            # Switch primary button to Cancel
            setattr(self.primary_button, "text", "Cancel")
            self.primary_button.icon = ft.Icons.CANCEL
            self.primary_button.style = ft.ButtonStyle(color=ft.Colors.RED_400)
            self.primary_button.disabled = False
        else:
            self.progress_container.visible = False
            setattr(self.primary_button, "text", self.primary_text)
            self.primary_button.icon = self.primary_icon
            self.primary_button.style = None
            self.primary_button.disabled = global_building or self.primary_action == "none"
            
            if success is True:
                self.container.border = ft.Border.all(1, ft.Colors.GREEN_500)
                def reset_border():
                    time.sleep(2.5)
                    self.container.border = ft.Border.all(1, ft.Colors.WHITE24)
                    safe_update(self.view)
                threading.Thread(target=reset_border, daemon=True).start()
            elif success is False:
                self.container.border = ft.Border.all(1, ft.Colors.RED_500)
                def reset_border():
                    time.sleep(2.5)
                    self.container.border = ft.Border.all(1, ft.Colors.WHITE24)
                    safe_update(self.view)
                threading.Thread(target=reset_border, daemon=True).start()
                
        safe_update(self.view)

    def update_progress(self, line: str, flush: bool = True):
        """Value parser for the progress bar."""
        line = line.strip()
        if not line: return
        
        if "Running headless Blender" in line:
            self.progress_bar.value = 0.05
            self.status_text.value = "[1/4] Running Blender (Exporting FBX)..."
            
        elif "Connecting to Open Unreal Engine" in line:
            self.progress_bar.value = 0.15
            self.status_text.value = "[2/4] Connecting to Unreal Engine..."
        elif "Importing texture:" in line or "Importing skeletal mesh:" in line or "Creating material instance:" in line or "Linking Materials" in line:
            self.import_current_step += 1
            progress = 0.15 + (0.30 * (self.import_current_step / max(1, self.import_total_steps)))
            self.progress_bar.value = min(0.45, progress)
            self.status_text.value = f"[2/4] Importing Assets into Unreal ({self.import_current_step}/{self.import_total_steps})...."
            
        elif "Cooking Target Folders" in line:
            self.progress_bar.value = 0.45
            self.status_text.value = "[3/4] Preparing to Cook Assets..."
            
        elif "LogCook: Display: Cooked packages" in line:
            match = re.search(r"Cooked packages (\d+) Packages Remain (\d+)", line)
            if match:
                cooked = int(match.group(1))
                remain = int(match.group(2))
                total = cooked + remain
                if total > 0:
                    sub_progress = cooked / total
                    self.progress_bar.value = 0.45 + (0.45 * sub_progress)
                    self.status_text.value = f"[3/4] Cooking Assets ({cooked}/{total} packages)..."
                    
        elif "Preparing Pak" in line:
            self.progress_bar.value = 0.90
            self.status_text.value = "[4/4] Packing Cooked Assets..."
        elif "Building final PAK" in line:
            self.progress_bar.value = 0.95
            self.status_text.value = "[4/4] Generating .pak file..."
            
        if flush:
            safe_update(self.view)