import os
import sys
import json
import subprocess

BLENDER_TEST_SCRIPT = """import bpy
import os
import sys

def run_diagnostic():
    print("\\n" + "=" * 60)
    print("=== BLENDER HEADLESS BAKE DIAGNOSTIC ===")
    print("=" * 60)
    
    found_any = False
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
            
        # Find the Combine Color node
        combine_node = next((n for n in mat.node_tree.nodes if n.type == 'COMBINE_COLOR'), None)
        if not combine_node:
            continue
            
        found_any = True
        print(f"\\n[Material: {mat.name}]")
        print(f"Found Node: {combine_node.name} ({combine_node.bl_idname})")
        print(f"Active Mode: {combine_node.mode}")
        
        # Print each input socket's state and connection
        for i, socket in enumerate(combine_node.inputs):
            print(f"  * Input[{i}] ({socket.name}):")
            print(f"    - is_linked:     {socket.is_linked}")
            
            # Read direct default value
            val = socket.default_value
            if hasattr(val, "__getitem__"):
                val = list(val)
            print(f"    - default_value: {val}")
            
            if socket.is_linked:
                link = socket.links[0]
                from_node = link.from_node
                print(f"    - Connected to:  {from_node.name} ({from_node.bl_idname})")
                
                if from_node.type == 'RGB':
                    # Print the exact color picker floats (0.0 to 1.0)
                    color_val = list(from_node.outputs[0].default_value)
                    print(f"      -> Color Picker RGBA: {color_val}")
                elif from_node.type == 'TEX_IMAGE':
                    img = from_node.image
                    print(f"      -> Image Name:     {img.name if img else 'None'}")
                    print(f"      -> Image Filepath: {img.filepath if img else 'None'}")
                    if img:
                        print(f"      -> Image Size:     {img.size[0]}x{img.size[1]}")
                        try:
                            # Test if the pixels are readable or uninitialized
                            _ = img.pixels[0]
                            print(f"      -> Pixel Read:     Success (First float: {img.pixels[0]})")
                        except Exception as e:
                            print(f"      -> Pixel Read:     FAILED: {e}")
                            
    if not found_any:
        print("\\nNo materials with a Combine Color node were found in this .blend file.")
    print("\\n" + "=" * 60)

run_diagnostic()
"""

def main():
    settings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "manager_settings.json"))
    if not os.path.exists(settings_path):
        print(f"ERROR: Settings file not found at {settings_path}")
        return

    with open(settings_path, "r") as f:
        settings = json.load(f)

    blender_path = settings.get("blender", "blender")
    fmodel_output = settings.get("fmodel_output", "")
    
    # Prompt for the mod name to inspect (e.g. Eagle)
    mod_name = input("Enter the Mod Name to inspect (e.g., Eagle, FlowerDinosaur): ").strip()
    if not mod_name:
        return

    # Find the .blend file
    blend_file = None
    search_dir = os.path.join(fmodel_output, "Exports", "Pal", "Content", "Pal", "Model", "Character")
    for root, dirs, files in os.walk(search_dir):
        if mod_name in root:
            for f in files:
                if f.lower() == f"{mod_name.lower()}.blend":
                    blend_file = os.path.join(root, f)
                    break
            if blend_file:
                break

    if not blend_file or not os.path.exists(blend_file):
        print(f"ERROR: Could not locate .blend file for {mod_name} in FModel output directories.")
        return

    print(f"Target .blend file found: {blend_file}")
    
    # Execute Blender headlessly with the diagnostics script
    cmd = [
        blender_path,
        "-b",
        blend_file,
        "--python-expr",
        BLENDER_TEST_SCRIPT
    ]
    
    subprocess.run(cmd)

if __name__ == "__main__":
    main()