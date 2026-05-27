import bpy
import sys
import os

def parse_args():
    """Parses command-line arguments passed after the double dash '--' in Blender."""
    args = []
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
    
    fbx_path = None
    blend_path = None
    for i, arg in enumerate(args):
        if arg == "--fbx" and i + 1 < len(args):
            fbx_path = args[i + 1]
        elif arg == "--output" and i + 1 < len(args):
            blend_path = args[i + 1]
    return fbx_path, blend_path

def reconstruct_blend(fbx_path, blend_path):
    if not fbx_path or not os.path.exists(fbx_path):
        print(f"ERROR: FBX file not found at {fbx_path}")
        sys.exit(1)

    # 1. Reset to a completely empty factory scene (no default cube, camera, or light)
    print("Resetting scene to empty factory defaults...")
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # 2. Import FBX (disabling leaf bones to keep the hierarchy clean)
    print(f"Importing FBX: {fbx_path}")
    bpy.ops.import_scene.fbx(
        filepath=fbx_path,
        ignore_leaf_bones=True,  # Suppress dummy leaf bones to maintain clean rigging
        global_scale=100.0       # FIXED: Scale Unreal's 1x export up to Palworld's standard 100x Blender scale
    )

    # 3. Save Mainfile natively
    print(f"Saving .blend file to: {blend_path}")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print("BLEND Reconstruction Complete.")

if __name__ == "__main__":
    fbx, blend = parse_args()
    reconstruct_blend(fbx, blend)