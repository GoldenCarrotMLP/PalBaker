"use client"

import { useState, useRef, useEffect, useMemo } from "react"
import { type ModItem, type AltermaticVariant } from "@/lib/mock-data"
import { Separator } from "@/components/ui/separator"
import { Play, Upload, Trash2, Plus, ImagePlus, X, Sliders, ChevronDown, Check } from "lucide-react"
import { cn } from "@/lib/utils"
import { ModManagerAPI } from "@/lib/data-service"
import { convertFileSrc } from "@tauri-apps/api/core"

interface Props {
  mod: ModItem
  onRefresh: () => void
}

const CRY_SLOTS = ["Normal", "Joy", "Anger", "Sorrow", "Pain", "Death"] as const

// Mirrors mod_details.py build_variants_list() badge logic
function VariantChip({ variant, modName, onClick }: { variant: AltermaticVariant; modName: string; onClick?: () => void }) {
  // Strip "ModName_" prefix from label for display
  const prefix = `${modName}_`
  const displayLabel = variant.label.startsWith(prefix)
    ? variant.label.slice(prefix.length)
    : variant.label

  const traitsCount = (variant.ReqTrait || []).length + (variant.PrefTrait || []).length
  const matsCount = (variant.MatReplace || []).length
  const morphsCount = (variant.MorphTarget || []).length

  const chips: { text: string; cls: string }[] = []

  if (variant.is_base) {
    chips.push({ text: "BASE", cls: "bg-muted text-muted-foreground" })
  } else {
    if (variant.Gender && variant.Gender !== "None") {
      chips.push({ text: variant.Gender[0], cls: "bg-blue-900/60 text-blue-300" })
    }
    if (variant.IsRarePal) {
      chips.push({ text: "LUCKY", cls: "bg-amber-900/60 text-amber-300" })
    }
    if (traitsCount > 0) {
      chips.push({ text: `T:${traitsCount}`, cls: "bg-green-900/60 text-green-300" })
    }
    if (matsCount > 0) {
      chips.push({ text: `M:${matsCount}`, cls: "bg-purple-900/60 text-purple-300" })
    }
    if (morphsCount > 0) {
      chips.push({ text: `MPH:${morphsCount}`, cls: "bg-cyan-900/60 text-cyan-300" })
    }
    if (chips.length === 0) {
      chips.push({ text: "DEFAULT", cls: "bg-muted text-muted-foreground" })
    }
  }

  return (
    <button
      onClick={onClick}
      className="flex flex-col gap-1 bg-muted/50 border border-border rounded px-3 py-2 text-left hover:border-primary/50 transition-colors min-w-[64px] cursor-pointer"
    >
      <span className="text-primary text-xs font-semibold truncate max-w-[120px]">{displayLabel}</span>
      <div className="flex flex-wrap gap-1">
        {chips.map((c, i) => (
          <span key={i} className={cn("text-[9px] font-bold px-1 py-0.5 rounded", c.cls)}>
            {c.text}
          </span>
        ))}
      </div>
    </button>
  )
}

export function ModCardExpanded({ mod, onRefresh }: Props) {
  const [altermaticEnabled, setAltermaticEnabled] = useState(mod.is_altermatic_active)
  const iconInputRef = useRef<HTMLInputElement>(null)
  const audioInputRefs = useRef<Record<string, HTMLInputElement | null>>({})

  const availableCries = CRY_SLOTS.filter((s) => mod.sound_metadata[s] !== undefined)
  const hasSoundData = availableCries.length > 0

  // ── Notification Toast States ──
  const [notifications, setNotifications] = useState<any[]>([])

  const showNotification = (message: string, type: "success" | "info" | "error" | "warning" = "info", title?: string) => {
    const id = Math.random().toString(36).slice(2, 9)
    setNotifications((prev) => [...prev, { id, message, type, title }])
    setTimeout(() => {
      setNotifications((prev) => prev.filter((n) => n.id !== id))
    }, 4000)
  }

  // ── Altermatic States ──
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [editingVariant, setEditingVariant] = useState<AltermaticVariant | null>(null)
  const [editingIndex, setEditingIndex] = useState<number>(-1)
  const [altermaticMetadata, setAltermaticMetadata] = useState<any>(null)
  const [traitsDb, setTraitsDb] = useState<Record<string, string>>({})

  // Add Form states
  const [newVariantLabel, setNewVariantLabel] = useState("")
  const [newVariantCustom, setNewVariantCustom] = useState(true)
  const [newVariantSource, setNewVariantSource] = useState("base")

  // Edit Form states
  const [variantLabel, setVariantLabel] = useState("")
  const [selectedSkeletonSource, setSelectedSkeletonSource] = useState("base")
  const [selectedGender, setSelectedGender] = useState("None")
  const [isRarePal, setIsRarePal] = useState(false)
  const [skinName, setSkinName] = useState("")
  const [reqTraits, setReqTraits] = useState<string[]>([])
  const [prefTraits, setPrefTraits] = useState<string[]>([])
  const [matOverrides, setMatOverrides] = useState<Record<number, string>>({})
  const [morphs, setMorphs] = useState<any[]>([])

  // Sidecar slots & morph options
  const [slots, setSlots] = useState<string[]>([])
  const [traitSearch, setTraitSearch] = useState("")

  // Fetch Altermatic contextual metadata & traits database
  const loadAltermaticMetadata = async () => {
    try {
      const meta = await ModManagerAPI.altermaticMetadata(mod.name)
      setAltermaticMetadata(meta)

      const caches = await ModManagerAPI.getAltermaticCaches()
      if (caches && caches.traits_db) {
        setTraitsDb(caches.traits_db)
      } else if (caches && caches.passive_skills) {
        setTraitsDb(caches.passive_skills)
      }
    } catch (err) {
      console.error("Failed to load Altermatic metadata or caches:", err)
    }
  }

  useEffect(() => {
    if (altermaticEnabled) {
      loadAltermaticMetadata()
    }
  }, [altermaticEnabled, mod.name])

  // Dynamically load skeleton material slots whenever the source skeleton file changes
  useEffect(() => {
    if (isEditModalOpen && editingVariant) {
      const fetchSlots = async () => {
        try {
          const res = await ModManagerAPI.altermaticSidecar(mod.name, selectedSkeletonSource)
          if (res && res.status === "success" && res.data && res.data.materials) {
            setSlots(Object.keys(res.data.materials))
          } else {
            // fallback
            setSlots(["mi_body", "mi_eye"])
          }
        } catch (err) {
          console.error("Failed to load sidecar slots:", err)
          setSlots(["mi_body", "mi_eye"])
        }
      }
      fetchSlots()
    }
  }, [selectedSkeletonSource, editingVariant, isEditModalOpen, mod.name])

  const handleIconChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    try {
      const reader = new FileReader()
      reader.onload = async () => {
        const arrBuffer = reader.result as ArrayBuffer
        const bytes = Array.from(new Uint8Array(arrBuffer))
        await ModManagerAPI.saveModIconBytes(mod.name, file.name, bytes)
        showNotification("Custom Pal Icon updated successfully!", "success")
        onRefresh()
      }
      reader.readAsArrayBuffer(file)
    } catch (err) {
      console.error("Failed to save icon:", err)
      showNotification(`Failed to save icon: ${err}`, "error", "Operation Failed")
    }
  }

  const handleAudioChange = async (slot: string, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    try {
      const reader = new FileReader()
      reader.onload = async () => {
        const arrBuffer = reader.result as ArrayBuffer
        const bytes = Array.from(new Uint8Array(arrBuffer))
        await ModManagerAPI.saveModAudioBytes(mod.name, slot, file.name, bytes)
        showNotification(`Custom audio override for ${slot} updated successfully!`, "success")
        onRefresh()
      }
      reader.readAsArrayBuffer(file)
    } catch (err) {
      console.error("Failed to save audio:", err)
      showNotification(`Failed to save audio: ${err}`, "error", "Operation Failed")
    }
  }

  const handleAudioClear = async (slot: string) => {
    try {
      if (confirm(`Are you sure you want to clear the custom override for ${slot}?`)) {
        await ModManagerAPI.audioClear(mod.name, slot)
        showNotification(`Cleared custom override for ${slot}.`, "success")
        onRefresh()
      }
    } catch (err) {
      console.error("Failed to clear audio:", err)
      showNotification(`Failed to clear audio: ${err}`, "error", "Operation Failed")
    }
  }

  const handleAudioPlay = async (slot: string) => {
    try {
      await ModManagerAPI.audioPlay(mod.name, slot)
    } catch (err) {
      console.error("Failed to play audio:", err)
      showNotification(`Failed to play audio: ${err}`, "error", "Playback Failed")
    }
  }

  const handleAltermaticToggle = async (enabled: boolean) => {
    try {
      await ModManagerAPI.altermaticToggle(mod.name, enabled)
      setAltermaticEnabled(enabled)
      showNotification(`Altermatic framework ${enabled ? "enabled" : "disabled"}.`, "success")
      onRefresh()
    } catch (err) {
      console.error("Failed to toggle Altermatic:", err)
      showNotification(`Failed to toggle Altermatic: ${err}`, "error", "Operation Failed")
    }
  }

  // ── Add Variant Actions ──
  const openAddModal = () => {
    setNewVariantLabel("")
    setNewVariantCustom(true)
    setNewVariantSource("base")
    setIsAddModalOpen(true)
  }

  const handleCreateVariant = async () => {
    const labelVal = newVariantLabel.trim()
    if (!labelVal) {
      showNotification("Variant Name/Label is required.", "warning", "Validation")
      return
    }
    try {
      await ModManagerAPI.altermaticAdd(mod.name, labelVal, newVariantCustom, newVariantSource)
      setIsAddModalOpen(false)
      showNotification(`Successfully created variant: ${labelVal}`, "success")
      onRefresh()
    } catch (err) {
      console.error("Failed to add variant:", err)
      showNotification(`Failed to add variant: ${err}`, "error", "Operation Failed")
    }
  }

  // ── Edit Variant Actions ──
  const handleEditVariant = (v: AltermaticVariant, index: number) => {
    setEditingVariant(v)
    setEditingIndex(index)
    const cleanLabel = v.is_base ? "base" : (v.label.startsWith(`${mod.name}_`) ? v.label.slice(mod.name.length + 1) : v.label)
    setVariantLabel(cleanLabel)
    setSelectedSkeletonSource(v.SkeletonSource || "base")
    setSelectedGender(v.Gender || "None")
    setIsRarePal(!!v.IsRarePal)
    setSkinName(v.SkinName || "")
    setReqTraits(v.ReqTrait || [])
    setPrefTraits(v.PrefTrait || [])
    
    // Parse Material Overrides
    const initialMatOverrides: Record<number, string> = {}
    if (v.MatReplace) {
      // Map Sequential Falls
      v.MatReplace.forEach((item: any) => {
        const idx = parseInt(item.Index)
        if (!isNaN(idx)) {
          const parts = item.MatPath.split("/")
          const matName = parts[parts.length - 1]
          initialMatOverrides[idx] = matName
        }
      })
    }
    setMatOverrides(initialMatOverrides)

    // Parse Morphs
    setMorphs(v.MorphTarget || [])
    setTraitSearch("")
    setIsEditModalOpen(true)
  }

  const handleOpenInBlender = async () => {
    if (!altermaticMetadata) return
    console.log(`Dispatched request to open model in Blender: ${selectedSkeletonSource}`)
    showNotification(`Opening ${selectedSkeletonSource} in Blender...`, "info", "Blender Dispatch")
    try {
      await ModManagerAPI.altermaticOpenBlend(mod.name, selectedSkeletonSource, altermaticMetadata.category)
    } catch (err) {
      console.error("Failed to open model in Blender:", err)
      showNotification(`Blender invocation failed: ${err}`, "error", "Launch Failed")
    }
  }

  const handleDeleteVariant = async () => {
    if (editingIndex === -1 || !editingVariant) return
    if (editingVariant.is_base) return
    
    if (confirm(`Are you sure you want to delete variant: ${editingVariant.label}?`)) {
      try {
        await ModManagerAPI.altermaticDelete(mod.name, editingIndex)
        setIsEditModalOpen(false)
        showNotification(`Deleted variant: ${editingVariant.label}`, "success")
        onRefresh()
      } catch (err) {
        console.error("Failed to delete variant:", err)
        showNotification(`Failed to delete variant: ${err}`, "error", "Operation Failed")
      }
    }
  }

  const handleSaveVariant = async () => {
    if (editingIndex === -1 || !editingVariant) return

    try {
      // Build Sequential Material Overrides
      const matReplaces = Object.entries(matOverrides)
        .filter(([_, val]) => val && val !== "default")
        .map(([idxStr, val]) => {
          const idx = parseInt(idxStr)
          const slotName = slots[idx] || "mi_body"
          const category = altermaticMetadata?.category || "Monster"
          const resolvedMatPath = `/Game/Palbaker/Model/Character/${category}/${mod.name}/${val}`.replace(/ /g, "_")
          return {
            Index: idxStr,
            MatPath: resolvedMatPath,
            SlotName: slotName
          }
        })

      const payload = {
        label: editingVariant.is_base ? "base" : variantLabel,
        CharacterID: mod.name,
        SkeletonSource: selectedSkeletonSource,
        Gender: selectedGender,
        IsRarePal: isRarePal,
        SkinName: skinName,
        ReqTrait: reqTraits,
        PrefTrait: prefTraits,
        MatReplace: matReplaces,
        MorphTarget: morphs,
        is_base: editingVariant.is_base
      }

      await ModManagerAPI.altermaticSave(editingIndex, payload)
      setIsEditModalOpen(false)
      showNotification("Variant changes compiled and saved successfully!", "success")
      onRefresh()
    } catch (err) {
      console.error("Failed to save variant payload:", err)
      showNotification(`Failed to save variant changes: ${err}`, "error", "Operation Failed")
    }
  }

  // Fuzzy Traits Search List
  const filteredTraits = useMemo(() => {
    const q = traitSearch.trim().toLowerCase()
    if (!q) return []
    return Object.entries(traitsDb)
      .filter(([displayName, id]) => displayName.toLowerCase().includes(q) || id.toLowerCase().includes(q))
      .filter(([_, id]) => !reqTraits.includes(id) && !prefTraits.includes(id))
      .slice(0, 5)
  }, [traitSearch, traitsDb, reqTraits, prefTraits])

  // Morph values update helper
  const updateMorphType = (target: string, type: "None" | "Static" | "Random") => {
    setMorphs((prev) => {
      const filtered = prev.filter((m) => m.Target !== target)
      if (type === "None") return filtered
      if (type === "Static") {
        return [...filtered, { Target: target, Type: "Static", Set: 0.5 }]
      }
      return [...filtered, { Target: target, Type: "Random", Min: 0.0, Max: 1.0, TypeVal: "Free" }]
    })
  }

  const updateMorphValue = (target: string, key: string, value: any) => {
    setMorphs((prev) =>
      prev.map((m) => {
        if (m.Target === target) {
          if (m.Type === "Static") {
            return { ...m, Set: value }
          } else {
            return { ...m, [key]: value }
          }
        }
        return m
      })
    )
  }

  // Preloaded/Active blendshapes list
  const activeMorphTargets = ["breast_size", "belly_fat", "waist_width", "height_scale"]

  return (
    <div className="border-t border-border px-5 py-5">
      <div className="flex gap-6 items-start">

        {/* ── Col 1: Custom Pal Icon ── */}
        <div className="flex flex-col gap-2 shrink-0">
          <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">
            Custom Pal Icon
          </span>
          <input
            type="file"
            ref={iconInputRef}
            onChange={handleIconChange}
            accept="image/png, image/dds"
            className="hidden"
          />
          <button
            onClick={() => iconInputRef.current?.click()}
            className="size-20 rounded border border-border bg-muted/50 flex flex-col items-center justify-center gap-1 hover:border-primary/50 transition-colors group cursor-pointer"
            title="Click to set custom Pal Icon"
          >
            {mod.has_icon ? (
              <div className="size-full rounded flex items-center justify-center bg-muted relative">
                {mod.icon_path ? (
                  <img
                    src={typeof window !== "undefined" && (window as any).__TAURI_INTERNALS__ !== undefined
                      ? convertFileSrc(mod.icon_path)
                      : mod.icon_path.startsWith("http") ? mod.icon_path : `https://asset.localhost/${mod.icon_path}`
                    }
                    alt="Custom Pal Icon"
                    className="size-full object-cover rounded"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none';
                    }}
                  />
                ) : null}
                <span className="text-muted-foreground text-xs font-mono absolute">icon</span>
              </div>
            ) : (
              <>
                <ImagePlus className="size-6 text-muted-foreground group-hover:text-primary transition-colors" />
              </>
            )}
          </button>
          <span className="text-muted-foreground text-xs font-mono">64×64 PNG/DDS</span>
        </div>

        <Separator orientation="vertical" className="self-stretch opacity-50" />

        {/* ── Col 2: Cries Replacement ── */}
        <div className="flex flex-col gap-2 flex-1 min-w-0">
          <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">
            Cries Replacement
          </span>

          {!hasSoundData ? (
            <p className="text-muted-foreground text-xs italic">
              {mod.has_fmodel
                ? "No mapped audio database found for this Pal."
                : "Audio replacement requires raw FModel files. Click 'Create .blend file' or 'Generate Sources' first."}
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-2">
              {availableCries.map((slot) => {
                const hasOverride = !!mod.audio_overrides[slot]
                return (
                  <div
                    key={slot}
                    className={cn(
                      "flex items-center gap-2 rounded px-3 py-2 border",
                      hasOverride
                        ? "bg-primary/5 border-primary/30"
                        : "bg-muted/50 border-border",
                    )}
                  >
                    <input
                      type="file"
                      ref={(el) => { audioInputRefs.current[slot] = el }}
                      onChange={(e) => handleAudioChange(slot, e)}
                      accept="audio/wav, audio/mp3, audio/ogg"
                      className="hidden"
                    />
                    <button
                      onClick={() => handleAudioPlay(slot)}
                      className="shrink-0 size-6 rounded-full bg-primary/10 hover:bg-primary/20 flex items-center justify-center transition-colors cursor-pointer"
                    >
                      <Play className="size-3 text-primary" />
                    </button>
                    <div className="flex-1 min-w-0">
                      <div className="text-foreground text-xs font-semibold">{slot}</div>
                      <div className={cn("text-[10px] truncate", hasOverride ? "text-status-warning" : "text-muted-foreground")}>
                        {hasOverride ? "Custom Override" : "Original Game Sound"}
                      </div>
                    </div>
                    {hasOverride ? (
                      <button
                        onClick={() => handleAudioClear(slot)}
                        className="shrink-0 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                      >
                        <Trash2 className="size-3.5 text-status-error" />
                      </button>
                    ) : (
                      <button
                        onClick={() => audioInputRefs.current[slot]?.click()}
                        className="shrink-0 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                      >
                        <Upload className="size-3.5" />
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <Separator orientation="vertical" className="self-stretch opacity-50" />

        {/* ── Col 3: Altermatic Variants ── */}
        <div className="flex flex-col gap-2 min-w-[220px] shrink-0">
          <div className="flex items-center justify-between gap-3">
            <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider">
              Altermatic Variants
            </span>
            {/* Toggle switch */}
            <label className="flex items-center gap-1.5 cursor-pointer shrink-0">
              <span className="text-xs text-muted-foreground font-mono">ENABLE</span>
              <div className="relative w-9 h-5">
                <input
                  type="checkbox"
                  checked={altermaticEnabled}
                  onChange={(e) => handleAltermaticToggle(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-muted border border-border peer-checked:bg-primary rounded-full transition-colors" />
                <div className="absolute top-0.5 left-0.5 size-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
              </div>
            </label>
          </div>

          {altermaticEnabled && (
            <div className="flex flex-col gap-2">
              {(mod.altermatic_variants || []).length === 0 ? (
                <p className="text-muted-foreground text-xs italic">No custom variants added yet.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {(mod.altermatic_variants || []).map((v, i) => (
                    <VariantChip key={i} variant={v} modName={mod.name} onClick={() => handleEditVariant(v, i)} />
                  ))}
                </div>
              )}
              <button
                onClick={openAddModal}
                className="flex items-center justify-center gap-1.5 border border-dashed border-border rounded px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:border-primary/50 transition-colors mt-1 cursor-pointer"
              >
                <Plus className="size-3.5" />
                ADD VARIANT
              </button>
            </div>
          )}
        </div>

      </div>

      {/* ── ADD VARIANT MODAL ── */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-background border border-border rounded-lg shadow-lg w-full max-w-md flex flex-col p-6 gap-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-lg text-foreground">Add New {mod.localized_name || mod.name} Variant</h3>
              <button onClick={() => setIsAddModalOpen(false)} className="text-muted-foreground hover:text-foreground">
                <X className="size-5" />
              </button>
            </div>

            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs text-muted-foreground font-semibold uppercase">New Variant Name/Label</label>
                <input
                  type="text"
                  placeholder="e.g., Bikini_Gold_Trim"
                  value={newVariantLabel}
                  onChange={(e) => setNewVariantLabel(e.target.value)}
                  className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                />
              </div>

              <div className="flex items-center justify-between border-t border-b border-border py-3">
                <div className="flex flex-col gap-0.5">
                  <span className="text-sm font-semibold text-foreground">Custom Model Blend</span>
                  <span className="text-xs text-muted-foreground">Create a custom .blend file for this variant?</span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={newVariantCustom}
                    onChange={(e) => {
                      setNewVariantCustom(e.target.checked)
                      if (!e.target.checked) setNewVariantSource("base")
                    }}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-muted border border-border peer-checked:bg-primary rounded-full transition-colors" />
                  <div className="absolute top-0.5 left-0.5 size-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
                </label>
              </div>

              {newVariantCustom && (
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs text-muted-foreground font-semibold uppercase">Clone Skeleton Template From</label>
                  <div className="relative">
                    <select
                      value={newVariantSource}
                      onChange={(e) => setNewVariantSource(e.target.value)}
                      className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary appearance-none pr-8 cursor-pointer"
                    >
                      <option value="base" className="bg-background">base (Vanilla Canonical Mesh)</option>
                      {(altermaticMetadata?.blend_files || []).map((file: string) => (
                        <option key={file} value={file} className="bg-background">
                          Variant: {file.startsWith(`${mod.name}_`) ? file.slice(mod.name.length + 1) : file}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-2.5 top-2.5 size-4 text-muted-foreground pointer-events-none" />
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 mt-4">
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="inline-flex h-9 items-center justify-center rounded px-4 text-sm font-semibold border border-input bg-transparent hover:bg-muted/50 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateVariant}
                className="inline-flex h-9 items-center justify-center rounded bg-primary text-primary-foreground px-4 text-sm font-semibold hover:bg-primary/90 transition-colors cursor-pointer shadow"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── EDIT VARIANT CONFIGURATOR MODAL ── */}
      {isEditModalOpen && editingVariant && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-background border border-border rounded-lg shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
            
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <div className="flex flex-col">
                <span className="text-[10px] text-primary uppercase font-mono font-bold tracking-wider">Visual Altermatic Configurator</span>
                <h3 className="font-bold text-lg text-foreground">
                  Configurator: {editingVariant.is_base ? "Base Model" : (editingVariant.label.startsWith(`${mod.name}_`) ? editingVariant.label.slice(mod.name.length + 1) : editingVariant.label)}
                </h3>
              </div>
              <button onClick={() => setIsEditModalOpen(false)} className="text-muted-foreground hover:text-foreground">
                <X className="size-5" />
              </button>
            </div>

            {/* Scrollable Form Body */}
            <div className="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-6">

              {/* SECTION 1: General Settings */}
              <div className="border border-border rounded-lg p-4 bg-muted/10 flex flex-col gap-4">
                <span className="text-xs text-primary font-bold font-mono tracking-wider uppercase">1. General Settings</span>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1.5">
                    <label className="text-[11px] text-muted-foreground uppercase font-semibold">Variant Label</label>
                    <input
                      type="text"
                      disabled={editingVariant.is_base}
                      readOnly={editingVariant.is_base}
                      value={variantLabel}
                      onChange={(e) => setVariantLabel(e.target.value)}
                      className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors disabled:opacity-50"
                    />
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <label className="text-[11px] text-muted-foreground uppercase font-semibold">Skeleton Source</label>
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <select
                          value={selectedSkeletonSource}
                          onChange={(e) => setSelectedSkeletonSource(e.target.value)}
                          className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none appearance-none pr-8 cursor-pointer"
                        >
                          <option value="base" className="bg-background">base (Vanilla Canonical)</option>
                          {(altermaticMetadata?.blend_files || []).map((file: string) => (
                            <option key={file} value={file} className="bg-background">
                              Variant: {file.startsWith(`${mod.name}_`) ? file.slice(mod.name.length + 1) : file}
                            </option>
                          ))}
                        </select>
                        <ChevronDown className="absolute right-2.5 top-2.5 size-4 text-muted-foreground pointer-events-none" />
                      </div>
                      
                      {selectedSkeletonSource !== "base" && (
                        <button
                          onClick={handleOpenInBlender}
                          className="px-3 rounded border border-primary/40 bg-primary/5 text-primary text-xs font-semibold hover:bg-primary/10 transition-colors disabled:opacity-50 cursor-pointer"
                        >
                          Blender
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                {!editingVariant.is_base && (
                  <div className="grid grid-cols-2 gap-4 border-t border-border pt-4">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[11px] text-muted-foreground uppercase font-semibold">Gender Override</label>
                      <div className="relative">
                        <select
                          value={selectedGender}
                          onChange={(e) => setSelectedGender(e.target.value)}
                          className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none appearance-none pr-8 cursor-pointer"
                        >
                          <option value="None" className="bg-background">None (Ignore Gender)</option>
                          <option value="Male" className="bg-background">Male Only</option>
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

                {!editingVariant.is_base && (
                  <div className="flex items-center justify-between border-t border-border pt-3">
                    <div className="flex flex-col gap-0.5">
                      <span className="text-sm font-semibold text-foreground">Is Lucky Pal? (IsRarePal)</span>
                      <span className="text-xs text-muted-foreground">Only spawn on lucky/giant Pal instances.</span>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={isRarePal}
                        onChange={(e) => setIsRarePal(e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-9 h-5 bg-muted border border-border peer-checked:bg-primary rounded-full transition-colors" />
                      <div className="absolute top-0.5 left-0.5 size-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
                    </label>
                  </div>
                )}
              </div>

              {/* SECTION 2: Passive Traits */}
              {!editingVariant.is_base && (
                <div className="border border-border rounded-lg p-4 bg-muted/10 flex flex-col gap-4">
                  <span className="text-xs text-primary font-bold font-mono tracking-wider uppercase">2. Passive Traits Requirements</span>
                  
                  {/* Tag list */}
                  <div className="flex flex-wrap gap-1.5 min-h-[32px] border border-border rounded p-2 bg-background/50">
                    {reqTraits.length === 0 && prefTraits.length === 0 && (
                      <span className="text-xs text-muted-foreground italic">No conditions added. This variant will spawn by default.</span>
                    )}
                    {reqTraits.map((id) => {
                      const label = Object.keys(traitsDb).find((k) => traitsDb[k] === id) || id
                      return (
                        <span key={id} className="flex items-center gap-1 bg-green-950 border border-green-800 text-green-300 text-[10px] font-bold px-2 py-0.5 rounded">
                          Req: {label}
                          <button onClick={() => setReqTraits((p) => p.filter((x) => x !== id))} className="hover:text-white shrink-0">
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
                          <button onClick={() => setPrefTraits((p) => p.filter((x) => x !== id))} className="hover:text-white shrink-0">
                            <X className="size-3" />
                          </button>
                        </span>
                      )
                    })}
                  </div>

                  {/* Fuzzy Search tag finder */}
                  <div className="flex flex-col gap-1.5 relative">
                    <input
                      type="text"
                      placeholder="Fuzzy Search Passive Traits (e.g. Swift, Legend...)"
                      value={traitSearch}
                      onChange={(e) => setTraitSearch(e.target.value)}
                      className="flex h-9 w-full rounded border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                    />

                    {filteredTraits.length > 0 && (
                      <div className="absolute top-10 left-0 right-0 border border-border bg-background shadow-lg rounded-md z-40 flex flex-col overflow-hidden">
                        {filteredTraits.map(([display, id]) => (
                          <div key={id} className="flex items-center justify-between px-3 py-2 border-b border-border/50 last:border-0 hover:bg-muted/40 transition-colors">
                            <span className="text-xs text-foreground font-semibold">{display} <span className="text-[10px] text-muted-foreground font-mono">({id})</span></span>
                            <div className="flex gap-2">
                              <button
                                onClick={() => {
                                  setReqTraits((p) => [...p, id])
                                  setTraitSearch("")
                                }}
                                className="px-2 py-1 border border-green-700/50 bg-green-950/20 text-[10px] text-green-400 rounded font-semibold hover:bg-green-950/50"
                              >
                                + Req
                              </button>
                              <button
                                onClick={() => {
                                  setPrefTraits((p) => [...p, id])
                                  setTraitSearch("")
                                }}
                                className="px-2 py-1 border border-purple-700/50 bg-purple-950/20 text-[10px] text-purple-400 rounded font-semibold hover:bg-purple-950/50"
                              >
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

              {/* SECTION 3: Visual Material Overrides */}
              {!editingVariant.is_base && (
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

              {/* SECTION 4: Morphs Targets */}
              {!editingVariant.is_base && (
                <div className="border border-border rounded-lg p-4 bg-muted/10 flex flex-col gap-4">
                  <span className="text-xs text-primary font-bold font-mono tracking-wider uppercase">4. Morph Target Parameters</span>

                  <div className="flex flex-col gap-4">
                    {activeMorphTargets.map((morphName) => {
                      const config = morphs.find((m) => m.Target === morphName)
                      const type = config ? config.Type : "None"

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
                                <option value="None" className="bg-background">Ignore/Default</option>
                                <option value="Static" className="bg-background">Static (Set)</option>
                                <option value="Random" className="bg-background">Random (Range)</option>
                              </select>
                              <ChevronDown className="absolute right-2 top-2 size-3 text-muted-foreground pointer-events-none" />
                            </div>
                          </div>

                          {type === "Static" && (
                            <div className="flex items-center gap-3">
                              <span className="text-[10px] text-muted-foreground font-semibold uppercase shrink-0">Forced: {(config.Set ?? 0.5).toFixed(2)}</span>
                              <input
                                type="range"
                                min="0.0"
                                max="1.0"
                                step="0.05"
                                value={config.Set ?? 0.5}
                                onChange={(e) => updateMorphValue(morphName, "Set", parseFloat(e.target.value))}
                                className="flex-1 accent-primary h-1 bg-muted rounded-full cursor-pointer appearance-none"
                              />
                            </div>
                          )}

                          {type === "Random" && (
                            <div className="flex flex-col gap-2 pt-1 border-t border-border/20">
                              <div className="flex items-center gap-3">
                                <span className="text-[10px] text-muted-foreground font-semibold uppercase w-[80px] shrink-0">Min Bound: {(config.Min ?? 0.0).toFixed(2)}</span>
                                <input
                                  type="range"
                                  min="0.0"
                                  max="1.0"
                                  step="0.05"
                                  value={config.Min ?? 0.0}
                                  onChange={(e) => updateMorphValue(morphName, "Min", parseFloat(e.target.value))}
                                  className="flex-1 accent-primary h-1 bg-muted rounded-full cursor-pointer appearance-none"
                                />
                              </div>
                              <div className="flex items-center gap-3">
                                <span className="text-[10px] text-muted-foreground font-semibold uppercase w-[80px] shrink-0">Max Bound: {(config.Max ?? 1.0).toFixed(2)}</span>
                                <input
                                  type="range"
                                  min="0.0"
                                  max="1.0"
                                  step="0.05"
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
                                    <option value="Free" className="bg-background">Free Roll</option>
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
                {!editingVariant.is_base && (
                  <button
                    onClick={handleDeleteVariant}
                    className="inline-flex h-9 items-center justify-center rounded bg-status-error/10 text-status-error px-4 text-sm font-semibold hover:bg-status-error/20 transition-colors border border-status-error/25 cursor-pointer"
                  >
                    Delete Variant
                  </button>
                )}
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setIsEditModalOpen(false)}
                  className="inline-flex h-9 items-center justify-center rounded px-4 text-sm font-semibold border border-input bg-transparent hover:bg-muted/50 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveVariant}
                  className="inline-flex h-9 items-center justify-center rounded bg-primary text-primary-foreground px-4 text-sm font-semibold hover:bg-primary/90 transition-colors cursor-pointer shadow"
                >
                  Apply Changes
                </button>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* ── FLOATING NOTIFICATION TOASTS ── */}
      <div className="fixed top-6 right-6 z-[100] flex flex-col gap-3 max-w-sm w-full pointer-events-none">
        {notifications.map((n) => (
          <div
            key={n.id}
            className={cn(
              "p-4 rounded-lg border shadow-xl flex gap-3 items-start pointer-events-auto animate-in fade-in slide-in-from-top-4 duration-300 bg-background/95 backdrop-blur",
              n.type === "success" && "border-green-800/40 bg-green-950/20 text-green-300",
              n.type === "info" && "border-blue-800/40 bg-blue-950/20 text-blue-300",
              n.type === "error" && "border-red-800/40 bg-red-950/20 text-red-300",
              n.type === "warning" && "border-amber-800/40 bg-amber-950/20 text-amber-300"
            )}
          >
            <div className="flex-1">
              {n.title && <div className="font-bold text-sm mb-0.5">{n.title}</div>}
              <div className="text-xs">{n.message}</div>
            </div>
            <button
              onClick={() => setNotifications((prev) => prev.filter((x) => x.id !== n.id))}
              className="text-muted-foreground hover:text-foreground shrink-0 cursor-pointer"
            >
              <X className="size-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
