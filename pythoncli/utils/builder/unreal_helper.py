import sys
import os
import time

def run_remote_command(ue_root: str, project_name: str, cmd: str) -> tuple[bool, str]:
    """
    Establishes a remote execution connection with the running Unreal Editor 
    and executes a raw python code string.
    """
    ue_python_dir = os.path.join(ue_root, "Engine", "Plugins", "Experimental", "PythonScriptPlugin", "Content", "Python")
    sys.path.append(ue_python_dir)
    
    try:
        import remote_execution  # type: ignore
    except ImportError:
        return False, "Could not find remote_execution.py in Unreal installation directory."

    remote_exec = remote_execution.RemoteExecution()
    remote_exec.start()
    
    # Non-blocking polling loop to connect to Unreal Node instantly
    node = None
    timeout = 10.0
    elapsed = 0.0
    while elapsed < timeout:
        node = next((n for n in remote_exec.remote_nodes if n.get('project_name', '').lower() == project_name.lower()), None)
        if node:
            break
        time.sleep(0.5)
        elapsed += 0.5

    if not node:
        all_nodes = list(remote_exec.remote_nodes)
        remote_exec.stop()
        
        if not all_nodes:
            error_details = (
                f"Unreal Editor is running but remote connection timed out ({timeout}s).\n\n"
                f"=== REMOTE EXECUTION TROUBLESHOOTING ===\n"
                f"1. Verify Project Settings:\n"
                f"   Inside Unreal Editor, open Edit -> Project Settings -> Plugins -> Python.\n"
                f"   Ensure 'Enable Remote Execution' is checked.\n"
                f"2. Network Adapter Conflict (Highly Likely):\n"
                f"   Your logs show active virtual adapters (e.g., Oculus Virtual Audio/Network).\n"
                f"   WSL, Hyper-V, VMware, and VR headsets install virtual network adapters\n"
                f"   that frequently hijack local UDP multicast traffic. Python binds to these\n"
                f"   instead of your main loopback card.\n"
                f"   -> Try temporarily disabling non-essential virtual adapters in your OS:\n"
                f"      Control Panel -> Network and Internet -> Network Connections (right-click & disable).\n"
                f"3. Check Firewall Rules:\n"
                f"   Make sure both 'UnrealEditor.exe' and your active Python executable have Private/Public\n"
                f"   network permissions allowed in the Windows Defender Firewall panel."
            )
        else:
            found_names = [n.get('project_name', 'Unknown') for n in all_nodes]
            error_details = (
                f"Found active Unreal Editor nodes, but none matched your configured project name '{project_name}'.\n"
                f"Active project nodes discovered: {found_names}\n\n"
                f"Verify that your .uproject file name ({project_name}.uproject) exactly matches\n"
                f"the project currently open in your Unreal Editor."
            )
        return False, error_details
        
    remote_exec.open_command_connection(node.get('node_id'))
    
    print("Sending navigation command to Unreal Editor...", flush=True)
    response = remote_exec.run_command(cmd)
    remote_exec.stop()

    logs = []
    if response is not None:
        if response.get('output'):
            for log_entry in response['output']:
                log_text = log_entry.get('output', '') if isinstance(log_entry, dict) else str(log_entry)
                if log_text.strip():
                    logs.append(log_text.rstrip())
                    
        success = response.get('success', False)
        result_msg = "\n".join(logs)
        if not success:
            result_msg += f"\nError Details: {response.get('result')}"
        return success, result_msg
    else:
        return False, "No response received from Unreal remote execution."

def focus_unreal_window(project_name: str):
    """
    Finds the active Unreal Editor window matching the target project name 
    and brings it to the front/foreground (Windows only).
    """
    if os.name != 'nt':
        return
        
    import ctypes
    user32 = ctypes.windll.user32
    
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
    hwnds = []
    
    def foreach_window(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                if "unreal editor" in title.lower() and project_name.lower() in title.lower():
                    hwnds.append(hwnd)
        return True
        
    try:
        user32.EnumWindows(EnumWindowsProc(foreach_window), 0)
    except Exception as e:
        print(f"Warning: Failed to enumerate OS windows: {e}")
        return

    for hwnd in hwnds:
        user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)
        break


def run_remote_import(ue_root: str, project_name: str, fmodel_dir: str, ue_script_path: str) -> tuple[bool, str]:
    """Establishes a remote execution socket connection with the Unreal Editor and runs the importer."""
    ue_python_dir = os.path.join(ue_root, "Engine", "Plugins", "Experimental", "PythonScriptPlugin", "Content", "Python")
    sys.path.append(ue_python_dir)
    
    try:
        import remote_execution  # type: ignore
    except ImportError:
        return False, "Could not find remote_execution.py in Unreal installation directory."

    remote_exec = remote_execution.RemoteExecution()
    remote_exec.start()
    
    # Non-blocking polling loop
    node = None
    timeout = 10.0
    elapsed = 0.0
    while elapsed < timeout:
        node = next((n for n in remote_exec.remote_nodes if n.get('project_name', '').lower() == project_name.lower()), None)
        if node:
            break
        time.sleep(0.5)
        elapsed += 0.5

    if not node:
        all_nodes = list(remote_exec.remote_nodes)
        remote_exec.stop()
        
        if not all_nodes:
            error_details = (
                f"Unreal Editor is running but remote connection timed out ({timeout}s).\n\n"
                f"=== REMOTE EXECUTION TROUBLESHOOTING ===\n"
                f"1. Verify Project Settings:\n"
                f"   Inside Unreal Editor, open Edit -> Project Settings -> Plugins -> Python.\n"
                f"   Ensure 'Enable Remote Execution' is checked.\n"
                f"2. Network Adapter Conflict (Highly Likely):\n"
                f"   Your logs show active virtual adapters (e.g., Oculus Virtual Audio/Network).\n"
                f"   WSL, Hyper-V, VMware, and VR headsets install virtual network adapters\n"
                f"   that frequently hijack local UDP multicast traffic. Python binds to these\n"
                f"   instead of your main loopback card.\n"
                f"   -> Try temporarily disabling non-essential virtual adapters in your OS:\n"
                f"      Control Panel -> Network and Internet -> Network Connections (right-click & disable).\n"
                f"3. Check Firewall Rules:\n"
                f"   Make sure both 'UnrealEditor.exe' and your active Python executable have Private/Public\n"
                f"   network permissions allowed in the Windows Defender Firewall panel."
            )
        else:
            found_names = [n.get('project_name', 'Unknown') for n in all_nodes]
            error_details = (
                f"Found active Unreal Editor nodes, but none matched your configured project name '{project_name}'.\n"
                f"Active project nodes discovered: {found_names}\n\n"
                f"Verify that your .uproject file name ({project_name}.uproject) exactly matches\n"
                f"the project currently open in your Unreal Editor."
            )
        return False, error_details
        
    remote_exec.open_command_connection(node.get('node_id'))
    
    palbaker_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")).replace("\\", "/")
    ue_script_path_clean = ue_script_path.replace("\\", "/")
    
    cmd = f'TARGET_FOLDER = r"{fmodel_dir}"; PALBAKER_ROOT = r"{palbaker_root}"; f = open(r"{ue_script_path_clean}", encoding="utf-8"); exec(f.read()); f.close()'
    
    print("Injecting import commands into Unreal Editor...")
    response = remote_exec.run_command(cmd)
    remote_exec.stop()

    logs = []
    if response is not None:
        if response.get('output'):
            for log_entry in response['output']:
                log_text = log_entry.get('output', '') if isinstance(log_entry, dict) else str(log_entry)
                if log_text.strip():
                    logs.append(log_text.rstrip())
                    
        success = response.get('success', False)
        result_msg = "\n".join(logs)
        if not success:
            result_msg += f"\nError Details: {response.get('result')}"
        return success, result_msg
    else:
        return False, "No response received from Unreal remote execution."