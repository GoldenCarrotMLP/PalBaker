# utils/cli/mod_handlers.py
import os
import sys
import json
import shutil
import subprocess
from utils.config import validate_settings
from utils.cli.shared import json_print, error_print, system_open_path
from utils.scanner import get_mod_info
from utils.audio_helper import apply_custom_audio_worker, clear_audio_worker

def get_category_from_path(path: str | None) -> str:
    """Helper to extract Category (e.g. Monster) from active directory."""
    if not path:
        return "Monster"
    parts = path.replace("\\", "/").split("/")
    if "Character" in parts:
        idx = parts.index("Character")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return "Monster"

def play_wav_file(wav_path: str):
    """Cross-platform lightweight WAV audio previewer."""
    if not os.path.exists(wav_path):
        return
    if sys.platform == "win32":
        import winsound
        try:
            winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass
    elif sys.platform == 'darwin':
        subprocess.Popen(["afplay", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        for player in ["paplay", "aplay", "play"]:
            if shutil.which(player):
                subprocess.Popen([player, wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                break

def verify_unreal_connection(settings: dict) -> tuple[bool, str, str]:
    """
    Executes a rapid, lightweight handshake to verify if Unreal Editor 
    is running and accepts Python remote connections.
    Returns: (is_connected, error_code, error_message)
    """
    from utils.plugins.installer import is_unreal_running
    if not is_unreal_running():
        return False, "UNREAL_CLOSED", "Unreal Editor is not running. Please launch the editor first."
        
    from utils.plugins.detector import check_remote_execution_settings
    uproject = settings.get("uproject", "")
    if uproject and not check_remote_execution_settings(uproject):
        return False, "REMOTE_EXEC_DISABLED", "Python Remote Execution is currently disabled in your project's settings."
        
    # Attempt rapid UDP socket handshake
    try:
        from utils.cli.ping_helper import run_unreal_ping
        res = run_unreal_ping(settings)
        if res.get("diagnostic_code") != "FULLY_CONNECTED":
            return False, res.get("diagnostic_code", "TIMEOUT"), f"UDP handshake with Unreal Editor failed: {res.get('message', 'Connection Timeout')}"
    except Exception as e:
        return False, "CRASH", f"Unreal remote connection check failed: {str(e)}"
        
    return True, "FULLY_CONNECTED", ""

def verify_project_integrity(settings: dict) -> tuple[bool, str]:
    """
    Verifies if the C++ plugin and master assets are installed in the Unreal project.
    Returns: (is_intact: bool, error_message: str)
    """
    from utils.plugin_manager import check_project_requirements
    
    reqs = check_project_requirements(settings.get("ue_root", ""), settings.get("uproject", ""))
    
    if reqs.get("error"):
        return False, f"Project Validation Failed: {reqs['error']}"
        
    if reqs.get("needs_compile") or reqs.get("needs_plugin_sync") or reqs.get("plugin_outdated"):
        return False, (
            "The PalBaker C++ Editor Helper Plugin is missing or outdated in your Unreal project!\n\n"
            "This plugin is strictly required to programmatically build animation blueprints and material connections.\n"
            "Please navigate to System Settings and click 'Save & Verify Project Requirements' to install it."
        )
        
    if reqs.get("missing_assets"):
        return False, (
            "Your Unreal project is missing crucial master materials and framework assets!\n\n"
            "PalBaker requires these base assets to safely link materials onto your meshes.\n"
            "Please navigate to System Settings and click 'Save & Verify Project Requirements' to inject them."
        )
        
    return True, ""

def run_build_mod_and_stream(monster_name: str, category: str, action: str):
    """
    Spawns build_mod.py unbuffered, intercepts output lines, and 
    emits version-safe JSONL envelopes for real-time progress.
    """
    is_frozen = getattr(sys, 'frozen', False)
    if is_frozen:
        cmd = [sys.executable, "internal-build-mod", monster_name, category, action]
    else:
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        build_mod_path = os.path.join(repo_root, "build_mod.py")
        cmd = [sys.executable, "-u", build_mod_path, monster_name, category, action]
    
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags,
            bufsize=1
        )
        
        if proc.stdout:
            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                line_clean = line.strip()
                if not line_clean:
                    continue
                
                # If build_mod.py already outputted a pre-formatted JSON string, pass it through
                if line_clean.startswith("{") and line_clean.endswith("}"):
                    try:
                        json.loads(line_clean)
                        print(line_clean, flush=True)
                        continue
                    except json.JSONDecodeError:
                        pass
                
                # Parse standard logs and emit progress triggers
                percent = 0.0
                is_progress = False
                
                if "running headless blender" in line_clean.lower() or "exporting fbx" in line_clean.lower():
                    percent = 0.15
                    is_progress = True
                elif "connecting to open unreal engine" in line_clean.lower():
                    percent = 0.35
                    is_progress = True
                elif "importing texture:" in line_clean.lower() or "importing skeletal mesh:" in line_clean.lower():
                    percent = 0.55
                    is_progress = True
                elif "cooking target folders" in line_clean.lower():
                    percent = 0.75
                    is_progress = True
                elif "building final pak" in line_clean.lower():
                    percent = 0.95
                    is_progress = True
                    
                if is_progress:
                    json_print({"type": "progress", "percent": percent, "message": line_clean})
                    
                # Standard log wrapper fallback
                level = "error" if "error" in line_clean.lower() else ("warning" if "warning" in line_clean.lower() else "standard")
                json_print({"type": "log", "level": level, "message": line_clean})
                
        proc.wait()
        if proc.returncode == 0:
            json_print({"type": "result", "status": "success", "message": f"Successfully completed action: {action}"})
        else:
            json_print({"type": "result", "status": "error", "message": f"Pipeline action {action} failed with exit code: {proc.returncode}"})
            
    except Exception as e:
        json_print({"type": "result", "status": "error", "message": f"Pipeline execution crashed: {str(e)}"})


def handle_mod_command(args, settings):
    """Router for all mod-level pipeline commands."""
    
    # 1. Path Validation Routing
    action = args.action
    if action == "extract":
        is_valid, err_msg = validate_settings(settings, ["fmodel_output", "palworld_exe"])
    elif action in ["create-blend", "set-icon", "open-source"]:
        is_valid, err_msg = validate_settings(settings, ["fmodel_output"])
    elif action in ["open-ue", "open-pak"]:
        is_valid, err_msg = validate_settings(settings, ["uproject"])
    else:
        # push, cook, pack, full, decompile, refresh-blend
        is_valid, err_msg = validate_settings(settings, ["fmodel_output", "ue_root", "uproject"])
        
    if not is_valid:
        error_print(err_msg)
        sys.exit(1)

    # 2. Connection Validation Routing (Remote execution circuit breaker)
    if action in ["push", "full", "decompile", "browse-ue"]:
        is_connected, err_code, err_msg = verify_unreal_connection(settings)
        if not is_connected:
            json_print({"status": "error", "error_code": err_code, "message": err_msg})
            sys.exit(1)

    # 3. Project Integrity Validation (Missing Assets & Plugin check)
    if action in ["push", "full", "cook", "pack", "decompile"]:
        is_intact, integrity_msg = verify_project_integrity(settings)
        if not is_intact:
            json_print({"status": "error", "message": integrity_msg})
            sys.exit(1)

    # 4. Command Execution
    mods = get_mod_info(settings, args.mod)
    if not mods and action not in ["extract", "cancel-pipeline"]:
        error_print(f"Mod {args.mod} was not found on disk.")
        sys.exit(1)

    # Extract pal from game archives (Cue4Parse)
    if action == "extract":
        from utils.extractor import extract_pal_assets
        success, msg = extract_pal_assets(settings, args.mod, "Monster")
        json_print({"status": "success" if success else "error", "message": msg})
        if not success:
            sys.exit(1)

    # Decompile compiled .uassets back into Blender
    elif action == "decompile":
        from utils.plugins.decompiler import run_decompile_pipeline
        mod_data = mods[0]
        category = get_category_from_path(mod_data["fmodel_path"])
        ue_virtual_path = f"/Game/Pal/Model/Character/{category}/{args.mod}"
        
        success, msg = run_decompile_pipeline(
            settings["ue_root"],
            settings["uproject"],
            args.mod,
            mod_data["fmodel_path"],
            ue_virtual_path,
            settings["blender"],
            verbose=True,
            overwrite=getattr(args, "overwrite", False)
        )
        if success:
            json_print({"status": "success", "message": msg})
        else:
            json_print({"status": "error", "message": msg})
            sys.exit(1)

    # Copy custom Icon into the staging directory
    elif action == "set-icon":
        icon_path = getattr(args, "path", "")
        if not icon_path or not os.path.exists(icon_path):
            error_print("Source icon path was not provided or does not exist.")
            sys.exit(1)
            
        mod_data = mods[0]
        dest_icon = os.path.join(mod_data["fmodel_path"], f"T_{args.mod}_icon_normal.png")
        try:
            os.makedirs(os.path.dirname(dest_icon), exist_ok=True)
            shutil.copy2(icon_path, dest_icon)
            json_print({"status": "success", "message": f"Successfully imported custom icon to {dest_icon}"})
        except Exception as e:
            error_print(f"Failed to copy icon: {str(e)}")
            sys.exit(1)

    # Kill stranded background Unreal build processes safely
    elif action == "cancel-pipeline":
        try:
            if os.name == 'nt':
                creation_flags = 0x08000000 # CREATE_NO_WINDOW
                subprocess.run(["taskkill", "/F", "/T", "/IM", "UnrealEditor-Cmd.exe"], capture_output=True, creationflags=creation_flags)
                subprocess.run(["taskkill", "/F", "/T", "/IM", "UnrealPak.exe"], capture_output=True, creationflags=creation_flags)
                subprocess.run(["taskkill", "/F", "/T", "/IM", "Palworld-Win64-Shipping.exe"], capture_output=True, creationflags=creation_flags)
                subprocess.run(["taskkill", "/F", "/T", "/IM", "Palworld.exe"], capture_output=True, creationflags=creation_flags)
            else:
                subprocess.run(["pkill", "-f", "UnrealEditor-Cmd"], capture_output=True)
                subprocess.run(["pkill", "-f", "UnrealPak"], capture_output=True)
                subprocess.run(["pkill", "-f", "Palworld"], capture_output=True)
            json_print({"status": "success", "message": "Cancellation signals sent successfully. Locked files released!"})
        except Exception as e:
            error_print(f"Failed to execute process cancellation: {str(e)}")
            sys.exit(1)

    # Open local mod workspace source directory on native host or WSL
    elif action == "open-source":
        mod_data = mods[0]
        path = mod_data.get("fmodel_path")
        if not path or not os.path.exists(path):
            error_print(f"Source folder for {args.mod} does not exist on disk.")
            sys.exit(1)
        success, msg = system_open_path(path)
        if success:
            json_print({"status": "success", "message": msg})
        else:
            error_print(msg)
            sys.exit(1)

    # Open cooked Unreal Engine Content workspace directory
    elif action == "open-ue":
        mod_data = mods[0]
        path = mod_data.get("ue_path")
        if not path or not os.path.exists(path):
            error_print(f"Unreal assets folder for {args.mod} does not exist on disk. Have you run 'Push to Unreal' yet?")
            sys.exit(1)
        success, msg = system_open_path(path)
        if success:
            json_print({"status": "success", "message": msg})
        else:
            error_print(msg)
            sys.exit(1)

    # Open mod Pak folder and highlight output pak file
    elif action == "open-pak":
        mod_data = mods[0]
        path = mod_data.get("pak_path")
        if not path or not os.path.exists(path):
            error_print(f"Compiled PAK file for {args.mod} does not exist on disk. Have you cooked and packaged the mod yet?")
            sys.exit(1)
        success, msg = system_open_path(path, is_file=True)
        if success:
            json_print({"status": "success", "message": msg})
        else:
            error_print(msg)
            sys.exit(1)

    # Standard / Long-running pipeline commands (reconstructed via build_mod.py subprocess)
    else:
        mod_data = mods[0]
        category = get_category_from_path(mod_data["fmodel_path"])
        
        # Map CLI subcommand action name to build_mod.py action argument format
        action_mapping = {
            "create-blend": "create_blend",
            "refresh-blend": "refresh_blend",
            "cook-only": "cook_only",
            "pack-only": "pack_only"
        }
        build_action = action_mapping.get(action, action)
        
        run_build_mod_and_stream(args.mod, category, build_action)


def handle_audio_command(args, settings):
    """Router for all custom audio subcommands."""
    is_valid, err_msg = validate_settings(settings, ["fmodel_output"])
    if not is_valid:
        error_print(err_msg)
        sys.exit(1)

    mod_name = args.mod
    cry_name = args.cry
    
    mods = get_mod_info(settings, mod_name)
    if not mods:
        error_print(f"Mod {mod_name} was not found on disk.")
        sys.exit(1)
        
    mod_data = mods[0]

    # 1. audio set <mod> <cry> <path>
    if args.subcommand == "set":
        audio_path = args.path
        if not audio_path or not os.path.exists(audio_path):
            error_print(f"Source audio file path not found: {audio_path}")
            sys.exit(1)
            
        success, msg = apply_custom_audio_worker(settings, mod_data, cry_name, audio_path)
        if success:
            json_print({"status": "success", "message": msg})
        else:
            json_print({"status": "error", "message": msg})
            sys.exit(1)

    # 2. audio clear <mod> <cry>
    elif args.subcommand == "clear":
        removed = clear_audio_worker(mod_data, cry_name)
        if removed:
            json_print({"status": "success", "message": f"Successfully cleared custom override for {cry_name}."})
        else:
            json_print({"status": "error", "message": f"No custom override was active for {cry_name}."})

    # 3. audio play <mod> <cry>
    elif args.subcommand == "play":
        audio_dir = os.path.join(mod_data["fmodel_path"], ".palbaker_audio", "sources")
        
        custom_file = None
        for ext in [".wav", ".mp3", ".ogg"]:
            test_file = os.path.join(audio_dir, f"{cry_name}{ext}")
            if os.path.exists(test_file):
                custom_file = test_file
                break

        if custom_file:
            ext = os.path.splitext(custom_file)[1].lower()
            if ext == ".wav":
                play_wav_file(custom_file)
                json_print({"status": "success", "message": "Playing custom WAV override."})
            else:
                # Transcode MP3/OGG preview to temp wav via vgmstream
                repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                vgmstream_cli = os.path.join(repo_root, "deps", "vgmstream", "vgmstream-cli.exe")
                if not os.path.exists(vgmstream_cli):
                    vgmstream_cli = os.path.join(repo_root, "deps", "vgmstream-cli.exe")
                    
                if not os.path.exists(vgmstream_cli):
                    error_print("vgmstream-cli.exe missing. Cannot transcode MP3/OGG preview.")
                    sys.exit(1)
                    
                temp_preview_wav = os.path.join(audio_dir, ".temp_custom_preview.wav")
                if os.path.exists(temp_preview_wav):
                    try: os.remove(temp_preview_wav)
                    except OSError: pass
                    
                cmd = [vgmstream_cli, "-o", temp_preview_wav, custom_file]
                creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creation_flags)
                
                if os.path.exists(temp_preview_wav):
                    play_wav_file(temp_preview_wav)
                    json_print({"status": "success", "message": "Playing transcoded MP3/OGG preview."})
                else:
                    error_print("Failed to transcode preview file.")
                    sys.exit(1)
        else:
            # Play original game sound
            sound_meta = mod_data.get("sound_metadata", {})
            cry_meta = sound_meta.get(cry_name)
            if not cry_meta:
                error_print(f"No original game sound mapped for {cry_name}")
                sys.exit(1)
                
            wem_rel = cry_meta.get("wem_relative_path")
            wem_abs_path = os.path.normpath(os.path.join(settings["fmodel_output"], "Exports", wem_rel))
            
            repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            vgmstream_cli = os.path.join(repo_root, "deps", "vgmstream", "vgmstream-cli.exe")
            if not os.path.exists(vgmstream_cli):
                vgmstream_cli = os.path.join(repo_root, "deps", "vgmstream-cli.exe")
                
            if not os.path.exists(vgmstream_cli):
                error_print("vgmstream-cli.exe missing. Cannot transcode original preview.")
                sys.exit(1)
                
            # Extract dynamically if missing
            if not os.path.exists(wem_abs_path):
                export_root = os.path.join(settings["fmodel_output"], "Exports")
                from utils.extractor import extract_single_file
                extract_single_file(settings, wem_rel, export_root)
                
            if not os.path.exists(wem_abs_path):
                error_print("Original game asset is missing and failed to extract.")
                sys.exit(1)
                
            audio_dir = os.path.join(mod_data["fmodel_path"], ".palbaker_audio")
            os.makedirs(audio_dir, exist_ok=True)
            temp_wav = os.path.join(audio_dir, ".temp_preview.wav")
            if os.path.exists(temp_wav):
                try: os.remove(temp_wav)
                except OSError: pass
                
            cmd = [vgmstream_cli, "-o", temp_wav, wem_abs_path]
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creation_flags)
            
            if os.path.exists(temp_wav):
                play_wav_file(temp_wav)
                json_print({"status": "success", "message": "Playing original game sound preview."})
            else:
                error_print("Failed to transcode original game sound.")
                sys.exit(1)