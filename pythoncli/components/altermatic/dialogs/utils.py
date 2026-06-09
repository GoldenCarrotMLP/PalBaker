# components/altermatic/dialogs/utils.py
import flet as ft  # type: ignore

def show_dialog_safe(page: ft.Page, dialog: ft.AlertDialog):
    if getattr(dialog, "open", False):
        return
    setattr(dialog, "open", True)
    if hasattr(dialog, "title") and isinstance(dialog.title, ft.Text):
        dialog.title.color = None
        
    try:
        if hasattr(page, "show_dialog"):
            getattr(page, "show_dialog")(dialog)
        elif hasattr(page, "open"):
            getattr(page, "open")(dialog)
        else:
            setattr(page, "dialog", dialog)
            page.update()
    except RuntimeError as e:
        if "already opened" not in str(e).lower():
            raise

def close_dialog_safe(page: ft.Page, dialog: ft.AlertDialog):
    setattr(dialog, "open", False)
    if hasattr(dialog, "title") and isinstance(dialog.title, ft.Text):
        dialog.title.color = ft.Colors.TRANSPARENT
        
    try:
        dialog.update()
    except Exception:
        pass

    try:
        if hasattr(page, "close"):
            getattr(page, "close")(dialog)
        elif hasattr(page, "pop_dialog"):
            getattr(page, "pop_dialog")()
    except Exception:
        pass
        
    try:
        page.update()
    except Exception:
        pass