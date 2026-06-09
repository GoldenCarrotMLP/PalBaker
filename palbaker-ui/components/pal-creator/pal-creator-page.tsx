"use client"

import { useState } from "react"
import { mockCreatorPals, mockPalTemplates, type CreatorPal, type LearnsetEntry, ELEMENT_COLORS, mockActiveSkills } from "@/lib/mock-data"
import { Separator } from "@/components/ui/separator"
import { Slider } from "@/components/ui/slider"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { ChevronDown, Plus, Trash2 } from "lucide-react"
import { cn } from "@/lib/utils"

const WORK_SUITS = [
  "Kindling", "Planting", "Handiwork", "Watering",
  "Gathering", "Lumbering", "Mining", "Medicine",
] as const

type WorkKey = typeof WORK_SUITS[number]

export function PalCreatorPage() {
  const [pal, setPal] = useState<CreatorPal>(mockCreatorPals[0])
  const [templateOpen, setTemplateOpen] = useState(false)

  function updatePal(patch: Partial<CreatorPal>) {
    setPal((p) => ({ ...p, ...patch }))
  }

  function updateSuit(key: WorkKey, val: boolean) {
    setPal((p) => ({ ...p, workSuitabilities: { ...p.workSuitabilities, [key]: val } }))
  }

  function addLearnsetRow() {
    setPal((p) => ({ ...p, Learnset: [...p.Learnset, { Level: 1, WazaID: "" }] }))
  }

  function removeLearnsetRow(i: number) {
    setPal((p) => ({ ...p, Learnset: p.Learnset.filter((_, idx) => idx !== i) }))
  }

  function updateLearnsetRow(i: number, patch: Partial<LearnsetEntry>) {
    setPal((p) => ({
      ...p,
      Learnset: p.Learnset.map((r, idx) => (idx === i ? { ...r, ...patch } : r)),
    }))
  }

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* ── Row 1 left: Parent Template ── */}
      <section className="bg-card rounded-md border border-border p-5 flex flex-col gap-4">
        <SectionLabel>Parent Template</SectionLabel>

        {/* Dropdown */}
        <div className="relative">
          <button
            onClick={() => setTemplateOpen((v) => !v)}
            className="w-full flex items-center justify-between bg-muted/60 border border-border rounded px-4 py-2.5 text-primary font-semibold text-sm"
          >
            {pal.parentTemplate}
            <ChevronDown className="size-4 text-primary" />
          </button>
          {templateOpen && (
            <div className="absolute top-full left-0 right-0 z-20 mt-1 bg-card border border-border rounded shadow-xl max-h-52 overflow-y-auto">
              {mockPalTemplates.map((t) => (
                <button
                  key={t}
                  onClick={() => { updatePal({ parentTemplate: t }); setTemplateOpen(false) }}
                  className={cn(
                    "w-full text-left px-4 py-2 text-sm hover:bg-accent transition-colors",
                    t === pal.parentTemplate ? "text-primary font-semibold" : "text-foreground"
                  )}
                >
                  {t}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Quick-pick chips */}
        <div className="flex gap-2 flex-wrap">
          {["Chillet", "Anubis"].map((t) => (
            <button
              key={t}
              onClick={() => updatePal({ parentTemplate: t })}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded border text-sm font-medium transition-colors",
                pal.parentTemplate === t
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border bg-muted/40 text-foreground hover:border-primary/50"
              )}
            >
              <span className="size-4 rounded-full bg-primary/20 inline-block" />
              {t}
            </button>
          ))}
        </div>
      </section>

      {/* ── Row 1 right: Core Identification ── */}
      <section className="bg-card rounded-md border border-border p-5 flex flex-col gap-4">
        <SectionLabel>Core Identification</SectionLabel>

        <div className="grid grid-cols-3 gap-3">
          <FieldGroup label="PAL ID">
            <input
              value={pal.palId}
              onChange={(e) => updatePal({ palId: e.target.value })}
              className="input-field"
            />
          </FieldGroup>
          <FieldGroup label="SPECIES NAME">
            <input
              value={pal.speciesName}
              onChange={(e) => updatePal({ speciesName: e.target.value })}
              className="input-field"
            />
          </FieldGroup>
          <FieldGroup label="ELEMENT TYPE">
            <div className="flex gap-2 items-center">
              <input
                value={pal.elementTypes[0] ?? ""}
                onChange={(e) => updatePal({ elementTypes: [e.target.value] })}
                className="input-field flex-1"
              />
              <button className="size-8 rounded bg-primary text-primary-foreground flex items-center justify-center font-bold shrink-0">
                <Plus className="size-4" />
              </button>
            </div>
          </FieldGroup>
        </div>
      </section>

      {/* ── Row 2 left: Base Attributes ── */}
      <section className="bg-card rounded-md border border-border p-5 flex flex-col gap-5">
        <div className="flex items-center justify-between">
          <SectionLabel>Base Attributes</SectionLabel>
          <Badge variant="outline" className="text-xs font-bold border-primary text-primary">STABLE</Badge>
        </div>

        {(["hp", "attack", "defense", "workSpeed"] as const).map((stat) => (
          <StatSlider
            key={stat}
            label={stat === "workSpeed" ? "WORK SPEED" : stat.toUpperCase()}
            value={pal[stat] as number}
            min={1}
            max={500}
            onChange={(v) => updatePal({ [stat]: v })}
          />
        ))}
      </section>

      {/* ── Row 2 right: Work Suitabilities ── */}
      <section className="bg-card rounded-md border border-border p-5">
        <SectionLabel className="mb-4">Work Suitabilities</SectionLabel>

        <div className="grid grid-cols-4 gap-x-4 gap-y-3">
          {WORK_SUITS.map((key) => (
            <label key={key} className="flex items-center gap-2 cursor-pointer select-none">
              <Checkbox
                checked={pal.workSuitabilities[key as WorkKey]}
                onCheckedChange={(checked) => updateSuit(key as WorkKey, !!checked)}
                className="border-border data-[state=checked]:bg-primary data-[state=checked]:border-primary"
              />
              <span className="text-xs text-foreground">{key}</span>
            </label>
          ))}
        </div>
      </section>

      {/* ── Row 3 left: Spawning Logic ── */}
      <section className="bg-card rounded-md border border-border p-5 flex flex-col gap-4">
        <SectionLabel>Spawning Logic</SectionLabel>

        <FieldGroup label="Coordinates (X, Y)">
          <div className="flex gap-2">
            <input
              type="number"
              value={pal.spawnX}
              onChange={(e) => updatePal({ spawnX: Number(e.target.value) })}
              className="input-field flex-1"
            />
            <input
              type="number"
              value={pal.spawnY}
              onChange={(e) => updatePal({ spawnY: Number(e.target.value) })}
              className="input-field flex-1"
            />
          </div>
        </FieldGroup>

        <FieldGroup label="Level Range">
          <div className="flex gap-2">
            <input
              type="number"
              value={pal.levelMin}
              onChange={(e) => updatePal({ levelMin: Number(e.target.value) })}
              className="input-field flex-1"
              placeholder="15"
            />
            <input
              type="number"
              value={pal.levelMax}
              onChange={(e) => updatePal({ levelMax: Number(e.target.value) })}
              className="input-field flex-1"
              placeholder="25"
            />
          </div>
        </FieldGroup>

        <FieldGroup label="Group Size">
          <input
            type="number"
            value={pal.groupSize}
            onChange={(e) => updatePal({ groupSize: Number(e.target.value) })}
            className="input-field"
            placeholder="3"
          />
        </FieldGroup>
      </section>

      {/* ── Row 3 right: Learnset Matrix ── */}
      <section className="bg-card rounded-md border border-border p-5 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <SectionLabel>Learnset Matrix</SectionLabel>
          <button
            onClick={addLearnsetRow}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-primary text-primary text-xs font-semibold hover:bg-primary/10 transition-colors"
          >
            <Plus className="size-3.5" />
            Add Progression Row
          </button>
        </div>

        {/* Table header */}
        <div className="grid grid-cols-[60px_1fr_100px_70px_32px] gap-3 px-2">
          {["LEVEL", "ACTIVE MOVE", "ELEMENT", "POWER", ""].map((h) => (
            <span key={h} className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">{h}</span>
          ))}
        </div>

        <Separator />

        <div className="flex flex-col gap-2 max-h-64 overflow-y-auto pr-1">
          {pal.Learnset.map((row, i) => {
            const skill = mockActiveSkills[row.WazaID]
            const element = skill?.element ?? "Normal"
            const elementClass = ELEMENT_COLORS[element] ?? ELEMENT_COLORS["Normal"]

            return (
              <div
                key={i}
                className="grid grid-cols-[60px_1fr_100px_70px_32px] gap-3 items-center py-2 border-b border-border/50 last:border-0"
              >
                <span className="text-primary font-bold text-sm">{row.Level}</span>
                <span className="text-foreground text-sm truncate">
                  {row.WazaID.replace(/_/g, " ")}
                </span>
                <span className={cn("text-xs font-bold px-2 py-0.5 rounded text-center", elementClass)}>
                  {element.toUpperCase()}
                </span>
                <span className="text-foreground text-sm">
                  {40 + i * 15}
                </span>
                <button
                  onClick={() => removeLearnsetRow(i)}
                  className="text-muted-foreground hover:text-status-error transition-colors"
                >
                  <Trash2 className="size-4" />
                </button>
              </div>
            )
          })}
        </div>
      </section>
    </div>
  )
}

/* ── Sub-components ── */

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
  min,
  max,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  onChange: (v: number) => void
}) {
  return (
    <div className="grid grid-cols-[110px_1fr_56px] items-center gap-3">
      <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">{label}</span>
      <Slider
        value={[value]}
        min={min}
        max={max}
        step={1}
        onValueChange={([v]) => onChange(v)}
        className="[&_[role=slider]]:bg-primary [&_[role=slider]]:border-primary [&_.bg-primary]:bg-primary"
      />
      <div className="bg-muted/60 border border-border rounded px-2 py-1 text-primary text-xs font-mono text-center">
        {value}
      </div>
    </div>
  )
}
