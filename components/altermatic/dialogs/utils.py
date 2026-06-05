# components/altermatic/dialogs/utils.py
import flet as ft

def show_dialog_safe(page: ft.Page, dialog: ft.AlertDialog):
    if getattr(dialog, "open", False):
        return
    dialog.open = True
    if hasattr(dialog, "title") and isinstance(dialog.title, ft.Text):
        dialog.title.color = None
        
    try:
        if hasattr(page, "show_dialog"):
            page.show_dialog(dialog)
        elif hasattr(page, "open"):
            page.open(dialog)
        else:
            page.dialog = dialog
            page.update()
    except RuntimeError as e:
        if "already opened" not in str(e).lower():
            raise

def close_dialog_safe(page: ft.Page, dialog: ft.AlertDialog):
    dialog.open = False
    if hasattr(dialog, "title") and isinstance(dialog.title, ft.Text):
        dialog.title.color = ft.Colors.TRANSPARENT
        
    try:
        dialog.update()
    except Exception:
        pass

    try:
        if hasattr(page, "close"):
            page.close(dialog)
        elif hasattr(page, "pop_dialog"):
            page.pop_dialog()
    except Exception:
        pass
        
    try:
        page.update()
    except Exception:
        pass