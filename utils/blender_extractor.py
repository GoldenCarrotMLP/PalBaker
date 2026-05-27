import bpy
import json
import sys
import os
import math
from mathutils import Matrix

def parse_args():
    args = []
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
    
    output_json = "bone_data.json"
    output_fbx = None
    
    for i, arg in enumerate(args):
        if arg == "--output" and i + 1 < len(args):
            output_json = args[i + 1]
        elif arg == "--fbx" and i + 1 < len(args):
            output_fbx = args[i + 1]
            
    return output_json, output_fbx

def process_blender_file(output_json: str, output_fbx: str):
    armature_obj = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            armature_obj = obj
            break
            
    if not armature_obj:
        print("ERROR: No armature found in the Blender file.")
        sys.exit(1)
        
    print(f"Scanning armature: {armature_obj.name}")
    
    jiggle_bones = []
    offset_bones = []
    
    # Coordinate Conversion Matrix: Flips Y axis (Blender Right-Handed to UE Left-Handed)
    swap = Matrix((
        (1,  0,  0, 0),
        (0, -1,  0, 0),
        (0,  0,  1, 0),
        (0,  0,  0, 1)
    ))
    
    for p_bone in armature_obj.pose.bones:
        raw_name = p_bone.name
        ue_bone_name = raw_name.replace('.', '_')
        
        # --- A. CHECK JIGGLE BONES ---
        if raw_name.endswith("_jiggle") or "_phy" in raw_name.lower():
            jiggle_bones.append({
                "bone_name": ue_bone_name,
                "spring_stiffness": 300.0,
                "spring_damping": 8.0,
                "max_displacement": 20.0,
                "error_reset_thresh": 1000.0,
                "limit_displacement": True,
                "translate_x": True,
                "translate_y": True,
                "translate_z": True,
                "rotate_x": True,
                "rotate_y": True,
                "rotate_z": True
            })
            
        # --- B. CHECK OFFSET BONES ---
        matrix_basis = p_bone.matrix_basis
        loc_basis, rot_basis, scale_basis = matrix_basis.decompose()
        
        has_translation = loc_basis.length > 0.0001
        rot_euler = rot_basis.to_euler()
        has_rotation = (abs(rot_euler.x) > 0.0001 or abs(rot_euler.y) > 0.0001 or abs(rot_euler.z) > 0.0001)
        has_scale = (abs(scale_basis.x - 1.0) > 0.0001 or abs(scale_basis.y - 1.0) > 0.0001 or abs(scale_basis.z - 1.0) > 0.0001)
        
        if has_translation or has_rotation or has_scale:
            
            # Extract matrices in Parent Space
            if p_bone.parent:
                l_pose = p_bone.parent.matrix.inverted() @ p_bone.matrix
                l_rest = p_bone.parent.bone.matrix_local.inverted() @ p_bone.bone.matrix_local
            else:
                l_pose = p_bone.matrix
                l_rest = p_bone.bone.matrix_local
                
            # --- TRANSLATION (Simple Vector Difference in Parent Space) ---
            delta_loc = l_pose.translation - l_rest.translation
            ue_translation = [
                round(delta_loc.x, 6),
                round(-delta_loc.y, 6), # Y-flipped for Unreal Space
                round(delta_loc.z, 6)
            ]
            
            # --- ROTATION (Matrix projection to avoid FBX twisted axes) ---
            blender_delta_mat = l_pose @ l_rest.inverted()
            ue_delta_mat = swap @ blender_delta_mat @ swap
            _, rot, _ = ue_delta_mat.decompose()
            
            rot_euler_ue = rot.to_euler('XYZ')
            ue_rotation = [
                round(math.degrees(rot_euler_ue.x), 6),
                round(math.degrees(rot_euler_ue.y), 6),
                round(math.degrees(rot_euler_ue.z), 6)
            ]
            
            # --- SCALE (Replaced in pure Bone Space) ---
            ue_scale = [
                round(scale_basis.x, 6),
                round(scale_basis.y, 6),
                round(scale_basis.z, 6)
            ]
            
            offset_bones.append({
                "bone_name": ue_bone_name,
                "translation": ue_translation,
                "rotation": ue_rotation,
                "scale": ue_scale
            })

    output_data = {
        "jiggle_bones": jiggle_bones,
        "offset_bones": offset_bones
    }
    
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4)
        
    print(f"SUCCESS: Exported {len(jiggle_bones)} jiggle bones and {len(offset_bones)} offset bones to: {output_json}")

    # --- C. EXPORT FBX IN REST POSE ---
    if output_fbx:
        print("Clearing pose transforms to Rest Pose...")
        for p_bone in armature_obj.pose.bones:
            p_bone.matrix_basis = Matrix.Identity(4)
            
        bpy.context.view_layer.update()
        
        abs_fbx = os.path.abspath(output_fbx)
        print(f"Exporting FBX to: {abs_fbx}")
        
        bpy.ops.export_scene.fbx(
            filepath=abs_fbx,
            use_selection=False,
            add_leaf_bones=False,
            mesh_smooth_type='FACE',
            armature_nodetype='ROOT',
            global_scale=0.01,
            apply_scale_options='FBX_SCALE_ALL'
        )
        print("FBX Export Complete.")

if __name__ == "__main__":
    out_json, out_fbx = parse_args()
    process_blender_file(out_json, out_fbx)