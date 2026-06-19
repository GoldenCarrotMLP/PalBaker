# Understanding Status Badges

PalBaker tracks the lifecycle of your mods in real-time by scanning your folders and comparing file states. Status badges are displayed on each Mod Card to help you understand what stage your mod is in and prevent you from accidentally overwriting your work.

## Core Status Badges

- **UNEXTRACTED (Red)**:
  This Pal's files reside purely inside your game's compressed archives. You must click the primary button to extract them before you can begin modding.

- **RAW (Dark Gray)**:
  Vanilla game assets have been successfully dumped, but no editable Blender workspace (`.blend`) file exists yet. Click **Create .blend file** to set up your 3D environment.

- **SOURCE (Blue)**:
  An active Blender workspace (`.blend`) file has been detected. This indicates you are currently editing or customizing the 3D model.

- **UE ASSETS (Orange)**:
  Your customized assets have been successfully imported and reside inside your active Unreal Engine project directory.

---

## Warning & Synchronization Badges

- **MODIFIED (Red Warning)**:
  Manual edits (like shader changes or node re-wiring) have been detected inside your Unreal Engine editor since your last model push. Pushing from Blender again will overwrite these changes unless you enable **Preserve Shaders**.

- **SRC CHANGED (Dark Blue)**:
  Your local 3D workspace (Blender files or texture maps) has been updated since your last push to Unreal Engine. It is recommended to trigger **Push & Cook & Pack** to sync these changes.

- **ALTERMATIC (Teal)**:
  Dynamic Altermatic variants are configured and active for this Pal. This indicates the Pal has custom dynamic skins, genders, or morphs enabled.