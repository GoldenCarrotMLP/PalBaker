# tests/test_01_preflight.py
import os
import sys
import json
import shutil
import subprocess

# Resolve paths relative to the test file location
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
SETTINGS_FILE = os.path.join(REPO_ROOT, "manager_settings.json")
BACKUP_FILE = os.path.join(REPO_ROOT, "manager_settings.json.bak")
CLI_ENTRY_POINT = os.path.join(REPO_ROOT, "palbaker_cli.py")

# State tracker to prevent false-alarm double restorations
config_is_dirty = False

def log(message: str, category: str = "INFO"):
    """Formatted terminal output for preflight tracking."""
    print(f"[{category}] {message}", flush=True)

def run_cli_command(args: list[str]) -> tuple[int, str, str]:
    """
    Executes a CLI command via subprocess and captures outputs.
    Guarantees cross-platform execution without popping cmd windows on Windows.
    """
    cmd = [sys.executable, CLI_ENTRY_POINT] + args
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags,
            timeout=10 # Prevents hangs during socket connection tests
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Process timed out after 10 seconds."

def backup_config() -> bool:
    """Creates a safety copy of manager_settings.json."""
    if os.path.exists(SETTINGS_FILE):
        log(f"Backing up active settings to: {BACKUP_FILE}")
        shutil.copy2(SETTINGS_FILE, BACKUP_FILE)
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
        with open(BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(base_settings, f, indent=4)
        return False

def restore_config():
    """Guarantees the restoration of the original settings file safely."""
    global config_is_dirty
    if not config_is_dirty:
        return # Configuration is already clean, skip restoration

    if os.path.exists(BACKUP_FILE):
        log(f"Restoring original settings: {SETTINGS_FILE}")
        shutil.copy2(BACKUP_FILE, SETTINGS_FILE)
        try:
            os.remove(BACKUP_FILE)
        except OSError:
            pass
        config_is_dirty = False
    else:
        log("Backup file missing during teardown. Manual settings recovery may be required.", "ERROR")

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

def main():
    global config_is_dirty
    log("=== PalBaker CLI Modular Preflight Diagnostics ===")
    
    if not os.path.exists(CLI_ENTRY_POINT):
        log(f"Fatal: palbaker_cli.py not found at expected path: {CLI_ENTRY_POINT}", "ERROR")
        sys.exit(1)

    backup_config()
    
    try:
        # ---------------------------------------------------------------------
        # SCENARIO 1: Unconfigured / Empty Settings Validation
        # ---------------------------------------------------------------------
        log("\n--- Scenario 1: Empty Settings Verification ---")
        empty_settings = {
            "fmodel_output": "", 
            "ue_root": "", 
            "uproject": "", 
            "blender": "",
            "palworld_exe": "",
            "show_mapped": False,
            "console_height": 200
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(empty_settings, f, indent=4)
        config_is_dirty = True

        # Run command mapped to manager_handlers.py
        exit_code, stdout, stderr = run_cli_command(["manager", "list"])
        
        # Diagnostics for unhandled crashes
        if "traceback" in stdout.lower() or "traceback" in stderr.lower():
            raise AssertionError(
                "CLI crashed with a raw Python traceback under empty configurations.\n"
                "Please ensure 'utils.cli.manager_handlers' implements validate_settings."
            )
            
        parsed = parse_cli_json(stdout)
        if not parsed:
            raise AssertionError(
                f"CLI did not output a valid JSON envelope on failure. "
                f"Exit Code: {exit_code}\nSTDOUT: {stdout}\nSTDERR: {stderr}"
            )
            
        if parsed.get("status") != "error":
            raise AssertionError(f"Expected JSON 'status' to be 'error', got: '{parsed.get('status')}'")
            
        log("✅ PASS: CLI handles empty configurations gracefully.")

        # ---------------------------------------------------------------------
        # SCENARIO 2: Garbage / Invalid Paths Validation
        # ---------------------------------------------------------------------
        log("\n--- Scenario 2: Garbage Paths Verification ---")
        garbage_settings = {
            "fmodel_output": "C:\\This\\Is\\A\\Fake\\Path", 
            "ue_root": "D:\\Unreal\\NotReal", 
            "uproject": "E:\\NoProject\\test.uproject", 
            "blender": "F:\\NoBlender\\blender.exe",
            "palworld_exe": "G:\\NoGame\\Palworld.exe",
            "show_mapped": False,
            "console_height": 200
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(garbage_settings, f, indent=4)
        config_is_dirty = True

        # Run command mapped to mod_handlers.py requiring Blender config
        exit_code, stdout, stderr = run_cli_command(["mod", "create-blend", "BadCatgirl"])
        
        if "traceback" in stdout.lower() or "traceback" in stderr.lower():
            raise AssertionError(
                "CLI crashed with a raw Python traceback under garbage configurations.\n"
                "Please ensure 'utils.cli.mod_handlers' implements validate_settings."
            )
            
        parsed = parse_cli_json(stdout)
        if not parsed:
            raise AssertionError(
                f"CLI did not output a valid JSON envelope on failure. "
                f"Exit Code: {exit_code}\nSTDOUT: {stdout}\nSTDERR: {stderr}"
            )
            
        if parsed.get("status") != "error":
            raise AssertionError(f"Expected JSON 'status' to be 'error', got: '{parsed.get('status')}'")
            
        if "does not exist on disk" not in parsed.get("message", ""):
            log(f"Warning: Expected path existence warning message. Got: '{parsed.get('message')}'", "WARNING")
            
        log("✅ PASS: CLI handles invalid disk paths gracefully without OS-level process crashes.")

        # ---------------------------------------------------------------------
        # SCENARIO 3: Positive Lightweight Path Resolution
        # ---------------------------------------------------------------------
        log("\n--- Scenario 3: Real Configuration Verification ---")
        restore_config() # Restore actual config file early to execute positive tests
        
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            real_settings = json.load(f)
            
        uproject_val = real_settings.get("uproject", "")
        if not uproject_val or not os.path.exists(uproject_val):
            log("Positive verification skipped: 'uproject' path is not configured locally.", "WARNING")
        else:
            # 1. Executability & Version Handshake (Autodetect & Executable Check)
            log("Checking local toolchain executability and version metrics...")
            exit_code, stdout, stderr = run_cli_command(["env", "autodetect"])
            parsed_detect = parse_cli_json(stdout)
            if not parsed_detect or parsed_detect.get("status") != "success":
                raise AssertionError(f"Autodetect verification failed. Output: {stdout} {stderr}")
            
            # 2. Unreal Engine Connection Verification
            exit_code, stdout, stderr = run_cli_command(["mod", "ping", "BadCatgirl"])
            parsed_ping = parse_cli_json(stdout)
            if not parsed_ping:
                raise AssertionError(
                    f"CLI did not output valid JSON during lightweight ping. "
                    f"Exit Code: {exit_code}\nSTDOUT: {stdout}\nSTDERR: {stderr}"
                )
                
            log(f"Connection Diagnostic Code: {parsed_ping.get('diagnostic_code')}")
            log(f"Connection Status Message:   {parsed_ping.get('message')}")
            
            # 3. MSVC Compiler & ModKit Asset Verification
            log("Verifying MSVC compiler and required asset injection...")
            exit_code, stdout, stderr = run_cli_command(["env", "verify"])
            parsed_verify = parse_cli_json(stdout)
            if not parsed_verify or parsed_verify.get("status") != "success":
                # If compiler or asset validation failed, grab the data error block
                err_details = parsed_verify.get("data", {}).get("error") if parsed_verify else stderr
                raise AssertionError(f"ModKit compilation environment is unhealthy: {err_details}")
            
            log("✅ PASS: CLI resolved paths, verified compiler metrics, and executed connection check successfully.")

        log("\n🎉 ALL PREFLIGHT DIAGNOSTIC SCENARIOS PASSED.")

    except Exception as e:
        log(f"❌ PREFLIGHT TEST FAILED: {str(e)}", "ERROR")
        sys.exit(1)
        
    finally:
        log("\n--- Cleanup & Teardown ---")
        restore_config()

if __name__ == "__main__":
    main()