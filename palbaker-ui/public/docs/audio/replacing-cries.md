# Replacing Pal Cries

PalBaker features a dynamic vocal compilation engine that allows you to replace a Pal's standard voice, cries, and grunts with custom audio files on the fly.

## Supported Formats
You can upload custom voice tracks in **WAV**, **MP3**, or **OGG** formats.

---

## How to Replace Cries

1. Expand the target Pal's Mod Card and locate the **Cries Replacement** panel.
2. If your mod is raw, you will need to click **Create .blend file** or **Generate Sources** first so the backend can map the Wwise database.
3. Locate the cry state you wish to replace:
   - **Normal**: Passive ambient overworld sounds.
   - **Joy**: Happy expressions (such as eating or being petted).
   - **Anger**: Spawning or initiating combat.
   - **Sorrow**: Being depressed or neglected.
   - **Pain**: Taking damage in combat.
   - **Death**: Being incapacitated.
4. Click the **Upload** icon on the slot, select your audio file, and confirm.

---

## How it Works Under the Hood

When you confirm an upload, PalBaker executes a background transcoding pipeline:
- If the file is an MP3 or OGG, it is headlessly decoded to an uncompressed WAV using `vgmstream-cli`.
- It invokes your local **Wwise Console** behind the scenes to compile the WAV into a high-fidelity `.wem` file.
- The compiled `.wem` is named exactly after the Pal's Wwise numeric `media_id` (e.g., `424023866.wem`) and staged inside your workspace's `.palbaker_audio` directory.
- During packaging, these `.wem` files are merged into your final `.pak` archive.

To preview your custom sound at any time, simply click the **Play** button next to the slot!