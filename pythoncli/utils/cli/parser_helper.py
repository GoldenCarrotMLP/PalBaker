# utils/cli/parser_helper.py
import argparse

def create_cli_parser() -> argparse.ArgumentParser:
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


    # manager
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

    return parser
