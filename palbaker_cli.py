import argparse
import json
import sys
import os
from utils.config import load_settings, save_settings
from utils.scanner import get_mod_info
from utils.plugins.installer import is_unreal_running
import asyncio
from controllers.audio_controller import AudioController
from controllers.altermatic import AltermaticController

def json_print(data):
    """Outputs data as a JSON string and forces stdout flush to prevent buffering issues."""
    print(json.dumps(data), flush=True)

def error_print(message):
    json_print({"status": "error", "message": message})

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



    # mod
    mod_parser = subparsers.add_parser("mod", help="Pipeline execution")
    mod_parser.add_argument("action", choices=["extract", "create-blend", "push", "cook", "pack", "full", "decompile", "set-icon"])
    mod_parser.add_argument("mod", help="Internal name of the Pal")
    mod_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing .blend files during decompile")
    mod_parser.add_argument("--path", help="Path to icon file (used with set-icon)")


    # altermatic
    altermatic_parser = subparsers.add_parser("altermatic", help="Manage Altermatic variants")
    altermatic_subparsers = altermatic_parser.add_subparsers(dest="subcommand", required=True)
    
    altermatic_toggle = altermatic_subparsers.add_parser("toggle", help="Toggle Altermatic framework on/off")
    altermatic_toggle.add_argument("mod", help="Internal name of the Pal")
    altermatic_toggle.add_argument("status", choices=["on", "off"], help="Toggle status")
    
    altermatic_list = altermatic_subparsers.add_parser("list", help="List all variants")
    altermatic_list.add_argument("mod", help="Internal name of the Pal")


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



    # manager
    manager_parser = subparsers.add_parser("manager", help="Global state management")
    manager_subparsers = manager_parser.add_subparsers(dest="subcommand", required=True)
    
    manager_build_db = manager_subparsers.add_parser("build-db", help="Build the Pal database cache")
    manager_list = manager_subparsers.add_parser("list", help="List all parsed mods")
    manager_list.add_argument("--show-unextracted", action="store_true", help="Include unextracted Pals")

    # env
    env_parser = subparsers.add_parser("env", help="Environment and UE4SS tasks")
    env_subparsers = env_parser.add_subparsers(dest="subcommand", required=True)
    env_subparsers.add_parser("verify", help="Verify workspace setup")
    env_subparsers.add_parser("ue4ss-install", help="Install UE4SS")
    env_subparsers.add_parser("install-plugin", help="Install PalSchema Plugin")


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
            
            class DummyView:
                def write_log(self, text, category="standard", flush=True):
                    if category == "error": raise Exception(text)
                    # print(f"[{category}] {text}")
                def run_in_thread(self, func): func()
            
            class DummyMC:
                def __init__(self, settings, view):
                    self.settings = settings
                    self.view = view
                async def run_async_task_threadsafe(self, func):
                    # We just run it synchronously since we're in a CLI script, not a GUI loop
                    import asyncio
                    return await asyncio.to_thread(func)
                def refresh_mods(self, scan_disk, target_mod): pass

            view = DummyView()
            mc = DummyMC(settings, view)
            audio_ctrl = AudioController(mc)
            
            if args.subcommand == "set":
                # Need to run an async method
                async def run_set():
                    # Actually apply_custom_audio uses run_async_task_threadsafe to run the worker
                    # We can just run it directly. But wait, apply_custom_audio is async.
                    # Wait, let's look at apply_custom_audio.
                    pass
                    
                # To keep it simple, we just replicate the worker here or call apply_custom_audio?
                # Actually, apply_custom_audio does everything.
                asyncio.run(audio_ctrl.apply_custom_audio(mod_data, args.cry, args.path))
                
                json_print({"status": "success", "message": f"Audio {args.cry} set for {args.mod}"})
                
            elif args.subcommand == "clear":
                asyncio.run(audio_ctrl.clear_audio(mod_data, args.cry))
                json_print({"status": "success", "message": f"Audio {args.cry} cleared for {args.mod}"})
            elif args.subcommand == "play":
                asyncio.run(audio_ctrl.play_audio(mod_data, args.cry))
                json_print({"status": "success", "message": f"Audio playing for {args.cry}"})



        elif args.command == "mod":
            settings = load_settings()
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
            
            elif args.action == "set-icon":
                if not args.path:
                    error_print("Missing --path for set-icon")
                    sys.exit(1)
                import shutil
                icon_dir = os.path.join(mod_data["mod_dir"], "Resources")
                os.makedirs(icon_dir, exist_ok=True)
                dest = os.path.join(icon_dir, "icon.png")
                shutil.copy2(args.path, dest)
                json_print({"status": "success", "message": f"Icon set for {args.mod}"})
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
                json_print({"type": "result", "status": "success" if proc.returncode == 0 else "error"})


        elif args.command == "altermatic":
            settings = load_settings()
            mods = get_mod_info(settings, args.mod)
            if not mods:
                json_print({"status": "error", "message": f"Mod {args.mod} not found."})
                sys.exit(1)
            mod_data = mods[0]
            
            class DummyView:
                def write_log(self, text, category="standard", flush=True): pass
                def show_snackbar(self, message, color): pass
                def force_update(self): pass
            
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


        elif args.command == "creator":
            settings = load_settings()
            from controllers.creator import CreatorController
            class DummyView:
                def write_log(self, text, category="standard", flush=True): pass
                def show_snackbar(self, message, color): pass
                def force_update(self): pass
                def refresh_creator_mods_ui(self): pass
            view = DummyView()
            creator_ctrl = CreatorController(view, settings)
            
            if args.subcommand == "list":
                creator_ctrl.load_custom_pals()
                json_print({"status": "success", "data": creator_ctrl.custom_pals})
                
            elif args.subcommand == "add":
                creator_ctrl.add_custom_pal(args.id, args.template)
                import time
                for _ in range(50):
                    creator_ctrl.load_custom_pals()
                    if any(p.get("CharacterID") == args.id for p in creator_ctrl.custom_pals):
                        break
                    time.sleep(0.1)
                json_print({"status": "success", "message": f"Successfully created new Pal template: {args.id}"})
                
            elif args.subcommand == "delete":
                creator_ctrl.delete_custom_pal(args.id)
                import time
                for _ in range(50):
                    creator_ctrl.load_custom_pals()
                    if not any(p.get("CharacterID") == args.id for p in creator_ctrl.custom_pals):
                        break
                    time.sleep(0.1)
                json_print({"status": "success", "message": f"Deleted custom Pal: {args.id}"})
                
            elif args.subcommand == "update":
                import json
                try:
                    payload = json.loads(args.data)
                except Exception as ex:
                    error_print(f"Malformed update data: {ex}")
                    sys.exit(1)
                creator_ctrl.save_custom_pal(args.id, payload)
                import time
                time.sleep(0.2) # give it a brief moment to write out the thread
                json_print({"status": "success", "message": f"Successfully updated custom Pal parameters for: {args.id}"})
            elif args.subcommand == "refresh-bp":
                creator_ctrl.refresh_actor_blueprint(args.id)
                json_print({"status": "success", "message": f"Refreshed Actor Blueprint for {args.id}"})



        
        elif args.command == "env":
            settings = load_settings()
            from controllers.settings_controller import SettingsController
            class DummyView:
                def write_log(self, text, category="standard", flush=True): log_print(text)
                def show_snackbar(self, msg, color): pass
                def force_update(self): pass
            
            def log_print(msg, level="standard"):
                json_print({"type": "log", "level": level, "message": msg})
                
            ctrl = SettingsController(DummyView(), settings)
            if args.subcommand == "verify":
                ctrl.verify_and_build(auto_close=True)
                json_print({"status": "success", "message": "Verification completed."})
            elif args.subcommand == "ue4ss-install":
                ctrl.manage_ue4ss()
                json_print({"status": "success", "message": "UE4SS install triggered."})
            elif args.subcommand == "install-plugin":
                ctrl.manage_palschema()
                json_print({"status": "success", "message": "PalSchema install triggered."})

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
                from utils.asset_manager import AssetManager
                settings = load_settings()
                class DummyLog:
                    def write_log(self, msg, category="standard", flush=False): pass
                AssetManager.build_pal_database(settings["fmodel_path"], DummyLog())
                json_print({"status": "success", "message": "Database built successfully."})

    except Exception as e:
        error_print(str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()