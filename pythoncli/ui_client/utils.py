# ui_client/utils.py
import functools
import flet as ft  # type: ignore

def cli_action(func):
    """
    Universal decorator for Flet View event handlers.
    Automatically manages button disabling, icon indicators, and global spinners.
    """
    @functools.wraps(func)
    async def wrapper(self, e, *args, **kwargs):
        # 1. Identify the view's global spinner
        spinner = getattr(self, "refresh_spinner", None)
        if spinner:
            spinner.visible = True
            try:
                spinner.update()
            except Exception:
                pass

        # 2. Identify the clicked button/control
        control = getattr(e, "control", None)
        orig_disabled = False
        orig_icon = None
        orig_text = None

        if control:
            orig_disabled = getattr(control, "disabled", False)
            control.disabled = True
            
            # Visual feedback: Change button icon to hourglass/sync while working
            if hasattr(control, "icon"):
                orig_icon = control.icon
                control.icon = ft.Icons.HOURGLASS_EMPTY_ROUNDED
                
            # Visual feedback: If the button has an inner text object, we can note it
            if hasattr(control, "text") and isinstance(control.text, str):
                orig_text = control.text
                
            try:
                control.update()
            except Exception:
                pass

        try:
            # 3. Execute the actual CLI-bound View method
            return await func(self, e, *args, **kwargs)
            
        finally:
            # 4. Safely restore the button state
            if control:
                control.disabled = orig_disabled
                if orig_icon is not None:
                    control.icon = orig_icon
                if orig_text is not None:
                    control.text = orig_text
                try:
                    control.update()
                except Exception:
                    pass

            # 5. Hide the global spinner
            if spinner:
                spinner.visible = False
                try:
                    spinner.update()
                except Exception:
                    pass

    return wrapper
