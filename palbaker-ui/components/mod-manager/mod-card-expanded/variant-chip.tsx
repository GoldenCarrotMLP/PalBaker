// palbaker-ui/components/mod-manager/mod-card-expanded/variant-chip.tsx
"use client"

import { type DynamicPalVariant } from "@/lib/mock-data"
import { cn } from "@/lib/utils"

interface Props {
  variant: DynamicPalVariant
  modName: string
  onClick?: () => void
}

export function VariantChip({ variant, modName, onClick }: Props) {
  const prefix = `${modName}_`
  const displayLabel = variant.label.startsWith(prefix)
    ? variant.label.slice(prefix.length)
    : variant.label

  const traitsCount = (variant.PassiveSkills || []).length + (variant.PrefTrait || []).length
  const skipCount   = (variant.SkipTrait || []).length
  const matsCount   = (variant.SpecialMaterial || []).length
  const morphsCount = (variant.ShapeKeys || []).length
  const hasAnimTarget = !!variant.AnimTarget

  const chips: { text: string; cls: string }[] = []

  if (variant.is_base) {
    chips.push({ text: "BASE", cls: "bg-muted text-muted-foreground" })
  } else {
    if (variant.Gender && variant.Gender !== "None")
      chips.push({ text: variant.Gender[0], cls: "bg-blue-900/60 text-blue-300" })
    if (variant.LuckyStarReq)
      chips.push({ text: "LUCKY", cls: "bg-amber-900/60 text-amber-300" })
      
    // NEW: Yellow AnimTarget Chip
    if (hasAnimTarget)
      chips.push({ text: "AnimTarget", cls: "bg-yellow-900/60 text-yellow-300" })
      
    if (traitsCount > 0)
      chips.push({ text: `T:${traitsCount}`, cls: "bg-green-900/60 text-green-300" })
    if (skipCount > 0)
      chips.push({ text: `BLK:${skipCount}`, cls: "bg-red-900/60 text-red-300" })
    if (matsCount > 0)
      chips.push({ text: `M:${matsCount}`, cls: "bg-purple-900/60 text-purple-300" })
    if (morphsCount > 0)
      chips.push({ text: `SK:${morphsCount}`, cls: "bg-cyan-900/60 text-cyan-300" })
    if (chips.length === 0)
      chips.push({ text: "DEFAULT", cls: "bg-muted text-muted-foreground" })
  }


  return (
    <button
      onClick={onClick}
      className="flex flex-col gap-1 bg-muted/50 border border-border rounded px-3 py-2 text-left hover:border-primary/50 transition-colors min-w-[64px] cursor-pointer"
    >
      <span className="text-primary text-xs font-semibold truncate max-w-[120px]">{displayLabel}</span>
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