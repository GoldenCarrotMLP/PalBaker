# Cloning & Instantiating Standalone Pals

The Pal Creator tab allows you to create completely brand-new, standalone Pal species—fully patched with unique stats, elements, wild spawners, and custom learnsets—without replacing any of the game's existing vanilla characters.

## Creating a Standalone Pal

1. Navigate to the **Pal Creator** tab.
2. Click the **New Pal** button on the top-right.
3. Configure the following parameters:
   - **New Standalone Pal ID**: A unique, alphanumeric identifier (e.g., \`ShadowAnubis\` or \`Furret\`). Do not use spaces or special characters.
   - **Parent Template to Clone**: Select a vanilla Pal species to copy as your base template (e.g., \`Anubis\`).
4. Click **Create Pal**.

---

## Under the Hood: Automated Patching

When you click Create, PalBaker executes a multi-step patching pipeline in the background:
- It copies the parent's base stats, typing, and skeletal layouts.
- It headlessly invokes **UAssetGUI** to decompile and patch the parent's native `.uasset` blueprint code.
- It applies lookbehind regex rules to rename internal class mappings from the parent (e.g., `BP_Anubis`) to your new Pal (e.g., `BP_ShadowAnubis`) while strictly preserving animation blueprint (`ABP`) links so your custom Pal animates correctly!
- It generates a modular **PalSchema** JSON directory and deploys it to your game's UE4SS folder to dynamically inject your new species ID into the game engine at runtime.