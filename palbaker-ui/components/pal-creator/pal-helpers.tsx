"use client"

import { Slider } from "@/components/ui/slider"
import { cn } from "@/lib/utils"

export const WORK_SUITS = [
  "Kindling", "Watering", "Planting", "Electricity", "Handiwork",
  "Gathering", "Lumbering", "Mining", "Oil Extraction", "Medicine",
  "Cooling", "Transport", "Farming",
] as const

export type WorkKey = typeof WORK_SUITS[number]

export const WORK_SUITABILITY_MAP: Record<WorkKey, string> = {
  "Kindling":  "WorkSuitability_EmitFlame",
  "Watering":  "WorkSuitability_Watering",
  "Planting":  "WorkSuitability_Seeding",
  "Electricity": "WorkSuitability_GenerateElectricity",
  "Handiwork": "WorkSuitability_Handcraft",
  "Gathering": "WorkSuitability_Collection",
  "Lumbering": "WorkSuitability_Deforest",
  "Mining":    "WorkSuitability_Mining",
  "Oil Extraction": "WorkSuitability_OilExtraction",
  "Medicine":  "WorkSuitability_ProductMedicine",
  "Cooling": "WorkSuitability_Cool",
  "Transport": "WorkSuitability_Transport",
  "Farming": "WorkSuitability_MonsterFarm",
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
  min = 1,
  max = 500,
}: {
  label: string
  value: number
  onChange: (v: number) => void
  min?: number
  max?: number
}) {
  return (
    <div className="grid grid-cols-[120px_1fr_56px] items-center gap-3">
      <span className="text-muted-foreground text-[10px] font-semibold uppercase tracking-wider">{label}</span>
      <Slider
        value={[value]}
        min={min}
        max={max}
        step={1}
        onValueChange={(vals) => onChange(Array.isArray(vals) ? (vals as number[])[0] : Number(vals))}
        className="[&_[role=slider]]:bg-primary [&_[role=slider]]:border-primary"
      />
      <div className="bg-muted/60 border border-border rounded px-2 py-1 text-primary text-[10px] font-mono text-center">
        {value}
      </div>
    </div>
  )
}