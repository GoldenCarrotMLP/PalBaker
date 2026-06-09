"use client"

import { type CreatorPal, type ActiveSkill, mockPalTemplates, mockSpawnerCache } from "@/lib/mock-data"
import { PalCreatorAPI } from "@/lib/data-service"
import { Checkbox } from "@/components/ui/checkbox"
import { Trash2 } from "lucide-react"
import { PalLearnset } from "./pal-learnset"
import { FieldGroup, StatSlider, WORK_SUITS, WORK_SUITABILITY_MAP, ELEMENT_OPTIONS } from "./pal-helpers"

interface Props {
  pal: CreatorPal
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

export function PalDetails({ pal, onUpdate, onOpenDialog, onSave, onDelete }: Props) {
  const isNew = pal.CharacterID.startsWith("NewPal_")

  const handleSave = async () => {
    try {
      let finalCharId = pal.CharacterID
      if (isNew) {
        finalCharId = pal.Name.replace(/\s+/g, "")
        if (!finalCharId) {
          alert("Please enter a Display Name first!")
          return
        }
      }
      const cleanPal = { ...pal, CharacterID: finalCharId }
      const saved    = await PalCreatorAPI.save(cleanPal, isNew)
      onSave(pal.CharacterID, saved)
      alert("Pal saved successfully!")
    } catch (err) {
      console.error("Save failed:", err)
      alert(`Save failed: ${err}`)
    }
  }

  const handleDelete = async () => {
    if (!confirm(`Delete custom Pal '${pal.Name || pal.CharacterID}'?`)) return
    try {
      if (!isNew) await PalCreatorAPI.delete(pal.CharacterID)
      onDelete(pal.CharacterID)
    } catch (err) {
      console.error("Delete failed:", err)
      alert(`Delete failed: ${err}`)
    }
  }

  return (
    <div className="border-t border-border bg-muted/30 p-5 flex flex-col gap-5">

      {/* Core IDs */}
      <div className="grid grid-cols-4 gap-3">
        <FieldGroup label="CHARACTER ID">
          <input
            value={pal.CharacterID}
            onChange={(e) => onUpdate({ CharacterID: e.target.value })}
            disabled={!isNew}
            title={!isNew ? "Character ID is locked after initial creation" : ""}
            className="input-field disabled:opacity-50 disabled:cursor-not-allowed font-mono text-xs"
          />
        </FieldGroup>
        <FieldGroup label="DISPLAY NAME">
          <input
            value={pal.Name}
            onChange={(e) => onUpdate({ Name: e.target.value })}
            className="input-field"
          />
        </FieldGroup>
        <FieldGroup label="PARENT TEMPLATE">
          <select
            value={pal.TemplateID}
            onChange={(e) => onUpdate({ TemplateID: e.target.value })}
            className="input-field"
          >
            {mockPalTemplates.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </FieldGroup>
        <FieldGroup label="PALDECK INDEX">
          <div className="flex gap-1.5">
            <input
              type="number"
              value={pal.ZukanIndex || 1}
              onChange={(e) => onUpdate({ ZukanIndex: Number(e.target.value) })}
              className="input-field flex-1"
            />
            <input
              value={pal.ZukanIndexSuffix || ""}
              onChange={(e) => onUpdate({ ZukanIndexSuffix: e.target.value })}
              className="input-field w-14 text-center font-bold"
              placeholder="Sfx"
              maxLength={2}
            />
          </div>
        </FieldGroup>
      </div>

      <FieldGroup label="DESCRIPTION">
        <textarea
          value={pal.Description}
          onChange={(e) => onUpdate({ Description: e.target.value })}
          className="input-field min-h-12 py-1.5 text-xs"
          placeholder="A short description..."
          rows={2}
        />
      </FieldGroup>

      {/* Elements */}
      <div className="grid grid-cols-2 gap-3">
        <FieldGroup label="PRIMARY ELEMENT (Required)">
          <select
            value={pal.ElementType1 || "EPalElementType::Normal"}
            onChange={(e) => onUpdate({ ElementType1: e.target.value })}
            className="input-field"
          >
            {ELEMENT_OPTIONS.map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>
        </FieldGroup>
        <FieldGroup label="SECONDARY ELEMENT (Optional)">
          <select
            value={pal.ElementType2 || "EPalElementType::None"}
            onChange={(e) => onUpdate({ ElementType2: e.target.value })}
            className="input-field"
          >
            {ELEMENT_OPTIONS.map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>
        </FieldGroup>
      </div>

      {/* Attributes + Work Suitabilities */}
      <div className="grid grid-cols-2 gap-6">
        <div>
          <h3 className="text-muted-foreground text-xs font-bold uppercase tracking-widest mb-4">Base Attributes</h3>
          <div className="flex flex-col gap-4">
            <StatSlider label="HP"         value={pal.BaseHP}         onChange={(v) => onUpdate({ BaseHP: v })} />
            <StatSlider label="ATTACK"     value={pal.BaseAtk}        onChange={(v) => onUpdate({ BaseAtk: v })} />
            <StatSlider label="DEFENSE"    value={pal.BaseDef}        onChange={(v) => onUpdate({ BaseDef: v })} />
            <StatSlider label="WORK SPEED" value={pal.BaseWorkSpeed}  onChange={(v) => onUpdate({ BaseWorkSpeed: v })} />
          </div>
        </div>

        <div>
          <h3 className="text-muted-foreground text-xs font-bold uppercase tracking-widest mb-4">Work Suitabilities</h3>
          <div className="grid grid-cols-2 gap-2">
            {WORK_SUITS.map((key) => {
              const rawKey   = WORK_SUITABILITY_MAP[key]
              const isChecked = (pal.WorkSuitabilities?.[rawKey] || 0) > 0
              return (
                <label key={key} className="flex items-center gap-2 cursor-pointer select-none">
                  <Checkbox
                    checked={isChecked}
                    onCheckedChange={(c) => {
                      onUpdate({
                        WorkSuitabilities: {
                          ...(pal.WorkSuitabilities || {}),
                          [rawKey]: c ? 1 : 0,
                        },
                      })
                    }}
                    className="border-border data-[state=checked]:bg-primary data-[state=checked]:border-primary"
                  />
                  <span className="text-xs text-foreground">{key}</span>
                </label>
              )
            })}
          </div>
        </div>
      </div>

      {/* Spawning Logic */}
      <div className="grid grid-cols-2 gap-4">
        <FieldGroup label="Spawner Location ID">
          <select
            value={pal.SpawnLocationID || ""}
            onChange={(e) => onUpdate({ SpawnLocationID: e.target.value })}
            className="input-field"
          >
            <option value="">Select spawner...</option>
            {Object.entries(mockSpawnerCache).map(([display, actual]) => (
              <option key={actual} value={actual}>{display}</option>
            ))}
          </select>
        </FieldGroup>

        <FieldGroup label="Level Range">
          <div className="flex gap-2">
            <input
              type="number"
              value={pal.SpawnMinLevel || 1}
              onChange={(e) => onUpdate({ SpawnMinLevel: Number(e.target.value) })}
              className="input-field flex-1"
              placeholder="1"
              min={1} max={100}
            />
            <input
              type="number"
              value={pal.SpawnMaxLevel || 50}
              onChange={(e) => onUpdate({ SpawnMaxLevel: Number(e.target.value) })}
              className="input-field flex-1"
              placeholder="50"
              min={1} max={100}
            />
          </div>
        </FieldGroup>

        <FieldGroup label="Group Size Range">
          <div className="flex gap-2">
            <input type="number" value={pal.SpawnMinGroup || 1} onChange={(e) => onUpdate({ SpawnMinGroup: Number(e.target.value) })} className="input-field flex-1" placeholder="Min" min={1} />
            <input type="number" value={pal.SpawnMaxGroup || 1} onChange={(e) => onUpdate({ SpawnMaxGroup: Number(e.target.value) })} className="input-field flex-1" placeholder="Max" min={1} />
          </div>
        </FieldGroup>
      </div>

      {/* Learnset */}
      <PalLearnset pal={pal} onUpdate={onUpdate} onOpenDialog={onOpenDialog} />

      {/* Action row */}
      <div className="flex items-center justify-end gap-3 mt-4 border-t border-border pt-4">
        <button
          onClick={handleDelete}
          className="flex items-center gap-1.5 px-3 py-2 rounded border border-status-error text-status-error text-xs font-semibold hover:bg-status-error/10 transition-colors cursor-pointer"
        >
          <Trash2 className="size-3.5" />
          Delete Pal
        </button>
        <button
          onClick={handleSave}
          className="flex items-center gap-1.5 px-4 py-2 rounded bg-primary text-primary-foreground text-xs font-bold uppercase tracking-wider hover:bg-primary/90 transition-colors cursor-pointer"
        >
          Save Changes
        </button>
      </div>
    </div>
  )
}
