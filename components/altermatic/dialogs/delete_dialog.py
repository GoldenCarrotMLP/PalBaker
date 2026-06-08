# components/altermatic/dialogs/delete_dialog.py
import flet as ft
from .utils import show_dialog_safe, close_dialog_safe

class AltermaticDeleteDialog:
    def __init__(self, page: ft.Page):
        self.page = page
        self.on_confirm = None
        self.cancel_btn = ft.TextButton("Cancel", on_click=self.close_dialog)
        self.delete_btn = ft.TextButton("Delete", on_click=self.execute_delete, style=ft.ButtonStyle(color=ft.Colors.RED))
        
        self.content_text = ft.Text("")
        
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Deletion"),
            content=self.content_text,
            actions=[self.cancel_btn, self.delete_btn]
        )

    def show(self, message: str, on_confirm_callback):
        self.on_confirm = on_confirm_callback
        self.content_text.value = message
        # FIXED: Bypasses Pylance attribute access errors
        setattr(self.delete_btn, "text", "Delete")
        self.delete_btn.disabled = False
        show_dialog_safe(self.page, self.dialog)

    def close_dialog(self, e=None):
        close_dialog_safe(self.page, self.dialog)

    def execute_delete(self, e):
        self.delete_btn.disabled = True
        # FIXED: Bypasses Pylance attribute access errors
        setattr(self.delete_btn, "text", "Closing...")
        try: self.dialog.update()
        except Exception: pass
        
        close_dialog_safe(self.page, self.dialog)
        
        if self.on_confirm:
            self.on_confirm()