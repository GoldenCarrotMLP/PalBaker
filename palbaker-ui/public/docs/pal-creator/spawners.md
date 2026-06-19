# Configuring Wild Spawners

To make your custom standalone Pal obtainable without using admin console spawn commands, you can configure them to spawn dynamically in the wild alongside vanilla species.

## Configuring Spawn Logic

Scroll to the Spawners panel inside your custom Pal's card and configure these parameters:

- **Spawner Location ID**: Select which wild spawner pool your Pal belongs to (e.g., selecting `1_10_plain_F_Boss_Anubis` will spawn your Pal in Anubis's boss arena, while `2_2_forestsnow_1` will spawn them in northern snowy forests).
- **Level Range**: Set the minimum and maximum levels your Pal can spawn with (e.g., Min: 10, Max: 15).
- **Group Size**: Set how many individuals of this species can spawn in a single overworld group (e.g., setting Min: 1 and Max: 1 will spawn solitary individuals, while Min: 3 and Max: 5 will spawn complete packs).
- **Spawn Weight**: A percentage value between 1% and 100%. This determines how rare your Pal is compared to other species in the same spawner pool.

---

## Infiltrating the Game Engine

Unlike old-school mods that corrupt native save games by hard-overwriting spawner tables, PalBaker uses **Spawner Infiltration via Blueprint Patching**. 

When compiled, it generates a minor JSON injection payload. UE4SS reads this payload at runtime and dynamically appends your custom Pal directly into the target overworld spawner’s active list in memory. This ensures your custom spawns are completely safe, highly compatible, and won't corrupt player save games!