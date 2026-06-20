// lib/theme-engine.ts
// Parametric theme system: 6 base values → all CSS tokens via math

export interface ColorHCL {
  h: number // hue (0-360)
  c: number // chroma (0-0.4)
  l: number // lightness (0-1)
}

export interface ThemePreset {
  name: string
  base: ColorHCL
  accent: ColorHCL
  layerDepth?: number  // 0.2–3.0, default 1.0 — scales lightness offsets between surface layers
  borderWeight?: number // 0.0–3.0, default 1.0 — scales border opacity/visibility
}

// ── oklch helpers ──────────────────────────────────────────────────

function oklch(l: number, c: number, h: number): string {
  return `oklch(${clamp(l, 0, 1).toFixed(3)} ${clamp(c, 0, 0.4).toFixed(3)} ${((h % 360) + 360) % 360})`
}

function oklchAlpha(l: number, c: number, h: number, alpha: number): string {
  return `oklch(${clamp(l, 0, 1).toFixed(3)} ${clamp(c, 0, 0.4).toFixed(3)} ${((h % 360) + 360) % 360} / ${(clamp(alpha, 0, 1) * 100).toFixed(1)}%)`
}

function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v))
}

// ── Derivation engine ──────────────────────────────────────────────
// Takes 6 user values → produces all ~42 CSS custom properties

export function deriveTokens(base: ColorHCL, accent: ColorHCL, layerDepth: number = 1, borderWeight: number = 1): Record<string, string> {
  const bH = base.h
  const bC = base.c
  const bL = base.l
  const aH = accent.h
  const aC = accent.c
  const aL = accent.l
  const d = clamp(layerDepth, 0.2, 3)   // depth multiplier
  const bw = clamp(borderWeight, 0, 3) // border weight multiplier

  return {
    // ── Surface hierarchy (base hue/chroma, lightness offsets scaled by depth) ──
    "--background":           oklch(bL,              bC,       bH),
    "--surface":              oklch(bL,              bC,       bH),
    "--console-bg":           oklch(bL - 0.03 * d,   bC,       bH),
    "--sidebar":              oklch(bL - 0.01 * d,   bC,       bH),
    "--card":                 oklch(bL + 0.04 * d,   bC,       bH - 5),
    "--popover":              oklch(bL + 0.04 * d,   bC,       bH - 5),
    "--surface-raised":       oklch(bL + 0.04 * d,   bC,       bH - 5),
    "--sidebar-accent":       oklch(bL + 0.06 * d,   bC + 0.01, bH - 5),
    "--secondary":            oklch(bL + 0.08 * d,   bC,       bH - 5),
    "--muted":                oklch(bL + 0.08 * d,   bC - 0.01, bH - 5),
    "--accent":               oklch(bL + 0.10 * d,   bC,       bH - 5),

    // ── Primary / accent family ──
    "--primary":              oklch(aL,        aC,       aH),
    "--ring":                 oklch(aL,        aC,       aH),
    "--cyan":                 oklch(aL,        aC,       aH),
    "--sidebar-primary":      oklch(aL,        aC,       aH),
    "--sidebar-ring":         oklch(aL,        aC,       aH),

    // ── Primary foreground (dark text on accent backgrounds) ──
    "--primary-foreground":   oklch(bL - 0.02, bC,       bH),
    "--cyan-foreground":      oklch(bL - 0.02, bC,       bH),
    "--sidebar-primary-foreground": oklch(bL - 0.02, bC, bH),

    // ── Foreground / text ──
    "--foreground":           oklch(0.93,      0,        0),
    "--card-foreground":      oklch(0.93,      0,        0),
    "--popover-foreground":   oklch(0.93,      0,        0),
    "--secondary-foreground": oklch(0.93,      0,        0),
    "--accent-foreground":    oklch(0.93,      0,        0),
    "--sidebar-accent-foreground": oklch(0.93, 0,        0),
    "--muted-foreground":     oklch(0.60,      0.03,     bH - 10),
    "--sidebar-foreground":   oklch(0.85,      0.02,     bH - 10),

    // ── Status colors (hue offsets from accent) ──
    "--status-success":       oklch(0.70,      0.18,     aH - 45),
    "--status-warning":       oklch(0.75,      0.18,     aH + 155),
    "--status-error":         oklch(0.60,      0.22,     aH + 172),
    "--status-info":          oklch(aL,        aC,       aH),
    "--status-idle":          oklch(0.55,      0.04,     bH),
    "--destructive":          oklch(0.60,      0.22,     aH + 172),

    // ── Charts (mirror status) ──
    "--chart-1":              oklch(aL,        aC,       aH),
    "--chart-2":              oklch(0.70,      0.18,     aH - 45),
    "--chart-3":              oklch(0.75,      0.18,     aH + 155),
    "--chart-4":              oklch(0.60,      0.22,     aH + 172),
    "--chart-5":              oklch(0.55,      0.04,     bH),

    // ── Borders (white overlay, opacity scales with base lightness + border weight) ──
    "--border":               oklchAlpha(1, 0, 0, clamp((bL * 0.55 + 0.04) * bw, 0, 0.3)),
    "--input":                oklchAlpha(1, 0, 0, clamp((bL * 0.55 + 0.06) * bw, 0, 0.35)),
    "--sidebar-border":       oklchAlpha(1, 0, 0, clamp((bL * 0.55 + 0.04) * bw, 0, 0.3)),
  }
}

// ── Apply tokens to DOM ────────────────────────────────────────────

export function applyTokens(tokens: Record<string, string>) {
  if (typeof document === "undefined") return
  let style = document.getElementById("palbaker-theme") as HTMLStyleElement | null
  if (!style) {
    style = document.createElement("style")
    style.id = "palbaker-theme"
    document.head.appendChild(style)
  }
  const lines = [":root {"]
  for (const [key, value] of Object.entries(tokens)) {
    lines.push(`  ${key}: ${value};`)
  }
  lines.push("}")
  style.textContent = lines.join("\n")
}

// ── Presets ────────────────────────────────────────────────────────

export const DEFAULT_THEME: ThemePreset = {
  name: "PalBaker Cyan",
  base: { h: 240, c: 0.04, l: 0.12 },
  accent: { h: 200, c: 0.18, l: 0.72 },
  layerDepth: 1,
  borderWeight: 1,
}

export const BUILT_IN_PRESETS: ThemePreset[] = [
  { name: "PalBaker Cyan",    base: { h: 240, c: 0.04, l: 0.12 }, accent: { h: 200, c: 0.18, l: 0.72 } },
  { name: "PalBaker Violet",  base: { h: 270, c: 0.04, l: 0.12 }, accent: { h: 270, c: 0.16, l: 0.70 } },
  { name: "PalBaker Emerald", base: { h: 160, c: 0.04, l: 0.12 }, accent: { h: 155, c: 0.18, l: 0.70 } },
  { name: "PalBaker Amber",   base: { h: 30,  c: 0.04, l: 0.12 }, accent: { h: 40,  c: 0.18, l: 0.72 } },
  { name: "PalBaker Rose",    base: { h: 340, c: 0.04, l: 0.12 }, accent: { h: 340, c: 0.18, l: 0.70 } },
  { name: "Midnight",         base: { h: 230, c: 0.02, l: 0.08 }, accent: { h: 210, c: 0.12, l: 0.65 } },
  { name: "High Contrast",    base: { h: 240, c: 0.01, l: 0.05 }, accent: { h: 200, c: 0.22, l: 0.78 }, layerDepth: 1.5, borderWeight: 1.4 },
]

// ── Serialization ──

export function serializePreset(p: ThemePreset): string {
  return JSON.stringify({ name: p.name, base: p.base, accent: p.accent, layerDepth: p.layerDepth, borderWeight: p.borderWeight }, null, 2)
}

export function deserializePreset(json: string): ThemePreset | null {
  try {
    const data = JSON.parse(json)
    if (data.name && data.base && data.accent) {
      return {
        name: data.name,
        base: { h: data.base.h, c: data.base.c, l: data.base.l },
        accent: { h: data.accent.h, c: data.accent.c, l: data.accent.l },
        layerDepth: data.layerDepth ?? 1,
        borderWeight: data.borderWeight ?? 1,
      }
    }
  } catch {}
  return null
}
