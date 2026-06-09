# utils/builder/pipeline_runner.py
import os
import sys
import asyncio
import subprocess
import time
from utils.builder.log_analyzer import LogAnalyzer

async def run_pipeline_async(script_args: list, log_callback, progress_callback, complete_callback, cancel_token: dict):
    """
    Spawns build_mod.py as an unbuffered async subprocess, streams the output,
    runs the log analyzer on every line, and triggers callbacks.
    """
    script_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "build_mod.py"))
    
    analyzer = LogAnalyzer()
    cmd = [sys.executable, "-u", script_path] + script_args
    
    try:
        # Cross-platform arguments to ensure the process group can be cleanly killed
        kwargs = {}
        if os.name == 'nt':
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        else:
            kwargs['start_new_session'] = True
            
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            **kwargs
        )
        
        cancel_token["process"] = process
        last_update_time = time.time()
        
        if process.stdout:
            while True:
                line_bytes = await process.stdout.readline()
                if not line_bytes:
                    break
                
                line = line_bytes.decode('utf-8', errors='replace').rstrip()
                
                analyzed_text, color, is_error = analyzer.analyze_line(line)
                log_callback(analyzed_text, color, flush=False)
                progress_callback(line, flush=False)
                
                await asyncio.sleep(0.001)
                
                current_time = time.time()
                if current_time - last_update_time >= 0.10:
                    log_callback(None, None, flush=True)
                    last_update_time = current_time

        returncode = await process.wait()
        success = (returncode == 0)
        
        summary = analyzer.generate_summary(success)
        complete_callback(success, returncode, summary)
        
    except Exception as e:
        print(f"[PalBaker] Fatal Exception in Async Pipeline Runner: {e}", flush=True)
        complete_callback(False, -1, None)