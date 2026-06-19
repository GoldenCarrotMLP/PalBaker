# Cooking & Packing Mods

Cooking is the process of compiling your Unreal Engine development assets into platform-specific, unversioned binary formats. Packing compiles those cooked binaries into a single, compressed archive (`_P.pak`) that the game can read.

## Targeted Micro-Cooking

Standard Unreal Engine cooking compiles your entire project directory, which can take several minutes. PalBaker avoids this by performing **Targeted Micro-Cooking**:

- When you click **Cook & Pack**, PalBaker temporarily backs up and modifies your project's `DefaultGame.ini` config.
- It instructs the Unreal Cooker to restrict compilation *strictly* to your active mod's folders and skeletal directory.
- This reduces cook times from minutes to under 5 seconds!
- Once complete, your original `DefaultGame.ini` is safely restored.

---

## Safe Skeleton Stripping

Shipping custom skeleton (`.uasset`) files in your pak without shipping completely custom animation sets can conflict with the game's native bone controllers, resulting in infinite character stretching, t-poses, or ragdoll crashes in-world.

PalBaker's packager automatically applies **Safe Skeleton Stripping**:
- During packaging, it parses your cooked folders and automatically filters out both your `.uasset` skeleton and your `.uasset` physics assets.
- Your customized meshes are packaged safely while utilizing the game's robust, built-in bone controllers and anims.
- **Exception**: If you have placed custom animation sequences inside your ModKit's animation folder, PalBaker will automatically detect them and include the skeleton assets, allowing you to ship custom movements.