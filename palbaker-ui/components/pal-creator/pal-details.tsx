"use client"

import { useState, useMemo } from "react"
import { type CreatorPal, type ActiveSkill } from "@/lib/mock-data"
import { PalCreatorAPI } from "@/lib/data-service"
import { Checkbox } from "@/components/ui/checkbox"
import { Trash2, RefreshCw, ChevronDown, ChevronUp } from "lucide-react"
import { PalLearnset } from "./pal-learnset"
import { FieldGroup, StatSlider, SectionLabel, WORK_SUITS, WORK_SUITABILITY_MAP, ELEMENT_OPTIONS } from "./pal-helpers"
import { DiagnosticsModal } from "@/components/common/diagnostics-modal"
import { useNotifications } from "../mod-manager/mod-card-expanded/use-notifications"
import { NotificationToast } from "../mod-manager/mod-card-expanded/notification-toast"
import { SearchableSelect } from "@/components/ui/searchable-select"

interface Props {
  pal: CreatorPal
  spawners: Record<string, string>
  activeSkills: Record<string, ActiveSkill>
  onUpdate: (patch: Partial<CreatorPal>) => void
  onOpenDialog: (
    title: string,
    dataset: Record<string, ActiveSkill | string>,
    onSelect: (id: string, label: string) => void,
    palElements?: string[]
  ) => void
  onSave: (oldId: string, saved: CreatorPal) => void
  onDelete: (id: string) => void
  templates: string[]
  palNames: Record<string, string>
}

export function PalDetails({ pal, spawners, activeSkills, onUpdate, onOpenDialog, onSave, onDelete, templates, palNames }: Props) {
  const [diagnosticError, setDiagnosticError] = useState<string | null>(null)
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false)
  const { notifications, showNotification, dismissNotification } = useNotifications()

  const handleSave = async () => {
    try {
      const saved = await PalCreatorAPI.save(pal)
      onSave(pal.CharacterID, saved)
      showNotification("Pal saved successfully! 🦊💖", "success", "Pal Saved")
    } catch (err: any) {
      console.error("Save failed:", err)
      setDiagnosticError(String(err.message || err))
    }
  }

  const handleRefreshBP = async () => {
    try {
      await PalCreatorAPI.refreshBP(pal.CharacterID)
      showNotification("Blueprint refreshed and patched successfully! 🦊✨", "success", "Blueprint Patched")
    } catch (err: any) {
      console.error("Blueprint refresh failed:", err)
      setDiagnosticError(String(err.message || err))
    }
  }

  // Safe option builder: Ensure that whatever the TemplateID is, it is included in the dropdown options
  const options = useMemo(() => {
    const opts = [...templates]
    if (pal.TemplateID && !opts.includes(pal.TemplateID)) {
      opts.unshift(pal.TemplateID)
    }
    return opts
  }, [templates, pal.TemplateID])

  const parentTemplateOptions = useMemo(() => {
    return options.map((t) => ({
      value: t,
      label: `${palNames[t] || t} (${t})`
    }))
  }, [options, palNames])

  const spawnerOptions = useMemo(() => {
    return Object.entries(spawners).map(([display, actual]) => ({
      value: actual,
      label: display
    }))
  }, [spawners])

  return (
    <div className="border-t border-border bg-muted/30 p-5 flex flex-col gap-5">

      <div className="grid grid-cols-4 gap-3">
        <FieldGroup label="CHARACTER ID">
          <input
            value={pal.CharacterID}
            onChange={() => {}}
            disabled={true}
            title="Character ID is locked after initial creation"
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
          <SearchableSelect
            value={pal.TemplateID}
            onChange={(val) => onUpdate({ TemplateID: val })}
            options={parentTemplateOptions}
            placeholder="Select parent template..."
            emptyText="No templates found."
          />
        </FieldGroup>
        <FieldGroup label="PALDECK INDEX">
          <div className="flex gap-1.5">
            <input
              type="number"
              value={pal.ZukanIndex || -1}
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

      <div className="grid grid-cols-2 gap-3">
        <FieldGroup label="PRIMARY ELEMENT (Required)">
          <select value={pal.ElementType1 || "EPalElementType::None"} onChange={(e) => onUpdate({ ElementType1: e.target.value })} className="input-field">
            {ELEMENT_OPTIONS.map(([val, label]) => <option key={val} value={val}>{label}</option>)}
          </select>
        </FieldGroup>
        <FieldGroup label="SECONDARY ELEMENT (Optional)">
          <select value={pal.ElementType2 || "EPalElementType::None"} onChange={(e) => onUpdate({ ElementType2: e.target.value })} className="input-field">
            {ELEMENT_OPTIONS.map(([val, label]) => <option key={val} value={val}>{label}</option>)}
          </select>
        </FieldGroup>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div>
          <h3 className="text-muted-foreground text-xs font-bold uppercase tracking-widest mb-4">Base Attributes</h3>
          <div className="flex flex-col gap-4">
            <StatSlider label="HP"         value={pal.Hp ?? pal.BaseHP ?? 100} onChange={(v) => onUpdate({ Hp: v })} />
            <StatSlider label="MELEE ATTACK" value={pal.MeleeAttack ?? pal.BaseMelee ?? pal.BaseAtk ?? 100} onChange={(v) => onUpdate({ MeleeAttack: v })} />
            <StatSlider label="SHOT ATTACK" value={pal.ShotAttack ?? pal.BaseShot ?? 100} onChange={(v) => onUpdate({ ShotAttack: v })} />
            <StatSlider label="DEFENSE"    value={pal.Defense ?? pal.BaseDef ?? 100} onChange={(v) => onUpdate({ Defense: v })} />
            <StatSlider label="SUPPORT"    value={pal.Support ?? 100} onChange={(v) => onUpdate({ Support: v })} />
            <StatSlider label="CRAFT SPEED" value={pal.CraftSpeed ?? pal.BaseWorkSpeed ?? 100}  onChange={(v) => onUpdate({ CraftSpeed: v })} />
          </div>
        </div>

        <div>
          <h3 className="text-muted-foreground text-xs font-bold uppercase tracking-widest mb-4">Work Suitabilities</h3>
          <div className="grid grid-cols-2 gap-2">
            {WORK_SUITS.map((key) => {
              const rawKey = WORK_SUITABILITY_MAP[key] as keyof CreatorPal
              const val = (pal[rawKey] as number | undefined) ?? pal.WorkSuitabilities?.[rawKey] ?? 0
              const isChecked = val > 0
              return (
                <label key={key} className="flex items-center gap-2 cursor-pointer select-none">
                  <Checkbox checked={isChecked} onCheckedChange={(c) => onUpdate({ [rawKey]: c ? 1 : 0 })} className="border-border data-[state=checked]:bg-primary/50 data-[state=checked]:border-primary" />
                  <span className="text-xs text-foreground">{key}</span>
                </label>
              )
            })}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <FieldGroup label="Spawner Location ID">
          <SearchableSelect
            value={pal.SpawnLocationID || ""}
            onChange={(val) => onUpdate({ SpawnLocationID: val })}
            options={spawnerOptions}
            placeholder="Select spawner pool..."
            emptyText="No spawners found."
          />
        </FieldGroup>
        <FieldGroup label="Level Range">
          <div className="flex gap-2">
            <input type="number" value={pal.SpawnMinLevel || 1} onChange={(e) => onUpdate({ SpawnMinLevel: Number(e.target.value) })} className="input-field flex-1" placeholder="1" min={1} max={100} />
            <input type="number" value={pal.SpawnMaxLevel || 50} onChange={(e) => onUpdate({ SpawnMaxLevel: Number(e.target.value) })} className="input-field flex-1" placeholder="50" min={1} max={100} />
          </div>
        </FieldGroup>
        <FieldGroup label="Group Size Range">
          <div className="flex gap-2">
            <input type="number" value={pal.SpawnMinGroup || 1} onChange={(e) => onUpdate({ SpawnMinGroup: Number(e.target.value) })} className="input-field flex-1" placeholder="Min" min={1} />
            <input type="number" value={pal.SpawnMaxGroup || 1} onChange={(e) => onUpdate({ SpawnMaxGroup: Number(e.target.value) })} className="input-field flex-1" placeholder="Max" min={1} />
          </div>
        </FieldGroup>
      </div>

      <PalLearnset pal={pal} activeSkills={activeSkills} onUpdate={onUpdate} onOpenDialog={onOpenDialog} />

      <button
        onClick={() => setIsAdvancedOpen(!isAdvancedOpen)}
        className="flex items-center gap-2 text-xs font-semibold text-primary hover:text-primary/80 transition-colors cursor-pointer mr-auto"
      >
        {isAdvancedOpen ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
        {isAdvancedOpen ? "Hide Advanced Tuning" : "Show Advanced Tuning"}
      </button>

      {isAdvancedOpen && (
        <div className="grid grid-cols-2 gap-x-6 gap-y-4 border-t border-border/50 pt-4">
          <div className="flex flex-col gap-3 border border-border/50 p-4 rounded bg-background/30 shadow-inner">
            <SectionLabel>Speed & Movement</SectionLabel>
            <StatSlider label="WALK SPEED" value={pal.WalkSpeed ?? 180} onChange={(v) => onUpdate({ WalkSpeed: v })} max={1000} />
            <StatSlider label="RUN SPEED" value={pal.RunSpeed ?? 750} onChange={(v) => onUpdate({ RunSpeed: v })} max={2000} />
            <StatSlider label="SPRINT (RIDE)" value={pal.RideSprintSpeed ?? 1050} onChange={(v) => onUpdate({ RideSprintSpeed: v })} max={3000} />
            <StatSlider label="TRANSPORT" value={pal.TransportSpeed ?? 390} onChange={(v) => onUpdate({ TransportSpeed: v })} max={1500} />
          </div>
          
          <div className="flex flex-col gap-3 border border-border/50 p-4 rounded bg-background/30 shadow-inner">
            <SectionLabel>Breeding & World Values</SectionLabel>
            <StatSlider label="COMBI RANK" value={pal.CombiRank ?? 800} onChange={(v) => onUpdate({ CombiRank: v })} max={1500} />
            <StatSlider label="MALE RATIO %" value={pal.MaleProbability ?? 50} onChange={(v) => onUpdate({ MaleProbability: v })} max={100} />
            
            <div className="grid grid-cols-2 gap-3 mt-1">
              <FieldGroup label="Base Price">
                <input type="number" value={pal.Price ?? 3000} onChange={(e) => onUpdate({ Price: Number(e.target.value) })} className="input-field" min={0} />
              </FieldGroup>
              <FieldGroup label="Capture Rate Multiplier">
                <input type="number" step="0.1" value={pal.CaptureRateCorrect ?? 1.0} onChange={(e) => onUpdate({ CaptureRateCorrect: Number(e.target.value) })} className="input-field" min={0} />
              </FieldGroup>
            </div>
          </div>
          
          <div className="flex flex-col gap-3 border border-border/50 p-4 rounded bg-background/30 shadow-inner col-span-2">
            <SectionLabel>Physiology & Collision Capsule</SectionLabel>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-3">
                <FieldGroup label="Scale / Size Class">
                  <select value={pal.Size ?? "EPalSizeType::M"} onChange={(e) => onUpdate({ Size: e.target.value })} className="input-field">
                    {["XS", "S", "M", "L", "XL"].map(sz => (
                      <option key={sz} value={`EPalSizeType::${sz}`}>{sz}</option>
                    ))}
                  </select>
                </FieldGroup>
                
                <StatSlider label="CAPSULE HALF-HEIGHT" value={pal.MeshCapsuleHalfHeight ?? 110} onChange={(v) => onUpdate({ MeshCapsuleHalfHeight: v, MeshRelativeLocation: { X: pal.MeshRelativeLocation?.X ?? 0.0, Y: pal.MeshRelativeLocation?.Y ?? 0.0, Z: -v } })} min={10} max={500} />
                <StatSlider label="CAPSULE RADIUS" value={pal.MeshCapsuleRadius ?? 50} onChange={(v) => onUpdate({ MeshCapsuleRadius: v })} min={10} max={300} />
              </div>
              <div className="flex flex-col gap-3">
                <StatSlider label="RARITY" value={pal.Rarity ?? 4} onChange={(v) => onUpdate({ Rarity: v })} min={1} max={10} />
                <StatSlider label="FOOD AMOUNT" value={pal.FoodAmount ?? 3} onChange={(v) => onUpdate({ FoodAmount: v })} min={1} max={10} />
                <StatSlider label="STAMINA" value={pal.Stamina ?? 100} onChange={(v) => onUpdate({ Stamina: v })} max={500} />
                
                <StatSlider label="MESH Z-TRANSLATION" value={pal.MeshRelativeLocation?.Z ?? -110} onChange={(v) => onUpdate({ MeshRelativeLocation: { X: pal.MeshRelativeLocation?.X ?? 0.0, Y: pal.MeshRelativeLocation?.Y ?? 0.0, Z: v } })} min={-500} max={0} />
              </div>
            </div>
          </div>
          
          <div className="flex flex-col gap-3 border border-border/50 p-4 rounded bg-background/30 shadow-inner col-span-2">
            <SectionLabel>Paldeck / Tribe Configuration</SectionLabel>
            <div className="grid grid-cols-2 gap-4">
              <FieldGroup label="Paldeck Classification">
                <select value={pal.PaldexType ?? "Species"} onChange={(e) => onUpdate({ PaldexType: e.target.value })} className="input-field">
                  <option value="Species">New Standalone Species (Unique Tribe ID)</option>
                  <option value="Variant">Subspecies Variant (Share Parent Tribe)</option>
                </select>
              </FieldGroup>
              <div className="flex flex-col justify-end text-xs text-muted-foreground leading-relaxed italic p-1">
                {pal.PaldexType === "Variant" 
                  ? `This Pal will share a single Paldeck card with its parent template (${pal.TemplateID}).`
                  : `This Pal gets a dedicated, completely separate entry card in your Paldeck!`
                }
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center justify-end gap-3 mt-2 border-t border-border pt-4">
        <button
          onClick={handleRefreshBP}
          className="flex items-center gap-1.5 px-3 py-2 rounded border border-primary text-primary text-xs font-semibold hover:bg-primary/10 transition-colors cursor-pointer mr-auto"
          title="Forcefully regenerate and patch the Actor Blueprint for this Pal"
        >
          <RefreshCw className="size-3.5" />
          Refresh Blueprint
        </button>
        <button
          onClick={() => onDelete(pal.CharacterID)}
          className="flex items-center gap-1.5 px-3 py-2 rounded border border-status-error text-status-error text-xs font-semibold hover:bg-status-error/10 transition-colors cursor-pointer"
        >
          <Trash2 className="size-3.5" />
          Delete Pal
        </button>
        <button
          onClick={handleSave}
          className="flex items-center gap-1.5 px-4 py-2 rounded bg-primary text-primary-foreground text-xs font-bold uppercase tracking-wider hover:bg-primary/90 transition-colors cursor-pointer shadow"
        >
          Save Changes
        </button>
      </div>

      {diagnosticError && <DiagnosticsModal errorText={diagnosticError} onClose={() => setDiagnosticError(null)} />}
      <NotificationToast notifications={notifications} onDismiss={dismissNotification} />
    </div>
  )
}