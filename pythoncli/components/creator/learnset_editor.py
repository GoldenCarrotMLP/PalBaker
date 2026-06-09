# components/creator/learnset_editor.py
import flet as ft  # type: ignore

class LearnsetEditor:
    def __init__(self, page: ft.Page, active_skills_cache: dict, initial_learnset: list, show_search_dialog_callback):
        self.page = page
        self.active_skills_cache = active_skills_cache
        self.learnset = list(initial_learnset)
        self.show_search_dialog = show_search_dialog_callback

        self.rows_col = ft.Column(spacing=5, expand=True)

        self.new_move_lvl_input = ft.TextField(label="Lvl", width=55, text_size=11, content_padding=5)
        self.selected_new_move_id = ["AirCanon"]
        
        self.choose_new_move_btn_text = ft.Text("Choose Active Move...")
        self.choose_new_move_btn = ft.OutlinedButton(
            content=self.choose_new_move_btn_text,
            expand=True,
            on_click=self.handle_choose_move_click
        )

        self.add_move_trigger_btn = ft.IconButton(
            icon=ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED,
            icon_color=ft.Colors.CYAN_400,
            on_click=self.add_move_to_learnset
        )

        self.view = ft.Container(
            content=ft.Column([
                ft.Text("Level-Up Learnset Matrix", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_400),
                self.rows_col,
                ft.Row([
                    self.new_move_lvl_input,
                    self.choose_new_move_btn,
                    self.add_move_trigger_btn
                ], spacing=10)
            ], spacing=10),
            padding=10,
            border=ft.Border.all(1, ft.Colors.WHITE10),
            border_radius=6,
            bgcolor=ft.Colors.BLACK
        )

        self.render_rows()

    def render_rows(self):
        self.rows_col.controls.clear()
        self.learnset.sort(key=lambda x: x["Level"])
        
        for idx, entry in enumerate(self.learnset):
            lvl = entry["Level"]
            w_id = entry["WazaID"]
            
            # Safe layout lookup supporting both flat and enriched cache types
            friendly_waza = next((lbl for lbl, val in self.active_skills_cache.items() if (val["id"] if isinstance(val, dict) else val) == w_id), w_id)
            
            row = ft.Row([
                ft.Text(f"Lv. {lvl}:", size=11, weight=ft.FontWeight.BOLD, width=50),
                ft.Text(friendly_waza, size=11, expand=True),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                    icon_size=16,
                    icon_color=ft.Colors.RED_400,
                    on_click=lambda e, index=idx: self.delete_entry(index)
                )
            ], spacing=10)
            self.rows_col.controls.append(row)
        try: self.rows_col.update()
        except Exception: pass

    def delete_entry(self, index: int):
        self.learnset.pop(index)
        self.render_rows()

    def handle_choose_move_click(self, e):
        self.show_search_dialog(
            "Select Level-up Move",
            self.active_skills_cache,
            lambda val, lbl: (setattr(self.choose_new_move_btn_text, "value", lbl), self.selected_new_move_id.__setitem__(0, val), self.page.update())
        )

    def add_move_to_learnset(self, e):
        try:
            level_val = int(self.new_move_lvl_input.value.strip())
        except ValueError:
            self.page.overlay.append(ft.SnackBar(ft.Text("Level must be a valid integer.", color=ft.Colors.RED_400), open=True))
            self.page.update()
            return
            
        self.learnset.append({
            "Level": level_val,
            "WazaID": self.selected_new_move_id[0]
        })
        self.new_move_lvl_input.value = ""
        self.choose_new_move_btn_text.value = "Choose Active Move..."
        self.selected_new_move_id[0] = "AirCanon"
        
        self.render_rows()
        self.page.update()

    def get_values(self) -> list:
        return self.learnset