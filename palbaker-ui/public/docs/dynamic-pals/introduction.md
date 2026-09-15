# What is Dynamic Pals?

Dynamic Pals is a runtime model and material replacement system for Palworld powered by the Format V2 grouped schema specification.

Traditionally, mesh mods are "replacers"—meaning if you replace Chillet's mesh, every single Chillet spawning in your world will look identical. Dynamic Pals completely eliminates this limitation.

---

## Dynamic Runtime Variant Swapping

With Dynamic Pals active, your custom models are registered as **Format V2 skins**:
- You can create multiple different skins, accessories, or completely different meshes for a single Pal.
- Models and materials are loaded dynamically into memory at runtime using the `SwapJSON` loader.
- A single species can spawn in the wild with rich visual variety!

---

## Format V2 Parameters

PalBaker's Dynamic Pals Configurator allows you to customize exact spawn parameters for each variant:

- **Gender Constraints**: Force a model to only spawn on Male, Female, or other gender instances.
- **Lucky Star Attributes (`LuckyStarReq`)**: Force a variant to only trigger when a Pal spawns as a "Lucky" (giant/shiny) overworld encounter.
- **Passive Skill Matching (`PassiveSkills`)**: Force a skin to appear only if the Pal possesses specific passive traits (e.g. showing a gold skin only if the Pal has "Artisan").
- **Wild Pal Filtering (`IsWildPal`)**: Restrict a variant to wild encounters or bred Pals.