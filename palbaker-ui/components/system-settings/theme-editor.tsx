"use client"

import { useState, useRef, useCallback } from "react"
import { useTheme } from "@/lib/theme-context"
import { type ThemePreset, type ColorHCL, deriveTokens, applyTokens } from "@/lib/theme-engine"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Slider } from "@/components/ui/slider"
import { Separator } from "@/components/ui/separator"
import { Palette, Copy, Trash2, Save, RotateCcw, Check } from "lucide-react"

// ── Color swatch preview ──

function SwatchRow({ tokens }: { tokens: Record<string, string> }) {
  const groups = [
    { label: "BG", keys: ["--console-bg", "--sidebar", "--background", "--card", "--secondary", "--accent"] },
    { label: "Accent", keys: ["--primary", "--status-success", "--status-warning", "--status-error"] },
    { label: "Border", keys: ["--border", "--input"] },
  ]

  return (
    <div className="flex flex-col gap-3">
      {groups.map((g) => (
        <div key={g.label} className="flex items-center gap-2">
          <span className="w-14 text-xs text-muted-foreground font-mono">{g.label}</span>
          <div className="flex gap-1 flex-1">
            {g.keys.map((k) => (
              <div
                key={k}
                className="h-7 flex-1 rounded-md border border-white/10 first:rounded-l-lg last:rounded-r-lg"
                style={{ backgroundColor: tokens[k] ?? "#333" }}
                title={k}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Slider group ──

function ColorSlider({
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  step: number
  unit?: string
  onChange: (v: number) => void
}) {
  const display = step >= 1 ? Math.round(value) : value.toFixed(2)
  return (
    <div className="flex items-center gap-3">
      <span className="w-24 text-xs text-muted-foreground shrink-0">{label}</span>
      <Slider
        value={[value] as any}
        min={min}
        max={max}
        step={step}
        onValueChange={(v: any) => onChange(Array.isArray(v) ? v[0] : v)}
        className="flex-1"
      />
      <span className="w-14 text-right text-xs font-mono text-foreground/80 tabular-nums">
        {display}{unit ?? ""}
      </span>
    </div>
  )
}

// ── Main component ──

export function ThemeEditor() {
  const {
    active,
    base,
    accent,
    layerDepth,
    borderWeight,
    presets,
    setBase,
    setAccent,
    setLayerDepth,
    setBorderWeight,
    setActivePreset,
    saveCustomPreset,
    deleteCustomPreset,
    renameCustomPreset,
    duplicatePreset,
  } = useTheme()

  const [selectedName, setSelectedName] = useState(active.name)
  const [customName, setCustomName] = useState("")
  const [editingName, setEditingName] = useState<string | null>(null)
  const [editValue, setEditValue] = useState("")
  const [saved, setSaved] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const previewTokens = deriveTokens(base, accent, layerDepth, borderWeight)

  const handleSelect = useCallback(
    (name: string) => {
      const preset = presets.find((p) => p.name === name)
      if (preset) {
        setActivePreset(preset)
        setSelectedName(name)
      }
    },
    [presets, setActivePreset]
  )

  const handleSave = useCallback(() => {
    const name = customName.trim() || active.name
    saveCustomPreset(name)
    setSelectedName(name)
    setCustomName("")
    setSaved(true)
    setTimeout(() => setSaved(false), 1500)
  }, [customName, active.name, saveCustomPreset])

  const handleDuplicate = useCallback(() => {
    const name = `${active.name} Copy`
    duplicatePreset(active, name)
    setSelectedName(name)
  }, [active, duplicatePreset])

  const handleDelete = useCallback(() => {
    deleteCustomPreset(selectedName)
    setSelectedName("PalBaker Cyan")
    const fallback = presets.find((p) => p.name === "PalBaker Cyan")
    if (fallback) setActivePreset(fallback)
  }, [selectedName, deleteCustomPreset, presets, setActivePreset])

  const startRename = useCallback(() => {
    setEditingName(selectedName)
    setEditValue(selectedName)
    setTimeout(() => inputRef.current?.focus(), 50)
  }, [selectedName])

  const commitRename = useCallback(() => {
    if (editingName && editValue.trim() && editValue.trim() !== editingName) {
      renameCustomPreset(editingName, editValue.trim())
      setSelectedName(editValue.trim())
    }
    setEditingName(null)
  }, [editingName, editValue, renameCustomPreset])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Palette className="size-4 text-primary" />
          THEME EDITOR
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        {/* Live preview */}
        <SwatchRow tokens={previewTokens} />

        {/* Theme selector */}
        <div className="flex flex-col gap-2">
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Active Theme
          </label>
          <div className="flex gap-2">
            <select
              value={selectedName}
              onChange={(e) => handleSelect(e.target.value)}
              className="h-8 flex-1 rounded-lg border border-input bg-background px-2.5 text-sm text-foreground outline-none focus:border-ring focus:ring-3 focus:ring-ring/50 font-mono appearance-none"
            >
              <optgroup label="Built-in">
                {presets.filter((p) => !p.name.endsWith(" Copy") && !["Midnight", "High Contrast"].includes(p.name)).map((p) => (
                  <option key={p.name} value={p.name}>{p.name}</option>
                ))}
              </optgroup>
              {presets.some((p) => p !== presets.find((bp) => bp.name === p.name)) && (
                <optgroup label="Custom">
                  {presets.filter((p) => !["PalBaker Cyan", "PalBaker Violet", "PalBaker Emerald", "PalBaker Amber", "PalBaker Rose", "Midnight", "High Contrast"].includes(p.name)).map((p) => (
                    <option key={p.name} value={p.name}>{p.name}</option>
                  ))}
                </optgroup>
              )}
            </select>
            <Button variant="ghost" size="icon" onClick={handleDuplicate} title="Duplicate theme">
              <Copy className="size-4" />
            </Button>
            <Button variant="ghost" size="icon" onClick={handleDelete} title="Delete custom theme">
              <Trash2 className="size-4" />
            </Button>
          </div>
        </div>

        {/* Rename */}
        <div className="flex flex-col gap-2">
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Rename
          </label>
          {editingName ? (
            <div className="flex gap-2">
              <Input
                ref={inputRef}
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") commitRename()
                  if (e.key === "Escape") setEditingName(null)
                }}
                onBlur={commitRename}
                className="font-mono"
              />
              <Button variant="ghost" size="icon" onClick={commitRename}>
                <Check className="size-4" />
              </Button>
            </div>
          ) : (
            <Button variant="outline" size="sm" onClick={startRename}>
              Rename "{selectedName}"
            </Button>
          )}
        </div>

        <Separator />

        {/* Surface controls */}
        <div className="flex flex-col gap-3">
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Surface Colors
          </label>
          <ColorSlider
            label="Hue"
            value={base.h}
            min={0}
            max={360}
            step={1}
            unit="°"
            onChange={(h) => setBase({ h })}
          />
          <ColorSlider
            label="Chroma"
            value={base.c}
            min={0}
            max={0.15}
            step={0.005}
            onChange={(c) => setBase({ c })}
          />
          <ColorSlider
            label="Lightness"
            value={base.l}
            min={0.02}
            max={0.4}
            step={0.005}
            onChange={(l) => setBase({ l })}
          />
        </div>

        <Separator />

        {/* Accent controls */}
        <div className="flex flex-col gap-3">
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Accent / Primary Colors
          </label>
          <ColorSlider
            label="Hue"
            value={accent.h}
            min={0}
            max={360}
            step={1}
            unit="°"
            onChange={(h) => setAccent({ h })}
          />
          <ColorSlider
            label="Chroma"
            value={accent.c}
            min={0}
            max={0.35}
            step={0.005}
            onChange={(c) => setAccent({ c })}
          />
          <ColorSlider
            label="Lightness"
            value={accent.l}
            min={0.3}
            max={0.9}
            step={0.005}
            onChange={(l) => setAccent({ l })}
          />
        </div>

        <Separator />

        {/* Structure controls */}
        <div className="flex flex-col gap-3">
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Structure
          </label>
          <ColorSlider
            label="Layer Depth"
            value={layerDepth}
            min={0.2}
            max={3}
            step={0.05}
            unit="x"
            onChange={setLayerDepth}
          />
          <ColorSlider
            label="Border Weight"
            value={borderWeight}
            min={0}
            max={3}
            step={0.05}
            unit="x"
            onChange={setBorderWeight}
          />
        </div>

        <Separator />

        {/* Save as new */}
        <div className="flex flex-col gap-2">
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Save as New Theme
          </label>
          <div className="flex gap-2">
            <Input
              placeholder="Theme name..."
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
              className="font-mono"
            />
            <Button variant="default" size="sm" onClick={handleSave}>
              {saved ? <Check className="size-4 mr-1" /> : <Save className="size-4 mr-1" />}
              {saved ? "Saved" : "Save"}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
