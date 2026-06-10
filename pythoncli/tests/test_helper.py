# tests/test_helper.py
import os
import sys
import json
import time
import shutil
import subprocess

def log(message: str, category: str = "INFO"):
    """Formatted terminal output for tracking."""
    print(f"[{category}] {message}", flush=True)

# Resolve paths relative to the helper file location
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)

def run_cli_command(args: list[str], cli_entry_point: str) -> tuple[int, str, str]:
    """
    Executes a CLI command via subprocess and captures outputs.
    Guarantees cross-platform execution and forces the working directory 
    to the repository root to prevent relative path leaks.
    """
    cmd = [sys.executable, cli_entry_point] + args
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags,
            cwd=REPO_ROOT,
            timeout=120
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Process timed out."

def parse_cli_json(stdout: str) -> dict | None:
    """
    Searches for and parses a valid JSON line in stdout.
    This protects the test from breaking on random prints or compiler warnings.
    """
    for line in reversed(stdout.splitlines()):
        line_clean = line.strip()
        if line_clean.startswith("{") and line_clean.endswith("}"):
            try:
                return json.loads(line_clean)
            except json.JSONDecodeError:
                pass
    return None


# =============================================================================
# AUTONOMOUS PROCESS ORCHESTRATION ENGINE (UNREAL ENGINE CONTROLLER)
# =============================================================================

def is_unreal_running() -> bool:
    """Checks if UnrealEditor.exe is physically running on the system."""
    try:
        if os.name == 'nt':
            creation_flags = 0x08000000 # CREATE_NO_WINDOW
            output = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq UnrealEditor.exe", "/NH"], 
                capture_output=True, text=True, creationflags=creation_flags
            ).stdout
            return "UnrealEditor.exe" in output
        else:
            output = subprocess.run(["pgrep", "-x", "UnrealEditor"], capture_output=True, text=True).stdout
            return bool(output.strip())
    except Exception:
        return False

def close_unreal_editor() -> bool:
    """Force-kills running instances of UnrealEditor and UnrealEditor-Cmd."""
    try:
        if os.name == 'nt':
            creation_flags = 0x08000000 # CREATE_NO_WINDOW
            subprocess.run(["taskkill", "/F", "/T", "/IM", "UnrealEditor.exe"], capture_output=True, creationflags=creation_flags)
            subprocess.run(["taskkill", "/F", "/T", "/IM", "UnrealEditor-Cmd.exe"], capture_output=True, creationflags=creation_flags)
        else:
            subprocess.run(["pkill", "-f", "UnrealEditor"], capture_output=True)
            subprocess.run(["pkill", "-f", "UnrealEditor-Cmd"], capture_output=True)
            
        # Poll up to 10 seconds for process termination
        for _ in range(20):
            if not is_unreal_running():
                return True
            time.sleep(0.5)
    except Exception:
        pass
    return not is_unreal_running()

def ensure_unreal_closed():
    """Safety wrapper: Guarantees that Unreal Editor is closed to prevent DLL locks."""
    if is_unreal_running():
        log("Unreal Editor process detected. Issuing automated force-close to release file locks...")
        success = close_unreal_editor()
        if success:
            log("✅ Unreal Editor successfully terminated.")
        else:
            log("⚠️ Failed to terminate Unreal Editor cleanly.", "WARNING")
    else:
        log("Unreal Editor is offline (Clean compiler environment verified).")

def ensure_unreal_opened(settings: dict, cli_entry_point: str) -> bool:
    """
    Safely launches Unreal Editor headlessly and polls UDP pings 
    until the editor is responsive and ready to receive commands.
    """
    if is_unreal_running():
        # Rapid connection check
        exit_code, stdout, _ = run_cli_command(["mod", "ping", "BadCatgirl"], cli_entry_point)
        parsed = parse_cli_json(stdout)
        if parsed and parsed.get("diagnostic_code") == "FULLY_CONNECTED":
            log("Unreal Editor is already running and fully responsive.")
            return True
        else:
            log("Unreal Editor is running but unresponsive. Triggering automated restart...")
            close_unreal_editor()

    log("Unreal Editor is offline. Launching headlessly...")
    exit_code, stdout, stderr = run_cli_command(["env", "launch-unreal"], cli_entry_point)
    parsed_launch = parse_cli_json(stdout)
    
    if exit_code != 0 or not parsed_launch or parsed_launch.get("status") != "success":
        raise RuntimeError(f"Failed to launch Unreal Editor. STDOUT: {stdout}\nSTDERR: {stderr}")

    log("Launch command accepted. Polling UDP handshake connection (can take up to 90 seconds)...")
    
    # Poll connection up to 90 seconds (180 iterations of 0.5s)
    for i in range(180):
        exit_code, stdout, _ = run_cli_command(["mod", "ping", "BadCatgirl"], cli_entry_point)
        parsed_ping = parse_cli_json(stdout)
        if parsed_ping and parsed_ping.get("diagnostic_code") == "FULLY_CONNECTED":
            log(f"✅ Unreal Editor booted and fully connected (Ready after {i*0.5}s)!")
            return True
        time.sleep(0.5)

    raise TimeoutError("Unreal Editor launched successfully but failed to accept Python remote connections within 90 seconds.")


class SettingsSandbox:
    """
    Chaos-Engineering context helper to manage 3 distinct configuration states.
    1. 'empty'   : Zeroed out settings keys
    2. 'garbage' : Fake directory paths to test robust failure checks
    3. 'real'    : Restored production settings configuration
    """
    def __init__(self, repo_root: str):
        self.repo_root = repo_root
        self.settings_file = os.path.join(repo_root, "manager_settings.json")
        self.backup_file = os.path.join(repo_root, "manager_settings.json.bak")
        self.config_is_dirty = False

    def backup(self) -> bool:
        """Creates a safety copy of manager_settings.json."""
        if os.path.exists(self.settings_file):
            log(f"Backing up active settings to: {self.backup_file}")
            shutil.copy2(self.settings_file, self.backup_file)
            return True
        else:
            log("No existing manager_settings.json detected. Creating base config for test sequence.", "WARNING")
            base_settings = {
                "fmodel_output": "", 
                "ue_root": "", 
                "uproject": "", 
                "blender": "",
                "palworld_exe": "",
                "show_mapped": False,
                "console_height": 200
            }
            with open(self.backup_file, "w", encoding="utf-8") as f:
                json.dump(base_settings, f, indent=4)
            return False

    def apply_profile(self, profile_type: str):
        """Applies one of the three configuration profiles to the settings file."""
        if profile_type == "empty":
            empty_settings = {
                "fmodel_output": "", 
                "ue_root": "", 
                "uproject": "", 
                "blender": "",
                "palworld_exe": "",
                "show_mapped": False,
                "console_height": 200
            }
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(empty_settings, f, indent=4)
            self.config_is_dirty = True
            log("Applied Profile: EMPTY_SETTINGS")

        elif profile_type == "garbage":
            garbage_settings = {
                "fmodel_output": "C:\\This\\Is\\A\\Fake\\Path", 
                "ue_root": "D:\\Unreal\\NotReal", 
                "uproject": "E:\\NoProject\\test.uproject", 
                "blender": "F:\\NoBlender\\blender.exe",
                "palworld_exe": "G:\\NoGame\\Palworld.exe",
                "show_mapped": False,
                "console_height": 200
            }
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(garbage_settings, f, indent=4)
            self.config_is_dirty = True
            log("Applied Profile: GARBAGE_SETTINGS")

        elif profile_type == "real":
            self.restore()
            log("Applied Profile: REAL_SETTINGS (Restored active config)")

        else:
            raise ValueError(f"Unknown settings profile: {profile_type}")

    def restore(self):
        """Guarantees the restoration of the original settings file safely."""
        if not self.config_is_dirty:
            return

        if os.path.exists(self.backup_file):
            shutil.copy2(self.backup_file, self.settings_file)
            try:
                os.remove(self.backup_file)
            except OSError:
                pass
            self.config_is_dirty = False
        else:
            log("Backup file missing during teardown. Manual settings recovery may be required.", "ERROR")