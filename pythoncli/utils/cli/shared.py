# utils/cli/shared.py
import json
import sys
import os

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
