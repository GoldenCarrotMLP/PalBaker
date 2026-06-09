# controllers/altermatic/manifest_manager.py
import os
import json

class ManifestManager:
    def __init__(self, controller):
        self.c = controller

    def get_manifest_path(self, current_char_id: str, fmodel_altermatic_dir: str) -> str:
        """Returns the absolute file path for a character's Altermatic manifest."""
        return os.path.join(fmodel_altermatic_dir, f"{current_char_id}_altermatic.json")

    def load_manifest(self, manifest_path: str) -> dict:
        """Loads and translates old array-based Altermatic structures to unified dictionary states."""
        manifest_data = {"is_altermatic_active": True, "variants": {}}
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f_man:
                    manifest_data = json.load(f_man)
                    if isinstance(manifest_data.get("variants"), list):
                        old_list = manifest_data["variants"]
                        manifest_data["variants"] = {item.get("label", "base"): item for item in old_list}
            except json.JSONDecodeError as e:
                self.c.view.write_log(f"ERROR: Manifest JSON corrupted ({os.path.basename(manifest_path)}): {e}. Initializing fresh state.", "error")
            except Exception as e:
                self.c.view.write_log(f"Warning: Failed to read manifest ({os.path.basename(manifest_path)}): {e}", "warning")
        return manifest_data

    def save_manifest(self, manifest_path: str, manifest_data: dict) -> bool:
        """Flushes the serializable manifest dictionary back to the workspace file on disk."""
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=4)
            return True
        except Exception as e:
            self.c.view.write_log(f"ERROR: Failed to save Altermatic manifest: {e}", "error")
            return False