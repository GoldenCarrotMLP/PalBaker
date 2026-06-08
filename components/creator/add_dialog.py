# components/creator/add_dialog.py
import flet as ft
import re
from utils.names import get_localized_name

class AddPalDialog:
    def __init__(self, page: ft.Page, templates_cache: dict, on_confirm_callback):
        self.page = page
        self.templates = templates_cache
        self.on_confirm = on_confirm_callback
        
        self.selected_parent_id = ["WeaselDragon"]
        if self.templates:
            self.selected_parent_id[0] = list(self.templates.keys())[0]

        self.pal_id_input = ft.TextField(label="New Standalone Pal ID", hint_text="e.g., Furret")
        self.selected_parent_text = ft.Text(
            f"Selected: {get_localized_name(self.selected_parent_id[0])} ({self.selected_parent_id[0]})", 
            weight=ft.FontWeight.BOLD, 
            color=ft.Colors.CYAN_400
        )
        
        self.search_input = ft.TextField(
            label="Fuzzy Search Parent Template...",
            prefix_icon=ft.Icons.SEARCH,
            hint_text="e.g., Anubis, Lamball, Chillet"
        )
        
        self.results_list = ft.ListView(
            height=220,
            spacing=2,
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )
        
        self.search_input.on_change = lambda e: self.populate_results(self.search_input.value)
        
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Instantiate Custom Pal"),
            content=ft.Column([
                self.pal_id_input,
                self.selected_parent_text,
                self.search_input,
                self.results_list
            ], tight=True, spacing=15, width=420),
            actions=[
                ft.TextButton("Cancel", on_click=self.close_dialog),
                ft.TextButton("Create", on_click=self.execute_create, style=ft.ButtonStyle(color=ft.Colors.CYAN_400))
            ]
        )

    def show(self):
        self.pal_id_input.value = ""
        self.search_input.value = ""
        
        if self.templates:
            self.selected_parent_id[0] = list(self.templates.keys())[0]
            self.selected_parent_text.value = f"Selected: {get_localized_name(self.selected_parent_id[0])} ({self.selected_parent_id[0]})"
        
        self.populate_results("")
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

    def populate_results(self, query=""):
        query_clean = query.strip().lower()
        self.results_list.controls.clear()
        matches = 0
        for k in self.templates.keys():
            localized = get_localized_name(k)
            if not query_clean or (query_clean in k.lower() or query_clean in localized.lower()):
                self.results_list.controls.append(
                    ft.ListTile(
                        title=ft.Text(f"{localized} ({k})", size=12),
                        on_click=lambda ev, tid=k, tlbl=localized: self.select_template(tid, tlbl),
                        hover_color=ft.Colors.WHITE10,
                        dense=True
                    )
                )
                matches += 1
        if matches == 0:
            self.results_list.controls.append(
                ft.Text("No templates match search query.", italic=True, size=12, color=ft.Colors.WHITE38)
            )
        try: self.dialog.update()
        except Exception: pass

    def select_template(self, t_id, t_lbl):
        self.selected_parent_id[0] = t_id
        self.selected_parent_text.value = f"Selected: {t_lbl} ({t_id})"
        try: self.dialog.update()
        except Exception: pass

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

    def execute_create(self, e):
        val = self.pal_id_input.value.strip() if self.pal_id_input.value else ""
        if not val:
            self.page.overlay.append(ft.SnackBar(ft.Text("Standalone Pal ID is required.", color=ft.Colors.RED_400), open=True))
            self.page.update()
            return
        self.close_dialog()
        if self.on_confirm:
            self.on_confirm(val, self.selected_parent_id[0])