import re

with open("palbaker_cli.py", "r") as f:
    content = f.read()

# Add env parser
if "env_parser =" not in content:
    parsers_insert = """
    # env
    env_parser = subparsers.add_parser("env", help="Environment and UE4SS tasks")
    env_subparsers = env_parser.add_subparsers(dest="subcommand", required=True)
    env_subparsers.add_parser("verify", help="Verify workspace setup")
    env_subparsers.add_parser("ue4ss-install", help="Install UE4SS")
    env_subparsers.add_parser("install-plugin", help="Install PalSchema Plugin")
"""
    content = content.replace('manager_list.add_argument("--show-unextracted", action="store_true", help="Include unextracted Pals")', 
                              'manager_list.add_argument("--show-unextracted", action="store_true", help="Include unextracted Pals")\n' + parsers_insert)

# Add audio play
if 'audio_play =' not in content:
    audio_play_insert = """
    audio_play = audio_subparsers.add_parser("play", help="Play a custom audio file")
    audio_play.add_argument("mod", help="Internal name of the Pal")
    audio_play.add_argument("cry", help="Name of the cry")
"""
    content = content.replace('audio_clear.add_argument("cry", help="Name of the cry")',
                              'audio_clear.add_argument("cry", help="Name of the cry")\n' + audio_play_insert)

# Add creator refresh-bp
if 'creator_refresh_bp =' not in content:
    creator_refresh_bp_insert = """
    creator_refresh_bp = creator_subparsers.add_parser("refresh-bp", help="Refresh Actor Blueprint")
    creator_refresh_bp.add_argument("id", help="Target unique ID to refresh")
"""
    content = content.replace('creator_update.add_argument("--data", required=True, help="JSON payload to save")',
                              'creator_update.add_argument("--data", required=True, help="JSON payload to save")\n' + creator_refresh_bp_insert)

# Modify mod parser choices
if 'set-icon' not in content:
    content = content.replace('choices=["extract", "create-blend", "push", "cook", "pack", "full", "decompile"]',
                              'choices=["extract", "create-blend", "push", "cook", "pack", "full", "decompile", "set-icon"]')
    content = content.replace('mod_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing .blend files during decompile")',
                              'mod_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing .blend files during decompile")\n    mod_parser.add_argument("--path", help="Path to icon file (used with set-icon)")')

# Implement handlers
handler_insert = """
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
"""
if 'elif args.command == "env":' not in content:
    content = content.replace('elif args.command == "manager":', handler_insert + '\n        elif args.command == "manager":')

manager_build_db_insert = """
            elif args.subcommand == "build-db":
                from utils.asset_manager import AssetManager
                settings = load_settings()
                class DummyLog:
                    def write_log(self, msg, category="standard", flush=False): pass
                AssetManager.build_pal_database(settings["fmodel_path"], DummyLog())
                json_print({"status": "success", "message": "Database built successfully."})
"""
if 'elif args.subcommand == "build-db":' not in content:
    content = re.sub(r'(manager_list = manager_subparsers\.add_parser\("list", help="List all parsed mods"\))',
                     r'manager_build_db = manager_subparsers.add_parser("build-db", help="Build the Pal database cache")\n    \1', content)

    content = re.sub(r'(\s*json_print\(\{\s*"status": "success",\s*"data": all_mods\s*\}\))',
                     r'\1' + manager_build_db_insert, content)

audio_play_insert2 = """
            elif args.subcommand == "play":
                asyncio.run(audio_ctrl.play_audio(mod_data, args.cry))
                json_print({"status": "success", "message": f"Audio playing for {args.cry}"})
"""
if 'elif args.subcommand == "play":' not in content:
    content = re.sub(r'(json_print\(\{"status": "success", "message": f"Audio \{args.cry\} cleared for \{args.mod\}"\}\))',
                     r'\1' + audio_play_insert2, content)


mod_set_icon_insert = """
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
"""
if 'elif args.action == "set-icon":' not in content:
    content = re.sub(r'(else:\n\s*# Delegate to build_mod.py)',
                     mod_set_icon_insert.lstrip('\n') + r'            \1', content)

creator_refresh_bp_insert2 = """
            elif args.subcommand == "refresh-bp":
                creator_ctrl.refresh_actor_blueprint(args.id)
                json_print({"status": "success", "message": f"Refreshed Actor Blueprint for {args.id}"})
"""
if 'elif args.subcommand == "refresh-bp":' not in content:
    content = re.sub(r'(json_print\(\{"status": "success", "message": f"Successfully updated custom Pal parameters for: \{args.id\}"\}\))',
                     r'\1' + creator_refresh_bp_insert2, content)

with open("palbaker_cli.py", "w") as f:
    f.write(content)
