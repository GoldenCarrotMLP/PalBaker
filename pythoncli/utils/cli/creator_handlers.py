# utils/cli/creator_handlers.py
import os
import sys
import json
from utils.config import validate_settings
from utils.cli.shared import json_print, error_print
from utils.creator import CreatorController

class CliCreatorView:
    """
    Headless CLI view adaptor. Captures controller logs, wraps them 
    in clean JSON lines, and writes them directly to stdout.
    """
    def write_log(self, text: str, category: str = "standard"):
        json_print({"type": "log", "level": category, "message": text})

    def refresh_creator_mods_ui(self):
        pass

    def run_in_thread(self, func):
        # Execute synchronously in CLI thread
        func()


def resolve_pal_id(args) -> str:
    """
    Dynamically extracts the Pal/Character ID from the argparse Namespace 
    to support any local naming variations (pal_id, customPalId, etc.).
    """
    possible_keys = ["pal_id", "character_id", "customPalId", "custom_pal_id", "palId", "pal", "mod", "name", "id"]
    for key in possible_keys:
        if hasattr(args, key):
            val = getattr(args, key)
            if val:
                return str(val).strip()
                
    # Fallback: scan for any positional string argument that isn't a known keyword
    known_keywords = {"add", "delete", "update", "list", "refresh-bp", "get-caches", "build-db", "creator"}
    for k, v in vars(args).items():
        if isinstance(v, str) and v not in known_keywords and k not in ["command", "subcommand", "action", "key", "value"]:
            return v.strip()
            
    return ""


def resolve_template_id(args) -> str:
    """Dynamically resolves the parent template ID under any common naming permutation."""
    possible_keys = ["template", "parent", "parent_id", "template_id"]
    for key in possible_keys:
        if hasattr(args, key):
            val = getattr(args, key)
            if val:
                return str(val).strip()
    return "WeaselDragon" # Fallback baseline template


def resolve_data_payload(args) -> str:
    """Dynamically resolves the JSON data payload key."""
    possible_keys = ["data", "payload", "json", "json_data"]
    for key in possible_keys:
        if hasattr(args, key):
            val = getattr(args, key)
            if val:
                return str(val).strip()
    return ""


def handle_creator_command(args, settings):
    """Router for all standalone custom Pal Creator subcommands."""
    subcommand = args.subcommand

    # 1. Route validation based on targeted operations
    if subcommand in ["add", "refresh-bp"]:
        # Blueprint patching/cloning requires a healthy ModKit compiler
        is_valid, err_msg = validate_settings(settings, ["fmodel_output", "ue_root", "uproject"])
    else:
        # list, delete, update
        is_valid, err_msg = validate_settings(settings, ["fmodel_output"])

    if not is_valid:
        error_print(err_msg)
        sys.exit(1)

    # 2. Instantiate decoupled controller with headless CLI view
    cli_view = CliCreatorView()
    controller = CreatorController(cli_view, settings)

    # 3. Resolve target variables dynamically to prevent Namespace AttributeErrors
    pal_id = resolve_pal_id(args)
    template_id = resolve_template_id(args)
    data_str = resolve_data_payload(args)

    # 4. Handle 'creator list'
    if subcommand == "list":
        try:
            controller.load_custom_pals()
            json_print({"status": "success", "data": controller.custom_pals})
        except Exception as e:
            error_print(f"Failed to load custom Pals: {str(e)}")
            sys.exit(1)

    # 5. Handle 'creator add <pal_id> --template <template_id>'
    elif subcommand == "add":
        if not pal_id or not template_id:
            error_print("Missing required parameters. Usage: creator add <pal_id> --template <parent_id>")
            sys.exit(1)

        try:
            # FIXED: Bypasses the controller wrapper and calls the manager directly with sync=True
            controller.manager.add_custom_pal(pal_id, template_id, sync=True)
            json_print({"status": "success", "message": f"Successfully instantiated custom standalone Pal: {pal_id}"})
        except Exception as e:
            error_print(f"Failed to create standalone Pal: {str(e)}")
            sys.exit(1)

    # 6. Handle 'creator delete <pal_id>'
    elif subcommand == "delete":
        if not pal_id:
            error_print("Missing required parameter: <pal_id>")
            sys.exit(1)

        try:
            # FIXED: Bypasses the controller wrapper and calls the manager directly with sync=True
            controller.manager.delete_custom_pal(pal_id, sync=True)
            json_print({"status": "success", "message": f"Deleted custom Pal config and Palschema exports for: {pal_id}"})
        except Exception as e:
            error_print(f"Failed to delete standalone Pal: {str(e)}")
            sys.exit(1)

    # 7. Handle 'creator update <pal_id> --data <json_string>'
    elif subcommand == "update":
        if not pal_id or not data_str:
            error_print("Missing required parameters. Usage: creator update <pal_id> --data '<json_string>'")
            sys.exit(1)

        try:
            updated_data = json.loads(data_str)
            # FIXED: Bypasses the controller wrapper and calls the manager directly with sync=True
            controller.manager.save_custom_pal(pal_id, updated_data, sync=True)
            json_print({"status": "success", "message": f"Successfully updated custom Pal parameters for: {pal_id}"})
        except json.JSONDecodeError:
            error_print("Invalid JSON payload passed to --data.")
            sys.exit(1)
        except Exception as e:
            error_print(f"Failed to update standalone Pal: {str(e)}")
            sys.exit(1)

    # 8. Handle 'creator refresh-bp <pal_id>'
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

            # Exporter's blueprint generator is synchronous by default
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