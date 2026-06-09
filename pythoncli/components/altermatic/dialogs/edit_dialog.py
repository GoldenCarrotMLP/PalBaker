# components/altermatic/dialogs/edit_dialog.py
import flet as ft  # type: ignore
import os
import subprocess
import json
from .utils import show_dialog_safe, close_dialog_safe
from components.altermatic.general_section import GeneralSection
from components.altermatic.traits_section import TraitsSection
from components.altermatic.materials_section import MaterialsSection
from components.altermatic.morphs_section import MorphsSection

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
        
        # FIXED: Bypasses Pylance attribute access errors
        setattr(self.apply_btn, "text", "Apply Changes")
        setattr(self.delete_btn, "text", "Delete")
        self.apply_btn.disabled = False
        self.delete_btn.disabled = False

        self.general_section.populate(character_id, blend_files, variant_data, self.is_base)
        self.traits_section.populate(variant_data, self.is_base)
        
        # FIXED: Enforce a strict fallback string to satisfy Pylance
        selected_source = self.general_section.skeleton_source_dropdown.value or "base"
        
        # Populate material and morphs asynchronously
        async def load_advanced_data():
            await self.materials_section.populate(character_id, selected_source, variant_data, available_mats, self.is_base, self.current_category)
            await self.morphs_section.populate(character_id, selected_source, variant_data.get("MorphTarget", []), self.is_base)
            self.force_ui_update()
            
        self.page.run_task(load_advanced_data)

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
        # FIXED: Enforce a strict fallback string to satisfy Pylance
        selected_source = self.general_section.skeleton_source_dropdown.value or "base"
        is_base_source = (selected_source == "base")
        self.general_section.open_blend_button.disabled = is_base_source
        self.general_section.refresh_layout_button.disabled = is_base_source

        async def reload_advanced():
            await self.materials_section.populate(self.current_character_id, selected_source, None, self.available_mats, self.is_base, self.current_category)
            await self.morphs_section.populate(self.current_character_id, selected_source, [], self.is_base)
            self.force_ui_update()
            
        self.page.run_task(reload_advanced)

    def force_ui_update(self):
        try: self.dialog.update()
        except Exception: pass

    def handle_open_blend_click(self, e):
        source = self.general_section.skeleton_source_dropdown.value
        if not source: return

        async def _async_open_blend():
            await self.page.mods_view.cli.altermatic_open_blend(self.current_character_id, source, self.current_category)
            
        self.page.run_task(_async_open_blend)

    def handle_refresh_layout_click(self, e):
        close_dialog_safe(self.page, self.dialog)
        self.on_refresh_callback(self.current_character_id)

    def handle_delete_click(self, e):
        self.delete_btn.disabled = True
        setattr(self.delete_btn, "text", "Closing...")
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

        self.apply_btn.disabled = True
        setattr(self.apply_btn, "text", "Saving...")
        self.delete_btn.disabled = True
        self.force_ui_update()

        req_traits, pref_traits = self.traits_section.get_values()
        mat_resolved_dir = f"/Game/Palbaker/Model/Character/{self.current_category}/{self.current_character_id}".replace(" ", "_")
        morphs = self.morphs_section.get_values()

        async def fetch_slots_and_save():
            mat_replaces = []
            slots = await self.materials_section.get_slots_for_skeleton(self.current_character_id, general_values["SkeletonSource"], self.current_category)

            for idx, dropdown in self.materials_section.active_material_dropdowns.items():
                if dropdown.value and dropdown.value != "default":
                    resolved_mat_path = f"{mat_resolved_dir}/{dropdown.value}"
                    mat_replaces.append({
                        "Index": str(idx),
                        "MatPath": resolved_mat_path,
                        "SlotName": slots[idx]
                    })

            full_variant_data = {
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

            close_dialog_safe(self.page, self.dialog)
            self.on_save_callback(self.editing_index, full_variant_data)

        self.page.run_task(fetch_slots_and_save)