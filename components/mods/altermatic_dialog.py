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
    if getattr(dialog, "open", False):
        return
        
    dialog.open = True
    # Reset title color if it was made transparent by the closing hack
    if hasattr(dialog, "title") and isinstance(dialog.title, ft.Text):
        dialog.title.color = None
        
    try:
        if hasattr(page, "show_dialog"):
            page.show_dialog(dialog)
        elif hasattr(page, "open"):
            page.open(dialog)
        else:
            page.dialog = dialog
            page.update()
    except RuntimeError as e:
        if "already opened" not in str(e).lower():
            raise

def close_dialog_safe(page: ft.Page, dialog: ft.AlertDialog):
    dialog.open = False
    
    # THE HACK: Mutate a dummy visual property to guarantee Flet's diff engine triggers a redraw
    if hasattr(dialog, "title") and isinstance(dialog.title, ft.Text):
        dialog.title.color = ft.Colors.TRANSPARENT
        
    try:
        dialog.update()
    except Exception:
        pass

    try:
        if hasattr(page, "close"):
            page.close(dialog)
        elif hasattr(page, "pop_dialog"):
            page.pop_dialog()
    except Exception:
        pass
        
    try:
        page.update()
    except Exception:
        pass


class AltermaticEditDialog:
    def __init__(self, page: ft.Page, settings: dict, traits_db: dict, on_save_callback, on_refresh_callback, on_delete_callback):
        self.page = page
        self.settings = settings
        self.on_save_callback = on_save_callback
        self.on_refresh_callback = on_refresh_callback
        self.on_delete_callback = on_delete_callback

        self.current_character_id = ""
        self.editing_index = -1
        self.is_base = False
        self.current_category = "Monster"  

        self.general_section = GeneralSection(
            on_skeleton_changed=self.on_skeleton_source_changed,
            on_open_blend=self.handle_open_blend_click,
            on_refresh_layout=self.handle_refresh_layout_click
        )
        self.traits_section = TraitsSection(traits_db=traits_db, on_update_callback=self.force_ui_update)
        self.materials_section = MaterialsSection(page=page, settings=settings)
        self.morphs_section = MorphsSection(page=page, settings=settings, on_update_callback=self.force_ui_update)

        self.cancel_btn = ft.TextButton("Cancel", on_click=self.close_dialog)
        self.delete_btn = ft.TextButton("Delete", on_click=self.handle_delete_click, style=ft.ButtonStyle(color=ft.Colors.RED_400))
        self.apply_btn = ft.TextButton("Apply Changes", on_click=self.save_variant)

        self.advanced_toggle_button = ft.TextButton(
            "Advanced Options",
            icon=ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED,
            on_click=self.toggle_advanced_panel,
            style=ft.ButtonStyle(color=ft.Colors.CYAN_400)
        )
        
        self.advanced_options_column = ft.Column([
            self.general_section.skin_name_input,
            self.materials_section.view,
            self.morphs_section.view
        ], spacing=15, visible=False)

        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Visual Altermatic Configurator"),
            actions=[self.cancel_btn, self.delete_btn, self.apply_btn],
            content=ft.Column([
                self.general_section.view,
                self.traits_section.view,
                ft.Divider(height=10, color=ft.Colors.WHITE10),
                self.advanced_toggle_button,
                self.advanced_options_column
            ], scroll=ft.ScrollMode.ALWAYS, height=450, width=580)
        )

    def show(self, character_id: str, index: int, variant_data: dict, blend_files: list[str], available_mats: list[str], category: str = "Monster"):
        self.editing_index = index
        self.current_character_id = character_id
        self.available_mats = available_mats
        self.is_base = variant_data.get("is_base", False)
        self.current_category = category  
        
        # Reset visual states
        self.apply_btn.text = "Apply Changes"
        self.delete_btn.text = "Delete"
        self.apply_btn.disabled = False
        self.delete_btn.disabled = False

        self.general_section.populate(character_id, blend_files, variant_data, self.is_base)
        self.traits_section.populate(variant_data, self.is_base)
        
        selected_source = self.general_section.skeleton_source_dropdown.value
        self.materials_section.populate(character_id, selected_source, variant_data, available_mats, self.is_base, self.current_category)
        self.morphs_section.populate(character_id, selected_source, variant_data.get("MorphTarget", []), self.is_base)

        self.delete_btn.visible = not self.is_base

        self.advanced_toggle_button.visible = not self.is_base
        self.advanced_options_column.visible = False
        self.advanced_toggle_button.icon = ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED

        clean_title = variant_data.get("label", "")
        prefix = f"{character_id}_"
        if clean_title.startswith(prefix):
            clean_title = clean_title[len(prefix):]
        self.dialog.title = ft.Text(f"Configurator: {clean_title}")

        show_dialog_safe(self.page, self.dialog)
        self.force_ui_update()

    def toggle_advanced_panel(self, e):
        is_visible = not self.advanced_options_column.visible
        self.advanced_options_column.visible = is_visible
        self.advanced_toggle_button.icon = ft.Icons.KEYBOARD_ARROW_UP_ROUNDED if is_visible else ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED
        self.force_ui_update()

    def on_skeleton_source_changed(self, e):
        selected_source = self.general_section.skeleton_source_dropdown.value
        is_base_source = (selected_source == "base")
        self.general_section.open_blend_button.disabled = is_base_source
        self.general_section.refresh_layout_button.disabled = is_base_source

        self.materials_section.populate(self.current_character_id, selected_source, None, self.available_mats, self.is_base, self.current_category)
        self.morphs_section.populate(self.current_character_id, selected_source, [], self.is_base)
        self.force_ui_update()

    def force_ui_update(self):
        try: self.dialog.update()
        except Exception: pass

    def handle_open_blend_click(self, e):
        source = self.general_section.skeleton_source_dropdown.value
        if not source: return

        fmodel_root = self.settings.get("fmodel_output", "")
        if not fmodel_root:
            print("Altermatic Mod Builder: Workspace Folder is not configured in settings.", flush=True)
            return
        
        if source == "base":
            blend_path = os.path.normpath(os.path.join(
                fmodel_root, "Exports", "Pal", "Content", "Pal", "Model", "Character", self.current_category,
                self.current_character_id, f"{self.current_character_id}.blend"
            ))
        else:
            blend_path = os.path.normpath(os.path.join(
                fmodel_root, "Exports", "Pal", "Content", "Palbaker", "Model", "Character", self.current_category,
                self.current_character_id, source
            ))

        blender_exe = self.settings.get("blender")
        if os.path.exists(blend_path) and blender_exe and os.path.exists(blender_exe):
            try: subprocess.Popen([blender_exe, blend_path])
            except Exception as err: print(f"Failed to launch Blender: {err}", flush=True)

    def handle_refresh_layout_click(self, e):
        close_dialog_safe(self.page, self.dialog)
        self.on_refresh_callback(self.current_character_id)

    def handle_delete_click(self, e):
        self.delete_btn.disabled = True
        self.delete_btn.text = "Closing..."
        self.apply_btn.disabled = True
        self.force_ui_update()
        
        close_dialog_safe(self.page, self.dialog)
        self.on_delete_callback(self.current_character_id, self.editing_index)

    def close_dialog(self, e):
        close_dialog_safe(self.page, self.dialog)

    def save_variant(self, e):
        general_values = self.general_section.get_values()
        if not general_values["label"] or not general_values["SkeletonSource"]:
            return

        # UI Hack: Mutate state to force Flet diff redraw instantly
        self.apply_btn.disabled = True
        self.apply_btn.text = "Saving..."
        self.delete_btn.disabled = True
        self.force_ui_update()

        req_traits, pref_traits = self.traits_section.get_values()
        
        from utils.altermatic_helper import get_virtual_path_for_file
        root_dir = os.path.dirname(self.settings.get("uproject", ""))
        target_dir = os.path.join(root_dir, "Content", "Palbaker", "Model", "Character", self.current_category, self.current_character_id)
        mat_resolved_dir = get_virtual_path_for_file(os.path.join(target_dir, "dummy_sidecar_blend.json"))

        mat_replaces = []
        slots = self.materials_section.get_slots_for_skeleton(self.current_character_id, general_values["SkeletonSource"], self.current_category)

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
            "is_base": self.is_base
        }

        # Lock UI, close immediately, dispatch to background
        close_dialog_safe(self.page, self.dialog)
        self.on_save_callback(self.editing_index, variant_data)


class AltermaticAddDialog:
    def __init__(self, page: ft.Page):
        self.page = page
        self.on_confirm = None
        
        self.label_input = ft.TextField(label="New Variant Name/Label", hint_text="e.g., SFW_Bikini_T-Shirt")
        self.custom_mesh_switch = ft.Switch(label="Create a custom .blend file for this variant?", value=True)
        self.clone_source_dropdown = ft.Dropdown(label="Clone Skeleton Template From", value="base", visible=True)
        
        self.custom_mesh_switch.on_change = self.handle_switch_change
        
        self.cancel_btn = ft.TextButton("Cancel", on_click=self.close_dialog)
        self.create_btn = ft.TextButton("Create", on_click=self.execute_create)
        
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Add New Variant"),
            actions=[self.cancel_btn, self.create_btn],
            content=ft.Column([
                self.label_input,
                self.custom_mesh_switch,
                self.clone_source_dropdown
            ], tight=True, spacing=15)
        )

    def handle_switch_change(self, e):
        self.clone_source_dropdown.visible = self.custom_mesh_switch.value
        try: self.dialog.update()
        except Exception: pass

    def show(self, character_id: str, blend_files: list[str], on_confirm_callback):
        self.on_confirm = on_confirm_callback
        self.dialog.title = ft.Text(f"Add New {character_id} Variant")
        
        self.label_input.value = ""
        self.custom_mesh_switch.value = True
        self.clone_source_dropdown.visible = True
        
        dropdown_options = [ft.dropdown.Option("base", "base (Vanilla Canonical Mesh)")]
        for f in blend_files:
            clean_lbl = f
            prefix = f"{character_id}_"
            if clean_lbl.startswith(prefix):
                clean_lbl = clean_lbl[len(prefix):]
            dropdown_options.append(ft.dropdown.Option(f, f"Variant: {clean_lbl}"))
            
        self.clone_source_dropdown.options = dropdown_options
        self.clone_source_dropdown.value = "base"
        
        self.create_btn.text = "Create"
        self.create_btn.disabled = False
        
        show_dialog_safe(self.page, self.dialog)

    def close_dialog(self, e=None):
        close_dialog_safe(self.page, self.dialog)

    def execute_create(self, e):
        label_val = self.label_input.value.strip() if self.label_input.value else ""
        if not label_val:
            self.page.overlay.append(ft.SnackBar(ft.Text("Variant Label is required.", color=ft.Colors.RED_400), open=True))
            self.page.update()
            return
            
        # UI Hack: Mutate state to force Flet diff redraw instantly
        self.create_btn.disabled = True
        self.create_btn.text = "Creating..."
        try: self.dialog.update()
        except Exception: pass
        
        close_dialog_safe(self.page, self.dialog)
        
        if self.on_confirm:
            self.on_confirm(label_val, self.custom_mesh_switch.value, self.clone_source_dropdown.value)


class AltermaticDeleteDialog:
    def __init__(self, page: ft.Page):
        self.page = page
        self.on_confirm = None
        self.cancel_btn = ft.TextButton("Cancel", on_click=self.close_dialog)
        self.delete_btn = ft.TextButton("Delete", on_click=self.execute_delete, style=ft.ButtonStyle(color=ft.Colors.RED))
        
        self.content_text = ft.Text("")
        
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Deletion"),
            content=self.content_text,
            actions=[self.cancel_btn, self.delete_btn]
        )

    def show(self, message: str, on_confirm_callback):
        self.on_confirm = on_confirm_callback
        self.content_text.value = message
        self.delete_btn.text = "Delete"
        self.delete_btn.disabled = False
        show_dialog_safe(self.page, self.dialog)

    def close_dialog(self, e=None):
        close_dialog_safe(self.page, self.dialog)

    def execute_delete(self, e):
        # UI Hack: Mutate state to force Flet diff redraw instantly
        self.delete_btn.disabled = True
        self.delete_btn.text = "Closing..."
        try: self.dialog.update()
        except Exception: pass
        
        close_dialog_safe(self.page, self.dialog)
        
        if self.on_confirm:
            self.on_confirm()