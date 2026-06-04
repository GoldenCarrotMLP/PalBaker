# components/creator/search_selector.py
import flet as ft

class SearchSelectorDialog:
    def __init__(self, page: ft.Page):
        self.page = page
        self.on_select = None
        self.dataset = {}
        
        self.search_input = ft.TextField(label="Search...", prefix_icon=ft.Icons.SEARCH)
        self.results_list = ft.ListView(height=250, spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        
        self.cancel_btn = ft.TextButton("Cancel", on_click=self.close_dialog)
        
        self.dialog = ft.AlertDialog(
            modal=True,
            content=ft.Column([self.search_input, self.results_list], tight=True, spacing=15, width=400),
            actions=[self.cancel_btn]
        )
        self.search_input.on_change = lambda e: self.populate_results(self.search_input.value)

    def show(self, title: str, dataset_dict: dict, on_select_callback):
        self.on_select = on_select_callback
        self.dataset = dataset_dict
        self.dialog.title = ft.Text(title)
        self.search_input.label = f"Search {title}..."
        self.search_input.value = ""
        
        self.populate_results("")
        self.dialog.open = True
        
        try:
            if hasattr(self.page, "show_dialog"):
                self.page.show_dialog(self.dialog)
            elif hasattr(self.page, "open"):
                self.page.open(self.dialog)
            else:
                self.page.dialog = self.dialog
                self.page.update()
        except Exception:
            pass

    def populate_results(self, query=""):
        query_clean = query.strip().lower()
        self.results_list.controls.clear()
        matches = 0
        
        for friendly_name, internal_id in self.dataset.items():
            if not query_clean or (query_clean in friendly_name.lower() or query_clean in internal_id.lower()):
                self.results_list.controls.append(
                    ft.ListTile(
                        title=ft.Text(friendly_name, size=12),
                        subtitle=ft.Text(internal_id, size=10, color=ft.Colors.WHITE38),
                        on_click=lambda ev, i_id=internal_id, f_name=friendly_name: self.execute_select(i_id, f_name),
                        dense=True
                    )
                )
                matches += 1
                
        if matches == 0:
            self.results_list.controls.append(
                ft.Text("No entries match search query.", italic=True, size=12, color=ft.Colors.WHITE38)
            )
        try: self.dialog.update()
        except Exception: pass

    def close_dialog(self, e=None):
        self.dialog.open = False
        try:
            if hasattr(self.page, "pop_dialog"):
                self.page.pop_dialog()
            elif hasattr(self.page, "close"):
                self.page.close(self.dialog)
            else:
                self.page.update()
        except Exception:
            pass

    def execute_select(self, internal_id, friendly_name):
        self.close_dialog()
        if self.on_select:
            self.on_select(internal_id, friendly_name)