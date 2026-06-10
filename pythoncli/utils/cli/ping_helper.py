# utils/cli/ping_helper.py
import os
import sys
import time
from utils.plugins.installer import is_unreal_running
from utils.plugins.detector import check_remote_execution_settings

def run_unreal_ping(settings) -> dict:
    unreal_running = is_unreal_running()
    ini_enabled = check_remote_execution_settings(settings["uproject"]) if settings.get("uproject") else False
    
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
        
    return {
        "unreal_running": unreal_running,
        "ini_enabled": ini_enabled,
        "connection_active": connection_active,
        "plugin_loaded": plugin_loaded,
        "diagnostic_code": diagnostic_code,
        "message": message
    }
