"use client"

import { useState, useMemo } from "react"
import { Plus, Trash2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { type CreatorPal, type ActiveSkill, type LearnsetEntry, ELEMENT_COLORS } from "@/lib/mock-data"
import { AlertTriangle } from "lucide-react"
import { cn } from "@/lib/utils"
import { UniqueWazaMapperModal } from "./unique-waza-mapper-modal"

interface Props {
  pal: CreatorPal
  activeSkills: Record<string, ActiveSkill>
  onUpdate: (patch: Partial<CreatorPal>) => void
  onOpenDialog: (
    title: string,
    dataset: Record<string, ActiveSkill | string>,
    onSelect: (id: string, label: string) => void,
    palElements?: string[]
  ) => void
}

export function PalLearnset({ pal, activeSkills, onUpdate, onOpenDialog }: Props) {
  // Sync wrapper (prevents react-hooks/exhaustive-deps trigger)
  const learnset: LearnsetEntry[] = useMemo(() => pal.Learnset || [], [pal.Learnset])

  // Synchronously adjust local state during render (prevents cascading effects)
  const [prevPalId, setPrevPalId] = useState(pal.CharacterID)
  const [editingLevels, setEditingLevels] = useState<Record<number, string>>({})
  const [mappingWaza, setMappingWaza] = useState<{ id: string; originalIndex?: number } | null>(null)

  if (pal.CharacterID !== prevPalId) {
    setPrevPalId(pal.CharacterID)
    setEditingLevels({})
  }

  const handleAddMove = () => {
    onOpenDialog("Add Move", activeSkills, (id) => {
      if (id.startsWith("Unique_")) {
        setMappingWaza({ id })
      } else {
        onUpdate({ Learnset: [...learnset, { Level: 1, WazaID: id }] })
      }
    })
  }

  const handleChangeMove = (originalIndex: number) => {
    onOpenDialog("Select Move", activeSkills, (id) => {
      if (id.startsWith("Unique_")) {
        setMappingWaza({ id, originalIndex })
      } else {
        const next = [...learnset]
        next[originalIndex] = { ...next[originalIndex], WazaID: id }
        onUpdate({ Learnset: next })
      }
    })
  }

  const handleMoveClick = (row: typeof sorted[0]) => {
    if (row.WazaID.startsWith("Unique_")) {
      setMappingWaza({ id: row.WazaID, originalIndex: row.originalIndex })
    } else {
      handleChangeMove(row.originalIndex)
    }
  }

  const handleChangeLevel = (originalIndex: number, level: number) => {
    const next = [...learnset]
    next[originalIndex] = { ...next[originalIndex], Level: level }
    onUpdate({ Learnset: next })
  }

  const handleRemove = (originalIndex: number) => {
    onUpdate({ Learnset: learnset.filter((_, i) => i !== originalIndex) })
  }

  const indexedLearnset = useMemo(() => {
    return learnset.map((row, originalIndex) => ({ ...row, originalIndex }))
  }, [learnset])

  const sorted = useMemo(() => {
    return [...indexedLearnset].sort((a, b) => a.Level - b.Level)
  }, [indexedLearnset])

  const isMissingDeps = (wazaId: string) => {
    return (pal.missing_dependencies || []).some(
      d => d.feature === `Unique Attack: ${wazaId.replace("EPalWazaID::", "").replace("Unique_", "")}` ||
           d.feature === `Unique Attack: ${wazaId.replace("EPalWazaID::", "")}` ||
           d.feature === `Unique Attack: Unique_${wazaId.replace("EPalWazaID::", "").replace("Unique_", "")}`
    )
  }

  return (
    <div>
      {mappingWaza && (
        <UniqueWazaMapperModal
          pal={pal}
          wazaId={mappingWaza.id}
          onClose={() => setMappingWaza(null)}
          onChangeMove={() => {
            const origIdx = mappingWaza.originalIndex
            setMappingWaza(null)
            if (origIdx !== undefined) {
              handleChangeMove(origIdx)
            } else {
              handleAddMove()
            }
          }}
          onConfirm={() => {
            if (mappingWaza.originalIndex !== undefined) {
              const next = [...learnset]
              next[mappingWaza.originalIndex] = { ...next[mappingWaza.originalIndex], WazaID: mappingWaza.id }
              onUpdate({ Learnset: next })
            } else {
              onUpdate({ Learnset: [...learnset, { Level: 1, WazaID: mappingWaza.id }] })
            }
            setMappingWaza(null)
          }}
        />
      )}
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

      <div className="grid grid-cols-[56px_1fr_100px_64px_32px] gap-2 px-1 mb-2">
        {["LEVEL", "MOVE", "ELEMENT", "POWER", ""].map((h) => (
          <span key={h} className="text-muted-foreground text-xs font-semibold uppercase">{h}</span>
        ))}
      </div>

      <div className="max-h-48 overflow-y-auto border border-border rounded">
        {sorted.length === 0 ? (
          <p className="text-muted-foreground text-xs italic p-3">No moves. Add one above.</p>
        ) : (
          sorted.map((row) => {
            const skillValues = Object.values(activeSkills)
            const skillObj = skillValues.find(s => s.id === row.WazaID) || activeSkills[row.WazaID]
            
            const el      = skillObj?.element ?? "?"
            const elColor = ELEMENT_COLORS[el] ?? ELEMENT_COLORS["Normal"]
            const power   = skillObj?.power !== undefined && skillObj?.power !== 0 ? skillObj.power : "—"

            const isEditing = editingLevels[row.originalIndex] !== undefined
            const displayValue = isEditing ? editingLevels[row.originalIndex] : String(row.Level)

            return (
              <div key={row.originalIndex} className="grid grid-cols-[56px_1fr_100px_64px_32px] gap-2 items-center p-2 border-b border-border/40 last:border-0 hover:bg-accent/20">
                <input
                  type="number"
                  value={displayValue}
                  onChange={(e) => {
                    const val = e.target.value
                    setEditingLevels((prev) => ({ ...prev, [row.originalIndex]: val }))
                  }}
                  onBlur={() => {
                    const val = editingLevels[row.originalIndex]
                    if (val !== undefined) {
                      const numVal = parseInt(val) || 1
                      handleChangeLevel(row.originalIndex, numVal)
                      setEditingLevels((prev) => {
                        const next = { ...prev }
                        delete next[row.originalIndex]
                        return next
                      })
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.currentTarget.blur()
                    }
                  }}
                  className="bg-muted text-primary text-xs px-1 py-1 rounded border border-border focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <div className="flex items-center min-w-0">
                  <button
                    onClick={() => handleMoveClick(row)}
                    className={cn("text-xs truncate text-left transition-colors cursor-pointer", isMissingDeps(row.WazaID) ? "text-status-warning hover:text-status-warning/80" : "text-foreground hover:text-primary")}
                  >
                    {row.WazaID.replace(/_/g, " ")}
                  </button>
                  {isMissingDeps(row.WazaID) && (
                    <button 
                      onClick={() => setMappingWaza({ id: row.WazaID, originalIndex: row.originalIndex })} 
                      title="Missing Animations! Click to map."
                      className="ml-2 shrink-0 cursor-pointer"
                    >
                      <AlertTriangle className="size-3.5 text-status-warning animate-pulse" />
                    </button>
                  )}
                </div>
                <Badge variant="outline" className={cn("text-[10px] font-bold", elColor)}>
                  {el.toUpperCase()}
                </Badge>
                <span className="text-foreground text-xs font-mono">{power}</span>
                <button
                  onClick={() => handleRemove(row.originalIndex)}
                  className="text-muted-foreground hover:text-status-error transition-colors cursor-pointer justify-self-end"
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