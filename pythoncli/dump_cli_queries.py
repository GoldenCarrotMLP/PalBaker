# dump_cli_queries.py
import subprocess
import json
import os
import sys

# Target output dump file
OUTPUT_FILE = "cli_queries_dump.json"

# Define the baseline mock Pal ID to query mod-specific Altermatic states
BASELINE_PAL = "Furret" 

# Comprehensive array of read/get query endpoints of your CLI API
QUERY_COMMANDS = [
    ("config_get", ["config", "get"]),
    ("manager_list", ["manager", "list"]),
    ("manager_list_unextracted", ["manager", "list", "--show-unextracted"]),
    ("manager_get_caches", ["manager", "get-caches"]),
    ("creator_list", ["creator", "list"]),
    ("env_status", ["env", "status"]),
    ("env_verify", ["env", "verify"]),
    ("env_autodetect", ["env", "autodetect"]),
    ("altermatic_list", ["altermatic", "list", BASELINE_PAL]),
    ("altermatic_metadata", ["altermatic", "metadata", BASELINE_PAL]),
    ("altermatic_sidecar", ["altermatic", "sidecar", BASELINE_PAL, "base"])
]

def truncate_first_mid_last(data):
    """
    Recursively walks through any JSON structure and extracts ONLY 
    the first, middle, and last elements/keys of lists and dictionaries.
    """
    if isinstance(data, list):
        n = len(data)
        if n == 0:
            return []
        elif n == 1:
            selected = [data[0]]
        elif n == 2:
            selected = [data[0], data[1]]
        else:
            # Slices to first, middle, and last elements
            selected = [data[0], data[n // 2], data[-1]]
        return [truncate_first_mid_last(item) for item in selected]
        
    elif isinstance(data, dict):
        items = list(data.items())
        n = len(items)
        if n == 0:
            return {}
        elif n == 1:
            selected = [items[0]]
        elif n == 2:
            selected = [items[0], items[1]]
        else:
            # Slices to first, middle, and last dictionary key-value tuples
            selected = [items[0], items[n // 2], items[-1]]
        return {k: truncate_first_mid_last(v) for k, v in selected}
        
    return data

def main():
    print("=== PalBaker CLI Get-Request Query Dumper ===", flush=True)
    cli_path = os.path.join(os.path.dirname(__file__), "palbaker_cli.py")
    
    if not os.path.exists(cli_path):
        print(f"❌ Error: Could not locate 'palbaker_cli.py' at {cli_path}", flush=True)
        sys.exit(1)

    dump_payload = {}
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

    for label, args in QUERY_COMMANDS:
        print(f"Executing: python palbaker_cli.py {' '.join(args)} ...", end="", flush=True)
        cmd = [sys.executable, cli_path] + args
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags
            )
            
            raw_stdout = result.stdout.strip()
            if not raw_stdout:
                print(" ⚠️ Empty response (skip)", flush=True)
                continue
                
            last_line = raw_stdout.split('\n')[-1]
            parsed_json = json.loads(last_line)
            
            # Extract first, middle, and last elements/keys
            truncated_json = truncate_first_mid_last(parsed_json)
            dump_payload[label] = truncated_json
            print(" ✓ OK", flush=True)
            
        except json.JSONDecodeError:
            print(" ❌ Failed to parse JSON (skip)", flush=True)
        except Exception as e:
            print(f" ❌ Error: {str(e)}", flush=True)

    if dump_payload:
        try:
            output_path = os.path.join(os.path.dirname(__file__), OUTPUT_FILE)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(dump_payload, f, indent=4)
            print(f"\n🎉 SUCCESS: Consolidated query outputs saved to: {output_path}")
            print(f"Size on disk: {os.path.getsize(output_path)} bytes")
        except Exception as e:
            print(f"\n❌ Error writing output file: {e}", flush=True)
    else:
        print("\n⚠️ Warning: No query payloads were successfully captured.", flush=True)

if __name__ == "__main__":
    main()