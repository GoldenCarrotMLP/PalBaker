"use client"

import { useState, useEffect, useMemo } from "react"
import { X, ChevronDown } from "lucide-react"
import { type AltermaticVariant } from "@/lib/mock-data"
import { ModManagerAPI } from "@/lib/data-service"
import { cn } from "@/lib/utils"

interface Props {
  modName: string
  variant: AltermaticVariant
  variantIndex: number
  altermaticMetadata: any
  traitsDb: Record<string, string>
  onClose: () => void
  onSaved: () => void
  onNotify: (msg: string, type: "success" | "info" | "error" | "warning", title?: string) => void
}

const ACTIVE_MORPH_TARGETS = ["breast_size", "belly_fat", "waist_width", "height_scale"] as const

export function EditVariantModal({
  modName, variant, variantIndex, altermaticMetadata, traitsDb,
  onClose, onSaved, onNotify,
}: Props) {
  const cleanLabel = variant.is_base
    ? "base"
    : (variant.label.startsWith(`${modName}_`) ? variant.label.slice(modName.length + 1) : variant.label)

  const [variantLabel,          setVariantLabel]          = useState(cleanLabel)
  const [selectedSkeletonSource, setSelectedSkeletonSource] = useState(variant.SkeletonSource || "base")
  const [selectedGender,        setSelectedGender]        = useState(variant.Gender || "None")
  const [isRarePal,             setIsRarePal]             = useState(!!variant.IsRarePal)
  const [skinName,              setSkinName]              = useState(variant.SkinName || "")
  const [reqTraits,             setReqTraits]             = useState<string[]>(variant.ReqTrait || [])
  const [prefTraits,            setPrefTraits]            = useState<string[]>(variant.PrefTrait || [])
  const [matOverrides,          setMatOverrides]          = useState<Record<number, string>>(() => {
    const init: Record<number, string> = {}
    ;(variant.MatReplace || []).forEach((item: any) => {
      const idx = parseInt(item.Index)
      if (!isNaN(idx)) {
        const parts = item.MatPath.split("/")
        init[idx] = parts[parts.length - 1]
      }
    })
    return init
  })
  const [morphs,      setMorphs]      = useState<any[]>(variant.MorphTarget || [])
  const [slots,       setSlots]       = useState<string[]>([])
  const [traitSearch, setTraitSearch] = useState("")

  // Fetch material slots when skeleton source changes
  useEffect(() => {
    const fetchSlots = async () => {
      try {
        const res = await ModManagerAPI.altermaticSidecar(modName, selectedSkeletonSource)
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
  }, [selectedSkeletonSource, modName])

  const filteredTraits = useMemo(() => {
    const q = traitSearch.trim().toLowerCase()
    if (!q) return []
    return Object.entries(traitsDb)
      .filter(([display, id]) =>
        display.toLowerCase().includes(q) || id.toLowerCase().includes(q)
      )
      .filter(([, id]) => !reqTraits.includes(id) && !prefTraits.includes(id))
      .slice(0, 5)
  }, [traitSearch, traitsDb, reqTraits, prefTraits])

  const updateMorphType = (target: string, type: "None" | "Static" | "Random") => {
    setMorphs((prev) => {
      const filtered = prev.filter((m) => m.Target !== target)
      if (type === "None")   return filtered
      if (type === "Static") return [...filtered, { Target: target, Type: "Static", Set: 0.5 }]
      return [...filtered, { Target: target, Type: "Random", Min: 0.0, Max: 1.0, TypeVal: "Free" }]
    })
  }

  const updateMorphValue = (target: string, key: string, value: any) => {
    setMorphs((prev) =>
      prev.map((m) => m.Target === target ? { ...m, [key]: value } : m)
    )
  }

  const handleOpenInBlender = async () => {
    onNotify(`Opening ${selectedSkeletonSource} in Blender...`, "info", "Blender Dispatch")
    try {
      await ModManagerAPI.altermaticOpenBlend(modName, selectedSkeletonSource, altermaticMetadata?.category)
    } catch (err) {
      onNotify(`Blender invocation failed: ${err}`, "error", "Launch Failed")
    }
  }

  const handleDelete = async () => {
    if (variant.is_base) return
    if (!window.confirm(`Delete variant: ${variant.label}?`)) return
    try {
      await ModManagerAPI.altermaticDelete(modName, variantIndex)
      onNotify(`Deleted variant: ${variant.label}`, "success")
      onSaved()
      onClose()
    } catch (err) {
      onNotify(`Failed to delete variant: ${err}`, "error", "Operation Failed")
    }
  }

  const handleSave = async () => {
    const matReplaces = Object.entries(matOverrides)
      .filter(([, val]) => val && val !== "default")
      .map(([idxStr, val]) => {
        const idx = parseInt(idxStr)
        const slotName = slots[idx] || "mi_body"
        const category = altermaticMetadata?.category || "Monster"
        const resolvedMatPath = `/Game/Palbaker/Model/Character/${category}/${modName}/${val}`.replace(/ /g, "_")
        return { Index: idxStr, MatPath: resolvedMatPath, SlotName: slotName }
      })

    const payload = {
      label: variant.is_base ? "base" : variantLabel,
      CharacterID: modName,
      SkeletonSource: selectedSkeletonSource,
      Gender: selectedGender,
      IsRarePal: isRarePal,
      SkinName: skinName,
      ReqTrait: reqTraits,
      PrefTrait: prefTraits,
      MatReplace: matReplaces,
      MorphTarget: morphs,
      is_base: variant.is_base,
    }

    try {
      await ModManagerAPI.altermaticSave(variantIndex, payload)
      onNotify("Variant changes compiled and saved successfully!", "success")
      onSaved()
      onClose()
    } catch (err) {
      onNotify(`Failed to save variant changes: ${err}`, "error", "Operation Failed")
    }
  }

  const displayName = variant.is_base
    ? "Base Model"
    : (variant.label.startsWith(`${modName}_`) ? variant.label.slice(modName.length + 1) : variant.label)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="bg-background border border-border rounded-lg shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
          <div className="flex flex-col">
            <span className="text-[10px] text-primary uppercase font-mono font-bold tracking-wider">Visual Altermatic Configurator</span>
            <h3 className="font-bold text-lg text-foreground">Configurator: {displayName}</h3>
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground cursor-pointer">
            <X className="size-5" />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-6">

          {/* Section 1: General Settings */}
          <div className="border border-border rounded-lg p-4 bg-muted/10 flex flex-col gap-4">
            <span className="text-xs text-primary font-bold font-mono tracking-wider uppercase">1. General Settings</span>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] text-muted-foreground uppercase font-semibold">Variant Label</label>
                <input
                  type="text"
                  disabled={variant.is_base}
                  value={variantLabel}
                  onChange={(e) => setVariantLabel(e.target.value)}
                  className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm disabled:opacity-50"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] text-muted-foreground uppercase font-semibold">Skeleton Source</label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <select
                      value={selectedSkeletonSource}
                      onChange={(e) => setSelectedSkeletonSource(e.target.value)}
                      className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm appearance-none pr-8 cursor-pointer focus-visible:outline-none"
                    >
                      <option value="base" className="bg-background">base (Vanilla Canonical)</option>
                      {(altermaticMetadata?.blend_files || []).map((file: string) => (
                        <option key={file} value={file} className="bg-background">
                          Variant: {file.startsWith(`${modName}_`) ? file.slice(modName.length + 1) : file}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-2.5 top-2.5 size-4 text-muted-foreground pointer-events-none" />
                  </div>
                  {selectedSkeletonSource !== "base" && (
                    <button
                      onClick={handleOpenInBlender}
                      className="px-3 rounded border border-primary/40 bg-primary/5 text-primary text-xs font-semibold hover:bg-primary/10 transition-colors cursor-pointer"
                    >
                      Blender
                    </button>
                  )}
                </div>
              </div>
            </div>

            {!variant.is_base && (
              <div className="grid grid-cols-2 gap-4 border-t border-border pt-4">
                <div className="flex flex-col gap-1.5">
                  <label className="text-[11px] text-muted-foreground uppercase font-semibold">Gender Override</label>
                  <div className="relative">
                    <select
                      value={selectedGender}
                      onChange={(e) => setSelectedGender(e.target.value)}
                      className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm appearance-none pr-8 cursor-pointer"
                    >
                      <option value="None"   className="bg-background">None (Ignore Gender)</option>
                      <option value="Male"   className="bg-background">Male Only</option>
                      <option value="Female" className="bg-background">Female Only</option>
                    </select>
                    <ChevronDown className="absolute right-2.5 top-2.5 size-4 text-muted-foreground pointer-events-none" />
                  </div>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-[11px] text-muted-foreground uppercase font-semibold">Skin Name Override</label>
                  <input
                    type="text"
                    placeholder="e.g. RareSkin"
                    value={skinName}
                    onChange={(e) => setSkinName(e.target.value)}
                    className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                  />
                </div>
              </div>
            )}

            {!variant.is_base && (
              <div className="flex items-center justify-between border-t border-border pt-3">
                <div className="flex flex-col gap-0.5">
                  <span className="text-sm font-semibold text-foreground">Is Lucky Pal? (IsRarePal)</span>
                  <span className="text-xs text-muted-foreground">Only spawn on lucky/giant Pal instances.</span>
                </div>
                <label className="relative inline-flex inline-flex items-center cursor-pointer">
                  <input type="checkbox" checked={isRarePal} onChange={(e) => setIsRarePal(e.target.checked)} className="sr-only peer" />
                  <div className="w-9 h-5 bg-muted border border-border peer-checked:bg-primary rounded-full transition-colors" />
                  <div className="absolute top-0.5 left-0.5 size-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
                </label>
              </div>
            )}
          </div>

          {/* Section 2: Passive Traits */}
          {!variant.is_base && (
            <div className="border border-border rounded-lg p-4 bg-muted/10 flex flex-col gap-4">
              <span className="text-xs text-primary font-bold font-mono tracking-wider uppercase">2. Passive Traits Requirements</span>

              <div className="flex flex-wrap gap-1.5 min-h-[32px] border border-border rounded p-2 bg-background/50">
                {reqTraits.length === 0 && prefTraits.length === 0 && (
                  <span className="text-xs text-muted-foreground italic">No conditions added. This variant will spawn by default.</span>
                )}
                {reqTraits.map((id) => {
                  const label = Object.keys(traitsDb).find((k) => traitsDb[k] === id) || id
                  return (
                    <span key={id} className="flex items-center gap-1 bg-green-950 border border-green-800 text-green-300 text-[10px] font-bold px-2 py-0.5 rounded">
                      Req: {label}
                      <button onClick={() => setReqTraits((p) => p.filter((x) => x !== id))} className="hover:text-white shrink-0 cursor-pointer">
                        <X className="size-3" />
                      </button>
                    </span>
                  )
                })}
                {prefTraits.map((id) => {
                  const label = Object.keys(traitsDb).find((k) => traitsDb[k] === id) || id
                  return (
                    <span key={id} className="flex items-center gap-1 bg-purple-950 border border-purple-800 text-purple-300 text-[10px] font-bold px-2 py-0.5 rounded">
                      Pref: {label}
                      <button onClick={() => setPrefTraits((p) => p.filter((x) => x !== id))} className="hover:text-white shrink-0 cursor-pointer">
                        <X className="size-3" />
                      </button>
                    </span>
                  )
                })}
              </div>

              <div className="flex flex-col gap-1.5 relative">
                <input
                  type="text"
                  placeholder="Fuzzy Search Passive Traits (e.g. Swift, Legend...)"
                  value={traitSearch}
                  onChange={(e) => setTraitSearch(e.target.value)}
                  className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                />
                {filteredTraits.length > 0 && (
                  <div className="absolute top-10 left-0 right-0 border border-border bg-background shadow-lg rounded-md z-40 flex flex-col overflow-hidden">
                    {filteredTraits.map(([display, id]) => (
                      <div key={id} className="flex items-center justify-between px-3 py-2 border-b border-border/50 last:border-0 hover:bg-muted/40 transition-colors">
                        <span className="text-xs text-foreground font-semibold">
                          {display} <span className="text-[10px] text-muted-foreground font-mono">({id})</span>
                        </span>
                        <div className="flex gap-2">
                          <button onClick={() => { setReqTraits((p) => [...p, id]); setTraitSearch("") }} className="px-2 py-1 border border-green-700/50 bg-green-950/20 text-[10px] text-green-400 rounded font-semibold hover:bg-green-950/50 cursor-pointer">
                            + Req
                          </button>
                          <button onClick={() => { setPrefTraits((p) => [...p, id]); setTraitSearch("") }} className="px-2 py-1 border border-purple-700/50 bg-purple-950/20 text-[10px] text-purple-400 rounded font-semibold hover:bg-purple-950/50 cursor-pointer">
                            + Pref
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Section 3: Material Overrides */}
          {!variant.is_base && (
            <div className="border border-border rounded-lg p-4 bg-muted/10 flex flex-col gap-4">
              <span className="text-xs text-primary font-bold font-mono tracking-wider uppercase">3. Visual Material Overrides</span>
              <div className="flex flex-col gap-3">
                {slots.length === 0 ? (
                  <span className="text-xs text-muted-foreground italic">No material slots defined on the source skeleton file.</span>
                ) : (
                  slots.map((slotName, idx) => {
                    const currentVal = matOverrides[idx] || "default"
                    return (
                      <div key={idx} className="flex items-center justify-between gap-4 border-b border-border/30 last:border-0 pb-2.5 last:pb-0">
                        <span className="text-xs text-foreground font-semibold font-mono w-1/3 truncate">Slot {idx}: {slotName}</span>
                        <div className="relative flex-1 max-w-[280px]">
                          <select
                            value={currentVal}
                            onChange={(e) => setMatOverrides((p) => ({ ...p, [idx]: e.target.value }))}
                            className="flex h-8 w-full rounded border border-input bg-transparent px-3 py-1 text-xs shadow-sm appearance-none pr-8 cursor-pointer"
                          >
                            <option value="default" className="bg-background">Default (No Override)</option>
                            {(altermaticMetadata?.available_materials || []).map((mat: string) => (
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

          {/* Section 4: Morph Targets */}
          {!variant.is_base && (
            <div className="border border-border rounded-lg p-4 bg-muted/10 flex flex-col gap-4">
              <span className="text-xs text-primary font-bold font-mono tracking-wider uppercase">4. Morph Target Parameters</span>
              <div className="flex flex-col gap-4">
                {ACTIVE_MORPH_TARGETS.map((morphName) => {
                  const config = morphs.find((m) => m.Target === morphName)
                  const type   = config ? config.Type : "None"
                  return (
                    <div key={morphName} className="border border-border/50 rounded-md p-3 bg-background/40 flex flex-col gap-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-foreground font-mono">{morphName}</span>
                        <div className="relative w-[150px]">
                          <select
                            value={type}
                            onChange={(e) => updateMorphType(morphName, e.target.value as any)}
                            className="flex h-7 w-full rounded border border-input bg-transparent px-2.5 text-xs appearance-none pr-6 cursor-pointer"
                          >
                            <option value="None"   className="bg-background">Ignore/Default</option>
                            <option value="Static" className="bg-background">Static (Set)</option>
                            <option value="Random" className="bg-background">Random (Range)</option>
                          </select>
                          <ChevronDown className="absolute right-2 top-2 size-3 text-muted-foreground pointer-events-none" />
                        </div>
                      </div>

                      {type === "Static" && (
                        <div className="flex items-center gap-3">
                          <span className="text-[10px] text-muted-foreground font-semibold uppercase shrink-0">
                            Forced: {(config.Set ?? 0.5).toFixed(2)}
                          </span>
                          <input
                            type="range" min="0.0" max="1.0" step="0.05"
                            value={config.Set ?? 0.5}
                            onChange={(e) => updateMorphValue(morphName, "Set", parseFloat(e.target.value))}
                            className="flex-1 accent-primary h-1 bg-muted rounded-full cursor-pointer appearance-none"
                          />
                        </div>
                      )}

                      {type === "Random" && (
                        <div className="flex flex-col gap-2 pt-1 border-t border-border/20">
                          <div className="flex items-center gap-3">
                            <span className="text-[10px] text-muted-foreground font-semibold uppercase w-[80px] shrink-0">
                              Min: {(config.Min ?? 0.0).toFixed(2)}
                            </span>
                            <input type="range" min="0.0" max="1.0" step="0.05"
                              value={config.Min ?? 0.0}
                              onChange={(e) => updateMorphValue(morphName, "Min", parseFloat(e.target.value))}
                              className="flex-1 accent-primary h-1 bg-muted rounded-full cursor-pointer appearance-none"
                            />
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="text-[10px] text-muted-foreground font-semibold uppercase w-[80px] shrink-0">
                              Max: {(config.Max ?? 1.0).toFixed(2)}
                            </span>
                            <input type="range" min="0.0" max="1.0" step="0.05"
                              value={config.Max ?? 1.0}
                              onChange={(e) => updateMorphValue(morphName, "Max", parseFloat(e.target.value))}
                              className="flex-1 accent-primary h-1 bg-muted rounded-full cursor-pointer appearance-none"
                            />
                          </div>
                          <div className="flex items-center justify-between mt-1">
                            <span className="text-[10px] text-muted-foreground font-semibold uppercase">Roll Mode:</span>
                            <div className="relative w-[120px]">
                              <select
                                value={config.TypeVal || "Free"}
                                onChange={(e) => updateMorphValue(morphName, "TypeVal", e.target.value)}
                                className="flex h-6 w-full rounded border border-input bg-transparent px-2 text-[10px] appearance-none pr-5 cursor-pointer"
                              >
                                <option value="Free"     className="bg-background">Free Roll</option>
                                <option value="Restrict" className="bg-background">Restrict</option>
                              </select>
                              <ChevronDown className="absolute right-2 top-1.5 size-3 text-muted-foreground pointer-events-none" />
                            </div>
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
        <div className="px-6 py-4 border-t border-border bg-muted/5 flex justify-between items-center shrink-0">
          <div>
            {!variant.is_base && (
              <button
                onClick={handleDelete}
                className="inline-flex h-9 items-center justify-center rounded bg-status-error/10 text-status-error px-4 text-sm font-semibold hover:bg-status-error/20 transition-colors border border-status-error/25 cursor-pointer"
              >
                Delete Variant
              </button>
            )}
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="inline-flex h-9 items-center justify-center rounded px-4 text-sm font-semibold border border-input bg-transparent hover:bg-muted/50 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="inline-flex h-9 items-center justify-center rounded bg-primary text-primary-foreground px-4 text-sm font-semibold hover:bg-primary/90 transition-colors cursor-pointer shadow"
            >
              Apply Changes
            </button>
          </div>
        </div>

      </div>
    </div>
  )
}