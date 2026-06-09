# utils/blender_utils/adapters_base.py
import bpy  # type: ignore
import os
import math
import re
from . import translator

# --- Shared Low-Level Helpers ---
PHYSICS_BONE_PRESETS = {
    "_jiggle": {
        "spring_stiffness": 300.0, "spring_damping": 8.0, "max_displacement": 20.0, 
        "error_reset_thresh": 1000.0, "limit_displacement": True,
        "translate_x": True, "translate_y": True, "translate_z": True,
        "rotate_x": True, "rotate_y": True, "rotate_z": True, "alpha": 1.0
    },
    "_phy": {
        "spring_stiffness": 300.0, "spring_damping": 8.0, "max_displacement": 20.0, 
        "error_reset_thresh": 1000.0, "limit_displacement": True,
        "translate_x": True, "translate_y": True, "translate_z": True,
        "rotate_x": True, "rotate_y": True, "rotate_z": True, "alpha": 1.0
    },
    "_hair": {
        "spring_stiffness": 300.0, "spring_damping": 20.0, "max_displacement": 20.0, 
        "error_reset_thresh": 1000.0, "limit_displacement": True,
        "translate_x": True, "translate_y": True, "translate_z": True,
        "rotate_x": True, "rotate_y": True, "rotate_z": True, "alpha": 0.5
    }
}

def get_node_image_name(link):
    if link and link[0].from_node.type == 'TEX_IMAGE' and link[0].from_node.image:
        return link[0].from_node.image.name.split(".")[0]
    return None

def create_texture_node(nodes, working_dir, texture_name, loc_x, loc_y, non_color=False):
    tex_node = nodes.new("ShaderNodeTexImage")
    tex_node.location = (loc_x, loc_y)
    if texture_name:
        img_path = os.path.join(working_dir, f"{texture_name}.png")
        if os.path.exists(img_path):
            img = bpy.data.images.get(f"{texture_name}.png") or bpy.data.images.load(img_path)
            if img and img.colorspace_settings:
                if non_color:
                    setattr(img.colorspace_settings, 'name', 'Non-Color')
            tex_node.image = img
    return tex_node

# --- Registered Base Operations ---

@translator.register("clean_scene", (0, 0))
def clean_scene_base():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

@translator.register("ensure_addon_enabled", (4, 2))
def ensure_addon_enabled_v4_2(addon_name: str):
    import addon_utils  # type: ignore
    pkg_id = f"bl_ext.system.{addon_name}"
    
    state = addon_utils.check(pkg_id)
    if state and state[1]:
        print(f"[PalBaker] Addon {pkg_id} is already active.")
        return

    try:
        if hasattr(bpy.ops, "extensions") and hasattr(bpy.ops.extensions, "package_enable"):
            bpy.ops.extensions.package_enable(pkg_id=pkg_id)  # type: ignore
            bpy.ops.wm.save_userpref()
            return
    except Exception:
        pass

    try:
        addon_utils.enable(pkg_id)
        bpy.ops.wm.save_userpref()
    except Exception:
        pass

@translator.register("get_addon_name", (4, 2))
def get_addon_name_v4_2() -> str:
    return "io_scene_psk_psa"

@translator.register("get_addons_list", (4, 2))
def get_addons_list_v4_2() -> str:
    return "bl_ext.system.io_scene_psk_psa"

@translator.register("get_download_url", (4, 2))
def get_download_url_v4_2(version_str: str = "4.2") -> str:
    import urllib.request
    import json
    import ssl
    
    version_parts = version_str.split(".")
    while len(version_parts) < 3:
        version_parts.append("0")
    clean_version = ".".join(version_parts[:3])
    
    url = f"https://extensions.blender.org/api/v1/extensions/?blender_version={clean_version}&platform=windows"
    
    try:
        print(f"[PalBaker] Querying Blender Extensions API: {url}...", flush=True)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))
            for item in data.get("data", []):
                if item.get("id") == "io_scene_psk_psa":
                    archive_url = item.get("archive_url")
                    if archive_url:
                        print(f"[PalBaker] Successfully resolved verified Extensions URL: {archive_url}", flush=True)
                        return archive_url
    except Exception as e:
        print(f"[PalBaker] Warning: Extensions API check failed: {e}", flush=True)
        
    return "https://extensions.blender.org/download/sha256:d89df8bca31a01ebf7cfa0ecb4382cda19c0b17b2b8004f141bf165e63df8e76/add-on-io_scene_psk_psa-v9.1.2.zip"

@translator.register("get_target_addon_directory", (4, 2))
def get_target_addon_directory_v4_2(blender_dir: str, version_str: str, appdata: str) -> str:
    system_path = os.path.join(blender_dir, version_str, "extensions", "system", "io_scene_psk_psa")
    system_version_dir = os.path.join(blender_dir, version_str)
    if os.path.exists(system_path) or (os.path.exists(system_version_dir) and os.access(system_version_dir, os.W_OK)):
        return system_path
    return os.path.join(appdata, "Blender Foundation", "Blender", version_str, "extensions", "user_default", "io_scene_psk_psa")

@translator.register("import_mesh", (0, 0))
def import_mesh_base(file_path: str):
    if file_path.lower().endswith(".psk"):
        resolved_name = translator.execute("get_addon_name")
        translator.ensure_addon_enabled(resolved_name)
        
        try:
            bpy.ops.psk.import_file(filepath=file_path)  # type: ignore
            print(f"[PalBaker] Imported PSK using modern operator: {file_path}")
        except (AttributeError, RuntimeError):
            try:
                import_op_group = getattr(bpy.ops, "import")  # type: ignore
                import_op_group.psk(filepath=file_path)
                print(f"[PalBaker] Imported PSK using legacy 'import.psk' operator: {file_path}")
            except (AttributeError, RuntimeError):
                try:
                    bpy.ops.import_scene.psk(filepath=file_path)  # type: ignore
                    print(f"[PalBaker] Imported PSK using legacy 'import_scene.psk' operator fallback: {file_path}")
                except Exception as e:
                    print(f"[PalBaker] ERROR: Failed to import PSK asset: {e}")
                    raise e
    else:
        bpy.ops.import_scene.fbx(filepath=file_path, ignore_leaf_bones=True, global_scale=100.0)

@translator.register("save_blend", (0, 0))
def save_blend_base(blend_path: str):
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

@translator.register("fix_hierarchy", (0, 0))
def fix_hierarchy_base(armature_name: str = "Armature"):
    for empty in [obj for obj in bpy.data.objects if obj.type == 'EMPTY']:
        for child in list(empty.children):
            world_mat = child.matrix_world.copy()
            child.parent = None
            child.matrix_world = world_mat
        bpy.data.objects.remove(empty, do_unlink=True)
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            obj.name = armature_name
            if obj.data:  # type: ignore
                obj.data.name = armature_name

@translator.register("get_pose_bones_info", (0, 0))
def get_pose_bones_info_base(armature_name: str = "Armature") -> list[dict]:
    from mathutils import Matrix  # type: ignore
    
    arm_obj = bpy.data.objects.get(armature_name)
    if not arm_obj:
        return []
    
    bones_info = []
    swap = Matrix(((1, 0, 0, 0), (0, -1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))

    for p_bone in arm_obj.pose.bones:  # type: ignore
        raw_name = p_bone.name
        ue_bone_name = raw_name.replace('.', '_')
        raw_name_lower = raw_name.lower()
        match_name = re.sub(r'\.\d+$', '', raw_name_lower)

        is_physics = False
        physics_config = {}
        for suffix, preset in PHYSICS_BONE_PRESETS.items():
            if match_name.endswith(suffix):
                physics_config = dict(preset)
                is_physics = True
                break
        
        loc, rot, scale = p_bone.matrix_basis.decompose()
        has_transform = (loc.length > 0.0001 or any(abs(v) > 0.0001 for v in rot.to_euler()) or any(abs(v - 1.0) > 0.0001 for v in scale))
        transform_data = None

        if has_transform:
            l_pose = p_bone.parent.matrix.inverted() @ p_bone.matrix if p_bone.parent else p_bone.matrix
            l_rest = p_bone.parent.bone.matrix_local.inverted() @ p_bone.bone.matrix_local if p_bone.parent else p_bone.bone.matrix_local
            
            delta_loc = l_pose.translation - l_rest.translation
            ue_translation = [round(delta_loc.x, 6), round(-delta_loc.y, 6), round(delta_loc.z, 6)]
            
            blender_delta_mat = l_pose @ l_rest.inverted()
            ue_delta_mat = swap @ blender_delta_mat @ swap
            _, rot_ue, _ = ue_delta_mat.decompose()
            rot_ue_euler = rot_ue.to_euler('XYZ')
            ue_rotation = [round(math.degrees(rot_ue_euler.x), 6), round(math.degrees(rot_ue_euler.y), 6), round(math.degrees(rot_ue_euler.z), 6)]
            ue_scale = [round(scale.x, 6), round(scale.y, 6), round(scale.z, 6)]
            
            transform_data = {
                "translation": ue_translation,
                "rotation": ue_rotation,
                "scale": ue_scale
            }

        bones_info.append({
            "bone_name": ue_bone_name,
            "raw_name": raw_name,
            "is_physics": is_physics,
            "physics_config": physics_config,
            "transform_data": transform_data
        })
    return bones_info

@translator.register("get_skeletal_mesh_material_slots", (0, 0))
def get_skeletal_mesh_material_slots_base() -> list[str]:
    mesh_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    slots_in_order = []
    for obj in mesh_objs:
        for slot in obj.material_slots:
            if slot.material and slot.material.name not in slots_in_order:
                slots_in_order.append(slot.material.name)
    for mat in bpy.data.materials:
        if mat.name not in slots_in_order:
            slots_in_order.append(mat.name)
    return slots_in_order

@translator.register("connect_mix_nodes", (0, 0))
def connect_mix_nodes_base(nodes, links, base_tex_output, blue_channel_output, base_color_socket):
    mix_node = nodes.new("ShaderNodeMix")
    mix_node.data_type = 'RGBA'
    mix_node.blend_type = 'MULTIPLY'
    mix_node.inputs["Factor"].default_value = 1.0
    mix_node.location = (-400, 200)
    
    if base_color_socket:
        links.new(mix_node.outputs["Result"], base_color_socket)
    if base_tex_output:
        links.new(base_tex_output, mix_node.inputs["A"])
    if blue_channel_output:
        links.new(blue_channel_output, mix_node.inputs["B"])
    return mix_node

@translator.register("compile_material_instance", (0, 0))
def compile_material_instance_base(mat_name: str, parent_class: str, params: dict, working_dir: str):
    mat = bpy.data.materials.get(mat_name)
    if not mat: return
    
    mat.use_nodes = True
    if mat.node_tree:  # type: ignore
        nodes = mat.node_tree.nodes  # type: ignore
        links = mat.node_tree.links  # type: ignore
    else:
        return
    nodes.clear()

    output_node = nodes.new("ShaderNodeOutputMaterial")
    output_node.location = (300, 100)
    
    bsdf_node = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf_node.location = (-100, 100)
    links.new(bsdf_node.outputs["BSDF"], output_node.inputs["Surface"])

    base_color_socket = translator.execute("get_bsdf_socket", bsdf_node, "base_color")
    metallic_socket = translator.execute("get_bsdf_socket", bsdf_node, "metallic")
    roughness_socket = translator.execute("get_bsdf_socket", bsdf_node, "roughness")
    normal_socket = translator.execute("get_bsdf_socket", bsdf_node, "normal")
    subsurface_socket = translator.execute("get_bsdf_socket", bsdf_node, "subsurface_radius")
    emission_color_socket = translator.execute("get_bsdf_socket", bsdf_node, "emission_color")
    emission_strength_socket = translator.execute("get_bsdf_socket", bsdf_node, "emission_strength")
    alpha_socket = translator.execute("get_bsdf_socket", bsdf_node, "alpha")

    tex_base_name = params.get("Base Texture")
    is_transparent = "eye" in parent_class.lower() or "mouth" in parent_class.lower() or "eye" in mat_name.lower() or "mouth" in mat_name.lower()
    
    if is_transparent:
        mat.blend_method = 'HASHED'
        if tex_base_name:
            base_tex = create_texture_node(nodes, working_dir, tex_base_name, -500, 100)
            if base_color_socket: links.new(base_tex.outputs["Color"], base_color_socket)
            if alpha_socket: links.new(base_tex.outputs["Alpha"], alpha_socket)
        return

    base_tex_output = None
    if tex_base_name:
        base_tex = create_texture_node(nodes, working_dir, tex_base_name, -800, 300)
        base_tex_output = base_tex.outputs["Color"]

    tex_mrao_name = params.get("MetallicRoughnessOcclusionSpecularTexture")
    sep_color = nodes.new("ShaderNodeSeparateColor")
    sep_color.mode = 'RGB'  # type: ignore
    sep_color.location = (-800, 0)
    
    if metallic_socket: links.new(sep_color.outputs["Red"], metallic_socket)
    if roughness_socket: links.new(sep_color.outputs["Green"], roughness_socket)
    
    if tex_mrao_name:
        mrao_tex = create_texture_node(nodes, working_dir, tex_mrao_name, -1200, 0, non_color=True)
        links.new(mrao_tex.outputs["Color"], sep_color.inputs["Color"])
    else:
        combine_node = nodes.new("ShaderNodeCombineColor")
        combine_node.mode = 'RGB'  # type: ignore
        combine_node.location = (-1200, 0)
        
        color_r = nodes.new("ShaderNodeRGB")
        color_r.location = (-1500, 100)
        color_r.outputs[0].default_value = (0.0, 0.0, 0.0, 1.0)  # type: ignore
        
        color_g = nodes.new("ShaderNodeRGB")
        color_g.location = (-1500, -100)
        color_g.outputs[0].default_value = (0.5, 0.5, 0.5, 1.0)  # type: ignore
        
        color_b = nodes.new("ShaderNodeRGB")
        color_b.location = (-1500, -300)
        color_b.outputs[0].default_value = (1.0, 1.0, 1.0, 1.0)  # type: ignore
        
        links.new(color_r.outputs[0], combine_node.inputs["Red"])
        links.new(color_g.outputs[0], combine_node.inputs["Green"])
        links.new(color_b.outputs[0], combine_node.inputs["Blue"])
        links.new(combine_node.outputs["Color"], sep_color.inputs["Color"])

        # --- DYNAMICALLY BAKE AND CONNECT COMBINED CHANNELS TO DISK AND SHADER TREE ---
        try:
            from image_combiner import build_mrao_texture
            mrao_filename = f"T_{mat_name}_M"
            out_filepath = os.path.join(working_dir, f"{mrao_filename}.png")
            
            print(f"[PalBaker] Baking combined MRAO channels to: {out_filepath}", flush=True)
            build_mrao_texture(combine_node, out_filepath)
            
            # Replace combine network with baked texture node
            nodes.remove(color_r)
            nodes.remove(color_g)
            nodes.remove(color_b)
            nodes.remove(combine_node)
            
            mrao_tex = create_texture_node(nodes, working_dir, mrao_filename, -1200, 0, non_color=True)
            links.new(mrao_tex.outputs["Color"], sep_color.inputs["Color"])
            
            # Add to params so downstream unreal import logic picks up on it
            params["MetallicRoughnessOcclusionSpecularTexture"] = mrao_filename
        except Exception as e:
            print(f"[PalBaker Warning] Failed to bake combined MRAO texture: {e}", flush=True)

    mix_node = translator.execute(
        "connect_mix_nodes", 
        nodes, 
        links, 
        base_tex_output, 
        sep_color.outputs["Blue"], 
        base_color_socket
    )

    tex_norm_name = params.get("Normal Map")
    if tex_norm_name and normal_socket:
        norm_tex = create_texture_node(nodes, working_dir, tex_norm_name, -800, -300, non_color=True)
        norm_map = nodes.new("ShaderNodeNormalMap")
        norm_map.location = (-400, -300)
        if hasattr(norm_map, "convention"):
            norm_map.convention = 'DIRECTX'  # type: ignore
        links.new(norm_map.outputs["Normal"], normal_socket)
        links.new(norm_tex.outputs["Color"], norm_map.inputs["Color"])

    tex_sss_name = params.get("Subsurface Texture")
    if tex_sss_name and subsurface_socket:
        sss_tex = create_texture_node(nodes, working_dir, tex_sss_name, -400, -600)
        links.new(sss_tex.outputs["Color"], subsurface_socket)

    tex_em_name = params.get("Emissive Texture")
    if tex_em_name and emission_color_socket:
        em_tex = create_texture_node(nodes, working_dir, tex_em_name, -800, -600)
        links.new(em_tex.outputs["Color"], emission_color_socket)
        if emission_strength_socket:
            emission_strength_socket.default_value = 1.0

@translator.register("export_fbx", (0, 0))
def export_fbx_base(fbx_path: str, armature_name: str = "Armature"):
    from mathutils import Matrix  # type: ignore
    
    arm_obj = bpy.data.objects.get(armature_name)
    if arm_obj:
        print("Restoring bones to T-pose before export...")
        for p_bone in arm_obj.pose.bones:  # type: ignore
            p_bone.matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()  # type: ignore
    
    bpy.ops.export_scene.fbx(
        filepath=os.path.abspath(fbx_path),
        use_selection=False,
        add_leaf_bones=False,
        mesh_smooth_type='FACE',
        armature_nodetype='ROOT',
        global_scale=0.01,
        apply_scale_options='FBX_SCALE_ALL'
    )

# --- ADDED INTERACTIVE SHADER ADAPTERS ---

@translator.register("get_bsdf_socket", (4, 0))
def get_bsdf_socket_v4(bsdf_node, role: str):
    """Blender 4.0+ Principled BSDF socket resolver."""
    mapping = {
        "base_color": "Base Color",
        "subsurface_weight": "Subsurface Weight",
        "subsurface_radius": "Subsurface Radius",
        "metallic": "Metallic",
        "roughness": "Roughness",
        "specular": "Specular IOR Level",
        "normal": "Normal",
        "emission_color": "Emission Color",
        "emission_strength": "Emission Strength",
        "coat_weight": "Coat Weight",
        "alpha": "Alpha"
    }
    socket_name = mapping.get(role)
    if not socket_name or not bsdf_node:
        return None
    return bsdf_node.inputs.get(socket_name)

@translator.register("get_material_textures", (0, 0))
def get_material_textures_base(mat_name: str) -> dict:
    """
    Recursively walks through active material shader nodes inside Blender 
    to extract currently bound texture parameters for Unreal mapping.
    """
    mat = bpy.data.materials.get(mat_name)
    if not mat or not mat.use_nodes:
        return {}
        
    textures = {}
    nodes = mat.node_tree.nodes  # type: ignore
    links = mat.node_tree.links  # type: ignore
    
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf:
        # --- AUTO-BAKE MRAO CHANNELS ON-THE-FLY IF DETECTED ---
        metallic_socket = translator.execute("get_bsdf_socket", bsdf, "metallic")
        if metallic_socket and metallic_socket.is_linked:
            sep_node = metallic_socket.links[0].from_node
            if sep_node.type in ['SEPARATE_COLOR', 'SEPARATE_RGB']:
                color_socket = sep_node.inputs.get("Color") or sep_node.inputs.get("Image")
                if color_socket and color_socket.is_linked:
                    combine_node = color_socket.links[0].from_node
                    if combine_node.type in ['COMBINE_COLOR', 'COMBINE_RGB']:
                        blend_path = bpy.data.filepath
                        if blend_path:
                            working_dir = os.path.dirname(blend_path)
                            try:
                                from image_combiner import build_mrao_texture
                                mrao_filename = f"T_{mat_name}_M"
                                out_filepath = os.path.join(working_dir, f"{mrao_filename}.png")
                                
                                print(f"[PalBaker] Auto-baking combined MRAO channels during export to: {out_filepath}", flush=True)
                                build_mrao_texture(combine_node, out_filepath)
                                
                                # Replace combine network with baked texture node
                                nodes_to_remove = [combine_node]
                                for input_socket in combine_node.inputs:
                                    if input_socket.is_linked:
                                        input_node = input_socket.links[0].from_node
                                        if input_node.type == 'RGB':
                                            nodes_to_remove.append(input_node)
                                            
                                for node in nodes_to_remove:
                                    try: nodes.remove(node)
                                    except Exception: pass
                                    
                                mrao_tex = create_texture_node(nodes, working_dir, mrao_filename, -1200, 0, non_color=True)
                                links.new(mrao_tex.outputs["Color"], sep_node.inputs["Color"])
                                
                                print(f"[PalBaker] Successfully baked and connected MRAO texture: {mrao_filename}", flush=True)
                            except Exception as e:
                                print(f"[PalBaker Warning] Auto-baking MRAO failed: {e}", flush=True)

        def trace_texture(socket):
            if not socket or not socket.is_linked:
                return None
            
            link = socket.links[0]
            from_node = link.from_node
            
            if from_node.type == 'NORMAL_MAP':
                color_socket = from_node.inputs.get("Color")
                if color_socket and color_socket.is_linked:
                    from_node = color_socket.links[0].from_node
            
            elif from_node.type in ['SEPARATE_COLOR', 'SEPARATE_RGB']:
                color_socket = from_node.inputs.get("Color") or from_node.inputs.get("Image")
                if color_socket and color_socket.is_linked:
                    from_node = color_socket.links[0].from_node
                    
            elif from_node.type in ['MIX', 'MIX_RGB']:
                for input_name in ["A", "B", "Color1", "Color2"]:
                    input_socket = from_node.inputs.get(input_name)
                    if input_socket and input_socket.is_linked:
                        potential_node = input_socket.links[0].from_node
                        if potential_node.type == 'TEX_IMAGE' and potential_node.image:
                            return potential_node.image.name.split(".")[0]

            if from_node.type == 'TEX_IMAGE' and from_node.image:
                return from_node.image.name.split(".")[0]
            return None

        base_socket = translator.execute("get_bsdf_socket", bsdf, "base_color")
        base_tex = trace_texture(base_socket)
        if base_tex:
            textures["Base Texture"] = base_tex

        normal_socket = translator.execute("get_bsdf_socket", bsdf, "normal")
        normal_tex = trace_texture(normal_socket)
        if normal_tex:
            textures["Normal Map"] = normal_tex

        metallic_socket = translator.execute("get_bsdf_socket", bsdf, "metallic")
        mrao_tex = trace_texture(metallic_socket)
        if not mrao_tex:
            roughness_socket = translator.execute("get_bsdf_socket", bsdf, "roughness")
            mrao_tex = trace_texture(roughness_socket)
        if mrao_tex:
            textures["MetallicRoughnessOcclusionSpecularTexture"] = mrao_tex

        emissive_socket = translator.execute("get_bsdf_socket", bsdf, "emission_color")
        emissive_tex = trace_texture(emissive_socket)
        if emissive_tex:
            textures["Emissive Texture"] = emissive_tex

        sss_socket = translator.execute("get_bsdf_socket", bsdf, "subsurface_radius")
        sss_tex = trace_texture(sss_socket)
        if sss_tex:
            textures["Subsurface Texture"] = sss_tex

    non_base_suffixes = ["_n", "_normal", "_m", "_s", "_specular", "_param", "_mrao", "_ao", "_em", "_emissive", "_rgn"]
    for node in nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            img_name = node.image.name.split(".")[0]
            img_name_lower = img_name.lower()
            
            if "Base Texture" not in textures:
                if any(img_name_lower.endswith(s) for s in ["_b", "_d", "_albedo", "_basecolor"]) or not any(img_name_lower.endswith(s) for s in non_base_suffixes):
                    textures["Base Texture"] = img_name
            if "Normal Map" not in textures and any(img_name_lower.endswith(s) for s in ["_n", "_normal"]):
                textures["Normal Map"] = img_name
            if "MetallicRoughnessOcclusionSpecularTexture" not in textures and any(img_name_lower.endswith(s) for s in ["_m", "_s", "_specular", "_param", "_mrao"]):
                textures["MetallicRoughnessOcclusionSpecularTexture"] = img_name
            if "Emissive Texture" not in textures and any(img_name_lower.endswith(s) for s in ["_em", "_emissive"]):
                textures["Emissive Texture"] = img_name
            if "Subsurface Texture" not in textures and any(img_name_lower.endswith(s) for s in ["_sss", "_subsurface"]):
                textures["Subsurface Texture"] = img_name

    return textures