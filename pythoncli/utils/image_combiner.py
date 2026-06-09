import bpy  # type: ignore
import os
import numpy as np  # type: ignore

def build_mrao_texture(combine_node, out_filepath):
    """Packs R, G, B inputs into a single texture file using NumPy."""
    width = 32
    height = 32
    
    # 1. Determine maximum resolution among connected textures
    for i in range(3):
        socket = combine_node.inputs[i]
        if socket.is_linked:
            node = socket.links[0].from_node
            if node.type == 'TEX_IMAGE' and node.image:
                abs_path = bpy.path.abspath(node.image.filepath)
                if os.path.exists(abs_path):
                    # Load a clean temporary image to force Blender to read the dimensions
                    try:
                        temp_img = bpy.data.images.load(abs_path)
                        w, h = temp_img.size
                        width = max(width, w)
                        height = max(height, h)
                        bpy.data.images.remove(temp_img)
                    except Exception:
                        pass
                
    # 2. Extract channel arrays (Metallic, Roughness, AO)
    r_data = _get_socket_data(combine_node.inputs[0], width, height)
    g_data = _get_socket_data(combine_node.inputs[1], width, height)
    b_data = _get_socket_data(combine_node.inputs[2], width, height)
    
    # Alpha channel (1.0)
    a_data = np.ones((height, width), dtype=np.float32)
    
    # Stack arrays: (height, width, 4) -> flatten
    rgba_data = np.dstack((r_data, g_data, b_data, a_data)).flatten()
    
    # Convert to Python list to ensure no C++ memory alignment issues
    pixels_list = rgba_data.tolist()
    
    # 3. Create and Save the Generated Image
    img_name = os.path.basename(out_filepath)
    img = bpy.data.images.get(img_name)
    if not img:
        img = bpy.data.images.new(name=img_name, width=width, height=height, alpha=False, float_buffer=False)
    elif img.size[0] != width or img.size[1] != height:
        img.scale(width, height)
        
    img.pixels.foreach_set(pixels_list) # type: ignore
    
    # Set save settings
    img.filepath_raw = out_filepath
    img.file_format = 'PNG'
    
    # Force write memory pixels to physical disk file
    print(f"Baking texture channels to disk: {out_filepath}")
    img.save_render(out_filepath)
    
    # Clean up the generated memory image
    bpy.data.images.remove(img)
    
    return img_name

def _get_socket_data(socket, target_w, target_h):
    """Extracts pixel data by loading a clean temporary file directly from disk to bypass lazy loading."""
    if socket.is_linked:
        node = socket.links[0].from_node
        if node.type == 'TEX_IMAGE' and node.image:
            abs_path = bpy.path.abspath(node.image.filepath)
            
            if os.path.exists(abs_path):
                try:
                    temp_img = bpy.data.images.load(abs_path)
                    
                    # Force buffer load
                    try:
                        _ = temp_img.pixels[0]# type: ignore
                    except Exception:
                        pass
                        
                    if temp_img.size[0] != target_w or temp_img.size[1] != target_h:
                        temp_img.scale(target_w, target_h)
                        
                    arr = np.empty(target_w * target_h * 4, dtype=np.float32)
                    temp_img.pixels.foreach_get(arr)# type: ignore
                    
                    bpy.data.images.remove(temp_img)
                    
                    arr = arr.reshape((target_h, target_w, 4))
                    return arr[:, :, 0] # Extract Red channel
                except Exception as e:
                    print(f"Warning: Failed to read image file directly: {e}")
            
        elif node.type == 'RGB':
            val = node.outputs[0].default_value[0]
            return np.full((target_h, target_w), val, dtype=np.float32)
            
    # Fallback to direct input value
    val = 0.0
    if type(socket.default_value) is float:
        val = socket.default_value
    elif hasattr(socket.default_value, '__getitem__'):
        val = socket.default_value[0]
        
    return np.full((target_h, target_w), val, dtype=np.float32)