# Creating Altermatic Variants

Creating an Altermatic variant workspace is fully automated inside PalBaker. You can choose to create material-only reskins (extremely lightweight) or copy complete skeletons to build custom geometries.

## Step-by-Step Variant Creation

1. Expand the Mod Card of an extracted Pal.
2. Locate the **Altermatic Variants** panel on the right and toggle **ENABLE** to active.
3. Click the **ADD VARIANT** button to open the creation modal.
4. Configure the following properties:
   - **New Variant Name**: A descriptive label (e.g., `Shiny` or `Winter_Coat`).
   - **Custom Model Blend**: 
     - **Toggle ON**: Creates a brand-new, independent `.blend` file on disk. Use this if you want to modify the actual 3D geometry of this variant in Blender.
     - **Toggle OFF**: Shares the base skeleton mesh. Use this if you are only creating a texture/material reskin of the base model.
   - **Clone Skeleton Template**: If Custom Model is enabled, choose which of your existing variants to copy as your starting 3D geometry template.
5. Click **Create** to compile the variant.

---

## Deleting Variants

If you want to remove a variant:
1. Click on the Variant Chip to open the Configurator modal.
2. Click the red **Delete Variant** button at the bottom-left.
3. Confirming this will prune the variant from your `_altermatic.json` manifest and permanently delete its custom `.blend` model from your disk.