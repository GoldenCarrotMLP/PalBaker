# Decompiling Existing Mods

The decompiler pipeline is a powerful "round-trip" feature. It allows you to reverse-engineer cooked `.uasset` binaries from your project directory (or an existing mod) back into editable Blender `.blend` workspaces and source `.png` textures.

## When to Use Decompilation

- **Restoring Missing Source Workspaces**:
  If you lost your local `.blend` files but still have the mod compiled in your Unreal project, you can salvage your work cleanly.
  
- **Customizing Other Modders' Work**:
  If you want to edit or customize an existing mod file, you can import its assets into your project, select **Generate Sources**, and PalBaker will rebuild a Blender project for you!

---

## How to Run a Decompile

1. Locate your target Pal mod (ensure it possesses the **UE ASSETS** badge).
2. Click the three-dots overflow menu on the right of the Mod Card and select **Generate Sources**.
3. If an editable workspace already exists on disk, a diagnostic warning will ask if you want to overwrite it. Select confirm if you are sure.
4. PalBaker will:
   - Query your running Unreal Editor to export the mesh as an `.fbx` and dump all texture channels to `.png`.
   - Extract and salvage the material parameters, writing them to `materials_metadata.json`.
   - Headlessly launch Blender to reconstruct a clean `.blend` workspace matching your Unreal materials precisely.