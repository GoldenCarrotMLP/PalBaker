# views/creator_view.py
import flet as ft  # type: ignore
import os
from ui_client.dispatcher import PalBakerCLI
from components.creator.pal_card import PalCreatorCard
from components.creator.add_dialog import AddPalDialog
from components.creator.search_selector import SearchSelectorDialog

class CreatorView:
    def __init__(self, page: ft.Page, settings: dict):
        self.main_page = page
        self.settings = settings
        
        self.cli = PalBakerCLI()
        
        # Local view-managed caches to fully bypass CreatorController instantiation!
        self.active_skills_cache = {}
        self.passive_skills_cache = {}
        self.partner_skills_cache = {}
        self.coop_passives_cache = {}  
        self.monster_spawners_cache = {}
        self.monster_spawners_default_map = {}
        self.templates_cache = {}
        self.learnsets_cache = {}
        self.camera_offsets_cache = {}
        self.custom_pals = []

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
        self.add_pal_dialog = AddPalDialog(self.main_page, self.templates_cache, self.handle_create_pal_confirm)
        self.search_selector_dialog = SearchSelectorDialog(self.main_page)

        self.editing_states = {}
        
        # Load index caches asynchronously via UI Dispatcher
        self.run_async_task(self.load_index_caches)

    async def load_index_caches(self):
        caches = await self.cli.get_skills_cache()
        self.main_page.pal_names = caches.get("pal_names", {})
        self.active_skills_cache.update(caches.get("active_skills", {}))
        self.passive_skills_cache.update(caches.get("passive_skills", {}))
        self.coop_passives_cache.update(caches.get("coop_passives", {}))
        self.partner_skills_cache.update(caches.get("partner_skills", {}))
        self.templates_cache.update(caches.get("templates", {}))
        self.learnsets_cache.update(caches.get("learnsets", {}))
        self.monster_spawners_cache.update(caches.get("monster_spawners", {}))
        self.monster_spawners_default_map.update(caches.get("monster_spawners_default_map", {}))
        self.camera_offsets_cache.update(caches.get("camera_offsets", {}))
        
        # Load the initial standalone custom Pals list on startup
        await self._async_refresh_pals()

    def run_in_thread(self, func):
        self.main_page.run_thread(func)

    def run_async_task(self, func, *args):
        self.main_page.run_task(func, *args)

    def refresh_pals(self):
        self.render_pals(self.custom_pals)

    def refresh_creator_mods_ui(self):
        self.render_pals(self.custom_pals)

    def handle_refresh_bp(self, pal_id: str):
        self.add_pal_btn.disabled = True
        self.force_update()
        self.run_async_task(self._async_refresh_bp, pal_id)

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
                active_skills=self.active_skills_cache,
                passive_skills=self.passive_skills_cache,
                partner_skills=self.partner_skills_cache,
                coop_passives=self.coop_passives_cache,
                monster_spawners=self.monster_spawners_cache,
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
                self.custom_pals = result.get("data", [])
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
            self.main_page.mods_view.write_log(text, category)  # type: ignore

    def force_update(self):
        try: self.view.update()
        except Exception: pass