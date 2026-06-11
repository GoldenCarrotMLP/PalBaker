# utils/cli/altermatic_handlers.py
import os
import sys
import json
import shutil
import subprocess
from utils.config import validate_settings
from utils.cli.shared import json_print, error_print
from utils.altermatic import AltermaticController
from utils.altermatic_helper import (
    sync_sidecar_metadata, 
    get_blend_files_for_context, 
    get_available_materials_for_context
)

class CliAltermaticView:
    def write_log(self, text: str, category: str = "standard"):
        json_print({"type": "log", "level": category, "message": text})

    def show_snackbar(self, message: str, color: str = ""):
        json_print({"type": "log", "level": "error", "message": message})


class CliMasterController:
    def __init__(self, settings: dict):
        self.settings = settings
        self.view = CliAltermaticView()
        self.raw_mods = []

    def refresh_mods(self, scan_disk: bool = True, target_mod: str | None = None):
        from utils.scanner import get_mod_info
        self.raw_mods = get_mod_info(self.settings, target_mod)


def get_category_from_path(path: str | None) -> str:
    if not path:
        return "Monster"
    parts = path.replace("\\", "/").split("/")
    if "Character" in parts:
        idx = parts.index("Character")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return "Monster"


def resolve_altermatic_args(args) -> tuple[str, str, str, str]:
    mod_name = getattr(args, "mod", "") or getattr(args, "mod_name", "")
    label = getattr(args, "label", "") or getattr(args, "label_name", "")
    status = getattr(args, "status", "")
    index = getattr(args, "index", "") or getattr(args, "index_number", "")
    
    if not mod_name:
        known_keywords = {"toggle", "list", "add", "delete", "save", "sidecar", "metadata", "open-blend", "altermatic"}
        for k, v in vars(args).items():
            if isinstance(v, str) and v not in known_keywords and k not in ["command", "subcommand", "action", "key", "value", "data"]:
                if not mod_name:
                    mod_name = v
                elif not label:
                    label = v
                elif not status:
                    status = v
                    
    return str(mod_name), str(label), str(status), str(index)


def handle_altermatic_command(args, settings):
    subcommand = args.subcommand

    is_valid, err_msg = validate_settings(settings, ["fmodel_output"])
    if not is_valid:
        error_print(err_msg)
        sys.exit(1)

    mod_name, label, status, index = resolve_altermatic_args(args)
    data_str = getattr(args, "data", "")

    mc = CliMasterController(settings)

    if subcommand == "toggle":
        if not mod_name or not status:
            error_print("Usage: altermatic toggle <mod_name> <on|off>")
            sys.exit(1)

        mc.refresh_mods(target_mod=mod_name)
        if not mc.raw_mods:
            error_print(f"Mod {mod_name} was not found on disk.")
            sys.exit(1)

        controller = AltermaticController(mc)
        controller.toggle_altermatic(mc.raw_mods[0], status == "on")
        json_print({"status": "success", "message": f"Successfully toggled Altermatic {status} for {mod_name}."})

    elif subcommand == "list":
        if not mod_name:
            error_print("Usage: altermatic list <mod_name>")
            sys.exit(1)

        mc.refresh_mods(target_mod=mod_name)
        if not mc.raw_mods:
            error_print(f"Mod {mod_name} was not found on disk.")
            sys.exit(1)

        json_print({"status": "success", "data": mc.raw_mods[0].get("altermatic_variants", [])})

    elif subcommand == "add":
        if not mod_name or not label:
            error_print("Usage: altermatic add <mod_name> <label_name> [--custom] [--source <source_choice>]")
            sys.exit(1)

        mc.refresh_mods(target_mod=mod_name)
        if not mc.raw_mods:
            error_print(f"Mod {mod_name} was not found on disk.")
            sys.exit(1)

        custom_mesh = getattr(args, "custom", False)
        source_choice = getattr(args, "source", "base")

        fmodel_dir = mc.raw_mods[0]["fmodel_path"]
        base_blend_path = os.path.join(fmodel_dir, f"{mod_name}.blend")
        category = get_category_from_path(fmodel_dir)

        fmodel_altermatic_dir = mc.raw_mods[0]["fmodel_altermatic_path"]
        if not fmodel_altermatic_dir:
            fmodel_altermatic_dir = os.path.join(settings["fmodel_output"], "Exports", "Pal", "Content", "Palbaker", "Model", "Character", category, mod_name)

        controller = AltermaticController(mc)
        controller.cloner._execute_clone_workflow(
            mc.raw_mods[0], label, custom_mesh, source_choice, base_blend_path, fmodel_altermatic_dir, sync=True
        )
        json_print({"status": "success", "message": f"Added variant '{label}' successfully."})

    elif subcommand == "delete":
        if not mod_name or not index:
            error_print("Usage: altermatic delete <mod_name> <index_number>")
            sys.exit(1)

        mc.refresh_mods(target_mod=mod_name)
        if not mc.raw_mods:
            error_print(f"Mod {mod_name} was not found on disk.")
            sys.exit(1)

        fmodel_altermatic_dir = mc.raw_mods[0]["fmodel_altermatic_path"]
        sidecar_to_clean = ""
        idx_int = int(index)
        variants = mc.raw_mods[0].get("altermatic_variants", [])
        
        if fmodel_altermatic_dir and 0 <= idx_int < len(variants):
            v = variants[idx_int]
            if v.get("SkeletonSource") != "base":
                sidecar_name = v["SkeletonSource"].replace(".blend", "_blend.json")
                sidecar_to_clean = os.path.join(fmodel_altermatic_dir, sidecar_name)

        controller = AltermaticController(mc)
        controller.delete_altermatic_variant(mc.raw_mods[0], idx_int, sync=True)
        
        if sidecar_to_clean and os.path.exists(sidecar_to_clean):
            try: os.remove(sidecar_to_clean)
            except OSError: pass

        json_print({"status": "success", "message": f"Deleted variant at index {index} successfully."})

    elif subcommand == "save":
        if not index or not data_str:
            error_print("Usage: altermatic save <index_number> --data '<json_string>'")
            sys.exit(1)

        try:
            variant_data = json.loads(data_str)
            current_char_id = variant_data["CharacterID"]
            
            mc.refresh_mods(target_mod=current_char_id)
            if not mc.raw_mods:
                error_print(f"Parent mod {current_char_id} not found on disk.")
                sys.exit(1)

            controller = AltermaticController(mc)
            variants = mc.raw_mods[0].get("altermatic_variants", [])
            
            idx_int = int(index)
            if 0 <= idx_int < len(variants):
                controller.original_editing_label = variants[idx_int]["label"]
                
            controller.save_altermatic_variant_callback(idx_int, variant_data, sync=True)
            json_print({"status": "success", "message": "Successfully saved variant parameters."})
        except json.JSONDecodeError:
            error_print("Invalid JSON data string passed to --data.")
            sys.exit(1)
        except Exception as e:
            error_print(f"Failed to save Altermatic variant: {str(e)}")
            sys.exit(1)

    elif subcommand == "sidecar":
        mod_name = getattr(args, "mod", "")
        blend_name = getattr(args, "blend_name", "") # FIXED: Pulling the correct argument!
        
        if not mod_name or not blend_name:
            error_print("Usage: altermatic sidecar <mod_name> <blend_name>")
            sys.exit(1)

        mc.refresh_mods(target_mod=mod_name)
        if not mc.raw_mods:
            error_print(f"Mod {mod_name} was not found on disk.")
            sys.exit(1)

        f_dir = mc.raw_mods[0]["fmodel_altermatic_path"] or mc.raw_mods[0]["fmodel_path"]
        blend_path = os.path.join(f_dir, blend_name)
        
        if not os.path.exists(blend_path):
            error_print(f"Skeletal blend file not found at: {blend_path}")
            sys.exit(1)

        try:
            synced_data = sync_sidecar_metadata(settings["blender"], blend_path)
            json_print({"status": "success", "data": synced_data})
        except Exception as e:
            error_print(f"Failed to sync sidecar metadata: {str(e)}")
            sys.exit(1)

    elif subcommand == "metadata":
        if not mod_name:
            error_print("Usage: altermatic metadata <mod_name>")
            sys.exit(1)

        mc.refresh_mods(target_mod=mod_name)
        if not mc.raw_mods:
            error_print(f"Mod {mod_name} was not found on disk.")
            sys.exit(1)

        mod_data = mc.raw_mods[0]
        category = get_category_from_path(mod_data["fmodel_path"])
        
        blend_files = get_blend_files_for_context(mod_data["fmodel_altermatic_path"], mod_data["fmodel_path"])
        available_mats = get_available_materials_for_context(settings["fmodel_output"], mod_data["fmodel_altermatic_path"], mod_name, category)

        json_print({
            "status": "success",
            "blend_files": blend_files,
            "available_materials": available_mats,
            "category": category
        })

    elif subcommand == "open-blend":
        mod_name = args.mod
        blend_name = getattr(args, "blend_name", "base")
        category = getattr(args, "category", "Monster")

        if not mod_name or not blend_name:
            error_print("Usage: altermatic open-blend <mod_name> <blend_name> [--category <category>]")
            sys.exit(1)

        mc.refresh_mods(target_mod=mod_name)
        if not mc.raw_mods:
            error_print(f"Mod {mod_name} was not found on disk.")
            sys.exit(1)

        f_dir = mc.raw_mods[0]["fmodel_altermatic_path"] or mc.raw_mods[0]["fmodel_path"]
        blend_path = os.path.join(f_dir, blend_name)

        if not os.path.exists(blend_path):
            error_print(f"Target blend file not found at: {blend_path}")
            sys.exit(1)

        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            subprocess.Popen([settings["blender"], blend_path], creationflags=creation_flags, close_fds=True, start_new_session=True if os.name != 'nt' else False)
            json_print({"status": "success", "message": "Blender launched successfully."})
        except Exception as e:
            error_print(f"Failed to launch Blender: {str(e)}")
            sys.exit(1)

    else:
        error_print(f"Unknown altermatic subcommand: {subcommand}")
        sys.exit(1)