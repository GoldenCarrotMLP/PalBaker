import argparse
import json
import sys
import os
from utils.config import load_settings, save_settings
from utils.scanner import get_mod_info
from utils.plugins.installer import is_unreal_running
import asyncio
from utils.audio_controller import AudioController
from utils.altermatic import AltermaticController

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

def json_print(data):
    """Outputs data as a JSON string and forces stdout flush to prevent buffering issues."""
    print(json.dumps(data), flush=True)

def error_print(message):
    json_print({"status": "error", "message": message})

def system_open_path(path: str, is_file: bool = False):
    if not path:
        return False, "Empty path"
    
    # Check if we are inside WSL and the path points to a Windows mount
    is_wsl = False
    if sys.platform == "linux" and (os.path.exists("/proc/sys/fs/binfmt_misc/WSLPersonalities") or "WSL_DISTRO_NAME" in os.environ):
        is_wsl = True

    if is_wsl:
        import subprocess
        try:
            # Under WSL, we can call explorer.exe directly with a path
            # Running `wslpath -w <path>` converts it perfectly to a Windows path
            windows_path = subprocess.check_output(["wslpath", "-w", path], text=True).strip()
            if is_file:
                subprocess.Popen(["explorer.exe", "/select,", windows_path])
            else:
                subprocess.Popen(["explorer.exe", windows_path])
            return True, f"Opened in Windows Explorer: {windows_path}"
        except Exception as e:
            try:
                subprocess.Popen(["xdg-open", path if not is_file else os.path.dirname(path)])
                return True, "Opened via xdg-open fallback"
            except Exception as ex:
                return False, f"WSL open failed: {ex}"
    else:
        # Standard native host execution
        import subprocess
        if not os.path.exists(path):
            return False, f"Path does not exist: {path}"
        try:
            if is_file:
                if os.name == 'nt':
                    subprocess.run(['explorer.exe', f'/select,{os.path.normpath(path)}'])
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', '-R', path])
                else:
                    parent_dir = os.path.dirname(path)
                    subprocess.Popen(['xdg-open', parent_dir])
            else:
                if os.name == 'nt':
                    os.startfile(path)
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', path])
                else:
                    subprocess.Popen(['xdg-open', path])
            return True, "Path opened successfully"
        except Exception as e:
            return False, f"Error opening path: {e}"

def main():
    parser = argparse.ArgumentParser(description="PalBaker Headless CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # config
    config_parser = subparsers.add_parser("config", help="Manage settings")
    config_subparsers = config_parser.add_subparsers(dest="subcommand", required=True)
    
    config_get = config_subparsers.add_parser("get", help="Get all settings")
    
    config_set = config_subparsers.add_parser("set", help="Set a specific setting")
    config_set.add_argument("key", help="Setting key to update")
    config_set.add_argument("value", help="Setting value to save")


    # mod
    mod_parser = subparsers.add_parser("mod", help="Pipeline execution")
    mod_parser.add_argument("action", choices=["extract", "create-blend", "push", "cook", "pack", "full", "decompile", "set-icon", "browse-ue", "open-source", "open-ue", "open-pak", "ping"])
    mod_parser.add_argument("mod", help="Internal name of the Pal")
    mod_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing .blend files during decompile")
    mod_parser.add_argument("--path", help="Path to icon file (used with set-icon)")


    # audio
    audio_parser = subparsers.add_parser("audio", help="Manage custom audio overrides")
    audio_subparsers = audio_parser.add_subparsers(dest="subcommand", required=True)
    
    audio_set = audio_subparsers.add_parser("set", help="Set a custom audio file for a Pal cry")
    audio_set.add_argument("mod", help="Internal name of the Pal")
    audio_set.add_argument("cry", help="Name of the cry (e.g. Normal, Joy)")
    audio_set.add_argument("path", help="Path to the audio file (.wav, .mp3, .ogg)")
    
    audio_clear = audio_subparsers.add_parser("clear", help="Clear a custom audio file")
    audio_clear.add_argument("mod", help="Internal name of the Pal")
    audio_clear.add_argument("cry", help="Name of the cry")

    audio_play = audio_subparsers.add_parser("play", help="Play a custom audio file")
    audio_play.add_argument("mod", help="Internal name of the Pal")
    audio_play.add_argument("cry", help="Name of the cry")


    # altermatic
    altermatic_parser = subparsers.add_parser("altermatic", help="Manage Altermatic variants")
    altermatic_subparsers = altermatic_parser.add_subparsers(dest="subcommand", required=True)
    
    altermatic_toggle = altermatic_subparsers.add_parser("toggle", help="Toggle Altermatic framework on/off")
    altermatic_toggle.add_argument("mod", help="Internal name of the Pal")
    altermatic_toggle.add_argument("status", choices=["on", "off"], help="Toggle status")
    
    altermatic_list = altermatic_subparsers.add_parser("list", help="List all variants")
    altermatic_list.add_argument("mod", help="Internal name of the Pal")

    altermatic_add = altermatic_subparsers.add_parser("add", help="Add Altermatic variant")
    altermatic_add.add_argument("mod", help="Internal name of the Pal")
    altermatic_add.add_argument("label", help="Variant label name")
    altermatic_add.add_argument("--custom", action="store_true", help="Create custom mesh blend")
    altermatic_add.add_argument("--source", default="base", help="Skeleton source choice")

    altermatic_delete = altermatic_subparsers.add_parser("delete", help="Delete Altermatic variant")
    altermatic_delete.add_argument("mod", help="Internal name of the Pal")
    altermatic_delete.add_argument("index", type=int, help="Variant index to delete")

    altermatic_save = altermatic_subparsers.add_parser("save", help="Save/update Altermatic variant")
    altermatic_save.add_argument("index", type=int, help="Variant index (-1 for new)")
    altermatic_save.add_argument("--data", required=True, help="JSON data payload")

    altermatic_sidecar = altermatic_subparsers.add_parser("sidecar", help="Sync/Fetch Altermatic sidecar")
    altermatic_sidecar.add_argument("mod", help="Internal name of the Pal")
    altermatic_sidecar.add_argument("blend_name", help="Blend file name")

    altermatic_metadata = altermatic_subparsers.add_parser("metadata", help="Fetch blend files and available materials for a mod context")
    altermatic_metadata.add_argument("mod", help="Internal name of the Pal")

    altermatic_open_blend = altermatic_subparsers.add_parser("open-blend", help="Open a .blend file in Blender")
    altermatic_open_blend.add_argument("mod", help="Internal name of the Pal")
    altermatic_open_blend.add_argument("blend_name", help="Blend file name or 'base'")
    altermatic_open_blend.add_argument("--category", default="Monster", help="Pal category name")


    # creator
    creator_parser = subparsers.add_parser("creator", help="Manage custom standalone Pals")
    creator_subparsers = creator_parser.add_subparsers(dest="subcommand", required=True)
    
    creator_list = creator_subparsers.add_parser("list", help="List all custom standalone Pals")
    
    creator_add = creator_subparsers.add_parser("add", help="Create a new standalone Pal")
    creator_add.add_argument("id", help="Target unique ID of the custom Pal")
    creator_add.add_argument("--template", required=True, help="Parent template Pal ID to clone (e.g. WeaselDragon)")
    
    creator_delete = creator_subparsers.add_parser("delete", help="Delete a custom standalone Pal")
    creator_delete.add_argument("id", help="Target unique ID to delete")
    
    creator_update = creator_subparsers.add_parser("update", help="Update parameters of a custom standalone Pal")
    creator_update.add_argument("id", help="Target unique ID to update")
    creator_update.add_argument("--data", required=True, help="JSON payload to save")

    creator_refresh_bp = creator_subparsers.add_parser("refresh-bp", help="Refresh Actor Blueprint")
    creator_refresh_bp.add_argument("id", help="Target unique ID to refresh")



    manager_parser = subparsers.add_parser("manager", help="Global state management")
    manager_subparsers = manager_parser.add_subparsers(dest="subcommand", required=True)
    
    manager_build_db = manager_subparsers.add_parser("build-db", help="Build the Pal database cache")
    manager_list = manager_subparsers.add_parser("list", help="List all parsed mods")
    manager_list.add_argument("--show-unextracted", action="store_true", help="Include unextracted Pals")

    manager_caches = manager_subparsers.add_parser("get-caches", help="Fetch consolidated database/skills caches directly")

    # env
    env_parser = subparsers.add_parser("env", help="Environment and UE4SS tasks")
    env_subparsers = env_parser.add_subparsers(dest="subcommand", required=True)
    env_subparsers.add_parser("verify", help="Verify workspace setup")
    
    env_ue4ss = env_subparsers.add_parser("ue4ss-install", help="Install, uninstall, or repair UE4SS")
    env_ue4ss.add_argument("--action", choices=["install-palworld", "install-latest", "repair", "uninstall"], default="install-palworld")
    
    env_plugin = env_subparsers.add_parser("install-plugin", help="Install or uninstall PalSchema Plugin")
    env_plugin.add_argument("--action", choices=["install", "uninstall"], default="install")

    env_status = env_subparsers.add_parser("status", help="Fetch complete real-time status of UE4SS and PalSchema")
    env_subparsers.add_parser("launch-unreal", help="Launch the configured Unreal Editor for the project")
    env_subparsers.add_parser("enable-remote-exec", help="Configure DefaultEngine.ini to enable remote Python execution")
    env_subparsers.add_parser("autodetect", help="Autodetect Unreal Engine, Palworld, and Blender paths")


    args = parser.parse_args()

    try:
        if args.command == "config":
            settings = load_settings()
            if args.subcommand == "get":
                json_print({"status": "success", "data": settings})
            elif args.subcommand == "set":
                settings[args.key] = args.value
                save_settings(settings)
                json_print({"status": "success", "message": f"Updated {args.key}."})
                

        elif args.command == "audio":
            settings = load_settings()
            mods = get_mod_info(settings, args.mod)
            if not mods:
                json_print({"status": "error", "message": f"Mod {args.mod} not found."})
                sys.exit(1)
            
            mod_data = mods[0]
            
            if args.subcommand == "set":
                from utils.audio_helper import apply_custom_audio_worker
                success, msg = apply_custom_audio_worker(settings, mod_data, args.cry, args.path)
                if success:
                    json_print({"status": "success", "message": f"Audio {args.cry} set for {args.mod}"})
                else:
                    json_print({"status": "error", "message": msg})
                
            elif args.subcommand == "clear":
                from utils.audio_helper import clear_audio_worker
                removed = clear_audio_worker(mod_data, args.cry)
                if removed:
                    json_print({"status": "success", "message": f"Audio {args.cry} cleared for {args.mod}"})
                else:
                    json_print({"status": "error", "message": f"No custom audio found to clear for {args.cry}."})
            elif args.subcommand == "play":
                from utils.audio_controller import AudioController
                class DummyMC:
                    def __init__(self, settings):
                        self.settings = settings
                        self.view = DummyView()
                    def run_async_task_threadsafe(self, func): pass
                    def refresh_mods(self, scan_disk, target_mod): pass
                mc = DummyMC(settings)
                ac = AudioController(mc)
                asyncio.run(ac.play_audio(mod_data, args.cry))
                json_print({"status": "success", "message": f"Played audio {args.cry} for {args.mod}"})



        elif args.command == "mod":
            settings = load_settings()
            
            if args.action == "ping":
                import time
                unreal_running = is_unreal_running()
                
                from utils.plugins.detector import check_remote_execution_settings
                ini_enabled = check_remote_execution_settings(settings["uproject"])
                
                connection_active = False
                plugin_loaded = False
                diagnostic_code = "UNREAL_CLOSED"
                message = "Unreal Editor is not running."
                
                if unreal_running:
                    ue_python_dir = os.path.join(settings["ue_root"], "Engine", "Plugins", "Experimental", "PythonScriptPlugin", "Content", "Python")
                    if os.path.exists(ue_python_dir) and ue_python_dir not in sys.path:
                        sys.path.append(ue_python_dir)
                    
                    try:
                        import remote_execution
                        remote_exec = remote_execution.RemoteExecution()
                        remote_exec.start()
                        
                        time.sleep(0.8)
                        project_name = os.path.splitext(os.path.basename(settings["uproject"]))[0]
                        node = next((n for n in remote_exec.remote_nodes if n.get('project_name', '').lower() == project_name.lower()), None)
                        
                        if node:
                            connection_active = True
                            remote_exec.open_command_connection(node.get('node_id'))
                            response = remote_exec.run_command("import sys; print('ready')")
                            remote_exec.stop()
                            
                            if response and response.get('success', False):
                                plugin_loaded = True
                                diagnostic_code = "FULLY_CONNECTED"
                                message = f"Connected to Unreal Editor project: '{project_name}'."
                            else:
                                diagnostic_code = "MISSING_HELPER_PLUGIN"
                                message = "Unreal Remote Execution responded but commands failed to execute."
                        else:
                            remote_exec.stop()
                            if ini_enabled:
                                diagnostic_code = "NEEDS_RESTART_OR_FIREWALL"
                                message = "Unreal remote execution is enabled in config, but connection timed out. Please restart Unreal or check for network conflicts."
                            else:
                                diagnostic_code = "REMOTE_EXEC_DISABLED"
                                message = "Unreal is running, but Remote Execution is disabled in Project Settings."
                    except Exception as e:
                        if ini_enabled:
                            diagnostic_code = "NEEDS_RESTART_OR_FIREWALL"
                            message = f"Failed to initialize remote execution: {e}"
                        else:
                            diagnostic_code = "REMOTE_EXEC_DISABLED"
                            message = "Unreal is running, but remote execution libraries are unavailable or disabled."
                else:
                    diagnostic_code = "UNREAL_CLOSED"
                    message = "Unreal Editor is not running."
                
                json_print({
                    "unreal_running": unreal_running,
                    "ini_enabled": ini_enabled,
                    "connection_active": connection_active,
                    "plugin_loaded": plugin_loaded,
                    "diagnostic_code": diagnostic_code,
                    "message": message
                })
                sys.exit(0)

            mods = get_mod_info(settings, args.mod)
            if not mods:
                json_print({"status": "error", "message": f"Mod {args.mod} not found."})
                sys.exit(1)
            mod_data = mods[0]

            def log_print(msg, level="standard"):
                json_print({"type": "log", "level": level, "message": msg})

            if args.action == "extract":
                from utils.extractor import extract_pal_assets
                success, msg = extract_pal_assets(settings, mod_data["name"], "Monster")
                json_print({"type": "result", "status": "success" if success else "error", "message": msg})
                if not success:
                    sys.exit(1)
                
            elif args.action == "decompile":
                if not is_unreal_running():
                    json_print({
                        "status": "error",
                        "error_code": "UNREAL_CLOSED",
                        "message": "Unreal Editor is not running. Please open your project first."
                    })
                    sys.exit(1)
                from utils.plugins.decompiler import run_decompile_pipeline
                from utils.builder.log_analyzer import LogAnalyzer
                
                fmodel_dir = mod_data["fmodel_path"]
                category = "Monster"
                ue_virtual_path = f"/Game/Pal/Model/Character/Monster/{mod_data['name']}"
                
                success, msg = run_decompile_pipeline(settings["ue_root"], settings["uproject"], mod_data["name"], fmodel_dir, ue_virtual_path, settings["blender"], overwrite=args.overwrite)
                
                analyzer = LogAnalyzer()
                for line in msg.splitlines():
                    analyzer.analyze_line(line)
                summary = analyzer.generate_summary(success)
                
                json_print({
                    "type": "result", 
                    "status": "success" if success else "error", 
                    "message": msg,
                    "summary": summary
                })
                if not success:
                    sys.exit(1)
            
            elif args.action == "set-icon":
                if not args.path:
                    error_print("Missing --path for set-icon")
                    sys.exit(1)
                import shutil
                dest = os.path.join(mod_data["fmodel_path"], f"T_{mod_data['name']}_icon_normal.png")
                shutil.copy2(args.path, dest)
                json_print({"status": "success", "message": f"Icon set for {args.mod}"})
            elif args.action == "browse-ue":
                f_path = mod_data.get("fmodel_path") or mod_data.get("fmodel_altermatic_path") or mod_data.get("ue_path")
                # Deduce category from f_path
                parts = f_path.replace("\\", "/").split("/")
                category = "Monster"
                if "Character" in parts:
                    idx = parts.index("Character")
                    if idx + 1 < len(parts):
                        category = parts[idx + 1]
                category_sanitized = category.replace(" ", "_")
                ue_virtual_path = f"/Game/Pal/Model/Character/{category_sanitized}/{mod_data['name']}"
                python_cmd = f'import unreal; unreal.EditorUtilityLibrary.sync_browser_to_folders(["{ue_virtual_path}"])'
                from utils.builder.unreal_helper import run_remote_command, focus_unreal_window
                target_project_name = os.path.splitext(os.path.basename(settings["uproject"]))[0]
                run_remote_command(settings["ue_root"], target_project_name, python_cmd) # FIXED: Pass arguments correctly
                focus_unreal_window(target_project_name)
                json_print({"status": "success", "message": f"Focused Unreal content browser to {mod_data['name']}"})
            elif args.action == "open-source":
                path = mod_data.get("fmodel_path") or mod_data.get("fmodel_altermatic_path")
                if path:
                    success, msg = system_open_path(path, is_file=False)
                    if success:
                        json_print({"status": "success", "message": f"Opened source folder for {args.mod}."})
                    else:
                        error_print(msg)
                else:
                    error_print("Source folder does not exist for this mod.")
            elif args.action == "open-ue":
                path = mod_data.get("ue_path")
                if path:
                    success, msg = system_open_path(path, is_file=False)
                    if success:
                        json_print({"status": "success", "message": f"Opened Unreal folder for {args.mod}."})
                    else:
                        error_print(msg)
                else:
                    error_print("Unreal assets folder does not exist for this mod.")
            elif args.action == "open-pak":
                path = mod_data.get("pak_path")
                if path:
                    success, msg = system_open_path(path, is_file=True)
                    if success:
                        json_print({"status": "success", "message": f"Opened PAK folder for {args.mod}."})
                    else:
                        error_print(msg)
                else:
                    error_print("PAK file does not exist for this mod.")
            else:
                # Delegate to build_mod.py
                if args.action in ["push", "full"] and not is_unreal_running():
                    json_print({
                        "status": "error",
                        "error_code": "UNREAL_CLOSED",
                        "message": "Unreal Editor is not running. Please open your project first."
                    })
                    sys.exit(1)
                
                import subprocess
                action_map = {
                    "create-blend": "create_blend",
                    "push": "push",
                    "cook": "cook_only",
                    "pack": "pack_only",
                    "full": "full"
                }
                mapped_action = action_map[args.action]
                
                cmd = [sys.executable, "build_mod.py", mod_data["name"], "Monster", mapped_action]
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=creationflags)
                for line in proc.stdout:
                    log_print(line.strip())
                proc.wait()
                if proc.returncode == 0:
                    json_print({"type": "result", "status": "success"})
                else:
                    json_print({"type": "result", "status": "error", "message": f"Pipeline action '{args.action}' failed with exit code {proc.returncode}"})
                    sys.exit(proc.returncode)


        elif args.command == "altermatic":
            settings = load_settings()
            
            mod_name = getattr(args, "mod", None)
            if args.subcommand == "save" and not mod_name:
                import json as json_lib
                try:
                    payload = json_lib.loads(args.data)
                    mod_name = payload.get("CharacterID")
                except Exception:
                    pass
            
            if not mod_name:
                json_print({"status": "error", "message": "Missing target mod name."})
                sys.exit(1)
                
            mods = get_mod_info(settings, mod_name)
            if not mods:
                json_print({"status": "error", "message": f"Mod {mod_name} not found."})
                sys.exit(1)
            mod_data = mods[0]
            
            class DummyMC:
                def __init__(self, settings, view):
                    self.settings = settings
                    self.view = view
                    self.raw_mods = [mod_data]
                def refresh_mods(self, scan_disk, target_mod=None): pass
                
            view = DummyView()
            mc = DummyMC(settings, view)
            alt_ctrl = AltermaticController(mc)
            
            if args.subcommand == "toggle":
                is_active = (args.status == "on")
                alt_ctrl.toggle_altermatic(mod_data, is_active)
                json_print({"status": "success", "message": f"Altermatic toggle set to {args.status} for {args.mod}"})
                
            elif args.subcommand == "list":
                # Returns the current active variants from the mod data directly
                json_print({"status": "success", "data": mod_data.get("altermatic_variants", [])})

            elif args.subcommand == "add":
                alt_ctrl.cloner._execute_clone_workflow(
                    mod_data, 
                    args.label, 
                    args.custom, 
                    args.source, 
                    os.path.join(mod_data.get("fmodel_path", ""), f"{mod_data['name']}.blend"),
                    mod_data.get("fmodel_altermatic_path", ""),
                    sync=True # FIXED: Synchronous execution on main thread
                )
                json_print({"status": "success", "message": f"Successfully queued Altermatic variant: {args.label}"})

            elif args.subcommand == "delete":
                alt_ctrl.delete_altermatic_variant_by_index(mod_data["name"], args.index, sync=True) # FIXED: Synchronous bypass
                json_print({"status": "success", "message": f"Deleted variant at index {args.index}"})

            elif args.subcommand == "save":
                import json as json_lib
                try:
                    payload = json_lib.loads(args.data)
                except Exception as ex:
                    error_print(f"Malformed update data: {ex}")
                    sys.exit(1)
                alt_ctrl.save_altermatic_variant_callback(args.index, payload, sync=True) # FIXED: Synchronous write
                json_print({"status": "success", "message": "Successfully updated Altermatic variant structure."})

            elif args.subcommand == "sidecar":
                from utils.altermatic_helper import sync_sidecar_metadata
                fmodel_altermatic_dir = mod_data.get("fmodel_altermatic_path")
                if not fmodel_altermatic_dir:
                    category = alt_ctrl.get_category_from_path(mod_data.get("fmodel_path"))
                    fmodel_root = settings.get("fmodel_output", "")
                    fmodel_altermatic_dir = os.path.join(fmodel_root, "Exports", "Pal", "Content", "Palbaker", "Model", "Character", category, mod_data["name"])
                
                blend_file_path = os.path.normpath(os.path.join(fmodel_altermatic_dir, args.blend_name))
                if not os.path.exists(blend_file_path):
                    # Check in normal fmodel dir too
                    fmodel_dir = mod_data.get("fmodel_path")
                    if fmodel_dir:
                        blend_file_path = os.path.normpath(os.path.join(fmodel_dir, args.blend_name))
                
                if os.path.exists(blend_file_path):
                    sidecar_data = sync_sidecar_metadata(settings.get("blender"), blend_file_path)
                    json_print({"status": "success", "data": sidecar_data})
                else:
                    json_print({"status": "error", "message": f"Blend file {args.blend_name} not found on disk."})

            elif args.subcommand == "metadata":
                from utils.altermatic_helper import get_blend_files_for_context, get_available_materials_for_context
                fmodel_altermatic_dir = mod_data.get("fmodel_altermatic_path")
                fmodel_dir = mod_data.get("fmodel_path")
                f_path = fmodel_dir or fmodel_altermatic_dir or mod_data.get("ue_path")
                category = alt_ctrl.get_category_from_path(f_path)
                fmodel_root = settings.get("fmodel_output", "")
                
                base_blend_path = os.path.join(fmodel_dir, f"{mod_data['name']}.blend") if fmodel_dir else ""
                has_base_blend = bool(base_blend_path and os.path.exists(base_blend_path))
                
                blend_files = get_blend_files_for_context(fmodel_altermatic_dir, fmodel_dir)
                available_mats = get_available_materials_for_context(fmodel_root, fmodel_altermatic_dir, mod_data["name"], category)
                
                json_print({
                    "status": "success",
                    "has_base_blend": has_base_blend,
                    "blend_files": blend_files,
                    "available_materials": available_mats,
                    "category": category
                })
            elif args.subcommand == "open-blend":
                category = args.category
                source = args.blend_name
                
                fmodel_root = settings.get("fmodel_output", "")
                if not fmodel_root:
                    json_print({"status": "error", "message": "Workspace Folder not set in Settings."})
                    sys.exit(1)
                
                altermatic_path = os.path.normpath(os.path.join(
                    fmodel_root, "Exports", "Pal", "Content", "Palbaker", "Model", "Character", category,
                    mod_data["name"], source
                ))
                vanilla_path = os.path.normpath(os.path.join(
                    fmodel_root, "Exports", "Pal", "Content", "Pal", "Model", "Character", category,
                    mod_data["name"], f"{mod_data['name']}.blend" if source == "base" else source
                ))
                
                if os.path.exists(altermatic_path):
                    blend_path = altermatic_path
                elif os.path.exists(vanilla_path):
                    blend_path = vanilla_path
                else:
                    blend_path = altermatic_path # fallback to show path in error

                blender_exe = settings.get("blender")
                if not blender_exe or not os.path.exists(blender_exe):
                    json_print({"status": "error", "message": "Blender executable path invalid or not found."})
                    sys.exit(1)
                
                if not os.path.exists(blend_path):
                    json_print({"status": "error", "message": f"Blend file not found: {blend_path}"})
                    sys.exit(1)
                
                import subprocess
                try:
                    subprocess.Popen([blender_exe, blend_path])
                    json_print({"status": "success", "message": f"Launched Blender for {blend_path}"})
                except Exception as ex:
                    json_print({"status": "error", "message": f"Failed to spawn Blender process: {ex}"})


        elif args.command == "creator":
            settings = load_settings()
            
            if args.subcommand == "list":
                from utils.creator.cache_loader import CacheLoader
                import json as json_lib
                cl = CacheLoader()
                cl.load_index_caches()
                # Instead of instantiating the old controller to find templates or pals, let's call the manager directly
                from utils.creator.pal_manager import PalManager
                
                dc = DummyController(settings)
                pm = PalManager(dc)
                pm.load_custom_pals()
                json_print({"status": "success", "data": dc.custom_pals})
                
            elif args.subcommand == "add":
                from utils.creator.pal_manager import PalManager
                
                dc = DummyController(settings)
                pm = PalManager(dc)
                pm.add_custom_pal(args.id, args.template, sync=True) # FIXED: Synchronous write
                json_print({"status": "success", "message": f"Successfully created new Pal template: {args.id}"})
                
            elif args.subcommand == "delete":
                from utils.creator.pal_manager import PalManager
                
                dc = DummyController(settings)
                pm = PalManager(dc)
                pm.delete_custom_pal(args.id, sync=True) # FIXED: Synchronous deletion
                json_print({"status": "success", "message": f"Deleted custom Pal: {args.id}"})
                
            elif args.subcommand == "update":
                import json as json_lib
                try:
                    payload = json_lib.loads(args.data)
                except Exception as ex:
                    error_print(f"Malformed update data: {ex}")
                    sys.exit(1)
                from utils.creator.pal_manager import PalManager
                
                dc = DummyController(settings)
                pm = PalManager(dc)
                pm.save_custom_pal(args.id, payload, sync=True) # FIXED: Synchronous write
                json_print({"status": "success", "message": f"Successfully updated custom Pal parameters for: {args.id}"})
            elif args.subcommand == "refresh-bp":
                from utils.creator.pal_manager import PalManager
                from utils.creator.palschema_exporter import PalSchemaExporter
                
                dc = DummyController(settings)
                pm = PalManager(dc)
                pm.load_custom_pals()
                pal_data = next((p for p in dc.custom_pals if p["CharacterID"] == args.id), None)
                if not pal_data:
                    error_print(f"Custom Pal configuration {args.id} not found.")
                    sys.exit(1)
                
                pe = PalSchemaExporter(dc)
                success = pe.generate_custom_actor_blueprint(pal_data)
                if success:
                    json_print({"status": "success", "message": f"Refreshed Actor Blueprint for {args.id}"})
                else:
                    json_print({"status": "error", "message": "Failed to refresh blueprint."})



        
        elif args.command == "env":
            settings = load_settings()
            if args.subcommand == "verify":
                from utils.check_compiler_requirements import verify_compiler_requirements
                from utils.plugin_manager import check_project_requirements
                # Run standard check_project_requirements or verification
                success, msg = verify_compiler_requirements(all_yes=True, print_output=False)
                if success:
                    # Let's check requirements
                    reqs = check_project_requirements(settings.get("ue_root", ""), settings.get("uproject", ""))
                    if reqs.get("error"):
                        json_print({"status": "error", "message": reqs["error"]})
                    else:
                        json_print({"status": "success", "data": reqs, "message": "Verification completed."})
                else:
                    json_print({"status": "error", "message": msg})
            elif args.subcommand == "ue4ss-install":
                from utils.ue4ss_helper import download_and_extract_ue4ss, uninstall_ue4ss, get_ue4ss_status
                exe_path = settings.get("palworld_exe", "")
                if not exe_path:
                    json_print({"status": "error", "message": "Palworld.exe path not set in config."})
                else:
                    status = get_ue4ss_status(exe_path)
                    branch = status.get("branch", "Palworld-Experimental")
                    if branch == "Unknown" or branch == "None":
                        branch = "Palworld-Experimental"
                    
                    action = args.action
                    if action == "install-palworld":
                        download_and_extract_ue4ss(exe_path, "Palworld-Experimental", lambda m, e: None)
                    elif action == "install-latest":
                        download_and_extract_ue4ss(exe_path, "Latest-Experimental", lambda m, e: None)
                    elif action == "repair":
                        download_and_extract_ue4ss(exe_path, branch, lambda m, e: None)
                    elif action == "uninstall":
                        from utils.palschema_helper import uninstall_palschema
                        uninstall_palschema(exe_path, lambda m, e: None)
                        uninstall_ue4ss(exe_path, lambda m, e: None)
                        
                    json_print({"status": "success", "message": "UE4SS management action completed."})
            elif args.subcommand == "install-plugin":
                action = args.action
                if action == "install":
                    from utils.plugin_manager import install_and_compile_plugin
                    success, msg = install_and_compile_plugin(settings.get("ue_root", ""), settings.get("uproject", ""))
                    if success:
                        json_print({"status": "success", "message": msg})
                    else:
                        json_print({"status": "error", "message": msg})
                elif action == "uninstall":
                    from utils.palschema_helper import uninstall_palschema
                    exe_path = settings.get("palworld_exe", "")
                    if not exe_path:
                        json_print({"status": "error", "message": "Palworld.exe path not set in config."})
                    else:
                        uninstall_palschema(exe_path, lambda m, e: None)
                        json_print({"status": "success", "message": "PalSchema uninstalled successfully."})
            elif args.subcommand == "status":
                from utils.ue4ss_helper import get_ue4ss_status
                from utils.palschema_helper import get_palschema_status
                from utils.plugins.detector import check_remote_execution_settings
                exe_path = settings.get("palworld_exe", "")
                uproject_path = settings.get("uproject", "")
                ue4ss_stat = get_ue4ss_status(exe_path)
                palschema_stat = get_palschema_status(exe_path)
                json_print({
                    "status": "success",
                    "ue4ss": ue4ss_stat,
                    "palschema": palschema_stat,
                    "unreal_running": is_unreal_running(),
                    "remote_exec_enabled": check_remote_execution_settings(uproject_path) if uproject_path else False
                })
            elif args.subcommand == "launch-unreal":
                from utils.plugins.installer import launch_unreal_editor
                ue_root = settings.get("ue_root", "")
                uproject_path = settings.get("uproject", "")
                if not ue_root or not uproject_path:
                    json_print({"status": "error", "message": "Unreal root or uproject path not configured."})
                else:
                    success, msg = launch_unreal_editor(ue_root, uproject_path)
                    if success:
                        json_print({"status": "success", "message": "Unreal Editor launch triggered."})
                    else:
                        json_print({"status": "error", "message": msg})
            elif args.subcommand == "enable-remote-exec":
                from utils.plugins.installer import enable_remote_execution_settings
                uproject_path = settings.get("uproject", "")
                if not uproject_path:
                    json_print({"status": "error", "message": "uproject path not configured."})
                else:
                    enable_remote_execution_settings(uproject_path)
                    json_print({"status": "success", "message": "Python Remote Execution settings enabled."})
            elif args.subcommand == "autodetect":
                from utils.autofill_helper import detect_unreal_engine, detect_palworld_exe, find_blender_versions
                json_print({
                    "status": "success",
                    "ue_root": detect_unreal_engine(),
                    "palworld_exe": detect_palworld_exe(),
                    "blender_versions": find_blender_versions()
                })

        elif args.command == "manager":
            if args.subcommand == "list":
                settings = load_settings()
                # Run scanner
                all_mods = get_mod_info(settings)
                
                if not args.show_unextracted:
                    all_mods = [m for m in all_mods if m.get("has_fmodel", False)]
                
                json_print({
                    "status": "success",
                    "data": all_mods
                })
            elif args.subcommand == "build-db":
                from utils.extractor import build_pal_names_map
                success, msg = build_pal_names_map(settings)
                if success:
                    json_print({"status": "success", "message": "Database built successfully."})
                else:
                    json_print({"status": "error", "message": msg})
            elif args.subcommand == "get-caches":
                repo_root = os.path.dirname(os.path.abspath(__file__))
                def load_json(name):
                    p = os.path.join(repo_root, "deps", name)
                    if os.path.exists(p):
                        try:
                            with open(p, "r", encoding="utf-8") as f:
                                return json.load(f)
                        except Exception: pass
                    return {}
                from utils.names import load_names_map
                from utils.altermatic_helper import load_traits_database
                json_print({
                    "status": "success",
                    "data": {
                        "active_skills": load_json("active_skills_cache.json"),
                        "passive_skills": load_json("passive_skills_cache.json"),
                        "coop_passives": load_json("coop_passives_cache.json"),
                        "partner_skills": load_json("partner_skills_cache.json"),
                        "templates": load_json("monster_parameter_cache.json"),
                        "learnsets": load_json("waza_master_level_cache.json"),
                        "monster_spawners": load_json("monster_spawners_cache.json"),
                        "monster_spawners_default_map": load_json("monster_spawners_default_map.json"),
                        "camera_offsets": load_json("camera_offsets_cache.json"),
                        "pal_names": load_names_map(),
                        "traits_db": load_traits_database()
                    }
                })

    except Exception as e:
        error_print(str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()