# components/mods/altermatic_dialog.py
import flet as ft
import os
import subprocess
from components.altermatic.general_section import GeneralSection
from components.altermatic.traits_section import TraitsSection
from components.altermatic.materials_section import MaterialsSection
from components.altermatic.morphs_section import MorphsSection

# --- Version-Safe Dialog Handlers ---
def show_dialog_safe(page: ft.Page, dialog: ft.AlertDialog):
    """Bypasses version conflicts across Flet 0.22, 0.23, 0.85, and 1.0."""
    if hasattr(page, "show_dialog"):
        page.show_dialog(dialog)
    elif hasattr(page, "open"):
        page.open(dialog)
    else:
        page.dialog = dialog
        dialog.open = True
        page.update()

def close_dialog_safe(page: ft.Page, dialog: ft.AlertDialog):
    """Safely closes active modal dialogs on any Flet version."""
    if hasattr(page, "pop_dialog"):
        page.pop_dialog()
    elif hasattr(page, "close"):
        page.close(dialog)
    else:
        dialog.open = False
        page.update()


class AltermaticDialog:
    def __init__(self, page: ft.Page, settings: dict, traits_db: dict, on_save_callback, on_refresh_callback, on_delete_callback):
        self.page = page
        self.settings = settings
        self.on_save_callback = on_save_callback
        self.on_refresh_callback = on_refresh_callback
        self.on_delete_callback = on_delete_callback

        # Active runtime states
        self.current_character_id = ""
        self.editing_index = -1
        self.is_base = False

        # Instantiate React-style sub-components cleanly
        self.general_section = GeneralSection(
            on_skeleton_changed=self.on_skeleton_source_changed,
            on_open_blend=self.handle_open_blend_click,
            on_refresh_layout=self.handle_refresh_layout_click
        )
        self.traits_section = TraitsSection(traits_db=traits_db, on_update_callback=self.force_ui_update)
        self.materials_section = MaterialsSection(page=page, settings=settings)
        self.morphs_section = MorphsSection(page=page, settings=settings, on_update_callback=self.force_ui_update)

        # Configure action buttons
        self.cancel_btn = ft.TextButton("Cancel", on_click=self.close_dialog)
        self.delete_btn = ft.TextButton("Delete", on_click=self.handle_delete_click, style=ft.ButtonStyle(color=ft.Colors.RED_400))
        self.apply_btn = ft.TextButton("Apply Changes", on_click=self.save_variant)

        # --- DYNAMIC ACCORDION EXPANDER ---
        # Fixed: Changed "text" keyword to positional "Advanced Options" string
        self.advanced_toggle_button = ft.TextButton(
            "Advanced Options",
            icon=ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED,
            on_click=self.toggle_advanced_panel,
            style=ft.ButtonStyle(color=ft.Colors.CYAN_400)
        )
        
        # Group cosmetic and target-skin configs inside a hidden panel
        self.advanced_options_column = ft.Column([
            self.general_section.skin_name_input,
            self.materials_section.view,
            self.morphs_section.view
        ], spacing=15, visible=False)

        # Build AlertDialog
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Visual Altermatic Configurator"),
            actions=[
                self.cancel_btn,
                self.delete_btn,
                self.apply_btn
            ],
            content=ft.Column([
                self.general_section.view,
                self.traits_section.view,
                ft.Divider(height=10, color=ft.Colors.WHITE10),
                self.advanced_toggle_button,
                self.advanced_options_column
            ], scroll=ft.ScrollMode.ALWAYS, height=450, width=580)
        )
        self.page.dialog = self.dialog

    def show(self, character_id: str, index: int, variant_data: dict, blend_files: list[str], available_mats: list[str]):
        """Populates the fields and opens the modal visual builder."""
        self.editing_index = index
        self.current_character_id = character_id
        self.available_mats = available_mats
        self.is_base = variant_data.get("is_base", False)

        # 1. Populate General Section
        self.general_section.populate(character_id, blend_files, variant_data, self.is_base)

        # 2. Populate Trait Selection Section
        self.traits_section.populate(variant_data, self.is_base)

        # 3. Populate Material Selector & Morphs
        self.materials_section.populate(character_id, self.general_section.skeleton_source_dropdown.value, variant_data.get("MatReplace"), available_mats, self.is_base)
        self.morphs_section.populate(character_id, self.general_section.skeleton_source_dropdown.value, variant_data.get("MorphTarget", []), self.is_base)

        # Hide the delete button if editing the pinned canonical base mesh fallback
        self.delete_btn.visible = not self.is_base

        # Collapse advanced panel and reset toggle icon on open
        self.advanced_toggle_button.visible = not self.is_base
        self.advanced_options_column.visible = False
        self.advanced_toggle_button.icon = ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED

        # --- Dynamic Header Title Stripper ---
        clean_title = variant_data["label"]
        prefix = f"{character_id}_"
        if clean_title.startswith(prefix):
            clean_title = clean_title[len(prefix):]
        self.dialog.title = ft.Text(f"Configurator: {clean_title}")

        show_dialog_safe(self.page, self.dialog)

    def toggle_advanced_panel(self, e):
        """Animates and toggles the visibility of the advanced parameters accordion."""
        is_visible = not self.advanced_options_column.visible
        self.advanced_options_column.visible = is_visible
        self.advanced_toggle_button.icon = ft.Icons.KEYBOARD_ARROW_UP_ROUNDED if is_visible else ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED
        self.force_ui_update()

    def on_skeleton_source_changed(self, e):
        """Dynamic orchestrator update triggered when the selected skeleton source shifts."""
        selected_source = self.general_section.skeleton_source_dropdown.value
        self.materials_section.populate(self.current_character_id, selected_source, None, self.available_mats, self.is_base)
        self.morphs_section.populate(self.current_character_id, selected_source, [], self.is_base)
        self.force_ui_update()

    def force_ui_update(self):
        try:
            self.dialog.update()
        except Exception:
            pass

    def handle_open_blend_click(self, e):
        """Locates and natively launches the selected .blend file on disk in Blender GUI."""
        source = self.general_section.skeleton_source_dropdown.value
        if not source:
            return

        fmodel_root = self.settings.get("fmodel_output", "")
        if not fmodel_root:
            print("Altermatic Mod Builder: FModel Output Folder is not configured in settings.", flush=True)
            return
        
        # Resolve exact physical path of target .blend inside FModel exports directory
        if source == "base":
            blend_path = os.path.normpath(os.path.join(
                fmodel_root, "Exports", "Pal", "Content", "Pal", "Model", "Character", "Monster", 
                self.current_character_id, f"{self.current_character_id}.blend"
            ))
        else:
            blend_path = os.path.normpath(os.path.join(
                fmodel_root, "Exports", "Pal", "Content", "Palbaker", "Model", "Character", "Monster", 
                self.current_character_id, source
            ))

        blender_exe = self.settings.get("blender")
        
        # Diagnostics warning prints
        if not os.path.exists(blend_path):
            print(f"Altermatic Mod Builder Warning: Target .blend file not found on disk at: {blend_path}", flush=True)
        if not blender_exe or not os.path.exists(blender_exe):
            print(f"Altermatic Mod Builder Warning: Blender executable path is invalid or missing: {blender_exe}", flush=True)

        # Spawn Blender Popen Subprocess
        if os.path.exists(blend_path) and blender_exe and os.path.exists(blender_exe):
            try:
                subprocess.Popen([blender_exe, blend_path])
                print(f"Launched Blender directly for: {blend_path}", flush=True)
            except Exception as err:
                print(f"Failed to launch Blender: {err}", flush=True)

    def handle_refresh_layout_click(self, e):
        """Closes the dialog instantly and offloads the sync to your unbuffered background pipeline."""
        page = self.page
        close_dialog_safe(page, self.dialog)
        
        # Bubble up to trigger build_mod refresh_blend pipeline
        self.on_refresh_callback(self.current_character_id)

    def handle_delete_click(self, e):
        """Closes the dialog instantly and offloads the deletion to your staging background controller."""
        page = self.page
        close_dialog_safe(page, self.dialog)
        self.on_delete_callback(self.current_character_id, self.editing_index)

    def close_dialog(self, e):
        close_dialog_safe(self.page, self.dialog)

    def save_variant(self, e):
        general_values = self.general_section.get_values()
        
        if not general_values["label"] or not general_values["SkeletonSource"]:
            return

        # Resolve traits
        req_traits, pref_traits = self.traits_section.get_values()

        # Resolve materials & morphs
        from utils.altermatic_helper import get_virtual_path_for_file
        
        # Build physical path of sidecar on disk to resolve its virtual target directory
        root_dir = os.path.dirname(self.settings.get("uproject", ""))
        target_dir = os.path.join(
            root_dir, "Content", "Palbaker", "Model", "Character", "Monster", 
            self.current_character_id
        )
        mat_resolved_dir = get_virtual_path_for_file(os.path.join(target_dir, "dummy_sidecar_blend.json"))

        mat_replaces = []
        slots = self.materials_section.get_slots_for_skeleton(self.current_character_id, general_values["SkeletonSource"])

        for idx, dropdown in self.materials_section.active_material_dropdowns.items():
            if dropdown.value and dropdown.value != "default":
                resolved_mat_path = f"{mat_resolved_dir}/{dropdown.value}"
                mat_replaces.append({
                    "Index": str(idx),
                    "MatPath": resolved_mat_path,
                    "SlotName": slots[idx]
                })

        morphs = self.morphs_section.get_values()

        variant_data = {
            "label": "base" if self.is_base else general_values["label"],
            "CharacterID": self.current_character_id,
            "SkeletonSource": general_values["SkeletonSource"],
            "Gender": general_values["Gender"],
            "IsRarePal": general_values["IsRarePal"],
            "SkinName": general_values["SkinName"],
            "ReqTrait": req_traits,
            "PrefTrait": pref_traits,
            "MatReplace": mat_replaces,
            "MorphTarget": morphs,
            "is_base": self.is_base,
            "base_type": general_values.get("base_type", "vanilla")  # Capture base type (vanilla vs custom)
        }

        close_dialog_safe(self.page, self.dialog)
        self.on_save_callback(self.editing_index, variant_data)