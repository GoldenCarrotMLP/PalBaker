This is a fantastic architectural choice. Providing a **Hybrid Workspace** system solves the friction of deep FModel directory diving while ensuring 100% backward compatibility for users who rely on the current folder structure.

To implement this perfectly, we will introduce a **Unified Sidecar I/O Manager**. By routing all JSON reads/writes through a dedicated `utils/sidecar.py` script, `blender_extractor.py` and `altermatic_helper.py` will effortlessly perform deep delta-merges without ever accidentally wiping out the user's `routing_metadata`.

Here are the complete, updated files to implement the **Hybrid Workspace Architecture** and the **Unified Sidecar Synchronizer**.

### 1. Unified Sidecar Manager (NEW FILE)
Create this new file to centralize all sidecar JSON reading, merging, and writing.

**`utils/sidecar.py`**
```python
# utils/sidecar.py
import json
import os

def read_sidecar(path: str) -> dict:
    """Safely loads a companion sidecar JSON."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def write_sidecar(path: str, data: dict):
    """Safely writes to a companion sidecar JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def update_sidecar_fields(path: str, **kwargs) -> dict:
    """
    Performs a non-destructive delta-merge. 
    Preserves all existing data (like routing_metadata) and only updates the requested keys.
    """
    data = read_sidecar(path)
    for k, v in kwargs.items():
        data[k] = v
    write_sidecar(path, data)
    return data
```

### 2. Update Configurations
Add the new Workspace path to our configuration definitions.

**`utils/config.py`**
```python
# utils/config.py
import os
import json

# Force settings file to always save in the root PalBaker directory
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "manager_settings.json")

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {
        "workspace": "",
        "fmodel_output": "", 
        "ue_root": "", 
        "uproject": "", 
        "blender": "",
        "palworld_exe": "",
        "show_mapped": False,
        "console_height": 200
    }

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)
```

**`views/settings_view.py`**
```python
# views/settings_view.py
import flet as ft
from components.common.path_picker import PathPicker
from controllers.settings_controller import SettingsController

class SettingsView:
    def __init__(self, page: ft.Page, settings: dict, on_save_callback):
        self.main_page = page
        self.settings = settings
        
        self.dir_picker = ft.FilePicker()
        self.file_picker = ft.FilePicker()
        self.main_page.services.append(self.dir_picker)
        self.main_page.services.append(self.file_picker)

        self.controller = SettingsController(self, settings, on_save_callback)

        self.workspace_picker = PathPicker(
            label="Flat Workspace Folder (Optional - for flat custom projects)", 
            value=str(settings.get("workspace", "")), 
            icon=ft.Icons.FOLDER_SPECIAL,
            on_browse_click=lambda e: self.main_page.run_task(self.controller.pick_directory, self.workspace_picker, self.dir_picker)
        )

        self.fmodel_picker = PathPicker(
            label="FModel Output Folder", 
            value=str(settings.get("fmodel_output", "")), 
            icon=ft.Icons.FOLDER_OPEN,
            on_browse_click=lambda e: self.main_page.run_task(self.controller.pick_directory, self.fmodel_picker, self.dir_picker)
        )
        
        self.ue_root_picker = PathPicker(
            label="Unreal Engine Root (e.g. UE_5.1)", 
            value=str(settings.get("ue_root", "")), 
            icon=ft.Icons.FOLDER_OPEN,
            on_browse_click=lambda e: self.main_page.run_task(self.controller.pick_directory, self.ue_root_picker, self.dir_picker)
        )
        
        self.uproject_picker = PathPicker(
            label="Palworld ModKit .uproject Path", 
            value=str(settings.get("uproject", "")), 
            icon=ft.Icons.FILE_OPEN,
            on_browse_click=lambda e: self.main_page.run_task(self.controller.pick_file, self.uproject_picker, self.file_picker, ["uproject"])
        )
        
        self.blender_picker = PathPicker(
            label="Blender Executable Path", 
            value=str(settings.get("blender", "")), 
            icon=ft.Icons.FILE_OPEN,
            on_browse_click=lambda e: self.main_page.run_task(self.controller.pick_file, self.blender_picker, self.file_picker)
        )
        
        self.palworld_exe_picker = PathPicker(
            label="Palworld.exe Path", 
            value=str(settings.get("palworld_exe", "")), 
            icon=ft.Icons.FILE_OPEN,
            on_browse_click=lambda e: self.main_page.run_task(self.controller.pick_file, self.palworld_exe_picker, self.file_picker, ["exe"])
        )

        self.show_mapped_switch = ft.Switch(
            label="Show Mapped Names (e.g. Chillet instead of WeaselDragon)", 
            value=bool(settings.get("show_mapped", False))
        )

        self.view = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=20,
            controls=[
                ft.Text("Application Paths", size=20, weight=ft.FontWeight.BOLD),
                self.workspace_picker.view,
                self.fmodel_picker.view,
                self.ue_root_picker.view,
                self.uproject_picker.view,
                self.blender_picker.view,
                self.palworld_exe_picker.view,
                ft.Divider(),
                ft.Text("Preferences", size=20, weight=ft.FontWeight.BOLD),
                self.show_mapped_switch,
                ft.Divider(),
                ft.ElevatedButton("Save and Reload Mod List", icon=ft.Icons.SAVE, on_click=self._on_save, height=50)
            ]
        )

    def update_settings(self, new_settings: dict):
        self.settings = new_settings
        self.workspace_picker.set_value(str(new_settings.get("workspace", "")))
        self.fmodel_picker.set_value(str(new_settings.get("fmodel_output", "")))
        self.ue_root_picker.set_value(str(new_settings.get("ue_root", "")))
        self.uproject_picker.set_value(str(new_settings.get("uproject", "")))
        self.blender_picker.set_value(str(new_settings.get("blender", "")))
        self.palworld_exe_picker.set_value(str(new_settings.get("palworld_exe", "")))
        self.show_mapped_switch.value = bool(new_settings.get("show_mapped", False))
        self.main_page.update()

    def _on_save(self, e):
        current_paths = {
            "workspace": self.workspace_picker.get_value(),
            "fmodel_output": self.fmodel_picker.get_value(),
            "ue_root": self.ue_root_picker.get_value(),
            "uproject": self.uproject_picker.get_value(),
            "blender": self.blender_picker.get_value(),
            "palworld_exe": self.palworld_exe_picker.get_value(),
        }
        self.controller.save_clicked(current_paths, bool(self.show_mapped_switch.value))
```

**`controllers/settings_controller.py`**
```python
# controllers/settings_controller.py
import flet as ft
import threading
from utils.config import save_settings
from utils.builder.config_helper import restore_palbaker_backup
from utils.plugin_manager import (
    check_project_requirements, 
    install_and_compile_plugin, 
    inject_missing_assets, 
    enable_remote_execution_settings,
    enable_cooking_settings,
    restart_unreal_editor
)

class SettingsController:
    def __init__(self, view, settings: dict, on_save_callback):
        self.view = view
        self.settings = settings
        self.on_save_callback = on_save_callback

    async def pick_directory(self, target_picker_component, picker):
        result = await picker.get_directory_path()
        if result:
            target_picker_component.set_value(str(result))

    async def pick_file(self, target_picker_component, picker, allowed_extensions=None):
        result = await picker.pick_files(allow_multiple=False, allowed_extensions=allowed_extensions)
        if result and len(result) > 0 and result[0].path:
            target_picker_component.set_value(str(result[0].path))


    def save_clicked(self, current_paths: dict, show_mapped: bool):
        self.settings.update(current_paths)
        self.settings["show_mapped"] = show_mapped
        save_settings(self.settings)

        restore_palbaker_backup(self.settings.get("uproject"))

        def verify_and_build():
            def ask_user_modal(title, content_control):
                result = [False]
                event = threading.Event()

                def on_yes(e):
                    result[0] = True
                    self.view.pop_dialog()
                    event.set()

                def on_no(e):
                    result[0] = False
                    self.view.pop_dialog()
                    event.set()

                dlg = ft.AlertDialog(
                    modal=True,
                    title=ft.Text(title),
                    content=content_control,
                    actions=[
                        ft.TextButton("Cancel", on_click=on_no),
                        ft.TextButton("Yes, Install", on_click=on_yes, style=ft.ButtonStyle(color=ft.Colors.BLUE)),
                    ]
                )
                self.view.show_dialog(dlg)
                event.wait()
                return result[0]

            reqs = check_project_requirements(self.settings.get("ue_root", ""), self.settings.get("uproject", ""))

            if reqs.get("error"):
                self.view.show_snackbar(reqs["error"], ft.Colors.RED_400)
                self.on_save_callback()
                return

            if reqs["needs_plugin_sync"] or reqs["needs_compile"]:
                plugin_names = ["PalBaker Editor Utilities"]
                plugins_text = "\n".join([f" • {name}" for name in plugin_names])
                content = ft.Column([
                    ft.Text("PalBaker requires the following custom C++ Editor Utility Plugin(s) to automatically generate Animation Blueprints via Python:"),
                    ft.Text(plugins_text, color=ft.Colors.CYAN_200, weight=ft.FontWeight.BOLD),
                    ft.Text("The plugin(s) are missing or outdated in your active Unreal Engine project.", color=ft.Colors.ORANGE_400),
                    ft.Text("Would you like to install and bind them to your ModKit now?", weight=ft.FontWeight.BOLD)
                ], tight=True)

                if ask_user_modal("Required Plugin Missing", content):
                    self.view.show_snackbar("Installing and verifying C++ plugin... (This may take a moment)", ft.Colors.WHITE)
                    success, msg = install_and_compile_plugin(self.settings["ue_root"], self.settings["uproject"])
                    color = ft.Colors.GREEN_400 if success else ft.Colors.RED_400
                    self.view.show_snackbar(msg, color)

            missing_assets = reqs.get("missing_assets", [])
            if missing_assets:
                files_controls = [ft.Text(f" • {f}", size=12, color=ft.Colors.WHITE70) for f in missing_assets]
                files_list = ft.ListView(controls=files_controls, height=150, spacing=2, padding=10)
                
                content = ft.Column([
                    ft.Text("The following core framework assets are missing from your ModKit's Content directory:"),
                    ft.Container(content=files_list, border=ft.Border.all(1, ft.Colors.WHITE24), border_radius=5),
                    ft.Text("PalBaker requires these to cleanly bind Material Instances.\nWould you like to inject them into your project automatically?", weight=ft.FontWeight.BOLD)
                ], tight=True)

                if ask_user_modal("Missing Core Assets", content):
                    success, msg = inject_missing_assets(self.settings["uproject"])
                    color = ft.Colors.GREEN_400 if success else ft.Colors.RED_400
                    self.view.show_snackbar(msg, color)

            needs_remote_exec = reqs.get("needs_remote_exec_enable")
            needs_cooking_setup = reqs.get("needs_cooking_setup")

            if needs_remote_exec or needs_cooking_setup:
                reasons = []
                if needs_remote_exec:
                    reasons.append(" • Enable 'Python Remote Execution' (allows Python script orchestration)")
                if needs_cooking_setup:
                    reasons.append(" • Disable 'I/O Store' & 'Material Shader Sharing' (forces compilation to loose .uasset files)")

                content = ft.Column([
                    ft.Text("PalBaker needs to apply the following required configuration changes to your project's .ini files:"),
                    ft.Text("\n".join(reasons), color=ft.Colors.ORANGE_400),
                    ft.Text("Please ensure your work inside Unreal is saved before proceeding! Clicking 'Yes, Install' will write these settings and AUTOMATICALLY restart your Unreal Editor project.", weight=ft.FontWeight.BOLD)
                ], tight=True)

                if ask_user_modal("Project Configurations Required", content):
                    if needs_remote_exec:
                        enable_remote_execution_settings(self.settings["uproject"])
                    if needs_cooking_setup:
                        enable_cooking_settings(self.settings["uproject"])
                        
                    self.view.show_snackbar("Configurations successfully written. Restarting Unreal Editor...", ft.Colors.WHITE)
                    restart_success, restart_msg = restart_unreal_editor(self.settings["ue_root"], self.settings["uproject"])
                    color = ft.Colors.GREEN_400 if restart_success else ft.Colors.RED_400
                    self.view.show_snackbar(restart_msg, color)

            self.view.show_snackbar("Settings saved and verified!", ft.Colors.GREEN_400)
            self.on_save_callback(scan_disk=True)

        threading.Thread(target=verify_and_build, daemon=True).start()
```

### 3. Refactor Sidecar Overwriters
Update existing headless extractors to funnel all writes through `update_sidecar_fields()`.

**`utils/blender_extractor.py`**
```python
# utils/blender_extractor.py
import sys
import os
import json

current_dir = os.path.dirname(__file__)
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Ensure the parent directory is in path so we can import 'sidecar'
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from blender_utils import translator
from sidecar import read_sidecar, update_sidecar_fields

def parse_args():
    args = []
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
    
    output_json = "sidecar_blend.json"
    output_fbx = None
    for i, arg in enumerate(args):
        if arg == "--output" and i + 1 < len(args):
            output_json = args[i + 1]
            if not output_json.endswith(".json"):
                for next_arg in args[i+1:]:
                    if next_arg.endswith(".json"):
                        output_json = next_arg
                        break
        elif arg == "--fbx" and i + 1 < len(args):
            output_fbx = args[i + 1]
    return output_json, output_fbx

def extract_metadata(output_path: str, fbx_path: str = None):
    working_dir = os.path.dirname(output_path)
    bones_info = translator.get_pose_bones_info("Armature")
    
    jiggle_bones = []
    offset_bones = []

    for bone in bones_info:
        if bone["is_physics"]:
            spring_config = {
                "bone_name": bone["bone_name"],
                **bone["physics_config"]
            }
            jiggle_bones.append(spring_config)
            
        if bone["transform_data"]:
            transform_config = {
                "bone_name": bone["bone_name"],
                **bone["transform_data"]
            }
            offset_bones.append(transform_config)

    slots_in_order = translator.get_skeletal_mesh_material_slots()

    materials_compile = {}
    for mat_name in slots_in_order:
        k_lower = mat_name.lower()
        if "dots stroke" in k_lower or mat_name.startswith("."):
            continue
        materials_compile[mat_name] = {"parent_class": "MI_PalLit_CharacterBodyBase", "textures": {}}

    existing_data = read_sidecar(output_path)

    merged_materials = {}
    for k, v in materials_compile.items():
        merged_materials[k] = v

    if "materials" in existing_data:
        for k, v in existing_data["materials"].items():
            k_lower = k.lower()
            if "dots stroke" in k_lower or k.startswith("."):
                continue
            if k not in merged_materials:
                merged_materials[k] = v

    # Send updates cleanly through the unified sidecar manager
    update_sidecar_fields(
        output_path,
        jiggle_bones=jiggle_bones,
        offset_bones=offset_bones,
        materials=merged_materials
    )

    if fbx_path:
        translator.export_fbx(fbx_path, "Armature")

if __name__ == "__main__":
    out_json, fbx_out = parse_args()
    extract_metadata(out_json, fbx_out)
```

**`utils/altermatic_helper.py`**
*(Updates `sync_sidecar_metadata` and routing inside `compile_unified_altermatic_json`)*
```python
# utils/altermatic_helper.py
import os
import json
import re
import subprocess
from utils.sidecar import read_sidecar, update_sidecar_fields

BLENDER_EXTRACTOR_SCRIPT = (
    "import bpy, json; "
    "mesh_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH']; "
    "slots = list(set(slot.name for obj in mesh_objs for slot in obj.material_slots if slot.name)); "
    "morphs = list(set(kb.name for obj in mesh_objs if obj.data.shape_keys for kb in obj.data.shape_keys.key_blocks if kb.name != 'Basis')); "
    "print('ALTERMATIC_METADATA_START' + json.dumps({'slots': slots, 'morphs': morphs}) + 'ALTERMATIC_METADATA_END')"
)

def get_virtual_path_for_file(absolute_path: str) -> str:
    clean_path = absolute_path.replace("\\", "/")
    marker = "Pal/Content/"
    if marker in clean_path:
        relative_part = clean_path.split(marker, 1)[1]
        folder_part = "/".join(relative_part.split("/")[:-1]).replace(" ", "_")
        return f"/Game/{folder_part}"
    return ""

def extract_blend_metadata(blender_path: str, blend_file_path: str) -> dict:
    if not blender_path or not os.path.exists(blender_path):
        return {"slots": [], "morphs": []}
    if not blend_file_path or not os.path.exists(blend_file_path):
        return {"slots": [], "morphs": []}

    cmd = [blender_path, "-b", blend_file_path, "--python-expr", BLENDER_EXTRACTOR_SCRIPT]

    try:
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', creationflags=creation_flags)
        match = re.search(r"ALTERMATIC_METADATA_START(.*?)ALTERMATIC_METADATA_END", result.stdout)
        if match:
            return json.loads(match.group(1))
    except Exception:
        pass

    return {"slots": [], "morphs": []}

def delta_merge_sidecar(existing_data: dict, fresh_slots: list[str], fresh_morphs: list[str]) -> dict:
    synced = {
        "Gender": existing_data.get("Gender", "None"),
        "IsRarePal": bool(existing_data.get("IsRarePal", False)),
        "SkinName": existing_data.get("SkinName", ""),
        "ReqTrait": list(existing_data.get("ReqTrait", [])),
        "PrefTrait": list(existing_data.get("PrefTrait", [])),
        "MaterialOverrides": {},
        "MorphTarget": []
    }

    old_overrides = existing_data.get("MaterialOverrides", {})
    for slot_name in fresh_slots:
        if slot_name in old_overrides:
            synced["MaterialOverrides"][slot_name] = old_overrides[slot_name]

    old_morphs = {m["Target"]: m for m in existing_data.get("MorphTarget", []) if "Target" in m}
    for morph_name in fresh_morphs:
        if morph_name in old_morphs:
            synced["MorphTarget"].append(old_morphs[morph_name])
        else:
            synced["MorphTarget"].append({"Target": morph_name, "Type": "None"})

    return synced

def sync_sidecar_metadata(blender_path: str, blend_file_path: str) -> dict:
    root_dir = os.path.dirname(blend_file_path)
    base_name = os.path.splitext(os.path.basename(blend_file_path))[0]
    sidecar_path = os.path.join(root_dir, f"{base_name}_blend.json")

    existing_data = read_sidecar(sidecar_path)
    fresh_metadata = extract_blend_metadata(blender_path, blend_file_path)
    
    synced_data = delta_merge_sidecar(existing_data, fresh_metadata.get("slots", []), fresh_metadata.get("morphs", []))
    
    # Save cleanly through the sidecar manager
    update_sidecar_fields(sidecar_path, **synced_data)

    return synced_data

def compile_unified_altermatic_json(target_character_id: str, altermatic_staging_dir: str, swap_json_dir: str, target_category: str) -> tuple[bool, str]:
    manifest_name = f"{target_character_id}_altermatic.json"
    manifest_path = os.path.join(altermatic_staging_dir, manifest_name)

    if not os.path.exists(manifest_path):
        return True, "No Altermatic variants manifest detected to compile."

    try:
        with open(manifest_path, "r", encoding="utf-8") as f_man:
            manifest_data = json.load(f_man)
        variants_data = manifest_data.get("variants", {})
        
        variants_list = []
        if isinstance(variants_data, dict):
            for k, v in variants_data.items():
                v["label"] = k
                variants_list.append(v)
        elif isinstance(variants_data, list):
            variants_list = variants_data
            
    except Exception as e:
        return False, f"Failed to read Altermatic manifest: {e}"

    swaps_array = []
    cat_sanitized = target_category.replace(" ", "_")

    for v in variants_list:
        if v.get("is_base"):
            continue

        try:
            blend_base_name = os.path.splitext(v["SkeletonSource"])[0]
            blend_file_path = os.path.join(altermatic_staging_dir, f"{blend_base_name}.blend")
            sidecar_path = os.path.join(altermatic_staging_dir, f"{blend_base_name}_blend.json")

            clean_path = blend_file_path.replace("\\", "/")
            marker = "Pal/Content/"
            if marker in clean_path:
                relative_part = clean_path.split(marker, 1)[1]
                sk_name = blend_base_name if blend_base_name.startswith("SK_") else f"SK_{blend_base_name}"
                relative_virtual_dir = "/".join(relative_part.split("/")[:-1]).replace(" ", "_")
                mesh_resolved_path = f"/Game/{relative_virtual_dir}/{sk_name}"
            else:
                # Fallback to standard explicit path routing using the Target Character ID
                mesh_resolved_path = f"/Game/Palbaker/Model/Character/{cat_sanitized}/{target_character_id}/SK_{blend_base_name}"

            mat_replace_list = []
            slots_order = []
            if os.path.exists(sidecar_path):
                sidecar_data = read_sidecar(sidecar_path)
                slots_order = list(sidecar_data.get("materials", {}).keys())

            if not slots_order:
                slots_order = ["mi_body", "mi_eye", "mi_mouth"]

            slots_order_lower = [s.lower() for s in slots_order]
            material_overrides = v.get("MaterialOverrides", {})
            for slot_name, mat_override_name in material_overrides.items():
                slot_name_lower = slot_name.lower()
                if slot_name_lower in slots_order_lower and mat_override_name:
                    idx = slots_order_lower.index(slot_name_lower)
                    mat_resolved_dir = get_virtual_path_for_file(sidecar_path)
                    resolved_mat_path = f"{mat_resolved_dir}/{mat_override_name}"
                    mat_replace_list.append({
                        "Index": str(idx),
                        "MatPath": resolved_mat_path
                    })

            compiled_swap = {
                "CharacterID": target_character_id,
                "SkelMeshPath": mesh_resolved_path,
                "Gender": v.get("Gender", "None")
            }

            if v.get("IsRarePal"):
                compiled_swap["IsRarePal"] = "True"
            if v.get("SkinName"):
                compiled_swap["SkinName"] = v["SkinName"]
            if v.get("ReqTrait"):
                compiled_swap["ReqTrait"] = v["ReqTrait"]
            if v.get("PrefTrait"):
                compiled_swap["PrefTrait"] = v["PrefTrait"]
            if mat_replace_list:
                compiled_swap["MatReplace"] = mat_replace_list

            compiled_morphs = []
            for m in v.get("MorphTarget", []):
                if m.get("Type") == "Static" and "Set" in m:
                    compiled_morphs.append({"Target": m["Target"], "Set": m["Set"]})
                elif m.get("Type") == "Random":
                    compiled_morphs.append({"Target": m["Target"], "Min": m.get("Min", 0.0), "Max": m.get("Max", 1.0), "Type": m.get("Type", "Free")})
            
            if compiled_morphs:
                compiled_swap["MorphTarget"] = compiled_morphs

            swaps_array.append(compiled_swap)
        except Exception as e:
            print(f"Altermatic Mod Builder Warning: Skipping corrupted variant compilation: {e}", flush=True)

    output_structure = {
        "PackName": f"PalBaker-{target_character_id} Replacer Pack",
        "SkelMeshSwap": swaps_array
    }

    os.makedirs(swap_json_dir, exist_ok=True)
    target_path = os.path.join(swap_json_dir, f"palbaker-{target_character_id}.json")

    try:
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(output_structure, f, indent=4)
        return True, f"SUCCESS: Compiled and deployed Altermatic config to {target_path}"
    except Exception as e:
        return False, f"Failed to write deployment JSON: {e}"

def get_available_materials_for_context(fmodel_root: str, fmodel_altermatic_dir: str, target_character_id: str, category: str = "Monster") -> list[str]:
    materials = []
    paths_to_check = []

    if fmodel_root:
        base_dir = os.path.join(fmodel_root, "Exports", "Pal", "Content", "Pal", "Model", "Character", category, target_character_id)
        if os.path.exists(base_dir):
            paths_to_check.append(base_dir)

    if fmodel_altermatic_dir and os.path.exists(fmodel_altermatic_dir):
        paths_to_check.append(fmodel_altermatic_dir)

    for directory in paths_to_check:
        for f in os.listdir(directory):
            if f.endswith("_blend.json"):
                sidecar_path = os.path.join(directory, f)
                data = read_sidecar(sidecar_path)
                mats = data.get("materials", {})
                for mat_name in mats.keys():
                    if mat_name and mat_name not in materials:
                        materials.append(mat_name)

    if not materials:
        materials = [
            f"MI_{target_character_id}_Body_Latex",
            f"MI_{target_character_id}_Body_Shiny",
            f"MI_{target_character_id}_Body_Gold"
        ]

    return sorted(materials)

def load_traits_database() -> dict:
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_path = os.path.join(root_dir, "traits_db.json")
    
    if not os.path.exists(target_path):
        return {}
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
```

### 4. Upgrade The Hybrid Pathing Logic
We now scan both `workspace` and `fmodel_output`. UI identifies Workspace mods via `is_workspace_mode`. 

**`utils/scanner.py`**
```python
# utils/scanner.py
import os
import json
from .state import is_ue_modified, is_source_modified
from .names import get_localized_name
from .audio_helper import get_pal_sound_metadata
from .sidecar import read_sidecar

def scan_character_folders(base_path: str) -> dict:
    discovered = {}
    if not base_path or not os.path.exists(base_path):
        return discovered
        
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        has_assets = any(f.endswith(('.blend', '.uasset', '.json', '.fbx')) for f in files)
        if has_assets:
            folder_name = os.path.basename(root)
            if folder_name not in ["Character", "Skeleton", "PalActorBP", "Normal", "WwiseAudio", "Media", "sources"]:
                discovered[folder_name] = os.path.abspath(root)
    return discovered

def scan_workspace_folders(workspace_path: str) -> dict:
    discovered = {}
    if not workspace_path or not os.path.exists(workspace_path):
        return discovered
        
    for root, dirs, files in os.walk(workspace_path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        has_assets = any(f.endswith(('.blend', '.uasset', '.json', '.fbx')) for f in files)
        if has_assets:
            # The mod name is the root folder name inside the workspace
            folder_name = os.path.basename(root)
            if folder_name not in ["Character", "Skeleton", "PalActorBP", "Normal", "WwiseAudio", "Media", "sources"]:
                discovered[folder_name] = os.path.abspath(root)
    return discovered

def get_mod_info(settings: dict):
    fmodel_base = settings.get("fmodel_output", "")
    workspace_base = settings.get("workspace", "")
    uproject = settings.get("uproject", "")
    palworld_exe = settings.get("palworld_exe", "")

    ue_base = ""
    if uproject and os.path.exists(uproject):
        ue_base = os.path.join(os.path.dirname(uproject), "Content", "Pal", "Model", "Character")

    fmodel_monsters = os.path.join(fmodel_base, "Exports", "Pal", "Content", "Pal", "Model", "Character") if fmodel_base else ""
    fmodel_altermatic = os.path.join(fmodel_base, "Exports", "Pal", "Content", "Palbaker", "Model", "Character") if fmodel_base else ""

    discovered_fmodel = scan_character_folders(fmodel_monsters)
    discovered_altermatic = scan_character_folders(fmodel_altermatic)
    discovered_ue = scan_character_folders(ue_base)
    discovered_workspace = scan_workspace_folders(workspace_base)

    all_names = set(
        list(discovered_fmodel.keys()) + 
        list(discovered_altermatic.keys()) + 
        list(discovered_ue.keys()) +
        list(discovered_workspace.keys())
    )

    results = []

    swap_json_dir = ""
    if palworld_exe and os.path.exists(palworld_exe):
        swap_json_dir = os.path.join(os.path.dirname(palworld_exe), "Pal", "Content", "Paks", "~Mods", "SwapJSON")

    for name in all_names:
        is_workspace_mode = name in discovered_workspace
        
        fmodel_path = discovered_workspace.get(name, "") if is_workspace_mode else discovered_fmodel.get(name, "")
        fmodel_altermatic_path = os.path.join(fmodel_path, "Palbaker") if is_workspace_mode else discovered_altermatic.get(name, "")
        ue_path = discovered_ue.get(name, "")

        is_unmapped = False
        target_id = name
        target_category = "Monster"

        if is_workspace_mode:
            sidecar_path = os.path.join(fmodel_path, f"{name}_blend.json")
            sidecar = read_sidecar(sidecar_path)
            routing = sidecar.get("routing_metadata", {})
            if routing:
                target_id = routing.get("target_character_id", name)
                target_category = routing.get("target_category", "Monster")
            else:
                is_unmapped = True
        else:
            # Try to infer category from FModel path
            parts = fmodel_path.replace("\\", "/").split("/")
            if "Character" in parts:
                idx = parts.index("Character")
                if idx + 1 < len(parts):
                    target_category = parts[idx + 1]

        data = {
            "name": name,
            "target_id": target_id,
            "target_category": target_category,
            "is_workspace_mode": is_workspace_mode,
            "is_unmapped": is_unmapped,
            "fmodel_path": fmodel_path,
            "fmodel_altermatic_path": fmodel_altermatic_path,
            "ue_path": ue_path
        }

        badges = []
        has_fmodel = bool(fmodel_path)
        has_blend = has_fmodel and any(f.endswith(".blend") for f in os.listdir(fmodel_path))
        has_ue = bool(ue_path) and any(f.endswith(".uasset") for f in os.listdir(ue_path))
        
        is_altermatic_active = False
        altermatic_config_path = ""
        
        if swap_json_dir and os.path.exists(swap_json_dir):
            target_json = os.path.join(swap_json_dir, f"palbaker-{target_id}.json")
            if os.path.exists(target_json):
                is_altermatic_active = True
                altermatic_config_path = target_json

        if fmodel_altermatic_path and os.path.exists(fmodel_altermatic_path):
            is_altermatic_active = True

        altermatic_variants = []
        manifest_name = f"{target_id}_altermatic.json"
        manifest_path = os.path.join(fmodel_altermatic_path if fmodel_altermatic_path else fmodel_path, manifest_name)
        
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f_man:
                    loaded_structure = json.load(f_man)
                    is_altermatic_active = bool(loaded_structure.get("is_altermatic_active", False))
                    
                    variants_data = loaded_structure.get("variants", {})
                    if isinstance(variants_data, dict):
                        for k, v in variants_data.items():
                            v["label"] = k
                            v["CharacterID"] = target_id
                            v["is_base"] = (k == "base")
                            v["has_base_blend"] = has_blend
                            altermatic_variants.append(v)
                    elif isinstance(variants_data, list):
                        for v in variants_data:
                            v["CharacterID"] = target_id
                            v["is_base"] = (v.get("label") == "base")
                            v["has_base_blend"] = has_blend
                            altermatic_variants.append(v)
            except Exception:
                pass

        if is_altermatic_active:
            if not altermatic_variants:
                base_variant = {
                    "label": "base", "CharacterID": target_id, "SkeletonSource": "base",
                    "Gender": "None", "IsRarePal": False, "SkinName": "",
                    "ReqTrait": [], "PrefTrait": [], "MatReplace": [], "MorphTarget": [],
                    "is_base": True, "base_type": "vanilla", "has_base_blend": has_blend
                }
                altermatic_variants.append(base_variant)
                
            has_base_variant = any(v.get("is_base") for v in altermatic_variants)
            if not has_base_variant:
                base_variant = {
                    "label": "base", "CharacterID": target_id, "SkeletonSource": "base",
                    "Gender": "None", "IsRarePal": False, "SkinName": "",
                    "ReqTrait": [], "PrefTrait": [], "MatReplace": [], "MorphTarget": [],
                    "is_base": True, "base_type": "vanilla", "has_base_blend": has_blend
                }
                altermatic_variants.insert(0, base_variant)

        icon_path = ""
        if fmodel_base and not is_workspace_mode:
            icon_path = os.path.join(fmodel_base, "Exports", "Pal", "Content", "Pal", "Texture", "PalIcon", "Normal", f"T_{name}_icon_normal.png")
            
        has_icon = os.path.exists(icon_path) if icon_path else False
        data["icon_path"] = icon_path
        data["has_icon"] = has_icon
        data["is_altermatic_active"] = is_altermatic_active
        data["altermatic_config_path"] = altermatic_config_path
        data["altermatic_variants"] = altermatic_variants

        sound_meta = get_pal_sound_metadata(target_id)
        audio_overrides = {}
        
        if has_fmodel:
            audio_dir = os.path.join(fmodel_path, ".palbaker_audio", "sources")
            for cry_name in ["Normal", "Joy", "Anger", "Sorrow", "Pain", "Death"]:
                if cry_name in sound_meta:
                    audio_overrides[cry_name] = None
                    for ext in [".wav", ".mp3", ".ogg"]:
                        test_path = os.path.join(audio_dir, f"{cry_name}{ext}")
                        if os.path.exists(test_path):
                            audio_overrides[cry_name] = test_path
                            break
                        
        data["audio_overrides"] = audio_overrides
        data["sound_metadata"] = sound_meta

        if is_unmapped:
            badges.append(("UNMAPPED", "#FF5252"))
        if has_fmodel and not has_blend:
            badges.append(("RAW", "#333333"))
        if has_blend:
            badges.append(("SOURCE", "#2196F3"))
        if has_ue:
            badges.append(("UE ASSETS", "#FF9800"))
        if is_altermatic_active:
            badges.append(("ALTERMATIC", "#008080"))

        source_modified = is_source_modified(fmodel_path) if (has_fmodel and has_blend) else False
        if source_modified:
            badges.append(("SRC CHANGED", "#0D47A1"))

        ue_modified_files = is_ue_modified(fmodel_path, ue_path) if (has_fmodel and has_ue) else []
        ue_modified = len(ue_modified_files) > 0
        if ue_modified:
            badges.append(("MODIFIED", "#D32F2F"))

        pak_status = "Unpacked"
        pak_path = ""
        pak_err_path = ""
        
        if palworld_exe and os.path.exists(palworld_exe):
            pak_path = os.path.join(os.path.dirname(palworld_exe), "Pal", "Content", "Paks", "palBaker", f"{target_id}_P.pak")
            pak_err_path = os.path.join(os.path.dirname(palworld_exe), "Pal", "Content", "Paks", "palBaker", f"{target_id}_err_P.pak")
            
        has_pak = os.path.exists(pak_path)
        has_pak_err = os.path.exists(pak_err_path)
        active_pak_path = pak_path if has_pak else (pak_err_path if has_pak_err else "")
        
        if active_pak_path:
            pak_mtime = os.path.getmtime(active_pak_path)
            outdated = False
            
            if has_fmodel:
                for root, dirs, files in os.walk(fmodel_path):
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    for f in files:
                        if f.endswith(('.blend', '.fbx', '.png', '.json')) and os.path.getmtime(os.path.join(root, f)) > pak_mtime:
                            outdated = True
            if has_ue and not outdated:
                for root, _, files in os.walk(ue_path):
                    for f in files:
                        if f.endswith('.uasset') and os.path.getmtime(os.path.join(root, f)) > pak_mtime:
                            outdated = True
                            
            if outdated:
                pak_status = "Outdated"
            elif has_pak_err:
                pak_status = "Packed with Errors"
            else:
                pak_status = "Packed"

        data["badges"] = badges
        data["pak_status"] = pak_status
        data["pak_path"] = active_pak_path
        data["ue_modified"] = ue_modified
        data["ue_modified_files"] = ue_modified_files
        data["source_modified"] = source_modified
        data["has_fmodel"] = has_fmodel
        data["has_blend"] = has_blend
        data["has_ue"] = has_ue
        data["localized_name"] = get_localized_name(name) if not is_workspace_mode else name
        results.append(data)

    return sorted(results, key=lambda x: x["name"])
```

**`components/mods/mod_card.py`**
*(Adding support for the UNMAPPED action state)*
```python
# components/mods/mod_card.py
import flet as ft
import os
import sys
import subprocess
import glob
import re
import threading
import time
from components.mods.mod_details import ModDetails

def open_folder(path: str):
    if path and os.path.exists(path):
        if os.name == 'nt':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', path])
        else:
            subprocess.Popen(['xdg-open', path])

def open_file_in_explorer(file_path: str):
    if not file_path:
        return
    if os.path.exists(file_path):
        if os.name == 'nt':
            subprocess.run(['explorer.exe', f'/select,{os.path.normpath(file_path)}'])
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', '-R', file_path])
        else:
            parent_dir = os.path.dirname(file_path)
            if os.path.exists(parent_dir):
                subprocess.Popen(['xdg-open', parent_dir])

def safe_update(control):
    try:
        control.update()
    except Exception:
        pass

class ModItem:
    def __init__(self, mod_data: dict, on_action_click, on_cancel_click, on_pick_icon, on_pick_audio, on_play_audio, on_clear_audio,
                 on_toggle_altermatic, on_add_variant, on_edit_variant, on_delete_variant,
                 is_building: bool, show_mapped: bool):
        self.mod_data = mod_data
        self.on_action_click = on_action_click
        self.on_cancel_click = on_cancel_click
        self.on_pick_icon = on_pick_icon
        self.on_pick_audio = on_pick_audio
        self.on_play_audio = on_play_audio
        self.on_clear_audio = on_clear_audio
        self.on_toggle_altermatic = on_toggle_altermatic
        self.on_add_variant = on_add_variant
        self.on_edit_variant = on_edit_variant
        self.on_delete_variant = on_delete_variant
        
        self.is_building = is_building
        self.show_mapped = show_mapped

        self.import_total_steps = 1
        self.import_current_step = 0

        self.name_text = ft.Text(
            value=self.get_display_name(),
            weight=ft.FontWeight.BOLD,
            size=16
        )

        self.details_visible = False
        self.chevron = ft.IconButton(
            icon=ft.Icons.KEYBOARD_ARROW_DOWN,
            on_click=self.toggle_details,
            icon_size=20
        )

        badge_controls = []
        for text, color_hex in mod_data["badges"]:
            tooltip_msg = ""
            if text == "UNMAPPED":
                tooltip_msg = "This workspace mod is not mapped to a target Pal. Click the Map button."
            elif text == "RAW":
                tooltip_msg = "FModel files extracted, but no Blender (.blend) file has been created yet."
            elif text == "SOURCE":
                tooltip_msg = "Blender (.blend) source file detected. Mod is actively being worked on."
            elif text == "UE ASSETS":
                tooltip_msg = "Unreal Engine binaries (.uasset) found in the ModKit project."
            elif text == "MODIFIED":
                tooltip_msg = "Warning: Files have been manually modified inside Unreal Engine since your last Push!"
            elif text == "SRC CHANGED":
                tooltip_msg = "Source files (Blender/textures) have been edited since your last Push! It is recommended to run 'Push & Cook & Pack'."
            elif text == "ALTERMATIC":
                tooltip_msg = "Altermatic dynamic variants are active for this Pal."

            badge_controls.append(
                ft.Container(
                    content=ft.Text(text, size=10, weight=ft.FontWeight.BOLD),
                    bgcolor=color_hex, 
                    padding=ft.Padding(left=6, right=6, top=2, bottom=2), 
                    border_radius=4,
                    tooltip=tooltip_msg
                )
            )

        status_colors = {
            "Packed": ft.Colors.GREEN_400,
            "Packed with Errors": ft.Colors.YELLOW_400,
            "Outdated": ft.Colors.ORANGE_400,
            "Unpacked": ft.Colors.RED_400
        }
        status_color = status_colors.get(mod_data["pak_status"], ft.Colors.RED_400)

        self.update_primary_button_config()

        self.primary_button = ft.ElevatedButton(
            self.primary_text, 
            icon=self.primary_icon, 
            on_click=self.handle_button_click, 
            disabled=self.is_building or self.primary_action == "none"
        )

        overflow_menu = ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT,
            items=[
                ft.PopupMenuItem(content=ft.Text("Push to Unreal"), on_click=lambda e: on_action_click(self.mod_data, "push"), disabled=not self.mod_data["has_fmodel"] or not self.mod_data.get("has_blend", False) or self.mod_data.get("is_unmapped", False)),
                ft.PopupMenuItem(content=ft.Text("Cook & Pack (Skip Import)"), on_click=lambda e: on_action_click(self.mod_data, "cook"), disabled=not self.mod_data["has_ue"] or self.mod_data.get("is_unmapped", False)),
                ft.PopupMenuItem(content=ft.Text("Push & Cook & Pack"), on_click=lambda e: on_action_click(self.mod_data, "full"), disabled=not self.mod_data["has_fmodel"] or not self.mod_data.get("has_blend", False) or self.mod_data.get("is_unmapped", False)),
                ft.PopupMenuItem(content=ft.Text("Generate Sources"), on_click=lambda e: on_action_click(self.mod_data, "decompile"), disabled=not self.mod_data["has_ue"] or self.mod_data.get("is_unmapped", False))
            ]
        )

        row_controls: list[ft.Control] = [
            self.chevron,
            ft.Icon(ft.Icons.FOLDER, color=ft.Colors.BLUE_200),
            self.name_text,
            ft.Row(badge_controls, spacing=5),
            ft.Container(expand=True),
            ft.Text(mod_data["pak_status"], color=status_color, size=12, width=120, text_align=ft.TextAlign.RIGHT),
            self.primary_button,
            overflow_menu
        ]
        self.main_row = ft.Row(controls=row_controls)

        self.progress_bar = ft.ProgressBar(value=0.0, color=ft.Colors.CYAN_400, bgcolor=ft.Colors.WHITE10)
        self.status_text = ft.Text("Waiting...", size=12, color=ft.Colors.WHITE54, italic=True)
        self.progress_container = ft.Column(
            controls=[
                ft.Divider(height=1, color=ft.Colors.WHITE24),
                self.progress_bar,
                self.status_text
            ],
            visible=False,
            spacing=5
        )

        self.details = ModDetails(
            mod_data=mod_data, 
            on_pick_icon=self.on_pick_icon,
            on_pick_audio=self.on_pick_audio,
            on_play_audio=self.on_play_audio,
            on_clear_audio=self.on_clear_audio,
            on_toggle_altermatic=self.on_toggle_altermatic,
            on_add_variant=self.on_add_variant,
            on_edit_variant=self.on_edit_variant,
            on_delete_variant=self.on_delete_variant
        )
        self.details_container = ft.Container(content=self.details.view, visible=False)

        self.container = ft.Container(
            content=ft.Column([self.main_row, self.progress_container, self.details_container], spacing=0),
            padding=10,
            border=ft.Border.all(1, ft.Colors.WHITE24),
            border_radius=8,
            animate=ft.Animation(500, ft.AnimationCurve.EASE_OUT) 
        )

        self.view = ft.ContextMenu(
            content=self.container,
            secondary_items=[
                ft.PopupMenuItem(content=ft.Text("Open source in file explorer"), on_click=lambda e: open_folder(self.mod_data["fmodel_path"]), disabled=not self.mod_data["has_fmodel"]),
                ft.PopupMenuItem(content=ft.Text("Open unreal assets in file explorer"), on_click=lambda e: open_folder(self.mod_data["ue_path"]), disabled=not self.mod_data["has_ue"]),
                ft.PopupMenuItem(
                    content=ft.Text("Open PAK in file explorer"), 
                    on_click=lambda e: open_file_in_explorer(self.mod_data.get("pak_path", "")), 
                    disabled=self.mod_data.get("pak_status") != "Packed"
                ),
                ft.PopupMenuItem(
                    content=ft.Text("Show in Unreal Content Browser"),
                    on_click=lambda e: on_action_click(self.mod_data, "browse_unreal"),
                    disabled=not self.mod_data["has_ue"]
                )
            ]
        ) # type: ignore

    def toggle_details(self, e):
        self.details_visible = not self.details_visible
        self.details_container.visible = self.details_visible
        self.chevron.icon = ft.Icons.KEYBOARD_ARROW_UP if self.details_visible else ft.Icons.KEYBOARD_ARROW_DOWN
        safe_update(self.view)

    def handle_button_click(self, e):
        if self.is_building:
            if self.on_cancel_click:
                self.on_cancel_click()
        elif self.primary_action == "create_blend":
            self.on_action_click(self.mod_data, "create_blend")
        elif self.primary_action == "open_folder":
            open_folder(self.mod_data["fmodel_path"])
        else:
            self.on_action_click(self.mod_data, self.primary_action)

    def update_primary_button_config(self):
        if self.mod_data.get("is_unmapped"):
            self.primary_text = "Map Mod to Pal"
            self.primary_action = "map_mod"
            self.primary_icon = ft.Icons.MAP
        elif self.mod_data["has_ue"]:
            if self.mod_data.get("source_modified", False):
                self.primary_text = "Push & Cook & Pack"
                self.primary_action = "full"
                self.primary_icon = ft.Icons.PUBLISH
            else:
                self.primary_text = "Cook & Pack"
                self.primary_action = "cook"
                self.primary_icon = ft.Icons.FAST_FORWARD
        elif self.mod_data["has_fmodel"]:
            if not self.mod_data.get("has_blend", False):
                self.primary_text = "Create .blend file"
                self.primary_action = "create_blend"
                self.primary_icon = ft.Icons.CREATE_NEW_FOLDER
            else:
                self.primary_text = "Push to Unreal"
                self.primary_action = "push"
                self.primary_icon = ft.Icons.CLOUD_UPLOAD
        else:
            self.primary_text = "Unavailable"
            self.primary_action = "none"
            self.primary_icon = ft.Icons.BLOCK

    def get_display_name(self) -> str:
        return str(self.mod_data["localized_name"]) if self.show_mapped else str(self.mod_data["name"])

    def set_show_mapped(self, show_mapped: bool):
        self.show_mapped = show_mapped
        self.name_text.value = self.get_display_name()
        safe_update(self.name_text)

    def set_state(self, global_building: bool, is_active_target: bool = False, success: bool | None = None):
        self.is_building = global_building
        self.update_primary_button_config()

        if is_active_target:
            fmodel_path = self.mod_data["fmodel_path"]
            if os.path.exists(fmodel_path):
                pngs = len(glob.glob(os.path.join(fmodel_path, "*.png")))
                jsons = len(glob.glob(os.path.join(fmodel_path, "MI_*.json")))
                fbx = 1 if glob.glob(os.path.join(fmodel_path, "*.fbx")) else 0
                self.import_total_steps = pngs + jsons + fbx + 1
            else:
                self.import_total_steps = 1
            
            self.import_current_step = 0
            self.progress_container.visible = True
            self.progress_bar.value = 0.0
            self.status_text.value = "Starting pipeline..."
            self.container.border = ft.Border.all(1, ft.Colors.CYAN_700)
            
            setattr(self.primary_button, "text", "Cancel")
            self.primary_button.icon = ft.Icons.CANCEL
            self.primary_button.style = ft.ButtonStyle(color=ft.Colors.RED_400)
            self.primary_button.disabled = False
        else:
            self.progress_container.visible = False
            setattr(self.primary_button, "text", self.primary_text)
            self.primary_button.icon = self.primary_icon
            self.primary_button.style = None
            self.primary_button.disabled = global_building or self.primary_action == "none"
            
            if success is True:
                self.container.border = ft.Border.all(1, ft.Colors.GREEN_500)
                def reset_border():
                    time.sleep(2.5)
                    self.container.border = ft.Border.all(1, ft.Colors.WHITE24)
                    safe_update(self.view)
                threading.Thread(target=reset_border, daemon=True).start()
            elif success is False:
                self.container.border = ft.Border.all(1, ft.Colors.RED_500)
                def reset_border():
                    time.sleep(2.5)
                    self.container.border = ft.Border.all(1, ft.Colors.WHITE24)
                    safe_update(self.view)
                threading.Thread(target=reset_border, daemon=True).start()
                
        safe_update(self.view)

    def update_progress(self, line: str, flush: bool = True):
        line = line.strip()
        if not line: return
        
        if "Running headless Blender" in line:
            self.progress_bar.value = 0.05
            self.status_text.value = "[1/4] Running Blender (Exporting FBX)..."
            
        elif "Connecting to Open Unreal Engine" in line:
            self.progress_bar.value = 0.15
            self.status_text.value = "[2/4] Connecting to Unreal Engine..."
        elif "Importing texture:" in line or "Importing skeletal mesh:" in line or "Creating material instance:" in line or "Linking Materials" in line:
            self.import_current_step += 1
            progress = 0.15 + (0.30 * (self.import_current_step / max(1, self.import_total_steps)))
            self.progress_bar.value = min(0.45, progress)
            self.status_text.value = f"[2/4] Importing Assets into Unreal ({self.import_current_step}/{self.import_total_steps})...."
            
        elif "Cooking Target Folders" in line:
            self.progress_bar.value = 0.45
            self.status_text.value = "[3/4] Preparing to Cook Assets..."
            
        elif "LogCook: Display: Cooked packages" in line:
            match = re.search(r"Cooked packages (\d+) Packages Remain (\d+)", line)
            if match:
                cooked = int(match.group(1))
                remain = int(match.group(2))
                total = cooked + remain
                if total > 0:
                    sub_progress = cooked / total
                    self.progress_bar.value = 0.45 + (0.45 * sub_progress)
                    self.status_text.value = f"[3/4] Cooking Assets ({cooked}/{total} packages)..."
                    
        elif "Preparing Pak" in line:
            self.progress_bar.value = 0.90
            self.status_text.value = "[4/4] Packing Cooked Assets..."
        elif "Building final PAK" in line:
            self.progress_bar.value = 0.95
            self.status_text.value = "[4/4] Generating .pak file..."
            
        if flush:
            safe_update(self.view)
```

**`views/mods_view.py`**
*(Adding the `prompt_map_mod_dialog` modal and integrating it)*
```python
# views/mods_view.py
import flet as ft
import os

from controllers.mods_controller import ModsController
from components.mods.mod_card import ModItem
from components.mods.dialogs import (
    create_overwrite_warning_dialog,
    create_decompile_options_dialog,
    create_troubleshooting_advisor_dialog
)
from components.mods.altermatic_dialog import AltermaticDialog
from utils.names import load_names_map

class ModsView:
    def __init__(self, page: ft.Page, settings: dict):
        self.main_page = page
        self.settings = settings
        
        self.controller = ModsController(self, settings)

        self.mods_list = ft.ListView(expand=True, spacing=10)
        self.log_view = ft.ListView(expand=True, spacing=2, auto_scroll=True)
        self.cached_components = {}

        self.icon_picker = ft.FilePicker()
        self.main_page.services.append(self.icon_picker)
        
        self.audio_picker = ft.FilePicker()
        self.main_page.services.append(self.audio_picker)

        self.active_icon_mod_data = None
        self.search_bar = ft.TextField(
            label="Search by internal or actual name...",
            expand=True,
            on_change=lambda e: self.controller.update_search(self.search_bar.value),
            prefix_icon=ft.Icons.SEARCH
        )
        
        self.badge_chips = ft.Row([
            ft.Text("Tags:", weight=ft.FontWeight.BOLD),
            ft.Chip(label=ft.Text("RAW"), on_select=lambda e: self.controller.update_badge_filter("RAW", e.control.selected)),
            ft.Chip(label=ft.Text("SOURCE"), on_select=lambda e: self.controller.update_badge_filter("SOURCE", e.control.selected)),
            ft.Chip(label=ft.Text("UE ASSETS"), on_select=lambda e: self.controller.update_badge_filter("UE ASSETS", e.control.selected)),
            ft.Chip(label=ft.Text("MODIFIED"), on_select=lambda e: self.controller.update_badge_filter("MODIFIED", e.control.selected)),
            ft.Chip(label=ft.Text("ALTERMATIC"), on_select=lambda e: self.controller.update_badge_filter("ALTERMATIC", e.control.selected)),
            ft.Chip(label=ft.Text("UNMAPPED"), on_select=lambda e: self.controller.update_badge_filter("UNMAPPED", e.control.selected)),
        ], spacing=10)

        self.status_chips = ft.Row([
            ft.Text("Status:", weight=ft.FontWeight.BOLD),
            ft.Chip(label=ft.Text("Packed"), on_select=lambda e: self.controller.update_status_filter("Packed", e.control.selected)),
            ft.Chip(label=ft.Text("Packed with Errors"), on_select=lambda e: self.controller.update_status_filter("Packed with Errors", e.control.selected)),
            ft.Chip(label=ft.Text("Unpacked"), on_select=lambda e: self.controller.update_status_filter("Unpacked", e.control.selected)),
            ft.Chip(label=ft.Text("Outdated"), on_select=lambda e: self.controller.update_status_filter("Outdated", e.control.selected)),
        ], spacing=10)

        self.refresh_button = ft.IconButton(
            icon=ft.Icons.REFRESH, 
            tooltip="Rescan disk for mods",
            on_click=lambda e: self.controller.refresh_mods(scan_disk=True)
        )
        self.refresh_button.disabled = False
        self.refresh_spinner = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False)

        self.console_height = int(settings.get("console_height", 200))
        
        self.mods_list_container = ft.Container(
            self.mods_list, 
            expand=True,
            border=ft.Border.all(1, ft.Colors.WHITE10), 
            border_radius=10, 
            padding=10
        )
        
        self.console_container = ft.Container(
            content=self.log_view, 
            height=self.console_height,
            bgcolor=ft.Colors.BLACK, 
            border_radius=10, 
            padding=15, 
            border=ft.Border.all(1, ft.Colors.WHITE10)
        )

        self.divider_handle = ft.GestureDetector(
            content=ft.Container(height=10, content=ft.Icon(ft.Icons.DRAG_HANDLE, size=16), bgcolor=ft.Colors.WHITE10, border_radius=5),
            on_pan_update=self.on_divider_drag
        )

        self.view = ft.Column(
            expand=True,
            controls=[
                ft.Row([self.search_bar, self.refresh_spinner, self.refresh_button]),
                self.badge_chips,
                self.status_chips,
                self.mods_list_container,
                self.divider_handle,
                ft.Row([
                    ft.Text("Build Console", size=16, weight=ft.FontWeight.BOLD),
                    ft.IconButton(icon=ft.Icons.COPY_ALL, tooltip="Copy console", on_click=self.copy_console_to_clipboard)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.console_container
            ]
        )

        self.altermatic_dialog = AltermaticDialog(
            self.main_page, 
            self.settings, 
            self.controller.traits_db, 
            self.controller.save_altermatic_variant_callback,
            on_refresh_callback=self.controller.run_refresh_pipeline_callback,
            on_delete_callback=self.controller.delete_altermatic_variant_by_index
        )

    def on_divider_drag(self, e: ft.DragUpdateEvent):
        delta = 0.0
        if hasattr(e, "local_delta") and e.local_delta is not None:
            delta = e.local_delta.y
        elif hasattr(e, "delta_y"):
            delta = e.delta_y

        new_console_height = max(50, self.console_container.height - delta)
        self.console_container.height = new_console_height
        self.console_height = new_console_height
        
        self.settings["console_height"] = new_console_height
        from utils.config import save_settings
        save_settings(self.settings)
        self.force_update()

    def run_in_thread(self, func):
        self.main_page.run_thread(func)

    def run_async_task(self, func, *args):
        self.main_page.run_task(func, *args)

    def clear_ui_cache(self):
        self.cached_components.clear()

    def render_mods(self, mods_data: list[dict], global_building: bool, active_mod_name: str):
        self.mods_list.controls.clear()
        
        for mod_data in mods_data:
            name = mod_data["name"]
            if name in self.cached_components:
                item = self.cached_components[name]
                item.mod_data = mod_data
                item.set_show_mapped(self.controller.show_mapped)
                item.set_state(global_building, is_active_target=(name == active_mod_name))
            else:
                item = ModItem(
                    mod_data=mod_data,
                    on_action_click=self.controller.handle_action,
                    on_cancel_click=self.controller.handle_cancel,
                    on_pick_icon=self.trigger_icon_picker,
                    on_pick_audio=self.trigger_audio_picker,
                    on_play_audio=self.controller.play_audio,
                    on_clear_audio=self.controller.clear_audio,
                    on_toggle_altermatic=self.controller.toggle_altermatic,
                    on_add_variant=self.controller.add_altermatic_variant,
                    on_edit_variant=self.controller.edit_altermatic_variant,
                    on_delete_variant=self.controller.delete_altermatic_variant,
                    is_building=global_building,
                    show_mapped=self.controller.show_mapped
                )
                item.set_state(global_building, is_active_target=(name == active_mod_name))
                self.cached_components[name] = item
                
            self.mods_list.controls.append(item.view)
        self.force_update()

    def prompt_map_mod_dialog(self, mod_data, on_save):
        names_map = load_names_map()
        
        # Sort items by mapped name A-Z for clean dropdown searching
        sorted_names = sorted(names_map.items(), key=lambda item: item[1])
        
        target_id_dd = ft.Dropdown(
            label="Target Pal Character ID",
            options=[ft.dropdown.Option(k, f"{v} ({k})") for k, v in sorted_names],
            expand=True
        )
        category_dd = ft.Dropdown(
            label="Category",
            options=[ft.dropdown.Option("Monster"), ft.dropdown.Option("Pending Monster")],
            value="Monster",
            expand=True
        )
        
        def save_click(e):
            if not target_id_dd.value:
                return
            on_save(mod_data, target_id_dd.value, category_dd.value)
            self.pop_dialog()
            
        dlg = ft.AlertDialog(
            title=ft.Text("Map Custom Workspace Mod"),
            content=ft.Column([
                ft.Text("Select the target Pal this custom mod replaces. This resolves where the assets are placed inside Unreal Engine.", size=12),
                target_id_dd,
                category_dd
            ], tight=True, spacing=15),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.pop_dialog()),
                ft.TextButton("Save Mapping", on_click=save_click, style=ft.ButtonStyle(color=ft.Colors.CYAN_400))
            ]
        )
        self.show_dialog(dlg)

    async def trigger_icon_picker(self, mod_data):
        result = await self.icon_picker.pick_files(allow_multiple=False, allowed_extensions=["png", "jpg", "jpeg"])
        if result and len(result) > 0:
            path = result[0].path
            if isinstance(path, str):
                self.controller.apply_custom_icon(mod_data, path)

    async def trigger_audio_picker(self, mod_data, cry_name):
        result = await self.audio_picker.pick_files(allow_multiple=False, allowed_extensions=["wav", "mp3", "ogg"])
        if result and len(result) > 0:
            path = result[0].path
            if isinstance(path, str):
                await self.controller.apply_custom_audio(mod_data, cry_name, path)

    def update_card_progress(self, mod_name: str, line: str, flush: bool):
        if mod_name in self.cached_components:
            self.cached_components[mod_name].update_progress(line, flush)

    def reset_card_state(self, mod_name: str, success: bool):
        if mod_name in self.cached_components:
            self.cached_components[mod_name].set_state(global_building=False, is_active_target=False, success=success)

    def prompt_overwrite_warning(self, mod_data, confirm_callback):
        dlg = create_overwrite_warning_dialog(mod_data.get("ue_modified_files", []), lambda e: (self.pop_dialog(), confirm_callback()), lambda e: self.pop_dialog())
        self.show_dialog(dlg)

    def prompt_decompile_options(self, mod_data):
        dlg = create_decompile_options_dialog(
            lambda e: (self.pop_dialog(), self.controller.execute_decompile_pipeline(mod_data, False)),
            lambda e: (self.pop_dialog(), self.controller.execute_decompile_pipeline(mod_data, True)),
            lambda e: self.pop_dialog()
        )
        self.show_dialog(dlg)

    def prompt_troubleshooting_advisor(self, summary):
        dlg = create_troubleshooting_advisor_dialog(summary, lambda e: self.pop_dialog())
        self.show_dialog(dlg)

    def set_refresh_state(self, loading: bool):
        self.refresh_button.disabled = loading
        self.refresh_spinner.visible = loading
        self.force_update()

    def set_log_autoscroll(self, enabled: bool):
        self.log_view.auto_scroll = enabled
        self.force_update()

    def write_log(self, text: str, category: str = "standard", flush: bool = True):
        color_map = {
            "error": ft.Colors.RED_400, "warning": ft.Colors.ORANGE_400, 
            "success": ft.Colors.GREEN_400, "stage": ft.Colors.CYAN_400, "standard": ft.Colors.WHITE70
        }
        self.log_view.controls.append(ft.Text(text, color=color_map.get(category, ft.Colors.WHITE70), size=12, font_family="Consolas"))
        if len(self.log_view.controls) > 100:
            self.log_view.controls = self.log_view.controls[-100:]
        if flush: self.force_update()

    def render_empty(self):
        self.mods_list.controls.clear()
        self.mods_list.controls.append(ft.Text("No mods match active filters.", color=ft.Colors.YELLOW_400))
        self.force_update()

    def render_error(self, message: str):
        self.mods_list.controls.clear()
        self.mods_list.controls.append(ft.Text(message, color=ft.Colors.RED_400))
        self.force_update()

    def show_dialog(self, dlg: ft.AlertDialog):
        if hasattr(self.main_page, "show_dialog"):
            self.main_page.show_dialog(dlg)
        elif hasattr(self.main_page, "open"):
            self.main_page.open(dlg)
        else:
            self.main_page.dialog = dlg
            dlg.open = True
            self.main_page.update()

    def pop_dialog(self):
        if hasattr(self.main_page, "pop_dialog"):
            try:
                self.main_page.pop_dialog()
                return
            except Exception:
                pass
                
        if hasattr(self.main_page, "close") and hasattr(self.main_page, "dialog") and self.main_page.dialog:
            try:
                self.main_page.close(self.main_page.dialog)
                return
            except Exception:
                pass
                
        if hasattr(self.main_page, "dialog") and self.main_page.dialog:
            self.main_page.dialog.open = False
            self.main_page.update()

    def show_snackbar(self, message: str, color):
        self.main_page.overlay.append(ft.SnackBar(ft.Text(message, color=color), open=True))
        self.main_page.update()

    def force_update(self):
        try: self.view.update()
        except Exception: pass

    async def copy_console_to_clipboard(self, e):
        log_lines = [ctrl.value for ctrl in self.log_view.controls if isinstance(ctrl, ft.Text) and ctrl.value]
        full_log = "\n".join(log_lines)
        if full_log.strip():
            await ft.Clipboard().set(full_log)
            self.main_page.overlay.append(ft.SnackBar(ft.Text("Console content copied!"), open=True))
        self.main_page.update()

    def refresh_mods(self, scan_disk: bool = True):
        self.controller.refresh_mods(scan_disk)
```

**`controllers/mods_controller.py`**
*(Routing `map_mod` logic and pipeline args to handle workspace mods)*
```python
# controllers/mods_controller.py
import asyncio
import os
import sys
import shutil
import subprocess
from utils import get_mod_info
from utils.builder.pipeline_runner import run_pipeline_async
from utils.builder.log_analyzer import LogAnalyzer
from utils.plugins.decompiler import run_decompile_pipeline

from controllers.audio_controller import AudioController
from controllers.altermatic_controller import AltermaticController

class ModsController:
    def __init__(self, view, settings: dict):
        self.view = view
        self.settings = settings
        
        self.is_building = False
        self.active_mod_name = ""
        self.active_token = {"process": None}
        
        self.raw_mods: list[dict] = []
        self.search_query = ""
        self.show_mapped = False
        self.selected_badges: set[str] = set()
        self.selected_statuses: set[str] = set()

        self.audio = AudioController(self)
        self.altermatic = AltermaticController(self)

        from utils.altermatic_helper import load_traits_database
        self.traits_db = load_traits_database()

    def update_search(self, query: str):
        self.search_query = query
        self.apply_filters()

    def update_badge_filter(self, badge: str, selected: bool):
        if selected:
            self.selected_badges.add(badge)
        else:
            self.selected_badges.discard(badge)
        self.apply_filters()

    def update_status_filter(self, status: str, selected: bool):
        if selected:
            self.selected_statuses.add(status)
        else:
            self.selected_statuses.discard(status)
        self.apply_filters()

    def refresh_mods(self, scan_disk: bool = True):
        self.show_mapped = bool(self.settings.get("show_mapped", False))

        if scan_disk:
            self.view.set_refresh_state(loading=True)
            def worker():
                try:
                    self.raw_mods = get_mod_info(self.settings)
                    self.view.clear_ui_cache()
                except Exception as e:
                    print(f"[PalBaker] Disk scan encountered an error: {e}", flush=True)
                finally:
                    self.view.set_refresh_state(loading=False)
                    self.apply_filters()
            self.view.run_in_thread(worker)
        else:
            self.apply_filters()

    def apply_filters(self):
        filtered_mods = []
        for mod in self.raw_mods:
            search_lower = self.search_query.lower()
            name_match = (search_lower in mod["name"].lower()) or (search_lower in mod["localized_name"].lower())
            if not name_match: continue

            if self.selected_badges:
                mod_badges = {b[0] for b in mod["badges"]}
                if not self.selected_badges.issubset(mod_badges): continue

            if self.selected_statuses:
                if mod["pak_status"] not in self.selected_statuses: continue

            filtered_mods.append(mod)

        filtered_mods.sort(key=lambda x: str(x["localized_name"] if self.show_mapped else x["name"]).lower())

        if not filtered_mods:
            self.view.render_empty()
        else:
            self.view.render_mods(filtered_mods, self.is_building, self.active_mod_name)

    def apply_custom_icon(self, mod_data: dict, src_path: str):
        self.audio.mc.apply_custom_icon(mod_data, src_path)

    async def run_async_task_threadsafe(self, func, *args):
        return await asyncio.to_thread(func, *args)

    def toggle_altermatic(self, mod_data: dict, is_active: bool):
        self.altermatic.toggle_altermatic(mod_data, is_active)

    def add_altermatic_variant(self, mod_data: dict):
        self.altermatic.add_altermatic_variant(mod_data)

    def edit_altermatic_variant(self, mod_data: dict, index: int):
        self.altermatic.edit_altermatic_variant(mod_data, index)

    def delete_altermatic_variant(self, mod_data: dict, index: int):
        self.altermatic.delete_altermatic_variant(mod_data, index)

    def delete_altermatic_variant_by_index(self, monster_name: str, index: int):
        self.altermatic.delete_altermatic_variant_by_index(monster_name, index)

    def save_altermatic_variant_callback(self, index: int, variant_data: dict):
        self.altermatic.save_altermatic_variant_callback(index, variant_data)

    def run_refresh_pipeline_callback(self, monster_name: str):
        mod_data = next((m for m in self.raw_mods if m["name"] == monster_name), None)
        if mod_data:
            self.execute_pipeline(mod_data, "refresh_blend")

    async def apply_custom_audio(self, mod_data: dict, cry_name: str, src_path: str):
        await self.audio.apply_custom_audio(mod_data, cry_name, src_path)

    async def clear_audio(self, mod_data: dict, cry_name: str):
        await self.audio.clear_audio(mod_data, cry_name)

    async def play_audio(self, mod_data: dict, cry_name: str):
        await self.audio.play_audio(mod_data, cry_name)

    def save_map_mod(self, mod_data: dict, target_id: str, target_cat: str):
        sidecar_path = os.path.join(mod_data["fmodel_path"], f"{mod_data['name']}_blend.json")
        routing_metadata = {
            "target_character_id": target_id,
            "target_category": target_cat,
            "ue_virtual_path": f"/Game/Pal/Model/Character/{target_cat.replace(' ', '_')}/{target_id}"
        }
        
        from utils.sidecar import update_sidecar_fields
        update_sidecar_fields(sidecar_path, routing_metadata=routing_metadata)
        
        self.view.write_log(f"Successfully mapped workspace mod '{mod_data['name']}' -> {target_id}.", "success")
        self.refresh_mods(scan_disk=True)

    def handle_action(self, mod_data, action):
        if self.is_building: return
        
        if action == "map_mod":
            self.view.prompt_map_mod_dialog(mod_data, self.save_map_mod)
            return

        if action in ["push", "full"] and mod_data.get("ue_modified"):
            self.view.prompt_overwrite_warning(mod_data, lambda: self.execute_pipeline(mod_data, action))
        elif action == "decompile":
            self.view.prompt_decompile_options(mod_data)
        elif action == "browse_unreal":
            self.execute_browse_unreal(mod_data)
        else:
            self.execute_pipeline(mod_data, action)

    def handle_cancel(self):
        if self.active_token and self.active_token.get("process"):
            self.view.write_log("\n[!] Force terminating the active pipeline...", "error")
            try:
                proc = self.active_token["process"]
                if os.name == 'nt':
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    proc.kill()
            except Exception as e:
                self.view.write_log(f"Error terminating process: {e}", "error")

    def execute_decompile_pipeline(self, mod_data, overwrite: bool = False):
        self.is_building = True
        self.active_mod_name = mod_data["name"]
        self.refresh_mods(scan_disk=False)
        self.view.write_log(f"\n>>> EXECUTING DECOMPILER: {mod_data['name']}", "stage")
        
        async def decompile_task():
            mod_path = mod_data.get("fmodel_path")
            target_id = mod_data.get("target_id", mod_data["name"])
            target_cat = mod_data.get("target_category", "Monster")
            
            category_sanitized = target_cat.replace(" ", "_")
            ue_virtual_path = f"/Game/Pal/Model/Character/{category_sanitized}/{target_id}"
            
            success, msg = await asyncio.to_thread(
                run_decompile_pipeline,
                self.settings["ue_root"],
                self.settings["uproject"],
                mod_data["name"], # Use actual blender name (folder name)
                mod_path,
                ue_virtual_path,
                self.settings["blender"],
                verbose=True,
                overwrite=overwrite
            )
            
            analyzer = LogAnalyzer()
            for line in msg.splitlines():
                analyzed_text, category_log, is_error = analyzer.analyze_line(line)
                self.view.write_log(analyzed_text, category_log, flush=False)
                
            summary = analyzer.generate_summary(success)
            status = summary.get("status", "failed") if summary else "pure_success"
            
            if success and status == "pure_success":
                self.view.write_log("SUCCESS: Decompile completed cleanly.", "success")
            elif status == "success_with_warnings":
                self.view.write_log("WARNING: Decompile completed with warnings.", "warning")
            elif status == "success_with_errors":
                self.view.write_log("ERROR: Decompile completed but found compiler errors.", "error")
            else:
                self.view.write_log("FAILED: Decompile failed. Check logs.", "error")
                
            self.is_building = False
            self.active_mod_name = ""
            
            if summary:
                self.view.prompt_troubleshooting_advisor(summary)
                
            self.refresh_mods(scan_disk=False)
            self.refresh_mods(scan_disk=True)
            
        self.view.run_async_task(decompile_task)

    def execute_pipeline(self, mod_data, action):
        self.is_building = True
        self.view.set_log_autoscroll(True)
        self.active_mod_name = mod_data["name"]
        self.refresh_mods(scan_disk=False)
        self.view.write_log(f"\n>>> EXECUTING [{action.upper()}]: {mod_data['name']}", "stage")
        
        self.active_token = {"process": None}
        
        async def run_task():
            def log_callback(text, category, flush=True):
                if text is not None:
                    self.view.write_log(text, category, flush=False)
                if flush:
                    self.view.force_update()
                    
            def progress_callback(line, flush=True):
                self.view.update_card_progress(self.active_mod_name, line, flush)
                        
            def complete_callback(success, returncode, summary):
                status = "pure_success"
                if summary:
                    status = summary.get("status", "failed")

                if status == "pure_success" and success:
                    self.view.write_log("SUCCESS: Operation completed cleanly.", "success")
                elif status == "success_with_warnings":
                    self.view.write_log(f"WARNING: Operation completed with {summary['total_warnings']} warnings.", "warning")
                elif status == "success_with_errors":
                    self.view.write_log(f"ERROR: Operation completed but found {summary['total_errors']} compilation errors.", "error")
                else:
                    self.view.write_log(f"FAILED: Process terminated with exit code {returncode}", "error")
                
                self.is_building = False
                self.view.set_log_autoscroll(False)
                self.active_token = {"process": None}
                
                card_success = success and (status != "success_with_errors")
                self.view.reset_card_state(self.active_mod_name, card_success)
                self.active_mod_name = ""
                
                if summary:
                    self.view.prompt_troubleshooting_advisor(summary)
                    
                self.refresh_mods(scan_disk=False)
                self.refresh_mods(scan_disk=True)

            mod_path = mod_data.get("fmodel_path") or mod_data.get("ue_path")
            
            # Pass folder name and absolute directory directly to build_mod.py
            script_args = [mod_data["name"], mod_path, action]
            await run_pipeline_async(script_args, log_callback, progress_callback, complete_callback, self.active_token)

        self.view.run_async_task(run_task)

    def execute_browse_unreal(self, mod_data):
        self.is_building = True
        self.active_mod_name = mod_data["name"]
        self.refresh_mods(scan_disk=False)
        self.view.write_log(f"\n>>> FOCUSING UNREAL CONTENT BROWSER: {mod_data['name']}", "stage")
        
        async def browse_task():
            target_id = mod_data.get("target_id", mod_data["name"])
            target_cat = mod_data.get("target_category", "Monster")

            category_sanitized = target_cat.replace(" ", "_")
            ue_virtual_path = f"/Game/Pal/Model/Character/{category_sanitized}/{target_id}"
            python_cmd = f'import unreal; unreal.EditorUtilityLibrary.sync_browser_to_folders(["{ue_virtual_path}"])'
            
            from utils.builder.unreal_helper import run_remote_command, focus_unreal_window
            target_project_name = os.path.splitext(os.path.basename(self.settings["uproject"]))[0]
            
            success, msg = await asyncio.to_thread(
                run_remote_command,
                self.settings["ue_root"],
                target_project_name,
                python_cmd
            )
            
            if success:
                self.view.write_log(f"SUCCESS: Focused Content Browser to: {ue_virtual_path}", "success")
                focus_unreal_window(target_project_name)
            else:
                self.view.write_log(f"FAILED to focus Unreal: {msg}", "error")
                
            self.is_building = False
            self.active_mod_name = ""
            self.refresh_mods(scan_disk=False)
            
        self.view.run_async_task(browse_task)
```

**`utils/builder/workspace.py`**
*(Parsing the target IDs directly from the workspace and overriding virtual paths)*
```python
# utils/builder/workspace.py
import os
import json
from utils.sidecar import read_sidecar

def get_virtual_path_for_file(absolute_path: str) -> str:
    clean_path = absolute_path.replace("\\", "/")
    marker = "Pal/Content/"
    if marker in clean_path:
        relative_part = clean_path.split(marker, 1)[1]
        folder_part = "/".join(relative_part.split("/")[:-1]).replace(" ", "_")
        return f"/Game/{folder_part}"
    return ""

class ModWorkspace:
    def __init__(self, folder_name: str, mod_path: str, settings: dict):
        self.folder_name = folder_name
        self.mod_path = mod_path
        self.settings = settings

        self.fmodel_root = settings.get("fmodel_output", "")
        self.ue_root = settings.get("ue_root", "")
        self.uproject_path = settings.get("uproject", "")
        self.blender_path = settings.get("blender", "blender")
        self.palworld_exe = settings.get("palworld_exe", "")

        # Target determinations
        self.target_id = folder_name
        self.category = "Monster"
        
        workspace_root = settings.get("workspace", "")
        self.is_workspace_mode = bool(workspace_root and mod_path.startswith(workspace_root))

        # Check sidecar for hybrid metadata routing
        sidecar_path = os.path.join(mod_path, f"{folder_name}_blend.json")
        if os.path.exists(sidecar_path):
            sidecar = read_sidecar(sidecar_path)
            routing = sidecar.get("routing_metadata", {})
            if routing:
                self.target_id = routing.get("target_character_id", self.target_id)
                self.category = routing.get("target_category", self.category)
        elif not self.is_workspace_mode:
            parts = mod_path.replace("\\", "/").split("/")
            if "Character" in parts:
                idx = parts.index("Character")
                if idx + 1 < len(parts):
                    self.category = parts[idx + 1]

        self.monster_name = self.target_id
        
        self.project_dir = os.path.dirname(self.uproject_path) if self.uproject_path else ""
        self.target_project_name = os.path.splitext(os.path.basename(self.uproject_path))[0] if self.uproject_path else ""

        self.ue_cmd_path = os.path.join(self.ue_root, "Engine", "Binaries", "Win64", "UnrealEditor-Cmd.exe") if self.ue_root else ""
        self.unrealpak_path = os.path.join(self.ue_root, "Engine", "Binaries", "Win64", "UnrealPak.exe") if self.ue_root else ""

        self.fmodel_dir = mod_path
        
        if self.is_workspace_mode:
            self.fmodel_altermatic_dir = os.path.join(self.fmodel_dir, "Palbaker")
        else:
            self.fmodel_altermatic_dir = os.path.join(self.fmodel_root, "Exports", "Pal", "Content", "Palbaker", "Model", "Character", self.category, self.target_id) if self.fmodel_root else ""
        
        is_altermatic_active = False
        base_type = "vanilla"
        manifest_path = os.path.join(self.fmodel_altermatic_dir if self.fmodel_altermatic_dir else self.fmodel_dir, f"{self.target_id}_altermatic.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    is_altermatic_active = bool(data.get("is_altermatic_active", False))
                    
                    variants = data.get("variants", [])
                    if isinstance(variants, dict):
                        base_block = variants.get("base", {})
                    else:
                        base_block = next((v for v in variants if v.get("is_base")), {})
                    
                    base_skeleton = base_block.get("SkeletonSource", "base")
                    base_type = "custom" if base_skeleton != "base" else "vanilla"
            except Exception:
                pass
                
        self.is_altermatic_active = is_altermatic_active
        self.base_type = base_type

        # Fix UI Icons if working in standard FModel
        self.icon_fmodel_path = os.path.join(self.fmodel_root, "Exports", "Pal", "Content", "Pal", "Texture", "PalIcon", "Normal", f"T_{self.target_id}_icon_normal.png") if self.fmodel_root and not self.is_workspace_mode else ""
        self.has_icon = os.path.exists(self.icon_fmodel_path) if self.icon_fmodel_path else False

        category_sanitized = self.category.replace(" ", "_")
        self.ue_virtual_path = f"/Game/Pal/Model/Character/{category_sanitized}/{self.target_id}"
        self.ue_altermatic_virtual_path = f"/Game/Palbaker/Model/Character/{category_sanitized}/{self.target_id}"
        
        self.skeleton_virtual_path = f"/Game/Pal/Model/Character/Skeleton/{self.target_id}"
        self.anims_virtual_path = f"/Game/Pal/Animation/Character/Monster/{self.target_id}"
        self.blueprint_virtual_path = f"/Game/Pal/Blueprint/Character/Monster/PalActorBP/{self.target_id}"
        self.icon_virtual_path = "/Game/Pal/Texture/PalIcon/Normal"

        self.config_dir = os.path.join(self.project_dir, "Config") if self.project_dir else ""
        self.ini_path = os.path.join(self.config_dir, "DefaultGame.ini") if self.config_dir else ""
        self.ini_backup = os.path.join(self.config_dir, "DefaultGame.ini.palbaker.bak") if self.config_dir else ""

        self.cooked_dir = os.path.join(self.project_dir, "Saved", "Cooked", "Windows", self.target_project_name, "Content", self.ue_virtual_path.replace("/Game/", "").replace("/", os.sep)) if self.project_dir else ""
        self.cooked_altermatic_dir = os.path.join(self.project_dir, "Saved", "Cooked", "Windows", self.target_project_name, "Content", self.ue_altermatic_virtual_path.replace("/Game/", "").replace("/", os.sep)) if self.project_dir else ""
        self.cooked_skel_dir = os.path.join(self.project_dir, "Saved", "Cooked", "Windows", self.target_project_name, "Content", self.skeleton_virtual_path.replace("/Game/", "").replace("/", os.sep)) if self.project_dir else ""
        self.cooked_anims_dir = os.path.join(self.project_dir, "Saved", "Cooked", "Windows", self.target_project_name, "Content", self.anims_virtual_path.replace("/Game/", "").replace("/", os.sep)) if self.project_dir else ""
        self.cooked_bp_dir = os.path.join(self.project_dir, "Saved", "Cooked", "Windows", self.target_project_name, "Content", self.blueprint_virtual_path.replace("/Game/", "").replace("/", os.sep)) if self.project_dir else ""
        
        self.anims_source_dir = os.path.join(self.project_dir, "Content", "Pal", "Animation", "Character", "Monster", self.target_id) if self.project_dir else ""
        self.has_anims = os.path.exists(self.anims_source_dir) if self.anims_source_dir else False

        self.custom_shader_raw = os.path.join(self.project_dir, "Content", "CartoonCelShader", "Materials", "CelShader") if self.project_dir else ""
        self.has_custom_shader = os.path.exists(self.custom_shader_raw) if self.custom_shader_raw else False

        self.output_dir = self.fmodel_dir if os.path.exists(self.fmodel_dir) else self.project_dir
        if self.palworld_exe and os.path.exists(self.palworld_exe):
            self.output_dir = os.path.join(os.path.dirname(self.palworld_exe), "Pal", "Content", "Paks", "palBaker")

        self.output_pak_clean = os.path.join(self.output_dir, f"{self.target_id}_P.pak")
        self.output_pak_err = os.path.join(self.output_dir, f"{self.target_id}_err_P.pak")

        self.audio_media_dir = os.path.join(self.fmodel_dir, ".palbaker_audio", "WwiseAudio", "Media") if self.fmodel_dir else ""
```

**`build_mod.py`**
*(Refactored to take raw pathings)*
```python
# build_mod.py
import os
import sys
import glob
import json
import shutil
import subprocess
from utils.builder.workspace import ModWorkspace
from utils.builder.config_helper import restore_palbaker_backup, GameIniCookContext
from utils.builder.blender_helper import run_headless_blender
from utils.builder.unreal_helper import run_remote_import
from utils.builder.cooker_helper import clean_cook_environment, resolve_packaging_manifest, run_and_stream, pack_cooked_assets
from utils.state import save_push_state

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding='utf-8')

def main():
    if len(sys.argv) < 4:
        print("ERROR: Missing arguments. Usage: build_mod.py <folder_name> <mod_path> <action>")
        sys.exit(1)

    FOLDER_NAME = sys.argv[1]
    MOD_PATH = sys.argv[2] 
    ACTION = sys.argv[3]   

    SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "manager_settings.json")
    with open(SETTINGS_FILE, "r") as f:
        settings = json.load(f)

    workspace = ModWorkspace(FOLDER_NAME, MOD_PATH, settings)
    
    # Expose resolved parameters to downstream functions
    MONSTER_NAME = workspace.target_id

    # -------------------------------------------------------------
    # PHASE 0: RAW FMODEL DECOMPILE (Create .blend file)
    # -------------------------------------------------------------
    if ACTION == "create_blend":
        psk_files = glob.glob(os.path.join(workspace.fmodel_dir, "*.psk"))
        if not psk_files:
            print("ERROR: No .psk skeletal mesh found in FModel directory.", flush=True)
            sys.exit(1)
            
        psk_file = psk_files[0]
        blend_file = os.path.join(workspace.fmodel_dir, f"{FOLDER_NAME}.blend")
        reconstructor_script = os.path.join(os.path.dirname(__file__), "utils", "blender_reconstruct.py")
        
        psk_file_clean = psk_file.replace("\\", "/")
        blend_file_clean = blend_file.replace("\\", "/")
        
        from utils.fmodel_helper import preprocess_fmodel_textures
        preprocess_fmodel_textures(workspace.fmodel_dir, workspace.fmodel_root)
        
        print("Launching headless Blender to reconstruct .blend workspace from .psk...", flush=True)
        result = run_headless_blender(
            workspace.blender_path, 
            None, 
            reconstructor_script, 
            ["--fbx", psk_file_clean, "--output", blend_file_clean]
        )
        
        if os.path.exists(blend_file):
            print(f"SUCCESS! .blend file generated at: {blend_file}", flush=True)
            
            extractor_script = os.path.normpath(os.path.join(os.path.dirname(__file__), "utils", "blender_extractor.py"))
            output_json = os.path.join(workspace.fmodel_dir, f"{FOLDER_NAME}_blend.json")
            
            print("Generating companion sidecar layout on the fly...", flush=True)
            run_headless_blender(
                workspace.blender_path,
                blend_file,
                extractor_script,
                ["--output", output_json]
            )
            
            if result.stdout.strip():
                print("\n=== BLENDER PIPELINE LOGS ===", flush=True)
                print(result.stdout, flush=True)
                print("=============================\n", flush=True)
        else:
            print("ERROR: Blender executed but failed to save .blend file. Internal traceback:", flush=True)
            print(result.stdout, flush=True)
            print(result.stderr, flush=True)
            sys.exit(1)

    # -------------------------------------------------------------
    # PHASE 1: IMPORT (Push to Unreal)
    # -------------------------------------------------------------
    if ACTION in ["push", "full"]:
        import_targets = []
        
        should_push_vanilla = not workspace.is_altermatic_active or workspace.base_type == "custom"

        if should_push_vanilla:
            if os.path.exists(workspace.fmodel_dir):
                import_targets.append((workspace.fmodel_dir, workspace.ue_virtual_path))
        else:
            if os.path.exists(workspace.fmodel_dir) and os.path.exists(workspace.fmodel_altermatic_dir):
                print("Standalone Altermatic Fallback active. Mirroring modified base assets to Palbaker directory...", flush=True)
                for item in os.listdir(workspace.fmodel_dir):
                    if item == f"{MONSTER_NAME}_altermatic.json" or item == ".palbaker_state.json":
                        continue
                    src_file = os.path.join(workspace.fmodel_dir, item)
                    if os.path.isfile(src_file):
                        dest_file = os.path.join(workspace.fmodel_altermatic_dir, item)
                        if not os.path.exists(dest_file) or os.path.getmtime(src_file) > os.path.getmtime(dest_file):
                            shutil.copy2(src_file, dest_file)
                            print(f"  Mirrored: {item}", flush=True)

        if workspace.is_altermatic_active and os.path.exists(workspace.fmodel_altermatic_dir) and any(f.endswith(".blend") for f in os.listdir(workspace.fmodel_altermatic_dir)):
            import_targets.append((workspace.fmodel_altermatic_dir, workspace.ue_altermatic_virtual_path))

        if not import_targets:
            print("ERROR: No raw model sources found in workspaces to push.", flush=True)
            sys.exit(1)

        from utils.altermatic_helper import sync_sidecar_metadata
        for target_dir, _ in import_targets:
            for blend_file in glob.glob(os.path.join(target_dir, "*.blend")):
                if target_dir == workspace.fmodel_altermatic_dir:
                    base_sidecar = os.path.join(workspace.fmodel_dir, f"{FOLDER_NAME}_blend.json")
                    var_base_name = os.path.splitext(os.path.basename(blend_file))[0]
                    var_sidecar = os.path.join(workspace.fmodel_altermatic_dir, f"{var_base_name}_blend.json")
                    if os.path.exists(base_sidecar) and not os.path.exists(var_sidecar):
                        print(f"  [Self-Healing] Restoring base sidecar {os.path.basename(base_sidecar)} to {os.path.basename(var_sidecar)}", flush=True)
                        shutil.copy2(base_sidecar, var_sidecar)

                print(f"Pre-import synchronizing layout metadata for {os.path.basename(blend_file)}...", flush=True)
                sync_sidecar_metadata(workspace.blender_path, blend_file)

        for target_dir, virtual_path in import_targets:
            blend_files = glob.glob(os.path.join(target_dir, "*.blend"))
            for blend_file in blend_files:
                base_name = os.path.splitext(os.path.basename(blend_file))[0]
                fbx_file = os.path.join(target_dir, f"{base_name}.fbx")
                output_json = os.path.join(target_dir, f"{base_name}_blend.json")
                
                extractor_script = os.path.join(os.path.dirname(__file__), "utils", "blender_extractor.py")
                print(f"Running headless Blender (Exporting FBX for {base_name})...", flush=True)
                run_headless_blender(workspace.blender_path, blend_file, extractor_script, ["--output", output_json, "--fbx", fbx_file])

            pngs = glob.glob(os.path.join(target_dir, "*.png"))
            jsons = glob.glob(os.path.join(target_dir, "MI_*.json"))
            fbx_files = glob.glob(os.path.join(target_dir, "*.fbx"))
            
            fbx_file = fbx_files[0] if fbx_files else ""
            base_mesh_name = os.path.splitext(os.path.basename(fbx_file))[0] if fbx_file else FOLDER_NAME

            config = {
                "ue_target_path": virtual_path,
                "textures": pngs,
                "fbx_file": fbx_file if os.path.exists(fbx_file) else None,
                "mi_jsons": jsons,
                "icon_file": workspace.icon_fmodel_path if (workspace.has_icon and target_dir == workspace.fmodel_dir) else None,
                "bone_data_file": f"{base_mesh_name}_blend.json",
                "target_character_id": MONSTER_NAME
            }
            config_path = os.path.join(target_dir, "import_config.json")
            with open(config_path, "w") as f:
                json.dump(config, f)

            print(f"Connecting to Open Unreal Engine (Target: {os.path.basename(target_dir)})...", flush=True)
            ue_import_script = os.path.join(os.path.dirname(__file__), "ue_import.py")
            success, log_msg = run_remote_import(workspace.ue_root, workspace.target_project_name, target_dir, ue_import_script)
            
            if log_msg.strip():
                print(log_msg, flush=True)
                
            if not success:
                print(f"!!! ERROR INSIDE UNREAL ENGINE DURING {os.path.basename(target_dir)} IMPORT !!!", flush=True)
                sys.exit(1)

        ue_abs_path = os.path.join(workspace.project_dir, "Content", "Pal", "Model", "Character", workspace.category, MONSTER_NAME)
        save_push_state(workspace.fmodel_dir, ue_abs_path)

    # -------------------------------------------------------------
    # PHASE 1.5: REFRESH BLEND (Sync layouts on the spot)
    # -------------------------------------------------------------
    if ACTION == "refresh_blend":
        blend_files = []
        if os.path.exists(workspace.fmodel_dir):
            blend_files.extend(glob.glob(os.path.join(workspace.fmodel_dir, "*.blend")))
        if workspace.is_altermatic_active and os.path.exists(workspace.fmodel_altermatic_dir):
            blend_files.extend(glob.glob(os.path.join(workspace.fmodel_altermatic_dir, "*.blend")))

        if not blend_files:
            print("ERROR: No .blend files found in workspace to refresh.", flush=True)
            sys.exit(1)

        extractor_script = os.path.normpath(os.path.join(os.path.dirname(__file__), "utils", "blender_extractor.py"))
        for blend_file in blend_files:
            parent_dir = os.path.dirname(blend_file)
            base_name = os.path.splitext(os.path.basename(blend_file))[0]
            output_json = os.path.normpath(os.path.join(parent_dir, f"{base_name}_blend.json"))
            
            print(f"Synchronizing sidecar layout metadata for {os.path.basename(blend_file)}...", flush=True)
            
            result = run_headless_blender(
                workspace.blender_path,
                blend_file,
                extractor_script,
                ["--output", output_json]
            )
            
            if result.stdout.strip():
                print(result.stdout, flush=True)
            if result.stderr.strip():
                print(result.stderr, flush=True)
            
        print("SUCCESS! Staged layout sync completed.", flush=True)

    # -------------------------------------------------------------
    # PHASE 2: COOK & PACK
    # -------------------------------------------------------------
    if ACTION in ["cook", "full"]:
        restore_palbaker_backup(workspace.uproject_path)
        clean_cook_environment(workspace)

        extra_cook_paths = []
        if workspace.has_custom_shader:
            extra_cook_paths.append("/Game/CartoonCelShader/Materials/CelShader")
        if workspace.has_icon:
            extra_cook_paths.append(workspace.icon_virtual_path)
        extra_cook_paths.append(workspace.blueprint_virtual_path)

        altermatic_rel_path = workspace.ue_altermatic_virtual_path.replace("/Game/", "")
        altermatic_project_source_dir = os.path.join(workspace.project_dir, "Content", os.path.normpath(altermatic_rel_path))
        
        if workspace.is_altermatic_active and os.path.exists(altermatic_project_source_dir):
            extra_cook_paths.append(workspace.ue_altermatic_virtual_path)

        with GameIniCookContext(workspace, extra_paths=extra_cook_paths):
            print("Cooking Target Folders...", flush=True)
            had_cook_issues = run_and_stream([
                workspace.ue_cmd_path, 
                workspace.uproject_path, 
                "-run=cook", 
                "-targetplatform=Windows", 
                "-unversioned", 
                "-NoUI", 
                "-Map=/Engine/Maps/Entry"
            ])

            final_pak_path = workspace.output_pak_err if had_cook_issues else workspace.output_pak_clean
            print(f"Preparing Pak (Target: {os.path.basename(final_pak_path)})...", flush=True)
            response_file = os.path.join(workspace.output_dir, "response.txt")

            folders_to_pack = resolve_packaging_manifest(workspace, workspace.has_anims)

            print("Building final PAK...", flush=True)
            files_found = pack_cooked_assets(
                workspace.unrealpak_path, 
                response_file, 
                final_pak_path, 
                folders_to_pack, 
                workspace.has_anims
            )
            
            if files_found == 0:
                print("ERROR: No files found to pack. Cook process might have failed.", flush=True)
                sys.exit(1)
                
            if not had_cook_issues:
                print(f"SUCCESS! Pak created at: {final_pak_path} ({files_found} files)", flush=True)
                for suffix in ["_err_P.pak", "_err_p.pak"]:
                    err_pak = os.path.join(workspace.output_dir, f"{MONSTER_NAME}{suffix}")
                    if os.path.exists(err_pak):
                        try:
                            os.remove(err_pak)
                        except OSError:
                            pass

                swap_json_dir = ""
                if workspace.palworld_exe and os.path.exists(workspace.palworld_exe):
                    swap_json_dir = os.path.join(os.path.dirname(workspace.palworld_exe), "Pal", "Content", "Paks", "~Mods", "SwapJSON")
                
                if workspace.is_altermatic_active and swap_json_dir and os.path.exists(workspace.fmodel_altermatic_dir):
                    from utils.altermatic_helper import compile_unified_altermatic_json
                    success, msg = compile_unified_altermatic_json(MONSTER_NAME, workspace.fmodel_altermatic_dir, swap_json_dir, workspace.category)
                    print(msg, flush=True)

if __name__ == "__main__":
    main()
```

**`utils/builder/pipeline_runner.py`**
```python
# utils/builder/pipeline_runner.py
import os
import sys
import asyncio
import subprocess
import time
from utils.builder.log_analyzer import LogAnalyzer

async def run_pipeline_async(script_args: list, log_callback, progress_callback, complete_callback, cancel_token: dict):
    script_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "build_mod.py"))
    
    analyzer = LogAnalyzer()
    cmd = [sys.executable, "-u", script_path] + script_args
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        cancel_token["process"] = process
        last_update_time = time.time()
        
        if process.stdout:
            while True:
                line_bytes = await process.stdout.readline()
                if not line_bytes:
                    break
                
                line = line_bytes.decode('utf-8', errors='replace').rstrip()
                
                analyzed_text, color, is_error = analyzer.analyze_line(line)
                log_callback(analyzed_text, color, flush=False)
                progress_callback(line, flush=False)
                
                await asyncio.sleep(0.001)
                
                current_time = time.time()
                if current_time - last_update_time >= 0.10:
                    log_callback(None, None, flush=True)
                    last_update_time = current_time

        returncode = await process.wait()
        success = (returncode == 0)
        
        summary = analyzer.generate_summary(success)
        complete_callback(success, returncode, summary)
        
    except Exception as e:
        print(f"[PalBaker] Fatal Exception in Async Pipeline Runner: {e}", flush=True)
        complete_callback(False, -1, None)
```

**`ue_import.py`**
```python
# ue_import.py
import sys
import os
import json
import unreal

palbaker_root = globals().get('PALBAKER_ROOT', '')
if palbaker_root and palbaker_root not in sys.path:
    sys.path.append(palbaker_root)

for k in list(sys.modules.keys()):
    if k.startswith("unreal_scripts"):
        del sys.modules[k]

from unreal_scripts.importer import clear_cache, import_assets
from unreal_scripts.materials import build_materials, bind_materials_to_mesh
from unreal_scripts.rigging import apply_rigging

def run_pipeline():
    working_dir = globals().get('TARGET_FOLDER', os.getcwd())
    config_path = os.path.join(working_dir, "import_config.json")
    
    with open(config_path, "r") as f:
        config = json.load(f)

    ue_path = config["ue_target_path"]
    
    # Read the explicit character mapping ID if running from custom workspaces
    target_character_id = config.get("target_character_id", ue_path.split("/")[-1])
    
    clear_cache(ue_path, config.get("fbx_file"), target_character_id)
    
    # 1. Import meshes and textures
    target_asset_path, target_phys_path = import_assets(ue_path, config["textures"], config.get("fbx_file"), target_character_id)
    
    icon_file = config.get("icon_file")
    if icon_file:
        from unreal_scripts.importer import import_icon
        import_icon(icon_file, "/Game/Pal/Texture/PalIcon/Normal")

    # 2. Build material instances dynamically (Reading the dynamic sidecar JSON file)
    bone_data_file = config.get("bone_data_file", "bone_data.json")
    sidecar_json_path = os.path.join(working_dir, bone_data_file)
    
    mi_assets = build_materials(ue_path, sidecar_json_path, config["textures"], target_asset_path)
    
    # 3. Bind everything together
    bind_materials_to_mesh(target_asset_path, target_phys_path, mi_assets)
    
    # 4. Generate & apply rigging
    apply_rigging(working_dir, ue_path, target_character_id, target_asset_path, bone_data_file)

    print("Flushing all generated assets to disk...")
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(save_map_packages=False, save_content_packages=True)
    print("--- IMPORT COMPLETE ---")

run_pipeline()
```

**`unreal_scripts/importer.py`**
*(Routing imports explicitly to `target_character_id` instead of assuming it matches `folder_name`)*
```python
# unreal_scripts/importer.py
import unreal
import os

def clear_cache(ue_path, fbx_file, target_character_id):
    if fbx_file and os.path.exists(fbx_file):
        fbx_base_name = os.path.splitext(os.path.basename(fbx_file))[0]
        paths_to_delete = [
            f"{ue_path}/SK_{fbx_base_name}",
            f"{ue_path}/SK_{target_character_id}"
        ]
        
        for path in paths_to_delete:
            if unreal.EditorAssetLibrary.does_asset_exist(path):
                print(f"[PalBaker] Clearing old mesh asset from cache: {path}")
                try:
                    unreal.EditorAssetLibrary.delete_asset(path)
                except Exception as e:
                    print(f"[PalBaker] Warning: Failed to delete mesh asset: {e}")

def import_assets(ue_path, textures, fbx_file, target_character_id):
    if textures:
        print("[PalBaker] Importing textures...")
        import_tasks = []
        for png in textures:
            if os.path.exists(png):
                tex_name = os.path.splitext(os.path.basename(png))[0]
                tex_path = f"{ue_path}/{tex_name}"
                
                task = unreal.AssetImportTask()
                task.set_editor_property('filename', png)
                task.set_editor_property('destination_path', ue_path)
                task.set_editor_property('automated', True)
                task.set_editor_property('save', True)
                task.set_editor_property('factory', unreal.TextureFactory())
                import_tasks.append(task)
                
        if import_tasks:
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(import_tasks)

    target_asset_path = ""
    target_phys_path = ""
    
    if fbx_file and os.path.exists(fbx_file):
        fbx_filename = os.path.basename(fbx_file)
        fbx_base_name = os.path.splitext(fbx_filename)[0]
        
        print(f"[PalBaker] Importing Skeletal FBX: {fbx_filename}")
        
        is_vanilla_replace = "Palbaker" not in ue_path
        if is_vanilla_replace:
            fbx_import_name = f"SK_{target_character_id}"
        else:
            fbx_import_name = f"SK_{fbx_base_name}"
            
        target_asset_path = f"{ue_path}/{fbx_import_name}"
        target_phys_path = f"{ue_path}/PA_{target_character_id}_PhysicsAsset"

        task = unreal.AssetImportTask()
        task.set_editor_property('filename', fbx_file)
        task.set_editor_property('destination_path', ue_path)
        task.set_editor_property('destination_name', fbx_import_name)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', True)
        
        import_ui = unreal.FbxImportUI()
        import_ui.set_editor_property('import_mesh', True)
        import_ui.set_editor_property('import_as_skeletal', True)
        import_ui.set_editor_property('import_materials', False)
        import_ui.set_editor_property('import_textures', False)
        import_ui.set_editor_property('import_animations', False)
        import_ui.set_editor_property('create_physics_asset', True)
        
        skel_data = import_ui.skeletal_mesh_import_data
        skel_data.set_editor_property('import_mesh_lo_ds', False)
        skel_data.set_editor_property('import_morph_targets', True)
        skel_data.set_editor_property('use_t0_as_ref_pose', True)
        
        skeleton_path = f"/Game/Pal/Model/Character/Skeleton/{target_character_id}/SK_{target_character_id}_Skeleton"
        existing_skeleton = unreal.EditorAssetLibrary.load_asset(skeleton_path)
        if existing_skeleton:
            print(f"[PalBaker] Existing skeleton found at {skeleton_path}. Merging and updating bone container...")
            import_ui.set_editor_property('skeleton', existing_skeleton)
            skel_data.set_editor_property('import_mesh_lo_ds', False)
        else:
            print(f"[PalBaker] No existing skeleton found at {skeleton_path}. Unreal will generate a new skeleton.")

        task.set_editor_property('options', import_ui)
        
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        print(f"[PalBaker] Successfully imported skeletal mesh to: {target_asset_path}")

        expected_skeleton_path = f"/Game/Pal/Model/Character/Skeleton/{target_character_id}/SK_{target_character_id}_Skeleton"
        expected_phys_path = f"{ue_path}/PA_{target_character_id}_PhysicsAsset"
        
        skeleton_relocated = False
        phys_relocated = False

        imported_paths = list(task.get_editor_property('imported_object_paths'))
        for imported_path in imported_paths:
            asset = unreal.EditorAssetLibrary.load_asset(imported_path)
            if not asset: continue
            
            asset_class = asset.get_class().get_name()
            
            if asset_class == "Skeleton":
                if imported_path != expected_skeleton_path:
                    print(f"[PalBaker] Relocating generated skeleton: {imported_path} -> {expected_skeleton_path}")
                    unreal.EditorAssetLibrary.make_directory(f"/Game/Pal/Model/Character/Skeleton/{target_character_id}")
                    if unreal.EditorAssetLibrary.rename_asset(imported_path, expected_skeleton_path):
                        print(f"[PalBaker] Successfully relocated skeleton to {expected_skeleton_path}!")
                skeleton_relocated = True
            
            elif asset_class == "PhysicsAsset":
                if imported_path != expected_phys_path:
                    print(f"[PalBaker] Relocating generated physics asset: {imported_path} -> {expected_phys_path}")
                    unreal.EditorAssetLibrary.rename_asset(imported_path, expected_phys_path)
                phys_relocated = True

        if not skeleton_relocated:
            generated_skeleton_path = f"{ue_path}/{fbx_import_name}_Skeleton"
            if unreal.EditorAssetLibrary.does_asset_exist(generated_skeleton_path) and generated_skeleton_path != expected_skeleton_path:
                print(f"[PalBaker] Hard Lookup: Relocating generated skeleton: {generated_skeleton_path} -> {expected_skeleton_path}")
                unreal.EditorAssetLibrary.make_directory(f"/Game/Pal/Model/Character/Skeleton/{target_character_id}")
                if unreal.EditorAssetLibrary.rename_asset(generated_skeleton_path, expected_skeleton_path):
                    print(f"[PalBaker] Successfully relocated skeleton to {expected_skeleton_path}!")

        if not phys_relocated:
            generated_phys_path = f"{ue_path}/{fbx_import_name}_PhysicsAsset"
            if unreal.EditorAssetLibrary.does_asset_exist(generated_phys_path) and generated_phys_path != expected_phys_path:
                print(f"[PalBaker] Hard Lookup: Relocating generated physics asset: {generated_phys_path} -> {expected_phys_path}")
                unreal.EditorAssetLibrary.rename_asset(generated_phys_path, expected_phys_path)

    return target_asset_path, target_phys_path

def import_icon(icon_file, destination_path):
    if icon_file and os.path.exists(icon_file):
        print(f"[PalBaker] Importing UI Icon: {os.path.basename(icon_file)} -> {destination_path}")
        task = unreal.AssetImportTask()
        task.set_editor_property('filename', icon_file)
        task.set_editor_property('destination_path', destination_path)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', True)
        task.set_editor_property('factory', unreal.TextureFactory())
        
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        print(f"[PalBaker] Successfully imported UI Icon to: {destination_path}")
```

**`unreal_scripts/rigging.py`**
```python
# unreal_scripts/rigging.py
import unreal
import os

def apply_rigging(working_dir, ue_path, target_character_id, target_asset_path, bone_data_file="bone_data.json"):
    json_path = os.path.join(working_dir, bone_data_file)
    if not os.path.exists(json_path):
        return

    print(f"Checking for Animation Blueprint to apply advanced rigging to: {target_asset_path}")
    anim_bp = None
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    
    mesh_name = target_asset_path.split("/")[-1]
    base_mesh_name = mesh_name.replace("SK_", "")
    bp_name = f"{base_mesh_name}_BP"
    
    if "Palbaker" in target_asset_path:
        target_bp_dir = "/".join(target_asset_path.split("/")[:-1])
    else:
        target_bp_dir = f"/Game/Pal/Model/Character/Skeleton/{target_character_id}"
        
    target_bp_path = f"{target_bp_dir}/{bp_name}"
    skeleton_path = f"/Game/Pal/Model/Character/Skeleton/{target_character_id}/SK_{target_character_id}_Skeleton"

    if unreal.EditorAssetLibrary.does_asset_exist(target_bp_path):
        print(f"Cleaning old Animation Blueprint for fresh rebuild: {target_bp_path}")
        unreal.EditorAssetLibrary.delete_asset(target_bp_path)
        
    print(f"Generating new custom Animation Blueprint: {target_bp_path}")
    skel = unreal.EditorAssetLibrary.load_asset(skeleton_path)
    if skel:
        factory = unreal.AnimBlueprintFactory()
        factory.set_editor_property('target_skeleton', skel)
        unreal.EditorAssetLibrary.make_directory(target_bp_dir)
        anim_bp = asset_tools.create_asset(bp_name, target_bp_dir, unreal.AnimBlueprint.static_class(), factory)
        if anim_bp:
            print(f"Successfully generated new Animation Blueprint: {bp_name}")
    else:
        print(f"ERROR: Cannot create Animation Blueprint because skeleton {skeleton_path} is missing.")
            
    if anim_bp:
        print(f"Applying PalBaker rigging setup to: {anim_bp.get_name()}")
        try:
            success = unreal.AnimScriptingLibrary.apply_pal_baker_rigging(anim_bp, json_path)
            if success:
                print("Rigging applied and compiled successfully.")
                
                loaded_mesh = unreal.EditorAssetLibrary.load_asset(target_asset_path)
                
                bp_name = anim_bp.get_name()
                bp_path_name = anim_bp.get_path_name().split(".")[0]
                class_path = f"{bp_path_name}.{bp_name}_C"
                
                gen_class = unreal.load_class(None, class_path)
                if gen_class and loaded_mesh:
                    loaded_mesh.set_editor_property('post_process_anim_blueprint', gen_class)
                    unreal.EditorAssetLibrary.save_loaded_asset(loaded_mesh)
                    print(f"Successfully bound {gen_class.get_name()} to Mesh: {loaded_mesh.get_name()}!")
                else:
                    print("Failed to load generated blueprint class or skeletal mesh target.")
        except Exception as e:
            print(f"Failed to execute rigging setup: {e}")
```