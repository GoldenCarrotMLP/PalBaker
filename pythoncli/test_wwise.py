# test_wwise.py
import os
import subprocess
import shutil

def run_isolated_test():
    repo_root = os.path.abspath(os.path.dirname(__file__))
    
    # The specific file you want to test
    input_audio = r"H:\SteamLibrary\steamapps\common\Palworld\Output\Exports\Pal\Content\Pal\Model\Character\Monster\WeaselDragon\.palbaker_audio\sources\Normal.mp3"
    
    if not os.path.exists(input_audio):
        print(f"❌ Error: Input test audio not found at: {input_audio}")
        return

    # 1. Resolve WwiseConsole location
    candidate_paths = [
        os.path.join(repo_root, "deps", "wwise", "Authoring", "x64", "Release", "bin", "WwiseConsole.exe"),
        os.path.join(repo_root, "deps", "wwise", "bin", "WwiseConsole.exe")
    ]
    
    wwise_console = next((p for p in candidate_paths if os.path.exists(p)), None)
    if not wwise_console:
        print("❌ Error: Could not locate WwiseConsole.exe inside 'deps/wwise/' folder.")
        return

    # 2. Locate the Wwise Project file
    project_dir = os.path.join(repo_root, "deps", "wwise", "project")
    wproj_path = None
    if os.path.exists(project_dir):
        for root, _, files in os.walk(project_dir):
            for f in files:
                if f.endswith(".wproj"):
                    wproj_path = os.path.join(root, f)
                    break
            if wproj_path: break

    if not wproj_path:
        print(f"❌ Error: No .wproj file found inside: {project_dir}")
        return

    print(f"Found WwiseConsole: {wwise_console}")
    print(f"Found Wwise Project: {wproj_path}")

    # 3. Create the list.wsources file for external sources compilation
    wsources_path = os.path.join(repo_root, "deps", "test_list.wsources")
    output_dir = os.path.join(repo_root, "deps", "output_test_wwise")
    
    xml_content = f"""<?xml version="1.0" encoding="utf-8"?>
<ExternalSourcesList SchemaVersion="1">
    <Source Path="{input_audio.replace(os.sep, '/')}" Conversion="Default Conversion Settings" />
</ExternalSourcesList>
"""
    with open(wsources_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
        
    print(f"Created sources descriptor: {wsources_path}")

    # Reset test output directory
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # 4. Execute the command line conversion
    cmd = [
        wwise_console,
        "convert-external-source",
        wproj_path,
        "--source-file", wsources_path,
        "--output", output_dir,
        "--platform", "Windows",
        "--verbose"
    ]

    print("\n" + "="*50)
    print(f"Executing Wwise Console...")
    print("="*50)
    
    try:
        # Run and stream output directly to the terminal
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        print("="*50)
        print(f"Exit Code: {result.returncode}")
        
    except Exception as e:
        print(f"Execution crashed: {e}")
        return

    # 5. Check if ANY .wem file was generated ANYWHERE in the output directory
    print("\nScanning output directory for generated files...")
    found_wems = []
    for root, _, files in os.walk(output_dir):
        for f in files:
            if f.endswith(".wem"):
                found_wems.append(os.path.join(root, f))

    if found_wems:
        print(f"🎉 SUCCESS! Found {len(found_wems)} generated .wem file(s):")
        for fw in found_wems:
            print(f"  -> {fw}")
    else:
        print("❌ Failure: No .wem files were generated. Wwise failed to convert the file.")

if __name__ == "__main__":
    run_isolated_test()