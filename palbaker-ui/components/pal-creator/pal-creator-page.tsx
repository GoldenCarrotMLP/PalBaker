"use client"

import { useState, useRef, useEffect } from "react"
import {
  mockCreatorPals,
  mockPalTemplates,
  mockActiveSkills,
  mockSpawnerCache,
  type CreatorPal,
  type LearnsetEntry,
  type ActiveSkill,
  ELEMENT_COLORS,
} from "@/lib/mock-data"
import { Separator } from "@/components/ui/separator"
import { Slider } from "@/components/ui/slider"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { ChevronDown, Plus, Trash2, Search, X, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

const WORK_SUITS = [
  "Kindling", "Planting", "Handiwork", "Watering",
  "Gathering", "Lumbering", "Mining", "Medicine",
] as const

type WorkKey = typeof WORK_SUITS[number]

// ── Search selector dialog ──────────────────────────────────────────────────────
interface SearchSelectorProps {
  title: string
  dataset: Record<string, ActiveSkill | string>
  palElements?: string[]
  onSelect: (id: string, label: string) => void
  onClose: () => void
}

function SearchSelectorDialog({ title, dataset, palElements, onSelect, onClose }: SearchSelectorProps) {
  const [query, setQuery] = useState("")
  const [filterElement, setFilterElement] = useState("All")
  const [filterCategory, setFilterCategory] = useState("All")
  const [palOnly, setPalOnly] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const firstVal = Object.values(dataset)[0]
  const isSkillDataset = !!(firstVal && typeof firstVal === "object" && "element" in firstVal)
  const allElements = isSkillDataset
    ? [...new Set((Object.values(dataset) as ActiveSkill[]).map((v) => v.element))]
    : []
  const allCategories = isSkillDataset
    ? [...new Set((Object.values(dataset) as ActiveSkill[]).map((v) => v.category))]
    : []

  const filtered = Object.entries(dataset).filter(([label, val]) => {
    if (isSkillDataset) {
      const skill = val as ActiveSkill
      if (palOnly && palElements && palElements.length > 0 && !palElements.includes(skill.element)) return false
      if (filterElement !== "All" && skill.element !== filterElement) return false
      if (filterCategory !== "All" && skill.category !== filterCategory) return false
    }
    if (query) {
      const q = query.toLowerCase()
      return label.toLowerCase().includes(q) || String(val).toLowerCase().includes(q)
    }
    return true
  })

  const MAX = 35
  const shown = filtered.slice(0, MAX)
  const extra = filtered.length - MAX

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-card border border-border rounded-lg shadow-2xl w-[420px] max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <span className="text-foreground font-semibold text-sm">{title}</span>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">
            <X className="size-4" />
          </button>
        </div>

        <div className="px-4 pt-3 pb-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={`Search ${title}...`}
              className="w-full bg-muted/60 border border-border rounded pl-8 pr-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
        </div>

        {isSkillDataset && palElements && palElements.length > 0 && (
          <label className="flex items-center gap-2 px-4 pb-2 cursor-pointer">
            <Checkbox
              checked={palOnly}
              onCheckedChange={(c) => setPalOnly(!!c)}
              className="border-border data-[state=checked]:bg-primary data-[state=checked]:border-primary"
            />
            <span className="text-xs text-muted-foreground">
              Match Pal Elements ({palElements.join(", ")})
            </span>
          </label>
        )}

        {isSkillDataset && (
          <div className="flex gap-2 px-4 pb-3">
            <select
              value={filterElement}
              onChange={(e) => setFilterElement(e.target.value)}
              className="flex-1 bg-muted/60 border border-border rounded px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="All">All Elements</option>
              {allElements.map((el) => <option key={el} value={el}>{el}</option>)}
            </select>
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="flex-1 bg-muted/60 border border-border rounded px-2 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="All">All Types</option>
              {allCategories.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        )}

        <div className="overflow-y-auto flex-1 border-t border-border">
          {shown.length === 0 ? (
            <p className="text-muted-foreground text-xs italic px-4 py-3">No entries match criteria.</p>
          ) : (
            shown.map(([label, val]) => {
              const detail = isSkillDataset
                ? `${(val as ActiveSkill).element} • ${(val as ActiveSkill).category} • PWR ${(val as ActiveSkill).power}`
                : label
              return (
                <button
                  key={label}
                  onClick={() => { onSelect(label, label); onClose() }}
                  className="w-full text-left px-4 py-2.5 hover:bg-accent transition-colors border-b border-border/40 last:border-0"
                >
                  <div className="text-foreground text-sm font-medium">{label}</div>
                  {isSkillDataset && <div className="text-muted-foreground text-xs font-mono">{detail}</div>}
                </button>
              )
            })
          )}
          {extra > 0 && (
            <p className="text-primary text-xs italic px-4 py-2">
              ...and {extra} more. Type to filter.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Main page with list view ────────────────────────────────────────────────────
export function PalCreatorPage() {
  const [pals, setPals] = useState<CreatorPal[]>(mockCreatorPals)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [dialog, setDialog] = useState<{
    title: string
    dataset: Record<string, any>
    onSelect: (id: string, label: string) => void
    palElements?: string[]
  } | null>(null)

  function updatePal(id: string, patch: Partial<CreatorPal>) {
    setPals((list) => list.map((p) => (p.CharacterID === id ? { ...p, ...patch } : p)))
  }

  function addPal() {
    const newPal: CreatorPal = {
      CharacterID: `NewPal_${Date.now()}`,
      TemplateID: "Anubis",
      palId: "",
      speciesName: "",
      elementTypes: ["", ""],
      hp: 100,
      attack: 50,
      defense: 50,
      workSpeed: 100,
      workSuitabilities: {
        Kindling: false,
        Planting: false,
        Handiwork: false,
        Watering: false,
        Gathering: false,
        Lumbering: false,
        Mining: false,
        Medicine: false,
      },
      Learnset: [],
      spawnX: 0,
      spawnY: 0,
      levelMin: 1,
      levelMax: 50,
      groupSize: 1,
      parentTemplate: "Anubis",
    }
    setPals((list) => [...list, newPal])
  }

  return (
    <>
      {dialog && (
        <SearchSelectorDialog
          title={dialog.title}
          dataset={dialog.dataset}
          palElements={dialog.palElements}
          onSelect={dialog.onSelect}
          onClose={() => setDialog(null)}
        />
      )}

      <div className="flex flex-col gap-4">
        {/* Header + Add button */}
        <div className="flex items-center justify-between">
          <h2 className="text-muted-foreground text-xs font-bold uppercase tracking-widest">Pal Definitions</h2>
          <button
            onClick={addPal}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-primary text-primary text-xs font-semibold hover:bg-primary/10 transition-colors"
          >
            <Plus className="size-3.5" />
            New Pal
          </button>
        </div>

        {/* Pal list */}
        <div className="flex flex-col gap-2 border border-border rounded-md divide-y divide-border overflow-hidden">
          {pals.map((pal) => (
            <PalListRow
              key={pal.CharacterID}
              pal={pal}
              expanded={expandedId === pal.CharacterID}
              onToggle={() => setExpandedId(expandedId === pal.CharacterID ? null : pal.CharacterID)}
              onUpdate={(patch) => updatePal(pal.CharacterID, patch)}
              onOpenDialog={(title, dataset, onSelect, palElements) =>
                setDialog({ title, dataset, onSelect, palElements })
              }
            />
          ))}
        </div>
      </div>
    </>
  )
}

// ── List row (collapsed) ────────────────────────────────────────────────────────
function PalListRow({
  pal,
  expanded,
  onToggle,
  onUpdate,
  onOpenDialog,
}: {
  pal: CreatorPal
  expanded: boolean
  onToggle: () => void
  onUpdate: (patch: Partial<CreatorPal>) => void
  onOpenDialog: (title: string, dataset: Record<string, any>, onSelect: (id: string, label: string) => void, palElements?: string[]) => void
}) {
  const el1 = pal.elementTypes[0] || "?"
  const el2 = pal.elementTypes[1]
  const el1Color = ELEMENT_COLORS[el1] ?? ELEMENT_COLORS["Normal"]
  const el2Color = el2 ? (ELEMENT_COLORS[el2] ?? ELEMENT_COLORS["Normal"]) : "bg-muted text-muted-foreground"

  return (
    <div className="bg-card">
      {/* Collapsed row */}
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center gap-3 hover:bg-accent/50 transition-colors"
      >
        <ChevronRight
          className={cn("size-4 text-muted-foreground transition-transform", expanded && "rotate-90")}
        />
        <div className="flex-1 text-left min-w-0">
          <div className="text-foreground font-semibold text-sm">{pal.speciesName || "(Unnamed)"}</div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-muted-foreground text-xs">ID: {pal.palId || "—"}</span>
            <Badge variant="outline" className={cn("text-[10px] font-bold h-5", el1Color)}>
              {el1.toUpperCase()}
            </Badge>
            {el2 && (
              <Badge variant="outline" className={cn("text-[10px] font-bold h-5", el2Color)}>
                {el2.toUpperCase()}
              </Badge>
            )}
            <span className="text-muted-foreground text-xs">• {pal.Learnset.length} moves</span>
          </div>
        </div>
        <span className="text-muted-foreground text-xs">{pal.parentTemplate}</span>
      </button>

      {/* Expanded details */}
      {expanded && (
        <PalDetails pal={pal} onUpdate={onUpdate} onOpenDialog={onOpenDialog} />
      )}
    </div>
  )
}

// ── Expanded details panel ──────────────────────────────────────────────────────
function PalDetails({
  pal,
  onUpdate,
  onOpenDialog,
}: {
  pal: CreatorPal
  onUpdate: (patch: Partial<CreatorPal>) => void
  onOpenDialog: (title: string, dataset: Record<string, any>, onSelect: (id: string, label: string) => void, palElements?: string[]) => void
}) {
  return (
    <div className="border-t border-border bg-muted/30 p-5 flex flex-col gap-5">
      {/* Core IDs */}
      <div className="grid grid-cols-3 gap-3">
        <FieldGroup label="PAL ID">
          <input
            value={pal.palId}
            onChange={(e) => onUpdate({ palId: e.target.value })}
            disabled={!!pal.palId}
            title={pal.palId ? "PAL ID is locked after initial set" : ""}
            className="input-field disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </FieldGroup>
        <FieldGroup label="SPECIES NAME">
          <input
            value={pal.speciesName}
            onChange={(e) => onUpdate({ speciesName: e.target.value })}
            className="input-field"
          />
        </FieldGroup>
        <FieldGroup label="PARENT TEMPLATE">
          <select
            value={pal.parentTemplate}
            onChange={(e) => onUpdate({ parentTemplate: e.target.value })}
            className="input-field"
          >
            {mockPalTemplates.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </FieldGroup>
      </div>

      {/* Elements — 2 required */}
      <div className="grid grid-cols-2 gap-3">
        <FieldGroup label="PRIMARY ELEMENT (Required)">
          <select
            value={pal.elementTypes[0] || ""}
            onChange={(e) => onUpdate({ elementTypes: [e.target.value, pal.elementTypes[1] || ""] })}
            className="input-field"
          >
            <option value="">Select element...</option>
            {Object.keys(ELEMENT_COLORS).map((el) => <option key={el} value={el}>{el}</option>)}
          </select>
        </FieldGroup>
        <FieldGroup label="SECONDARY ELEMENT (Optional)">
          <select
            value={pal.elementTypes[1] || ""}
            onChange={(e) => onUpdate({ elementTypes: [pal.elementTypes[0] || "", e.target.value] })}
            className="input-field"
          >
            <option value="">None</option>
            {Object.keys(ELEMENT_COLORS).map((el) => <option key={el} value={el}>{el}</option>)}
          </select>
        </FieldGroup>
      </div>

      {/* Attributes */}
      <div className="grid grid-cols-2 gap-6">
        <div>
          <h3 className="text-muted-foreground text-xs font-bold uppercase tracking-widest mb-4">Base Attributes</h3>
          <div className="flex flex-col gap-4">
            {(["hp", "attack", "defense", "workSpeed"] as const).map((stat) => (
              <StatSlider
                key={stat}
                label={stat === "workSpeed" ? "WORK SPEED" : stat.toUpperCase()}
                value={pal[stat] as number}
                onChange={(v) => onUpdate({ [stat]: v })}
              />
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-muted-foreground text-xs font-bold uppercase tracking-widest mb-4">Work Suitabilities</h3>
          <div className="grid grid-cols-2 gap-2">
            {WORK_SUITS.map((key) => (
              <label key={key} className="flex items-center gap-2 cursor-pointer select-none">
                <Checkbox
                  checked={pal.workSuitabilities[key as WorkKey]}
                  onCheckedChange={(c) =>
                    onUpdate({
                      workSuitabilities: { ...pal.workSuitabilities, [key]: !!c },
                    })
                  }
                  className="border-border data-[state=checked]:bg-primary data-[state=checked]:border-primary"
                />
                <span className="text-xs text-foreground">{key}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Spawning Logic */}
      <div className="grid grid-cols-2 gap-4">
        <FieldGroup label="Spawner Location">
          <select
            value={Object.entries(mockSpawnerCache).find(([_, v]) => v === pal.parentTemplate)?.[0] || ""}
            onChange={(e) => {
              const selected = e.target.value
              onUpdate({ parentTemplate: mockSpawnerCache[selected] || pal.parentTemplate })
            }}
            className="input-field"
          >
            <option value="">Select spawner...</option>
            {Object.entries(mockSpawnerCache).map(([display, actual]) => (
              <option key={actual} value={display}>{display}</option>
            ))}
          </select>
        </FieldGroup>

        <FieldGroup label="Coordinates (X, Y)">
          <div className="flex gap-2">
            <input
              type="number"
              value={pal.spawnX}
              onChange={(e) => onUpdate({ spawnX: Number(e.target.value) })}
              className="input-field flex-1"
            />
            <input
              type="number"
              value={pal.spawnY}
              onChange={(e) => onUpdate({ spawnY: Number(e.target.value) })}
              className="input-field flex-1"
            />
          </div>
        </FieldGroup>

        <FieldGroup label="Level Range">
          <div className="flex gap-2">
            <input
              type="number"
              value={pal.levelMin}
              onChange={(e) => onUpdate({ levelMin: Number(e.target.value) })}
              className="input-field flex-1"
              placeholder="1"
            />
            <input
              type="number"
              value={pal.levelMax}
              onChange={(e) => onUpdate({ levelMax: Number(e.target.value) })}
              className="input-field flex-1"
              placeholder="50"
            />
          </div>
        </FieldGroup>

        <FieldGroup label="Group Size">
          <input
            type="number"
            value={pal.groupSize}
            onChange={(e) => onUpdate({ groupSize: Number(e.target.value) })}
            className="input-field"
          />
        </FieldGroup>
      </div>

      {/* Learnset */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-muted-foreground text-xs font-bold uppercase tracking-widest">Learnset Matrix</h3>
          <button
            onClick={() =>
              onOpenDialog("Add Move", mockActiveSkills, (id, label) => {
                onUpdate({
                  Learnset: [...pal.Learnset, { Level: 1, WazaID: id }],
                })
              })
            }
            className="flex items-center gap-1.5 px-2 py-1 rounded border border-primary text-primary text-xs font-semibold hover:bg-primary/10"
          >
            <Plus className="size-3" />
            Add Move
          </button>
        </div>

        <div className="grid grid-cols-[56px_1fr_100px_64px_32px] gap-2 px-1 mb-2">
          {["LEVEL", "MOVE", "ELEMENT", "POWER", ""].map((h) => (
            <span key={h} className="text-muted-foreground text-xs font-semibold uppercase">
              {h}
            </span>
          ))}
        </div>

        <div className="max-h-48 overflow-y-auto border border-border rounded">
          {pal.Learnset.length === 0 ? (
            <p className="text-muted-foreground text-xs italic p-3">No moves. Add one above.</p>
          ) : (
            pal.Learnset.sort((a, b) => a.Level - b.Level).map((row, i) => {
              const skill = mockActiveSkills[row.WazaID]
              const el = skill?.element ?? "?"
              const elColor = ELEMENT_COLORS[el] ?? ELEMENT_COLORS["Normal"]
              const power = skill?.power ?? "—"

              return (
                <div key={i} className="grid grid-cols-[56px_1fr_100px_64px_32px] gap-2 items-center p-2 border-b border-border/40 last:border-0 hover:bg-accent/20">
                  <input
                    type="number"
                    value={row.Level}
                    onChange={(e) => {
                      const newLearnset = [...pal.Learnset]
                      newLearnset[i].Level = Number(e.target.value)
                      onUpdate({ Learnset: newLearnset })
                    }}
                    className="bg-muted text-primary text-xs px-1 py-1 rounded border border-border focus:outline-none focus:ring-1 focus:ring-primary"
                  />

                  <button
                    onClick={() =>
                      onOpenDialog("Select Move", mockActiveSkills, (id, label) => {
                        const newLearnset = [...pal.Learnset]
                        newLearnset[i].WazaID = id
                        onUpdate({ Learnset: newLearnset })
                      })
                    }
                    className="text-foreground text-xs truncate text-left hover:text-primary transition-colors"
                  >
                    {row.WazaID.replace(/_/g, " ")}
                  </button>

                  <Badge variant="outline" className={cn("text-[10px] font-bold", elColor)}>
                    {el.toUpperCase()}
                  </Badge>

                  <span className="text-foreground text-xs font-mono">{power}</span>

                  <button
                    onClick={() => onUpdate({ Learnset: pal.Learnset.filter((_, idx) => idx !== i) })}
                    className="text-muted-foreground hover:text-status-error transition-colors"
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}

/* ── Helpers ── */

function SectionLabel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <h2 className={cn("text-muted-foreground text-xs font-bold uppercase tracking-widest", className)}>
      {children}
    </h2>
  )
}

function FieldGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">{label}</label>
      {children}
    </div>
  )
}

function StatSlider({
  label,
  value,
  onChange,
}: {
  label: string
  value: number
  onChange: (v: number) => void
}) {
  return (
    <div className="grid grid-cols-[110px_1fr_56px] items-center gap-3">
      <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">{label}</span>
      <Slider
        value={[value]}
        min={1}
        max={500}
        step={1}
        onValueChange={(vals) => onChange(Array.isArray(vals) ? (vals as number[])[0] : Number(vals))}
        className="[&_[role=slider]]:bg-primary [&_[role=slider]]:border-primary"
      />
      <div className="bg-muted/60 border border-border rounded px-2 py-1 text-primary text-xs font-mono text-center">
        {value}
      </div>
    </div>
  )
}
