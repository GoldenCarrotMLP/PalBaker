# Extracting Game Assets

PalBaker is designed to build custom mods directly on top of vanilla game assets. To begin modding a Pal, you must first extract its raw models, material parameters, and textures from the Palworld game archives.

## The Extraction Workflow

1. Navigate to the **Mod Manager** tab.
2. If your workspace is empty, select the **Unextracted** preset filter at the top. This will display a comprehensive list of all vanilla Pals registered in the game archives.
3. Find the target Pal you wish to customize and click the red **EXTRACT PAL** button.

---

## What Happens Under the Hood

When you click Extract, PalBaker headlessly invokes the `cue4parse` extractor to dump the target Pal's assets from your game's `.pak` files directly into your FModel Workspace:

- **Skeletal Mesh**: The `.psk` skeletal mesh file containing the character's geometry and bone structures.
- **Textures**: All dependent base colors (`_B`), normal maps (`_N`), and parameter maps (`_M`) are extracted and converted to standard `.png` images.
- **Material Topology**: Parses the game's compiled `.uasset` material instances and writes them to a readable `.json` topology map so Blender and Unreal know exactly how to hook up parameters.
- **Wwise Audio**: Detects the Pal's vocal events and maps them to their respective numeric Wwise IDs.

Once completed, the Pal's status will update to **RAW** (indicating assets are ready but a Blender workspace has not yet been established).