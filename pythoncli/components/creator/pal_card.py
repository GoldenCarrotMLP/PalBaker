# components/creator/pal_card.py
import flet as ft  # type: ignore
import os
from .learnset_editor import LearnsetEditor

class PalCreatorCard:
    def __init__(self, page: ft.Page, pal_data: dict, settings: dict, active_skills: dict, passive_skills: dict, partner_skills: dict, coop_passives: dict, monster_spawners: dict, is_expanded: bool, on_toggle, on_save, on_delete, show_search_dialog_callback, on_refresh_bp):
        self.page = page
        self.p = pal_data
        self.settings = settings
        self.active_skills = active_skills
        self.passive_skills = passive_skills
        self.partner_skills = partner_skills
        self.coop_passives = coop_passives
        self.monster_spawners = monster_spawners
        self.is_expanded = is_expanded
        self.on_toggle = on_toggle
        self.on_save = on_save
        self.on_delete = on_delete
        self.show_search_dialog = show_search_dialog_callback
        self.on_refresh_bp = on_refresh_bp
        
        self.pal_id = pal_data["CharacterID"]

        # Header Controls
        title = ft.Text(f"{pal_data['Name']} ({self.pal_id})", weight=ft.FontWeight.BOLD, size=15)
        subtitle = ft.Text(f"Template Cloned From: {pal_data['TemplateID']}", size=11, color=ft.Colors.WHITE54)
        
        chevron = ft.IconButton(
            icon=ft.Icons.KEYBOARD_ARROW_UP if is_expanded else ft.Icons.KEYBOARD_ARROW_DOWN,
            on_click=lambda e: self.on_toggle(self.pal_id)
        )

        resolved_icon_path = pal_data.get("resolved_icon_path", "")
            
        if resolved_icon_path:
            avatar = ft.Container(
                content=ft.Image(src=resolved_icon_path, width=32, height=32, fit=ft.BoxFit.CONTAIN),
                width=32, height=32, border_radius=6, bgcolor=ft.Colors.WHITE10
            )
        else:
            avatar = ft.Container(
                content=ft.Icon(ft.Icons.ADD_PHOTO_ALTERNATE_ROUNDED, color=ft.Colors.WHITE38, size=18),
                width=32,
                height=32,
                alignment=ft.Alignment.CENTER,
                border_radius=6,
                border=ft.Border.all(1, ft.Colors.WHITE10),
                bgcolor=ft.Colors.WHITE10
            )

        body_container = ft.Container(visible=is_expanded, padding=ft.Padding(left=10, top=10, right=10, bottom=10))
        if is_expanded:
            body_container.content = self.build_editor_fields()

        self.view = ft.Container(
            content=ft.Column([
                ft.Row([
                    avatar,
                    ft.Column([title, subtitle], spacing=1, expand=True),
                    chevron
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                body_container
            ], spacing=5),
            padding=10,
            border=ft.Border.all(1, ft.Colors.WHITE24),
            border_radius=8,
            bgcolor=ft.Colors.WHITE10 if is_expanded else None
        )

    def show_search_dialog_with_elements(self, title: str, dataset_dict: dict, on_select_callback):
        """Pre-processes active Pal element structures and routes them directly to the search modal."""
        raw_el1 = self.p.get("ElementType1", "EPalElementType::None")
        pal_el1 = raw_el1.split("::")[-1] if "::" in raw_el1 else raw_el1
        
        raw_el2 = self.p.get("ElementType2", "EPalElementType::None")
        pal_el2 = raw_el2.split("::")[-1] if "::" in raw_el2 else raw_el2
        
        elements_list = [pal_el1]
        if pal_el2 and pal_el2 != "None":
            elements_list.append(pal_el2)
            
        self.show_search_dialog(title, dataset_dict, on_select_callback, elements_list)

    def build_editor_fields(self) -> ft.Control:
        p = self.p
        template_id = p.get("TemplateID", "WeaselDragon")
        
        name_input = ft.TextField(label="Display Name", value=p["Name"], expand=True)
        desc_input = ft.TextField(label="Short Description", value=p["Description"], expand=True, multiline=True, max_lines=2)

        elem_options = [
            ft.dropdown.Option("EPalElementType::None", "None"),
            ft.dropdown.Option("EPalElementType::Normal", "Neutral"),
            ft.dropdown.Option("EPalElementType::Fire", "Fire"),
            ft.dropdown.Option("EPalElementType::Water", "Water"),
            ft.dropdown.Option("EPalElementType::Leaf", "Grass"),
            ft.dropdown.Option("EPalElementType::Electricity", "Electric"),
            ft.dropdown.Option("EPalElementType::Ice", "Ice"),
            ft.dropdown.Option("EPalElementType::Earth", "Ground"),
            ft.dropdown.Option("EPalElementType::Dragon", "Dragon"),
            ft.dropdown.Option("EPalElementType::Dark", "Dark")
        ]
        elem1_dd = ft.Dropdown(label="Primary Element", value=p["ElementType1"], options=elem_options, expand=True)
        elem2_dd = ft.Dropdown(label="Secondary Element", value=p["ElementType2"], options=elem_options, expand=True)

        selected_skills = list(p["BaseSkills"])
        friendly_skill = "None"
        if selected_skills:
            friendly_skill = next((lbl for lbl, val in self.active_skills.items() if (val["id"] if isinstance(val, dict) else val) == selected_skills[0]), selected_skills[0])
        skills_btn_text = ft.Text(f"Skills: {friendly_skill}")
        skills_btn = ft.OutlinedButton(
            content=skills_btn_text,
            expand=True,
            on_click=lambda e: self.show_search_dialog(
                "Select Active Attack",
                self.active_skills,
                lambda val, lbl: (setattr(skills_btn_text, "value", f"Skills: {lbl}"), selected_skills.__setitem__(0, val), self.page.update())
            )
        )

        selected_passives = list(p["PassiveSkills"])
        friendly_passive = "None"
        if selected_passives:
            friendly_passive = next((lbl for lbl, val in self.passive_skills.items() if val == selected_passives[0]), selected_passives[0])
        passives_btn_text = ft.Text(f"Passive: {friendly_passive}")
        passives_btn = ft.OutlinedButton(
            content=passives_btn_text,
            expand=True,
            on_click=lambda e: self.show_search_dialog(
                "Select Passive Trait",
                self.passive_skills,
                lambda val, lbl: (setattr(passives_btn_text, "value", f"Passive: {lbl}"), selected_passives.__setitem__(0, val) if selected_passives else selected_passives.append(val), self.page.update())
            )
        )

        selected_partner = [p.get("PartnerSkill", "None")]
        friendly_partner = next((lbl for lbl, val in self.partner_skills.items() if val == selected_partner[0]), selected_partner[0])
        partner_btn_text = ft.Text(f"Ability: {friendly_partner}")
        partner_btn = ft.OutlinedButton(
            content=partner_btn_text,
            expand=True,
            on_click=lambda e: self.show_search_dialog(
                "Select Partner Skill",
                self.partner_skills,
                lambda val, lbl: (setattr(partner_btn_text, "value", f"Ability: {lbl}"), selected_partner.__setitem__(0, val), self.force_update())
            )
        )

        saddle_input = ft.TextField(
            label="Unlock Key Item ID (Saddle/Harness)", 
            value=p.get("SaddleItem", "None"), 
            expand=True
        )

        selected_coop_passives = list(p.get("CoopPassives", []))
        friendly_coop_passive = "None"
        if selected_coop_passives:
            friendly_coop_passive = next((lbl for lbl, val in self.coop_passives.items() if val == selected_coop_passives[0]), selected_coop_passives[0])
        
        coop_passives_btn_text = ft.Text(f"Co-op Passive: {friendly_coop_passive}")
        coop_passives_btn = ft.OutlinedButton(
            content=coop_passives_btn_text,
            expand=True,
            on_click=lambda e: self.show_search_dialog(
                "Select Co-op Passive Buff",
                self.coop_passives, 
                lambda val, lbl: (setattr(coop_passives_btn_text, "value", f"Co-op Passive: {lbl}"), selected_coop_passives.__setitem__(0, val) if selected_coop_passives else selected_coop_passives.append(val), self.page.update())
            )
        )

        coop_panel = ft.Container(
            content=ft.Column([
                ft.Text("Co-op / Mount Configurations", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_400),
                ft.Row([saddle_input, coop_passives_btn], spacing=10)
            ], spacing=10),
            padding=10,
            border=ft.Border.all(1, ft.Colors.WHITE10),
            border_radius=6,
            bgcolor=ft.Colors.BLACK
        )

        enable_spawns_checkbox = ft.Checkbox(
            label="Enable Overworld Wild Spawning", 
            value=p.get("EnableSpawns", True)
        )
        
        selected_spawner = [p.get("SpawnLocationID", "1_1_plain_begginer")]
        friendly_spawner = next((lbl for lbl, val in self.monster_spawners.items() if val == selected_spawner[0]), selected_spawner[0])
        spawner_btn_text = ft.Text(f"Spawner Pool: {friendly_spawner}")
        spawner_btn = ft.OutlinedButton(
            content=spawner_btn_text,
            expand=True,
            on_click=lambda e: self.show_search_dialog(
                "Select Spawner Location",
                self.monster_spawners,
                lambda val, lbl: (setattr(spawner_btn_text, "value", f"Spawner Pool: {lbl}"), selected_spawner.__setitem__(0, val), self.page.update())
            )
        )

        spawn_min_lvl = ft.TextField(
            label="Min Wild Level", 
            value=str(p.get("SpawnMinLevel", 2)), 
            expand=True
        )
        spawn_max_lvl = ft.TextField(
            label="Max Wild Level", 
            value=str(p.get("SpawnMaxLevel", 5)), 
            expand=True
        )
        spawn_min_group = ft.TextField(
            label="Min Group Size", 
            value=str(p.get("SpawnMinGroup", 1)), 
            expand=True
        )
        spawn_max_group = ft.TextField(
            label="Max Group Size", 
            value=str(p.get("SpawnMaxGroup", 3)), 
            expand=True
        )

        spawner_panel = ft.Container(
            content=ft.Column([
                ft.Text("Overworld Wild Spawner Configurations", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_400),
                ft.Row([enable_spawns_checkbox, spawner_btn], spacing=10),
                ft.Row([spawn_min_lvl, spawn_max_lvl, spawn_min_group, spawn_max_group], spacing=10)
            ], spacing=10),
            padding=10,
            border=ft.Border.all(1, ft.Colors.WHITE10),
            border_radius=6,
            bgcolor=ft.Colors.BLACK
        )

        z_index = p.get("ZukanIndex", -1)
        has_paldeck = z_index != -1
        
        enable_paldeck_checkbox = ft.Checkbox(
            label="Enable Paldeck (PalPedia) Entry", 
            value=has_paldeck
        )
        
        zukan_index_input = ft.TextField(
            label="Paldeck Sort Number", 
            value=str(z_index) if has_paldeck else "55", 
            expand=True,
            disabled=not has_paldeck
        )
        
        zukan_suffix_input = ft.TextField(
            label="Sub-Species Suffix (Optional)", 
            value=p.get("ZukanIndexSuffix", ""), 
            expand=True,
            disabled=not has_paldeck
        )

        paldex_type_dd = ft.Dropdown(
            label="Paldex Classification",
            value=p.get("PaldexType", "Species"),
            options=[
                ft.dropdown.Option("Species", "New Standalone Species (Unique Tribe)"),
                ft.dropdown.Option("Variant", "Subspecies Variant (Inherits Parent Tribe)")
            ],
            expand=True,
            disabled=not has_paldeck
        )
        
        pedia_desc_input = ft.TextField(
            label="Paldeck Lore Description", 
            value=p.get("LongDescription", f"A custom standalone Pal cloned from {template_id}."), 
            expand=True, 
            multiline=True, 
            max_lines=3,
            disabled=not has_paldeck
        )

        def handle_paldeck_toggle(e):
            is_enabled = enable_paldeck_checkbox.value
            zukan_index_input.disabled = not is_enabled
            zukan_suffix_input.disabled = not is_enabled
            pedia_desc_input.disabled = not is_enabled
            paldex_type_dd.disabled = not is_enabled
            self.page.update()

        enable_paldeck_checkbox.on_change = handle_paldeck_toggle

        paldeck_panel = ft.Container(
            content=ft.Column([
                ft.Text("Paldeck (PalPedia) Configurations", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_400),
                enable_paldeck_checkbox,
                ft.Row([zukan_index_input, zukan_suffix_input], spacing=10),
                paldex_type_dd,
                pedia_desc_input
            ], spacing=10),
            padding=10,
            border=ft.Border.all(1, ft.Colors.WHITE10),
            border_radius=6,
            bgcolor=ft.Colors.BLACK
        )

        # Injecting the element-aware search wrapper [7]
        self.learnset_editor = LearnsetEditor(
            self.page,
            self.active_skills,
            p.get("Learnset", []),
            self.show_search_dialog_with_elements
        )

        hp_input = ft.TextField(label="Base HP", value=str(p["BaseHP"]), expand=True)
        atk_input = ft.TextField(label="Base Attack", value=str(p["BaseAtk"]), expand=True)
        def_input = ft.TextField(label="Base Defense", value=str(p["BaseDef"]), expand=True)
        ws_input = ft.TextField(label="Base WorkSpeed", value=str(p["BaseWorkSpeed"]), expand=True)

        advanced_cols = ft.Column([
            ft.Row([hp_input, atk_input], spacing=10),
            ft.Row([def_input, ws_input], spacing=10)
        ], visible=False, spacing=10)

        adv_btn = ft.TextButton(
            "Toggle Advanced Parameters", 
            icon=ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED,
            on_click=lambda e: self.toggle_advanced_accordion(advanced_cols, adv_btn)
        )

        def on_save_click(e):
            save_payload = {
                "CharacterID": self.pal_id,
                "TemplateID": p["TemplateID"],
                "Name": name_input.value.strip(),
                "Description": desc_input.value.strip(),
                "ElementType1": elem1_dd.value,
                "ElementType2": elem2_dd.value,
                "BaseHP": int(hp_input.value.strip() or "100"),
                "BaseAtk": int(atk_input.value.strip() or "100"),
                "BaseDef": int(def_input.value.strip() or "100"),
                "BaseWorkSpeed": int(ws_input.value.strip() or "70"),
                "WorkSuitabilities": p["WorkSuitabilities"],
                "BaseSkills": selected_skills if selected_skills else [],
                "PassiveSkills": selected_passives if (selected_passives and selected_passives[0] != "None") else [],
                "PartnerSkill": selected_partner[0],
                "Learnset": self.learnset_editor.get_values(),
                "SaddleItem": saddle_input.value.strip() if saddle_input.value else "None",
                "CoopPassives": selected_coop_passives if (selected_coop_passives and selected_coop_passives[0] != "None") else [],
                "EnableSpawns": enable_spawns_checkbox.value,
                "SpawnLocationID": selected_spawner[0],
                "SpawnMinLevel": int(spawn_min_lvl.value.strip() or "2"),
                "SpawnMaxLevel": int(spawn_max_lvl.value.strip() or "5"),
                "SpawnMinGroup": int(spawn_min_group.value.strip() or "1"),
                "SpawnMaxGroup": int(spawn_max_group.value.strip() or "3"),
                "EnablePaldeck": enable_paldeck_checkbox.value,
                "ZukanIndex": int(zukan_index_input.value.strip() or "55") if enable_paldeck_checkbox.value else -1,
                "ZukanIndexSuffix": zukan_suffix_input.value.strip() if enable_paldeck_checkbox.value else "",
                "LongDescription": pedia_desc_input.value.strip() if enable_paldeck_checkbox.value else "",
                "PaldexType": paldex_type_dd.value
            }

            self.on_save(self.pal_id, save_payload)

        def on_delete_click(e):
            self.on_delete(self.pal_id)

        refresh_bp_btn = ft.TextButton(
            "Refresh Actor Blueprint", 
            icon=ft.Icons.AUTORENEW_ROUNDED, 
            on_click=lambda e: self.on_refresh_bp(self.pal_id),
            style=ft.ButtonStyle(color=ft.Colors.CYAN_400)
        )

        save_btn = ft.TextButton("Save Pal", icon=ft.Icons.SAVE, on_click=on_save_click, style=ft.ButtonStyle(color=ft.Colors.GREEN_400))
        delete_btn = ft.TextButton("Delete", icon=ft.Icons.DELETE, on_click=on_delete_click, style=ft.ButtonStyle(color=ft.Colors.RED_400))

        fields_view = ft.Column([
            ft.Row([name_input, elem1_dd, elem2_dd], spacing=10),
            ft.Row([skills_btn, passives_btn, partner_btn], spacing=10),
            desc_input,
            coop_panel,
            spawner_panel,
            paldeck_panel,
            self.learnset_editor.view,
            adv_btn,
            advanced_cols,
            ft.Row([refresh_bp_btn, save_btn, delete_btn], alignment=ft.MainAxisAlignment.END, spacing=10)
        ], spacing=10)
        
        return fields_view

    def toggle_advanced_accordion(self, target_col: ft.Column, toggle_btn: ft.TextButton):
        target_col.visible = not target_col.visible
        toggle_btn.icon = ft.Icons.KEYBOARD_ARROW_UP_ROUNDED if target_col.visible else ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED
        self.page.update()

    def force_update(self):
        try:
            self.view.update()
        except Exception:
            pass