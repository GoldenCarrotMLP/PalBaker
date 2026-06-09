"use client"

import { type AltermaticVariant } from "@/lib/mock-data"
import { cn } from "@/lib/utils"

interface VariantChipProps {
  variant: AltermaticVariant
  modName: string
}

// Mirrors mod_details.py build_variants_list() badge logic
export function VariantChip({ variant, modName }: VariantChipProps) {
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
