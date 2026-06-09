import subprocess
import json
import sys

def run_cmd(cmd):
    print(f"\n[RUNNING] > {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(f"[STDOUT] {result.stdout.strip()}")
    if result.stderr:
        print(f"[STDERR] {result.stderr.strip()}")
    return result.stdout.strip()

def main():
    print("=== PalBaker CLI Creator CRUD Test ===")

    print("\n--- 1. Querying List of Standalone Custom Pals ---")
    stdout = run_cmd([sys.executable, "palbaker_cli.py", "creator", "list"])
    try:
        data = json.loads(stdout)
    except Exception as e:
        print(f"Failed to parse list: {e}")
        sys.exit(1)

    furret_record = None
    for pal in data.get("data", []):
        if pal.get("CharacterID") == "Furret":
            furret_record = pal
            break

    if not furret_record:
        print("❌ ERROR: Could not find 'Furret' standalone Pal on disk. Ensure it is initialized in your Creator directory.")
        sys.exit(1)

    print(f"✅ FOUND Furret! Original Level-1 Move is: {furret_record['Learnset'][0]['WazaID']}")

    print("\n--- 2. Updating Learnset (Replacing level 1 Scratch with AirCanon) ---")
    # Mutate record
    furret_record["Learnset"][0]["WazaID"] = "AirCanon"
    
    # Execute update via CLI using --data payload
    payload_str = json.dumps(furret_record)
    run_cmd([sys.executable, "palbaker_cli.py", "creator", "update", "Furret", "--data", payload_str])

    print("\n--- 3. Verifying Update on Disk (Read) ---")
    stdout2 = run_cmd([sys.executable, "palbaker_cli.py", "creator", "list"])
    try:
        data2 = json.loads(stdout2)
    except Exception as e:
        print(f"Failed to parse updated list: {e}")
        sys.exit(1)

    updated_furret = None
    for pal in data2.get("data", []):
        if pal.get("CharacterID") == "Furret":
            updated_furret = pal
            break

    if updated_furret and updated_furret["Learnset"][0]["WazaID"] == "AirCanon":
        print("🎉 SUCCESS: Furret's level 1 move successfully saved as AirCanon!")
    else:
        print("❌ WARNING: Update did not persist on disk.")

if __name__ == "__main__":
    main()
