# components/altermatic/materials_section.py
import flet as ft  # type: ignore
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

    async def get_slots_for_skeleton(self, character_id: str, source: str, category: str = "Monster") -> list[str]:
        """Resolves material slots directly via the CLI (0ms overhead / client-server safe)."""
        try:
            res = await self.page.mods_view.cli.altermatic_sidecar(character_id, source)
            if res.get("status") == "success":
                data = res.get("data", {})
                mats = data.get("materials", {})
                if mats:
                    return list(mats.keys())
        except Exception:
            pass
        return self.DEFAULT_SLOTS_MAP.get(character_id, ["mi_body", "mi_eye"])

    # FIXED: Piped 'category' parameter downwards and made asynchronous
    async def populate(self, character_id: str, selected_source: str, variant_data: dict | None, available_mats: list[str], is_base: bool, category: str = "Monster"):
        self.view.visible = not is_base
        if is_base:
            return

        self.mat_replaces_col.controls.clear()
        self.active_material_dropdowns.clear()

        slots = await self.get_slots_for_skeleton(character_id, selected_source, category)

        # Resolve preloaded material overrides cleanly from either format (MaterialOverrides dict or MatReplace list)
        preloaded_overrides_dict = {}
        if variant_data:
            # 1. Primary on-disk dictionary format (MaterialOverrides)
            mat_overrides = variant_data.get("MaterialOverrides", {})
            if isinstance(mat_overrides, dict):
                for k, v in mat_overrides.items():
                    preloaded_overrides_dict[k.lower()] = v

            # 2. Sequential fallback list format (MatReplace)
            mat_replaces = variant_data.get("MatReplace", [])
            if isinstance(mat_replaces, list):
                for item in mat_replaces:
                    idx = item.get("Index")
                    mat_path = item.get("MatPath", "")
                    if idx is not None and mat_path:
                        try:
                            idx_int = int(idx)
                            if 0 <= idx_int < len(slots):
                                slot_name = slots[idx_int]
                                mat_name = mat_path.split("/")[-1]
                                preloaded_overrides_dict[slot_name.lower()] = mat_name
                        except (ValueError, TypeError):
                            pass

        for idx, slot_name in enumerate(slots):
            dropdown_options = [ft.dropdown.Option("default", "Default (No Override)")]
            for mat in available_mats:
                dropdown_options.append(ft.dropdown.Option(mat, mat))

            initial_val = "default"
            slot_key = slot_name.lower()
            if slot_key in preloaded_overrides_dict:
                initial_val = preloaded_overrides_dict[slot_key]

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