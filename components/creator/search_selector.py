# components/creator/search_selector.py
import flet as ft

class SearchSelectorDialog:
    def __init__(self, page: ft.Page):
        self.page = page
        self.on_select = None
        self.dataset = {}
        self.pal_elements = []
        
        self.search_input = ft.TextField(label="Search...", prefix_icon=ft.Icons.SEARCH)
        self.results_list = ft.ListView(height=250, spacing=2, scroll=ft.ScrollMode.AUTO)
        self.cancel_btn = ft.TextButton("Cancel", on_click=self.close_dialog)

        # Pal matching checkbox (Instantiated without lambdas to guarantee event binding)
        self.pal_only_checkbox = ft.Checkbox(
            label="Match Pal Elements Only",
            value=False,
            visible=False
        )
        self.pal_only_checkbox.on_change = self._on_pal_only_change
        
        # Dynamic filter dropdowns (Instantiated without lambdas to guarantee event binding)
        self.element_filter = ft.Dropdown(
            label="Filter by Element",
            width=180,
            options=[ft.dropdown.Option("All")],
            value="All"
        )
        self.element_filter.on_change = self._on_element_filter_change

        self.category_filter = ft.Dropdown(
            label="Filter by Type",
            width=180,
            options=[ft.dropdown.Option("All")],
            value="All"
        )
        self.category_filter.on_change = self._on_category_filter_change

        self.filters_row = ft.Row([self.element_filter, self.category_filter], visible=False, spacing=10)
        
        self.dialog = ft.AlertDialog(
            modal=True,
            content=ft.Column([self.search_input, self.pal_only_checkbox, self.filters_row, self.results_list], tight=True, spacing=15, width=400),
            actions=[self.cancel_btn]
        )
        self.search_input.on_change = self._on_search_input_change

    def _on_element_filter_change(self, e):
        """Strongly-bound event handler for element dropdown selections."""
        self.populate_results(self.search_input.value)

    def _on_category_filter_change(self, e):
        """Strongly-bound event handler for type dropdown selections."""
        self.populate_results(self.search_input.value)

    def _on_pal_only_change(self, e):
        """Strongly-bound event handler for the Pal element matching checkbox."""
        self.populate_results(self.search_input.value)

    def _on_search_input_change(self, e):
        """Strongly-bound event handler for the search text field."""
        self.populate_results(self.search_input.value)

    def show(self, title: str, dataset_dict: dict, on_select_callback, pal_elements: list | None = None):
        self.on_select = on_select_callback
        self.dataset = dataset_dict
        self.dialog.title = ft.Text(title)
        self.search_input.label = f"Search {title}..."
        self.search_input.value = ""
        self.pal_elements = pal_elements or []
        
        is_enriched = any(isinstance(v, dict) and ("element" in v or "category" in v) for v in dataset_dict.values())
        self.filters_row.visible = is_enriched
        
        # Dynamically configures the Pal Affinity match filter checkbox
        if is_enriched and self.pal_elements and any(el != "None" for el in self.pal_elements):
            clean_els = [el for el in self.pal_elements if el != "None"]
            self.pal_only_checkbox.label = f"Match Pal Elements ({', '.join(clean_els)})"
            self.pal_only_checkbox.visible = True
            self.pal_only_checkbox.value = True
        else:
            self.pal_only_checkbox.visible = False
            self.pal_only_checkbox.value = False
        
        if is_enriched:
            elements = set()
            categories = set()
            for v in dataset_dict.values():
                if isinstance(v, dict):
                    if "element" in v and v["element"]: 
                        elements.add(v["element"])
                    if "category" in v and v["category"]: 
                        categories.add(v["category"])
            
            self.element_filter.options = [ft.dropdown.Option("All", "All Elements")] + [
                ft.dropdown.Option(el, el) for el in sorted(list(elements))
            ]
            self.element_filter.value = "All"
            
            self.category_filter.options = [ft.dropdown.Option("All", "All Types")] + [
                ft.dropdown.Option(cat, cat) for cat in sorted(list(categories))
            ]
            self.category_filter.value = "All"
        
        setattr(self.dialog, "open", True)
        try:
            if hasattr(self.page, "show_dialog"):
                getattr(self.page, "show_dialog")(self.dialog)
            elif hasattr(self.page, "open"):
                getattr(self.page, "open")(self.dialog)
            else:
                setattr(self.page, "dialog", self.dialog)
                self.page.update()
        except Exception:
            pass

        self.populate_results("")

    def populate_results(self, query=""):
        query_clean = query.strip().lower()
        self.results_list.controls.clear()
        matches = 0
        max_render_limit = 35 
        
        show_pal_only = self.pal_only_checkbox.value if self.pal_only_checkbox.visible else False
        selected_element = self.element_filter.value if self.filters_row.visible else "All"
        selected_category = self.category_filter.value if self.filters_row.visible else "All"
        
        for friendly_name, val in self.dataset.items():
            actual_id = val["id"] if isinstance(val, dict) else val
            element = val.get("element", "None") if isinstance(val, dict) else "None"
            category = val.get("category", "None") if isinstance(val, dict) else "None"
            
            # Match elements filter rules
            if show_pal_only and self.pal_elements:
                if element not in self.pal_elements:
                    continue
            
            if selected_element != "All" and element != selected_element:
                continue
            if selected_category != "All" and category != selected_category:
                continue
                
            if not query_clean or (query_clean in friendly_name.lower() or query_clean in actual_id.lower()):
                if matches < max_render_limit:
                    subtitle_str = f"ID: {actual_id}"
                    if isinstance(val, dict):
                        subtitle_str += f" | {element} | {category}"
                        
                    self.results_list.controls.append(
                        ft.ListTile(
                            title=ft.Text(friendly_name, size=12),
                            subtitle=ft.Text(subtitle_str, size=10, color=ft.Colors.WHITE38),
                            on_click=lambda ev, i_id=val, f_name=friendly_name: self.execute_select(i_id, f_name),
                            dense=True
                        )
                    )
                matches += 1
                
        if matches == 0:
            self.results_list.controls.append(
                ft.Text("No entries match criteria.", italic=True, size=12, color=ft.Colors.WHITE38)
            )
        elif matches > max_render_limit:
            self.results_list.controls.append(
                ft.Text(f"...and {matches - max_render_limit} more entries. Type to filter.", italic=True, size=11, color=ft.Colors.CYAN_400)
            )
            
        try: 
            # Force target-level updates to guarantee synchronization
            if self.filters_row.visible:
                self.element_filter.update()
                self.category_filter.update()
            self.pal_only_checkbox.update()
            self.results_list.update()
            self.dialog.update()
        except Exception: 
            pass

    def close_dialog(self, e=None):
        setattr(self.dialog, "open", False)
        try:
            if hasattr(self.page, "pop_dialog"):
                getattr(self.page, "pop_dialog")()
            elif hasattr(self.page, "close"):
                getattr(self.page, "close")(self.dialog)
            else:
                self.page.update()
        except Exception:
            pass

    def execute_select(self, val, friendly_name):
        actual_id = val["id"] if isinstance(val, dict) else val
        self.close_dialog()
        if self.on_select:
            self.on_select(actual_id, friendly_name)