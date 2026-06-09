"use client"

import { type ModItem } from "@/lib/mock-data"
import { Separator } from "@/components/ui/separator"
import { Play, Upload, Trash2, Plus } from "lucide-react"
import { cn } from "@/lib/utils"

interface Props {
  mod: ModItem
}

const SOUND_SLOTS = ["Normal", "Joy", "Anger", "Sorrow", "Pain", "Death"] as const

const VARIANTS = [
  { label: "base", tag: "BASE", sub: "T:3  M:1", color: "bg-muted text-foreground" },
  { label: "Bikini", tag: "LUCKY", sub: "M  MPH:4", color: "bg-status-success/20 text-status-success" },
  { label: "NSFW", tag: "F", sub: "T:1", color: "bg-muted text-muted-foreground" },
]

export function ModCardExpanded({ mod }: Props) {
  return (
    <div className="border-t border-border px-5 py-5">
      <div className="grid grid-cols-[auto_1fr_auto] gap-6">
        {/* Col 1: Custom Pal Icon */}
        <div className="flex flex-col gap-2">
          <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">
            Custom Pal Icon
          </span>
          <div className="size-20 rounded border border-border bg-muted flex items-center justify-center overflow-hidden">
            {mod.has_icon ? (
              <div className="size-full bg-gradient-to-br from-muted to-accent flex items-center justify-center">
                <span className="text-muted-foreground text-xs font-mono">64px</span>
              </div>
            ) : (
              <span className="text-muted-foreground text-xs font-mono">—</span>
            )}
          </div>
          <span className="text-muted-foreground text-xs font-mono">64×64 PNG/DDS</span>
        </div>

        {/* Col 2: Cries Replacement */}
        <div className="flex flex-col gap-2">
          <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">
            Cries Replacement
          </span>
          <div className="grid grid-cols-2 gap-2">
            {SOUND_SLOTS.map((slot) => {
              const entry = mod.sound_metadata[slot]
              const hasOverride = !!entry?.override
              return (
                <div
                  key={slot}
                  className="flex items-center gap-2 bg-muted/50 rounded px-3 py-2 border border-border"
                >
                  <button className="shrink-0 size-6 rounded-full bg-primary/10 hover:bg-primary/20 flex items-center justify-center transition-colors">
                    <Play className="size-3 text-primary" />
                  </button>
                  <div className="flex-1 min-w-0">
                    <div className="text-foreground text-xs font-medium">{slot}</div>
                    <div className={cn("text-xs truncate", hasOverride ? "text-status-warning" : "text-muted-foreground")}>
                      {hasOverride ? entry!.override : "Original Game Sound"}
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
        </div>

        {/* Col 3: Altermatic Variants */}
        <div className="flex flex-col gap-2 min-w-[200px]">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">
              Altermatic Variants
            </span>
            <label className="flex items-center gap-2 cursor-pointer">
              <span className="text-xs text-muted-foreground">ENABLE</span>
              <div className="relative w-9 h-5">
                <input type="checkbox" defaultChecked className="sr-only peer" />
                <div className="w-9 h-5 bg-muted peer-checked:bg-primary rounded-full transition-colors" />
                <div className="absolute top-0.5 left-0.5 size-4 bg-white rounded-full transition-transform peer-checked:translate-x-4" />
              </div>
            </label>
          </div>

          <div className="flex flex-col gap-2">
            {VARIANTS.map((v) => (
              <div key={v.label} className="flex items-center gap-2 bg-muted/50 rounded px-3 py-2 border border-border">
                <span className="text-foreground text-xs font-medium w-12">{v.label}</span>
                <span className={cn("text-xs px-1.5 py-0.5 rounded font-bold", v.color)}>{v.tag}</span>
                <span className="text-muted-foreground text-xs font-mono ml-auto">{v.sub}</span>
              </div>
            ))}

            <button className="flex items-center justify-center gap-1.5 border border-dashed border-border rounded px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:border-primary transition-colors">
              <Plus className="size-3.5" />
              ADD VARIANT
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
