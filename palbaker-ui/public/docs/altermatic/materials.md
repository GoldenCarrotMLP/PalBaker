# Material Overrides & Reskins

Material overrides allow you to swap the textures and shaders of specific slots on your Pal's mesh dynamically per variant. This enables lightweight reskins (such as shiny variants, element swaps, or accessory color shifts).

## How to Set Overrides

1. Click on your Altermatic Variant Chip to open the Configurator modal.
2. Scroll down to Section 3: **Visual Material Overrides**.
3. PalBaker will query your sidecar database to display a list of all active material slots present on your mesh (e.g., `Slot 0: mi_body`, `Slot 1: mi_eye`).
4. Select the dropdown for your target slot and choose any compiled Material Instance available in your workspace (e.g., `MI_Drillgame_Body_shiny`).
5. Click **Apply Changes** to serialize.

---

## Registering Custom Textures

To make a completely new material instance available in your dropdown menu:
1. Open your base `.blend` file or your variant's `.blend` file in Blender.
2. Select your mesh, go to the material properties, and assign a new material slot named exactly what you want your new Material Instance to be called (e.g., `MI_PalName_Body_Shiny`).
3. Connect your new `.png` textures to the shader tree in Blender.
4. Hit **SYNC** inside your Altermatic panel. PalBaker will headlessly read your Blender file, update your companion sidecars, and make your new material instantly selectable inside your overrides dropdown!