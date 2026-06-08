# components/altermatic/dialogs/add_dialog.py
import flet as ft
from .utils import show_dialog_safe, close_dialog_safe

class AltermaticAddDialog:
    def __init__(self, page: ft.Page):
        self.page = page
        self.on_confirm = None
        
        self.label_input = ft.TextField(label="New Variant Name/Label", hint_text="e.g., SFW_Bikini_T-Shirt")
        self.custom_mesh_switch = ft.Switch(label="Create a custom .blend file for this variant?", value=True)
        self.clone_source_dropdown = ft.Dropdown(label="Clone Skeleton Template From", value="base", visible=True)
        
        self.custom_mesh_switch.on_change = self.handle_switch_change
        
        self.cancel_btn = ft.TextButton("Cancel", on_click=self.close_dialog)
        self.create_btn = ft.TextButton("Create", on_click=self.execute_create)
        
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Add New Variant"),
            actions=[self.cancel_btn, self.create_btn],
            content=ft.Column([
                self.label_input,
                self.custom_mesh_switch,
                self.clone_source_dropdown
            ], tight=True, spacing=15)
        )

    def handle_switch_change(self, e):
        self.clone_source_dropdown.visible = self.custom_mesh_switch.value
        try: self.dialog.update()
        except Exception: pass

    def show(self, character_id: str, blend_files: list[str], on_confirm_callback):
        self.on_confirm = on_confirm_callback
        self.dialog.title = ft.Text(f"Add New {character_id} Variant")
        
        self.label_input.value = ""
        self.custom_mesh_switch.value = True
        self.clone_source_dropdown.visible = True
        
        dropdown_options = [ft.dropdown.Option("base", "base (Vanilla Canonical Mesh)")]
        for f in blend_files:
            clean_lbl = f
            prefix = f"{character_id}_"
            if clean_lbl.startswith(prefix):
                clean_lbl = clean_lbl[len(prefix):]
            dropdown_options.append(ft.dropdown.Option(f, f"Variant: {clean_lbl}"))
            
        self.clone_source_dropdown.options = dropdown_options
        self.clone_source_dropdown.value = "base"
        
        # FIXED: Bypasses Pylance attribute access errors
        setattr(self.create_btn, "text", "Create")
        self.create_btn.disabled = False
        
        show_dialog_safe(self.page, self.dialog)

    def close_dialog(self, e=None):
        close_dialog_safe(self.page, self.dialog)

    def execute_create(self, e):
        label_val = self.label_input.value.strip() if self.label_input.value else ""
        if not label_val:
            self.page.overlay.append(ft.SnackBar(ft.Text("Variant Label is required.", color=ft.Colors.RED_400), open=True))
            self.page.update()
            return
            
        self.create_btn.disabled = True
        # FIXED: Bypasses Pylance attribute access errors
        setattr(self.create_btn, "text", "Creating...")
        try: self.dialog.update()
        except Exception: pass
        
        close_dialog_safe(self.page, self.dialog)
        
        if self.on_confirm:
            self.on_confirm(label_val, self.custom_mesh_switch.value, self.clone_source_dropdown.value)