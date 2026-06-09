import os
import sys
import json
import subprocess

BLENDER_TEST_SCRIPT = """import bpy
import os
import sys
import numpy as np
from mathutils import Matrix

def _get_socket_data(socket, target_w, target_h):
    if socket.is_linked:
        node = socket.links[0].from_node
        if node.type == 'TEX_IMAGE' and node.image:
            img = node.image
            try:
                _ = img.pixels[0]
            except Exception:
                pass
            
            if img.size[0] != target_w or img.size[1] != target_h:
                temp = img.copy()
                temp.scale(target_w, target_h)
                try:
                    _ = temp.pixels[0]
                except Exception:
                    pass
                arr = np.empty(target_w * target_h * 4, dtype=np.float32)
                temp.pixels.foreach_get(arr)
                bpy.data.images.remove(temp)
            else:
                arr = np.empty(target_w * target_h * 4, dtype=np.float32)
                img.pixels.foreach_get(arr)
                
            arr = arr.reshape((target_h, target_w, 4))
            return arr[:, :, 0]
        elif node.type == 'RGB':
            val = node.outputs[0].default_value[0]
            return np.full((target_h, target_w), val, dtype=np.float32)
            
    val = 0.0
    if type(socket.default_value) is float:
        val = socket.default_value
    elif hasattr(socket.default_value, '__getitem__'):
        val = socket.default_value[0]
    return np.full((target_h, target_w), val, dtype=np.float32)

def run_test_save():
    print("\\n" + "=" * 60)
    print("=== STANDALONE BAKE TEST ===")
    print("=" * 60)
    
    mat = bpy.data.materials.get("MI_Body")
    if not mat or not mat.use_nodes:
        print("ERROR: MI_Body material not found or not using nodes.")
        return
        
    combine_node = next((n for n in mat.node_tree.nodes if n.type == 'COMBINE_COLOR'), None)
    if not combine_node:
        print("ERROR: No Combine Color node found in MI_Body.")
        return

    # Set dimensions to 32x32 for test
    width = 32
    height = 32
    
    r_data = _get_socket_data(combine_node.inputs[0], width, height)
    g_data = _get_socket_data(combine_node.inputs[1], width, height)
    b_data = _get_socket_data(combine_node.inputs[2], width, height)
    a_data = np.ones((height, width), dtype=np.float32)
    
    # Stack channels into RGBA
    rgba_data = np.dstack((r_data, g_data, b_data, a_data)).flatten()
    
    print(f"NumPy Stacked Array Size: {rgba_data.size} floats (Expected: 4096)")
    print(f"First pixel (R, G, B, A): {list(rgba_data[:4])}")
    print(f"Last pixel  (R, G, B, A): {list(rgba_data[-4:])}")
    
    # Convert to Python list to ensure no data alignments issue in C++ wrapper
    pixels_list = rgba_data.tolist()
    
    # Save image
    out_filepath = os.path.abspath("M_texture_result_test.png")
    img_name = "M_texture_result_test.png"
    
    img = bpy.data.images.get(img_name)
    if not img:
        img = bpy.data.images.new(name=img_name, width=width, height=height, alpha=False, float_buffer=False)
        
    img.pixels.foreach_set(pixels_list)
    img.filepath_raw = out_filepath
    img.file_format = 'PNG'
    
    print(f"Saving test image using save_render() to: {out_filepath}")
    img.save_render(out_filepath)
    bpy.data.images.remove(img)
    
    if os.path.exists(out_filepath):
        print(f"SUCCESS: Physical image file created at {out_filepath}")
        print(f"File Size on disk: {os.path.getsize(out_filepath)} bytes")
    else:
        print("ERROR: File was not written to disk.")
        
    print("=" * 60 + "\\n")

run_test_save()
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
    
    blend_file = None
    search_dir = os.path.join(fmodel_output, "Exports", "Pal", "Content", "Pal", "Model", "Character")
    for root, dirs, files in os.walk(search_dir):
        if "Eagle" in root:
            for f in files:
                if f.lower() == "eagle.blend":
                    blend_file = os.path.join(root, f)
                    break
            if blend_file:
                break

    if not blend_file or not os.path.exists(blend_file):
        print("ERROR: Could not find Eagle.blend")
        return

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