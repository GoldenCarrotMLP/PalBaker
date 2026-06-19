# Morphs & Shape Keys

Morph Targets (known as Blendshapes or Shape Keys in Blender) allow you to deform and scale specific parts of your Pal's geometry dynamically. This is useful for creating unique proportions, modifying heights, or adjusting accessories per variant.

## Supported Morph Targets
PalBaker supports the following standard overworld deformers natively:
- `breast_size`
- `belly_fat`
- `waist_width`
- `height_scale`

---

## Configuring Morphs

Open your Variant Configurator modal and scroll to Section 4. Select the dropdown next to your target morph and choose a roll mode:

### 1. Static Mode (Forced Value)
Forces the morph key to a fixed, constant value between `0.0` (fully collapsed) and `1.0` (fully expanded). This is useful for forcing a variant to always spawn with thick winter fur, giant proportions, or custom accessories.

### 2. Random Mode (Range Roll)
Allows the morph key to roll randomly within custom bounds on spawn. You can set the minimum and maximum ranges.
- **Free Roll**: Picks any random float value between your min and max bounds.
- **Restrict**: Locks the roll to increments, preventing extreme clipping.
This enables amazing variety—Pals of the same variant will spawn with slightly different heights, waist sizes, or accessory scales!