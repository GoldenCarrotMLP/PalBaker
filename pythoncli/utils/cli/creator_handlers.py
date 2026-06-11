# utils/cli/creator_handlers.py
import os
import sys
import json
from utils.config import validate_settings
from utils.cli.shared import json_print, error_print
from utils.creator import CreatorController

class CliCreatorView:
    def write_log(self, text: str, category: str = "standard"):
        json_print({"type": "log", "level": category, "message": text})

    def show_snackbar(self, message: str, color: str = ""):
        json_print({"type": "log", "level": "error", "message": message})

    def refresh_creator_mods_ui(self):
        pass

    def run_in_thread(self, func):
        func()

def resolve_pal_id(args) -> str:
    possible_keys = ["pal_id", "character_id", "customPalId", "custom_pal_id", "palId", "pal", "mod", "name", "id"]
    for key in possible_keys:
        if hasattr(args, key):
            val = getattr(args, key)
            if val:
                return str(val).strip()
                
    known_keywords = {"add", "delete", "update", "list", "refresh-bp", "get-caches", "build-db", "creator"}
    for k, v in vars(args).items():
        if isinstance(v, str) and v not in known_keywords and k not in ["command", "subcommand", "action", "key", "value"]:
            return v.strip()
    return ""

def resolve_template_id(args) -> str:
    possible_keys = ["template", "parent", "parent_id", "template_id"]
    for key in possible_keys:
        if hasattr(args, key):
            val = getattr(args, key)
            if val:
                return str(val).strip()
    return "WeaselDragon" 

def resolve_data_payload(args) -> str:
    possible_keys = ["data", "payload", "json", "json_data"]
    for key in possible_keys:
        if hasattr(args, key):
            val = getattr(args, key)
            if val:
                return str(val).strip()
    return ""

def handle_creator_command(args, settings):
    subcommand = args.subcommand

    if subcommand in ["add", "refresh-bp"]:
        is_valid, err_msg = validate_settings(settings, ["fmodel_output", "ue_root", "uproject"])
    else:
        is_valid, err_msg = validate_settings(settings, ["fmodel_output"])

    if not is_valid:
        error_print(err_msg)
        sys.exit(1)

    cli_view = CliCreatorView()
    controller = CreatorController(cli_view, settings)

    pal_id = resolve_pal_id(args)
    template_id = resolve_template_id(args)
    data_str = resolve_data_payload(args)

    if subcommand == "list":
        try:
            controller.load_custom_pals()
            json_print({"status": "success", "data": controller.custom_pals})
        except Exception as e:
            error_print(f"Failed to load custom Pals: {str(e)}")
            sys.exit(1)

    elif subcommand == "add":
        if not pal_id or not template_id:
            error_print("Missing required parameters. Usage: creator add <pal_id> --template <parent_id>")
            sys.exit(1)
        try:
            controller.manager.add_custom_pal(pal_id, template_id, sync=True)
            # Echo back the fully populated defaults
            controller.load_custom_pals()
            new_pal = next((p for p in controller.custom_pals if p["CharacterID"] == pal_id), None)
            
            if not new_pal:
                # Forces a fatal exit so Tauri throws the Promise rejection!
                error_print(f"Validation failed: Standalone Pal '{pal_id}' could not be created. Ensure the name is not reserved or already exists.")
                sys.exit(1)

            json_print({
                "status": "success", 
                "message": f"Successfully instantiated custom standalone Pal: {pal_id}",
                "data": new_pal
            })
        except Exception as e:
            error_print(f"Failed to create standalone Pal: {str(e)}")
            sys.exit(1)

    elif subcommand == "delete":
        if not pal_id:
            error_print("Missing required parameter: <pal_id>")
            sys.exit(1)
        try:
            controller.manager.delete_custom_pal(pal_id, sync=True)
            json_print({"status": "success", "message": f"Deleted custom Pal config and Palschema exports for: {pal_id}"})
        except Exception as e:
            error_print(f"Failed to delete standalone Pal: {str(e)}")
            sys.exit(1)

    elif subcommand == "update":
        if not pal_id or not data_str:
            error_print("Missing required parameters. Usage: creator update <pal_id> --data '<json_string>'")
            sys.exit(1)
        try:
            updated_data = json.loads(data_str)
            controller.manager.save_custom_pal(pal_id, updated_data, sync=True)
            # Echo back the updated data
            json_print({
                "status": "success", 
                "message": f"Successfully updated custom Pal parameters for: {pal_id}",
                "data": updated_data
            })
        except json.JSONDecodeError:
            error_print("Invalid JSON payload passed to --data.")
            sys.exit(1)
        except Exception as e:
            error_print(f"Failed to update standalone Pal: {str(e)}")
            sys.exit(1)

    elif subcommand == "refresh-bp":
        if not pal_id:
            error_print("Missing required parameter: <pal_id>")
            sys.exit(1)
        try:
            controller.load_custom_pals()
            pal_data = next((p for p in controller.custom_pals if p["CharacterID"] == pal_id), None)
            if not pal_data:
                error_print(f"Custom Pal {pal_id} configuration not found on disk.")
                sys.exit(1)

            success = controller.exporter.generate_custom_actor_blueprint(pal_data)
            if success:
                json_print({"status": "success", "message": f"Successfully refreshed standalone Actor Blueprint for {pal_id}!"})
            else:
                error_print(f"Failed to compile custom Actor Blueprint for {pal_id}.")
                sys.exit(1)
        except Exception as e:
            error_print(f"Blueprint patching routine crashed: {str(e)}")
            sys.exit(1)

    else:
        error_print(f"Unknown creator subcommand: {subcommand}")
        sys.exit(1)