import subprocess
import json
import os
import sys

MOD_NAME = "OctopusGirl"

def run_cmd(cmd):
    print(f"\n[RUNNING] > {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    for line in result.stdout.strip().split('\n'):
        if line:
            try:
                data = json.loads(line)
                if data.get("type") == "log":
                    print(f"[{data.get('level', 'INFO').upper()}] {data.get('message')}")
                else:
                    print(f"[{data.get('type', 'RESULT').upper()}] {data}")
            except json.JSONDecodeError:
                print(f"[RAW] {line}")

    if result.stderr:
        print(f"[STDERR] {result.stderr.strip()}")
        
    return result.stdout.strip()

def main():
    print(f"=== PalBaker CLI Pipeline Test: {MOD_NAME} ===")
    
    print("\n--- 1. Extracting from Game ---")
    run_cmd([sys.executable, "palbaker_cli.py", "mod", "extract", MOD_NAME])

    print("\n--- 2. Generating .blend file ---")
    run_cmd([sys.executable, "palbaker_cli.py", "mod", "create-blend", MOD_NAME])

    print("\n--- 3. Pushing to Unreal ---")
    run_cmd([sys.executable, "palbaker_cli.py", "mod", "push", MOD_NAME])
    
    print("\n--- 4. Generate sources from Unreal (Decompile - FORCED OVERWRITE) ---")
    run_cmd([sys.executable, "palbaker_cli.py", "mod", "decompile", MOD_NAME, "--overwrite"])

    print("\n--- 5. Cook ---")
    run_cmd([sys.executable, "palbaker_cli.py", "mod", "cook", MOD_NAME])

    print("\n--- 6. Pack ---")
    run_cmd([sys.executable, "palbaker_cli.py", "mod", "pack", MOD_NAME])

    print("\n✅ PIPELINE TEST COMPLETE")

if __name__ == "__main__":
    main()
