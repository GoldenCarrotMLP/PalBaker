# Restoring Vanilla Audio

If you no longer want to use a custom voice override and wish to revert a Pal's cries back to the standard, built-in game vocals, you can easily perform an audio restoration.

## Reverting to Vanilla

1. Expand your target Pal's Mod Card.
2. Locate the **Cries Replacement** panel.
3. Find the slot showing the yellow **Custom Override** status indicator.
4. Click the red **Trash / Delete** icon on the right-hand side of the slot.
5. Click **Confirm** on the warning prompt.

---

## What the Clean-up Does

When you clear an override, PalBaker executes a clean-up routine on disk:
- It deletes your copied source file (e.g., `sources/Joy.mp3`) from your workspace.
- It deletes the compiled `.wem` file from your `.palbaker_audio/WwiseAudio/Media/` folder.
- When you cook and pack your mod again, the packager will no longer package any custom vocals for that slot, and the game will naturally fall back to playing its original, archived audio assets.