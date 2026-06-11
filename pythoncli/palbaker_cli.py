# palbaker_cli.py
import sys

# Standard library dummy imports to force PyInstaller to bundle dependencies
# required by Unreal Engine's out-of-process remote_execution.py script
import uuid
import socket
import select
import struct
import logging

from utils.config import load_settings, save_settings
from utils.cli.parser_helper import create_cli_parser
from utils.cli.shared import json_print, error_print

def main():
    import sys
    # Intercept frozen subprocess calls to 'build_mod.py'
    if getattr(sys, 'frozen', False) and len(sys.argv) >= 2 and sys.argv[1] == "internal-build-mod":
        import build_mod
        # Shift sys.argv so build_mod's main() parses its arguments starting at index 1
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        build_mod.main()
        sys.exit(0)

    parser = create_cli_parser()
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
            from utils.cli.mod_handlers import handle_audio_command
            settings = load_settings()
            handle_audio_command(args, settings)

        elif args.command == "mod":
            settings = load_settings()
            if args.action == "ping":
                from utils.cli.ping_helper import run_unreal_ping
                result = run_unreal_ping(settings)
                json_print(result)
                sys.exit(0)
            from utils.cli.mod_handlers import handle_mod_command
            handle_mod_command(args, settings)

        elif args.command == "altermatic":
            from utils.cli.altermatic_handlers import handle_altermatic_command
            settings = load_settings()
            handle_altermatic_command(args, settings)

        elif args.command == "creator":
            from utils.cli.creator_handlers import handle_creator_command
            settings = load_settings()
            handle_creator_command(args, settings)
        
        elif args.command == "env":
            from utils.cli.env_handlers import handle_env_command
            settings = load_settings()
            handle_env_command(args, settings)

        elif args.command == "manager":
            from utils.cli.manager_handlers import handle_manager_command
            settings = load_settings()
            handle_manager_command(args, settings)

    except Exception as e:
        error_print(str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()