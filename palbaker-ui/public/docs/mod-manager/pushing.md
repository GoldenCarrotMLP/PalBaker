# Pushing to Unreal Engine

Once you have customized your Pal's 3D model, textures, or skeletal bone configurations in Blender, you must import them into Unreal Engine. PalBaker automates this entire process using a remote execution live link handshake.

## Executing the Push

1. Open your configured Unreal Engine project in the background.
2. Inside PalBaker, click the **PUSH TO UNREAL** button on the Mod Card.
3. PalBaker will perform the following actions headlessly:
   - Export your customized mesh as a game-ready `.fbx`.
   - Connect to your running Unreal Editor via UDP remote execution.
   - Auto-import your textures and meshes into your project content folder.
   - Instantiation of all material instances, linking textures to their correct shader slots.
   - Invoke our custom C++ plugin (`PalBakerEditorUtils`) to programmatically build an AnimBP from scratch, wire up spring nodes for your custom jiggle bones, and bind the compiled class to your skeletal mesh's Post-Process slot.

---

## Shader Preservation

By default, pushing a mod will overwrite your project's material instances to align with the Blender shader tree. 

If you have performed custom material adjustments inside Unreal Engine (such as custom shading nodes, colors, or scalar parameters) that you do not want to lose:
1. Click the expand arrow on the Mod Card.
2. Toggle **PRESERVE SHADERS** to **ON**.

This will instruct the importer to parse and cache your custom material parameters, only updating the underlying skeletal mesh geometry without resetting your custom Unreal shaders.