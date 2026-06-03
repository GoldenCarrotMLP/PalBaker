# components/altermatic/materials_section.py
import flet as ft
import os
import json

class MaterialsSection:
    def __init__(self, page: ft.Page, settings: dict):
        self.page = page
        self.settings = settings
        
        self.active_material_dropdowns = {}
        self.DEFAULT_SLOTS_MAP = {
            "WeaselDragon": ["mi_weaseldragon_body", "mi_weaseldragon_eye", "mi_weaseldragon_mouth"],
            "AmaterasuWolf": ["mi_amaterasu_body", "mi_amaterasu_hair"],
            "GrimGirl": ["mi_grimgirl_body", "mi_grimgirl_eye", "mi_grimgirl_weapon"],
            "Cattiva": ["mi_cattiva_body", "mi_cattiva_eye"]
        }

        # Dynamic slot containers
        self.mat_replaces_col = ft.Column(spacing=8)

        # Layout view
        self.view = ft.Column([
            ft.Text("Visual Material Overrides (MatReplace)", size=12, weight=ft.FontWeight.BOLD),
            self.mat_replaces_col
        ], spacing=15)

    def get_slots_for_skeleton(self, character_id: str, source: str) -> list[str]:
        """Resolves material slots directly from the consolidated sidecar JSON on disk (0ms overhead)."""
        root_dir = os.path.dirname(self.settings.get("uproject", ""))
        
        if source == "base":
            sidecar_path = os.path.join(
                root_dir, "Content", "Pal", "Model", "Character", "Monster", 
                character_id, f"{character_id}_blend.json"
            )
        else:
            sidecar_name = f"{os.path.splitext(source)[0]}_blend.json"
            sidecar_path = os.path.join(
                root_dir, "Content", "Palbaker", "Model", "Character", "Monster", 
                character_id, sidecar_name
            )

        # Read directly from the consolidated sidecar's materials block
        if os.path.exists(sidecar_path):
            try:
                with open(sidecar_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    mats = data.get("materials", {})
                    if mats:
                        return list(mats.keys())
            except Exception:
                pass

        # Fallback to local default mappings if sidecar doesn't exist yet
        return self.DEFAULT_SLOTS_MAP.get(character_id, ["mi_body", "mi_eye"])

    def populate(self, character_id: str, selected_source: str, preloaded_overrides: list, available_mats: list[str], is_base: bool):
        self.view.visible = not is_base
        if is_base:
            return

        self.mat_replaces_col.controls.clear()
        self.active_material_dropdowns.clear()

        slots = self.get_slots_for_skeleton(character_id, selected_source)

        for idx, slot_name in enumerate(slots):
            dropdown_options = [ft.dropdown.Option("default", "Default (No Override)")]
            for mat in available_mats:
                dropdown_options.append(ft.dropdown.Option(mat, mat))

            initial_val = "default"
            if preloaded_overrides:
                matched_override = next((item for item in preloaded_overrides if int(item["Index"]) == idx), None)
                if matched_override:
                    initial_val = matched_override["MatPath"].split("/")[-1]

            dd = ft.Dropdown(
                value=initial_val,
                options=dropdown_options,
                expand=True
            )
            self.active_material_dropdowns[idx] = dd

            self.mat_replaces_col.controls.append(
                ft.Row([
                    ft.Text(f"Slot {idx} ({slot_name}):", size=11, weight=ft.FontWeight.BOLD, width=150),
                    dd
                ], spacing=10)
            )

    def get_values(self, category: str, character_id: str, source: str) -> list[dict]:
        mat_replaces = []
        slots = self.get_slots_for_skeleton(character_id, source)

        for idx, dropdown in self.active_material_dropdowns.items():
            if dropdown.value and dropdown.value != "default":
                mat_path = f"/Game/Palbaker/Model/Character/{category}/{character_id}/{dropdown.value}"
                mat_replaces.append({
                    "Index": str(idx),
                    "MatPath": mat_path,
                    "SlotName": slots[idx]
                })
        return mat_replaces