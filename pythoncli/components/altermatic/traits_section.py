# components/altermatic/traits_section.py
import flet as ft  # type: ignore
import threading
import time

class TraitsSection:
    def __init__(self, traits_db: dict, on_update_callback):
        self.traits_db = traits_db
        self.on_update_callback = on_update_callback
        
        self.temp_req_traits = []
        self.temp_pref_traits = []

        # UI Controls
        self.search_input = ft.TextField(label="Fuzzy Search Passive Traits...", hint_text="e.g., Artisan, Swift, Rare")
        self.selected_tags_row = ft.Row(wrap=True, spacing=5)
        
        # Hide the list by default
        self.search_results_col = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, height=140, visible=False)

        # Bind listeners safely after creation
        self.search_input.on_change = lambda e: self.refresh_search_results(self.search_input.value)
        self.search_input.on_focus = self.handle_focus
        self.search_input.on_blur = self.handle_blur

        # Layout view
        self.view = ft.Column([
            ft.Text("Required & Preferred Passive Traits", size=12, weight=ft.FontWeight.BOLD),
            self.selected_tags_row,
            self.search_input,
            self.search_results_col
        ], spacing=15)

    def populate(self, variant_data: dict, is_base: bool):
        """Pre-populates active traits as dismissible chips."""
        self.view.visible = not is_base
        if is_base:
            return

        self.temp_req_traits = list(variant_data.get("ReqTrait", []))
        self.temp_pref_traits = list(variant_data.get("PrefTrait", []))
        self.search_input.value = ""
        self.search_results_col.visible = False  # Hide on modal open until focused
        
        self.refresh_selected_tags()
        self.refresh_search_results("")

    def handle_focus(self, e):
        """Instantly shows the complete list when the search field is selected."""
        self.search_results_col.visible = True
        self.refresh_search_results(self.search_input.value)
        self.on_update_callback()

    def handle_blur(self, e):
        """Slightly buffers the blur action to let Flet register the click on list buttons before hiding."""
        def delay_hide():
            time.sleep(0.2)  # 200ms buffer is standard for responsive dropdown lists
            self.search_results_col.visible = False
            self.on_update_callback()
            
        threading.Thread(target=delay_hide, daemon=True).start()

    def refresh_selected_tags(self):
        self.selected_tags_row.controls.clear()
        
        # Required traits (Green)
        for trait_id in self.temp_req_traits:
            game_name = next((g for g, i in self.traits_db.items() if i == trait_id), trait_id)
            self.selected_tags_row.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(f"Req: {game_name}", size=10, weight=ft.FontWeight.BOLD),
                        ft.IconButton(
                            ft.Icons.CLOSE, icon_size=10, icon_color=ft.Colors.WHITE,
                            data=("req", trait_id), on_click=self.remove_selected_trait,
                            style=ft.ButtonStyle(padding=0)
                        )
                    ], spacing=1, tight=True),
                    bgcolor=ft.Colors.GREEN_900, border_radius=4,
                    padding=ft.Padding(left=6, right=2, top=4, bottom=4)
                )
            )

        # Preferred traits (Purple)
        for trait_id in self.temp_pref_traits:
            game_name = next((g for g, i in self.traits_db.items() if i == trait_id), trait_id)
            self.selected_tags_row.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(f"Pref: {game_name}", size=10, weight=ft.FontWeight.BOLD),
                        ft.IconButton(
                            ft.Icons.CLOSE, icon_size=10, icon_color=ft.Colors.WHITE,
                            data=("pref", trait_id), on_click=self.remove_selected_trait,
                            style=ft.ButtonStyle(padding=0)
                        )
                    ], spacing=1, tight=True),
                    bgcolor=ft.Colors.PURPLE_900, border_radius=4,
                    padding=ft.Padding(left=6, right=2, top=4, bottom=4)
                )
            )
        self.on_update_callback()

    def remove_selected_trait(self, e):
        list_type, trait_id = e.control.data
        if list_type == "req":
            self.temp_req_traits.remove(trait_id)
        else:
            self.temp_pref_traits.remove(trait_id)
        self.refresh_selected_tags()
        self.refresh_search_results(self.search_input.value)

    def refresh_search_results(self, query: str = ""):
        query = query.strip().lower()
        self.search_results_col.controls.clear()
        
        matches_found = 0
        for game_name, internal_id in self.traits_db.items():
            if not query or (query in game_name.lower() or query in internal_id.lower()):
                is_req = internal_id in self.temp_req_traits
                is_pref = internal_id in self.temp_pref_traits
                
                if not is_req and not is_pref:
                    self.search_results_col.controls.append(
                        ft.Row([
                            ft.Text(f"{game_name} ({internal_id})", size=12, expand=True),
                            ft.TextButton(
                                "Add Req", style=ft.ButtonStyle(color=ft.Colors.GREEN_400),
                                on_click=lambda e, tid=internal_id: self.add_trait_to_state(tid, "req")
                            ),
                            ft.TextButton(
                                "Add Pref", style=ft.ButtonStyle(color=ft.Colors.PURPLE_400),
                                on_click=lambda e, tid=internal_id: self.add_trait_to_state(tid, "pref")
                            )
                        ], spacing=10)
                    )
                    matches_found += 1
                        
        if matches_found == 0:
            self.search_results_col.controls.append(
                ft.Text("No matching traits found.", size=12, italic=True, color=ft.Colors.WHITE38)
            )
        self.on_update_callback()

    def add_trait_to_state(self, trait_id: str, list_type: str):
        if list_type == "req":
            self.temp_req_traits.append(trait_id)
        else:
            self.temp_pref_traits.append(trait_id)
        
        self.search_input.value = ""
        self.refresh_search_results("")
        self.refresh_selected_tags()

    def get_values(self) -> tuple[list[str], list[str]]:
        return list(self.temp_req_traits), list(self.temp_pref_traits)