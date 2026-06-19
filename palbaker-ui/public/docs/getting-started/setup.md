# Initial Setup & Paths

Before utilizing PalBaker's automation features, you must configure your workspace paths so the toolchain can locate your external game files, compiler binaries, and Unreal project directories.

## Required Environment Paths

Go to the **System Settings** tab to set up the following directories:

- **Workspace Root (FModel Output)**:
  This must point to your FModel output folder. FModel is used to extract game files. Specifically, PalBaker expects to find your exported assets under this directory in the path:
  \`Exports/Pal/Content/\`

- **Unreal Engine Root**:
  Point this to your Unreal Engine 5.1 directory (e.g., \`C:\\Program Files\\Epic Games\\UE_5.1\`). This is required so PalBaker can invoke the Unreal Cooker and packaging tools (\`UnrealPak.exe\`).

- **.uproject File Path**:
  The absolute path to your active ModKit \`.uproject\` file. This project acts as your development staging ground where mesh and material compilations are performed.

- **Blender Executable**:
  The absolute path to your \`blender.exe\`. Blender is launched headlessly by PalBaker to automate mesh processing, bone rigging, and FBX generation.

- **Palworld.exe Path**:
  Point this to your main game executable (usually located under your Steam library at \`Steam/steamapps/common/Palworld/Palworld.exe\`). This is used to automatically deploy built pak files and Altermatic configurations directly into your active game directory.

---

## Auto-Detecting Paths

If your software is installed in default system directories, click the **Auto-detect Paths** button at the top-right of the System Settings page. PalBaker will scan your drive letters, Steam libraries, and registry paths to automatically resolve your game, Blender, and Unreal Engine paths.