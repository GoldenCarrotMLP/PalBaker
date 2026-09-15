// In palbaker-ui/components/mod-manager/mod-card-expanded/edit-variant-modal.tsx

import { useState, useEffect, useMemo } from "react"
import { X, ChevronDown } from "lucide-react"
import { type DynamicPalVariant } from "@/lib/mock-data"
import { ModManagerAPI } from "@/lib/data-service"
import { Slider } from "@/components/ui/slider"
import { ConfirmModal } from "@/components/common/confirm-modal"
import { SearchableSelect } from "@/components/ui/searchable-select"

interface Props {
  basePal: string
  modName: string
  variant: DynamicPalVariant
  variantIndex: number
  dynamicPalsMetadata: any
  traitsDb: Record<string, string>
  onClose: () => void
  onSaved: () => void
  onNotify: (msg: string, type: "success" | "info" | "error" | "warning", title?: string) => void
}

const ACTIVE_MORPH_TARGETS = ["breast_size", "belly_fat", "waist_width", "height_scale"] as const

export function EditVariantModal({
  basePal, modName, variant, variantIndex, dynamicPalsMetadata, traitsDb,
  onClose, onSaved, onNotify,
}: Props) {
  const displayName = variant.is_base ? "Base Model" : (variant.label.startsWith(`${modName}_`) ? variant.label.slice(modName.length + 1) : variant.label)
  
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [variantLabel, setVariantLabel] = useState(variant.is_base ? "base" : (variant.label.startsWith(`${modName}_`) ? variant.label.slice(modName.length + 1) : variant.label))

  // --- ANIM TARGET & SKELETON SOURCE ---
  const [enableAnimTarget, setEnableAnimTarget] = useState(!!variant.AnimTarget)
  const [animTarget, setAnimTarget] = useState(variant.AnimTarget || "")
  const [selectedSkeletonSource, setSelectedSkeletonSource] = useState(variant.SkeletonSource || "base")
  
  // Extract the global workspace scan from metadata
  const allBlendFiles = dynamicPalsMetadata?.all_blend_files as Record<string, string[]> | undefined

  const [selectedGender, setSelectedGender] = useState(variant.Gender || "None")
  const [luckyStarReq, setLuckyStarReq] = useState(Boolean(variant.LuckyStarReq))
  const [skinName, setSkinName] = useState(variant.SkinName || "")
  const [setNickname, setSetNickname] = useState(variant.SetNickname || "")
  const [spawnWeight, setSpawnWeight] = useState(variant.SpawnWeight ?? 1)
  const [isWildPal, setIsWildPal] = useState(Boolean(variant.IsWildPal))

  const hasCustomLevel = Boolean(variant.enableLevelRange || (variant.MinLevel !== undefined && variant.MaxLevel !== undefined && !(variant.MinLevel === 1 && variant.MaxLevel === 999)))
  const [enableLevel, setEnableLevel] = useState(hasCustomLevel)
  const [levelRange, setLevelRange] = useState<[number, number]>(hasCustomLevel ? [variant.MinLevel!, variant.MaxLevel!] : [5, 20])

  const hasCustomTrust = Boolean(variant.enableTrustRange || (variant.MinTrust !== undefined && variant.MaxTrust !== undefined && !(variant.MinTrust === 0 && variant.MaxTrust === 999999)))
  const [enableTrust, setEnableTrust] = useState(hasCustomTrust)
  const [trustRange, setTrustRange] = useState<[number, number]>(hasCustomTrust ? [variant.MinTrust!, variant.MaxTrust!] : [2, 40])

  const hasCustomRank = Boolean(variant.enableRankRange || (variant.MinRank !== undefined && variant.MaxRank !== undefined && !(variant.MinRank === 0 && variant.MaxRank === 999)))
  const [enableRank, setEnableRank] = useState(hasCustomRank)
  const [rankRange, setRankRange] = useState<[number, number]>(hasCustomRank ? [variant.MinRank!, variant.MaxRank!] : [50, 200])

  const hasCustomSize = Boolean(variant.enableSizeRange || (variant.MinSizeMultiplier !== undefined && variant.MaxSizeMultiplier !== undefined && !(variant.MinSizeMultiplier === 1.0 && variant.MaxSizeMultiplier === 1.0)))
  const [enableSize, setEnableSize] = useState(hasCustomSize)
  const [sizeRange, setSizeRange] = useState<[number, number]>(hasCustomSize ? [variant.MinSizeMultiplier!, variant.MaxSizeMultiplier!] : [0.7, 2.0])

  const [passiveSkills, setPassiveSkills] = useState<string[]>(variant.PassiveSkills || [])
  const [prefTraits, setPrefTraits] = useState<string[]>(variant.PrefTrait || [])
  const [skipTraits, setSkipTraits] = useState<string[]>(variant.SkipTrait || [])
  const [reqSwapStr, setReqSwapStr] = useState<string>((variant.ReqSwap || []).join(", "))

  const [matOverrides, setMatOverrides] = useState<Record<number, string>>(() => {
    const init: Record<number, string> = {}
    ;(variant.SpecialMaterial || []).forEach((item: any) => {
      const idx = parseInt(item.Index)
      if (!isNaN(idx)) {
        const parts = (item.MaterialAsset || "").split("/")
        init[idx] = parts[parts.length - 1]
      }
    })
    return init
  })

  const [shapeKeys, setShapeKeys] = useState<any[]>(variant.ShapeKeys || [])
  const [slots, setSlots] = useState<string[]>([])
  const [traitSearch, setTraitSearch] = useState("")

  useEffect(() => {
    const fetchSlots = async () => {
      try {
        const res = await ModManagerAPI.dynamicPalsSidecar(animTarget || basePal, modName, selectedSkeletonSource)
        if (res?.status === "success" && res.data?.materials) {
          setSlots(Object.keys(res.data.materials))
        } else {
          setSlots(["mi_body", "mi_eye"])
        }
      } catch {
        setSlots(["mi_body", "mi_eye"])
      }
    }
    fetchSlots()
  }, [selectedSkeletonSource, modName, basePal, animTarget])

  const filteredTraits = useMemo(() => {
    const q = traitSearch.trim().toLowerCase()
    if (!q) return []
    return Object.entries(traitsDb)
      .filter(([display, id]) => display.toLowerCase().includes(q) || id.toLowerCase().includes(q))
      .filter(([, id]) => !passiveSkills.includes(id) && !prefTraits.includes(id) && !skipTraits.includes(id))
      .slice(0, 5)
  }, [traitSearch, traitsDb, passiveSkills, prefTraits, skipTraits])

  const updateMorphMode = (target: string, mode: "None" | "Free" | "Restrictive" | "Static") => {
    setShapeKeys((prev) => {
      const filtered = prev.filter((m) => (m.Name || m.Target) !== target)
      if (mode === "None") return filtered
      if (mode === "Static") return [...filtered, { Name: target, Mode: "Free", Set: 0.5 }]
      return [...filtered, { Name: target, Mode: mode, Min: 0.0, Max: 1.0 }]
    })
  }

  const updateMorphValue = (target: string, key: string, value: any) => {
    setShapeKeys((prev) => prev.map((m) => (m.Name === target || m.Target === target) ? { ...m, [key]: value } : m))
  }

  const handleOpenInBlender = async () => {
    onNotify(`Opening ${selectedSkeletonSource} in Blender...`, "info", "Blender Dispatch")
    try {
      await ModManagerAPI.dynamicPalsOpenBlend(animTarget || basePal, modName, selectedSkeletonSource, dynamicPalsMetadata?.category)
    } catch (err) {
      onNotify(`Blender invocation failed: ${err}`, "error", "Launch Failed")
    }
  }

  const executeDelete = async () => {
    setShowDeleteConfirm(false)
    if (variant.is_base) return
    try {
      await ModManagerAPI.dynamicPalsDelete(basePal, modName, variantIndex)
      onNotify(`Deleted variant: ${displayName}`, "success")
      onSaved()
      onClose()
    } catch (err) {
      onNotify(`Failed to delete variant: ${err}`, "error", "Operation Failed")
    }
  }

  const handleSave = async () => {
    const specialMaterials = Object.entries(matOverrides)
      .filter(([, val]) => val && val !== "default")
      .map(([idxStr, val]) => {
        const idx = parseInt(idxStr)
        const slotName = slots[idx] || "mi_body"
        const category = dynamicPalsMetadata?.category || "Monster"
        const resolvedMatPath = `/Game/Palbaker/Model/Character/${category}/${basePal}/${modName}/${val}`.replace(/ /g, "_")
        return { Index: idxStr, MaterialAsset: resolvedMatPath, RandomHue: false, SlotName: slotName }
      })

    const payload: any = {
      label: variant.is_base ? "base" : variantLabel,
      CharacterID: modName,
      SkeletonSource: selectedSkeletonSource,
      Gender: selectedGender,
      LuckyStarReq: luckyStarReq,
      SkinName: skinName,
      SetNickname: setNickname,
      SpawnWeight: spawnWeight,
      IsWildPal: isWildPal,
      is_base: variant.is_base,
    }

    if (enableAnimTarget && animTarget) {
      payload.AnimTarget = animTarget
    }

    // --- NEW: Fix ReqSwap payload binding ---
    if (reqSwapStr.trim()) {
      payload.ReqSwap = reqSwapStr.split(",").map(s => s.trim()).filter(Boolean)
    }


    if (enableLevel) {
      payload.enableLevelRange = true
      payload.MinLevel = levelRange[0]
      payload.MaxLevel = levelRange[1]
    }
    if (enableTrust) {
      payload.enableTrustRange = true
      payload.MinTrust = trustRange[0]
      payload.MaxTrust = trustRange[1]
    }
    if (enableRank) {
      payload.enableRankRange = true
      payload.MinRank = rankRange[0]
      payload.MaxRank = rankRange[1]
    }
    if (enableSize) {
      payload.enableSizeRange = true
      payload.MinSizeMultiplier = sizeRange[0]
      payload.MaxSizeMultiplier = sizeRange[1]
    }

    if (reqSwapStr.trim()) payload.ReqSwap = reqSwapStr.split(",").map(s => s.trim()).filter(Boolean)
    if (passiveSkills.length > 0) payload.PassiveSkills = passiveSkills
    if (prefTraits.length > 0) payload.PrefTrait = prefTraits
    if (skipTraits.length > 0) payload.SkipTrait = skipTraits
    if (specialMaterials.length > 0) payload.SpecialMaterial = specialMaterials
    if (shapeKeys.length > 0) payload.ShapeKeys = shapeKeys

    try {
      await ModManagerAPI.dynamicPalsSave(variantIndex, payload)
      onNotify("Dynamic Pal variant compiled and saved in V2 format!", "success")
      onSaved()
      onClose()
    } catch (err) {
      onNotify(`Failed to save variant changes: ${err}`, "error", "Operation Failed")
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-background border border-border rounded-lg shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
          <div className="flex flex-col">
            <span className="text-[10px] text-primary uppercase font-mono font-bold tracking-wider">Dynamic Pals V2 Configurator</span>
            <h3 className="font-bold text-lg text-foreground">Configurator: {displayName}</h3>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground cursor-pointer"><X className="size-5" /></button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-6">
          {/* SECTION 1: GENERAL SETTINGS */}
          <div className="border border-border rounded-lg p-4 bg-muted/10 flex flex-col gap-4">
            <span className="text-xs text-primary font-bold font-mono tracking-wider uppercase">1. General Settings</span>
            
            <div className="flex flex-col gap-4 mb-2">
              {/* Variant Label */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] text-muted-foreground uppercase font-semibold">Variant Label</label>
                <input type="text" disabled={variant.is_base} value={variantLabel} onChange={(e) => setVariantLabel(e.target.value)} className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm disabled:opacity-50" />
              </div>

              {/* SKELETON SOURCE & ANIM TARGET TOGGLE */}
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-[11px] text-muted-foreground uppercase font-semibold">Skeleton Source</label>
                  
                  <div className="flex items-center gap-2" title="Enable Global Mesh Select (AnimTarget)">
                    <span className="text-[10px] text-muted-foreground font-semibold uppercase flex items-center gap-1">
                      <span className="bg-yellow-900/60 text-yellow-300 px-1.5 py-0.5 rounded text-[9px]">AnimTarget</span>
                      Cross-Pal Mesh
                    </span>
                    {/* FIXED: The toggle track and thumb must be wrapped in a relative container */}
                    <label className="relative inline-flex items-center cursor-pointer shrink-0">
                      <input 
                        type="checkbox" 
                        checked={enableAnimTarget} 
                        onChange={(e) => { 
                          const isChecked = e.target.checked
                          setEnableAnimTarget(isChecked)
                          if (!isChecked) {
                            setAnimTarget("")
                            setSelectedSkeletonSource("base")
                          } else {
                            setAnimTarget(basePal)
                            setSelectedSkeletonSource("base")
                          }
                        }} 
                        className="sr-only peer" 
                      />
                      <div className="w-8 h-4.5 bg-muted border border-border peer-checked:bg-yellow-600 rounded-full transition-colors" />
                      <div className="absolute top-0.5 left-0.5 size-3.5 bg-white rounded-full shadow transition-transform peer-checked:translate-x-3.5" />
                    </label>
                  </div>
                </div>

                <div className="flex gap-2">
                  <div className="flex-1 min-w-0">
                    {/* FIXED: Replaced standard HTML <select> with <SearchableSelect> */}
                    {enableAnimTarget ? (
                      <SearchableSelect
                        value={`${animTarget}|||${selectedSkeletonSource}`}
                        onChange={(val) => {
                          if (val) {
                            const [tPal, bPath] = val.split("|||")
                            setAnimTarget(tPal)
                            setSelectedSkeletonSource(bPath)
                          }
                        }}
                        options={allBlendFiles 
                          ? Object.entries(allBlendFiles).flatMap(([palKey, files]) => 
                              files.map(f => ({
                                value: `${palKey}|||${f}`,
                                label: `[${palKey}] ${f}`
                              }))
                            )
                          : []
                        }
                        placeholder="-- Search any Pal .blend --"
                      />
                    ) : (
                      <div className="relative">
                        <select 
                          value={selectedSkeletonSource} 
                          onChange={(e) => setSelectedSkeletonSource(e.target.value)} 
                          className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm appearance-none pr-8 cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                        >
                          <option value="base" className="bg-background">base (Vanilla Canonical)</option>
                          {(dynamicPalsMetadata?.blend_files || []).map((file: string) => (
                            <option key={file} value={file} className="bg-background">
                              {file.startsWith(`${modName}_`) ? file.slice(modName.length + 1) : file} ({file})
                            </option>
                          ))}
                        </select>
                        <ChevronDown className="absolute right-2.5 top-2.5 size-4 text-muted-foreground pointer-events-none" />
                      </div>
                    )}
                  </div>
                  {selectedSkeletonSource !== "base" && !enableAnimTarget && (
                    <button onClick={handleOpenInBlender} className="px-3 rounded border border-primary/40 bg-primary/5 text-primary text-xs font-semibold hover:bg-primary/10 transition-colors cursor-pointer shrink-0">Blender</button>
                  )}
                </div>
              </div>
            </div>

            {!variant.is_base && (
              <div className="grid grid-cols-3 gap-4 border-t border-border pt-4">
                <div className="flex flex-col gap-1.5">
                  <label className="text-[11px] text-muted-foreground uppercase font-semibold">Gender</label>
                  <div className="relative">
                    <select value={selectedGender} onChange={(e) => setSelectedGender(e.target.value)} className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm appearance-none pr-8 cursor-pointer">
                      <option value="None" className="bg-background">None</option>
                      <option value="Male" className="bg-background">Male</option>
                      <option value="Female" className="bg-background">Female</option>
                      <option value="Futa" className="bg-background">Futa</option>
                      <option value="FullFuta" className="bg-background">FullFuta</option>
                      <option value="Andro" className="bg-background">Andro</option>
                      <option value="Neutered" className="bg-background">Neutered</option>
                      <option value="FullNeutered" className="bg-background">FullNeutered</option>
                    </select>
                    <ChevronDown className="absolute right-2.5 top-2.5 size-4 text-muted-foreground pointer-events-none" />
                  </div>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-[11px] text-muted-foreground uppercase font-semibold">Skin Name Override</label>
                  <input type="text" placeholder="e.g. RareSkin" value={skinName} onChange={(e) => setSkinName(e.target.value)} className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm" />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-[11px] text-muted-foreground uppercase font-semibold">Set Nickname</label>
                  <input type="text" placeholder="e.g. CoolCat" value={setNickname} onChange={(e) => setSetNickname(e.target.value)} className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm" />
                </div>
              </div>
            )}

            {!variant.is_base && (
              <div className="grid grid-cols-3 gap-4 border-t border-border pt-3">
                <div className="flex items-center justify-between border border-border/40 p-2.5 rounded">
                  <div className="flex flex-col">
                    <span className="text-xs font-semibold text-foreground">Lucky Star (LuckyStarReq)</span>
                    <span className="text-[10px] text-muted-foreground">Only lucky/giant Pals</span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" checked={luckyStarReq} onChange={(e) => setLuckyStarReq(e.target.checked)} className="sr-only peer" />
                    <div className="w-8 h-4 bg-muted border border-border peer-checked:bg-primary rounded-full transition-colors" />
                    <div className="absolute top-0.5 left-0.5 size-3 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
                  </label>
                </div>

                <div className="flex items-center justify-between border border-border/40 p-2.5 rounded">
                  <div className="flex flex-col">
                    <span className="text-xs font-semibold text-foreground">Wild Pal Only (IsWildPal)</span>
                    <span className="text-[10px] text-muted-foreground">Restrict to wild encounters</span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" checked={isWildPal} onChange={(e) => setIsWildPal(e.target.checked)} className="sr-only peer" />
                    <div className="w-8 h-4 bg-muted border border-border peer-checked:bg-primary rounded-full transition-colors" />
                    <div className="absolute top-0.5 left-0.5 size-3 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
                  </label>
                </div>

                <div className="flex flex-col gap-1 border border-border/40 p-2.5 rounded">
                  <span className="text-xs font-semibold text-foreground">Spawn Weight</span>
                  <input 
                    type="number" 
                    min={0} 
                    step="0.1"
                    value={spawnWeight} 
                    onChange={(e) => {
                      const val = parseFloat(e.target.value)
                      setSpawnWeight(isNaN(val) ? 0 : val)
                    }} 
                    className="flex h-7 w-full rounded border border-input bg-transparent px-2 text-xs" 
                  />
                </div>
              </div>
            )}
          </div>

          {/* SECTION 2: DYNAMIC RANGES (ANTD-STYLE DUAL THUMB SLIDERS) */}
          {!variant.is_base && (
            <div className="border border-border rounded-lg p-4 bg-muted/10 flex flex-col gap-4">
              <span className="text-xs text-primary font-bold font-mono tracking-wider uppercase">
                2. Spawn Range Constraints (Toggle ON to Activate)
              </span>

              <div className="grid grid-cols-2 gap-3">
                {/* LEVEL RANGE */}
                <div className="border border-border/40 p-3 rounded-md bg-background/40 flex flex-col gap-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex flex-col">
                      <span className="text-xs font-semibold text-foreground">Level Range</span>
                      <span className="text-[10px] text-muted-foreground">
                        {enableLevel ? `Min: ${levelRange[0]} — Max: ${levelRange[1]}` : "Disabled (no level limits)"}
                      </span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer shrink-0">
                      <input
                        type="checkbox"
                        checked={enableLevel}
                        onChange={(e) => {
                          const on = e.target.checked
                          setEnableLevel(on)
                          if (on && (levelRange[0] === 1 && levelRange[1] === 999)) {
                            setLevelRange([5, 20])
                          }
                        }}
                        className="sr-only peer"
                      />
                      <div className="w-8 h-4.5 bg-muted border border-border peer-checked:bg-primary rounded-full transition-colors" />
                      <div className="absolute top-0.5 left-0.5 size-3.5 bg-white rounded-full shadow transition-transform peer-checked:translate-x-3.5" />
                    </label>
                  </div>
                  {enableLevel && (
                    <div className="pt-2 flex flex-col gap-2">
                      <Slider
                        min={0}
                        max={100}
                        step={1}
                        value={[levelRange[0], levelRange[1]]}
                        onValueChange={(vals) => {
                          if (Array.isArray(vals) && vals.length === 2) {
                            setLevelRange([vals[0], vals[1]])
                          }
                        }}
                        className="[&_[role=slider]]:bg-primary [&_[role=slider]]:border-primary"
                      />
                      <div className="flex justify-between text-[10px] text-muted-foreground font-mono">
                        <span>MinLevel: <strong className="text-primary">{levelRange[0]}</strong></span>
                        <span>MaxLevel: <strong className="text-primary">{levelRange[1]}</strong></span>
                      </div>
                    </div>
                  )}
                </div>

                {/* TRUST RANGE */}
                <div className="border border-border/40 p-3 rounded-md bg-background/40 flex flex-col gap-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex flex-col">
                      <span className="text-xs font-semibold text-foreground">Trust Range</span>
                      <span className="text-[10px] text-muted-foreground">
                        {enableTrust ? `Min: ${trustRange[0]} — Max: ${trustRange[1]}` : "Disabled (no trust limits)"}
                      </span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer shrink-0">
                      <input
                        type="checkbox"
                        checked={enableTrust}
                        onChange={(e) => {
                          const on = e.target.checked
                          setEnableTrust(on)
                          if (on && (trustRange[0] === 0 && trustRange[1] === 999999)) {
                            setTrustRange([2, 40])
                          }
                        }}
                        className="sr-only peer"
                      />
                      <div className="w-8 h-4.5 bg-muted border border-border peer-checked:bg-primary rounded-full transition-colors" />
                      <div className="absolute top-0.5 left-0.5 size-3.5 bg-white rounded-full shadow transition-transform peer-checked:translate-x-3.5" />
                    </label>
                  </div>
                  {enableTrust && (
                    <div className="pt-2 flex flex-col gap-2">
                      <Slider
                        min={0}
                        max={100}
                        step={1}
                        value={[trustRange[0], trustRange[1]]}
                        onValueChange={(vals) => {
                          if (Array.isArray(vals) && vals.length === 2) {
                            setTrustRange([vals[0], vals[1]])
                          }
                        }}
                        className="[&_[role=slider]]:bg-primary [&_[role=slider]]:border-primary"
                      />
                      <div className="flex justify-between text-[10px] text-muted-foreground font-mono">
                        <span>MinTrust: <strong className="text-primary">{trustRange[0]}</strong></span>
                        <span>MaxTrust: <strong className="text-primary">{trustRange[1]}</strong></span>
                      </div>
                    </div>
                  )}
                </div>

                {/* RANK RANGE */}
                <div className="border border-border/40 p-3 rounded-md bg-background/40 flex flex-col gap-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex flex-col">
                      <span className="text-xs font-semibold text-foreground">Rank Range</span>
                      <span className="text-[10px] text-muted-foreground">
                        {enableRank ? `Min: ${rankRange[0]} — Max: ${rankRange[1]}` : "Disabled (no rank limits)"}
                      </span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer shrink-0">
                      <input
                        type="checkbox"
                        checked={enableRank}
                        onChange={(e) => {
                          const on = e.target.checked
                          setEnableRank(on)
                          if (on && (rankRange[0] === 0 && rankRange[1] === 999)) {
                            setRankRange([50, 200])
                          }
                        }}
                        className="sr-only peer"
                      />
                      <div className="w-8 h-4.5 bg-muted border border-border peer-checked:bg-primary rounded-full transition-colors" />
                      <div className="absolute top-0.5 left-0.5 size-3.5 bg-white rounded-full shadow transition-transform peer-checked:translate-x-3.5" />
                    </label>
                  </div>
                  {enableRank && (
                    <div className="pt-2 flex flex-col gap-2">
                      <Slider
                        min={0}
                        max={255}
                        step={1}
                        value={[rankRange[0], rankRange[1]]}
                        onValueChange={(vals) => {
                          if (Array.isArray(vals) && vals.length === 2) {
                            setRankRange([vals[0], vals[1]])
                          }
                        }}
                        className="[&_[role=slider]]:bg-primary [&_[role=slider]]:border-primary"
                      />
                      <div className="flex justify-between text-[10px] text-muted-foreground font-mono">
                        <span>MinRank: <strong className="text-primary">{rankRange[0]}</strong></span>
                        <span>MaxRank: <strong className="text-primary">{rankRange[1]}</strong></span>
                      </div>
                    </div>
                  )}
                </div>

                {/* SIZE MULTIPLIER RANGE */}
                <div className="border border-border/40 p-3 rounded-md bg-background/40 flex flex-col gap-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex flex-col">
                      <span className="text-xs font-semibold text-foreground">Size Multiplier</span>
                      <span className="text-[10px] text-muted-foreground">
                        {enableSize ? `Min: ${sizeRange[0].toFixed(1)}x — Max: ${sizeRange[1].toFixed(1)}x` : "Disabled (default 1.0x)"}
                      </span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer shrink-0">
                      <input
                        type="checkbox"
                        checked={enableSize}
                        onChange={(e) => {
                          const on = e.target.checked
                          setEnableSize(on)
                          if (on && (sizeRange[0] === 1.0 && sizeRange[1] === 1.0)) {
                            setSizeRange([0.7, 2.0])
                          }
                        }}
                        className="sr-only peer"
                      />
                      <div className="w-8 h-4.5 bg-muted border border-border peer-checked:bg-primary rounded-full transition-colors" />
                      <div className="absolute top-0.5 left-0.5 size-3.5 bg-white rounded-full shadow transition-transform peer-checked:translate-x-3.5" />
                    </label>
                  </div>
                  {enableSize && (
                    <div className="pt-2 flex flex-col gap-2">
                      <Slider
                        min={0}
                        max={10}
                        step={0.1}
                        value={[sizeRange[0], sizeRange[1]]}
                        onValueChange={(vals) => {
                          if (Array.isArray(vals) && vals.length === 2) {
                            setSizeRange([Number(vals[0].toFixed(1)), Number(vals[1].toFixed(1))])
                          }
                        }}
                        className="[&_[role=slider]]:bg-primary [&_[role=slider]]:border-primary"
                      />
                      <div className="flex justify-between text-[10px] text-muted-foreground font-mono">
                        <span>MinSize: <strong className="text-primary">{sizeRange[0].toFixed(1)}x</strong></span>
                        <span>MaxSize: <strong className="text-primary">{sizeRange[1].toFixed(1)}x</strong></span>
                      </div>
                    </div>
                  )}
                </div>
                </div>
              </div>
            
          )}

          {/* SECTION 3: PASSIVE SKILLS, TRAITS & EVOLUTIONS */}
          {!variant.is_base && (
            <div className="border border-border rounded-lg p-4 bg-muted/10 flex flex-col gap-4">
              <span className="text-xs text-primary font-bold font-mono tracking-wider uppercase">
                3. Passive Skills, Traits & Evolutions
              </span>

              {/* 1. Required Swap States (Evolutions / ReqSwap) */}
              <div className="flex flex-col gap-1.5 pb-3 border-b border-border/40">
                <label className="text-[11px] text-muted-foreground uppercase font-semibold">
                  Required Swap States (Evolutions)
                </label>
                <input 
                  type="text" 
                  placeholder="e.g. Fennekin, Braixen" 
                  value={reqSwapStr} 
                  onChange={(e) => setReqSwapStr(e.target.value)} 
                  className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary" 
                />
                <span className="text-[10px] text-muted-foreground">
                  Comma-separated list of variant labels this Pal must evolve/swap from (ReqSwap).
                </span>
              </div>

              {/* 2. Active Selected Badges (Req, Pref, and Block) */}
              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] text-muted-foreground uppercase font-semibold">
                  Configured Trait Rules
                </label>
                <div className="flex flex-wrap gap-1.5 min-h-[36px] border border-border rounded p-2 bg-background/50 items-center">
                  {passiveSkills.length === 0 && prefTraits.length === 0 && skipTraits.length === 0 && (
                    <span className="text-xs text-muted-foreground italic">
                      No trait conditions added. This variant will spawn by default.
                    </span>
                  )}

                  {/* Required Traits (Green) */}
                  {passiveSkills.map((id) => {
                    const label = Object.keys(traitsDb).find((k) => traitsDb[k] === id) || id
                    return (
                      <span key={id} className="flex items-center gap-1 bg-green-950 border border-green-800 text-green-300 text-[10px] font-bold px-2 py-0.5 rounded">
                        Req: {label}
                        <button 
                          type="button"
                          onClick={() => setPassiveSkills((p) => p.filter((x) => x !== id))} 
                          className="hover:text-white shrink-0 cursor-pointer"
                        >
                          <X className="size-3" />
                        </button>
                      </span>
                    )
                  })}

                  {/* Preferred Traits (Purple) */}
                  {prefTraits.map((id) => {
                    const label = Object.keys(traitsDb).find((k) => traitsDb[k] === id) || id
                    return (
                      <span key={id} className="flex items-center gap-1 bg-purple-950 border border-purple-800 text-purple-300 text-[10px] font-bold px-2 py-0.5 rounded">
                        Pref: {label}
                        <button 
                          type="button"
                          onClick={() => setPrefTraits((p) => p.filter((x) => x !== id))} 
                          className="hover:text-white shrink-0 cursor-pointer"
                        >
                          <X className="size-3" />
                        </button>
                      </span>
                    )
                  })}

                  {/* Block Traits (Red) */}
                  {skipTraits.map((id) => {
                    const label = Object.keys(traitsDb).find((k) => traitsDb[k] === id) || id
                    return (
                      <span key={id} className="flex items-center gap-1 bg-red-950 border border-red-800 text-red-300 text-[10px] font-bold px-2 py-0.5 rounded">
                        Block: {label}
                        <button 
                          type="button"
                          onClick={() => setSkipTraits((p) => p.filter((x) => x !== id))} 
                          className="hover:text-white shrink-0 cursor-pointer"
                        >
                          <X className="size-3" />
                        </button>
                      </span>
                    )
                  })}
                </div>
              </div>

              {/* 3. Trait Search Box & Dropdown Actions */}
              <div className="flex flex-col gap-1.5 relative">
                <input
                  type="text"
                  placeholder="Fuzzy Search Passive Traits (e.g. Swift, Legend, Coward...)"
                  value={traitSearch}
                  onChange={(e) => setTraitSearch(e.target.value)}
                  className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                />

                {filteredTraits.length > 0 && (
                  <div className="absolute top-10 left-0 right-0 border border-border bg-background shadow-xl rounded-md z-40 flex flex-col overflow-hidden">
                    {filteredTraits.map(([display, id]) => (
                      <div key={id} className="flex items-center justify-between px-3 py-2 border-b border-border/50 hover:bg-muted/40 transition-colors">
                        <span className="text-xs text-foreground font-semibold">
                          {display} <span className="text-[10px] text-muted-foreground font-mono">({id})</span>
                        </span>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => { setPassiveSkills((p) => [...p, id]); setTraitSearch("") }}
                            className="px-2 py-1 border border-green-700/50 bg-green-950/20 text-[10px] text-green-400 rounded font-semibold hover:bg-green-950/50 cursor-pointer"
                          >
                            + Req
                          </button>
                          <button
                            type="button"
                            onClick={() => { setPrefTraits((p) => [...p, id]); setTraitSearch("") }}
                            className="px-2 py-1 border border-purple-700/50 bg-purple-950/20 text-[10px] text-purple-400 rounded font-semibold hover:bg-purple-950/50 cursor-pointer"
                          >
                            + Pref
                          </button>
                          <button
                            type="button"
                            onClick={() => { setSkipTraits((p) => [...p, id]); setTraitSearch("") }}
                            className="px-2 py-1 border border-red-700/50 bg-red-950/20 text-[10px] text-red-400 rounded font-semibold hover:bg-red-950/50 cursor-pointer"
                          >
                            + Block
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* SECTION 4: SPECIAL MATERIAL OVERRIDES */}
          {!variant.is_base && (
            <div className="border border-border rounded-lg p-4 bg-muted/10 flex flex-col gap-4">
              <span className="text-xs text-primary font-bold font-mono tracking-wider uppercase">4. Special Material Overrides</span>
              <div className="flex flex-col gap-3">
                {slots.length === 0 ? (
                  <span className="text-xs text-muted-foreground italic">No material slots defined on the source skeleton file.</span>
                ) : (
                  slots.map((slotName, idx) => {
                    const currentVal = matOverrides[idx] || "default"
                    return (
                      <div key={idx} className="flex items-center justify-between gap-4 border-b border-border/30 pb-2.5 last:border-0 last:pb-0">
                        <span className="text-xs text-foreground font-semibold font-mono w-1/3 truncate">Slot {idx}: {slotName}</span>
                        <div className="relative flex-1 max-w-[280px]">
                          <select value={currentVal} onChange={(e) => setMatOverrides((p) => ({ ...p, [idx]: e.target.value }))} className="flex h-8 w-full rounded border border-input bg-transparent px-3 py-1 text-xs shadow-sm appearance-none pr-8 cursor-pointer">
                            <option value="default" className="bg-background">Default (No Override)</option>
                            {(dynamicPalsMetadata?.available_materials || []).map((mat: string) => (
                              <option key={mat} value={mat} className="bg-background">{mat}</option>
                            ))}
                          </select>
                          <ChevronDown className="absolute right-2.5 top-2 size-3.5 text-muted-foreground pointer-events-none" />
                        </div>
                      </div>
                    )
                  })
                )}
              </div>
            </div>
          )}

          {/* SECTION 5: SHAPE KEYS */}
          {!variant.is_base && (
            <div className="border border-border rounded-lg p-4 bg-muted/10 flex flex-col gap-4">
              <span className="text-xs text-primary font-bold font-mono tracking-wider uppercase">5. Shape Keys & Morph Sliders</span>
              <div className="flex flex-col gap-4">
                {ACTIVE_MORPH_TARGETS.map((morphName) => {
                  const config = shapeKeys.find((m) => (m.Name || m.Target) === morphName)
                  const mode = config ? (config.Set !== undefined ? "Static" : (config.Mode || "Free")) : "None"
                  return (
                    <div key={morphName} className="border border-border/50 rounded-md p-3 bg-background/40 flex flex-col gap-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-foreground font-mono">{morphName}</span>
                        <div className="relative w-[150px]">
                          <select value={mode} onChange={(e) => updateMorphMode(morphName, e.target.value as any)} className="flex h-7 w-full rounded border border-input bg-transparent px-2.5 text-xs appearance-none pr-6 cursor-pointer">
                            <option value="None" className="bg-background">Ignore/Default</option>
                            <option value="Static" className="bg-background">Static (Set Value)</option>
                            <option value="Free" className="bg-background">Random (Free Mode)</option>
                            <option value="Restrictive" className="bg-background">Random (Restrictive)</option>
                          </select>
                          <ChevronDown className="absolute right-2 top-2 size-3 text-muted-foreground pointer-events-none" />
                        </div>
                      </div>
                      {mode === "Static" && (
                        <div className="flex items-center gap-3">
                          <span className="text-[10px] text-muted-foreground font-semibold uppercase shrink-0">Forced: {(config?.Set ?? 0.5).toFixed(2)}</span>
                          <input type="range" min="0.0" max="1.0" step="0.05" value={config?.Set ?? 0.5} onChange={(e) => updateMorphValue(morphName, "Set", parseFloat(e.target.value))} className="flex-1 accent-primary h-1 bg-muted rounded-full cursor-pointer appearance-none" />
                        </div>
                      )}
                      {(mode === "Free" || mode === "Restrictive") && (
                        <div className="flex flex-col gap-2 pt-1 border-t border-border/20">
                          <div className="flex items-center gap-3">
                            <span className="text-[10px] text-muted-foreground font-semibold uppercase w-[80px] shrink-0">Min: {(config?.Min ?? 0.0).toFixed(2)}</span>
                            <input type="range" min="0.0" max="1.0" step="0.05" value={config?.Min ?? 0.0} onChange={(e) => updateMorphValue(morphName, "Min", parseFloat(e.target.value))} className="flex-1 accent-primary h-1 bg-muted rounded-full cursor-pointer appearance-none" />
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="text-[10px] text-muted-foreground font-semibold uppercase w-[80px] shrink-0">Max: {(config?.Max ?? 1.0).toFixed(2)}</span>
                            <input type="range" min="0.0" max="1.0" step="0.05" value={config?.Max ?? 1.0} onChange={(e) => updateMorphValue(morphName, "Max", parseFloat(e.target.value))} className="flex-1 accent-primary h-1 bg-muted rounded-full cursor-pointer appearance-none" />
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between mt-2 border-t border-border pt-4 px-6 pb-4">
          <button 
            type="button"
            onClick={() => setShowDeleteConfirm(true)} 
            className="text-xs text-status-error hover:underline cursor-pointer"
          >
            Delete Variant
          </button>
          <div className="flex items-center gap-3">
            <button onClick={onClose} className="px-4 py-2 rounded text-sm text-muted-foreground hover:bg-muted/50 cursor-pointer transition-colors">Cancel</button>
            <button onClick={handleSave} className="px-4 py-2 rounded text-sm bg-primary text-primary-foreground font-semibold hover:bg-primary/90 shadow transition-colors cursor-pointer">Apply Changes</button>
          </div>
        </div>
      </div>

      {/* 4. In-App Confirmation Modal */}
      {showDeleteConfirm && (
        <ConfirmModal
          title="Delete Dynamic Pal Variant"
          message={`Are you sure you want to permanently delete variant '${displayName}'?`}
          confirmText="Delete Variant"
          danger={true}
          onConfirm={executeDelete}
          onCancel={() => setShowDeleteConfirm(false)}
        />
      )}
    </div>
  )
}