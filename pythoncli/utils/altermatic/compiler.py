# controllers/altermatic/compiler.py
import os
from utils.altermatic_helper import compile_unified_altermatic_json

class AltermaticCompiler:
    def __init__(self, controller):
        self.c = controller

    def deploy_to_game(self, current_char_id: str, fmodel_target_dir: str):
        """Compiles the memory states and deploys the JSON configurations directly to the game SwapJSON folder."""
        palworld_exe = self.c.settings.get("palworld_exe", "")
        if palworld_exe and os.path.exists(palworld_exe):
            swap_json_dir = os.path.join(os.path.dirname(palworld_exe), "Pal", "Content", "Paks", "~Mods", "SwapJSON")
            success, msg = compile_unified_altermatic_json(current_char_id, fmodel_target_dir, swap_json_dir)
            if success:
                self.c.view.write_log(f"Auto-deployed updated Altermatic JSON config: {msg}", "success")
            else:
                self.c.view.write_log(f"Auto-deployment failed: {msg}", "error")