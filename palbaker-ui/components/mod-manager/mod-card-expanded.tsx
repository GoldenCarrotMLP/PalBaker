"use client"

import { useState } from "react"
import { type ModItem, type AltermaticVariant } from "@/lib/mock-data"
import { Separator } from "@/components/ui/separator"
import { Play, Upload, Trash2, Plus, ImagePlus } from "lucide-react"
import { cn } from "@/lib/utils"

interface Props {
  mod: ModItem
}

const CRY_SLOTS = ["Normal", "Joy", "Anger", "Sorrow", "Pain", "Death"] as const

// Mirrors mod_details.py build_variants_list() badge logic
function VariantChip({ variant, modName }: { variant: AltermaticVariant; modName: string }) {
  // Strip "ModName_" prefix from label for display
  const prefix = `${modName}_`
  const displayLabel = variant.label.startsWith(prefix)
    ? variant.label.slice(prefix.length)
    : variant.label

  const traitsCount = variant.ReqTrait.length + variant.PrefTrait.length
  const matsCount = variant.MatReplace.length
  const morphsCount = variant.MorphTarget.length

  const chips: { text: string; cls: string }[] = []

  if (variant.is_base) {
    chips.push({ text: "BASE", cls: "bg-muted text-muted-foreground" })
  } else {
    if (variant.Gender !== "None") {
      chips.push({ text: variant.Gender[0], cls: "bg-blue-900/60 text-blue-300" })
    }
    if (variant.IsRarePal) {
      chips.push({ text: "LUCKY", cls: "bg-amber-900/60 text-amber-300" })
    }
    if (traitsCount > 0) {
      chips.push({ text: `T:${traitsCount}`, cls: "bg-green-900/60 text-green-300" })
    }
    if (matsCount > 0) {
      chips.push({ text: `M:${matsCount}`, cls: "bg-purple-900/60 text-purple-300" })
    }
    if (morphsCount > 0) {
      chips.push({ text: `MPH:${morphsCount}`, cls: "bg-cyan-900/60 text-cyan-300" })
    }
    if (chips.length === 0) {
      chips.push({ text: "DEFAULT", cls: "bg-muted text-muted-foreground" })
    }
  }

  return (
    <button className="flex flex-col gap-1 bg-muted/50 border border-border rounded px-3 py-2 text-left hover:border-primary/50 transition-colors min-w-[64px]">
      <span className="text-primary text-xs font-semibold truncate">{displayLabel}</span>
      <div className="flex flex-wrap gap-1">
        {chips.map((c, i) => (
          <span key={i} className={cn("text-[9px] font-bold px-1 py-0.5 rounded", c.cls)}>
            {c.text}
          </span>
        ))}
      </div>
    </button>
  )
}

export function ModCardExpanded({ mod }: Props) {
  const [altermaticEnabled, setAltermaticEnabled] = useState(mod.is_altermatic_active)
  const availableCries = CRY_SLOTS.filter((s) => mod.sound_metadata[s] !== undefined)
  const hasSoundData = availableCries.length > 0

  return (
    <div className="border-t border-border px-5 py-5">
      <div className="flex gap-6 items-start">

        {/* ── Col 1: Custom Pal Icon ── */}
        <div className="flex flex-col gap-2 shrink-0">
          <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">
            Custom Pal Icon
          </span>
          <button
            className="size-20 rounded border border-border bg-muted/50 flex flex-col items-center justify-center gap-1 hover:border-primary/50 transition-colors group"
            title="Click to set custom Pal Icon"
          >
            {mod.has_icon ? (
              <div className="size-full rounded flex items-center justify-center bg-muted">
                <span className="text-muted-foreground text-xs font-mono">icon</span>
              </div>
            ) : (
              <>
                <ImagePlus className="size-6 text-muted-foreground group-hover:text-primary transition-colors" />
              </>
            )}
          </button>
          <span className="text-muted-foreground text-xs font-mono">64×64 PNG/DDS</span>
        </div>

        <Separator orientation="vertical" className="self-stretch opacity-50" />

        {/* ── Col 2: Cries Replacement ── */}
        <div className="flex flex-col gap-2 flex-1 min-w-0">
          <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">
            Cries Replacement
          </span>

          {!hasSoundData ? (
            <p className="text-muted-foreground text-xs italic">
              {mod.has_fmodel
                ? "No mapped audio database found for this Pal."
                : "Audio replacement requires raw FModel files. Click 'Create .blend file' or 'Generate Sources' first."}
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              {availableCries.map((slot) => {
                const hasOverride = !!mod.audio_overrides[slot]
                return (
                  <div
                    key={slot}
                    className={cn(
                      "flex items-center gap-2 rounded px-3 py-2 border",
                      hasOverride
                        ? "bg-primary/5 border-primary/30"
                        : "bg-muted/50 border-border",
                    )}
                  >
                    <button className="shrink-0 size-6 rounded-full bg-primary/10 hover:bg-primary/20 flex items-center justify-center transition-colors">
                      <Play className="size-3 text-primary" />
                    </button>
                    <div className="flex-1 min-w-0">
                      <div className="text-foreground text-xs font-semibold">{slot}</div>
                      <div className={cn("text-[10px] truncate", hasOverride ? "text-status-warning" : "text-muted-foreground")}>
                        {hasOverride ? "Custom Override" : "Original Game Sound"}
                      </div>
                    </div>
                    <button className="shrink-0 text-muted-foreground hover:text-foreground transition-colors">
                      {hasOverride ? (
                        <Trash2 className="size-3.5 text-status-error" />
                      ) : (
                        <Upload className="size-3.5" />
                      )}
                    </button>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <Separator orientation="vertical" className="self-stretch opacity-50" />

        {/* ── Col 3: Altermatic Variants ── */}
        <div className="flex flex-col gap-2 min-w-[220px] shrink-0">
          <div className="flex items-center justify-between gap-3">
            <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">
              Altermatic Variants
            </span>
            {/* Toggle switch */}
            <label className="flex items-center gap-1.5 cursor-pointer shrink-0">
              <span className="text-xs text-muted-foreground font-mono">ENABLE</span>
              <div className="relative w-9 h-5">
                <input
                  type="checkbox"
                  checked={altermaticEnabled}
                  onChange={(e) => setAltermaticEnabled(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-muted border border-border peer-checked:bg-primary rounded-full transition-colors" />
                <div className="absolute top-0.5 left-0.5 size-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
              </div>
            </label>
          </div>

          {altermaticEnabled && (
            <div className="flex flex-col gap-2">
              {mod.altermatic_variants.length === 0 ? (
                <p className="text-muted-foreground text-xs italic">No custom variants added yet.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {mod.altermatic_variants.map((v, i) => (
                    <VariantChip key={i} variant={v} modName={mod.name} />
                  ))}
                </div>
              )}
              <button className="flex items-center justify-center gap-1.5 border border-dashed border-border rounded px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:border-primary/50 transition-colors mt-1">
                <Plus className="size-3.5" />
                ADD VARIANT
              </button>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
