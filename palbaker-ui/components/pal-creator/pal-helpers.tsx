"use client"

import { Slider } from "@/components/ui/slider"
import { cn } from "@/lib/utils"

// ── Constants ────────────────────────────────────────────────────────────────────

export const WORK_SUITS = [
  "Kindling", "Planting", "Handiwork", "Watering",
  "Gathering", "Lumbering", "Mining", "Medicine",
] as const

export type WorkKey = typeof WORK_SUITS[number]

export const WORK_SUITABILITY_MAP: Record<WorkKey, string> = {
  Kindling:  "WorkSuitability_EmitFlame",
  Planting:  "WorkSuitability_Seeding",
  Handiwork: "WorkSuitability_Handcraft",
  Watering:  "WorkSuitability_Watering",
  Gathering: "WorkSuitability_Collection",
  Lumbering: "WorkSuitability_Deforest",
  Mining:    "WorkSuitability_Mining",
  Medicine:  "WorkSuitability_ProductMedicine",
}

export const ELEMENT_OPTIONS: [string, string][] = [
  ["EPalElementType::None",        "None"],
  ["EPalElementType::Normal",      "Neutral"],
  ["EPalElementType::Fire",        "Fire"],
  ["EPalElementType::Water",       "Water"],
  ["EPalElementType::Leaf",        "Grass"],
  ["EPalElementType::Electricity", "Electric"],
  ["EPalElementType::Ice",         "Ice"],
  ["EPalElementType::Earth",       "Ground"],
  ["EPalElementType::Dark",        "Dark"],
  ["EPalElementType::Dragon",      "Dragon"],
]

export function cleanElement(raw: string): string {
  if (!raw) return "Normal"
  const part = raw.split("::")[1] || "Normal"
  if (part === "Leaf")        return "Grass"
  if (part === "Electricity") return "Electric"
  if (part === "Earth")       return "Ground"
  if (part === "None")        return ""
  return part
}

// ── Shared UI helpers ─────────────────────────────────────────────────────────────

export function FieldGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">{label}</label>
      {children}
    </div>
  )
}

export function SectionLabel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <h2 className={cn("text-muted-foreground text-xs font-bold uppercase tracking-widest", className)}>
      {children}
    </h2>
  )
}

export function StatSlider({
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
