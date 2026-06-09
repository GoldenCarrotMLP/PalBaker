"use client"

import { type CreatorPal, type ActiveSkill, ELEMENT_COLORS } from "@/lib/mock-data"
import { Badge } from "@/components/ui/badge"
import { ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { PalDetails } from "./pal-details"
import { cleanElement } from "./pal-helpers"

interface Props {
  pal: CreatorPal
  expanded: boolean
  onToggle: () => void
  onUpdate: (patch: Partial<CreatorPal>) => void
  onOpenDialog: (
    title: string,
    dataset: Record<string, ActiveSkill | string>,
    onSelect: (id: string, label: string) => void,
    palElements?: string[]
  ) => void
  onSave: (oldId: string, saved: CreatorPal) => void
  onDelete: (id: string) => void
}

export function PalListRow({ pal, expanded, onToggle, onUpdate, onOpenDialog, onSave, onDelete }: Props) {
  const el1       = cleanElement(pal.ElementType1) || "Normal"
  const el2       = cleanElement(pal.ElementType2)
  const el1Color  = ELEMENT_COLORS[el1]  ?? ELEMENT_COLORS["Normal"]
  const el2Color  = el2 ? (ELEMENT_COLORS[el2] ?? ELEMENT_COLORS["Normal"]) : "bg-muted text-muted-foreground"
  const zukanStr  = pal.ZukanIndex !== undefined
    ? `${String(pal.ZukanIndex).padStart(3, "0")}${pal.ZukanIndexSuffix ? `-${pal.ZukanIndexSuffix}` : ""}`
    : "—"

  return (
    <div className="bg-card">
      {/* Collapsed row */}
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center gap-3 hover:bg-accent/50 transition-colors cursor-pointer"
      >
        <ChevronRight className={cn("size-4 text-muted-foreground transition-transform shrink-0", expanded && "rotate-90")} />
        <div className="flex-1 text-left min-w-0">
          <div className="text-foreground font-semibold text-sm">{pal.Name || pal.CharacterID || "(Unnamed)"}</div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-muted-foreground text-xs">INDEX: {zukanStr}</span>
            <Badge variant="outline" className={cn("text-[10px] font-bold h-5", el1Color)}>
              {el1.toUpperCase()}
            </Badge>
            {el2 && (
              <Badge variant="outline" className={cn("text-[10px] font-bold h-5", el2Color)}>
                {el2.toUpperCase()}
              </Badge>
            )}
            <span className="text-muted-foreground text-xs">• {(pal.Learnset || []).length} moves</span>
          </div>
        </div>
        <span className="text-muted-foreground text-xs font-mono shrink-0">{pal.TemplateID}</span>
      </button>

      {/* Expanded details */}
      {expanded && (
        <PalDetails
          pal={pal}
          onUpdate={onUpdate}
          onOpenDialog={onOpenDialog}
          onSave={onSave}
          onDelete={onDelete}
        />
      )}
    </div>
  )
}
