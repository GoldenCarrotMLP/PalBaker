# controllers/altermatic/cloner.py
import os
import re
import shutil
import threading
from utils.altermatic_helper import sync_sidecar_metadata, get_blend_files_for_context

class AltermaticCloner:
    def __init__(self, controller):
        self.c = controller

    def show_add_dialog(self, mod_data: dict):
        current_char_id = mod_data["name"]
        
        fmodel_dir = mod_data.get("fmodel_path", "")
        base_blend_path = os.path.join(fmodel_dir, f"{current_char_id}.blend") if fmodel_dir else ""
        if not base_blend_path or not os.path.exists(base_blend_path):
            self.c.view.write_log(f"ERROR: Cannot add variant. Base model {current_char_id}.blend is missing.", "error")
            self.c.mc.view.show_snackbar("Generate the base .blend file first.", "#EF5350")
            return
        
        category = self.c.get_category_from_path(fmodel_dir)
        fmodel_altermatic_dir = mod_data.get("fmodel_altermatic_path")
        if not fmodel_altermatic_dir:
            fmodel_root = self.c.settings.get("fmodel_output", "")
            fmodel_altermatic_dir = os.path.join(fmodel_root, "Exports", "Pal", "Content", "Palbaker", "Model", "Character", category, current_char_id)

        blend_files = get_blend_files_for_context(fmodel_altermatic_dir, fmodel_dir)

        self.c.view.altermatic_add_dialog.show(
            current_char_id, 
            blend_files, 
            lambda label, custom, src: self._execute_clone_workflow(mod_data, label, custom, src, base_blend_path, fmodel_altermatic_dir)
        )

    def _execute_clone_workflow(self, mod_data: dict, label_name: str, create_custom_mesh: bool, source_choice: str, base_blend_path: str, fmodel_altermatic_dir: str):
        current_char_id = mod_data["name"]
        clean_label = re.sub(r'[^a-zA-Z0-9_]', '_', label_name)
        new_label = f"{current_char_id}_{clean_label}"

        self.c.view.write_log(f"Staging Altermatic variant '{clean_label}'...", "standard")

        def background_clone_worker():
            import time
            time.sleep(0.1) # Yield GIL so WebSocket UI can flush
            
            try:
                manifest_path = self.c.manifest.get_manifest_path(current_char_id, fmodel_altermatic_dir)
                manifest_data = self.c.manifest.load_manifest(manifest_path)

                if new_label in manifest_data["variants"]:
                    self.c.mc.view.show_snackbar(f"Error: A variant named '{clean_label}' already exists!", "#EF5350")
                    return

                target_blend_name = f"{current_char_id}_{clean_label}.blend"

                os.makedirs(fmodel_altermatic_dir, exist_ok=True)
                target_blend_path = os.path.join(fmodel_altermatic_dir, target_blend_name)

                base_sidecar = os.path.join(os.path.dirname(base_blend_path), f"{current_char_id}_blend.json")
                if os.path.exists(base_blend_path) and not os.path.exists(base_sidecar):
                    self.c.view.write_log("Refreshing base model layout...", "standard")
                    sync_sidecar_metadata(self.c.settings.get("blender"), base_blend_path)

                if create_custom_mesh:
                    src_blend_path = ""
                    if source_choice == "base":
                        src_blend_path = base_blend_path
                    else:
                        possible_alt = os.path.join(fmodel_altermatic_dir, source_choice)
                        possible_vanilla = os.path.join(os.path.dirname(base_blend_path), source_choice)
                        src_blend_path = possible_alt if os.path.exists(possible_alt) else possible_vanilla

                    if os.path.exists(src_blend_path):
                        shutil.copy2(src_blend_path, target_blend_path)
                        self.c.view.write_log(f"Cloned skeleton: {os.path.basename(src_blend_path)} -> {target_blend_name}", "standard")
                        
                        src_sidecar_path = os.path.join(os.path.dirname(src_blend_path), f"{os.path.splitext(os.path.basename(src_blend_path))[0]}_blend.json")
                        dest_sidecar_path = os.path.join(os.path.dirname(target_blend_path), f"{os.path.splitext(os.path.basename(target_blend_path))[0]}_blend.json")
                        
                        if os.path.exists(src_sidecar_path):
                            shutil.copy2(src_sidecar_path, dest_sidecar_path)
                            self.c.view.write_log(f"Inherited material mappings: {os.path.basename(src_sidecar_path)} -> {os.path.basename(dest_sidecar_path)}", "standard")
                        else:
                            self.c.view.write_log(f"Extracting layout and metadata for {target_blend_name}...", "standard")
                            sync_sidecar_metadata(self.c.settings.get("blender"), target_blend_path)
                    else:
                        self.c.view.write_log(f"ERROR: Source blend model {src_blend_path} is missing.", "error")
                        return

                manifest_data_to_write = self.c.manifest.load_manifest(manifest_path)
                new_variant = {
                    "SkeletonSource": target_blend_name if create_custom_mesh else "base",
                    "Gender": "None",
                    "IsRarePal": False,
                    "SkinName": "",
                    "ReqTrait": [],
                    "PrefTrait": [],
                    "MaterialOverrides": {},
                    "MorphTarget": [],
                    "is_base": False
                }
                manifest_data_to_write["variants"][new_label] = new_variant
                self.c.manifest.save_manifest(manifest_path, manifest_data_to_write)

                self.c.view.write_log(f"Successfully generated variant: {clean_label}", "success")
                
                # Update the main UI strictly in background; no auto-open
                self.c.mc.refresh_mods(scan_disk=True, target_mod=current_char_id)

            except Exception as err:
                self.c.view.write_log(f"FAILED to stage variant: {err}", "error")

        threading.Thread(target=background_clone_worker, daemon=True).start()