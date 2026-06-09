import re
from pathlib import Path

content = Path("views/mods_view.py").read_text()

# Add import
if "from ui_client.dispatcher import PalBakerCLI" not in content:
    content = content.replace("from controllers.mods import ModsController", "from controllers.mods import ModsController\nfrom ui_client.dispatcher import PalBakerCLI")

# Initialize CLI
if "self.cli = PalBakerCLI()" not in content:
    content = content.replace("self.controller = ModsController(self, settings)", "self.controller = ModsController(self, settings)\n        self.cli = PalBakerCLI()")

# Replace refresh_mods
old_refresh = """    def refresh_mods(self, scan_disk: bool = True):
        self.controller.refresh_mods(scan_disk)"""

new_refresh = """    def refresh_mods(self, scan_disk: bool = True):
        self.controller.show_mapped = bool(self.settings.get("show_mapped", False))
        if scan_disk:
            self.set_refresh_state(loading=True)
            async def worker():
                try:
                    response = await self.cli.list_mods(show_unextracted=True) # Always fetch all, filter locally
                    if response.get("status") == "success":
                        self.controller.raw_mods = response.get("data", [])
                        self.clear_ui_cache()
                    else:
                        self.write_log(f"CLI Error: {response.get('message')}", "error")
                except Exception as e:
                    self.write_log(f"Disk scan encountered an error: {e}", "error")
                finally:
                    self.set_refresh_state(loading=False)
                    self.controller.apply_filters()
            self.run_async_task(worker)
        else:
            self.controller.apply_filters()"""

content = content.replace(old_refresh, new_refresh)
Path("views/mods_view.py").write_text(content)
print("Done")