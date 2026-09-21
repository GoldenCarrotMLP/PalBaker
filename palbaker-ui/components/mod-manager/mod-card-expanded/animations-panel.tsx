"use client"

import { useState, useMemo } from "react"
import { 
  DownloadCloud, 
  UploadCloud, 
  Film, 
  CheckCircle2, 
  XCircle, 
  Bell, 
  Loader2, 
  Copy, 
  Check, 
  Layers, 
  AlertCircle, 
  Search, 
  Activity, 
  Gauge, 
  Plus, 
  Trash2 
} from "lucide-react"
import { cn } from "@/lib/utils"
import { type ModItem, type CustomAnimationEntry, type BlendSpaceDef } from "@/lib/mock-data"
import { ModManagerAPI } from "@/lib/data-service"
import { ALL_ENGINE_ANIM_SLOTS } from "@/lib/animation-enums"
import { EditNotifiesModal } from "./edit-notifies-modal"
import { useTaskQueue } from "@/lib/task-queue-context"

interface Props {
  mod: ModItem
  onRefresh: () => void
  onNotify: (msg: string, type: "success" | "info" | "error" | "warning", title?: string) => void
  onUpdateMod?: (modKey: string, patch: Partial<ModItem>) => void
}

type ViewSection = "rests" | "blendspaces" | "mapped" | "unmapped"
type SlotCategory = "all" | "GeneralMontage" | "ActionMontage"

export function AnimationsPanel({ mod, onRefresh, onNotify, onUpdateMod }: Props) {
  const [activeSection, setActiveSection] = useState<ViewSection>("mapped")
  const [slotCategory, setSlotCategory] = useState<SlotCategory>("all")
  const [slotSearch, setSlotSearch] = useState("")
  const [copiedTrack, setCopiedTrack] = useState<string | null>(null)

  const [dumping, setDumping] = useState(false)
  const [pushing, setPushing] = useState(false)
  const [selectedAnimKey, setSelectedAnimKey] = useState<string | null>(null)

  const customAnims = mod.custom_animations
  const isActive = customAnims?.is_active ?? false

  const animsList: [string, CustomAnimationEntry][] = customAnims?.anims ? Object.entries(customAnims.anims) : []
  const blendSpacesList: [string, BlendSpaceDef][] = customAnims?.blend_spaces ? Object.entries(customAnims.blend_spaces) : []

  // Extract Random Rests vs Standard Montages
  const restList = useMemo(() => animsList.filter(([, a]) => a.category === "RandomRest"), [animsList])
  const montagesOnlyList = useMemo(
    () => animsList.filter(([, a]) => a.category !== "BlendSpaceSample" && a.category !== "RandomRest"), 
    [animsList]
  )

  const handleToggleActive = async (val: boolean) => {
    const updated = { ...(customAnims || { anims: {}, blend_spaces: {} }), is_active: val }
    if (onUpdateMod) onUpdateMod(mod.id || mod.name, { custom_animations: updated as any })
    try {
      await ModManagerAPI.toggleAnimations(mod.base_pal, mod.name, val)
      onNotify(
        val
          ? "Custom animations framework enabled."
          : "Custom animations disabled. Next push will revert to the shared vanilla skeleton.",
        "success"
      )
      if (val && Object.keys(updated.anims || {}).length === 0) {
        onNotify("Click 'Dump & Map Data' to extract animations into your Blender file!", "info")
      }
    } catch (err) {
      onNotify(`Failed to toggle animations: ${err}`, "error")
    }
  }

  const handleCopyTrackName = async (trackName: string) => {
    try {
      await navigator.clipboard.writeText(trackName)
      setCopiedTrack(trackName)
      setTimeout(() => setCopiedTrack(null), 1800)
    } catch {}
  }

  const unmappedSlots = useMemo(() => {
    const existingKeys = new Set(
      animsList.flatMap(([k, v]) => [
        k.toLowerCase(),
        v.enum_key?.toLowerCase(),
        v.nla_track_name?.toLowerCase(),
        v.sequence_asset?.toLowerCase(),
        v.montage_asset?.toLowerCase()
      ].filter(Boolean))
    )

    return ALL_ENGINE_ANIM_SLOTS.filter((slot) => {
      if (slot.category === "BlendSpace") return false // BlendSpaces handled in their own dashboard
      
      const isMapped = existingKeys.has(slot.shortName.toLowerCase()) || 
                       existingKeys.has(slot.enumKey.toLowerCase()) ||
                       slot.expectedNlaTracks.some(t => existingKeys.has(t.toLowerCase()))
                       
      return !isMapped
    })
  }, [animsList])

  const filteredUnmapped = useMemo(
    () => unmappedSlots.filter(
      (slot) => 
        (slotCategory === "all" || slot.category === slotCategory) && 
        (!slotSearch.trim() || slot.shortName.toLowerCase().includes(slotSearch.toLowerCase().trim()))
    ), 
    [unmappedSlots, slotCategory, slotSearch]
  )

  const { addTask } = useTaskQueue()

  const handleDump = () => {
    addTask({
      name: mod.name,
      basePal: mod.base_pal,
      actionKey: "dump_anims",
      actionLabel: "Dump & Map Animations",
      channel: "unreal",
      run: async () => {
        setDumping(true)
        try {
          const res = await ModManagerAPI.dumpAnimations(mod.base_pal, mod.name)
          if (res?.custom_animations && onUpdateMod) {
            onUpdateMod(mod.id || mod.name, { custom_animations: res.custom_animations })
          }
          return res
        } finally {
          setDumping(false)
        }
      },
      onSuccess: (res) => {
        onNotify(res?.message || "Animations dumped successfully! ;3", "success")
        onRefresh()
      },
      onError: (err) => onNotify(`Dump failed: ${err}`, "error")
    })
  }

  const handlePushAnims = () => {
    addTask({
      name: mod.name,
      basePal: mod.base_pal,
      actionKey: "push_anims",
      actionLabel: "Push Animations & Montages",
      channel: "unreal",
      run: async () => {
        setPushing(true)
        try {
          return await ModManagerAPI.pushAnimations(mod.base_pal, mod.name)
        } finally {
          setPushing(false)
        }
      },
      onSuccess: (res) => {
        onNotify(res?.message || "Custom animations compiled! ;3", "success")
        onRefresh()
      },
      onError: (err) => onNotify(`Push animations failed: ${err}`, "error")
    })
  }

  const handleUpdateRest = async (key: string, field: string, value: number) => {
    if (!customAnims) return
    const updated = { ...customAnims }
    updated.anims[key].rest_props = { ...updated.anims[key].rest_props!, [field]: value }
    if (onUpdateMod) onUpdateMod(mod.id || mod.name, { custom_animations: updated })
    await ModManagerAPI.saveAnimationsSidecar(mod.base_pal, mod.name, updated)
  }

  const handleAddRest = async () => {
    if (!customAnims) return
    const nextIdx = restList.length + 1
    const newKey = `Rest_${nextIdx}_AM_${mod.name}_Rest0${nextIdx}`
    const updated = { ...customAnims }
    updated.anims[newKey] = {
      category: "RandomRest",
      enum_key: `Rest_${nextIdx}`,
      display_name: `Idle/Rest: Rest0${nextIdx}`,
      montage_asset: `AM_${mod.name}_Rest0${nextIdx}`,
      sequence_asset: `AS_${mod.name}_Rest0${nextIdx}`,
      nla_track_name: `Rest0${nextIdx}`,
      in_nla: false,
      is_modified: false,
      notifies: [],
      rest_props: { weight: 1.0, loop_min: 1, loop_max: 1, after_idle_time: 2.0 }
    }
    if (onUpdateMod) onUpdateMod(mod.id || mod.name, { custom_animations: updated })
    await ModManagerAPI.saveAnimationsSidecar(mod.base_pal, mod.name, updated)
  }

  const handleDeleteRest = async (key: string) => {
    if (!customAnims) return
    const updated = { ...customAnims }
    delete updated.anims[key]
    if (onUpdateMod) onUpdateMod(mod.id || mod.name, { custom_animations: updated })
    await ModManagerAPI.saveAnimationsSidecar(mod.base_pal, mod.name, updated)
  }

  return (
    <div className="flex flex-col gap-4 w-full">
      {/* Header Controls with Toggle Switch */}
      <div className="flex items-center justify-between bg-muted/20 p-3 rounded-lg border border-border">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-foreground">
            <Film className={cn("size-4", isActive ? "text-primary" : "text-muted-foreground")} />
            <span>Animations, BlendSpaces & Rests</span>
          </div>
          <label className="flex items-center gap-1.5 cursor-pointer shrink-0">
            <span className="text-xs text-muted-foreground font-mono">ENABLE</span>
            <div className="relative w-9 h-5">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => handleToggleActive(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-9 h-5 bg-muted border border-border peer-checked:bg-primary rounded-full transition-colors" />
              <div className="absolute top-0.5 left-0.5 size-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
            </div>
          </label>
        </div>
        
        {isActive && (
          <div className="flex items-center gap-2">
            <button
              onClick={handleDump}
              disabled={dumping || pushing}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded text-xs font-bold border border-primary/40 bg-primary/10 text-primary hover:bg-primary/20 transition-colors shadow-sm cursor-pointer disabled:opacity-50"
            >
              {dumping ? <Loader2 className="size-3.5 animate-spin" /> : <DownloadCloud className="size-3.5" />} Dump & Map Data
            </button>
            <button
              onClick={handlePushAnims}
              disabled={dumping || pushing}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded text-xs font-bold bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-md cursor-pointer disabled:opacity-50"
            >
              {pushing ? <Loader2 className="size-3.5 animate-spin" /> : <UploadCloud className="size-3.5" />} Push Animations
            </button>
          </div>
        )}
      </div>

      {/* Main Panel Content (Hidden if disabled) */}
      {isActive && (
        <div className="grid grid-cols-[200px_1fr] gap-4 min-h-[300px] animate-in fade-in slide-in-from-top-2 duration-300">
          {/* Left Side: Vertical Tabs */}
          <div className="flex flex-col gap-1.5 border-r border-border/50 pr-4">
            <button
              onClick={() => setActiveSection("mapped")}
              className={`flex items-center gap-2 px-3 py-2.5 rounded text-xs font-semibold transition-all cursor-pointer ${
                activeSection === "mapped" ? "bg-primary text-primary-foreground shadow-md" : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              }`}
            >
              <Layers className="size-4" /> Montages & Actions ({montagesOnlyList.length})
            </button>
            <button
              onClick={() => setActiveSection("rests")}
              className={`flex items-center gap-2 px-3 py-2.5 rounded text-xs font-semibold transition-all cursor-pointer ${
                activeSection === "rests" ? "bg-primary text-primary-foreground shadow-md" : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              }`}
            >
              <Activity className="size-4" /> Random Rests ({restList.length})
            </button>
            <button
              onClick={() => setActiveSection("blendspaces")}
              className={`flex items-center gap-2 px-3 py-2.5 rounded text-xs font-semibold transition-all cursor-pointer ${
                activeSection === "blendspaces" ? "bg-primary text-primary-foreground shadow-md" : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              }`}
            >
              <Gauge className="size-4" /> Locomotion BlendSpaces ({blendSpacesList.length})
            </button>
            <button
              onClick={() => setActiveSection("unmapped")}
              className={`flex items-center gap-2 px-3 py-2.5 rounded text-xs font-semibold transition-all cursor-pointer ${
                activeSection === "unmapped" ? "bg-primary text-primary-foreground shadow-md" : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              }`}
            >
              <AlertCircle className="size-4" /> Unmapped Slots ({unmappedSlots.length})
            </button>
          </div>

          {/* Right Side: Tab Content */}
          <div className="flex flex-col min-w-0">
            {/* Rests Tab */}
            {activeSection === "rests" && (
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground leading-relaxed">
                    These idle animations loop randomly while the Pal is resting. You can add as many as you want!
                  </span>
                  <button
                    onClick={handleAddRest}
                    className="flex items-center gap-1.5 px-3 py-1.5 border border-primary/50 text-primary text-xs font-bold rounded hover:bg-primary/10 cursor-pointer"
                  >
                    <Plus className="size-3.5" /> Add Rest Cycle
                  </button>
                </div>

                <div className="flex flex-col gap-2 max-h-[400px] overflow-y-auto pr-2">
                  {restList.map(([key, anim]) => (
                    <div key={key} className="bg-muted/30 border border-border/50 rounded-lg p-3 flex flex-col gap-3">
                      <div className="flex items-center justify-between border-b border-border/40 pb-2">
                        <div className="flex items-center gap-2">
                          <span title={anim.in_nla ? "Present in Blender NLA Track" : "Missing in NLA Track"} className="flex items-center">
                            {anim.in_nla ? (
                              <CheckCircle2 className="size-3.5 text-status-success" />
                            ) : (
                              <XCircle className="size-3.5 text-muted-foreground" />
                            )}
                          </span>
                          <span className="font-bold text-sm text-foreground">{anim.display_name}</span>
                          <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground font-mono">
                            NLA Track: {anim.nla_track_name}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleCopyTrackName(anim.nla_track_name!)}
                            className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono border border-border/60 hover:border-primary text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
                          >
                            {copiedTrack === anim.nla_track_name ? <Check className="size-3" /> : <Copy className="size-3" />}
                            {copiedTrack === anim.nla_track_name ? "Copied" : "Copy Name"}
                          </button>
                          <button
                            onClick={() => handleDeleteRest(key)}
                            className="text-muted-foreground hover:text-status-error p-1 cursor-pointer transition-colors"
                          >
                            <Trash2 className="size-4" />
                          </button>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-4 gap-4">
                        <div className="flex flex-col gap-1.5">
                          <label className="text-[10px] uppercase font-bold text-muted-foreground">Selection Weight</label>
                          <input
                            type="number"
                            step="0.1"
                            value={anim.rest_props?.weight}
                            onChange={(e) => handleUpdateRest(key, "weight", parseFloat(e.target.value))}
                            className="bg-background border border-border rounded px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                        </div>
                        <div className="flex flex-col gap-1.5">
                          <label className="text-[10px] uppercase font-bold text-muted-foreground">Min Loops</label>
                          <input
                            type="number"
                            min="1"
                            value={anim.rest_props?.loop_min}
                            onChange={(e) => handleUpdateRest(key, "loop_min", parseInt(e.target.value))}
                            className="bg-background border border-border rounded px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                        </div>
                        <div className="flex flex-col gap-1.5">
                          <label className="text-[10px] uppercase font-bold text-muted-foreground">Max Loops</label>
                          <input
                            type="number"
                            min="1"
                            value={anim.rest_props?.loop_max}
                            onChange={(e) => handleUpdateRest(key, "loop_max", parseInt(e.target.value))}
                            className="bg-background border border-border rounded px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                        </div>
                        <div className="flex flex-col gap-1.5">
                          <label className="text-[10px] uppercase font-bold text-muted-foreground">Post-Idle Time (s)</label>
                          <input
                            type="number"
                            step="0.5"
                            value={anim.rest_props?.after_idle_time}
                            onChange={(e) => handleUpdateRest(key, "after_idle_time", parseFloat(e.target.value))}
                            className="bg-background border border-border rounded px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Montages Tab */}
            {activeSection === "mapped" && (
              <div className="grid grid-cols-2 gap-2 max-h-[400px] overflow-y-auto pr-2">
                {montagesOnlyList.map(([key, anim]) => (
                  <div
                    key={key}
                    className="flex items-center justify-between gap-2 py-2 px-3 border border-border/40 bg-muted/20 hover:bg-muted/40 rounded-lg transition-colors text-xs"
                  >
                    <div className="flex flex-col min-w-0">
                      <div className="flex items-center gap-1.5 truncate">
                        {anim.in_nla ? (
                          <CheckCircle2 className="size-3.5 text-status-success shrink-0" />
                        ) : (
                          <XCircle className="size-3.5 text-muted-foreground shrink-0" />
                        )}
                        <span className="font-bold text-foreground truncate">{anim.display_name}</span>
                      </div>
                      <span className="text-[10px] text-muted-foreground font-mono truncate pl-5">
                        NLA: {anim.nla_track_name}
                      </span>
                    </div>
                    <button
                      onClick={() => setSelectedAnimKey(key)}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-border hover:border-primary text-muted-foreground hover:text-foreground transition-colors cursor-pointer shrink-0"
                    >
                      <Bell className="size-3.5 text-primary" /> <span>{anim.notifies?.length || 0}</span>
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* BlendSpaces Tab */}
            {activeSection === "blendspaces" && (
              <div className="flex flex-col gap-3 max-h-[400px] overflow-y-auto pr-2">
                {blendSpacesList.map(([bsKey, bs]) => (
                  <div key={bsKey} className="border border-border/50 rounded-lg p-3 bg-muted/10 flex flex-col gap-3">
                    <div className="flex items-center justify-between border-b border-border/40 pb-2">
                      <div className="flex items-center gap-2">
                        <Gauge className="size-4 text-primary shrink-0" />
                        <span className="font-bold text-sm text-foreground">{bsKey}</span>
                      </div>
                      <span className="text-[10px] font-mono bg-muted px-2 py-1 rounded text-muted-foreground">
                        Axis: {bs.axis_name} (0 – {bs.max_speed})
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      {bs.samples.map((s, idx) => {
                        const isCopied = copiedTrack === s.clean_name
                        return (
                          <div key={idx} className="flex items-center justify-between bg-background border border-border/50 px-3 py-2 rounded-md text-xs">
                            <div className="flex items-center gap-2 truncate">
                              {s.in_nla ? (
                                <CheckCircle2 className="size-3.5 text-status-success shrink-0" />
                              ) : (
                                <XCircle className="size-3.5 text-muted-foreground shrink-0" />
                              )}
                              <span className="font-mono text-primary font-bold w-12 shrink-0">{s.speed} u/s</span>
                              <span className="font-semibold text-foreground truncate">{s.clean_name}</span>
                            </div>
                            <button
                              onClick={() => handleCopyTrackName(s.clean_name)}
                              className={`flex items-center gap-1.5 px-2 py-1.5 rounded-md text-[10px] font-mono border transition-all cursor-pointer shrink-0 ${
                                isCopied
                                  ? "border-status-success bg-status-success/20 text-status-success font-bold"
                                  : "border-border/60 hover:border-primary text-muted-foreground hover:text-foreground hover:bg-muted"
                              }`}
                            >
                              {isCopied ? <Check className="size-3" /> : <Copy className="size-3" />}
                            </button>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Unmapped Tab */}
            {activeSection === "unmapped" && (
              <div className="flex flex-col gap-3 max-h-[400px] overflow-y-auto pr-2">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search unmapped slots (e.g. Rolling, Mining)..."
                    value={slotSearch}
                    onChange={(e) => setSlotSearch(e.target.value)}
                    className="w-full bg-muted/40 border border-border/60 rounded-lg px-3 py-2.5 pl-9 text-xs text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                  <Search className="size-4 absolute left-3 top-2.5 text-muted-foreground pointer-events-none" />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {filteredUnmapped.map((slot) => {
                    const isCopied = copiedTrack === slot.primaryNlaTrack
                    return (
                      <div
                        key={slot.enumKey}
                        className="flex items-center justify-between gap-2 py-2 px-3 border border-border/40 bg-muted/10 hover:bg-muted/30 rounded-lg transition-colors text-xs"
                      >
                        <div className="flex flex-col min-w-0 pr-2">
                          <span className="font-bold text-foreground truncate">{slot.shortName}</span>
                          <span className="text-[10px] text-muted-foreground font-mono truncate">
                            NLA: {slot.primaryNlaTrack}
                          </span>
                        </div>
                        <button
                          onClick={() => handleCopyTrackName(slot.primaryNlaTrack)}
                          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[10px] font-mono border transition-all cursor-pointer shrink-0 ${
                            isCopied
                              ? "border-status-success bg-status-success/20 text-status-success font-bold"
                              : "border-border/60 hover:border-primary text-muted-foreground hover:text-foreground hover:bg-muted"
                          }`}
                        >
                          {isCopied ? <Check className="size-3" /> : <Copy className="size-3" />}
                          <span>{copiedTrack === slot.primaryNlaTrack ? "Copied" : slot.primaryNlaTrack}</span>
                        </button>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {selectedAnimKey && customAnims?.anims?.[selectedAnimKey] && (
        <EditNotifiesModal
          basePal={mod.base_pal}
          modName={mod.name}
          animKey={selectedAnimKey}
          anim={customAnims.anims[selectedAnimKey]}
          onClose={() => setSelectedAnimKey(null)}
          onSaved={onRefresh}
          onNotify={onNotify}
        />
      )}
    </div>
  )
}