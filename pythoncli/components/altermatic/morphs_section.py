# components/altermatic/morphs_section.py
import flet as ft  # type: ignore
import os
import json

class MorphsSection:
    def __init__(self, page: ft.Page, settings: dict, on_update_callback):
        self.page = page
        self.settings = settings
        self.on_update_callback = on_update_callback
        
        self.active_morph_states = {}

        # Dynamic slot containers
        self.morphs_col = ft.Column(spacing=8)

        # Layout view
        self.view = ft.Column([
            ft.Text("Dynamic Morph Target Parameters", size=12, weight=ft.FontWeight.BOLD),
            self.morphs_col
        ], spacing=15)

    async def get_morph_targets_for_skeleton(self, character_id: str, source: str) -> list[str]:
        """Resolves active blendshapes directly via the CLI (0ms overhead / client-server safe)."""
        try:
            res = await self.page.mods_view.cli.altermatic_sidecar(character_id, source)
            if res.get("status") == "success":
                data = res.get("data", {})
                morphs = [m["Target"] for m in data.get("MorphTarget", []) if "Target" in m]
                if morphs:
                    return morphs
        except Exception:
            pass
        return ["breast_size", "belly_fat", "waist_width", "height_scale"]

    def update_morph_state(self, morph_name: str, key: str, value):
        self.active_morph_states[morph_name][key] = value

    def render_morph_row_controls(self, morph_name: str, mode: str, preloaded_data: dict | None = None) -> list[ft.Control]:
        controls = []
        state_key = morph_name

        if state_key not in self.active_morph_states:
            self.active_morph_states[state_key] = {
                "mode": "None",
                "set_val": 0.5,
                "min_val": 0.0,
                "max_val": 1.0,
                "type_val": "Free"
            }

            if preloaded_data:
                if "Set" in preloaded_data:
                    self.active_morph_states[state_key]["mode"] = "Static"
                    self.active_morph_states[state_key]["set_val"] = float(preloaded_data["Set"])
                elif "Min" in preloaded_data or "Max" in preloaded_data:
                    self.active_morph_states[state_key]["mode"] = "Random"
                    self.active_morph_states[state_key]["min_val"] = float(preloaded_data.get("Min", 0.0))
                    self.active_morph_states[state_key]["max_val"] = float(preloaded_data.get("Max", 1.0))
                    self.active_morph_states[state_key]["type_val"] = preloaded_data.get("Type", "Free")

        current_state = self.active_morph_states[state_key]
        current_state["mode"] = mode

        if mode == "Static":
            slider = ft.Slider(
                min=0.0, max=1.0, divisions=20,
                value=current_state["set_val"],
                label="Set: {value}",
                on_change=lambda e, mn=state_key: self.update_morph_state(mn, "set_val", e.control.value),
                expand=True
            )
            controls.append(ft.Row([ft.Text("Forced value:", size=11, width=100), slider], spacing=5))
            
        elif mode == "Random":
            min_slider = ft.Slider(
                min=0.0, max=1.0, divisions=20,
                value=current_state["min_val"],
                label="Min: {value}",
                on_change=lambda e, mn=state_key: self.update_morph_state(mn, "min_val", e.control.value),
                expand=True
            )
            max_slider = ft.Slider(
                min=0.0, max=1.0, divisions=20,
                value=current_state["max_val"],
                label="Max: {value}",
                on_change=lambda e, mn=state_key: self.update_morph_state(mn, "max_val", e.control.value),
                expand=True
            )
            type_dd = ft.Dropdown(
                value=current_state["type_val"],
                options=[ft.dropdown.Option("Free"), ft.dropdown.Option("Restrict")],
                width=140
            )
            type_dd.on_change = lambda e, mn=state_key: self.update_morph_state(mn, "type_val", e.control.value)  # type: ignore

            controls.append(ft.Column([
                ft.Row([ft.Text("Min Boundary:", size=11, width=100), min_slider], spacing=5),
                ft.Row([ft.Text("Max Boundary:", size=11, width=100), max_slider], spacing=5),
                ft.Row([ft.Text("Roll Mode:", size=11, width=100), type_dd], spacing=5)
            ]))
            
        return controls

    async def populate(self, character_id: str, selected_source: str, preloaded_morphs: list, is_base: bool):
        self.view.visible = not is_base
        if is_base:
            return

        self.morphs_col.controls.clear()
        self.active_morph_states.clear()
        
        morph_names = await self.get_morph_targets_for_skeleton(character_id, selected_source)
        
        preload_map = {}
        if preloaded_morphs:
            for item in preloaded_morphs:
                preload_map[item["Target"]] = item

        for name in morph_names:
            preload_data = preload_map.get(name)
            options_container = ft.Column()
            
            initial_mode = "None"
            if preload_data:
                if "Set" in preload_data:
                    initial_mode = "Static"
                elif "Min" in preload_data or "Max" in preload_data:
                    initial_mode = "Random"

            mode_dd = ft.Dropdown(
                value=initial_mode,
                options=[
                    ft.dropdown.Option("None", "Ignore"),
                    ft.dropdown.Option("Static", "Static (Set)"),
                    ft.dropdown.Option("Random", "Random (Range)")
                ],
                width=160
            )

            def handle_mode_change(e, m_name=name, container=options_container):
                container.controls = self.render_morph_row_controls(m_name, e.control.value)
                self.on_update_callback()

            mode_dd.on_change = handle_mode_change  # type: ignore

            options_container.controls = self.render_morph_row_controls(name, initial_mode, preload_data)

            self.morphs_col.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(name, size=12, weight=ft.FontWeight.BOLD, expand=True),
                            mode_dd
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        options_container
                    ], spacing=10),
                    padding=10,
                    border=ft.Border.all(1, ft.Colors.WHITE10),
                    border_radius=6,
                    bgcolor=ft.Colors.WHITE10
                )
            )

    def get_values(self) -> list[dict]:
        morphs = []
        for name, state in self.active_morph_states.items():
            if state["mode"] == "Static":
                morphs.append({
                    "Target": name,
                    "Set": state["set_val"]
                })
            elif state["mode"] == "Random":
                morphs.append({
                    "Target": name,
                    "Min": state["min_val"],
                    "Max": state["max_val"],
                    "Type": state["type_val"]
                })
        return morphs