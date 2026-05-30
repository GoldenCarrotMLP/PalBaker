# components/mods/mod_details.py
import flet as ft

class ModDetails:
    def __init__(self, mod_data: dict, on_pick_icon):
        self.mod_data = mod_data
        self.on_pick_icon = on_pick_icon
        
        has_icon = mod_data.get("has_icon", False)
        icon_path = mod_data.get("icon_path", "")
        
        if has_icon and icon_path:
            content = ft.Image(src=icon_path, width=64, height=64, fit=ft.BoxFit.CONTAIN)
        else:
            content = ft.Icon(ft.Icons.ADD_PHOTO_ALTERNATE, size=32, color=ft.Colors.WHITE54)

        self.icon_slot = ft.Container(
            content=content,
            width=64,
            height=64,
            border=ft.Border.all(1, ft.Colors.WHITE24),
            border_radius=8,
            ink=True,
            on_click=self.handle_icon_click,  # FIX: Reference the async method directly
            tooltip="Click to set custom Pal Icon"
        )
        
        self.view = ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text("Pal Icon", size=12, weight=ft.FontWeight.BOLD),
                    self.icon_slot
                ])
            ]),
            padding=ft.Padding(left=40, top=10, right=10, bottom=10),
            bgcolor=ft.Colors.WHITE10,
            border_radius=8
        )

    async def handle_icon_click(self, e):
        """
        Async event handler natively recognized and awaited by Flet's loop.
        Cleanly forwards the click and awaits the parent's icon picker.
        """
        await self.on_pick_icon(self.mod_data)