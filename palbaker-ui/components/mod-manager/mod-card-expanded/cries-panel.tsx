"use client"

import { Play, Upload, Trash2 } from "lucide-react"
import { type ModItem } from "@/lib/mock-data"
import { cn } from "@/lib/utils"

const CRY_SLOTS = ["Normal", "Joy", "Anger", "Sorrow", "Pain", "Death"] as const

interface CriesPanelProps {
  mod: ModItem
}

export function CriesPanel({ mod }: CriesPanelProps) {
  const availableCries = CRY_SLOTS.filter((s) => mod.sound_metadata[s] !== undefined)
  const hasSoundData = availableCries.length > 0

  return (
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
  )
}
