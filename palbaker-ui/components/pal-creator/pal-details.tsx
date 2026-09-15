"use client"

import { useState, useMemo } from "react"
import { type CreatorPal, type ActiveSkill } from "@/lib/mock-data"
import { PalCreatorAPI } from "@/lib/data-service"
import { Checkbox } from "@/components/ui/checkbox"
import { Trash2, RefreshCw, Plus, MapPin, Award } from "lucide-react"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { SpawnerMap } from "./spawner-map"
import { PalLearnset } from "./pal-learnset"
import { 
  FieldGroup, 
  StatSlider, 
  SectionLabel, 
  WORK_SUITS, 
  WORK_SUITABILITY_MAP, 
  ELEMENT_OPTIONS,
  WEAPON_EFFECT_OPTIONS,
  NIAGARA_EFFECT_LIST,
  CUSTOMIZABLE_WEAPON_SKILLS,
  FUNNEL_PARTNER_SKILLS
} from "./pal-helpers"

import { DiagnosticsModal } from "@/components/common/diagnostics-modal"
import { useNotifications } from "../mod-manager/mod-card-expanded/use-notifications"
import { NotificationToast } from "../mod-manager/mod-card-expanded/notification-toast"
import { SearchableSelect } from "@/components/ui/searchable-select"
import { cn } from "@/lib/utils"


interface Props {
  pal: CreatorPal
  spawners: Record<string, string>
  activeSkills: Record<string, ActiveSkill>
  partnerSkills?: Record<string, string>
  items?: Record<string, any>
  cageFields?: string[]
  bossSpawnerPresets?: Record<string, any>
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

const DEFAULT_CAGE_FIELDS = ["Grass", "Desert", "Viking", "Snow", "Volcano", "Grass2", "Desert1", "Viking1"]

export function PalDetails({ 
  pal, spawners, activeSkills, partnerSkills = {}, items = {}, cageFields = [], bossSpawnerPresets = {}, 
  onUpdate, onOpenDialog, onSave, onDelete, templates, palNames 
}: Props) {
  const [diagnosticError, setDiagnosticError] = useState<string | null>(null)
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
      showNotification("Blueprints regenerated & retargeted successfully! 🦊✨", "success", "Blueprint Patched")
    } catch (err: any) {
      console.error("Blueprint refresh failed:", err)
      setDiagnosticError(String(err.message || err))
    }
  }

 const niagaraOptions = useMemo(() => {
    return NIAGARA_EFFECT_LIST.map((path) => {
      const parts = path.split("/")
      const name = parts[parts.length - 1].replace("NS_CommonSkill_", "")
      const category = parts[parts.length - 2]
      return {
        value: path,
        label: `${name} (${category})`
      }
    })
  }, [])

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

  const partnerSkillOptions = useMemo(() => {
    return Object.entries(partnerSkills).map(([display, actual]) => ({
      value: actual,
      label: display
    })).sort((a, b) => a.label.localeCompare(b.label))
  }, [partnerSkills])

  const saddleOptions = useMemo(() => {
    const rawItems = Object.values(items)
    const unlockItems = rawItems.filter((it: any) => 
      typeof it.id === "string" && it.id.startsWith("SkillUnlock_")
    )

    let list: { value: string; label: string }[] = []

    if (unlockItems.length === 0) {
      // Fallback list when items cache isn't fully extracted
      const fallbacks = [
        "SkillUnlock_Anubis", "SkillUnlock_Kitsunebi", "SkillUnlock_WeaselDragon",
        "SkillUnlock_Deer", "SkillUnlock_Boar", "SkillUnlock_Eagle",
        "SkillUnlock_KingAlpaca", "SkillUnlock_FairyDragon", "SkillUnlock_AmaterasuWolf"
      ]
      list = fallbacks.map(f => ({ value: f, label: `${f.replace("SkillUnlock_", "")} Harness/Saddle (${f})` }))
    } else {
      list = unlockItems.map((it: any) => ({
        value: it.id,
        label: `${it.name} (${it.id})`
      })).sort((a, b) => a.label.localeCompare(b.label))
    }

    list.unshift({ value: "None", label: "None (No Saddle / Harness Required)" })

    if (pal.SaddleItem && pal.SaddleItem !== "None" && !list.some(opt => opt.value === pal.SaddleItem)) {
      list.push({ value: pal.SaddleItem, label: `${pal.SaddleItem} (Custom)` })
    }

    return list
  }, [items, pal.SaddleItem])

  const itemOptions = useMemo(() => {
    const rawItems = Object.values(items)
    if (rawItems.length === 0) {
      return [
        { value: "Money", label: "Gold Coin (Money)" },
        { value: "Diamond", label: "Diamond" },
        { value: "Ruby", label: "Ruby" },
        { value: "Sapphire", label: "Sapphire" },
        { value: "Eemerald", label: "Emerald (Eemerald)" },
        { value: "Quartz", label: "Pure Quartz" },
        { value: "Pal_crystal_S", label: "Paldium Fragment (Pal_crystal_S)" },
        { value: "Bone", label: "Bone" },
        { value: "Leather", label: "Leather" },
        { value: "Wool", label: "Wool" }
      ]
    }
    return rawItems.map((it: any) => ({
      value: it.id,
      label: `${it.name} (${it.id})`
    }))
  }, [items])

  const availableCageFields = cageFields.length > 0 ? cageFields : DEFAULT_CAGE_FIELDS

  // Handlers for Breeding Combos
  const addBreedingCombo = () => {
    const next = [...(pal.BreedingCombos || []), { parentA: "Anubis", parentB: "PinkCat" }]
    onUpdate({ BreedingCombos: next })
  }

  const removeBreedingCombo = (idx: number) => {
    const next = (pal.BreedingCombos || []).filter((_, i) => i !== idx)
    onUpdate({ BreedingCombos: next })
  }

  // Handlers for Item Drops
  const addItemDrop = () => {
    const next = [...(pal.ItemDrops || []), { itemId: "Money", rate: 100.0, min: 10, max: 50 }]
    onUpdate({ ItemDrops: next })
  }

  const removeItemDrop = (idx: number) => {
    const next = (pal.ItemDrops || []).filter((_, i) => i !== idx)
    onUpdate({ ItemDrops: next })
  }

  // Handlers for Field Boss Locations
  const addFieldBossPin = () => {
    const next = [...(pal.FieldBossSpawns || []), { level: 50, x: -443191.0, y: -116597.0, z: 10791.0, adds: [] }]
    onUpdate({ FieldBossSpawns: next })
  }

  const removeFieldBossPin = (idx: number) => {
    const next = (pal.FieldBossSpawns || []).filter((_, i) => i !== idx)
    onUpdate({ FieldBossSpawns: next })
  }

  const activeWildSpawners = pal.WildSpawners ?? (
    pal.SpawnLocationID ? [{
      SpawnLocationID: pal.SpawnLocationID,
      SpawnWeight: pal.SpawnWeight ?? 40,
      SpawnMinLevel: pal.SpawnMinLevel ?? 2,
      SpawnMaxLevel: pal.SpawnMaxLevel ?? 5,
      SpawnMinGroup: pal.SpawnMinGroup ?? 1,
      SpawnMaxGroup: pal.SpawnMaxGroup ?? 3
    }] : []
  )

  const addWildSpawner = () => {
    const next = [...activeWildSpawners, {
      SpawnLocationID: "1_1_plain_begginer",
      SpawnWeight: 40,
      SpawnMinLevel: 2,
      SpawnMaxLevel: 5,
      SpawnMinGroup: 1,
      SpawnMaxGroup: 3
    }]
    onUpdate({ WildSpawners: next })
  }

  const removeWildSpawner = (idx: number) => {
    const next = activeWildSpawners.filter((_, i) => i !== idx)
    onUpdate({ WildSpawners: next })
  }

  const updateWildSpawner = (idx: number, patch: Partial<typeof activeWildSpawners[0]>) => {
    const next = [...activeWildSpawners]
    next[idx] = { ...next[idx], ...patch }
    onUpdate({ WildSpawners: next })
  }


  return (
    <div className="border-t border-border bg-muted/30 p-5 flex flex-col gap-5">
      
      <Tabs defaultValue="general" className="w-full">
        <TabsList className="w-full justify-start border-b border-border rounded-none pb-0 mb-4 bg-transparent gap-6 h-10 px-2 overflow-x-auto">
          <TabsTrigger value="general" className="rounded-none border-b-2 data-[state=active]:border-primary data-[state=inactive]:border-transparent bg-transparent pb-2 h-full text-xs uppercase tracking-wider font-bold">General & Stats</TabsTrigger>
          <TabsTrigger value="combat" className="rounded-none border-b-2 data-[state=active]:border-primary data-[state=inactive]:border-transparent bg-transparent pb-2 h-full text-xs uppercase tracking-wider font-bold">Combat & Skills</TabsTrigger>
          <TabsTrigger value="ecology" className="rounded-none border-b-2 data-[state=active]:border-primary data-[state=inactive]:border-transparent bg-transparent pb-2 h-full text-xs uppercase tracking-wider font-bold">Spawning & Ecology</TabsTrigger>
          <TabsTrigger value="loot" className="rounded-none border-b-2 data-[state=active]:border-primary data-[state=inactive]:border-transparent bg-transparent pb-2 h-full text-xs uppercase tracking-wider font-bold">Loot & Drops</TabsTrigger>
          <TabsTrigger value="variants" className="rounded-none border-b-2 data-[state=active]:border-primary data-[state=inactive]:border-transparent bg-transparent pb-2 h-full text-xs uppercase tracking-wider font-bold">Bosses & Predators</TabsTrigger>
        </TabsList>

        {/* TAB 1: GENERAL & STATS */}
        <TabsContent value="general" className="flex flex-col gap-5">
          <div className="grid grid-cols-4 gap-3">
            <FieldGroup label="CHARACTER ID">
              <input value={pal.CharacterID} onChange={() => {}} disabled className="input-field disabled:opacity-50 disabled:cursor-not-allowed font-mono text-xs" />
            </FieldGroup>
            <FieldGroup label="DISPLAY NAME">
              <input value={pal.Name} onChange={(e) => onUpdate({ Name: e.target.value })} className="input-field" />
            </FieldGroup>
            <FieldGroup label="PARENT TEMPLATE">
              <SearchableSelect value={pal.TemplateID} onChange={(val) => onUpdate({ TemplateID: val })} options={parentTemplateOptions} placeholder="Select template..." />
            </FieldGroup>
            <FieldGroup label="PALDECK INDEX">
              <div className="flex gap-1.5">
                <input type="number" value={pal.ZukanIndex || -1} onChange={(e) => onUpdate({ ZukanIndex: Number(e.target.value) })} className="input-field flex-1" />
                <input value={pal.ZukanIndexSuffix || ""} onChange={(e) => onUpdate({ ZukanIndexSuffix: e.target.value })} className="input-field w-14 text-center font-bold" placeholder="Sfx" maxLength={2} />
              </div>
            </FieldGroup>
          </div>

          <FieldGroup label="DESCRIPTION">
            <textarea value={pal.Description} onChange={(e) => onUpdate({ Description: e.target.value })} className="input-field min-h-12 py-1.5 text-xs" rows={2} />
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
              <SectionLabel className="mb-4">Base Combat Stats</SectionLabel>
              <div className="flex flex-col gap-4">
                <StatSlider label="HP"         value={pal.Hp ?? pal.BaseHP ?? 100} onChange={(v) => onUpdate({ Hp: v })} max={250} />
                <StatSlider label="MELEE ATTACK" value={pal.MeleeAttack ?? pal.BaseMelee ?? pal.BaseAtk ?? 100} onChange={(v) => onUpdate({ MeleeAttack: v })} max={250} />
                <StatSlider label="SHOT ATTACK" value={pal.ShotAttack ?? pal.BaseShot ?? 100} onChange={(v) => onUpdate({ ShotAttack: v })} max={250} />
                <StatSlider label="DEFENSE"    value={pal.Defense ?? pal.BaseDef ?? 100} onChange={(v) => onUpdate({ Defense: v })} max={250} />
                <StatSlider label="SUPPORT"    value={pal.Support ?? 100} onChange={(v) => onUpdate({ Support: v })} max={250} />
                <StatSlider label="CRAFT SPEED" value={pal.CraftSpeed ?? pal.BaseWorkSpeed ?? 100}  onChange={(v) => onUpdate({ CraftSpeed: v })} max={250} />
              </div>
            </div>

            <div>
              <SectionLabel className="mb-4">Work Suitabilities</SectionLabel>
              <div className="grid grid-cols-2 gap-2">
                {WORK_SUITS.map((key) => {
                  const rawKey = WORK_SUITABILITY_MAP[key] as keyof CreatorPal
                  const val = (pal[rawKey] as number | undefined) ?? pal.WorkSuitabilities?.[rawKey] ?? 0
                  return (
                    <label key={key} className="flex items-center gap-2 cursor-pointer select-none">
                      <Checkbox checked={val > 0} onCheckedChange={(c) => onUpdate({ [rawKey]: c ? 1 : 0 })} className="data-[state=checked]:bg-primary/50 data-[state=checked]:border-primary" />
                      <span className="text-xs text-foreground">{key}</span>
                      {val > 0 && (
                        <input type="number" min={1} max={5} value={val} onChange={(e) => onUpdate({ [rawKey]: parseInt(e.target.value) || 1 })} className="ml-auto w-10 h-5 text-xs text-center bg-muted border border-border rounded" />
                      )}
                    </label>
                  )
                })}
              </div>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-x-6 gap-y-4 border-t border-border/50 pt-4">
            <div className="flex flex-col gap-3 border border-border/50 p-4 rounded bg-background/30 shadow-inner">
              <SectionLabel>Speed & Movement</SectionLabel>
              <StatSlider label="WALK SPEED" value={pal.WalkSpeed ?? 180} onChange={(v) => onUpdate({ WalkSpeed: v })} max={1000} />
              <StatSlider label="RUN SPEED" value={pal.RunSpeed ?? 750} onChange={(v) => onUpdate({ RunSpeed: v })} max={2000} />
              <StatSlider label="SPRINT (RIDE)" value={pal.RideSprintSpeed ?? 1050} onChange={(v) => onUpdate({ RideSprintSpeed: v })} max={3000} />
              <StatSlider label="TRANSPORT" value={pal.TransportSpeed ?? 390} onChange={(v) => onUpdate({ TransportSpeed: v })} max={1500} />
            </div>
            
            <div className="flex flex-col gap-3 border border-border/50 p-4 rounded bg-background/30 shadow-inner">
              <SectionLabel>Physiology & Collision</SectionLabel>
              <div className="flex flex-col gap-3">
                <FieldGroup label="Scale / Size Class">
                  <select value={pal.Size ?? "EPalSizeType::M"} onChange={(e) => onUpdate({ Size: e.target.value })} className="input-field">
                    {["XS", "S", "M", "L", "XL"].map(sz => <option key={sz} value={`EPalSizeType::${sz}`}>{sz}</option>)}
                  </select>
                </FieldGroup>
                <StatSlider label="CAPSULE HALF-HEIGHT" value={pal.MeshCapsuleHalfHeight ?? 100} onChange={(v) => onUpdate({ MeshCapsuleHalfHeight: v, MeshRelativeLocation: { X: pal.MeshRelativeLocation?.X ?? 0.0, Y: pal.MeshRelativeLocation?.Y ?? 0.0, Z: -v } })} min={10} max={500} />
                <StatSlider label="CAPSULE RADIUS" value={pal.MeshCapsuleRadius ?? 40} onChange={(v) => onUpdate({ MeshCapsuleRadius: v })} min={10} max={300} />
              </div>
            </div>
          </div>
        </TabsContent>

        {/* TAB 2: COMBAT & SKILLS */}
        <TabsContent value="combat" className="flex flex-col gap-5">
          <PalLearnset pal={pal} activeSkills={activeSkills} onUpdate={onUpdate} onOpenDialog={onOpenDialog} />
          
          <div className="border border-border/50 p-4 rounded bg-background/30 shadow-inner flex flex-col gap-4">
            <SectionLabel>Partner Skill & Mount Tool</SectionLabel>
            <div className="grid grid-cols-3 gap-4 border-b border-border/40 pb-4">
              <FieldGroup label="Saddle / Tool Unlock Item">
                <SearchableSelect
                  value={pal.SaddleItem || "None"}
                  onChange={(val) => onUpdate({ SaddleItem: val })}
                  options={saddleOptions}
                  placeholder="Select Saddle / Unlock Item..."
                  emptyText="No saddle items found."
                />
              </FieldGroup>
              <FieldGroup label="Partner Skill Identifier">
                <SearchableSelect 
                  value={pal.PartnerSkill || "None"} 
                  onChange={(val) => onUpdate({ PartnerSkill: val })} 
                  options={partnerSkillOptions} 
                  placeholder="Select Partner Skill..." 
                  emptyText="No skills found." 
                />
              </FieldGroup>
              <FieldGroup label="Partner Skill Display Name">
                <input 
                  value={pal.PartnerSkillName || ""} 
                  onChange={(e) => onUpdate({ PartnerSkillName: e.target.value })} 
                  className="input-field" 
                  placeholder="e.g. Fox's Fire" 
                />
              </FieldGroup>
            </div>

             {/* Custom Partner Weapon Properties */}
             {CUSTOMIZABLE_WEAPON_SKILLS.includes(pal.PartnerSkill || "") && (
            <div className="border-t border-border/40 pt-4 mt-2 flex flex-col gap-4">
              <span className="text-xs font-bold text-primary font-mono uppercase tracking-wider">
                Weapon Attack & Visual VFX Tuning
              </span>
              
              <div className="grid grid-cols-3 gap-4">
                <FieldGroup label="Weapon Attack Element">
                  <select
                    value={pal.PartnerWeaponElement || "EPalElementType::Fire"}
                    onChange={(e) => onUpdate({ PartnerWeaponElement: e.target.value })}
                    className="input-field"
                  >
                    {ELEMENT_OPTIONS.map(([val, label]) => (
                      <option key={val} value={val}>{label}</option>
                    ))}
                  </select>
                </FieldGroup>

                <FieldGroup label="Inflicted Status Effect">
                  <select
                    value={pal.PartnerWeaponEffectType || "EPalAdditionalEffectType::Burn"}
                    onChange={(e) => onUpdate({ PartnerWeaponEffectType: e.target.value })}
                    className="input-field"
                  >
                    {WEAPON_EFFECT_OPTIONS.map(([val, label]) => (
                      <option key={val} value={val}>{label}</option>
                    ))}
                  </select>
                </FieldGroup>

                <FieldGroup label="Niagara Projectile VFX">
                  <SearchableSelect
                    value={pal.PartnerWeaponNiagara || "Pal/Content/Pal/Effect/Skill/FlameThrower/NS_CommonSkill_Flamethrower"}
                    onChange={(val) => onUpdate({ PartnerWeaponNiagara: val })}
                    options={niagaraOptions}
                    placeholder="Search Niagara VFX..."
                    emptyText="No effect found."
                  />
                </FieldGroup>
              </div>
            </div>
            )}

            
            {/* Custom Funnel Companion Properties */}
            <div className="border-t border-border/40 pt-4 mt-2 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-primary font-mono uppercase tracking-wider">
                  Hovering Funnel Companion
                </span>
                <Checkbox 
                  checked={!!pal.HasFunnel} 
                  onCheckedChange={(c) => onUpdate({ HasFunnel: !!c })} 
                />
              </div>
              
              {!!pal.HasFunnel && (
                <div className="grid grid-cols-2 gap-4">
                  <FieldGroup label="Funnel Attack Projectile (Waza ID)">
                    <SearchableSelect
                      value={pal.FunnelWazaID || "Funnel_DreamDemon"}
                      onChange={(val) => onUpdate({ FunnelWazaID: val })}
                      options={[
                        { value: "Funnel_DreamDemon", label: "Daedream Base (Funnel_DreamDemon)" },
                        { value: "Funnel_RaijinDaughter", label: "Dazzi Base (Funnel_RaijinDaughter)" },
                        ...Object.values(activeSkills).map(s => ({ value: s.id, label: `${s.id.replace(/_/g, " ")} (${s.element})` }))
                      ]}
                      placeholder="Search Attack Skills..."
                    />
                  </FieldGroup>
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <FieldGroup label="Active Player Stat Buff (While in Party)">
                <select 
                  value={pal.PartnerPlayerBuff || "None"} 
                  onChange={(e) => onUpdate({ PartnerPlayerBuff: e.target.value as any })} 
                  className="input-field cursor-pointer"
                >
                  <option value="None">None</option>
                  <option value="Attack">Player Attack UP</option>
                  <option value="Defense">Player Defense UP</option>
                  <option value="WorkSpeed">Player Work Speed UP</option>
                </select>
              </FieldGroup>
              
              <FieldGroup label="Base Camp Suitability Buff (For All Pals)">
                <select 
                  value={pal.PartnerCampBuff || "None"} 
                  onChange={(e) => onUpdate({ PartnerCampBuff: e.target.value as any })} 
                  className="input-field cursor-pointer"
                >
                  <option value="None">None</option>
                  <option value="Handcraft">Handiwork Rank UP</option>
                  <option value="Transport">Transporting Rank UP</option>
                  <option value="Mining">Mining Rank UP</option>
                  <option value="Lumbering">Lumbering Rank UP</option>
                  <option value="Kindling">Kindling Rank UP</option>
                  <option value="Watering">Watering Rank UP</option>
                  <option value="Gathering">Gathering Rank UP</option>
                  <option value="Planting">Planting Rank UP</option>
                  <option value="Medicine">Medicine Rank UP</option>
                  <option value="Electricity">Electricity Rank UP</option>
                  <option value="Cooling">Cooling Rank UP</option>
                  <option value="Farming">Farming Rank UP</option>
                </select>
              </FieldGroup>
            </div>

            <div className="flex flex-col gap-2 mt-2">
              <div className="flex items-center justify-between">
                <FieldGroup label="Periodic Item Drops (While in Party)">
                  <span className="text-[10px] text-muted-foreground -mt-1">Pal will occasionally dig up or drop these items while traveling.</span>
                </FieldGroup>
                <button 
                  onClick={() => onUpdate({ PartnerDropItems: [...(pal.PartnerDropItems || []), "Money"] })}
                  className="flex items-center gap-1.5 px-2 py-1 rounded border border-primary text-primary text-xs font-semibold hover:bg-primary/10 cursor-pointer"
                >
                  <Plus className="size-3" /> Add Item
                </button>
              </div>
              
              <div className="flex flex-col gap-2">
                {(pal.PartnerDropItems || []).length === 0 ? (
                  <p className="text-muted-foreground text-xs italic">No periodic drop items assigned.</p>
                ) : (
                  pal.PartnerDropItems!.map((itemId, idx) => (
                    <div key={idx} className="flex items-center gap-2 bg-muted/40 p-1.5 rounded border border-border">
                      <div className="flex-1">
                        <SearchableSelect 
                          value={itemId}
                          onChange={(val) => {
                            const next = [...pal.PartnerDropItems!]
                            next[idx] = val
                            onUpdate({ PartnerDropItems: next })
                          }}
                          options={itemOptions}
                          placeholder="Select Item..."
                        />
                      </div>
                      <button 
                        onClick={() => onUpdate({ PartnerDropItems: pal.PartnerDropItems!.filter((_, i) => i !== idx) })} 
                        className="text-muted-foreground hover:text-status-error p-1 cursor-pointer"
                      >
                        <Trash2 className="size-4" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </TabsContent>

        {/* TAB 3: SPAWNING & ECOLOGY */}
        <TabsContent value="ecology" className="flex flex-col gap-5">
          <div className="border border-border/50 p-4 rounded bg-background/30 shadow-inner flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <SectionLabel>Wild Spawner Injections</SectionLabel>
              <button onClick={addWildSpawner} className="flex items-center gap-1.5 px-2 py-1 rounded border border-primary text-primary text-xs font-semibold hover:bg-primary/10 cursor-pointer">
                <Plus className="size-3" /> Add Spawner
              </button>
            </div>

            <div className="flex flex-col gap-3">
              {activeWildSpawners.length === 0 ? (
                <p className="text-muted-foreground text-xs italic">No wild spawners assigned. This Pal will not spawn naturally.</p>
              ) : (
                activeWildSpawners.map((spawner, idx) => (
                  <div key={idx} className="bg-muted/40 p-3 rounded border border-border flex flex-col gap-4 relative">
                    <button 
                      onClick={() => removeWildSpawner(idx)} 
                      className="absolute top-3 right-3 text-muted-foreground hover:text-status-error p-1 cursor-pointer transition-colors z-10"
                    >
                      <Trash2 className="size-4" />
                    </button>
                    
                    <div className="grid grid-cols-2 gap-4 pr-8">
                      <FieldGroup label="Target Spawner Map Area">
                        <SearchableSelect 
                          value={spawner.SpawnLocationID || ""} 
                          onChange={(val) => updateWildSpawner(idx, { SpawnLocationID: val })} 
                          options={spawnerOptions} 
                        />
                      </FieldGroup>
                      <FieldGroup label="Spawn Weight (1-100)">
                        <input type="number" min="1" max="100" value={spawner.SpawnWeight ?? 40} onChange={(e) => updateWildSpawner(idx, { SpawnWeight: Number(e.target.value) })} className="input-field" />
                      </FieldGroup>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <FieldGroup label="Level Range (Min - Max)">
                        <div className="flex gap-2">
                          <input type="number" value={spawner.SpawnMinLevel || 1} onChange={(e) => updateWildSpawner(idx, { SpawnMinLevel: Number(e.target.value) })} className="input-field flex-1" min={1} />
                          <input type="number" value={spawner.SpawnMaxLevel || 50} onChange={(e) => updateWildSpawner(idx, { SpawnMaxLevel: Number(e.target.value) })} className="input-field flex-1" min={1} />
                        </div>
                      </FieldGroup>
                      <FieldGroup label="Group Size (Min - Max)">
                        <div className="flex gap-2">
                          <input type="number" value={spawner.SpawnMinGroup || 1} onChange={(e) => updateWildSpawner(idx, { SpawnMinGroup: Number(e.target.value) })} className="input-field flex-1" min={1} />
                          <input type="number" value={spawner.SpawnMaxGroup || 1} onChange={(e) => updateWildSpawner(idx, { SpawnMaxGroup: Number(e.target.value) })} className="input-field flex-1" min={1} />
                </div>
              </FieldGroup>
            </div>
          </div>
        )))}
          </div>
        </div>

          {/* Syndicate Cage Spawns */}
          <div className="border border-border/50 p-4 rounded bg-background/30 shadow-inner flex flex-col gap-3">
            <SectionLabel>Syndicate Camp Cage Rescues</SectionLabel>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Select which enemy bandit camps can have this Pal locked inside their rescue cages:
            </p>
            <div className="flex flex-wrap gap-2 pt-1">
              {availableCageFields.map((field) => {
                const isSelected = (pal.CageSpawns || []).includes(field)
                return (
                  <button
                    key={field}
                    type="button"
                    onClick={() => {
                      const current = pal.CageSpawns || []
                      const next = isSelected ? current.filter(f => f !== field) : [...current, field]
                      onUpdate({ CageSpawns: next })
                    }}
                    className={cn(
                      "px-3 py-1.5 rounded border text-xs font-medium transition-colors cursor-pointer",
                      isSelected ? "bg-primary/20 border-primary text-primary font-bold shadow-sm" : "bg-muted/40 border-border text-muted-foreground hover:text-foreground"
                    )}
                  >
                    {field} {isSelected ? "✓" : "+"}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Unique Breeding Combos */}
          <div className="border border-border/50 p-4 rounded bg-background/30 shadow-inner flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <SectionLabel>Unique Breeding Recipes</SectionLabel>
              <button onClick={addBreedingCombo} className="flex items-center gap-1.5 px-2 py-1 rounded border border-primary text-primary text-xs font-semibold hover:bg-primary/10 cursor-pointer">
                <Plus className="size-3" /> Add Combo
              </button>
            </div>
            <div className="flex flex-col gap-2">
              {(pal.BreedingCombos || []).length === 0 ? (
                <p className="text-muted-foreground text-xs italic">No custom breeding recipes assigned. The Pal will be bred using game formula calculations.</p>
              ) : (
                pal.BreedingCombos!.map((combo, idx) => (
                  <div key={idx} className="flex items-center gap-3 bg-muted/40 p-2 rounded border border-border">
                    <div className="flex-1">
                      <SearchableSelect 
                        value={combo.parentA} 
                        onChange={(val) => {
                          const next = [...pal.BreedingCombos!]
                          next[idx].parentA = val
                          onUpdate({ BreedingCombos: next })
                        }} 
                        options={parentTemplateOptions} 
                        placeholder="Parent A"
                      />
                    </div>
                    <span className="text-xs text-muted-foreground font-bold">+</span>
                    <div className="flex-1">
                      <SearchableSelect 
                        value={combo.parentB} 
                        onChange={(val) => {
                          const next = [...pal.BreedingCombos!]
                          next[idx].parentB = val
                          onUpdate({ BreedingCombos: next })
                        }} 
                        options={parentTemplateOptions} 
                        placeholder="Parent B"
                      />
                    </div>
                    <span className="text-xs text-primary font-bold truncate max-w-[140px]">= {pal.Name || pal.CharacterID}</span>
                    <button onClick={() => removeBreedingCombo(idx)} className="text-muted-foreground hover:text-status-error p-1 cursor-pointer">
                      <Trash2 className="size-4" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </TabsContent>

        {/* TAB 4: LOOT & DROPS */}
        <TabsContent value="loot" className="flex flex-col gap-5">
           <div className="border border-border/50 p-4 rounded bg-background/30 shadow-inner flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <SectionLabel>Item Drops & Defeat Rewards</SectionLabel>
              <button onClick={addItemDrop} className="flex items-center gap-1.5 px-2 py-1 rounded border border-primary text-primary text-xs font-semibold hover:bg-primary/10 cursor-pointer">
                <Plus className="size-3" /> Add Drop
              </button>
            </div>
            <div className="flex flex-col gap-2">
              {(pal.ItemDrops || []).length === 0 ? (
                <p className="text-muted-foreground text-xs italic">No custom drops assigned. The Pal will use cloned parent drops.</p>
              ) : (
                pal.ItemDrops!.map((drop, idx) => (
                  <div key={idx} className="grid grid-cols-[1.5fr_1fr_1fr_1fr_32px] gap-2 items-center bg-muted/40 p-2 rounded border border-border">
                    <SearchableSelect 
                      value={drop.itemId}
                      onChange={(val) => {
                        const next = [...pal.ItemDrops!]
                        next[idx].itemId = val
                        onUpdate({ ItemDrops: next })
                      }}
                      options={itemOptions}
                      placeholder="Select Drop Item..."
                    />
                    <div className="flex items-center gap-1">
                      <input 
                        type="number" 
                        value={drop.rate} 
                        onChange={(e) => {
                          const next = [...pal.ItemDrops!]
                          next[idx].rate = parseFloat(e.target.value) || 0
                          onUpdate({ ItemDrops: next })
                        }}
                        className="input-field" 
                        placeholder="Rate %"
                        step="0.1"
                      />
                      <span className="text-xs text-muted-foreground">%</span>
                    </div>
                    <input 
                      type="number" 
                      value={drop.min} 
                      onChange={(e) => {
                        const next = [...pal.ItemDrops!]
                        next[idx].min = parseInt(e.target.value) || 1
                        onUpdate({ ItemDrops: next })
                      }}
                      className="input-field" 
                      placeholder="Min"
                    />
                    <input 
                      type="number" 
                      value={drop.max} 
                      onChange={(e) => {
                        const next = [...pal.ItemDrops!]
                        next[idx].max = parseInt(e.target.value) || 1
                        onUpdate({ ItemDrops: next })
                      }}
                      className="input-field" 
                      placeholder="Max"
                    />
                    <button onClick={() => removeItemDrop(idx)} className="text-muted-foreground hover:text-status-error p-1 cursor-pointer justify-self-end">
                      <Trash2 className="size-4" />
                    </button>
                  </div>
                ))
              )}
            </div>

            {/* Bounty Token Item Generator */}
            <div className="flex items-center justify-between border-t border-border/40 pt-3 mt-2">
              <div className="flex flex-col">
                <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
                  <Award className="size-3.5 text-status-warning" />
                  Generate Alpha Boss Defeat Token
                </span>
                <span className="text-[11px] text-muted-foreground">
                  Creates a permanent Bounty Token item that drops on first defeat, matching high-tier mod reward standards.
                </span>
              </div>
              <Checkbox 
                checked={!!pal.GenerateBountyToken} 
                onCheckedChange={(c) => onUpdate({ GenerateBountyToken: !!c })} 
              />
            </div>
          </div>
        </TabsContent>

        {/* TAB 5: BOSS & PREDATOR VARIANTS */}
        <TabsContent value="variants" className="flex flex-col gap-5">
          {/* Alpha Boss Panel */}
          <div className="border border-border/50 p-4 rounded bg-background/30 shadow-inner flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div className="flex flex-col">
                <span className="text-sm font-bold text-foreground">Generate Alpha Boss Variant</span>
                <span className="text-xs text-muted-foreground">Compiles BP_{pal.CharacterID}_BOSS with a boss gauge, FieldBoss music, and larger 3D scale.</span>
              </div>
              <Checkbox 
                checked={pal.GenerateBoss !== false} 
                onCheckedChange={(c) => onUpdate({ GenerateBoss: !!c })} 
              />
            </div>

            {pal.GenerateBoss !== false && (
              <div className="grid grid-cols-2 gap-4 border-t border-border/40 pt-3">
                <FieldGroup label="Boss Prefix Title">
                  <input 
                    value={pal.BossPrefix || "Gilded Monarch"} 
                    onChange={(e) => onUpdate({ BossPrefix: e.target.value })} 
                    className="input-field" 
                    placeholder="e.g. Queen of the Oasis" 
                  />
                </FieldGroup>
                <StatSlider 
                  label="BOSS HP MULTIPLIER" 
                  value={pal.BossHPMultiplier ?? 5} 
                  onChange={(v) => onUpdate({ BossHPMultiplier: v })} 
                  min={1} 
                  max={20} 
                />
              </div>
            )}
          </div>

          {/* Rampaging Predator Panel */}
          <div className="border border-border/50 p-4 rounded bg-background/30 shadow-inner flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div className="flex flex-col">
                <span className="text-sm font-bold text-foreground">Generate Rampaging Predator Variant</span>
                <span className="text-xs text-muted-foreground">Compiles BP_{pal.CharacterID}_PREDATOR with red Niagara auras, uncapturable traits, and hyper-aggressive AI.</span>
              </div>
              <Checkbox 
                checked={!!pal.GeneratePredator} 
                onCheckedChange={(c) => onUpdate({ GeneratePredator: !!c })} 
              />
            </div>

            {!!pal.GeneratePredator && (
              <div className="grid grid-cols-2 gap-4 border-t border-border/40 pt-3">
                <FieldGroup label="Predator Prefix Title">
                  <input 
                    value={pal.PredatorPrefix || "Rampaging Predator"} 
                    onChange={(e) => onUpdate({ PredatorPrefix: e.target.value })} 
                    className="input-field" 
                  />
                </FieldGroup>
                <StatSlider 
                  label="PREDATOR HP MULTIPLIER" 
                  value={pal.PredatorHPMultiplier ?? 10} 
                  onChange={(v) => onUpdate({ PredatorHPMultiplier: v })} 
                  min={1} 
                  max={30} 
                />
                <StatSlider 
                  label="PREDATOR ATK MULTIPLIER" 
                  value={pal.PredatorAtkMultiplier ?? 2} 
                  onChange={(v) => onUpdate({ PredatorAtkMultiplier: v })} 
                  min={1} 
                  max={10} 
                />
                <StatSlider 
                  label="SPEED BOOST MULTIPLIER" 
                  value={pal.PredatorSpeedMultiplier ?? 1.5} 
                  onChange={(v) => onUpdate({ PredatorSpeedMultiplier: v })} 
                  min={1} 
                  max={3} 
                />
              </div>
            )}
          </div>

          {/* NEW INTERACTIVE OVERWORLD MAP */}
          <div className="border border-border/50 p-4 rounded bg-background/30 shadow-inner flex flex-col gap-4">
            <div className="flex flex-col">
              <SectionLabel>Interactive World Map Boss Coordinates</SectionLabel>
              <span className="text-[11px] text-muted-foreground mt-1">
                Visually place fixed Alpha Boss encounters on the overworld map. Z-Axis collisions are auto-calculated from Palworld terrain data.
              </span>
            </div>
            
            {/* Mount the imported Map Component */}
            <SpawnerMap pal={pal} onUpdate={onUpdate} />
            
          </div>
        </TabsContent>
      </Tabs>

      <div className="flex items-center justify-end gap-3 mt-2 border-t border-border pt-4">
        <button
          onClick={handleRefreshBP}
          className="flex items-center gap-1.5 px-3 py-2 rounded border border-primary text-primary text-xs font-semibold hover:bg-primary/10 transition-colors cursor-pointer mr-auto"
          title="Forcefully regenerate and retarget the base, Boss, and Predator blueprints for this Pal"
        >
          <RefreshCw className="size-3.5" />
          Regenerate Blueprints
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