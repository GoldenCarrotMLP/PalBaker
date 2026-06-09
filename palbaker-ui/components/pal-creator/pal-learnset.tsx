"use client"

import { Plus, Trash2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { type CreatorPal, type ActiveSkill, type LearnsetEntry, ELEMENT_COLORS } from "@/lib/mock-data"
import { mockActiveSkills } from "@/lib/mock-data"
import { cn } from "@/lib/utils"

interface Props {
  pal: CreatorPal
  onUpdate: (patch: Partial<CreatorPal>) => void
  onOpenDialog: (
    title: string,
    dataset: Record<string, ActiveSkill | string>,
    onSelect: (id: string, label: string) => void,
    palElements?: string[]
  ) => void
}

export function PalLearnset({ pal, onUpdate, onOpenDialog }: Props) {
  const learnset: LearnsetEntry[] = pal.Learnset || []

  const handleAddMove = () => {
    onOpenDialog("Add Move", mockActiveSkills, (id) => {
      onUpdate({ Learnset: [...learnset, { Level: 1, WazaID: id }] })
    })
  }

  const handleChangeMove = (index: number) => {
    onOpenDialog("Select Move", mockActiveSkills, (id) => {
      const next = [...learnset]
      next[index] = { ...next[index], WazaID: id }
      onUpdate({ Learnset: next })
    })
  }

  const handleChangeLevel = (index: number, level: number) => {
    const next = [...learnset]
    next[index] = { ...next[index], Level: level }
    onUpdate({ Learnset: next })
  }

  const handleRemove = (index: number) => {
    onUpdate({ Learnset: learnset.filter((_, i) => i !== index) })
  }

  const sorted = [...learnset].sort((a, b) => a.Level - b.Level)

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-muted-foreground text-xs font-bold uppercase tracking-widest">Learnset Matrix</h3>
        <button
          onClick={handleAddMove}
          className="flex items-center gap-1.5 px-2 py-1 rounded border border-primary text-primary text-xs font-semibold hover:bg-primary/10 cursor-pointer"
        >
          <Plus className="size-3" />
          Add Move
        </button>
      </div>

      {/* Header row */}
      <div className="grid grid-cols-[56px_1fr_100px_64px_32px] gap-2 px-1 mb-2">
        {["LEVEL", "MOVE", "ELEMENT", "POWER", ""].map((h) => (
          <span key={h} className="text-muted-foreground text-xs font-semibold uppercase">{h}</span>
        ))}
      </div>

      <div className="max-h-48 overflow-y-auto border border-border rounded">
        {sorted.length === 0 ? (
          <p className="text-muted-foreground text-xs italic p-3">No moves. Add one above.</p>
        ) : (
          sorted.map((row, i) => {
            const skill   = mockActiveSkills[row.WazaID]
            const el      = skill?.element ?? "?"
            const elColor = ELEMENT_COLORS[el] ?? ELEMENT_COLORS["Normal"]
            const power   = skill?.power ?? "—"

            return (
              <div key={i} className="grid grid-cols-[56px_1fr_100px_64px_32px] gap-2 items-center p-2 border-b border-border/40 last:border-0 hover:bg-accent/20">
                <input
                  type="number"
                  value={row.Level}
                  onChange={(e) => handleChangeLevel(i, Number(e.target.value))}
                  className="bg-muted text-primary text-xs px-1 py-1 rounded border border-border focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <button
                  onClick={() => handleChangeMove(i)}
                  className="text-foreground text-xs truncate text-left hover:text-primary transition-colors cursor-pointer"
                >
                  {row.WazaID.replace(/_/g, " ")}
                </button>
                <Badge variant="outline" className={cn("text-[10px] font-bold", elColor)}>
                  {el.toUpperCase()}
                </Badge>
                <span className="text-foreground text-xs font-mono">{power}</span>
                <button
                  onClick={() => handleRemove(i)}
                  className="text-muted-foreground hover:text-status-error transition-colors cursor-pointer"
                >
                  <Trash2 className="size-3.5" />
                </button>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
