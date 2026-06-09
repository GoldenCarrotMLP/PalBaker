import flet as ft  # type: ignore

class PathPicker:
    # FIXED: Removed the narrow ': str' type constraint from the 'icon' parameter 
    # to allow Flet's native 'IconData' constants without causing type checker errors.
    def __init__(self, label: str, value: str, icon, on_browse_click, on_change=None):
        self.on_change = on_change
        self.text_field = ft.TextField(
            label=label, 
            value=value, 
            expand=True,
            on_change=self._on_text_change
        )
        self.button = ft.IconButton(icon, on_click=on_browse_click)
        
        # Expose the layout tree
        self.view = ft.Row([self.text_field, self.button])

    def _on_text_change(self, e):
        # Update the internal value when typed manually
        self.text_field.value = e.control.value
        if self.on_change:
            self.on_change(e)

    def get_value(self) -> str:
        return str(self.text_field.value)

    def set_value(self, value: str):
        if self.text_field.value != value:
            self.text_field.value = value
            try:
                self.text_field.update()
            except Exception:
                pass
            if self.on_change:
                self.on_change(None)
