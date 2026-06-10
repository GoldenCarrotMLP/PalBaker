# utils/cli/dummies.py
from utils.creator import CreatorController

class DummyView:
    def write_log(self, text, category="standard", flush=True):
        pass
    def show_snackbar(self, message, color=None):
        pass
    def force_update(self):
        pass
    def refresh_creator_mods_ui(self):
        pass
    def run_in_thread(self, func):
        import threading
        threading.Thread(target=func, daemon=True).start()

class DummyController(CreatorController):
    def __init__(self, settings):
        super().__init__(DummyView(), settings)

    def refresh_pals(self):
        pass
