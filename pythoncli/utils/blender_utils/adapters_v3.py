# utils/blender_utils/adapters_v3.py
import bpy  # type: ignore
import os
from . import translator

@translator.register("ensure_addon_enabled", (0, 0))
def ensure_addon_enabled_legacy(addon_name: str):
    """
    Legacy Blender (< 4.2) Addon enabler.
    Directly activates pre-staged addons.
    """
    import addon_utils  # type: ignore
    resolved_name = translator.execute("get_addon_name")
    
    state = addon_utils.check(resolved_name)
    if state and state[1]:
        print(f"[PalBaker] Addon {resolved_name} is already active.")
        return
        
    try:
        addon_utils.enable(resolved_name)
        bpy.ops.wm.save_userpref()
        print(f"[PalBaker] Successfully activated legacy addon: {resolved_name}")
    except Exception as e:
        print(f"[PalBaker] Warning: Failed to enable legacy addon {resolved_name}: {e}")

@translator.register("get_bsdf_socket", (3, 0))
def get_bsdf_socket_v3(bsdf_node, role: str):
    """Blender 3.x Principled BSDF socket resolver."""
    mapping = {
        "base_color": "Base Color",
        "subsurface_weight": "Subsurface",                          # Differs in 3.x
        "subsurface_radius": "Subsurface Radius",
        "metallic": "Metallic",
        "roughness": "Roughness",
        "specular": "Specular",                                      # Differs in 3.x
        "normal": "Normal",
        "emission_color": "Emission",                                # Differs in 3.x
        "emission_strength": "Emission Strength",
        "coat_weight": "Clearcoat",                                  # Differs in 3.x
        "alpha": "Alpha"
    }
    
    socket_name = mapping.get(role)
    if not socket_name or not bsdf_node:
        return None
    return bsdf_node.inputs.get(socket_name)

@translator.register("connect_mix_nodes", (3, 0))
def connect_mix_nodes_v3(nodes, links, base_tex_output, blue_channel_output, base_color_socket):
    """
    Legacy Blender < 3.4 MixRGB Node binder.
    Utilizes legacy ShaderNodeMixRGB with corresponding socket connections (Color1, Color2, Color).
    """
    mix_node = nodes.new("ShaderNodeMixRGB")
    mix_node.blend_type = 'MULTIPLY'
    mix_node.inputs["Fac"].default_value = 1.0
    mix_node.location = (-400, 200)
    
    if base_color_socket:
        links.new(mix_node.outputs["Color"], base_color_socket)
    if base_tex_output:
        links.new(base_tex_output, mix_node.inputs["Color1"])
    if blue_channel_output:
        links.new(blue_channel_output, mix_node.inputs["Color2"])
    return mix_node

@translator.register("get_addon_name", (0, 0))
def get_addon_name_legacy() -> str:
    return "io_import_scene_unreal_psa_psk"

@translator.register("get_addon_name", (3, 4))
def get_addon_name_v3_4() -> str:
    return "io_scene_psk_psa"

@translator.register("get_addons_list", (0, 0))
def get_addons_list_legacy() -> str:
    return "io_scene_psk_psa"

# FIXED: Refactored legacy parameters signatures to accept the version_str string variable
@translator.register("get_download_url", (0, 0))
def get_download_url_legacy(version_str: str = "3.3") -> str:
    return "https://github.com/DarklightGames/io_scene_psk_psa/releases/download/4.3.0/io_scene_psk_psa-master-4.3.0.zip"

@translator.register("get_download_url", (3, 4))
def get_download_url_v3_4(version_str: str = "3.6") -> str:
    return "https://github.com/DarklightGames/io_scene_psk_psa/releases/download/5.0.6/io_scene_psk_psa-master-5.0.6.zip"

@translator.register("get_download_url", (4, 0))
def get_download_url_v4_0(version_str: str = "4.0") -> str:
    return "https://github.com/DarklightGames/io_scene_psk_psa/releases/download/6.2.1/io_scene_psk_psa-master-6.2.1.zip"

@translator.register("get_download_url", (4, 1))
def get_download_url_v4_1(version_str: str = "4.1") -> str:
    return "https://github.com/DarklightGames/io_scene_psk_psa/releases/download/7.0.0/io_scene_psk_psa-master-7.0.0.zip"

@translator.register("get_target_addon_directory", (0, 0))
def get_target_addon_directory_legacy(blender_dir: str, version_str: str, appdata: str) -> str:
    system_path = os.path.join(blender_dir, version_str, "scripts", "addons", "io_scene_psk_psa")
    system_version_dir = os.path.join(blender_dir, version_str)
    if os.path.exists(system_path) or (os.path.exists(system_version_dir) and os.access(system_version_dir, os.W_OK)):
        return system_path
    return os.path.join(appdata, "Blender Foundation", "Blender", version_str, "scripts", "addons", "io_scene_psk_psa")