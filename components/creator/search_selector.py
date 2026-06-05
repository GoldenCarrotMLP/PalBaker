# components/creator/search_selector.py
import flet as ft

class SearchSelectorDialog:
    def __init__(self, page: ft.Page):
        self.page = page
        self.on_select = None
        self.dataset = {}
        
        self.search_input = ft.TextField(label="Search...", prefix_icon=ft.Icons.SEARCH)
        self.results_list = ft.ListView(height=250, spacing=2, scroll=ft.ScrollMode.AUTO)
        
        self.cancel_btn = ft.TextButton("Cancel", on_click=self.close_dialog)
        
        self.dialog = ft.AlertDialog(
            modal=True,
            content=ft.Column([self.search_input, self.results_list], tight=True, spacing=15, width=400),
            actions=[self.cancel_btn]
        )
        self.search_input.on_change = lambda e: self.populate_results(self.search_input.value)

    def show(self, title: str, dataset_dict: dict, on_select_callback):
        print(f"\n[SearchSelector] ---> show() called for '{title}'", flush=True)
        print(f"[SearchSelector] Received dataset of type: {type(dataset_dict)} with length: {len(dataset_dict)}", flush=True)
        
        if not dataset_dict:
            print("[SearchSelector] ⚠️ WARNING: The dataset dictionary passed is completely empty!", flush=True)
            
        self.on_select = on_select_callback
        self.dataset = dataset_dict
        self.dialog.title = ft.Text(title)
        self.search_input.label = f"Search {title}..."
        self.search_input.value = ""
        
        # 1. Mount and open the dialog first so the Flet layout engine registers it
        self.dialog.open = True
        try:
            if hasattr(self.page, "show_dialog"):
                self.page.show_dialog(self.dialog)
            elif hasattr(self.page, "open"):
                self.page.open(self.dialog)
            else:
                self.page.dialog = self.dialog
                self.page.update()
            print("[SearchSelector] Dialog successfully mounted in UI.", flush=True)
        except Exception as e:
            print(f"[SearchSelector] ❌ ERROR opening dialog: {e}", flush=True)

        # 2. Populate and update the lists now that the dialog is fully mounted
        self.populate_results("")

    def populate_results(self, query=""):
        query_clean = query.strip().lower()
        print(f"[SearchSelector] Populating results for query: '{query_clean}'", flush=True)
        
        self.results_list.controls.clear()
        matches = 0
        max_render_limit = 35 
        
        for friendly_name, internal_id in self.dataset.items():
            if not query_clean or (query_clean in friendly_name.lower() or query_clean in internal_id.lower()):
                if matches < max_render_limit:
                    self.results_list.controls.append(
                        ft.ListTile(
                            title=ft.Text(friendly_name, size=12),
                            subtitle=ft.Text(internal_id, size=10, color=ft.Colors.WHITE38),
                            on_click=lambda ev, i_id=internal_id, f_name=friendly_name: self.execute_select(i_id, f_name),
                            dense=True
                        )
                    )
                matches += 1
                
        print(f"[SearchSelector] Total matches found in loop: {matches}", flush=True)
        
        if matches == 0:
            self.results_list.controls.append(
                ft.Text("No entries match search query.", italic=True, size=12, color=ft.Colors.WHITE38)
            )
        elif matches > max_render_limit:
            self.results_list.controls.append(
                ft.Text(f"...and {matches - max_render_limit} more locations. Type to filter.", italic=True, size=11, color=ft.Colors.CYAN_400)
            )
            
        try: 
            self.dialog.update()
            print("[SearchSelector] Dialog layout successfully updated and rendered.", flush=True)
        except Exception as e: 
            print(f"[SearchSelector] ❌ ERROR updating dialog layout: {e}", flush=True)

    def close_dialog(self, e=None):
        print("[SearchSelector] Closing dialog...", flush=True)
        self.dialog.open = False
        try:
            if hasattr(self.page, "pop_dialog"):
                self.page.pop_dialog()
            elif hasattr(self.page, "close"):
                self.page.close(self.dialog)
            else:
                self.page.update()
        except Exception as e:
            print(f"[SearchSelector] ❌ ERROR closing dialog: {e}", flush=True)

    def execute_select(self, internal_id, friendly_name):
        print(f"[SearchSelector] User selected: {friendly_name} ({internal_id})", flush=True)
        self.close_dialog()
        if self.on_select:
            self.on_select(internal_id, friendly_name)