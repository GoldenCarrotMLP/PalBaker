# components/altermatic/general_section.py
import flet as ft  # type: ignore

class GeneralSection:
    def __init__(self, on_skeleton_changed, on_open_blend, on_refresh_layout):
        self.on_skeleton_changed = on_skeleton_changed
        self.on_open_blend = on_open_blend
        self.on_refresh_layout = on_refresh_layout

        # UI Input controls
        self.label_input = ft.TextField(label="Variant Label/Name", hint_text="e.g., SFW_Bikini_T-Shirt")
        self.char_id_input = ft.TextField(label="Character ID (Locked)", disabled=True)
        
        # Instantiate and assign event handler after creation to bypass Flet constructor bugs
        self.skeleton_source_dropdown = ft.Dropdown(
            label="Skeleton / Mesh Source",
            expand=True
        )
        self.skeleton_source_dropdown.on_change = self.on_skeleton_changed
        
        self.open_blend_button = ft.IconButton(
            icon=ft.Icons.EDIT_NOTE_ROUNDED,
            icon_color=ft.Colors.CYAN_400,
            tooltip="Open selected .blend file directly in Blender",
            on_click=self.on_open_blend
        )

        # Dynamic Sync Button
        self.refresh_layout_button = ft.IconButton(
            icon=ft.Icons.SYNC_ROUNDED,
            icon_color=ft.Colors.CYAN_400,
            tooltip="Scan Blender file for new material slots and blendshapes on the spot",
            on_click=self.on_refresh_layout
        )

        self.gender_dropdown = ft.Dropdown(
            label="Gender",
            options=[
                ft.dropdown.Option("None"),
                ft.dropdown.Option("Male"),
                ft.dropdown.Option("Female"),
                ft.dropdown.Option("Futa"),
                ft.dropdown.Option("FullFuta"),
                ft.dropdown.Option("Andro"),
                ft.dropdown.Option("Neutered")
            ]
        )
        self.is_rare_checkbox = ft.Checkbox(label="Is Rare/Lucky Pal")
        self.skin_name_input = ft.TextField(label="Target Skin Override Name (Optional)", hint_text="e.g., WeaselDragon_Skin001")

        # De-structure the walrus assignment to satisfy Python's compiler rules
        self.conditions_row = ft.Row([self.gender_dropdown, self.is_rare_checkbox], spacing=20)

        # Layout view (Skins Override textfield is removed from here)
        self.view = ft.Column([
            self.label_input,
            self.char_id_input,
            ft.Row([
                self.skeleton_source_dropdown, 
                self.open_blend_button,
                self.refresh_layout_button
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=5),
            self.conditions_row
        ], spacing=15)

    def populate(self, character_id: str, blend_files: list[str], variant_data: dict, is_base: bool):
        """Populates fields and manages locked states for the base fallback."""
        self.char_id_input.value = character_id
        self.label_input.disabled = is_base
        self.skeleton_source_dropdown.disabled = False
        
        # Manage visibility based on base card
        self.conditions_row.visible = not is_base
        self.skin_name_input.visible = not is_base

        # Populate Skeleton sources with clean stripped labels
        dropdown_options = [ft.dropdown.Option("base", "base (Vanilla Canonical Mesh)")]
        for f in blend_files:
            # Strip parent prefix for display
            clean_lbl = f
            prefix = f"{character_id}_"
            if clean_lbl.startswith(prefix):
                clean_lbl = clean_lbl[len(prefix):]
            dropdown_options.append(ft.dropdown.Option(f, f"Blender: {clean_lbl}"))
        self.skeleton_source_dropdown.options = dropdown_options

        if is_base:
            self.label_input.value = "base"
            self.skeleton_source_dropdown.value = variant_data.get("SkeletonSource", "base")
        else:
            raw_label = variant_data.get("label", "")
            prefix = f"{character_id}_"
            if raw_label.startswith(prefix):
                raw_label = raw_label[len(prefix):]
                
            self.label_input.value = raw_label
            self.skeleton_source_dropdown.value = variant_data.get("SkeletonSource", "base")
            self.gender_dropdown.value = variant_data.get("Gender", "None")
            self.is_rare_checkbox.value = bool(variant_data.get("IsRarePal", False))
            self.skin_name_input.value = variant_data.get("SkinName", "")

        # FIXED: Grey out the Blender tools if the canonical base is selected to prevent crashes
        is_base_source = (self.skeleton_source_dropdown.value == "base")
        self.open_blend_button.disabled = is_base_source
        self.refresh_layout_button.disabled = is_base_source

    def get_values(self) -> dict:
        return {
            "label": self.label_input.value.strip() if self.label_input.value else "",
            "SkeletonSource": self.skeleton_source_dropdown.value,
            "Gender": self.gender_dropdown.value if self.gender_dropdown.value else "None",
            "IsRarePal": bool(self.is_rare_checkbox.value),
            "SkinName": self.skin_name_input.value.strip() if self.skin_name_input.value else ""
        }