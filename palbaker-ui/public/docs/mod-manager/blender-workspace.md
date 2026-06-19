# Creating Blender Workspaces

To begin customizing a Pal's 3D model, you must create a Blender workspace. PalBaker automates this process by headlessly reconstructing a full `.blend` file from your extracted raw `.psk` and `.json` assets.

## Setting Up Your Workspace

1. Locate a mod marked with the **RAW** badge.
2. Click the primary button: **CREATE .BLEND FILE**.
3. PalBaker will headlessly launch Blender to:
   - Import the raw skeletal mesh `.psk`.
   - Setup and name the parent Armature.
   - Reconstruct all nodes, linking base color, normal, and parameter textures to their respective slot shaders.
   - Generate a companion sidecar `.json` file containing slot topologies.

Once complete, the mod badge changes to **SOURCE**. Click the expand icon and find the **Blender** button to launch your model directly.

---

## 3D Modding Guidelines

When modifying your Pal's mesh in Blender, follow these strict rules to ensure the model compiles and animates correctly in-game:

### Rigging & Bone Parentage
Your mesh must remain parented to the parent armature named exactly `Armature`. Do not rename, delete, or re-parent core skeletal bones, as this will break in-game animations.

### Physics and Jiggle Bones
PalBaker features a C++ rigging pipeline that automatically applies advanced spring node physics to custom bones. To add bouncy ears, tails, or hair:
1. Enter Armature **Edit Mode** and add your custom accessory bones.
2. Rename your custom physics bones to end with these exact suffixes:
   - `_jiggle` or `_phy` (for standard spring physics, useful for ears and accessories).
   - `_hair` (for looser, higher-damping hair simulations).
3. Adjust their transforms in Pose Mode. PalBaker's backend will automatically read these bone structures and wire up spring nodes inside Unreal!