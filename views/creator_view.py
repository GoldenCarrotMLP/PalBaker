# views/creator_view.py
import flet as ft  # type: ignore
import os
from controllers.creator import CreatorController
from ui_client.dispatcher import PalBakerCLI
from components.creator.pal_card import PalCreatorCard
from components.creator.add_dialog import AddPalDialog
from components.creator.search_selector import SearchSelectorDialog

class CreatorView:
    def __init__(self, page: ft.Page, settings: dict):
        self.main_page = page
        self.settings = settings
        
        self.controller = CreatorController(self, settings)
        self.cli = PalBakerCLI()

        # Dynamic dialogs
        self.add_pal_btn = ft.FloatingActionButton(
            icon=ft.Icons.ADD, 
            tooltip="Add Brand New Standalone Pal", 
            on_click=self.show_add_dialog,
            bgcolor=ft.Colors.CYAN_700
        )
        
        self.pals_list = ft.ListView(expand=True, spacing=10)
        
        self.view = ft.Column(
            expand=True,
            controls=[
                ft.Row([
                    ft.Text("Pal Creator Panel", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_400),
                    self.add_pal_btn
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text("Instantiate standalone custom Pals using PalSchema JSON injection. These Pals inherit animations and skeletons from their parent template.", size=12, color=ft.Colors.WHITE54),
                ft.Divider(height=10, color=ft.Colors.WHITE10),
                ft.Container(
                    content=self.pals_list,
                    expand=True,
                    border=ft.Border.all(1, ft.Colors.WHITE10),
                    border_radius=10,
                    padding=10
                )
            ]
        )

        # Instantiated sub-component dialog views
        self.add_pal_dialog = AddPalDialog(self.main_page, self.controller.templates_cache, self.handle_create_pal_confirm)
        self.search_selector_dialog = SearchSelectorDialog(self.main_page)

        self.editing_states = {}

    def run_in_thread(self, func):
        self.main_page.run_thread(func)

    def run_async_task(self, func, *args):
        self.main_page.run_task(func, *args)

    def refresh_pals(self):
        self.controller.refresh_pals()

    def refresh_creator_mods_ui(self):
        self.render_pals(self.controller.custom_pals)

    def handle_refresh_bp(self, pal_id: str):
        self.add_pal_btn.disabled = True
        self.force_update()
        self.controller.refresh_actor_blueprint(pal_id)

    def render_pals(self, pals_data: list[dict]):
        self.pals_list.controls.clear()
        self.add_pal_btn.disabled = False
        
        if not pals_data:
            self.pals_list.controls.append(
                ft.Container(
                    content=ft.Text("No custom Pals created yet. Click [+] to instantiate one.", italic=True, size=13),
                    alignment=ft.Alignment.CENTER,
                    padding=20
                )
            )
            self.force_update()
            return

        for p in pals_data:
            card = PalCreatorCard(
                page=self.main_page,
                pal_data=p,
                settings=self.settings,
                active_skills=self.controller.active_skills_cache,
                passive_skills=self.controller.passive_skills_cache,
                partner_skills=self.controller.partner_skills_cache,
                coop_passives=self.controller.coop_passives_cache,
                monster_spawners=self.controller.monster_spawners_cache,
                is_expanded=self.editing_states.get(p["CharacterID"], False),
                on_toggle=self.toggle_card_editor,
                on_save=self.handle_save_pal_confirm,
                on_delete=self.handle_delete_pal_confirm,
                show_search_dialog_callback=self.show_search_selector_dialog,
                on_refresh_bp=self.handle_refresh_bp
            )
            self.pals_list.controls.append(card.view)

        self.force_update()

    def toggle_card_editor(self, pal_id: str):
        self.editing_states[pal_id] = not self.editing_states.get(pal_id, False)
        self.refresh_pals()

    def show_search_selector_dialog(self, title: str, dataset_dict: dict, on_select_callback, pal_elements: list | None = None):
        self.search_selector_dialog.show(title, dataset_dict, on_select_callback, pal_elements)

    def show_add_dialog(self, e):
        self.add_pal_dialog.show()

    def handle_create_pal_confirm(self, pal_id: str, template_id: str):
        self.add_pal_btn.disabled = True
        self.force_update()
        self.run_async_task(self._async_create_pal, pal_id, template_id)

    async def _async_create_pal(self, pal_id: str, template_id: str):
        try:
            result = await self.cli.creator_add(pal_id, template_id)
            if result.get("status") == "success":
                self.show_snackbar(f"Created Pal: {pal_id}", ft.Colors.GREEN)
                await self._async_refresh_pals()
            else:
                self.show_snackbar(f"Error: {result.get('message', 'Unknown error')}", ft.Colors.RED)
        except Exception as e:
            self.show_snackbar(f"Error: {str(e)}", ft.Colors.RED)
        finally:
            self.add_pal_btn.disabled = False
            self.force_update()

    def handle_save_pal_confirm(self, pal_id: str, updated_data: dict):
        self.editing_states[pal_id] = False
        self.add_pal_btn.disabled = True
        self.force_update()
        self.run_async_task(self._async_save_pal, pal_id, updated_data)

    async def _async_save_pal(self, pal_id: str, updated_data: dict):
        try:
            result = await self.cli.creator_update(pal_id, updated_data)
            if result.get("status") == "success":
                self.show_snackbar(f"Saved Pal: {pal_id}", ft.Colors.GREEN)
                await self._async_refresh_pals()
            else:
                self.show_snackbar(f"Error: {result.get('message', 'Unknown error')}", ft.Colors.RED)
        except Exception as e:
            self.show_snackbar(f"Error: {str(e)}", ft.Colors.RED)
        finally:
            self.add_pal_btn.disabled = False
            self.force_update()

    def handle_delete_pal_confirm(self, pal_id: str):
        self.editing_states[pal_id] = False
        self.add_pal_btn.disabled = True
        self.force_update()
        self.run_async_task(self._async_delete_pal, pal_id)

    async def _async_delete_pal(self, pal_id: str):
        try:
            result = await self.cli.creator_delete(pal_id)
            if result.get("status") == "success":
                self.show_snackbar(f"Deleted Pal: {pal_id}", ft.Colors.GREEN)
                await self._async_refresh_pals()
            else:
                self.show_snackbar(f"Error: {result.get('message', 'Unknown error')}", ft.Colors.RED)
        except Exception as e:
            self.show_snackbar(f"Error: {str(e)}", ft.Colors.RED)
        finally:
            self.add_pal_btn.disabled = False
            self.force_update()

    def handle_refresh_bp(self, pal_id: str):
        self.add_pal_btn.disabled = True
        self.force_update()
        self.run_async_task(self._async_refresh_bp, pal_id)

    async def _async_refresh_bp(self, pal_id: str):
        try:
            result = await self.cli.refresh_actor_blueprint(pal_id)
            if result.get("status") == "success":
                self.show_snackbar(f"Refreshed Blueprint: {pal_id}", ft.Colors.GREEN)
            else:
                self.show_snackbar(f"Error: {result.get('message', 'Unknown error')}", ft.Colors.RED)
        except Exception as e:
            self.show_snackbar(f"Error: {str(e)}", ft.Colors.RED)
        finally:
            self.add_pal_btn.disabled = False
            self.force_update()

    async def _async_refresh_pals(self):
        """Refresh the pals list from CLI."""
        try:
            result = await self.cli.creator_list()
            if result.get("status") == "success":
                self.controller.custom_pals = result.get("data", [])
                self.refresh_pals()
            else:
                self.show_snackbar(f"Error refreshing pals: {result.get('message', 'Unknown error')}", ft.Colors.RED)
        except Exception as e:
            self.show_snackbar(f"Error: {str(e)}", ft.Colors.RED)

    def show_dialog(self, dlg: ft.AlertDialog):
        self.current_dialog = dlg
        if hasattr(self.main_page, "show_dialog"):
            getattr(self.main_page, "show_dialog")(dlg)
        elif hasattr(self.main_page, "open"):
            getattr(self.main_page, "open")(dlg)
        else:
            setattr(self.main_page, "dialog", dlg)
            setattr(dlg, "open", True)
            self.main_page.update()

    def pop_dialog(self):
        if hasattr(self.main_page, "pop_dialog"):
            try: getattr(self.main_page, "pop_dialog")(); return
            except Exception: pass
            
        dlg = getattr(self, "current_dialog", getattr(self.main_page, "dialog", None))
        if dlg:
            if hasattr(self.main_page, "close"):
                try: getattr(self.main_page, "close")(dlg); return
                except Exception: pass
            
            setattr(dlg, "open", False)
            self.main_page.update()

    def show_snackbar(self, message: str, color):
        self.main_page.overlay.append(ft.SnackBar(ft.Text(message, color=color), open=True))
        self.main_page.update()

    def write_log(self, text: str, category: str = "standard"):
        if hasattr(self.main_page, "mods_view"):
            self.main_page.mods_view.write_log(text, category)

    def force_update(self):
        try: self.view.update()
        except Exception: pass