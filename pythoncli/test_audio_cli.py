import subprocess
import json
import os
import sys

# Hardcoded test file from your previous message
TEST_FILE = r"C:\Users\ander\Downloads\a.mp3"

def run_cmd(cmd, silent=False):
    print(f"\n[RUNNING] > {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if not silent and result.stdout:
        print(f"[STDOUT] {result.stdout.strip()}")
    if result.stderr:
        print(f"[STDERR] {result.stderr.strip()}")
    return result.stdout.strip()

def get_pinkcat_joy():
    stdout = run_cmd([sys.executable, "palbaker_cli.py", "manager", "list", "--show-unextracted"], silent=True)
    try:
        # We only want the last line in case there are warnings or other prints
        json_str = stdout.strip().split('\n')[-1]
        data = json.loads(json_str)
        if data.get("status") == "success":
            for mod in data.get("data", []):
                if mod.get("name") == "PinkCat":
                    return mod.get("audio_overrides", {}).get("Joy")
    except Exception as e:
        print(f"[JSON ERROR] Failed to parse manager list output: {e}")
    return None

def main():
    print("=== PalBaker CLI Audio CRUD Test ===")
    if not os.path.exists(TEST_FILE):
        print(f"ERROR: Test file {TEST_FILE} not found! Please place an mp3 there or adjust the TEST_FILE variable.")
        sys.exit(1)

    print("\n--- 1. Checking Initial State (Read) ---")
    initial = get_pinkcat_joy()
    print(f"PinkCat 'Joy' override is currently: {initial}")

    print("\n--- 2. Setting Audio (Create/Update) ---")
    run_cmd([sys.executable, "palbaker_cli.py", "audio", "set", "PinkCat", "Joy", TEST_FILE])

    print("\n--- 3. Verifying the Set Command (Read) ---")
    staged = get_pinkcat_joy()
    print(f"PinkCat 'Joy' override is now: {staged}")
    if staged is not None:
        print("✅ SUCCESS: Audio override correctly detected in manager list!")
    else:
        print("❌ WARNING: Audio override was not staged properly.")

    print("\n--- 4. Clearing Audio (Delete) ---")
    run_cmd([sys.executable, "palbaker_cli.py", "audio", "clear", "PinkCat", "Joy"])

    print("\n--- 5. Verifying the Clear Command (Read) ---")
    cleared = get_pinkcat_joy()
    print(f"PinkCat 'Joy' override is now: {cleared}")
    if cleared is None:
        print("✅ SUCCESS: Audio override correctly cleared!")
    else:
        print("❌ WARNING: Audio override was not cleared.")

if __name__ == "__main__":
    main()
