# utils/cli/env_handlers.py
import os
import sys
import json
import shutil
from utils.config import validate_settings
from utils.cli.shared import json_print, error_print

def handle_env_command(args, settings):
    """Router for all system environment subcommands."""
    subcommand = args.subcommand

    # 1. Route validation based on targeted operations
    if subcommand in ["verify", "install-plugin", "launch-unreal"]:
        is_valid, err_msg = validate_settings(settings, ["ue_root", "uproject"])
    elif subcommand in ["ue4ss-install", "status"]:
        is_valid, err_msg = validate_settings(settings, ["palworld_exe"])
    elif subcommand == "enable-remote-exec":
        is_valid, err_msg = validate_settings(settings, ["uproject"])
    else:
        # autodetect has no prerequisites
        is_valid = True
        err_msg = ""

    if not is_valid:
        error_print(err_msg)
        sys.exit(1)

    # 2. Handle 'env verify'
    if subcommand == "verify":
        from utils.check_compiler_requirements import verify_compiler_requirements
        from utils.plugin_manager import check_project_requirements
        
        try:
            # First verify physical compiler toolsets
            success, msg = verify_compiler_requirements(all_yes=True, print_output=False)
            if success:
                # Next verify ModKit dependencies and injected material assets
                reqs = check_project_requirements(settings.get("ue_root", ""), settings.get("uproject", ""))
                if reqs.get("error"):
                    json_print({"status": "error", "message": reqs["error"]})
                    sys.exit(1)
                else:
                    json_print({"status": "success", "data": reqs, "message": "Verification completed."})
            else:
                json_print({"status": "error", "message": msg})
                sys.exit(1)
        except Exception as e:
            error_print(f"Prerequisite verification crashed: {str(e)}")
            sys.exit(1)

    # 3. Handle 'env install-plugin'
    elif subcommand == "install-plugin":
        from utils.plugin_manager import install_and_compile_plugin, inject_missing_assets
        action = getattr(args, "action", "install")

        project_dir = os.path.dirname(settings["uproject"])
        installed_plugin_dir = os.path.join(project_dir, "Plugins", "PalBakerEditorUtils")

        if action == "uninstall":
            try:
                if os.path.exists(installed_plugin_dir):
                    shutil.rmtree(installed_plugin_dir)
                    json_print({"status": "success", "message": "Successfully uninstalled C++ editor plugin."})
                else:
                    json_print({"status": "success", "message": "C++ plugin is already uninstalled."})
            except Exception as e:
                error_print(f"Failed to uninstall plugin: {str(e)}")
                sys.exit(1)
        else:
            try:
                # Compile and install plugin
                success, msg = install_and_compile_plugin(
                    settings["ue_root"], 
                    settings["uproject"], 
                    verbose=False, 
                    force_recompile=True
                )
                if success:
                    # Ingest required material assets
                    inject_missing_assets(settings["uproject"], verbose=False)
                    json_print({"status": "success", "message": "C++ Plugin compiled and installed successfully."})
                else:
                    json_print({"status": "error", "message": f"Compilation failed: {msg}"})
                    sys.exit(1)
            except Exception as e:
                error_print(f"C++ Plugin setup crashed: {str(e)}")
                sys.exit(1)

    # 4. Handle 'env ue4ss-install'
    elif subcommand == "ue4ss-install":
        from utils.ue4ss_helper import download_and_extract_ue4ss, uninstall_ue4ss
        action = getattr(args, "action", "install-palworld")

        def log_callback(msg, is_error=False):
            # Formats output for real-time streaming to your build console
            json_print({"type": "log", "level": "error" if is_error else "standard", "message": msg})

        try:
            if action == "install-palworld":
                success = download_and_extract_ue4ss(settings["palworld_exe"], "Palworld-Experimental", log_callback)
            elif action == "install-latest":
                success = download_and_extract_ue4ss(settings["palworld_exe"], "Latest-Experimental", log_callback)
            elif action == "repair":
                from utils.ue4ss_helper import get_ue4ss_status
                status = get_ue4ss_status(settings["palworld_exe"])
                branch = status.get("branch", "Palworld-Experimental")
                if branch == "Unknown" or branch == "None":
                    branch = "Palworld-Experimental"
                success = download_and_extract_ue4ss(settings["palworld_exe"], branch, log_callback)
            elif action == "uninstall":
                success = uninstall_ue4ss(settings["palworld_exe"], log_callback)
            else:
                success = False
                log_callback(f"Unknown action: {action}", is_error=True)

            if success:
                json_print({"status": "success", "message": f"Successfully completed action: {action}"})
            else:
                json_print({"status": "error", "message": f"Action failed: {action}"})
                sys.exit(1)
        except Exception as e:
            error_print(f"UE4SS routine crashed: {str(e)}")
            sys.exit(1)

    # 5. Handle 'env status'
    elif subcommand == "status":
        from utils.ue4ss_helper import get_ue4ss_status
        from utils.palschema_helper import get_palschema_status
        from utils.plugins.detector import check_remote_execution_settings
        from utils.plugins.installer import is_unreal_running

        try:
            pal_exe = settings.get("palworld_exe", "")
            uproject = settings.get("uproject", "")

            ue4ss_status = get_ue4ss_status(pal_exe)
            palschema_status = get_palschema_status(pal_exe)
            remote_exec_enabled = check_remote_execution_settings(uproject) if uproject else False
            unreal_running = is_unreal_running()

            json_print({
                "status": "success",
                "ue4ss": ue4ss_status,
                "palschema": palschema_status,
                "remote_exec_enabled": remote_exec_enabled,
                "unreal_running": unreal_running
            })
        except Exception as e:
            error_print(f"Failed to fetch integration status: {str(e)}")
            sys.exit(1)

    # 6. Handle 'env launch-unreal'
    elif subcommand == "launch-unreal":
        from utils.plugins.installer import launch_unreal_editor
        try:
            success, msg = launch_unreal_editor(settings["ue_root"], settings["uproject"])
            if success:
                json_print({"status": "success", "message": msg})
            else:
                json_print({"status": "error", "message": msg})
                sys.exit(1)
        except Exception as e:
            error_print(f"Failed to launch Unreal: {str(e)}")
            sys.exit(1)

    # 7. Handle 'env enable-remote-exec'
    elif subcommand == "enable-remote-exec":
        from utils.plugins.installer import enable_remote_execution_settings
        try:
            success, msg = enable_remote_execution_settings(settings["uproject"])
            if success:
                json_print({"status": "success", "message": msg})
            else:
                json_print({"status": "error", "message": msg})
                sys.exit(1)
        except Exception as e:
            error_print(f"Failed to enable Remote Execution: {str(e)}")
            sys.exit(1)

    # 8. Handle 'env autodetect'
    elif subcommand == "autodetect":
        from utils.autofill_helper import detect_unreal_engine, detect_palworld_exe, find_blender_versions
        try:
            ue_root = detect_unreal_engine()
            pal_exe = detect_palworld_exe()
            blender_vers = find_blender_versions()
            json_print({
                "status": "success",
                "ue_root": ue_root,
                "palworld_exe": pal_exe,
                "blender_versions": blender_vers
            })
        except Exception as e:
            error_print(f"Path autodetection crashed: {str(e)}")
            sys.exit(1)

    else:
        error_print(f"Unknown env subcommand: {subcommand}")
        sys.exit(1)