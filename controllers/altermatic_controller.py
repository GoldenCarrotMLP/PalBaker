# controllers/altermatic_controller.py
import os
import json
import re
import shutil
import threading
import time
import flet as ft
from utils.altermatic_helper import sync_sidecar_metadata, get_available_materials_for_context
from components.mods.altermatic_dialog import show_dialog_safe, close_dialog_safe

class AltermaticController:
    def __init__(self, master_controller):
        self.mc = master_controller
        self.settings = master_controller.settings
        self.view = master_controller.view
        
        # Track the active edited variant label to map indices safely
        self.original_editing_label = ""

    def toggle_altermatic(self, mod_data: dict, is_active: bool):
        current_char_id = mod_data["name"]
        fmodel_altermatic_dir = mod_data.get("fmodel_altermatic_path")
        if not fmodel_altermatic_dir:
            fmodel_root = self.settings.get("fmodel_output", "")
            fmodel_altermatic_dir = os.path.join(fmodel_root, "Exports", "Pal", "Content", "Palbaker", "Model", "Character", "Monster", current_char_id)

        os.makedirs(fmodel_altermatic_dir, exist_ok=True)
        manifest_name = f"{mod_data['name']}_altermatic.json"
        manifest_path = os.path.join(fmodel_altermatic_dir, manifest_name)

        manifest_data = {"is_altermatic_active": is_active, "variants": {}}
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f_man:
                    manifest_data = json.load(f_man)
                    if isinstance(manifest_data.get("variants"), list):
                        old_list = manifest_data["variants"]
                        manifest_data["variants"] = {}
                        for item in old_list:
                            lbl_key = item.get("label", "base")
                            manifest_data["variants"][lbl_key] = item
            except Exception: pass

        manifest_data["is_altermatic_active"] = is_active

        if is_active:
            has_base = any(k == "base" for k in manifest_data["variants"].keys())
            if not has_base:
                default_skeleton_source = "base"
                base_blend_name = f"{mod_data['name']}.blend"
                if mod_data.get("fmodel_path") and os.path.exists(os.path.join(mod_data["fmodel_path"], base_blend_name)):
                    default_skeleton_source = base_blend_name

                manifest_data["variants"]["base"] = {
                    "SkeletonSource": default_skeleton_source,
                    "Gender": "None",
                    "IsRarePal": False,
                    "SkinName": "",
                    "ReqTrait": [],
                    "PrefTrait": [],
                    "MatReplace": [],
                    "MorphTarget": [],
                    "is_base": True,
                    "base_type": "vanilla"  # Default base type is standalone vanilla
                }

        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=4)
                
            if is_active:
                self.view.write_log(f"Altermatic Mod Mode enabled for {current_char_id}.", "success")
            else:
                self.view.write_log(f"Altermatic Mod Mode disabled for {current_char_id}. Staged models remain untouched on disk.", "warning")
        except Exception as e:
            self.view.write_log(f"ERROR: Failed to save Altermatic state: {e}", "error")

        self.mc.refresh_mods(scan_disk=True)

    def add_altermatic_variant(self, mod_data: dict):
        """Launches the dynamic cloning onboarding wizard dialog."""
        current_char_id = mod_data["name"]
        fmodel_altermatic_dir = mod_data.get("fmodel_altermatic_path")
        if not fmodel_altermatic_dir:
            fmodel_root = self.settings.get("fmodel_output", "")
            fmodel_altermatic_dir = os.path.join(fmodel_root, "Exports", "Pal", "Content", "Palbaker", "Model", "Character", "Monster", current_char_id)

        # UI Input controls
        label_input = ft.TextField(label="New Variant Name/Label", hint_text="e.g., SFW_Bikini_T-Shirt")
        custom_mesh_switch = ft.Switch(label="Create a custom .blend file for this variant?", value=True)
        
        # Populate template clone dropdown choices with clean stripped labels
        dropdown_options = [ft.dropdown.Option("base", "base (Vanilla Canonical Mesh)")]
        if os.path.exists(fmodel_altermatic_dir):
            for f in os.listdir(fmodel_altermatic_dir):
                if f.endswith(".blend"):
                    clean_lbl = f
                    prefix = f"{current_char_id}_"
                    if clean_lbl.startswith(prefix):
                        clean_lbl = clean_lbl[len(prefix):]
                    dropdown_options.append(ft.dropdown.Option(f, f"Variant: {clean_lbl}"))
                    
        clone_source_dropdown = ft.Dropdown(
            label="Clone Skeleton Template From",
            value="base",
            options=dropdown_options,
            visible=True
        )

        def handle_switch_change(e):
            clone_source_dropdown.visible = custom_mesh_switch.value
            add_dlg.update()

        custom_mesh_switch.on_change = handle_switch_change

        def cancel_clone(e):
            page = self.view.main_page
            close_dialog_safe(page, add_dlg)

        def execute_clone_workflow(e):
            page = self.view.main_page
            if not label_input.value:
                self.mc.view.show_snackbar("Variant Label is required.", ft.Colors.RED_400)
                return

            label_name = label_input.value.strip()
            # Ensure safe alphanumeric formatting
            clean_label = re.sub(r'[^a-zA-Z0-9_]', '_', label_name)
            new_label = f"{current_char_id}_{clean_label}"

            # Synchronously load manifest and check for duplicate label
            manifest_path = os.path.join(fmodel_altermatic_dir, f"{current_char_id}_altermatic.json")
            manifest_data = {"is_altermatic_active": True, "variants": {}}
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f_man:
                        manifest_data = json.load(f_man)
                    
                    # Convert to Map dictionary cleanly
                    if isinstance(manifest_data.get("variants"), list):
                        old_list = manifest_data["variants"]
                        manifest_data["variants"] = {item.get("label", "base"): item for item in old_list}

                    # --- DYNAMIC O(1) DICTIONARY UNIQUE GUARD ---
                    if new_label in manifest_data["variants"]:
                        self.mc.view.show_snackbar(f"Error: A variant named '{clean_label}' already exists!", ft.Colors.RED_400)
                        return
                except Exception: pass
            
            close_dialog_safe(page, add_dlg)
            self.view.write_log(f"Staging Altermatic variant '{clean_label}'...", "standard")

            def background_clone_worker():
                try:
                    target_blend_name = f"{current_char_id}_{clean_label}.blend"

                    os.makedirs(fmodel_altermatic_dir, exist_ok=True)
                    target_blend_path = os.path.join(fmodel_altermatic_dir, target_blend_name)

                    # Always sync the base vanilla .blend first so its updated materials are mapped
                    base_blend = os.path.join(mod_data["fmodel_path"], f"{current_char_id}.blend")
                    if os.path.exists(base_blend):
                        self.view.write_log(f"Refreshing base model layout...", "standard")
                        sync_sidecar_metadata(self.settings.get("blender"), base_blend)

                    if custom_mesh_switch.value:
                        source_choice = clone_source_dropdown.value
                        src_blend_path = ""
                        if source_choice == "base":
                            src_blend_path = base_blend
                        else:
                            src_blend_path = os.path.join(fmodel_altermatic_dir, source_choice)

                        if os.path.exists(src_blend_path):
                            shutil.copy2(src_blend_path, target_blend_path)
                            self.view.write_log(f"Cloned skeleton: {os.path.basename(src_blend_path)} -> {target_blend_name}", "standard")
                        else:
                            with open(target_blend_path, "w") as f: f.write("")

                        # Headlessly synchronize the newly created variant skeletal layout
                        self.view.write_log(f"Extracting layout and metadata for {target_blend_name}...", "standard")
                        sync_sidecar_metadata(self.settings.get("blender"), target_blend_path)

                    # Update manifest JSON
                    manifest_data_to_write = {"is_altermatic_active": True, "variants": {}}
                    if os.path.exists(manifest_path):
                        try:
                            with open(manifest_path, "r", encoding="utf-8") as f_man:
                                manifest_data_to_write = json.load(f_man)
                                if isinstance(manifest_data_to_write.get("variants"), list):
                                    old_list = manifest_data_to_write["variants"]
                                    manifest_data_to_write["variants"] = {item.get("label", "base"): item for item in old_list}
                        except Exception: pass

                    new_variant = {
                        "SkeletonSource": target_blend_name if custom_mesh_switch.value else "base",
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

                    with open(manifest_path, "w", encoding="utf-8") as f_man:
                        json.dump(manifest_data_to_write, f_man, indent=4)

                    self.view.write_log(f"Successfully generated variant: {clean_label}", "success")
                    self.mc.refresh_mods(scan_disk=True)

                    # Focus editor modal
                    def open_editor_delay():
                        time.sleep(0.5)
                        refreshed_mod = next((m for m in self.mc.raw_mods if m["name"] == current_char_id), None)
                        if refreshed_mod:
                            variants_list = refreshed_mod.get("altermatic_variants", [])
                            new_index = next((idx for idx, v in enumerate(variants_list) if v["label"] == new_label), -1)
                            if new_index != -1:
                                self.edit_altermatic_variant(refreshed_mod, new_index)
                    threading.Thread(target=open_editor_delay, daemon=True).start()

                except Exception as err:
                    self.view.write_log(f"FAILED to stage variant: {err}", "error")

            threading.Thread(target=background_clone_worker, daemon=True).start()

        add_dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Add New {current_char_id} Variant"),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_clone),
                ft.TextButton("Create", on_click=execute_clone_workflow)
            ],
            content=ft.Column([
                label_input,
                custom_mesh_switch,
                clone_source_dropdown
            ], tight=True, spacing=15)
        )
        self.view.show_dialog(add_dlg)

    def edit_altermatic_variant(self, mod_data: dict, index: int):
        """Loads and displays the Altermatic dialog instantly using on-disk cached layouts."""
        variants = mod_data.get("altermatic_variants", [])
        if index < 0 or index >= len(variants): return
        
        v = variants[index]
        current_char_id = mod_data["name"]
        
        # Cache the current, un-edited label name to perform a safe on-disk overwrite later
        self.original_editing_label = v["label"]

        fmodel_altermatic_dir = mod_data.get("fmodel_altermatic_path")
        blend_files = get_blend_files_for_context(fmodel_altermatic_dir)
        
        fmodel_root = self.settings.get("fmodel_output", "")
        available_mats = get_available_materials_for_context(fmodel_root, fmodel_altermatic_dir, current_char_id)
        
        self.view.altermatic_dialog.show(
            current_char_id, 
            index, 
            v, 
            blend_files, 
            available_mats
        )

    def delete_altermatic_variant(self, mod_data: dict, index: int):
        variants = mod_data.get("altermatic_variants", [])
        if index < 0 or index >= len(variants): return
        
        v = variants[index]
        current_char_id = mod_data["name"]
        fmodel_altermatic_dir = mod_data.get("fmodel_altermatic_path")
        if not fmodel_altermatic_dir: return

        is_material_only_reskin = (v.get("SkeletonSource", "base") == "base")
        if is_material_only_reskin:
            confirm_message = f"Are you sure you want to permanently delete the variant '{v['label']}'? This will erase its configuration from your files. Your base Blender model ({current_char_id}.blend) will remain completely untouched."
        else:
            confirm_message = f"Are you sure you want to permanently delete the variant '{v['label']}'? This will erase its configuration sidecar and its custom Blender model ({v['SkeletonSource']}) from your hard drive."

        def cancel_del(e):
            close_dialog_safe(page, del_dlg)

        def execute_del(e):
            close_dialog_safe(page, del_dlg)
            
            # 1. Update and remove from the manifest
            manifest_path = os.path.join(fmodel_altermatic_dir, f"{current_char_id}_altermatic.json")
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f_man:
                        manifest_data = json.load(f_man)
                    
                    # Convert old list structures to Map dictionary cleanly
                    if isinstance(manifest_data.get("variants"), list):
                        old_list = manifest_data["variants"]
                        manifest_data["variants"] = {item.get("label", "base"): item for item in old_list}

                    # --- DECOUPLED KEY DELETION ---
                    manifest_data["variants"].pop(v["label"], None)
                    
                    with open(manifest_path, "w", encoding="utf-8") as f_man:
                        json.dump(manifest_data, f_man, indent=4)
                except Exception: pass

            # 2. Delete the physical .blend file from disk ONLY if it is not the canonical base template!
            if not is_material_only_reskin:
                blend_file = os.path.join(fmodel_altermatic_dir, v["SkeletonSource"])
                if os.path.exists(blend_file):
                    try: os.remove(blend_file)
                    except OSError: pass

            self.view.write_log(f"Deleted variant: {v['label']}", "warning")
            self.mc.refresh_mods(scan_disk=True)

        page = self.view.main_page
        del_dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Deletion"),
            content=ft.Text(confirm_message),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_del),
                ft.TextButton("Delete", on_click=execute_del, style=ft.ButtonStyle(color=ft.Colors.RED))
            ]
        )
        self.view.show_dialog(del_dlg)

    def delete_altermatic_variant_by_index(self, monster_name: str, index: int):
        mod_data = next((m for m in self.mc.raw_mods if m["name"] == monster_name), None)
        if mod_data:
            self.delete_altermatic_variant(mod_data, index)

    def save_altermatic_variant_callback(self, index: int, variant_data: dict):
        """Saves edited modal states directly back to the unified Altermatic JSON on disk."""
        is_base = variant_data.get("is_base", False)
        current_char_id = variant_data["CharacterID"]

        # Resolve the folder holding the unified altermatic JSON manifest
        if is_base:
            fmodel_target_dir = os.path.join(
                self.settings.get("fmodel_output", ""), 
                "Exports", "Pal", "Content", "Pal", "Model", "Character", "Monster", 
                current_char_id
            )
        else:
            fmodel_target_dir = os.path.join(
                self.settings.get("fmodel_output", ""), 
                "Exports", "Pal", "Content", "Palbaker", "Model", "Character", "Monster", 
                current_char_id
            )

        os.makedirs(fmodel_target_dir, exist_ok=True)
        
        manifest_name = f"{current_char_id}_altermatic.json"
        manifest_path = os.path.join(fmodel_target_dir, manifest_name)

        manifest_data = {"is_altermatic_active": True, "variants": {}}
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f_man:
                    manifest_data = json.load(f_man)
                    if isinstance(manifest_data.get("variants"), list):
                        old_list = manifest_data["variants"]
                        manifest_data["variants"] = {item.get("label", "base"): item for item in old_list}
            except Exception: pass

        # Prepare proposed label name (with folder name prefix)
        new_label = f"{current_char_id}_{variant_data['label']}" if not is_base else "base"

        # --- DYNAMIC EDITING RENAME GUARD ---
        # Checks if another variant already uses this proposed name, rejecting update on collision
        for label_key, other_var in manifest_data["variants"].items():
            if label_key != self.original_editing_label and label_key == new_label:
                self.mc.view.show_snackbar(f"Error: A variant named '{variant_data['label']}' already exists!", ft.Colors.RED_400)
                self.mc.refresh_mods(scan_disk=True)
                return

        # --- AUTOMATED ON-DISK FILE RENAMER ---
        # If the user renamed their variant, natively rename the physical model assets on disk!
        old_label = self.original_editing_label if (index != -1 and hasattr(self, "original_editing_label")) else ""
        
        if index >= 0 and index < len(manifest_data["variants"]):
            old_variant = manifest_data["variants"].get(old_label, {})
            
            # Match the true index using the persistent old_label
            if old_label and old_label != new_label and not is_base:
                # Rename the sidecar config file on disk
                old_sidecar = os.path.join(fmodel_target_dir, f"{old_label}_blend.json")
                new_sidecar = os.path.join(fmodel_target_dir, f"{new_label}_blend.json")
                if os.path.exists(old_sidecar):
                    try:
                        os.rename(old_sidecar, new_sidecar)
                        self.view.write_log(f"Renamed sidecar file: {os.path.basename(old_sidecar)} -> {os.path.basename(new_sidecar)}", "standard")
                    except OSError: pass

                # Rename the physical .blend model on disk
                if old_label in manifest_data["variants"] and manifest_data["variants"][old_label].get("SkeletonSource") != "base":
                    old_blend_file = os.path.join(fmodel_target_dir, manifest_data["variants"][old_label]["SkeletonSource"])
                    new_blend_name = f"{new_label}.blend"
                    new_blend_file = os.path.join(fmodel_target_dir, new_blend_name)
                    if os.path.exists(old_blend_file):
                        try:
                            os.rename(old_blend_file, new_blend_file)
                            self.view.write_log(f"Renamed .blend model: {manifest_data['variants'][old_label]['SkeletonSource']} -> {new_blend_name}", "standard")
                        except OSError: pass
                    
                    # Update the skeleton source reference inside our memory save block
                    variant_data["SkeletonSource"] = new_blend_name

            # Delete the old key from the dictionary manifest
            manifest_data["variants"].pop(old_label, None)

        # De-serialize material slot name keys safely to avoid index rot
        mat_replace_map = {}
        for item in variant_data.get("MatReplace", []):
            if "SlotName" in item:
                mat_replace_map[item["SlotName"]] = item["MatPath"].split("/")[-1]

        sidecar_structure = {
            "Gender": variant_data["Gender"],
            "IsRarePal": variant_data["IsRarePal"],
            "SkinName": variant_data["SkinName"],
            "ReqTrait": variant_data["ReqTrait"],
            "PrefTrait": variant_data["PrefTrait"],
            "MaterialOverrides": mat_replace_map,
            "MorphTarget": []
        }

        for m in variant_data.get("MorphTarget", []):
            if "Set" in m:
                sidecar_structure["MorphTarget"].append({
                    "Target": m["Target"],
                    "Type": "Static",
                    "Set": m["Set"]
                })
            else:
                sidecar_structure["MorphTarget"].append({
                    "Target": m["Target"],
                    "Type": "Random",
                    "Min": m.get("Min", 0.0),
                    "Max": m.get("Max", 1.0),
                    "Type": m.get("Type", "Free")
                })

        # Map saved fields
        save_block = {
            "SkeletonSource": variant_data["SkeletonSource"],
            "Gender": sidecar_structure["Gender"],
            "IsRarePal": sidecar_structure["IsRarePal"],
            "SkinName": sidecar_structure["SkinName"],
            "ReqTrait": sidecar_structure["ReqTrait"],
            "PrefTrait": sidecar_structure["PrefTrait"],
            "MaterialOverrides": sidecar_structure["MaterialOverrides"],
            "MorphTarget": sidecar_structure["MorphTarget"],
            "is_base": is_base,
            "base_type": variant_data.get("base_type", "vanilla")  # Capture base type (vanilla vs custom)
        }

        # Save directly to dictionary key
        manifest_data["variants"][new_label] = save_block

        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=4)
            self.view.write_log(f"Successfully saved Altermatic variant manifest: {manifest_name}", "success")
        except Exception as e:
            self.view.write_log(f"ERROR: Failed to save Altermatic manifest: {e}", "error")

        self.mc.refresh_mods(scan_disk=True)

# Helper function to scan files dynamically inside the controller
def get_blend_files_for_context(fmodel_altermatic_dir: str) -> list[str]:
    """Helper used during UI population to resolve Blender choices dynamically."""
    blend_files = []
    if fmodel_altermatic_dir and os.path.exists(fmodel_altermatic_dir):
        for f in os.listdir(fmodel_altermatic_dir):
            if f.endswith(".blend"):
                blend_files.append(f)
    return blend_files